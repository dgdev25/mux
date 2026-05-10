# mux

**A pragmatic local-first coding assistant with automatic escalation.**

`mux` runs coding tasks locally when it's confident, and escalates to cloud backends (Claude, Codex, Gemini) when it needs to. It's designed to maximize local execution while maintaining reliability through transparency and intelligent fallback.

**Use mux when you want:**
- Coding tasks to run on your machine, not in the cloud
- Automatic escalation when complexity increases or confidence is low
- Visibility into which tasks went local vs. cloud, and why
- Lower latency for routine refactors, fixes, and small features

## Core Features

- **Local-first with smart escalation** — runs tasks locally unless confidence is low, complexity is high, or verification fails
- **Automatic fallback** — escalates to Claude, Codex, or Gemini CLIs with one command
- **Observability** — ledger tracking of every task, routing decisions, and failure reasons
- **Health checks** — quickly verify local model availability and backend CLIs
- **MCP integration** — use as a tool in Claude Code or any MCP-compatible client
- **File-aware** — handles file creation, modification, and testing through structured materialization

## Quick Start

After installation, you're ready to route tasks:

```bash
# Run a task (routes locally if available, escalates if needed)
python3 -m mux.cli run --task "Fix the null pointer bug in UserService and keep tests passing"

# Check health of local model and backends
python3 -m mux.cli doctor

# View routing stats and recent activity
python3 -m mux.cli status
```

Tasks with file paths or explicit intent (`create`, `build`, `scaffold`) automatically use local executor:

```bash
# Local executor will write these files to disk
python3 -m mux.cli run --task "Create a Python CLI project in /tmp/my-app with README and tests"
```

View what was routed, why, and recent failures:

```bash
cat logs/run_ledger.jsonl | tail -5 | jq .
```

## How mux makes routing decisions

**Local tasks stay local** when:
- Local model is available
- Task confidence is ≥0.6 (adjustable)
- No escalation keywords detected (see below)

**Tasks escalate to cloud** when:
- Local model is unavailable
- Confidence drops below threshold
- Complexity keywords detected: `security`, `migration`, `architecture`, `multi-file`, `refactor`, `concurrency`, etc.
- Verification repeatedly fails

**File-creation tasks** (detected by path or keywords like `create`, `build`, `scaffold`) route through local executor first, then optionally get SOTA peer review.

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

## Installation

### 1. Clone and set up Python environment

```bash
git clone https://github.com/dgdev25/mux.git
cd mux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

**Requirements:**
- Python 3.10+
- At least one cloud backend CLI installed (for escalation):
  - `claude` (Claude Code CLI)
  - `codex` (OpenAI Codex)
  - `gemini` (Google Gemini CLI)

### 2. Set up a local model (optional but recommended)

**Important:** If you don't set up a local model, `mux` will still work but will escalate all tasks to cloud backends. Local models give you the benefits of low latency and privacy.

#### Quick start: Use Ollama (recommended for beginners)

Ollama makes running local models simple. Install it, then:

```bash
# Download and run a model (this takes a few minutes the first time)
ollama run mistral:7b

# In another terminal, verify it's running:
curl -s http://127.0.0.1:11434/api/tags | grep mistral
```

Then update `config/mux.yaml`:

```yaml
local_runtime:
  health_url: "http://127.0.0.1:11434/api/health"
  restart_cmd: "systemctl restart ollama"  # or your restart method

providers:
  local:
    base_url: "http://127.0.0.1:11434/v1"
    model: "mistral:7b"
```

Test it:

```bash
python3 -m mux.cli doctor
python3 -m mux.cli status
```

#### More options

- **Ollama** (simplest): Download from [ollama.ai](https://ollama.ai) — works for Mistral, Llama, and other models
- **LM Studio** (GUI-friendly): Download from [lmstudio.ai](https://lmstudio.ai) — visually manage models, same OpenAI API
- **Qwen 35B** (high performance): More complex setup for better quality. See [docs/qwen-35b-setup.md](docs/qwen-35b-setup.md)
- **vLLM** or **Text Generation WebUI**: Advanced setups for production use

The key requirement: your local model server must expose an **OpenAI-compatible `/v1/chat/completions` endpoint**. Almost all modern local model servers support this.

## Advanced Routing (How mux works under the hood)

### Two task types

1. **Advisory tasks** (read-only, no file changes)
   - Examples: refactoring explanations, code reviews, architecture discussions
   - Route: local model → confidence check → escalate if needed

2. **Persistence tasks** (create/modify files)
   - Examples: `create a project in /tmp/app`, `build a CLI in /data/tool`
   - Route: local executor → file materialization → optional SOTA review → optional SOTA fallback

### Persistence detection

Detected by keywords (`build`, `create`, `scaffold`, `project`) or absolute paths in task prompt.

### Escalation triggers

**Local model** escalates when any of these occur:
- Confidence drops below 0.6 (configurable)
- Complexity keywords found: `security`, `architecture`, `migration`, `multi-file`, `refactor`, `concurrency`, `performance`, `ambiguous`
- Verification fails repeatedly

**Local executor** can request SOTA review after file creation, and optionally fall back to SOTA write if local materialization fails.

### Confidence scoring

Confidence is determined by:
- Response length (longer = more thought)
- Completion reason (`stop` and `length` are good, others lower confidence)
- Task complexity

Adjust `router.local_confidence_threshold` in `config/mux.yaml` to be more/less aggressive about escalation.

## CLI Commands

### `run` — Execute a task

```bash
python3 -m mux.cli run --task "Fix the JWT validation bug in auth/middleware.py"
```

Returns:
- `route`: `local` or `{backend}` (e.g., `claude`, `codex`)
- `model`: Which model handled the task
- `reason`: Why this route was chosen
- `run_id`: Unique ID for logging/tracking
- `output`: The model's response

### `doctor` — Check system health

```bash
python3 -m mux.cli doctor
```

Verifies:
- Local model available at configured health URL
- Restart command is valid (if configured)
- Cloud backend CLIs installed and accessible
- Network connectivity

Run this if tasks aren't behaving as expected.

### `status` — Quick operational summary

```bash
python3 -m mux.cli status
```

Shows:
- Local model health (UP/DOWN)
- Recent task counts by route
- Common failure reasons from last 200 tasks
- Ledger file location

Use this to spot trends (e.g., too many escalations, repeated errors).

## Using mux as an MCP tool (in Claude Code or other clients)

### Start the MCP server

```bash
. .venv/bin/activate
python3 -m mux.mcp_server
```

This starts a stdio server that listens for requests from MCP clients.

### Configure your MCP client

Add to your Claude Code `settings.json`:

```json
{
  "mcpServers": {
    "mux": {
      "command": "python3",
      "args": ["-m", "mux.mcp_server"],
      "cwd": "/path/to/mux"
    }
  }
}
```

Or copy the template from `mcp-config.example.json` and adjust paths.

### Available MCP tools

- `mux(task: str)` — Route a single task
- `mux_json(payload_json: str)` — Send a JSON payload with options
- `mux_doctor()` — Health check
- `mux_health()` — Quick health status

### How to phrase tasks for best results

Be outcome-focused; let `mux` decide routing:

✅ **Good:**
- `Harden JWT auth middleware, keep API behavior unchanged, add regression tests`
- `Refactor caching layer for readability, preserve performance, run tests`
- `Build a Python CLI in /tmp/report-cli with README, tests, and argument parsing`
- `Investigate flaky integration tests and propose minimal safe fix`

❌ **Avoid:**
- `Use Claude to refactor...` (let mux choose the backend)
- `Implement X in 100 tokens` (constraints pre-judge routing)
- `Fix this in local mode` (mux decides when to escalate)

### JSON payload (for advanced use)

```json
{
  "task": "Build a scientific calculator in /tmp/calculator with Python CLI, safe expression eval, README, and tests",
  "prefer_local": false,
  "verify_with": "claude"
}
```

## Configuration

All settings are in `config/mux.yaml`. The defaults work for most users.

### Common adjustments

**To use a different local model:**

```yaml
providers:
  local:
    base_url: "http://127.0.0.1:11434/v1"  # Your model server URL
    model: "mistral:7b"                     # Your model name
```

**To escalate more aggressively (safer, but more cloud usage):**

```yaml
router:
  local_confidence_threshold: 0.8  # Default 0.6; higher = escalate sooner
```

**To trust local model more (faster, riskier):**

```yaml
router:
  local_confidence_threshold: 0.4  # Lower = keep more tasks local
```

**To set up automatic restart of your local model service:**

```yaml
local_runtime:
  restart_cmd: "/home/user/models/restart-ollama.sh"  # Custom script or systemctl
```

**To change where logs are stored:**

```yaml
ledger:
  file_path: "/var/log/mux/run_ledger.jsonl"
```

### All configuration sections

| Section | Purpose | Default |
|---------|---------|---------|
| `router` | Escalation thresholds and keywords | 0.6 confidence, `security`, `architecture` escalate |
| `local_runtime` | Health URL and restart strategy | `http://127.0.0.1:18473/health` |
| `providers.local` | Local model endpoint details | Qwen 35B on port 18473 |
| `providers.sota_cli` | Cloud backends (Claude, Codex, Gemini) | All available, Claude first |
| `workflow` | How persistence tasks are handled | Escalate, review, no fallback |
| `ledger` | Logging and observability | ~2MB rotation, keep 5 files |

See comments in `config/mux.yaml` for every option.

## Observability and logging

Every task is logged to a JSON ledger for auditing and analytics.

**Default location:** `logs/run_ledger.jsonl`

**View recent tasks:**

```bash
# Last 5 tasks (pretty-printed)
tail -5 logs/run_ledger.jsonl | jq .

# All local tasks
grep '"route":"local"' logs/run_ledger.jsonl | jq .

# All escalations (with reasons)
grep -v '"route":"local"' logs/run_ledger.jsonl | jq '{route, reason, model}'

# Count by route in last 100 tasks
tail -100 logs/run_ledger.jsonl | jq -s 'group_by(.route) | map({route: .[0].route, count: length})'
```

**Ledger fields:**
- `run_id`: Unique identifier
- `route`: `local` or backend name (`claude`, `codex`, `gemini`)
- `reason`: Why this route was chosen
- `model`: Which model handled it
- `confidence`: Confidence score (0–1)
- `timestamp`: When it ran
- `task_length`: Characters in task
- `output_length`: Characters in response

**Automatic rotation:** Ledger rotates at ~2MB and keeps 5 historical files.

## Testing

```bash
pytest -q           # Run all tests
pytest -v           # Verbose output
pytest tests/test_policy.py  # Run one test file
```

Test coverage includes:
- Escalation routing logic (when does local stay local?)
- Local runtime health checks and recovery
- Ledger persistence and rotation
- File materialization and security
- Cloud backend fallback behavior

All tests use mocks and don't hit real APIs or models.

## Troubleshooting

### Local model isn't being used (everything escalates to cloud)

```bash
python3 -m mux.cli doctor
```

If local runtime shows DOWN:

1. **Check your model server is running:**
   ```bash
   curl -s http://127.0.0.1:18473/health  # or your configured port
   ```

2. **Verify the URL in config:**
   ```bash
   grep health_url config/mux.yaml
   ```

3. **If using Ollama, make sure it's running:**
   ```bash
   ollama serve  # or check systemctl status ollama
   ```

4. **Check logs:**
   ```bash
   tail -20 logs/run_ledger.jsonl | jq '.[] | select(.route != "local") | {reason, confidence}'
   ```

### Files aren't being created

Make sure your task includes:
- An absolute path (e.g., `/tmp/my-app`) or relative to current dir
- Keywords like `create`, `build`, `scaffold`, `project`

Example task:
```bash
python3 -m mux.cli run --task "Create a Python project in /tmp/test-app with main.py and tests"
```

Check the ledger reason if it doesn't create files:
```bash
tail -1 logs/run_ledger.jsonl | jq '{reason, route}'
```

### Backend CLI not found

```bash
which claude   # or which codex, which gemini
```

If not installed, use your package manager or visit:
- Claude: https://github.com/anthropics/claude-code
- Codex: https://github.com/openai/codex-cli
- Gemini: https://github.com/google-gemini/google-cloud-sdk

### Tasks are escalating too much

Lower the confidence threshold:

```yaml
router:
  local_confidence_threshold: 0.4  # Default 0.6
```

Or check if complexity keywords are triggering escalation:

```bash
grep '"reason":"complexity' logs/run_ledger.jsonl | tail -10
```

## Security considerations

**Local model safety:**
- Your code never leaves your machine (good for IP, bad for capability)
- Local models can be weaker than cloud models — expect more escalations
- No API keys needed for local mode

**File materialization safety:**
- Only files in the configured work directory can be created
- Path traversal (`../`) is rejected
- Absolute paths outside the intended directory are rejected
- All file operations are logged

**Cloud escalation safety:**
- Cloud backend CLIs use your configured API keys (set via env vars)
- Review what commands are actually being executed (check logs)
- `mux` doesn't modify your actual `claude`, `codex`, or `gemini` configurations

**Running in production:**
- Start with local model only, no cloud escalation
- Gradually expand escalation as you build confidence
- Monitor the ledger for what's staying local vs. escalating
- Set `router.local_confidence_threshold` conservatively (higher = safer)

## Contributing and development

**Common workflows:**

- **Adding a new config option:** Update `config/mux.yaml`, add env var support, update `types.py`, add test
- **Changing routing logic:** Update `router.py`, add test in `test_policy.py`, update README routing section
- **Adding a new backend:** Add to `providers/sota_provider.py`, configure in `mux.yaml`, test

**Before committing:**

```bash
pytest -q                    # All tests pass
python3 -m mux.cli doctor   # Doctor works
python3 -m mux.cli status   # Status works
```
