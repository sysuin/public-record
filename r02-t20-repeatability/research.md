# R02 — "Does one T20 season tell you anything about the next?"

**Series:** Public Record · **Compiled:** 21 Nov 2026 · **Timed to:** IPL 2027 auction (mid-Dec 2026)
**Status:** analysis complete; every headline number re-computed by a second, independent code path (§9).

How to re-run everything (≈6 minutes on a laptop):
`sh scripts/run_all.sh <folder of extracted Cricsheet zips> <scratch folder>`

---

## 1. Source

| | |
|---|---|
| Publisher | **Cricsheet** (https://cricsheet.org), Stephen Rushe's volunteer project transcribing official scorecards ball by ball |
| Index page | https://cricsheet.org/downloads/ (fetched 21 Nov 2026, 14:07 UTC) |
| Format | JSON v1.3.0, one file per match (https://cricsheet.org/format/json/) |
| Licence | Open Data Commons Attribution License (ODC-By), shipped as `LICENSE.txt` in every zip — attribution "Cricsheet" required on screen |
| Downloaded | 21 Nov 2026, 14:07–14:08 UTC (server last-modified on `all_json.zip`: 3 Nov 2026) |

### Exact files (URL = `https://cricsheet.org/downloads/<file>`), with file counts and md5 of each zip

File counts match the counts printed on the Cricsheet downloads page exactly for every zip.

| File | Competition | Files | md5 |
|---|---|---|---|
| ipl_json.zip | Indian Premier League | 1,243 | 2c2b1ed7620c6b71b989cda19ece6665 |
| bbl_json.zip | Big Bash League | 662 | e2db73b0e0b92f177f7f76339a7a665e |
| psl_json.zip | Pakistan Super League | 357 | ce5f0ff5eb1e326864197cc518398c11 |
| cpl_json.zip | Caribbean Premier League | 445 | ad39556f21ed0274c32679099ad028d4 |
| sat_json.zip | SA20 | 130 | d1fe4baecc89012ce61feec05b13b8fa |
| ilt_json.zip | International League T20 | 134 | 598b4d9eac78ad2604892a153ccc3ab8 |
| ntb_json.zip | T20 Blast (England) | 1,570 | e502c41a782443c2be1560c8096322e5 |
| bpl_json.zip | Bangladesh Premier League | 469 | f52f80af65d546353b9de7acfe3063ed |
| lpl_json.zip | Lanka Premier League | 143 | 07ee9802b93586e0017e19ece8ae07f5 |
| mlc_json.zip | Major League Cricket | 109 | 99a5052934c70178b1d86edb53706a0c |
| msl_json.zip | Mzansi Super League | 56 | 747d2d2f4605b1fb0515dea015b8c783 |
| npl_json.zip | Nepal Premier League | 76 | 116d1ff4a83e4d96cf44ed3013c692e4 |
| sma_json.zip | Syed Mushtaq Ali Trophy | 695 | bae3c3d5382018a666a7d7e731259383 |
| ssm_male_json.zip | Super Smash (NZ men) | 270 | 9c89b22b650ec5a12a15a0cdd5cfe551 |
| ctc_json.zip | CSA T20 Challenge | 314 | d0b0745d6e011ee240f8a2615aa0a3e6 |
| ipt_json.zip | Ireland Inter-Provincial T20 | 111 | ffa4451f4f60d0bb2a9487a0a2bf9fe8 |
| mct_json.zip | Sri Lanka Major Clubs T20 | 121 | 18869278a21c2b99f572af841c5741c2 |
| etpl_json.zip | European T20 Premier League | 31 | 8628bd267394fdba16776d3df65d5ae6 |
| hnd_male_json.zip | The Hundred (men) | 201 | ec13e433ee19acc3e4a4f25909bbb33e |
| t20s_male_json.zip | T20 internationals (men) | 3,649 | 28884e40c12efde03f9fc94dbaec4526 |
| wpl_json.zip | Women's Premier League | 88 | 4d352de69cde8c5121051c0d2b44a152 |
| wbb_json.zip | Women's Big Bash League | 527 | fa42bdf1de9973948f185f2fc97aa17b |
| cec_json.zip | Charlotte Edwards Cup | 124 | 1f0509d74270a1e772bf15df46b49897 |
| wcl_json.zip | Women's CPL | 33 | db8786be40b4b037a52be6635977a6a7 |
| wtb_json.zip | Women's T20 Blast | 112 | 5cbe5cb9f5fc14e37c6e092871ababf4 |
| wsl_json.zip | Women's Cricket Super League | 95 | ff079a74f8369f06622ee49217d684f5 |
| blz_json.zip | T20 Blaze (WI women) | 17 | 7ecc8a00e1dea50cf2c976aadee40d6d |
| frb_json.zip | FairBreak Invitational | 39 | 03c7bc0581510d889b432d8dda335ade |
| wtc_json.zip | Women's T20 Challenge (India) | 13 | eae264de8e62bd9fba70f0b88dd56ebd |
| ssm_female_json.zip | Super Smash (NZ women) | 197 | 0c60a36b42037663b5fb21a13ef135f1 |
| hnd_female_json.zip | The Hundred (women) | 188 | 9713ffb86e3ba044b10611fdb040b086 |
| t20s_female_json.zip | T20 internationals (women) | 2,200 | 2594188c2969bcdcc11765ff2903aed1 |
| **Total** | **32 competitions** | **14,419** | |

Not used: `it20s_*` (non-official T20Is), all one-day and multi-day zips, and the 386 matches Cricsheet itself withholds (listed as "withheld" on the downloads page — we never see them).

### How Cricsheet meets — and falls short of — the "body that generated it" bar
The body that generates a T20 scorecard is the league or board (BCCI for the IPL and SMAT, Cricket Australia for the BBL, ECB for the Blast, the ICC for T20Is, etc.). **None of them publishes a bulk, downloadable ball-by-ball record.** They publish match-by-match scorecards and commentary on their own sites, in formats that change (iplt20.com was rebuilt in 2026, as PR#1 found). Cricsheet is a volunteer transcription of those official records, published openly, versioned, with a stable per-match file and a public format spec. That makes it the **only downloadable ball-by-ball record that exists for this question**.

**The substitution, stated plainly (as PR#1 did):** every number in R02 comes from Cricsheet, not from the leagues. To state on air: *"The leagues publish their scorecards one match at a time. Cricsheet, a free volunteer project, has transcribed every ball of every match into one download — that's what we used, and you can download it yourself at cricsheet.org."*

Independent structural checks of the transcription (what substitutes for a second source):
- File counts per zip equal the counts on the downloads page (32/32).
- Every innings' runs and wickets are internally consistent with the deliveries (our parser rebuilds totals from deliveries; the run-value model nets to ~0 per league-season, §4).
- Known Cricsheet data faults found and logged: 18 T20Is carry `overs: 50` in their metadata (the ball data shows 20-over innings; treated as T20); 26 matches whose first innings stopped short of 20 overs without being bowled out but carry no reduced-overs flag (dropped); PSL 2020's four Nov-2020 playoff matches are labelled season "2020/21" by Cricsheet although they finished PSL 2020 (our date-based seasons fix this).

## 2. Coverage after exclusions

| Group | Competitions | Matches | Competition-seasons | Deliveries |
|---|---|---|---|---|
| Men — franchise & domestic leagues | 18 | 6,427 | 150 | 1,525,877 |
| Men — The Hundred | 1 | 189 | 6 | 37,680 |
| Men — T20Is (full members only) | 1 | 1,035 | 22 calendar years | 246,419 |
| Women — franchise & domestic leagues | 10 | 1,127 | 46 | 267,996 |
| Women — The Hundred | 1 | 181 | 6 | 35,879 |
| Women — T20Is (full members only) | 1 | 653 | 18 calendar years | 153,773 |
| **Total** | **32** | **9,612** | **248** | **2,267,624** |

6,072 distinct players (4,929 men, 1,143 women); 34,972 player-competition-seasons (22,743 in men's leagues). IPL: 1,199 matches, 19 seasons (2008–2026), 288,530 deliveries. Per-competition detail: `data/coverage_by_competition.csv`; every season with its dates: `data/seasons.csv`.

## 3. Seasons — derived from match dates
Cricsheet's `season` field is a free label ("2009", "2009/10", "2020/21"); slicing it to four characters makes "2009/10" collide with "2009". We never use it. Instead:
1. Within each competition, matches are sorted by date; **a gap of more than 90 days starts a new season.** Checked against Cricsheet's labels: at 90 days only two labels are split by the rule, both genuine COVID suspensions.
2. **Three documented merges** for suspended-and-resumed seasons: IPL 2021 (Apr–May + Sep–Oct 2021), PSL 2020 (Feb–Mar + playoffs Nov 2020), PSL 2021 (Feb–Mar + Jun 2021).
3. Label = start year of the season's first match, or "YYYY/YY" when it crosses New Year. Because two seasons can start in one calendar year (SA20 Jan 2025 and Dec 2025; BPL Jan 2019 and Dec 2019; ILT20; women's Super Smash), the unique key is the full label and order is an explicit ordinal.
4. T20 internationals have no season: calendar year.
5. "Next season" = next ordinal in the same competition, starting within two calendar years.

## 4. Method

### 4.1 Metrics (per player, per competition-season)
Batting (balls faced = all deliveries except wides): strike rate; average (runs per dismissal); boundary % (4s and 6s per ball faced, excluding "non-boundary" fours); dot-ball %; dismissals per 100 balls; **runs added per 100 balls** (value). Bowling (legal balls): economy (runs conceded excluding byes and leg-byes, per 6 balls); wickets per 24 balls (bowler-credited dismissals only); bowling dot %; boundaries conceded per 100; **runs saved per 100 balls** (value).
Every metric is expressed **relative to its competition-season average** (a strike rate of 150 in a 140 league-season is +10). This removes league and era scoring levels from every comparison and is what allows pooling.

Added because the data demanded it:
- **Situation-adjusted** strike rate and economy: runs relative to what an average player produces in the same over and wickets-down state, same competition-season (no wicket pricing).
- **"The job" metrics**: share of a player's balls in the powerplay (overs 1–6) and at the death (16–20).
- **Phase and batting-position splits**: strike rate, economy and wickets by phase; strike rate for openers (No. 1–2), No. 3–4, finishers (No. 5–7). Batting position = order of first appearance at the crease in that innings.

### 4.2 The run-value model (PR#1's method, rebuilt)
Reused from PR#1: per-ball runs above expected by (over, wickets down); wicket cost from the run-expectancy surface `RE = C·(1−e^(−b·balls_left/120))·(wickets_in_hand/10)^g`.
Fixed:
| PR#1 | R02 |
|---|---|
| Players keyed by **name** | Keyed by Cricsheet **registry ID** (names collide across 32 competitions) |
| Baselines from one league | Baseline per **competition-season** and state; thin cells shrunk toward the pooled format×gender×era cell rescaled to that competition-season (PR#1 shrank to the over mean, which biased thin high-wicket cells and made batting value net negative: −2.0 per 100 balls before the fix, −0.2 after) |
| One surface fit | Surface fitted per format (T20 / Hundred) × gender × era (≤2012, 2013–17, 2018–21, 2022–; women pre-2013 merged; Hundred one era). Weighted R² 0.994–0.998 for every fit with ≥50 cells (`data/wicket_cost_fits.csv`), scaled to each competition-season's run rate |
| Non-striker run-outs ignored | Dismissal charged to whoever is out |
| Dismissals off wides missed | Counted (found by the independent re-computation, §9) |
| Calendar year = season | Date-derived seasons (§3) |
Sanity: value nets to −0.28 (batting) / +0.19 (bowling) runs per 100 balls, ball-weighted, across 248 competition-seasons; the larger residuals are tiny seasons (e.g. Ireland IPT 2026, 889 balls).

### 4.3 Repeatability (season N vs N+1)
Same player, same competition, consecutive seasons, minimum balls in **both** seasons (main: 120; also 30, 60, 180, 240, 300, 400). Pearson correlation of the relative values. Pooled men's leagues = all 18 men's franchise/domestic competitions; Hundred and T20Is reported separately and in a wider pool. **Intervals: 95% percentile intervals from 1,000 resamples of players** (a player contributes several season-pairs, so resampling pairs would understate uncertainty). Slope of N+1 on N = share of the edge kept.

### 4.4 Signal vs noise
Split-half within a season by **alternate matches** (player's 1st, 3rd, 5th… vs 2nd, 4th…), each half ≥60 balls. From the half-season correlation r and the typical balls per half n (harmonic mean), the **balls-to-half-signal** K = n(1−r)/r: after K balls, half of the observed spread between players is real. Reliability at n balls = n/(n+K). "Talent carryover" = year-to-year r ÷ the reliability both seasons allow — an approximate read of how much real skill persists once noise is removed (reported only where reliability ≥0.25; unstable otherwise).
**Why not PR#1's split:** PR#1 split alternate *deliveries*, which puts both halves in the same matches, conditions and opponents. Reproduced here on IPL batters (≥150 balls): alternate deliveries **r = 0.564** [0.504, 0.623] (PR#1 reported 0.565); alternate matches **r = 0.390** [0.314, 0.460], same 743 player-seasons. PR#1's within-season reliability was overstated (`data/split_method_check_ipl.csv`).

### 4.5 Forecast contest (out of sample)
Target: a player-season with ≥120 balls whose previous season in that competition had ≥60 balls. Forecasts built only from earlier data: F0 league average; F1 last season as recorded; F2 career to date (same competition); F3 recency-weighted career (weight λ^k for k seasons back); F4 last season pulled toward average (×n/(n+K)); F5 recency-weighted **and** pulled toward average; F6 = F5 using every T20 competition (same gender) in the 3 years before the target season, each match measured against its own competition-season average. λ and K chosen by grid search on **targets 2008–2019 only**; scored on **2020–2026**; also run reversed (tune on 2020–26, test on ≤2019). Score = % of error removed vs F0 (1 − MSE/MSE₀); 1,000 player resamples, paired.

### 4.6 Cross-league translation
Target: player's season in competition B (≥120 balls). Source: the same player's matches in competition A in the 365 days before B's season started (≥60 balls), relative to A's own season averages. Correlation, slope and the mean gap (target − source). Baseline: B's own previous season under the same window. IPL sources also grouped: SMAT / T20Is / all overseas leagues + Hundred. Selection check for SMAT: established IPL regulars (≥120 balls the previous IPL season) vs new or fringe players.

### 4.7 The Hundred
100-ball innings in 5-ball sets. Kept as its **own competition**, never pooled into the main men's/women's league figures: per-ball rates are comparable, but phases and over-based states are not (its 20 sets of 5 are mapped to "overs" 1–20 for the value model, with its own run-expectancy fit). It is used as a **source** in cross-league tests and in F6, where per-ball rates relative to its own season average are what matter. Only 22–28 consecutive-season pairs reach 120 balls, so Hundred-only results are too thin to report on their own.

### 4.8 Age curves — skipped
Cricsheet's people register carries identifiers, not birth dates. No primary source for player birth dates exists in the download; aggregator DOBs fail the sourcing bar. Not attempted.

### 4.9 Pace vs spin — cannot be done
Cricsheet does not record bowling type. Classifying bowlers would require outside data (aggregators), which fails the bar. Not attempted; said on air.

## 5. Exclusion log
Full row-level log: `data/exclusion_log.csv` (every match/innings, with reason). Summary (`data/exclusion_summary.csv`):

| Level | Reason | Count |
|---|---|---|
| match | T20I involving an associate member (kept T20Is between the 12 ICC full members only) | 3,695 |
| match | Decided by D/L (interrupted / reduced) | 496 |
| match | Reduced-overs innings (target overs < 20) | 298 |
| match | No result | 283 |
| match | First innings ended short of full overs without 10 wickets — unrecorded reduction or data gap | 26 |
| match | Decided by VJD | 5 |
| match | Awarded | 4 |
| innings | Super-over innings dropped (match kept) | 73 matches |
| repair | `info.overs = 50` on a T20I file; ball data shows ≤20 overs; treated as 20 | 18 |

14,419 files → 9,612 matches kept (4,807 dropped). No file failed to parse.
**Player-seasons are never deleted** — they are filtered by the balls threshold of each test (documented with each number). Players below threshold, and players who did not return the next season, are not in the season-to-season tests (§7, survivorship).

## 6. Results — all numbers

Scope "men's leagues" = 18 men's franchise/domestic competitions pooled. Brackets = 95% interval. Threshold 120 balls both seasons unless stated. Source files in `data/`.

### 6.1 Repeatability and signal (`signal_summary_main.csv`, `yoy_repeatability.csv`, `split_half.csv`)

| Metric | Men's leagues N→N+1 r | IPL r | Women's leagues r | Balls to half-signal (men) | Reliability of a typical season (~215 balls) | Talent carryover |
|---|---|---|---|---|---|---|
| Strike rate | **0.31** [0.26, 0.35] (2,167 pairs, 586 players) | 0.33 [0.24, 0.41] (581) | 0.33 [0.21, 0.45] (358) | **270** [226, 328] | 0.45 | 0.69 |
| SR, situation-adjusted | 0.32 [0.27, 0.37] | 0.37 [0.26, 0.46] | 0.37 [0.24, 0.49] | 240 [203, 289] | 0.48 | 0.67 |
| Boundary % | 0.42 [0.37, 0.46] | 0.46 [0.36, 0.54] | 0.45 [0.33, 0.57] | 170 [146, 199] | 0.56 | 0.74 |
| Dot-ball % (bat) | 0.41 [0.36, 0.46] | 0.40 [0.30, 0.47] | 0.37 [0.25, 0.48] | 240 [206, 291] | 0.47 | 0.87 |
| Batting average | **0.15** [0.11, 0.20] | 0.19 [0.10, 0.27] | 0.35 [0.16, 0.47] | **1,640** [947, 3,682] | 0.12 | n/a |
| Dismissals per ball | 0.21 [0.16, 0.26] | 0.24 [0.14, 0.33] | 0.34 [0.20, 0.46] | 730 [548, 1,006] | 0.23 | 0.92 |
| Batting runs added | 0.18 [0.13, 0.22] | 0.19 [0.09, 0.28] | 0.24 [0.12, 0.35] | 500 [399, 655] | 0.30 | 0.59 |
| Economy | **0.40** [0.34, 0.46] (2,335 pairs, 696 players) | 0.39 [0.27, 0.48] (533) | 0.28 [0.14, 0.39] (472) | **320** [260, 411] | 0.40 | 1.02 |
| Economy, situation-adjusted | 0.29 [0.21, 0.37] | 0.33 [0.17, 0.45] | 0.19 [0.07, 0.30] | 560 [399, 854] | 0.28 | 1.05 |
| Wicket rate | **0.19** [0.15, 0.24] | 0.17 [0.09, 0.24] | 0.11 [0.01, 0.21] | **1,340** [905, 2,445] | 0.14 | n/a |
| Wickets, situation-adjusted | 0.10 [0.06, 0.14] | 0.06 [−0.03, 0.14] | 0.10 [0.00, 0.19] | 7,500 [2,285, ∞] | 0.03 | n/a |
| Dot-ball % (bowl) | 0.51 [0.47, 0.55] | 0.55 [0.48, 0.61] | 0.58 [0.48, 0.67] | 150 [134, 169] | 0.59 | 0.87 |
| Boundaries conceded | 0.54 [0.49, 0.58] | 0.57 [0.49, 0.64] | 0.18 [0.08, 0.27] | 210 [182, 248] | 0.50 | 1.06 |
| Bowling runs saved | 0.17 [0.11, 0.22] | 0.18 [0.05, 0.28] | 0.17 [0.06, 0.28] | 1,450 [900, 3,217] | 0.13 | n/a |
| Share of overs in powerplay | 0.80 [0.77, 0.82] | 0.81 [0.75, 0.85] | 0.80 | 14 | 0.94 | — |
| Share of overs at death | 0.74 [0.72, 0.77] | 0.71 [0.63, 0.76] | 0.41 | 38 | 0.85 | — |
| Share of balls faced in powerplay | 0.77 [0.74, 0.79] | 0.82 [0.77, 0.86] | 0.66 | 27 | 0.89 | — |
| Share of balls faced at death | 0.68 [0.64, 0.72] | 0.77 [0.70, 0.82] | 0.45 | 58 | 0.79 | — |

"Share explained" = r²: strike rate 9.5%, economy 16%, wicket rate 3.8%, batting average 2.4%, batting runs added 3.2% (PR#1's IPL-only value figure, r≈0.20 / 4%, is reproduced: IPL batting value 0.19, bowling 0.18).
Women's balls-to-half-signal: SR 200, boundary % 150, average 420, economy 500, wicket rate 1,820.
"Talent carryover" >1 or "n/a": where reliability is low the ratio is not identified; we do not interpret it. Bowling economy's ≈1.0 means the year-to-year drop is about what noise alone predicts.

### 6.2 Phase and role (60-ball threshold in the split, both seasons; `yoy_repeatability.csv`)
| Split | Men's leagues r | IPL r |
|---|---|---|
| SR powerplay | 0.27 [0.20, 0.33] (1,311) | 0.19 [0.02, 0.34] (315) |
| SR middle | 0.31 [0.25, 0.36] (1,969) | 0.36 [0.25, 0.47] (534) |
| SR death | 0.25 [0.09, 0.40] (208) | 0.29 [0.06, 0.49] (115) |
| Economy powerplay | 0.18 [0.11, 0.24] (1,130) | 0.24 [0.07, 0.37] (270) |
| Economy middle | 0.24 [0.16, 0.31] (1,768) | 0.28 [0.16, 0.37] (382) |
| Economy death | 0.23 [0.13, 0.32] (567) | 0.41 [0.22, 0.56] (167) |
| Wickets powerplay | 0.04 [−0.03, 0.10] | −0.06 [−0.18, 0.04] |
| Wickets middle | 0.05 [−0.01, 0.10] | 0.03 [−0.08, 0.14] |
| Wickets death | 0.05 [−0.03, 0.13] | 0.09 [−0.05, 0.21] |
| SR openers (No. 1–2) | 0.31 [0.24, 0.38] (1,204) | 0.37 [0.25, 0.48] (256) |
| SR No. 3–4 | 0.21 [0.14, 0.26] (1,019) | 0.25 [0.09, 0.36] (241) |
| SR finishers (No. 5–7) | 0.22 [0.13, 0.31] (859) | 0.13 [0.01, 0.25] (212) |

Wicket-taking has no detectable season-to-season repeat within any phase. Openers' strike rates repeat best; finishers' least (IPL finishers 0.13).

### 6.3 Edge kept (`edge_kept_quintiles.csv`) — men's leagues, ≥120 balls both seasons
| Group (fifth of players by season N) | Season N | Season N+1 | Kept |
|---|---|---|---|
| Top-fifth strike rate (434 player-seasons) | +31.2 SR | +12.3 [10.3, 14.2] | **39%** [33, 45] |
| Bottom-fifth strike rate | −16.5 | −2.1 [−3.5, −0.6] | 13% [4, 22] |
| Best-fifth economy (467) | −1.68 runs/over | −0.80 [−0.98, −0.62] | **48%** [38, 56] |
| Worst-fifth economy | +1.11 | +0.38 [0.29, 0.47] | 34% [26, 42] |
| Top-fifth boundary % | +7.4 pts | +3.6 | 49% [42, 54] |
| Top-fifth wicket rate | +0.65 per 24 balls | +0.13 | 21% [15, 26] |
| Top-fifth batting average | +29.2 | +12.2 | 42% [37, 47] |
| Top-fifth batting runs added | +34.4 per 100 | +12.1 | 35% [29, 41] |
| IPL top-fifth SR (116) | +32.4 | +12.4 | 38% [25, 49] |
| IPL best-fifth economy (107) | −1.58 | −0.69 | 44% [24, 58] |
| Women's top-fifth SR (72) | +30.1 | +11.2 | 37% [24, 51] |

### 6.4 Breakout seasons (`breakouts.csv`) — season N beat the player's own earlier record in that competition (≥2 earlier seasons, ≥240 earlier balls)
| | n | Earlier career | Season N | Season N+1 | Jump kept |
|---|---|---|---|---|---|
| SR jump ≥15, men's leagues | 222 | −1.0 | +25.5 | +8.2 | **35%** [24, 45] |
| SR jump ≥15, IPL | 50 | +1.9 | +29.0 | +9.8 | 29% [9, 48] |
| Economy ≥0.75 better, men's leagues | 277 | +0.15 | −1.14 | −0.15 | **24%** [14, 33] |
| Economy ≥0.75 better, IPL | 68 | +0.06 | −1.24 | −0.09 | 11% [−11, 31] |
| Boundary % jump ≥3, men's leagues | 275 | −0.1 | +5.4 | +1.8 | 35% [25, 45] |

### 6.5 Forecast contest (`forecast_contest.csv`, `forecast_tuning.csv`) — tune 2008–19, test 2020–26
% of error removed vs "everyone is league average" (negative = worse than that):
| Men's leagues | Last season as recorded | Career to date | Last season pulled to average | Recent seasons weighted + pulled | + all T20 leagues, 3 yrs |
|---|---|---|---|---|---|
| Strike rate (1,613) | **−43%** [−58, −28] | −5% | +10% [7, 13] | **+13%** [9, 16] | +14% [10, 19] |
| Boundary % | −31% | +4% | +15% | +20% [16, 25] | +22% [17, 26] |
| Dot-ball % | −27% | +6% | +17% | +24% [18, 29] | +24% |
| Batting average | −26% | +13% | +15% | +20% [16, 24] | +20% |
| Batting runs added | −70% | −17% | +5% | +7% [4, 10] | +8% |
| Economy (1,701) | **−32%** [−51, −16] | +4% | +16% | **+24%** [17, 31] | +24% |
| Wicket rate | **−92%** [−107, −77] | −33% | +2% | +3% [1, 5] | +4% [2, 6] |
| Bowling runs saved | −97% | −37% | +1% | +4% [1, 8] | +5% |
IPL only (295 batter / 258 bowler test seasons): SR −36% / +11% [4, 16] / +13% [2, 24]; economy −23% / +32% [19, 43] / +31%; wicket rate −77% / +4% / +5%.
Women's leagues (360 / 439): SR −58% / +17% [8, 25] / +17%; economy −83% / +7% [−3, 17] / +11% [2, 20]; wicket rate −75% / +1% / +1%.
Reversed split (tune 2020–26, test ≤2019), men's leagues: SR −53% → +12%; economy −41% → +17%; wicket rate −85% → +3%. Across 60 metric×scope×split cells (10 metrics × 3 scopes × 2 directions): **"last season as recorded" is worse than league average in 58 of 60** (the two exceptions: women's batting average and boundary % when tested on the thin pre-2020 women's sample, 131 targets); **"weighted + pulled to average" beats last season in all 60**, beats league average in 59 (exception: women's wicket rate, −1%), and beats "last season pulled to average" in 57. Adding every other T20 league (F6) improves on F5 in 49 of 60 cells, by 0–8 points, mostly within the intervals.
Tuned settings (men's leagues, 2008–19): strike rate — weight 0.65 per season back, pull of 400 balls; boundary % 0.8 / 200; dot % 0.65 / 200; economy 0.8 / 300; wicket rate 0.35 / 800 (1,200 when tuned on 2020–26); batting runs added 0.8 / 600.
The ceiling: next season's own luck caps what any forecast can explain. For strike rate at a typical ~220 balls, reliability is ~0.45; the best forecast's 13–14% is roughly a third of that ceiling, consistent with talent itself shifting (carryover ~0.7).

### 6.6 Survivorship (`survivorship.csv`)
Men's leagues, ≥120 balls in season N, competition held a next season: returned with ≥120 balls — bottom-fifth strike rate 44%, other fifths 52–56%; worst-fifth economy 38%, best-fifth 58%. IPL: 57% vs 68–76% (SR), 45% vs 65–73% (economy). Bad seasons are less likely to be followed by a measured season, so every season-to-season figure is computed on survivors.

### 6.7 Cross-league → IPL (`cross_league.csv`, `smat_selection_check.csv`)
Source = matches in the 365 days before the IPL season (≥60 balls); target = that IPL season (≥120 balls).
| Source | SR r | Economy r | SR gap (IPL − source) | Economy gap |
|---|---|---|---|---|
| IPL previous season | 0.24 [0.14, 0.34] (635) | 0.33 [0.23, 0.41] (576) | −1.2 [−2.7, 0.2] | +0.08 [0.01, 0.15] |
| Overseas leagues + Hundred | 0.35 [0.21, 0.46] (201) | 0.30 [0.07, 0.43] (207) | −4.7 [−8.1, −1.2] | +0.22 [0.04, 0.42] |
| T20Is | 0.27 [0.17, 0.38] (345) | 0.37 [0.24, 0.48] (290) | −5.9 [−8.6, −3.2] | +0.08 [−0.07, 0.23] |
| **SMAT** | 0.34 [0.05, 0.54] (93) | **0.09 [−0.13, 0.29]** (117) | **−18.8 [−23.2, −14.5]** | +0.35 [0.08, 0.62] |
SMAT situation-adjusted economy: −0.07 [−0.23, 0.09]. SMAT strike-rate gap for established IPL regulars: −17.8 [−23.0, −13.2] (68); new/fringe: −21.5 [−33.0, −10.7] (25) — the gap is mostly league strength, not selection.
Individual leagues (SR): BBL 0.46 [0.15, 0.66] (68), Hundred 0.44 (33), SA20 0.42 (36, gap −8.7 [−15.0, −1.7]), BPL 0.36 (25), PSL 0.29 (25), CPL 0.28 (60), Blast 0.08 [−0.17, 0.33] (39). All intervals overlap; **we cannot rank individual overseas leagues.**
WPL (women): sources n = 33–54; nothing distinguishable from zero except dot-ball % (WBBL 0.47 [0.22, 0.63], T20IW 0.42); not reported as a finding.

### 6.8 Robustness
- **Threshold** (`yoy_repeatability.csv`, chart07): SR 0.24 (30 balls, 6,141 pairs) → 0.27 (60) → 0.31 (120) → 0.37 (180) → 0.36 (240) → 0.43 (300, 106 pairs). Economy 0.26 → 0.31 → 0.40 → 0.42 → 0.52 → 0.49. Wicket rate 0.10 → 0.13 → 0.19 → 0.23 → 0.21 → 0.29. Balls-to-half-signal is stable across thresholds 30–180 (SR 239–276; boundary % 164–185; economy 324–393; wicket rate 1,245–1,404), which supports the noise model.
- **League** (chart08): SR r for every men's competition with ≥40 pairs lies in −0.02 (NZ Super Smash, 75 pairs) to 0.47 (CSA T20, 53), intervals overlapping the pooled 0.31 except Super Smash. Economy: 0.26–0.58 (CPL 0.58 [0.38, 0.69]). Wicket rate: 0.01 (T20I) to 0.27 (BBL, Super Smash).
- **Era** (`era_robustness.csv`): men's leagues, season N before 2018 vs 2018 on — SR 0.31 / 0.31; economy 0.40 / 0.40; boundary % 0.44 / 0.40; wicket rate 0.21 / 0.19; bowling runs saved 0.26 / 0.12 (the only metric that moved).
- **Metric choice**: situation-adjusting leaves batting unchanged (0.31 → 0.32) but cuts economy 0.40 → 0.29 — about a quarter of economy's repeatability is the phase a bowler is given.
- **Women**: same shape on every core metric except economy (0.28) and boundaries conceded (0.18), which repeat less; women's T20Is (full members) economy −0.04 [−0.18, 0.10] and Hundred women −0.12 — unexplained, scoped out.
- **T20Is (men, full members)**: SR 0.29 [0.13, 0.42] (230), economy 0.34 [0.23, 0.46] (260), wicket rate 0.01 [−0.11, 0.12].

## 7. What the data cannot tell us
- **Why** a season didn't repeat: injury, form, a new coach, a new role, a different home ground, a technical change — none is in a scorecard.
- **Pace vs spin**: Cricsheet does not record bowling type.
- **Age**: no birth dates in the primary data; age curves not attempted.
- **Fielding and wicketkeeping**: not valued.
- **Players who were not picked again.** Season-to-season figures use only players who got ≥120 balls in both seasons; those who had bad seasons return less often (44% vs ~55%). Their next season is unobserved.
- **Opposition and venue quality** beyond the league-season average; chasing vs setting; match situation beyond over and wickets.
- **League strength** is read only from players who cross between leagues; the SMAT gap mixes strength with the different roles players take.
- **Auction prices**: not in Cricsheet. R02 says what last season is worth as evidence, not what franchises paid for it (PR#1 has only 2025 prices).
- **Cricsheet is a transcription**, not the leagues' own record; 386 matches are withheld by Cricsheet; older files lack reduced-overs flags (26 caught and dropped by our own check — there may be others).
- **2020–2026 out-of-sample** means the forecast settings are tested on the impact-player era in the IPL; future rule changes may shift them.

## 8. Files
- `scripts/` — `01_parse.py` (JSON → balls, exclusions), `02_build.py` (seasons, value model, player-match table, exclusion log), `03_repeatability.py`, `04_predict.py`, `05_crossleague.py`, `06_extras.py`, `07_charts.py`, `verify_independent.py`, `r02lib.py`, `run_all.sh`. All run as `python3 -I`, data paths as arguments.
- `data/` — 19 derived CSVs, 1.5 MB total. Raw downloads are held outside the report folder (untrusted input) and are re-downloadable from the URLs above.
- `charts/` — chart01–chart08 PNG drafts.

## 9. Independent re-computation
`scripts/verify_independent.py` re-reads the raw JSON with the standard library only (no pandas/numpy), re-implements exclusions, date-based seasons, aggregation and correlation from scratch, and prints its numbers next to the main pipeline's (`data/verification_independent.csv`):

| Headline | Independent | Main |
|---|---|---|
| Kept matches / deliveries | 9,612 / 2,267,624 | 9,612 / 2,267,624 |
| SR season-to-season, men's leagues / IPL | 0.3083 (2,167) / 0.3283 (581) | identical |
| Economy, men's leagues / IPL | 0.4041 (2,335) / 0.3851 (533) | identical |
| Wicket rate, men's leagues / IPL | 0.1945 / 0.1659 | identical |
| Batting average, men's leagues / IPL | 0.1545 / 0.1900 | identical |
| Split-half SR / economy / wickets / average | 0.2863 / 0.2382 / 0.0705 / 0.0616 | identical |
| Balls to half-signal SR / economy / wickets / average | 268 / 324 / 1,337 / 1,641 | identical |
| Top-fifth SR, N → N+1 | +31.25 → +12.29 | +31.22 → +12.26 (fifths cut by rank vs by quantile; 433 vs 434 players) |
| Forecast SR: last season / weighted + pulled (independently re-tuned to 0.65, 400) | −42.75% / +12.56% | identical |
| SMAT → IPL SR gap | −18.82 (93) | identical |

The first run disagreed on batting average (0.1545 vs 0.1596): the main pipeline was not counting dismissals that happen off a wide (stumped / run out off a wide). Fixed in `02_build.py`; all downstream numbers above are post-fix.
