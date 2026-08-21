# IDX Exchange Real Estate Analysis

This repository contains my Python scripts and documentation for the IDX Exchange real estate data analytics internship project.

## Project Overview

The project focuses on working with CRMLS listing and sold transaction data, preparing monthly datasets, and building analysis-ready files for later Tableau dashboard development.

## Current Progress

### Week 0 - MLS Data Pipeline Orientation

* Set up FTP access and downloaded the available monthly CRMLS files.
* Set up Python in VS Code and installed the required packages.
* Reviewed the listing and sold extraction workflows.
* Collected listing and sold files from January 2024 through June 2026.

### Week 1 - Monthly Dataset Aggregation

* Created separate aggregation scripts for listings and sold transactions.
* Validated that all 30 required months are present.
* Combined the monthly files from January 2024 through June 2026.
* Selected one sold file per month so duplicate `_filled` versions are not
  counted twice.
* Removed the two extra coordinate columns from `_filled` sold files.
* Removed repeated listing headers while preserving the original columns.
* Filtered both combined datasets to `PropertyType == "Residential"`.
* Printed row counts before and after concatenation and filtering.
* Saved the two continuing project datasets locally as `listings.csv` and
  `sold.csv`.

Verified Week 1 output:

| Dataset | Rows before filter | Residential rows |
| --- | ---: | ---: |
| Listings | 901,610 | 573,911 |
| Sold | 665,426 | 447,998 |

Both outputs cover every calendar month from January 2024 through June 2026.

### Weeks 2-3 - Dataset Structuring and Validation

* Created a validation and EDA script for the first Weeks 2-3 deliverable.
* Reviewed dataset shapes, column data types, null counts, high-missing
  columns, and market-analysis vs. metadata/support fields.
* Calculated PropertyType shares from the raw monthly files before the Week 1
  Residential filter.
* Produced numeric distribution summaries, histograms, and boxplots for the
  handbook's key numeric fields: `ClosePrice`, `ListPrice`,
  `OriginalListPrice`, `LivingArea`, `LotSizeAcres`, `BedroomsTotal`,
  `BathroomsTotalInteger`, `DaysOnMarket`, and `YearBuilt`.
* Flagged extreme numeric outliers using a 3x IQR rule for later review.
* Answered the suggested intern EDA questions for price, days on market,
  sale-to-list behavior, date consistency, and county median prices.
* Saved local validation outputs, reports, and supporting plots under
  `outputs/week2_3/`. These generated files are excluded from Git.
* Added the mortgage rate enrichment script for the second Weeks 2-3
  deliverable.
* Fetched the FRED `MORTGAGE30US` 30-year fixed mortgage rate series, converted
  weekly observations to monthly averages, and merged the monthly rates onto
  both combined datasets.
* Validated that every sold and listing row received a mortgage rate after the
  merge.

Verified Weeks 2-3 validation highlights:

| Question | Result |
| --- | --- |
| Sold Residential share before filtering | 67.32% |
| Listing Residential share before filtering | 63.65% |
| Sold dataset shape after Week 1 filter | 447,998 rows x 82 columns |
| Listings dataset shape after Week 1 filter | 573,911 rows x 73 columns |
| Median sold close price | $825,000 |
| Average sold close price | $1,192,694 |
| Median Days on Market | 18 days |
| Sold above list price | 40.05% |
| Sold below list price | 42.58% |
| Sold at list price | 17.37% |
| Rows with apparent date consistency issues | 530 |
| Sold mortgage-rate missing values after merge | 0 |
| Listing mortgage-rate missing values after merge | 0 |
| Mortgage-rate months merged | January 2024 through June 2026 |

### Weeks 4-5 - Data Cleaning and Preparation

* Started the Weeks 4-5 cleaning script using the June-inclusive,
  mortgage-enriched sold and listing datasets.
* Converted key date fields to datetime format: `CloseDate`,
  `PurchaseContractDate`, `ListingContractDate`, and
  `ContractStatusChangeDate`.
* Converted core numeric fields to numeric types, including price, living area,
  days on market, bedrooms, bathrooms, coordinates, and mortgage rate.
* Dropped columns that were completely empty while keeping core analysis
  fields protected.
* Added invalid numeric value flags for non-positive close price, non-positive
  living area, negative days on market, and negative bedrooms or bathrooms.
* Added date consistency flags: `listing_after_close_flag`,
  `purchase_after_close_flag`, and `negative_timeline_flag`.
* Added geographic quality flags for missing coordinates, zero coordinates,
  positive longitude, and implausible California coordinate values.
* Removed rows with clearly unusable core values, such as invalid living area,
  negative days on market, invalid sold close price, or missing required date
  fields.
* Dropped non-core columns with more than 90% missing values while keeping core
  market-analysis fields protected.
* Saved final cleaned analysis-ready datasets and reports locally under
  `outputs/week4_5/`.
  These generated files are excluded from Git.

Verified Weeks 4-5 final cleaning output:

| Dataset | Rows before | Final rows | Rows removed | Columns before | Final columns |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sold | 447,998 | 447,781 | 217 | 87 | 84 |
| Listings | 573,911 | 573,510 | 401 | 78 | 77 |

### Week 6 - School District Mapping

* Added a school district mapping script using the California School District
  Areas 2025-26 GeoJSON boundary file.
* Installed GeoPandas and supporting geospatial packages for spatial joins.
* Loaded the school district boundary file and filtered it to
  `DistrictType == "Unified"`.
* Converted each property's `Latitude` and `Longitude` values into geographic
  points.
* Used a spatial join to assign each property to the Unified School District
  polygon containing that property.
* Added `UnifiedSchoolDistrict` and `UnifiedSchoolDistrictCounty` fields to
  the cleaned sold and listings datasets.
* Saved enriched Week 6 CSV outputs and mapping reports locally under
  `outputs/week6/`. These generated files are excluded from Git.

Verified Week 6 school district mapping output:

| Dataset | Rows | Valid coordinate rows | Rows assigned to Unified School District | Unique Unified districts |
| --- | ---: | ---: | ---: | ---: |
| Sold | 447,781 | 431,526 | 327,692 | 331 |
| Listings | 573,510 | 492,909 | 379,583 | 337 |

### Week 7 - Outlier Detection and Data Quality

* Created an IQR-based outlier detection script for the handbook's key numeric
  fields: `ClosePrice`, `LivingArea`, and `DaysOnMarket`.
* Calculated Q1, Q3, IQR, lower bounds, and upper bounds for each field.
* Added field-level outlier flags instead of deleting records outright:
  `ClosePrice_iqr_outlier_flag`, `LivingArea_iqr_outlier_flag`, and
  `DaysOnMarket_iqr_outlier_flag`.
* Added `any_iqr_outlier_flag` to identify records flagged by any Week 7
  outlier rule.
* Saved both full flagged datasets and separate filtered analysis datasets.
* Produced a written before/after comparison of dataset size and median values.
* Saved local Week 7 outputs and reports under `outputs/week7/`. These
  generated files are excluded from Git.

Verified Week 7 outlier filtering output:

| Dataset | Rows before | Rows after | Rows removed | Percent removed |
| --- | ---: | ---: | ---: | ---: |
| Sold | 447,781 | 377,505 | 70,276 | 15.69% |
| Listings | 573,510 | 493,118 | 80,392 | 14.02% |

Median values before vs. after filtering:

| Dataset | Field | Median before | Median after | Change |
| --- | --- | ---: | ---: | ---: |
| Sold | ClosePrice | $825,000 | $787,500 | -$37,500 |
| Sold | LivingArea | 1,646 | 1,572 | -74 |
| Sold | DaysOnMarket | 18 | 16 | -2 |
| Listings | ClosePrice | $854,300 | $827,500 | -$26,800 |
| Listings | LivingArea | 1,671 | 1,613 | -58 |
| Listings | DaysOnMarket | 10 | 9 | -1 |

### Week 8 - Feature Engineering and Market Summary Tables

* Created a feature engineering script using the Week 7 outlier-filtered sold
  and listings datasets.
* Added Tableau-ready date fields: `analysis_date`, `analysis_year`,
  `analysis_month`, `analysis_quarter`, and `year_month`.
* Added pricing and value features such as `close_price_per_sqft`,
  `list_price_per_sqft`, `close_to_list_ratio`, `close_minus_list_price`,
  `list_to_original_list_ratio`, and `list_minus_original_list_price`.
* Added timeline features including `listing_to_contract_days`,
  `contract_to_close_days`, and `listing_to_close_days`.
* Added Tableau-friendly categorical bands for close price and days on market.
* Created grouped market summary tables by month, county, city, and Unified
  School District.
* Saved feature-engineered datasets and summary CSVs locally under
  `outputs/week8/`. These generated files are excluded from Git.

Verified Week 8 feature engineering output:

| Dataset | Feature-engineered rows | Analysis month coverage | Price-per-sqft completeness |
| --- | ---: | ---: | ---: |
| Sold | 377,505 | 100.00% | 99.97% |
| Listings | 493,118 | 100.00% | 99.90% for list price per sqft |

Week 8 summary tables created:

| Summary level | Sold table | Listings table |
| --- | --- | --- |
| Monthly | `sold_monthly_market_summary.csv` | `listings_monthly_market_summary.csv` |
| County | `sold_county_market_summary.csv` | `listings_county_market_summary.csv` |
| City | `sold_city_market_summary.csv` | `listings_city_market_summary.csv` |
| School district | `sold_school_district_market_summary.csv` | `listings_school_district_market_summary.csv` |

### Week 9 - Tableau Dashboard Development and Reporting

* Used the Week 8 feature-engineered datasets and summary tables to create
  Tableau Public dashboards.
* Built a market analysis dashboard for price trends, sales volume, market
  speed, and sale-to-list behavior.
* Built a school district dashboard to compare residential market performance
  by Unified School District.
* Published Tableau dashboard links for external review while keeping
  confidential MLS datasets and generated output files out of GitHub.
* Added a dated project progress note under `docs/` summarizing the current
  dashboard and final reporting phase.

Week 9 Tableau deliverables:

| Dashboard | Link |
| --- | --- |
| Market Analysis | [IDX Exchange Market Analysis Dashboard](https://public.tableau.com/app/profile/david.wang1702/viz/market_analysis_17870424882870/IDXExchangeMarketAnalysisDashboard) |
| School District Market Dashboard | [School District Market Dashboard](https://public.tableau.com/app/profile/david.wang1702/viz/school_district_market_dashboard/SchoolDistrictMarketDashboard) |

## Running the Scripts

Install Pandas if it is not already available:

```bash
python -m pip install pandas
```

Place the confidential monthly files in the local `csv/` directory, then run:

```bash
python week1_listings.py
python week1_sold.py
```

The scripts create `listings.csv` and `sold.csv` in the project directory.
These output files and all source CSVs are excluded from Git.

To run the first Weeks 2-3 validation and EDA script:

```bash
python week2_3_validation.py
```

The script reads `listings.csv`, `sold.csv`, and the confidential source files
in `csv/`. It saves local reports and filtered validation outputs under
`outputs/week2_3/`, which is excluded from Git.

To run the Weeks 2-3 mortgage rate enrichment script:

```bash
python week2_3_mortgage_rates.py
```

The script fetches the FRED `MORTGAGE30US` series, averages weekly observations
to monthly mortgage rates, merges the rates onto `sold.csv` using `CloseDate`
and onto `listings.csv` using `ListingContractDate`, and validates that there
are no missing mortgage rates after the merge. The enriched CSV outputs are
saved locally under `outputs/week2_3/` and excluded from Git.

To run the Weeks 4-5 cleaning script:

```bash
python week4_5_cleaning.py
```

The script reads the mortgage-enriched datasets from `outputs/week2_3/`, adds
cleaning and quality-control flags, removes rows with clearly unusable core
values, drops all-null and high-missing non-core columns, and saves final
cleaned outputs plus reports under `outputs/week4_5/`.

To run the Week 6 school district mapping script:

```bash
python -m pip install geopandas shapely pyogrio
python week6_school_district_mapping.py
```

The script reads the cleaned Week 4-5 datasets from `outputs/week4_5/` and the
California School District Areas 2025-26 GeoJSON downloaded locally from
California Open Data. It filters the boundary file to Unified districts,
spatially joins property coordinates to those district polygons, and saves
enriched local outputs plus summary reports under `outputs/week6/`.

To run the Week 7 outlier detection script:

```bash
python week7_outlier_detection.py
```

The script reads the Week 6 school-district-enriched datasets when available,
adds IQR outlier flag columns for `ClosePrice`, `LivingArea`, and
`DaysOnMarket`, saves full flagged datasets, saves separate filtered analysis
datasets, and writes before/after comparison reports under `outputs/week7/`.

To run the Week 8 feature engineering script:

```bash
python week8_feature_engineering.py
```

The script reads the Week 7 outlier-filtered datasets, creates Tableau-ready
analysis fields, saves feature-engineered sold and listings datasets, and
creates market summary tables by month, county, city, and Unified School
District under `outputs/week8/`.

## Next Steps

The next project phase is final report writing, dashboard review, and any
requested refinements to the Tableau Public dashboards.

## Important Note

Raw CSV files and source data are not included in this repository because the MLS data is confidential. This repository only contains code, documentation, and project notes.
