# React Frontend — Add Prompt Version Selector

> Paste this entire file into the VS Code Copilot Chat window where the `real-estate-ui` project is open.

---

## Context

The backend now supports **versioned prompts**. Each version uses a different set of system prompts (chat + explanation) for the LLM, affecting how the AI assistant behaves (e.g., v3 uses full neighborhood names instead of codes). The frontend needs to:

1. Let the user pick which prompt version to use from the header dropdown
2. Send the selected version with every `POST /chat` request
3. Reset the conversation when the version changes

**The backend is already updated and running.** You are only updating the frontend.

---

## API Changes

### `GET /versions` (new endpoint)

```typescript
const response = await fetch(`${API_URL}/versions`);
const data: VersionsResponse = await response.json();
```

**Response:**

```typescript
interface VersionsResponse {
  default: string;  // e.g. "v3"
  versions: Array<{
    version: string;      // e.g. "v1"
    description: string;  // e.g. "Initial chat prompt"
  }>;
}
```

### `POST /chat` (updated request body)

The request body now accepts an optional `prompt_version` field:

```typescript
interface ChatRequest {
  message: string;
  history: ChatMessage[];
  accumulated_features: Record<string, unknown>;
  prompt_version?: string;  // ← NEW — e.g. "v1", "v2", "v3"
}
```

If `prompt_version` is omitted or `null`, the server uses its default (currently `"v3"`).

---

## What to Change

### 1. Add a new dropdown item to `HeaderDropdown`

Add a **"Prompt Version"** submenu/section to the existing dropdown (the one with "New Conversation", "View Insights", "Login"). This item should:

- Show the currently selected version (e.g., "Prompt: v3")
- Expand or cycle through available versions when clicked
- Display the version description as secondary text or tooltip

**Recommended approach — inline version list in the dropdown:**

```
┌─────────────────────────────┐
│ 💬  New Conversation        │
│ 📊  View Insights           │
│ ─────────────────────────── │
│ 🔧  Prompt Version          │
│     ○ v1 — Initial prompt   │
│     ○ v2 — Better enforce…  │
│     ● v3 — Full neighborh…  │  ← selected (radio dot)
│ ─────────────────────────── │
│ 🔒  Login (coming soon)     │
└─────────────────────────────┘
```

- Use radio-style indicators (● selected, ○ unselected)
- The versions should be fetched from `GET /versions` on mount (or when dropdown opens)
- Truncate long descriptions with ellipsis (CSS `text-overflow: ellipsis`)
- The "Prompt Version" label is a non-clickable section header
- Each version item below it IS clickable

### 2. Store the selected version in state

- Add a `promptVersion` state variable (initialize to `null` — server default)
- When a version is selected from the dropdown, update `promptVersion` and **reset the conversation** (clear history, accumulated features, messages) since changing the prompt mid-conversation would be confusing
- Show a brief indication somewhere that the version changed (optional — the reset itself is clear enough)

### 3. Send `prompt_version` in every `POST /chat` call

In the API helper / `useChat` hook / wherever `POST /chat` is called, include the selected version in the request body:

```typescript
const body: ChatRequest = {
  message,
  history,
  accumulated_features: accumulatedFeatures,
  prompt_version: promptVersion,  // ← add this
};
```

If `promptVersion` is `null`, either omit the field or send `null` — both are fine (server uses its default).

### 4. Fetch versions on app mount

In `App.tsx` (or wherever the header is rendered), fetch `GET /versions` once on mount:

```typescript
const [versions, setVersions] = useState<VersionsResponse | null>(null);
const [promptVersion, setPromptVersion] = useState<string | null>(null);

useEffect(() => {
  fetch(`${API_URL}/versions`)
    .then(res => res.json())
    .then((data: VersionsResponse) => {
      setVersions(data);
      setPromptVersion(data.default);  // start with server default
    })
    .catch(err => console.error("Failed to load versions:", err));
}, []);
```

### 5. Update `HeaderDropdown` props

```typescript
interface HeaderDropdownProps {
  onReset: () => void;
  onViewInsights: () => void;
  versions: VersionsResponse | null;     // ← new
  currentVersion: string | null;          // ← new
  onVersionChange: (version: string) => void;  // ← new
}
```

---

## Styling Guidelines

- Version items should be slightly indented under the "Prompt Version" section header
- Use a smaller font size for the description text (e.g., 0.75rem, muted color)
- The selected version should have a visible indicator (filled radio dot, checkmark, or highlighted background)
- Keep consistent with existing dropdown styling (same padding, hover states, etc.)
- The section dividers (horizontal lines) separate the action items from the version selector and from Login

---

## Behavior Summary

| Action | Result |
|--------|--------|
| App loads | Fetch `GET /versions`, set `promptVersion` to server default |
| User selects a different version | Update `promptVersion`, reset conversation |
| User sends a message | `POST /chat` includes `prompt_version` in body |
| `GET /versions` fails | Hide the version section from dropdown, use server default |
| User clicks "New Conversation" | Reset conversation, keep current `promptVersion` |

---

## Files to Modify

- `HeaderDropdown.tsx` — Add version selector section
- `HeaderDropdown.css` — Style version items
- `App.tsx` (or parent of HeaderDropdown) — Add versions state, fetch, pass props
- `api.ts` / `useChat.ts` (wherever POST /chat body is built) — Add `prompt_version` field

**No new files needed** — this extends the existing dropdown component.
