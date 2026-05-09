# mux

Hybrid coding router: local model first, CLI SOTA handoff when risk is high.

## Quick start
```bash
cd /media/lyle/datadisk/dev/mux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m mux.cli run --task "Refactor auth middleware and keep tests passing"
```

## Providers
- Local: OpenAI-compatible endpoint (`http://127.0.0.1:18473/v1` by default).
- SOTA: CLI backends only (no API keys by default): `codex`, `claude`, `gemini`.
- `mux` auto-discovers each CLI binary from PATH and uses the configured order.

## Robust local runtime
- `mux` preflights local health before each run.
- If unhealthy, it runs `/media/lyle/datadisk/models/start.sh restart` and retries health.
- `/media/lyle/datadisk/models/start.sh` auto-fallbacks `--n-cpu-moe` and context when VRAM is tight.

## Optional watchdog (recommended)
Install user systemd units/timer:
```bash
/media/lyle/datadisk/models/systemd/install-user-services.sh
```
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
cd /media/lyle/datadisk/dev/mux
. .venv/bin/activate
python -m mux.mcp_server
```

Example MCP config is in `mcp-config.example.json`.

Exposed MCP tools:
- `mux_doctor`
- `mux`
- `mux_run_task` (compat alias)
- `mux_json`
