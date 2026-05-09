# mux

`mux` is a local-first coding router with MCP support.
It routes coding tasks between:

- a local OpenAI-compatible model endpoint
- CLI-based SOTA backends (`codex`, `claude`, `gemini`)

`mux` is designed for:

- high local implementation share
- explicit escalation when risk increases
- operational visibility (health, ledger, routing summary)

## Features

- Local-first routing with escalation policy.
- Persistence-aware workflow for tasks that imply filesystem changes.
- MCP server with callable tools (`mux`, `mux_json`, `mux_health`, `mux_doctor`).
- Runtime preflight and restart attempts for local model availability.
- Run ledger with rotation and summary extraction.
- CLI status command for quick operator checks.

## Repository layout

- `mux/cli.py` CLI entrypoint (`run`, `doctor`, `status`)
- `mux/mcp_server.py` MCP tool server
- `mux/router.py` routing logic and escalation paths
- `mux/providers/local_provider.py` local model client
- `mux/providers/local_executor.py` local implementation materialization path
- `mux/providers/sota_provider.py` CLI-based SOTA routing/execution
- `mux/local_runtime.py` local runtime health/recovery diagnostics
- `mux/doctor.py` health checks for runtime and provider CLIs
- `mux/ledger.py` JSONL ledger, rotation, and summaries
- `mux/status.py` unified operational status payload
- `config/mux.yaml` primary configuration

## Requirements

- Python `3.10+`
- Local model endpoint compatible with OpenAI chat/completions API
- At least one installed CLI backend on `PATH`:
  - `codex`
  - `claude`
  - `gemini`

## Installation

```bash
git clone https://github.com/dgdev25/mux.git
cd mux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

Run a normal task:

```bash
python3 -m mux.cli run --task "Refactor auth middleware and keep tests passing"
```

Check backend and runtime readiness:

```bash
python3 -m mux.cli doctor
```

Get compact operational summary:

```bash
python3 -m mux.cli status
```

## Routing model

`mux` has two broad modes:

- Advisory mode: non-persistence tasks can stay local or escalate to SOTA.
- Persistence workflow: tasks that imply file writes route through local executor first.

### Persistence detection

`mux` treats a task as persistence-oriented when semantic hints are present (for example `build`, `create`, `scaffold`, `project in`) or when an absolute path is detected in the prompt.

### Escalation behavior

For non-persistence tasks, escalation may happen when:

- local confidence is below threshold
- verification repeatedly fails
- complexity keyword score is high

For persistence tasks:

- local executor runs first
- optional SOTA peer review can be applied
- optional SOTA write fallback can be enabled

## CLI commands

### `run`

```bash
python3 -m mux.cli run --task "<task>"
```

Output includes:

- selected route
- model identifier
- reason
- run id
- retry count
- verification summary
- model output

### `doctor`

```bash
python3 -m mux.cli doctor
```

Checks:

- local runtime health URL
- restart command availability and contract
- backend CLI availability/probe

### `status`

```bash
python3 -m mux.cli status
```

Shows:

- runtime pass/fail and status string
- last ledger run id
- route counts from recent ledger window
- recent failure reason count and values

## MCP server

Run MCP stdio server:

```bash
. .venv/bin/activate
python3 -m mux.mcp_server
```

Example MCP config is in `mcp-config.example.json`.

### Exposed MCP tools

- `mux(task: str)`
- `mux_run_task(task: str)` compatibility alias
- `mux_json(payload_json: str)`
- `mux_doctor()`
- `mux_health()`

### Semantic wording examples

Use outcome-focused prompts and let `mux` decide route/escalation:

- `Harden JWT auth middleware in src/auth, keep API behavior unchanged, and add regression tests.`
- `Refactor caching layer for readability, preserve performance characteristics, and run tests.`
- `Investigate flaky integration tests and propose the minimal safe fix.`
- `Build a small Python CLI project in /tmp/report-cli with README and tests.`

`mux_json` example payload:

```json
{
  "task": "Build a scientific calculator project in /tmp/calculator with runnable Python CLI, safe expression evaluator (no eval/exec), README, and tests. Ensure files are written on disk and run tests before finishing."
}
```

## Configuration

Primary config file: `config/mux.yaml`

### Key sections

- `router`
  - local retry limits
  - confidence threshold
  - complexity keywords
- `local_runtime`
  - `health_url`
  - `restart_cmd`
  - retry timings
- `providers.local`
  - local endpoint base URL
  - model id
  - generation controls
- `providers.sota_cli`
  - backend order
  - per-tool binary and args
  - execution timeout/retry behavior
- `workflow`
  - local vs SOTA write behavior
  - peer review application settings
  - local implementation ratio target
- `ledger`
  - rotation threshold
  - rotated file retention
  - summary windows

### Important note about defaults

Current defaults include a machine-specific `local_runtime.restart_cmd` path in `config/mux.yaml`.
You should change that value for your environment.

## Ledger and observability

Run records are appended to a JSONL ledger.

Current ledger file path in code:

- `/media/lyle/datadisk/dev/mux/logs/run_ledger.jsonl`

Ledger supports:

- size-based rotation
- rotated-file retention cap
- recent route and failure summaries used by `status` and `mux_health`

## Testing

Run all tests:

```bash
pytest -q
```

Current suite covers:

- policy escalation logic
- local runtime diagnostics
- ledger write/rotation/summaries
- local executor schema validation
- SOTA provider fallback and execution behavior
- calculator functional tests

## Troubleshooting

### Local runtime unavailable

- Run `python3 -m mux.cli doctor`.
- Verify `local_runtime.health_url`.
- Verify `local_runtime.restart_cmd` points to a valid restart command.

### Backend CLI not detected

- Ensure `codex`, `claude`, or `gemini` is installed and available on `PATH`.
- Confirm tool binary names in `config/mux.yaml`.
- Re-run `python3 -m mux.cli doctor`.

### Tasks produce no file changes

- Ensure your task includes explicit persistence intent and target path.
- Check executor-related output and `reason` in `run` results.
- Review `mux_health` and ledger summaries for repeated failure reasons.

## Security and safety notes

- For persistence tasks, local executor enforces strict JSON materialization schema.
- Path traversal and absolute path escapes are rejected in local executor payload parsing.
- SOTA execution mode can invoke powerful CLI commands based on configured tool args.
  - Review `providers.sota_cli.tools.*.exec_args` before production use.

## Development notes

- Keep docs and tool surface aligned (CLI and MCP names).
- Prefer updating tests when changing routing, diagnostics, or provider behavior.
- If config contract changes, update both this README and `config/mux.yaml` comments/keys in the same change.
