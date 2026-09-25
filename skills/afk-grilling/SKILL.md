---
name: afk-grilling
description: "Autonomous relentless grilling of a plan, decision, or idea WITHOUT a human in the loop. Walk the decision tree one question per turn; on every question gather tool-cited facts, enumerate edge cases, and consult at least one external source; accumulate a decision log. Use when the user says 'afk grilling', 'auto-grill', 'grill with docs', 'grill without me', 'grill me on <topic> without asking me back', or the slash form 'afk-grilling'."
---

# AFK Grilling

The autonomous twin of the interactive `grilling` skill. Same decision-tree depth - but you play **both seats**: the griller asks one question, the answerer (also you) answers it, then the next question is asked. Every fact claim is grounded in tool lookups (codebase knowledge graph, Context7, DeepWiki, web search) rather than assumed. The deliverable is a durable decision-log artifact, not chat output.

## When to use

User wants relentless grilling of a plan, decision, or idea but does NOT want to be asked back. Triggers: "afk grilling", "auto-grill", "grill with docs", "grill without me", "grill me on <topic> without asking me back", "afk-grilling".

Do NOT use when the user wants to be in the loop - that's the interactive `grilling` skill. Do NOT use as a generic "review my plan" pass; this is deliberately slow.

## The non-negotiable discipline

**One question per turn.** The griller asks ONE question; the answerer answers it in the SAME turn (after research + edge cases); the log entry is appended in that same turn; THEN the turn ends and the next question is asked fresh in a new turn. Batching decisions collapses the discipline into a one-shot review and forfeits the per-turn reasoning leverage that is the entire point of the skill.

**Every fact claim cited.** If a fact is not trivially evident from the codebase or the question text, look it up via tools before asserting it. "Common knowledge" is not evidence. If you cannot look it up, state the gap explicitly; do not invent.

**Every question gets edge case enumeration AND external consultation.** These are mandatory sub-steps of the micro-cycle, not optional polish. Skipping them is the failure mode.

**Deliberately slow.** This skill trades turns and tokens for depth. Say so before starting if the user might not have expected it.

## The decision-log artifact (IS the deliverable)

Throughout the grill, maintain a decision log at `grill-<topic-slug>.md` in the current working directory (use `.grill/<topic-slug>.md` if a `.grill/` directory exists). Each resolved question appends ONE entry to the log in the SAME turn that resolved it - never chat-only.

Entry shape (render as bullets inside an `## Q<n>` heading):

- **Dependencies**: Q<k> (resolved=… / pending=… / invariant=…)
- **Facts (tool-cited)**: list each fact with the tool + query/path that produced it
- **Edge cases**: enumerated list; for each, "what breaks if …"
- **External consultation**: <tool> - <link or query>
- **Decision**: the answer, in one or two lines
- **Rationale**: tied to cited facts, not vibes
- **Opened**: Q<n+1> …, Q<n+2> … (each with a one-line rationale for why it's now on the queue)

### Persistence mechanism (read-back discipline — load-bearing)

The decision log at `grill-<topic-slug>.md` (`use .grill/<topic-slug>.md` if a `.grill/` directory exists) is a rolling artifact. **Before the first write, load the shared `PERSISTENCE.md` (in this `skills/` directory) and follow the read-back discipline.** Composite operations for this skill:

- **Append a Q-entry** (Phase 2, every turn): old body verbatim, then the new `## Q<n>` block at the end.
- **Prepend the Phase 3 summary**: summary block directly under the Phase 0 header, then the entire existing body preserved unchanged below it — never write the summary alone.
- **Write the Phase 0 header / Phase 1 enumeration**: the full initial body in one write.

Tagline: "If it is not in the log file, it did not happen."

## Phase 0 - Orient

One turn. Write the log header; do NOT start asking questions yet.

- Orient: call `get_architecture` (if a project is indexed) or `read` CONTEXT.md / AGENTS.md / ADRs in the area you'll be grilling about.
- Restate the topic in one sentence: what is being grilled, and what does "done" mean (decision specification? plan? interface check?).
- Confirm the answerer's seat policy: you play both seats; user-stated constraints are invariants.
- Write the log header with the topic statement and the done-criterion, via the read-back discipline (`PERSISTENCE.md`).

## Phase 1 - Enumerate the decision tree

Cannot be skipped. Do NOT begin answering questions until enumeration is complete enough that you know the first several questions you'll ask. This phase itself may spread over multiple turns - one turn per major branch is fine.

In the log, enumerate:

- **Decisions** - every fork where a choice must be made (libraries, patterns, shapes, boundaries, persistence, error handling, ordering, concurrency). Filter via `search_graph` / `trace_path` against the project: anything the codebase already locked is a FACT (an invariant), not an open decision.
- **Concerns** - every risk (security, performance, correctness, migration, compatibility, UX, reversibility).
- **Questions** - every unknown that must be answered before the decision/spec is actionable.
- **Invariants** - constraints the user stated or the codebase already enforces. Use these to PRUNE the tree: invariant-resolved branches do NOT generate questions.

Mark each leaf OPEN (answer pending), INV (resolved by an invariant), or RES (resolved by an earlier turn). At end of Phase 1, publish the OPEN queue as a numbered list in the log via the read-back discipline (`PERSISTENCE.md`): append the enumeration under the header; do not overwrite it.

## Phase 2 - The grill loop (the engine)

Repeat, one iteration per turn, until the OPEN queue is empty.

Per turn, pop the next OPEN question and run the micro-cycle (1 → 9, in order):

1. **Restate** - frame this question in one paragraph. Cite any open dependency on a prior question. If a dependency is unresolved, queue this question and go resolve the dependency first; if a dependency is INV, cite the invariant and proceed.
2. **Gather facts** - cite tool evidence. Run these in parallel within the turn (parallel research is efficient fact-gathering, NOT batching decisions):
   - Codebase graph: `search_graph` (find symbols), `trace_path` (callers / callees / data flow), `get_code_snippet`, `search_code`, `query_graph` for multi-hop patterns, `get_architecture` for structure.
   - Repo files: `read` with offset/limit on relevant source/config; never open a file hoping.
   - Library/framework APIs: `mcp__context_resolve_library_id` → `mcp__context_query_docs`.
   - Other-repo behavior: `mcp__deepwiki_ask_question`.
   - External best practice / current behavior: `mcp__web_search`.
3. **Enumerate edge cases** - explicit list. For each: what input / concurrency / state / sequence / upgrade / failure breaks the answer? Treat the question as a hypothesis to BREAK, not a checklist to satisfy.
4. **External consultation** - at least ONE external source consulted per question; cite link or query string in the log. If the question is trivially-evident from step 2's facts, you MAY skip step 4 - but write the explicit skip rationale in the log and accept the risk.
5. **Open decisions** - if a sub-decision would normally go to the user, name it as an OPEN sub-question, queue it for a later turn, and pick the answer now with an explicit rationale tied to cited facts (not vibes). The rationale must reference specific tool evidence.
6. **Decide** - answer the question. If the answer is "we need to decide X first", split into two questions: queue X, take it next turn (NOT this one). One answer per turn.
7. **Log** - append the entry (shape above) to `grill-<topic-slug>.md` in THIS turn via the read-back discipline (`PERSISTENCE.md`). Never `write` the new block alone. Do not defer.
8. **Spawn** - list newly opened downstream Q's with a one-line rationale each; add them to the OPEN queue.
9. **End the turn** - do NOT proceed to the next question in the same turn. The next turn starts fresh with the popped question. This is the per-turn reasoning leverage. If you feel pulled to answer three questions in one turn, STOP - that is the canonical failure pattern.

## Phase 3 - Convergence

When the OPEN queue is empty AND every leaf answer is internally consistent:

- Prep-prepend a 5-10 line convergence summary at the top of the log (directly under the Phase 0 header, above the Q entries) via the read-back discipline (`PERSISTENCE.md`). The summary is the shared understanding; the Q entries below it stay intact.
- Yield the log path as the deliverable and state what the user can do with it next (plan, implement, file issues).

If you discover new OPEN questions while writing the summary, you have NOT converged - go back to Phase 2.

## Phase 4 - Handoff

The decision log is the deliverable. If the user asked you to follow through, name the downstream skill:

- Code design / module interface → `codebase-design`
- Explore multiple interface designs → `design-an-interface`
- Plan a refactor with tiny commits → `request-refactor-plan`
- Build test-first → `tdd`
- Implement → ask which; do NOT implement inline unless asked. This skill produces decisions, not code.

## Anti-patterns (do NOT)

- **Batching decisions** - answering multiple questions in one turn to "be efficient". This is the canonical failure; the skill collapses into a smaller-capability review. One question, one answer, one turn.
- **Writing the new block alone** - calling `write` with just the new Q-entry or just the summary self-destructs the log. Use the read-back discipline (`PERSISTENCE.md`); always read back.
- **Confusing fact with decision** - asserting library or codebase behavior from memory. Cite the doc, the code, or the graph query in the log entry.
- **Skipping edge case enumeration** - jumping to the recommended answer because the happy path is obvious. The edges are where this skill earns its keep.
- **Skipping external consultation** - "I know this". If you knew it, the source confirms it in 20 seconds.
- **Pre-computing downstream** - "if Q2 is X, then Q3 must be Y, so I'll answer both now". Do NOT. Q2's answer may surprise you and reshape Q3.
- **Asking the user back** - this is the autonomous variant. If you genuinely cannot proceed without the user, stop the grill and state what you need; do not silently relapse to interactive `grilling`.
- **Inlining decisions in chat only** - the log is the deliverable. If it is not in the log file, it did not happen.
- **Indefinite descent** - the decision tree is finite. If you find yourself 12 levels deep on a single leaf, you are grinding - converge or prune with a stated rationale.

## Completion checklist (publish in the final log entry)

- [ ] OPEN queue is empty.
- [ ] Every Phase 1 question has a log entry with cited facts and at least one external consultation (or an explicit skip rationale).
- [ ] Edge cases enumerated for every question.
- [ ] Decision log artifact exists on disk - `read` it and confirm body intact.
- [ ] Convergence summary prepended at the top of the log, existing Q entries preserved below it.
- [ ] Handoff skill (or "no follow-through requested") named.
