---
applyTo: "**"
---

# Project Instructions: AI Real Estate Agent

These instructions apply to all files in this project. They define the project context, constraints, and non-negotiable rules that must be respected during all code generation and documentation tasks.

---

## Project Identity

This is an AI Real Estate Agent project. It is a learning-first, documentation-driven ML + LLM pipeline project. The primary goal is deep understanding of every component — not shipping fast.

**System overview:**
1. User submits a plain-English property description
2. Stage 1 LLM extracts structured property features (validated by Pydantic)
3. Missing required features are collected via the UI
4. Stage 2 ML model predicts sale price from validated features
5. Stage 3 LLM generates a grounded plain-English explanation of the prediction
6. FastAPI serves the pipeline; Docker containerizes it
7. Dataset: Ames Housing

---

## Non-Negotiable Project Constraints

**Never violate these:**

1. **No code before planning.** Each phase must have its documentation and exit criteria reviewed before implementation begins.
2. **No silent defaults.** Missing required features must be surfaced explicitly. Never substitute a default value without documenting the decision.
3. **No data leakage.** All preprocessing statistics must be computed on training data only. The leakage prevention checklist in `docs/phases/phase-02-ml-foundation.md` is the authority.
4. **No hardcoded secrets.** LLM API keys and paths are always passed via environment variables.
5. **No prompts as strings in code.** All LLM prompts are stored as versioned files in `prompts/`.
6. **No unexplained decisions.** Every non-trivial implementation choice must have a written rationale (in comments, ADRs, or phase docs).
7. **No premature infrastructure.** Do not add Celery, Redis, auth, or database layers unless a specific named problem requires them. See `docs/context/future-considerations.md`.
8. **No unhandled errors.** Every failure mode must return a structured error response. Crashes are not acceptable.

---

## Current Phase

**Phase 0 — Planning and Documentation** is complete.  
**Phase 1 — Discovery and EDA** is the active phase.

Check `docs/status/current-status.md` for the current state before generating any code.

---

## Key Files to Reference Before Generating Code

- `docs/context/project-brief.md` — what the system does
- `docs/context/requirements.md` — what must be built
- `docs/context/assumptions-and-open-questions.md` — what is still unknown
- `docs/phases/phase-0X-*.md` — active phase plan and checklist
- `docs/decisions/architecture-decision-records.md` — past decisions and their rationale

---

## Documentation Before Implementation Rule

For any phase not yet complete, generated code suggestions must be preceded by:
1. A review of the phase document
2. Confirmation that the phase's pre-conditions (from its "Depends on" section) are met
3. A note if any open questions from `docs/context/assumptions-and-open-questions.md` remain unresolved and affect the suggested code

---

## Scope Enforcement

**Do not generate code for:**
- Authentication or JWT tokens (post-MVP per ADR-003)
- Celery, Redis, or task queues (post-MVP per ADR-002)
- S3 or object storage (post-MVP per `docs/context/future-considerations.md`)
- Database layers or ORM models (not required for MVP)
- Multi-user or multi-agent features
- Frontend beyond a simple form-based UI

If any of the above is requested, explain why it is post-MVP and suggest the minimal alternative that serves the actual need.
