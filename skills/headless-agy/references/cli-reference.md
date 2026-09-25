# Headless `agy` CLI Reference

This document details the command-line flags, process orchestration recipes, and model parameters for executing `agy` as a headless subagent.

---

## 1. CLI Execution Flags

The Antigravity CLI (`agy`) supports a dedicated print mode optimized for automation, pipes, and agent sub-processes.

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `-p`, `--print` | String | None | Runs a single prompt non-interactively, printing output and terminating upon turn completion. |
| `--prompt` | String | None | Alias for `--print`. |
| `--output-format` | String | `text` | Formats output. Options: `text`, `json`, `stream-json`. Always use `json` for automated agent consumption. |
| `--input-format` | String | `text` | Input format for print mode (`text`, `stream-json`). `stream-json` reads NDJSON messages from stdin. |
| `--dangerously-skip-permissions` | Boolean | `false` | **Critical for headless execution**. Automatically grants permission to all tool executions (file creation, editing, bash execution) without prompting for user confirmation on stdin. |
| `--print-timeout` | Duration | `0s` (unlimited) | Enforces a maximum wall-clock timeout on the turn (e.g., `180s`, `5m`). Strongly recommended to prevent runaway tool loops. |
| `--conversation` | String | None | Resumes a previous conversation by its UUID. Used for multi-turn corrective feedback. |
| `-c`, `--continue` | Boolean | `false` | Resumes the most recent conversation in the current directory. |
| `--mode` | String | `accept-edits` | Execution mode. Options: `accept-edits` (allows tool edits and bash commands), `plan` (generates an implementation plan without executing filesystem edits). |
| `--model` | String | Configured default | Overrides the LLM model for the session. |
| `--effort` | String | Configured default | Sets reasoning effort: `low`, `medium`, `high`. |
| `--agent` | String | None | Loads a named custom agent configuration (e.g., `codebase-memory`, `codebase-memory-auditor`). |
| `--sandbox` | Boolean | `false` | Restricts shell execution inside a sandbox environment for untrusted tasks. |
| `--add-dir` | String | `[]` | Adds additional directories to the active agent workspace (repeatable). |
| `--disable-slash-commands` | Boolean | `false` | Disables slash command and skill expansion in print mode. |
| `--json-schema` | String / Path | None | Enforces strict JSON schema validation on the agent's final text output. |

---

## 2. Model Selection Matrix for Subagents

Depending on the task complexity, cost, and latency tolerances, choose the appropriate `--model`:

| Model Name (`--model`) | Characteristics | Best Suited For |
| :--- | :--- | :--- |
| `gemini-3.8-flash-high` | High speed, large reasoning capacity, high throughput | Default choice for subagent refactoring, mechanical edits, and tests. |
| `gemini-3.8-flash-low` | Ultra fast, minimal thinking tokens, lower cost | Rapid exploratory searches, keyword lookups, quick diff summaries. |
| `gemini-3.1-pro-high` | Deep analytical capability, complex logical synthesis | Intricate algorithm implementation, difficult debugging, edge-case analysis. |
| `claude-sonnet-4-6` | High code synthesis precision, strict instruction adherence | Nuanced architectural refactoring, strict type system alignment. |

Example specifying model and effort:
```bash
agy -p "Refactor date parsing in src/utils.ts to handle ISO-8601 with fractional seconds" \
  --model gemini-3.8-flash-high \
  --effort high \
  --output-format json \
  --dangerously-skip-permissions \
  --print-timeout 240s
```

---

## 3. Parsing JSON Output

When running with `--output-format json`, `agy` returns a structured JSON payload on stdout:

```json
{
  "conversation_id": "8f3b7d14-3677-4c07-b6f7-b2f5d92e5c8e",
  "status": "SUCCESS",
  "response": "Created src/health.py with a FastAPI router exposing /healthz and /readyz.\nVerified with pytest tests/test_health.py.",
  "duration_seconds": 24.129381,
  "num_turns": 1,
  "usage": {
    "input_tokens": 24150,
    "output_tokens": 320,
    "thinking_tokens": 256,
    "cache_read_tokens": 18200,
    "total_tokens": 24470
  }
}
```

### Extraction via `jq`

```bash
# Capture output into variable or file
RESULT=$(agy -p "..." --output-format json --dangerously-skip-permissions)

# Extract conversation ID for subsequent turns
CONV_ID=$(echo "$RESULT" | jq -r '.conversation_id')

# Extract completion status
STATUS=$(echo "$RESULT" | jq -r '.status')

# Extract agent's narrative response
RESPONSE=$(echo "$RESULT" | jq -r '.response')
```

---

## 4. Multi-Turn Subagent Iteration

If the supervising agent detects issues during diff inspection or test runs, do **not** restart a new session from scratch. Use `--conversation <id>` to preserve context and issue targeted corrective prompts:

```bash
# First Turn: Initial Delegation
OUT_1=$(agy -p "Implement string sanitizer in src/sanitize.ts" \
  --output-format json \
  --dangerously-skip-permissions)
CONV_ID=$(echo "$OUT_1" | jq -r '.conversation_id')

# Supervising agent runs tests and observes a failure:
# Error: sanitizeString does not escape angle brackets in HTML entities

# Second Turn: Targeted Feedback
OUT_2=$(agy -p "The sanitizeString function fails to escape nested angle brackets. Update src/sanitize.ts and rerun tests." \
  --conversation "$CONV_ID" \
  --output-format json \
  --dangerously-skip-permissions)
```

---

## 5. Read-Only Exploration Mode (`--mode plan`)

When you want `agy` to survey the codebase, locate symbols, or prepare a proposed architectural plan **without making any filesystem edits or mutating code**, use `--mode plan`:

```bash
agy -p "Analyze src/auth/ and explain how refresh tokens are revoked across cluster nodes" \
  --mode plan \
  --output-format json \
  --print-timeout 180s
```

In `plan` mode, file edit tools are restricted, guaranteeing zero unintentional mutations to your working tree.

---

## 6. Structured Schema Output

When the calling agent requires a strictly structured data response (e.g., returning a list of affected files or parsed AST nodes):

```bash
SCHEMA='{
  "type": "object",
  "properties": {
    "files_analyzed": {"type": "array", "items": {"type": "string"}},
    "vulnerabilities_found": {"type": "integer"},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file": {"type": "string"},
          "line": {"type": "integer"},
          "description": {"type": "string"}
        },
        "required": ["file", "line", "description"]
      }
    }
  },
  "required": ["files_analyzed", "vulnerabilities_found", "findings"]
}'

agy -p "Audit src/crypto/ for insecure random number generation" \
  --json-schema "$SCHEMA" \
  --output-format json \
  --dangerously-skip-permissions
```
