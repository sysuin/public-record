# R03 · Which Indian airline is actually the most reliable?

**Report:** https://sysuin.github.io/public-record/r03-india-airlines/
**Scope:** scheduled domestic flights in India, as reported by the airlines to DGCA in its monthly domestic traffic reports, January 2018 to September 2026 (104 reports; April 2020 was never published). On-time figures cover departures from the airports DGCA lists: 4 until 2024, 6 in 2025, 10 in 2026.

## What's here

| Path | What it is |
|---|---|
| `research.md` | Sources with URLs and pull dates, extraction validation, exclusion log, robustness checks and every number |
| `scripts/` | Fetch, parse (two independent PDF methods), tidy, analyse, chart and verify. `sh scripts/run_all.sh` re-runs everything |
| `data/` | Tidy airline × month tables, airport tables, schedule coverage, validation spot-checks, `headline_numbers.json` |
| `charts/` | Analysis charts made while testing each finding |
| `report-build/` | Builds the report page from `data/`: `python3 report-build/build_pack.py . <fonts-folder> <out-folder>` |

## Sources

- **DGCA** monthly domestic traffic reports (dgca.gov.in → Data & Reports → Aviation Data & Statistics → Air Transport → Domestic).
- **DGCA** approved winter 2026 domestic schedules, used to measure what share of each airline's departures the on-time table covers.
- **AAI** 2026 domestic aircraft movement tables.

## What it can't tell you

Every figure is self-reported by the airlines. On-time means departures within 15 minutes, at the listed airports only; arrivals are not measured and no flight counts are published. The airport list changed in 2025 and 2026, and the Air India Group's composition changed in 2024. **Nothing here measures safety.**

## Requirements

Python 3 with pandas, numpy, scipy, matplotlib and pdfplumber (plus pdfminer.six for the second extraction). The report build also needs Playwright with Chrome.
