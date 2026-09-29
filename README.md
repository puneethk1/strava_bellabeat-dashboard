# Bellabeat Fitness Data Analytics — SQL + Streamlit

Case-study deliverable: clean the Fitbit/Fitabase smart-device data with SQL,
then present the analysis in an interactive Streamlit dashboard (queries and
charts both live in the app).

## Files

- `etl_build_db.py` — cleans the raw Fitabase CSVs and loads them into `fitbit.db` (SQLite)
- `fitbit.db` — the cleaned database, ready to use (already built, no need to rerun ETL unless you change the source data)
- `sql_analysis.sql` — the standalone SQL analysis (11 queries: activity overview, activity segmentation, day-of-week and hourly patterns, sleep quality, activity-vs-sleep correlation, heart rate by activity level, engagement, weight-logging adoption)
- `app.py` — the Streamlit dashboard
- `requirements.txt` — Python dependencies

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. Use the sidebar to filter by user and date range.

To rebuild the database from the raw data (only needed if the source CSVs change):

```bash
python etl_build_db.py
```
This expects the raw Fitabase folder at
`raw/Data Files/mturkfitbit_export_4.12.16-5.12.16/Fitabase Data 4.12.16-5.12.16/`.

## Dashboard structure

- **Overview** — headline metrics and activity-level segmentation
- **Activity Patterns** — day-of-week and hour-of-day movement patterns
- **Sleep** — sleep duration/quality and its relationship to daily activity
- **Heart Rate** — average heart rate by activity segment and time of day
- **Engagement & Weight** — logging consistency and weight-feature adoption
- **SQL Explorer** — run your own read-only SQL against the cleaned tables

Every chart tab has a "View SQL" expander showing the exact query that produced it.

## Data

Fitabase Fitbit export, 33 users, minute/hour/day granularity, April–May 2016.
Minute-level step/calorie/intensity/MET files and the raw per-second heart rate
log are large (tens to ~90 MB each); the ETL aggregates heart rate to daily and
hourly averages rather than loading all 2.48M second-level rows into the
dashboard. `minute_sleep` is loaded as-is for reference but not used in the
current dashboard views.

## Key findings (from the SQL analysis)

- 33 users average ~7,600 steps/day — below the 10,000-step benchmark, with the panel split roughly evenly across activity segments below and above that line.
- Sedentary time dominates: ~16.5 hours/day on average.
- Sleep duration and daily step count show only a weak correlation (r ≈ -0.19) — activity level alone doesn't explain who sleeps well.
- ~24% of logged nights fall under 6 hours of sleep.
- Weight logging is the least-adopted feature: only 8 of 33 users log weight at all, and most of those entries are manual rather than from a connected scale.
- Activity peaks in the hourly data around midday/early evening — the highest-leverage window for engagement nudges.
