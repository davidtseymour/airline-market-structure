# airline-market-structure
Code supporting the replication of research on the role of airline market structure in determining airline delays.

This repository contains the data-processing pipelines and regression code used to produce the main tables and robustness checks for the accompanying papers. The workflow is:

1. Build analysis samples from a local database that integrates public sources (DOT OTP, NOAA LCD, FAA aircraft registry, BEA metro GDP, ACS).
2. Export analysis-ready CSV files.
3. Run Stata `.do` files to generate regression tables in `output/`.

## Data availability
The full `delay.csv` used by the Stata scripts is not stored in this repository. It is available via Harvard Dataverse (see `externality/README.md` for the DOI and download instructions). Place the file in `data/delay.csv`.
