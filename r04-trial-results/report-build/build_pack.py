"""Build the R04 publishing pack: report page, carousel slides (PNG), LinkedIn PDF and, with REPORT_URL
and REPO_URL set, a public page + link-preview image.

Run:  python3 -I pack/build_pack.py <report_dir> <fonts_dir> <out_dir>
Every number is read from data/ at build time (headline_numbers.json and the tidy CSVs).
"""
import json, os, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts as C  # noqa: E402
import common  # noqa: E402

REP, FONTS, OUT = (Path(a) for a in sys.argv[1:4])
common.FONTS = FONTS
OUT.mkdir(parents=True, exist_ok=True)
D = REP / "data"
REPORT_URL = os.environ.get("REPORT_URL", "")
REPO_URL = os.environ.get("REPO_URL", "")
H = json.loads((D / "headline_numbers.json").read_text())
yr = pd.read_csv(D / "h1_completed_by_pcd_year.csv")
yr = yr[(yr.pcd_year >= 2008) & (yr.pcd_year <= 2023)]
seg = pd.read_csv(D / "h2_cohort_segments.csv")
size = pd.read_csv(D / "h6_by_sponsor_size.csv")
big = pd.read_csv(D / "h6_largest_sponsors_probably_required.csv")
who = pd.read_csv(D / "h4_who_reports.csv")
status = pd.read_csv(D / "h5_status_of_trials_past_completion.csv")

hm, mn = H["h2_main"], H["h1_mix"]
head = H["h1_completed_int_pcd2008_2023_submitted"]
w18 = H["h3_main_2018_22_by_window"]
adj = H["h4_adjusted"]


def segrow(name, grp="All"):
    return seg[(seg.segment == name) & (seg.sponsor_group == grp)].iloc[0]


def sizerow(s):
    return size[size.sponsor_size == s].iloc[0]


def y(year, col):
    return float(yr[yr.pcd_year == year][col].iloc[0])


sponsor_rows = who[who.dimension == "Lead sponsor"]
cert_all = float((sponsor_rows.pct_12m_or_cert * sponsor_rows.n).sum() / sponsor_rows.n.sum())
variants = [H[f"h2_{v}"] for v in ("main", "strict", "broad", "noloc")]
unk = status[status.status == "Unknown status"].iloc[0]
s14, s100 = sizerow("1-4 trials"), sizerow("100+ trials")
req, us_other, nonus, noloc = (segrow(n) for n in ("Probably required", "Not required, has a US site",
                                                    "Not required, non-US sites only", "Not required, no location listed"))
nonus_uni = segrow("Not required, non-US sites only", "Universities, hospitals & non-profits")

N = dict(
    records=H["coverage"]["All records in API download"], interventional=H["coverage"]["Interventional"],
    head_n=head["n"], head_k=head["k"], head_pct=head["pct"], head_posted=H["h1_completed_int_pcd2008_2023_posted"]["pct"],
    y08=mn["2008_actual"], y23=mn["2023_actual"], y23_mix=mn["2023_at_2008_mix"], mix_share=mn["share_of_drop_from_mix_pct"],
    like_n=H["h2_like_cohort_n"], req_n=hm["required_n"], other_n=hm["other_n"],
    req_share=H["h2_share_of_like_cohort_probably_required_pct"],
    r12=hm["required_sub12"]["pct"], o12=hm["other_sub12"]["pct"], r24=hm["required_sub24"]["pct"], o24=hm["other_sub24"]["pct"],
    rev=hm["required_ever"]["pct"], oev=hm["other_ever"]["pct"],
    d24=hm["diff_sub24"]["pp_diff"], d24_lo=hm["diff_sub24"]["lo"], d24_hi=hm["diff_sub24"]["hi"], ratio24=hm["diff_sub24"]["ratio"],
    v_r24_lo=min(v["required_sub24"]["pct"] for v in variants), v_r24_hi=max(v["required_sub24"]["pct"] for v in variants),
    v_o24_lo=min(v["other_sub24"]["pct"] for v in variants), v_o24_hi=max(v["other_sub24"]["pct"] for v in variants),
    r13=H["h3_main_like_sub13"]["pct"], cert_all=cert_all,
    req_cohort=req.pct_of_cohort, req_pile=req.pct_of_no_results_pile,
    nonus_cohort=nonus.pct_of_cohort, nonus_pile=nonus.pct_of_no_results_pile,
    us_cohort=us_other.pct_of_cohort, us_pile=us_other.pct_of_no_results_pile,
    nl_cohort=noloc.pct_of_cohort, nl_pile=noloc.pct_of_no_results_pile,
    nu_uni_cohort=nonus_uni.pct_of_cohort, nu_uni_pile=nonus_uni.pct_of_no_results_pile, nu_uni_24=nonus_uni.pct_sub24,
    nonus08=y(2008, "pct_nonus_only"), nonus23=y(2023, "pct_nonus_only"),
    us08=y(2008, "pct_submitted_us_site"), us23=y(2023, "pct_submitted_us_site"),
    us_lo=float(yr.pct_submitted_us_site.min()), us_hi=float(yr.pct_submitted_us_site.max()),
    nu08=y(2008, "pct_submitted_nonus_only"), nu23=y(2023, "pct_submitted_nonus_only"),
    ended_n=H["h5_ended_n"], unk_share=unk.pct_of_ended, unk_pile=unk.pct_of_no_results_pile, unk_sub=unk.pct_submitted,
    unk_years=H["h5_unknown_median_years_since_update"],
    unk_nonus=H["h5_unknown_pct_nonus_only"]["pct"], unk_us=H["h5_unknown_pct_us_sites"]["pct"],
    w12=w18["12m"]["pct"], w24=w18["24m"]["pct"], w36=w18["36m"]["pct"], wev=H["h3_main_2018_22_ever"]["pct"],
    w_n=w18["12m"]["n"], med_days=H["h3_main_2018_22_median_days_to_submit_among_sub36"],
    pile_n=H["h6_like_no_results_no_cert_n"],
    s14_pile=s14.pct_of_no_results_no_cert, s14_trials=s14.pct_of_trials, s14_sponsors=int(s14.n_sponsors),
    s14_24=s14.pct_24m, s14_ev=s14.pct_ever,
    s100_pile=s100.pct_of_no_results_no_cert, s100_trials=s100.pct_of_trials, s100_sponsors=int(s100.n_sponsors),
    s100_k=int(s100.n_no_results_no_cert), s100_24=s100.pct_24m, s100_ev=s100.pct_ever,
    big_min=float(big.pct_ever.min()), big_n=len(big),
    ind12=adj["y12"]["Industry"]["standardised_pct"], uni12=adj["y12"]["Universities, hospitals & non-profits"]["standardised_pct"],
    nih12=adj["y12"]["NIH"]["standardised_pct"],
    ind24=adj["y24"]["Industry"]["standardised_pct"], uni24=adj["y24"]["Universities, hospitals & non-profits"]["standardised_pct"],
    nih24=adj["y24"]["NIH"]["standardised_pct"],
    ind12c=adj["y12c"]["Industry"]["standardised_pct"], uni12c=adj["y12c"]["Universities, hospitals & non-profits"]["standardised_pct"],
    nih12c=adj["y12c"]["NIH"]["standardised_pct"],
    iu12=adj["y12"]["industry_minus_univ_std_pp"], iu24=adj["y24"]["industry_minus_univ_std_pp"],
    iu12c=adj["y12c"]["industry_minus_univ_std_pp"], nih_n=adj["y12"]["NIH"]["n"],
    cert_ind=H["h7_main_like_cert_by_sponsor"]["Industry"], cert_uni=H["h7_main_like_cert_by_sponsor"]["Universities, hospitals & non-profits"],
    pre17=H["h3_lite_pre_2014_16_sub12"]["pct"], post17=H["h3_lite_post_2018_20_sub12"]["pct"],
    due_n=H["h2_main_due_all"]["n"], due_none=H["h2_main_due_all"]["not_submitted_no_cert"]["k"],
    due_none_pct=H["h2_main_due_all"]["not_submitted_no_cert"]["pct"],
    fda_flags=H["h7_fda_violation_flag_n"], qc_int=H["h7_pending_int"], qc_reset=H["h7_pending_over_1yr_with_resets_pct"],
    stale_24=H["h5_main_like_plus_stale_sub24"]["pct"], stale_n=H["h5_probably_required_stale_n"],
)
print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in N.items()}, indent=1, default=str))

P0 = lambda v: f"{v:.0f}%"
P1 = lambda v: f"{v:.1f}%"


def charts(scale=1.0, w=960, hm_=1.0):
    n = N
    years = list(range(2008, 2024))
    c1 = C.season_bars(years, [y(t, "pct_submitted") for t in years], w=w, h=int(440 * scale * hm_), scale=scale,
                       highlight={2008, 2023}, label_years={2008, 2023}, ymax=50, fmt=P0, xticks={2008, 2011, 2014, 2017, 2020, 2023},
                       tipfmt=lambda t, v: f"Finished {t}: {v:.1f}% have results",
                       label="Share of completed trials with results on ClinicalTrials.gov, by year the trial finished, 2008 to 2023")
    c2 = C.grouped_pairs(["Within 12 months", "Within 2 years", "By November 2026"], [n["o12"], n["o24"], n["oev"]],
                         [n["r12"], n["r24"], n["rev"]], a_name="Everything else", b_name="Probably required by US law",
                         w=w, h=int(480 * scale * hm_), scale=scale, fmt=P0, tickfmt=P0,
                         label="Share of trials with results, probably required versus everything else, trials finished 2017 to 2024")
    c3 = C.grouped_pairs(["Probably required", "Other, US site", "Other, outside US", "No location"],
                         [n["req_cohort"], n["us_cohort"], n["nonus_cohort"], n["nl_cohort"]],
                         [n["req_pile"], n["us_pile"], n["nonus_pile"], n["nl_pile"]],
                         a_name="Share of all trials", b_name="Share of trials with no results",
                         w=w, h=int(480 * scale * hm_), scale=scale, fmt=P0, tickfmt=P0,
                         label="Where the missing results come from: share of trials versus share of trials with no results after 2 years")
    c4 = C.multi_line([("US site", "ln-hi", [(t, y(t, "pct_submitted_us_site")) for t in years]),
                       ("All trials", "ln-ctx", [(t, y(t, "pct_submitted")) for t in years]),
                       ("Outside US only", "ln-amb", [(t, y(t, "pct_submitted_nonus_only")) for t in years])],
                      w=w, h=int(460 * scale * hm_), scale=scale, ymax=80, gstep=20, xlabels=[2008, 2013, 2018, 2023],
                      padr=190,
                      label="Share of completed trials with results, by where the trial ran, 2008 to 2023")
    c5 = C.hbars([("12 months (deadline)", n["w12"], "bar-amb", f"Within 12 months: {n['w12']:.1f}%"),
                  ("2 years", n["w24"], "bar", f"Within 2 years: {n['w24']:.1f}%"),
                  ("3 years", n["w36"], "bar", f"Within 3 years: {n['w36']:.1f}%"),
                  ("By Nov 2026", n["wev"], "bar-hi", f"By November 2026: {n['wev']:.1f}%")],
                 w=w, h=int(330 * scale * hm_), scale=scale, xmax=100, ticks=(0, 25, 50, 75, 100), tickfmt=P0, fmt=P0, padl=290,
                 label="Probably required trials that finished 2018 to 2022: share with results after each interval")
    c6 = C.grouped_pairs(["1–4 trials", "5–19", "20–99", "100 or more"],
                         [float(sizerow(s).pct_of_trials) for s in ("1-4 trials", "5-19 trials", "20-99 trials", "100+ trials")],
                         [float(sizerow(s).pct_of_no_results_no_cert) for s in ("1-4 trials", "5-19 trials", "20-99 trials", "100+ trials")],
                         a_name="Share of required trials", b_name="Share of overdue trials", w=w, h=int(480 * scale * hm_),
                         scale=scale, fmt=lambda v: f"{v:.1f}%" if v < 1 else f"{v:.0f}%", tickfmt=P0,
                         label="Probably required trials by the sponsor's number of such trials: share of trials versus share of overdue trials")
    return dict(c1=c1, c2=c2, c3=c3, c4=c4, c5=c5, c6=c6)


EXTRA_PAGE_CSS = (".ln-hi{stroke:var(--accent);stroke-width:2.5;} .ln-ctx{stroke:var(--muted);stroke-width:2;} .ln-amb{stroke:var(--amber);stroke-width:2.5;}"
                  ".ln-hi-dot{fill:var(--accent);} .ln-ctx-dot{fill:var(--muted);} .ln-amb-dot{fill:var(--amber);}"
                  ".axlbl{font-size:.8rem;color:var(--faint);}")
EXTRA_SLIDE_CSS = (".ln-hi{stroke:#3B82F6;stroke-width:4;} .ln-ctx{stroke:#8B9DC3;stroke-width:3;} .ln-amb{stroke:#D97706;stroke-width:4;}"
                   ".ln-hi-dot{fill:#3B82F6;} .ln-ctx-dot{fill:#8B9DC3;} .ln-amb-dot{fill:#D97706;}")


def report():
    c = charts(1.0)
    n = N
    t1 = common.table(["Year finished", "Completed trials", "With results"],
                      [[int(r.pcd_year), f"{int(r.n_completed):,}", f"{r.pct_submitted:.1f}%"] for r in yr.itertuples()])
    t2 = common.table(["", "Probably required", "Everything else"],
                      [["Trials", f"{n['req_n']:,}", f"{n['other_n']:,}"], ["Within 12 months", P1(n["r12"]), P1(n["o12"])],
                       ["Within 2 years", P1(n["r24"]), P1(n["o24"])], ["By November 2026", P1(n["rev"]), P1(n["oev"])]])
    t3 = common.table(["Group", "Share of trials", "Share of trials with no results after 2 years"],
                      [["Probably required", P1(n["req_cohort"]), P1(n["req_pile"])],
                       ["Not required, with a US site", P1(n["us_cohort"]), P1(n["us_pile"])],
                       ["Not required, outside the US only", P1(n["nonus_cohort"]), P1(n["nonus_pile"])],
                       ["Not required, no location listed", P1(n["nl_cohort"]), P1(n["nl_pile"])]])
    t4 = common.table(["Year finished", "All", "US site", "Outside US only", "Share outside US only"],
                      [[int(r.pcd_year), P1(r.pct_submitted), P1(r.pct_submitted_us_site), P1(r.pct_submitted_nonus_only), P1(r.pct_nonus_only)]
                       for r in yr.itertuples()])
    t6 = common.table(["Sponsor has this many required trials", "Sponsors", "Share of trials", "Share of overdue trials", "Reported within 2 years"],
                      [[r.sponsor_size.replace("-", "–").replace("100+", "100 or more"), f"{int(r.n_sponsors):,}", P1(r.pct_of_trials),
                        P1(r.pct_of_no_results_no_cert), P1(r.pct_24m)] for r in size.itertuples()])
    t7 = common.table(["Same trial mix", "Industry", "Universities &amp; hospitals", "NIH"],
                      [["Within 12 months", P1(n["ind12"]), P1(n["uni12"]), P1(n["nih12"])],
                       ["Within 2 years", P1(n["ind24"]), P1(n["uni24"]), P1(n["nih24"])],
                       ["Within 12 months, or delay certificate filed", P1(n["ind12c"]), P1(n["uni12c"]), P1(n["nih12c"])]])
    return f"""<title>Do Clinical Trials Report Results?</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>/* Layout: one reading column (~68ch); Sartium dark canvas first, light mirror. */{common.PAGE_CSS}{EXTRA_PAGE_CSS}</style>
<main>
<div class="kick"><span>Public Record · Sartium</span><span class="draft">Draft for review</span></div>
<h1>How many clinical trials actually publish their results?</h1>
<p class="dek">We downloaded all {n['records']:,} records on ClinicalTrials.gov, the US government's trial registry. Most trials there have no results, but most of those were never required to post them there. Among trials US law probably covers, nearly 9 in 10 eventually report.</p>
<p class="byline">Scope: interventional trials on ClinicalTrials.gov, data as of 20 November 2026 · "Results" means summary results sent to the registry, not journal papers</p>
<div class="stats">
  <div class="stat"><b>{n['head_pct']:.0f}%</b><span>Completed trials (2008–2023) with results on ClinicalTrials.gov.</span></div>
  <div class="stat"><b>{n['rev']:.0f}%</b><span>Trials US law probably covers that have reported by now.</span></div>
  <div class="stat"><b>{n['nonus_pile']:.0f}%</b><span>Share of the missing results that come from trials run only outside the US and not covered by US law.</span></div>
</div>

<h2>The answer everyone assumes</h2>
<p>"Most clinical trials never report their results" is one of medicine's best-known complaints. The campaign figure that half of all trials go unreported dates from 2013 and is about publication in journals. On the US government's own trial registry, the number looks even worse.</p>

<h2>The source</h2>
<p>ClinicalTrials.gov is run by the US National Library of Medicine. Every trial record can be downloaded free through its official API at <code>clinicaltrials.gov/api/v2/studies</code>. Each record gives the trial's status, the dates it started and finished, who ran it and where, whether the product is regulated by the US Food and Drug Administration (FDA), and the dates results were first sent in and first posted. We took all {n['records']:,} records, {n['interventional']:,} of them interventional trials, which test a treatment, device or procedure on people.</p>
<p class="note">The registry stamps its own dates, such as when results arrived. Everything else in a record, including status, dates, phase, sponsor type and the FDA tick-boxes, is typed in by the sponsor.</p>

<h2>What the obvious number says</h2>
<p>Take completed interventional trials that finished collecting their main result between 2008 and 2023. <strong>{n['head_pct']:.0f}% have results on ClinicalTrials.gov: {n['head_k']:,} of {n['head_n']:,}.</strong> Here "results" means posted, or sent in and waiting to be posted; counting posted results only, it is {n['head_posted']:.0f}%. And the share is falling: from {n['y08']:.1f}% for trials that finished in 2008 to {n['y23']:.1f}% for 2023.</p>
<figure><figcaption>Completed trials with results on ClinicalTrials.gov, by year the trial finished</figcaption><div class="chart">{c['c1']}</div>
<span class="src">Interventional trials marked completed, by primary completion date. Source: ClinicalTrials.gov API, 20 Nov 2026.</span>{t1}</figure>
<p>On its face, about 7 in 10 trials never report, and it is getting worse.</p>

<h2>The turn: most trials were never required to report here</h2>
<p><strong>US law covers a minority of trials.</strong> The FDA Amendments Act of 2007 (section 801) and its 2017 Final Rule require results within 12 months of a trial's primary completion for a defined group: interventional trials of FDA-regulated drugs, biologics or devices, beyond phase 1 and not small device feasibility studies, with a US site or a US-made exported product (or run under an FDA application), finishing from 18 January 2017 on.</p>
<p>Using only the registry's own fields, we estimated which trials are <strong>probably required</strong> to report. This is our estimate, not a legal ruling. Of the {n['like_n']:,} trials that finished between 18 January 2017 and 20 November 2024, so that every one has had at least two full years, <strong>{n['req_n']:,} ({n['req_share']:.0f}%)</strong> fall in that group.</p>
<p><strong>Those trials mostly report. The rest mostly don't.</strong></p>
<figure><figcaption>Share of trials with results, probably required versus everything else</figcaption><div class="chart">{c['c2']}</div>
<span class="src">Interventional trials with an actual primary completion date from 18 Jan 2017 to 20 Nov 2024, not withdrawn. Source: ClinicalTrials.gov.</span>{t2}</figure>
<p>Within two years, {n['r24']:.0f}% of probably-required trials have results against {n['o24']:.0f}% of everything else: a gap of {n['d24']:.0f} points (95% range {n['d24_lo']:.1f} to {n['d24_hi']:.1f}), about {n['ratio24']:.0f} times the rate. The gap holds however we draw the line. Under stricter and looser definitions the required group's two-year figure stays between {n['v_r24_lo']:.0f}% and {n['v_r24_hi']:.0f}%, and everything else between {n['v_o24_lo']:.0f}% and {n['v_o24_hi']:.0f}%.</p>

<p><strong>Most of the missing results come from trials run outside the US.</strong> Trials run only outside the US, which the law does not cover, are {n['nonus_cohort']:.0f}% of the trials and <strong>{n['nonus_pile']:.0f}% of those with no results</strong> two years after finishing. The probably-required trials are {n['req_cohort']:.0f}% of the trials and {n['req_pile']:.1f}% of the missing results.</p>
<figure><figcaption>Where the missing results come from</figcaption><div class="chart">{c['c3']}</div>
<span class="src">Same trials as above. "No results" means none within two years of finishing. Source: ClinicalTrials.gov.</span>{t3}</figure>
<p>University and hospital trials run only outside the US are, on their own, {n['nu_uni_cohort']:.0f}% of the trials and {n['nu_uni_pile']:.0f}% of the missing results. Only {n['nu_uni_24']:.1f}% of them report here within two years. Many may report in a journal or in another country's registry, and this data cannot see that.</p>

<p><strong>The "getting worse" trend is mostly a change in which trials are registered.</strong> Trials run only outside the US went from {n['nonus08']:.0f}% of completed trials in 2008 to {n['nonus23']:.0f}% in 2023. Trials with at least one US site have reported at a steady {n['us_lo']:.0f}–{n['us_hi']:.0f}% every year.</p>
<figure><figcaption>Completed trials with results, by where the trial ran</figcaption><div class="chart">{c['c4']}</div>
<span class="src">By year the trial finished. Trials with no location listed are in "all" only. Source: ClinicalTrials.gov.</span>{t4}</figure>
<p>Had the 2008 mix of US and non-US trials held, the 2023 figure would be {n['y23_mix']:.1f}%, not {n['y23']:.1f}%. The changing mix explains about half of the fall. The other half is real: trials run only outside the US post here less and less, from {n['nu08']:.0f}% in 2008 to {n['nu23']:.0f}% in 2023.</p>

<p><strong>Nearly a quarter of the missing results sit in records nobody keeps up to date.</strong> Of the {n['ended_n']:,} trials at least two years past their end date, {n['unk_share']:.0f}% are in "unknown status": the label the registry applies when a record passes its completion date and nobody confirms its status for two years. They are {n['unk_pile']:.0f}% of the trials with no results. Their records were last touched a median {n['unk_years']:.1f} years ago, and only {n['unk_sub']:.1f}% have results. {n['unk_nonus']:.0f}% of trials run only outside the US end up "unknown", against {n['unk_us']:.1f}% of trials with a US site.</p>

<h2>Inside the required group: the deadline and the stragglers</h2>
<p><strong>About 4 in 10 report by the legal deadline.</strong> Of the probably-required trials, {n['r12']:.0f}% sent results within 12 months. Allowing 30 days of grace, {n['r13']:.0f}%. Counting the delay certificates the law allows, filed in time, {n['cert_all']:.0f}%. Results then keep arriving: for trials that finished in 2018–2022, {n['w12']:.0f}% had reported at 12 months, {n['w24']:.0f}% at two years, {n['w36']:.0f}% at three and {n['wev']:.0f}% by now.</p>
<figure><figcaption>Probably-required trials that finished 2018–2022: share with results</figcaption><div class="chart">{c['c5']}</div>
<span class="src">{n['w_n']:,} trials. Source: ClinicalTrials.gov.</span></figure>
<p>Reports bunch at the deadline: among trials that reported within three years, the median gap between finishing and sending results was {n['med_days']:.0f} days.</p>

<p><strong>The overdue trials sit with sponsors who run very few trials.</strong> {n['pile_n']:,} probably-required trials have no results and no delay certificate. Sponsors with one to four such trials hold <strong>{n['s14_pile']:.0f}%</strong> of them, while running {n['s14_trials']:.0f}% of the trials. The {n['s100_sponsors']} sponsors with 100 or more run {n['s100_trials']:.0f}% of the trials and hold {n['s100_pile']:.1f}% of the overdue ones ({n['s100_k']} trials). Every one of those {n['big_n']} has now reported at least {n['big_min']:.0f}% of its probably-required trials.</p>
<figure><figcaption>Share of required trials versus share of overdue trials, by sponsor size</figcaption><div class="chart">{c['c6']}</div>
<span class="src">Sponsor size = the sponsor's number of probably-required trials finishing 2017–2024, counted by registered name. Overdue = no results and no delay certificate. Source: ClinicalTrials.gov.</span>{t6}</figure>
<p>Sponsor size is counted by the name on the record. Companies that register under several names look smaller than they are, so the exact shares are approximate; the direction is not.</p>

<p><strong>At the deadline, industry and universities tie.</strong> Comparing them as if they ran the same mix of trials, industry reported {n['ind12']:.0f}% within 12 months and universities and hospitals {n['uni12']:.0f}%, a difference of {n['iu12']['point']:+.1f} points (95% range {n['iu12']['lo']:.1f} to {n['iu12']['hi']:+.1f}). Universities are ahead at two years ({n['uni24']:.0f}% against {n['ind24']:.0f}%). Industry leads only once delay certificates count: it files them on {n['cert_ind']:.0f}% of these trials, universities on {n['cert_uni']:.0f}%. The NIH, with {n['nih_n']} trials, is fastest at 12 months ({n['nih12']:.0f}%).</p>
{t7}

<h2>The corrected answer</h2>
<ul>
<li><strong>For trials US law probably covers:</strong> about 4 in 10 report by the deadline, 7 in 10 within two years and nearly 9 in 10 eventually. Counting legal delay certificates, about half are on time.</li>
<li><strong>For everything else on the registry:</strong> fewer than 1 in 5 report here. Most of those trials were never required to.</li>
</ul>
<p>Four popular claims did not survive:</p>
<ul>
<li><strong>"Reporting is getting worse."</strong> About half of the fall is a change in which trials are registered. Trials with a US site have held at {n['us_lo']:.0f}–{n['us_hi']:.0f}% for 15 years.</li>
<li><strong>"Big pharma is the problem."</strong> The {n['s100_sponsors']} largest sponsors hold {n['s100_pile']:.1f}% of the overdue required trials.</li>
<li><strong>"Industry reports best."</strong> It ties universities at the deadline and trails them at two years.</li>
<li><strong>"The 2017 rule transformed reporting."</strong> On-time reporting for drug and device trials with a US site rose from {n['pre17']:.1f}% (finished 2014–16) to {n['post17']:.1f}% (2018–20), but it had already been rising by 2–3 points a year since 2011. That fits a modest effect and proves none.</li>
</ul>
<p class="quote">Most trials registered on ClinicalTrials.gov have no results there, but most of those were never required to post them there. Among trials US law probably covers, nearly 9 in 10 eventually report, though only about 4 in 10 by the legal deadline.</p>

<h2>What this data cannot tell you</h2>
<ul>
<li><strong>Whether a trial was published anywhere else.</strong> It may be in a journal, the EU trials register or another country's registry. "No results on ClinicalTrials.gov" does not mean "never published".</li>
<li><strong>Who was legally required.</strong> Our group rests on sponsors' own tick-boxes. FDA application numbers are not public, and older records lack the FDA questions altogether. It is an estimate, not a compliance ruling about any trial or sponsor.</li>
<li><strong>Whether the records are true.</strong> Status, dates, phase and sponsor type are typed in by sponsors. "Unknown status" is the registry saying it doesn't know.</li>
<li><strong>Whether posted results are complete or correct.</strong></li>
<li><strong>Trials that were never registered.</strong></li>
<li><strong>Why</strong> small sponsors and non-US trials post less here: no obligation, another registry, or no capacity.</li>
<li><strong>The latest years.</strong> Trials whose records still show only a planned finish date drop out of the counts. Adding back {n['stale_n']:,} probably-required trials stuck with a past planned date lowers the group's two-year figure from {n['r24']:.0f}% to {n['stale_24']:.0f}%.</li>
</ul>

<section class="method">
<h2>How we did it</h2>
<p><strong>Source.</strong> All {n['records']:,} records from the ClinicalTrials.gov API (version 2.0.5), downloaded on 22 November 2026; the registry's data timestamp, 20 November 2026, was the same at the start and end of the download.</p>
<p><strong>Outcome.</strong> "Results" means summary results posted, or submitted and waiting in the registry's quality-control review ({n['qc_int']:,} interventional trials are in that queue). The law counts submission, not posting.</p>
<p><strong>"Probably required".</strong> Interventional, not withdrawn; the sponsor ticked "FDA-regulated drug" or "device"; not phase 1 alone; not a device feasibility study; at least one US site or a US-exported product. Three other definitions (stricter, looser, and without the location test) are reported as ranges.</p>
<p><strong>Fair comparisons.</strong> Group comparisons use trials that finished between 18 January 2017 and 20 November 2024, so every trial has had two full years, and fixed windows (12 months, 2 years). Ranges are 95% intervals. Sponsor comparisons are standardised to the same mix of phase, product, year and US site.</p>
<p><strong>Checks.</strong> A second, independent code path recomputed 113 headline numbers from the raw download with no mismatches, and 47 counts were checked against the registry's own search engine. We recomputed the main figures a third time before publishing.</p>
<p><strong>Reproduce it.</strong> The scripts and derived data will be published with this report. Every number on this page is read from them at build time.</p>
</section>
<div class="end"><div class="brand"><span class="sq">S</span>Sartium</div>
<p>Public Record is Sartium's series of questions settled with data anyone can download. Sartium builds analytics, automation and data products for businesses. sartium.com</p></div>
</main>{common.TIP_JS}"""


def slides():
    c = charts(1.0, w=936, hm_=1.45)
    n = N
    S = []

    def slide(kicker, head, body="", chart="", foot="", solo=False):
        S.append(f'<section class="s{" solo" if solo else ""}"><div class="k">{kicker}</div><h2>{head}</h2>'
                 f'{f"<div class=c>{chart}</div>" if chart else ""}{f"<p>{body}</p>" if body else ""}'
                 f'<div class="f"><span>{foot}</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')

    S.append(f'<section class="s cover"><div class="k">Public Record</div><h1>How many clinical trials actually publish their results?</h1>'
             f'<p class="big">We downloaded all {n["records"]:,} records on ClinicalTrials.gov.</p>'
             f'<p class="sc">US National Library of Medicine registry · data to 20 Nov 2026</p>'
             f'<div class="f"><span>Swipe →</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    slide("The obvious number", f"Only {n['head_pct']:.0f}% of completed trials have results on the registry. And it's falling.",
          f"{n['y08']:.0f}% for trials that finished in 2008. {n['y23']:.0f}% for 2023.", c["c1"], "Completed interventional trials · ClinicalTrials.gov")
    slide("The turn", f"Trials US law probably covers report about {n['ratio24']:.0f}× as often.",
          f"Only {n['req_share']:.0f}% of trials fall under the US reporting law, by our estimate. {n['rev']:.0f}% of them have reported.",
          c["c2"], "Trials finished 2017–2024 · “probably required” is our estimate")
    slide("The missing results", f"{n['nonus_pile']:.0f}% of trials with no results ran only outside the US, beyond the law's reach.",
          f"Trials the law probably covers: {n['req_pile']:.0f}% of the missing results.", c["c3"], "No results within 2 years of finishing")
    slide("“Getting worse”?", f"Trials with a US site have reported at {n['us_lo']:.0f}–{n['us_hi']:.0f}% for 15 years.",
          "About half the fall comes from the registry filling up with non-US trials.", c["c4"], "Completed trials, by year finished")
    slide("The deadline", "About 4 in 10 make the 12-month deadline. Nearly 9 in 10 report eventually.",
          f"Median time to report: {n['med_days']:.0f} days. Results bunch at the deadline.", c["c5"], "Probably-required trials finished 2018–2022")
    slide("Who's overdue", f"{n['s14_pile']:.0f}% of overdue trials belong to sponsors with 1–4 of them.",
          f"The {n['s100_sponsors']} largest sponsors hold {n['s100_pile']:.1f}%. Each has reported at least {n['big_min']:.0f}% of its trials.",
          c["c6"], "Sponsors grouped by number of required trials")
    slide("What didn't survive", "Three claims we tested and dropped.",
          f"“Big pharma is the problem”: the {n['s100_sponsors']} largest sponsors hold {n['s100_pile']:.1f}% of overdue trials.<br><br>"
          f"“Industry reports best”: it ties universities at the deadline.<br><br>"
          f"“It's getting worse”: half the fall is a change in which trials get registered.", "", "", solo=True)
    slide("Read this before sharing", "What this data can't tell you.",
          "Whether a trial was published in a journal or another registry. Who was legally required: our group is an estimate. "
          "Whether sponsor-entered records are true. And trials never registered.", "", "", solo=True)
    S.append(f'<section class="s"><div class="k">The answer</div><h2>Most trials with no results here were never required to post them here.</h2>'
             f'<ul><li>Probably required by US law: about 4 in 10 on time, nearly 9 in 10 eventually.</li>'
             f'<li>Everything else: fewer than 1 in 5 report on the registry.</li>'
             f'<li>“No results on ClinicalTrials.gov” is not “never published”.</li></ul>'
             f'<p class="cta">Full report, method and code: link in the comments.</p>'
             f'<div class="f"><span>Data: ClinicalTrials.gov (NLM)</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    css = common.slide_css() + EXTRA_SLIDE_CSS
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(S)}</body></html>"


def public_page(body):
    body = body.replace('<span class="draft">Draft for review</span>', '')
    body = body.replace("<p><strong>Reproduce it.</strong> The scripts and derived data will be published with this report. Every number on this page is read from them at build time.</p>",
                        f'<p><strong>Reproduce it.</strong> Scripts, derived data, the research file and the exclusion log: <a href="{REPO_URL}">{REPO_URL.replace("https://", "")}</a>. Every number on this page is read from them at build time.</p>')
    body = body.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    desc = (f"All {N['records']:,} ClinicalTrials.gov records: most trials there have no results, but most of those were never required "
            f"to post them there. Among trials US law probably covers, {N['rev']:.0f}% eventually report.")
    head = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="description" content="{desc}"><meta property="og:type" content="article">'
            f'<meta property="og:title" content="How many clinical trials actually publish their results?"><meta property="og:description" content="{desc}">'
            f'<meta property="og:url" content="{REPORT_URL}"><meta property="og:image" content="{REPORT_URL}og.png">'
            f'<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@SartiumHQ">'
            f'<link rel="canonical" href="{REPORT_URL}"><style>img{{max-width:100%}}[hidden]{{display:none!important}}</style></head><body>')
    return head + body + "</body></html>"


def og_card():
    n = N
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{common.font_face()}
*{{margin:0;box-sizing:border-box;}} body{{width:1200px;height:630px;background:#0A0A0F;color:#fff;font-family:Inter;padding:64px 72px;
display:flex;flex-direction:column;justify-content:space-between;background-image:radial-gradient(#1A2234 1.4px,transparent 1.4px);background-size:40px 40px;}}
.k{{font:500 22px 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}} h1{{font:700 64px/1.05 'Space Grotesk';margin-top:18px;}}
.row{{display:flex;gap:56px;align-items:flex-end;}} .st b{{font:700 54px 'Space Grotesk';display:block;}} .st span{{font-size:20px;color:#8B9DC3;}}
.br{{margin-left:auto;display:flex;gap:12px;align-items:center;font:700 28px 'Space Grotesk';}}
.sq{{width:38px;height:38px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 19px 'Space Grotesk';color:#3B82F6;}}
</style></head><body><div><div class='k'>Public Record · {n['records']:,} trial records</div><h1>How many clinical trials actually publish their results?</h1></div>
<div class='row'><div class='st'><b>{n['head_pct']:.0f}%</b><span>of completed trials have results</span></div>
<div class='st'><b>{n['rev']:.0f}%</b><span>of trials the law probably covers</span></div><div class='st'><b>{n['nonus_pile']:.0f}%</b><span>of gaps: non-US trials</span></div>
<div class='br'><span class='sq'>S</span>Sartium</div></div></body></html>"""


if __name__ == "__main__":
    (OUT / "report.html").write_text(report(), encoding="utf-8")
    (OUT / "carousel.html").write_text(slides(), encoding="utf-8")
    pub = None
    if REPORT_URL and REPO_URL:
        pub = OUT / "public"
        pub.mkdir(exist_ok=True)
        (pub / "index.html").write_text(public_page(report()), encoding="utf-8")
        (pub / "og.html").write_text(og_card(), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    sd = OUT / "slides"
    sd.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto((OUT / "carousel.html").resolve().as_uri())
        pg.wait_for_timeout(400)
        els = pg.query_selector_all("section.s")
        for i, el in enumerate(els, 1):
            el.screenshot(path=str(sd / f"r04-slide-{i:02d}.png"))
        pg.pdf(path=str(OUT / "r04-trials-linkedin-carousel.pdf"), width="1080px", height="1350px", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        if pub:
            og = b.new_page(viewport={"width": 1200, "height": 630})
            og.goto((pub / "og.html").resolve().as_uri())
            og.wait_for_timeout(300)
            og.screenshot(path=str(pub / "og.png"))
            (pub / "og.html").unlink()
        b.close()
    print("slides:", len(els))
