#!/usr/bin/env python3
"""Fetch raw Elering and Estonian Weather API data for Project 1.

Example:
    python3 fetch_project_data.py --start-date 2026-09-01 --end-date 2026-09-03
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ELERING_SYSTEM_WITH_PLAN_URL = "https://dashboard.elering.ee/api/system/with-plan/csv"
ELERING_NPS_PRICE_URL = "https://dashboard.elering.ee/api/nps/price"
WEATHER_HOURLY_URL = "https://publicapi.envir.ee/v1/combinedWeatherData/observationDataHourly"

ELERING_COLUMNS = [
    "timestamp_utc",
    "datetime_estonia",
    "production_mw",
    "consumption_mw",
    "wind_production_mw",
    "solar_production_mw",
    "solar_forecast_balance_responsible_mw",
    "solar_forecast_system_operator_mw",
    "frequency_hz",
    "system_balance_mw",
    "ac_balance_mw",
    "planned_production_mw",
    "planned_consumption_mw",
    "wind_forecast_balance_responsible_mw",
    "wind_forecast_system_operator_mw",
    "planned_losses_mw",
    "planned_system_balance_mw",
    "planned_ac_balance_mw",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True, help="First date, YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="Last date, YYYY-MM-DD")
    parser.add_argument("--output-dir", default="data/raw", help="Output folder")
    parser.add_argument("--weather-delay", type=float, default=0.05, help="Delay between weather API calls")
    return parser.parse_args()


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=60) as response:
        raw = response.read()
    for encoding in ("utf-8-sig", "cp1257", "iso-8859-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8-sig", errors="replace")


def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict:
    return json.loads(fetch_text(url, headers=headers))


def iso_utc(day: date) -> str:
    dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def fetch_elering_system_with_plan(start_date: date, end_date: date, output_dir: Path) -> Path:
    query = urlencode({"start": iso_utc(start_date), "end": iso_utc(end_date + timedelta(days=1))})
    text = fetch_text(f"{ELERING_SYSTEM_WITH_PLAN_URL}?{query}")

    rows = list(csv.reader(text.splitlines(), delimiter=";"))
    if not rows:
        raise RuntimeError("Elering returned no rows")

    output_path = output_dir / f"elering_system_with_plan_{start_date}_{end_date}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(ELERING_COLUMNS)
        for row in rows[1:]:
            if not any(row):
                continue
            writer.writerow((row + [""] * len(ELERING_COLUMNS))[: len(ELERING_COLUMNS)])

    return output_path


def fetch_nps_price(start_date: date, end_date: date, output_dir: Path) -> Path:
    query = urlencode({"start": iso_utc(start_date), "end": iso_utc(end_date + timedelta(days=1))})
    payload = fetch_json(f"{ELERING_NPS_PRICE_URL}?{query}")
    records = payload.get("data", {}).get("ee", [])
    if not records:
        raise RuntimeError("Elering NPS price endpoint returned no EE records")

    output_path = output_dir / f"nps_price_ee_{start_date}_{end_date}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "price"])
        writer.writeheader()
        writer.writerows(records)

    return output_path


def fetch_weather_hourly(start_date: date, end_date: date, output_dir: Path, delay: float) -> Path:
    records: list[dict[str, object]] = []

    for day in date_range(start_date, end_date):
        for hour in range(24):
            query = urlencode({"date": day.isoformat(), "hour": f"{hour:02d}"})
            payload = fetch_json(
                f"{WEATHER_HOURLY_URL}?{query}",
                headers={"accept": "application/json"},
            )
            entries = payload.get("entries", {}).get("entry", [])
            for entry in entries:
                if isinstance(entry, dict):
                    records.append(
                        {
                            "observation_date": day.isoformat(),
                            "observation_hour": f"{hour:02d}",
                            **entry,
                        }
                    )
            time.sleep(delay)

    if not records:
        raise RuntimeError("Weather API returned no records")

    first_columns = ["observation_date", "observation_hour", "station_id", "Jaam"]
    all_columns = sorted({key for record in records for key in record})
    fieldnames = first_columns + [column for column in all_columns if column not in first_columns]

    output_path = output_dir / f"weather_hourly_observations_{start_date}_{end_date}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def main() -> None:
    args = parse_args()
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    if end_date < start_date:
        raise ValueError("--end-date must be on or after --start-date")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    elering_path = fetch_elering_system_with_plan(start_date, end_date, output_dir)
    nps_path = fetch_nps_price(start_date, end_date, output_dir)
    weather_path = fetch_weather_hourly(start_date, end_date, output_dir, args.weather_delay)

    print(f"Wrote {elering_path}")
    print(f"Wrote {nps_path}")
    print(f"Wrote {weather_path}")


if __name__ == "__main__":
    main()
