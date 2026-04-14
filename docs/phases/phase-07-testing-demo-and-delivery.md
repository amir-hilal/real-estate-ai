# Phase 7: Testing, Demo, and Delivery

> **Status:** Not Started  
> **Depends on:** Phases 1–6 complete  
> **This is the final phase**

---

## Purpose

Phase 7 is not about writing new code. It is about confirming the system works end-to-end, preparing to present and explain it, and ensuring the project meets its definition of done.

The outputs of this phase are:
1. A confirmed, tested, and documented system
2. A demo script that you can execute from memory
3. The ability to answer any technical question about the system from first principles

---

## What Must Be Demonstrated

The demo must show the following sequence:

1. `docker-compose up` starts the system with no errors
2. `GET /health` returns `{ "status": "ok", "model_loaded": true }` (via browser or curl)
3. A realistic, full property description is submitted and returns a prediction + explanation
4. A minimal/incomplete property description is submitted, returns missing fields, and the full flow completes after supplemental input
5. An invalid or empty input returns a structured error response
6. The explanation is shown to a non-technical audience and is understandable

---

## Artifacts That Must Exist

Before the demo, confirm every artifact is present and usable:

| Artifact | Location | Checks |
|----------|----------|--------|
| EDA notebook | `ml/eda.ipynb` | Runs end-to-end without errors; EDA summary section present |
| ML training notebook | `ml/model_training.ipynb` | Runs end-to-end; metrics documented; leakage checklist complete |
| Serialized model | `ml/artifacts/model.pkl` | Loads successfully in fresh Python process |
| Training statistics | `ml/artifacts/training_stats.json` | Valid JSON; contains at minimum median, mean, std of SalePrice |
| Stage 1 prompt | `prompts/stage1_extraction_v1.md` | Present; readable; version number in header |
| Stage 2 prompt | `prompts/stage2_explanation_v1.md` | Present; readable; contains grounding instructions |
| Docker setup | `Dockerfile`, `docker-compose.yml` | `docker-compose up` works on clean pull |
| `.env.example` | Project root | Contains all required env variable names (no values) |
| README | `README.md` | Complete; phases listed; definition of done updated |
| Phase docs | `docs/phases/` | All phase checklist items and exit criteria filled in |
| ADR entries | `docs/decisions/architecture-decision-records.md` | All major decisions recorded |
| Master checklist | `docs/checklists/mvp-master-checklist.md` | Fully checked |
| Status doc | `docs/status/current-status.md` | Updated to reflect Phase 7 complete |

---

## Demo Checklist

Work through this checklist before any live demo:

### Setup
- [ ] `.env` file is in place with valid API key
- [ ] `docker-compose up` completes without errors
- [ ] `GET /health` returns 200
- [ ] Test all three demo inputs in Step 2 below — all pass

### Demo Inputs (prepare these in advance)

**Input 1 — Happy path (complete description):**
> "3-bedroom, 2-bathroom house in Northridge Heights, Ames. Built in 2001. Above-grade living area about 1,900 sq ft. Attached 2-car garage. Finished basement with 900 sq ft. Forced air heating, central air. Overall good condition."

Expected: Full prediction with explanation, no missing fields

**Input 2 — Partial description (triggers missing fields):**
> "2-bedroom house, older, in west Ames. Small backyard."

Expected: Partial extraction, several missing required fields, missing fields form displayed

**Input 3 — Invalid input:**
> "hello"

Expected: Structured error response, not a crash

### Demo Flow
- [ ] Submit Input 1 → confirm prediction + explanation displayed correctly
- [ ] Submit Input 2 → confirm missing fields form rendered → fill in fields → confirm prediction received
- [ ] Submit Input 3 → confirm structured error message displayed
- [ ] Show the extracted features panel for Input 1
- [ ] Show the EDA notebook and identify the most predictive features
- [ ] Show the training metrics from the ML notebook
- [ ] Show the Stage 1 prompt file and explain its structure

---

## Presentation Checklist

If presenting to a technical or non-technical audience:

- [ ] You can draw the system architecture from memory on a whiteboard
- [ ] You can explain what each component does without looking at code
- [ ] You can explain why Stage 1 validation is necessary
- [ ] You can explain what data leakage is and how you prevented it
- [ ] You can show and explain the model evaluation metrics
- [ ] You can explain why certain features are "required" vs "optional"
- [ ] You can explain what the training statistics file is and why it exists
- [ ] You can explain why the explanation is grounded rather than hallucinated
- [ ] You can describe one specific decision you would make differently in a second iteration

---

## Review Questions You Must Be Able to Answer

These are questions a reviewer might ask. If you cannot answer any of these, do not consider Phase 7 complete.

### About the ML Pipeline
1. What is your MAE on the test set, and what does that mean in plain English?
2. What is your baseline MAE, and how much does your model improve on it?
3. What is data leakage, and specifically which steps in your pipeline could introduce it?
4. Why did you choose this model over the alternatives you considered?
5. What does your preprocessing pipeline do, in order?
6. If you received a new property description with a feature value your model never saw during training (e.g., a new neighborhood), what would happen?

### About the LLM Pipeline
7. What happens if the LLM returns invalid JSON?
8. What prevents the Stage 2 LLM from making up statistics?
9. What does your Stage 1 prompt instruct the LLM to do when it can't infer a feature?
10. How is prompt version 1 different from a hypothetical version 2 you might write?

### About the Architecture
11. Why is the pipeline synchronous? What would async processing require?
12. Why is there no authentication in MVP?
13. What is in the Docker container, and why?
14. If this were going to production with 100 concurrent users, what would you change first?

### About the Project Process
15. Which assumption from `docs/context/assumptions-and-open-questions.md` turned out to be wrong?
16. What would you do differently if starting over?
17. What is the most important thing you learned from Phase 1 EDA?

---

## Exit Criteria (Project Complete)

The project is done when ALL of the following are true:

1. [ ] All demo steps run successfully in a live environment
2. [ ] All artifacts in the artifact table above are present and verified
3. [ ] The master checklist in `docs/checklists/mvp-master-checklist.md` is 100% checked
4. [ ] Every review question above can be answered from memory
5. [ ] `docs/status/current-status.md` is updated to reflect completion
6. [ ] `docs/status/progress-log.md` has a final entry summarizing the project

---

*Knowing the system well enough to explain it is the real definition of done.*
