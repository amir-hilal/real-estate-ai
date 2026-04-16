# React Frontend App — Creation Prompt

> Paste this entire file into a new VS Code Copilot Chat window to create the standalone React app.
> The app should be created in a NEW directory OUTSIDE the real-estate-ai project.

---

## Task

Create a standalone React frontend application for an AI Real Estate Agent. The app is a conversational chat interface that communicates with an existing FastAPI backend via SSE (Server-Sent Events).

**The backend already exists and runs inside a Docker container (Docker Desktop on Windows).** You are only building the frontend.

---

## Stack

- **Vite** — build tool and dev server
- **React 18** — UI framework (use `createRoot`, not `ReactDOM.render`)
- **TypeScript** — strict mode
- **Plain CSS** — regular `.css` files, no CSS framework (no Tailwind, no CSS-in-JS, no Sass)
- **No other libraries** — no state management (Redux, Zustand), no component library (MUI, shadcn), no routing (react-router). This is a single-page chat app.

---

## Project Setup

Create the project in a directory called `real-estate-ui` (anywhere convenient on your system — it is independent of the backend project).

```
real-estate-ui/
├── src/
│   ├── App.tsx              ← Root component
│   ├── App.css              ← App-level styles (layout, header, empty state)
│   ├── main.tsx             ← Entry point (createRoot)
│   ├── index.css            ← Global resets (box-sizing, body, fonts)
│   ├── components/
│   │   ├── ChatThread.tsx   ← Message list + auto-scroll
│   │   ├── ChatThread.css
│   │   ├── MessageBubble.tsx ← Single message (user or assistant)
│   │   ├── MessageBubble.css
│   │   ├── PredictionCard.tsx ← Prediction result card
│   │   ├── PredictionCard.css
│   │   ├── TypingIndicator.tsx ← Animated dots while waiting
│   │   ├── TypingIndicator.css
│   │   ├── InputBar.tsx     ← Text area + send button
│   │   └── InputBar.css
│   ├── hooks/
│   │   └── useChat.ts       ← All chat logic: state, fetch, SSE parsing
│   ├── services/
│   │   └── api.ts           ← fetch wrapper for POST /chat
│   └── types/
│       └── chat.ts          ← TypeScript interfaces
├── .env                     ← VITE_API_URL=http://localhost:8000
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## API Contract

The backend exposes a single endpoint the frontend uses:

### `POST /chat`

**Request body (JSON):**
```typescript
interface ChatRequest {
  message: string;           // User's message (1–2000 chars)
  history: ChatMessage[];    // Previous turns (max 50)
  accumulated_features: Record<string, unknown>; // Features gathered so far
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
```

**Response:** `text/event-stream` (SSE)

The response is a stream of Server-Sent Events. Each event has a type and a JSON data payload:

```
event: reply
data: {"text": "Got it — North Ames, built in 1990...", "extracted_features": {"YearBuilt": 1990, "Neighborhood": "NAmes"}}

event: prediction
data: {"prediction_usd": 183400, "features": {"GrLivArea": 1600, "OverallQual": 7, ...}}

event: token
data: {"text": "Based"}

event: token
data: {"text": " on"}

event: token
data: {"text": " our"}

event: done
data: {}

event: error
data: {"code": "LLM_ERROR", "message": "I had trouble understanding that — could you rephrase?"}
```

**Event types:**

| Event | Payload | Meaning |
|-------|---------|---------|
| `reply` | `{text: string, extracted_features: Record<string, unknown>}` | The assistant's conversational reply. May also contain newly extracted features to merge into `accumulated_features`. |
| `prediction` | `{prediction_usd: number, features: Record<string, unknown>}` | ML model prediction result. Render as a card. |
| `token` | `{text: string}` | One chunk of the streaming explanation. Append to the current assistant message. |
| `done` | `{}` | Stream complete. Commit the message to the thread. |
| `error` | `{code: string, message: string}` | An error occurred. Show as an assistant message. |

**Event sequence for different scenarios:**

1. **Greeting ("Hello"):** `reply` → `done`
2. **Partial property (missing fields):** `reply` (with extracted_features) → `done`
3. **Complete property (all required fields known):** `reply` → `prediction` → `token` × N → `done`
4. **Error:** `error` (terminates stream)

---

## SSE Parsing — Critical Implementation Detail

**Do NOT use `EventSource`.** It only supports GET requests. Use `fetch()` with `ReadableStream`:

```typescript
const res = await fetch(url, { method: "POST", headers: {...}, body: ... });
const reader = res.body!.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });

  const parts = buffer.split("\n\n");
  buffer = parts.pop()!; // keep incomplete tail

  for (const part of parts) {
    // parse event type and data from each part
    // dispatch based on event type
  }
}
```

### Token Streaming — THE MOST IMPORTANT REQUIREMENT

The whole reason this frontend exists is to render explanation tokens word-by-word as they arrive.

**Problem:** `reader.read()` may return a chunk containing multiple SSE events. If you process them all in a tight loop and call `setState` for each token, React 18 batches all updates and only paints the final accumulated value — the text appears to "pop in" all at once instead of streaming.

**Solution:** After processing each `token` event, **yield to the browser** before processing the next one. This gives React a chance to commit the state update and the browser a chance to paint:

```typescript
// Yield to browser so it can paint between token updates
const yieldToBrowser = () =>
  new Promise<void>(resolve =>
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  );

// In the event processing loop:
if (eventType === "token") {
  replyText += payload.text;
  setStreamingText(replyText);
  await yieldToBrowser(); // <-- CRITICAL: let browser paint this token
}
```

The double-`requestAnimationFrame` guarantees the previous frame was composited before continuing. This is the pattern that makes streaming work. **Do not skip this.**

---

## UI Design

### Layout
- Full-height single-column layout, max-width ~650px, centered
- Header bar at top: title "Property Price Estimator", subtitle "Ames, Iowa · ML + AI", "New conversation" button
- Scrollable message thread in the middle (flex-1, overflow-y-auto)
- Fixed input bar at the bottom

### Message Thread
- Empty state: centered placeholder with wave emoji, "Describe a property to get started", and example text: `Try: "3-bed house in North Ames, built 1995, about 1,600 sq ft, quality 7"`
- User messages: right-aligned, blue background, white text, rounded corners (bottom-right corner less rounded)
- Assistant messages: left-aligned, white background with light border, dark text, rounded corners (bottom-left corner less rounded)
- Streaming assistant message: shows a blinking cursor character (▋) at the end via CSS animation
- Auto-scroll to bottom on new messages and streaming text changes

### Prediction Card
- Rendered inline in the message thread (inside the assistant message area)
- Blue-tinted background, large bold price in USD format (e.g., "$183,400")
- Small text: "Ames, Iowa · 2006–2010 market data"
- Collapsible "Show details used" section listing the feature values

### Typing Indicator
- Three bouncing dots (gray circles with staggered animation delays: 0ms, 150ms, 300ms)
- Shown when the request is in-flight but no streaming text has arrived yet

### Input Bar
- Multi-line textarea (1 row default, max 140px height, auto-overflow)
- Character counter appears at 1800+ characters, red at 2000+
- Send button (blue, disabled when streaming, empty, or over limit)
- Keyboard: Enter to send, Shift+Enter for newline
- Hint text below: "Shift+Enter for new line · Enter to send"

---

## State Management

All state lives in a custom hook `useChat()`:

```typescript
interface UseChatReturn {
  messages: Message[];           // committed chat thread
  streamingText: string;         // in-flight assistant text (token by token)
  pendingPrediction: Prediction | null; // prediction card waiting during streaming
  accumulated: Record<string, unknown>; // features gathered across all turns
  streaming: boolean;            // whether SSE is in-flight
  sendMessage: (text: string) => Promise<void>;
  reset: () => void;
}
```

### Message type

```typescript
interface Message {
  role: "user" | "assistant";
  text: string;
  prediction?: Prediction | null;
}

interface Prediction {
  prediction_usd: number;
  features: Record<string, unknown>;
}
```

### State Flow per Turn

1. User types message, hits Enter
2. User message appended to `messages[]`
3. `streaming = true`, `streamingText = ""`
4. `POST /chat` sent with `{message, history, accumulated_features}`
5. **On `reply` event:** `streamingText` set to reply text; `accumulated` merged with `extracted_features`
6. **On `prediction` event:** `pendingPrediction` set
7. **On `token` event:** `streamingText` appended with token text; `await yieldToBrowser()`
8. **On `done` event:** new assistant `Message` committed to `messages[]` (with `prediction` if present); `streamingText = ""`; `streaming = false`
9. **On `error` event:** error message committed as assistant `Message`; streaming ends

### History Construction

Before each request, build `history` from `messages[]`:
```typescript
const history = messages.map(m => ({ role: m.role, content: m.text }));
```

---

## Field Metadata

Used in the PredictionCard to display human-readable labels:

```typescript
const FIELD_META: Record<string, { label: string; unit: string | null }> = {
  GrLivArea:    { label: "Above-Grade Living Area",     unit: "sq ft" },
  OverallQual:  { label: "Overall Quality",             unit: "1–10 scale" },
  YearBuilt:    { label: "Year Built",                  unit: null },
  Neighborhood: { label: "Neighborhood",                unit: null },
  TotalBsmtSF:  { label: "Total Basement Area",         unit: "sq ft" },
  GarageCars:   { label: "Garage Capacity",             unit: "cars" },
  FullBath:     { label: "Full Bathrooms (above grade)", unit: null },
  YearRemodAdd: { label: "Year Last Remodelled",        unit: null },
  Fireplaces:   { label: "Number of Fireplaces",        unit: null },
  LotArea:      { label: "Lot Area",                    unit: "sq ft" },
  MasVnrArea:   { label: "Masonry Veneer Area",         unit: "sq ft" },
  Exterior1st:  { label: "Primary Exterior Material",   unit: null },
};
```

---

## Error Handling

| Scenario | Handling |
|----------|---------|
| Empty message | Prevent send (button disabled) |
| Message > 2000 chars | Prevent send, show red counter |
| HTTP error (non-200) | Show "Something went wrong. Please try again." as assistant bubble |
| `error` SSE event | Show `payload.message` as assistant bubble |
| Network failure (fetch throws) | Show "Could not reach the server. Please check your connection." |
| Stream ends without `done` | Commit whatever text was accumulated |

---

## Environment Variable

```
VITE_API_URL=http://localhost:8000
```

> **Backend setup:** The FastAPI backend runs inside a Docker container via Docker Desktop on Windows.
> Docker Desktop maps the container's port 8000 to `localhost:8000` on the Windows host.
> `http://localhost:8000` is the correct URL — no WSL IP or special network config needed.

Use this in `api.ts`:
```typescript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

---

## Styling Notes

- **Plain CSS only.** Each component has a co-located `.css` file imported at the top of the `.tsx` file. No Tailwind, no CSS-in-JS, no Sass.
- Use descriptive class names scoped by component (e.g., `.message-bubble`, `.message-bubble--user`, `.prediction-card`). BEM-style naming is fine but not required.
- Global resets go in `index.css` (box-sizing, margin, font-family).
- Blinking cursor animation:
  ```css
  .cursor-blink::after {
    content: "▋";
    animation: blink 1s step-start infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }
  ```
- Color palette: `#2563eb` (blue) for user messages and send button, `#f9fafb` (light gray) for page background, `#ffffff` for assistant bubbles, `#eff6ff` (light blue) for prediction card
- Font: `system-ui, -apple-system, sans-serif`
- Responsive: works on mobile (single column is already mobile-friendly)

---

## What NOT to Build

- No routing (single page)
- No authentication
- No local storage persistence (state resets on refresh — that's fine)
- No unit tests (will be added later)
- No error boundary component
- No loading skeleton
- No dark mode
- No animations beyond the typing indicator and cursor blink

---

## Verification Steps

After building, verify these scenarios:

1. **Start the backend:** `docker compose up` in the `real-estate-ai` project (runs on port 8000 via Docker Desktop)
2. **Start the frontend:** `cd real-estate-ui && npm run dev` (runs on port 5173)
3. **Test greeting:** Type "Hello" → should get a conversational reply
4. **Test partial property:** Type "house in North Ames built 1995" → should ask for living area and quality
5. **Test completing fields:** Type "1600 sq ft, quality 7" → should show prediction card + streaming explanation
6. **Verify streaming:** The explanation text should appear word-by-word, not all at once
7. **Test new conversation:** Click "New conversation" → all state resets
8. **Test error state:** Stop the backend, send a message → should show connection error bubble
