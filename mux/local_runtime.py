import subprocess
import time
import urllib.request


def _health_ok(url: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_local_runtime(cfg: dict) -> tuple[bool, str]:
    rcfg = cfg.get("local_runtime", {})
    health_url = rcfg.get("health_url", "http://127.0.0.1:18473/health")
    restart_cmd = rcfg.get("restart_cmd", "")
    retries = int(rcfg.get("health_retries", 2))
    delay = int(rcfg.get("health_retry_delay_sec", 2))

    if _health_ok(health_url):
        return True, "healthy"

    if restart_cmd:
        try:
            proc = subprocess.run(restart_cmd, shell=True, check=False, capture_output=True, text=True, timeout=180)
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()[:200]
                return False, f"restart_failed:rc={proc.returncode}:{err}"
        except Exception as e:
            return False, f"restart_failed:{e}"
    else:
        return False, "unhealthy_no_restart_cmd"

    # First probe quickly after restart to distinguish booting from hard-failed.
    if not _health_ok(health_url):
        time.sleep(max(1, min(delay, 3)))

    status = "unhealthy_after_restart"
    for idx in range(retries):
        if _health_ok(health_url):
            return True, "recovered"
        if idx == 0:
            # Give callers clearer state than generic "unhealthy".
            status = "booting_after_restart"
        else:
            status = "still_unhealthy_after_restart"
        time.sleep(delay)

    return False, status
