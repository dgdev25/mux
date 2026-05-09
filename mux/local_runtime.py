import subprocess
import time
import urllib.request


def _health_ok(url: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def diagnose_local_runtime(cfg: dict) -> dict:
    rcfg = cfg.get("local_runtime", {})
    health_url = rcfg.get("health_url", "http://127.0.0.1:18473/health")
    restart_cmd = rcfg.get("restart_cmd", "")
    retries = int(rcfg.get("health_retries", 2))
    delay = int(rcfg.get("health_retry_delay_sec", 2))

    out = {
        "health_url": health_url,
        "restart_cmd": restart_cmd,
        "restart_cmd_configured": bool(restart_cmd),
        "status": "unknown",
        "ok": False,
        "restart_attempted": False,
        "restart_returncode": None,
        "restart_elapsed_ms": 0,
        "probes": [],
    }

    if _health_ok(health_url):
        out["status"] = "healthy"
        out["ok"] = True
        out["probes"].append({"step": "initial", "ok": True})
        return out

    out["probes"].append({"step": "initial", "ok": False})
    if not restart_cmd:
        out["status"] = "unhealthy_no_restart_cmd"
        return out

    out["restart_attempted"] = True
    started = time.monotonic()
    try:
        proc = subprocess.run(restart_cmd, shell=True, check=False, capture_output=True, text=True, timeout=180)
        out["restart_returncode"] = proc.returncode
        out["restart_elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:200]
            out["status"] = f"restart_failed:rc={proc.returncode}:{err}"
            return out
    except Exception as e:
        out["restart_elapsed_ms"] = int((time.monotonic() - started) * 1000)
        out["status"] = f"restart_failed:{e}"
        return out

    if not _health_ok(health_url):
        time.sleep(max(1, min(delay, 3)))

    status = "unhealthy_after_restart"
    for idx in range(retries):
        ok = _health_ok(health_url)
        out["probes"].append({"step": f"retry_{idx + 1}", "ok": ok})
        if ok:
            out["status"] = "recovered"
            out["ok"] = True
            return out
        if idx == 0:
            status = "booting_after_restart"
        else:
            status = "still_unhealthy_after_restart"
        time.sleep(delay)

    out["status"] = status
    return out


def ensure_local_runtime(cfg: dict) -> tuple[bool, str]:
    diag = diagnose_local_runtime(cfg)
    return bool(diag["ok"]), str(diag["status"])
