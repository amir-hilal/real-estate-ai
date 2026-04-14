# Phase Execution Guide

> **Skill type:** Process discipline  
> **Scope:** All phases  
> **Use when:** Starting or working through any phase of the project.

---

## The Core Execution Rule

**A phase is not started until its prerequisites are met.**  
**A phase is not complete until all its exit criteria are checked.**

Shortcuts between phases are how projects accumulate hidden debt. A model trained without understanding the data (skipping Phase 1) will require a full retraining cycle when EDA reveals problems. A prompt designed before the schema is locked (skipping Phase 2) will require redesign. The phase sequence is not bureaucracy — it is dependency management.

---

## How to Start a Phase

1. Open the phase document: `docs/phases/phase-0X-[name].md`
2. Confirm the "Depends on" section — all listed prerequisites must be complete
3. Review the objectives — understand what the phase is trying to achieve
4. Read the "Mistakes to Avoid" section — these are documented from prior experience
5. Check the unanswered questions in `docs/context/assumptions-and-open-questions.md` — any that affect this phase must be resolved first (or explicitly deferred with justification)
6. Update `docs/status/current-status.md`: set the current phase and status to "In Progress"
7. Begin the checklist from the top

---

## How to Complete a Phase

1. Work through every checklist item in the phase document
2. For each item, verify it passes its stated completion criterion — not just "seems done"
3. Run through the exit criteria section — every item must be checked
4. Update all resolved unknowns in `docs/context/assumptions-and-open-questions.md`
5. Add an ADR entry if any significant decision was made during this phase
6. Add a progress log entry to `docs/status/progress-log.md`
7. Update `docs/status/current-status.md` with current state and next actions

---

## Phase-Specific Guidance

### Phase 1 (EDA)
- Do not skip any section of the phase checklist
- Read the Ames data dictionary before writing any code
- The EDA summary section in the notebook is a deliverable, not a formality
- The most important output is a documented decision on: log-transform, outliers, feature shortlist, and imputation strategies

### Phase 2 (ML Foundation)
- Run through the leakage checklist before reporting any metrics
- Build and record the baseline before the "real" model
- Feature importance analysis is required — it feeds Phase 4 prompt design
- The model is not done until it loads cleanly from disk in a fresh process

### Phase 3 (LLM Extraction)
- The schema must be locked before the prompt is finalized
- Test with all 10 planned test queries, not just happy-path ones
- Null handling and failure mode paths must be explicitly tested, not assumed

### Phase 4 (LLM Explanation)
- Read the training statistics file before writing the prompt
- Manually verify at least 5 explanations against the injected statistics — no hallucinated numbers
- The fallback (explanation unavailable, prediction still returned) must be tested

### Phase 5 (API)
- All 6 integration tests must pass before the phase is complete
- Model loading must happen in `lifespan`, not in route handlers
- All secrets via environment variables — this is tested by checking that the `.env.example` file exists and that the real `.env` is in `.gitignore`

### Phase 6 (UI)
- Test all documented error states, not just the happy path
- The UI must work inside Docker — not just locally

### Phase 7 (Demo)
- Practice the demo at least once before treating it as complete
- Answer all review questions from memory, not by reading docs during the answer

---

## When a Phase Cannot Be Completed

If you reach a point in a phase where you cannot proceed:

1. Document the blocker in `docs/status/current-status.md` under "Active Blockers"
2. If the blocker is a data issue (unexpected EDA finding), re-examine whether earlier assumptions need to be updated in `docs/context/assumptions-and-open-questions.md`
3. If the blocker requires a new technical decision, create an ADR entry — even if the decision is "we are changing approach X to Y"
4. Do not implement a workaround without documenting it — silent workarounds become invisible tech debt

---

## What Good Phase Execution Looks Like

By the end of a phase, someone else (or future-you) should be able to:
- Read the phase document and understand exactly what was done and why
- Look at the outputs and confirm they match the exit criteria
- Understand every decision made during the phase without asking you
- Reproduce the phase's output independently from the documented process
