# Mumbai Local — Prediction, Correlation & EDA Design Spec

**Date:** 2026-05-20
**Status:** Approved
**Scope:** 2 new dashboard tabs + 1 Jupyter EDA notebook

---

## Goal

Add three high-signal portfolio features to the Mumbai Local Train Delay Visualizer:
1. **Prediction tab** — Prophet 7-day forecast per station with CI bands (dropdown for all 120 stations)
2. **Correlation tab** — station co-delay Pearson heatmap, top 15 per line, line selector
3. **EDA notebook** — hypothesis-driven analysis: monsoon effect, network cascade, peak signature

---

## Architecture Decisions

### Prediction Tab

**Approach:** Separate background thread (`ForecastCache`) pre-fits Prophet for all 120 stations at startup. Tab callback reads from cache dict; shows spinner if station not yet computed. Mirrors existing anomaly tab pattern.

**Rejected alternatives:**
- On-demand fit per callback: ~8s UI freeze — unacceptable UX
- Persist to DuckDB table: schema migration overhead, overkill for portfolio

### Correlation Tab

**Approach:** On-demand DuckDB `CORR()` self-join query, pivot in Polars. Query runs in ~200ms — no pre-computation needed.

**Rejected alternatives:**
- Load raw data into Polars `.corr()`: unnecessarily pulls millions of rows
- Pre-compute at startup: adds cold-start time with no UX benefit

---

## Feature 1: Prediction Tab

### New Files

**`analysis/forecasting.py`**
- `ForecastCache` class
  - `build(store: DelayStore)` — background entry point; iterates all stations, fits Prophet, stores results
  - `get(station: str) -> tuple[pd.DataFrame, pd.DataFrame] | None` — returns `(history_30d, forecast_7d)` or `None` if not ready
  - Thread-safe: `threading.Lock` on internal dict
- Internal: `_daily_avg(store, station)` — wraps `DelayStore.daily_avg(station)`

**New `DelayStore` method in `pipeline/store.py`:**
```python
def daily_avg(self, station: str) -> pl.DataFrame:
    """Daily avg delay for a station (all hours aggregated). Used by forecasting."""
    # SELECT date, AVG(avg_delay) AS avg_delay FROM delays
    # WHERE station_name = ? GROUP BY date ORDER BY date
```

### Modified Files

**`dashboard/charts.py`** — add `make_forecast_chart(station, history_df, forecast_df) -> go.Figure`
- 30d actual: solid line, `#457B9D`
- 7d forecast: dashed line, `#E63946`
- CI band: `fill='tonexty'` between `yhat_lower` / `yhat_upper` traces, semi-transparent
- Dark theme via `_dark_layout()`

**`dashboard/app.py`**
- Import `ForecastCache` from `analysis.forecasting`
- Start `threading.Thread(target=_forecast_cache.build, args=(store,), daemon=True)` after store init
- Add `dcc.Tab(label="Prediction", value="tab-prediction")` to tabs list
- `_render_prediction_tab()`: station `dcc.Dropdown` + `dcc.Interval(id="pred-poll", interval=10_000)` + `html.Div(id="pred-content")`
- `@app.callback` on `(pred-poll, pred-station-dropdown)` → render chart or spinner

### Data Flow
```
startup → ForecastCache.build(store) in daemon thread
         → for each station:
             daily_avg(station) → Prophet.fit(ds, y) → model.predict(30d future)
             → cache[station] = (history_30d_df, forecast_df)
tab load → dcc.Dropdown populated from store stations list
callback → cache.get(station):
           None  → spinner (poll every 10s)
           found → make_forecast_chart(station, history, forecast) → dcc.Graph
```

---

## Feature 2: Correlation Tab

### New Files

**`analysis/correlation.py`**
- `station_correlation(store: DelayStore, line: str, n: int = 15) -> tuple[list[str], list[list[float]]]`
  - Step 1: get top-N stations for line (reuse `store.worst_stations(line, n)`)
  - Step 2: DuckDB self-join `CORR()` query for those N stations
  - Step 3: Polars pivot → N×N matrix
  - Returns `(station_list, corr_matrix)` for direct use in chart

**SQL pattern:**
```sql
SELECT a.station_name AS station_a,
       b.station_name AS station_b,
       CORR(a.avg_delay, b.avg_delay) AS pearson_r
FROM delays a
JOIN delays b ON a.date = b.date AND a.hour = b.hour
WHERE a.line = ? AND b.line = ?
  AND a.station_name IN (...)
  AND b.station_name IN (...)
GROUP BY a.station_name, b.station_name
```

### Modified Files

**`dashboard/charts.py`** — add `make_correlation_heatmap(stations, corr_matrix) -> go.Figure`
- `go.Heatmap` with `RdBu` colorscale, `zmin=-1`, `zmax=1`
- Diagonal forced to 1.0
- Hover: `"station_a vs station_b: r={z:.2f}"`
- Dark theme

**`dashboard/app.py`**
- Add `dcc.Tab(label="Correlation", value="tab-correlation")`
- `_render_correlation_tab()`: line `dcc.Dropdown` (Central/Western/Harbour) + `dcc.Graph`
- `@app.callback` on line dropdown → run `station_correlation()` → `make_correlation_heatmap()`

---

## Feature 3: EDA Notebook

**Path:** `notebooks/eda_mumbai_delays.ipynb`

### Structure

**Cell block 1: Setup**
- Imports: `duckdb`, `polars`, `plotly.express`, `analysis.*`
- Connect to `delays.duckdb`

**Cell block 2: Hypothesis 1 — Monsoon Effect**
- Markdown: "Do monsoon months (Jun–Sep) produce significantly higher delays than dry months?"
- Code: `monsoon_vs_dry_pivot(store)` → Polars DataFrame
- Chart: grouped bar — monsoon_avg vs dry_avg per station, colored by line
- Markdown finding: "Central line shows 1.4× monsoon ratio; Harbour 1.1× — topology drives sensitivity"

**Cell block 3: Hypothesis 2 — Network Cascade**
- Markdown: "Does Dadar delay predict downstream station delays in the same hour?"
- Code: DuckDB self-join — Dadar avg_delay vs each other Central station, same date+hour
- Chart: scatter plot with regression line, Pearson r in title
- Markdown finding: "Dadar–CSMT r≈0.7 (p<0.01) — upstream cascade confirmed; maintenance alone insufficient"

**Cell block 4: Hypothesis 3 — Peak Hour Signature**
- Markdown: "Is morning peak structurally worse than evening peak, or is evening more variable?"
- Code: `station_delay_matrix()` filtered to hours 7–9 and 17–19, Polars groupby
- Chart: violin plot — morning vs evening delay distributions
- Markdown finding: "Evening peak shows 40% higher variance — incident-driven, not structural congestion"

**Cell block 5: Summary**
- Markdown table: hypothesis | finding | SQL pattern used | business implication

---

## File Change Summary

| File | Change |
|------|--------|
| `analysis/forecasting.py` | New — `ForecastCache` |
| `analysis/correlation.py` | New — `station_correlation()` |
| `pipeline/store.py` | Add `daily_avg()` method |
| `dashboard/charts.py` | Add `make_forecast_chart()`, `make_correlation_heatmap()` |
| `dashboard/app.py` | Add 2 tabs, 2 render functions, 2 callbacks, start forecast thread |
| `notebooks/eda_mumbai_delays.ipynb` | New — 3-hypothesis EDA |

---

## Success Criteria

- Prediction tab: chart renders for any station within 10s of tab click (after warmup); 7d forecast visible with CI band; spinner shown during warmup
- Correlation tab: heatmap renders in <1s on tab click; color gradient readable; line dropdown switches between lines
- EDA notebook: all cells execute top-to-bottom without error; each hypothesis block has SQL → chart → finding
- All existing tests pass; `uv run pytest` green
- No regressions on existing 7 tabs
