# AI Real Estate Agent

> A learning-first, documentation-driven ML + LLM pipeline project.  
> Every decision is explainable. Every line of code will be understood before it is written.

---

## Problem Statement

Estimating property value is a meaningful, high-complexity problem. It requires structured feature extraction, machine learning, and natural-language explanation — all of which expose real-world engineering challenges.

A user should be able to describe a property in plain English and receive:
1. A structured extraction of relevant features from their description
2. A predicted sale price from a trained ML model
3. A context-aware, human-readable explanation of that prediction

This project builds that pipeline end-to-end.

---

## Learning Goals

This project is explicitly designed for deep understanding. The goals are:

- Understand how an LLM can extract structured, validated data from free text
- Understand how to train, evaluate, and prevent leakage in an ML regression pipeline
- Understand how a second LLM call can produce grounded, data-informed explanations
- Understand how to serve ML and LLM components together through a REST API
- Understand how to containerize a multi-component AI system
- Build the discipline to document and plan before writing code
- Understand every tradeoff made — not just the outcome

---

## Project Scope

**In scope for MVP:**

- Stage 1: LLM-based property feature extraction from plain-English text input
- Feature validation and schema enforcement using Pydantic
- Stage 2: ML model training on the Ames Housing dataset
- Stage 3: Price prediction using extracted features
- Stage 4: LLM-based prediction explanation using summary statistics from training data
- FastAPI backend serving the full pipeline
- Docker-based containerization
- Simple form-based frontend UI (or curl-testable API)

**Not in scope for MVP (see `docs/context/future-considerations.md` for details):**

- Authentication or role-based access control
- Async/background task processing (Celery, Redis)
- Object storage (S3, MinIO)
- Multi-user or multi-agent architectures
- Real-time property search or integrations
- A/B testing of prompts or models
- Fine-tuning of the LLM
- Production SLA or scalability guarantees

---

## High-Level Architecture

```
User Input (plain English description)
        │
        ▼
┌─────────────────────────────┐
│  Stage 1: LLM Extraction    │  ← Structured property schema + validation
│  (prompt + Pydantic schema) │
└────────────┬────────────────┘
             │ Validated feature set
             ▼
  Missing required fields?
     ├─ Yes → UI prompts user to fill gaps manually
     └─ No  ▼
┌─────────────────────────────┐
│  Stage 2: ML Prediction     │  ← Trained regression model (Ames Housing)
│  (scikit-learn pipeline)    │
└────────────┬────────────────┘
             │ Predicted price + model confidence signal
             ▼
┌─────────────────────────────┐
│  Stage 3: LLM Explanation   │  ← Human-readable, grounded in data context
│  (prompt + stats context)   │
└────────────┬────────────────┘
             │
             ▼
        Final Response
  (prediction + explanation)
```

All stages are served synchronously through a single FastAPI endpoint.

---

## Execution Philosophy

> **Understand every line. Avoid premature complexity. Plan before building.**

This project follows a strict execution order:

1. Document first — understand the system before writing a single line of code
2. Explore the data (EDA) before choosing a model
3. Design the ML pipeline before building it
4. Design the LLM prompts before implementing them
5. Build the simplest thing that works for MVP
6. Add complexity only when a specific, named problem requires it

**Anti-patterns actively avoided:**
- Copying code without understanding it
- Adding infrastructure before it is justified
- Silently ignoring missing fields or errors
- Treating ML preprocessing as an afterthought
- Assuming prompt outputs are always well-formed

---

## Project Phases Overview

| Phase | Name | Summary |
|-------|------|---------|
| 0 | Planning & Documentation | This phase. All planning, decisions, context, and skills. |
| 1 | Discovery & EDA | Understand the Ames Housing dataset deeply before modeling |
| 2 | ML Foundation | Train, validate, and serialize a regression model |
| 3 | LLM Extraction Design | Design and test Stage 1 prompt + schema validation |
| 4 | Prediction Interpretation | Design and test Stage 2 explanation prompt |
| 5 | API & Containerization | FastAPI endpoints, Docker, model loading, integration tests |
| 6 | UI Flow | Simple frontend or form-based input/output |
| 7 | Testing, Demo & Delivery | End-to-end validation, demo script, final review |

See `docs/phases/` for detailed plans for each phase.

---

## Definition of Done for MVP

The MVP is complete when all of the following are true:

- [ ] A user can submit a plain-English property description and receive a price prediction and explanation
- [ ] All required features for prediction are either extracted from text or collected via UI fallback
- [ ] Feature extraction is validated against a typed Pydantic schema
- [ ] The ML model has been evaluated on a held-out test set with documented metrics
- [ ] No data leakage has been committed in the ML pipeline (confirmed by checklist)
- [ ] The explanation references the predicted price and at least two relevant data statistics
- [ ] The API is served by FastAPI and tested with at least three real property descriptions
- [ ] The full system runs in Docker
- [ ] All EDA findings are documented in `docs/phases/phase-01-discovery-and-eda.md`
- [ ] All major decisions have ADR entries in `docs/decisions/architecture-decision-records.md`
- [ ] The master checklist in `docs/checklists/mvp-master-checklist.md` is fully checked

---

## Repository Structure (Documentation Phase)

```
real-estate-ai/
├── README.md                          ← This file
├── docs/
│   ├── roadmap.md                     ← Phased execution roadmap
│   ├── context/
│   │   ├── project-brief.md           ← Engineering-language project description
│   │   ├── requirements.md            ← Functional + non-functional requirements
│   │   ├── assumptions-and-open-questions.md
│   │   └── future-considerations.md   ← Post-MVP scope separation
│   ├── phases/
│   │   ├── phase-01-discovery-and-eda.md
│   │   ├── phase-02-ml-foundation.md
│   │   ├── phase-03-llm-extraction-design.md
│   │   ├── phase-04-prediction-interpretation.md
│   │   ├── phase-05-api-and-containerization.md
│   │   ├── phase-06-ui-flow.md
│   │   └── phase-07-testing-demo-and-delivery.md
│   ├── decisions/
│   │   └── architecture-decision-records.md
│   ├── checklists/
│   │   └── mvp-master-checklist.md
│   └── status/
│       ├── current-status.md
│       └── progress-log.md
├── .github/
│   └── instructions/
│       ├── project.instructions.md
│       ├── architecture.instructions.md
│       ├── documentation.instructions.md
│       ├── ml.instructions.md
│       └── llm.instructions.md
├── .copilot/
│   └── skills/
│       ├── project-overview.md
│       ├── mvp-scope.md
│       ├── phase-execution.md
│       ├── common-mistakes.md
│       └── future-architecture-notes.md
└── ml/                                ← ML experimentation notebooks (populated in Phase 1)
```

---

## Getting Started

This is a planning-phase README. No code exists yet.

To understand the project before any implementation:
1. Read `docs/context/project-brief.md` — the engineering description of the system
2. Read `docs/context/requirements.md` — what must be built and why
3. Read `docs/phases/phase-01-discovery-and-eda.md` — where to begin
4. Review `docs/checklists/mvp-master-checklist.md` — what done looks like
5. Check `docs/status/current-status.md` — what state the project is in right now

---

*Last updated: Phase 0 — Documentation & Planning*
