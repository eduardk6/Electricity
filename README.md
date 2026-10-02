# Weather Aware Grid Loss Analytics

## Project Overview

This project proposes a near real time micro batch analytical data warehouse that combines Elering electricity grid performance data with Keskkonnaagentuur weather observations. The analytical focus is on Estonian electricity transmission losses: when actual losses exceed planned losses, how weather conditions relate to those deviations, and what the financial effect is during high price hours.

The project is designed for Project 1 in Data Architecture and Modeling. The scope is architecture, tooling choice, dimensional modeling, data dictionary, and demo queries. A full production implementation is left for the next project phase.

## Business Brief

**Objective:** Create an automated analytical data warehouse that links Elering transmission loss, consumption, production, and Nord Pool price data with hourly Estonian weather observations to monitor and explain grid loss behavior.

**Stakeholders:**

- Elering system operators
- Grid planning analysts
- Energy traders
- Renewable energy analysts
- Reporting and regulatory teams

**Business value:** The warehouse supports recurring monitoring of loss variance, weather sensitivity, and loss cost, helping stakeholders understand when and why grid losses become higher than expected.

**Update pattern:** Near real time micro batch. Airflow pulls API data hourly or every 15 minutes, depending on endpoint availability and business need.

## Key Metrics

| KPI | Formula | Purpose |
| --- | --- | --- |
| Grid Loss Ratio | `actual_loss_mwh / consumption_mwh * 100` | Shows the proportion of consumed electricity represented by grid losses. |
| Loss Forecast Variance | `actual_loss_mwh - planned_loss_mwh` | Measures whether actual losses are above or below planned losses. |
| Temperature Sensitivity Coefficient | Change in `actual_loss_mwh` per 1 C change in temperature | Quantifies how strongly losses move with temperature changes. |
| Financial Loss Cost | `actual_loss_mwh * nordpool_price_eur_mwh` | Estimates the hourly market value of grid losses. |
| Peak Loss Hours | Count of hours where loss variance exceeds a chosen threshold | Identifies hours requiring closer operational analysis. |

## Business Questions

1. At which hours and under which extreme temperatures do actual transmission losses exceed planned losses the most?
2. How do average wind speed and local renewable production affect grid loss dynamics?
3. What is the financial impact of grid losses during peak price hours compared with night time low load hours?
4. Which grid zones have the highest loss ratio under similar weather conditions?
5. How are grid losses distributed between workdays and weekends under similar weather conditions?

## 2. Datasets

The project uses two distinct API datasets. Both datasets satisfy the course requirement of at least 1000 rows and at least 8 columns.

### Dataset 1: Elering Live System and Planned Grid Data

**Source:** Elering Dashboard API  
**Endpoint:** `https://dashboard.elering.ee/api/system/with-plan/csv`, joined with `https://dashboard.elering.ee/api/nps/price` for Estonian NPS price  
**Theme:** energy, grid operations, renewable production, planned grid losses, electricity market price  
**Update frequency:** 15 minute intervals in the exported sample; can be pulled regularly with Airflow  
**Example CSV:** `data/elering_system_with_plan_nps_price_2026-09-01_2026-09-14.csv`  
**Sample size:** 1345 data rows and 10 columns

Selected schema attributes:

1. `timestamp_utc`
2. `datetime_estonia`
3. `consumption_mw`
4. `planned_consumption_mw`
5. `planned_losses_mw`
6. `nps_price_eur_mwh`
7. `production_mw`
8. `wind_production_mw`
9. `solar_production_mw`
10. `system_balance_mw`

This dataset is used to analyze national electricity consumption, production, renewable production, planned grid losses, NPS electricity price, system balance, and differences between planned and actual system behavior.

### Dataset 2: Keskkonnaagentuur Hourly Weather Observation Data

**Source:** Keskkonnaagentuur Estonian Weather API  
**Endpoint:** `https://publicapi.envir.ee/v1/combinedWeatherData/observationDataHourly`  
**Theme:** environment, weather, station observations  
**Update frequency:** hourly by weather station  
**Example CSV:** `data/weather_hourly_observations_2026-09-01_2026-09-14.csv`  
**Sample size:** 33264 data rows and 9 columns

Selected actual API schema attributes:

1. `observation_date`
2. `observation_hour`
3. `station_id`
4. `Jaam`
5. `tains`
6. `ws10ma`
7. `pr1hs`
8. `rhins`
9. `pw15maEng`

This dataset is used to calculate hourly weather indicators such as average outdoor temperature, wind speed, precipitation, humidity, and weather condition groups. These indicators are joined with the Elering dataset by timestamp after weather observations are aggregated from station level to hourly national or grid area level.

## Data Architecture

The design uses a near real time micro batch approach instead of a complex event streaming platform. This keeps the work inside the scope of Project 1 while still supporting frequently updated data.

```text
Elering API and Keskkonnaagentuur API
        |
        | Hourly or 15 minute REST API pull with Python
        v
Airflow orchestration and ingestion layer
        |
        | Raw JSON or CSV dump and staging tables
        v
Bronze layer in PostgreSQL staging
        |
        | Great Expectations or dbt checks
        v
dbt transformation and modeling
        |
        | Fact and dimension generation
        v
Silver and Gold data warehouse star schema
        |
        v
Metabase or Superset analytics and reporting
```

## Tooling

| Lifecycle stage | Tool | Role in project |
| --- | --- | --- |
| Orchestration and ingestion | Apache Airflow | Schedules Python tasks that pull REST API data every hour or every 15 minutes. |
| Raw storage | PostgreSQL staging schema or MinIO | Stores raw JSON or CSV responses before transformation. |
| Warehouse storage | PostgreSQL, ClickHouse, or DuckDB | Holds modeled star schema tables for analytical queries. |
| Transformation | dbt | Builds staging views, dimensions, facts, derived metrics, and SCD logic. |
| Data quality | Great Expectations or dbt tests | Runs null, range, uniqueness, and freshness checks before data reaches reporting. |
| Reporting | Metabase or Apache Superset | Visualizes KPIs, grid loss trends, and weather sensitivity charts. |

## Data Quality Checks

| Check | Rule | Layer | Why it matters |
| --- | --- | --- | --- |
| Null check | `timestamp`, `actual_loss_mwh`, `planned_loss_mwh`, `station_id`, `observation_time`, and `temperature` must not be null where required. | Bronze to Silver | Prevents broken joins and incomplete KPI calculations. |
| Range check | `-40 <= temperature <= 45`, `wind_speed >= 0`, `losses >= 0`, `consumption >= 0` | Staging and marts | Catches impossible sensor or parsing values. |
| Uniqueness check | Weather: `station_id + observation_time`. Grid fact: `date_hour_key + grid_zone_key`. | Silver and Gold | Prevents duplicate rows from repeated API pulls. |
| Freshness check | Latest API pull should be within the expected hourly or 15 minute window. | Bronze | Confirms the system is still receiving regular updates. |
| Referential integrity | Fact keys must exist in `dim_date_hour`, `dim_weather_station`, and `dim_grid_zone`. | Gold | Keeps the star schema queryable and consistent. |

## Star Schema

### Fact Table

`fact_grid_hourly_performance`

**Grain:** one row for each hour and grid zone.

If the implementation starts with Estonia wide data only, `dim_grid_zone` can initially contain one national `EE` zone and later expand to substation or regional zones when more detailed source data is available.

### Tables

| Table | Type | Key columns | Description |
| --- | --- | --- | --- |
| `fact_grid_hourly_performance` | Fact | `date_hour_key`, `grid_zone_key`, `station_group_key` | Hourly grid loss performance, energy measures, weather aggregates, and market price measures. |
| `dim_date_hour` | Dimension | `date_hour_key` | Calendar and hour attributes used for time based analysis. |
| `dim_weather_station` | Dimension | `station_key` | Weather station metadata and historical station versions. |
| `dim_grid_zone` | Dimension | `grid_zone_key` | Grid zone, region, or national EE area used for loss reporting. |
| `dim_weather_condition` | Dimension | `weather_condition_key` | Standardized weather condition labels from observation fields. |

## SCD Justification

| Dimension | SCD type | Reason |
| --- | --- | --- |
| `dim_date_hour` | Static | Calendar dates, hours, weekends, and seasons do not change retroactively. |
| `dim_weather_station` | Type 2 | Station name, location, status, or sensor metadata can change. Historical observations must remain tied to the correct station version. |
| `dim_grid_zone` | Type 2 | Grid regions may be reorganized or renamed. Type 2 preserves historical comparisons using the grid structure valid at the time. |
| `dim_weather_condition` | Type 1 | Weather condition labels can be standardized or corrected without preserving old label variants. |

## Data Dictionary

| Table | Column | Type | Description |
| --- | --- | --- | --- |
| `fact_grid_hourly_performance` | `date_hour_key` | INTEGER | Foreign key to `dim_date_hour`. |
| `fact_grid_hourly_performance` | `grid_zone_key` | INTEGER | Foreign key to `dim_grid_zone`. |
| `fact_grid_hourly_performance` | `actual_loss_mwh` | NUMERIC | Measured or derived actual transmission loss for the hour. |
| `fact_grid_hourly_performance` | `planned_loss_mwh` | NUMERIC | Planned grid loss for the hour. |
| `fact_grid_hourly_performance` | `loss_variance_mwh` | NUMERIC | Difference between actual and planned losses. |
| `fact_grid_hourly_performance` | `consumption_mwh` | NUMERIC | Hourly electricity consumption. |
| `fact_grid_hourly_performance` | `production_mwh` | NUMERIC | Hourly electricity production. |
| `fact_grid_hourly_performance` | `avg_temperature_c` | NUMERIC | Average observed temperature for the zone and hour. |
| `fact_grid_hourly_performance` | `avg_wind_speed_ms` | NUMERIC | Average observed wind speed for the zone and hour. |
| `fact_grid_hourly_performance` | `total_precipitation_mm` | NUMERIC | Total observed precipitation for the zone and hour. |
| `fact_grid_hourly_performance` | `nordpool_price_eur_mwh` | NUMERIC | Nord Pool electricity price for the hour. |
| `dim_date_hour` | `date_hour_key` | INTEGER | Surrogate key, for example `YYYYMMDDHH`. |
| `dim_date_hour` | `full_timestamp` | TIMESTAMP | Exact hour timestamp. |
| `dim_date_hour` | `is_weekend` | BOOLEAN | Indicates Saturday or Sunday. |
| `dim_date_hour` | `season` | TEXT | Winter, spring, summer, or autumn. |
| `dim_weather_station` | `station_key` | INTEGER | Surrogate key for the station version. |
| `dim_weather_station` | `station_id` | TEXT | Source system station identifier. |
| `dim_weather_station` | `station_name` | TEXT | Weather station name. |
| `dim_weather_station` | `latitude` | NUMERIC | Station latitude. |
| `dim_weather_station` | `longitude` | NUMERIC | Station longitude. |
| `dim_weather_station` | `valid_from` | TIMESTAMP | Start of SCD Type 2 validity. |
| `dim_weather_station` | `valid_to` | TIMESTAMP | End of SCD Type 2 validity. |
| `dim_grid_zone` | `grid_zone_key` | INTEGER | Surrogate key for grid zone version. |
| `dim_grid_zone` | `zone_code` | TEXT | Grid zone code such as `EE` or regional code. |
| `dim_grid_zone` | `zone_name` | TEXT | Human readable grid zone name. |

## Demo SQL Queries

### 1. Highest Loss Variance by Temperature Band

```sql
SELECT
  d.date,
  d.hour,
  g.zone_name,
  f.avg_temperature_c,
  f.actual_loss_mwh,
  f.planned_loss_mwh,
  f.loss_variance_mwh
FROM fact_grid_hourly_performance f
JOIN dim_date_hour d ON f.date_hour_key = d.date_hour_key
JOIN dim_grid_zone g ON f.grid_zone_key = g.grid_zone_key
WHERE f.avg_temperature_c <= -10 OR f.avg_temperature_c >= 25
ORDER BY f.loss_variance_mwh DESC
LIMIT 20;
```

### 2. Loss Ratio by Workday and Weekend

```sql
SELECT
  d.is_weekend,
  ROUND(AVG(f.actual_loss_mwh / NULLIF(f.consumption_mwh, 0) * 100), 2) AS avg_loss_ratio_pct,
  ROUND(AVG(f.avg_temperature_c), 2) AS avg_temperature_c,
  COUNT(*) AS hours
FROM fact_grid_hourly_performance f
JOIN dim_date_hour d ON f.date_hour_key = d.date_hour_key
GROUP BY d.is_weekend
ORDER BY d.is_weekend;
```

### 3. Financial Loss Cost During Peak Price Hours

```sql
SELECT
  d.date,
  d.hour,
  f.actual_loss_mwh,
  f.nordpool_price_eur_mwh,
  f.actual_loss_mwh * f.nordpool_price_eur_mwh AS estimated_loss_cost_eur
FROM fact_grid_hourly_performance f
JOIN dim_date_hour d ON f.date_hour_key = d.date_hour_key
WHERE f.nordpool_price_eur_mwh >= 100
ORDER BY estimated_loss_cost_eur DESC
LIMIT 20;
```

## Suggested Dashboard Pages

- Executive overview with total actual losses, planned losses, loss variance, loss ratio, and estimated financial loss cost.
- Hourly trend page showing actual loss, planned loss, consumption, Nord Pool price, temperature, and wind speed.
- Weather sensitivity page comparing loss variance against temperature bands, wind speed, precipitation, and weather condition.
- Grid zone comparison page ranking zones by loss ratio under similar weather conditions.
- Data quality page showing latest load time, duplicate count, null checks, range check failures, and freshness status.

## Scope Notes

- Project 1 is architecture and modeling, so the report should describe the planned pipeline and star schema rather than claiming a full production implementation.
- The design deliberately uses micro batch API pulls because the source data is naturally hourly or 15 minute data.
- Kafka and Flink are not required for this scope. Airflow plus dbt is enough for the proposed lifecycle.
- For the next project, the same design can be implemented using Python ingestion scripts, PostgreSQL staging, dbt transformations, and Metabase or Superset reporting.

## Local Example Data Fetch

This repository also contains a small example collector script:

```bash
python3 fetch_project_data.py --start-date 2026-09-01 --end-date 2026-09-01
```

The script writes raw CSV examples into `data/`.

## LLM Disclosure

This README draft was prepared with assistance from ChatGPT Codex. Add the final chat link or disclosure text required by the course before submission.
