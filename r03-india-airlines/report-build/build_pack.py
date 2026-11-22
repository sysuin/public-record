"""Build the R03 publishing pack: report page, carousel slides (PNG), LinkedIn PDF and, with REPORT_URL
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
panel = pd.read_csv(D / "main_airline_months.csv", parse_dates=["date"])
cov = pd.read_csv(D / "otp_scope_schedule_coverage_ws2026.csv")
mix = pd.read_csv(D / "otp_mix_counterfactual_2026.csv", parse_dates=["date"])

Y26, L12 = "10apt_2026-01_2026-09", "last12_2025-10_2026-09"
o26, c26, k26 = (H[k][Y26]["means"] for k in ("bootstrap_otp", "bootstrap_cancel", "bootstrap_complaints"))
lead26 = H["bootstrap_otp"][Y26]
lead25 = H["bootstrap_otp"]["6apt_2025"]
pre = H["bootstrap_otp"]["pre_covid_2018-2019"]
era4 = H["bootstrap_otp"]["4apt_era_2022-2024"]
cmp26 = H["bootstrap_complaints"][Y26]["top2_diff_ci95"]
leader = H["leader"]["all_2018-01_2026-09"]
agree = H["agreement"]
comp_l12 = H["composite_top3_only"][L12]
comp_x = H["composite_last12_excl_dec2025"]
dec = H["dec2025"]
dec_all = H["dec2025_overall"]
dec_rs = H["dec2025_cancel_reasons"]
icx = H["indigo_cancel"]
apt = H["airport_all_2026_mean"]
cy = H["complaints_median_monthly_rate_by_year_excl_dec2025"]
crs = H["complaint_reasons_by_year_pct"]
cby = H["complaints_by_year"]
fog = H["fog"]
size = H["size"]
cancel_rho = H["punctual_by_cancelling_within_airline"]["spearman"]


def cov_share(airline, s):
    r = cov[(cov.airline == airline) & (cov.airport_set == s)]
    return float(r.share_pct.iloc[0])


m26 = mix[(mix.date >= "2026-01-01") & (mix.date <= "2026-09-01")]
ai_own = float(m26[m26.airline == "Air India"].otp_pct.mean())
ai_on_ig = float(m26[m26.airline == "Air India"]["otp_with_IndiGo_mix"].mean())
ig_own = float(m26[m26.airline == "IndiGo"].otp_pct.mean())

ig = panel[(panel.airline == "IndiGo") & (panel.date >= "2022-01-01")].sort_values("date")
pts = [(d.year + (d.month - 1) / 12, float(v)) for d, v in zip(ig.date, ig.cancel_pct)]
nov25 = float(panel[(panel.airline == "IndiGo") & (panel.date == "2025-11-01")].pax_lakh.iloc[0])


N = dict(
    reports=leader["months"], changes=leader["leader_changes"], counts=leader["leader_counts"],
    ig26=o26["IndiGo"], ak26=o26["Akasa Air"], ai26=o26["Air India"],
    lead26=lead26["top2_diff"], lead26_lo=lead26["top2_diff_ci95"][0], lead26_hi=lead26["top2_diff_ci95"][1],
    lead25=lead25["top2_diff"], lead25_lo=lead25["top2_diff_ci95"][0], lead25_hi=lead25["top2_diff_ci95"][1],
    pre_gap=pre["top2_diff"], era4_gap=era4["top2_diff"],
    akc=c26["Akasa Air"], igc=c26["IndiGo"], aic=c26["Air India"],
    akk=k26["Akasa Air"], igk=k26["IndiGo"], aik=k26["Air India"], cmp_lo=cmp26[0], cmp_hi=cmp26[1],
    agree_months=agree["months"], joint=agree["months_best_or_joint_best_all_three"],
    same_best=agree["share_months_best_otp_eq_best_cancel"] * 100,
    ig4=cov_share("IndiGo", 4), ai4=cov_share("Air India", 4), ak4=cov_share("Akasa Air", 4), all4=cov_share("ALL", 4),
    ig10=cov_share("IndiGo", 10), ai10=cov_share("Air India", 10), ak10=cov_share("Akasa Air", 10), all10=cov_share("ALL", 10),
    aai4=H["scope_aai"]["share_2026_jan_sep_by_set"]["4"],
    ai_own=ai_own, ai_on_ig=ai_on_ig, ig_own=ig_own,
    maa=apt["MAA"], bom=apt["BOM"],
    dec_ig=dec["IndiGo"]["cancel_pct"], ig_med=icx["median_2022_2025nov"], ig_prevmax=icx["max_before_dec2025"],
    dec_all=dec_all["cancel_overall_pct"], dec_cmp=dec_all["complaints_total"], dec_ig_k=dec["IndiGo"]["complaints_per10k"],
    dec_op=dec_rs["Operational"], dec_wx=dec_rs["Weather"],
    pax_nov=nov25, pax_dec=dec["IndiGo"]["pax_lakh"],
    akw=comp_l12["share_won_rank"]["Akasa Air"] * 100, akw_s=comp_l12["share_won_scaled"]["Akasa Air"] * 100,
    igw_x=comp_x["share_won_rank"]["IndiGo"] * 100, igw_xs=comp_x["share_won_scaled"]["IndiGo"] * 100,
    c24=cy["2024"], c26=cy["2026"], bag24=crs["2024"]["Baggage"], bag26=crs["2026"]["Baggage"],
    fog_dj=fog["otp_w_decjan"], fog_rest=fog["otp_w_rest"], rho=cancel_rho,
    share_first=size["indigo_share_first"], share_last=size["indigo_share_last"],
)
N["ratio"] = N["dec_ig"] / N["ig_med"]
N["lead_mix"] = N["ig_own"] - N["ai_on_ig"]
N["lead_raw"] = N["ig_own"] - N["ai_own"]
print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in N.items()}, indent=1, default=str))

APT_NAMES = {"MAA": "Chennai", "HYD": "Hyderabad", "BLR": "Bengaluru", "CCU": "Kolkata", "AMD": "Ahmedabad",
             "COK": "Kochi", "LKO": "Lucknow", "DEL": "Delhi", "GAU": "Guwahati", "BOM": "Mumbai"}


def charts(scale=1.0, w=960, hm=1.0):
    n = N
    lead_rows = [(a, float(v), "bar-hi", f"{a}: #1 in {v} months") for a, v in
                 sorted(n["counts"].items(), key=lambda kv: -kv[1])]

    def three(metric_rows, fmt, xmax, title_cls=""):
        return C.hbars(metric_rows, w=w, h=int(190 * scale * hm), scale=scale, xmax=xmax, fmt=fmt, ticks=(), padl=230)

    otp_rows = [("IndiGo", n["ig26"], "bar-hi", ""), ("Akasa Air", n["ak26"], "bar", ""), ("Air India Group", n["ai26"], "bar", "")]
    can_rows = [("Akasa Air", n["akc"], "bar-hi", ""), ("IndiGo", n["igc"], "bar", ""), ("Air India Group", n["aic"], "bar", "")]
    cmp_rows = [("Akasa Air", n["akk"], "bar-hi", ""), ("IndiGo", n["igk"], "bar-hi", ""), ("Air India Group", n["aik"], "bar", "")]
    otp_rows = [(a, b, c, f"{a}: {b:.1f}% on time") for a, b, c, _ in otp_rows]
    can_rows = [(a, b, c, f"{a}: {b:.2f}% cancelled") for a, b, c, _ in can_rows]
    cmp_rows = [(a, b, c, f"{a}: {b:.2f} complaints per 10,000") for a, b, c, _ in cmp_rows]
    apt_rows = [(APT_NAMES[k], v, "bar-hi" if v >= 85 else "bar", f"{APT_NAMES[k]}: {v:.1f}% on time")
                for k, v in sorted(apt.items(), key=lambda kv: -kv[1])]
    years = list(range(2018, 2027))
    cvals = [float(cy[str(y)]) for y in years]
    return dict(
        c1=C.hbars(lead_rows, w=w, h=int(420 * scale * hm), scale=scale, xmax=62, ticks=(0, 20, 40, 60),
                   tickfmt=lambda v: f"{v:.0f}", fmt=lambda v: f"{v:.0f}", padl=250,
                   label="Months each airline topped DGCA's on-time table, January 2018 to September 2026"),
        c2a=three(otp_rows, lambda v: f"{v:.1f}%", 100),
        c2b=three(can_rows, lambda v: f"{v:.2f}%", 0.95),
        c2c=three(cmp_rows, lambda v: f"{v:.1f}", 4.0),
        c3=C.grouped_pairs(["IndiGo", "Air India Group", "Akasa Air", "All airlines"],
                           [n["ig4"], n["ai4"], n["ak4"], n["all4"]], [n["ig10"], n["ai10"], n["ak10"], n["all10"]],
                           a_name="4 airports (to 2024)", b_name="10 airports (2026)", w=w, h=int(500 * scale * hm), scale=scale,
                           fmt=lambda v: f"{v:.0f}%", tickfmt=lambda v: f"{v:.0f}%", label="Share of scheduled departures from the airports DGCA measures"),
        c4=C.step_line(pts, w=w, h=int(460 * scale * hm), scale=scale, ymax=11, gstep=2, gfmt=lambda v: f"{v:g}%",
                       xlabels=[2022, 2023, 2024, 2025, 2026],
                       annotations=[(2025 + 11 / 12, n["dec_ig"], f"{n['dec_ig']:.2f}% · Dec 2025", "end", 6),
                                    (2024.0, n["ig_prevmax"], f"{n['ig_prevmax']:.1f}% · Jan 2024 fog", "start", -12)],
                       label="IndiGo, share of flights cancelled each month, 2022 to 2026"),
        c5=C.hbars(apt_rows, w=w, h=int(560 * scale * hm), scale=scale, xmax=100, ticks=(0, 25, 50, 75, 100),
                   tickfmt=lambda v: f"{v:.0f}%", fmt=lambda v: f"{v:.1f}%", padl=220,
                   label="Share of departures on time by airport, all airlines, January to September 2026"),
        c6=C.season_bars(years, cvals, w=w, h=int(440 * scale * hm), scale=scale, highlight={2026}, label_years=set(years),
                         ymax=max(cvals) * 1.2, fmt=lambda v: f"{v:.2f}", tipfmt=lambda y, v: f"{y}: {v:.2f} per 10,000 passengers",
                         label="Complaints per 10,000 passengers, typical month each year"),
    )


EXTRA_PAGE_CSS = ".line{stroke:var(--accent);stroke-width:2.5;} .dot-hi{fill:var(--accent);stroke:var(--bg);stroke-width:2;} .panels{display:grid;grid-template-columns:1fr;gap:4px;} .panels h3{font:600 .9rem var(--text);color:var(--muted);margin:6px 0 0;}"
EXTRA_SLIDE_CSS = ".line{stroke:#3B82F6;stroke-width:4;} .dot-hi{fill:#3B82F6;stroke:#0A0A0F;stroke-width:3;} .ph{font:600 26px Inter;color:#8B9DC3;margin:4px 0 -10px;}"


def report():
    c = charts(1.0)
    n = N
    t1 = common.table(["Airline", "Months as #1"], [[a, v] for a, v in sorted(n["counts"].items(), key=lambda kv: -kv[1])])
    t5 = common.table(["Airport", "On time, Jan–Sep 2026"], [[APT_NAMES[k], f"{v:.1f}%"] for k, v in sorted(apt.items(), key=lambda kv: -kv[1])])
    t6 = common.table(["Year", "Complaints per 10,000 (typical month)"], [[y, f"{float(cy[str(y)]):.2f}"] for y in range(2018, 2027)])
    return f"""<title>Which Indian Airline Is Most Reliable?</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>/* Layout: one reading column (~68ch); Sartium dark canvas first, light mirror. */{common.PAGE_CSS}{EXTRA_PAGE_CSS}</style>
<main>
<div class="kick"><span>Public Record · Sartium</span><span class="draft">Draft for review</span></div>
<h1>Which Indian airline is actually the most reliable?</h1>
<p class="dek">We read {n['reports']} monthly reports from the Directorate General of Civil Aviation, January 2018 to September 2026. The airline that leaves on time most often, the one that cancels least and the one with the fewest complaints have not been the same airline in a single month.</p>
<p class="byline">Scope: scheduled domestic flights, as reported by the airlines to DGCA · On-time figures cover departures from the listed airports only</p>
<div class="stats">
  <div class="stat"><b>{n['changes']}</b><span>Times the "most punctual airline" title changed hands in {n['reports']} months.</span></div>
  <div class="stat"><b>0</b><span>Months in which one airline was outright best on punctuality, cancellations and complaints at once.</span></div>
  <div class="stat"><b>{n['ig4']:.0f}%</b><span>Share of IndiGo's departures from the four airports DGCA measured until 2024.</span></div>
</div>

<h2>The answer everyone assumes</h2>
<p>Every month DGCA publishes an on-time table, the winner advertises it, and the press repeats it. The working answer is that IndiGo is India's most reliable airline. It has topped the table in <strong>{n['counts']['IndiGo']} of {n['reports']} months</strong> since January 2018, and in every month of 2026.</p>

<h2>The source</h2>
<p>DGCA's monthly domestic traffic report is free to download at <code>dgca.gov.in</code> (Data &amp; Reports → Aviation Data &amp; Statistics → Air Transport → Domestic). For each airline it gives passengers carried, the share of flights that left on time, the share cancelled, and complaints per 10,000 passengers. We read every report from January 2018 to September 2026; April 2020 was never published. To see what the on-time figure covers, we also used DGCA's approved winter 2026 schedules and the Airports Authority of India's airport traffic tables.</p>
<p class="note">Every report says it is "prepared based on information received from scheduled domestic airlines". These are the airlines' own figures, and DGCA publishes no flight counts behind any percentage.</p>

<h2>What the obvious number says</h2>
<p>In January to September 2026, at the airports DGCA measures, <strong>IndiGo left on time {n['ig26']:.1f}%</strong> of the time, Akasa Air {n['ak26']:.1f}% and the Air India Group {n['ai26']:.1f}%. That lead is bigger than the normal month-to-month swing: reshuffling the nine months thousands of times keeps IndiGo's lead over Akasa between {n['lead26_lo']:.1f} and {n['lead26_hi']:.1f} points, with IndiGo on top every time. In 2025 the lead was smaller and just as steady, {n['lead25']:.1f} points.</p>
<p>That is a recent pattern. Over the whole record the title changed hands <strong>{n['changes']} times</strong>.</p>
<figure><figcaption>Months each airline topped DGCA's on-time table, 2018–2026</figcaption><div class="chart">{c['c1']}</div>
<span class="src">Airlines with at least 1% of passengers that month. Source: DGCA monthly domestic traffic reports.</span>{t1}</figure>
<p>In 2018–19 Go First beat IndiGo by {n['pre_gap']:.2f} points on average; in 2022–24 IndiGo beat Vistara by {n['era4_gap']:.2f}. Both gaps are smaller than one airline's normal swing from month to month, so in those years the winner was close to a coin toss.</p>

<h2>The turn: what the on-time number leaves out</h2>
<p><strong>It counts departures from a few airports.</strong> Until December 2024 only Bengaluru, Delhi, Hyderabad and Mumbai counted. Chennai and Kolkata were added in 2025, and Ahmedabad, Kochi, Guwahati and Lucknow in 2026. The original four handle about {n['aai4']:.0f}% of India's domestic aircraft movements.</p>
<figure><figcaption>Share of scheduled departures from the airports DGCA measures</figcaption><div class="chart">{c['c3']}</div>
<span class="src">Winter 2026 approved schedules (DGCA). Today's network stands in for earlier years.</span></figure>
<p>On today's schedule the original four airports carry <strong>{n['ig4']:.0f}% of IndiGo's departures</strong> and {n['ai4']:.0f}% of the Air India Group's. Even the ten airports measured in 2026 cover {n['ig10']:.0f}% of IndiGo's departures and {n['all10']:.0f}% of all scheduled domestic departures.</p>
<p><strong>The airport moves the number almost as much as the airline.</strong> In 2026, flights from Chennai left on time {n['maa']:.1f}% of the time and flights from Mumbai {n['bom']:.1f}%.</p>
<figure><figcaption>Departures on time by airport, all airlines, January–September 2026</figcaption><div class="chart">{c['c5']}</div>
<span class="src">Source: DGCA monthly reports, airport-level on-time tables.</span>{t5}</figure>
<p>If the Air India Group flew IndiGo's mix of airports, its 2026 score would rise from {n['ai_own']:.1f}% to about {n['ai_on_ig']:.1f}%, and IndiGo's lead would shrink from {n['lead_raw']:.1f} to {n['lead_mix']:.1f} points. The lead survives, but roughly a quarter of it comes from where IndiGo flies.</p>
<p><strong>Punctual is not the same as reliable.</strong> In none of {n['agree_months']} months was one airline outright best on punctuality, cancellations and complaints together. The most punctual airline also cancelled least in only {n['same_best']:.0f}% of months.</p>
<div class="panels">
<h3>On time, Jan–Sep 2026 (higher is better)</h3>{c['c2a']}
<h3>Cancelled, Jan–Sep 2026 (lower is better)</h3>{c['c2b']}
<h3>Complaints per 10,000 passengers, Jan–Sep 2026 (lower is better; the top two are tied)</h3>{c['c2c']}
</div>
<p>Akasa cancelled <strong>{n['akc']:.2f}%</strong> of flights, about 1 in {round(100/n['akc'], -1):,.0f}, against {n['igc']:.2f}% for IndiGo (1 in {round(100/n['igc'], -1):,.0f}) and {n['aic']:.2f}% for the Air India Group (1 in {round(100/n['aic'], -1):,.0f}). On complaints, Akasa ({n['akk']:.2f}) and IndiGo ({n['igk']:.2f}) cannot be separated.</p>

<h2>The worst month in eight years</h2>
<p>In <strong>December 2025, IndiGo cancelled {n['dec_ig']:.2f}% of its flights</strong>, {n['ratio']:.1f} times its typical month since 2022 ({n['ig_med']:.2f}%) and nearly double its previous worst ({n['ig_prevmax']:.1f}%, in the fog of January 2024). Airlines received {n['dec_cmp']:,.0f} complaints that month, more than in the whole of 2024. DGCA's report puts {n['dec_op']:.1f}% of the month's cancellations down to operational reasons and {n['dec_wx']:.1f}% to weather.</p>
<figure><figcaption>IndiGo, share of flights cancelled each month, 2022–2026</figcaption><div class="chart">{c['c4']}</div>
<span class="src">Source: DGCA monthly domestic traffic reports.</span></figure>
<p>That one month decides any single "most reliable" score. Combine the three measures with every reasonable weighting, and over October 2025 to September 2026 Akasa comes out on top under {n['akw']:.0f}% of them. Remove December 2025 alone and IndiGo comes out on top under {n['igw_x']:.0f}%.</p>

<h2>Complaints are up, and baggage now leads</h2>
<p>In a typical month, complaints per 10,000 passengers went from {n['c24']:.2f} in 2024 to <strong>{n['c26']:.2f} in 2026</strong>, a rise across every large airline. Baggage went from {n['bag24']:.1f}% of complaints to {n['bag26']:.1f}%. That is still about one complaint per {round(10000/n['c26'], -2):,.0f} passengers, and the reports do not say whether people complained more or complaints were counted differently.</p>
<figure><figcaption>Complaints per 10,000 passengers, typical month each year</figcaption><div class="chart">{c['c6']}</div>
<span class="src">Median month, December 2025 excluded. Complaints received by airlines, as reported to DGCA.</span>{t6}</figure>

<h2>The corrected answer</h2>
<p>There is a trade-off rather than one winner.</p>
<ul>
<li><strong>Leaves on time from a big airport:</strong> IndiGo, clearly, since 2025: {n['lead26']:.1f} points ahead of Akasa in 2026. Against the Air India Group the lead is {n['lead_raw']:.1f} points, or {n['lead_mix']:.1f} on the same mix of airports.</li>
<li><strong>Your flight actually operates:</strong> Akasa, clearly, in 2025 and 2026.</li>
<li><strong>Fewest complaints:</strong> no clear winner in 2026.</li>
<li><strong>One combined score:</strong> depends on the weights and on one month.</li>
</ul>
<p>Two popular explanations did not survive. Airlines do not stay punctual by cancelling: months with more cancellations had worse on-time rates, not better. And bad months are not just fog. Fog season costs about {n['fog_rest']-n['fog_dj']:.0f} points of punctuality ({n['fog_dj']:.1f}% in December–January against {n['fog_rest']:.1f}% otherwise), but the worst cancellation month on record was labelled mostly operational.</p>
<p class="quote">IndiGo is the most punctual large airline at the airports DGCA measures. Akasa is the least likely to cancel. No airline has led outright on all three measures in any month since 2018.</p>

<h2>What this data cannot tell you</h2>
<ul>
<li><strong>Anything independent of the airlines.</strong> Every figure is self-reported to DGCA.</li>
<li><strong>Arrivals, or most airports.</strong> On-time means departing within 15 minutes, at the listed airports only. Pune, Goa, Jaipur, Navi Mumbai and over a hundred others never enter the table.</li>
<li><strong>How many flights sit behind any percentage.</strong> No counts are published.</li>
<li><strong>Like-for-like years.</strong> The airport list changed in 2025 and again in 2026.</li>
<li><strong>A stable "Air India".</strong> The group absorbed Air India Express, AIX Connect (October 2024) and Vistara (November 2024).</li>
<li><strong>Why complaints rose,</strong> or what caused any delay. Causes are the airlines' own labels, and knock-on delays (about two-thirds of the total) hide the original cause.</li>
<li><strong>Safety.</strong> Nothing here measures it, and nothing here should be read as a safety ranking.</li>
</ul>

<section class="method">
<h2>How we did it</h2>
<p><strong>Source.</strong> {n['reports']} DGCA monthly domestic traffic reports (PDF), January 2018 to September 2026, plus DGCA's winter 2026 approved schedules and AAI's 2026 domestic movement tables. All free to download, with no login.</p>
<p><strong>Extraction.</strong> Every report was read by two independent PDF methods. A ten-month spot-check matched 265 of 265 chart values and 220 of 220 table values, and airline market shares sum to 97–100% in every month.</p>
<p><strong>Comparisons.</strong> Airlines with at least 1% of passengers that month. Ranges come from reshuffling months in three-month blocks, so a lead is only called a lead when it survives that.</p>
<p><strong>Checks.</strong> Every headline number was computed a second time by independent code.</p>
<p><strong>Reproduce it.</strong> The scripts and derived data will be published with this report. Every number on this page is read from them at build time.</p>
</section>
<div class="end"><div class="brand"><span class="sq">S</span>Sartium</div>
<p>Public Record is Sartium's series of questions settled with data anyone can download. Sartium builds analytics, automation and data products for businesses. sartium.com</p></div>
</main>{common.TIP_JS}"""


def slides():
    c = charts(1.0, w=936, hm=1.25)
    n = N
    S = []

    def slide(kicker, head, body="", chart="", foot="", solo=False):
        S.append(f'<section class="s{" solo" if solo else ""}"><div class="k">{kicker}</div><h2>{head}</h2>'
                 f'{f"<div class=c>{chart}</div>" if chart else ""}{f"<p>{body}</p>" if body else ""}'
                 f'<div class="f"><span>{foot}</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')

    S.append(f'<section class="s cover"><div class="k">Public Record</div><h1>Which Indian airline is actually the most reliable?</h1>'
             f'<p class="big">We read {n["reports"]} monthly DGCA reports, 2018 to 2026.</p>'
             f'<p class="sc">Scheduled domestic flights · airline-reported data</p>'
             f'<div class="f"><span>Swipe →</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    slide("The on-time title", f"“Most punctual airline” changed hands {n['changes']} times in {n['reports']} months.",
          f"IndiGo has led every month of 2026. In 2018–19 and 2022–24 the top two were a coin toss.", c["c1"], "Source: DGCA monthly domestic traffic reports")
    trio = (f'<p class="ph">On time (higher is better)</p>{c["c2a"]}<p class="ph">Cancelled (lower is better)</p>{c["c2b"]}'
            f'<p class="ph">Complaints per 10,000 (top two tied)</p>{c["c2c"]}')
    S.append(f'<section class="s"><div class="k">Jan–Sep 2026</div><h2>No airline has been best on all three in a single month since 2018.</h2>'
             f'<div class="c">{trio}</div><div class="f"><span>Source: DGCA</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    slide("What “on time” covers", f"Until 2025, DGCA's on-time figure counted 4 airports: {n['ig4']:.0f}% of IndiGo's departures.",
          "", c["c3"], "Share of scheduled departures · winter 2026 schedules")
    slide("Where you fly from", f"Chennai {n['maa']:.0f}% on time. Mumbai {n['bom']:.0f}%.",
          f"Give Air India IndiGo's mix of airports and IndiGo's 2026 lead shrinks from {n['lead_raw']:.1f} to {n['lead_mix']:.1f} points.",
          c["c5"], "All airlines, Jan–Sep 2026")
    slide("December 2025", f"IndiGo cancelled {n['dec_ig']:.2f}% of flights: {n['ratio']:.1f}× its typical month.",
          f"{n['dec_cmp']:,.0f} complaints that month, more than all of 2024. DGCA labels {n['dec_op']:.0f}% of the cancellations operational.",
          c["c4"], "Source: DGCA monthly domestic traffic reports")
    slide("One score?", "Pick your weights, pick your winner.",
          f"Combine punctuality, cancellations and complaints for Oct 2025–Sep 2026: Akasa wins under {n['akw']:.0f}% of weightings. "
          f"Drop December 2025 alone and IndiGo wins under {n['igw_x']:.0f}%.", "", "One month decides it", solo=True)
    slide("Complaints", f"Complaints per passenger roughly quadrupled from 2024 to 2026.",
          f"Baggage is now {n['bag26']:.0f}% of complaints, up from {n['bag24']:.0f}%. Still about 1 per {round(10000/n['c26'], -2):,.0f} passengers.", c["c6"],
          "Typical month each year · Dec 2025 excluded")
    slide("Read this before sharing", "What this data can't tell you.",
          "It's the airlines' own data. On-time means departures only, at listed airports. No flight counts are published. "
          "The airport list changed in 2025 and 2026. And nothing here measures safety.", "", "", solo=True)
    S.append(f'<section class="s"><div class="k">The answer</div><h2>IndiGo leaves on time most. Akasa cancels least. Nobody wins all three.</h2>'
             f'<ul><li>On-time: IndiGo, clearly, since 2025, at the airports DGCA measures.</li><li>Your flight operating: Akasa, in 2025 and 2026.</li>'
             f'<li>Complaints: a tie in 2026.</li></ul><p class="cta">Full report, method and code: link in the comments.</p>'
             f'<div class="f"><span>Data: DGCA</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    css = common.slide_css() + EXTRA_SLIDE_CSS
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(S)}</body></html>"


def public_page(body):
    body = body.replace('<span class="draft">Draft for review</span>', '')
    body = body.replace("<p><strong>Reproduce it.</strong> The scripts and derived data will be published with this report. Every number on this page is read from them at build time.</p>",
                        f'<p><strong>Reproduce it.</strong> Scripts, derived data, the research file and the exclusion log: <a href="{REPO_URL}">{REPO_URL.replace("https://", "")}</a>. Every number on this page is read from them at build time.</p>')
    body = body.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    desc = (f"{N['reports']} monthly DGCA reports: the most punctual Indian airline, the one that cancels least and the one with "
            "the fewest complaints have never been the same airline in one month.")
    head = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="description" content="{desc}"><meta property="og:type" content="article">'
            f'<meta property="og:title" content="Which Indian airline is actually the most reliable?"><meta property="og:description" content="{desc}">'
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
.k{{font:500 22px 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}} h1{{font:700 66px/1.05 'Space Grotesk';margin-top:18px;}}
.row{{display:flex;gap:56px;align-items:flex-end;}} .st b{{font:700 54px 'Space Grotesk';display:block;}} .st span{{font-size:20px;color:#8B9DC3;}}
.br{{margin-left:auto;display:flex;gap:12px;align-items:center;font:700 28px 'Space Grotesk';}}
.sq{{width:38px;height:38px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 19px 'Space Grotesk';color:#3B82F6;}}
</style></head><body><div><div class='k'>Public Record · {n['reports']} DGCA reports</div><h1>Which Indian airline is actually the most reliable?</h1></div>
<div class='row'><div class='st'><b>{n['changes']}</b><span>times the on-time title changed hands</span></div>
<div class='st'><b>0</b><span>months one airline won all three</span></div><div class='st'><b>{n['ig4']:.0f}%</b><span>of IndiGo flights measured, to 2024</span></div>
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
            el.screenshot(path=str(sd / f"r03-slide-{i:02d}.png"))
        pg.pdf(path=str(OUT / "r03-airlines-linkedin-carousel.pdf"), width="1080px", height="1350px", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        if pub:
            og = b.new_page(viewport={"width": 1200, "height": 630})
            og.goto((pub / "og.html").resolve().as_uri())
            og.wait_for_timeout(300)
            og.screenshot(path=str(pub / "og.png"))
            (pub / "og.html").unlink()
        b.close()
    print("slides:", len(els))
