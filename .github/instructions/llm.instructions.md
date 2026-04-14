---
applyTo: "app/services/**,prompts/**,app/clients/**"
---

# LLM Instructions

These instructions govern all LLM-related code and prompts in this project — including Stage 1 feature extraction, Stage 2 explanation generation, prompt file management, and LLM client code.

---

## The Most Important LLM Rule

**Never trust LLM output without validation.**

LLMs are not deterministic. They can return malformed JSON, values outside expected ranges, invented statistics, and grammatically valid but factually wrong content. Every point where LLM output enters the system must have an explicit, tested error handler. "It usually works" is not an error handling strategy.

---

## Prompt File Rules

1. **Prompts are versioned files, not embedded strings.** All prompts live in `prompts/`.
2. **File naming convention:** `extraction_v1.md`, `explanation_v1.md`
3. **Increment the version number** when the prompt changes in a way that could affect output. Do not edit a prompt in-place and forget to version it.
4. **Old prompt versions are never deleted.** They are the history of what was tried and why it changed.
5. **The active prompt version is configured via environment variable**, not hardcoded.
6. **Each prompt file must include a header:**
   ```
   # Prompt Name — Version X
   # Created: YYYY-MM-DD
   # Purpose: [one sentence]
   # Changes from previous version: [brief description or "Initial version"]
   ```

---

## Stage 1 Extraction Prompt Rules

### Anti-hallucination instructions are required
The prompt **must** include explicit instructions to return `null` for any field that cannot be confidently inferred from the user's text. Example:

> "If you cannot determine a field's value from the text provided, return `null` for that field. Do NOT guess, estimate, or infer from general knowledge."

### Output format must be strict
The prompt must specify:
- The exact JSON structure expected
- The field names as they appear in the `PropertyFeatures` schema
- The data types (integer, float, string from enum, or null)
- That no additional keys should be added

### Valid enum values must be listed
For categorical features, the prompt must list all valid enum values. The LLM must not invent values not in the list.

### One-shot or few-shot examples improve reliability
Include at least one well-formed example in the prompt showing a property description → correct JSON output.

---

## Stage 1 Output Validation Chain

After receiving the LLM response string, apply this chain in order:

```
1. Strip leading/trailing whitespace from response
2. Attempt JSON parsing (json.loads or equivalent)
   → On JSONDecodeError: raise ExtractionParseError, do not retry silently
3. Validate against PropertyFeatures Pydantic model
   → On ValidationError: log validation errors, set invalid fields to null
4. Check for required fields (Tier 1 features)
   → If any required field is null: return PartialExtraction(features, missing_fields)
5. All required fields present: proceed to Stage 2
```

Do not skip steps. Do not catch `JSONDecodeError` and return empty features — surface the error.

---

## Stage 2 Explanation Prompt Rules

### Grounding is not optional
The Stage 2 prompt **must** inject real statistics from `ml/artifacts/training_stats.json`. The LLM must not generate statistics from its parametric knowledge.

Pattern:
```
[CONTEXT: The following statistics come from the training dataset. Use ONLY these values when making comparisons.]
- Median sale price: $182,500
- Price range (25th–75th percentile): $129,500 – $214,000
- Average price per square foot: $97
...
```

### Anti-hallucination instruction
Include this explicitly:
> "Do not mention any price figures, statistics, or factual claims that are not in the context section above. If you are unsure whether something is in the context, do not say it."

### Vocabulary restriction
> "Do not use machine learning terminology such as 'model', 'feature', 'prediction', 'training data', or 'algorithm'. Explain the estimate as if you are a real estate professional speaking to a buyer."

### Output format instruction
> "Write exactly 2–4 paragraphs. First paragraph must state the estimated price. Second paragraph must compare the property to market context using at least two numbers from the context above."

---

## LLM Client Code Rules

1. **Use the official SDK** (openai, anthropic, etc.) — do not make raw HTTP calls to LLM APIs
2. **The API client is injected, not instantiated inline** — pass it as a parameter to functions for testability
3. **Log every LLM call:** timestamp, model name, prompt version, response latency, status (success/failure)
4. **Set explicit timeout on all LLM calls** — never wait indefinitely for a response
5. **Do not log full prompt content by default** — it may contain user data. Log prompt version and length only.
6. **Handle rate limits explicitly:** implement at most one retry with a brief delay. Do not implement exponential backoff for MVP (too complex).

---

## Retry Policy

For LLM calls:
- If the API returns a network error or timeout: retry once
- If the response cannot be JSON-parsed: retry once with a more explicit format instruction appended to the prompt
- If the second attempt also fails: return a structured error response. Do not retry more than twice.

For validation failures (valid JSON but schema violations):
- Do not retry — retry will not fix a schema mismatch. Return partial results with the validation error noted.

---

## What Not to Do with LLMs

- Do not use the LLM to compute statistics (e.g., "what is the average price in this neighborhood?") — it will hallucinate. Compute statistics from real data.
- Do not combine Stage 1 and Stage 2 into a single prompt for MVP. They have different responsibilities and failure modes.
- Do not include `SalePrice` or any target-adjacent information in the Stage 1 prompt — the LLM should not know the price before the ML model predicts it.
- Do not pass user-submitted text directly to the LLM without length validation. Set a maximum input length (e.g., 2,000 characters for property descriptions).
- Do not add the model's numeric prediction to the Stage 1 extraction flow — Stage 1 only does extraction.
- Do not trust the LLM to enumerate all valid categorical values for a feature dynamically — provide the valid values in the prompt.

---

## Token Cost Awareness

- Each Stage 1 request ≈ 500–1,500 tokens (prompt + response) depending on description length
- Each Stage 2 request ≈ 1,000–2,000 tokens (injected stats + explanation)
- During development, use `gpt-4o-mini` or equivalent for iteration; reserve `gpt-4o` for final validation
- If cost is a concern, log estimated token counts per request
