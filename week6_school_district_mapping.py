"""
Week 6: School District Mapping

This script enriches the Week 4-5 cleaned IDX Exchange datasets with California
Unified School District names using a school district boundary GeoJSON.

Workflow:
1. Read the California School District boundary GeoJSON.
2. Keep only Unified school district polygons.
3. Convert each property's Latitude and Longitude into a geographic point.
4. Spatially join property points to Unified school district polygons.
5. Add the matched district name as a new column.
6. Save enriched local CSV outputs and a mapping summary report.

Generated CSV outputs are confidential project data and are written to
outputs/week6/, which is ignored by Git through .gitignore.
"""

from pathlib import Path
import os

import geopandas as gpd
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "outputs" / "week4_5"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "week6"

SOLD_INPUT = INPUT_DIR / "sold_cleaned.csv"
LISTINGS_INPUT = INPUT_DIR / "listings_cleaned.csv"

SCHOOL_DISTRICT_GEOJSON = Path(
    os.environ.get(
        "SCHOOL_DISTRICT_GEOJSON",
        Path.home() / "Downloads" / "DistrictAreas2526_-284845464123469011.geojson",
    )
)

DISTRICT_TYPE_COLUMN = "DistrictType"
DISTRICT_NAME_COLUMN = "DistrictName"
DISTRICT_COUNTY_COLUMN = "CountyName"
DISTRICT_OUTPUT_COLUMN = "UnifiedSchoolDistrict"
DISTRICT_COUNTY_OUTPUT_COLUMN = "UnifiedSchoolDistrictCounty"


def require_file(path: Path, description: str) -> None:
    """Fail clearly if an expected local input is missing."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def load_unified_school_districts(path: Path) -> gpd.GeoDataFrame:
    """Load the district GeoJSON and keep only Unified district polygons."""
    require_file(path, "school district GeoJSON")

    districts = gpd.read_file(path)
    required_columns = {
        DISTRICT_TYPE_COLUMN,
        DISTRICT_NAME_COLUMN,
        DISTRICT_COUNTY_COLUMN,
        "geometry",
    }
    missing_columns = required_columns - set(districts.columns)
    if missing_columns:
        raise ValueError(
            "School district GeoJSON is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if districts.crs is None:
        districts = districts.set_crs("EPSG:4326")
    else:
        districts = districts.to_crs("EPSG:4326")

    unified = districts[
        districts[DISTRICT_TYPE_COLUMN].astype(str).str.strip().eq("Unified")
    ].copy()

    unified = unified[
        [DISTRICT_NAME_COLUMN, DISTRICT_COUNTY_COLUMN, DISTRICT_TYPE_COLUMN, "geometry"]
    ]

    if unified.empty:
        raise ValueError("No Unified school districts were found in the GeoJSON.")

    return unified


def valid_coordinate_mask(df: pd.DataFrame) -> pd.Series:
    """Identify rows with usable latitude and longitude values."""
    latitude = pd.to_numeric(df["Latitude"], errors="coerce")
    longitude = pd.to_numeric(df["Longitude"], errors="coerce")

    return (
        latitude.notna()
        & longitude.notna()
        & latitude.between(-90, 90)
        & longitude.between(-180, 180)
        & latitude.ne(0)
        & longitude.ne(0)
    )


def add_school_districts(
    df: pd.DataFrame, districts: gpd.GeoDataFrame, dataset_name: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Spatially join property coordinates to Unified school district polygons."""
    required_property_columns = {"Latitude", "Longitude"}
    missing_columns = required_property_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing coordinate columns: {sorted(missing_columns)}"
        )

    enriched = df.copy()
    enriched[DISTRICT_OUTPUT_COLUMN] = pd.NA
    enriched[DISTRICT_COUNTY_OUTPUT_COLUMN] = pd.NA

    valid_mask = valid_coordinate_mask(enriched)
    valid_properties = enriched.loc[valid_mask, ["Latitude", "Longitude"]].copy()
    valid_properties["Latitude"] = pd.to_numeric(
        valid_properties["Latitude"], errors="coerce"
    )
    valid_properties["Longitude"] = pd.to_numeric(
        valid_properties["Longitude"], errors="coerce"
    )

    property_points = gpd.GeoDataFrame(
        valid_properties,
        geometry=gpd.points_from_xy(
            valid_properties["Longitude"], valid_properties["Latitude"]
        ),
        crs="EPSG:4326",
    )

    joined = gpd.sjoin(property_points, districts, how="left", predicate="within")

    matched = joined[[DISTRICT_NAME_COLUMN, DISTRICT_COUNTY_COLUMN]].rename(
        columns={
            DISTRICT_NAME_COLUMN: DISTRICT_OUTPUT_COLUMN,
            DISTRICT_COUNTY_COLUMN: DISTRICT_COUNTY_OUTPUT_COLUMN,
        }
    )

    # If a boundary overlap ever produces multiple matches for one property,
    # keep the first non-null match so the output remains one row per property.
    matched = matched.groupby(level=0).first()

    enriched.loc[matched.index, DISTRICT_OUTPUT_COLUMN] = matched[
        DISTRICT_OUTPUT_COLUMN
    ]
    enriched.loc[matched.index, DISTRICT_COUNTY_OUTPUT_COLUMN] = matched[
        DISTRICT_COUNTY_OUTPUT_COLUMN
    ]

    assigned_count = int(enriched[DISTRICT_OUTPUT_COLUMN].notna().sum())

    summary = {
        "dataset": dataset_name,
        "input_rows": int(len(enriched)),
        "valid_coordinate_rows": int(valid_mask.sum()),
        "invalid_or_missing_coordinate_rows": int((~valid_mask).sum()),
        "assigned_unified_school_district_rows": assigned_count,
        "unassigned_valid_coordinate_rows": int(valid_mask.sum() - assigned_count),
        "unique_unified_school_districts_assigned": int(
            enriched[DISTRICT_OUTPUT_COLUMN].nunique(dropna=True)
        ),
    }

    return enriched, summary


def write_top_district_report(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Summarize the most common matched districts for a dataset."""
    counts = (
        df[DISTRICT_OUTPUT_COLUMN]
        .fillna("Unassigned")
        .value_counts(dropna=False)
        .head(25)
        .rename_axis(DISTRICT_OUTPUT_COLUMN)
        .reset_index(name="row_count")
    )
    counts.insert(0, "dataset", dataset_name)
    return counts


def write_markdown_report(
    summary: pd.DataFrame, districts: gpd.GeoDataFrame, output_path: Path
) -> None:
    """Write a readable Week 6 mapping report."""
    lines = [
        "# Week 6 School District Mapping Report",
        "",
        "## Source",
        "",
        f"- School district GeoJSON: `{SCHOOL_DISTRICT_GEOJSON}`",
        f"- Unified district polygons used: {len(districts):,}",
        "",
        "## Method",
        "",
        "- Loaded the California school district boundary GeoJSON.",
        "- Filtered the boundary file to `DistrictType == \"Unified\"`.",
        "- Converted each property's `Latitude` and `Longitude` into a point.",
        "- Used a spatial join to match each property point to the Unified",
        "  School District polygon that contains it.",
        f"- Added `{DISTRICT_OUTPUT_COLUMN}` and",
        f"  `{DISTRICT_COUNTY_OUTPUT_COLUMN}` columns to the cleaned datasets.",
        "",
        "## Mapping Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Notes",
        "",
        "- Rows with missing, zero, or out-of-range coordinates are left",
        "  unassigned.",
        "- Some valid California property coordinates can still be unassigned if",
        "  they fall outside a Unified district polygon or on a boundary edge.",
        "- The output CSVs are confidential local project files and are excluded",
        "  from Git.",
        "",
    ]
    output_path.write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    require_file(SOLD_INPUT, "Week 4-5 cleaned sold dataset")
    require_file(LISTINGS_INPUT, "Week 4-5 cleaned listings dataset")

    districts = load_unified_school_districts(SCHOOL_DISTRICT_GEOJSON)

    outputs = []
    top_district_reports = []

    for dataset_name, input_path, output_path in [
        ("sold", SOLD_INPUT, OUTPUT_DIR / "sold_with_school_districts.csv"),
        (
            "listings",
            LISTINGS_INPUT,
            OUTPUT_DIR / "listings_with_school_districts.csv",
        ),
    ]:
        print(f"Loading {dataset_name}: {input_path}")
        df = pd.read_csv(input_path, low_memory=False)

        print(f"Mapping {dataset_name} records to Unified school districts...")
        enriched, summary = add_school_districts(df, districts, dataset_name)

        print(f"Saving {dataset_name} enriched output: {output_path}")
        enriched.to_csv(output_path, index=False)

        outputs.append(summary)
        top_district_reports.append(write_top_district_report(enriched, dataset_name))

    summary_df = pd.DataFrame(outputs)
    summary_df.to_csv(OUTPUT_DIR / "school_district_mapping_summary.csv", index=False)

    top_district_df = pd.concat(top_district_reports, ignore_index=True)
    top_district_df.to_csv(OUTPUT_DIR / "top_school_district_counts.csv", index=False)

    write_markdown_report(
        summary_df, districts, OUTPUT_DIR / "week6_school_district_mapping_report.md"
    )

    print("\nWeek 6 school district mapping complete.")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
