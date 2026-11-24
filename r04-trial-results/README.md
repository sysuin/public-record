# R04 · How many clinical trials actually publish their results?

**Report:** https://sysuin.github.io/public-record/r04-trial-results/
**Scope:** interventional trials registered on ClinicalTrials.gov, the US National Library of Medicine's registry. All 612,892 records were downloaded through the official API (v2.0.5) on 22 November 2026; the registry's data timestamp was 20 November 2026. "Results" means summary results posted on ClinicalTrials.gov, or submitted and awaiting posting. It is not journal publication.

## What's here

| Path | What it is |
|---|---|
| `research.md` | Source, field definitions, the legal rules the "probably required" estimate imitates, cohorts, exclusions, robustness checks and every number |
| `scripts/` | Fetch, parse, analyse, server-side count checks, an independent second code path, charts. `sh scripts/run_all.sh <empty_raw_dir>` re-runs everything (about 35 minutes of downloading at NLM's rate guidance) |
| `data/` | Trial-level table (`interventional_trials.parquet`), tidy result tables, `headline_numbers.json`, `exclusion_log.csv`, `robustness_grid.csv`, `verification_table.csv` and `verification_server_counts.csv` |
| `charts/` | Analysis charts made while testing each finding |
| `report-build/` | Builds the report page from `data/`: `python3 report-build/build_pack.py . <fonts-folder> <out-folder>` |

## Source

- **ClinicalTrials.gov API v2**, US National Library of Medicine: `https://clinicaltrials.gov/api/v2/studies`. Field definitions: `https://clinicaltrials.gov/api/v2/studies/metadata`.
- The legal rules (FDAAA 801 and 42 CFR Part 11) are cited in `research.md` for the definition of the estimate only.

## What it can't tell you

"No results on ClinicalTrials.gov" does not mean "never published": a trial may report in a journal or another registry. **"Probably required" is our estimate from sponsor-entered fields, not a legal determination about any trial or sponsor.** Everything except the registry's own system dates is entered by sponsors. Sponsor names are not merged across corporate entities. The latest cohorts (2024–25) are provisional.

## Requirements

Python 3 with pandas, numpy, pyarrow, scipy, statsmodels and matplotlib. The report build also needs Playwright with Chrome.
