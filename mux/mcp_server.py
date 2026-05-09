from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from mux.doctor import run_doctor
from mux.local_runtime import ensure_local_runtime
from mux.config import load_config
from mux.router import run


mcp = FastMCP("mux")


def _normalize_result(out: dict[str, Any]) -> dict[str, Any]:
    return {
        "route": out.get("route"),
        "model": getattr(out.get("result"), "model", None),
        "reason": out.get("reason"),
        "run_id": out.get("run_id"),
        "retries": out.get("retries"),
        "verify_ok": getattr(out.get("verify"), "ok", None),
        "verify_summary": getattr(out.get("verify"), "summary", None),
        "output": getattr(out.get("result"), "output", None),
    }


@mcp.tool()
def mux_doctor() -> dict[str, Any]:
    """Check local runtime and CLI backend health (codex/claude/gemini)."""
    overall, checks = run_doctor()
    return {
        "overall": overall,
        "checks": [
            {"name": name, "ok": ok, "detail": detail}
            for name, ok, detail in checks
        ],
    }


@mcp.tool()
def mux(task: str) -> dict[str, Any]:
    """Run a coding task through mux local-first routing with escalation."""
    out = run(task)
    return _normalize_result(out)


@mcp.tool()
def mux_run_task(task: str) -> dict[str, Any]:
    """Compatibility alias for mux(task)."""
    return mux(task)


@mcp.tool()
def mux_json(payload_json: str) -> dict[str, Any]:
    """Run task from JSON payload: {\"task\": \"...\"}."""
    payload = json.loads(payload_json)
    task = payload.get("task", "")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("payload_json must include non-empty string field 'task'")
    return mux(task)


@mcp.tool()
def mux_health() -> dict[str, Any]:
    """Return runtime liveness state and basic doctor summary."""
    cfg = load_config()
    runtime_ok, runtime_status = ensure_local_runtime(cfg)
    overall, checks = run_doctor()
    return {
        "runtime_ok": runtime_ok,
        "runtime_status": runtime_status,
        "doctor_overall": overall,
        "checks": [
            {"name": name, "ok": ok, "detail": detail}
            for name, ok, detail in checks
        ],
    }


if __name__ == "__main__":
    mcp.run()
