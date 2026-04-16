# React Frontend — Debugging Prompt (SSE Event Loop Fix)

> Paste this into the VS Code Copilot Chat window where the `real-estate-ui` project is open.

---

## Problem

The backend is confirmed working correctly — 5/5 curl requests emit exactly 1 `prediction` event. The sequence is always:

```
features → token × N (reply) → prediction → token × N (explanation) → done
```

The frontend intermittently does NOT show the prediction card. The `yieldToBrowser()` was added to the prediction handler, which helped (1/4 success), but the problem persists.

---

## Root Cause

The SSE parser reads chunks from the network, splits on `\n\n`, and processes events in a `for` loop:

```typescript
const parts = buffer.split("\n\n");
buffer = parts.pop()!;

for (const part of parts) {
  const { eventType, payload } = parseSSE(part);
  switch (eventType) {
    case "token": ...
    case "prediction": ...
    // etc.
  }
}
```

**The problem:** When `prediction` and the first few `token` events (explanation chunks) arrive in the **same TCP chunk** — which happens frequently because the backend yields them back-to-back — the `for` loop processes ALL of them in sequence. Even though `prediction` calls `await yieldToBrowser()`, the `for` loop **does not await it** because the loop itself is synchronous (`for...of` doesn't pause for awaits in the switch body unless the entire loop body is awaited).

Check your code: is the event processing loop `for (const part of parts)` or `for await`? If it's a regular `for` loop inside an `async function`, the `await yieldToBrowser()` in the `token` and `prediction` handlers might not actually pause the loop — it depends on whether the `await` is inside the loop body or in a nested function.

**The fix must ensure:** After processing a `prediction` event, control returns to the browser (flush React state) before processing ANY subsequent events from the same chunk.

---

## The Fix

The event processing must `await` the yield for EVERY event that calls `yieldToBrowser()`. The simplest pattern:

```typescript
// Process events ONE AT A TIME with yields
async function processEvents(events: string[]) {
  for (const part of events) {
    const { eventType, payload } = parseSSE(part);
    
    switch (eventType) {
      case "features":
        // merge features, no display
        break;

      case "token": {
        if (receivedPrediction) {
          explanationText += payload.text;
        } else {
          replyText += payload.text;
        }
        setStreamingText(receivedPrediction ? explanationText : replyText);
        await yieldToBrowser();  // MUST be awaited by the for loop
        break;
      }

      case "prediction": {
        currentPrediction = payload;
        receivedPrediction = true;
        setPendingPrediction(payload);
        setStreamingText("");
        await yieldToBrowser();  // MUST be awaited — flush prediction card render
        break;
      }

      case "done": {
        // commit message
        break;
      }

      case "error": {
        // handle error
        break;
      }
    }
  }
}
```

**Critical check:** The `for` loop must be a regular `for` loop in an `async` function where `await` actually pauses iteration. If the loop is inside a `.then()` callback or a non-async function, `await` won't work as expected.

**Also check:** The outer `while (true)` read loop. It should look like:

```typescript
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });

  const parts = buffer.split("\n\n");
  buffer = parts.pop()!;

  // Process events — MUST await this
  for (const part of parts) {
    // ... switch with awaits inside ...
  }
}
```

Since the outer loop already uses `await reader.read()`, and the inner `for` loop is in the same `async` function scope, `await yieldToBrowser()` inside the `for` body will correctly pause the loop.

**If your inner event processing is extracted to a separate function**, make sure that function is `async` and that you `await` the call to it.

---

## Verification

After fixing, test with this exact message 5 times in a row (click "New conversation" between each):

```
3-bedroom house in North Ames, 1600 sq ft, quality 7, built 1995, 2-car garage, full basement 800 sq ft
```

**Expected result ALL 5 times:**
1. Reply text streams word-by-word
2. Prediction card appears (e.g., ~$191,000)
3. Explanation text streams word-by-word after the card

**If any of the 5 attempts fails to show the prediction card, the fix is incomplete.**

Also test:
- "Hello" → streamed text only, no prediction card
- "house in North Ames built 1995" → follow-up question, no prediction card
