---
name: afk-discipline-scaffold
description: "Autonomous rollout of an OmO-style discipline scaffold into ANY project, WITHOUT a human in the loop. Distill the portable intent behind OmO's project-discipline setup - human-in-loop-as-failure-signal manifesto, AGENTS.md as the canonical work contract, the .agents/ skills + commands directory shape, the notepad-write-guard / planner-md-only / model-routing hook patterns, wisdom-accumulation across tasks, and the planning-layer/reviewer/execution/orchestrator separation - and install the project-native equivalents (AGENTS.md, skills/, hooks or hook-equivalent pre-commit/lint-staged, notepads, review gates). Use when the user says 'afk discipline scaffold', 'rollout omo discipline', 'install project discipline', 'setup autonomous project guardrails', or wants the OmO setup's intent ported to their stack. Triggers: 'afk discipline scaffold', 'rollout discipline', 'install project guardrails', 'afk-discipline-scaffold'."
---

# AFK Discipline Scaffold

The autonomous rollout of an OmO-style project-discipline scaffold into any project. You inspect the target project's stack and existing conventions, distill the portable *intent* behind OmO's project-discipline setup, and install the project-native equivalents: an `AGENTS.md` work contract, a `skills/` directory shape, hook-equivalent guardrails (pre-commit / lint-staged / language-server rules / harness lifecycle hooks - whatever the stack supports), wisdom-accumulation notepads, and the planning/review/execution layer separation. The user does NOT sit in the loop - they asked for "afk" and you produce a coherent scaffold, installed, with documentation.

The skill's job is **the scaffold's intent**, not OmO's TypeScript idiom verbatim. OmO is a Bun/TypeScript OpenCode plugin; porting the discipline to a Python repo, a Go monolith, or a Rust workspace means translating the *intent* (human-in-loop-is-failure-signal; AGENTS.md is the work contract; plannermd-only guardrails; notepad-write-guard for append-only logs; wisdom accumulates across tasks) into the target's idiom (pyproject + ruff + pre-commit; go generate + golangci-lint; cargo + clippy + cargo-husky, etc.). Never copy OmO's `.omo/` paths, `task(subagent_type=...)` names, or its specific hook implementations - install the equivalent.

## When to use

User wants an OmO-discipline scaffold rolled into a project, autonomously. Triggers: "afk discipline scaffold", "rollout omo discipline", "install project guardrails", "setup autonomous project guardrails", "afk-discipline-scaffold".

Do NOT use when the user wants interactive setup decisions - that is a manual design exercise, not a scaffold rollout. Do NOT use on a project that already has a documented discipline setup (ask before overwriting). Do NOT use to install OmO itself - point the user to `bunx oh-my-openagent install` for that. Do NOT use to install OmO's model-routing or 11 named agents - those are OmO-runtime-specific; this skill ports the *intent* to the user's own agent workflow, not OmO's.

## The non-negotiable discipline

**Port intent, not idiom.** The OmO setup is TypeScript + OpenCode. Translating to Python/Go/Rust means understanding *why* each OmO piece exists and rebuilding it in the target idiom. Copying OmO's `.omo/` paths, `task(subagent_type=...)` calls, or hook implementations into a non-OmO project is the canonical failure - they do not compile or run.

**AGENTS.md is the canonical work contract.** Whatever the stack, an `AGENTS.md` at the repo root is the human- AND agent-readable contract: what the project does, how it's structured, what conventions agents must follow, what is forbidden. It is NOT documentation; it is the work contract a downstream agent reads first when it arrives.

**Human-in-loop is a failure signal.** The scaffold's design principle: every guardrail, every hook, every discipline entry exists so the agent can complete work without requiring the human to babysit it. "The agent thinks, the agent decides, the agent executes, the human only initiates." Each installed piece must support this - if a guardrail's only purpose is to make the human do more, do not install it.

**Indistinguishable code.** The scaffold's quality bar: code written by an agent following the scaffold should be indistinguishable from code written by a senior engineer on the team. Following existing patterns exactly; proper error handling without being asked; no AI slop (over-engineering, premature abstractions, needless scope). If a reviewer can tell a commit was agent-made, the scaffold has not done its job.

**Verify before install.** Every scaffold piece lands in a real project. Run the project's typecheck / test / lint / build commands BEFORE and AFTER install to prove the scaffold does not regress the project. If the scaffold breaks the build, revert and report.

**Persistence when documenting** (AGENTS.md, skills, hooks): `write` overwrites whole-file; updates use the read-back discipline (see `PERSISTENCE.md`).

## The deliverable: installed scaffold + `DISCIPLINE_SCAFFOLD.md` audit trail

The scaffold itself is the deliverable - a coherent set of installed files in the target project. The audit trail `DISCIPLINE_SCAFFOLD.md` in the repo root documents what was installed, why, and how each piece maps to the OmO intent it ports.

Required audit-trail sections:

1. **Intent Summary** - one paragraph: this scaffold ports OmO's discipline intent (human-in-loop-as-failure-signal; AGENTS.md work contract; planner/reviewer/executor separation; wisdom accumulation) to the target stack.
2. **Installed Pieces** - table: piece | path | OmO intent it ports | target-idiom translation | verification.
3. **Skipped OmO Pieces** - list of OmO pieces deliberately NOT ported, with rationale (e.g. OmO's 11 named agents - too OmO-runtime-specific to port to a generic workflow).
4. **Stack Notes** - what the target stack supports for hooks/guards and what was used.
5. **Verification** - typecheck/test/build command pass status pre- and post-install.
6. **Open Questions** - things the maintainer should clarify (e.g. preferred model routing, pre-commit vs husky, notepad directory location).

### Persistence mechanism (read-back discipline — load-bearing)

The audit trail at `DISCIPLINE_SCAFFOLD.md` is a rolling artifact. **Before the first write, load the shared `PERSISTENCE.md` (in this `skills/` directory) and follow the read-back discipline.** Composite operation: header intact, prior sections verbatim, new section appended (or the Intent Summary revised in place at the end when the install concludes).

Tagline: "If it is not in `DISCIPLINE_SCAFFOLD.md`, it did not happen."

## Phase 0 - Orient the target project

One turn. Inspect before installing.

- `glob("**/*")` to map the project shape; identify the stack via manifest files (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `mix.exs`, etc.).
- `read` the manifest to identify existing tooling: linter, formatter, test runner, build system, dependency manager.
- `read` any existing `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `CONTRIBUTING.md`, `README.md` - capture existing conventions; the scaffold must NOT contradict them silently.
- Run the project's existing typecheck/test/lint/build commands and record the baseline pass/fail counts. The post-install runs must equal this baseline.
- `bash("git status --porcelain")` - confirm a clean tree before install.
- Write the Intent Summary section to `DISCIPLINE_SCAFFOLD.md` first via the read-back discipline (`PERSISTENCE.md`).

## Phase 1 - Distill OmO intent

Already done at skill-write time, but you re-derive the mapping per-target because idiom differs. The OmO pieces and their portable intent:

| OmO piece | Portable intent | Target-idiom translation (varies by stack) |
|-----------|----------------|--------------------------------------------|
| `docs/manifesto.md` - "human-in-loop = failure signal"; "indistinguishable code" | The scaffold's quality bar and design principle | Distilled into `AGENTS.md` opening section + a discipline-rubric section; NOT copied verbatim
| `.agents/AGENTS.md` - project-scope skills/commands directory contract | AGENTS.md IS the work contract, declares skills + commands + conventions | Target's `AGENTS.md` at repo root carrying the equivalent content: stack-specific tooling, skill list, command list
| `.agents/skills/<name>/SKILL.md` - flat skill layout, one file per skill | Skills are flat, each SKILL.md is self-contained | Target's `skills/<name>/SKILL.md` if the harness supports it; otherwise an `AGENTS.md` skills section enumerating the equivalent workflow checklists
| Planners/editors restricted to `.omo/` plan files (`prometheus-md-only` hook) | Planners do NOT edit product code; planning and execution are separate | Pre-commit rule or harness hook that blocks planner-role agents from editing source; OR an AGENTS.md discipline rule that the agent enforces in-session
| `notepad-write-guard` - Write to notepad paths refused (append-only requires edit, not write) | Wisdom accumulates across tasks; notepads are append-only | A pre-commit / lint rule or harness hook that refuses `write` to notepad paths; OR a discipline rule with an audit-trail artifact that catches the violation
| Category-based model routing (`task(category=visual-engineering)` etc.) | Route by intent, not by model name | Stack-specific: a model-routing config or a policy file; OR an AGENTS.md discipline rule naming the routing intent and which model-family suits each role. Sparse intent - the target does not need OmO's 11 categories.
| 11 named agents (Sisyphus, Prometheus, Atlas, Metis, Momus, Hephaestus, Oracle, Librarian, Explore, Multimodal Looker, Sisyphus-Junior) | Planning-layer / orchestrator / worker / reviewer separation | Target's harness agents OR discipline rules describing the equivalent roles (planner, gap-analyst, plan-reviewer, orchestrator, deep-worker, code-grep, docs-search). DO NOT install OmO's named agents verbatim - they are OmO-runtime-specific.
| Wisdom notepads (`.omo/notepads/<plan-name>/*.md` - learnings, decisions, issues, verification, problems) | Knowledge accumulated across tasks; not repeated | Target's `<plans>/<slug>/notepads/` directory with the same five files (learnings, decisions, issues, verification, problems); appended per task; passed forward to subsequent subagents.
| Approval gate (`review_required: true` triggers dual Momus + Oracle review) | Plan is reviewed independently before execution | A reviewer subagent invocation OR a discipline rule that an approved plan must have two independent reviewers sign off (one approval-biased blocker-finder, one strategic slow-model). Configurable per-plan.
| IntentGate - classify user intent first (Refactoring/Build/Mid-sized/Collaborative/Architecture/Research) then route | Intent classification drives the planning strategy; not all planning is the same | An AGENTS.md discipline rule that planning begins with intent classification and the chosen class drives the interview strategy; OR a pre-planning subagent that produces the classification and feeds the plan agent.
| Auto-continue (orchestrator never asks "should I continue?") | The agent completes autonomously; only pauses on real blockers | An AGENTS.md discipline rule explicitly forbidding approval-style questions between plan steps.
| Parallel-by-default (sequential only for named blocking deps) | Wall-clock time matters; fire independent subagents in one message | Discipline rule. Plus the orchestrator's dispatch behavior depends on the harness's parallel `task` support.
| Self-origin verification (subagent claims are CLAIMS until verified) | Subagents lie; automated checks alone are not enough | Discipline rule plus the orchestrator's `read`-every-modified-file behavior.

Capture the per-target mapping in `DISCIPLINE_SCAFFOLD.md`'s Installed Pieces section. Skip the pieces that do not translate (and list them in Skipped OmO Pieces with rationale).

## Phase 2 - Install the pieces

Install in order, verifying after each batch via `bash(<project typecheck>)` and `bash(<project build>)`:

1. **`AGENTS.md` at repo root** - the work contract. Includes: project intent (1 paragraph), structure overview (module boundaries), stack tooling (build/test/lint/typecheck commands), conventions (naming, error-handling, test patterns, AI-slop guardrails - adapt to the stack's vocabulary), the discipline rules ported in Phase 1 (intent classification, parallel-by-default, auto-continue, self-origin verification, subagents-lie, planner-not-editor, indistinguishable-code, human-in-loop-is-failure-signal).
2. **`skills/` directory** - flat layout. If the project ships its own reusable skills, install each as `skills/<name>/SKILL.md` (frontmatter `name` + `description`, when-to-use, the core discipline, phases, anti-patterns, completion checklist). If the project does not yet have skills, install a starter skill (`skills/install-discipline-scaffold/SKILL.md` is itself the bootstrap) and document the schema in `AGENTS.md`.
3. **Wisdom notepads** - create `<plans>/<slug>/notepads/` (or `.notepads/<slug>/` if the user prefers) with five empty files: `learnings.md`, `decisions.md`, `issues.md`, `verification.md`, `problems.md`. Document the schema in AGENTS.md: each file is append-only via the read-back discipline (`PERSISTENCE.md`); the orchestrator reads all five before dispatching the next subagent and injects relevant wisdom as "Inherited Wisdom" in the dispatch prompt.
4. **Hook-equivalent guardrails** - adapted to the stack:
   - **If the project uses git**: install pre-commit hooks via the stack's mechanism (Husky + lint-staged for Node/TS/Bun; `pre-commit` framework for Python; `cargo-husky` for Rust; `golangci-lint` with a CI-side check for Go). The hooks enforce: AI-slop markers (`// TODO: implement`, `// stub`) blocked from commit; merge markers stripped; typecheck must pass on staged files.
   - **If the project uses a harness with lifecycle hooks** (OpenCode, Claude Code's hooks, Cursor rules): install a `prometheus-md-only`-equivalent that blocks the planner-role from editing source; install a `notepad-write-guard`-equivalent that refuses `write` to notepad paths (append-only enforcement).
   - **If neither**: encode the equivalent as discipline rules in `AGENTS.md` + an audit-trail artifact (`DISCIPLINE_SCAFFOLD.md` records violations for the maintainer to review).
5. **Reviewer gate** - AGENTS.md discipline rule that an executable plan which the user approved for execution must have two independent reviewers sign off (one approval-biased blocker-finder checking references + executability + QA scenarios; one strategic slow-model reviewer). The reviewers are invoked as `task` subagents in PARALLEL. Both must approve. No max retry limit; fix and re-submit.
6. **Intent classification rule** - AGENTS.md discipline rule that planning sessions begin with intent classification (Refactoring / Build from Scratch / Mid-sized / Collaborative / Architecture / Research) before any plan structure is attempted. The classification drives the interview-vs-defaults strategy.
7. **Model routing note** (optional, only if the user has multiple model providers configured) - AGENTS.md section naming the routing intent and which model-family suits each role. Sparse: do not enumerate 11 agents unless the user asks.

After each batch:
- Run `bash(<project typecheck>)` and `bash(<project test command>)`.
- If either regresses, revert the batch and report.
- Update `DISCIPLINE_SCAFFOLD.md`'s Installed Pieces and Verification sections via the read-back discipline (`PERSISTENCE.md`).

## Phase 3 - Verify

After all batches land:

- Run the full typecheck/test/lint/build battery. Results MUST equal the Phase 0 baseline (allow ±1 flake on slow CI).
- `bash("git status --porcelain")` - review the tree; stage new files; do NOT commit unless the user asked.
- `read` `AGENTS.md` and confirm body intact.
- `read` each installed `skills/<name>/SKILL.md` and confirm intact.
- `read` `DISCIPLINE_SCAFFOLD.md` and confirm body intact.

## Phase 4 - Handoff

The scaffold is the deliverable. If the user asked to follow through, name the downstream:

- Plan the first feature using the new scaffold → `afk-ulw-pipeline` (autonomous planning) or interactive `ulw-plan` if the user wants interview mode.
- Add project-specific skills under the new `skills/` dir → `request-refactor-plan` for the skill catalog or design each via `design-an-interface`.
- Audit the rest of the project's debt under the new discipline → `afk-debt-audit`.
- Set up pre-commit hooks specifically (if Phase 2 could not install them) → `setup-pre-commit`.

Do NOT install OmO itself. Do NOT implement features inline. Do NOT commit unless the user asked.

## Anti-patterns (do NOT)

- **Copying OmO idiom verbatim into a non-OmO project** - `.omo/` paths, `task(subagent_type=...)` names, the 11 named agents, `bun run knip` on a non-Bun repo. None of these compile in the target. Port intent, translate idiom.
- **Skipping intent-derivation** - copying OmO's pattern without understanding why it exists installs guardrails the target does not need and misses the guardrails the target's idiom calls for.
- **Installing OmO's 11 named agents** - they are OmO-runtime-specific. The portable intent is the *role separation* (planner / gap-analyst / reviewer / orchestrator / deep-worker / code-grep / docs-search). The target's harness agents, or discipline rules describing the roles, are the install.
- **AGENTS.md as documentation** - it is the work contract. If it reads like a README, it has failed. Agents consult it for "what conventions must I follow"; be specific.
- **Skipping Phase 0 baseline** - without it, "tests still pass" at the end is unverifiable. The scaffold must not regress the project.
- **Installing the scaffold on a dirty git tree** - Phase 0 records clean status; if dirty, ask before proceeding.
- **One giant commit** - each Phase 2 batch is its own atomic commit (if the user asked to commit). Mixed-batch commits make post-install regression bisection impossible.
- **Writing `DISCIPLINE_SCAFFOLD.md` with only the latest section** - `write` overwrites whole-file. Use the read-back discipline (`PERSISTENCE.md`); always read back.
- **Leaving Skipped OmO Pieces unexplained** - the audit trail exists so the maintainer knows what was deliberately not ported and why. Empty section is invalid.
- **Installing model routing for 11 OmO categories** - sparse intent. Most projects need 2-3 roles (planner, deep-worker, code-grep). Enumerating OmO's 11 category names in a non-OmO AGENTS.md is cargo-cult.
- **Auto-committing without permission** - stage, do not commit, unless the user said yes.
- **Treating the scaffold as a one-shot install** - capture Open Questions; the maintainer decides on the genuinely ambiguous parts (e.g. preferred notepad dir location, Husky vs lefthook, pre-commit framework vs bare script).

## Completion checklist

- [ ] Phase 0 baseline recorded (typecheck / test / lint / build / git status).
- [ ] `AGENTS.md` installed at repo root with: project intent, structure, stack tooling, conventions, and the discipline rules ported in Phase 1.
- [ ] `skills/` directory installed (flat layout; `skills/<name>/SKILL.md` schema documented in AGENTS.md).
- [ ] Wisdom notepads directory installed with the five append-only files; schema documented in AGENTS.md.
- [ ] Hook-equivalent guardrails installed OR documented as discipline rules if the stack has no hook mechanism.
- [ ] Reviewer gate installed (two independent reviewers, parallel, both must approve, no max retry).
- [ ] Intent classification rule installed.
- [ ] Model routing documented (optional, sparse - only if the user has multi-provider).
- [ ] Each Phase 2 batch verified: typecheck/test did not regress vs baseline.
- [ ] `DISCIPLINE_SCAFFOLD.md` exists with all 6 required sections; body intact (read-back after write).
- [ ] Skipped OmO Pieces listed with rationale (no silent omissions).
- [ ] Open Questions listed for the maintainer.
- [ ] Tree status presented; staged but NOT committed unless user said yes.
- [ ] Handoff skill (or "no follow-through requested") named.
