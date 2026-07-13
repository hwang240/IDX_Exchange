"""
Weeks 4-5: Data Cleaning and Preparation

This starter script covers the Week 4 portion of the Weeks 4-5 handbook work:

1. Load the mortgage-enriched sold and listings datasets.
2. Convert date fields to datetime format.
3. Convert key numeric fields to numeric types.
4. Remove columns that are completely empty.
5. Add invalid numeric value flags.
6. Add date consistency flags.
7. Add geographic data quality flags.
8. Save starter cleaned datasets and a cleaning report.

The script intentionally flags questionable records instead of deleting them.
This keeps the workflow auditable and lets Week 5 focus on final cleaning
decisions, column drops, and any row-removal rules.

Confidential cleaned CSV outputs are written to outputs/week4_5/, which is
ignored by Git through the repository .gitignore.
"""

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "outputs" / "week2_3"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "week4_5"

SOLD_INPUT = INPUT_DIR / "sold_with_mortgage_rates.csv"
LISTINGS_INPUT = INPUT_DIR / "listings_with_mortgage_rates.csv"

DATE_COLUMNS = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

NUMERIC_COLUMNS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

CORE_KEEP_COLUMNS = {
    "ListingKey",
    "ListingId",
    "PropertyType",
    "PropertySubType",
    "MlsStatus",
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
    "year_month",
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "Latitude",
    "Longitude",
    "UnparsedAddress",
    "City",
    "CountyOrParish",
    "StateOrProvince",
    "PostalCode",
    "rate_30yr_fixed",
}


def load_dataset(path: Path, dataset_name: str) -> pd.DataFrame:
    """Load one enriched dataset and fail clearly if it is missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {dataset_name} input: {path}. "
            "Run week2_3_mortgage_rates.py first."
        )
    return pd.read_csv(path, low_memory=False)


def convert_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert date fields to datetime and summarize invalid values."""
    cleaned = df.copy()
    rows = []

    for column in DATE_COLUMNS:
        if column not in cleaned.columns:
            rows.append(
                {
                    "column": column,
                    "exists": False,
                    "non_null_before": 0,
                    "invalid_or_missing_after_parse": None,
                    "min_date": None,
                    "max_date": None,
                }
            )
            continue

        non_null_before = int(cleaned[column].notna().sum())
        parsed = pd.to_datetime(cleaned[column], errors="coerce")
        cleaned[column] = parsed

        rows.append(
            {
                "column": column,
                "exists": True,
                "non_null_before": non_null_before,
                "invalid_or_missing_after_parse": int(parsed.isna().sum()),
                "min_date": parsed.min(),
                "max_date": parsed.max(),
            }
        )

    return cleaned, pd.DataFrame(rows)


def convert_numeric(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert numeric fields to numeric dtype and summarize missing values."""
    cleaned = df.copy()
    rows = []

    for column in NUMERIC_COLUMNS:
        if column not in cleaned.columns:
            rows.append(
                {
                    "column": column,
                    "exists": False,
                    "non_null_before": 0,
                    "non_null_after": 0,
                    "missing_after_parse": None,
                    "dtype_after": None,
                }
            )
            continue

        non_null_before = int(cleaned[column].notna().sum())
        parsed = pd.to_numeric(cleaned[column], errors="coerce")
        cleaned[column] = parsed

        rows.append(
            {
                "column": column,
                "exists": True,
                "non_null_before": non_null_before,
                "non_null_after": int(parsed.notna().sum()),
                "missing_after_parse": int(parsed.isna().sum()),
                "dtype_after": str(parsed.dtype),
            }
        )

    return cleaned, pd.DataFrame(rows)


def drop_empty_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Drop columns that are 100% missing, except protected core fields."""
    drop_columns = [
        column
        for column in df.columns
        if column not in CORE_KEEP_COLUMNS and df[column].isna().all()
    ]
    return df.drop(columns=drop_columns), drop_columns


def add_invalid_numeric_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag invalid numeric values named in the handbook."""
    cleaned = df.copy()

    cleaned["invalid_close_price_flag"] = (
        cleaned["ClosePrice"].notna() & (cleaned["ClosePrice"] <= 0)
        if "ClosePrice" in cleaned.columns
        else False
    )
    cleaned["invalid_living_area_flag"] = (
        cleaned["LivingArea"].notna() & (cleaned["LivingArea"] <= 0)
        if "LivingArea" in cleaned.columns
        else False
    )
    cleaned["invalid_days_on_market_flag"] = (
        cleaned["DaysOnMarket"].notna() & (cleaned["DaysOnMarket"] < 0)
        if "DaysOnMarket" in cleaned.columns
        else False
    )
    cleaned["invalid_bedrooms_flag"] = (
        cleaned["BedroomsTotal"].notna() & (cleaned["BedroomsTotal"] < 0)
        if "BedroomsTotal" in cleaned.columns
        else False
    )
    cleaned["invalid_bathrooms_flag"] = (
        cleaned["BathroomsTotalInteger"].notna()
        & (cleaned["BathroomsTotalInteger"] < 0)
        if "BathroomsTotalInteger" in cleaned.columns
        else False
    )

    return cleaned


def add_date_consistency_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag records that violate expected listing -> contract -> close order."""
    cleaned = df.copy()

    listing = cleaned.get("ListingContractDate")
    purchase = cleaned.get("PurchaseContractDate")
    close = cleaned.get("CloseDate")

    cleaned["listing_after_close_flag"] = (
        listing.notna() & close.notna() & (listing > close)
        if listing is not None and close is not None
        else False
    )
    cleaned["purchase_after_close_flag"] = (
        purchase.notna() & close.notna() & (purchase > close)
        if purchase is not None and close is not None
        else False
    )
    cleaned["negative_timeline_flag"] = (
        purchase.notna() & listing.notna() & (purchase < listing)
        if purchase is not None and listing is not None
        else False
    )

    return cleaned


def add_geographic_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag missing, zero, positive, or implausible California coordinates."""
    cleaned = df.copy()

    latitude = cleaned.get("Latitude")
    longitude = cleaned.get("Longitude")

    if latitude is None or longitude is None:
        cleaned["missing_coordinates_flag"] = True
        cleaned["zero_coordinates_flag"] = False
        cleaned["positive_longitude_flag"] = False
        cleaned["implausible_ca_coordinates_flag"] = False
        return cleaned

    cleaned["missing_coordinates_flag"] = latitude.isna() | longitude.isna()
    cleaned["zero_coordinates_flag"] = (latitude == 0) | (longitude == 0)
    cleaned["positive_longitude_flag"] = longitude > 0
    cleaned["implausible_ca_coordinates_flag"] = (
        latitude.notna()
        & longitude.notna()
        & (
            (latitude < 32)
            | (latitude > 42.5)
            | (longitude < -125)
            | (longitude > -114)
        )
    )

    return cleaned


def flag_summary(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Count boolean flag columns for one dataset."""
    flag_columns = [column for column in df.columns if column.endswith("_flag")]
    return pd.DataFrame(
        [
            {
                "dataset": dataset_name,
                "flag": column,
                "flagged_rows": int(df[column].sum()),
                "flagged_pct": float(df[column].mean() * 100),
            }
            for column in flag_columns
        ]
    )


def missing_summary(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Summarize missing values after starter cleaning."""
    return (
        pd.DataFrame(
            {
                "dataset": dataset_name,
                "column": df.columns,
                "missing_count": df.isna().sum().to_numpy(),
                "missing_pct": (df.isna().mean() * 100).to_numpy(),
                "dtype": [str(dtype) for dtype in df.dtypes],
            }
        )
        .sort_values(["missing_pct", "column"], ascending=[False, True])
        .reset_index(drop=True)
    )


def clean_dataset(df: pd.DataFrame, dataset_name: str) -> dict[str, object]:
    """Run starter cleaning steps for one dataset."""
    before_rows, before_columns = df.shape

    cleaned, date_report = convert_dates(df)
    cleaned, numeric_report = convert_numeric(cleaned)
    cleaned, dropped_columns = drop_empty_columns(cleaned)
    cleaned = add_invalid_numeric_flags(cleaned)
    cleaned = add_date_consistency_flags(cleaned)
    cleaned = add_geographic_flags(cleaned)

    after_rows, after_columns = cleaned.shape

    return {
        "dataset_name": dataset_name,
        "cleaned": cleaned,
        "date_report": date_report.assign(dataset=dataset_name),
        "numeric_report": numeric_report.assign(dataset=dataset_name),
        "dropped_columns": dropped_columns,
        "row_summary": {
            "dataset": dataset_name,
            "rows_before": before_rows,
            "rows_after": after_rows,
            "columns_before": before_columns,
            "columns_after": after_columns,
            "columns_dropped_as_all_null": len(dropped_columns),
        },
        "flag_summary": flag_summary(cleaned, dataset_name),
        "missing_summary": missing_summary(cleaned, dataset_name),
    }


def write_markdown_report(
    row_summary: pd.DataFrame,
    dropped_columns: pd.DataFrame,
    date_report: pd.DataFrame,
    numeric_report: pd.DataFrame,
    flags: pd.DataFrame,
) -> None:
    """Write a readable Week 4 starter cleaning report."""
    lines = [
        "# Weeks 4-5 Starter Cleaning Report",
        "",
        "This report covers the Week 4 starter cleaning pass. Records are flagged, not removed, so Week 5 can make final cleaning decisions transparently.",
        "",
        "## Before/after row and column counts",
        "",
        row_summary.to_markdown(index=False),
        "",
        "## Columns dropped as 100% missing",
        "",
        dropped_columns.to_markdown(index=False) if not dropped_columns.empty else "No columns were dropped.",
        "",
        "## Date type conversion report",
        "",
        date_report.to_markdown(index=False),
        "",
        "## Numeric type conversion report",
        "",
        numeric_report.to_markdown(index=False),
        "",
        "## Flag counts",
        "",
        flags.to_markdown(index=False),
        "",
        "## Notes for Week 5",
        "",
        "- Review flagged records before removing anything.",
        "- Decide which high-missing or metadata columns should be dropped permanently.",
        "- Decide whether invalid numeric rows should be removed or kept with flags.",
        "- Confirm coordinate bounds and any out-of-state records with the team.",
        "",
    ]
    (OUTPUT_DIR / "week4_5_cleaning_report.md").write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading mortgage-enriched datasets...")
    sold = load_dataset(SOLD_INPUT, "sold")
    listings = load_dataset(LISTINGS_INPUT, "listings")

    print("Running starter cleaning steps...")
    sold_result = clean_dataset(sold, "sold")
    listings_result = clean_dataset(listings, "listings")

    print("Saving starter cleaned outputs and reports...")
    sold_result["cleaned"].to_csv(OUTPUT_DIR / "sold_cleaning_started.csv", index=False)
    listings_result["cleaned"].to_csv(
        OUTPUT_DIR / "listings_cleaning_started.csv", index=False
    )

    row_summary = pd.DataFrame(
        [sold_result["row_summary"], listings_result["row_summary"]]
    )
    dropped_columns = pd.DataFrame(
        [
            {"dataset": result["dataset_name"], "dropped_column": column}
            for result in [sold_result, listings_result]
            for column in result["dropped_columns"]
        ]
    )
    date_report = pd.concat(
        [sold_result["date_report"], listings_result["date_report"]],
        ignore_index=True,
    )
    numeric_report = pd.concat(
        [sold_result["numeric_report"], listings_result["numeric_report"]],
        ignore_index=True,
    )
    flags = pd.concat(
        [sold_result["flag_summary"], listings_result["flag_summary"]],
        ignore_index=True,
    )
    missing = pd.concat(
        [sold_result["missing_summary"], listings_result["missing_summary"]],
        ignore_index=True,
    )

    row_summary.to_csv(OUTPUT_DIR / "cleaning_row_summary.csv", index=False)
    dropped_columns.to_csv(OUTPUT_DIR / "dropped_all_null_columns.csv", index=False)
    date_report.to_csv(OUTPUT_DIR / "date_type_conversion_report.csv", index=False)
    numeric_report.to_csv(OUTPUT_DIR / "numeric_type_conversion_report.csv", index=False)
    flags.to_csv(OUTPUT_DIR / "cleaning_flag_counts.csv", index=False)
    missing.to_csv(OUTPUT_DIR / "post_cleaning_missing_summary.csv", index=False)

    write_markdown_report(row_summary, dropped_columns, date_report, numeric_report, flags)

    print("\nWeek 4 starter cleaning complete.")
    print(row_summary.to_string(index=False))
    print(f"Reports saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
