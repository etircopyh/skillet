---
name: afk-deadcode-removal
description: "Autonomous dead-code removal from any TypeScript project WITHOUT a human in the loop. Scan with tsc --noEmit --noUnusedLocals --noUnusedParameters plus parallel explorer subagents, LSP-verify zero references before ANY removal, batch by file for conflict-free parallelism, dispatch parallel deep-worker subagents to apply the removals with atomic commit per batch, REVERT-ON-RED not fix. Use when the user says 'remove dead code', 'afk deadcode', 'auto remove dead symbols', or wants LSP-guaranteed zero-false-positive removal with atomic commits (NOT knip-driven Bun/TS monorepo cleanup - that is debloat-monorepo; NOT read-only debt cataloging - that is afk-debt-audit). Triggers: 'afk deadcode', 'remove dead code', 'auto deadcode', 'afk-deadcode-removal'."
---

# AFK Deadcode Removal

The autonomous dead-code removal pipeline for any TypeScript project. You (the orchestrator) scan with `tsc --noEmit --noUnusedLocals --noUnusedParameters` plus parallel explorer subagents, LSP-verify zero references before ANY removal decision, batch by file for conflict-free parallelism, then **delegate ALL removals to parallel deep-worker subagents** with atomic commits per batch and REVERT-ON-RED discipline. The user does NOT sit in the loop - they asked for "afk" and you run the whole pipeline autonomously.

Distinct from siblings:
- `debloat-monorepo` - mutating cleanup for Bun/TS monorepos specifically; uses `knip` (workspace-aware, files AND deps), main agent edits in-place, deep dep/marker/AGENTS.md scrub. Use when the repo is Bun/TS with knip installed and you want full debloat (deps, merge markers, AGENTS-image scrub, not just dead symbols).
- `afk-debt-audit` - read-only catalog across 9 dimensions; writes `TECH_DEBT_AUDIT.md`, mutates nothing. Use when the user wants the prioritized debt report, not removal.
- This skill (`afk-deadcode-removal`) - LSP-guaranteed dead-symbol removal from any TS repo; orchestrator scans + verifies + batches, parallel deep-workers apply the edits, atomic commit per batch. Use when the user wants the removal done with zero false positives and atomic commits.

## When to use

User wants dead-code REMOVED with LSP-guaranteed safety and NO human interview. Triggers: "afk deadcode", "remove dead code", "auto deadcode", "afk-deadcode-removal".

Do NOT use when the user wants a read-only audit - that is `afk-debt-audit`. Do NOT use when the repo is Bun/TS with knip installed and you want full dep+marker+AGENTS cleanup - that is `debloat-monorepo` (more thorough for that stack). Do NOT run on non-TypeScript repos without an equivalent strict-mode scanner.

## The non-negotiable discipline

**LSP is law.** Verify with `lsp references` (or the harness's equivalent `includeDeclaration=false` references tool) before ANY removal decision. Zero references = confirmed dead; one or more = NOT dead, drop from list. No exceptions, no "I'm pretty sure this is unused" exports.

**Never remove entry points.** `src/index.ts`, barrel `index.ts` re-exports, test files, config files, `packages/` - off-limits. The strict mode scanner may flag entry exports; the false-positive guards drop them.

**You do NOT remove code yourself.** You scan, verify, batch, then fire deep-worker subagents. They do the edits. The orchestrator editing directly is the canonical overreach - the whole point is parallel isolated batches with atomic commits.

**Atomic commit per batch, never `git add -A`.** Each batch subagent stages ONLY its batch's files and commits atomically. Other batches are working in parallel; `-A` would silently include their files. This is the contract.

**REVERT-ON-RED, do not fix.** If a batch's typecheck fails after its edits, the subagent runs `git checkout -- <files>` and reports failure. It does NOT attempt to fix the typecheck error - that is the orchestrator's downstream decision, not the worker's.

**Abort conditions held.** If >50 candidates are found, STOP and ask the user (or in afk mode: narrow scope and document). If the build breaks unfixable by revert, STOP.

## Phase 0 - Baseline BEFORE any scan

Establish the regression floor. Run in parallel:

- Project typecheck command (typically `bun run typecheck` / `npx tsc --noEmit` / `npm run typecheck`) - exit 0 baseline.
- Project test command - record "X pass / Y fail / Z errors" as the regression floor.
- Project build command (if separate from typecheck) - exit 0 baseline.
- `bash("git status --porcelain")` - clean tree baseline.

Record these. The post-removal runs must equal the baseline (allow for ±1 flake on slow CI). Do NOT skip - without a baseline, "tests still pass" at the end is unverifiable.

## Phase 1 - Scan: find dead-code candidates

Run these in PARALLEL:

**TypeScript strict mode (run FIRST as the primary scanner):**

```bash
npx tsc --noEmit --noUnusedLocals --noUnusedParameters 2>&1
```

(or `bunx tsc ...` if the project uses bun). This gives the definitive list of unused locals, imports, parameters, and types with exact `file:line` locations.

**Explorer subagents (fire simultaneously as background):**

Spawn two `task` subagents (default worker; `async: true`) with these tasks:

```
task 1: Find orphaned files in src/ NOT imported by any other file. Check all import statements.
        EXCLUDE: index.ts, *.test.ts, entry points, .md, packages/.
        Return: file paths (verbatim).

task 2: Find exported functions/types/constants in src/ that are never imported by other files.
        Cross-reference: for each export, grep the symbol name across src/ - if it only appears
        in its own file, it's a candidate.
        EXCLUDE: src/index.ts exports, test files.
        Return: file path, line, symbol name, export type.
```

Collect all results into a master candidate list. Wait for both subagents. Do NOT re-search yourself while waiting - the subagents are the source of truth for their scope.

## Phase 2 - Verify: LSP confirmation (zero false positives)

For EACH candidate from Phase 1, run `lsp references` with `includeDeclaration=false` (the harness's name may differ; the key is to exclude the symbol's own declaration):

- 0 references → CONFIRMED dead.
- 1+ references → NOT dead, drop from list.

Also apply the false-positive guards (NEVER mark as dead, even if LSP reports 0 refs):

- Symbols in `src/index.ts` or barrel `index.ts` re-exports.
- Symbols referenced in test files (tests are valid consumers).
- Symbols with `@public` / `@api` JSDoc tags.
- Hook factories (`createXXXHook`), tool factories (`createXXXTool`), agent/plugin definitions.
- Command templates, skill definitions, MCP configs.
- Symbols in `package.json` `exports` map.

Produce a confirmed list:

```
| # | File | Symbol | Type | Action |
|---|------|--------|------|--------|
| 1 | src/foo.ts:42 | unusedFunc | function | REMOVE |
| 2 | src/bar.ts:10 | OldType | type | REMOVE |
| 3 | src/baz.ts:7 | ctx | parameter | PREFIX _ |
```

**Action types:**
- `REMOVE` - delete the symbol/import/file entirely.
- `PREFIX _` - unused function parameter required by signature → rename to `_paramName`. Do NOT remove (the signature requires it).

If ZERO confirmed: report "No dead code found" and STOP. Do NOT manufacture work.

## Phase 3 - Batch: group by file for conflict-free parallelism

Goal: maximize parallel subagents with ZERO git conflicts.

1. Group confirmed dead-code items by FILE PATH.
2. All items in the SAME file go to the SAME batch (prevents two subagents editing the same file).
3. If a dead FILE (entire file deletion) exists, it is its own batch.
4. Target 5-15 batches. If fewer than 5 items total, use 1 batch per item.

Example:
```
Batch A: [src/hooks/foo/hook.ts - 3 unused imports]
Batch B: [src/features/bar/manager.ts - 2 unused constants, 1 dead function]
Batch C: [src/tools/baz/tool.ts - 1 unused param, src/tools/baz/types.ts - 1 unused type]
Batch D: [src/dead-file.ts - entire file deletion]
```

Files in the same directory CAN be batched together (they do not conflict as long as no two subagents edit the same file). Maximize batch count for parallelism.

## Phase 4 - Execute: dispatch parallel deep-worker subagents

For EACH batch, fire a `task` subagent (default worker; use `async: true` for parallelism). All batches fire in the SAME response - one message, multiple `task` calls.

Each subagent's task prompt template (fill in the specifics per batch):

```
## TASK: Remove dead code from [file list]

## DEAD CODE TO REMOVE

### [file path] line [N]
- Symbol: [name] - [type: unused import / unused constant / unused function / unused parameter / dead file]
- Action: [REMOVE entirely / REMOVE from import list / PREFIX with _]

### [file path] line [N]
- ...

## PROTOCOL

1. Read each file to understand exact syntax at the target lines.
2. For each symbol, run `lsp references` (with declaration excluded) to RE-VERIFY it is still dead.
   Another batch may have changed call sites - re-verification is mandatory.
3. Apply the change:
   - Unused import (only symbol in line): remove entire import line.
   - Unused import (one of many): remove only that symbol from the import list.
   - Unused constant/function/type: remove the declaration. Clean up trailing blank lines.
   - Unused parameter: prefix with `_` (do NOT remove - required by signature).
   - Dead file: delete with `rm`.
4. After ALL edits in this batch, run: [project typecheck command]
5. If typecheck fails: `git checkout -- [your batch's files]` and report failure.
   Do NOT attempt to fix the typecheck error - revert only.
6. If typecheck passes: stage ONLY your batch's files and commit:
   `git add [your-specific-files] && git commit -m "refactor: remove dead code from [brief file list]"`
7. Report what you removed and the commit hash.

## CRITICAL

- Stage ONLY your batch's files (`git add [specific files]`). NEVER `git add -A` - other subagents are working in parallel.
- If typecheck fails after your edits, REVERT all changes and report. Do not attempt to fix.
- Pre-existing test failures in other files are expected. Only your batch's typecheck matters.
```

Fire ALL batches simultaneously. Wait for all to complete via the `task` job system.

## Phase 5 - Final verification

After ALL subagents complete:

```bash
[project typecheck command]   # must pass
[project test command]         # note any NEW failures vs pre-existing
[project build command]        # must pass, if separate from typecheck
```

Produce summary to the user:

```markdown
## Dead Code Removal Complete

### Removed
| # | Symbol | File | Type | Commit | Batch |
|---|--------|------|------|--------|-------|
| 1 | unusedFunc | src/foo.ts | function | abc1234 | Batch A |

### Skipped (batch reported failure)
| # | Symbol | File | Reason |
|---|--------|------|--------|

### Verification
- Typecheck: PASS/FAIL (baseline was PASS)
- Tests: X passing, Y failing (Z pre-existing; baseline was X0 pass / Y0 fail / Z0 errors)
- Build: PASS/FAIL
- Total removed: N symbols across M files
- Total commits: K atomic commits
- Parallel subagents used: P
```

## Phase 6 - Handoff

The removal is the deliverable. If the user asked to follow through, name the downstream skill:

- Audit the rest of the repo for non-dead-code debt → `afk-debt-audit`.
- Plan a deeper refactor around the vacated areas → `request-refactor-plan`.
- Add tests for the surviving code → `tdd`.

Do NOT chain inline. This skill removes dead code; it does not refactor, test, or audit other dimensions.

## Scope control

If the user provided an argument narrowing scope, respect it:
- File path → only that file.
- Directory → only that directory.
- Symbol name → only that symbol.
- `all` or empty → full project scan (default).

## Anti-patterns (do NOT)

- **Trusting the strict-mode scanner without LSP re-verification** - tsc finds candidates; LSP confirms. They disagree on barrel re-exports, JSDoc-tagged symbols, and test consumers. LSP wins.
- **Removing an entry point or a barrel re-export** - these are the load-bearing false positives. If you remove one, you break the package's public API silently.
- **The orchestrator editing files directly** - you scan, verify, batch, dispatch. Direct edits forfeit the parallel atomic-commit discipline that is the entire point.
- **`git add -A`** - other batches are running in parallel. `-A` silently includes their files into your commit. Stage ONLY your batch's files.
- **Attempting to fix a typecheck failure** - revert and report. The orchestrator decides whether to re-dispatch with narrower scope; the worker does not fix.
- **Skipping Phase 0 baseline** - without a baseline, "tests still pass" at the end is unverifiable. Run the floor BEFORE any scan.
- **Stopping on first batch failure** - the orchestrator pauses only if the BUILD breaks unfixable. Per-batch typecheck failures are isolated; report and continue.
- **Exceeding 50 candidates without narrowing** - abort condition. Document and stop.
- **Using OmO `task(subagent_type=...)` agent names or `task(category=...)` categories** - strip both; the harness port uses generic `task` workers with role in the prompt and has no OmO categories.

## Completion checklist

- [ ] Phase 0 baseline recorded (typecheck / test / build / git status).
- [ ] All strict-mode candidates + subagent findings in the master candidate list.
- [ ] Every candidate LSP-verified (0 references = confirmed; 1+ = dropped).
- [ ] False-positive guards applied (entry points, @public, tests, package.json exports).
- [ ] Batched by file (5-15 batches, zero file overlap).
- [ ] All batches dispatched in ONE message with `async: true`.
- [ ] Every batch subagent ran REVERT-ON-RED, not fix.
- [ ] Every batch commit staged ONLY its files (never `git add -A`).
- [ ] Phase 5 final verification ran; results compared to baseline.
- [ ] Summary produced (removed + skipped + verification status).
- [ ] Handoff skill (or "no follow-through requested") named.
