# IDX Exchange Real Estate Analysis

This repository contains my Python scripts and documentation for the IDX Exchange real estate data analytics internship project.

## Project Overview

The project focuses on working with CRMLS listing and sold transaction data, preparing monthly datasets, and building analysis-ready files for later Tableau dashboard development.

## Current Progress

### Week 0 - MLS Data Pipeline Orientation

* Set up FTP access and downloaded the available monthly CRMLS files.
* Set up Python in VS Code and installed the required packages.
* Reviewed the listing and sold extraction workflows.
* Collected listing and sold files from January 2024 through May 2026.

### Week 1 - Monthly Dataset Aggregation

* Created separate aggregation scripts for listings and sold transactions.
* Validated that all 29 required months are present.
* Combined the monthly files from January 2024 through May 2026.
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
| Listings | 897,612 | 571,589 |
| Sold | 639,877 | 430,436 |

Both outputs cover every calendar month from January 2024 through May 2026.

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

Verified Weeks 2-3 validation highlights:

| Question | Result |
| --- | --- |
| Sold Residential share before filtering | 67.27% |
| Listing Residential share before filtering | 63.68% |
| Sold dataset shape after Week 1 filter | 430,436 rows x 82 columns |
| Listings dataset shape after Week 1 filter | 571,589 rows x 73 columns |
| Median sold close price | $825,000 |
| Average sold close price | $1,193,108 |
| Median Days on Market | 18 days |
| Sold above list price | 40.10% |
| Sold below list price | 42.54% |
| Sold at list price | 17.36% |
| Rows with apparent date consistency issues | 520 |

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

## Next Steps

The remaining Weeks 2-3 task is mortgage rate enrichment: fetch the FRED
`MORTGAGE30US` series, resample it to monthly averages, merge it onto both
combined datasets, validate that mortgage rate values are not missing, and save
new enriched local CSVs.

## Important Note

Raw CSV files and source data are not included in this repository because the MLS data is confidential. This repository only contains code, documentation, and project notes.
