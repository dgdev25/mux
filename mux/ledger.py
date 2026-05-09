from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mux.config import project_root

LEDGER_PATH = project_root() / "logs" / "run_ledger.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, limit: int = 1200) -> str:
    text = str(value or "")
    return text[:limit]


def _ledger_cfg(cfg: dict | None) -> dict[str, Any]:
    base = (cfg or {}).get("ledger", {})
    return {
        "max_bytes": int(base.get("max_bytes", 2_000_000)),
        "max_rotated_files": int(base.get("max_rotated_files", 5)),
        "summary_window": int(base.get("summary_window", 200)),
        "recent_failures_limit": int(base.get("recent_failures_limit", 5)),
    }


def _rotate_if_needed(cfg: dict | None) -> None:
    lc = _ledger_cfg(cfg)
    max_bytes = max(1, int(lc["max_bytes"]))
    if not LEDGER_PATH.exists():
        return
    if LEDGER_PATH.stat().st_size <= max_bytes:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rotated = LEDGER_PATH.with_name(f"{LEDGER_PATH.stem}-{stamp}{LEDGER_PATH.suffix}")
    LEDGER_PATH.rename(rotated)
    _prune_rotations(cfg)


def _prune_rotations(cfg: dict | None) -> None:
    lc = _ledger_cfg(cfg)
    keep = max(0, int(lc["max_rotated_files"]))
    pattern = f"{LEDGER_PATH.stem}-*{LEDGER_PATH.suffix}"
    files = sorted(
        LEDGER_PATH.parent.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass


def _load_records(path: Path, *, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            if isinstance(doc, dict):
                out.append(doc)
    if limit > 0:
        return out[-limit:]
    return out


def summarize(cfg: dict | None = None) -> dict[str, Any]:
    lc = _ledger_cfg(cfg)
    window = max(1, int(lc["summary_window"]))
    recs = _load_records(LEDGER_PATH, limit=window)
    if not recs:
        return {
            "ledger_exists": LEDGER_PATH.exists(),
            "ledger_path": str(LEDGER_PATH),
            "entries_considered": 0,
            "last_run_id": None,
            "route_counts": {},
            "recent_failure_reasons": [],
        }

    route_counts: dict[str, int] = {}
    failures: list[str] = []
    for rec in recs:
        route = str(rec.get("route") or "unknown")
        route_counts[route] = route_counts.get(route, 0) + 1
        reason = str(rec.get("reason") or "").strip()
        verify_ok = rec.get("verify_ok")
        if reason and (verify_ok is False or route in ("none", "executor", "sota")):
            failures.append(reason[:200])

    recent_failures_limit = max(1, int(lc["recent_failures_limit"]))
    return {
        "ledger_exists": True,
        "ledger_path": str(LEDGER_PATH),
        "ledger_size_bytes": os.path.getsize(LEDGER_PATH),
        "entries_considered": len(recs),
        "last_run_id": recs[-1].get("run_id"),
        "last_runtime_status": recs[-1].get("runtime_status"),
        "last_route": recs[-1].get("route"),
        "route_counts": route_counts,
        "recent_failure_reasons": failures[-recent_failures_limit:],
    }


def append_run(*, task: str, out: dict[str, Any], runtime_status: str, cfg: dict | None = None) -> str:
    _rotate_if_needed(cfg)
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
