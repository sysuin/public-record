# R04 — How many clinical trials actually publish their results? Research notes

**Series:** Public Record · **Compiled:** 22 Nov 2026 · **Data as of:** ClinicalTrials.gov dataTimestamp 2026-11-20T10:00:05 (API v2.0.5)

Every figure comes from one primary source: the ClinicalTrials.gov registry, published by the US National Library of Medicine (NLM), the body that runs it and generates every record's system dates (first submitted, results first submitted, results first posted, "unknown status"). No AACT, no TrialsTracker, no aggregators. Their published methods are cited for comparison only (§9).

Re-run everything: `sh scripts/run_all.sh <empty_raw_dir>` (≈35 min of polite downloading, then ≈6 min of analysis).

---

## 1. Source

| | |
|---|---|
| Publisher | US National Library of Medicine, ClinicalTrials.gov |
| Endpoint | `https://clinicaltrials.gov/api/v2/studies` (field-filtered with `fields=`, `pageSize=1000`, `pageToken` paging) |
| Version | `https://clinicaltrials.gov/api/v2/version` → `{"apiVersion":"2.0.5","dataTimestamp":"2026-11-20T10:00:05"}` — identical at the start and end of the download |
| Field definitions | `https://clinicaltrials.gov/api/v2/studies/metadata` (saved with the raw pages); data element definitions `https://clinicaltrials.gov/policy/protocol-definitions` and `https://clinicaltrials.gov/policy/results-definitions` |
| Registry size | `https://clinicaltrials.gov/api/v2/stats/size` → `totalStudies` 612,892 |
| Downloaded | 22 Nov 2026, 13:38 UTC onwards; one request every ~3 s (≈18/min, well under NLM's ~50/min guidance); User-Agent "research; public-data report" |
| Raw store | 613 gzipped JSON pages in a scratch folder outside the report (untrusted data; never executed); SHA-256 prefix of every page in `fetch_log.csv` there |
| Server-side check | 47 count queries to the same API using NLM's own search engine (`filter.advanced`, `countTotal=true`), `data/server_counts.json` |

Fields pulled (paths verified against the metadata endpoint): `protocolSection.identificationModule.nctId`, the whole `statusModule` (overall status, last known status, why stopped, start / primary completion / completion dates and their ACTUAL/ESTIMATED type, first-submitted, results first submitted / QC / posted, certification ("disposition") first submitted, results waived, delayed posting, last update), `designModule.studyType / phases / designInfo.primaryPurpose / designInfo.allocation / enrollmentInfo`, `sponsorCollaboratorsModule.leadSponsor` (name, class) and `responsibleParty.type`, the whole `oversightModule` (FDA-regulated drug, FDA-regulated device, unapproved device, PPSD, US export, DMC, FDAAA 801 violation flag), `contactsLocationsModule.locations.country`, `armsInterventionsModule.interventions.type`, `hasResults`, `derivedSection.miscInfoModule` (submission tracking: `estimatedResultsFirstSubmitDate` for results submitted but still in NLM quality-control review, submission cycles, resets), and `annotationSection` (unposted-results and FDA violation annotations).

**Does the source clear the bar?** Yes. ClinicalTrials.gov is the registry itself, run by the body that applies the system dates; the API is its official programmatic interface. Caveat that travels: everything in a record except the system dates is entered by the sponsor or investigator, so status, dates, phase, sponsor class and the FDA flags are **self-reported** and unaudited by NLM except for format/QC.

### Definitions used (from the metadata endpoint)
- `hasResults` = "Flag that indicates if a study has posted results on public site" (function: `Present(ResultsFirstSubmitDate)`).
- `resultsFirstSubmitDate` = "The date on which the study sponsor or investigator first submits a study record with summary results information" — i.e. the *first* submission, even if NLM's QC review sent it back.
- `estimatedResultsFirstSubmitDate` = "Results First Submitted Date but not yet Posted (e.g., still under QC review)".
- `dispFirstSubmitDate` = "the date on which the study sponsor or investigator first submitted a certification or an extension request to delay submission of results … can delay results submission up to 2 years after this date".

**Our outcome, "results submitted":** posted results (`hasResults`) **or** results submitted and waiting in QC (`estimatedResultsFirstSubmitDate`). Date of submission = `resultsFirstSubmitDate`, else `estimatedResultsFirstSubmitDate`. This matches the law, which counts submission, not posting. "Posted only" is a robustness variant.

## 2. The law the proxy imitates (for the denominator turn)
FDAAA 801 (2007) and its Final Rule, 42 CFR Part 11 (effective 18 Jan 2017):
- **§11.22(b)** — for trials initiated on or after 18 Jan 2017, a trial is an applicable clinical trial if it is interventional and (drug) studies a US FDA-regulated drug or biologic in a phase other than phase 1, or (device) studies a US FDA-regulated device with a primary purpose other than feasibility (or is a required pediatric postmarket surveillance); **and** has at least one US facility, **or** is under an IND/IDE, **or** studies a product manufactured in and exported from the US. Source: https://www.law.cornell.edu/cfr/text/42/11.22
- **§11.42** — results are required for applicable trials of approved products, and, for trials with a **primary completion date on or after 18 Jan 2017**, also for unapproved products. https://www.law.cornell.edu/cfr/text/42/11.42
- **§11.44** — results are due "no later than 1 year after the primary completion date"; a certification (new use, or seeking initial approval) delays the deadline to 30 days after an FDA decision, with an outer limit of 2 years after the certification; extensions for good cause can be requested before the deadline. https://www.law.cornell.edu/cfr/text/42/11.44

(The eCFR site, ecfr.gov, refused automated access; the Cornell LII copy of the CFR text was used.)

## 3. Method

**Pipeline** (`scripts/`): `01_fetch.py` (pages → raw folder, resumable, back-off) → `02_parse.py` (flatten to one row per study, pandas) → `03_analysis.py` (all tests → `data/*.csv`, `data/headline_numbers.json`) → `04_server_counts.py` (NLM's own search counts) → `05_verify.py` (independent second path: raw JSON + `json`/`csv`/`datetime` only, no pandas, no shared code; compares with the main path and with the server counts) → `06_charts.py`. All Python runs as `python3 -I` with data paths as arguments.

**Reference date:** 20 Nov 2026 (the data timestamp). **Dates given as month only** ("2019-06") are set to the last day of the month (benefit of the doubt to the sponsor); first-of-month is a robustness variant.

**Interventional only.** Observational studies and expanded-access records are excluded throughout (they have no results obligation of this kind).

**Cohorts**
- *Headline cohort:* interventional, overall status COMPLETED, primary completion date (PCD) in 2008–2023. 2008 is the first full year of FDAAA results posting (from Sept 2008); stopping at 2023 gives everyone ≥ ~3 years.
- *Due cohort:* interventional, not withdrawn/withheld, PCD marked ACTUAL, PCD from 18 Jan 2017 to 20 Nov 2025 (12-month window fully elapsed).
- *Like-for-like cohort:* the same but PCD to 20 Nov 2024, so **every trial has had a full 24 months**. All comparisons of groups use this cohort and fixed windows (within 12 months, within 24 months) so recent trials are not penalised for having had less time.
- *Ended cohort (status rot):* interventional, not withdrawn/withheld, PCD (actual or estimated) at least 2 years before 20 Nov 2026.

**"Probably required" proxy — not a legal determination.** Built only from registry fields (§2 mapping):

| Proxy | Definition |
|---|---|
| **main** | interventional; not withdrawn/withheld; `isFdaRegulatedDrug` or `isFdaRegulatedDevice` = true; phase not "Phase 1"/"Early Phase 1" alone (Phase 1/2 counts as beyond phase 1, as in the rule); not a device-only feasibility study; at least one US facility (incl. Puerto Rico, Guam, USVI, American Samoa, N. Mariana Is.) **or** `isUsExport` = true |
| strict | main + a US facility (export alone not enough) + study start on/after 18 Jan 2017 (the date from which §11.22(b)'s data-element test applies) + phase explicitly 1/2, 2, 2/3, 3, 4 or N/A |
| broad | main, but trials whose FDA flags are **missing** also count if they have a drug/biologic/device/genetic/radiation/combination/diagnostic intervention |
| noloc | main without the location/export condition (catches non-US trials run under a US IND/IDE, which the registry does not reveal) |
| lite | for the long time series only (FDA flags only exist from 2017): drug/biologic/device-type intervention + US facility + beyond phase 1 + not feasibility. Used for "before and after 2017" |

What the proxy cannot see: IND/IDE numbers (not public), whether the product is FDA-regulated beyond the sponsor's own tick box, approved-vs-unapproved status before 2017, and whether a responsible party was granted an extension (certification and extension requests share one date field) or a waiver.

**Intervals.** Proportions: Wilson 95% intervals. Differences: Newcombe hybrid-score 95% intervals. Sponsor comparisons "with the same trial mix": a logistic model of each outcome on sponsor group + phase + product (drug/device/both) + PCD year + US site, then every trial is assigned each sponsor group in turn and the predicted rates averaged (standardisation); 95% intervals from 200 bootstrap resamples of trials (seed 20261122).

**Second path.** `05_verify.py` re-reads the raw pages and recomputes every headline quantity with its own date parser and cohort logic (no pandas, no shared code). It also compares 47 counts with NLM's own search engine.

## 4. Coverage

- **612,892 records** downloaded in 613 pages (0 duplicates), equal to NLM's own `totalStudies` and to the server-side count; data timestamp 2026-11-20T10:00:05 unchanged from start to end of the pull.
- **467,733 interventional**, 143,090 observational, 1,077 expanded access, 992 withheld device records with no study type.
- 262,780 interventional trials marked COMPLETED; 195,425 of them have a primary completion date in 2008–2023 (headline cohort).
- Like-for-like cohort (actual PCD 18 Jan 2017 – 20 Nov 2024, not withdrawn): **139,674 trials**, of which **21,041** are "probably required" (main proxy).
- Due cohort (to 20 Nov 2025): 158,784 trials; 24,164 probably required.

## 5. Exclusion and treatment log (`data/exclusion_log.csv`)

| Item | Count | Treatment |
|---|---|---|
| Observational studies | 143,090 | Excluded throughout |
| Expanded-access records | 1,077 | Excluded |
| Withheld device records (no study type; details not public under FDAAA) | 992 | Excluded; cannot be assessed |
| Interventional, WITHDRAWN (never enrolled) | 14,026 | Excluded from due/like/ended cohorts; kept in "all interventional" counts |
| Completed interventional with no primary completion date (old records) | 10,408 | Fall out of every year-based cohort (they are in "all completed, any year": 26.3%) |
| Completed, PCD type missing / still ESTIMATED | 15 / 5 | Kept in headline; dropped in robustness (no change) |
| Month-only PCD ("2019-06") | 181,458 interventional | Last day of month; first-day variant in robustness |
| Results submitted before the recorded PCD | 927 | Counted as on time (PCD usually revised later) |
| Results submitted but not posted (`estimatedResultsFirstSubmitDate`) | 10,458 interventional (12,468 all) | Counted as submitted; "posted only" variant in robustness. **98.8% of those waiting > 1 year have been returned by NLM's review at least once** — they are stuck with the sponsor, not in NLM's queue |
| Results-waived flag | 0 | — |
| PCD marked ACTUAL required for due/like cohorts | — | Trials past their *estimated* PCD whose records were never updated are excluded from those cohorts; quantified in §6 H3/H5 and added back as a robustness variant |
| FDA flags missing (records not updated since Jan 2017) | 23,930 of the like cohort's non-required trials (20.2%) | Not counted as required in "main"; counted in "broad" |
| IND/IDE status | not public | Cannot be used; "noloc" variant catches non-US trials that may be under IND |
| Sponsor names | as registered | Not merged (e.g. "Janssen Research & Development, LLC" ≠ other Janssen entities) |

## 6. Results (every number; `data/headline_numbers.json`)

### H1 — The headline ("most never report")
- All 612,892 records: 13.2% have posted results. All interventional: 16.3%.
- Completed interventional, any year: **24.1% posted (63,247 of 262,780); 26.3% submitted**.
- **Completed interventional, PCD 2008–2023: 30.6% submitted (59,765 of 195,425; 95% CI 30.4–30.8); 28.4% posted.** So ~69% have no results on ClinicalTrials.gov. Completed + terminated: 32.3%.
- By PCD year (submitted, `h1_completed_by_pcd_year.csv`): 2008 40.5%, 2010 37.3%, 2012 34.3%, 2014 33.0%, 2016 31.4%, 2018 28.3%, 2020 27.6%, 2022 26.2%, 2023 24.9%, 2024 23.6%, 2025 19.2% (still accruing).
- **The fall is partly mix.** Share of completed trials with non-US sites only: 43.6% (2008) → 59.2% (2019) → 66.0% (2023). Completed trials **with a US site** have been flat: 55.6% (2008), 53.1% (2019), 57.2% (2022), 57.1% (2023). Non-US-only trials: 23.1% (2008) → 8.3% (2023). Holding 2008's location mix fixed, 2023's rate would be **32.3%** instead of 24.9%: **mix explains 48% of the 15.7-point fall**; the rest is non-US trials posting less here.
- Drug/device-type trials with a US site beyond phase 1 ("lite") that completed: 80–91% have results, every year 2008–2023.

### H2 — The denominator turn
Like-for-like cohort (actual PCD 18 Jan 2017 – 20 Nov 2024; every trial has had 24 months):

| | Probably required (main) | Everything else | Difference (95% CI) | Ratio |
|---|---|---|---|---|
| n | 21,041 (15.1% of cohort) | 118,633 | | |
| Submitted within 12 months | **41.9%** (41.3–42.6) | **7.5%** (7.4–7.7) | +34.4 pts (33.7–35.1) | 5.6× |
| Within 24 months | **69.6%** (69.0–70.2) | **13.5%** (13.4–13.7) | +56.1 (55.4–56.7) | 5.1× |
| By 20 Nov 2026 | **86.4%** (85.9–86.8) | **18.0%** (17.8–18.3) | +68.3 (67.8–68.8) | 4.8× |

- Why "everything else" is not in the proxy: product not FDA-regulated (flags = No) 72.2%; flags missing 20.2%; phase 1 only 6.7%; no US site and not exported 0.6%; device feasibility 0.3%.
- **Where the missing results are** (`h2_cohort_segments.csv`; share of the cohort → share of trials with no results at 24 months): probably required 15.1% → **5.9%**; not required with a US site 24.6% → 21.7%; **not required, non-US sites only 58.2% → 70.1%**; no location listed 2.1% → 2.4%. Non-US-only university/hospital trials alone are 45.1% of the cohort and **55.8%** of the no-results pile (3.6% of them report within 24 months).
- Whole due cohort, main proxy (PCD 18 Jan 2017 – 20 Nov 2025, n = 24,164): within 12 months 43.4%; by now 84.3% (posted 78.2%, waiting/returned 6.1%); certification or extension filed before the deadline 9.9%; within 12 months **or** certificate in time 52.9%; **no results and no certificate: 3,368 (13.9%)**.
- Proxy variants, within 24 months (required vs rest): main 69.6 vs 13.5; strict 71.2 vs 15.6; broad 69.2 vs 10.8; noloc 69.3 vs 13.3. Within 12 months: 41.9 / 42.4 / 41.0 / 41.9 for the required group.

### H3 — Timeliness
- Lite group (drug/device, US site, beyond phase 1), share within 12 months by PCD year: 2008 12.1%, 2010 13.6%, 2012 17.0%, 2014 23.1%, 2015 24.5%, 2016 31.4%, 2017 33.3%, 2018 35.9%, 2019 35.7%, 2020 39.2%, 2021 41.3%, 2022 43.4%, 2023 43.4%, 2024 52.3% (see selection note). Within 24 months: 22.6% (2008) → 59.2% (2016) → 72.4% (2023). Within 36 months: 32.8% (2008) → 68.2% (2016) → 81.5% (2022). **By now (Nov 2026): 79.5% (2008), 84–86% every year 2009–2016, 89–90% for 2017–2019, 85.5% (2022).** What changed over 15 years is mainly *speed*: eventual reporting moved by ~5 points, on-time reporting more than tripled.
- Pre vs post rule, lite: PCD 2014–16 **26.5%** within 12 months (n = 9,192) vs PCD 2018–20 **36.9%** (n = 9,976): **+10.4 pts (9.1–11.7)**. Within 24 months 55.6% → 65.3% (+9.7, 8.3–11.1). All other interventional trials: 6.7% → 5.6%.
- **A rise, with one step, not a transformation.** The 12-month share was already rising ~2–3 points a year (2011 14.3% → 2015 24.5%). The largest single-year step (+6.9 points, 24.5% → 31.4%) is for trials finishing in 2016 — the first whose 12-month deadline fell in 2017, when the rule took effect (compliance date 18 Apr 2017). After that the climb returns to ~2 points a year (2017 33.3% → 2022–23 43.4%). Consistent with a modest rule effect on top of a trend; the data cannot prove cause.
- Main proxy, PCD 2018–22 (n = 13,498): within 12 months 40.1%, 24 months 68.1%, 36 months 80.5%, by now 88.4%. Median delay among those reporting within 36 months: **366 days** — reporting clusters at the deadline (c4: ~10% by month 9, ~40% by month 12).
- **Selection in recent cohorts:** trials whose PCD has passed but whose record still says ESTIMATED are excluded from "actual PCD" cohorts. Among all interventional trials with a 2024 PCD, **33.5%** are still ESTIMATED (2018: 16.8%; 2008: 3.3%); in the main proxy 13.7% (2024) vs 4.8% (2018). Adding them back, the lite group's 2024 within-12-month figure falls from **52.3% to 46.9%** (2023: 43.4% → 40.3%). The apparent 2024 jump is partly this artefact; treat 2024–25 as provisional.
- 13-month slack (30 days for submission paperwork): 47.8%. Within 12 months or certificate filed in time: 51.3%.

### H4 — Who reports (main proxy, like cohort)

| Lead sponsor | n | Within 12 m | 12 m or certificate | Within 24 m |
|---|---|---|---|---|
| Industry | 10,456 | 43.0% (42.1–44.0) | 59.0% (58.1–60.0) | 66.2% (65.3–67.1) |
| Universities, hospitals & non-profits | 9,634 | 40.5% (39.6–41.5) | 43.3% (42.3–44.2) | 72.7% (71.8–73.6) |
| NIH | 533 | 54.0% (49.8–58.2) | 58.7% (54.5–62.8) | 87.8% (84.8–90.3) |
| Other US federal | 222 | 35.6% (29.6–42.1) | 41.9% (35.6–48.5) | 69.8% (63.5–75.5) |

- Certificates/extension requests filed in time: industry 16.6%, NIH 4.9%, universities 2.9%. Of all certified trials in the cohort, 90.9% have since submitted.
- **Same trial mix for everyone** (logistic model + standardisation; phase, product, PCD year, US site): within 12 months industry 42.0% (41.2–43.0) vs universities 41.6% (40.6–42.6): **difference +0.4 pts (−0.9 to +1.7) — a tie**. Within 24 months industry 64.9% vs universities 73.9%: **−9.0 (−10.1 to −7.6)**. Within 12 months or certificate: industry 57.0% vs universities 45.7%: **+11.3 (10.0 to 12.8)**. NIH vs industry: +9.4 at 12 months (5.7–13.8), +21.1 at 24 months (18.3–24.8); with certificates, industry–NIH +2.5 (−1.8 to +6.0), a tie.
- Mix: phase 3 is 29.0% of industry's probably-required trials vs 6.5% of universities'; phase N/A (mostly devices) 23.1% vs 32.3%.
- By phase (within 12 m): phase 3 49.1%, phase 2 44.2%, phase 1/2 45.5%, phase 4 42.7%, N/A 33.3%. Devices 33.4% vs drugs 45.4%.
- Location (noloc proxy): US site 43.3% within 12 m / 72.1% within 24 m; no US site, US-exported product 28.1% / 45.2%; no US site, not exported (possible IND) 39.7% / 59.3%.
- Status: completed 41.5% / 69.5%; terminated 45.1% / 72.4%; "unknown" 7.7% / 15.4% (n = 169).
- Enrolment: 1–20 participants 69.0% within 24 m; 101–300 69.4%; > 1,000 82.3%.
- Outside the proxy (within 24 m): NIH 58.1%, other US federal 57.0%, industry 21.7%, universities 10.8%, non-US governments 3.3%.
- **Comparison window of DeVito et al. 2020** (due Mar 2018 – Sep 2019; our proxy, n = 2,183): 35.9% within 12 months (their 40.9%, different method), 46.6% with certificates; **92.6% have now reported** (their snapshot: 63.8% "at any time" by Sept 2019). Industry 39.6%, universities 31.1%, NIH 43.4% within 12 months in that window — industry ahead then; the gap closed later.

### H5 — Status rot (ended cohort: interventional, PCD ≥ 2 years ago, n = 312,374; 26.0% submitted)

| Status | n | % of ended | % submitted | % of the no-results pile |
|---|---|---|---|---|
| Completed | 225,921 | 72.3 | 29.0 | 69.4 |
| Terminated | 26,946 | 8.6 | 43.8 | 6.5 |
| **Unknown status** | 55,507 | 17.8 | **4.5** | **22.9** |
| Still marked recruiting/active/suspended | 4,000 | 1.3 | 32.7 | 1.2 |

- "Unknown" is NLM's label for records past their completion date and not verified for 2 years; median **6.7 years** since the last update. Last known status: recruiting 55.8%, not yet recruiting 24.3%, active 16.3%.
- Unknown share among ended trials: universities/hospitals 21.9%, non-US governments 35.6%, industry 7.0%, NIH 1.4%. **Non-US-only trials 24.0% vs trials with a US site 4.5%.**
- Probably-required-type trials (FDA flag, US site) past their estimated PCD by 2+ years with the PCD never updated to actual: **1,954** (1,694 unknown status); 12.0% have results. Adding them to the like cohort lowers the required group's 24-month figure from 69.6% to **64.3%**.
- Counting unknown/stale trials in the headline denominator (PCD 2008–2023): 27.4% instead of 30.6%.

### H6 — Named sponsors and sponsor size
- **Sponsor size** (lead-sponsor names in the probably-required like cohort; `h6_by_sponsor_size.csv`):

| Sponsor runs | Sponsors | Trials | % of trials | 12 m or cert | 24 m | By now | Trials with no results and no certificate | % of that pile |
|---|---|---|---|---|---|---|---|---|
| 1–4 such trials | 4,344 | 6,501 | 30.9 | 30.0 | 48.7 | 68.2 | 1,945 | **73.1** |
| 5–19 | 454 | 3,870 | 18.4 | 42.2 | 61.0 | 85.4 | 520 | 19.5 |
| 20–99 | 118 | 5,085 | 24.2 | 59.5 | 81.3 | 96.1 | 175 | 6.6 |
| 100+ | 35 | 5,585 | 26.5 | 75.0 | 89.2 | 99.3 | 22 | **0.8** |

- 35 sponsors with ≥ 100 such trials (26.5% of the cohort): table in `h6_largest_sponsors_probably_required.csv` (n, within 12 m, within 12 m or certificate, within 24 m, by now, each with Wilson 95% intervals). Range within 24 months: 65.7% (Novo Nordisk A/S, n = 102; 94.1% within 12 m or certificate) to 99.4% (Merck Sharp & Dohme LLC, n = 164). Within 12 months or certificate: 33.1% (Massachusetts General Hospital, n = 148; 78.4% within 24 m, 94.6% by now) to 99.4% (AbbVie). Every one of the 35 has results for ≥ 94.1% of these trials by now.
- Robustness: sponsor rates under strict/broad proxies rank-correlate 0.95 / 0.97 with main; largest single change 7.4 points (main vs strict).
- **Fairness judgement:** the table is publishable as a scoped, factual reference (minimum n = 100, intervals, three outcome definitions, names as registered, proxy caveat) but **not as a league table of offenders**: the ordering depends on whether certificates count (industry) and on name fragmentation, and the overdue problem is overwhelmingly in the long tail (73% with sponsors of 1–4 trials), where naming individual sponsors on a proxy would be unfair.

### H7 — Other findings
- **Results stuck before posting:** 12,468 records (10,458 interventional) have submitted results that are not posted; median wait **1,100 days**; 8,730 waiting > 1 year, **98.8%** of which were returned by NLM's review at least once. 1,475 are in the main-proxy due cohort (6.1%). Counting them as "not submitted" lowers the required group's 24-month figure from 69.6% to 67.2%.
- NLM review time (first submission → posting), median by year of submission: 2010 70 days, 2014 44, 2017 120, 2019 68, 2020 48, 2022 107, 2023 103, 2024 91, 2025 59 (recent years include only already-posted results). No sustained trend.
- **FDA notices of non-compliance shown on the registry: 11 records** (8 industry, 3 other). Against 3,368 probably-required trials with no results and no certificate. Enforcement visible in the registry is close to nil.
- Terminated probably-required trials report at least as well as completed ones (72.4% vs 69.5% within 24 months).

## 7. Robustness (`data/robustness_grid.csv`)

| Claim | Variants tested | Range | Verdict |
|---|---|---|---|
| ~31% of completed interventional trials (PCD 2008–23) have results | posted only 28.4; any year 26.3; PCD actual only 30.6; study completion date 30.4; PCD 2010–20 31.2; 2017–23 27.0; + terminated 32.3; + unknown/stale 27.4; month-start dates 30.6 | 26.3–32.3% | **Robust: "about 7 in 10 have no results there"** |
| Probably required report ~5× as often | main/strict/broad/noloc; posted only; + stale | 24 m: 64.3–71.2% vs 10.8–15.6% | **Robust** |
| Under half on time | 12 m: 41.0–42.4 (proxies), 41.3 (posted only), 41.5 (completed only), 41.3 (PCD 2019–23), 41.7 (month-start); 47.8 with 30-day slack; 51.3 with certificates | 41–51% | **Robust for "about 4 in 10 by the deadline"; "under half" fragile once certificates count (51%)** |
| Industry = universities at 12 m | standardised and crude; DeVito window shows industry ahead (39.6 vs 31.1) | | **Moderate: holds for 2017–24 overall, not every sub-period** |
| NIH fastest | 12 m, 24 m, standardised | | **Robust at 12 and 24 m; tie with industry once certificates count** |
| Overdue pile is in the long tail | sponsor size from unmerged names | 73% / 0.8% | **Robust in direction; exact shares depend on name merging** |
| 2017 rule transformed on-time reporting | pre/post, year-on-year steps | +10 pts pre/post, of which one ~7-pt step at the 2017 deadline year; trend before and after | **"Transformed" dies; "a step on top of a slow trend" survives as description, not cause** |
| Headline fall is "worse reporting" | mix standardisation | mix = 48% of the fall | **Dies: half the fall is mix** |

## 8. Verification

1. **Second code path** (`05_verify.py`: raw JSON, own date parser, no pandas, no shared code): **113 quantities compared, 0 mismatches** (`data/verification_table.csv`). One earlier mismatch (a sponsor's 24-month rate, 82.0 vs 82.1) was a double-rounding artefact in the checker, fixed by comparing unrounded values.
2. **NLM's own search engine** (`04_server_counts.py`, 47 queries): record total, interventional, completed, completed with results, PCD 2008–2023 (n and with results), unknown status, withdrawn, FDAAA-violation flag, and completed / with results for every PCD year 2008–2025 — **all 45 identical to our download**. The one compound query (FDA flag + US location + actual PCD 18 Jan 2017 – 20 Nov 2024) differs by **+11 (0.04%)**, fully explained by month-only dates at the window edges: 12 trials with PCD "2017-01" (we place them on 31 Jan, inside; NLM's engine at 1 Jan, outside) and 1 with "2024-11" (the reverse).
3. **Lead check from the published derived file** (`data/interventional_trials.parquet`): mix-standardised 2023 rate 32.32% and non-US share 66.01% reproduced exactly.
4. **Earlier snapshot run** (first 199 pages) — 39/39 matches; the logic was then frozen before the full run.

## 9. Comparison with published methods (not used as data)
- Anderson et al., NEJM 2015 (DOI 10.1056/NEJMsa1409364): 13,327 "highly likely applicable" trials completed/terminated 2008–Aug 2012; 13.4% reported within 12 months; 38.3% by Sept 2013. Our lite group, PCD 2008–2012: 12.1–17.0% within 12 months. Consistent.
- DeVito, Bacon, Goldacre, Lancet 2020 (https://www.bennett.ox.ac.uk/papers/172/): 4,209 trials due Mar 2018 – Sep 2019; 40.9% within 1 year (95% CI 39.4–42.2); 63.8% at any time; median 424 days. Ours for the same window: 35.9% within 12 months; 92.6% by Nov 2026. Their ACT logic uses legacy fields via AACT; ours uses only today's registry fields.
- The "half of all trials never report" figure traces to the AllTrials campaign (2013), which summarises *journal publication* studies — a different measure from posting on ClinicalTrials.gov.

## 10. What the data cannot tell you
- **Publication anywhere else.** A trial with no results on ClinicalTrials.gov may be in a journal, the EU Clinical Trials Register/CTIS, ISRCTN, CTRI, a regulator's file or a press release. This is not "never published".
- **Legal status.** "Probably required" is our estimate from sponsor-entered fields. IND/IDE numbers are not public, FDA flags are self-reported and missing on older records, and certificates and good-cause extensions share one date field. Not a compliance finding about any trial or sponsor.
- **Accuracy of what sponsors type.** Status, dates, phase and sponsor class are self-reported; "unknown status" is the registry admitting it does not know.
- **Results quality.** Posting is counted, not whether the results are complete or correct.
- **Unregistered trials** are invisible.
- **Why** small sponsors and non-US trials post less — capacity, other registries, no obligation — is not in the data.
- **Recent cohorts** (2024–25) are provisional because unupdated records drop out of "actual completion" cohorts.

## 11. Charts (`charts/`, drafts)
c1 the obvious number (by year) · c2 the denominator turn · c3 on-time reporting by year · c4 how fast results arrive (cumulative, by cohort) · c5 who reports (crude and same-mix, three outcomes) · c6 where the missing results sit (status) · c7 NLM review time · c8 largest sponsors (scoped reference, not for social) · c9 where the missing results come from (segments) · c10 the mix moved · c11 small sponsors hold the overdue pile. Direct labels throughout; colour never the only encoding (blue/orange/grey with labels; no red/green).

## 12. Run log
Final run 22 Nov 2026: `01_fetch.py` (613 pages, 13:38–14:16 UTC, timestamp unchanged), `02_parse.py`, `03_analysis.py`, `04_server_counts.py` (14:18 UTC), `05_verify.py` (113/113 match; server 45/47 identical, 2 explained), `06_charts.py`. `data/` is 8 MB (includes `interventional_trials.parquet`, 467,733 rows, 26 columns, for independent re-verification; no raw pages).
