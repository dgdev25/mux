# Qwen 35B Local Runtime Setup

This guide documents the current Qwen 35B runtime shape used by `mux` and provides a reproducible setup path.

## Source references

- Local source capture: saved HTML article export (`35Bmodelsetup.html`)
- External setup/benchmark reference:
  - `https://github.com/abovespec/local-llm-benchmarks/blob/master/REPLICATE-ik-llama-IQ3_K_R4-16GB.md`

## Target runtime contract for mux

`mux` expects a local OpenAI-compatible endpoint with:

- Base URL: `http://127.0.0.1:18473/v1`
- Health URL: `http://127.0.0.1:18473/health`
- Model id in config: `Qwen3.6-35B-A3B-IQ3_K_R4`

These values are currently defined in `config/mux.yaml`.

## 1. Install model runtime

Use your preferred local serving stack that exposes OpenAI-style chat completions.

Requirements:

- A runnable local server binary/runtime
- Qwen 35B IQ3-compatible model artifact
- CUDA-capable GPU configuration appropriate for your model quantization

If you are following the benchmark replication flow, use the commands and model artifact details from the reference guide above.

## 2. Start the local server on port 18473

Run your server so that:

- `POST /v1/chat/completions` works
- `GET /health` returns `200`

Example health check:

```bash
curl -fsS http://127.0.0.1:18473/health
```

## 3. Configure mux

Update `config/mux.yaml`:

- `providers.local.base_url` -> `http://127.0.0.1:18473/v1`
- `providers.local.model` -> `Qwen3.6-35B-A3B-IQ3_K_R4`
- `local_runtime.health_url` -> `http://127.0.0.1:18473/health`
- `local_runtime.restart_cmd` -> your own restart command

`restart_cmd` is intentionally blank by default. Set it to a command that can stop/start your local model service.

## 4. Validate mux integration

Run:

```bash
python3 -m mux.cli doctor
python3 -m mux.cli status
python3 -m mux.cli run --task "Create a tiny file in /tmp/mux-qwen-check and confirm done"
```

Expected:

- `doctor` reports local health and backend CLI checks
- `status` shows runtime state and ledger summary
- `run` returns a route/result with a `run_id`

## 5. MCP usage with this runtime

Start MCP server:

```bash
python3 -m mux.mcp_server
```

From your MCP client, use semantic tasks via `mux(...)` or `mux_json(...)`.

## Troubleshooting

- Runtime unhealthy:
  - verify `local_runtime.health_url`
  - verify your server is actually bound to `127.0.0.1:18473`
  - verify `local_runtime.restart_cmd` works standalone
- No responses from local provider:
  - verify `providers.local.base_url`
  - verify model id spelling in config
  - check server logs for model load/VRAM issues
