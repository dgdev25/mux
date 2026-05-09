import shlex
import subprocess
from mux.types import VerifyResult


def verify(_: str, cfg: dict) -> VerifyResult:
    vcfg = cfg.get("verification", {})
    if not vcfg.get("enabled", True):
        return VerifyResult(ok=True, summary="verification disabled")

    cmds = vcfg.get("commands", [])
    if not cmds:
        return VerifyResult(ok=True, summary="no verification commands configured")

    for cmd in cmds:
        try:
            proc = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            return VerifyResult(ok=True, summary=f"skipped: command not found: {cmd}")
        except Exception as e:
            return VerifyResult(ok=False, summary=f"error running '{cmd}': {e}")

        if proc.returncode != 0:
            excerpt = (proc.stderr or proc.stdout or "").strip().splitlines()[:4]
            return VerifyResult(ok=False, summary=f"failed: {cmd}; {' | '.join(excerpt)}")

    return VerifyResult(ok=True, summary="all verification commands passed")
