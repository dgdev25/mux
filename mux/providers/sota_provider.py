import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from mux.types import ModelResult


def _find_binary(name: str, configured_binary: str | None = None) -> str | None:
    candidate = configured_binary or name
    return shutil.which(candidate)


def _run_cli(binary: str, args: list[str], prompt: str, prompt_via: str = "arg", timeout: int = 300, cwd: str | None = None) -> tuple[bool, str]:
    cmd = [binary, *args]
    kwargs = {
        "text": True,
        "capture_output": True,
        "timeout": timeout,
        "cwd": cwd,
    }

    if prompt_via == "stdin":
        kwargs["input"] = prompt
    else:
        cmd.append(prompt)

    try:
        proc = subprocess.run(cmd, **kwargs)
    except Exception as e:
        return False, f"CLI_EXEC_ERROR: {e}"

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return False, f"CLI_EXIT_{proc.returncode}: {err[:3000]}"

    out = (proc.stdout or "").strip()
    return True, out


def _extract_codex_output(raw: str) -> str:
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    pieces: list[str] = []
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if isinstance(obj.get("output_text"), str):
            pieces.append(obj["output_text"])
            continue
        item = obj.get("item")
        if isinstance(item, dict):
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                pieces.append(item["text"])
                continue
            if item.get("type") == "message" and isinstance(item.get("content"), str):
                pieces.append(item["content"])
                continue
    if pieces:
        return "\n\n".join(p.strip() for p in pieces if p.strip()).strip()
    return raw.strip()


def _extract_workdir(task: str) -> str:
    candidates = re.findall(r"(/[^\s]+)", task)
    cleaned = [Path(c.rstrip('.,;:')) for c in sorted(candidates, key=len, reverse=True)]

    # 1) Existing explicit directories
    for p in cleaned:
      if p.exists() and p.is_dir():
          return str(p)

    # 2) If path looks like a file path and parent exists, use parent
    for p in cleaned:
        if p.suffix and p.parent.exists() and p.parent.is_dir():
            return str(p.parent)

    # 3) If a non-existing absolute path is provided, treat it as intended target directory
    # and create it (common project scaffold flow).
    for p in cleaned:
        if p.is_absolute() and not p.suffix:
            try:
                p.mkdir(parents=True, exist_ok=True)
                return str(p)
            except Exception:
                pass

    return os.getcwd()


def _tree_snapshot(root: str) -> set[str]:
    p = Path(root)
    if not p.exists():
        return set()
    files: set[str] = set()
    for f in p.rglob("*"):
        if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts and ".pytest_cache" not in f.parts:
            try:
                files.add(str(f.relative_to(p)))
            except Exception:
                files.add(str(f))
    return files


def _required_markers_from_task(task: str) -> list[str]:
    t = task.lower()
    markers: list[str] = []
    if "readme" in t:
        markers.append("README.md")
    if "test" in t:
        markers.append("tests")
    if "python cli" in t or "cli" in t:
        markers.append("cli")
    return markers


def run_sota(task: str, context: str, cfg: dict) -> ModelResult:
    scfg = cfg["providers"]["sota_cli"]
    tools = scfg.get("tools", {})
    order = scfg.get("preferred_order", ["codex", "claude", "gemini"])

    prompt = (
        "You are the escalation model in a local-first coding router. "
        "Return concise, implementation-focused guidance.\n\n"
        f"Task:\n{task}\n\n"
        f"Local context:\n{context}\n"
    )

    tried: list[str] = []
    for tool_name in order:
        tcfg = tools.get(tool_name, {})
        binary = _find_binary(tool_name, tcfg.get("binary"))
        if not binary:
            tried.append(f"{tool_name}:not_found")
            continue

        args = tcfg.get("advisory_args", tcfg.get("args", ["-p"]))
        prompt_via = tcfg.get("prompt_via", "arg")
        ok, raw = _run_cli(binary, args, prompt, prompt_via=prompt_via, timeout=300)
        if not ok:
            tried.append(f"{tool_name}:{raw[:160]}")
            continue

        output = _extract_codex_output(raw) if tool_name == "codex" else raw
        if not output:
            tried.append(f"{tool_name}:empty_output")
            continue

        return ModelResult(model=f"sota-cli:{tool_name}", output=output, confidence=0.9)

    return ModelResult(
        model="sota-cli:none",
        output="SOTA_PROVIDER_ERROR: no usable CLI backend found or all failed: " + " | ".join(tried),
        confidence=0.1,
    )


def run_executor(task: str, cfg: dict) -> ModelResult:
    scfg = cfg["providers"]["sota_cli"]
    tools = scfg.get("tools", {})
    order = scfg.get("preferred_order", ["codex", "claude", "gemini"])
    workdir = _extract_workdir(task)

    timeout_sec = int(scfg.get("executor_timeout_sec", 900))
    retries_if_no_change = int(scfg.get("retry_if_no_change", 1))

    wrapper = (
        "You are an execution agent. You must perform real filesystem changes in the target directory.\n\n"
        "Hard requirements:\n"
        "1. Create/modify files directly on disk (not just describe them).\n"
        f"2. Keep all work inside: {workdir}\n"
        "3. Do not use eval/exec for expression evaluation.\n"
        "4. After implementation, run verification commands:\n"
        "   - python3 -m pytest -q\n"
        "5. If tests fail, fix and re-run until passing or blocked.\n"
        "6. Final output must include:\n"
        "   - changed file list (absolute paths)\n"
        "   - test command + result\n"
        "   - any remaining risks\n\n"
        f"User task:\n{task}\n"
    )

    strict_retry = (
        "Your previous response did not produce observable file changes. "
        "Now execute the task and persist files on disk. Do not return only prose."
    )

    required_markers = _required_markers_from_task(task)
    before = _tree_snapshot(workdir)

    tried: list[str] = []
    for tool_name in order:
        tcfg = tools.get(tool_name, {})
        binary = _find_binary(tool_name, tcfg.get("binary"))
        if not binary:
            tried.append(f"{tool_name}:not_found")
            continue

        raw_args = tcfg.get("exec_args", tcfg.get("advisory_args", ["-p"]))
        args = [a.replace("{workdir}", workdir) for a in raw_args]
        prompt_via = tcfg.get("prompt_via", "arg")

        attempt = 0
        last_output = ""
        while attempt <= retries_if_no_change:
            attempt_prompt = wrapper if attempt == 0 else f"{wrapper}\n\n{strict_retry}"
            ok, raw = _run_cli(binary, args, attempt_prompt, prompt_via=prompt_via, timeout=timeout_sec, cwd=workdir)
            if not ok:
                last_output = raw
                break

            output = _extract_codex_output(raw) if tool_name == "codex" else raw
            last_output = output or "executed"

            after = _tree_snapshot(workdir)
            changed = sorted(list(after - before))
            marker_ok = all(any(m.lower() in c.lower() for c in after) for m in required_markers)

            if changed and marker_ok:
                return ModelResult(
                    model=f"executor:{tool_name}",
                    output=last_output + f"\n\n[mux] changed_files_count={len(changed)}",
                    confidence=0.95,
                )
            attempt += 1

        tried.append(f"{tool_name}:{(last_output or 'no_change')[:200]}")

    return ModelResult(
        model="executor:none",
        output="EXECUTOR_ERROR: no CLI executor succeeded or no file changes detected: " + " | ".join(tried),
        confidence=0.1,
    )
