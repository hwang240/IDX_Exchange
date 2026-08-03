"""
Week 7: Outlier Detection and Data Quality

This script applies IQR-based outlier detection to the Week 6 school-district
enriched datasets. It follows the handbook approach of flagging outliers first,
then saving a separate filtered analysis dataset instead of permanently
deleting records.

Deliverables:
1. Full flagged sold and listings datasets.
2. Clean filtered sold and listings datasets with IQR outliers removed.
3. Written before/after comparison of row counts and median values.
4. Field-level IQR threshold and outlier count report.

Generated CSV outputs are confidential project data and are written to
outputs/week7/, which is ignored by Git through .gitignore.
"""

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "outputs" / "week6"
FALLBACK_INPUT_DIR = PROJECT_DIR / "outputs" / "week4_5"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "week7"

INPUTS = {
    "sold": {
        "primary": INPUT_DIR / "sold_with_school_districts.csv",
        "fallback": FALLBACK_INPUT_DIR / "sold_cleaned.csv",
        "flagged_output": OUTPUT_DIR / "sold_outlier_flagged.csv",
        "filtered_output": OUTPUT_DIR / "sold_outlier_filtered.csv",
    },
    "listings": {
        "primary": INPUT_DIR / "listings_with_school_districts.csv",
        "fallback": FALLBACK_INPUT_DIR / "listings_cleaned.csv",
        "flagged_output": OUTPUT_DIR / "listings_outlier_flagged.csv",
        "filtered_output": OUTPUT_DIR / "listings_outlier_filtered.csv",
    },
}

OUTLIER_FIELDS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
IQR_MULTIPLIER = 1.5


def choose_input_path(dataset_name: str) -> Path:
    """Use Week 6 enriched data if available, otherwise use Week 4-5 cleaned data."""
    primary = INPUTS[dataset_name]["primary"]
    fallback = INPUTS[dataset_name]["fallback"]

    if primary.exists():
        return primary
    if fallback.exists():
        return fallback

    raise FileNotFoundError(
        f"Missing input for {dataset_name}. Expected either {primary} or {fallback}."
    )


def calculate_iqr_bounds(series: pd.Series) -> dict[str, float | int]:
    """Calculate IQR bounds and basic counts for one numeric field."""
    numeric = pd.to_numeric(series, errors="coerce")
    non_missing = numeric.dropna()

    if non_missing.empty:
        return {
            "q1": pd.NA,
            "q3": pd.NA,
            "iqr": pd.NA,
            "lower_bound": pd.NA,
            "upper_bound": pd.NA,
            "non_missing_count": 0,
            "missing_count": int(numeric.isna().sum()),
        }

    q1 = float(non_missing.quantile(0.25))
    q3 = float(non_missing.quantile(0.75))
    iqr = q3 - q1

    return {
        "q1": q1,
        "q3": q3,
        "iqr": float(iqr),
        "lower_bound": float(q1 - IQR_MULTIPLIER * iqr),
        "upper_bound": float(q3 + IQR_MULTIPLIER * iqr),
        "non_missing_count": int(non_missing.size),
        "missing_count": int(numeric.isna().sum()),
    }


def add_iqr_outlier_flags(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add one IQR outlier flag per field plus an overall outlier flag."""
    flagged = df.copy()
    threshold_rows = []
    field_flag_columns = []

    for field in OUTLIER_FIELDS:
        if field not in flagged.columns:
            threshold_rows.append(
                {
                    "dataset": dataset_name,
                    "field": field,
                    "field_exists": False,
                    "q1": pd.NA,
                    "q3": pd.NA,
                    "iqr": pd.NA,
                    "lower_bound": pd.NA,
                    "upper_bound": pd.NA,
                    "non_missing_count": 0,
                    "missing_count": len(flagged),
                    "outlier_count": pd.NA,
                    "outlier_percent_of_rows": pd.NA,
                }
            )
            continue

        numeric = pd.to_numeric(flagged[field], errors="coerce")
        flagged[field] = numeric

        bounds = calculate_iqr_bounds(numeric)
        flag_column = f"{field}_iqr_outlier_flag"
        field_flag_columns.append(flag_column)

        if pd.isna(bounds["lower_bound"]) or pd.isna(bounds["upper_bound"]):
            flagged[flag_column] = False
        else:
            flagged[flag_column] = numeric.notna() & (
                (numeric < bounds["lower_bound"]) | (numeric > bounds["upper_bound"])
            )

        outlier_count = int(flagged[flag_column].sum())
        threshold_rows.append(
            {
                "dataset": dataset_name,
                "field": field,
                "field_exists": True,
                **bounds,
                "outlier_count": outlier_count,
                "outlier_percent_of_rows": round(outlier_count / len(flagged) * 100, 2),
            }
        )

    if field_flag_columns:
        flagged["any_iqr_outlier_flag"] = flagged[field_flag_columns].any(axis=1)
    else:
        flagged["any_iqr_outlier_flag"] = False

    return flagged, pd.DataFrame(threshold_rows)


def dataset_comparison(
    original: pd.DataFrame, filtered: pd.DataFrame, dataset_name: str
) -> pd.DataFrame:
    """Create before/after row count and median comparison rows."""
    rows = []
    row_count_before = len(original)
    row_count_after = len(filtered)

    for field in OUTLIER_FIELDS:
        if field not in original.columns:
            rows.append(
                {
                    "dataset": dataset_name,
                    "field": field,
                    "rows_before": row_count_before,
                    "rows_after": row_count_after,
                    "rows_removed": row_count_before - row_count_after,
                    "percent_removed": round(
                        (row_count_before - row_count_after) / row_count_before * 100,
                        2,
                    ),
                    "median_before": pd.NA,
                    "median_after": pd.NA,
                    "median_change": pd.NA,
                }
            )
            continue

        median_before = pd.to_numeric(original[field], errors="coerce").median()
        median_after = pd.to_numeric(filtered[field], errors="coerce").median()

        rows.append(
            {
                "dataset": dataset_name,
                "field": field,
                "rows_before": row_count_before,
                "rows_after": row_count_after,
                "rows_removed": row_count_before - row_count_after,
                "percent_removed": round(
                    (row_count_before - row_count_after) / row_count_before * 100, 2
                ),
                "median_before": median_before,
                "median_after": median_after,
                "median_change": median_after - median_before,
            }
        )

    return pd.DataFrame(rows)


def summarize_outlier_removal(flagged: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Count how many rows each outlier flag contributes."""
    flag_columns = [f"{field}_iqr_outlier_flag" for field in OUTLIER_FIELDS]
    rows = []

    for flag_column in flag_columns:
        if flag_column in flagged.columns:
            rows.append(
                {
                    "dataset": dataset_name,
                    "flag": flag_column,
                    "flagged_rows": int(flagged[flag_column].sum()),
                    "flagged_percent_of_rows": round(
                        flagged[flag_column].sum() / len(flagged) * 100, 2
                    ),
                }
            )

    rows.append(
        {
            "dataset": dataset_name,
            "flag": "any_iqr_outlier_flag",
            "flagged_rows": int(flagged["any_iqr_outlier_flag"].sum()),
            "flagged_percent_of_rows": round(
                flagged["any_iqr_outlier_flag"].sum() / len(flagged) * 100, 2
            ),
        }
    )

    return pd.DataFrame(rows)


def write_markdown_report(
    threshold_report: pd.DataFrame,
    comparison_report: pd.DataFrame,
    removal_report: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write the handbook-required written before/after comparison."""
    lines = [
        "# Week 7 Outlier Detection Report",
        "",
        "## Method",
        "",
        "This script uses the Interquartile Range (IQR) method to flag extreme",
        "values in `ClosePrice`, `LivingArea`, and `DaysOnMarket`. For each",
        "field, it calculates Q1, Q3, IQR, a lower bound, and an upper bound:",
        "",
        "`lower = Q1 - 1.5 * IQR`",
        "",
        "`upper = Q3 + 1.5 * IQR`",
        "",
        "Rows outside those bounds are flagged. Following the handbook guidance,",
        "the script preserves the full flagged dataset and also saves a separate",
        "filtered analysis dataset with IQR outlier rows removed.",
        "",
        "## IQR Thresholds and Outlier Counts",
        "",
        threshold_report.to_markdown(index=False),
        "",
        "## Dataset Size and Median Values Before vs. After Filtering",
        "",
        comparison_report.to_markdown(index=False),
        "",
        "## Flag Summary",
        "",
        removal_report.to_markdown(index=False),
        "",
        "## Output Files",
        "",
        "- `outputs/week7/sold_outlier_flagged.csv`",
        "- `outputs/week7/sold_outlier_filtered.csv`",
        "- `outputs/week7/listings_outlier_flagged.csv`",
        "- `outputs/week7/listings_outlier_filtered.csv`",
        "",
        "These generated files are confidential local project outputs and are",
        "excluded from Git.",
        "",
    ]

    output_path.write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    threshold_reports = []
    comparison_reports = []
    removal_reports = []

    for dataset_name in INPUTS:
        input_path = choose_input_path(dataset_name)
        print(f"Loading {dataset_name}: {input_path}")
        df = pd.read_csv(input_path, low_memory=False)

        print(f"Adding IQR outlier flags for {dataset_name}...")
        flagged, threshold_report = add_iqr_outlier_flags(df, dataset_name)
        filtered = flagged.loc[~flagged["any_iqr_outlier_flag"]].copy()

        print(f"Saving full flagged {dataset_name} dataset...")
        flagged.to_csv(INPUTS[dataset_name]["flagged_output"], index=False)

        print(f"Saving filtered {dataset_name} analysis dataset...")
        filtered.to_csv(INPUTS[dataset_name]["filtered_output"], index=False)

        threshold_reports.append(threshold_report)
        comparison_reports.append(dataset_comparison(flagged, filtered, dataset_name))
        removal_reports.append(summarize_outlier_removal(flagged, dataset_name))

    threshold_report = pd.concat(threshold_reports, ignore_index=True)
    comparison_report = pd.concat(comparison_reports, ignore_index=True)
    removal_report = pd.concat(removal_reports, ignore_index=True)

    threshold_report.to_csv(OUTPUT_DIR / "iqr_threshold_report.csv", index=False)
    comparison_report.to_csv(
        OUTPUT_DIR / "before_after_median_comparison.csv", index=False
    )
    removal_report.to_csv(OUTPUT_DIR / "outlier_flag_summary.csv", index=False)

    write_markdown_report(
        threshold_report,
        comparison_report,
        removal_report,
        OUTPUT_DIR / "week7_outlier_detection_report.md",
    )

    print("\nWeek 7 outlier detection complete.")
    print(comparison_report.to_string(index=False))


if __name__ == "__main__":
    main()
