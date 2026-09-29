"""
ETL script: cleans the raw Fitbit (Fitabase) export and loads it into a
single SQLite database (fitbit.db) for SQL analysis and the Streamlit
dashboard.

Source: Data Files/mturkfitbit_export_4.12.16-5.12.16/Fitabase Data 4.12.16-5.12.16/
"""
import pandas as pd
import sqlite3
import os

BASE = "raw/Data Files/mturkfitbit_export_4.12.16-5.12.16/Fitabase Data 4.12.16-5.12.16/"
DB_PATH = "fitbit.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)

def to_date(series, fmt=None):
    return pd.to_datetime(series, format=fmt, errors="coerce")

print("Loading daily_activity ...")
daily = pd.read_csv(BASE + "dailyActivity_merged.csv")
daily["ActivityDate"] = to_date(daily["ActivityDate"], "%m/%d/%Y")
daily = daily.drop_duplicates()
daily["Weekday"] = daily["ActivityDate"].dt.day_name()
daily.to_sql("daily_activity", conn, if_exists="replace", index=False)

print("Loading sleep_day ...")
sleep = pd.read_csv(BASE + "sleepDay_merged.csv")
sleep["SleepDay"] = to_date(sleep["SleepDay"], "%m/%d/%Y %I:%M:%S %p")
sleep = sleep.drop_duplicates()
sleep["AwakeMinutesInBed"] = sleep["TotalTimeInBed"] - sleep["TotalMinutesAsleep"]
sleep.to_sql("sleep_day", conn, if_exists="replace", index=False)

print("Loading weight_log ...")
weight = pd.read_csv(BASE + "weightLogInfo_merged.csv")
weight["Date"] = to_date(weight["Date"], "%m/%d/%Y %I:%M:%S %p")
weight = weight.drop_duplicates()
weight.to_sql("weight_log", conn, if_exists="replace", index=False)

print("Loading hourly_steps / hourly_calories / hourly_intensities and merging ...")
hs = pd.read_csv(BASE + "hourlySteps_merged.csv")
hc = pd.read_csv(BASE + "hourlyCalories_merged.csv")
hi = pd.read_csv(BASE + "hourlyIntensities_merged.csv")
for df in (hs, hc, hi):
    df["ActivityHour"] = to_date(df["ActivityHour"], "%m/%d/%Y %I:%M:%S %p")

hourly = hs.merge(hc, on=["Id", "ActivityHour"]).merge(hi, on=["Id", "ActivityHour"])
hourly["Hour"] = hourly["ActivityHour"].dt.hour
hourly["Date"] = hourly["ActivityHour"].dt.date
hourly.to_sql("hourly_activity", conn, if_exists="replace", index=False)

print("Loading and aggregating heartrate_seconds (large file, aggregating to daily + hourly) ...")
hr_chunks = pd.read_csv(BASE + "heartrate_seconds_merged.csv", chunksize=500_000)
daily_hr_parts, hourly_hr_parts = [], []
for chunk in hr_chunks:
    chunk["Time"] = to_date(chunk["Time"], "%m/%d/%Y %I:%M:%S %p")
    chunk["Date"] = chunk["Time"].dt.date
    chunk["Hour"] = chunk["Time"].dt.floor("h")
    daily_hr_parts.append(
        chunk.groupby(["Id", "Date"])["Value"].agg(["mean", "min", "max"]).reset_index()
    )
    hourly_hr_parts.append(
        chunk.groupby(["Id", "Hour"])["Value"].mean().reset_index()
    )

daily_hr = pd.concat(daily_hr_parts).groupby(["Id", "Date"]).agg(
    AvgHeartRate=("mean", "mean"), MinHeartRate=("min", "min"), MaxHeartRate=("max", "max")
).reset_index()
daily_hr.to_sql("daily_heartrate", conn, if_exists="replace", index=False)

hourly_hr = pd.concat(hourly_hr_parts).groupby(["Id", "Hour"])["Value"].mean().reset_index()
hourly_hr.columns = ["Id", "ActivityHour", "AvgHeartRate"]
hourly_hr.to_sql("hourly_heartrate", conn, if_exists="replace", index=False)

print("Loading minute_sleep (sleep-state minute log, kept for reference) ...")
msleep = pd.read_csv(BASE + "minuteSleep_merged.csv")
msleep["date"] = to_date(msleep["date"], "%m/%d/%Y %I:%M:%S %p")
msleep.to_sql("minute_sleep", conn, if_exists="replace", index=False)

# Helpful indexes for dashboard query speed
cur = conn.cursor()
for stmt in [
    "CREATE INDEX idx_daily_activity_id_date ON daily_activity(Id, ActivityDate)",
    "CREATE INDEX idx_sleep_id_date ON sleep_day(Id, SleepDay)",
    "CREATE INDEX idx_weight_id_date ON weight_log(Id, Date)",
    "CREATE INDEX idx_hourly_id_date ON hourly_activity(Id, Date)",
    "CREATE INDEX idx_daily_hr_id_date ON daily_heartrate(Id, Date)",
]:
    cur.execute(stmt)
conn.commit()

tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
print("\nTables built:")
for t in tables["name"]:
    n = pd.read_sql(f"SELECT COUNT(*) c FROM {t}", conn)["c"][0]
    print(f"  {t}: {n:,} rows")

conn.close()
print("\nDone -> fitbit.db")
