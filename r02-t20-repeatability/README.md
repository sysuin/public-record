# R02 · Does one T20 season predict the next?

**Report:** https://sysuin.github.io/public-record/r02-t20-repeatability/
**Scope:** every ball of 9,612 T20 matches across 32 competitions on Cricsheet (men's and women's franchise and domestic leagues, The Hundred, full-member internationals), 2008–2026. Every figure compares a player with the average of their league in that season.

## What's here

| Path | What it is |
|---|---|
| `research.md` | Sources, download date and file counts, method, exclusion log, robustness checks, verification table and every number |
| `scripts/` | Parse, build, measure, forecast and verify. `sh scripts/run_all.sh <raw-json-folder> <work-folder>` re-runs everything |
| `data/` | Derived tables: season-to-season results, the forecast contest, cross-league tests, exclusions, independent verification |
| `charts/` | Analysis charts made while testing each finding |
| `report-build/` | Builds the report page from `data/`: `python3 report-build/build_pack.py . <fonts-folder> <out-folder>` |

## Source and licence

Ball-by-ball data from [Cricsheet](https://cricsheet.org/downloads/), downloaded 21 November 2026 (14,419 files). Cricsheet transcribes official scorecards and releases its data under the Open Data Commons Attribution licence; credit "Data: Cricsheet" when reusing any chart or table. Cricsheet withholds 386 matches, which are therefore missing here.

## What it can't tell you

Pace against spin (not in the data), age (no birth dates), fielding, why any player's season changed, or anything about auction prices. Season-to-season figures only see players who were picked again. See the report's last section.

## Requirements

Python 3 with pandas, numpy, scipy and matplotlib. The report build also needs Playwright with Chrome.
