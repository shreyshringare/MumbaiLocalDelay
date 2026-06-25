# React Frontend Migration Design
**Date:** 2026-06-25  
**Project:** Mumbai Local Train Delay Visualizer  
**Scope:** Migrate presentation layer from Plotly Dash → React (Vite + TypeScript). Data layer (DuckDB, Prophet, FastAPI) unchanged.

---

## 1. API Contract

### Existing endpoints (no changes)

| Endpoint | Response type | Consumer |
|---|---|---|
| `GET /api/map-data` | `StationDelay[]` | MapTab |
| `GET /api/heatmap?station=` | `HeatmapResponse` (7×24 matrix) | HeatmapTab |
| `GET /api/rankings?line=&period=` | `RankingEntry[]` | RankingsTab, Excel export |
| `GET /api/anomalies` | `AnomalyEntry[]` | AnomalyTab |
| `GET /api/line-trend?line=` | `LineTrendPoint[]` | LineComparisonTab |
| `GET /api/quality` | `QualityEntry[]` | QualityTab |
| `GET /api/insights` | `InsightsResponse` | DashboardTab KPI chips |
| `GET /api/forecast?station=` | `ForecastPoint[] \| {status:"warming"}` | PredictionTab |
| `GET /api/correlation?line=` | `CorrelationResponse` | CorrelationTab |
| `GET /api/methodology` | `Record<string,unknown>` | MethodologyTab |
| `GET /api/export/excel` | binary `.xlsx` | InsightsTab export button |
| `POST /api/ask` | `{sql, result, answer}` | AskAITab |

### New endpoints

**`GET /api/wave-data?line=Central`**
```typescript
interface WaveStation {
  station_name: string
  line_order: number      // position along line, 0-based
  delays: number[]        // length 24, index = hour (0=midnight)
}
// Returns WaveStation[] — top 15 stations by avg delay, ordered by line_order
```
Backend: new `store.wave_data(line: str)` DuckDB query. Aggregates heatmap data across top 15 stations by all-time avg delay per line (not peak-period only). Canvas constants: `PADDING_LEFT=120, PADDING_RIGHT=40, PADDING_TOP=8, PADDING_BOTTOM=24`.

**`GET /api/forecast/status`**
```typescript
interface ForecastStatus {
  fitted: number    // stations fitted so far
  total: number     // total stations (120)
  ready: boolean
}
```
Backend: 2-line FastAPI route reading from the existing `ForecastCache` background thread counter.

---

## 2. Tab Architecture

### Tab order (Dashboard is new default landing)

```
Dashboard ★ | Station Map | Heatmap | Rankings | Anomaly Alerts |
Line Comparison | Prediction | Correlation | Data Quality |
Business Insights | Methodology | Ask AI
```

`App.tsx` change: `useState<TabId>('dashboard')` (was `'map'`).

### New component: `DashboardTab`

Replaces nothing — new tab inserted at index 0. Contains:
- Canvas delay wave centerpiece (`WaveCanvas` component)
- Line selector (Central / Western / Harbour)
- Time slider + Play button
- KPI chips (reuse `InsightsResponse` from `/api/insights`)
- Data provenance label (permanent, below canvas title)

### InsightsTab

KPI chips move to DashboardTab. InsightsTab retains only:
- Export to Excel button
- Any remaining business narrative text

---

## 3. Canvas Centerpiece — `WaveCanvas.tsx`

### Props
```typescript
interface WaveCanvasProps {
  data: WaveStation[]
  width: number         // from ResizeObserver on container
  height: number        // fixed 300px
  playbackHour: number  // 0–23, controlled by parent slider
  isPlaying: boolean
}
```

### D3 usage (calculation only — no DOM)
```typescript
const xScale = d3.scaleLinear([0, 23], [PADDING_LEFT, width - PADDING_RIGHT])
const yScale = d3.scaleBand(stationNames, [PADDING_TOP, height - PADDING_BOTTOM])
const colorScale = d3.scaleSequential(d3.interpolateRdYlGn).domain([8, 0])
// domain inverted: 8 min delay = red, 0 min = green
```

D3 never calls `.select()`, `.append()`, or any DOM method. Canvas is owned by `useRef`, drawn in `useEffect`.

### RAF loop
```typescript
useEffect(() => {
  const ctx = canvasRef.current!.getContext('2d')!
  let animFrame: number
  let hour = playbackHour

  function draw() {
    ctx.clearRect(0, 0, width, height)
    drawAxes(ctx, xScale, yScale, stationNames)
    drawWaveBands(ctx, data, xScale, yScale, colorScale)
    drawTimeCursor(ctx, xScale, hour)
    if (isPlaying) {
      hour = (hour + 0.02) % 24   // ~1 real-second per simulated hour
      animFrame = requestAnimationFrame(draw)
    }
  }

  animFrame = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(animFrame)
}, [data, width, playbackHour, isPlaying])
```

### Wave band rendering
Each station row = filled rect spanning the full x-axis. Fill color per x-pixel column:
```typescript
for (let px = xLeft; px < xRight; px++) {
  const hour = Math.floor(xScale.invert(px))
  ctx.fillStyle = colorScale(data[stationIdx].delays[hour])
  ctx.fillRect(px, yTop, 1, rowHeight)
}
```

### Responsive
`ResizeObserver` on container `<div ref={containerRef}>` updates `width` prop → triggers canvas redraw.

### DashboardTab structure
```typescript
export function DashboardTab() {
  const [line, setLine] = useState<'Central'|'Western'|'Harbour'>('Central')
  const [playbackHour, setPlaybackHour] = useState(8)
  const [isPlaying, setIsPlaying] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(800)

  const { data } = useQuery({
    queryKey: ['wave-data', line],
    queryFn: () => api.waveData(line),
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width))
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])
  // ...
}
```

---

## 4. Data Provenance

### Placement rule
Permanent subtitle directly below the canvas title. Always visible. Never in a tooltip, footer, or About page alone.

**Text:** `Simulated delays · calibrated on real Indian Railways timetable · not live data`  
**Color:** `#666` (readable but subordinate to the title)

### Methodology tab fix
`api/routers/meta.py` `get_methodology()` currently says *"Train delay data sourced from Mumbai Railway Vikas Corporation (MRVC)"* — factually wrong. Must be corrected to match the simulated/calibrated framing before the Dash removal is complete.

---

## 5. Loading Sequences

### Fast tabs (DuckDB — <300ms response)
Framer Motion `AnimatePresence` skeleton → content:
```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={activeTab}
    initial={{ opacity: 0, y: 6 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -6 }}
    transition={{ duration: 0.2 }}
  >
    {renderTab(activeTab)}
  </motion.div>
</AnimatePresence>
```
Individual tabs show a CSS shimmer skeleton while `isLoading` is true.

### PredictionTab — Prophet cold-start (2–10 min)
Poll `GET /api/forecast/status` every 5 seconds while `ready: false`. Show:
- Progress bar: `fitted / total` station count
- Label: `"Computing forecasts — 42 / 120 stations · ~4 min remaining"`
- Estimated time: `(total - fitted) * avg_seconds_per_station`

When `ready: true`, invalidate react-query cache for `['forecast', station]` and render the chart.

```typescript
const { data: status } = useQuery({
  queryKey: ['forecast-status'],
  queryFn: api.forecastStatus,
  refetchInterval: (data) => data?.ready ? false : 5000,
})
```

---

## 6. Dash Removal Sequence

Execute in this order — do not skip steps:

**Step 1 — Untangle `make_business_insights`**
- Move `make_business_insights` from `dashboard/charts.py` → `analysis/insights.py`
- Update `api/routers/meta.py` import: `from analysis.insights import make_business_insights`
- Fix methodology text in `get_methodology()` (simulated framing)
- Verify `/api/insights` still returns correct data

**Step 2 — Verify all 11 React tabs work**
- Each tab fetches from FastAPI only
- No Dash callbacks invoked
- Run `tests/test_api.py` against live server (note: file is currently untracked — commit it before this step)

**Step 3 — Delete Dash**
- `git rm -r dashboard/`
- Remove Python deps: `dash`, `plotly` from `pyproject.toml` (Python only — `react-plotly.js` is npm, unaffected)
- Verify FastAPI starts without import errors

---

## 7. Tech Stack Summary

| Layer | Technology | Notes |
|---|---|---|
| Build | Vite + React 18 + TypeScript | Keep existing scaffold |
| Data fetching | TanStack Query v5 | Already wired |
| Charts | react-plotly.js | All tabs except DashboardTab |
| Centerpiece | HTML Canvas + `useRef` | `WaveCanvas.tsx` |
| Math/scales | d3-scale, d3-array | Calculation only, no DOM |
| UI transitions | Framer Motion | Tab transitions + skeleton fade |
| Styling | Inline styles (existing pattern) | No Tailwind introduced |
| Backend | FastAPI + Uvicorn | Unchanged |
| Data | DuckDB + Polars | Unchanged |
| Forecasting | Prophet | Unchanged |
| AI | Anthropic Claude (ask endpoint) | Unchanged |

---

## 8. Out of Scope

- Authentication / API keys on public endpoints (documented in CONCERNS.md, deferred)
- MapTab implementation (untracked `MapTab.tsx` exists, not part of this migration phase)
- Rate limiting on `/api/ask` (Anthropic spend risk — separate concern)
- Next.js migration (Vite stays)
- Tailwind (inline styles stay for consistency with existing tabs)
