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

## Running the Week 1 Scripts

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

## Important Note

Raw CSV files and source data are not included in this repository because the MLS data is confidential. This repository only contains code, documentation, and project notes.
