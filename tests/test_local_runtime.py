from types import SimpleNamespace

import mux.local_runtime as local_runtime


def test_ensure_local_runtime_reports_recovered(monkeypatch):
    calls = {"n": 0}

    def fake_health(_: str, timeout: int = 5) -> bool:
        calls["n"] += 1
        return calls["n"] >= 2

    monkeypatch.setattr(local_runtime, "_health_ok", fake_health)
    monkeypatch.setattr(
        local_runtime.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    cfg = {"local_runtime": {"health_url": "http://x", "restart_cmd": "echo ok", "health_retries": 2, "health_retry_delay_sec": 0}}
    ok, status = local_runtime.ensure_local_runtime(cfg)
    assert ok is True
    assert status == "recovered"


def test_ensure_local_runtime_reports_restart_failure(monkeypatch):
    monkeypatch.setattr(local_runtime, "_health_ok", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        local_runtime.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="boom"),
    )
    cfg = {"local_runtime": {"health_url": "http://x", "restart_cmd": "echo no", "health_retries": 1, "health_retry_delay_sec": 0}}
    ok, status = local_runtime.ensure_local_runtime(cfg)
    assert ok is False
    assert status.startswith("restart_failed:")
