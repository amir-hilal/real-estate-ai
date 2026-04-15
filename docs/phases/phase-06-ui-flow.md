# Phase 6: UI Flow

> **Status:** In Progress
> **Depends on:** Phase 5 complete ✓ (API running in Docker, all 7 exit criteria met)
> **Blocks:** Phase 7 (demo requires a working interface)

---

## Purpose

Phase 6 adds a user interface to the system. The interface enables a non-technical user to describe a property in natural language, have a back-and-forth conversation until all required fields are known, and receive a price prediction with a streamed explanation — without needing to use curl or understand the API.

---

## Revision History

### Rev 1: Form-Based UI → Chat UI (ADR-008)

The original plan specified a form-based UI. After Phase 5 proved the pipeline end-to-end, a conversational chat interface was chosen instead. Missing fields are common in natural-language descriptions and a chat loop collects them more naturally than a form. Streaming the explanation token-by-token is a first-class requirement that belongs in a chat bubble.

### Rev 2: Embedded HTML → Standalone React App (ADR-009)

The chat UI was initially implemented as a single `app/static/index.html` file using React 18 + Babel Standalone + Tailwind Play CDN, served directly by the FastAPI backend. This approach failed to deliver reliable token-by-token streaming:

1. **Babel Standalone transpiles JSX in the browser.** This runtime transformation interacts poorly with React 18's automatic batching — `flushSync` and other batching workarounds did not produce visible per-token rendering.
2. **No build step means no control over the React runtime.** Production React apps use a bundler (Vite, webpack) that produces optimized output where `flushSync`, `startTransition`, and streaming patterns work as documented.
3. **CDN dependency for every page load.** React, ReactDOM, Babel, and Tailwind are all fetched from third-party CDNs on every page load. This is fragile and slow.
4. **Debugging is difficult.** Babel Standalone source maps are limited. Browser DevTools show transpiled code, not the original JSX.

A vanilla JS debug page (`debug-stream.html`) confirmed that the FastAPI SSE backend streams tokens correctly — each `event: token` arrives as a separate SSE event with correct timing. The streaming problem is exclusively in the React CDN frontend layer.

**Decision:** The frontend is extracted to a standalone React application (Vite + React 18 + TypeScript + plain CSS) in a separate directory. The FastAPI backend becomes a pure API server. See ADR-009.

---

## Conversational Flow

### Turn structure

Every user message goes through the same pipeline on the server:

```
User message
    │
    ▼
[LLM: intent classification + feature extraction]
    │
    ├─ emit features event (extracted_features metadata)
    │
    ├─ intent = "chat"      → stream reply as word-level tokens → done
    │
    └─ intent = "property"
            │
            ▼
        merge extracted_features with accumulated_features (client-side state)
            │
            ├─ required fields still missing
            │       └─ stream ask-for-missing reply as tokens → done
            │
            └─ all required fields present
                    ├─ stream reply as tokens
                    ├─ emit prediction event  (ML inference, ~instant)
                    └─ stream explanation tokens (Stage 3 LLM)
```

### Example conversation

| Turn | User | Assistant |
|------|------|-----------|
| 1 | "Hello" | "Hello! I'm a real estate pricing assistant for Ames, Iowa properties. Describe any property and I'll estimate its current market value." |
| 2 | "I have a house in North Ames built in 1990" | "Got it — North Ames, built in 1990. I still need a couple of details: how large is the above-grade living area (sq ft), and how would you rate the overall quality on a 1–10 scale?" |
| 3 | "About 1,800 sq ft, I'd say quality 7" | [prediction card renders: **$183,400**] [explanation streams]: "This 1,800 sq ft home in North Ames..." |
| 4 | "What if the quality was a 9?" | "If we raise the overall quality to 9, the estimate increases to **$221,500**." *(re-runs prediction with OverallQual=9)* |

---

## New Backend Components Required

### 1. `POST /chat` endpoint — SSE stream
**File:** `app/routes/chat.py`

**Request body:**
```json
{
  "message": "About 1,800 sq ft, I'd say quality 7",
  "history": [
    { "role": "user",      "content": "Hello" },
    { "role": "assistant", "content": "Hello! I'm a real estate pricing assistant..." },
    { "role": "user",      "content": "I have a house in North Ames built in 1990" },
    { "role": "assistant", "content": "Got it — North Ames, built in 1990..." }
  ],
  "accumulated_features": {
    "YearBuilt": 1990,
    "Neighborhood": "NAmes"
  }
}
```

**Response:** `text/event-stream` (SSE)

| Event | Payload | When emitted |
|-------|---------|-------------|
| `features` | `{"extracted_features": {...}}` | Feature metadata extracted from this turn (emitted once, before any tokens) |
| `token` | `{"text": "..."}` | Each word/chunk of the reply AND explanation (all text is streamed) |
| `prediction` | `{"prediction_usd": 183400, "features": {...}}` | Immediately when ML inference completes (between reply tokens and explanation tokens) |
| `done` | `{}` | End of stream |
| `error` | `{"code": "...", "message": "..."}` | Any failure |

**Why all text is token-streamed:** The reply text is split into word-level token events on the backend (via `_stream_text_as_tokens`). This gives the frontend a single streaming model — all visible text arrives as `token` events, whether it is a greeting, a follow-up question, or an explanation. The `features` event carries only metadata (no display text) and is emitted before the first token.

### 2. `app/services/chat.py` — Chat orchestration service

Responsibilities:
1. Call LLM with the chat prompt (non-streaming) to get `{intent, reply, extracted_features}`
2. Validate and merge `extracted_features` with `accumulated_features`
3. Emit `features` event with the current merged feature set
4. If `intent == "chat"` or missing fields remain → stream reply as word-level `token` events → emit `done`
5. If all required fields present → stream reply as tokens → run `predict_price()` → emit `prediction` event → call explanation LLM with streaming → forward each chunk as `token` event → emit `done`

The service must accept the LLM client as a parameter (testability requirement per LLM instructions).

### 3. `prompts/chat_v1.md` — Chat extraction + intent prompt

This is the most important new artifact. The prompt must instruct the LLM to:

- Return a **strict JSON object** (never prose):
  ```json
  {
    "intent": "property" | "chat",
    "reply": "...",
    "extracted_features": { "GrLivArea": 1800, "OverallQual": 7, ... } | null
  }
  ```
- For `intent = "chat"`: provide a helpful, concise reply; `extracted_features` must be `null`
- For `intent = "property"`: extract any property features mentioned in the new message (only the new message, not history); return only the fields that can be confidently inferred; `null` for anything uncertain
- **Must include:** list of already-known features (injected from `accumulated_features`) so the LLM does not re-ask for them
- **Must include:** list of still-missing required fields so the LLM asks for exactly those
- **Anti-hallucination:** must instruct the LLM to return `null` for any field not clearly stated — not to guess
- **Valid enum values must be listed** for `Neighborhood` and `Exterior1st`
- Must follow prompt file header format (name, version, date, purpose, changes)

### 4. `app/schemas/chat.py` — Request/response schemas

```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)
    accumulated_features: dict[str, Any] = Field(default_factory=dict)
```

`max_length=2000` on message follows the LLM instructions rule: never pass user input to LLM without length validation. `max_length=50` on history prevents unbounded context growth.

---

## Frontend: Standalone React Application

### Why standalone (see ADR-009)

The Babel Standalone CDN approach could not deliver reliable token-by-token streaming. A proper Vite + React 18 build produces bundled output where `requestAnimationFrame` yields, `flushSync`, and streaming patterns work correctly. The standalone app is created in a separate directory outside this project.

### Stack

- **Build tool:** Vite
- **Framework:** React 18 (with proper build — not CDN)
- **Language:** TypeScript
- **Styling:** Plain CSS (co-located `.css` files per component)
- **No additional libraries** — no state management library, no component library

### Frontend responsibilities

1. Render a chat thread: user messages right-aligned, assistant messages left-aligned
2. Maintain client-side state: `messages[]`, `accumulatedFeatures{}`, `streaming`, `streamingText`
3. Send `POST /chat` with `{message, history, accumulated_features}` on each turn
4. Parse the SSE response stream using `fetch()` + `ReadableStream` + `TextDecoder`
5. Dispatch events: `features` → merge into accumulated features, `prediction` → render prediction card, `token` → append to streaming text with browser yield, `done` → commit message, `error` → show error bubble
6. Yield to browser between token events (`requestAnimationFrame`) to guarantee per-token rendering
7. Render prediction card inline in the chat thread (collapsible feature details)
8. Character counter at 1800+, hard limit 2000
9. Shift+Enter for newlines, Enter to send
10. "New conversation" button resets all state

### CORS

The React dev server runs on a different port (e.g., `localhost:5173`) from the FastAPI backend (`localhost:8000`). The FastAPI backend must add CORS middleware to allow requests from the frontend origin.

### API base URL

The frontend reads the API URL from an environment variable (`VITE_API_URL`). Default: `http://localhost:8000`. In Docker, this can be overridden.

---

## Display of Extracted Values

| Schema field | Display label |
|-------------|--------------|
| `GrLivArea` | Above-Grade Living Area (sq ft) |
| `OverallQual` | Overall Quality (1–10) |
| `YearBuilt` | Year Built |
| `Neighborhood` | Neighborhood |
| `TotalBsmtSF` | Total Basement Area (sq ft) |
| `GarageCars` | Garage Capacity (cars) |
| `FullBath` | Full Bathrooms (above grade) |
| `YearRemodAdd` | Year Last Remodelled |
| `Fireplaces` | Number of Fireplaces |
| `LotArea` | Lot Area (sq ft) |
| `MasVnrArea` | Masonry Veneer Area (sq ft) |
| `Exterior1st` | Primary Exterior Material |

---

## Error Handling in the Chat UI

Errors surface as assistant chat bubbles, not page-level error cards. This keeps the conversation context visible and lets the user continue.

| Scenario | SSE event | Assistant bubble message |
|----------|-----------|--------------------------|
| Message is empty (client-side) | n/a — prevented before fetch | *(submission blocked)* |
| Message exceeds 2,000 chars | n/a — prevented before fetch | *(submission blocked with counter)* |
| LLM returns invalid JSON or times out | `error` event | "I had trouble understanding that — could you rephrase?" |
| ML model not loaded (503) | `error` event | "The estimation service isn't ready yet. Please try again in a moment." |
| Unexpected server error (500) | `error` event | "Something went wrong on my end. Please try again." |
| Explanation LLM fails mid-stream | `error` event after partial tokens | Prediction card still shown; "Explanation temporarily unavailable." appended |
| History length > 50 turns | client-side | Oldest turns pruned before sending (sliding window) |

---

## Technical Notes

- **Frontend stack:** Vite + React 18 + TypeScript + plain CSS — standalone app in a separate directory, with a proper build step.
- **Streaming transport:** `fetch()` + `ReadableStream` (not `EventSource` — SSE via EventSource is GET-only). The client reads the stream body with a `TextDecoder`, splits on `\n\n`, and dispatches each SSE event by type. `requestAnimationFrame` yields between token events to force per-token rendering.
- **Server-sent events:** FastAPI `StreamingResponse` with `media_type="text/event-stream"`. Each event is `event: <type>\ndata: <json>\n\n`.
- **State is client-side:** `accumulatedFeatures` and `history` live in React state and are sent with every `/chat` request. The `/chat` endpoint is stateless on the server — no sessions, no server-side storage.
- **CORS:** FastAPI `CORSMiddleware` added with allowed origin matching the frontend dev server (configurable via env var).
- **`/predict` endpoint unchanged:** The existing synchronous `/predict` endpoint continues to work. `/chat` is additive. Tests for `/predict` remain valid.
- **Prompt versioning:** `prompts/chat_v1.md` follows the same header convention as existing prompts. The active version is configured via `settings.chat_prompt_version`.
- **No static file serving.** The FastAPI backend does not serve HTML, CSS, or JS. `app/routes/ui.py` and `app/static/` are removed.

---

## Exit Criteria

Phase 6 is complete only when ALL of the following are true:

1. [ ] `POST /chat` endpoint returns SSE events — verified with curl
2. [ ] Greeting input ("Hello") receives a conversational reply, not an error
3. [ ] Vague property description triggers a follow-up question for the missing required fields
4. [ ] Conversation accumulates features across turns until all required fields are known
5. [ ] Prediction is returned when all required fields are present
6. [ ] Explanation streams token-by-token (verified with curl: individual `event: token` lines)
7. [ ] Error events are returned for LLM failure and model-not-ready scenarios
8. [ ] Standalone React app renders chat UI in browser and communicates with `POST /chat`
9. [ ] Explanation tokens render word-by-word in the React chat bubble (not popping in all at once)
10. [ ] Full end-to-end flow works from browser: greeting → property description → missing field follow-up → prediction + streamed explanation
11. [ ] `/predict` endpoint still passes all existing tests (no regression)

---

## Files Changed by This Phase

| File | Action | Notes |
|------|--------|-------|
| `app/routes/chat.py` | Create | `POST /chat` → SSE stream |
| `app/services/chat.py` | Create | Chat orchestration: intent routing, feature accumulation, predict + stream |
| `app/schemas/chat.py` | Create | `ChatMessage`, `ChatRequest` Pydantic models |
| `prompts/chat_v1.md` | Create | Combined intent + extraction prompt |
| `app/config.py` | Update | Add `chat_prompt_version`, `cors_origin` settings |
| `app/main.py` | Update | Register `chat_router`, add CORS middleware, remove `ui_router` |
| `app/routes/ui.py` | Delete | No longer serves static files |
| `app/static/` | Delete | Frontend is a standalone app |
| *Standalone React app* | Create | Separate directory, Vite + React 18 + TS + plain CSS |
