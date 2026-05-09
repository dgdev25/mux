import json
import re
import subprocess
from pathlib import Path

from mux.providers.local_provider import chat_local
from mux.types import ModelResult


RAW_LOG = Path('/media/lyle/datadisk/dev/mux/logs/local_executor_raw.log')


def _log_raw(text: str) -> None:
    RAW_LOG.parent.mkdir(parents=True, exist_ok=True)
    RAW_LOG.write_text(text)


def _extract_workdir(task: str) -> str:
    candidates = re.findall(r"(/[^\s]+)", task)
    cleaned = [Path(c.rstrip('.,;:')) for c in sorted(candidates, key=len, reverse=True)]

    for p in cleaned:
        if p.exists() and p.is_dir():
            return str(p)
    for p in cleaned:
        if p.suffix and p.parent.exists() and p.parent.is_dir():
            return str(p.parent)
    for p in cleaned:
        if p.is_absolute() and not p.suffix:
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
    return str(Path.cwd())


def _extract_markdown_files(text: str) -> list[dict]:
    files: list[dict] = []

    pattern = re.compile(
        r"(?:^|\n)#{1,6}\s+([^\n`]+?)\s*\n```[a-zA-Z0-9_+-]*\n([\s\S]*?)\n```",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        files.append({"path": m.group(1).strip(), "content": m.group(2)})

    if files:
        return files

    pattern2 = re.compile(
        r"(?:^|\n)(/[^\n`]+?)\s*\n```[a-zA-Z0-9_+-]*\n([\s\S]*?)\n```",
        re.MULTILINE,
    )
    for m in pattern2.finditer(text):
        files.append({"path": m.group(1).strip(), "content": m.group(2)})

    return files


def _extract_json_blob(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\n", "", t)
        t = re.sub(r"\n```$", "", t)

    try:
        return json.loads(t)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return None

    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _validate_payload_schema(payload: dict) -> tuple[bool, str]:
    files = payload.get("files")
    if not isinstance(files, list):
        return False, "files_not_list"
    for idx, obj in enumerate(files):
        if not isinstance(obj, dict):
            return False, f"file_{idx}_not_object"
        path = obj.get("path")
        content = obj.get("content")
        if not isinstance(path, str) or not path.strip():
            return False, f"file_{idx}_invalid_path"
        if not isinstance(content, str):
            return False, f"file_{idx}_invalid_content"
        p = Path(path.strip())
        if p.is_absolute():
            return False, f"file_{idx}_absolute_path_disallowed"
        if ".." in p.parts:
            return False, f"file_{idx}_path_traversal_disallowed"

    commands = payload.get("commands", [])
    if not isinstance(commands, list) or not all(isinstance(c, str) for c in commands):
        return False, "commands_invalid"

    summary = payload.get("summary", "")
    if summary is not None and not isinstance(summary, str):
        return False, "summary_invalid"
    return True, "ok"


def _snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()
    out: set[str] = set()
    for f in root.rglob("*"):
        if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts and ".pytest_cache" not in f.parts:
            out.add(str(f.relative_to(root)))
    return out


def _apply_files(workdir: Path, files: list[dict]) -> list[str]:
    changed: list[str] = []
    for file_obj in files:
        rel = str(file_obj.get("path", "")).strip()
        content = str(file_obj.get("content", ""))
        if not rel:
            continue

        rel_path = Path(rel)
        if rel_path.is_absolute():
            try:
                rel_path = rel_path.resolve().relative_to(workdir.resolve())
            except Exception:
                continue

        target = (workdir / rel_path).resolve()
        if workdir.resolve() not in target.parents and target != workdir.resolve():
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        changed.append(str(target))
    return changed


def _parse_files_from_output(output: str) -> tuple[list[dict], list[str], str, str]:
    payload = _extract_json_blob(output)
    if payload and isinstance(payload, dict):
        valid, reason = _validate_payload_schema(payload)
        if not valid:
            return [], [], "", f"invalid_schema:{reason}"
        files = payload.get("files", []) if isinstance(payload.get("files", []), list) else []
        commands = payload.get("commands", []) if isinstance(payload.get("commands", []), list) else []
        summary = str(payload.get("summary", "implemented"))
        return files, commands, summary, "json"

    # Strict mode: do not materialize from markdown/prose responses.
    return [], [], "", "none"


def run_local_executor(task: str, cfg: dict, *, review_feedback: str | None = None) -> ModelResult:
    workdir = Path(_extract_workdir(task))
    before = _snapshot(workdir)

    ecfg = cfg.get("local_executor", {})
    max_attempts = int(ecfg.get("max_attempts", 4))
    max_tokens = int(ecfg.get("max_tokens", 6000))

    system = (
        "You are the primary implementation agent. Output JSON ONLY. No prose.\n"
        "Required schema exactly:\n"
        "{\"files\":[{\"path\":\"relative/path\",\"content\":\"file text\"}],\"commands\":[\"command\"],\"summary\":\"short\"}\n"
        "Rules:\n"
        "- Keep all paths relative to target directory.\n"
        "- Write complete file contents.\n"
        "- Do not use eval/exec for calculator evaluation.\n"
        "- If uncertain, still emit valid JSON with best effort files."
    )

    user_base = (
        f"Target directory: {workdir}\n"
        f"Task: {task}\n"
        "Required: create runnable code, tests, and README where requested; include commands to validate."
    )

    if review_feedback:
        user_base += f"\n\nApply this peer-review feedback with minimal changes:\n{review_feedback}\n"

    last_output = ""
    for attempt in range(1, max_attempts + 1):
        user = user_base
        if attempt > 1:
            user += (
                "\n\nPrevious output was not usable. Return STRICT JSON ONLY with the required schema. "
                "No markdown, no commentary."
            )

        resp = chat_local(system, user, cfg, max_tokens=max_tokens, temperature=0.05)
        if resp.output.startswith("LOCAL_PROVIDER_ERROR"):
            last_output = resp.output
            continue

        last_output = resp.output
        _log_raw(last_output)

        files, commands, summary, mode = _parse_files_from_output(last_output)
        if not files:
            continue

        _apply_files(workdir, files)

        cmd_results: list[str] = []
        for cmd in commands:
            try:
                p = subprocess.run(cmd, shell=True, cwd=str(workdir), text=True, capture_output=True, timeout=300)
                head = (p.stdout or p.stderr or "").strip().splitlines()[:3]
                cmd_results.append(f"$ {cmd} -> rc={p.returncode} :: {' | '.join(head)}")
            except Exception as e:
                cmd_results.append(f"$ {cmd} -> error={e}")

        after = _snapshot(workdir)
        changed_rel = sorted(list(after - before))
        if not changed_rel:
            continue

        out = (
            f"{summary or 'implemented'}\n"
            f"[local_executor] workdir={workdir}\n"
            f"[local_executor] parse_mode={mode}\n"
            f"[local_executor] changed_files={len(changed_rel)}\n"
            + ("\n".join(cmd_results) if cmd_results else "")
        )
        return ModelResult(model="local-executor", output=out, confidence=0.9)

    tail = (last_output or "").strip()[:1000]
    return ModelResult(model="local-executor", output=f"LOCAL_EXECUTOR_ERROR: unable_to_materialize_files after {max_attempts} attempts :: {tail}", confidence=0.1)
