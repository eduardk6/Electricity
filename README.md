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
