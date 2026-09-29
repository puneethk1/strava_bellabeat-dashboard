-- ============================================================
-- Strava/Bellabeat Fitness Data — SQL Analysis
-- Database: fitbit.db (built by etl_build_db.py)
-- Source: Fitabase Fitbit export, 33 users, Apr–May 2016
-- ============================================================

-- 1. USER ACTIVITY OVERVIEW
-- How active is the panel overall? Averages per user, per day.
SELECT
    COUNT(DISTINCT Id) AS total_users,
    ROUND(AVG(TotalSteps), 0) AS avg_daily_steps,
    ROUND(AVG(TotalDistance), 2) AS avg_daily_distance_km,
    ROUND(AVG(Calories), 0) AS avg_daily_calories,
    ROUND(AVG(SedentaryMinutes) / 60.0, 1) AS avg_sedentary_hours,
    ROUND(AVG(VeryActiveMinutes + FairlyActiveMinutes + LightlyActiveMinutes), 1) AS avg_active_minutes
FROM daily_activity;

-- 2. ACTIVITY LEVEL SEGMENTATION
-- Classify each user by average daily steps against CDC activity bands.
WITH user_avg AS (
    SELECT Id, AVG(TotalSteps) AS avg_steps
    FROM daily_activity
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
    COUNT(*) AS user_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM user_avg), 1) AS pct_of_users
FROM user_avg
GROUP BY activity_segment
ORDER BY MIN(avg_steps);

-- 3. DAY-OF-WEEK PATTERNS
-- Are users more active on weekdays or weekends? Which day has the least movement?
SELECT
    Weekday,
    ROUND(AVG(TotalSteps), 0) AS avg_steps,
    ROUND(AVG(Calories), 0) AS avg_calories,
    ROUND(AVG(SedentaryMinutes), 0) AS avg_sedentary_minutes,
    ROUND(AVG(VeryActiveMinutes), 1) AS avg_very_active_minutes
FROM daily_activity
GROUP BY Weekday
ORDER BY CASE Weekday
    WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
    WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END;

-- 4. HOURLY ACTIVITY PATTERN
-- When during the day are users most active? (For push-notification timing.)
SELECT
    Hour,
    ROUND(AVG(StepTotal), 0) AS avg_steps,
    ROUND(AVG(Calories), 0) AS avg_calories,
    ROUND(AVG(AverageIntensity), 3) AS avg_intensity
FROM hourly_activity
GROUP BY Hour
ORDER BY Hour;

-- 5. SLEEP DURATION AND QUALITY
-- How much are users sleeping, and how much of "time in bed" is actually spent asleep?
SELECT
    COUNT(DISTINCT Id) AS users_with_sleep_data,
    ROUND(AVG(TotalMinutesAsleep) / 60.0, 2) AS avg_hours_asleep,
    ROUND(AVG(TotalTimeInBed) / 60.0, 2) AS avg_hours_in_bed,
    ROUND(AVG(AwakeMinutesInBed), 1) AS avg_minutes_awake_in_bed,
    ROUND(100.0 * SUM(CASE WHEN TotalMinutesAsleep < 360 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_nights_under_6h,
    ROUND(100.0 * SUM(CASE WHEN TotalMinutesAsleep BETWEEN 420 AND 540 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_nights_7to9h
FROM sleep_day;

-- 6. ACTIVITY vs SLEEP RELATIONSHIP
-- Does a more active day correlate with more (or less) sleep that night?
SELECT
    a.Id,
    a.ActivityDate,
    a.TotalSteps,
    a.VeryActiveMinutes,
    s.TotalMinutesAsleep
FROM daily_activity a
JOIN sleep_day s
    ON a.Id = s.Id AND DATE(a.ActivityDate) = DATE(s.SleepDay)
ORDER BY a.Id, a.ActivityDate;
-- (Correlation itself is computed in Python/pandas in the dashboard, since
--  SQLite has no built-in CORR() function.)

-- 7. SEDENTARY TIME vs SLEEP
-- Do users who sit more also sleep worse?
SELECT
    a.Id,
    ROUND(AVG(a.SedentaryMinutes), 0) AS avg_sedentary_minutes,
    ROUND(AVG(s.TotalMinutesAsleep), 0) AS avg_minutes_asleep
FROM daily_activity a
JOIN sleep_day s
    ON a.Id = s.Id AND DATE(a.ActivityDate) = DATE(s.SleepDay)
GROUP BY a.Id
ORDER BY avg_sedentary_minutes DESC;

-- 8. LOGGING CONSISTENCY / ENGAGEMENT
-- Which users are "power users" (log activity almost every day) vs. sporadic?
SELECT
    Id,
    COUNT(DISTINCT ActivityDate) AS days_logged,
    ROUND(100.0 * COUNT(DISTINCT ActivityDate) / 31, 1) AS pct_of_period_logged
FROM daily_activity
GROUP BY Id
ORDER BY days_logged DESC;

-- 9. WEIGHT LOGGING ENGAGEMENT (feature adoption gap)
-- Very few users log weight manually -- a key product/marketing insight.
SELECT
    (SELECT COUNT(DISTINCT Id) FROM daily_activity) AS total_users,
    (SELECT COUNT(DISTINCT Id) FROM weight_log) AS users_logging_weight,
    ROUND(100.0 * (SELECT COUNT(DISTINCT Id) FROM weight_log) /
          (SELECT COUNT(DISTINCT Id) FROM daily_activity), 1) AS pct_logging_weight,
    (SELECT COUNT(DISTINCT Id) FROM weight_log WHERE IsManualReport = 1) AS manual_log_count,
    (SELECT COUNT(DISTINCT Id) FROM weight_log WHERE IsManualReport = 0) AS auto_log_count;

-- 10. RESTING/AVERAGE HEART RATE BY ACTIVITY SEGMENT
-- Do more active users show lower average heart rate (a fitness proxy)?
WITH user_avg_steps AS (
    SELECT Id, AVG(TotalSteps) AS avg_steps FROM daily_activity GROUP BY Id
),
user_avg_hr AS (
    SELECT Id, AVG(AvgHeartRate) AS avg_hr FROM daily_heartrate GROUP BY Id
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
GROUP BY activity_segment;

-- 11. TOP AND BOTTOM PERFORMING DAYS (dataset-wide)
-- Which calendar dates saw the most/least overall movement (seasonality/day-of-week check)?
SELECT ActivityDate, ROUND(AVG(TotalSteps), 0) AS avg_steps
FROM daily_activity
GROUP BY ActivityDate
ORDER BY avg_steps DESC
LIMIT 5;

SELECT ActivityDate, ROUND(AVG(TotalSteps), 0) AS avg_steps
FROM daily_activity
GROUP BY ActivityDate
ORDER BY avg_steps ASC
LIMIT 5;
