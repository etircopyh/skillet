# Verification & Forensic Transcript Audit Protocol

This guide outlines the verification protocol for auditing changes made by a headless `agy` subagent, including automated diff validation and deep forensic inspection of `agy`'s tool-call execution transcripts.

---

## 1. The 5-Stage Verification Funnel

When `agy` completes its run and returns `status: "SUCCESS"`, the supervising agent must pass the workspace through a progressive verification funnel before accepting the work.

```
+-----------------------------------------------------------+
| Stage 1: Blast Radius Check (git status -s)               |
+-----------------------------------------------------------+
                             |  Pass
                             v
+-----------------------------------------------------------+
| Stage 2: Diff Syntax & Carelessness Scan (git diff)       |
+-----------------------------------------------------------+
                             |  Pass
                             v
+-----------------------------------------------------------+
| Stage 3: Type & Static Analysis Check (Compiler / Linter) |
+-----------------------------------------------------------+
                             |  Pass
                             v
+-----------------------------------------------------------+
| Stage 4: Independent Test Execution Floor (Test Runner)   |
+-----------------------------------------------------------+
                             |  Fail (Investigate Root Cause)
                             v
+-----------------------------------------------------------+
| Stage 5: Forensic Transcript Audit (transcript.jsonl)     |
+-----------------------------------------------------------+
```

---

## 2. Stage-by-Stage Verification Commands

### Stage 1: Blast Radius Check
Verify that `agy` only touched files within the authorized scope:
```bash
# View all modified, added, or deleted files
git status -s

# Discard any untracked auxiliary files or junk
git clean -nd # Dry run to inspect
# git clean -fd # If clean, discard
```

### Stage 2: Diff Quality & Carelessness Scan
Review the exact changes:
```bash
# 1. Print full diff
git diff

# 2. Check for stubbed implementations, placeholders, or relaxed types
git diff | grep -E "(\bTODO\b|\bFIXME\b|throw new Error|pass$|as any|@ts-ignore|# type: ignore)"

# 3. Check for empty catch / except blocks
git diff | grep -A 2 -E "(except\s+Exception|catch\s*\(.*\))"
```

### Stage 3: Typecheck & Static Analysis
Run the project's static analysis tools directly from the supervising agent:
```bash
# TypeScript
npx tsc --noEmit

# Python
mypy src/
ruff check src/

# Rust
cargo check

# Go
go vet ./...
```

### Stage 4: Test Suite Floor
Run the relevant test suite independently:
```bash
# Python
pytest tests/ -v

# Node / Bun
bun test # or npm test

# Rust
cargo test
```
**Rule**: If any test fails, do not attempt to guess what happened from `agy`'s narrative response. Either inspect the transcript (Stage 5) or prompt `agy` with the exact terminal output from the failed test.

---

## 3. Stage 5: Forensic Transcript Auditing

If `agy` behaved unexpectedly, claims it ran something that didn't take effect, or broke the codebase, you can inspect the exact tool execution history from disk.

### Transcript Location
Every CLI session writes its structured JSONL log to:
```
~/.gemini/antigravity-cli/brain/<CONVERSATION_ID>/.system_generated/logs/transcript.jsonl
```
And the complete untruncated transcript at:
```
~/.gemini/antigravity-cli/brain/<CONVERSATION_ID>/.system_generated/logs/transcript_full.jsonl
```

### Useful `jq` Forensic Queries

Replace `<ID>` with the `conversation_id` from `agy`'s JSON output.

#### 1. Extract All Tool Calls Made by `agy`
Inspect what tools `agy` called (e.g., `write_to_file`, `replace_file_content`, `run_command`):
```bash
LOG="$HOME/.gemini/antigravity-cli/brain/<ID>/.system_generated/logs/transcript.jsonl"

jq -c 'select(.tool_calls != null) | {step: .step_index, tools: [.tool_calls[].name]}' "$LOG"
```

#### 2. Audit All Bash Commands Run by `agy`
Check whether `agy` actually ran the test suite or if it hallucinated:
```bash
jq -r 'select(.tool_calls != null) | .tool_calls[] | select(.name == "run_command") | .args.CommandLine' "$LOG"
```

#### 3. Audit Tool Failures or Errors
Find every tool execution that returned an error status:
```bash
jq -c 'select(.status == "ERROR") | {step: .step_index, content: .content}' "$LOG"
```

#### 4. Read `agy`'s Internal Chain of Thought
View the reasoning `agy` used before taking an action:
```bash
jq -r 'select(.thinking != null) | "--- STEP \(.step_index) THINKING ---\n" + .thinking' "$LOG"
```

---

## 4. Decision Matrix: Accept, Iterate, or Revert

| Audit Result | Action | Command / Next Step |
| :--- | :--- | :--- |
| **All stages pass cleanly** | Accept & Commit | `git add <files> && git commit -m "..."` |
| **Clean diff, but minor test failure** | Multi-Turn Iteration | Pass error trace to `agy -p "..." --conversation <id>` |
| **Stubbed code or drive-by edits** | Revert & Iterate | Revert offending files (`git checkout -- <file>`), then instruct `agy` |
| **Broken architecture or destructive edits** | Hard Revert & Abort | `git restore . && git clean -fd`. Terminate delegation and implement directly. |
