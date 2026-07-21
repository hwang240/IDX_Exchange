"""
Weeks 4-5: Data Cleaning and Preparation

This script covers the Weeks 4-5 handbook work:

1. Load the mortgage-enriched sold and listings datasets.
2. Convert date fields to datetime format.
3. Convert key numeric fields to numeric types.
4. Remove columns that are completely empty.
5. Add invalid numeric value flags.
6. Add date consistency flags.
7. Add geographic data quality flags.
8. Apply final Week 5 cleaning rules.
9. Save final cleaned datasets and cleaning reports.

The script intentionally keeps date and geographic quality flags in the final
dataset. It removes only records with clearly unusable core numeric/date values
and drops non-core columns with very high missingness.

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

HIGH_MISSING_THRESHOLD = 90.0


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


def drop_high_missing_columns(
    df: pd.DataFrame,
    dataset_name: str,
    threshold: float = HIGH_MISSING_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Drop non-core columns above the missing-value threshold.

    Core analysis columns and flag columns are protected because they are useful
    for Tableau filtering and for documenting data quality.
    """
    missing_pct = df.isna().mean() * 100
    drop_columns = [
        column
        for column, pct in missing_pct.items()
        if pct > threshold
        and column not in CORE_KEEP_COLUMNS
        and not column.endswith("_flag")
    ]
    report = pd.DataFrame(
        [
            {
                "dataset": dataset_name,
                "dropped_column": column,
                "missing_pct": float(missing_pct[column]),
                "reason": f"non-core column above {threshold:.0f}% missing",
            }
            for column in drop_columns
        ]
    )
    return df.drop(columns=drop_columns), report


def final_row_removal_rules(df: pd.DataFrame, dataset_name: str) -> dict[str, pd.Series]:
    """
    Define final row-removal rules.

    Sold rows need a valid close price and close date for transaction analysis.
    Listings rows may legitimately have missing ClosePrice/CloseDate, so the
    listing rules focus on listing date and physical/numeric fields.
    """
    rules = {
        "invalid_living_area": df["invalid_living_area_flag"],
        "invalid_days_on_market": df["invalid_days_on_market_flag"],
        "invalid_bedrooms": df["invalid_bedrooms_flag"],
        "invalid_bathrooms": df["invalid_bathrooms_flag"],
    }

    if dataset_name == "sold":
        rules["invalid_close_price"] = df["invalid_close_price_flag"]
        rules["missing_close_date"] = df["CloseDate"].isna()
        rules["missing_listing_contract_date"] = df["ListingContractDate"].isna()
    else:
        rules["missing_listing_contract_date"] = df["ListingContractDate"].isna()

    return rules


def apply_final_cleaning_rules(
    df: pd.DataFrame,
    dataset_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove clearly unusable rows and high-missing non-core columns."""
    working = df.copy()
    row_rules = final_row_removal_rules(working, dataset_name)
    removal_mask = pd.Series(False, index=working.index)
    row_report_rows = []

    for rule_name, mask in row_rules.items():
        mask = mask.fillna(False)
        row_report_rows.append(
            {
                "dataset": dataset_name,
                "rule": rule_name,
                "rows_matching_rule": int(mask.sum()),
            }
        )
        removal_mask = removal_mask | mask

    rows_before = len(working)
    working = working.loc[~removal_mask].copy()
    rows_removed = rows_before - len(working)

    working, column_drop_report = drop_high_missing_columns(working, dataset_name)

    summary = pd.DataFrame(
        [
            {
                "dataset": dataset_name,
                "rule": "total_unique_rows_removed",
                "rows_matching_rule": rows_removed,
            }
        ]
        + row_report_rows
    )

    if not column_drop_report.empty:
        column_drop_report["rows_matching_rule"] = None
        column_drop_report = column_drop_report.rename(columns={"reason": "rule"})
        column_drop_report["rule"] = "dropped_column: " + column_drop_report["dropped_column"]
        column_drop_report = column_drop_report[
            ["dataset", "rule", "rows_matching_rule", "missing_pct"]
        ]
    else:
        column_drop_report = pd.DataFrame(
            columns=["dataset", "rule", "rows_matching_rule", "missing_pct"]
        )

    final_report = pd.concat([summary, column_drop_report], ignore_index=True)
    return working, final_report


def clean_dataset(df: pd.DataFrame, dataset_name: str) -> dict[str, object]:
    """Run starter and final cleaning steps for one dataset."""
    before_rows, before_columns = df.shape

    cleaned, date_report = convert_dates(df)
    cleaned, numeric_report = convert_numeric(cleaned)
    cleaned, dropped_columns = drop_empty_columns(cleaned)
    cleaned = add_invalid_numeric_flags(cleaned)
    cleaned = add_date_consistency_flags(cleaned)
    cleaned = add_geographic_flags(cleaned)

    starter_rows, starter_columns = cleaned.shape
    final_cleaned, final_rule_report = apply_final_cleaning_rules(cleaned, dataset_name)
    final_rows, final_columns = final_cleaned.shape

    return {
        "dataset_name": dataset_name,
        "starter_cleaned": cleaned,
        "final_cleaned": final_cleaned,
        "date_report": date_report.assign(dataset=dataset_name),
        "numeric_report": numeric_report.assign(dataset=dataset_name),
        "dropped_columns": dropped_columns,
        "final_rule_report": final_rule_report,
        "row_summary": {
            "dataset": dataset_name,
            "rows_before": before_rows,
            "starter_rows_after": starter_rows,
            "final_rows_after": final_rows,
            "rows_removed_in_final_pass": starter_rows - final_rows,
            "columns_before": before_columns,
            "starter_columns_after": starter_columns,
            "final_columns_after": final_columns,
            "columns_dropped_as_all_null": len(dropped_columns),
            "additional_columns_dropped_in_final_pass": starter_columns - final_columns,
        },
        "starter_flag_summary": flag_summary(cleaned, dataset_name),
        "final_flag_summary": flag_summary(final_cleaned, dataset_name),
        "starter_missing_summary": missing_summary(cleaned, dataset_name),
        "final_missing_summary": missing_summary(final_cleaned, dataset_name),
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


def write_final_markdown_report(
    row_summary: pd.DataFrame,
    final_rules: pd.DataFrame,
    date_report: pd.DataFrame,
    numeric_report: pd.DataFrame,
    flags: pd.DataFrame,
) -> None:
    """Write the final Week 4-5 cleaning deliverable report."""
    lines = [
        "# Weeks 4-5 Final Cleaning Report",
        "",
        "This report documents the final cleaning pass used to create the analysis-ready CSV outputs. The script keeps quality-control flags for date and coordinate issues so analysts can filter them in Tableau instead of losing that audit trail.",
        "",
        "## Final before/after row and column counts",
        "",
        row_summary.to_markdown(index=False),
        "",
        "## Final row-removal and column-drop rules",
        "",
        final_rules.fillna("").to_markdown(index=False),
        "",
        "## Data type confirmations - dates",
        "",
        date_report.to_markdown(index=False),
        "",
        "## Data type confirmations - numeric fields",
        "",
        numeric_report.to_markdown(index=False),
        "",
        "## Date consistency and data quality flag counts",
        "",
        flags.to_markdown(index=False),
        "",
        "## Geographic data quality summary",
        "",
        flags[flags["flag"].isin([
            "missing_coordinates_flag",
            "zero_coordinates_flag",
            "positive_longitude_flag",
            "implausible_ca_coordinates_flag",
        ])].to_markdown(index=False),
        "",
        "## Transformation rationale",
        "",
        "- Date columns were parsed with `pd.to_datetime(..., errors='coerce')` so invalid date strings become null and can be audited.",
        "- Numeric columns were parsed with `pd.to_numeric(..., errors='coerce')` so invalid numeric strings become null and can be audited.",
        "- Completely empty columns were removed because they provide no analytical value.",
        "- Non-core columns above 90% missing were removed to reduce noise while keeping protected market-analysis fields.",
        "- Rows with clearly unusable core numeric/date values were removed from the final CSVs.",
        "- Date consistency and geographic issues were kept as boolean flags for filtering and review.",
        "",
    ]
    (OUTPUT_DIR / "week4_5_final_cleaning_report.md").write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading mortgage-enriched datasets...")
    sold = load_dataset(SOLD_INPUT, "sold")
    listings = load_dataset(LISTINGS_INPUT, "listings")

    print("Running starter cleaning steps...")
    sold_result = clean_dataset(sold, "sold")
    listings_result = clean_dataset(listings, "listings")

    print("Saving starter and final cleaned outputs and reports...")
    sold_result["starter_cleaned"].to_csv(
        OUTPUT_DIR / "sold_cleaning_started.csv", index=False
    )
    listings_result["starter_cleaned"].to_csv(
        OUTPUT_DIR / "listings_cleaning_started.csv", index=False
    )
    sold_result["final_cleaned"].to_csv(OUTPUT_DIR / "sold_cleaned.csv", index=False)
    listings_result["final_cleaned"].to_csv(
        OUTPUT_DIR / "listings_cleaned.csv", index=False
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
        [sold_result["final_flag_summary"], listings_result["final_flag_summary"]],
        ignore_index=True,
    )
    final_rules = pd.concat(
        [sold_result["final_rule_report"], listings_result["final_rule_report"]],
        ignore_index=True,
    )
    starter_missing = pd.concat(
        [sold_result["starter_missing_summary"], listings_result["starter_missing_summary"]],
        ignore_index=True,
    )
    final_missing = pd.concat(
        [sold_result["final_missing_summary"], listings_result["final_missing_summary"]],
        ignore_index=True,
    )

    row_summary.to_csv(OUTPUT_DIR / "cleaning_row_summary.csv", index=False)
    dropped_columns.to_csv(OUTPUT_DIR / "dropped_all_null_columns.csv", index=False)
    date_report.to_csv(OUTPUT_DIR / "date_type_conversion_report.csv", index=False)
    numeric_report.to_csv(OUTPUT_DIR / "numeric_type_conversion_report.csv", index=False)
    flags.to_csv(OUTPUT_DIR / "cleaning_flag_counts.csv", index=False)
    final_rules.to_csv(OUTPUT_DIR / "final_cleaning_rules_report.csv", index=False)
    starter_missing.to_csv(OUTPUT_DIR / "post_starter_cleaning_missing_summary.csv", index=False)
    final_missing.to_csv(OUTPUT_DIR / "final_cleaning_missing_summary.csv", index=False)

    write_markdown_report(row_summary, dropped_columns, date_report, numeric_report, flags)
    write_final_markdown_report(row_summary, final_rules, date_report, numeric_report, flags)

    print("\nWeeks 4-5 final cleaning complete.")
    print(row_summary.to_string(index=False))
    print(f"Reports saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
