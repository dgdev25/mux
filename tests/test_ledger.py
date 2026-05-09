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
