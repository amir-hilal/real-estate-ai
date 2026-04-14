# Common Mistakes to Avoid

> **Skill type:** Anti-pattern catalog  
> **Scope:** All phases  
> **Use when:** Before making any significant implementation decision. These are documented failure modes.

---

## ML Mistakes

### Mistake 1: Data Leakage via Preprocessing Before Split
**What it looks like:**
```python
# WRONG
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # fit on full dataset
X_train, X_test = train_test_split(X_scaled, ...)
```
**Why it's wrong:** The scaler has seen test data statistics. The test set is contaminated.

**Correct pattern:**
```python
# CORRECT
X_train, X_test = train_test_split(X, ...)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # fit on train only
X_test_scaled = scaler.transform(X_test)         # only transform test
```
**Rule:** When in doubt, `fit_transform` is only ever called on training data. `transform` is called on everything else.

---

### Mistake 2: Reporting Only Training Metrics
**What it looks like:** "My model achieves R²=0.98!"  
**Why it's wrong:** If that 0.98 is on training data, it says nothing about generalization. Overfitting can produce near-perfect training metrics with terrible test metrics.

**Correct pattern:** Always report train metrics AND test metrics together. A large gap indicates overfitting.

---

### Mistake 3: Treating Ames "NA" as a Missing Value
**What it looks like:** Imputing `PoolQC: NA` with the mode of pool quality.  
**Why it's wrong:** In Ames, `PoolQC: NA` means the property has no pool. Replacing it with "Good" or "Typical" completely misrepresents the property.

**Correct pattern:** Encode these as a distinct "None" or "No Feature" category. Read the data dictionary before writing any imputation code.

---

### Mistake 4: Re-training the Preprocessor at Inference Time
**What it looks like:** Loading the model artifact, then also loading the raw training data to recompute normalization statistics.  
**Why it's wrong:** Inference-time data is different from training data. Re-fitting on inference data produces different statistics and corrupts predictions.

**Correct pattern:** Serialize the fitted preprocessor inside the sklearn Pipeline. At inference time, call `pipeline.predict()` only — no fitting.

---

### Mistake 5: Skipping the Baseline
**What it looks like:** Training XGBoost immediately and reporting an MAE of $22,000.  
**Why it's wrong:** Without a baseline, you don't know if $22,000 is good. A `DummyRegressor(median)` might achieve $35,000 MAE — in which case XGBoost is a major improvement. Or it might achieve $20,000 — in which case all that complexity bought almost nothing.

---

## LLM Mistakes

### Mistake 6: Not Validating LLM JSON Output
**What it looks like:**
```python
result = llm_response.content
features = PropertyFeatures(**json.loads(result))  # no error handling
```
**Why it's wrong:** LLMs frequently add prose before or after JSON, return malformed JSON, or omit required keys. This crashes unpredictably in production.

**Correct pattern:** Wrap parsing and validation in explicit try/except blocks with structured error responses.

---

### Mistake 7: Letting Stage 2 LLM Invent Statistics
**What it looks like:** Stage 2 prompt says "explain why this predicted price is reasonable for this neighborhood."  
**Why it's wrong:** The LLM will confidently invent median prices, appreciation rates, and comparison figures from its training data — which are wrong, outdated, or fabricated.

**Correct pattern:** Inject the actual statistics from `training_stats.json` into the prompt, and explicitly instruct the LLM to only use the provided numbers.

---

### Mistake 8: Hardcoding Prompt Content in Application Code
**What it looks like:**
```python
EXTRACTION_PROMPT = """You are a real estate expert...
Extract these fields: bedroom_abv_gr (integer), gr_liv_area (float)...
"""
```
**Why it's wrong:** Prompt iteration is a development activity separate from application code. Prompts embedded in code require a code change and redeployment to update. They cannot be reviewed in git history as distinct artifacts.

**Correct pattern:** Store prompts as files in `prompts/`. Load them at startup or request time. Version them with a version number in the filename.

---

### Mistake 9: Assuming LLM Enum Values Match the Schema
**What it looks like:** Prompt says "return basement quality as one of: Excellent, Good, Fair, Poor" but the Pydantic schema expects "Ex", "Gd", "Fa", "Po" (Ames raw encoding).  
**Why it's wrong:** Either the LLM returns values that fail validation, or you accept the LLM's format and apply a brittle mapping.

**Correct pattern:** Align the prompt's stated valid values with the exact values in the Pydantic schema. Decide once: use human-readable labels or Ames codes, and be consistent throughout.

---

## Architecture Mistakes

### Mistake 10: Adding Infrastructure Before the Problem Exists
**What it looks like:** "I'll add Redis and Celery now so we're ready to scale."  
**Why it's wrong:** Adding async infrastructure adds two new services to debug, a new set of failure modes, and significant cognitive overhead — for a problem that does not yet exist.

**Correct pattern:** See `docs/context/future-considerations.md`. Add infrastructure when a specific, documented problem requires it.

---

### Mistake 11: Loading the Model on Every Request
**What it looks like:**
```python
@app.post("/predict")
def predict(request: PredictRequest):
    model = joblib.load("model.pkl")  # loaded on every request
    return model.predict(...)
```
**Why it's wrong:** Model deserialization takes 100ms–500ms. For a synchronous API, doing this on every request adds consistent latency that compounds at scale.

**Correct pattern:** Load the model once at startup in `lifespan`, store it in app state, inject it into route handlers.

---

### Mistake 12: Returning Raw Stack Traces to API Clients
**What it looks like:** Unhandled exception propagates and FastAPI returns a 500 with the Python traceback in the response body.  
**Why it's wrong:** Exposes implementation details and internal paths to any client. Also provides no useful guidance for debugging.

**Correct pattern:** All exceptions should be caught at the service level. Return `{ "status": "error", "error_code": "...", "message": "human-readable message" }`.

---

## Process Mistakes

### Mistake 13: Writing Code Before Phase Prerequisites Are Met
**What it looks like:** Starting to write the ML model code before the feature shortlist from EDA is finalized.  
**Why it's wrong:** Model code depends on the feature list. An incomplete or wrong feature list means the model code will be wrong or need to be significantly rewritten.

**Correct pattern:** The phase sequence exists for a reason. The "Depends on" section of each phase document is the gate.

---

### Mistake 14: Updating Docs After the Fact Without Accuracy
**What it looks like:** Decision X was made in code, but `assumptions-and-open-questions.md` still says it's an open question, and the ADR was never written.  
**Why it's wrong:** The documentation becomes unreliable. Anyone (including future-you) reading it will make decisions based on wrong assumptions.

**Correct pattern:** When a decision is made, update the relevant doc at the same time. Add the ADR entry before or immediately after implementing the decision.

---

*This document is most useful before a mistake is made. Read it at the start of each phase.*
