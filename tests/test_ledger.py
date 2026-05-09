import json
from pathlib import Path

import mux.ledger as ledger
from mux.types import ModelResult, VerifyResult


def test_append_run_writes_jsonl(tmp_path, monkeypatch):
    ledger_file = tmp_path / "run_ledger.jsonl"
    monkeypatch.setattr(ledger, "LEDGER_PATH", ledger_file)

    out = {
        "route": "local",
        "result": ModelResult(model="local:test", output="done", confidence=0.9),
        "verify": VerifyResult(ok=True, summary="ok"),
        "reason": "",
        "retries": 0,
    }
    run_id = ledger.append_run(task="build x", out=out, runtime_status="healthy")
    assert run_id
    assert ledger_file.exists()

    lines = ledger_file.read_text().strip().splitlines()
    assert len(lines) == 1
    doc = json.loads(lines[0])
    assert doc["run_id"] == run_id
    assert doc["route"] == "local"
    assert doc["verify_ok"] is True
    assert doc["runtime_status"] == "healthy"


def test_rotation_and_summary(tmp_path, monkeypatch):
    ledger_file = tmp_path / "run_ledger.jsonl"
    monkeypatch.setattr(ledger, "LEDGER_PATH", ledger_file)

    cfg = {"ledger": {"max_bytes": 1, "max_rotated_files": 2, "summary_window": 50, "recent_failures_limit": 3}}
    out_ok = {
        "route": "local",
        "result": ModelResult(model="local:test", output="done", confidence=0.9),
        "verify": VerifyResult(ok=True, summary="ok"),
        "reason": "",
        "retries": 0,
    }
    out_fail = {
        "route": "none",
        "result": ModelResult(model="local:test", output="bad", confidence=0.2),
        "verify": VerifyResult(ok=False, summary="failed"),
        "reason": "local_down",
        "retries": 0,
    }
    ledger.append_run(task="a", out=out_ok, runtime_status="healthy", cfg=cfg)
    ledger.append_run(task="b", out=out_fail, runtime_status="unhealthy", cfg=cfg)
    ledger.append_run(task="c", out=out_ok, runtime_status="healthy", cfg=cfg)

    rotated = list(tmp_path.glob("run_ledger-*.jsonl"))
    assert len(rotated) <= 2

    summary = ledger.summarize(cfg)
    assert summary["ledger_exists"] is True
    assert summary["last_run_id"]
    assert "route_counts" in summary
