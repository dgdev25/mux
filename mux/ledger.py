from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEDGER_PATH = Path("/media/lyle/datadisk/dev/mux/logs/run_ledger.jsonl")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, limit: int = 1200) -> str:
    text = str(value or "")
    return text[:limit]


def append_run(*, task: str, out: dict[str, Any], runtime_status: str) -> str:
    run_id = str(uuid.uuid4())
    result = out.get("result")
    verify = out.get("verify")
    payload = {
        "run_id": run_id,
        "ts": _now_iso(),
        "task": _safe_text(task, limit=2000),
        "runtime_status": runtime_status,
        "route": out.get("route"),
        "model": getattr(result, "model", None),
        "reason": out.get("reason"),
        "retries": out.get("retries"),
        "verify_ok": getattr(verify, "ok", None),
        "verify_summary": getattr(verify, "summary", None),
        "local_impl_ratio": out.get("local_impl_ratio"),
        "output_excerpt": _safe_text(getattr(result, "output", ""), limit=2000),
    }
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return run_id
