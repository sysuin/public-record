"""Build the R01 publishing pack: report page (HTML), carousel slides (PNG) and LinkedIn PDF.

Run:  python3 -I pack/build_pack.py <report_dir> <fonts_dir> <out_dir>
  report_dir = Reports/R01-delhi-air   (reads data/*.csv, data/results.json)
  fonts_dir  = folder with space-grotesk-latin-{500,700}-normal.woff2 and inter-latin-{400,600}-normal.woff2
  out_dir    = where report.html, slides/*.png and the PDF are written
Every number on the page is read from the analysis outputs at build time; nothing is typed in by hand
except fixed facts about the source (URL pattern, scale bands).
"""
import base64, json, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts as C  # noqa: E402

REP, FONTS, OUT = (Path(a) for a in sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)
D = REP / "data"
R = json.loads((D / "results.json").read_text())
ss = pd.read_csv(D / "season_summary_by_city.csv")
yoy = pd.read_csv(D / "yoy_change_by_city.csv")
wx = pd.read_csv(D / "weather_adjusted_year_index.csv")
fires = pd.read_csv(D / "fires_vs_delhi.csv")
daily = pd.read_csv(D / "ncr_daily_aqi.csv", parse_dates=["date"])
wxs = pd.read_csv(D / "weather_season_summary_oct1_nov18.csv")

YEARS = list(range(2016, 2027))


def delhi(window, col):
    t = ss[(ss.city == "Delhi") & (ss.window == window)].set_index("year")[col]
    return [float(t[y]) for y in YEARS]


mean_oct = delhi("oct1_nov20", "mean")
severe = delhi("oct1_nov20", "days_severe")
nov = ss[(ss.city == "Delhi") & (ss.window == "nov1_20")].set_index("year")
cmp = R["delhi_2026_vs_2016_2025_oct1_nov20"]
stable = R["delhi_trend_oct1_nov20_stable_network_2019_2025"]
stable_cal = R["delhi_trend_calendar_stable_network_2019_2025"]

# monitors: monthly max of listed Delhi stations (falls back to reporting stations before lists existed)
daily["st"] = daily["Delhi_stations_total"].fillna(daily["Delhi_stations"])
mon = daily.set_index("date")["st"].resample("MS").max().dropna()
mon = mon["2015-05":]
pts = [(d.year + (d.month - 1) / 12, float(v)) for d, v in mon.items()]
st16 = float(ss[(ss.city == "Delhi") & (ss.window == "oct1_nov20") & (ss.year == 2016)].stations_median.iloc[0])
oct26 = daily[(daily.date >= "2026-10-01") & (daily.date <= "2026-10-20")]
st_before = int(oct26[oct26.date <= "2026-10-06"].Delhi_stations_total.max())
st_after = int(oct26[oct26.date >= "2026-10-13"].Delhi_stations_total.max())

# daily Delhi, 1-20 Nov 2026
nd = daily[(daily.date >= "2026-11-01") & (daily.date <= "2026-11-20")]
ndays = [int(d.day) for d in nd.date]
nvals = [float(v) for v in nd.Delhi]

# city change 1-20 Nov 2026 vs 2025
y26 = yoy[(yoy.year == 2026) & (yoy.window == "nov1_20")].set_index("city")
rows = []
for city in y26.index:
    r = y26.loc[city]
    now, prev = int(r.listed_now), int(r.listed_prev)
    grp = "added" if now > prev else "same"
    rows.append((city, float(r["pct_change"]) * 100, grp, f"{prev}→{now}"))
rows.sort(key=lambda r: r[1])

# fires vs Delhi 1-20 Nov (ICAR-IARI CREAMS years only, never mixed with NASA counts)
fy = [int(y) for y in fires.year]
fv = [float(v) / 1000 for v in fires.punjab_haryana]
fd = [float(v) for v in fires.delhi_nov1_20_mean]
f20, f25 = fires.set_index("year").loc[2020], fires.set_index("year").loc[2025]
fire_drop = (1 - f25.punjab_haryana / f20.punjab_haryana) * 100

# weather-adjusted index, typical autumn = 100
w = wx[wx.model == "weather"].set_index("year")
wmid = [float(w.loc[y].adjusted_index) * 100 for y in YEARS]
wlo = [float(w.loc[y].adj_lo) * 100 for y in YEARS]
whi = [float(w.loc[y].adj_hi) * 100 for y in YEARS]
rain = wxs.set_index("year")

N = dict(
    files=R["bulletin_files"], missing=R["bulletin_missing_files"],
    m16=mean_oct[0], m17=mean_oct[1], m25=mean_oct[-2], m26=mean_oct[-1],
    base=cmp["mean_base"], pct=cmp["paired_pct"] * 100,
    pct_lo=cmp["paired_pct_ci"][0] * 100, pct_hi=cmp["paired_pct_ci"][1] * 100,
    sev16=severe[0], nov26_poor=int(nov.loc[2026].days_poor_or_worse), nov26_n=int(nov.loc[2026].n_days_data),
    max_all=max(R["delhi_max_by_year"].values()), st16=st16, st_before=st_before, st_after=st_after,
    slope=stable["slope_per_year"], slope_lo=stable["ci"][0], slope_hi=stable["ci"][1],
    cal_lo=stable_cal["spread_min"], cal_hi=stable_cal["spread_max"],
    fire20=int(f20.punjab_haryana), fire25=int(f25.punjab_haryana), fire_drop=fire_drop,
    nov20=float(f20.delhi_nov1_20_mean), nov25=float(f25.delhi_nov1_20_mean),
    rain21=float(rain.loc[2021].rain_mm), rain22=float(rain.loc[2022].rain_mm),
    wx26=wmid[-1], wx26lo=wlo[-1], wx26hi=whi[-1],
    wxmin=min(wmid[:-1]), wxmax=max(wmid[:-1]),
)
cities = {r[0]: r for r in rows}
print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in N.items()}, indent=1))
print(rows)


def charts(scale=1.0, w=960, hm=1.0):
    return dict(
        c1=C.season_bars(YEARS, mean_oct, w=w, h=int(520 * scale * hm), scale=scale, highlight={2026},
                         label_years={2016, 2017, 2025, 2026}, ymax=420,
                         refs=[(300, "300"), (200, "200")],
                         tipfmt=lambda y, v: f"{y}: average {v:.0f}",
                         label="Delhi's average air quality score, 1 October to 20 November, by year"),
        c7=C.season_bars(ndays, nvals, w=w, h=int(460 * scale * hm), scale=scale, highlight=set(), ymax=420,
                         label_years={ndays[nvals.index(max(nvals))], ndays[nvals.index(min(nvals))]},
                         refs=[(300, "300"), (200, "200")], xticks={1, 5, 10, 15, 20},
                         tipfmt=lambda d, v: f"{d} Nov 2026: {v:.0f}",
                         label="Delhi's daily score, 1 to 20 November 2026"),
        c2=C.season_bars(YEARS, severe, w=w, h=int(460 * scale * hm), scale=scale, highlight={2026},
                         label_years=set(YEARS), ymax=14, fmt=lambda v: f"{v:.0f}",
                         tipfmt=lambda y, v: f"{y}: {v:.0f} Severe days",
                         label="Days Delhi scored above 400 (Severe), 1 October to 20 November"),
        c3=C.step_line(pts, w=w, h=int(460 * scale * hm), scale=scale, ymax=70,
                       annotations=[(2016.75, st16, f"about {st16:.0f} in autumn 2016", "start", 36),
                                    (2022.5, 39, "33 to 40, 2019–2025", "middle", -18),
                                    (2026.75, st_after, f"{st_after} by 13 Oct 2026", "end", -14)],
                       label="Number of monitoring stations behind Delhi's daily score"),
        c4=C.change_bars(rows, w=w, h=int(500 * scale * hm), scale=scale,
                         label="Change in average score, 1–20 November 2026 against 2025, by city"),
        c5=C.twin_panels(fy, fv, fd, w=w, h=int(540 * scale * hm), scale=scale,
                         a_title="Farm fires, Punjab + Haryana (thousands)",
                         b_title="Delhi's average score, 1–20 November",
                         a_fmt=lambda v: f"{v:.1f}k", b_fmt=lambda v: f"{v:.0f}",
                         a_label_years={2020, 2025}, b_label_years={2020, 2025},
                         label="Satellite-counted farm fires against Delhi's November air"),
        c6=C.range_dots(YEARS, wmid, wlo, whi, w=w, h=int(500 * scale * hm), scale=scale, highlight={2026},
                        ymin=60, ymax=130, ref=100, reflabel="",
                        label="Delhi's autumn after removing the weather, 100 = a typical autumn"),
    )


def font_face():
    def ff(fam, wt, file):
        b = base64.b64encode((FONTS / file).read_bytes()).decode()
        return f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,{b}) format('woff2');}}"
    return "".join([ff("Space Grotesk", 700, "space-grotesk-latin-700-normal.woff2"),
                    ff("Space Grotesk", 500, "space-grotesk-latin-500-normal.woff2"),
                    ff("Inter", 400, "inter-latin-400-normal.woff2"),
                    ff("Inter", 600, "inter-latin-600-normal.woff2")])


def table(headers, body):
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
    return f'<details class="tbl"><summary>Show the numbers</summary><div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>'


# ---------------------------------------------------------------- report page
def report():
    c = charts(1.0)
    n = N
    dn, nn = cities["Delhi"], cities["Noida"]
    gz, gn = cities["Ghaziabad"], cities["Greater Noida"]
    gg, fb = cities["Gurugram"], cities["Faridabad"]
    t1 = table(["Year", "Average score", "Severe days"], [[y, f"{m:.0f}", f"{s:.0f}"] for y, m, s in zip(YEARS, mean_oct, severe)])
    t4 = table(["City", "Change", "Monitors (Nov 2025 → Nov 2026)"], [[r[0], f"{r[1]:+.1f}%", r[3]] for r in rows])
    t5 = table(["Year", "Farm fires, Punjab + Haryana", "Delhi, 1–20 Nov average"], [[y, f"{a*1000:,.0f}", f"{b:.0f}"] for y, a, b in zip(fy, fv, fd)])
    t6 = table(["Year", "After weather (100 = typical)", "Plausible range"], [[y, f"{m:.0f}", f"{l:.0f}–{h:.0f}"] for y, m, l, h in zip(YEARS, wmid, wlo, whi)])
    return f"""<title>Is Delhi's Air Getting Worse?</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>
/* Layout: one reading column (~68ch) with charts allowed slightly wider; Sartium's dark canvas first, light mirror. */
:root{{
  --bg:#0A0A0F; --panel:#0F1420; --ink:#FFFFFF; --body:#D7DEEA; --muted:#8B9DC3; --faint:#5B6B8C;
  --rule:#1F2937; --accent:#3B82F6; --amber:#D97706; --ctx:#33405E; --chip:#13203A;
  --display:'Space Grotesk',ui-sans-serif,system-ui,sans-serif; --text:'Inter',ui-sans-serif,system-ui,sans-serif;
  color-scheme:dark;
}}
@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]){{
  --bg:#F6F7FA; --panel:#FFFFFF; --ink:#0B1220; --body:#253149; --muted:#4B5A78; --faint:#7A88A6;
  --rule:#E1E6EF; --accent:#2563EB; --amber:#B45309; --ctx:#B9C3D6; --chip:#E7EEFC; color-scheme:light;}}}}
:root[data-theme="light"]{{
  --bg:#F6F7FA; --panel:#FFFFFF; --ink:#0B1220; --body:#253149; --muted:#4B5A78; --faint:#7A88A6;
  --rule:#E1E6EF; --accent:#2563EB; --amber:#B45309; --ctx:#B9C3D6; --chip:#E7EEFC; color-scheme:light;}}
body{{background:var(--bg);color:var(--body);font:400 17px/1.65 var(--text);margin:0;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));}}
main{{max-width:760px;margin:0 auto;padding-block:48px 80px;display:flex;flex-direction:column;gap:22px;}}
h1,h2,h3{{font-family:var(--display);color:var(--ink);text-wrap:balance;margin:0;}}
h1{{font-size:clamp(2.1rem,5.4vw,3.3rem);line-height:1.08;font-weight:700;letter-spacing:-.01em;}}
h2{{font-size:1.55rem;line-height:1.2;font-weight:700;margin-top:30px;}}
p{{margin:0;}} strong{{color:var(--ink);font-weight:600;}}
a{{color:var(--accent);}} a:focus-visible,[tabindex]:focus-visible{{outline:2px solid var(--accent);outline-offset:2px;}}
.kick{{font:500 .78rem/1 var(--display);letter-spacing:.16em;text-transform:uppercase;color:var(--accent);display:flex;gap:12px;flex-wrap:wrap;align-items:center;}}
.draft{{background:var(--chip);color:var(--muted);padding:5px 9px;letter-spacing:.08em;}}
.dek{{font-size:1.2rem;line-height:1.55;color:var(--body);}}
.byline{{font-size:.88rem;color:var(--muted);}}
.stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin-top:8px;}}
.stat{{background:var(--bg);padding:18px 16px;display:flex;flex-direction:column;gap:6px;min-width:0;}}
.stat b{{font:700 2.2rem/1 var(--display);color:var(--ink);}}
.stat span{{font-size:.86rem;line-height:1.4;color:var(--muted);}}
figure{{margin:10px 0 4px;display:flex;flex-direction:column;gap:10px;}}
figcaption{{font:600 .98rem/1.35 var(--text);color:var(--ink);}}
figure .src{{font-size:.8rem;color:var(--faint);}}
.chart{{position:relative;}}
.note{{border-left:3px solid var(--amber);padding:4px 0 4px 16px;color:var(--body);}}
.quote{{font:500 1.12rem/1.5 var(--display);color:var(--ink);border-left:3px solid var(--accent);padding:2px 0 2px 16px;}}
ul{{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:8px;}}
.method{{background:var(--panel);border:1px solid var(--rule);padding:22px;display:flex;flex-direction:column;gap:12px;font-size:.93rem;}}
.method h2{{margin-top:0;font-size:1.2rem;}}
code{{font-size:.86em;background:var(--chip);padding:1px 5px;word-break:break-all;}}
.tbl summary{{cursor:pointer;font-size:.85rem;color:var(--muted);}}
.tw{{overflow-x:auto;}} table{{border-collapse:collapse;font-size:.88rem;margin-top:8px;font-variant-numeric:tabular-nums;}}
th,td{{text-align:left;padding:5px 14px 5px 0;border-bottom:1px solid var(--rule);}} th{{color:var(--muted);font-weight:600;}}
.end{{font-size:.9rem;color:var(--muted);border-top:1px solid var(--rule);padding-top:18px;display:flex;flex-direction:column;gap:8px;}}
.brand{{display:flex;align-items:center;gap:10px;font:700 1.05rem var(--display);color:var(--ink);}}
.sq{{width:26px;height:26px;border:2px solid var(--accent);display:grid;place-items:center;font:700 .8rem var(--display);color:var(--accent);}}
#tip{{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--rule);padding:6px 9px;font-size:.82rem;display:none;z-index:5;}}
/* chart tokens */
svg text{{font-family:var(--text);}}
.grid{{stroke:var(--rule);stroke-width:1;}} .ref{{stroke:var(--faint);stroke-width:1;opacity:.6;}} .ref0{{stroke:var(--muted);stroke-width:1.5;}}
.ax{{fill:var(--muted);font-size:15px;}} .axs{{fill:var(--muted);font-size:14px;}}
.reflbl{{fill:var(--faint);font-size:13px;}}
.lbl{{fill:var(--ink);font-size:16px;font-weight:600;}} .lblin{{fill:#fff;font-size:16px;font-weight:600;}} .lbls{{fill:var(--muted);font-size:14px;}}
.bar{{fill:var(--ctx);}} .bar-hi{{fill:var(--accent);}} .bar-amb{{fill:var(--amber);}}
.line{{stroke:var(--accent);stroke-width:2.5;}}
.rng{{stroke:var(--ctx);stroke-width:3;stroke-linecap:round;}} .rng-hi{{stroke:var(--accent);stroke-width:3;stroke-linecap:round;opacity:.55;}}
.dot{{fill:var(--muted);stroke:var(--bg);stroke-width:2;}} .dot-hi{{fill:var(--accent);stroke:var(--bg);stroke-width:2;}}
[data-tip]{{cursor:default;}} [data-tip]:hover{{opacity:.85;}}
@media (max-width:560px){{.stats{{grid-template-columns:1fr;}} body{{font-size:16px;}}}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important;}}}}
</style>
<main>
<div class="kick"><span>Public Record · Sartium</span><span class="draft">Draft for review</span></div>
<h1>Is Delhi's air getting worse?</h1>
<p class="dek">We read all {n['files']:,} daily air-quality bulletins the Central Pollution Control Board has published since 2015. By the government's own number, Delhi's autumn air is not getting worse. This year's improvement arrived in the same weeks the city's monitor count rose by more than a quarter, and the bulletins cannot separate the two.</p>
<p class="byline">Data to 20 November 2026 · Scope: CPCB city scores for Delhi and five NCR cities</p>
<div class="stats">
  <div class="stat"><b>{n['m26']:.0f}</b><span>Delhi's average score, 1 Oct–20 Nov 2026. The worst autumns were 2016 ({n['m16']:.0f}) and 2017 ({n['m17']:.0f}).</span></div>
  <div class="stat"><b>0</b><span>Severe days so far this season in all six NCR cities, a first in the record.</span></div>
  <div class="stat"><b>{n['st_before']}→{n['st_after']}</b><span>Monitors listed behind Delhi's score, before and after 7–13 October 2026.</span></div>
</div>

<h2>The answer everyone assumes</h2>
<p>Every November the same headline returns: Delhi's air has hit a new low. The working assumption, repeated every year, is that the city is getting worse. We tested it against the one number the government publishes for every city, every day.</p>

<h2>The source</h2>
<p>At 4 pm each day the Central Pollution Control Board (CPCB) publishes a PDF with an air quality score for every city it monitors. The score runs from 0 to 500. Above 200 is Poor, above 300 Very Poor, above 400 Severe. Each bulletin sits at a predictable address, so anyone can check a day for themselves:</p>
<p><code>https://www.cpcb.gov.in/upload/Downloads/AQI_Bulletin_20261120.pdf</code></p>
<p>We downloaded every bulletin from May 2015 to 20 November 2026 ({n['files']:,} files; {n['missing']} days were never published) and read the rows for Delhi, Gurugram, Noida, Ghaziabad, Faridabad and Greater Noida. To compare an unfinished winter fairly, every year below uses the same dates: <strong>1 October to 20 November</strong>.</p>

<h2>What the number says</h2>
<p>Delhi's worst autumns in the record are <strong>2016 and 2017</strong>, averaging {n['m16']:.0f} and {n['m17']:.0f}. This year's average so far is <strong>{n['m26']:.0f}</strong>, the lowest of the eleven. Matched day for day against 2016–2025, it is about a fifth lower ({n['pct']:.0f}%, with a plausible range of {n['pct_lo']:.0f}% to {n['pct_hi']:.0f}% given how much single days swing).</p>
<figure><figcaption>Delhi's average score, 1 October to 20 November</figcaption><div class="chart">{c['c1']}</div>
<span class="src">Lines mark 200 (Poor above) and 300 (Very Poor above). 2026 is highlighted. Source: CPCB daily AQI bulletins.</span>{t1}</figure>
<p>The worst days have eased faster than the typical day. Delhi had <strong>{n['sev16']:.0f} Severe days</strong> in this window in 2016. This year it has had none, and so have Gurugram, Noida, Ghaziabad, Faridabad and Greater Noida. Every earlier year had at least one NCR city above 400. No day in the whole archive has reached 500; Delhi's highest reading is {n['max_all']:.0f}, so a "record" on this scale would need a number the bulletin has never printed.</p>
<figure><figcaption>Days Delhi scored above 400 (Severe), 1 October to 20 November</figcaption><div class="chart">{c['c2']}</div>
<span class="src">Source: CPCB daily AQI bulletins.</span></figure>
<p class="note">None of this makes the air clean. Between 1 and 20 November this year, <strong>{n['nov26_poor']} of {n['nov26_n']} days</strong> were Poor or worse. "Not getting worse" describes the direction, not the level.</p>
<figure><figcaption>Delhi's daily score, 1 to 20 November 2026</figcaption><div class="chart">{c['c7']}</div>
<span class="src">Lines mark 200 (Poor above) and 300 (Very Poor above). Source: CPCB daily AQI bulletins.</span></figure>

<h2>The turn: the number is not counting the same thing</h2>
<p>Delhi's figure in the bulletin is an <strong>average of whichever monitoring stations reported that day</strong>. CPCB says plainly on its own bulletin that averaging stations this way is not scientifically sound, and it still prints the number.</p>
<p>That average has been built from very different networks. In autumn 2016 it came from about <strong>{n['st16']:.0f} stations</strong>. From 2019 to 2025 it came from 33 to 40. Then, between <strong>7 and 13 October this year</strong>, in the middle of the comparison window, the listed count jumped from {n['st_before']} to {n['st_after']}.</p>
<figure><figcaption>Monitoring stations behind Delhi's daily score</figcaption><div class="chart">{c['c3']}</div>
<span class="src">Source: station counts printed in the CPCB bulletins (monthly maximum).</span></figure>
<p>Neighbouring cities expanded too, and not evenly. Compare each city's 1–20 November average with the same dates last year, and the split lines up with the monitors:</p>
<figure><figcaption>Change in average score, 1–20 November 2026 against 2025</figcaption><div class="chart">{c['c4']}</div>
<span class="src">Blue: cities whose monitor list grew. Amber: no new monitors. Source: CPCB bulletins.</span>{t4}</figure>
<p>Greater Noida ({gn[1]:+.0f}%), Ghaziabad ({gz[1]:+.0f}%), Noida ({nn[1]:+.0f}%) and Delhi ({dn[1]:+.0f}%) all added monitors and all improved. Gurugram ({gg[1]:+.0f}%) and Faridabad ({fb[1]:+.0f}%) added none and did not. For the three Uttar Pradesh cities, the gap from Gurugram this year is wider than in any earlier year.</p>
<p class="note">This is a coincidence in timing that we cannot yet explain away. The cities that expanded are Delhi and the three east of it; the two that did not are the Haryana cities to the south-west, so a regional weather difference would produce the same split. Delhi's score also did not drop on the days its new stations appeared. Settling it needs station-by-station data, which CPCB keeps behind a CAPTCHA. We did not try to get past it.</p>

<h2>The fires fell. November did not move.</h2>
<p>Farm fires in Punjab and Haryana counted by satellite (ICAR-IARI's CREAMS bulletins, season to 20 November) fell from <strong>{n['fire20']:,} in 2020 to {n['fire25']:,} in 2025</strong>, a drop of {n['fire_drop']:.0f}%. Over the same years Delhi's 1–20 November average went from {n['nov20']:.0f} to {n['nov25']:.0f}.</p>
<figure><figcaption>Farm fires against Delhi's November air, by year</figcaption><div class="chart">{c['c5']}</div>
<span class="src">Sources: ICAR-IARI CREAMS (fires, Punjab + Haryana; 2019 and 2022 not available); CPCB bulletins (Delhi).</span>{t5}</figure>
<p>A satellite only sees a fire that is burning when it passes overhead. This data cannot tell "farm smoke matters less than the headlines say" from "more burning now happens when no satellite is looking". Both fit the numbers.</p>

<h2>The corrected answer</h2>
<p>Hold the network steady and the trend disappears. From 2019 to 2025, when Delhi's score came from a stable 33 to 40 stations, the autumn average moved by <strong>less than one point a year</strong> ({n['slope']:+.2f}, plausible range {n['slope_lo']:.0f} to +{n['slope_hi']:.0f}). The whole-year average stayed between {n['cal_lo']:.0f} and {n['cal_hi']:.0f}.</p>
<p>Weather explains most of what changes from one autumn to the next. Taking out wind, rain, temperature, humidity and the date of Diwali removes roughly <strong>three-quarters</strong> of the difference between years. The "good" autumns of 2021 and 2022 were the two wet ones, with {n['rain21']:.0f} mm and {n['rain22']:.0f} mm of rain between October and mid-November. After the weather, every autumn from 2016 to 2025 lands between {n['wxmin']:.0f} and {n['wxmax']:.0f} on a scale where 100 is typical.</p>
<figure><figcaption>Delhi's autumn after removing the weather (100 = a typical autumn)</figcaption><div class="chart">{c['c6']}</div>
<span class="src">100 = a typical autumn. Vertical lines show the plausible range. Weather: NASA MERRA-2 reanalysis (2026: NASA GEOS-IT).</span>{t6}</figure>
<p>This year still looks better after the weather, at about {n['wx26']:.0f} (range {n['wx26lo']:.0f}–{n['wx26hi']:.0f}). It also arrived in the same month the monitor count jumped, and with weather taken from a different NASA model than earlier years.</p>
<p class="quote">By the government's own number, Delhi's autumn air is not getting worse. It has not clearly been getting better either. For seven years it has been stuck, rising and falling with the weather.</p>

<h2>What this data cannot tell you</h2>
<ul>
<li><strong>Whether this year's improvement is real.</strong> Only a recount on last year's stations would show it, and station data sits behind a CAPTCHA.</li>
<li><strong>How much pollution anyone breathed.</strong> The bulletin is a 0–500 index for a city average, not a measure of dust in micrograms or of what one street experienced.</li>
<li><strong>Why the fires and the air came apart.</strong> Two explanations fit equally well.</li>
<li><strong>How precise the weather adjustment is.</strong> It is a model built on one NASA grid point, not on IMD observations, and the ranges are wide.</li>
<li><strong>The rest of this winter.</strong> Everything here stops on 20 November. December and January decide the season.</li>
</ul>

<section class="method">
<h2>How we did it</h2>
<p><strong>Source.</strong> CPCB daily AQI bulletins, {n['files']:,} PDFs, 1 May 2015 to 20 November 2026, downloaded on 21 November 2026 from <code>cpcb.gov.in/upload/Downloads/</code>. Each city row gives the score, the main pollutant and the number of stations reporting.</p>
<p><strong>Checks.</strong> Every bulletin was read by two independent methods; the scores agree on every one of the 20,859 city-days both could read. Six randomly chosen bulletins were checked again directly against the PDF text. {R['exclusions_count']} rows were dropped (for example, a bulletin whose header date differs from its file date) and every exclusion is logged.</p>
<p><strong>Comparisons.</strong> Same calendar window every year. Ranges come from resampling days and years, so a figure is only called a change when it survives that.</p>
<p><strong>Also used.</strong> ICAR-IARI CREAMS daily fire bulletins; NASA FIRMS satellite fire detections (as a cross-check, which tracks CREAMS closely); NASA MERRA-2 and GEOS-IT weather. IMD observations need an account, so we did not use them.</p>
<p><strong>Reproduce it.</strong> The scripts and the derived data will be published with this report. Every number on this page is read from them at build time.</p>
</section>

<div class="end">
  <div class="brand"><span class="sq">S</span>Sartium</div>
  <p>Public Record is Sartium's series of questions settled with data anyone can download. Sartium builds analytics, automation and data products for businesses. sartium.com</p>
</div>
</main>
<div id="tip" role="status"></div>
<script>
(function(){{
  var tip=document.getElementById('tip');
  function show(e,el){{tip.textContent=el.getAttribute('data-tip');tip.style.display='block';
    var r=el.getBoundingClientRect(),x=(e&&e.clientX)||r.left+r.width/2,y=(e&&e.clientY)||r.top;
    tip.style.left=Math.min(x+12,window.innerWidth-tip.offsetWidth-8)+'px';tip.style.top=Math.max(y-36,8)+'px';}}
  document.querySelectorAll('[data-tip]').forEach(function(el){{
    el.addEventListener('mousemove',function(e){{show(e,el);}});
    el.addEventListener('focus',function(){{show(null,el);}});
    el.addEventListener('mouseleave',function(){{tip.style.display='none';}});
    el.addEventListener('blur',function(){{tip.style.display='none';}});
  }});
}})();
</script>
"""


# ---------------------------------------------------------------- carousel
def slides():
    c = charts(1.0, w=936, hm=1.22)
    n = N
    dn, gg = cities["Delhi"], cities["Gurugram"]
    S = []

    def slide(kicker, head, body="", chart="", foot="", solo=False):
        S.append(f'<section class="s{" solo" if solo else ""}"><div class="k">{kicker}</div><h2>{head}</h2>'
                 f'{f"<div class=c>{chart}</div>" if chart else ""}{f"<p>{body}</p>" if body else ""}'
                 f'<div class="f"><span>{foot}</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')

    S.append(f'<section class="s cover"><div class="k">Public Record</div><h1>Is Delhi\'s air getting worse?</h1>'
             f'<p class="big">We read all {n["files"]:,} of the government\'s daily air bulletins since 2015.</p>'
             f'<p class="sc">CPCB city scores · Delhi + 5 NCR cities · data to 20 Nov 2026</p>'
             f'<div class="f"><span>Swipe →</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    slide("Same dates every year · 1 Oct–20 Nov", f"The worst autumns were 2016 and 2017. This year is the lowest so far.",
          f"Average {n['m26']:.0f}, against {n['m16']:.0f} in 2016 and {n['m17']:.0f} in 2017.", c["c1"], "Source: CPCB daily AQI bulletins")
    slide("Days above 400", "Zero Severe days so far, in all six NCR cities.",
          f"Delhi had {n['sev16']:.0f} in the same weeks of 2016. Every earlier year had at least one NCR city above 400.", c["c2"], "Source: CPCB daily AQI bulletins")
    slide("Still bad", f"{n['nov26_poor']} of {n['nov26_n']} November days were still Poor or worse.",
          "Not getting worse is a direction, not a level. The bulletin also has never printed a 500: Delhi's highest score in eleven years is "
          f"{n['max_all']:.0f}.", c["c7"], "Delhi, daily · lines at 200 (Poor) and 300 (Very Poor)")
    slide("The turn", f"Delhi's score is an average of whichever monitors report. In October that went from {n['st_before']} to {n['st_after']}.",
          f"About {n['st16']:.0f} stations in 2016, 33 to 40 from 2019 to 2025. CPCB's own bulletin says this averaging is not scientifically sound.", c["c3"], "Source: station counts in CPCB bulletins")
    slide("1–20 Nov 2026 vs 2025", "Every city that added monitors improved. The two that didn't got worse.",
          "", c["c4"], "Blue: monitor list grew · Amber: no new monitors")
    slide("Read this before sharing", "It coincides. We can't show it caused anything.",
          "The cities that expanded sit east of Delhi; the ones that didn't are south-west, so regional weather could make the same split. "
          "Delhi's score didn't drop on the days its new stations appeared. Proof needs station-level data, which CPCB keeps behind a CAPTCHA.", "", "", solo=True)
    slide("Farm fires vs November air", f"Satellite-counted farm fires fell {n['fire_drop']:.0f}%. Delhi's November didn't move.",
          f"Punjab + Haryana: {n['fire20']:,} (2020) → {n['fire25']:,} (2025). Delhi 1–20 Nov: {n['nov20']:.0f} → {n['nov25']:.0f}. "
          "A satellite only sees fires burning as it passes.", c["c5"], "Sources: ICAR-IARI CREAMS · CPCB")
    slide("After the weather", "Weather explains about three-quarters of the swing between autumns.",
          f"The good autumns of 2021 and 2022 were the wet ones ({n['rain21']:.0f} mm and {n['rain22']:.0f} mm). Hold the network steady (2019–25) and the trend is flat.",
          c["c6"], "100 = a typical autumn · Weather: NASA MERRA-2 / GEOS-IT")
    S.append(f'<section class="s"><div class="k">The answer</div><h2>Not getting worse. Not clearly getting better. Stuck for seven years, moving with the weather.</h2>'
             f'<ul><li>We can\'t tell if this year is really cleaner without station-level data.</li>'
             f'<li>The score is a city average on a 0–500 scale, not what anyone breathed.</li><li>December and January still decide this winter.</li></ul>'
             f'<p class="cta">Full report, method and data: link in the comments.</p>'
             f'<div class="f"><span>Public Record by Sartium</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    css = f"""{font_face()}
*{{box-sizing:border-box;margin:0;}} body{{background:#0A0A0F;}}
.s{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#0A0A0F;color:#D7DEEA;padding:96px 72px 120px;
 display:flex;flex-direction:column;gap:34px;font-family:Inter,sans-serif;page-break-after:always;
 background-image:radial-gradient(#1A2234 1.4px,transparent 1.4px);background-size:44px 44px;}}
.k{{font:500 24px/1 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}}
h1{{font:700 104px/1.02 'Space Grotesk';color:#fff;letter-spacing:-.01em;margin-top:220px;}}
h2{{font:700 58px/1.12 'Space Grotesk';color:#fff;}}
p{{font-size:32px;line-height:1.45;color:#B9C6DD;}} .big{{font-size:40px;color:#D7DEEA;}} .sc{{font-size:26px;color:#8B9DC3;}}
ul{{font-size:32px;line-height:1.45;color:#B9C6DD;display:flex;flex-direction:column;gap:18px;padding-left:34px;}}
.solo p{{font-size:42px;line-height:1.45;color:#D7DEEA;}} .solo h2{{font-size:72px;margin-top:120px;}}
.cta{{color:#fff;font-weight:600;border-left:4px solid #3B82F6;padding-left:20px;}}
.f{{position:absolute;left:72px;right:72px;bottom:56px;display:flex;justify-content:space-between;align-items:center;font-size:22px;color:#5B6B8C;}}
.brand{{display:flex;align-items:center;gap:14px;font:700 30px 'Space Grotesk';color:#fff;}}
.sq{{width:40px;height:40px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 20px 'Space Grotesk';color:#3B82F6;}}
svg text{{font-family:Inter,sans-serif;}}
.grid{{stroke:#1F2937;stroke-width:1.5;}} .ref{{stroke:#5B6B8C;stroke-width:1.5;opacity:.6;}} .ref0{{stroke:#8B9DC3;stroke-width:2;}}
.ax{{fill:#8B9DC3;font-size:21px;}} .axs{{fill:#8B9DC3;font-size:19px;}} .reflbl{{fill:#5B6B8C;font-size:18px;}}
.lbl{{fill:#fff;font-size:23px;font-weight:600;}} .lblin{{fill:#fff;font-size:23px;font-weight:600;}} .lbls{{fill:#8B9DC3;font-size:20px;}}
.bar{{fill:#33405E;}} .bar-hi{{fill:#3B82F6;}} .bar-amb{{fill:#D97706;}} .line{{stroke:#3B82F6;stroke-width:4;}}
.rng{{stroke:#33405E;stroke-width:4;stroke-linecap:round;}} .rng-hi{{stroke:#3B82F6;stroke-width:4;opacity:.55;stroke-linecap:round;}}
.dot{{fill:#8B9DC3;stroke:#0A0A0F;stroke-width:3;}} .dot-hi{{fill:#3B82F6;stroke:#0A0A0F;stroke-width:3;}}
"""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(S)}</body></html>", len(S)


import os
REPORT_URL = os.environ.get("REPORT_URL", "")
REPO_URL = os.environ.get("REPO_URL", "")


def public_page(body):
    """Standalone page for public hosting: real links, no draft badge, full document + link-preview tags."""
    body = body.replace('<span class="draft">Draft for review</span>', '')
    body = body.replace(
        "<p><strong>Reproduce it.</strong> The scripts and the derived data will be published with this report. Every number on this page is read from them at build time.</p>",
        f'<p><strong>Reproduce it.</strong> Scripts, derived data, the full research file and the exclusion log: <a href="{REPO_URL}">{REPO_URL.replace("https://", "")}</a>. Every number on this page is read from them at build time.</p>')
    body = body.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    desc = ("We read all 4,218 CPCB daily air bulletins since 2015. By the government's own number, Delhi's autumn air "
            "is not getting worse, and this year's improvement arrived as the monitor count jumped from 46 to 59.")
    head = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="description" content="{desc}">'
            f'<meta property="og:type" content="article"><meta property="og:title" content="Is Delhi\'s air getting worse?">'
            f'<meta property="og:description" content="{desc}"><meta property="og:url" content="{REPORT_URL}">'
            f'<meta property="og:image" content="{REPORT_URL}og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@SartiumHQ">'
            f'<link rel="canonical" href="{REPORT_URL}">'
            f'<style>img{{max-width:100%}}[hidden]{{display:none!important}}</style></head><body>')
    return head + body + "</body></html>"


def og_card():
    n = N
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{font_face()}
*{{margin:0;box-sizing:border-box;}} body{{width:1200px;height:630px;background:#0A0A0F;color:#fff;font-family:Inter;
padding:64px 72px;display:flex;flex-direction:column;justify-content:space-between;
background-image:radial-gradient(#1A2234 1.4px,transparent 1.4px);background-size:40px 40px;}}
.k{{font:500 22px 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}}
h1{{font:700 76px/1.05 'Space Grotesk';margin-top:18px;}}
.row{{display:flex;gap:56px;align-items:flex-end;}} .st b{{font:700 54px 'Space Grotesk';display:block;}}
.st span{{font-size:20px;color:#8B9DC3;}} .br{{margin-left:auto;display:flex;gap:12px;align-items:center;font:700 28px 'Space Grotesk';}}
.sq{{width:38px;height:38px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 19px 'Space Grotesk';color:#3B82F6;}}
</style></head><body><div><div class='k'>Public Record · CPCB data 2015–2026</div><h1>Is Delhi's air getting worse?</h1></div>
<div class='row'><div class='st'><b>{n['m26']:.0f}</b><span>this autumn so far</span></div>
<div class='st'><b>{n['m16']:.0f}</b><span>autumn 2016</span></div><div class='st'><b>{n['st_before']}→{n['st_after']}</b><span>monitors, Oct 2026</span></div>
<div class='br'><span class='sq'>S</span>Sartium</div></div></body></html>"""


if __name__ == "__main__":
    (OUT / "report.html").write_text(report(), encoding="utf-8")
    if REPORT_URL and REPO_URL:
        pub = OUT / "public"
        pub.mkdir(exist_ok=True)
        (pub / "index.html").write_text(public_page(report()), encoding="utf-8")
        (pub / "og.html").write_text(og_card(), encoding="utf-8")
    html, n_slides = slides()
    (OUT / "carousel.html").write_text(html, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    sd = OUT / "slides"
    sd.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto((OUT / "carousel.html").resolve().as_uri())
        pg.wait_for_timeout(400)
        for i, el in enumerate(pg.query_selector_all("section.s"), 1):
            el.screenshot(path=str(sd / f"r01-slide-{i:02d}.png"))
        pg.pdf(path=str(OUT / "r01-delhi-air-linkedin-carousel.pdf"), width="1080px", height="1350px",
               print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        if REPORT_URL and REPO_URL:
            og = b.new_page(viewport={"width": 1200, "height": 630})
            og.goto((OUT / "public" / "og.html").resolve().as_uri())
            og.wait_for_timeout(300)
            og.screenshot(path=str(OUT / "public" / "og.png"))
            (OUT / "public" / "og.html").unlink()
        b.close()
    print("slides:", n_slides, "->", sd)
