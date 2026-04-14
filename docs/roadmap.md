# Project Execution Roadmap

> **Purpose:** A single-view summary of all phases, their goals, outputs, and completion signals.  
> **Rule:** Do not start a phase before its dependencies are met — this is enforced by the phase documents.

---

## Phased Roadmap Table

| Phase | Name | Goal | Main Outputs | Dependencies | Completion Signal |
|-------|------|------|-------------|-------------|-------------------|
| **0** | Planning & Documentation | Define every decision before writing code. Establish project context, requirements, and execution guardrails. | README, phase docs, requirements, assumptions, ADRs, instructions, skills, status docs, roadmap | None | All planning documents created; master checklist Phase 0 section fully checked |
| **1** | Discovery & EDA | Understand the Ames dataset deeply. Make feature, imputation, and target-transform decisions based on evidence. | EDA notebook (`ml/eda.ipynb`), feature shortlist, resolved assumptions U-01 through U-10 | Phase 0 complete; dataset downloaded; data dictionary read | All Phase 1 exit criteria met; unknowns U-01 to U-10 resolved and documented |
| **2** | ML Foundation | Train an evaluated, leak-free regression model. Serialize the full preprocessing + model pipeline. | Trained model (`ml/artifacts/model.joblib`), training statistics (`ml/artifacts/training_stats.json`), ML training notebook | Phase 1 complete; feature shortlist locked | Leakage checklist complete; test-set metrics documented; model loads from disk cleanly |
| **3** | LLM Extraction Design | Design and validate the extraction prompt + Pydantic schema + validation chain. | `PropertyFeatures` schema, extraction prompt (`prompts/extraction_v1.md`), test query results | Phase 2 complete; feature schema locked; LLM API key configured | 10 test queries documented; T01 passes ≥8 fields; failure modes all handled |
| **4** | Prediction Interpretation | Design and validate the explanation prompt using grounded training statistics. | Explanation prompt (`prompts/explanation_v1.md`), 5 evaluation scenarios documented | Phase 2 (stats file), Phase 3 (extraction working) | 4/5 evaluation scenarios pass checklist; no hallucinated statistics confirmed |
| **5** | API & Containerization | Assemble all components into a testable FastAPI service running in Docker. | FastAPI app, `Dockerfile`, `docker-compose.yml`, 6 integration tests passing | Phases 2, 3, and 4 complete | `docker-compose up` works; all integration tests pass; `GET /health` returns OK |
| **6** | UI Flow | Add a form-based browser interface that covers the full interaction flow including missing-field collection. | HTML/template UI served by the API; all documented error states tested | Phase 5 complete | Full end-to-end flow works in a browser; all UI error states confirmed |
| **7** | Testing, Demo & Delivery | Confirm the system is complete, demo-ready, and fully explainable. | Demo script, final status update, all artifacts verified, review questions answerable | Phase 6 complete | Master checklist 100% checked; all review questions answered from memory |

---

## Dependency Graph

```
Phase 0 (Planning)
    │
    ▼
Phase 1 (EDA)
    │
    ▼
Phase 2 (ML Foundation) ──────────────────────────────────────────┐
    │                                                              │
    ▼                                                              │
Phase 3 (LLM Extraction) ─────────────────────────────────────┐  │
    │                                                           │  │
    ├──────────────────────────────────────────────────────┐   │  │
    │                                                       │   │  │
    ▼                                                       ▼   ▼  ▼
Phase 4 (Prediction Interpretation)              Phase 5 (API & Docker)
    │                                                       │
    └───────────────────────────────────────────────────────┘
                                                            │
                                                            ▼
                                                    Phase 6 (UI Flow)
                                                            │
                                                            ▼
                                                    Phase 7 (Demo & Delivery)
```

**Note:** Phases 3 and 4 can be designed in parallel after Phase 2 is complete, but both must be complete before Phase 5 integration.

---

## Phase Duration Estimates

> These are rough estimates for a solo developer learning as they go. They are not commitments.

| Phase | Estimated Effort |
|-------|-----------------|
| Phase 0 | 1 day (completed) |
| Phase 1 | 2–4 days (EDA is thorough, not rushed) |
| Phase 2 | 3–5 days (first model + documentation) |
| Phase 3 | 2–3 days (prompt design + 10 test cases) |
| Phase 4 | 1–2 days (dependent on Phase 2 stats) |
| Phase 5 | 3–4 days (API + Docker + integration tests) |
| Phase 6 | 2–3 days (UI implementation) |
| Phase 7 | 1 day (demo preparation + final check) |
| **Total** | **~15–22 working days** |

---

## What Should Stay Flexible After EDA

The following decisions are intentionally deferred until Phase 1 EDA provides evidence:

| Decision | Deferred Until | Risk of Deciding Now |
|----------|---------------|---------------------|
| Final feature list for schema | After Phase 1 | Wrong features = wrong schema = ML pipeline redone |
| Log-transform of `SalePrice` | After Phase 1 histogram | Premature decision = evaluation metrics are not comparable |
| Required vs. optional feature classification | After Phase 1 feature importances | Misclassification = either too many UI prompts or bad model input |
| Imputation strategy per feature | After Phase 1 missing value analysis | Incorrect imputation = data quality issues in training |
| Model architecture choice | After Phase 2 baseline | Choosing XGBoost before seeing if Ridge suffices = unnecessary complexity |
| Prompt structure for Stage 1 | After schema is locked | Schema changes = prompt redesign |
| Training statistics file format | After Phase 2 confirms required stats | Stage 2 prompt cannot be finalized without knowing what stats are available |

---

## Recommended Order of Document Creation (Already Executed)

For reference, this was the optimal order for creating documentation:

1. `README.md` — anchors the entire project
2. `docs/context/project-brief.md` — engineering description before requirements
3. `docs/context/requirements.md` — functional constraints before phase design
4. `docs/context/assumptions-and-open-questions.md` — surfaces unknowns before phases are planned
5. Phase documents (in order 1 through 7) — each building on the previous
6. `docs/decisions/architecture-decision-records.md` — records decisions made during planning
7. `docs/checklists/mvp-master-checklist.md` — constructed last so it reflects all prior docs
8. `docs/status/` files — reflect current state after all planning is done
9. `docs/context/future-considerations.md` — written last so scope creep pressure is already felt
10. Instruction and skills files — written after all context is established

---

*The roadmap is a plan, not a contract. Update it when reality diverges, but do not use flexibility as an excuse to skip phases.*
