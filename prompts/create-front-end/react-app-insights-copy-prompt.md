# Prompt: Update Insights Overlay Copy for Non-Technical Audience

Paste this prompt into GitHub Copilot Chat in the real-estate-ui project.

---

Update the copy inside the Market Insights overlay so it reads clearly for a non-technical audience (home buyers, not data scientists). Do not change any logic, layout, CSS classes, or data. Only change visible text strings.

Here is the current JSX for the overlay content. Apply exactly the text changes listed below:

---

## Section B — Model Performance Cards

Current:
```
<span className="insights-card__label">Prediction Accuracy (MAE)</span>
<span className="insights-card__label">Average prediction error</span>
```
Replace with:
```
<span className="insights-card__label">Typical Estimate Error</span>
<span className="insights-card__label">How far off our estimates usually are</span>
```

Current:
```
<span className="insights-card__label">Model R² Score</span>
```
Replace with:
```
<span className="insights-card__label">Prediction Accuracy</span>
```

Current:
```
<span className="insights-card__label">Improvement Over Baseline</span>
```
Replace with:
```
<span className="insights-card__label">Better Than Guessing</span>
```

(Keep the `$X/sq ft` card and its label exactly as-is — it is already clear.)

---

## Section C — Price Distribution Labels

Current:
```
<span className="price-distribution__label">25th Percentile</span>
```
Replace with:
```
<span className="price-distribution__label">Budget Range</span>
```

Current:
```
<span className="price-distribution__label">Median</span>
```
Replace with:
```
<span className="price-distribution__label">Typical Home</span>
```

Current:
```
<span className="price-distribution__label">75th Percentile</span>
```
Replace with:
```
<span className="price-distribution__label">Premium Range</span>
```

---

## Section D — Feature Importance Subtitle

Current:
```
<p className="insights-section__subtitle">Feature importance from the LightGBM model (gain-based)</p>
```
Replace with:
```
<p className="insights-section__subtitle">How much each factor influences the final price estimate</p>
```

---

## Section E — Neighborhood Subtitle

Current:
```
<p className="insights-section__subtitle">Median sale price by neighborhood</p>
```
Replace with:
```
<p className="insights-section__subtitle">Typical sale price in each neighborhood</p>
```

---

## No other changes

- Do not change section titles ("Market Insights", "Price Distribution", "What Drives Property Prices", "Neighborhood Price Comparison")
- Do not change the footer text
- Do not touch any className, style, logic, or data binding
- Do not move or restructure any JSX

---

## Version selector descriptions (separate component)

The version selector dropdown displays a `description` field from the `/versions` API. These descriptions are already updated on the server side. No frontend change needed for the descriptions themselves.

If the version selector shows a label like "AI Version" or "Prompt Version", change it to:

```
Conversation Style
```

This label should appear above or beside the dropdown, wherever it currently says "AI Version", "Prompt Version", or similar.
