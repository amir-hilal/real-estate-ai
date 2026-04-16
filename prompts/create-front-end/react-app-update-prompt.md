# React Frontend App — Update Prompt (SSE Protocol Change)

> Paste this entire file into the VS Code Copilot Chat window where the React app (`real-estate-ui`) is open.

---

## Context

The backend SSE event protocol has changed. The `reply` event no longer exists. All visible text — greetings, follow-up questions, AND explanations — now arrives as word-level `token` events. A new `features` event carries extracted feature metadata (no display text).

**The backend is already updated and running.** You are only updating the frontend.

---

## What Changed in the Backend

### Old protocol

| Event | Payload | Purpose |
|-------|---------|---------|
| `reply` | `{text: string, extracted_features: Record<string, unknown>}` | Full reply text + features in one event |
| `prediction` | `{prediction_usd: number, features: Record<string, unknown>}` | ML prediction |
| `token` | `{text: string}` | Explanation chunks only |
| `done` | `{}` | Stream complete |
| `error` | `{code: string, message: string}` | Error |

### New protocol

| Event | Payload | Purpose |
|-------|---------|---------|
| `features` | `{extracted_features: Record<string, unknown>}` | Feature metadata only (no display text). Merge into `accumulated_features`. |
| `token` | `{text: string}` | ALL visible text — reply words AND explanation chunks |
| `prediction` | `{prediction_usd: number, features: Record<string, unknown>}` | ML prediction (unchanged) |
| `done` | `{}` | Stream complete (unchanged) |
| `error` | `{code: string, message: string}` | Error (unchanged) |

### New event sequences

| Scenario | Events |
|----------|--------|
| Greeting ("Hello") | `features` → `token` × N → `done` |
| Partial property (missing fields) | `features` → `token` × N → `done` |
| Complete property (all fields known) | `features` → `token` × N → `prediction` → `token` × N → `done` |
| Error | `error` |

**Key difference for complete property:** The reply text streams as tokens BEFORE the prediction card, then the explanation streams as tokens AFTER the prediction card. The `prediction` event is the boundary between reply tokens and explanation tokens.

---

## Required Code Changes

### 1. TypeScript types (`src/types/chat.ts`)

Remove the `reply` event type. Add the `features` event type:

```typescript
// REMOVE any type/interface for ReplyEvent or "reply" event handling

// ADD:
interface FeaturesEvent {
  extracted_features: Record<string, unknown>;
}
```

### 2. SSE event dispatcher (`src/hooks/useChat.ts`)

In the event processing loop, replace the `reply` case with `features`:

```typescript
// REMOVE:
case "reply":
  // ... whatever it does with payload.text and payload.extracted_features
  break;

// ADD:
case "features":
  // Merge extracted features into accumulated_features — NO display text
  mergeFeatures(payload.extracted_features);
  break;
```

The `token` case should NOT change — it already appends `payload.text` to `streamingText` with `await yieldToBrowser()`. Since both reply text and explanation text now arrive as `token` events, the existing token handler does all the work.

### 3. State flow update

The `streamingText` accumulation now serves double duty:
- Before `prediction` event: it accumulates the reply text (greeting, follow-up question, or "Got it, estimating now…")
- After `prediction` event: it continues accumulating the explanation text

When `prediction` arrives mid-stream:
1. Commit the reply text accumulated so far as part of the current message
2. Store the prediction
3. Reset `streamingText` to `""` so explanation tokens start fresh
4. Continue appending explanation tokens

When `done` arrives:
- Commit the final assistant message with both the reply text, prediction (if any), and explanation text

### 4. Message structure change

Each committed assistant message may now have three parts:

```typescript
interface Message {
  role: "user" | "assistant";
  text: string;              // The reply text (streamed before prediction)
  prediction?: Prediction;   // The prediction card (if any)
  explanation?: string;       // The explanation text (streamed after prediction)
}
```

Update `MessageBubble` rendering to show these in order: `text` → `PredictionCard` → `explanation`.

For messages without a prediction (greetings, follow-up questions), `text` contains the full reply and `prediction`/`explanation` are undefined.

### 5. History construction

When building `history` for the next request, concatenate the parts:

```typescript
const history = messages.map(m => ({
  role: m.role,
  content: m.explanation ? `${m.text}\n${m.explanation}` : m.text,
}));
```

---

## What Should NOT Change

- SSE parsing logic (`fetch` + `ReadableStream` + `TextDecoder` + `\n\n` splitting) — unchanged
- `yieldToBrowser()` double-`requestAnimationFrame` pattern — unchanged
- `prediction`, `done`, `error` event handling — unchanged (except prediction now triggers a text commit)
- UI layout, styling, components — unchanged
- `PredictionCard`, `TypingIndicator`, `InputBar` — unchanged
- Environment variable (`VITE_API_URL`) — unchanged

---

## Verification Steps

1. **Start the backend:** `docker compose up` in the `real-estate-ai` project (port 8000)
2. **Start the frontend:** `cd real-estate-ui && npm run dev` (port 5173)
3. **Test greeting:** Type "Hello" → reply should stream word-by-word (not appear all at once)
4. **Test partial property:** Type "house in North Ames built 1995" → follow-up question should stream word-by-word
5. **Test complete property:** Type "3-bed house in North Ames, 1600 sq ft, quality 7, built 1995, 2-car garage, full basement 800 sq ft" → reply streams → prediction card appears → explanation streams seamlessly after the card
6. **Verify no seam:** The transition from reply text to explanation text should feel natural — no text collision at the boundary (the prediction card separates them visually)
7. **Test new conversation:** Click "New conversation" → all state resets

---

## Documentation

After completing the code changes, add a `README.md` to the `real-estate-ui` project root with:

1. **Project description** — one paragraph: what the app is, what it does
2. **Stack** — Vite, React 18, TypeScript, plain CSS
3. **Prerequisites** — Node.js version, backend running on port 8000
4. **Getting started** — `npm install`, `npm run dev`, open `http://localhost:5173`
5. **Environment variables** — `VITE_API_URL` (default `http://localhost:8000`)
6. **Project structure** — the directory tree with one-line descriptions per file/folder
7. **API contract** — brief description of `POST /chat` and the SSE event types (`features`, `token`, `prediction`, `done`, `error`) with their payloads
8. **Architecture notes** — client-side state management (`useChat` hook), SSE parsing with `fetch` + `ReadableStream`, `yieldToBrowser` pattern for per-token rendering
