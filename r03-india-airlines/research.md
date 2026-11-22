# R03 — Which Indian airline is actually the most reliable? Research notes

All figures trace to data published by the body that generated it: DGCA (airline-reported monthly performance and DGCA-approved schedules) and AAI (airport movements). No aggregators, no trade press. Analysis re-runs end to end with `sh scripts/run_all.sh <empty_raw_dir>`.

## 1. Sources (pulled 21 Nov 2026)

| # | Body | What | Where |
|---|---|---|---|
| S1 | DGCA | *Performance of domestic airlines* monthly traffic report (PDF), Jan 2018 – Sep 2026, 104 files | Listing page: https://www.dgca.gov.in/digigov-portal/?page=4264/4206/sericename (Data & Reports → Aviation Data & Statistics → Air Transport → Domestic → Air Traffic). Files served from DGCA's public document store: `https://public-prd-dgca.s3.ap-south-1.amazonaws.com/InventoryList/dataReports/aviationDataStatistics/airTransport/domestic/airTraffic/<file>`; exact file names per month in `scripts/manifest.json`; URLs + SHA-256 prefixes in `<raw>/pdf/fetch_log.csv` |
| S2 | DGCA | Approved Winter Schedule 2026 (effective 25 Oct 2026 – 27 Mar 2027), domestic, 9 operators, published 22 Oct 2026 | Listing: https://www.dgca.gov.in/digigov-portal/?page=4201/4200/servicename ; files `https://public-prd-dgca.s3.ap-south-1.amazonaws.com/InventoryList/airOperation/certification/scheduled/domestic/<file>` (names in `scripts/01b_fetch_schedules.py`) |
| S3 | AAI | Traffic News, Annexure-II B "Domestic Aircraft Movement" by airport, Jan–Sep 2026 (each with the same month of 2025) | https://www.aai.aero/en/business-opportunities/aai-traffic-news ; files `https://www.aai.aero/sites/default/files/traffic-news/<Mon>2k26Annex2*.pdf` |
| — | DGCA | Per-airline "Monthly statistics" (ASK/RPK etc., PDF + Excel), 2017–2026 | https://www.dgca.gov.in/digigov-portal/?page=259/4184/servicename — seen, **not used** (no reliability measures) |

Access notes: the DGCA portal renders its listings with JavaScript; listings were read in a normal browser view and file paths copied (no login, no CAPTCHA, no form submission). A direct scripted POST to the portal's internal `scan?` endpoint was not used. AAI's page includes a Drupal CAPTCHA *module script* but serves the files without any challenge.

### What each DGCA monthly report contains (and what we used)
Narrative + charts for the month: passengers YTD; load factor by airline; **cancellation rate by airline** (bar chart, %); cancellation reasons (pie, all airlines); **market-share table** (passengers in lakh and % share, every month YTD); **complaints per 10,000 passengers by airline** (bar chart); complaint reasons (pie); route-dispersal compliance; **on-time performance (OTP) by airline** at the measured airports (bar chart); **OTP by airport for each airline** (bar charts); delay reasons (pie); from Jan 2026 **share of flights delayed >2 h by airline** and an all-airline OTP-by-airport chart; highest fare-bucket charts (not used); CAR Section 3 Series M Part IV table — denied boarding, cancellations, delays >2 h: passengers affected and amounts spent (layout too irregular to parse reliably; read by hand for Sep 2026 only: 471 denied boarding, 78,207 passengers hit by cancellations, 108,783 by >2 h delays); Table 1 load factor; Table 2 complaints redressal (count, per 10k, closed, open).

Definitions stated in the reports: OTP = departures; "a delay of more than 15 minutes from the scheduled departure time is considered a delayed flight". Footer of every report: "The Traffic report is being prepared based on information received from scheduled domestic airlines."

**OTP scope, verified in all 104 reports' text:**
- Jan 2018 – Dec 2024: "four metro airports viz. Bangalore, Delhi, Hyderabad and Mumbai".
- Jan 2025 – Dec 2025: six (+ Chennai, Kolkata).
- Jan 2026 – Sep 2026: "ten major airports" (+ Ahmedabad, Cochin, Guwahati, Lucknow).

## 2. Method

**Pipeline** (`scripts/`): `01_fetch.py` (manifest → PDFs), `01b_fetch_schedules.py`, `01c_fetch_aai.py`, `02_parse_reports.py` (pdfplumber text + word geometry), `03_parse_schedules.py` (table extraction), `03b_parse_aai.py`, `04_tidy.py` (airline name normalisation, revisions, panel), `05_analysis.py` (all tests → `data/headline_numbers.json`), `06_charts.py`, `07_verify.py` (second code path → `data/verify_numbers.json`, `data/validation_*.csv`). All run as `python3 -I` with data paths as arguments; nothing executes from the raw folder.

**Extraction.** Bar-chart values are read from the PDF text layer (each bar is labelled "Airline value"); market-share and load-factor tables are read by word x-positions (numeric column clusters; wrapped header words assigned to the nearest column); pie charts by matching each percentage to the nearest category label (one-to-one assignment). Market-share cells are taken from the **latest** report of the same year (December report, or September 2026), so later revisions win; the month's own report is kept for comparison.

**Panel.** `data/airline_month_panel.csv` (airline × month): otp_pct, cancel_pct, complaints_per10k, delay2h_pct, pax_lakh, share_pct, load_factor_pct, complaint counts, OTP scope label and Air India definition. Long form: `airline_month_metric_long.csv`. Airport-level OTP: `airport_airline_otp.csv`. Reasons: `reason_shares.csv`. Headline narrative numbers: `overall_monthly.csv`.

**"Main" airlines** for rankings: ≥1% of domestic passengers in that month and an OTP figure (8 airlines ever qualify: IndiGo, Air India, Akasa, SpiceJet, Vistara, AirAsia India/AIX Connect, Go First, Alliance Air). Jet Airways (to Apr 2019) also qualifies in 2018–19.

**Intervals.** Monthly OTP is a rate over thousands of flights, so the relevant noise is month-to-month variation, not flight sampling. We use a **moving-block bootstrap over months** (blocks of 3 months, 4,000 resamples, seed 20261121): resample months, recompute each airline's mean, record the winner and the top-two difference (computed only on months where both airlines are present). Airlines enter a window's comparison if present in ≥90% of its months.

**Composite.** Window means of OTP (higher better), cancellation % and complaints per 10k (lower better), combined two ways: (a) sum of ranks, (b) min–max scaled scores; weights swept over the simplex in 5% steps (231 weightings). Reported: share of weightings each airline wins. Variants: all main airlines vs top three only; with and without December 2025.

**Scope / network mix.** (i) Share of each airline's scheduled weekly departures (reference week Mon 9 – Sun 15 Nov 2026, frequency days × effective dates) from the 4/6/10 measured airports (S2); Air India + Air India Express combined to match DGCA's "Air India Group". (ii) AAI domestic aircraft movements at those airports as a share of all AAI-reported domestic movements (S3). (iii) Airport effect: within each month, airport OTP minus the airline's average across its airports; a two-way (airline + airport) sum-of-squares split per month on the original four airports. (iv) Equal-weight OTP: each airline's simple average over the four original airports, compared with the published figure. (v) 2026 rebuild: published OTP ≈ schedule-weighted average of the airline's airport OTPs; then the same airport OTPs re-weighted with another airline's airport mix.

## 3. Coverage

- **104 monthly reports**, Jan 2018 – Sep 2026. April 2020 was not published (no scheduled flights after the 25 Mar 2020 lockdown). October 2026 not yet published on 21 Nov 2026.
- 21 airline names normalised to canonical airlines; 1,127 airline-months; 641 airline-months with OTP, 1,079 with cancellation rate, 1,055 with complaints per 10k.
- 3,015 airline-airport-month OTP values (1 missing value: Go First, HYD, Nov 2022 — label without a number in the PDF).
- Schedules: 13,642 schedule rows (6,970 departure rows, 6,672 arrival rows; weekly departures 23,034 vs arrivals ≈ the same, a consistency check). AAI: 9 monthly annexes; airport rows sum **exactly** to the printed grand total in all 9.

## 4. Extraction validation

1. **Independent re-extraction (second code path).** Every bar value in every report (OTP, cancellations, complaints: 312 report×metric blocks) re-extracted with pdfminer's own layout engine and different layout parameters. Result: see §4a (filled from `verify_numbers.json`).
2. **Spot-check of 10 random months** (seed 42: 2018-04, 2019-02, 2019-03, 2019-06, 2020-07, 2020-10, 2021-02, 2024-12, 2025-05, 2026-01): every parsed bar value and every market-table value must appear verbatim in that report's text. Results in §4a; detail in `data/validation_spotcheck_10_months.csv`.
3. **Market shares sum to ~100%:** 103 of 104 months between 99.0 and 101.0 (range 99.8–100.2 apart from one); Nov 2024 sums to 97.0 (Vistara's partial month, see exclusion log).
4. **Two tables, one fact:** passengers implied by the complaints table (complaints ÷ complaints-per-10k) vs passengers in the market table, 258 airline-months with ≥50 complaints and rate ≥0.5: median absolute difference 1.0%, 91% within 10% (residual is the one-decimal rounding of the rate).
5. **Revisions:** 2,167 market-table cells appear both in their own month's report and in the year's latest report; 11 differ, none by more than 0.5.
6. **Pie sums:** complaint-reason shares sum to 97–103% in every parsed month; delay reasons 99–101%; cancellation reasons <97% in 2020-11 (94.0), 2021-04 (89.1), 2022-02 (93.4), 2022-03 (82.7) — those four months' cancellation-reason shares are unreliable (used only in the seasonality averages).
7. **Rebuild check:** for IndiGo, Air India Group and Akasa in 2026, the schedule-weighted average of their own airport OTPs reproduces DGCA's published airline OTP within **0.29 points** on average — confirming the published figure is a departure-weighted average over the listed airports.
8. **Headline numbers recomputed by a second path** (`07_verify.py`, csv module only, no pandas; schedule coverage recomputed from word x-positions instead of table extraction) — see §4a.

### 4a. Second-path results (`data/verify_numbers.json`, final run 21 Nov 2026 after a clean re-fetch with `run_all.sh`, exit 0)
- **pdfminer re-extraction:** 312 blocks; **every value we parsed was found by pdfminer** (0 parsed values missing). 8 blocks contain pdfminer numbers we did not parse: 4 are axis ticks on a 50-step scale (2018-03, 2019-12, 2024-01, 2024-04 complaints), 1 is the Air Deccan/Pawan Hans footnote (2018-07: 172.4, 833.33), 3 are the known-partial March 2020 report. No unexplained miss remains. (Earlier runs of this check caught real parser misses — "Jet Airways+JetLite" in 2018–19, starred names such as "Vistara*" and "Go First*", a value printed above its label in Apr 2026 — all fixed before the final run.)
- **Spot-check, 10 random months:** 265 of 265 bar values and 220 of 220 market-table values found verbatim in the report text.
- **Headlines recomputed (csv module only):** leader counts IndiGo 53 / Go First 17 / AirAsia 13 / Akasa 12 / Vistara 5 / Air India 2 / SpiceJet 2; 35 leader changes; 2026 means OTP IndiGo 86.02, Akasa 80.79, Air India 79.50 (gap 5.23); cancellations Akasa 0.13, IndiGo 0.41, Air India 0.74; complaints Akasa 2.52, IndiGo 2.63; Dec 2025 IndiGo 62.7 / 9.65 / 31.7 / 59.6; IndiGo median cancellation Jan 2022–Nov 2025 0.62 → Dec 2025 = **15.6×**; complaints 2024 9,437, 2025 41,518, Dec 2025 29,212, Jan–Sep 2026 38,237; IndiGo share 39.7 → 65.4 (peak 67.4, Jul 2026). All identical to `headline_numbers.json`.
- **"Best on all three" — a discrepancy found and resolved:** the first second-path run gave 3 months, the main path 0. Cause: ties (complaint rates are printed to one decimal; cancellation rates can tie at 0.00) broken by row order. Both paths now report tie-aware counts: **outright best on all three: 0 of 102 months; best or joint-best on all three: 4 of 102** (Apr 2021 and Jan 2022 Go First, Apr 2022 AirAsia India, Jun 2026 IndiGo — each a tie on complaints or cancellations).
- **Schedule coverage from word x-positions** (independent of table extraction): identical to the table path for every airline (e.g. IndiGo 14,057 weekly departures, 37.6% from 4 airports, 58.0% from 10; Air India Group 6,080, 56.0% / 69.0%).

## 5. Exclusion log

| Item | What happened | Treatment |
|---|---|---|
| Apr 2020 | No report published (lockdown) | Missing month |
| Oct 2026 | Not yet published (21 Nov 2026) | Series ends Sep 2026 |
| Mar 2020 report | Text layer encodes spaces as `$`; bar values partly unreadable (OTP 3 of 6, cancellations 5 of 10, complaints 0) | Partial; market shares for Mar 2020 come from the Dec 2020 report; Mar 2020 excluded from complaint and pie analyses |
| Mar 2020 – Dec 2021 | Covid schedules | Kept in counts; excluded from seasonality, within-airline and size tests |
| Nov 2024 Vistara | Data only to 11 Nov (merged into Air India 12 Nov). OTP published (79.3%, highest that month) but no share in the year's latest market table → shares sum 97.0 | Vistara Nov 2024 not "main" (no share); **sensitivity: if included, Vistara leads Nov 2024 and IndiGo's leader count is 52 not 53** |
| 2026-04 complaints table | Table 2 layout broken in PDF (columns misaligned) | Per-10k from the bar chart used; Table 2 counts for Apr 2026 dropped |
| Air Deccan, Pawan Hans complaint rates in some 2018 reports | Printed as a footnote ("Air Deccan-172.4"), not as bars | Not parsed (tiny airlines, never "main") |
| Axis-label artefact | In Feb/Mar 2021 a chart heading was read as an airline with value 7.0 | Dropped by name normalisation (unmapped) |
| Airport OTP, Go First HYD Nov 2022 | Label without value | Missing |
| CAR Sec 3 Series M Pt IV (denied boarding / compensation) | Irregular multi-line table | Not systematically parsed; Sep 2026 read by hand only |
| Highest fare bucket charts | Not reliability | Not used |
| Definition change: OTP airports | 4 → 6 (Jan 2025) → 10 (Jan 2026) | Analyses split by era; "scope" labelled in the panel |
| Definition change: Air India | Market table combines Alliance Air with Air India until Sep 2021; from Oct 2024 "Air India" includes Air India Express (and AIX Connect from Oct 2024, Vistara from 12 Nov 2024) — per report footnotes | Labelled in `air_india_definition`; Air India's series is not one company over time |
| Definition change: Jet Airways | OTP charts report "Jet Airways+JetLite" | Mapped to Jet Airways |
| Entries/exits | Akasa Air from Aug 2022; Go First stopped 3 May 2023; Jet Airways stopped Apr 2019; AirAsia India/AIX Connect merged Oct 2024; Vistara merged Nov 2024; Flybig suspended Oct 2025; TruJet, Zoom Air, Air Odisha, Air Deccan, Air Heritage, Pawan Hans intermittent | Windows only compare airlines present ≥90% of months |
| Schedules | Only the current (Winter 2026) schedule is published; past schedules not available on the portal | Coverage shares are a present-day proxy for 2018–2024 |
| AAI | Traffic News page lists 2026 months only; movements include non-scheduled traffic | Used as all-airline airport share only |
| Complaints source | Complaints "received by the scheduled domestic airlines"; DGCA AirSewa grievance data not in this series | Not used |

## 6. Results (all numbers)

### T1 — Scope: what the on-time number covers
- Measured airports' share of AAI domestic aircraft movements (mean of months): **4 airports 34.9% (Jan–Sep 2026), 35.1% (Jan–Sep 2025); 6 airports 44.1% / 45.3%; 10 airports 52.5% / 54.0%.**
- Share of scheduled weekly departures (Winter 2026, week of 9 Nov 2026; 23,034 departures):

| Airline | weekly deps | from 4 airports | from 6 | from 10 |
|---|---|---|---|---|
| IndiGo | 14,057 | 37.6% | 49.4% | 58.0% |
| Air India Group (AI + AI Express) | 6,080 | 56.0% | 61.8% | 69.0% |
| Akasa Air | 1,395 | 49.2% | 57.6% | 68.2% |
| SpiceJet | 269 | 38.7% | 49.1% | 51.7% |
| Alliance Air | 406 | 26.1% | 32.3% | 45.1% |
| Star Air | 363 | 19.6% | 21.2% | 29.2% |
| Fly91 | 380 | 23.2% | 23.2% | 26.3% |
| IndiaOne Air | 84 | 0% | 0% | 0% |
| All | 23,034 | 42.3% | 51.8% | 60.0% |

- Airport effect (points vs the airline's own average, all months): Chennai +7.7, Kochi +5.1, Hyderabad +3.2, Bengaluru +3.1, Delhi 0.0, Kolkata −0.8, Ahmedabad −3.7, Lucknow −4.4, Mumbai −6.8, Guwahati −7.5.
- 2026 all-airline OTP by airport (Jan–Sep mean): Chennai 93.1, Hyderabad 87.8, Bengaluru 87.7, Kolkata 86.0, Ahmedabad 82.7, Kochi 82.2, Lucknow 81.1, Delhi 78.2, Guwahati 75.9, Mumbai 73.9.
- Variance split (original four airports, main airlines, median of 104 months): airline 54.4%, airport 21.7%, remainder 18.5%.
- Equal-weight four-airport OTP vs published: mean absolute shift 1.64 points; changes the month's leader in **22 of 104 months** (2018–19: 1 of 24; 2022–24: 6 of 36; 2025–26: 9 of 21).
- 2026 mix counterfactual (Jan–Sep means): published IndiGo 86.02 / Akasa 80.79 / Air India Group 79.50; rebuilt from own mix 86.07 / 81.32 / 79.53. On IndiGo's airport mix: Akasa 82.08, Air India 81.13. On Air India's mix: IndiGo 83.53, Akasa 79.44. On Akasa's mix: IndiGo 84.75, Air India 79.81. → IndiGo's lead over Air India: 6.5 points published, **4.9** on a common (IndiGo) mix, **4.0** on Air India's mix.

### T2 — Rank stability
- Leader (highest OTP among main airlines) by month, 104 months: IndiGo 53, Go First 17, AirAsia India 13, Akasa 12, Vistara 5, Air India 2, SpiceJet 2. **35 changes of leader** in 103 transitions (34%). Median lead over second place 2.0 points; lead under 1 point in 30% of months.
- By era: 2018–19 Go First 15 / IndiGo 7 / SpiceJet 2 (5 changes); 2022–24 IndiGo 13 / Akasa 11 / AirAsia 8 / Vistara 2 / Go First 1 / Air India 1 (15 changes); 2025 IndiGo 10 / Akasa 1 / Air India 1; 2026 IndiGo 9 of 9.
- Typical month-to-month move in an airline's OTP (median absolute change, 2022–26): Vistara 2.9, IndiGo 3.9, AirAsia 4.0, Air India 4.6, Akasa 5.3, Alliance 5.7, SpiceJet 6.4, Go First 6.6 points.
- Block bootstrap, OTP:

| Window | Means | P(first) | Top-two gap (95% interval) |
|---|---|---|---|
| 2018–19 | Go First 81.32, IndiGo 80.36, Vistara 79.43, SpiceJet 76.31, Air India 64.50 | Go First 0.77, IndiGo 0.23 | 0.95 (−2.75 to 5.73) |
| 2022–24 | IndiGo 81.69, Vistara 81.23, AirAsia 79.95, Air India 74.96, SpiceJet 62.47 | IndiGo 0.66, Vistara 0.19, AirAsia 0.15 | 0.92 (−1.51 to 3.41) |
| 2025 | IndiGo 81.61, Akasa 78.36, Air India 76.42, SpiceJet 58.11 | IndiGo 1.00 | 3.25 (2.11 to 4.26) |
| Jan–Sep 2026 | IndiGo 86.02, Akasa 80.79, Air India 79.50 | IndiGo 1.00 | 5.23 (2.34 to 8.06) |
| Oct 2025–Sep 2026 | IndiGo 82.50, Akasa 77.84, Air India 77.52, SpiceJet 40.37 | IndiGo 0.999 | 4.66 (2.57 to 7.74) |
| same, excl. Dec 2025 (top 3) | IndiGo 84.30, Akasa 79.86, Air India 78.54 | IndiGo 1.00 | 4.44 (2.63 to 7.56) |
| 2018–Sep 2026 (airlines present ≥90%) | IndiGo 84.17, Air India 74.45, SpiceJet 68.43 | IndiGo 1.00 | 9.71 (7.76 to 11.95) |

(2022–24 excludes Akasa, present in <90% of months.)

### T3 — Do the measures agree?
- Within-month rank agreement across main airlines (median of 102 months): OTP vs cancellations −0.46 (better OTP goes with fewer cancellations), OTP vs complaints −0.67, cancellations vs complaints +0.49.
- **Months where one airline is outright best on all three: 0 of 102; best or joint-best: 4 of 102** (all via ties). Best OTP = fewest cancellations: 23% of months. Equal-weight rank composite picks the same airline as OTP in 53% of months; post-2022 composite leaders: Vistara 17, IndiGo 17, Akasa 16, AirAsia 5, Go First 2 (OTP leaders: IndiGo 32, Akasa 12, AirAsia 8, Vistara 2, Air India 2, Go First 1).
- Cancellations (bootstrap): 2025 Akasa 0.28%, Air India 0.97%, IndiGo 1.54% (Akasa first 99.8%; Akasa–Air India −0.70, −1.19 to −0.22). Jan–Sep 2026 Akasa 0.13%, IndiGo 0.41%, Air India 0.74% (Akasa first 100%; Akasa–IndiGo −0.28, −0.32 to −0.16). Last 12 months Akasa 0.23, Air India 0.94, IndiGo 1.28, SpiceJet 4.67.
- Complaints per 10k: 2025 Akasa 0.76, Air India 1.22, IndiGo 2.82 (mean inflated by Dec 2025; bootstrap P(first) IndiGo 0.65, Akasa 0.35). Jan–Sep 2026 Akasa 2.52, IndiGo 2.63, Air India 3.23 (Akasa–IndiGo −0.11, −1.87 to 1.50: tie). Last 12 months Akasa 2.23, Air India 2.82, IndiGo 4.65; excluding Dec 2025: IndiGo 2.19, Akasa 2.23, Air India 2.84 (tie, −1.32 to 1.80).
- "Punctual by cancelling": within-airline monthly deviations (2018–2026 excl. Covid, 484 airline-months) — higher-than-usual cancellation goes with *lower*-than-usual OTP (rank correlation −0.49). No monthly-level evidence of a trade-off.
- "Flights that operated and left on time, per 100 scheduled" ((100 − cancel%) × OTP%), last 12 months: IndiGo 81.6, Akasa 77.7, Air India 76.8, SpiceJet 39.0 — ranking unchanged vs OTP (cancellation rates are ~1%).
- Composite weight sweep (share of 231 weightings won; rank-based / scaled):
  - Oct 2025–Sep 2026, top three: **Akasa 88% / 76%**, IndiGo 12% / 24%, Air India 0 / 0.
  - Same window **without December 2025**: **IndiGo 71% / 58%**, Akasa 29% / 42%.
  - Jan–Sep 2026: Akasa 76% / 47%, IndiGo 24% / 53%.
  - 2025: Akasa 88% / 84%, IndiGo 12% / 16%.
  - Post-2022 (top three): Akasa 82% / 72%, IndiGo 18% / 28%.
  - 2018–19 (all main): Vistara 71% / 78%, Go First 29% / 22%.
  - 2022–24 (all main): Vistara 62% / 56%, AirAsia 19% / 33%, IndiGo 19% / 10%.
  - Including SpiceJet in min-max scaling compresses the others' OTP differences — hence the rank-based version is preferred.

### T4 — Size
- IndiGo share: 39.7% (Jan 2018) → 47.1% (2019 mean) → 64.9% (2026 mean); peak 67.4% (Jul 2026); 65.4% Sep 2026. HHI (sum of squared shares) 2,245 → 5,028.
- Within IndiGo (83 non-Covid months): share vs OTP rank correlation 0.11, share vs cancellations −0.04 — no relationship.
- Across main airlines (window means): post-2022 share vs OTP +0.62, vs cancellations −0.12, vs complaints −0.36 (8 airlines); 2018–19 −0.29 / +0.75 / +0.46 (7 airlines). Direction flips; too few airlines to conclude.

### T5 — Events and seasonality
- **December 2025:** IndiGo OTP 62.7%, cancellations **9.65%**, complaints 31.7 per 10k, passengers 85.23 lakh (Nov 96.93), share 59.6% (Nov 63.6%). IndiGo's median month Jan 2022–Nov 2025: 0.62% cancelled (×15.6); previous high 5.00% (Jan 2024). All airlines: 6.92% cancelled; 29,212 complaints; 20.41 per 10k. Air India Group 66.3% OTP / 3.28% cancelled; Akasa 55.6% / 0.93%; SpiceJet 46.9% / 1.89%. Cancellation reasons: operational 63.9%, weather 31.6%, technical 2.3%, misc 2.2%. Complaint reasons: flight problem 60.2%, baggage 28.1%, refund 7.5%.
- **Go First:** share 8.4% (Jan 2023) → 6.4% (Apr) → 0.4% (May 2023); OTP 41.7–54.2% in its last four months.
- **SpiceJet:** OTP 54.8% (Jan 2025) → 16.6% (Sep 2026); Sep 2026 cancellations 20.29%, >2 h delays 39.36%, complaints 14.3/10k, share 0.6%. Mean >2 h delay share Jan–Sep 2026: SpiceJet 20.5%, Fly91 4.4%, Alliance 2.4%, Star 1.5%, Akasa 1.5%, Air India 1.35%, IndiGo 0.81%.
- **Seasonality** (passenger-weighted OTP of main airlines, 2018–2026 excl. Mar 2020–Dec 2021): Dec–Jan **70.7%** vs other months **80.3%**; November 72.2%. Weather's share of recorded causes: cancellations 57.4% (Dec–Jan) vs 24.4%; delays 5.9% vs 2.6%; reactionary delays 64.2% vs 66.4%.
- Ten worst months for weighted OTP: Jan 2024 58.6, Jul 2024 61.0, Nov 2019 61.9, Dec 2025 62.7, Dec 2023 64.4, Dec 2019 65.0, Jan 2019 65.2, Aug 2024 65.7, Sep 2024 68.0, Nov 2025 68.4. Worst overall cancellation months: Dec 2025 6.92%, Jan 2024 3.67%, May 2025 2.51%, Dec 2019 2.34%.

### T6 — Complaints
- Annual complaints / passengers: 2018 8,409 (0.61 per 10k), 2019 9,162 (0.64), 2020 4,961 (0.79), 2021 4,983 (0.59), 2022 5,901 (0.48), 2023 5,055 (0.33), 2024 9,437 (0.59), **2025 41,518 (2.49; Dec alone 29,212)**, **2026 Jan–Sep 38,237 (3.13)**.
- Median monthly rate (excl. Dec 2025): 2018 0.60, 2019 0.72, 2020 0.83, 2021 0.59, 2022 0.49, 2023 0.30, 2024 0.57, 2025 0.78, **2026 2.09**.
- By airline (median monthly per 10k): IndiGo 0.5 (2019), 0.1 (2023), 0.2 (2024), 0.2 (2025), 1.0 (2026); Air India 1.7, 0.65, 1.15, 1.15, 3.1; Akasa –, 0.4, 0.4, 0.6, 2.6. Rise is across airlines.
- Reasons (complaint-weighted, % of year): 2019 flight problem 49.9, customer service 20.2, baggage 20.0, refund 4.1; 2020 refund 49.5; 2021 refund 42.3; 2024 flight problem 39.0, baggage 19.8, refund 13.9; 2025 flight problem 54.9, baggage 25.1; **2026 baggage 43.1**, flight problem 22.0, refund 16.0, others 11.4.

## 7. Robustness summary

| Claim | Alternate windows | Airline set | Metric choice | Verdict |
|---|---|---|---|---|
| No airline outright best on all three in any month | all months | main airlines (≥1% share) only — not tested with smaller airlines | three published metrics | **Robust** (0 of 102; 4 of 102 if ties count — say "outright") |
| IndiGo most punctual 2025–26 | 2025, 2026, last 12, excl. Dec 2025 | top 3 / all main | equal-weight airports, common mix | **Robust** (lead 3.3–5.2; ~4 after mix) |
| IndiGo most punctual across all eras | 2018–19, 2022–24 | ≥90% presence | — | **Fragile / dies** (coin toss vs Go First, Vistara) |
| Akasa fewest cancellations | 2025, 2026, last 12 | top 3 / all main | — | **Robust** |
| Composite winner | last 12 vs excl. Dec 2025; 2025; 2026 | top 3 vs all main | rank vs scaled | **Fragile** (flips on one month; reported as fragile) |
| Complaints rising | yearly, monthly medians, excl. Dec 2025 | all airlines, by airline | — | **Robust in the data; cause unknown** |
| Scope (≈35–42% at 4 airports) | AAI 2025, 2026; schedule | all airlines and per airline | movements vs departures | **Robust for today; proxy for the past** |

## 8. What the data cannot tell you
Airline-reported, unaudited (as published); departures only, 15-minute threshold, listed airports only; no flight counts behind any rate; airport list changed twice; Air India's composition changed; complaints are those received by airlines and their 2026 jump is unexplained; delay causes are airline-assigned and "reactionary" hides the original cause; nothing route-, time- or passenger-level; the December 2025 crew-duty rule is not named in the reports — only the scale and the "operational" label are.
