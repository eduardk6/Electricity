#!/usr/bin/env python3
"""Build processed sample CSVs from raw API ingestion files.

This mirrors the first transformation step that would later be handled by dbt:

* keep only hourly Elering rows from the raw 15-minute source;
* join Elering rows to raw NPS price by timestamp;
* keep only the analytical Elering columns needed for the questions;
* filter raw weather observations to one representative station per county.

Example:
    python3 scripts/build_processed_samples.py --start-date 2026-09-01 --end-date 2026-09-14
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from select_weather_stations_by_county import COUNTY_STATIONS, OUTPUT_COLUMNS


ELERING_OUTPUT_COLUMNS = [
    "timestamp_utc",
    "datetime_estonia",
    "consumption_mw",
    "planned_consumption_mw",
    "planned_losses_mw",
    "nps_price_eur_mwh",
    "production_mw",
    "wind_production_mw",
    "solar_production_mw",
    "system_balance_mw",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True, help="First date, YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="Last date, YYYY-MM-DD")
    parser.add_argument("--raw-dir", default="data/raw", help="Raw data folder")
    parser.add_argument("--processed-dir", default="data/processed", help="Processed data folder")
    return parser.parse_args()


def normalize_decimal(value: str) -> str:
    return value.replace(",", ".") if value is not None else ""


def build_elering_hourly(raw_dir: Path, processed_dir: Path, start_date: str, end_date: str) -> Path:
    elering_path = raw_dir / f"elering_system_with_plan_{start_date}_{end_date}.csv"
    nps_path = raw_dir / f"nps_price_ee_{start_date}_{end_date}.csv"
    output_path = processed_dir / f"elering_hourly_with_plan_nps_price_{start_date}_{end_date}.csv"

    with nps_path.open(newline="", encoding="utf-8") as file:
        nps_by_timestamp = {row["timestamp"]: row["price"] for row in csv.DictReader(file)}

    with elering_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = []
        for row in reader:
            if row["datetime_estonia"][14:16] != "00":
                continue
            rows.append(
                {
                    "timestamp_utc": row["timestamp_utc"],
                    "datetime_estonia": row["datetime_estonia"],
                    "consumption_mw": normalize_decimal(row["consumption_mw"]),
                    "planned_consumption_mw": normalize_decimal(row["planned_consumption_mw"]),
                    "planned_losses_mw": normalize_decimal(row["planned_losses_mw"]),
                    "nps_price_eur_mwh": normalize_decimal(nps_by_timestamp.get(row["timestamp_utc"], "")),
                    "production_mw": normalize_decimal(row["production_mw"]),
                    "wind_production_mw": normalize_decimal(row["wind_production_mw"]),
                    "solar_production_mw": normalize_decimal(row["solar_production_mw"]),
                    "system_balance_mw": normalize_decimal(row["system_balance_mw"]),
                }
            )

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ELERING_OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def build_weather_county(raw_dir: Path, processed_dir: Path, start_date: str, end_date: str) -> Path:
    input_path = raw_dir / f"weather_hourly_observations_{start_date}_{end_date}.csv"
    output_path = processed_dir / f"weather_county_station_hourly_{start_date}_{end_date}.csv"
    station_to_county = {station: county for county, station in COUNTY_STATIONS.items()}

    with input_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [row for row in reader if row.get("Jaam") in station_to_county]

    for row in rows:
        row["maakond"] = station_to_county[row["Jaam"]]
        for column in ("tains", "ws10ma", "pr1hs", "rhins"):
            row[column] = normalize_decimal(row.get(column, ""))

    rows.sort(key=lambda row: (row["maakond"], row["observation_date"], row["observation_hour"]))

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})

    return output_path


def main() -> None:
    args = parse_args()
    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    elering_path = build_elering_hourly(raw_dir, processed_dir, args.start_date, args.end_date)
    weather_path = build_weather_county(raw_dir, processed_dir, args.start_date, args.end_date)

    print(f"Wrote {elering_path}")
    print(f"Wrote {weather_path}")


if __name__ == "__main__":
    main()
