"""
Weeks 2-3: Dataset Structuring and Validation

This script completes the first half of the Weeks 2-3 handbook work:

1. Inspect the combined listing and sold datasets.
2. Document property type values and Residential filtering.
3. Create null-count and high-missing-value reports.
4. Produce numeric distribution summaries, histograms, and boxplots.
5. Identify extreme numeric outliers for later handling.
6. Answer the suggested intern EDA questions.
7. Save filtered/validated Residential datasets as new local CSV files.

Confidential CSV outputs are written to outputs/week2_3/, which is ignored by
Git through the repository .gitignore.
"""

import os
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
RAW_CSV_DIR = PROJECT_DIR / "csv"
SOLD_PATH = PROJECT_DIR / "sold.csv"
LISTINGS_PATH = PROJECT_DIR / "listings.csv"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "week2_3"

NUMERIC_FIELDS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
]

def clean_property_type(series: pd.Series) -> pd.Series:
    """Normalize property type values for consistent counting/filtering."""
    return series.astype("string").str.strip()


def selected_sold_files() -> list[Path]:
    """
    Return one sold CSV per month.

    If both normal and _filled versions exist for a month, prefer the normal
    file so the same month is not counted twice.
    """
    files_by_month: dict[str, list[Path]] = {}
    for path in sorted(RAW_CSV_DIR.glob("CRMLSSold*.csv")):
        month = path.stem.replace("CRMLSSold", "").replace("_filled", "")
        files_by_month.setdefault(month, []).append(path)

    selected = []
    for month, files in sorted(files_by_month.items()):
        normal = [path for path in files if not path.stem.endswith("_filled")]
        selected.append(normal[0] if normal else files[0])
    return selected


def selected_listing_files() -> list[Path]:
    """Return the monthly listing files."""
    return sorted(RAW_CSV_DIR.glob("CRMLSListing*.csv"))


def property_type_share(files: list[Path]) -> pd.DataFrame:
    """
    Count PropertyType values directly from the raw monthly files.

    This answers the Residential vs. other share question before the Week 1
    Residential filter was applied.
    """
    counts: dict[str, int] = {}
    total_rows = 0

    for path in files:
        chunk = pd.read_csv(path, usecols=["PropertyType"], low_memory=False)
        property_types = clean_property_type(chunk["PropertyType"]).fillna("Missing")
        file_counts = property_types.value_counts(dropna=False)
        total_rows += len(property_types)

        for property_type, count in file_counts.items():
            counts[str(property_type)] = counts.get(str(property_type), 0) + int(count)

    report = (
        pd.DataFrame(
            [{"PropertyType": key, "row_count": value} for key, value in counts.items()]
        )
        .sort_values("row_count", ascending=False)
        .reset_index(drop=True)
    )
    report["share_pct"] = report["row_count"] / total_rows * 100
    return report


def null_report(df: pd.DataFrame) -> pd.DataFrame:
    """Create a null-count and null-percentage table."""
    report = pd.DataFrame(
        {
            "column": df.columns,
            "missing_count": df.isna().sum().to_numpy(),
            "missing_pct": (df.isna().mean() * 100).to_numpy(),
            "dtype": [str(dtype) for dtype in df.dtypes],
        }
    )
    return report.sort_values("missing_pct", ascending=False).reset_index(drop=True)


def numeric_summary(df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """Create min/max/mean/median/percentile summaries for numeric fields."""
    rows = []
    percentiles = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]

    for field in fields:
        if field not in df.columns:
            continue

        values = pd.to_numeric(df[field], errors="coerce").dropna()
        if values.empty:
            continue

        summary = {
            "field": field,
            "non_null_count": int(values.count()),
            "missing_count": int(df[field].isna().sum()),
            "min": values.min(),
            "max": values.max(),
            "mean": values.mean(),
            "median": values.median(),
        }
        for percentile, value in values.quantile(percentiles).items():
            summary[f"p{int(percentile * 100):02d}"] = value
        rows.append(summary)

    return pd.DataFrame(rows)


def extreme_outlier_report(df: pd.DataFrame, dataset_name: str, fields: list[str]) -> pd.DataFrame:
    """
    Identify extreme outliers using the 3x IQR rule.

    Standard boxplots often flag values outside 1.5x IQR. For this early EDA
    step, the report uses a stricter 3x IQR threshold to identify the most
    extreme values for later review, not automatic deletion.
    """
    rows = []

    for field in fields:
        if field not in df.columns:
            continue

        values = pd.to_numeric(df[field], errors="coerce").dropna()
        if values.empty:
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - (3 * iqr)
        upper_bound = q3 + (3 * iqr)
        lower_outliers = values[values < lower_bound]
        upper_outliers = values[values > upper_bound]
        total_outliers = len(lower_outliers) + len(upper_outliers)

        rows.append(
            {
                "dataset": dataset_name,
                "field": field,
                "non_null_count": int(values.count()),
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "extreme_lower_bound": lower_bound,
                "extreme_upper_bound": upper_bound,
                "low_extreme_outlier_count": int(len(lower_outliers)),
                "high_extreme_outlier_count": int(len(upper_outliers)),
                "total_extreme_outlier_count": int(total_outliers),
                "extreme_outlier_pct": total_outliers / len(values) * 100,
                "min_value": values.min(),
                "max_value": values.max(),
            }
        )

    return pd.DataFrame(rows)


def date_consistency_report(sold: pd.DataFrame) -> pd.Series:
    """Count apparent date consistency issues in the sold dataset."""
    close_date = pd.to_datetime(sold.get("CloseDate"), errors="coerce")
    listing_date = pd.to_datetime(sold.get("ListingContractDate"), errors="coerce")
    purchase_date = pd.to_datetime(sold.get("PurchaseContractDate"), errors="coerce")

    listing_after_close = listing_date.notna() & close_date.notna() & (listing_date > close_date)
    purchase_after_close = purchase_date.notna() & close_date.notna() & (purchase_date > close_date)
    purchase_before_listing = (
        purchase_date.notna() & listing_date.notna() & (purchase_date < listing_date)
    )

    return pd.Series(
        {
            "listing_after_close_count": int(listing_after_close.sum()),
            "purchase_after_close_count": int(purchase_after_close.sum()),
            "purchase_before_listing_count": int(purchase_before_listing.sum()),
            "rows_with_any_date_issue": int(
                (listing_after_close | purchase_after_close | purchase_before_listing).sum()
            ),
        }
    )


def sale_to_list_report(sold: pd.DataFrame) -> pd.Series:
    """Calculate share of homes sold above, below, or equal to list price."""
    close_price = pd.to_numeric(sold["ClosePrice"], errors="coerce")
    list_price = pd.to_numeric(sold["ListPrice"], errors="coerce")
    valid = close_price.notna() & list_price.notna() & (list_price > 0)

    above = valid & (close_price > list_price)
    below = valid & (close_price < list_price)
    equal = valid & (close_price == list_price)

    valid_count = int(valid.sum())
    return pd.Series(
        {
            "valid_price_comparison_rows": valid_count,
            "sold_above_list_count": int(above.sum()),
            "sold_above_list_pct": above.sum() / valid_count * 100,
            "sold_below_list_count": int(below.sum()),
            "sold_below_list_pct": below.sum() / valid_count * 100,
            "sold_at_list_count": int(equal.sum()),
            "sold_at_list_pct": equal.sum() / valid_count * 100,
        }
    )


def county_price_report(sold: pd.DataFrame) -> pd.DataFrame:
    """Find counties with the highest median close prices."""
    close_price = pd.to_numeric(sold["ClosePrice"], errors="coerce")
    county_data = sold.assign(ClosePriceNumeric=close_price).dropna(
        subset=["CountyOrParish", "ClosePriceNumeric"]
    )

    report = (
        county_data.groupby("CountyOrParish")
        .agg(
            sold_count=("ClosePriceNumeric", "size"),
            median_close_price=("ClosePriceNumeric", "median"),
            average_close_price=("ClosePriceNumeric", "mean"),
        )
        .sort_values("median_close_price", ascending=False)
        .reset_index()
    )
    return report


def field_grouping_report(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """
    Separate likely market analysis fields from metadata/admin fields.

    The handbook asks interns to distinguish analysis fields from metadata.
    This grouping is intentionally conservative: fields commonly used for
    pricing, location, property characteristics, dates, and status are marked
    as market analysis fields; the rest are marked as metadata/support fields.
    """
    market_fields = {
        "ListingKey",
        "ListingId",
        "CloseDate",
        "PurchaseContractDate",
        "ListingContractDate",
        "ContractStatusChangeDate",
        "ClosePrice",
        "ListPrice",
        "OriginalListPrice",
        "PropertyType",
        "PropertySubType",
        "LivingArea",
        "LotSizeAcres",
        "LotSizeArea",
        "LotSizeSquareFeet",
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
        "MLSAreaMajor",
        "MlsStatus",
        "AssociationFee",
        "AssociationFeeFrequency",
        "GarageSpaces",
        "ParkingTotal",
        "PoolPrivateYN",
        "ViewYN",
        "WaterfrontYN",
        "FireplaceYN",
        "Stories",
        "Levels",
        "NewConstructionYN",
        "HighSchoolDistrict",
        "ElementarySchool",
        "MiddleOrJuniorSchool",
        "HighSchool",
    }

    rows = []
    for column in df.columns:
        rows.append(
            {
                "dataset": dataset_name,
                "column": column,
                "field_group": (
                    "market_analysis" if column in market_fields else "metadata_or_support"
                ),
            }
        )
    return pd.DataFrame(rows)


def days_on_market_distribution(sold: pd.DataFrame) -> pd.Series:
    """Summarize the DaysOnMarket distribution in plain terms."""
    dom = pd.to_numeric(sold["DaysOnMarket"], errors="coerce").dropna()
    return pd.Series(
        {
            "valid_days_on_market_rows": int(dom.count()),
            "min": dom.min(),
            "p25": dom.quantile(0.25),
            "median": dom.median(),
            "mean": dom.mean(),
            "p75": dom.quantile(0.75),
            "p95": dom.quantile(0.95),
            "p99": dom.quantile(0.99),
            "max": dom.max(),
        }
    )


def save_optional_plots(dataset_name: str, df: pd.DataFrame, fields: list[str]) -> None:
    """
    Save histograms and boxplots for numeric fields when matplotlib is available.

    The deliverable requires numeric summaries; the handbook also asks interns to
    generate histograms and boxplots, so this creates local PNGs as supporting
    EDA artifacts.
    """
    plot_dir = OUTPUT_DIR / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    matplotlib_config_dir = OUTPUT_DIR / "matplotlib_config"
    matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_config_dir))

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping histogram and boxplot PNGs.")
        return

    for field in fields:
        if field not in df.columns:
            continue

        values = pd.to_numeric(df[field], errors="coerce").dropna()
        if values.empty:
            continue

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(values, bins=50)
        ax.set_title(f"{dataset_name}: {field} histogram")
        ax.set_xlabel(field)
        ax.set_ylabel("Record count")
        fig.tight_layout()
        fig.savefig(plot_dir / f"{dataset_name}_{field}_histogram.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 2.8))
        ax.boxplot(values, vert=False, showfliers=True)
        ax.set_title(f"{dataset_name}: {field} boxplot")
        ax.set_xlabel(field)
        fig.tight_layout()
        fig.savefig(plot_dir / f"{dataset_name}_{field}_boxplot.png", dpi=150)
        plt.close(fig)


def write_markdown_report(
    sold: pd.DataFrame,
    listings: pd.DataFrame,
    raw_sold_property_share: pd.DataFrame,
    raw_listing_property_share: pd.DataFrame,
    sold_nulls: pd.DataFrame,
    listings_nulls: pd.DataFrame,
    sold_numeric: pd.DataFrame,
    listings_numeric: pd.DataFrame,
    outliers: pd.DataFrame,
    sale_to_list: pd.Series,
    date_issues: pd.Series,
    dom: pd.Series,
    counties: pd.DataFrame,
    field_groups: pd.DataFrame,
) -> None:
    """Write the Week 2-3 EDA answers to a Markdown report."""
    close_price = pd.to_numeric(sold["ClosePrice"], errors="coerce")
    residential_sold_share = raw_sold_property_share.loc[
        raw_sold_property_share["PropertyType"].eq("Residential"), "share_pct"
    ].iloc[0]
    residential_listing_share = raw_listing_property_share.loc[
        raw_listing_property_share["PropertyType"].eq("Residential"), "share_pct"
    ].iloc[0]

    lines = [
        "# Weeks 2-3 Dataset Structuring and Validation Report",
        "",
        "## Dataset shape after Week 1 Residential filter",
        "",
        f"- Sold dataset: {sold.shape[0]:,} rows and {sold.shape[1]:,} columns.",
        f"- Listings dataset: {listings.shape[0]:,} rows and {listings.shape[1]:,} columns.",
        "",
        "## Suggested intern questions",
        "",
        "### What is the Residential vs. other property type share?",
        "",
        (
            f"- Raw sold files: Residential is {residential_sold_share:.2f}% of records "
            f"before filtering."
        ),
        (
            f"- Raw listing files: Residential is {residential_listing_share:.2f}% of records "
            f"before filtering."
        ),
        "- The Week 1 output files are already filtered to Residential only.",
        "",
        "### What are the median and average close prices?",
        "",
        f"- Median sold close price: ${close_price.median():,.0f}.",
        f"- Average sold close price: ${close_price.mean():,.0f}.",
        "",
        "### What does the Days on Market distribution look like?",
        "",
        (
            f"- Median Days on Market is {dom['median']:.0f} days; "
            f"average is {dom['mean']:.1f} days."
        ),
        (
            f"- 25th percentile: {dom['p25']:.0f} days; "
            f"75th percentile: {dom['p75']:.0f} days; "
            f"95th percentile: {dom['p95']:.0f} days."
        ),
        "",
        "### What percentage of homes sold above vs. below list price?",
        "",
        f"- Sold above list: {sale_to_list['sold_above_list_pct']:.2f}%.",
        f"- Sold below list: {sale_to_list['sold_below_list_pct']:.2f}%.",
        f"- Sold at list: {sale_to_list['sold_at_list_pct']:.2f}%.",
        "",
        "### Are there any apparent date consistency issues?",
        "",
        (
            f"- Rows with ListingContractDate after CloseDate: "
            f"{date_issues['listing_after_close_count']:,}."
        ),
        (
            f"- Rows with PurchaseContractDate after CloseDate: "
            f"{date_issues['purchase_after_close_count']:,}."
        ),
        (
            f"- Rows with PurchaseContractDate before ListingContractDate: "
            f"{date_issues['purchase_before_listing_count']:,}."
        ),
        f"- Rows with any date issue: {date_issues['rows_with_any_date_issue']:,}.",
        "",
        "### Which counties have the highest median prices?",
        "",
        "The table below uses counties with at least 100 sold records so the result is not driven by one-off records.",
        "",
        counties[counties["sold_count"] >= 100].head(10).to_markdown(index=False),
        "",
        "## Field grouping",
        "",
        "Market analysis vs. metadata/support field counts:",
        "",
        field_groups.groupby(["dataset", "field_group"])
        .size()
        .reset_index(name="column_count")
        .to_markdown(index=False),
        "",
        "## High-missing columns",
        "",
        "### Sold columns above 90% missing",
        "",
        sold_nulls[sold_nulls["missing_pct"] > 90].to_markdown(index=False),
        "",
        "### Listings columns above 90% missing",
        "",
        listings_nulls[listings_nulls["missing_pct"] > 90].to_markdown(index=False),
        "",
        "## Numeric distribution summaries",
        "",
        "### Sold dataset",
        "",
        sold_numeric.to_markdown(index=False),
        "",
        "### Listings dataset",
        "",
        listings_numeric.to_markdown(index=False),
        "",
        "## Extreme outlier review",
        "",
        "Extreme outliers are flagged using a stricter 3x IQR rule. These rows are marked for later review, not removed at this stage.",
        "",
        outliers.to_markdown(index=False),
        "",
    ]

    (OUTPUT_DIR / "week2_3_validation_report.md").write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Week 1 Residential output files...")
    sold = pd.read_csv(SOLD_PATH, low_memory=False)
    listings = pd.read_csv(LISTINGS_PATH, low_memory=False)

    print("Documenting Residential filtering logic...")
    sold["PropertyType"] = clean_property_type(sold["PropertyType"])
    listings["PropertyType"] = clean_property_type(listings["PropertyType"])
    sold_residential = sold[sold["PropertyType"].eq("Residential")].copy()
    listings_residential = listings[listings["PropertyType"].eq("Residential")].copy()

    print("Calculating raw PropertyType shares from monthly source files...")
    raw_sold_property_share = property_type_share(selected_sold_files())
    raw_listing_property_share = property_type_share(selected_listing_files())

    print("Creating null-count reports...")
    sold_nulls = null_report(sold_residential)
    listings_nulls = null_report(listings_residential)

    print("Creating numeric distribution summaries...")
    sold_numeric = numeric_summary(sold_residential, NUMERIC_FIELDS)
    listings_numeric = numeric_summary(listings_residential, NUMERIC_FIELDS)
    outliers = pd.concat(
        [
            extreme_outlier_report(sold_residential, "sold", NUMERIC_FIELDS),
            extreme_outlier_report(listings_residential, "listings", NUMERIC_FIELDS),
        ],
        ignore_index=True,
    )

    print("Answering suggested intern questions...")
    sale_to_list = sale_to_list_report(sold_residential)
    date_issues = date_consistency_report(sold_residential)
    dom = days_on_market_distribution(sold_residential)
    counties = county_price_report(sold_residential)
    field_groups = pd.concat(
        [
            field_grouping_report(sold_residential, "sold"),
            field_grouping_report(listings_residential, "listings"),
        ],
        ignore_index=True,
    )

    print("Saving reports and filtered datasets...")
    sold_residential.to_csv(OUTPUT_DIR / "sold_residential_validated.csv", index=False)
    listings_residential.to_csv(OUTPUT_DIR / "listings_residential_validated.csv", index=False)
    raw_sold_property_share.to_csv(OUTPUT_DIR / "raw_sold_property_type_share.csv", index=False)
    raw_listing_property_share.to_csv(
        OUTPUT_DIR / "raw_listing_property_type_share.csv", index=False
    )
    sold_nulls.to_csv(OUTPUT_DIR / "sold_null_report.csv", index=False)
    listings_nulls.to_csv(OUTPUT_DIR / "listings_null_report.csv", index=False)
    sold_nulls[sold_nulls["missing_pct"] > 90].to_csv(
        OUTPUT_DIR / "sold_high_missing_columns.csv", index=False
    )
    listings_nulls[listings_nulls["missing_pct"] > 90].to_csv(
        OUTPUT_DIR / "listings_high_missing_columns.csv", index=False
    )
    sold_numeric.to_csv(OUTPUT_DIR / "sold_numeric_summary.csv", index=False)
    listings_numeric.to_csv(OUTPUT_DIR / "listings_numeric_summary.csv", index=False)
    outliers.to_csv(OUTPUT_DIR / "numeric_extreme_outlier_report.csv", index=False)
    sale_to_list.to_csv(OUTPUT_DIR / "sold_above_below_list_price.csv")
    date_issues.to_csv(OUTPUT_DIR / "sold_date_consistency_report.csv")
    dom.to_csv(OUTPUT_DIR / "sold_days_on_market_distribution.csv")
    counties.to_csv(OUTPUT_DIR / "county_median_price_report.csv", index=False)
    field_groups.to_csv(OUTPUT_DIR / "field_grouping_report.csv", index=False)

    save_optional_plots("sold", sold_residential, NUMERIC_FIELDS)
    save_optional_plots("listings", listings_residential, NUMERIC_FIELDS)

    write_markdown_report(
        sold_residential,
        listings_residential,
        raw_sold_property_share,
        raw_listing_property_share,
        sold_nulls,
        listings_nulls,
        sold_numeric,
        listings_numeric,
        outliers,
        sale_to_list,
        date_issues,
        dom,
        counties,
        field_groups,
    )

    print("\nWeek 2-3 validation complete.")
    print(f"Sold Residential rows: {len(sold_residential):,}")
    print(f"Listings Residential rows: {len(listings_residential):,}")
    print(f"Reports saved to: {OUTPUT_DIR}")
    print("\nSuggested intern question answers are in:")
    print(OUTPUT_DIR / "week2_3_validation_report.md")


if __name__ == "__main__":
    main()
