-- 1. Weekday vs weekend consumption under similar conditions
SELECT
  wb.weather_band,
  ROUND(AVG(CASE WHEN d.is_weekend = FALSE THEN f.consumption_mwh END), 2) AS avg_weekday_consumption_mwh,
  ROUND(AVG(CASE WHEN d.is_weekend = TRUE THEN f.consumption_mwh END), 2) AS avg_weekend_consumption_mwh,
  ROUND(
    AVG(CASE WHEN d.is_weekend = FALSE THEN f.consumption_mwh END)
    - AVG(CASE WHEN d.is_weekend = TRUE THEN f.consumption_mwh END),
    2
  ) AS weekday_weekend_diff_mwh,
  ROUND(
    (
      AVG(CASE WHEN d.is_weekend = FALSE THEN f.consumption_mwh END)
      - AVG(CASE WHEN d.is_weekend = TRUE THEN f.consumption_mwh END)
    ) / NULLIF(AVG(CASE WHEN d.is_weekend = TRUE THEN f.consumption_mwh END), 0) * 100,
    2
  ) AS pct_difference
FROM fact_energy f
JOIN dim_date d ON f.dim_date_id = d.date_key
JOIN dim_weather_band wb ON f.dim_weather_band_id = wb.weather_key
GROUP BY wb.weather_key, wb.weather_band;

-- 2. Consumption sensitivity to temperature below freezing
-- Computes linear regression slope: change in MWh per 1C drop below freezing (avg_temp <= 0)
SELECT
  COUNT(*) AS sub_zero_hours,
  ROUND(AVG(f.consumption_mwh), 2) AS avg_sub_zero_consumption_mwh,
  ROUND(REGR_SLOPE(f.consumption_mwh, f.avg_temp)::NUMERIC, 2) AS mwh_change_per_degree_celsius,
  ROUND(ABS(REGR_SLOPE(f.consumption_mwh, f.avg_temp))::NUMERIC, 2) AS consumption_increase_per_degree_drop_mwh,
  ROUND(REGR_R2(f.consumption_mwh, f.avg_temp)::NUMERIC, 4) AS r_squared
FROM fact_energy f
JOIN dim_weather_band wb ON f.dim_weather_band_id = wb.weather_key
WHERE wb.sub_zero = TRUE;

-- 3. Financial cost of grid losses (peak vs off-peak)
SELECT
  CASE
    WHEN t.is_peak THEN 'Peak Hours (08:00-20:00)'
    ELSE 'Off-Peak Hours (Night)'
  END AS period_type,
  COUNT(*) AS total_hours,
  ROUND(SUM(f.planned_losses_mwh), 2) AS total_planned_losses_mwh,
  ROUND(AVG(f.nps_price_eur_mwh), 2) AS avg_nps_price_eur,
  ROUND(SUM(f.planned_losses_mwh * f.nps_price_eur_mwh), 2) AS total_loss_cost_eur,
  ROUND(AVG(f.planned_losses_mwh * f.nps_price_eur_mwh), 2) AS hourly_avg_loss_cost_eur
FROM fact_energy f
JOIN dim_time t ON f.dim_time_id = t.time_key
GROUP BY t.is_peak;

-- 4. NPS price comparison (days below -10C vs days above freezing)
WITH daily_metrics AS (
  SELECT
    f.dim_date_id,
    AVG(f.avg_temp) AS daily_avg_temp,
    AVG(f.nps_price_eur_mwh) AS daily_avg_nps_price
  FROM fact_energy f
  GROUP BY f.dim_date_id
),
classified_days AS (
  SELECT
    daily_avg_nps_price,
    CASE
      WHEN daily_avg_temp < -10.0 THEN 'Deep Frost (< -10C)'
      WHEN daily_avg_temp > 0.0 THEN 'Above Freezing (> 0C)'
      ELSE 'Intermediate (-10°C to 0°C)'
    END AS temp_category
  FROM daily_metrics
)
SELECT
  temp_category,
  COUNT(*) AS total_days,
  ROUND(AVG(daily_avg_nps_price), 2) AS avg_nps_price_eur_mwh,
  ROUND(MIN(daily_avg_nps_price), 2) AS min_daily_avg_nps_price,
  ROUND(MAX(daily_avg_nps_price), 2) AS max_daily_avg_nps_price
FROM classified_days
WHERE temp_category IN ('Deep Frost (< -10C)', 'Above Freezing (> 0C)')
GROUP BY temp_category;

-- 5. Grid losses distribution (weekdays vs weekends by weather band)
SELECT
  wb.weather_band,
  ROUND(AVG(CASE WHEN d.is_weekend = FALSE THEN f.planned_losses_mwh END), 2) AS avg_weekday_losses_mwh,
  ROUND(
    AVG(CASE
      WHEN d.is_weekend = FALSE THEN (f.planned_losses_mwh / NULLIF(f.production_mwh, 0)) * 100
    END),
    2
  ) AS avg_weekday_loss_rate_pct,
  ROUND(AVG(CASE WHEN d.is_weekend = TRUE THEN f.planned_losses_mwh END), 2) AS avg_weekend_losses_mwh,
  ROUND(
    AVG(CASE
      WHEN d.is_weekend = TRUE THEN (f.planned_losses_mwh / NULLIF(f.production_mwh, 0)) * 100
    END),
    2
  ) AS avg_weekend_loss_rate_pct,
  ROUND(
    AVG(CASE WHEN d.is_weekend = FALSE THEN f.planned_losses_mwh END)
    - AVG(CASE WHEN d.is_weekend = TRUE THEN f.planned_losses_mwh END),
    2
  ) AS absolute_loss_diff_mwh
FROM fact_energy f
JOIN dim_date d ON f.dim_date_id = d.date_key
JOIN dim_weather_band wb ON f.dim_weather_band_id = wb.weather_key
GROUP BY wb.weather_key, wb.weather_band;
