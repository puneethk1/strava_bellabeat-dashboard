"""
Bellabeat / Fitbit Fitness Data — Streamlit Dashboard
Loads fitbit.db (built by etl_build_db.py) and runs the SQL analysis
queries live, showing both the query and the resulting chart/table.

Run with:  streamlit run app.py
"""
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = "fitbit.db"

st.set_page_config(page_title="Bellabeat Fitness Analytics", layout="wide", page_icon="📊")


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def run_query(sql, params=None):
    conn = get_connection()
    return pd.read_sql(sql, conn, params=params)


def show_sql(label, sql):
    with st.expander(f"View SQL — {label}"):
        st.code(sql.strip(), language="sql")


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("Filters")

all_users = run_query("SELECT DISTINCT Id FROM daily_activity ORDER BY Id")["Id"].tolist()
user_options = ["All users"] + [str(u) for u in all_users]
selected_user = st.sidebar.selectbox("User", user_options)

date_bounds = run_query("SELECT MIN(ActivityDate) mn, MAX(ActivityDate) mx FROM daily_activity")
min_date = pd.to_datetime(date_bounds["mn"][0]).date()
max_date = pd.to_datetime(date_bounds["mx"][0]).date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

user_filter = "" if selected_user == "All users" else f"AND Id = {selected_user}"
st.sidebar.caption("33 users · Fitabase Fitbit export · Apr\u2013May 2016")

st.title("Bellabeat Fitness Data Analytics")
st.caption(
    "Case study: how consumers use smart-device fitness trackers, and what that means "
    "for Bellabeat's marketing strategy. Data cleaned and analyzed with SQL, visualized below."
)

tab_overview, tab_activity, tab_sleep, tab_heart, tab_engagement, tab_sql = st.tabs(
    ["Overview", "Activity Patterns", "Sleep", "Heart Rate", "Engagement & Weight", "SQL Explorer"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Overview
# ---------------------------------------------------------------------------
with tab_overview:
    sql_overview = f"""
        SELECT
            COUNT(DISTINCT Id) AS total_users,
            ROUND(AVG(TotalSteps), 0) AS avg_daily_steps,
            ROUND(AVG(TotalDistance), 2) AS avg_daily_distance_km,
            ROUND(AVG(Calories), 0) AS avg_daily_calories,
            ROUND(AVG(SedentaryMinutes) / 60.0, 1) AS avg_sedentary_hours,
            ROUND(AVG(VeryActiveMinutes + FairlyActiveMinutes + LightlyActiveMinutes), 1) AS avg_active_minutes
        FROM daily_activity
        WHERE DATE(ActivityDate) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
    """
    overview = run_query(sql_overview)
    show_sql("Overview metrics", sql_overview)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Users", int(overview["total_users"][0]))
    c2.metric("Avg daily steps", f"{overview['avg_daily_steps'][0]:,.0f}")
    c3.metric("Avg daily calories", f"{overview['avg_daily_calories'][0]:,.0f}")
    c4.metric("Avg sedentary hours/day", f"{overview['avg_sedentary_hours'][0]:.1f}")
    c5.metric("Avg active minutes/day", f"{overview['avg_active_minutes'][0]:.0f}")

    st.markdown("#### Activity level segmentation")
    sql_segment = f"""
        WITH user_avg AS (
            SELECT Id, AVG(TotalSteps) AS avg_steps
            FROM daily_activity
            WHERE DATE(ActivityDate) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
            GROUP BY Id
        )
        SELECT
            CASE
                WHEN avg_steps < 5000 THEN 'Sedentary (<5k)'
                WHEN avg_steps < 7500 THEN 'Low Active (5k-7.5k)'
                WHEN avg_steps < 10000 THEN 'Somewhat Active (7.5k-10k)'
                WHEN avg_steps < 12500 THEN 'Active (10k-12.5k)'
                ELSE 'Highly Active (12.5k+)'
            END AS activity_segment,
            COUNT(*) AS user_count
        FROM user_avg
        GROUP BY activity_segment
    """
    seg = run_query(sql_segment)
    show_sql("Activity level segmentation", sql_segment)
    order = ["Sedentary (<5k)", "Low Active (5k-7.5k)", "Somewhat Active (7.5k-10k)",
             "Active (10k-12.5k)", "Highly Active (12.5k+)"]
    seg["activity_segment"] = pd.Categorical(seg["activity_segment"], categories=order, ordered=True)
    seg = seg.sort_values("activity_segment")
    fig = px.bar(seg, x="activity_segment", y="user_count", text="user_count",
                 labels={"activity_segment": "", "user_count": "Users"},
                 title="Users by activity level (avg daily steps)")
    fig.update_traces(marker_color="#2E86AB")
    st.plotly_chart(fig, use_container_width=True)
    st.info(
        "Most users fall short of the 10,000-step benchmark. This is the core Bellabeat "
        "marketing opening: nudges and content aimed at the 'somewhat active' middle "
        "segment have the most room to move the needle."
    )

# ---------------------------------------------------------------------------
# TAB 2 — Activity Patterns
# ---------------------------------------------------------------------------
with tab_activity:
    st.markdown("#### Steps and calories by day of week")
    sql_dow = f"""
        SELECT Weekday,
               ROUND(AVG(TotalSteps), 0) AS avg_steps,
               ROUND(AVG(Calories), 0) AS avg_calories,
               ROUND(AVG(SedentaryMinutes), 0) AS avg_sedentary_minutes
        FROM daily_activity
        WHERE DATE(ActivityDate) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
        GROUP BY Weekday
    """
    dow = run_query(sql_dow)
    show_sql("Day-of-week pattern", sql_dow)
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow["Weekday"] = pd.Categorical(dow["Weekday"], categories=weekday_order, ordered=True)
    dow = dow.sort_values("Weekday")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(dow, x="Weekday", y="avg_steps", title="Average steps by day of week",
                     labels={"avg_steps": "Avg steps", "Weekday": ""})
        fig.update_traces(marker_color="#2E86AB")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(dow, x="Weekday", y="avg_sedentary_minutes",
                     title="Average sedentary minutes by day of week",
                     labels={"avg_sedentary_minutes": "Sedentary min", "Weekday": ""})
        fig.update_traces(marker_color="#C1666B")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Hourly activity pattern (when users move)")
    sql_hourly = f"""
        SELECT Hour,
               ROUND(AVG(StepTotal), 0) AS avg_steps,
               ROUND(AVG(AverageIntensity), 3) AS avg_intensity
        FROM hourly_activity
        WHERE Date BETWEEN '{start_date}' AND '{end_date}' {user_filter}
        GROUP BY Hour
        ORDER BY Hour
    """
    hourly = run_query(sql_hourly)
    show_sql("Hourly activity pattern", sql_hourly)
    fig = px.line(hourly, x="Hour", y="avg_steps", markers=True,
                  title="Average steps by hour of day",
                  labels={"avg_steps": "Avg steps", "Hour": "Hour (0-23)"})
    fig.update_traces(line_color="#2E86AB")
    st.plotly_chart(fig, use_container_width=True)
    peak_hour = int(hourly.loc[hourly["avg_steps"].idxmax(), "Hour"])
    st.info(
        f"Activity peaks around **{peak_hour}:00**, consistent with commute/exercise "
        "windows around midday and early evening. This is the highest-leverage time "
        "for Bellabeat to send activity nudges or promotional content."
    )

# ---------------------------------------------------------------------------
# TAB 3 — Sleep
# ---------------------------------------------------------------------------
with tab_sleep:
    sql_sleep = f"""
        SELECT
            COUNT(DISTINCT Id) AS users_with_sleep_data,
            ROUND(AVG(TotalMinutesAsleep) / 60.0, 2) AS avg_hours_asleep,
            ROUND(AVG(TotalTimeInBed) / 60.0, 2) AS avg_hours_in_bed,
            ROUND(AVG(AwakeMinutesInBed), 1) AS avg_minutes_awake_in_bed,
            ROUND(100.0 * SUM(CASE WHEN TotalMinutesAsleep < 360 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_nights_under_6h,
            ROUND(100.0 * SUM(CASE WHEN TotalMinutesAsleep BETWEEN 420 AND 540 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_nights_7to9h
        FROM sleep_day
        WHERE DATE(SleepDay) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
    """
    sleep_stats = run_query(sql_sleep)
    show_sql("Sleep duration and quality", sql_sleep)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Users logging sleep", int(sleep_stats["users_with_sleep_data"][0]))
    c2.metric("Avg hours asleep", f"{sleep_stats['avg_hours_asleep'][0]:.2f}")
    c3.metric("Nights under 6h", f"{sleep_stats['pct_nights_under_6h'][0]:.0f}%")
    c4.metric("Nights in 7-9h range", f"{sleep_stats['pct_nights_7to9h'][0]:.0f}%")

    st.markdown("#### Activity vs. sleep relationship")
    sql_corr = f"""
        SELECT a.Id, a.ActivityDate, a.TotalSteps, a.VeryActiveMinutes, s.TotalMinutesAsleep
        FROM daily_activity a
        JOIN sleep_day s ON a.Id = s.Id AND DATE(a.ActivityDate) = DATE(s.SleepDay)
        WHERE DATE(a.ActivityDate) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
    """
    corr_df = run_query(sql_corr)
    show_sql("Activity joined to same-night sleep", sql_corr)

    if len(corr_df) > 2:
        r = corr_df["TotalSteps"].corr(corr_df["TotalMinutesAsleep"])
        fig = px.scatter(corr_df, x="TotalSteps", y="TotalMinutesAsleep", trendline="ols",
                          labels={"TotalSteps": "Steps that day", "TotalMinutesAsleep": "Minutes asleep that night"},
                          title=f"Daily steps vs. minutes asleep (r = {r:.2f}, n = {len(corr_df)})")
        fig.update_traces(marker=dict(color="#2E86AB", opacity=0.6), selector=dict(mode="markers"))
        st.plotly_chart(fig, use_container_width=True)
        st.info(
            f"Correlation between steps and same-night sleep is weak (r = {r:.2f}) in this "
            "panel. Sleep duration looks driven more by lifestyle/schedule than by how "
            "active the day was — useful context for not over-promising sleep gains from "
            "an activity-focused campaign."
        )
    else:
        st.warning("Not enough overlapping activity/sleep records for the current filter.")

# ---------------------------------------------------------------------------
# TAB 4 — Heart Rate
# ---------------------------------------------------------------------------
with tab_heart:
    sql_hr_segment = f"""
        WITH user_avg_steps AS (
            SELECT Id, AVG(TotalSteps) AS avg_steps
            FROM daily_activity
            WHERE DATE(ActivityDate) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
            GROUP BY Id
        ),
        user_avg_hr AS (
            SELECT Id, AVG(AvgHeartRate) AS avg_hr
            FROM daily_heartrate
            WHERE Date BETWEEN '{start_date}' AND '{end_date}' {user_filter}
            GROUP BY Id
        )
        SELECT
            CASE
                WHEN s.avg_steps < 7500 THEN 'Low Active (<7.5k)'
                WHEN s.avg_steps < 10000 THEN 'Somewhat Active (7.5k-10k)'
                ELSE 'Active (10k+)'
            END AS activity_segment,
            COUNT(*) AS users,
            ROUND(AVG(h.avg_hr), 1) AS avg_heart_rate
        FROM user_avg_steps s
        JOIN user_avg_hr h ON s.Id = h.Id
        GROUP BY activity_segment
    """
    hr_seg = run_query(sql_hr_segment)
    show_sql("Average heart rate by activity segment", sql_hr_segment)

    if len(hr_seg):
        fig = px.bar(hr_seg, x="activity_segment", y="avg_heart_rate", text="avg_heart_rate",
                     labels={"activity_segment": "", "avg_heart_rate": "Avg heart rate (bpm)"},
                     title="Average heart rate by activity segment")
        fig.update_traces(marker_color="#C1666B")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Only a subset of users have heart rate device data (Fitbit vs. Bellabeat Leaf/Time users).")

    sql_hr_hourly = f"""
        SELECT
            CAST(strftime('%H', ActivityHour) AS INTEGER) AS Hour,
            ROUND(AVG(AvgHeartRate), 1) AS avg_hr
        FROM hourly_heartrate
        WHERE DATE(ActivityHour) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
        GROUP BY Hour
        ORDER BY Hour
    """
    hr_hourly = run_query(sql_hr_hourly)
    show_sql("Average heart rate by hour of day", sql_hr_hourly)
    if len(hr_hourly):
        fig = px.line(hr_hourly, x="Hour", y="avg_hr", markers=True,
                      title="Average heart rate by hour of day",
                      labels={"avg_hr": "Avg heart rate (bpm)", "Hour": "Hour (0-23)"})
        fig.update_traces(line_color="#C1666B")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 5 — Engagement & Weight
# ---------------------------------------------------------------------------
with tab_engagement:
    st.markdown("#### Logging consistency (engagement)")
    sql_engagement = f"""
        SELECT Id, COUNT(DISTINCT ActivityDate) AS days_logged
        FROM daily_activity
        WHERE DATE(ActivityDate) BETWEEN '{start_date}' AND '{end_date}' {user_filter}
        GROUP BY Id
        ORDER BY days_logged DESC
    """
    eng = run_query(sql_engagement)
    show_sql("Logging consistency per user", sql_engagement)
    fig = px.bar(eng, x="Id", y="days_logged", labels={"Id": "User ID", "days_logged": "Days logged"},
                 title="Days of activity logged per user")
    fig.update_xaxes(type="category")
    fig.update_traces(marker_color="#2E86AB")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Weight logging — feature adoption gap")
    sql_weight = """
        SELECT
            (SELECT COUNT(DISTINCT Id) FROM daily_activity) AS total_users,
            (SELECT COUNT(DISTINCT Id) FROM weight_log) AS users_logging_weight,
            (SELECT COUNT(DISTINCT Id) FROM weight_log WHERE IsManualReport = 1) AS manual_entries,
            (SELECT COUNT(DISTINCT Id) FROM weight_log WHERE IsManualReport = 0) AS auto_entries
    """
    w = run_query(sql_weight)
    show_sql("Weight logging engagement", sql_weight)
    pct = 100 * w["users_logging_weight"][0] / w["total_users"][0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Users logging weight", f"{w['users_logging_weight'][0]} / {w['total_users'][0]}")
    c2.metric("Adoption rate", f"{pct:.0f}%")
    c3.metric("Manually entered logs", int(w["manual_entries"][0]))
    st.info(
        f"Only {pct:.0f}% of users log weight at all, and most of those entries are "
        "manual rather than from a connected scale. Weight tracking is the weakest "
        "adopted feature in the panel — a clear gap Bellabeat could close with a "
        "smart-scale bundle or simplified manual-entry flow."
    )

# ---------------------------------------------------------------------------
# TAB 6 — SQL Explorer
# ---------------------------------------------------------------------------
with tab_sql:
    st.markdown(
        "Run any read-only SQL query against the cleaned database. "
        "Tables: `daily_activity`, `sleep_day`, `weight_log`, `hourly_activity`, "
        "`daily_heartrate`, `hourly_heartrate`, `minute_sleep`."
    )
    default_query = "SELECT * FROM daily_activity LIMIT 20;"
    query_text = st.text_area("SQL query", value=default_query, height=140)
    run_clicked = st.button("Run query")
    if run_clicked:
        cleaned = query_text.strip().rstrip(";")
        if not cleaned.lower().startswith("select") and not cleaned.lower().startswith("with"):
            st.error("Only SELECT / WITH (read-only) queries are allowed here.")
        else:
            try:
                result = run_query(cleaned)
                st.dataframe(result, use_container_width=True)
                st.caption(f"{len(result):,} rows returned")
            except Exception as e:
                st.error(f"Query failed: {e}")

st.divider()
st.caption(
    "Data source: Fitabase Fitbit export (mturkfitbit_export_4.12.16-5.12.16), 33 users. "
    "Built for the Bellabeat wellness-technology case study."
)
