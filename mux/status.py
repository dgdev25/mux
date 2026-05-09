from __future__ import annotations

from typing import Any

from mux.config import load_config
from mux.doctor import run_doctor
from mux.ledger import summarize
from mux.local_runtime import diagnose_local_runtime


def build_status(cfg: dict | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    runtime = diagnose_local_runtime(cfg)
    overall, checks = run_doctor()
    ledger = summarize(cfg)
    return {
        "runtime_ok": runtime.get("ok", False),
        "runtime_status": runtime.get("status", "unknown"),
        "runtime_diagnostics": runtime,
        "doctor_overall": overall,
        "checks": [
            {"name": name, "ok": ok, "detail": detail}
            for name, ok, detail in checks
        ],
        "ledger": ledger,
    }
