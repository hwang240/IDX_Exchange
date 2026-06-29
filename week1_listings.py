"""Combine monthly CRMLS listing files for the Week 1 deliverable."""

from pathlib import Path
import re

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "csv"
OUTPUT_FILE = Path(__file__).resolve().parent / "listings.csv"
START_MONTH = "2024-01"
END_MONTH = "2026-05"


def expected_months() -> list[str]:
    """Return every required YYYYMM value from January 2024 through May 2026."""
    return [
        period.strftime("%Y%m")
        for period in pd.period_range(START_MONTH, END_MONTH, freq="M")
    ]


def remove_repeated_columns(data: pd.DataFrame, source: Path) -> pd.DataFrame:
    """Remove duplicate CSV headers that pandas renamed with .1, .2, etc."""
    repeated_columns = []

    for column in data.columns:
        match = re.fullmatch(r"(.+)\.(\d+)", column)
        if not match:
            continue

        original = match.group(1)
        if original not in data.columns:
            continue

        matching_rows = (
            data[column].eq(data[original])
            | (data[column].isna() & data[original].isna())
        )
        if not matching_rows.all():
            mismatch_count = int((~matching_rows).sum())
            print(
                f"  Warning: {column!r} differs from the original "
                f"{original!r} in {mismatch_count:,} row(s); preserving the "
                "original column."
            )

        repeated_columns.append(column)

    if repeated_columns:
        data = data.drop(columns=repeated_columns)
        print(
            f"  Removed {len(repeated_columns)} repeated header columns: "
            f"{', '.join(repeated_columns)}"
        )

    return data


def find_listing_files() -> list[Path]:
    """Find exactly one listing file for every required month."""
    files_by_month = {}

    for path in sorted(DATA_DIR.glob("CRMLSListing*.csv")):
        match = re.fullmatch(r"CRMLSListing(\d{6})\.csv", path.name)
        if match:
            files_by_month[match.group(1)] = path

    required = expected_months()
    missing = [month for month in required if month not in files_by_month]
    if missing:
        raise FileNotFoundError(
            "Missing listing files for: " + ", ".join(missing)
        )

    return [files_by_month[month] for month in required]


def main() -> None:
    """Load, concatenate, filter, validate, and save listing data."""
    listing_files = find_listing_files()
    frames = []
    input_row_total = 0

    print(f"Found {len(listing_files)} monthly listing files.")
    print(f"Required range: {START_MONTH} through {END_MONTH}\n")

    for path in listing_files:
        data = pd.read_csv(path, low_memory=False)
        rows_before = len(data)
        input_row_total += rows_before

        print(f"{path.name}: {rows_before:,} rows, {len(data.columns)} columns")
        data = remove_repeated_columns(data, path)
        frames.append(data)

    # Row count before concatenation: sum of all individual monthly files.
    print(f"\nRows before concatenation (monthly total): {input_row_total:,}")

    listings = pd.concat(frames, ignore_index=True, sort=False)

    # Row count after concatenation should equal the monthly total above.
    print(f"Rows after concatenation: {len(listings):,}")
    if len(listings) != input_row_total:
        raise ValueError("Listing row count changed during concatenation.")

    if "PropertyType" not in listings.columns:
        raise KeyError("PropertyType column is missing from the listing data.")

    # Row counts immediately before and after the required Residential filter.
    rows_before_filter = len(listings)
    residential_mask = (
        listings["PropertyType"]
        .astype("string")
        .str.strip()
        .eq("Residential")
        .fillna(False)
    )
    listings = listings.loc[residential_mask].copy()

    print(f"Rows before Residential filter: {rows_before_filter:,}")
    print(f"Rows after Residential filter: {len(listings):,}")
    print(f"Rows removed by Residential filter: {rows_before_filter - len(listings):,}")

    listings.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved {len(listings):,} Residential listing rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
