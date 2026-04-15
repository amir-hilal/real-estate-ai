# Prompt Version Results Tracker

> **Purpose:** Track prompt versions, their changes, and observed behavior across test conversations.
> **Rule:** Each version gets a section. Test results are immutable — add new results, never edit old ones.

---

## chat_v1.md

**Created:** 2026-04-15
**Status:** Superseded by v2

### Changes
- Initial version
- Combined intent classification + feature extraction
- 3 examples (greeting, partial property, completing required fields)
- 7 critical rules

### Known Issues

| # | Test Input | Expected Behavior | Actual Behavior | Root Cause |
|---|-----------|-------------------|-----------------|------------|
| 1 | "Estimate a 2,000 sq ft house with 3-car garage" | Extract GrLivArea=2000, GarageCars=3; ask for OverallQual, YearBuilt, Neighborhood | Asked for "living area size" (already provided!) and "remodeling" (optional) | LLM didn't recognize "2,000 sq ft" as GrLivArea; no rule prioritizing required over optional fields |
| 2 | "go ahead" (with YearBuilt still missing) | Ask for YearBuilt | Said "I have all the details needed" — no prediction produced | LLM hallucinated completeness; no example showing "go ahead" with missing fields |
| 3 | Multi-turn accumulation | Features accumulate across turns | `accumulated_keys=[]` on turn 2 (frontend sends stale state) | Frontend React batching issue (not a prompt issue) |

---

## chat_v2.md

**Created:** 2026-04-15
**Status:** Active

### Changes from v1
1. **Stronger missing-field instructions:** Must name the specific missing required fields in the reply
2. **New rule 8:** "Extract ALL features you can find BEFORE deciding what is missing" — prevents skipping clearly stated features
3. **New rule 9:** "NEVER ask about optional features while any required feature is still missing"
4. **Bolded guard in `{still_missing}` section:** "If this list is not empty, you are NOT allowed to say 'I have everything'"
5. **New Example 2:** First-turn partial extraction ("2,000 sq ft with 3-car garage") — shows extracting GrLivArea + GarageCars and asking for the 3 remaining required fields specifically
6. **New Example 5:** "Go ahead" with YearBuilt still missing — shows the LLM must ask for it instead of confirming
7. **Inline hint in property intent:** "2,000 sq ft = GrLivArea 2000, 3-car garage = GarageCars 3" — helps LLM map natural language to field names

### Test Results

| # | Date | Test Input | History/Context | Expected | Actual | Pass? |
|---|------|-----------|----------------|----------|--------|-------|
| | | | | | | |

*(Run tests and record results here)*
