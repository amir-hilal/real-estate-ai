# Project Overview

> **Skill type:** Project context  
> **Scope:** Entire project  
> **Use when:** You need a concise summary of what this project is, what it does, and what its goals are.

---

## What This Project Is

A learning-first AI Real Estate Agent pipeline. The system accepts a plain-English property description and outputs:
1. A validated set of extracted property features (via LLM)
2. A predicted sale price (via ML model trained on Ames Housing)
3. A grounded plain-English explanation of the prediction (via second LLM call)

---

## What This Project Is Not

- Not a production real estate platform
- Not a live property search system
- Not a generative AI assistant for buying/selling advice
- Not a system trained on current market data (uses Ames Housing 2006–2010)

---

## The Four Processing Stages

| Stage | Name | Input | Output |
|-------|------|-------|--------|
| 1 | LLM Extraction | Free-text description | Validated `PropertyFeatures` (possibly partial) |
| 1.5 | UI Missing-Field Collection | Partial features + missing fields list | Fully populated features |
| 2 | ML Prediction | Complete `PropertyFeatures` | Predicted price in USD |
| 3 | LLM Explanation | Features + price + training stats | 2–4 paragraph explanation |

---

## Technology Stack (MVP)

| Component | Technology |
|-----------|-----------|
| API framework | FastAPI (Python) |
| ML framework | scikit-learn (+ XGBoost or LightGBM) |
| LLM | OpenAI GPT-4o (or equivalent via API) |
| Schema validation | Pydantic v2 |
| Containerization | Docker + docker-compose |
| Training dataset | Ames Housing (Kaggle / OpenML) |
| Prompt storage | Versioned `.md` files in `prompts/` |

---

## Current State

- **Phase 0 (Planning):** Complete
- **Phase 1 (EDA):** Not started
- **All other phases:** Not started

Check `docs/status/current-status.md` for current blockers and next actions.

---

## Primary Learning Goals

1. Understand end-to-end ML pipeline design with real data
2. Understand structured LLM output extraction and validation
3. Understand how to ground LLM explanations in data
4. Understand FastAPI service design for ML + LLM systems
5. Understand Docker-based deployment of multi-component AI systems
6. Practice documentation-first, disciplined engineering

---

## Key Project Documents

- Full overview: `README.md`
- Engineering description: `docs/context/project-brief.md`
- Requirements: `docs/context/requirements.md`
- Phase plans: `docs/phases/`
- Decision log: `docs/decisions/architecture-decision-records.md`
- Current status: `docs/status/current-status.md`
