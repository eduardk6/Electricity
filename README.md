# Estonian Electricity and Weather Data Modeling

Repository files for Project 1:

- `data/` - sample API data
- `scripts/` - API and sample-data scripts
- `sql/` - demo SQL queries

## Sample Data

```text
data/
|-- raw/
|   |-- elering_system_with_plan_2026-09-01_2026-09-14.csv
|   |-- nps_price_ee_2026-09-01_2026-09-14.csv
|   `-- weather_hourly_observations_2026-09-01_2026-09-14.csv
`-- processed/
    |-- elering_hourly_with_plan_nps_price_2026-09-01_2026-09-14.csv
    `-- weather_county_station_hourly_2026-09-01_2026-09-14.csv
```

| File | Rows | Columns |
| --- | ---: | ---: |
| `data/raw/elering_system_with_plan_2026-09-01_2026-09-14.csv` | 1345 | 18 |
| `data/raw/nps_price_ee_2026-09-01_2026-09-14.csv` | 1345 | 2 |
| `data/raw/weather_hourly_observations_2026-09-01_2026-09-14.csv` | 33264 | 25 |
| `data/processed/elering_hourly_with_plan_nps_price_2026-09-01_2026-09-14.csv` | 337 | 10 |
| `data/processed/weather_county_station_hourly_2026-09-01_2026-09-14.csv` | 5040 | 10 |

## APIs

| Source | Endpoint |
| --- | --- |
| Elering system data | `https://dashboard.elering.ee/api/system/with-plan/csv` |
| Elering NPS price | `https://dashboard.elering.ee/api/nps/price` |
| Keskkonnaagentuur weather observations | `https://publicapi.envir.ee/v1/combinedWeatherData/observationDataHourly` |

## How to Start

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Fetch raw API data:

```bash
python3 scripts/fetch_project_data.py --start-date 2026-09-01 --end-date 2026-09-14
```

Build processed sample data:

```bash
python3 scripts/build_processed_samples.py --start-date 2026-09-01 --end-date 2026-09-14
```

Filter weather observations to one representative station per county:

```bash
python3 scripts/select_weather_stations_by_county.py \
  data/raw/weather_hourly_observations_2026-09-01_2026-09-14.csv \
  --output-csv data/processed/weather_county_station_hourly_2026-09-01_2026-09-14.csv
```

## Demo SQL Queries

Demo queries are in `sql/demo_queries.sql`.

The queries answer:

1. Weekday vs weekend consumption under similar weather conditions
2. Consumption sensitivity to temperature below freezing
3. Planned grid loss cost during peak hours compared to off-peak night hours
4. NPS price comparison on days below -10 C vs days above freezing
5. Planned grid losses by weekday/weekend under similar weather bands

## Data Dictionary

### 1. Fact Table

Grain: Exactly one record per calendar hour for the Estonian national transmission grid.

| Column Name | Data Type | Constraint / Key | Description & Business Rules | Sample Value |
| --- | --- | --- | --- | --- |
| fact\_id | BIGSERIAL | PK, NOT NULL | Unique surrogate key for each hourly fact record. | 10425 |
| dim\_date\_id | INT | FK, NOT NULL | Foreign key referencing dim\_date.date\_key (YYYYMMDD). | 20261002 |
| dim\_time\_id | INT | FK, NOT NULL | Foreign key referencing dim\_time.time\_key (0–23). | 14 |
| dim\_weather\_band\_id | INT | FK, NOT NULL | Foreign key referencing dim\_weather\_band.weather\_key. | 2 |
| consumption\_mwh | NUMERIC(10,3) | NOT NULL, >= 0 | Total national actual electricity consumption in MWh. | 1142.550 |
| production\_mwh | NUMERIC(10,3) | NOT NULL, >= 0 | Total national actual electricity generation in MWh. | 980.120 |
| planned\_consumption | NUMERIC(10,3) | NOT NULL, >= 0 | Elering forecasted electricity consumption in MWh. | 1120.000 |
| planned\_losses\_mwh | NUMERIC(10,3) | NOT NULL, >= 0 | Elering planned grid transmission losses in MWh. | 28.450 |
| solar\_production\_mwh | NUMERIC(10,3) | NOT NULL, >= 0 | Total national solar PV power generation in MWh. | 145.200 |
| wind\_production\_mwh | NUMERIC(10,3) | NOT NULL, >= 0 | Total national wind power generation in MWh. | 310.800 |
| nps\_price\_eur\_mwh | NUMERIC(8,2) | NOT NULL | Nord Pool Day-Ahead spot price for EE bidding zone (€/MWh). | 84.50 |
| avg\_temp | NUMERIC(4,2) | NOT NULL | National population/station-averaged hourly temperature (°C). | -3.40 |

### 2. Dimension Table: dim\_date

SCD Type: Static — Calendar definitions are fixed and do not change retroactively.

| Column Name | Data Type | Constraint / Key | Description & Business Rules | Sample Value |
| --- | --- | --- | --- | --- |
| date\_key | INT | PK, NOT NULL | Surrogate integer key in YYYYMMDDformat. | 20261002 |
| full\_date | DATE | NOT NULL | Full calendar date in standard YYYY-MM-DD format. | 2026-10-02 |
| day\_of\_the\_week | INT | NOT NULL, 1..7 | Day of week index (1 = Monday, 7 = Sunday). | 5 |
| is\_weekend | BOOLEAN | NOT NULL | TRUE if Saturday or Sunday; FALSE for weekdays. | FALSE |
| season | VARCHAR(10) | NOT NULL | Meteorological season ('Winter', 'Spring', 'Summer', 'Autumn'). | 'Autumn' |

### 3. Dimension Table: dim\_time

SCD Type: Static — Diurnal 24-hour cycle and peak definitions are immutable.

| Column Name | Data Type | Constraint / Key | Description & Business Rules | Sample Value |
| --- | --- | --- | --- | --- |
| time\_key | INT | PK, NOT NULL | Hour surrogate identifier matching the hour value (0–23). | 14 |
| hour | INT | NOT NULL, 0..23 | Hour of the day in 24-hour format. | 14 |
| is\_peak | BOOLEAN | NOT NULL | TRUE for peak hours (08:00–20:00); FALSE for off-peak/night hours. | TRUE |

### 4. Dimension Table: dim\_weather\_band

SCD Type: SCD Type 1 — Label updates overwrite existing values directly as historical version tracking is unnecessary.

| Column Name | Data Type | Constraint / Key | Description & Business Rules | Sample Value |
| --- | --- | --- | --- | --- |
| weather\_key | INT | PK, NOT NULL | Surrogate key for the discrete temperature band. | 2 |
| weather\_band | VARCHAR(50) | NOT NULL | Classification label (e.g., 'Deep Frost (< -10C)', 'Freezing (-10C to 0C)', 'Mild (0C to 15C)'). | 'Freezing (-10C to 0C)' |
| sub\_zero | BOOLEAN | NOT NULL | TRUE if temperature is at or below freezing ($\le 0^\circ\text{C}$); FALSE otherwise. | TRUE |
