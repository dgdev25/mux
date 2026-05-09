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
            subprocess.run(restart_cmd, shell=True, check=False, capture_output=True, text=True, timeout=180)
        except Exception as e:
            return False, f"restart_failed:{e}"

    for _ in range(retries):
        if _health_ok(health_url):
            return True, "recovered"
        time.sleep(delay)

    return False, "unhealthy_after_restart"
