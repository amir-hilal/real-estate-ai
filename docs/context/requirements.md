# Requirements: AI Real Estate Agent

> **Status:** Draft — Phase 0 (Planning)  
> **Last reviewed:** April 2026  
> **Review trigger:** Revisit after Phase 1 EDA and before any implementation begins

---

## How to Read This Document

Requirements are organized by concern area. Each requirement has:
- A unique ID (for tracing in ADRs and checklists)
- A priority: **Must (MVP)**, **Should (MVP)**, **Could (Post-MVP)**
- Plain-language rationale

A requirement without a clear rationale should not exist.

---

## 1. Functional Requirements

### FR-01 — Plain-English Property Input
**Priority:** Must (MVP)  
The system must accept a free-text English description of a residential property as input.  
*Rationale: This is the entry point of the pipeline. Without unstructured text input, Stage 1 LLM has nothing to process.*

### FR-02 — Structured Feature Extraction
**Priority:** Must (MVP)  
The system must use an LLM to extract a defined set of property features from the input text and return them as a structured, typed object conforming to the `PropertyFeatures` schema.  
*Rationale: The ML model requires structured numeric and categorical features. The LLM bridges natural language and structured input.*

### FR-03 — Feature Schema Validation
**Priority:** Must (MVP)  
All extracted features must be validated against the `PropertyFeatures` Pydantic schema before any downstream processing. Invalid types, out-of-range values, or missing required fields must be caught at this validation boundary.  
*Rationale: Silent garbage-in/garbage-out is the most common failure mode. Validation is not optional.*

### FR-04 — Missing-Field Identification
**Priority:** Must (MVP)  
After extraction, the system must identify which required features are absent (null or missing) and return them as a structured list of missing fields.  
*Rationale: The ML model cannot produce a valid prediction from incomplete data. Missing fields must be explicitly surfaced, not silently defaulted.*

### FR-05 — Missing-Field Collection (UI Fallback)
**Priority:** Must (MVP)  
When required features are missing, the frontend must display appropriate input controls for each missing field. The user must be able to fill those values and resubmit.  
*Rationale: This closes the gap between open-ended user input and the strict requirements of the ML model.*

### FR-06 — Price Prediction
**Priority:** Must (MVP)  
The system must run the validated feature set through the trained and serialized regression model and return a numeric USD price prediction.  
*Rationale: This is the core ML deliverable.*

### FR-07 — Prediction Explanation
**Priority:** Must (MVP)  
The system must use a second LLM call to generate a 2–4 paragraph natural-language explanation of the prediction. The explanation must reference the predicted price, at least two statistical comparisons from training data, and the primary contributing features.  
*Rationale: A number alone is not useful or trustworthy. Context makes the prediction actionable.*

### FR-08 — Training Statistics Context
**Priority:** Must (MVP)  
The system must compute and persist summary statistics from the training dataset (median price, price distributions by neighborhood, per-sqft statistics, etc.) and inject them into the Stage 2 explanation prompt.  
*Rationale: Without grounding data, the LLM will hallucinate statistics. The explanation must come from real numbers.*

### FR-09 — Combined API Response
**Priority:** Must (MVP)  
The final API response must include: extracted features, predicted price, and the plain-English explanation in a single structured response object.  
*Rationale: The frontend needs all three components together to render the complete result.*

---

## 2. Non-Functional Requirements

### NFR-01 — Synchronous Request Processing
**Priority:** Must (MVP)  
All pipeline stages (extraction → validation → prediction → explanation) must execute synchronously within a single HTTP request/response cycle.  
*Rationale: Async infrastructure (Celery, Redis, webhooks) adds significant complexity that is not justified at MVP stage. Accepted tradeoff: latency may be 3–8 seconds per request.*

### NFR-02 — Reproducible Model Training
**Priority:** Must (MVP)  
The ML training process must be reproducible. Random seeds must be set. The dataset split must produce the same train/test split every time.  
*Rationale: Non-reproducible training makes evaluation results meaningless.*

### NFR-03 — No Data Leakage
**Priority:** Must (MVP)  
No test-set data may influence any training-time decisions (feature selection, preprocessing statistics, hyperparameter tuning). The leakage-prevention checklist in `docs/phases/phase-02-ml-foundation.md` is the enforcement mechanism.  
*Rationale: Leakage produces falsely optimistic metrics and a model that does not generalize.*

### NFR-04 — Containerized Deployment
**Priority:** Must (MVP)  
The full system must run inside Docker containers via `docker-compose up`. No manual environment setup should be required.  
*Rationale: Reproducible deployment is a core engineering deliverable, not optional polish.*

### NFR-05 — Explainability of Every Design Decision
**Priority:** Must (MVP, learning goal)  
Every non-trivial implementation choice — model selection, feature encoding, prompt structure, validation logic — must have a written rationale, either in code comments, ADRs, or phase documentation.  
*Rationale: The primary learning goal of this project is not to ship fast, but to understand deeply.*

### NFR-06 — Latency Tolerance
**Priority:** Should (MVP)  
End-to-end request latency should be under 15 seconds under normal conditions. This is a guideline, not a hard contract, given two LLM calls are in the path.  
*Rationale: MVP is not performance-optimized. Latency is acceptable if it does not break the user experience.*

---

## 3. Validation Requirements

### VR-01 — Pydantic Schema Must Define All ML Features
**Priority:** Must (MVP)  
The `PropertyFeatures` Pydantic model must enumerate every feature the ML model expects, with types, valid ranges, and required/optional classification.  
*Rationale: The schema is the contract between the LLM and the ML model. It must be complete and strict.*

### VR-02 — Required vs Optional Feature Classification
**Priority:** Must (MVP)  
Each feature in the schema must be explicitly marked as required or optional, with documented justification.  
*Rationale: "Optional" is an engineering decision, not a default. If a feature is optional, there must be a documented imputation strategy.*

### VR-03 — Validation Must Happen at the API Boundary
**Priority:** Must (MVP)  
Feature validation must occur before the ML model is called. The ML pipeline must never receive unvalidated data.  
*Rationale: Downstream errors from invalid inputs are hard to trace. Validation at the boundary makes failures explicit and localized.*

### VR-04 — LLM Output Must Be Parseable
**Priority:** Must (MVP)  
The system must handle LLM outputs that are malformed, incomplete, or outside the expected schema. A well-defined error path must exist for each failure mode.  
*Rationale: LLMs are not deterministic. Output parsing failures are expected, not exceptional.*

---

## 4. UI Requirements

### UI-01 — Text Input Area
**Priority:** Must (MVP)  
The UI must include a text area where users can enter their property description.

### UI-02 — Missing Field Controls
**Priority:** Must (MVP)  
When required features are missing from extraction, the UI must render a labeled input control (dropdown, number field, etc.) for each missing field. The control type should match the feature's data type.

### UI-03 — Display of Extracted Features
**Priority:** Should (MVP)  
After extraction, the UI should show the user which features were extracted and their values. This allows the user to verify and correct errors.

### UI-04 — Prediction and Explanation Display
**Priority:** Must (MVP)  
The UI must display the predicted price prominently and the explanation below it in readable text.

### UI-05 — Error State Handling
**Priority:** Must (MVP)  
The UI must show a clear, user-friendly message when extraction fails, prediction fails, or the LLM returns an unusable response.

### UI-06 — No Chat Interface for MVP
**Priority:** Must (MVP, constraint)  
The MVP UI must be form-based, not chat-based. A conversational UI adds state management complexity that is not justified before the core pipeline is proven.  
*See ADR-004 for the decision rationale.*

---

## 5. ML Requirements

### ML-01 — Dataset: Ames Housing
**Priority:** Must (MVP)  
The model must be trained on the Ames Housing dataset. Alternatives require revisiting the feature schema.

### ML-02 — Train/Test Split Before All Preprocessing
**Priority:** Must (MVP)  
The dataset must be split into train and test sets before any preprocessing step is applied. All preprocessing statistics (means, encodings, scalers) must be fit only on training data.

### ML-03 — Preprocessing Pipeline Serialized with Model
**Priority:** Must (MVP)  
The preprocessing steps (imputation, encoding, scaling) must be part of the serialized artifact. They must not be re-fitted at inference time.

### ML-04 — Baseline Model First
**Priority:** Must (MVP)  
A simple baseline model (e.g., median price predictor) must be implemented and evaluated before any complex model is tried.  
*Rationale: Without a baseline, there is no way to know if a complex model is actually better.*

### ML-05 — Documented Evaluation Metrics
**Priority:** Must (MVP)  
Model evaluation must include at minimum: MAE, RMSE, R² score on the test set. Results must be documented in the phase log.

### ML-06 — Feature Importance Analysis
**Priority:** Should (MVP)  
Feature importances or SHAP values should be computed and documented to inform the Stage 2 explanation prompt design.

### ML-07 — No Target Leakage
**Priority:** Must (MVP)  
No feature derived from or correlated with the target variable (SalePrice) through time or data-collection process may be used in training.

---

## 6. Prompt-Chain Requirements

### PC-01 — Prompts Are Versioned Artifacts
**Priority:** Must (MVP)  
Both prompts (Stage 1 extraction, Stage 2 explanation) must be stored as versioned files, not hardcoded strings in application code.

### PC-02 — Prompt Outputs Must Be Validated
**Priority:** Must (MVP)  
Stage 1 prompt output must be validated against the `PropertyFeatures` schema. Parsing errors must be caught and handled.

### PC-03 — Stage 2 Prompt Must Inject Real Statistics
**Priority:** Must (MVP)  
The Stage 2 prompt must include actual numeric context from the training data. It must not rely on the LLM's parametric knowledge for statistics about the dataset.

### PC-04 — Prompt Content Must Be Human-Reviewable
**Priority:** Must (MVP)  
Prompts must be readable in plain English. They must be structured, documented, and justify their instructions.

### PC-05 — Stage 1 Must Instruct Against Hallucination
**Priority:** Must (MVP)  
The Stage 1 prompt must explicitly instruct the LLM to return null for features it cannot confidently infer, rather than guessing.

---

## 7. Deployment Requirements

### DR-01 — Docker Required
**Priority:** Must (MVP)  
The application must run via `docker-compose up` with no additional configuration.

### DR-02 — Environment Variables for Secrets
**Priority:** Must (MVP)  
LLM API keys and any other secrets must be passed through environment variables, never hardcoded.

### DR-03 — Model Path Configurable
**Priority:** Must (MVP)  
The path to the serialized model artifact must be configurable via environment variable.

### DR-04 — Health Check Endpoint
**Priority:** Must (MVP)  
The API must expose a `GET /health` endpoint that confirms the model is loaded and the service is ready.

---

## 8. Error-Handling Requirements

### EH-01 — Explicit Failure Responses
**Priority:** Must (MVP)  
All API errors must return structured JSON responses with an error code, error type, and human-readable message.

### EH-02 — LLM Extraction Failure Path
**Priority:** Must (MVP)  
If the LLM fails to return parseable JSON, or if schema validation fails entirely (no usable fields), the API must return a `422 Unprocessable Entity` with a clear explanation.

### EH-03 — Missing Required Fields Does Not Cause a 500
**Priority:** Must (MVP)  
Missing required features is an expected state, not a server error. It must return `200 OK` with extracted features and a list of missing fields.

### EH-04 — Model Inference Failure
**Priority:** Must (MVP)  
If the ML model raises an exception during inference (e.g., unexpected feature type), the error must be caught, logged, and returned as a `500 Internal Server Error` with a diagnostic message — not an unhandled crash.

### EH-05 — LLM Explanation Failure Does Not Block Prediction
**Priority:** Should (MVP)  
If Stage 3 LLM call fails, the system should still return the prediction with a fallback explanation message. A broken explanation should not cause the entire prediction to fail.

---

*Requirements are stable for Phase 0. Schedule a review before Phase 2 begins to confirm ML requirements match EDA findings.*
