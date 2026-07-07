"""
Weeks 2-3: Mortgage Rate Enrichment

This script completes the second half of the Weeks 2-3 handbook work:

1. Fetch the FRED MORTGAGE30US 30-year fixed mortgage rate series.
2. Resample weekly mortgage rates to monthly averages.
3. Create year_month merge keys on the sold and listings datasets.
4. Merge monthly mortgage rates onto both combined datasets.
5. Validate that no MLS rows are missing mortgage rates after the merge.
6. Save enriched local CSV outputs.

Confidential enriched CSV outputs are written to outputs/week2_3/, which is
ignored by Git through the repository .gitignore.
"""

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
SOLD_PATH = PROJECT_DIR / "sold.csv"
LISTINGS_PATH = PROJECT_DIR / "listings.csv"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "week2_3"

FRED_MORTGAGE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"


def fetch_monthly_mortgage_rates() -> pd.DataFrame:
    """
    Fetch weekly FRED MORTGAGE30US rates and convert them to monthly averages.

    FRED returns weekly observations with columns:
    - observation_date
    - MORTGAGE30US

    The MLS datasets are monthly analysis datasets, so this script averages all
    weekly observations within each calendar month.
    """
    mortgage = pd.read_csv(FRED_MORTGAGE_URL, parse_dates=["observation_date"])
    mortgage = mortgage.rename(
        columns={
            "observation_date": "date",
            "MORTGAGE30US": "rate_30yr_fixed",
        }
    )
    mortgage["rate_30yr_fixed"] = pd.to_numeric(
        mortgage["rate_30yr_fixed"], errors="coerce"
    )
    mortgage = mortgage.dropna(subset=["date", "rate_30yr_fixed"])
    mortgage["year_month"] = mortgage["date"].dt.to_period("M").astype(str)

    monthly = (
        mortgage.groupby("year_month", as_index=False)
        .agg(
            rate_30yr_fixed=("rate_30yr_fixed", "mean"),
            weekly_observation_count=("rate_30yr_fixed", "size"),
            first_weekly_observation=("date", "min"),
            last_weekly_observation=("date", "max"),
        )
        .sort_values("year_month")
    )
    return monthly


def add_year_month_key(df: pd.DataFrame, date_column: str, dataset_name: str) -> pd.DataFrame:
    """Add a year_month key to an MLS dataset from the specified date column."""
    if date_column not in df.columns:
        raise KeyError(f"{dataset_name} dataset is missing required column: {date_column}")

    enriched = df.copy()
    parsed_date = pd.to_datetime(enriched[date_column], errors="coerce")
    null_date_count = int(parsed_date.isna().sum())

    if null_date_count:
        raise ValueError(
            f"{dataset_name} has {null_date_count:,} rows with invalid or missing "
            f"{date_column}; cannot guarantee complete mortgage-rate merge."
        )

    enriched["year_month"] = parsed_date.dt.to_period("M").astype(str)
    return enriched


def merge_mortgage_rates(
    df: pd.DataFrame,
    mortgage_monthly: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    """Left-merge mortgage rates and validate every row received a rate."""
    merged = df.merge(mortgage_monthly, on="year_month", how="left", validate="many_to_one")
    missing_rate_count = int(merged["rate_30yr_fixed"].isna().sum())

    if missing_rate_count:
        missing_months = sorted(
            merged.loc[merged["rate_30yr_fixed"].isna(), "year_month"].dropna().unique()
        )
        raise ValueError(
            f"{dataset_name} has {missing_rate_count:,} rows without a mortgage rate. "
            f"Missing months: {missing_months}"
        )

    return merged


def validation_summary(
    dataset_name: str,
    before: pd.DataFrame,
    after: pd.DataFrame,
    date_column: str,
) -> dict[str, object]:
    """Create a compact validation summary for one enriched dataset."""
    return {
        "dataset": dataset_name,
        "source_rows": len(before),
        "enriched_rows": len(after),
        "source_columns": before.shape[1],
        "enriched_columns": after.shape[1],
        "merge_date_column": date_column,
        "min_year_month": after["year_month"].min(),
        "max_year_month": after["year_month"].max(),
        "missing_rate_count": int(after["rate_30yr_fixed"].isna().sum()),
        "min_rate_30yr_fixed": after["rate_30yr_fixed"].min(),
        "max_rate_30yr_fixed": after["rate_30yr_fixed"].max(),
        "mean_rate_30yr_fixed": after["rate_30yr_fixed"].mean(),
    }


def write_markdown_report(
    mortgage_monthly: pd.DataFrame,
    validation: pd.DataFrame,
) -> None:
    """Save a readable mortgage enrichment report."""
    lines = [
        "# Weeks 2-3 Mortgage Rate Enrichment Report",
        "",
        "## Source",
        "",
        f"- FRED series: `MORTGAGE30US`",
        f"- Source URL: {FRED_MORTGAGE_URL}",
        "- Weekly observations were averaged to monthly rates before merging.",
        "",
        "## Merge logic",
        "",
        "- Sold dataset merge key: `year_month` derived from `CloseDate`.",
        "- Listings dataset merge key: `year_month` derived from `ListingContractDate`.",
        "- Merge type: left merge from MLS datasets to monthly mortgage rates.",
        "- Validation: fail the script if any MLS row has a missing `rate_30yr_fixed` after merge.",
        "",
        "## Validation summary",
        "",
        validation.to_markdown(index=False),
        "",
        "## Monthly mortgage-rate range used by the MLS data",
        "",
        mortgage_monthly.to_markdown(index=False),
        "",
    ]
    (OUTPUT_DIR / "mortgage_rate_enrichment_report.md").write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading combined Week 1 datasets...")
    sold = pd.read_csv(SOLD_PATH, low_memory=False)
    listings = pd.read_csv(LISTINGS_PATH, low_memory=False)

    print("Fetching and resampling FRED MORTGAGE30US mortgage rates...")
    mortgage_monthly = fetch_monthly_mortgage_rates()

    print("Creating MLS year_month keys...")
    sold_with_key = add_year_month_key(sold, "CloseDate", "sold")
    listings_with_key = add_year_month_key(listings, "ListingContractDate", "listings")

    needed_months = sorted(
        set(sold_with_key["year_month"].unique()) | set(listings_with_key["year_month"].unique())
    )
    mortgage_for_data = mortgage_monthly[mortgage_monthly["year_month"].isin(needed_months)].copy()

    if len(mortgage_for_data) != len(needed_months):
        missing_months = sorted(set(needed_months) - set(mortgage_for_data["year_month"]))
        raise ValueError(f"FRED mortgage data is missing required months: {missing_months}")

    print("Merging monthly mortgage rates onto MLS datasets...")
    sold_with_rates = merge_mortgage_rates(sold_with_key, mortgage_for_data, "sold")
    listings_with_rates = merge_mortgage_rates(
        listings_with_key, mortgage_for_data, "listings"
    )

    print("Saving enriched datasets and validation reports...")
    mortgage_for_data.to_csv(OUTPUT_DIR / "mortgage_rate_monthly.csv", index=False)
    sold_with_rates.to_csv(OUTPUT_DIR / "sold_with_mortgage_rates.csv", index=False)
    listings_with_rates.to_csv(OUTPUT_DIR / "listings_with_mortgage_rates.csv", index=False)

    validation = pd.DataFrame(
        [
            validation_summary("sold", sold, sold_with_rates, "CloseDate"),
            validation_summary("listings", listings, listings_with_rates, "ListingContractDate"),
        ]
    )
    validation.to_csv(OUTPUT_DIR / "mortgage_rate_merge_validation.csv", index=False)
    write_markdown_report(mortgage_for_data, validation)

    print("\nMortgage rate enrichment complete.")
    print(f"Monthly mortgage-rate rows used: {len(mortgage_for_data):,}")
    print(f"Sold rows enriched: {len(sold_with_rates):,}")
    print(f"Listings rows enriched: {len(listings_with_rates):,}")
    print("Missing sold mortgage rates:", int(sold_with_rates["rate_30yr_fixed"].isna().sum()))
    print(
        "Missing listings mortgage rates:",
        int(listings_with_rates["rate_30yr_fixed"].isna().sum()),
    )
    print(f"Reports saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
