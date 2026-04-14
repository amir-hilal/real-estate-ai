# MVP Scope

> **Skill type:** Scope boundaries  
> **Scope:** All phases  
> **Use when:** You need to decide whether something is in or out of scope for MVP.

---

## The MVP Test

Before adding any feature, technology, or layer, ask:
> "Does the MVP fail to work correctly without this?"

If the answer is "no" or "it depends" — it's probably post-MVP. If the answer is "yes, without this the pipeline cannot function as specified" — it belongs in scope.

---

## What Is In Scope for MVP

| Component | Status |
|-----------|--------|
| Plain-English property description input | Required |
| LLM-based feature extraction (Stage 1) | Required |
| Pydantic schema validation of extracted features | Required |
| Missing required field detection and surfacing | Required |
| UI form for collecting missing fields | Required |
| ML regression model (Ames Housing) | Required |
| Serialized preprocessing + model pipeline | Required |
| Training statistics file (for grounding) | Required |
| LLM-based prediction explanation (Stage 2) | Required |
| FastAPI API with `/health`, `/extract`, `/predict` | Required |
| Docker + docker-compose deployment | Required |
| Form-based web UI | Required |
| Structured error responses for all failure modes | Required |
| Versioned prompt files in `prompts/` | Required |
| Leakage-free ML evaluation | Required |

---

## What Is Explicitly Out of Scope for MVP

| Feature | Reason | Reference |
|---------|--------|-----------|
| Authentication / JWT / OAuth | No external users | ADR-003 |
| Celery + Redis (async task queue) | Sync is acceptable for MVP latency | ADR-002 |
| Database / ORM (SQLAlchemy, etc.) | No persistence required | ADR-003 |
| S3 or object storage | Local filesystem is sufficient | future-considerations.md |
| Role separation (agent vs. customer) | No auth to support it | future-considerations.md |
| Chat-based conversational UI | Form UI is sufficient and faster to build | ADR-004 |
| Experiment tracking (MLflow, W&B) | One model, one run — notebook is sufficient | future-considerations.md |
| Fine-tuning the LLM | Prompt engineering is adequate | future-considerations.md |
| Continuous retraining | Static dataset; no new data pipeline | future-considerations.md |
| API key management (Vault, Secrets Manager) | Local `.env` is sufficient for MVP | future-considerations.md |
| Kubernetes / Helm | docker-compose is sufficient | future-considerations.md |
| Multi-user support | One developer/demo user | ADR-003 |
| Real MLS data integration | Ames dataset is sufficient for learning | ADR-005 |

---

## The Scope Creep Warning Signs

If you find yourself doing any of the following, stop and check the scope:

1. "Let me add a users table while I'm setting up the database"
2. "I should make this async with Celery so it scales better"
3. "A chat UI would be much cooler than a form"
4. "Let me add an S3 bucket for model storage"
5. "I should track experiments in MLflow"
6. "I'll add authentication just in case"

All of these are legitimate ideas. None of them are MVP requirements. Put them in `docs/context/future-considerations.md` and continue.

---

## The Signal to Expand Scope

It is appropriate to revisit the scope when:
- A specific named problem arises that the excluded feature would solve
- The MVP is demonstrated, working, and validated
- A new stakeholder requirement is formally added

"It would be nice" is never sufficient justification. "We have X specific problem that Y would solve, and we have confirmed Y is the right solution" is sufficient.
