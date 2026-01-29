# Stata regressions

This directory contains the Stata `.do` files used to generate the regression tables for:

Seymour, D. T., & Aydemir, R. (2024).  
**The Role of Market Structure in Airline Mergers: Evaluating Alternative Causes of Delays.**  
*Journal of Transport Economics and Policy*, 58(2), 150–172.  

Data: Harvard Dataverse (DOI: 10.7910/DVN/IUVNCX)

## Files
- `MarketStructureDeparture.do`: main results
- `MarketStructureArrival.do`: robustness / appendix results

## How to run
1. Download `delay.csv` from the Dataverse deposit (DOI above).
2. Place the file at: `data/delay.csv` (relative to the repository root).
3. From Stata, run:
   - `do stata/MarketStructureDeparture.do`
   - `do stata/MarketStructureArrival.do`

## Output
Tables are written to the `output/` directory (created automatically by the scripts).

## Dependencies (Stata packages)
These scripts require the following user-written packages:

- `reghdfe`
- `estout` (provides `esttab` / `eststo` / `estpost`)

Install from Stata using:
```stata
ssc install reghdfe, replace
ssc install estout, replace
