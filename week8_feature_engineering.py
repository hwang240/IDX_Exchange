"""
Week 8: Feature Engineering and Market Summary Tables

This script prepares the cleaned, enriched, outlier-filtered IDX datasets for
Tableau analysis. It creates analysis fields such as price per square foot,
close-to-list ratio, date parts, and timeline duration fields, then saves
summary tables by month, county, city, and Unified School District.

Generated CSV outputs are confidential project data and are written to
outputs/week8/, which is ignored by Git through .gitignore.
"""

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "outputs" / "week7"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "week8"

SOLD_INPUT = INPUT_DIR / "sold_outlier_filtered.csv"
LISTINGS_INPUT = INPUT_DIR / "listings_outlier_filtered.csv"

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
    "DaysOnMarket",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "LotSizeAcres",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

GROUPING_COLUMNS = {
    "monthly": ["year_month"],
    "county": ["CountyOrParish"],
    "city": ["CountyOrParish", "City"],
    "school_district": ["UnifiedSchoolDistrict"],
}


def require_file(path: Path, description: str) -> None:
    """Fail clearly if a required input file is missing."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def load_dataset(path: Path, dataset_name: str) -> pd.DataFrame:
    """Load a Week 7 filtered dataset."""
    require_file(path, f"Week 7 filtered {dataset_name} dataset")
    return pd.read_csv(path, low_memory=False)


def convert_core_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert common date and numeric fields used by feature calculations."""
    engineered = df.copy()

    for column in DATE_COLUMNS:
        if column in engineered.columns:
            engineered[column] = pd.to_datetime(engineered[column], errors="coerce")

    for column in NUMERIC_COLUMNS:
        if column in engineered.columns:
            engineered[column] = pd.to_numeric(engineered[column], errors="coerce")

    return engineered


def add_date_parts(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Add year/month fields for Tableau trend charts."""
    engineered = df.copy()

    if dataset_name == "sold" and "CloseDate" in engineered.columns:
        primary_date = engineered["CloseDate"]
    elif dataset_name == "listings" and "ListingContractDate" in engineered.columns:
        primary_date = engineered["ListingContractDate"]
    elif "CloseDate" in engineered.columns and engineered["CloseDate"].notna().any():
        primary_date = engineered["CloseDate"]
    elif "ListingContractDate" in engineered.columns:
        primary_date = engineered["ListingContractDate"]
    else:
        primary_date = pd.Series(pd.NaT, index=engineered.index)

    engineered["analysis_date"] = primary_date
    engineered["analysis_year"] = primary_date.dt.year
    engineered["analysis_month"] = primary_date.dt.month
    engineered["analysis_quarter"] = primary_date.dt.quarter
    engineered["year_month"] = primary_date.dt.to_period("M").astype("string")

    return engineered


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add core price and value ratio fields for market analysis."""
    engineered = df.copy()

    if {"ClosePrice", "LivingArea"}.issubset(engineered.columns):
        engineered["close_price_per_sqft"] = (
            engineered["ClosePrice"] / engineered["LivingArea"]
        ).where(engineered["LivingArea"] > 0)

    if {"ListPrice", "LivingArea"}.issubset(engineered.columns):
        engineered["list_price_per_sqft"] = (
            engineered["ListPrice"] / engineered["LivingArea"]
        ).where(engineered["LivingArea"] > 0)

    if {"ClosePrice", "ListPrice"}.issubset(engineered.columns):
        engineered["close_to_list_ratio"] = (
            engineered["ClosePrice"] / engineered["ListPrice"]
        ).where(engineered["ListPrice"] > 0)
        engineered["close_minus_list_price"] = (
            engineered["ClosePrice"] - engineered["ListPrice"]
        )
        engineered["sold_above_list_flag"] = engineered["ClosePrice"] > engineered[
            "ListPrice"
        ]
        engineered["sold_below_list_flag"] = engineered["ClosePrice"] < engineered[
            "ListPrice"
        ]
        engineered["sold_at_list_flag"] = engineered["ClosePrice"].eq(
            engineered["ListPrice"]
        )

    if {"ListPrice", "OriginalListPrice"}.issubset(engineered.columns):
        engineered["list_to_original_list_ratio"] = (
            engineered["ListPrice"] / engineered["OriginalListPrice"]
        ).where(engineered["OriginalListPrice"] > 0)
        engineered["list_minus_original_list_price"] = (
            engineered["ListPrice"] - engineered["OriginalListPrice"]
        )

    return engineered


def add_timeline_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add duration fields between key MLS timeline dates."""
    engineered = df.copy()

    if {"ListingContractDate", "PurchaseContractDate"}.issubset(engineered.columns):
        engineered["listing_to_contract_days"] = (
            engineered["PurchaseContractDate"] - engineered["ListingContractDate"]
        ).dt.days

    if {"PurchaseContractDate", "CloseDate"}.issubset(engineered.columns):
        engineered["contract_to_close_days"] = (
            engineered["CloseDate"] - engineered["PurchaseContractDate"]
        ).dt.days

    if {"ListingContractDate", "CloseDate"}.issubset(engineered.columns):
        engineered["listing_to_close_days"] = (
            engineered["CloseDate"] - engineered["ListingContractDate"]
        ).dt.days

    return engineered


def add_tableau_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add simple categorical labels that are convenient in Tableau."""
    engineered = df.copy()

    if "ClosePrice" in engineered.columns:
        bins = [0, 500_000, 750_000, 1_000_000, 1_500_000, 2_000_000, float("inf")]
        labels = [
            "Under $500K",
            "$500K-$750K",
            "$750K-$1M",
            "$1M-$1.5M",
            "$1.5M-$2M",
            "$2M+",
        ]
        engineered["close_price_band"] = pd.cut(
            engineered["ClosePrice"], bins=bins, labels=labels, right=False
        )

    if "DaysOnMarket" in engineered.columns:
        bins = [0, 8, 15, 31, 61, 91, float("inf")]
        labels = ["0-7", "8-14", "15-30", "31-60", "61-90", "91+"]
        engineered["days_on_market_band"] = pd.cut(
            engineered["DaysOnMarket"], bins=bins, labels=labels, right=False
        )

    if "UnifiedSchoolDistrict" in engineered.columns:
        engineered["UnifiedSchoolDistrict"] = engineered[
            "UnifiedSchoolDistrict"
        ].fillna("Unassigned")

    return engineered


def engineer_dataset(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Apply all Week 8 feature engineering steps."""
    engineered = convert_core_types(df)
    engineered = add_date_parts(engineered, dataset_name)
    engineered = add_price_features(engineered)
    engineered = add_timeline_features(engineered)
    engineered = add_tableau_labels(engineered)
    return engineered


def safe_groupby(df: pd.DataFrame, group_columns: list[str]) -> pd.core.groupby.DataFrameGroupBy:
    """Group only rows where the requested grouping values are present."""
    usable = df.copy()

    for column in group_columns:
        if column not in usable.columns:
            usable[column] = "Missing"
        usable[column] = usable[column].fillna("Missing")

    return usable.groupby(group_columns, dropna=False)


def summarize_sold_market(
    sold: pd.DataFrame, group_columns: list[str], summary_name: str
) -> pd.DataFrame:
    """Create sold-market summary metrics for one grouping level."""
    grouped = safe_groupby(sold, group_columns)

    summary = grouped.agg(
        sales_count=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        average_close_price=("ClosePrice", "mean"),
        median_price_per_sqft=("close_price_per_sqft", "median"),
        median_days_on_market=("DaysOnMarket", "median"),
        average_days_on_market=("DaysOnMarket", "mean"),
        median_close_to_list_ratio=("close_to_list_ratio", "median"),
        average_mortgage_rate=("rate_30yr_fixed", "mean"),
    ).reset_index()

    above_share = grouped["sold_above_list_flag"].mean().reset_index(
        name="pct_sold_above_list"
    )
    below_share = grouped["sold_below_list_flag"].mean().reset_index(
        name="pct_sold_below_list"
    )

    summary = summary.merge(above_share, on=group_columns, how="left")
    summary = summary.merge(below_share, on=group_columns, how="left")
    summary.insert(0, "summary_level", summary_name)

    return summary


def summarize_listing_market(
    listings: pd.DataFrame, group_columns: list[str], summary_name: str
) -> pd.DataFrame:
    """Create listing-market summary metrics for one grouping level."""
    grouped = safe_groupby(listings, group_columns)

    summary = grouped.agg(
        listing_count=("ListingKey", "count"),
        median_list_price=("ListPrice", "median"),
        average_list_price=("ListPrice", "mean"),
        median_list_price_per_sqft=("list_price_per_sqft", "median"),
        median_days_on_market=("DaysOnMarket", "median"),
        average_days_on_market=("DaysOnMarket", "mean"),
        average_mortgage_rate=("rate_30yr_fixed", "mean"),
    ).reset_index()

    if "ClosePrice" in listings.columns:
        closed_listing_count = grouped["ClosePrice"].apply(lambda s: s.notna().sum())
        summary = summary.merge(
            closed_listing_count.reset_index(name="closed_listing_count"),
            on=group_columns,
            how="left",
        )

    summary.insert(0, "summary_level", summary_name)

    return summary


def create_summary_outputs(
    sold: pd.DataFrame, listings: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    """Create and save all Week 8 market summary CSV files."""
    output_paths = []
    sold_summaries = []
    listing_summaries = []

    for summary_name, group_columns in GROUPING_COLUMNS.items():
        sold_summary = summarize_sold_market(sold, group_columns, summary_name)
        listing_summary = summarize_listing_market(listings, group_columns, summary_name)

        sold_path = OUTPUT_DIR / f"sold_{summary_name}_market_summary.csv"
        listing_path = OUTPUT_DIR / f"listings_{summary_name}_market_summary.csv"

        sold_summary.to_csv(sold_path, index=False)
        listing_summary.to_csv(listing_path, index=False)

        output_paths.extend([sold_path, listing_path])
        sold_summaries.append(sold_summary)
        listing_summaries.append(listing_summary)

    all_sold = pd.concat(sold_summaries, ignore_index=True, sort=False)
    all_listings = pd.concat(listing_summaries, ignore_index=True, sort=False)

    all_sold_path = OUTPUT_DIR / "sold_all_market_summaries.csv"
    all_listings_path = OUTPUT_DIR / "listings_all_market_summaries.csv"
    all_sold.to_csv(all_sold_path, index=False)
    all_listings.to_csv(all_listings_path, index=False)
    output_paths.extend([all_sold_path, all_listings_path])

    return all_sold, all_listings, output_paths


def feature_summary(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Summarize key Week 8 feature completeness for documentation."""
    feature_columns = [
        "close_price_per_sqft",
        "list_price_per_sqft",
        "close_to_list_ratio",
        "close_minus_list_price",
        "listing_to_contract_days",
        "contract_to_close_days",
        "listing_to_close_days",
        "analysis_year",
        "analysis_month",
        "year_month",
        "close_price_band",
        "days_on_market_band",
    ]

    rows = []
    for column in feature_columns:
        if column not in df.columns:
            continue
        rows.append(
            {
                "dataset": dataset_name,
                "feature": column,
                "non_missing_count": int(df[column].notna().sum()),
                "missing_count": int(df[column].isna().sum()),
                "non_missing_percent": round(df[column].notna().mean() * 100, 2),
            }
        )

    return pd.DataFrame(rows)


def write_report(
    sold: pd.DataFrame,
    listings: pd.DataFrame,
    feature_report: pd.DataFrame,
    sold_summaries: pd.DataFrame,
    listing_summaries: pd.DataFrame,
    output_paths: list[Path],
) -> None:
    """Write a concise Week 8 report for the internship deliverable."""
    monthly_sold = sold_summaries[sold_summaries["summary_level"].eq("monthly")]
    monthly_listing = listing_summaries[
        listing_summaries["summary_level"].eq("monthly")
    ]

    lines = [
        "# Week 8 Feature Engineering and Market Summary Report",
        "",
        "## Purpose",
        "",
        "Week 8 prepares the cleaned and outlier-filtered IDX datasets for Tableau",
        "dashboard development by adding analysis fields and creating grouped",
        "market summary tables.",
        "",
        "## Inputs",
        "",
        f"- Sold input: `{SOLD_INPUT}`",
        f"- Listings input: `{LISTINGS_INPUT}`",
        "",
        "## Feature Engineering Completed",
        "",
        "- Added price-per-square-foot fields.",
        "- Added close-to-list and list-to-original-list ratios.",
        "- Added sale/list price difference fields.",
        "- Added year, month, quarter, and year-month fields.",
        "- Added listing-to-contract, contract-to-close, and listing-to-close day",
        "  counts.",
        "- Added Tableau-friendly price and days-on-market bands.",
        "",
        "## Output Row Counts",
        "",
        f"- Sold feature-engineered rows: {len(sold):,}",
        f"- Listings feature-engineered rows: {len(listings):,}",
        "",
        "## Feature Completeness",
        "",
        feature_report.to_markdown(index=False),
        "",
        "## Monthly Sold Market Summary Preview",
        "",
        monthly_sold.head(12).to_markdown(index=False),
        "",
        "## Monthly Listings Market Summary Preview",
        "",
        monthly_listing.head(12).to_markdown(index=False),
        "",
        "## Output Files",
        "",
    ]

    for path in output_paths:
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "Generated CSV files are local confidential project outputs and are",
            "excluded from Git.",
            "",
        ]
    )

    (OUTPUT_DIR / "week8_feature_engineering_report.md").write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading sold data: {SOLD_INPUT}")
    sold = load_dataset(SOLD_INPUT, "sold")
    print(f"Loading listings data: {LISTINGS_INPUT}")
    listings = load_dataset(LISTINGS_INPUT, "listings")

    print("Engineering sold features...")
    sold_engineered = engineer_dataset(sold, "sold")
    print("Engineering listings features...")
    listings_engineered = engineer_dataset(listings, "listings")

    sold_output = OUTPUT_DIR / "sold_feature_engineered.csv"
    listings_output = OUTPUT_DIR / "listings_feature_engineered.csv"

    print(f"Saving sold feature-engineered dataset: {sold_output}")
    sold_engineered.to_csv(sold_output, index=False)
    print(f"Saving listings feature-engineered dataset: {listings_output}")
    listings_engineered.to_csv(listings_output, index=False)

    print("Creating market summary tables...")
    sold_summaries, listing_summaries, summary_paths = create_summary_outputs(
        sold_engineered, listings_engineered
    )

    feature_report = pd.concat(
        [
            feature_summary(sold_engineered, "sold"),
            feature_summary(listings_engineered, "listings"),
        ],
        ignore_index=True,
    )
    feature_report.to_csv(OUTPUT_DIR / "feature_completeness_report.csv", index=False)

    output_paths = [
        sold_output,
        listings_output,
        OUTPUT_DIR / "feature_completeness_report.csv",
        *summary_paths,
        OUTPUT_DIR / "week8_feature_engineering_report.md",
    ]

    write_report(
        sold_engineered,
        listings_engineered,
        feature_report,
        sold_summaries,
        listing_summaries,
        output_paths,
    )

    print("\nWeek 8 feature engineering complete.")
    print(f"Sold rows: {len(sold_engineered):,}")
    print(f"Listings rows: {len(listings_engineered):,}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
