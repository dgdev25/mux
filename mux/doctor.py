import shlex
import shutil
import subprocess
import urllib.request
from mux.config import load_config


def _check_local_health(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            body = r.read(200).decode("utf-8", "ignore")
            return r.status == 200, f"http {r.status} body={body!r}"
    except Exception as e:
        return False, str(e)


def _check_restart_cmd(cmd: str) -> tuple[bool, str]:
    try:
        # validate command can be parsed and executable exists when absolute path is first token
        parts = shlex.split(cmd)
        if not parts:
            return False, "empty command"
        exe = parts[0]
        if "/" in exe:
            ok = shutil.which(exe) is not None or subprocess.run(["test", "-x", exe]).returncode == 0
            return (ok, f"executable={exe}")
        found = shutil.which(exe)
        return (found is not None, f"resolved={found}")
    except Exception as e:
        return False, str(e)


def _check_restart_contract(cmd: str) -> tuple[bool, str]:
    parts = shlex.split(cmd)
    if not parts:
        return False, "empty command"
    if "restart" not in parts:
        return False, "missing_restart_token"
    return True, "contains_restart_token"


def _check_cli(name: str, binary: str, args: list[str]) -> tuple[bool, str]:
    path = shutil.which(binary)
    if not path:
        return False, f"binary_not_found:{binary}"

    # light smoke-check: run with --help when possible, fallback to version
    probes = [
        [path, "--help"],
        [path, "-h"],
        [path, "--version"],
    ]
    for cmd in probes:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                line = (p.stdout or p.stderr or "").strip().splitlines()[:1]
                preview = line[0] if line else "ok"
                return True, f"path={path} probe={' '.join(cmd[1:])} out={preview[:120]}"
        except Exception:
            pass

    # final fallback: try configured args with a tiny prompt
    try:
        p = subprocess.run([path, *args], input="health check", text=True, capture_output=True, timeout=20)
        if p.returncode == 0:
            out = (p.stdout or "").strip().splitlines()[:1]
            preview = out[0] if out else "ok"
            return True, f"path={path} run={' '.join(args)} out={preview[:120]}"
        return False, f"path={path} run_failed rc={p.returncode} err={(p.stderr or p.stdout)[:120]}"
    except Exception as e:
        return False, f"path={path} exec_error={e}"


def run_doctor() -> tuple[bool, list[tuple[str, bool, str]]]:
    cfg = load_config()
    checks: list[tuple[str, bool, str]] = []

    local_cfg = cfg.get("local_runtime", {})
    health_url = local_cfg.get("health_url", "http://127.0.0.1:18473/health")
    restart_cmd = local_cfg.get("restart_cmd", "")

    ok, msg = _check_local_health(health_url)
    checks.append(("local_health", ok, msg))

    if restart_cmd:
        ok, msg = _check_restart_cmd(restart_cmd)
        checks.append(("restart_cmd", ok, msg))
        ok, msg = _check_restart_contract(restart_cmd)
        checks.append(("restart_contract", ok, msg))

    scli = cfg.get("providers", {}).get("sota_cli", {})
    tools = scli.get("tools", {})
    order = scli.get("preferred_order", ["codex", "claude", "gemini"])

    for tool in order:
        tcfg = tools.get(tool, {})
        binary = tcfg.get("binary", tool)
        args = tcfg.get("args", ["-p"])
        ok, msg = _check_cli(tool, binary, args)
        checks.append((f"cli_{tool}", ok, msg))

    overall = all(ok for _, ok, _ in checks)
    return overall, checks
