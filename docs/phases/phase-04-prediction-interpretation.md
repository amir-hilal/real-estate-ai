# Phase 4: Prediction Interpretation (Stage 2 LLM)

> **Status:** Complete  
> **Depends on:** Phase 2 (training statistics available), Phase 3 (extraction working), Phase 1 (feature importances known)  
> **Blocks:** Phase 5 (full API integration requires all stages working)

---

## Purpose

A predicted price is a number. Without context, a non-technical user cannot evaluate whether $243,000 is reasonable, high, or low for a property they described. Stage 2 turns that number into an explanation that is grounded in data, written in plain English, and honest about the model's basis for the prediction.

This phase designs, tests, and validates that explanation. The risk in Stage 2 is different from Stage 1: the primary risk is not parsing failure — it is **hallucination**. The LLM must explain using facts we provide, not facts it invents.

---

## Stage 2 Goals

1. Receive: validated `PropertyFeatures` + predicted price + training statistics
2. Generate: a 2–4 paragraph plain-English explanation of the prediction
3. The explanation must mention the predicted price explicitly
4. The explanation must include at least two numerical comparisons from the injected training statistics
5. The explanation must reference the top 1–3 features driving the prediction (from Phase 2 feature importances)
6. The explanation must be written for a non-technical user — no jargon, no ML terminology
7. The explanation must not assert facts that were not in the prompt context

---

## What Makes an Explanation Useful

Not all explanations are created equal. A useful explanation:

**Does:**
- States the predicted price clearly in the first sentence
- Compares the property to relevant reference points (e.g., "similar properties in this neighborhood")
- Explains *why* the price is what it is (feature-driven reasoning)
- Acknowledges significant features that raised or lowered the price
- Uses numbers from the training statistics, not invented ones
- Feels honest — not marketing copy

**Does not:**
- Start with "Based on our analysis..." (vague filler)
- Say "The model predicts..." (exposes internal terminology)
- Invent statistics not provided in the prompt
- Contradict the features provided (e.g., explain a high price for a property marked as having poor quality)
- Claim certainty on subjective judgments (e.g., "This is an excellent investment")

---

## Required Inputs for Stage 2

| Input | Source | Required? |
|-------|--------|-----------|
| Predicted price (USD) | Stage 2 ML Model output | Yes |
| Validated `PropertyFeatures` | Stage 1 + user fill-in | Yes |
| Median `SalePrice` in training data | `ml/artifacts/training_stats.json` | Yes |
| `SalePrice` statistics by neighborhood (if neighborhood is a feature) | Training stats file | Yes, if neighborhood available |
| Price per square foot statistics | Training stats file | Yes, if GrLivArea is a feature |
| Top 3 feature importances for this prediction type | Available from model or precomputed | Should |
| Optional: prediction confidence interval | If model supports it | Optional |

---

## Prompt Design Considerations

### Structure of the Stage 2 Prompt

The prompt must contain:
1. **Role assignment:** "You are explaining a property price estimate to a potential buyer or seller."
2. **Strict grounding instruction:** "Use ONLY the statistics provided below. Do not add or invent any data points."
3. **Injected statistics block:** A formatted section containing all numeric context from the training stats file
4. **Injected property features block:** Key feature values in plain-English format
5. **Predicted price:** Explicit statement of the price to explain
6. **Output format instruction:** "Write 2–4 paragraphs. First paragraph: state the price clearly. Second paragraph: compare to market context. Third paragraph: explain key drivers. Do not use ML jargon."
7. **Example of a good response** (one-shot or few-shot)

### Anti-hallucination instructions
The prompt must include explicit language such as:
> "Do not mention any specific neighborhoods, price figures, or statistics that are not listed in the context section above."
> "If you are uncertain about any claim, omit it rather than guessing."

### Handling edge cases in the prompt
- If the prediction is significantly above the dataset median: explain premium factors
- If the prediction is significantly below the dataset median: explain discount factors
- If a key feature is null (optional field): do not mention it unless the prompt context includes it

---

## Failure Cases

| Failure Mode | Likely Cause | Expected Handling |
|-------------|-------------|------------------|
| LLM invents statistics not in context | Insufficient grounding instruction | Check explanation output against injected stats; fail loudly if invented values detected |
| LLM uses ML jargon ("the model assigned a weight of...") | Prompt does not restrict vocabulary | Add explicit vocabulary restriction to prompt |
| Explanation contradicts property features | LLM ignores injected data | Strengthen grounding instructions; add few-shot examples |
| Explanation is too generic ("This is a nice house in a good area") | Prompt allows vague responses | Add specificity requirements: "mention at least two numeric comparisons" |
| LLM refuses to generate due to safety filter | Not applicable to property descriptions | Unlikely; handle as stage failure with fallback message |
| LLM explanation fails entirely | API timeout, rate limit | Return prediction with fallback message: "Explanation temporarily unavailable." |

---

## Evaluation Checklist

For each Stage 2 output, verify:

- [ ] The predicted price is mentioned explicitly and accurately (matches Stage 2 ML output)
- [ ] At least two numeric comparisons are present (e.g., "compared to the median of $X")
- [ ] All mentioned statistics appear in the injected training stats context
- [ ] No ML-specific terminology is used
- [ ] No factual claims are made about features that were null/missing
- [ ] The tone is neutral and informative, not promotional
- [ ] The explanation would make sense to a first-time homebuyer
- [ ] The length is 2–4 paragraphs

### Test battery (minimum 5 scenarios)

| ID | Scenario | Expected Behavior |
|----|----------|------------------|
| E01 | High-value property (predicted > 75th percentile) | Explanation highlights premium features; references upper-quartile comparison |
| E02 | Low-value property (predicted < 25th percentile) | Explanation honestly describes limiting factors |
| E03 | Average property (predicted near median) | Comparison to median is the anchor; balanced explanation |
| E04 | Property with several null optional features | Explanation does not mention absent features |
| E05 | Training stats injected with one unusual stat | Stats appear correctly; LLM does not add extra made-up stats |

---

## Exit Criteria

Phase 4 is complete only when ALL of the following are true:

1. [x] Stage 2 prompt is written, versioned, and stored in `prompts/` — `prompts/explanation_v1.md` with grounding instructions, anti-hallucination rules, vocabulary restriction, price-bracket contextualisation, and injected statistics block
2. [x] Training statistics file is finalized and confirmed correct — `ml/artifacts/training_stats.json` extended with `top_features` ranked by LightGBM gain importance: `["OverallQual", "GrLivArea", "Neighborhood", ...]`
3. [x] All 5 evaluation test scenarios are run and documented — `tests/test_explanation_integration.py` (E01–E05 against Ollama `phi4-mini`, all passing)
4. [x] At least 4 of 5 test scenarios produce explanations that pass the evaluation checklist — 5/5 pass: price stated, ≥2 numeric comparisons, no ML jargon, no absent-feature claims, grounded statistics
5. [x] No test scenario produces a hallucinated statistic (verified by E05) — E05 asserts every dollar amount in the explanation is within $1,000 of an allowed value from the injected context; passes
6. [x] Fallback behavior for Stage 2 failure is implemented and tested — `ExplanationError` raised on empty response or LLM exception; tested in `tests/test_explanation.py`
7. [x] Prompt version 1 is committed to version control — `prompts/explanation_v1.md`

---

*The explanation is not a bonus — it is what makes the prediction trustworthy. A model that just outputs a number is less useful than one that contextualizes it.*
