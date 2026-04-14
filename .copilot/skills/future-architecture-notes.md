# Future Architecture Notes

> **Skill type:** Future scope guardrail  
> **Scope:** Entire project  
> **Use when:** An idea surfaces that is clearly legitimate but belongs after MVP.

---

## Purpose of This Skill

Ideas for improving the system will arise during every phase. Some of them are genuinely good ideas — but they are good ideas for a system that is already working, not for a system that is still being built.

This skill is a reference for knowing where future ideas are catalogued and how to evaluate whether the time to act on them has come.

---

## Where Future Ideas Are Documented

All post-MVP features are documented with full rationale in:  
**`docs/context/future-considerations.md`**

That file includes:
- What each future feature is
- Why it was excluded from MVP
- What specific signal would justify adding it

Do not add future features to `docs/context/requirements.md`, `docs/phases/`, or any implementation plan. They belong only in `future-considerations.md` and this skill file.

---

## Quick Reference: Future Features and Their Triggers

| Feature | Add it when... |
|---------|----------------|
| **Celery + Redis (async tasks)** | Latency > 10s routinely, or concurrent users require it |
| **S3 / object storage** | Model artifact needs versioning across multiple instances |
| **Keycloak / auth** | Real external users, or sensitive data is collected |
| **Agent vs. customer roles** | Auth is in place AND role-specific features are requested |
| **Event-driven messaging** | Pipeline needs fan-out to multiple consumers |
| **LLM fine-tuning** | >10% extraction error rate on production traffic, labeled data available |
| **MLflow / W&B** | >3 meaningful model variants being compared, team collaboration |
| **Microservices** | Stages need independent scaling, teams own different components |
| **Continuous retraining** | Live labeled data pipeline exists, concept drift measured |
| **Chat UI** | Form-based flow confirmed inadequate via user testing, missing-field rate is high |

---

## How to Respond When a Future Feature Is Requested

If during development a request surfaces for any of the above features, the response is:

1. **Acknowledge it's a good idea** — don't dismiss it
2. **Name the trigger criteria** — "That's the right idea for when [trigger condition]"
3. **Confirm the trigger isn't here yet** — "Right now, we have [one user / static dataset / MVP scope]"
4. **Confirm it's documented** — "It's in `docs/context/future-considerations.md` with the exact signal we'd need to add it"
5. **Return to the current phase**

This is not refusing to think about the future. It is protecting the current phase from scope expansion that would slow or block completion of the MVP.

---

## The Anti-Pattern This Skill Prevents

The most common failure mode in projects with future-thinking ambition:

> Phase 2 is in progress. While setting up the ML model, the engineer realizes "we'll eventually need Celery for async." They add a Celery dependency, configure Redis, add task decorators, and spend 3 days on that before returning to the actual ML problem.  
>
> When Phase 4 arrives, the Celery setup is half-working, the ML model is half-documented, and the team has no clear picture of what the current state of the system is.

The MVP exists to prevent this. Ship the working synchronous system. Then, if you have real users experiencing real latency problems, add async processing. Not before.

---

## Legitimate Reasons to Revisit This Skill

- You are in Phase 7 and the MVP is complete and working
- A specific user or stakeholder has named a specific problem that a future feature solves
- A new phase is being planned for v2.0 of the system
- You are writing a post-MVP architecture document

Any of those is a valid trigger for engaging seriously with post-MVP architecture. "It would be interesting" is not.
