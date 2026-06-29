"""Combine monthly CRMLS sold files for the Week 1 deliverable."""

from pathlib import Path
import re

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "csv"
OUTPUT_FILE = Path(__file__).resolve().parent / "sold.csv"
START_MONTH = "2024-01"
END_MONTH = "2026-05"
FILLED_COLUMNS = ["latfilled", "lonfilled"]


def expected_months() -> list[str]:
    """Return every required YYYYMM value from January 2024 through May 2026."""
    return [
        period.strftime("%Y%m")
        for period in pd.period_range(START_MONTH, END_MONTH, freq="M")
    ]


def find_sold_files() -> list[Path]:
    """Select one sold file per month, preferring the normal version."""
    candidates: dict[str, dict[str, Path]] = {}

    for path in sorted(DATA_DIR.glob("CRMLSSold*.csv")):
        match = re.fullmatch(r"CRMLSSold(\d{6})(_filled)?\.csv", path.name)
        if not match:
            continue

        month = match.group(1)
        version = "filled" if match.group(2) else "normal"
        candidates.setdefault(month, {})[version] = path

    required = expected_months()
    missing = [month for month in required if month not in candidates]
    if missing:
        raise FileNotFoundError("Missing sold files for: " + ", ".join(missing))

    selected = []
    print("Sold file selection (normal files are preferred over duplicates):")

    for month in required:
        versions = candidates[month]
        chosen = versions.get("normal") or versions.get("filled")
        if chosen is None:
            raise FileNotFoundError(f"No usable sold file found for {month}.")

        selected.append(chosen)
        ignored = [
            path.name for path in versions.values() if path != chosen
        ]
        note = f"; ignored duplicate: {', '.join(ignored)}" if ignored else ""
        print(f"  {month}: {chosen.name}{note}")

    return selected


def main() -> None:
    """Load, concatenate, filter, validate, and save sold data."""
    sold_files = find_sold_files()
    frames = []
    input_row_total = 0

    print(f"\nFound {len(sold_files)} unique monthly sold files.")
    print(f"Required range: {START_MONTH} through {END_MONTH}\n")

    for path in sold_files:
        data = pd.read_csv(path, low_memory=False)
        rows_before = len(data)
        input_row_total += rows_before

        print(f"{path.name}: {rows_before:,} rows, {len(data.columns)} columns")

        if "_filled" in path.stem:
            missing_filled_columns = [
                column for column in FILLED_COLUMNS if column not in data.columns
            ]
            if missing_filled_columns:
                raise KeyError(
                    f"{path.name}: expected _filled columns are missing: "
                    + ", ".join(missing_filled_columns)
                )

            data = data.drop(columns=FILLED_COLUMNS)
            print(f"  Removed extra columns: {', '.join(FILLED_COLUMNS)}")

        frames.append(data)

    # Row count before concatenation: sum of all selected monthly files.
    print(f"\nRows before concatenation (monthly total): {input_row_total:,}")

    sold = pd.concat(frames, ignore_index=True, sort=False)

    # Row count after concatenation should equal the monthly total above.
    print(f"Rows after concatenation: {len(sold):,}")
    if len(sold) != input_row_total:
        raise ValueError("Sold row count changed during concatenation.")

    if "PropertyType" not in sold.columns:
        raise KeyError("PropertyType column is missing from the sold data.")

    # Row counts immediately before and after the required Residential filter.
    rows_before_filter = len(sold)
    residential_mask = (
        sold["PropertyType"]
        .astype("string")
        .str.strip()
        .eq("Residential")
        .fillna(False)
    )
    sold = sold.loc[residential_mask].copy()

    print(f"Rows before Residential filter: {rows_before_filter:,}")
    print(f"Rows after Residential filter: {len(sold):,}")
    print(f"Rows removed by Residential filter: {rows_before_filter - len(sold):,}")

    sold.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved {len(sold):,} Residential sold rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
