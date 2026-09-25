---
name: afk-debt-audit
description: "Autonomous read-only technical-debt audit across 9 dimensions WITHOUT a human in the loop. Cite every finding with file:line:col, classify Critical/High/Medium/Low, estimate effort, surface 'Looks Bad But Is Fine' false positives, and produce a TECH_DEBT_AUDIT.md report in the repo root with executive summary, findings table, Top-5 priorities, quick-wins checklist, and open questions. Use when the user says 'afk debt audit', 'auto tech debt', 'codebase health check without me', 'audit code quality', 'find tech debt', 'debt analysis', or wants a read-only catalog of debt (NOT a mutating cleanup - that is debloat-monorepo or afk-deadcode-removal). Triggers: 'afk debt audit', 'auto tech debt', 'debt audit', 'codebase health', 'afk-debt-audit'."
---

# AFK Debt Audit

The autonomous read-only technical-debt audit. You catalog all debt across 9 dimensions, cite every finding with `file:line:col`, classify by severity, estimate effort, and write a `TECH_DEBT_AUDIT.md` report in the repo root. The user does NOT sit in the loop - they asked for "afk" and you run the full audit autonomously.

This is the **read-only** sibling of `debloat-monorepo` (mutating Bun/TS cleanup) and `afk-deadcode-removal` (LSP-guaranteed removal with atomic commits). All three touch dead code or stale debt; they differ in *how*: this one catalogs and ranks, the other two excise. User runs `afk-debt-audit` first to get the prioritized report; weeks later they may run one of the mutating skills to actually remove what it flagged.

## When to use

User wants a read-only debt audit with NO human interview. Triggers: "afk debt audit", "auto tech debt", "debt audit", "codebase health check", "find tech debt", "debt analysis".

Do NOT use when the user wants to remove code - that is `debloat-monorepo` (Bun/TS, knip-driven, in-place edits) or `afk-deadcode-removal` (any TS, LSP-verified, parallel subagents, atomic commits). Do NOT use as a generic "review my PR" pass. Do NOT use on a repo with no source (it scans source code).

## The non-negotiable discipline

**Every finding cites `file:line:col`.** No generic claims without evidence. "There's a lot of `any`" is invalid output. "`src/api/handler.ts:42:5` uses `as any` on the public `RequestHandler` return type" is valid. The report is grounded or it does not exist.

**9 dimensions, all covered.** Architectural Decay, Consistency Rot, Type & Contract Debt, Test Debt, Dependency & Config Debt, Performance & Resource Hygiene, Error Handling & Observability, Security Hygiene, Documentation Drift. Skipping any dimension is the failure mode - the audit is incomplete and the report's priorities are skewed.

**Read-only.** No file is edited, no dependency is removed, no migration is performed. The deliverable is `TECH_DEBT_AUDIT.md`. If you find yourself about to `edit` or `write` source code, STOP - that is the mutation skills' job.

**Severity rubric held.** Critical / High / Medium / Low is applied with the definitions in Phase 3, not vibes. A missing edge case is not Critical. A hardcoded secret in source is.

**Deliberately thorough.** Subagents fan out per dimension on large repos. The cost is the feature - shallow audits are useless.

## The deliverable: `TECH_DEBT_AUDIT.md`

Write the report to `TECH_DEBT_AUDIT.md` in the repo root (use `TECH_DEBT_AUDIT.md` in cwd if no repo root is determinable). Required sections, in this order:

1. **Executive Summary** - 3-5 sentences: overall health, worst dimension, quick-wins count.
2. **Mental Model** - the repo's architecture in 1 paragraph (what it does, stack, module boundaries).
3. **Findings Table** - columns: ID, Category, File:Line, Severity (Critical/High/Medium/Low), Effort (Hours), Description, Recommendation.
4. **Top 5 Priorities** - ranked by impact/effort ratio.
5. **Quick Wins Checklist** - items under 30 minutes each.
6. **"Looks Bad But Is Fine"** - patterns that look like debt but are intentional (false-positive guards).
7. **Open Questions** - things the maintainer should clarify.

### Persistence mechanism (read-back discipline — load-bearing)

The report at `TECH_DEBT_AUDIT.md` is a rolling artifact. **Before the first write, load the shared `PERSISTENCE.md` (in this `skills/` directory) and follow the read-back discipline.** Composite operation: header intact, prior sections verbatim, new section appended at the end (or the Executive Summary revised in place when the audit concludes).

Tagline: "If it is not in `TECH_DEBT_AUDIT.md`, it did not happen."

## Phase 0 - Orient

One turn. Map the repo before auditing.

- `glob("**/*.{ts,tsx,js,jsx,py,go,rs,java,rb,...}")` - map the language stack (filter to the repo's actual languages).
- `glob("**/package.json")` + `read` - dependencies and build tooling.
- `bash("git log --oneline -200")` - churn: find highest-change files.
- `glob("**/*")` + basic math - find largest files (>300 LOC are candidates).
- Cross-reference high-churn + large = debt hot zones.
- Optional `mcp__codegraph_explore(query="architecture overview and main modules")` if a `.codegraph/` index exists at or above the repo path - replaces hand-inferring module boundaries.
- Write the Mental Model section first via the read-back discipline (`PERSISTENCE.md`).

## Phase 1 - Audit across 9 dimensions

Run all 9 dimensions. Parallelize tool calls within each dimension. Every finding cites `file:line:col` and includes the dimension name.

### 1. Architectural Decay

- `bash("ast-grep -p 'import { $$$ } from \"$SRC\"' -l ts .")` or `grep "^import .* from "` - map module graph, look for circular patterns.
- `grep("TODO|FIXME|HACK|XXX|WORKAROUND|TEMP")` - tagged debt markers.
- `grep("async|await")` on sync-looking files - misplaced async boundaries.
- `bash("wc -l <file>")` on each large file found in Phase 0.
- What to flag: files > 500 LOC (god files), functions > 80 LOC or > 4 nesting levels, classes > 15 methods or > 400 LOC, import cycles, dead exports (function/class defined but never imported elsewhere), commented-out code blocks (>3 consecutive lines).
- CodeGraph enhance (if available): `mcp__codegraph_explore(query="module dependencies and architecture boundaries")`.

### 2. Consistency Rot

- `bash("ast-grep -p 'import $CLIENT from \"$PKG\"' -l ts .")` - multiple HTTP clients.
- `grep("console.log|console.error|console.warn")` - direct console use vs logger.
- `grep("as any|@ts-ignore|@ts-expect-error|as unknown")` - type escapes (also flagged in dimension 3).
- `grep("eslint-disable|prettier-ignore")` - lint suppressions.
- What to flag: 3+ ways of doing the same thing (HTTP, logging, validation, config), mixed naming conventions, multiple date/time libraries, mixed error response shapes.

### 3. Type & Contract Debt

- `bash("ast-grep -p '$VALUE as any' -l ts .")` - runtime type escapes.
- `grep("@ts-expect-error")` - suppressed errors.
- `grep("@ts-ignore")` - suppressed errors (legacy).
- `bash("ast-grep -p '$NAME: any' -l ts .")` - typed as any.
- `lsp diagnostics` (file glob `src/**/*`) - current type errors.
- What to flag: `any` types on public APIs and exported interfaces, untyped function parameters, missing schema validation at API/IO boundaries, LSP type errors grouped by file.

### 4. Test Debt

- `glob("**/*.test.{ts,tsx,js,jsx,py,go,rs}")` - find all test files.
- `bash("npm test 2>&1 | grep -E '(fail|skip|todo)'")` or the repo's test command - current test health.
- Cross-reference Phase 0 high-churn files with test existence.
- What to flag: critical-path files with zero tests, skipped tests (`test.skip`, `describe.skip`), tests asserting implementation details vs behavior, slow tests (>1s each).

### 5. Dependency & Config Debt

- `bash("npm audit --omit=dev 2>&1 | head -40")` or the repo's audit command - known CVEs (if node_modules present).
- `read("package.json")` or the repo's manifest - dependency count, stale deps.
- `grep(".env|process.env|Bun.env")` - env var usage.
- `grep("(?i)API_KEY|SECRET|PASSWORD|TOKEN")` in non-config files - hardcoded config.
- What to flag: outdated major-version deps, deps that do the same thing (duplicate libraries), referenced env vars not documented in README, hardcoded environment-specific values.
- CodeGraph enhance (if available): `mcp__codegraph_explore` impact queries on key internal modules (logger, config loader, HTTP client) to see how widely a poor-quality core module ripples.

### 6. Performance & Resource Hygiene

- `bash("ast-grep -p 'for ($$$ of $$$) { $$$ await $$$ }' -l ts .")` - async-in-loop.
- `grep("await.*map|await.*filter|await.*forEach")` - sequential async iteration.
- `grep("Promise\\.all|Promise\\.allSettled")` - existing parallel patterns (good signal).
- `grep("addEventListener|on\\(|subscribe")` without `removeEventListener|off\\(|unsubscribe` nearby - listener hygiene.
- What to flag: `await` inside `for/of` loops, N+1 query patterns, missing cleanup on event listeners/intervals/handles, unnecessary serialization/deserialization.

### 7. Error Handling & Observability

- `bash("ast-grep -p 'catch ($$$) { $$$ }' -l ts .")` - catch blocks.
- `grep("catch.*{}|catch.*{\\s*}")` - empty catch blocks.
- `grep("console.error|logger\\.error|log\\.error")` - actual error logging.
- `bash("ast-grep -p 'throw new $ERR($$$)' -l ts .")` - error types used.
- What to flag: empty catch blocks (worst offense), generic `catch (e) { console.error(e) }` without recovery, inconsistent error shapes across modules, missing structured logging on critical paths, errors swallowed in promise chains (`.catch(() => {})`).
- CodeGraph enhance: `mcp__codegraph_explore(query="how errors propagate through <key-error-handler>")` to find swallows.

### 8. Security Hygiene

- `grep("(?i)api[Kk]ey|api_secret|password|secret|token|credential")` in source files (not config or env).
- `grep("(?i)SELECT .* FROM|INSERT INTO|UPDATE.*SET|DELETE FROM")` - SQL construction.
- `grep("innerHTML|dangerouslySetInnerHTML")` - XSS vectors.
- `grep("eval\\(|Function\\(|setTimeout\\(.*string|setInterval\\(.*string")` - code injection.
- What to flag: hardcoded secrets in source, string-concatenated SQL, `innerHTML` / `dangerouslySetInnerHTML` usage, `eval()` or string-based `setTimeout`/`setInterval`, permissive CORS or auth middleware.

### 9. Documentation Drift

- `read("README.md")` - check if claims match reality.
- `grep("@param|@returns|@throws")` - docstring coverage.
- `grep("FIXME|TODO|HACK|XXX|WORKAROUND")` - fixme density.
- Compare README API examples with actual signatures.
- What to flag: README claiming features that do not exist, public functions without doc comments, comments that contradict the code, stale ADRs if present.

## Phase 2 - Deeper dives (parallel subagents on large repos)

For repos > 50k LOC, dispatch heavy dimensions to parallel `task` subagents. Each subagent gets a `task()` prompt scoped to 2-3 dimensions with: CONTEXT (tech-debt-audit skill), GOAL (audit dimensions N and M), REQUEST (run the standard-tool searches from Phase 1 for those dimensions, report every finding with `file:line:col`, tag severity Critical/High/Medium/Low). Subagents do NOT use CodeGraph even if available - they use standard tools only.

Spawn 2-3 subagents in PARALLEL for the heaviest dimensions, collect results, synthesize. The main agent handles any CodeGraph queries itself while subagents run standard-tool passes.

## Phase 3 - Synthesize and deliver

1. Collect all findings from direct tool calls, CodeGraph queries (if available), and subagent results.
2. Deduplicate - same issue mentioned by multiple dimensions.
3. Classify severity:

   ```
   Critical = actively causing bugs or security holes
   High     = will cause problems under normal operation; blocks changes
   Medium   = reduces maintainability; inconsistent; violates team conventions
   Low      = cosmetic; would be nice to fix when nearby
   ```

4. Estimate effort in hours per finding (conservative).
5. Write `TECH_DEBT_AUDIT.md` with all 7 required sections, via the read-back discipline (`PERSISTENCE.md`).
6. Report summary to the user: overall health, worst dimension, quick-wins count, plan path.

## Phase 4 - Handoff

The report is the deliverable. If the user asked to follow through, name the downstream skill:

- Implement the Top-5 priorities as a real refactor → `request-refactor-plan`.
- Remove the dead-code findings the report flagged → `afk-deadcode-removal` (any TS, LSP-guaranteed, parallel atomic commits) or `debloat-monorepo` (Bun/TS, knip-driven, in-place edits + AGENTS.md scrub).
- Implement test coverage for the flagged critical-path files → `tdd`.
- Debug a Critical-severity finding → `diagnosing-bugs`.

Do NOT implement inline. This skill produces a report, not code.

## Anti-patterns (do NOT)

- **Citing findings without `file:line:col`** - "there's a lot of `any`" is invalid. The report is grounded or it does not exist.
- **Skipping a dimension** - the 9 dimensions are not optional. An incomplete audit skews the priorities and the user acts on bad data.
- **Editing source files** - this is read-only. If you find yourself about to `edit` or `write` source, STOP; route to a mutation skill.
- **Writing `TECH_DEBT_AUDIT.md` with only the latest section** - `write` overwrites whole-file and wipes prior sections. Use the read-back discipline (`PERSISTENCE.md`); always read back.
- **Conflating severity classes** - a styling nit is Low, not Medium. A hardcoded secret is Critical, not High. Severity drives the Top 5; misclassification leaks into bad user action.
- **Skipping the "Looks Bad But Is Fine" section** - false-positive guards are part of the deliverable. Without them the user wastes time "fixing" intentional patterns.
- **Using `task(category=...)` OmO categories** - strip; use generic `task` workers. (Kept in this port: `task` with explicit prompt, no `category=` / `subagent_type=` OmO specifics.)
- **Inventing `TECH_DEBT_AUDIT.md` schema not in the deliverable spec** - the 7 sections are the contract. Extra sections are fine if they fit between Findings Table and Top 5; never omit a required one.
- **Acting on the audit inline** - the audit produces a report; the user decides. If they say "fix it too", route to a mutation skill, do not edit in-skill.

## Completion checklist

- [ ] All 9 dimensions audited (every one has findings or explicit "no debt found").
- [ ] Every finding in the Findings Table has `file:line:col` and a dimension name.
- [ ] Severity applied per the rubric (Critical/High/Medium/Low, not vibes).
- [ ] Effort estimated in hours per finding (conservative).
- [ ] Top 5 Priorities ranked by impact/effort ratio.
- [ ] Quick Wins Checklist has at least 2 items under 30 minutes each (or an explicit "no quick wins" note).
- [ ] "Looks Bad But Is Fine" section explains at least 2-3 patterns.
- [ ] Open Questions section lists things the maintainer should clarify.
- [ ] `TECH_DEBT_AUDIT.md` exists on disk - `read` it and confirm body intact (read-back after write).
- [ ] Handoff skill (or "no follow-through requested") named.
