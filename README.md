# mux

Hybrid coding router: local model first, CLI SOTA handoff when risk is high.

## Quick start
```bash
git clone https://github.com/dgdev25/mux.git
cd mux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 -m mux.cli run --task "Refactor auth middleware and keep tests passing"
```

## Providers
- Local: OpenAI-compatible endpoint (`http://127.0.0.1:18473/v1` by default).
- SOTA: CLI backends only (no API keys by default): `codex`, `claude`, `gemini`.
- `mux` auto-discovers each CLI binary from PATH and uses the configured order.

## Robust local runtime
- `mux` preflights local health before each run.
- If unhealthy, it runs the configured restart command (`local_runtime.restart_cmd` in `config/mux.yaml`) and retries health.
- Keep `local_runtime.health_url` and `local_runtime.restart_cmd` aligned with your local model service.

## Optional watchdog (recommended)
Install user systemd units/timer using your local service scripts (outside this repo), then point `local_runtime.restart_cmd` to that managed service restart path.

This enables:
- `mux-llm.service` for lifecycle management
- `mux-llm-healthcheck.timer` for periodic health check + auto-restart

## Main files
- `mux/cli.py`
- `mux/router.py`
- `mux/local_runtime.py`
- `mux/policies/escalation.py`
- `mux/providers/local_provider.py`
- `mux/providers/sota_provider.py`
- `mux/verifier.py`
- `config/mux.yaml`


## MCP server
Run as MCP stdio server:
```bash
cd mux
. .venv/bin/activate
python3 -m mux.mcp_server
```

Example MCP config is in `mcp-config.example.json`.

Exposed MCP tools:
- `mux_doctor`
- `mux`
- `mux_run_task` (compat alias)
- `mux_json`

## MCP semantic examples
Use natural task wording in your MCP client and let `mux` decide local vs escalation.

Example prompts for `mux(task=...)`:

- `Harden JWT auth middleware in src/auth, keep API behavior unchanged, and add regression tests.`
- `Build a small Python CLI project in /tmp/report-cli with README and pytest coverage.`
- `Refactor caching layer for readability, preserve performance characteristics, and run tests.`
- `Investigate flaky test failures in tests/integration and propose the minimal safe fix.`

JSON payload example for `mux_json(payload_json=...)`:

```json
{
  "task": "Build a scientific calculator project in /tmp/calculator with runnable Python CLI, safe expression evaluator (no eval/exec), README, and tests. Ensure files are written on disk and run tests before finishing."
}
```

Operational checks:

- Use `mux_doctor` to confirm runtime + CLI backend readiness.
- Use `mux_health` to inspect runtime diagnostics, last run id, route counts, and recent failure reasons.
