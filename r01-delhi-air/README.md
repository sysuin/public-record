# R01 · Is Delhi's air getting worse?

**Report:** https://sysuin.github.io/public-record/r01-delhi-air/
**Scope:** the Central Pollution Control Board's daily city AQI for Delhi, Gurugram, Noida, Ghaziabad, Faridabad and Greater Noida, May 2015 to 20 November 2026. Every year is compared on the same dates, 1 October to 20 November.

## What's here

| Path | What it is |
|---|---|
| `research.md` | Sources with URLs and pull dates, method, robustness checks, the exclusion log and every number |
| `scripts/` | Download, parse, analyse and verify. `sh scripts/run_all.sh <empty-folder-for-raw-pdfs>` re-runs everything |
| `data/` | Derived tables (chart-ready CSVs, `results.json`, the exclusion log, the verification table) |
| `charts/` | Analysis charts made while testing each finding |
| `report-build/` | Builds the report page from `data/`: `python3 report-build/build_pack.py . <fonts-folder> <out-folder>` |

## Sources

- **Air quality:** CPCB daily National AQI bulletins, `https://www.cpcb.gov.in/upload/Downloads/AQI_Bulletin_YYYYMMDD.pdf` (4,218 files; 35 days were never published).
- **Farm fires:** ICAR-IARI CREAMS daily bulletins (Punjab, Haryana); NASA FIRMS MODIS detections as a cross-check.
- **Weather:** NASA MERRA-2 reanalysis (2026 from NASA GEOS-IT), used for the weather adjustment. IMD observations need an account and were not used.

Station-level CPCB data sits behind a CAPTCHA and was not used. The report says what that leaves open.

## Requirements

Python 3 with pandas, numpy, scipy, matplotlib, statsmodels and pdfplumber; poppler's `pdftotext`. The report build also needs Playwright with Chrome.
