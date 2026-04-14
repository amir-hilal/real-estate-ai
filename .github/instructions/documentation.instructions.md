---
applyTo: "**/*.md"
---

# Documentation Instructions

These instructions govern all documentation in the project — including phase documents, ADRs, requirements, and status files.

---

## Documentation Philosophy

Documentation in this project is a first-class engineering artifact. It is not written after the fact. It is written before implementation as the plan, and maintained during implementation as the record.

**Documentation that does not match the current reality is worse than no documentation** — it creates false confidence and misleads future engineers (including future-you).

---

## Document Types and Their Purposes

| Type | Location | Purpose | When to update |
|------|---------|---------|----------------|
| Phase documents | `docs/phases/` | Define objectives, checklists, exit criteria for each implementation phase | Before starting a phase; when a decision changes |
| Requirements | `docs/context/requirements.md` | What must be built and why | When scope changes or a requirement is added/removed |
| Assumptions | `docs/context/assumptions-and-open-questions.md` | What is believed true and what is unknown | When an assumption is proven, disproven, or a new one emerges |
| ADRs | `docs/decisions/architecture-decision-records.md` | Why a technical decision was made | When any significant technical decision is made |
| Status | `docs/status/current-status.md` | Current phase, blockers, next actions | Every work session |
| Progress log | `docs/status/progress-log.md` | Historical record of what was done and learned | End of every work session |
| Future considerations | `docs/context/future-considerations.md` | Post-MVP features, clearly separated | When a post-MVP idea surfaces during planning or implementation |

---

## Documentation Quality Rules

### Be concrete, not generic
❌ "The system will handle errors properly."  
✅ "If the LLM returns invalid JSON, the API returns a 422 with `error_code: EXTRACTION_PARSE_FAILURE`."

### Distinguish required now vs. future later
Every document must make clear which items are in-scope for MVP and which are post-MVP. Use explicit labels: **Must (MVP)**, **Should (MVP)**, **Could (Post-MVP)**.

### Make tradeoffs explicit
When a decision is made, document what was not chosen and why. "We chose synchronous processing because async infrastructure (Celery) adds complexity that is not justified at MVP scale." Not just "we chose synchronous processing."

### Checklist items must be verifiable
❌ "Model performs well"  
✅ "Test-set MAE is documented and is lower than the baseline MAE by at least 30%"

### Keep status files current
The `docs/status/current-status.md` file must never be more than one work session out of date. An outdated status file is misleading.

---

## Writing Style

- Use professional engineering language
- Present tense for facts ("The system accepts..."), future tense for plans ("Phase 3 will produce...")
- Use numbered lists for ordered steps, bullet lists for unordered items
- Use tables for comparisons and structured data
- Do not use marketing language ("powerful", "seamless", "revolutionary")
- Do not use vague hedging ("might", "could potentially", "in some cases")
- Use specific numbers rather than qualitative descriptions where possible

---

## What Documentation Is Not

- Documentation is not a substitute for clear, named code
- Documentation is not a graveyard for every idea — speculative ideas belong in `assumptions-and-open-questions.md` or `future-considerations.md`, not in requirements or phase docs
- Documentation is not final — it evolves with the system
- A doc that was accurate 3 phases ago and has not been updated is misleading, not helpful

---

## ADR Writing Rules

When writing a new ADR:
1. State the context first — what situation forced this decision?
2. List the alternatives considered — even the obviously rejected ones
3. State the decision clearly and specifically
4. State the consequences and accepted tradeoffs
5. Use `Accepted` status for decided items; `Proposed` only if the decision is not yet made
6. Never delete a past ADR entry — mark it `Superseded by ADR-XXX` instead

---

## Phase Document Checklist Requirements

Each phase document checklist item must:
- Start with a concrete, observable action or output
- Be verifiable by someone other than the author
- Refer to a specific file, output, or test case where possible
- Not be ambiguous about what "done" means

The exit criteria section is the highest standard — these items are the gate between phases.
