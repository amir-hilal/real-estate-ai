# Phase 6: UI Flow

> **Status:** Not Started  
> **Depends on:** Phase 5 (API running and tested)  
> **Blocks:** Phase 7 (demo requires a working interface)

---

## Purpose

Phase 6 adds a user interface to the system. The interface must enable a non-technical user to describe a property, fill in any missing fields, and receive a prediction with explanation — without needing to use curl or understand the API.

The UI is an MVP-tier deliverable. It is not a polished product. It is sufficient to demonstrate the full pipeline end-to-end in a real-world interaction pattern.

---

## Why Form-Based UI Before Chat-First UI (for MVP)

A conversational chat UI is tempting — it feels modern and aligns with how LLMs are popularly used. However, for MVP, a form-based UI is strongly preferred for the following reasons:

### Against a chat-first UI for MVP:
1. **State management complexity:** A chat interface requires managing conversation history, turn tracking, and contextual memory. None of this is needed when all relevant information can be gathered in one or two form submissions.
2. **Validation is harder to express:** In a form, missing required fields are shown as labeled controls. In a chat, the conversation needs to pivot to question the user — requiring prompt engineering for the collection flow, not just extraction.
3. **Results are harder to display:** Showing a structured price prediction and explanation in a chat thread is visually awkward. A dedicated results layout is cleaner.
4. **Development time:** A form UI can be built in a fraction of the time. The core pipeline is the learning priority — not UI sophistication.

### When a chat UI becomes justified:
- The pipeline is proven end-to-end and reliable
- Users are returning frequently and want natural back-and-forth
- Multiple rounds of clarification are needed (which EDA and Phase 3 testing will reveal)

---

## Recommended MVP UI Flow

### Step 1: Input Form
**Purpose:** Collect the property description  
**Contents:**
- Page title: "Property Price Estimator"
- Large text area: "Describe the property" (placeholder: "e.g., 3-bedroom house, built in 1995, finished basement, 2-car garage, northwest Ames...")
- "Estimate Price" button

**On submit:**
- Disable button while request is in-flight
- Show loading spinner with message: "Extracting property details..."
- Call `POST /predict` with the description

---

### Step 2a: Missing Fields Form (Conditional)
**Displayed when:** API returns `status: "incomplete"` with `missing_required_fields` list  
**Purpose:** Collect the fields the LLM could not extract  
**Contents:**
- Header: "We need a few more details"
- Subheader: "The following fields couldn't be determined from your description. Please fill them in:"
- One input control per missing field (see "Control Types" below)
- "Get Estimate" button

**Control types by feature type:**
| Feature Type | Control |
|-------------|---------|
| Integer (e.g., bedrooms, year) | Number input with min/max hints |
| Float (e.g., area in sq ft) | Number input |
| Enum/categorical (e.g., neighborhood, quality rating) | Dropdown select with all valid options |
| Boolean (e.g., central air) | Toggle or Yes/No dropdown |

**On submit:**
- Call `POST /predict` again with original description + `supplemental_features`

---

### Step 2b: Pipeline Error State
**Displayed when:** API returns `status: "error"`  
**Contents:**
- Error icon
- Human-readable error message from API response
- "Try Again" button that resets to Step 1

---

### Step 3: Results Display
**Displayed when:** API returns `status: "complete"`  
**Contents:**

**Section 1 — Prediction card:**
```
Estimated Property Value
$243,500
```
(Large, prominent, center-aligned)

**Section 2 — Explanation:**
```
[Full 2–4 paragraph explanation from Stage 2 LLM]
```

**Section 3 (Optional/collapsible) — Extracted Features:**
```
Details we used:
• Bedrooms above grade: 3
• Year built: 1995
• Garage capacity: 2 cars
• Basement quality: Good
...
```
Collapsed by default to avoid overwhelming the user; expandable with "Show details."

**Section 4 — Reset:**
- "Estimate Another Property" button that resets to Step 1

---

## Handling Missing Fields (Design Details)

When the API returns `missing_required_fields`, the UI must:

1. Preserve the values already extracted — do not ask the user to re-describe the whole property
2. Display only the missing fields — do not show all schema fields
3. Provide helpful label text and units for each field (e.g., "Above-Grade Living Area (square feet)")
4. Validate the filled-in values client-side where possible (e.g., year built must be a 4-digit number between 1800–2030)
5. Merge the user-supplied values with the extracted features before the second API call

---

## Display of Extracted Values

The extracted features section should be human-friendly, not raw schema field names:

| Schema field | Display label |
|-------------|--------------|
| `bedroom_abv_gr` | Bedrooms (above grade) |
| `year_built` | Year Built |
| `gr_liv_area` | Above-Grade Living Area (sq ft) |
| `garage_cars` | Garage Capacity (cars) |
| `neighborhood` | Neighborhood |
| `bsmt_qual` | Basement Quality |
| `overall_qual` | Overall Quality (1–10) |

A field-to-label mapping must be defined once and reused across all UI components.

---

## Error States

| Scenario | UI Behavior | Message |
|----------|------------|---------|
| Text input is empty | Prevent submission (client-side validation) | "Please describe a property before submitting." |
| API returns 422 (validation error) | Show error card | "Your description couldn't be processed. Try adding more details." |
| API returns 500 | Show error card | "An internal error occurred. Please try again." |
| API call times out (>15s) | Show timeout card | "This is taking longer than expected. Please try again." |
| Missing fields form submitted with empty values | Client validation, prevent submission | Required field labels turn red |
| Explanation unavailable (fallback message from API) | Show prediction + fallback message | "Explanation temporarily unavailable." |

---

## Technical Notes

- The MVP UI does not require a complex frontend framework. A minimal approach with plain HTML/CSS and JavaScript, or a simple Python-rendered template (Jinja2 via FastAPI) is sufficient.
- If a framework is used (React, Vue, etc.), it must be chosen based on the developer's existing knowledge — not because it is popular. Learning a frontend framework should not compete with learning the ML/LLM pipeline.
- The UI communicates with the FastAPI backend only through documented API endpoints. No direct model or LLM calls from the frontend.
- The UI is served by the same Docker container as the API in MVP (no separate frontend container).

---

## Exit Criteria

Phase 6 is complete only when ALL of the following are true:

1. [ ] Input form renders and submits a description to the API
2. [ ] Missing fields form renders correctly for at least one real missing-field scenario
3. [ ] Results page displays prediction and explanation correctly
4. [ ] All error states from the table above have been tested and render correctly
5. [ ] Extracted features section is displayed (even if collapsed)
6. [ ] Full end-to-end flow works from browser without touching the terminal
7. [ ] UI runs inside the Docker container

---

*The UI exists to demonstrate the pipeline. Its quality is secondary to the correctness of the underlying system.*
