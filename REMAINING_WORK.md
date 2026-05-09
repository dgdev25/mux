# Remaining Work for `mux`

This document captures the work that is still open after the current robustness pass.

## Completed

- Added a persistent JSONL run ledger.
- Hardened local executor parsing so only strict JSON payloads are materialized into files.
- Exposed clearer runtime health states in the local runtime and MCP surface.
- Verified the `mux` CLI and MCP health path with live runs.
- Added focused tests for the new behavior.
- Fixed repository-wide `pytest` import-path collection issues for both `mux` and `calculator`.

## Still To Do

### 1. Keep import-path behavior stable

The top-level collection issue is resolved via root test configuration. The full repository test run now passes from the repo root.

Current status:

- `pytest -q` passes (`21 passed`).
- Imports for both `mux` and nested `calculator` tests resolve without manual `PYTHONPATH`.

What remains:

- Keep this behavior covered as tests evolve and package layout changes.

### 2. Expand provider-path coverage

Status: Completed.

Implemented:

- Added mocked integration tests for `mux/providers/sota_provider.py`.
- Covered backend fallback behavior and codex JSON parsing.
- Verified advisory and execution flows under no-change and empty-output cases.

### 3. Add ledger retention or rotation

Status: Completed.

Implemented:

- Added size-based ledger rotation.
- Added capped rotated-file retention.
- Added operational summary extraction for recent runs and failure reasons.

### 4. Improve runtime recovery diagnostics

Status: Completed.

Implemented:

- Added structured runtime diagnostics with probe history and restart timing.
- Added restart return-code and elapsed-time reporting.
- Added doctor contract check for restart command structure.

### 5. Enrich operational visibility

Status: Completed.

Implemented:

- `mux_health` now returns runtime diagnostics plus ledger summary.
- Added last run id, route counts, and recent failure reasons in status payload.
- Added `mux status` compact CLI view for operators.

## Suggested Next Order

1. Keep tests green as routing rules evolve.
2. Revisit thresholds in `config/mux.yaml` using real production telemetry.
