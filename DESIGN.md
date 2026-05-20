# Design System — Mumbai Local Train Delay Visualizer

## Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `_DARK` | `#1a1a2e` | Page background |
| `_CARD_BG` | `#16213e` | Card / panel background, tab bar |
| `_TEXT` | `#eaeaea` | Primary text |
| `_MUTED` | `#888888` | Secondary text, axis labels |
| `Central` | `#E63946` | Central line accent, primary CTA |
| `Western` | `#457B9D` | Western line accent |
| `Harbour` | `#2A9D8F` | Harbour line accent, success states |
| `MEDIUM` | `#E9C46A` | Warning / medium severity |
| `HIGH` | `#E63946` | Error / high severity (same as Central) |
| `LOW` | `#2A9D8F` | On-time / low severity (same as Harbour) |

## Delay Severity Scale

| Range | Color | Label |
|-------|-------|-------|
| ≤ 2 min | `#2A9D8F` (green) | On time |
| 2–5 min | orange | Minor delay |
| > 5 min | `#E63946` (red) | Severe delay |

## Typography

- Font family: `Inter, sans-serif`
- H1 / dashboard title: `22px`, color `#eaeaea`
- H3 / section headings: default browser size, color varies by context
- Body text helper `_text()`: `14px` default, configurable size and color
- Subtitle / meta: `13px`, color `#888`

## Spacing & Layout

- Header padding: `16px 24px`
- Tab content padding: `16px`
- Card padding: `16px`, border-radius: `8px`, margin-bottom: `12px`
- Card background: `#16213e`

## Component Patterns

### `_card(children, style=None)`
Wraps content in a dark card. Use for every logical content block.
```python
_card([html.P("content")])
_card([...], style={"borderTop": "4px solid #E63946"})  # severity accent on top
```

**Severity accent:** Use `borderTop` (not `borderLeft`) with a 4px solid line in the severity color.

### `_text(content, size="14px", color="#eaeaea")`
Renders a paragraph with consistent dark-theme styling.

### Dropdowns
```python
dcc.Dropdown(..., style={"width": "300px", "display": "inline-block"})
```
Note: fixed-width (P3 TODO — mobile responsive deferred).

### Loading States
Wrap async/slow content in `dcc.Loading`:
```python
dcc.Loading(type="circle", color="#E63946", children=html.Div(id="content"))
```

### Map iframe
```python
html.Iframe(srcDoc=map_html, style={"width": "100%", "height": "600px", "border": "none"})
```

## Error States

Never expose raw Python exceptions to users. Use friendly messages:
- No data: `"No data available."` (color `#888`)
- Feature unavailable: `"<Feature> unavailable."` (color `#888`)
- Log the real exception via `logger.exception(...)` server-side.

## Map

- Tiles: CartoDB `dark_matter`
- Center: `[19.0760, 72.8777]` (Mumbai), zoom 11
- Station markers: `CircleMarker`, radius 6, fill color = delay severity, border = line color
- Legend: fixed position, bottom-left, `#1a1a2e` background

## Tabs

7 tabs in order: Live Map · Heatmap · Rankings · Anomaly Alerts · Line Comparison · Data Quality · Business Insights

Tab bar: background `#16213e`, primary (active) `#E63946`, border `#1a1a2e`.
