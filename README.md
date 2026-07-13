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

### Week 4 - Data Cleaning and Preparation Starter

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
* Saved starter cleaned datasets and reports locally under `outputs/week4_5/`.
  These generated files are excluded from Git.

Verified Week 4 starter cleaning output:

| Dataset | Rows before | Rows after | Columns before | Columns after | All-null columns dropped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sold | 447,998 | 447,998 | 87 | 91 | 8 |
| Listings | 573,911 | 573,911 | 78 | 82 | 8 |

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

To run the Week 4 starter cleaning script:

```bash
python week4_5_cleaning.py
```

The script reads the mortgage-enriched datasets from `outputs/week2_3/`, adds
cleaning and quality-control flags, drops columns that are completely empty, and
saves starter cleaned outputs plus reports under `outputs/week4_5/`.

## Next Steps

The next project phase is the Week 5 finish pass for data cleaning. This will
focus on deciding which flagged records or high-missing columns should be
removed, finalizing missing value handling, confirming coordinate rules with the
team, and saving the final analysis-ready cleaned datasets.

## Important Note

Raw CSV files and source data are not included in this repository because the MLS data is confidential. This repository only contains code, documentation, and project notes.
