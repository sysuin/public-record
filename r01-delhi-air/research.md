# R01 — "Is Delhi NCR's air actually getting worse?" — research file

**Compiled 21 November 2026** (peak smog season). All downloads pulled 21 Nov 2026.
**Scope, stated everywhere a number appears:** the Central Pollution Control Board's daily National
AQI bulletin, 4 PM edition (average of the previous 24 hours), for Delhi, Gurugram, Noida, Ghaziabad,
Faridabad and Greater Noida, May 2015 to 21 Nov 2026. The bulletin publishes one **city AQI** per day
(the average of the AQI at each reporting station), the number of stations behind it, and the
prominent pollutant. It does **not** publish PM2.5 concentrations. Every claim below is a claim about
that published city AQI, not about "the air" in general — and the episode turns on exactly that gap.

Everything here is reproduced by `scripts/run_all.sh`. Every headline number is computed twice by
code paths that share nothing (§8).

---

## 1. Sources — and the sourcing bar

| # | Dataset | Publisher (= generator?) | Exact URL | Used for | Status |
|---|---|---|---|---|---|
| S1 | Daily National AQI bulletin, PDF, one per day | **CPCB** (generates the AQI from its own and state boards' CAAQMS stations) | `https://www.cpcb.gov.in/upload/Downloads/AQI_Bulletin_YYYYMMDD.pdf` (linked from `https://cpcb.nic.in/AQI_Bulletin.php` and from the CPCB CCR portal code) | Everything about air quality | **4,218 PDFs** downloaded for 1 Apr 2015–21 Nov 2026 (4,253 days); 35 days return 404 (31 in 2015; 2016-06-06; 2017-06-18; 2017-10-14; 2025-01-01) |
| S2 | CREAMS paddy-residue burning bulletin, 20 Nov of each year | **ICAR-IARI** CREAMS Lab (generates the counts from satellite data using its own protocol) | list page `https://creams.iari.res.in/?page_id=1123`; files e.g. `https://creams.iari.res.in/Creams_website_bulletin/Fire_bulletin_2026/Fire_bulletin_2026r/67.RiceResidueFireBulletin_20Nov_2026_ICAR.pdf` | Cumulative farm-fire events to 20 Nov, by state, 2018, 2020, 2021, 2023–2026 | 7 bulletins. No 20-Nov rice bulletin listed for 2019 or 2022 |
| S3 | FIRMS yearly country archive, MODIS Collection 6.1 | **NASA** (FIRMS/LANCE processes the MODIS detections) | `https://firms.modaps.eosdis.nasa.gov/data/country/modis/{YEAR}/modis_{YEAR}_India.csv` | Daily fire detections 2015–2025 for the weather/fire model; cross-check on S2 | 11 files. 2026 not yet published as a yearly file (404) |
| S4 | POWER daily point API, 28.61 N 77.21 E | **NASA** (POWER serves NASA GMAO's MERRA-2 reanalysis; GEOS-IT for the latest months) | `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=WS10M,WS2M,WD10M,T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,PS,QV2M&community=RE&longitude=77.21&latitude=28.61&start=20150101&end=20261121&format=JSON` | Weather confounders (wind, rain, temperature, humidity) | Daily to 18 Nov 2026. **Source switches from MERRA-2 to GEOS-IT on 1 Oct 2026** (checked month by month against the API's own `sources` field) |
| S5 | Diwali (Lakshmi Puja) dates, Delhi | public calendar fact | — | Diwali night indicator | 2015-11-11, 2016-10-30, 2017-10-19, 2018-11-07, 2019-10-27, 2020-11-14, 2021-11-04, 2022-10-24, 2023-11-12, 2024-10-31, 2025-10-20, 2026-11-08 |

**Did the source clear the bar?** The air-quality series (S1) does: CPCB computes and publishes the AQI
and a viewer can download any day's PDF. S2 and S3 clear it for fire counts. Two deviations from the
brief must be stated:

- **Weather is not from the IMD.** IMD's free gridded data (imdpune.gov.in) is served only through a
  form (POST) and stops at 2024; IMD's Data Supply Portal needs registration. The brief rules out forms
  and accounts, so weather comes from NASA's MERRA-2 reanalysis via NASA POWER. That is primary for
  what it is (a NASA model reconstruction of the weather), but it is **a model, not a measurement at
  Safdarjung**, and its 2026 values come from a different model (GEOS-IT).
- **S5 is not a downloaded dataset.** Diwali dates are single-valued public calendar facts. Structural
  check: the bulletin for the day after Diwali is higher than the previous week's average in 10 of 12
  years (mean +66 AQI points); the two exceptions (2015, 2023 — 2023 followed rain on 10 Nov) are
  known clean Diwalis. The model results do not depend on this (Diwali is 2 days in 51).

Station-level data — which would have settled the main open question — did **not** clear: see §9.

The CPCB's own footnote on every bulletin says city averaging is a convenience, not science: averaging
"is not a scientifically sound approach" (CPCB bulletin note). That sentence is the hinge of this report.

---

## 2. Method

**Extraction.** Each PDF is parsed twice: path A with poppler `pdftotext -layout` + a line pattern;
path B with `pdfplumber` table cells. Path A is the analysis input; path B feeds the independent
verification (§8). City names are matched case-insensitively (2026 bulletins print "Greater noida");
"Gurgaon" is renamed Gurugram.

**Comparison windows.** The current season is incomplete, so every year-on-year claim uses the same
calendar window in every year: **1 Oct–20 Nov** (51 days) and **1–20 Nov** (20 days). Full winters
(**1 Oct–31 Jan**) are used for completed seasons 2015-16 to 2025-26; calendar years for 2016–2025.
Extra windows in robustness: 15 Oct–15 Nov, 1–31 Oct, 1–15 Nov.

**Metrics.** Mean and median city AQI; number/share of days Poor or worse (>200), Very Poor or worse
(>300) and Severe (>400); 90th-percentile day. AQI 100 is the top of "Satisfactory" (at or below the
24-hour standard for the governing pollutant); the brief's PM2.5 60 µg/m³ standard corresponds to
PM2.5 sub-index 100, but the bulletin gives only the overall AQI, so the 60 µg/m³ test is not directly
available — in Delhi every day from 1 Oct to 20 Nov in almost every year is above AQI 100, so it does
not discriminate anyway (§4.3).

**Uncertainty.**
1. *Within-window noise* — 95% moving-block bootstrap, 7-day blocks (air quality is strongly
   autocorrelated), 4,000 replicates. Two versions: **unpaired** (each window resampled on its own —
   conservative, because blocks drawn from a window that climbs from October into November mix early
   and late days) and **paired by calendar date** (2026 day *d* against the same date in the comparison
   year, blocks of dates resampled — removes the shared seasonal climb). Paired is the primary interval
   for year-against-year statements; unpaired is reported alongside.
2. *Between-year noise* — trends are ordinary least squares on yearly window means, with a t-interval
   from the scatter of years around the line (so a single odd-weather year widens it); Theil–Sen slope
   as a check.
3. *Weather model* — cluster bootstrap over year-week blocks (400 replicates).

**Weather/fire/Diwali model** (`analysis.py`, 1 Oct–20 Nov, Delhi): log(city AQI) on log wind speed,
rain >1 mm today and yesterday, minimum temperature, day–night temperature range (a stability proxy),
humidity, north-westerly wind indicator, Diwali night +1 and +2 days, week-of-window effects, and a
separate level for each year. Weather is blended 1/3 previous day + 2/3 same day, because the 4 PM
bulletin covers 4 PM yesterday to 4 PM today. Variant 2 adds log(1 + MODIS fire detections in the box
29.0–32.5 N, 73.8–77.5 E, summed over the previous two days), 2015–2025 only. The year levels from the
model are the **weather-adjusted year index**. "Share of year-to-year spread explained by weather" =
1 − variance(adjusted year levels) / variance(raw year means).

**Network-change tests (H2).** Station-level data is not obtainable (§9), so composition is tested
indirectly: (a) Delhi relative to its NCR neighbours, 30 days before vs after each jump in Delhi's
reporting-station count, against the same calendar dates in other years; (b) day-to-day station
drop-outs within winters; (c) for 2026, each city's change from 2025 against whether its monitor list
grew, and against the history of that city's change relative to Gurugram (the only city whose list did
not change).

---

## 3. What the bulletin says — the obvious answer (H1, H3)

### 3.1 Delhi, same window every year

| Year | 1 Oct–20 Nov mean AQI | days >300 | days >400 | 1–20 Nov mean | days >300 | days >400 | Delhi stations (median, window) |
|---|---|---|---|---|---|---|---|
| 2015 | 301 (48 d) | 26 | 3 | 357 | 17 | 3 | 5 |
| 2016 | 320 | 27 | 12 | **397** | 20 | 9 | 6 |
| 2017 | **321** | **33** | 8 | 376 | 18 | 7 | 15 |
| 2018 | 297 | 25 | 6 | 342 | 15 | 5 | 33 |
| 2019 | 280 | 22 | 9 | 353 | 15 | 7 | 34 |
| 2020 | 298 | 23 | 8 | 349 | 14 | 8 | 35 |
| 2021 | 255 | 19 | 8 | 383 | 19 | 8 | 36 |
| 2022 | 257 | 19 | 3 | 329 | 12 | 3 | 35 |
| 2023 | 279 | 22 | 8 | 372 | 17 | 8 | 35 |
| 2024 | 294 | 28 | 7 | 387 | 20 | 7 | 36 |
| 2025 | 275 | 25 | 3 | 355 | 18 | 3 | 38 |
| **2026** | **226** | **12** | **0** | **320** | **12** | **0** | **56** |

(Every year 2016–2026 has 51/51 and 20/20 days published except 2017 Oct–Nov, 50/51.)

- **Not worse.** On both windows 2026 is the lowest of the 11 years 2016–2026; the worst autumns in the
  bulletin are 2016 and 2017. Trend 2016→2026, 1 Oct–20 Nov: **−6.5 AQI points a year** (95% range
  −10.8 to −2.1; Theil–Sen −6.5). 1–20 Nov: −2.9 a year (−8.0 to +2.3) — no clear trend.
- **2026 against the 2016–2025 average (paired by date):** 1 Oct–20 Nov **226 vs 288, −21%** (−33% to
  −12%); 1–20 Nov **320 vs 364, −12%** (−16% to −5%). Unpaired intervals: −123 to −5 points and −72 to
  −6 points.
- **2026 against 2025 (paired):** 1 Oct–20 Nov −17.8% (−32% to −1%); 1–20 Nov −9.8% (−22% to +15%) —
  the November improvement on last year is within day-to-day noise.
- **No Delhi day in the archive reached 500.** The highest bulletin value is 497 (2016). "Record" in a
  headline is therefore never a record on this scale, which caps at 500.
- **Even this year, every day from 1 to 20 Nov 2026 was Poor or worse (20 of 20 days >200).**

### 3.2 Full winters and whole years (completed seasons)

| | 15-16 | 16-17 | 17-18 | 18-19 | 19-20 | 20-21 | 21-22 | 22-23 | 23-24 | 24-25 | 25-26 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Oct–Jan mean | 323 | 328 | 323 | 323 | 292 | 312 | 290 | 290 | 323 | 301 | 309 |
| Oct–Jan days >300 | 82 | 84 | 82 | 78 | 58 | 67 | 63 | 68 | 88 | 66 | 78 |

Calendar-year means 2016–2025: 256, 228, 225, 215, 185 (lockdown year), 209, 209, 204, 209, 200.
Trends: Oct–Jan 2016-17→2025-26 −2.1/yr (−5.7 to +1.5); calendar 2016–2025 −4.5/yr (−8.1 to −0.8).

### 3.3 Averages vs threshold days (H3)

Threshold days and averages tell the same broad story but with different force:
- **Severe days fell further than averages.** Share of 1 Oct–20 Nov days >400: 16.9% (2016–20) vs
  8.2% (2022–26); Delhi average fell only 12% (304 → 266; unpaired interval −81 to −6 points).
  In 1–20 Nov the average barely moved (363 → 353, −3%, interval −46 to +6) while Severe days fell
  from 36% to 21% of days.
- **2026: zero Severe days in every NCR city** between 1 Oct and 20 Nov — the first time for every
  city in the archive (previous Delhi minimum: 3, in 2022 and 2025). Gurugram, whose monitor list did
  not change, also had none (it had 0 in 2025 too). Highest 2026 values: Delhi 382, Gurugram 368,
  Ghaziabad 368, Faridabad 350, Greater Noida 348, Noida 332. A bootstrap cannot put a range on zero;
  the comparison is with the history.
- **"Above standard" (AQI >100) doesn't discriminate:** Delhi had 45–51 of 51 days above 100 between
  1 Oct and 20 Nov in every year, 2026 included (48), and 20 of 20 days in 1–20 Nov in every year
  2016–2026 (`season_summary_by_city.csv`, `days_above_100`).

---

## 4. The turn — the number is not measuring the same thing every year (H2)

### 4.1 The network behind "Delhi"

Delhi's daily figure came from a median of **5 stations in 2015–16, 9 in 2017, 28 in 2018, 33–37 in
2019–2025** — and then:
- **28 Feb–11 Mar 2026:** listed Delhi stations 40 → 47.
- **7–13 Oct 2026 — inside this autumn's comparison window:** 46 → **59** (+13, +28%).
- Noida 4 → 7 on 27 Oct 2026; Ghaziabad 4 → 9 in steps (Apr, Jul, 28 Oct, 13 Nov 2026); Greater Noida
  2 → 3 → 5 → 7 (31 Oct, 6 Nov, 20 Nov 2026); Faridabad 4 → 3 (28 Oct 2026); **Gurugram 4 throughout.**
- Nationally the bulletin grew from a median 11 cities (2015) to 243 (2026).

So this autumn's Delhi figure averages ~56 stations against 38 last autumn and 6 in 2016. A city
average is only comparable over time if the stations added are like the ones already there.

### 4.2 Test (c): did the cities whose networks grew improve more? — **yes, strikingly**

Change in mean AQI, 2026 vs 2025, paired by date (95% range in brackets):

| City | listed monitors 2025 → 2026 | 1 Oct–20 Nov | 1–20 Nov | 14 Oct–20 Nov | 1–31 Oct |
|---|---|---|---|---|---|
| Gurugram | 4 → 4 | −3.9% (−25, +16) | **+7.4%** (0, +30) | −10.4% | −14.6% |
| Faridabad | 4 → 3 | −7.5% (−29, +13) | **+2.5%** (−1, +30) | −12.7% | −18.2% |
| Delhi | 39 → 59 | −17.8% (−32, −1) | **−9.8%** (−22, +15) | −22.6% (−35, −4) | −25.9% |
| Noida | 4 → 7 | −23.2% (−35, −7) | **−20.4%** (−33, +2) | −29.5% (−38, −13) | −25.8% |
| Ghaziabad | 4 → 9 | −23.7% (−36, −7) | **−24.4%** (−33, −8) | −31.1% (−39, −17) | −23.0% |
| Greater Noida | 2 → 7 | −25.4% (−33, −14) | **−25.6%** (−38, −3) | −27.1% (−36, −13) | −25.2% |

- **October 2026 was cleaner everywhere** (−15% to −26%), including in the two cities with unchanged
  networks — that part is regional (1 Oct–18 Nov 2026 had 6 rain days at Delhi in the NASA series, the
  most since 2022).
- **In November the split is clean:** the four cities whose monitor lists grew are 10–26% below
  last year; the two whose did not are 2–7% *above* it.
- **Against history:** relative to Gurugram, Noida's, Ghaziabad's and Greater Noida's 2026 change (−19
  to −33 points in the two main windows) is **beyond the most negative value in each city's own
  history** (historical minimum −8 to −16 points; 5–8 earlier year pairs). Delhi's (−14 / −17 points)
  is the 2nd most negative of 10 year pairs.

**What this does not prove:** the expanded cities are Delhi and the three Uttar Pradesh cities east of
it; the unchanged ones are the two Haryana cities to the south. Anything that differed between the
east and the south-west of the region this November (local measures, wind direction, local sources)
would produce the same split. Faridabad sits ~20 km from Greater Noida, which weakens but does not
remove the geography explanation. Only station-level data (§9) can separate the two.

### 4.3 Tests (a) and (b): timing and drop-outs — **inconclusive / no effect**

- **Delhi, 11 Oct 2026 jump (46 → 59 listed):** Delhi relative to Gurugram rose **+25.8%** in the 14
  days after vs before (range +17% to +35%). Same dates in 2019–2025 ranged −21% to +35% (mean +2%):
  mid-October is when Delhi pulls away from Gurugram anyway. No sign the new stations pulled the
  number *down* at the moment they joined.
- **Noida, 27 Oct 2026 (4 → 7):** −11.4% relative to Gurugram (−19% to +2%); same dates other years −19%
  to +6% (mean −2%). Suggestive, not clear.
- **Delhi, 19 Feb 2026 (38 → 44 reporting):** −7.6% (−10% to −3%); other years −10% to +17% (mean −1%).
- **All 12 detected Delhi steps since 2017** (30-day windows, vs all NCR neighbours): effects from −12%
  to +24%; ordinary dates give −16% to +16% (95% of 366 placebo dates). Only the Oct 2026 step falls
  outside, and in the *upward* direction. `station_step_events.csv`.
- **Drop-outs:** on winter days 2018–2026 when fewer Delhi stations reported than usual (s.d. 2.5
  stations), Delhi's figure relative to its neighbours moved −0.04% per missing station (−0.38% to
  +0.30%; 1,063 days). Losing a few *existing* stations at random does not move the average — so the
  old stations are interchangeable among themselves. That says nothing about whether the *new* ones are.

**Verdict on H2:** for 2016→2018 (6 → 33 stations) there is no clear signature in the step tests, and
the neighbours with one station each did not move consistently (Faridabad flat, Gurugram up). For
**2026**, the cross-city pattern is strong and the timing test is inconclusive. **Unresolved, and it
matters**: the whole of this year's apparent improvement in November rests on cities whose monitor
lists changed during the window.

---

## 5. The corrected answer

### 5.1 Hold the network roughly constant: 2019–2025 (Delhi 33–40 stations)

| Window | yearly means 2019 → 2025 | trend per year (95% range) |
|---|---|---|
| 1 Oct–20 Nov | 280, 298, 255, 257, 279, 294, 275 | **−0.04** (−8.9 to +8.8) |
| 1–20 Nov | 353, 349, 383, 329, 372, 387, 355 | **+2.6** (−8.0 to +13.1) |
| Calendar year | 215, 185, 209, 209, 204, 209, 200 | **0.0** (−5.1 to +5.1) |

**With a stable network, Delhi's published AQI has been flat for seven years** — autumn, November and
whole-year. The 2016–17 highs (6–15 stations) and the 2026 low (56–59 stations) are the two ends of
the record, and both sit on network changes.

### 5.2 Take the weather out (H4)

Model on 606 Delhi days (1 Oct–20 Nov, 2015–2026), R² 0.79.
- Doubling wind speed → about **−17%** AQI; rain (>1 mm) the previous day → **−38%**; rain the same day
  → −13%; warmer nights and a larger day–night range → higher; **Diwali night → +18% next day, +12% the
  day after.**
- **Weather accounts for about 76% of the year-to-year spread** in this window (95% range 20%–94% —
  wide, because 12 years is few). With fires added (2015–2025): 87% (41%–96%).
- Weather-adjusted year index (1 = 2015–2026 average): 2015 1.00, 2016 1.04, 2017 1.04, 2018 1.11,
  2019 0.97, 2020 0.98, 2021 0.99, 2022 1.02, 2023 0.98, 2024 1.03, 2025 1.04, **2026 0.84 (0.73–0.95)**.
- The two "good" autumns of 2021 and 2022 (raw 0.85, 0.86) were rain: 119 mm and 133 mm between 1 Oct
  and 18 Nov, against 0–34 mm in other years. After adjustment they are ordinary (0.99, 1.02).
- **2026 survives the weather adjustment (−16%)** — but its weather inputs come from a different NASA
  model (GEOS-IT), and its air-quality input from a network 28–50% larger than any earlier year's.

### 5.3 Farm fires — the second turn

| Year | CREAMS fire events to 20 Nov, Punjab + Haryana | NASA MODIS detections, PB-HR box, 1 Oct–20 Nov | Delhi 1 Oct–20 Nov | Delhi 1–20 Nov |
|---|---|---|---|---|
| 2016 | — | 20,213 | 320 | 397 |
| 2018 | 66,478 | 14,665 | 297 | 342 |
| 2020 | **83,394** | 18,267 | 298 | 349 |
| 2021 | 77,320 | 19,947 | 255 | 383 |
| 2023 | 37,216 | 8,867 | 279 | 372 |
| 2024 | 11,287 | 4,181 | 294 | 387 |
| 2025 | **5,638** | 3,697 | 275 | 355 |
| 2026 | 7,244 | (not yet published) | 226 | 320 |

- **Counted fires fell 93% from 2020 to 2025** (CREAMS, Punjab + Haryana: 83,394 → 5,638; NASA MODIS in
  the box: −80% from 2021). The two independent counts move together (correlation 0.99 across the 6
  shared years). Over the same span Delhi's 1 Oct–20 Nov AQI fell 8% (298 → 275) and its 1–20 Nov AQI
  rose 2% (349 → 355).
- In the daily model, doubling the two-day fire count raises Delhi's AQI by about **2.3%** — small.
- CREAMS windows differ slightly by year (start 30 Sep in 2018, 1 Oct in 2020, 15 Sep from 2021); the
  Sept fires are few. Haryana's 2026 count (307) is the lowest in the series.

The data cannot say *why* the air did not follow the fires: either farm smoke was a smaller share of
Delhi's autumn pollution than the annual headlines imply, or the satellite counts stopped capturing the
burning (a count depends on burning happening while a satellite passes overhead). Both readings fit.

### 5.4 Diwali and COVID

- Diwali fell in October in 2016, 2017, 2019, 2022, 2024, 2025 and in November in the other years. The
  bulletin after Diwali night averages +66 points over the previous week (10 of 12 years higher). It is
  2 days in a 51-day window; dropping Diwali+1 to +3 changes no conclusion (robustness grid).
- The 2020 lockdown (25 Mar–31 May) is outside every autumn window. Calendar-year 2020 (185) is the
  record low year; dropping 2020 from the comparison base changes no conclusion.

---

## 6. NCR cities (H5)

1 Oct–20 Nov means (stations behind the figure, window median):

| | Delhi | Gurugram | Noida | Ghaziabad | Faridabad | Greater Noida |
|---|---|---|---|---|---|---|
| 2016 | 320 (6) | 238 (1; 78% of days) | — | — | 348 (1; 84%) | — |
| 2018 | 297 (33) | 310 (1) | 308 (2) | 323 (1) | 315 (1) | — |
| 2020 | 298 (35) | 280 (4) | 300 (3) | 316 (4) | 297 (4) | 314 (2) |
| 2022 | 257 (35) | 237 (4) | 239 (4) | 243 (4) | 248 (4) | 241 (2) |
| 2024 | 294 (36) | 220 (3) | 241 (4) | 262 (4) | 186 (4) | 238 (2) |
| 2025 | 275 (38) | 225 (3) | 281 (4) | 277 (4) | 181 (3) | 270 (2) |
| 2026 | 226 (56) | 217 (4) | 216 (4→7) | 211 (7→9) | 168 (3) | 202 (2→7) |

Full table for every year in `data/season_summary_by_city.csv`. Notes:
- Before 2019–20 Gurugram, Faridabad, Noida and Ghaziabad were single-station cities: their figure
  was one monitor. Years with <60% of days published are excluded from city charts.
- Delhi is the worst of the five in 1 Oct–20 Nov 2024 (294) and close to the worst in 2025 (275, behind
  Noida 281 and Ghaziabad 277). Faridabad's figure fell ~30% in
  2024 (270 → 186) with no change in listed monitors; we cannot see why from the bulletin.
- **Delhi is the laggard over 2020–2025** (years when every city had a multi-station network). Trend in
  the 1 Oct–20 Nov mean, points per year: Delhi +0.6 (−12.7 to +14.0); Gurugram **−9.9 (−17.6 to −2.2)**;
  Faridabad **−22.7 (−38.4 to −6.9)**, driven by an abrupt 2024 drop; Noida −4.3, Ghaziabad −7.6, Greater
  Noida −6.8 (all intervals span zero). Calendar-year trends 2020–2025: none clear for any city.
  (`results.json` → `city_trends_2020_2025`.)
- Every city's 2026 1 Oct–20 Nov is its lowest on record; in 1–20 Nov Gurugram's 2026 ranks 8th of 11
  (i.e. an ordinary November) and Faridabad's 10th of 11.

---

## 7. Robustness

`data/robustness_grid.csv` — 5 windows × 6 metrics × 2 Diwali treatments × 2 series (Delhi; average of
the five NCR cities on days all five published) × 4 comparisons = 240 rows; unpaired block-bootstrap
intervals (the conservative kind).

| Headline | Survives? |
|---|---|
| "Not getting worse" (2026 or 2022–26 vs earlier) | **Yes, everywhere.** In no variant is the later period clearly worse except one: NCR-5 share of days Poor or worse in 1–20 Nov (2026 100% vs ~97%) — every November day is Poor in nearly every year. |
| "2026 is the lowest year" (rank) | Yes for mean, 90th-percentile day and Severe days in every window; on the median it is lowest or second-lowest. |
| "2026 clearly below 2016–2025 average" | Mean: yes in all 5 windows. Days >300: only in Oct 1–31 (Delhi). Median: only in Nov 1–15 and Oct. |
| "2026 clearly below the stable-network years 2018–2025" | **Only for Severe days, 90th-percentile day, and October.** Delhi mean AQI in Nov 1–20, Nov 1–15, Oct 15–Nov 15 and Oct 1–Nov 20: no clear difference (unpaired). Paired: −11% (−15 to −2) in 1–20 Nov. |
| "2022–26 lower than 2016–20" | Delhi 1–20 Nov mean and median: **no clear difference**; Severe share and 90th percentile: lower. NCR-5: lower on every metric in every window with enough years. |
| Trend 2016–2026 1 Oct–20 Nov (−6.5/yr) | Dies when start moved to 2018 (−4.8, −11.3 to +1.7) or network held constant 2019–2025 (−0.04). |
| Weather explains most year-to-year spread | Central 71–87% across three model variants, but every interval is wide (20%–96%). |

**What died:** (1) "Delhi's air is getting worse" — dead on every metric and window. (2) "Delhi's air is
getting steadily better" — survives only if you start in 2016 and include 2026; with the network held
constant it is flat. (3) "Farm fires drive the year-to-year swings" — not supported: counted fires fell
93% while the November AQI did not move. (4) A clean detection-effect estimate for 2016→2018 — the
tests show nothing clear either way.

---

## 8. Verification — every headline number computed twice

`scripts/verify.py` recomputes from **path B** (pdfplumber table cells instead of pdftotext lines),
using only the Python standard library (no pandas/numpy), FIRMS totals recounted from the raw CSVs with
the `csv` module, CREAMS totals re-read with pdfplumber instead of pdftotext. Output:
`data/verification.csv`. Result: see §8.1 (filled in from the run).

### 8.1 Verification run
**206 of 206 checks PASS** (run 21 Nov 2026; `data/verification.csv`). Covered: every Delhi window
mean, day count (>300, >400) and day total for 2015–2026 in both windows; Oct–Jan and calendar-year
means; Delhi station medians by year; the 2016–20 vs 2022–26 means and the 2016–2025 base; every NCR
city's 2025 and 2026 window means; every 2026-vs-2025 city change; the six trend slopes quoted (stdlib
regression); zero Severe days in all six cities in 2026; the archive maximum (497) and the count of
days at 500 (0); FIRMS box totals 2015–2025 (recounted from raw CSV); CREAMS Punjab and Haryana counts
(re-read with pdfplumber); and the weather model refitted with statsmodels (share 0.755, wind
coefficient, 2026 adjusted index).

Row-level agreement between the two extraction paths: 20,859 city-days read by both; **AQI identical on
all 20,859**. Station counts identical wherever both paths read one; path A failed to read the station
count on 88 city-days (74 Delhi; 2018–2019 and four in 2023 — a wrapped table cell), path B on 4.
Those days carry no station count in the analysis (the AQI is unaffected). Path A reads 184 early-2015
rows path B cannot (the May–Sept 2015 bulletins have no ruled table); all are before the first window.

Not re-derived by a second path: the bootstrap intervals themselves (seeded, so re-running reproduces
them exactly; a different seed will move the interval ends slightly — treat the second significant
figure as soft) and the station-step event studies.

---

## 9. Exclusion log

**Sources and routes not used**

| Route | Why excluded |
|---|---|
| CPCB CCR "Data Repository" (station-level CAAQMS data), `https://airquality.cpcb.gov.in/ccr/#/repository/data` | **CAPTCHA** on opening (screenshot-confirmed 21 Nov 2026). Not bypassed. This is the data that would settle H2. The portal's internal download endpoints (e.g. its mixing-height spreadsheets) were also not used. |
| `cpcb.nic.in` (original bulletin host) | TLS certificate expired 17 Nov 2026. Same files fetched from CPCB's other domain `www.cpcb.gov.in` (valid certificate, same file names, file referenced in CPCB's own portal code). |
| DPCC air-data portal, `https://www.dpccairdata.com/` | Returns HTTP 406 to automated requests. Not pursued. |
| IMD gridded rainfall/temperature (imdpune.gov.in) | Form POST download (brief: no forms); ends 2024. |
| IMD Data Supply Portal | Registration required. |
| data.gov.in CPCB real-time API | API key (registration) required; real-time only. |
| US Embassy New Delhi monitor (AirNow DOS, `dosairnowdata.org`) | Host does not resolve; also not Indian official data. Would have been the ideal single-fixed-site check. |
| NASA FIRMS near-real-time API (for 2026) | Needs a MAP_KEY (registration). 2026 fires taken from CREAMS instead. |
| OpenAQ, IQAir, news reports | Aggregators / secondary — excluded by the series rule. |

**Rows and days** (`data/exclusion_log_rows.csv`, `data/excl_missing_bulletin_files.csv`)

| Item | Count | Action |
|---|---|---|
| Bulletin days with no PDF (HTTP 404) | 35 (31 in 2015; 2016-06-06; 2017-06-18; **2017-10-14**; 2025-01-01) | Missing; only 2017-10-14 falls in a comparison window (Delhi 2017 = 50/51 days) |
| 1 Apr–1 May 2015 | no NCR rows (Delhi first appears 2 May 2015) | outside all windows |
| Bulletin 2016-04-01 | carries the 31 Mar 2016 header (duplicate) | 3 rows dropped |
| Header date unreadable (2015-07-16, 2015-07-31) | 2 files | kept, file-name date used |
| Printed category disagrees with printed AQI | 17 rows (e.g. AQI 300 printed "Very Poor"; Delhi 2023-11-15 AQI 398 printed "Severe") | kept; the AQI number is used for every threshold. Boundary cases (exactly 100/200/300) probably reflect CPCB rounding |
| City missing on a published day, inside 1 Oct–20 Nov | Delhi 0 (2016–2026); Gurugram 11 (2016), 6 (2017), 6 (2018), 1 (2019); Faridabad 8 (2016), 15 (2017), 1 (2018), 7 (2019), 1 (2025), 1 (2026); Noida 2 (2017), 1 (2018); Ghaziabad 1 (2017), 4 (2018) | windows computed on available days; city-years <60% coverage excluded from city charts/rankings |
| Greater Noida, 2016–2019 | not in bulletin | starts 2020 |
| Station count unreadable by path A | 88 city-days (74 Delhi, mostly 2018–19) | AQI kept; station count blank on those days |
| Weather, 19–21 Nov 2026 | not yet in NASA POWER | model window for 2026 ends 18 Nov for weather terms (2026 rows 19–20 Nov drop out of the model only) |
| FIRMS detections outside the box, or `type` ≠ 0 (not presumed vegetation fire) | per year in `prep_aux.py` output | excluded from fire counts |

---

## 10. What the data cannot tell you

1. **Whether the 2026 improvement is real.** The cities whose monitor lists grew this autumn are the
   ones that improved; the one that didn't, didn't. Station-level data (CAPTCHA-gated) is the only way
   to recompute 2026 on last year's stations. Until then, "cleanest autumn on record" cannot be said
   without "measured by a larger network".
2. **PM2.5 concentrations.** The bulletin publishes an index, not micrograms. The index is capped at
   500 and squeezes high concentrations (each band covers more µg/m³ than the one below), so a fall in
   AQI from 380 to 340 is not a fixed percentage fall in PM2.5. The 60 µg/m³ test in the brief cannot
   be done from this source.
3. **What anyone breathed.** A city average of station indices is not exposure. CPCB says so itself.
4. **Why farm-fire counts and Delhi's air came apart.** Smaller-than-claimed contribution, or burning
   the satellites no longer see — this data cannot choose.
5. **The weather adjustment's precision.** It uses a NASA reanalysis at one grid point, not IMD
   observations; 12 seasons is few (the 76% has a 20–94% range); and 2026 weather comes from a
   different model.
6. **The rest of this winter.** The comparison stops on 20 Nov. December and January are typically as
   bad as November; the Oct–Jan verdict for 2026-27 does not exist yet.
7. **Anything outside these six cities**, or before May 2015.
