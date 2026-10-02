#!/usr/bin/env python3
"""Filter Keskkonnaagentuur weather data to one representative station per county.

The input CSV is expected to contain hourly station observations from
`observationDataHourly`. The output keeps only selected stations and adds a
`maakond` column.

Example:
    python3 scripts/select_weather_stations_by_county.py \
        data/weather_hourly_observations_2026-09-01_2026-09-14.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


COUNTY_STATIONS = {
    "Harju maakond": "Tallinn-Harku",
    "Hiiu maakond": "Heltermaa",
    "Ida-Viru maakond": "Narva",
    "Jõgeva maakond": "Jõgeva",
    "Järva maakond": "Türi",
    "Lääne maakond": "Haapsalu",
    "Lääne-Viru maakond": "Kunda",
    "Põlva maakond": "Ahja",
    "Pärnu maakond": "Pärnu",
    "Rapla maakond": "Kuusiku",
    "Saare maakond": "Kuressaare linn",
    "Tartu maakond": "Tartu",
    "Valga maakond": "Valga",
    "Viljandi maakond": "Viljandi",
    "Võru maakond": "Võru",
}

OUTPUT_COLUMNS = [
    "maakond",
    "observation_date",
    "observation_hour",
    "station_id",
    "Jaam",
    "tains",
    "ws10ma",
    "pr1hs",
    "rhins",
    "pw15maEng",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", help="Weather CSV to filter")
    parser.add_argument(
        "--output-csv",
        help="Output path. Defaults to overwriting input CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv) if args.output_csv else input_path
    temp_path = output_path.with_suffix(".tmp.csv")

    station_to_county = {station: county for county, station in COUNTY_STATIONS.items()}

    with input_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        missing = [column for column in OUTPUT_COLUMNS if column != "maakond" and column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Input CSV is missing required columns: {missing}")
        rows = [row for row in reader if row.get("Jaam") in station_to_county]

    for row in rows:
        row["maakond"] = station_to_county[row["Jaam"]]

    rows.sort(key=lambda row: (row["maakond"], row["observation_date"], row["observation_hour"]))

    with temp_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})

    temp_path.replace(output_path)

    counties = {row["maakond"] for row in rows}
    print(f"Wrote {output_path}")
    print(f"Rows: {len(rows)}")
    print(f"Counties: {len(counties)}")


if __name__ == "__main__":
    main()
