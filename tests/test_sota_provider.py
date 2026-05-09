from __future__ import annotations

from pathlib import Path

from mux.providers.sota_provider import run_executor, run_sota


def _cfg() -> dict:
    return {
        "providers": {
            "sota_cli": {
                "preferred_order": ["codex", "claude", "gemini"],
                "executor_timeout_sec": 10,
                "retry_if_no_change": 1,
                "tools": {
                    "codex": {"binary": "codex", "advisory_args": ["--json"], "exec_args": ["-C", "{workdir}"], "prompt_via": "arg"},
                    "claude": {"binary": "claude", "advisory_args": ["-p"], "exec_args": ["-p"], "prompt_via": "arg"},
                    "gemini": {"binary": "gemini", "advisory_args": ["-p"], "exec_args": ["-p"], "prompt_via": "arg"},
                },
            }
        }
    }


def test_run_sota_falls_back_when_first_missing(monkeypatch):
    from mux.providers import sota_provider as sp

    monkeypatch.setattr(sp, "_find_binary", lambda name, configured_binary=None: None if name == "codex" else f"/bin/{name}")
    monkeypatch.setattr(sp, "_run_cli", lambda *_args, **_kwargs: (True, "claude answer"))
    out = run_sota(task="x", context="y", cfg=_cfg())
    assert out.model == "sota-cli:claude"
    assert out.output == "claude answer"


def test_run_sota_parses_codex_json(monkeypatch):
    from mux.providers import sota_provider as sp

    monkeypatch.setattr(sp, "_find_binary", lambda *_args, **_kwargs: "/bin/codex")
    raw = '{"output_text":"first"}\n{"item":{"type":"agent_message","text":"second"}}'
    monkeypatch.setattr(sp, "_run_cli", lambda *_args, **_kwargs: (True, raw))
    out = run_sota(task="x", context="y", cfg=_cfg())
    assert out.model == "sota-cli:codex"
    assert "first" in out.output and "second" in out.output


def test_run_sota_skips_empty_then_uses_next(monkeypatch):
    from mux.providers import sota_provider as sp

    def fake_find(name: str, configured_binary=None):
        return f"/bin/{name}"

    calls = {"n": 0}

    def fake_run(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return True, "   "
        return True, "ok from next"

    monkeypatch.setattr(sp, "_find_binary", fake_find)
    monkeypatch.setattr(sp, "_run_cli", fake_run)
    out = run_sota(task="x", context="y", cfg=_cfg())
    assert out.model == "sota-cli:claude"
    assert out.output == "ok from next"


def test_run_executor_retries_then_succeeds(monkeypatch, tmp_path):
    from mux.providers import sota_provider as sp

    workdir = tmp_path / "proj"
    workdir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(sp, "_extract_workdir", lambda _task: str(workdir))
    monkeypatch.setattr(sp, "_required_markers_from_task", lambda _task: [])
    monkeypatch.setattr(sp, "_find_binary", lambda *_args, **_kwargs: "/bin/codex")

    calls = {"n": 0}
    before_set = set()

    def fake_snapshot(_root: str):
        if calls["n"] == 0:
            return before_set
        return {"new.txt"}

    def fake_run(*_args, **_kwargs):
        calls["n"] += 1
        return True, "executor output"

    monkeypatch.setattr(sp, "_tree_snapshot", fake_snapshot)
    monkeypatch.setattr(sp, "_run_cli", fake_run)
    out = run_executor(task=f"build in {workdir}", cfg=_cfg())
    assert out.model == "executor:codex"
    assert "[mux] changed_files_count=1" in out.output


def test_run_executor_errors_when_no_change(monkeypatch, tmp_path):
    from mux.providers import sota_provider as sp

    workdir = tmp_path / "proj"
    workdir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(sp, "_extract_workdir", lambda _task: str(workdir))
    monkeypatch.setattr(sp, "_required_markers_from_task", lambda _task: [])
    monkeypatch.setattr(sp, "_find_binary", lambda *_args, **_kwargs: "/bin/codex")
    monkeypatch.setattr(sp, "_tree_snapshot", lambda _root: set())
    monkeypatch.setattr(sp, "_run_cli", lambda *_args, **_kwargs: (True, "no-op"))

    out = run_executor(task=f"build in {workdir}", cfg=_cfg())
    assert out.model == "executor:none"
    assert out.output.startswith("EXECUTOR_ERROR:")
