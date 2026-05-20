-- ============================================================
-- Mumbai Local Train Delay Visualizer — SQL Showcase
-- 10 query patterns from DA/DS interviews
-- Data: DuckDB, 2 years, 113 stations, 3 lines
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- QUERY 1: TOP-N PER GROUP  (ROW_NUMBER + PARTITION BY)
-- ANSWERS:  Which 3 stations on each line have the worst delays?
-- PATTERN:  Classic "top-N per group" — asked in 80% of DA interviews
-- STAKEHOLDER USE: Infrastructure team prioritises which stations to fix first per line
-- ────────────────────────────────────────────────────────────
WITH station_avgs AS (
    SELECT station_name, line, AVG(avg_delay) AS avg_delay
    FROM delays
    GROUP BY station_name, line
),
ranked AS (
    SELECT
        station_name, line, avg_delay,
        ROW_NUMBER() OVER (PARTITION BY line ORDER BY avg_delay DESC) AS rn
    FROM station_avgs
)
SELECT station_name, line, ROUND(avg_delay, 2) AS avg_delay, rn AS rank
FROM ranked
WHERE rn <= 3
ORDER BY line, rn;


-- ────────────────────────────────────────────────────────────
-- QUERY 2: WEEK-OVER-WEEK CHANGE  (LAG + multi-step CTE)
-- ANSWERS:  Is the Central line getting better or worse week-on-week?
-- PATTERN:  LAG() window function + chained CTEs
-- STAKEHOLDER USE: Ops manager identifies deteriorating periods to investigate
-- ────────────────────────────────────────────────────────────
WITH weekly AS (
    SELECT DATE_TRUNC('week', date) AS week_start, line,
           AVG(avg_delay) AS weekly_avg
    FROM delays
    WHERE line = 'Central'
    GROUP BY DATE_TRUNC('week', date), line
),
with_prev AS (
    SELECT *, LAG(weekly_avg) OVER (ORDER BY week_start) AS prev_week_avg
    FROM weekly
)
SELECT
    week_start, weekly_avg, prev_week_avg,
    ROUND((weekly_avg - prev_week_avg) / NULLIF(prev_week_avg, 0) * 100, 2) AS pct_change
FROM with_prev
ORDER BY week_start DESC;


-- ────────────────────────────────────────────────────────────
-- QUERY 3: CONDITIONAL AGGREGATION  (peak vs off-peak pivot)
-- ANSWERS:  How much worse is morning peak vs off-peak, per station?
-- PATTERN:  AVG(CASE WHEN ... THEN ... END) — pivot without PIVOT syntax
-- STAKEHOLDER USE: Scheduling team decides where to add trains during peak
-- ────────────────────────────────────────────────────────────
SELECT
    station_name, line,
    ROUND(AVG(CASE WHEN period = 'morning_peak' THEN avg_delay END), 2) AS morning_peak,
    ROUND(AVG(CASE WHEN period = 'evening_peak' THEN avg_delay END), 2) AS evening_peak,
    ROUND(AVG(CASE WHEN period = 'off_peak'     THEN avg_delay END), 2) AS off_peak,
    ROUND(AVG(avg_delay), 2)                                             AS overall
FROM delays
GROUP BY station_name, line
ORDER BY morning_peak DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- QUERY 4: ROLLING 7-DAY AVERAGE  (ROWS BETWEEN window)
-- ANSWERS:  What is the smoothed delay trend for the Western line?
-- PATTERN:  AVG() OVER (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
-- STAKEHOLDER USE: Removes daily noise to surface underlying trend direction
-- ────────────────────────────────────────────────────────────
WITH daily AS (
    SELECT date, line, AVG(avg_delay) AS daily_avg
    FROM delays
    WHERE line = 'Western'
    GROUP BY date, line
)
SELECT
    date, daily_avg,
    ROUND(AVG(daily_avg) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 3) AS rolling_7d
FROM daily
ORDER BY date DESC
LIMIT 30;


-- ────────────────────────────────────────────────────────────
-- QUERY 5: PERCENTILE ANALYSIS  (PERCENTILE_CONT)
-- ANSWERS:  What is the p50 / p90 / p95 delay distribution per station?
-- PATTERN:  PERCENTILE_CONT() WITHIN GROUP — non-parametric stats in SQL
-- STAKEHOLDER USE: SLA setting — "95% of peak trains arrive within X min"
-- ────────────────────────────────────────────────────────────
SELECT
    station_name, line,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_delay), 2) AS p50,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY avg_delay), 2) AS p90,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY avg_delay), 2) AS p95,
    ROUND(MAX(avg_delay), 2) AS worst_day
FROM delays
GROUP BY station_name, line
ORDER BY p95 DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- QUERY 6: YEAR-OVER-YEAR COMPARISON  (conditional aggregation by year)
-- ANSWERS:  Which stations got significantly worse from 2023 to 2024?
-- PATTERN:  CASE WHEN YEAR() pivot — YoY without self-join
-- STAKEHOLDER USE: Annual infrastructure review — measure intervention impact
-- ────────────────────────────────────────────────────────────
SELECT
    station_name, line,
    ROUND(AVG(CASE WHEN YEAR(date) = 2023 THEN avg_delay END), 2) AS avg_2023,
    ROUND(AVG(CASE WHEN YEAR(date) = 2024 THEN avg_delay END), 2) AS avg_2024,
    ROUND(
        (AVG(CASE WHEN YEAR(date) = 2024 THEN avg_delay END)
       - AVG(CASE WHEN YEAR(date) = 2023 THEN avg_delay END))
      / NULLIF(AVG(CASE WHEN YEAR(date) = 2023 THEN avg_delay END), 0) * 100,
        1
    ) AS yoy_pct_change
FROM delays
GROUP BY station_name, line
HAVING avg_2023 IS NOT NULL AND avg_2024 IS NOT NULL
ORDER BY yoy_pct_change DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- QUERY 7: SEASONAL PIVOT  (monsoon vs dry season)
-- ANSWERS:  How much worse are delays during monsoon (Jun-Sep)?
-- PATTERN:  CASE WHEN MONTH() IN (...) — seasonal segmentation
-- STAKEHOLDER USE: Monsoon preparedness budget — quantify seasonal impact
-- ────────────────────────────────────────────────────────────
SELECT
    station_name, line,
    ROUND(AVG(CASE WHEN MONTH(date) IN (6,7,8,9) THEN avg_delay END), 2) AS monsoon_avg,
    ROUND(AVG(CASE WHEN MONTH(date) NOT IN (6,7,8,9) THEN avg_delay END), 2) AS dry_avg,
    ROUND(
        AVG(CASE WHEN MONTH(date) IN (6,7,8,9) THEN avg_delay END)
      / NULLIF(AVG(CASE WHEN MONTH(date) NOT IN (6,7,8,9) THEN avg_delay END), 0),
        2
    ) AS monsoon_ratio
FROM delays
GROUP BY station_name, line
HAVING monsoon_avg IS NOT NULL AND dry_avg IS NOT NULL
ORDER BY monsoon_ratio DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- QUERY 8: ROLLING DEVIATION FLAG  (nested window functions)
-- ANSWERS:  Which stations are trending worse vs their 30-day baseline?
-- PATTERN:  Ratio of 7-day rolling avg to 30-day rolling avg
-- STAKEHOLDER USE: Early-warning dashboard — flag stations before they become critical
-- ────────────────────────────────────────────────────────────
WITH daily AS (
    SELECT date, station_name, line, AVG(avg_delay) AS daily_avg
    FROM delays
    GROUP BY date, station_name, line
),
windowed AS (
    SELECT
        date, station_name, line,
        AVG(daily_avg) OVER (PARTITION BY station_name ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d,
        AVG(daily_avg) OVER (PARTITION BY station_name ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS baseline_30d
    FROM daily
)
SELECT date, station_name, line,
    ROUND(rolling_7d, 2)    AS rolling_7d,
    ROUND(baseline_30d, 2)  AS baseline_30d,
    ROUND(rolling_7d / NULLIF(baseline_30d, 0), 3) AS deviation_ratio
FROM windowed
WHERE date = (SELECT MAX(date) FROM delays)
  AND baseline_30d IS NOT NULL
ORDER BY deviation_ratio DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- QUERY 9: STATION CORRELATION PROXY  (same-hour self-join)
-- ANSWERS:  Do Dadar delays predict Kurla delays? (cascade effect)
-- PATTERN:  Self-join on date+hour — proxy for station correlation
-- STAKEHOLDER USE: Network planners identify cascade failure risk pairs
-- ────────────────────────────────────────────────────────────
SELECT
    a.date,
    a.avg_delay AS dadar_delay,
    b.avg_delay AS kurla_delay,
    ABS(a.avg_delay - b.avg_delay) AS delay_gap
FROM delays a
JOIN delays b
  ON a.date = b.date AND a.hour = b.hour
WHERE a.station_name = 'Dadar'
  AND b.station_name = 'Kurla'
  AND a.period = 'morning_peak'
ORDER BY a.date DESC
LIMIT 30;


-- ────────────────────────────────────────────────────────────
-- QUERY 10: ECONOMIC IMPACT ESTIMATE  (derived column calculation)
-- ANSWERS:  What is the daily passenger-hour cost of delays at each station?
-- PATTERN:  Derived columns from domain constants — business translation of metrics
-- STAKEHOLDER USE: CFO/policy brief — translate delays into rupee impact
-- Note: 15 trains/hr x 3,000 commuters/train x 8 peak hours x median wage Rs.250/hr
-- ────────────────────────────────────────────────────────────
WITH station_peak AS (
    SELECT
        station_name, line,
        AVG(CASE WHEN period IN ('morning_peak', 'evening_peak') THEN avg_delay END) AS peak_delay_min
    FROM delays
    GROUP BY station_name, line
)
SELECT
    station_name, line,
    ROUND(peak_delay_min, 2) AS peak_delay_min,
    ROUND(peak_delay_min / 60 * 15 * 3000 * 8, 0) AS passenger_hours_lost_per_day,
    ROUND(peak_delay_min / 60 * 15 * 3000 * 8 * 250, 0) AS economic_cost_inr_per_day
FROM station_peak
WHERE peak_delay_min IS NOT NULL
ORDER BY economic_cost_inr_per_day DESC
LIMIT 10;