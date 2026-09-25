---
name: afk-ulw-pipeline
description: "Autonomous planning-and-execution handoff pipeline WITHOUT a human in the loop. Walk an intent-routing decision (CLEAR vs UNCLEAR), explore the codebase, ask only the genuine forks exploration cannot resolve OR adopt best-practice defaults for fuzzy intent, then write ONE decision-complete work plan a downstream worker executes with zero further interview. Approval authorizes the plan, never implementation. Use when the user says 'afk ulw plan', 'auto-plan', 'plan without me', 'just plan it', 'figure out what to build', or wants the harness to chain planning -> review -> execution without yielding back. Portable distillation of OmO's ulw-plan + Prometheus/Metis/Momus pipeline, stripped of OpenCode runtime. Triggers: 'afk ulw plan', 'auto-plan', 'plan without me', 'afk-ulw-pipeline', 'just plan it'."
---

# AFK ULW Pipeline

The autonomous pipeline that turns a vague or large request into ONE decision-complete work plan, then optionally hands off to an executor that runs it without interviewing the user again. This is the portable distillation of OmO's `ulw-plan` skill + the Prometheus/Metis/Momus/Atlas pipeline, stripped of OpenCode runtime (no `.omo/` paths, no `subagent_type` OmO names, no model assignments). What survives the extraction is the *decision protocol*: explore-first, two-filter on candidate questions, decision-complete north star, full-scope default, approval authorizes the plan not the implementation, agent-executed QA per todo.

The user does NOT sit in the interview loop in afk mode - they asked for "afk" and you adopt best-practice defaults for any fuzzy intent, with each default ANNOUNCED (not silently applied). The deliverable is a work-plan artifact on disk that a downstream worker (this skill, in execution mode, or a separate role the user invokes) executes with zero further interview.

## When to use

User wants a plan produced autonomously - they do NOT want to be interviewed. Triggers: "afk ulw plan", "auto-plan", "plan without me", "afk-ulw-pipeline", "just plan it", "figure out what to build".

Do NOT use when the user wants to BE interviewed ("ask me", "interview me", "why aren't you asking") - route to interactive planning instead. Do NOT use to actually implement code in the planning pass - approval authorizes the plan, not implementation. Do NOT use for trivial single-file changes - direct action is cheaper.

## The non-negotiable discipline

**Intent routing is decisive, not exploratory.** Make ONE CLEAR vs UNCLEAR judgment, ANNOUNCE it to the user in one line, then load the matching intent path. A misrouted CLEAR request silently defaults over user-owned forks; a misrouted UNCLEAR request offloads the agent's job onto the user. The dominant failure to guard against is mis-routing CLEAR to UNCLEAR.

**Two filters on every candidate question, in order.** (1) Could collected evidence answer it? → explore instead. (2) Could a defensible default answer it (and it is not an owner-decision)? → adopt and ANNOUNCE the default, do not ask. Only owner-decisions (irreversible / destructive / safety-critical / cross-cutting product choices) survive as questions to the user. Default the reversible internals; surface the owner-decisions.

**Decision-complete is the north star.** The downstream executor has zero interview context. Spell out exact paths, "every X in Y", and an explicit Must-NOT-Have. Leave the executor zero judgment calls.

**Full scope is the default.** Plan the ENTIRE request. "MVP", "v1", "phase 1", any reduced subset is never an option the agent invents - it exists only if the user introduces it. Scope OUT entries are guardrails against unrequested additions, never reductions of the request.

**Approval is not execution.** Approval authorizes writing the plan ONLY, never implementation. ONE request → ONE plan, however large. The plan is the deliverable; execution is a separate invocation (or the executor subagent after the plan is locked).

**Agent-executed QA per todo.** Every task has QA with: specific tool, concrete steps, expected result, evidence path. Happy-path AND failure/edge-case scenarios. Zero human-intervention verification. "User manually tests" is FORBIDDEN.

**Persistence when writing the plan.** `write` overwrites whole-file; updates use the read-back discipline (`PERSISTENCE.md`).

## The plan artifact: `<slug>-plan.md`

The plan lives in the repo at `<slug>-plan.md` in cwd (use `.plans/<slug>-plan.md` if a `.plans/` directory exists). Required sections, in this order:

1. **Intent & Routing** - `intent: clear | unclear`, `review_required: true | false`, one-line announcement to the user.
2. **Mental Model** - the relevant codebase area in 1 paragraph.
3. **Hard Constraints** - invariants the plan MUST respect (codebase locks + user-stated).
4. **Decisions Made** - adopted defaults with their rationale; survey user-answered forks here too.
5. **Scope** - Must-Have (explicit deliverables) + Must-NOT-Have (explicit exclusions, the AI-slop guardrails).
6. **Todos** - column-zero Markdown task rows: `- [ ] N. <title>`. Each todo has: references (`file:lines`), acceptance criteria (executable commands, not human actions), QA scenarios (tool + steps + expected result + evidence path), commit message.
7. **Dependency Matrix** - parallelizable groups vs sequential tasks with the named blocker.
8. **Final Verification Wave** - column-zero task rows: `- [ ] F1. <title>`. Verifier tasks (reviewers, build, test) that ALL must pass before the work is considered complete.
9. **Review State** - Momus-style review verdict (OKAY / REJECT), Oracle review verdict if high-accuracy requested.

### Persistence mechanism (read-back discipline — load-bearing)

The plan at `<slug>-plan.md` (`.plans/<slug>-plan.md` if `.plans/` exists) is a rolling artifact. **Before the first write, load the shared `PERSISTENCE.md` (in this `skills/` directory) and follow the read-back discipline.** Composite operation: header intact, prior sections verbatim, new/updated section appended or modified in place (per the per-phase instructions).

Tagline: "If it is not in the plan file, it did not happen."

## Phase 0 - Intent routing

One turn. Make ONE judgment, ANNOUNCE it, load the matching path.

- Read the user's request carefully.
- Use `CodeGraph` (if available) or `read` on CONTEXT.md / AGENTS.md / ADRs to ground yourself in the relevant area.
- Decide: is the desired **OUTCOME** clear, or fuzzy?
  - **CLEAR** - the user knows the outcome; open items are only preferences/tradeoffs the repo cannot answer (genuine owner-decisions).
  - **UNCLEAR** - the outcome itself is fuzzy (vague brief, "make it better", bootstrap).
- Review modifiers ("high accuracy", "deep review", afk variants of "고정밀") → set `review_required: true` in the plan; the dual review (native + independent slow-model) is REQUIRED before handoff.
- ANNOUNCE both signals to the user in one line:
  - "Intent: **CLEAR**, review required - [reason]. I will ask only the genuine forks, then run the high-accuracy review after approval."
  - "Intent: **UNCLEAR**, review required - [reason]. I will adopt best-practice defaults and announce them, then run the high-accuracy review automatically."
- **OVERRIDE - explicit ask wins:** if the user explicitly asked to be interviewed ("ask me", "interview me"), route CLEAR with the adopt-default filter OFF; every surviving fork is ASKED, not defaulted. This beats the OUTCOME test even on a fuzzy brief.
- **ON THE FENCE** - when CLEAR vs UNCLEAR is genuinely ambiguous, treat as CLEAR and ask exactly ONE question. A user wrongly silenced is worse than one extra question. The dominant failure is mis-routing a CLEAR request to UNCLEAR (silently defaults over user-owned forks the user wanted to own).

## Phase 1 - Explore (both paths)

Explore-ground yourself BEFORE producing any task list.

- `CodeGraph` first if `codegraph_explore` is available - one capped call per area for source + callers/callees/impact.
- Otherwise `read` + `grep` + `glob` + `lsp` for the relevant files.
- Parallel-dispatch independent research subagents in ONE turn:
  - Internal patterns/conventions/tests → `task` worker ("explorer" role in the prompt).
  - External docs/contracts → `task` worker ("librarian" role in the prompt); use `mcp__context_resolve_library_id` + `mcp__context_query_docs` and `mcp__deepwiki_ask_question`.
  - High-IQ architectural consultation (optional, for Architecture intent) → `task` worker with slow model ("oracle" role in the prompt), read-only.
- Subagent outputs are CLAIMS until you independently verify them.
- Explore to sufficiency, then STOP. One research wave per open question; never re-explore to double-check.

## Phase 2 - Apply the two-filter (per candidate question)

For EACH candidate question that survives exploration:

1. Could collected evidence answer it? → explore more or cite the existing evidence; do not ask.
2. Could a defensible default answer it (and it is NOT an owner-decision)? → adopt and ANNOUNCE the default; do not ask.
3. Is it an owner-decision (irreversible / destructive / safety-critical / cross-cutting product choice)? → it survives as a question to the user EVEN WHEN a default exists.

**CLEAR intent path:** ask the surviving forks with WHY; record each answer in the plan's Decisions Made. Offer high-accuracy review ONLY if `review_required: false` (if true, review is mandatory, not offered).

**UNCLEAR intent path:** research maximally (Phase 1), adopt and ANNOUNCE best-practice defaults for every fork; do NOT ask the user extra questions. Unless the work classified Trivial, set `review_required: true` before the approval gate and run the high-accuracy review automatically.

Record all decisions and the `intent` / `review_required` fields to the plan file's Intent & Routing + Decisions Made sections via the read-back discipline (`PERSISTENCE.md`).

## Phase 3 - Plan artifact production

When exploration is exhausted and unknowns are answered:

- Compose the full plan body: Intent & Routing, Mental Model, Hard Constraints, Decisions Made, Scope (Must-Have + Must-NOT-Have), Todos (column-zero rows with references + acceptance + QA + commit), Dependency Matrix, Final Verification Wave (verifier rows).
- Each Todo row format: `- [ ] N. <title>`.
- Each Verifier row format: `- [ ] F<number>. <title>`.
- Each Todo MUST include: file references (`file:lines`), acceptance criteria as EXECUTABLE commands (not "user manually tests"), QA scenarios (specific tool + concrete steps + expected result + evidence path, both happy and failure/edge), commit message.
- Structural self-check before write: every implementation row is column-zero, matches `- [ ] N. <title>`; every verifier row is column-zero, matches `- [ ] F<n>. <title>`; no prose heading masquerades as a task; tasks appear in the intended section.
- Write the plan via the read-back discipline (`PERSISTENCE.md`).

## Phase 4 - Approval gate

Approval authorizes plan creation / finalization, NEVER implementation. ONE request → ONE plan, however large.

- When the plan file is complete: present a short brief once, then `status: awaiting-approval` recorded in the plan file's Review State section.
- **W ait for the user's explicit okay** in afk mode, this means: do NOT implement; do NOT spawn implementers; do NOT consume the approval as authorization to do anything beyond the plan existing on disk.
- If the user approved already (one-shot afk mode), proceed to Phase 5 and run any required review AUTOMATICALLY (unclear intent + review_required, OR clear intent with review_required:true).

If `review_required: false` and CLEAR intent: present the plan and ask the start-or-review question, OR yield with the plan on disk for the user to invoke the executor separately.

## Phase 5 - High-accuracy review (if required)

If `review_required: true`, run two independent reviews in parallel:

1. **Native reviewer** (the harness's default reviewer, or a `task` worker with the "momus" role) - approval-biased: rejects ONLY verified blockers; max 3 specific issues; no design nitpicks; "good enough is good enough".
2. **Independent slow-model reviewer** (a `task` worker with the slow model and the "oracle" role) - strategic, architectural, blast-radius review.

Both must approve before handoff. If either rejects, fix every cited issue and re-submit to both. No max retry limit. Record both verdicts in the plan file's Review State section via the read-back discipline (`PERSISTENCE.md`).

## Phase 6 - Handoff

The plan is the deliverable. Name the downstream:

- Implement the plan → invoke the executor (a separate `task` worker with the "executor" role, or the user's chosen orchestration mode). The plan file is self-contained; the executor reads it and runs the Todos in parallel batches with auto-continue.
- Refine the plan further → `afk-hyperplan` for a 5-reviewer adversarial pass on the Insights, or `request-refactor-plan` if the plan is fundamentally a refactor.
- Test-first implementation of specific todos → `tdd`.

Do NOT implement inline in this skill. Plan mode is sticky.

## Anti-patterns (do NOT)

- **Mis-routing CLEAR to UNCLEAR** - silently applies defaults over user-owned forks. The dominant failure. On the fence, route CLEAR and ask ONE question.
- **Mis-routing UNCLEAR to CLEAR** - offloads the agent's job onto the user. When the outcome is fuzzy, adopt and ANNOUNCE defaults; do not interrogate.
- **Asking discoverable facts** - if the codebase or docs answer it, explore. Owner-decisions are the ONLY thing that survives exploration.
- **Adopting defaults silently** - every adopted default is ANNOUNCED in the plan's Decisions Made section, with rationale. Silent defaults forfeit the user's audit trail.
- **Inventing an "MVP" / "v1" / "phase 1" scope reduction** - full scope is the default. Reduced scope exists only if the user introduces it.
- **Approval as execution** - approval authorizes the plan. Implementation is a separate step. Conflating them is the canonical scope leak.
- **Writing the plan with ONLY the new section** - `write` overwrites whole-file and wipes prior sections. Use the read-back discipline (`PERSISTENCE.md`); always read back.
- **Vague QA criteria** - "verify it works" is invalid. QA is tool + steps + expected result + evidence path, both happy and failure cases.
- **User-intervention acceptance criteria** - "user manually tests", "user visually confirms" is FORBIDDEN. Agent-executed QA only.
- **Re-exploring to double-check** - one research wave per question; stop at sufficiency.
- **Subagent outputs treated as truth** - verify before incorporating.
- **Using OmO `subagent_type` names directly** - the harness port uses generic `task` workers with role descriptions in the prompt (explorer, librarian, oracle, momus, executor). The skill describes function, not the OmO agent's name as a subagent_type.
- **Hardcoding `.omo/plans/*.md` paths** - replaced with `<slug>-plan.md` in cwd (or `.plans/<slug>-plan.md` if that dir exists). No OmO runtime paths.
- **Implementing in any Phase other than the explicit handoff** - plan mode is sticky across all six phases. The plan file is the deliverable.

## Completion checklist

- [ ] Intent & Routing section declares `intent: clear|unclear` and `review_required: true|false`.
- [ ] One-line announcement made to the user (intent + review state).
- [ ] Phase 1 exploration run with CodeGraph first OR fallback to read/grep/glob/lsp.
- [ ] Two-filter applied to every candidate question; owner-decisions surfaced, defaults ANNOUNCED.
- [ ] Plan file has all 9 required sections in the required order.
- [ ] Every Todo row is column-zero, matches `- [ ] N. <title>`, and has references + executable acceptance + QA + commit message.
- [ ] Every Verifier row is column-zero, matches `- [ ] F<n>. <title>`.
- [ ] Structural self-check passed; no prose heading masquerades as a task.
- [ ] `review_required: true` → both reviewers (native + slow-model) ran; verdicts recorded in Review State.
- [ ] Plan file written via the read-back discipline (`PERSISTENCE.md`): body confirmed intact after read-back.
- [ ] Approval gate recorded `status: awaiting-approval` (or afk one-shot approval consumed for the plan only).
- [ ] Handoff skill or executor named (or "no follow-through requested").
