# Mumbai Local Delay Visualizer — 10/10 Portfolio Upgrade

**Date:** 2026-05-20  
**Scope:** Today (resume submission tomorrow) — Tier 1 data realism + Tier 2 SQL depth + Tier 4 storytelling  
**Deferred:** Prediction tab, Correlation tab, Jupyter notebook, /health endpoint  

---

## Goal

Upgrade the project from ~7/10 to 9/10 for DA/DS hiring. Fix the three gaps visible to a recruiter in 30 seconds:
1. Data Quality tab shows identical row counts for every station (obviously fake)
2. SQL showcase missing YoY, seasonal, and trend-deviation patterns
3. README lacks narrative — findings listed but not interpreted

---

## Section 1: Data Realism

### Problem
`DelaySimulator.generate()` produces identical rows per station per day. Every station has 8,784 rows and 366 unique days. Real operational data has gaps, incidents, and station-level personality.

### Changes to `pipeline/ingest/simulator.py`

**1. Station personality multiplier**
- Each station gets a deterministic float multiplier in [0.85, 1.25] seeded by `hash(station_name) % 1000 / 1000`
- Applied to base mean delay — Dadar always worse than Vidyavihar across all dates
- Seeded (not random) so re-runs produce consistent results

**2. Missing day probability**
- Each (station, date) pair has a 4% chance of being skipped entirely
- Implemented as: `if random.random() < 0.04: continue` inside the date loop, per station
- Results in different row counts per station (roughly 345–365 days each)

**3. Day-of-week multipliers**
```
Monday:    1.15x  (week startup chaos)
Tuesday:   1.05x
Wednesday: 1.00x  (baseline)
Thursday:  1.02x
Friday:    1.10x  (end-of-week crowding)
Saturday:  0.80x
Sunday:    0.65x
```

**4. Incident injection**
- Per line per month: inject 2 incidents on random dates
- Incident: one random station on that line gets 2.8x normal delay for 3 consecutive days
- Incidents are seeded by `(year, month, line)` for reproducibility
- Creates visible spikes in heatmap and triggers Prophet anomaly detection

**5. Re-seed**
- Run `scripts/seed_db.py` locally after simulator changes
- Commit regenerated `delays.duckdb` (or trigger Render redeploy via push)

### Expected output
Data Quality tab: stations show 340–365 unique days, row counts 7,800–8,760 (not all 8,784). Pipeline Health still ~100% (all stations have recent data). Heatmap shows visible incident spikes.

---

## Section 2: SQL Depth

### New functions in `analysis/sql_queries.py`

**`yoy_delay_change(store)`**
- YoY % change per station: 2023 vs 2024 avg delay
- Pattern: conditional aggregation by year + percent difference column
- Interview analog: "Compare this year's revenue vs last year by product"

**`monsoon_vs_dry_pivot(store)`**
- Monsoon months (Jun–Sep) vs dry season (Oct–May) avg delay per station
- Columns: station, line, monsoon_avg, dry_avg, monsoon_ratio
- Pattern: conditional aggregation with CASE WHEN MONTH()
- Interview analog: "Compare Q1 vs Q3 performance by region"

**`rolling_deviation(store, line)`**
- 7-day rolling avg vs 30-day baseline per station
- Deviation column = rolling_7d / baseline_30d — values > 1.2 flag worsening trend
- Pattern: nested window functions, ratio-based flagging
- Interview analog: "Flag products whose 7-day sales deviate >20% from 30-day baseline"

### New file: `sql_showcase.sql`

10 queries at project root with analyst commentary format:
```sql
-- QUERY: [name]
-- ANSWERS: [business question]
-- PATTERN: [SQL concept]
-- STAKEHOLDER USE: [what a manager does with this output]
<query>
```

Queries covered:
1. Top-N per group (ROW_NUMBER + PARTITION BY)
2. Week-over-week change (LAG + CTE)
3. Conditional aggregation (peak vs off-peak pivot)
4. Rolling 7-day average (ROWS BETWEEN window)
5. Percentile delays (PERCENTILE_CONT)
6. YoY comparison (year conditional aggregation)
7. Monsoon vs dry pivot (CASE WHEN MONTH)
8. Rolling deviation flag (nested windows + ratio)
9. Station correlation proxy (self-join on same date/hour)
10. Economic impact estimate (delay × passenger volume derived column)

---

## Section 3: README Storytelling

### New "The Data Story" section (after Key Findings table)

Narrative covering:
- **Why Dadar CR is worst**: Central line junction with cross-platform transfers from Harbour line; convergence point means any upstream delay cascades. Not a maintenance problem — a network topology problem.
- **What the monsoon spike means**: 40% delay increase × 7.5M daily passengers = ~450,000 additional delay-hours per day in June–September. At median Mumbai wage of ₹250/hr, this is ~₹11 crore/day in lost productivity.
- **Business recommendation**: Infrastructure priority score = avg_delay × daily_passenger_volume. Dadar and CSMT should be prioritized not just because they're worst, but because delay × volume product is highest.

### Corrections
- Remove bare "87% anomaly precision" claim — replace with: "Prophet evaluated on 20% held-out dates; anomaly recall measured against manually-labeled incident days in simulator"
- README tech stack already updated to Render (done)

### "Ongoing Development" section
```
## Ongoing Development
- **Prediction tab** — Prophet 7-day delay forecast per station with 95% CI bands
- **Correlation tab** — Station co-delay heatmap: does a Dadar spike cascade to Kurla?
- **EDA Notebook** — Jupyter walkthrough of hypothesis → SQL → finding pattern
```

---

## Deferred (post-apply)

| Feature | Tier | Effort | Planned |
|---|---|---|---|
| Prediction tab | 2 | 3h | This week |
| Correlation tab | 2 | 2h | This week |
| Jupyter EDA notebook | 4 | 3h | This week |
| Property-based tests | 3 | 2h | Next week |
| /health endpoint | 3 | 1h | Next week |
| Medium writeup | 4 | 2h | After interview prep |

---

## Implementation Order

1. Simulator changes (data realism) → re-seed DB → push → Render redeploys
2. Three new SQL functions in `sql_queries.py`
3. `sql_showcase.sql` file
4. README: data story + corrections + ongoing section
5. Update screenshots (Data Quality will look different)
6. Final commit + push

---

## Success Criteria

- [ ] Data Quality tab: no two stations have identical row counts
- [ ] Heatmap: visible incident spikes on at least 2 stations
- [ ] `sql_queries.py`: 9 functions (6 existing + 3 new)
- [ ] `sql_showcase.sql`: 10 queries with analyst commentary
- [ ] README: "The Data Story" section present and narrative
- [ ] README: "87% precision" claim qualified
- [ ] All existing tests pass after simulator changes
- [ ] Live site updated on Render
