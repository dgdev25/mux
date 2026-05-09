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
