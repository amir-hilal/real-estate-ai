# Phase 3: LLM Extraction Design (Stage 1)

> **Status:** Complete  
> **Depends on:** Phase 2 complete — the `PropertyFeatures` schema is locked before prompts are designed  
> **Blocks:** Phase 4 (Prediction Interpretation) and Phase 5 (API integration)

---

## Purpose

Stage 1 of the pipeline is responsible for transforming unstructured natural-language property descriptions into machine-usable structured data. This is the "bridge" between the user and the ML model.

This phase designs, tests, and validates that bridge. A poorly designed Stage 1 means the ML model receives garbage, the validation fails constantly, and the user experience degrades. Getting this right requires iterating on the prompt, the schema, and the failure-handling logic — not just writing a quick prompt and hoping it works.

---

## Stage 1 Goals

1. Accept any reasonable plain-English property description as input
2. Extract the `PropertyFeatures` schema fields with high confidence
3. Return `null` (not a guess) for fields that cannot be reliably inferred from the text
4. Produce a JSON output that is always parseable and always passes Pydantic validation (possibly with nulls)
5. Never hallucinate a specific value when the text is ambiguous or silent on a field
6. Fail gracefully with a structured error response when the input is completely unparseable

---

## Schema Design Considerations

### What the schema must do
- Define every feature the ML model requires
- Specify the data type for each field (int, float, str, Optional[str], etc.)
- Define valid value ranges for numeric fields (e.g., year_built: 1800–2030)
- Define valid enum values for categorical fields (e.g., BsmtQual: "Excellent", "Good", "Typical", "Fair", "Poor", None)
- Separate required fields (ML cannot run without them) from optional fields (ML can use a default or imputed value)

### Naming convention
Use field names that map directly to the ML model's feature names. Avoid using Ames-dataset raw column names in the API schema — prefer human-readable names that can be translated at inference time.

### Considerations for each field
Before adding a field to the schema, ask:
1. **Can a user realistically describe this in plain English?** (e.g., "3 bedrooms" → yes; "OverallQual = 7" → no)
2. **Is it predictive?** (Confirmed in Phase 1 feature importance)
3. **Can the LLM confidently infer it from property descriptions?** (Validate in test queries below)
4. **What is the null behavior?** (If the user doesn't mention it, what does the ML model get?)

### Schema completeness levels
Design the schema with three tiers:
- **Tier 1 — Required:** ML model will not run without these. If null after extraction, UI collects them before proceeding.
- **Tier 2 — Preferred:** Significantly improve prediction accuracy. LLM should try to extract; ML model uses imputed value if absent.
- **Tier 3 — Optional / Enriching:** Minor predictive value. Extracted if present in text, otherwise absent without issue.

---

## Prompt Versioning Plan

Prompts are versioned artifacts. They are not strings embedded in source code.

### Storage convention
- Prompts live in a dedicated directory: `prompts/` (to be created in Phase 5)
- Each prompt version is a separate file: `prompts/stage1_extraction_v1.md`, `v2.md`, etc.
- The active version is referenced by a configuration variable, not hardcoded
- Every version is committed to version control — old versions are never deleted

### Version structure
Each prompt file must contain:
```
# Stage 1 Extraction Prompt — Version: X
# Author: <name>
# Created: <date>
# Changes from previous: <brief description>
# Test results: <pass/fail summary>

---
[SYSTEM PROMPT]

[ROLE AND TASK DESCRIPTION]

[SCHEMA DEFINITION OR EXAMPLE]

[OUTPUT FORMAT INSTRUCTIONS]

[ANTI-HALLUCINATION INSTRUCTIONS]

[EXAMPLES OF GOOD OUTPUT]

[EXAMPLES OF EDGE CASES]
```

---

## Validation Strategy

The validation chain after Stage 1 extraction is critical:

```
LLM Raw Output (string)
        │
        ▼
JSON Parsing
  ├── Failure: return ParseError(stage="extraction", raw_output=...)
  └── Success ▼
Pydantic Validation
  ├── Hard type failure: return ValidationError(field=..., value=..., message=...)
  └── Partial validation (some fields null) ▼
Required Field Check
  ├── Any required fields null: return PartialExtraction(features=..., missing_fields=[...])
  └── All required fields present ▼
Proceed to Stage 2 (ML Prediction)
```

Every branch must return a structured response. Nothing should raise an unhandled exception.

---

## Failure Modes

Document each failure mode and its expected system behavior:

| Failure Mode | Example | Expected Response |
|-------------|---------|------------------|
| LLM returns invalid JSON | LLM adds prose before the JSON object | ParseError — retry once with stricter instructions; return 422 if retry fails |
| LLM invents a value not in enum | `bsmt_qual: "Average"` (not a valid enum value) | Pydantic ValidationError — field is set to null; add to missing fields |
| LLM returns all nulls (no extractable features) | User enters "house for sale" | Return EmptyExtraction — prompt user to provide more detail |
| User input is not a property description | "what is the weather today?" | Return InvalidInputType — tell user to describe a property |
| LLM response is cut off / incomplete | Partial JSON | ParseError — return 422; do not try to guess the remaining fields |
| Numeric field out of valid range | `year_built: 1200` | Pydantic ValidationError — set to null; add to missing fields |

---

## Test Query Plan

Before this phase is considered complete, the following test cases must be run and results documented:

### Test Set Design (minimum 10 queries)

| ID | Description | Expected Extractable Fields | Notable Challenge |
|----|-------------|---------------------------|------------------|
| T01 | Full-detail description (realistic, complete) | All Tier 1 + most Tier 2 fields | Happy path |
| T02 | Minimal description (just bedroom + location) | 2–3 Tier 1 fields | Many fields null |
| T03 | Description mentions neighborhood obscurely | Neighborhood via inference | Ambiguity test |
| T04 | Description uses approx. values ("about 2,000 sq ft") | GrLivArea as ~2000 | Approximate value handling |
| T05 | Description mentions garage capacity | garage_cars extracted | Direct mention test |
| T06 | Description in informal language ("cozy 2BR near downtown") | bedroom_abv_gr=2 | Informal text extraction |
| T07 | Description does not mention basement | bsmt_qual = null | Null behavior test |
| T08 | Description contains contradictory info ("3BR, 5 rooms") | Conflict surfaced via validation | Contradiction handling |
| T09 | Description in mixed units or ambiguous floor area | Parsed with best effort or null | Edge case |
| T10 | Non-property description ("I want to invest in real estate") | All null or InvalidInputType | Invalid input test |

### Passing criteria
- T01 must extract ≥8 Tier 1 fields correctly
- T07, T02, T10 must return properly structured null/empty responses without crashing
- All responses must pass Pydantic schema validation (possibly with nulls)
- No test case should cause an unhandled exception

---

## Key Questions to Resolve in This Phase

- [x] Which LLM is being used? Does it support JSON mode or function calling? **ANSWERED** — Ollama `phi4-mini` (dev) + Groq `llama-3.3-70b-versatile` (prod). Both support JSON mode via `response_format={"type": "json_object"}`. See ADR-007.
- [x] Will the prompt use few-shot examples, zero-shot, or structured output via tool call? **ANSWERED** — Few-shot (2 examples in the prompt). Small models need examples for reliable JSON structure.
- [x] How many retry attempts will be made if JSON parsing fails? **ANSWERED** — 1 retry with a stricter format instruction appended. If that also fails, return 422. Per `llm.instructions.md`.
- [x] If the LLM is changed in the future, how do we know the extraction quality hasn't regressed? **ANSWERED** — The 10 test queries become a regression suite. Run them on both `phi4-mini` and `llama-3.3-70b`.
- [x] What is the token cost per extraction request? Is it within acceptable range? **ANSWERED** — Free for dev (Ollama local). Groq free tier handles low volume. Not a blocker.

---

## Exit Criteria

Phase 3 is complete only when ALL of the following are true:

1. [x] Stage 1 prompt is written, versioned, and stored in `prompts/` — `prompts/extraction_v1.md` with guardrail, schema tables, enum mappings, anti-hallucination rules, 3 few-shot examples
2. [x] `PropertyFeatures` Pydantic model is finalized — `app/schemas/property_features.py` with `Literal` enum types for `Neighborhood` and `Exterior1st`, range constraints on all numeric fields
3. [x] All 10 test queries have been run and results documented — `tests/test_extraction_integration.py` (11 tests, all passing against Ollama `phi4-mini`)
4. [x] T01 passes with ≥8 correctly extracted fields — 11/12 fields extracted (only `MasVnrArea` null)
5. [x] T07 and T10 return well-structured null/error responses without crashes — T07: `TotalBsmtSF=null`, 0 missing required; T10: `is_property_description=false` with redirect message
6. [x] Validation chain (JSON → Pydantic → required field check) is designed and implemented — `app/services/extraction.py` with field-by-field validation, invalid→null fallback
7. [x] All failure modes have a defined handling path — retry on bad JSON, nullify invalid fields, `ExtractionError` after 2 failures, guardrail for off-topic input
8. [x] Prompt version 1 is committed to version control — `prompts/extraction_v1.md`

---

*Stage 1 is not done when it works on one input. It is done when it handles every failure mode correctly.*
