# React Frontend — Add Market Insights Overlay + Header Dropdown

> Paste this entire file into the VS Code Copilot Chat window where the `real-estate-ui` project is open.

---

## Context

The backend now has a `GET /insights` endpoint that returns market data, model performance metrics, neighborhood price comparisons, and feature importances. We want to display this data in a scrollable overlay accessible from a new dropdown menu in the header.

**The backend is already updated and running.** You are only updating the frontend.

---

## Task Summary

1. Replace the "New conversation" button in the header with a **dropdown menu**
2. The dropdown has three items: **New Conversation**, **View Insights**, and **Login** (disabled)
3. Clicking **View Insights** opens a **full-screen scrollable overlay** with charts and stats
4. The overlay fetches data from `GET /insights` on open

---

## API Contract

### `GET /insights`

**Request:** No body. Simple GET.

```typescript
const response = await fetch(`${API_URL}/insights`);
const data: InsightsData = await response.json();
```

**Response shape:**

```typescript
interface InsightsData {
  price_statistics: {
    median: number;        // e.g. 165000
    mean: number;          // e.g. 181457
    std: number;           // e.g. 77327
    percentile_25: number; // e.g. 130000
    percentile_75: number; // e.g. 214975
    median_price_per_sqft: number; // e.g. 120.09
    sample_size: number;   // e.g. 1166
  };
  neighborhoods: Array<{
    code: string;          // e.g. "NridgHt"
    name: string;          // e.g. "Northridge Heights"
    median_price: number;  // e.g. 314813
  }>;  // sorted by median_price descending (25 neighborhoods)
  feature_importances: Array<{
    feature: string;       // e.g. "OverallQual"
    display_name: string;  // e.g. "Overall Quality"
    importance: number;    // e.g. 928.42
  }>;  // sorted by importance descending (12 features)
  model_performance: {
    test_mae: number;      // 17936
    test_rmse: number;     // 29238
    test_r2: number;       // 0.8885
    baseline_mae: number;  // 59568
    improvement_pct: number; // 69.9
  };
}
```

---

## New Files to Create

```
src/
├── components/
│   ├── HeaderDropdown.tsx      ← Dropdown menu (replaces "New conversation" button)
│   ├── HeaderDropdown.css
│   ├── InsightsOverlay.tsx     ← Full-screen scrollable overlay
│   ├── InsightsOverlay.css
│   ├── charts/
│   │   ├── BarChart.tsx        ← Reusable horizontal bar chart (pure CSS, no libraries)
│   │   └── BarChart.css
├── services/
│   └── api.ts                  ← Add fetchInsights() function to existing file
└── types/
    └── chat.ts                 ← Add InsightsData interface to existing file
```

---

## 1. Header Dropdown (`HeaderDropdown.tsx`)

Replace the existing "New conversation" button in the header with a dropdown.

### Behavior

- A single button labeled **"☰ Menu"** (or a hamburger icon) triggers the dropdown
- Clicking the button toggles the dropdown open/closed
- Clicking anywhere outside the dropdown closes it (use `useEffect` with a document click listener)
- Pressing `Escape` closes the dropdown

### Menu Items

| Label | Icon/Emoji | Action | State |
|-------|-----------|--------|-------|
| New Conversation | 💬 | Calls the existing `reset()` function from `useChat` | Always enabled |
| View Insights | 📊 | Opens the insights overlay | Always enabled |
| Login | 🔒 | Nothing (placeholder) | Visually disabled (grayed out, `cursor: not-allowed`) with tooltip text "Coming soon" |

### Styling

- Dropdown appears below the button, right-aligned to the button
- White background, subtle box-shadow (`0 4px 12px rgba(0,0,0,0.1)`), border-radius `8px`
- Each item is a row: emoji + label, padding `10px 16px`, hover background `#f3f4f6`
- Disabled item (Login) has `opacity: 0.5`, no hover effect
- Separator line between "View Insights" and "Login" (a thin `border-top` on the Login item)
- z-index high enough to sit above the chat thread (`z-index: 100`)

### Props

```typescript
interface HeaderDropdownProps {
  onReset: () => void;
  onViewInsights: () => void;
}
```

---

## 2. Insights Overlay (`InsightsOverlay.tsx`)

A full-screen overlay that shows market data with visualizations.

### Layout

- **Backdrop:** fixed position, covers entire viewport, semi-transparent dark background (`rgba(0,0,0,0.5)`)
- **Content panel:** centered, `max-width: 800px`, `max-height: 90vh`, white background, border-radius `12px`, `overflow-y: auto`, padding `32px`
- **Close button:** top-right corner of the panel, `×` character, `position: sticky` at top so it stays visible while scrolling
- Clicking the backdrop (outside the panel) closes the overlay
- Pressing `Escape` closes the overlay

### Content Sections (top to bottom)

#### Section A: Header
- Title: **"Market Insights"**
- Subtitle: "Ames, Iowa · Based on {sample_size} property sales"

#### Section B: Model Performance (highlight cards)

Four stat cards in a 2×2 grid (or 4-column on wide screens, 2-column on narrow):

| Card | Value | Label |
|------|-------|-------|
| 1 | `$17,936` | Prediction Accuracy (MAE) |
| 2 | `88.9%` | Model R² Score |
| 3 | `69.9%` | Improvement Over Baseline |
| 4 | `$120/sq ft` | Median Price per Sq Ft |

**Format the MAE card helpfully:** Show the MAE value as "$17,936" with a sub-label: "Average prediction error". Show R² as a percentage (`test_r2 * 100`, rounded to 1 decimal). Show improvement as `improvement_pct` + "%". Show price per sqft from `price_statistics.median_price_per_sqft`, rounded to nearest dollar.

Card styling: light background (`#f0f9ff`), border-radius `8px`, padding `16px`, the value in large bold text (`1.5rem`), the label in smaller muted text.

#### Section C: Price Distribution Summary

A horizontal stat bar or summary row showing:
- **25th percentile:** $130,000
- **Median:** $165,000
- **75th percentile:** $214,975

Display as three values side by side with labels, possibly with a simple visual indicator (a horizontal bar where the median is marked). Keep it simple — a styled `<div>` with three labeled sections is fine.

#### Section D: What Drives Property Prices (Feature Importance Chart)

A horizontal bar chart showing all 12 features ranked by importance.

- Each bar shows the feature `display_name` on the left, a colored bar proportional to the maximum importance, and no numeric labels (the relative lengths tell the story)
- Bar color: gradient or solid blue (`#2563eb` to `#93c5fd`)
- Top feature (Overall Quality) will have the longest bar — all others are proportional to it
- Title: **"What Drives Property Prices"**
- Subtitle: "Feature importance from the LightGBM model (gain-based)"

**Implementation:** This is a pure-CSS bar chart. Each bar is a `<div>` with `width` set as a percentage of the maximum importance value. No charting library needed.

```tsx
// Example: normalize importances to percentages
const maxImportance = Math.max(...importances.map(f => f.importance));
const widthPct = (item.importance / maxImportance) * 100;
```

#### Section E: Neighborhood Price Comparison

A horizontal bar chart showing all 25 neighborhoods sorted by median price (already sorted from the API).

- Neighborhood `name` (full name, not code) on the left, colored bar on the right
- Bar width proportional to the maximum neighborhood price
- Bar color: a different hue from the feature chart — use green (`#059669` to `#6ee7b7`)
- Title: **"Neighborhood Price Comparison"**
- Subtitle: "Median sale price by neighborhood"
- Optionally show the dollar value at the end of each bar or on hover

Use the same `BarChart` component as Section D (reusable).

#### Section F: Footer Note

Small muted text at the bottom:
> "Based on Ames, Iowa housing data (2006–2010). Prices reflect historical market conditions and are used for demonstration purposes."

### Data Fetching

- Fetch `GET /insights` when the overlay opens (not on page load)
- Show a centered loading spinner/text ("Loading insights...") while fetching
- If fetch fails, show an error message inside the overlay: "Could not load market insights. Please try again."
- Cache the response in component state — if the overlay is closed and reopened, use cached data (don't re-fetch unless it's stale). A simple `useRef` or state variable is sufficient.

### Props

```typescript
interface InsightsOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}
```

---

## 3. Reusable Bar Chart Component (`charts/BarChart.tsx`)

A simple reusable horizontal bar chart built with pure CSS divs.

### Props

```typescript
interface BarChartItem {
  label: string;
  value: number;
  displayValue?: string;  // optional formatted text to show (e.g. "$314,813")
}

interface BarChartProps {
  items: BarChartItem[];
  color?: string;         // bar color, default "#2563eb"
  maxValue?: number;      // if not provided, derived from max item value
}
```

### Rendering

```tsx
<div className="bar-chart">
  {items.map(item => (
    <div className="bar-chart__row" key={item.label}>
      <span className="bar-chart__label">{item.label}</span>
      <div className="bar-chart__track">
        <div
          className="bar-chart__fill"
          style={{ width: `${(item.value / maxValue) * 100}%`, backgroundColor: color }}
        />
      </div>
      {item.displayValue && (
        <span className="bar-chart__value">{item.displayValue}</span>
      )}
    </div>
  ))}
</div>
```

### Styling

- Each row: `display: flex`, `align-items: center`, `gap: 8px`, `margin-bottom: 4px`
- Label: `min-width: 180px` (for neighborhood names), `font-size: 0.85rem`, `text-align: right`
- Track: `flex: 1`, `height: 20px`, `background: #f3f4f6`, `border-radius: 4px`, `overflow: hidden`
- Fill: `height: 100%`, `border-radius: 4px`, `transition: width 0.3s ease`
- Value: `min-width: 80px`, `font-size: 0.8rem`, `color: #6b7280`

---

## 4. Integration into App.tsx

### State Changes

Add to `App.tsx`:

```typescript
const [insightsOpen, setInsightsOpen] = useState(false);
```

### Header Changes

Replace the current "New conversation" button with `HeaderDropdown`:

```tsx
// BEFORE (something like):
<button onClick={reset}>New conversation</button>

// AFTER:
<HeaderDropdown
  onReset={reset}
  onViewInsights={() => setInsightsOpen(true)}
/>
```

### Add Overlay

Render `InsightsOverlay` at the root level (sibling to the main chat layout):

```tsx
<InsightsOverlay
  isOpen={insightsOpen}
  onClose={() => setInsightsOpen(false)}
/>
```

---

## 5. API Service Update (`services/api.ts`)

Add to the existing `api.ts`:

```typescript
export async function fetchInsights(): Promise<InsightsData> {
  const response = await fetch(`${API_URL}/insights`);
  if (!response.ok) {
    throw new Error(`Insights fetch failed: ${response.status}`);
  }
  return response.json();
}
```

---

## 6. Types Update (`types/chat.ts`)

Add to the existing types file:

```typescript
export interface InsightsData {
  price_statistics: {
    median: number;
    mean: number;
    std: number;
    percentile_25: number;
    percentile_75: number;
    median_price_per_sqft: number;
    sample_size: number;
  };
  neighborhoods: Array<{
    code: string;
    name: string;
    median_price: number;
  }>;
  feature_importances: Array<{
    feature: string;
    display_name: string;
    importance: number;
  }>;
  model_performance: {
    test_mae: number;
    test_rmse: number;
    test_r2: number;
    baseline_mae: number;
    improvement_pct: number;
  };
}
```

---

## What Should NOT Change

- Chat functionality — all SSE parsing, token streaming, prediction cards, `useChat` hook — unchanged
- `ChatThread`, `MessageBubble`, `PredictionCard`, `TypingIndicator`, `InputBar` — unchanged
- SSE event handling — unchanged
- Environment variable (`VITE_API_URL`) — unchanged (reused by `fetchInsights`)
- Main chat layout and styling — unchanged (the dropdown replaces one button; the overlay is a sibling)

---

## Styling Notes

- **Plain CSS only** — consistent with the existing app. No Tailwind, no CSS-in-JS.
- The overlay uses `position: fixed` and `z-index: 1000` (above everything)
- The dropdown uses `position: absolute` relative to the header button and `z-index: 100`
- Body scroll should be disabled when the overlay is open (`document.body.style.overflow = 'hidden'` on open, restore on close)
- All new CSS goes in co-located `.css` files imported in the corresponding `.tsx` file
- Use the existing color palette: `#2563eb` (blue), `#f9fafb` (light gray bg), `#f0f9ff` (light blue for cards)
- Responsive: the overlay panel should be `width: 90%` on mobile, `max-width: 800px` on desktop

---

## Verification Steps

1. **Start the backend:** `docker compose up` in the `real-estate-ai` project (port 8000)
2. **Start the frontend:** `cd real-estate-ui && npm run dev` (port 5173)
3. **Test dropdown:** Click the menu button → dropdown appears with 3 items
4. **Test "New Conversation":** Click it → dropdown closes, chat resets (same as old button)
5. **Test "View Insights":** Click it → dropdown closes, overlay opens with loading state, then data renders
6. **Test overlay content:** Scroll through — should see model performance cards, price distribution, feature importance chart, neighborhood comparison chart
7. **Test overlay close:** Click `×` button or click backdrop or press `Escape` → overlay closes
8. **Test Login item:** Should be grayed out, non-clickable, shows "Coming soon" on hover
9. **Test chat still works:** Close overlay, send a message → chat works as before
10. **Test caching:** Open insights, close, reopen → should show instantly (no re-fetch)
