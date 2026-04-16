# React Frontend — Fix Duplicate Message in History

> Paste this into the VS Code Copilot Chat window where the `real-estate-ui` project is open.

---

## Bug

When sending a message to `POST /chat`, the frontend is including the **current user message** in both the `message` field AND as the last entry in the `history` array. This sends the same text to the LLM twice, which confuses it and causes extraction failures.

### What the backend receives now (WRONG):

```json
{
  "message": "3-bedroom house in North Ames, 1600 sq ft...",
  "history": [
    { "role": "user", "content": "3-bedroom house in North Ames, 1600 sq ft..." }
  ],
  "accumulated_features": {}
}
```

### What the backend should receive (CORRECT):

```json
{
  "message": "3-bedroom house in North Ames, 1600 sq ft...",
  "history": [],
  "accumulated_features": {}
}
```

## The Rule

`history` is the **past conversation** — messages from previous turns that are already committed. The current user message goes in `message` only. The backend appends it to the LLM context itself.

### Correct payload for the FIRST message:

```json
{
  "message": "3-bedroom house in North Ames...",
  "history": [],
  "accumulated_features": {}
}
```

### Correct payload for the SECOND message (after one exchange):

```json
{
  "message": "confirm",
  "history": [
    { "role": "user", "content": "3-bedroom house in North Ames..." },
    { "role": "assistant", "content": "Thanks for the details! Just to confirm..." }
  ],
  "accumulated_features": { "GrLivArea": 1600, "OverallQual": 7, "YearBuilt": 1995, "Neighborhood": "NAmes" }
}
```

### Correct payload for the THIRD message:

```json
{
  "message": "yes, go ahead",
  "history": [
    { "role": "user", "content": "3-bedroom house in North Ames..." },
    { "role": "assistant", "content": "Thanks for the details! Just to confirm..." },
    { "role": "user", "content": "confirm" },
    { "role": "assistant", "content": "Got it! Estimating now..." }
  ],
  "accumulated_features": { "GrLivArea": 1600, "OverallQual": 7, "YearBuilt": 1995, "Neighborhood": "NAmes", "TotalBsmtSF": 800, "GarageCars": 2 }
}
```

## Your Task

1. Find where the `POST /chat` request body is assembled (likely in a hook like `useChat.ts` or a service file).

2. Check how `history` is built before sending. The bug is that the current user message is being added to `history` (or to the messages state) **before** the fetch call, so it ends up in both `message` and `history`.

3. Fix it so that:
   - `message` = the current user input (string)
   - `history` = all **previously committed** user + assistant messages (does NOT include the current message being sent)
   - `accumulated_features` = the latest merged features from all previous `features` events

4. The typical fix is to capture the history snapshot **before** appending the new user message to the UI's messages state:

   ```typescript
   // BEFORE sending — snapshot history from committed messages only
   const historySnapshot = messages
     .filter(m => m.role === "user" || m.role === "assistant")
     .map(m => ({ role: m.role, content: m.text }));

   // Add user message to UI state (for display)
   setMessages(prev => [...prev, { role: "user", text: input }]);

   // Send request with history snapshot (does NOT include the just-added message)
   const response = await fetch("/chat", {
     method: "POST",
     body: JSON.stringify({
       message: input,
       history: historySnapshot,      // past messages only
       accumulated_features: features, // from previous features events
     }),
   });
   ```

   The key: snapshot `history` from the state **before** the optimistic UI update that adds the current user message.

## Verification

After fixing, open browser DevTools → Network tab → click the test message button. Check the request payload:

- **First message:** `history` should be `[]`
- **Second message:** `history` should have exactly 2 entries (the first user + first assistant)
- The current message should NEVER appear in `history`
