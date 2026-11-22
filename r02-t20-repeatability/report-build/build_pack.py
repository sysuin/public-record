"""Build the R02 publishing pack: report page (HTML), carousel slides (PNG), LinkedIn PDF and, with
REPORT_URL and REPO_URL set, a public page + link-preview image.

Run:  python3 -I pack/build_pack.py <report_dir> <fonts_dir> <out_dir>
Every number is read from data/ at build time. The only fixed facts typed in are about the source
download itself (file and competition counts, withheld matches), taken from research.md §1.
"""
import base64, json, os, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts as C  # noqa: E402

REP, FONTS, OUT = (Path(a) for a in sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)
D = REP / "data"
REPORT_URL = os.environ.get("REPORT_URL", "")
REPO_URL = os.environ.get("REPO_URL", "")

# fixed facts about the download (research.md §1)
FILES, COMPS, WITHHELD, DL_DATE = 14419, 32, 386, "21 November 2026"

ver = pd.read_csv(D / "verification_independent.csv")
vv = {r.headline.strip(): r.main for r in ver.itertuples()}
MATCHES, BALLS = int(vv["kept matches"]), int(vv["kept balls (all deliveries)"])

sig = pd.read_csv(D / "signal_summary_main.csv")
men = sig[sig.scope == "Men: all franchise/domestic leagues"].set_index("metric")
ipl_sig = sig[sig.scope == "IPL"].set_index("metric")
wom = sig[sig.scope == "Women: all franchise/domestic leagues"].set_index("metric")
fc = pd.read_csv(D / "forecast_contest.csv")
q = pd.read_csv(D / "edge_kept_quintiles.csv")
br = pd.read_csv(D / "breakouts.csv")
cl = pd.read_csv(D / "cross_league.csv")
sv = pd.read_csv(D / "survivorship.csv")
tune = pd.read_csv(D / "forecast_tuning.csv")


def fx(scope, split, metric, f):
    r = fc[(fc.scope == scope) & (fc.split == split) & (fc.metric == metric) & (fc.forecast == f)]
    return float(r.explained_pct.iloc[0])


MS, TR, RV = "Men: all franchise/domestic leagues", "train<=2019,test>=2020", "train>=2020,test<=2019"
qm = q[(q.scope == MS) & (q.metric == "sr")].set_index("quintile")
qe = q[(q.scope == MS) & (q.metric == "econ")].set_index("quintile")
qw = q[(q.scope == MS) & (q.metric == "wktrate")].set_index("quintile")
b_sr = br[(br.metric == "sr") & (br.scope == MS)].iloc[0]
b_ec = br[(br.metric == "econ") & (br.scope == MS)].iloc[0]
smat = cl[(cl.metric == "sr") & (cl.target == "IPL") & (cl.source == "GROUP: SMAT")].iloc[0]
smat_ec = cl[(cl.metric == "econ") & (cl.target == "IPL") & (cl.source == "GROUP: SMAT")].iloc[0]
over = cl[(cl.metric == "sr") & (cl.target == "IPL") & (cl.source == "GROUP: overseas leagues + Hundred")].iloc[0]
t20i = cl[(cl.metric == "sr") & (cl.target == "IPL") & (cl.source == "GROUP: T20I")].iloc[0]
iplown = cl[(cl.metric == "sr") & (cl.target == "IPL") & (cl.source == "IPL")].iloc[0]
svm = sv[(sv.scope == MS) & (sv.metric == "sr")].set_index("quintile_best5")
k_sr = int(tune[(tune.metric == "sr") & (tune.scope == MS) & (tune.split == TR)].K_F5.iloc[0])
k_ec = int(tune[(tune.metric == "econ") & (tune.scope == MS) & (tune.split == TR)].K_F5.iloc[0])

N = dict(
    matches=MATCHES, balls=BALLS,
    r_sr=men.loc["sr"].r_yoy, r_ec=men.loc["econ"].r_yoy, r_wk=men.loc["wktrate"].r_yoy, r_avg=men.loc["avg"].r_yoy,
    r_bnd=men.loc["bndpct"].r_yoy, r_bdot=men.loc["bdotpct"].r_yoy, r_ecadj=men.loc["econ_adj"].r_yoy,
    r_wkadj=men.loc["wkt_adj"].r_yoy, r_pp=men.loc["bowl_pp_share"].r_yoy, r_death=men.loc["bowl_death_share"].r_yoy,
    r_ipl=ipl_sig.loc["sr"].r_yoy, r_wom=wom.loc["sr"].r_yoy,
    k_sr=men.loc["sr"].balls_to_half_signal, k_ec=men.loc["econ"].balls_to_half_signal,
    k_wk=men.loc["wktrate"].balls_to_half_signal, k_avg=men.loc["avg"].balls_to_half_signal,
    k_bnd=men.loc["bndpct"].balls_to_half_signal, k_dot=men.loc["dotpct"].balls_to_half_signal,
    season=men.loc["sr"].typical_season_balls,
    pairs=int(men.loc["sr"].pairs),
    q5n=qm.loc[5].mean_N, q5n1=qm.loc[5].mean_N1, q5kept=qm.loc[5].kept_pct,
    e5kept=qe.loc[1].kept_pct, w5kept=qw.loc[5].kept_pct,
    bsr_kept=b_sr.kept_pct, bsr_jump=b_sr.jump, bsr_n=int(b_sr.n),
    bec_kept=b_ec.kept_pct, bec_n=int(b_ec.n),
    f1_sr=fx(MS, TR, "sr", "F1"), f1_ec=fx(MS, TR, "econ", "F1"), f1_wk=fx(MS, TR, "wktrate", "F1"),
    f2_sr=fx(MS, TR, "sr", "F2"), f5_sr=fx(MS, TR, "sr", "F5"), f5_ec=fx(MS, TR, "econ", "F5"),
    f5_bnd=fx(MS, TR, "bndpct", "F5"), f6_sr=fx(MS, TR, "sr", "F6"),
    ipl_f1=fx("IPL", TR, "sr", "F1"), ipl_f5=fx("IPL", TR, "sr", "F5"),
    ipl_ec1=fx("IPL", TR, "econ", "F1"), ipl_ec5=fx("IPL", TR, "econ", "F5"),
    w_f1=fx("Women: all franchise/domestic leagues", TR, "sr", "F1"), w_f5=fx("Women: all franchise/domestic leagues", TR, "sr", "F5"),
    rv_f1=fx(MS, RV, "sr", "F1"), rv_f5=fx(MS, RV, "sr", "F5"),
    smat_gap=smat.gap, smat_n=int(smat.n), smat_src=smat.mean_source, smat_ec_r=smat_ec.r,
    over_r=over.r, t20i_r=t20i.r, iplown_r=iplown.r,
    back_bottom=svm.loc[1].back_main * 100, back_rest=svm.loc[[2, 3, 4, 5]].back_main.mean() * 100,
    k=k_sr, kec=k_ec,
)
N["ex"] = 30 * 250 / (250 + N["k"])
for _k in ("k_sr", "k_ec", "k_wk", "k_avg", "k_bnd", "k_dot", "season"):
    N[_k] = float(round(N[_k], -1))
print(json.dumps({k: (round(float(v), 3) if isinstance(v, float) else v) for k, v in N.items()}, indent=1))


def pct(v):
    return f"{v:+.0f}%".replace("-", "−")


def charts(scale=1.0, w=960, hm=1.0):
    n = N
    contest = [
        ("Last season at face value", n["f1_sr"], "bar-amb", f"Last season as recorded: {n['f1_sr']:.0f}%"),
        ("Career at face value", n["f2_sr"], "bar-amb" if n["f2_sr"] < 0 else "bar-hi", f"Career to date: {n['f2_sr']:.0f}%"),
        ("Last season, pulled to average", fx(MS, TR, "sr", "F4"), "bar-hi", ""),
        ("Recent seasons, pulled to average", n["f5_sr"], "bar-hi", ""),
        ("+ every other T20 league", n["f6_sr"], "bar-hi", ""),
    ]
    contest = [(a, b, c, d or f"{a}: {b:+.0f}%") for a, b, c, d in contest]
    balls = [("Boundary %", n["k_bnd"]), ("Dot-ball % (batting)", n["k_dot"]), ("Strike rate", n["k_sr"]),
             ("Economy rate", n["k_ec"]), ("Wickets per ball", n["k_wk"]), ("Batting average", n["k_avg"])]
    balls_rows = [(a, b, "bar-hi" if b < n["season"] * 1.6 else "bar", f"{a}: about {b:,.0f} balls") for a, b in balls]
    repeat = [("Share of overs in the powerplay", n["r_pp"], "bar-hi"), ("Share of overs at the death", n["r_death"], "bar-hi"),
              ("Dot-ball % (bowling)", n["r_bdot"], "bar"), ("Boundary % (batting)", n["r_bnd"], "bar"),
              ("Economy rate", n["r_ec"], "bar"), ("Strike rate", n["r_sr"], "bar"),
              ("Wickets per ball", n["r_wk"], "bar"), ("Batting average", n["r_avg"], "bar")]
    repeat_rows = [(a, b, c, f"{a}: {b:.2f}") for a, b, c in repeat]
    kept = [("Best fifth of economy seasons", n["e5kept"]), ("Best fifth of strike-rate seasons", n["q5kept"]),
            ("Breakout batters", n["bsr_kept"]), ("Breakout bowlers", n["bec_kept"]),
            ("Best fifth of wicket-taking seasons", n["w5kept"])]
    kept_rows = [(a, b, "bar-hi", f"{a}: kept {b:.0f}%") for a, b in kept]
    qa = [float(qm.loc[i].mean_N) for i in range(1, 6)]
    qb = [float(qm.loc[i].mean_N1) for i in range(1, 6)]
    return dict(
        c1=C.hbars(contest, w=w, h=int(430 * scale * hm), scale=scale, xmin=-50, xmax=25,
                   ticks=(-40, -20, 0, 20), tickfmt=lambda v: pct(v) if v else "0", fmt=lambda v: pct(v), padl=400,
                   label="How much each forecast cuts the error against assuming every player is league average (strike rate)"),
        c2=C.grouped_pairs(["Worst fifth", "2nd", "Middle", "4th", "Best fifth"], qa, qb, w=w, h=int(520 * scale * hm),
                           scale=scale, a_name="This season", b_name="Next season",
                           label="Strike rate against league average, this season and the next, by fifth"),
        c3=C.hbars(balls_rows, w=w, h=int(470 * scale * hm), scale=scale, xmax=1900, ref=n["season"],
                   reflabel=f"a regular's season ≈ {n['season']:.0f} balls", ticks=(0, 500, 1000, 1500),
                   tickfmt=lambda v: f"{v:,.0f}", fmt=lambda v: f"{v:,.0f}", padl=300,
                   label="Balls needed before a number reflects more skill than luck"),
        c4=C.hbars(repeat_rows, w=w, h=int(560 * scale * hm), scale=scale, xmax=1.0, ticks=(0, 0.25, 0.5, 0.75, 1.0),
                   tickfmt=lambda v: f"{v:g}", fmt=lambda v: f"{v:.2f}", padl=380,
                   label="How closely next season follows this one, 0 = no link, 1 = identical"),
        c5=C.hbars(kept_rows, w=w, h=int(430 * scale * hm), scale=scale, xmax=100, ref=100, reflabel="",
                   ticks=(0, 25, 50, 75, 100), tickfmt=lambda v: f"{v:.0f}%", fmt=lambda v: f"{v:.0f}%", padl=410,
                   label="Share of an above-average edge still there the next season"),
    )


def font_face():
    def ff(fam, wt, file):
        b = base64.b64encode((FONTS / file).read_bytes()).decode()
        return f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,{b}) format('woff2');}}"
    return "".join([ff("Space Grotesk", 700, "space-grotesk-latin-700-normal.woff2"),
                    ff("Space Grotesk", 500, "space-grotesk-latin-500-normal.woff2"),
                    ff("Inter", 400, "inter-latin-400-normal.woff2"), ff("Inter", 600, "inter-latin-600-normal.woff2")])


def table(headers, body):
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
    return f'<details class="tbl"><summary>Show the numbers</summary><div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>'


PAGE_CSS = """
:root{--bg:#0A0A0F;--panel:#0F1420;--ink:#FFFFFF;--body:#D7DEEA;--muted:#8B9DC3;--faint:#5B6B8C;--rule:#1F2937;
 --accent:#3B82F6;--amber:#D97706;--ctx:#33405E;--chip:#13203A;
 --display:'Space Grotesk',ui-sans-serif,system-ui,sans-serif;--text:'Inter',ui-sans-serif,system-ui,sans-serif;color-scheme:dark;}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#F6F7FA;--panel:#FFFFFF;--ink:#0B1220;--body:#253149;
 --muted:#4B5A78;--faint:#7A88A6;--rule:#E1E6EF;--accent:#2563EB;--amber:#B45309;--ctx:#B9C3D6;--chip:#E7EEFC;color-scheme:light;}}
:root[data-theme="light"]{--bg:#F6F7FA;--panel:#FFFFFF;--ink:#0B1220;--body:#253149;--muted:#4B5A78;--faint:#7A88A6;--rule:#E1E6EF;
 --accent:#2563EB;--amber:#B45309;--ctx:#B9C3D6;--chip:#E7EEFC;color-scheme:light;}
body{background:var(--bg);color:var(--body);font:400 17px/1.65 var(--text);margin:0;
 padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));}
main{max-width:760px;margin:0 auto;padding-block:48px 80px;display:flex;flex-direction:column;gap:22px;}
h1,h2{font-family:var(--display);color:var(--ink);text-wrap:balance;margin:0;}
h1{font-size:clamp(2.1rem,5.4vw,3.3rem);line-height:1.08;font-weight:700;letter-spacing:-.01em;}
h2{font-size:1.55rem;line-height:1.2;font-weight:700;margin-top:30px;}
p{margin:0;} strong{color:var(--ink);font-weight:600;} a{color:var(--accent);}
a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.kick{font:500 .78rem/1 var(--display);letter-spacing:.16em;text-transform:uppercase;color:var(--accent);display:flex;gap:12px;flex-wrap:wrap;align-items:center;}
.draft{background:var(--chip);color:var(--muted);padding:5px 9px;letter-spacing:.08em;}
.dek{font-size:1.2rem;line-height:1.55;} .byline{font-size:.88rem;color:var(--muted);}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin-top:8px;}
.stat{background:var(--bg);padding:18px 16px;display:flex;flex-direction:column;gap:6px;min-width:0;}
.stat b{font:700 2.2rem/1 var(--display);color:var(--ink);} .stat span{font-size:.86rem;line-height:1.4;color:var(--muted);}
figure{margin:10px 0 4px;display:flex;flex-direction:column;gap:10px;}
figcaption{font:600 .98rem/1.35 var(--text);color:var(--ink);} figure .src{font-size:.8rem;color:var(--faint);}
.note{border-left:3px solid var(--amber);padding:4px 0 4px 16px;}
.quote{font:500 1.12rem/1.5 var(--display);color:var(--ink);border-left:3px solid var(--accent);padding:2px 0 2px 16px;}
ul,ol{margin:0;padding-left:22px;display:flex;flex-direction:column;gap:8px;}
.method{background:var(--panel);border:1px solid var(--rule);padding:22px;display:flex;flex-direction:column;gap:12px;font-size:.93rem;}
.method h2{margin-top:0;font-size:1.2rem;}
code{font-size:.86em;background:var(--chip);padding:1px 5px;word-break:break-all;}
.tbl summary{cursor:pointer;font-size:.85rem;color:var(--muted);}
.tw{overflow-x:auto;} table{border-collapse:collapse;font-size:.88rem;margin-top:8px;font-variant-numeric:tabular-nums;}
th,td{text-align:left;padding:5px 14px 5px 0;border-bottom:1px solid var(--rule);} th{color:var(--muted);font-weight:600;}
.end{font-size:.9rem;color:var(--muted);border-top:1px solid var(--rule);padding-top:18px;display:flex;flex-direction:column;gap:8px;}
.brand{display:flex;align-items:center;gap:10px;font:700 1.05rem var(--display);color:var(--ink);}
.sq{width:26px;height:26px;border:2px solid var(--accent);display:grid;place-items:center;font:700 .8rem var(--display);color:var(--accent);}
#tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--rule);padding:6px 9px;font-size:.82rem;display:none;z-index:5;}
svg text{font-family:var(--text);}
.grid{stroke:var(--rule);stroke-width:1;} .ref{stroke:var(--faint);stroke-width:1;opacity:.6;} .ref0{stroke:var(--muted);stroke-width:1.5;}
.refstrong{stroke:var(--ink);stroke-width:1.5;opacity:.7;}
.ax{fill:var(--muted);font-size:15px;} .axs{fill:var(--muted);font-size:14px;} .reflbl{fill:var(--faint);font-size:13px;} .reflbl2{fill:var(--ink);font-size:14px;}
.lbl{fill:var(--ink);font-size:16px;font-weight:600;} .lblin{fill:#fff;font-size:16px;font-weight:600;} .lbls{fill:var(--muted);font-size:14px;}
.bar{fill:var(--ctx);} .bar-hi{fill:var(--accent);} .bar-amb{fill:var(--amber);}
[data-tip]{cursor:default;} [data-tip]:hover{opacity:.85;}
@media (max-width:560px){.stats{grid-template-columns:1fr;} body{font-size:16px;}}
"""

TIP_JS = """<div id="tip" role="status"></div><script>(function(){var t=document.getElementById('tip');
function s(e,el){t.textContent=el.getAttribute('data-tip');t.style.display='block';var r=el.getBoundingClientRect(),
x=(e&&e.clientX)||r.left+r.width/2,y=(e&&e.clientY)||r.top;t.style.left=Math.min(x+12,innerWidth-t.offsetWidth-8)+'px';
t.style.top=Math.max(y-36,8)+'px';}document.querySelectorAll('[data-tip]').forEach(function(el){
el.addEventListener('mousemove',function(e){s(e,el)});el.addEventListener('focus',function(){s(null,el)});
el.addEventListener('mouseleave',function(){t.style.display='none'});el.addEventListener('blur',function(){t.style.display='none'});});})();</script>"""


def report():
    c = charts(1.0)
    n = N
    t1 = table(["Forecast", "Error removed vs “everyone is league average”"],
               [["Last season, as recorded", pct(n["f1_sr"])], ["Career so far, as recorded", pct(n["f2_sr"])],
                ["Last season, pulled toward average", pct(fx(MS, TR, "sr", "F4"))],
                ["Recent seasons weighted + pulled toward average", pct(n["f5_sr"])], ["…plus every other T20 league", pct(n["f6_sr"])]])
    t2 = table(["This season's fifth", "This season", "Next season"],
               [[g, f"{qm.loc[i].mean_N:+.1f}", f"{qm.loc[i].mean_N1:+.1f}"] for i, g in
                zip(range(1, 6), ["Worst", "2nd", "Middle", "4th", "Best"])])
    t3 = table(["Number", "Balls before skill outweighs luck"],
               [[a, f"{b:,.0f}"] for a, b in [("Boundary %", n["k_bnd"]), ("Dot-ball % (batting)", n["k_dot"]),
                ("Strike rate", n["k_sr"]), ("Economy rate", n["k_ec"]), ("Wickets per ball", n["k_wk"]), ("Batting average", n["k_avg"])]])
    return f"""<title>Does One T20 Season Predict the Next?</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>/* Layout: one reading column (~68ch); Sartium dark canvas first, light mirror. */{PAGE_CSS}</style>
<main>
<div class="kick"><span>Public Record · Sartium</span><span class="draft">Draft for review</span></div>
<h1>Does one T20 season predict the next?</h1>
<p class="dek">We followed every player through {n['matches']:,} T20 matches across {COMPS} competitions, {n['balls']/1e6:.2f} million balls in all. Taken at face value, a player's last season is a worse guide to his next one than assuming he is exactly average. Here is what works instead, in time for this month's IPL auction.</p>
<p class="byline">Data: Cricsheet ball-by-ball records, 2008–2026 · Every figure is measured against that league's average that season</p>
<div class="stats">
  <div class="stat"><b>{pct(n['f1_sr'])}</b><span>Error added by taking last season's strike rate at face value, against calling everyone average.</span></div>
  <div class="stat"><b>{n['k_sr']:,.0f}</b><span>Balls before a strike rate reflects more skill than luck. A regular faces about {n['season']:.0f} a season.</span></div>
  <div class="stat"><b>{n['q5kept']:.0f}%</b><span>Share of their edge that the best fifth of strike-rate seasons kept the next year.</span></div>
</div>

<h2>The answer everyone assumes</h2>
<p>Every December, franchises spend crores on the strength of the season just gone. A batter who struck at 180 is in form; a bowler who went at six an over is a find. The assumption underneath is simple: what a player did last season is roughly what he will do next season. We tested how much of a season actually carries over.</p>

<h2>The source</h2>
<p>Cricsheet, a long-running volunteer project, transcribes every ball of every match from the official scorecards and publishes them free at <code>cricsheet.org/downloads</code>. We downloaded every T20 competition it covers on {DL_DATE}: {FILES:,} matches. After removing rain-shortened, abandoned and reduced-overs games, and internationals involving associate nations, <strong>{n['matches']:,} matches and {n['balls']:,} deliveries</strong> remain: the IPL, Big Bash, PSL, CPL, SA20, ILT20, the Blast, Syed Mushtaq Ali and ten more men's competitions, ten women's competitions, The Hundred, and internationals between full members.</p>
<p>The leagues publish scorecards one match at a time. Cricsheet is the only place they exist as one download, so it stands in for the official record here, and {WITHHELD} matches it has not released are missing.</p>
<p class="note">Every number in this report compares a player with the average of his league in that season. A strike rate of 150 in a league that scored at 140 counts as +10. Without that step, league-wide scoring rises (the IPL's in 2023–26, for example) make players look more consistent than they are.</p>

<h2>What the obvious numbers say</h2>
<p>Take every batter who faced at least 120 balls in two seasons running in the same men's league ({n['pairs']:,} pairs) and put this season's strike rate next to the next one. <strong>Last season explains about a tenth of next season.</strong> For economy rate it is about a sixth, for wicket-taking under 4 per cent, and for batting average under 3 per cent. The IPL looks like every other league.</p>
<figure><figcaption>How closely next season follows this one (0 = no link, 1 = identical)</figcaption><div class="chart">{c['c4']}</div>
<span class="src">Men's franchise and domestic leagues, players with 120+ balls in both seasons. Blue: the role a player is given. Grey: what he produced.</span></figure>
<p>What repeats strongly is the job. Whether a bowler is used in the powerplay repeats at {n['r_pp']:.2f}; how well he bowls repeats at {n['r_ec']:.2f}, and only {n['r_ecadj']:.2f} once you allow for the overs he is given.</p>

<h2>The turn: a season is mostly luck</h2>
<p>Split one season into a player's odd and even matches and the two halves barely agree. The reason is size. A season is small, and a few big innings or one bad over move the numbers a long way.</p>
<figure><figcaption>Balls needed before a number reflects more skill than luck</figcaption><div class="chart">{c['c3']}</div>
<span class="src">Men's franchise and domestic leagues. The vertical line marks a regular's season.</span>{t3}</figure>
<p>A strike rate needs about <strong>{n['k_sr']:,.0f} balls</strong> before it is more skill than luck, and a regular faces about {n['season']:.0f} in a season, so a full season's strike rate is still roughly half noise. Boundary percentage settles faster, at about {n['k_bnd']:,.0f} balls. A wicket rate needs about {n['k_wk']:,.0f} balls, roughly six seasons of a regular bowler, and a batting average about {n['k_avg']:,.0f}, seven or eight seasons.</p>
<p>So the best seasons fall back hardest. The top fifth of strike-rate seasons were <strong>{n['q5n']:.0f} runs per 100 balls</strong> above their league's average. The next year the same players were {n['q5n1']:.0f} above.</p>
<figure><figcaption>Strike rate against league average, this season and the next</figcaption><div class="chart">{c['c2']}</div>
<span class="src">Players grouped into fifths by this season's strike rate (men's leagues, 120+ balls both seasons).</span>{t2}</figure>
<figure><figcaption>How much of an above-average edge is still there the next season</figcaption><div class="chart">{c['c5']}</div>
<span class="src">Breakout batters beat their own career strike rate by 15+; breakout bowlers were 0.75+ an over cheaper than their career.</span></figure>
<p>Breakout batters, whose season beat their own career strike rate by {n['bsr_jump']:.0f} on average, kept {n['bsr_kept']:.0f}% of the jump. Breakout bowlers kept {n['bec_kept']:.0f}%.</p>

<h2>The corrected answer</h2>
<p>We tested five ways of predicting the next season. Every setting was chosen on 2008–2019 and then scored on 2020–2026, seasons the methods had never seen.</p>
<figure><figcaption>Error removed against assuming every player is league average (strike rate)</figcaption><div class="chart">{c['c1']}</div>
<span class="src">Men's leagues, forecasting 2020–2026. Amber: worse than calling everyone average. Blue: better.</span>{t1}</figure>
<ul>
<li><strong>Last season at face value is the worst option tested.</strong> It adds {abs(n['f1_sr']):.0f}% more error than assuming every player is league average for strike rate, {abs(n['f1_ec']):.0f}% for economy and {abs(n['f1_wk']):.0f}% for wicket rate.</li>
<li><strong>What works is weighting recent seasons more and pulling every number toward the average.</strong> That beats "everyone is average" by {n['f5_sr']:.0f}% for strike rate, {n['f5_ec']:.0f}% for economy and {n['f5_bnd']:.0f}% for boundary percentage, and it beats last season at face value in all 60 combinations of measure, league group and test period we ran.</li>
<li><strong>It holds in the IPL alone</strong> (strike rate {pct(n['ipl_f1'])} → {pct(n['ipl_f5'])}; economy {pct(n['ipl_ec1'])} → {pct(n['ipl_ec5'])}), in women's leagues ({pct(n['w_f1'])} → {pct(n['w_f5'])}), and when the test is run backwards ({pct(n['rv_f1'])} → {pct(n['rv_f5'])}).</li>
</ul>
<p>Two more findings matter for an auction room. Batters arriving from the Syed Mushtaq Ali Trophy were {n['smat_src']:.0f} runs per 100 balls above its average and <strong>level with the IPL average</strong> once they got there ({n['smat_n']} player-seasons), and Mushtaq Ali economy rates showed almost no link to IPL ones ({n['smat_ec_r']:.2f}). Form in overseas leagues was at least as good a guide to an IPL season ({n['over_r']:.2f}) as the IPL's own previous season ({n['iplown_r']:.2f}); the ranges overlap, so "no worse" is the safe reading.</p>
<p class="quote">Last season is evidence, not a forecast. Pull it hard toward the average, add earlier seasons and other leagues, and buy the skills that repeat.</p>

<h2>What this means at the auction table</h2>
<ol>
<li><strong>Never price last season at face value.</strong> On this evidence it is worse than pricing everyone at league average.</li>
<li><strong>Pull every number toward the league average, by balls.</strong> Add roughly {n['k']} balls of average batting to a strike rate and about {n['kec']} balls of average bowling to an economy rate. A batter 30 runs per 100 balls above average in 250 balls, with no other history, projects to about +{n['ex']:.0f} next season.</li>
<li><strong>Use earlier seasons too, leaning on the latest.</strong> Each season back counts roughly two-thirds to four-fifths as much as the one after it.</li>
<li><strong>Buy what repeats.</strong> Boundary percentage, dot balls, economy and a player's role carry over. One season's wicket haul or batting average is close to noise.</li>
<li><strong>Discount domestic strike rates</strong> by roughly {abs(n['smat_gap']):.0f} points before comparing them with IPL numbers, and be most suspicious of the breakout season.</li>
</ol>

<h2>What this data cannot tell you</h2>
<ul>
<li><strong>Why a season went up or down.</strong> Injury, a new role, a new coach and a different home ground are all invisible here.</li>
<li><strong>Pace against spin.</strong> The scorecard does not record bowling type.</li>
<li><strong>Age.</strong> There are no birth dates in the data, so we drew no age curve.</li>
<li><strong>Fielding and keeping.</strong> Not measured.</li>
<li><strong>The players who were not picked again.</strong> Only {n['back_bottom']:.0f}% of the worst fifth of strike-rate seasons were followed by another full season, against about {n['back_rest']:.0f}% of the rest, so every comparison describes players who came back.</li>
<li><strong>Prices.</strong> Cricsheet has no auction data. This says what a season is worth as evidence, not whether any team overpaid.</li>
<li><strong>Which overseas league is the best guide to the IPL.</strong> The samples are too small to rank them.</li>
</ul>

<section class="method">
<h2>How we did it</h2>
<p><strong>Source.</strong> Cricsheet ball-by-ball JSON for all {COMPS} T20 competitions it covers, downloaded {DL_DATE} ({FILES:,} files). Seasons come from match dates. Rain-affected, shortened, abandoned and super-over-only results were removed, and every exclusion is logged.</p>
<p><strong>Measures.</strong> Each player-season is compared with the average of that competition in that season. Players need 120+ balls in both seasons for the season-to-season comparisons (results checked at 30 to 400 balls).</p>
<p><strong>Ranges.</strong> Every figure was re-run on 1,000 reshuffled sets of players, so a result is only reported when it survives that.</p>
<p><strong>Forecasts.</strong> Settings chosen on 2008–2019 targets only, scored on 2020–2026, then run in reverse.</p>
<p><strong>Checks.</strong> Every headline number was computed a second time by independent code. That second pass caught one real bug (dismissals off wides were missing), which is fixed.</p>
<p><strong>Reproduce it.</strong> The scripts and derived data will be published with this report. Every number on this page is read from them at build time.</p>
</section>
<div class="end"><div class="brand"><span class="sq">S</span>Sartium</div>
<p>Public Record is Sartium's series of questions settled with data anyone can download. Data: Cricsheet (Open Data Commons Attribution licence). Sartium builds analytics, automation and data products for businesses. sartium.com</p></div>
</main>{TIP_JS}"""


def slides():
    c = charts(1.0, w=936, hm=1.25)
    n = N
    S = []

    def slide(kicker, head, body="", chart="", foot="", solo=False):
        S.append(f'<section class="s{" solo" if solo else ""}"><div class="k">{kicker}</div><h2>{head}</h2>'
                 f'{f"<div class=c>{chart}</div>" if chart else ""}{f"<p>{body}</p>" if body else ""}'
                 f'<div class="f"><span>{foot}</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')

    S.append(f'<section class="s cover"><div class="k">Public Record · before the IPL auction</div><h1>Does one T20 season predict the next?</h1>'
             f'<p class="big">We followed every player through {n["matches"]:,} matches and {n["balls"]/1e6:.2f} million balls.</p>'
             f'<p class="sc">Cricsheet ball-by-ball · {COMPS} competitions · 2008–2026</p>'
             f'<div class="f"><span>Swipe →</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    slide("Forecasting 2020–2026", "Taking last season at face value is worse than calling everyone average.",
          f"Strike rate: {abs(n['f1_sr']):.0f}% more error. What works: weight recent seasons and pull every number toward average.",
          c["c1"], "All figures vs that league's average that season")
    slide("The best fifth", f"The best strike-rate seasons were +{n['q5n']:.0f}. The next year: +{n['q5n1']:.0f}.",
          f"Runs per 100 balls above league average. They kept {n['q5kept']:.0f}% of their edge.", c["c2"], "Men's leagues, 120+ balls both seasons")
    slide("Why", f"A strike rate needs ~{n['k_sr']:,.0f} balls before skill outweighs luck. A season is ~{n['season']:.0f}.",
          "", c["c3"], "Men's franchise and domestic leagues")
    slide("What repeats", "The job repeats. The output barely does.",
          f"Powerplay role {n['r_pp']:.2f}. Economy {n['r_ec']:.2f}. Wickets {n['r_wk']:.2f}. (0 = no link, 1 = identical)", c["c4"],
          "Men's leagues, season to season")
    slide("Breakouts", f"Breakout batters kept {n['bsr_kept']:.0f}% of the jump. Bowlers kept {n['bec_kept']:.0f}%.",
          "", c["c5"], "Share of an above-average edge kept the next season")
    slide("Domestic to IPL", f"A Mushtaq Ali strike rate arrives about {abs(n['smat_gap']):.0f} points lighter in the IPL.",
          f"Batters were +{n['smat_src']:.0f} above the domestic average and level with the IPL average once there ({n['smat_n']} player-seasons). "
          f"Overseas-league form predicted the IPL at least as well as the IPL's own last season.", "", "Small samples: read as a direction, not a price", solo=True)
    slide("At the auction table", "How to read a season before you pay for it.",
          f"Add ~{n['k']} balls of average batting to a strike rate. +30 above average in 250 balls projects to about +{n['ex']:.0f}. "
          "Use earlier seasons, lean on the latest, and buy boundary %, dot balls, economy and role.", "", "", solo=True)
    slide("Read this before sharing", "What this data can't tell you.",
          "Why a season changed (injury, role, coach, ground). Pace vs spin. Age. Fielding. "
          f"And it only sees players who were picked again: {n['back_bottom']:.0f}% of the worst seasons came back, against ~{n['back_rest']:.0f}%.", "", "", solo=True)
    S.append(f'<section class="s"><div class="k">The answer</div><h2>Last season is evidence, not a forecast.</h2>'
             f'<ul><li>Pull every number hard toward the league average.</li><li>Add earlier seasons and other leagues.</li>'
             f'<li>Buy the skills that repeat, and distrust the breakout.</li></ul>'
             f'<p class="cta">Full report, method and code: link in the comments.</p>'
             f'<div class="f"><span>Data: Cricsheet</span><span class="brand"><span class="sq">S</span>Sartium</span></div></section>')
    css = f"""{font_face()}
*{{box-sizing:border-box;margin:0;}} body{{background:#0A0A0F;}}
.s{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#0A0A0F;color:#D7DEEA;padding:96px 72px 120px;
 display:flex;flex-direction:column;gap:34px;font-family:Inter,sans-serif;page-break-after:always;
 background-image:radial-gradient(#1A2234 1.4px,transparent 1.4px);background-size:44px 44px;}}
.k{{font:500 24px/1 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}}
h1{{font:700 98px/1.02 'Space Grotesk';color:#fff;letter-spacing:-.01em;margin-top:200px;}}
h2{{font:700 56px/1.12 'Space Grotesk';color:#fff;}}
p{{font-size:32px;line-height:1.45;color:#B9C6DD;}} .big{{font-size:40px;color:#D7DEEA;}} .sc{{font-size:26px;color:#8B9DC3;}}
.solo p{{font-size:42px;line-height:1.45;color:#D7DEEA;}} .solo h2{{font-size:72px;margin-top:120px;}}
ul{{font-size:34px;line-height:1.45;color:#B9C6DD;display:flex;flex-direction:column;gap:18px;padding-left:34px;}}
.cta{{color:#fff;font-weight:600;border-left:4px solid #3B82F6;padding-left:20px;}}
.f{{position:absolute;left:72px;right:72px;bottom:56px;display:flex;justify-content:space-between;align-items:center;font-size:22px;color:#5B6B8C;}}
.brand{{display:flex;align-items:center;gap:14px;font:700 30px 'Space Grotesk';color:#fff;}}
.sq{{width:40px;height:40px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 20px 'Space Grotesk';color:#3B82F6;}}
svg text{{font-family:Inter,sans-serif;}}
.grid{{stroke:#1F2937;stroke-width:1.5;}} .ref0{{stroke:#8B9DC3;stroke-width:2;}} .refstrong{{stroke:#fff;stroke-width:2;opacity:.7;}}
.ax{{fill:#8B9DC3;font-size:21px;}} .axs{{fill:#8B9DC3;font-size:19px;}} .reflbl2{{fill:#fff;font-size:20px;}}
.lbl{{fill:#fff;font-size:23px;font-weight:600;}} .lblin{{fill:#fff;font-size:23px;font-weight:600;}} .lbls{{fill:#8B9DC3;font-size:20px;}}
.bar{{fill:#33405E;}} .bar-hi{{fill:#3B82F6;}} .bar-amb{{fill:#D97706;}}
"""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(S)}</body></html>"


def public_page(body):
    body = body.replace('<span class="draft">Draft for review</span>', '')
    body = body.replace("<p><strong>Reproduce it.</strong> The scripts and derived data will be published with this report. Every number on this page is read from them at build time.</p>",
                        f'<p><strong>Reproduce it.</strong> Scripts, derived data, the research file and the exclusion log: <a href="{REPO_URL}">{REPO_URL.replace("https://", "")}</a>. Every number on this page is read from them at build time.</p>')
    body = body.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    desc = (f"{N['matches']:,} T20 matches, {N['balls']/1e6:.2f} million balls: taking last season at face value predicts worse than "
            "assuming every player is average. What works instead, before the IPL auction.")
    head = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="description" content="{desc}"><meta property="og:type" content="article">'
            f'<meta property="og:title" content="Does one T20 season predict the next?"><meta property="og:description" content="{desc}">'
            f'<meta property="og:url" content="{REPORT_URL}"><meta property="og:image" content="{REPORT_URL}og.png">'
            f'<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@SartiumHQ">'
            f'<link rel="canonical" href="{REPORT_URL}"><style>img{{max-width:100%}}[hidden]{{display:none!important}}</style></head><body>')
    return head + body + "</body></html>"


def og_card():
    n = N
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{font_face()}
*{{margin:0;box-sizing:border-box;}} body{{width:1200px;height:630px;background:#0A0A0F;color:#fff;font-family:Inter;padding:64px 72px;
display:flex;flex-direction:column;justify-content:space-between;background-image:radial-gradient(#1A2234 1.4px,transparent 1.4px);background-size:40px 40px;}}
.k{{font:500 22px 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}} h1{{font:700 70px/1.05 'Space Grotesk';margin-top:18px;}}
.row{{display:flex;gap:56px;align-items:flex-end;}} .st b{{font:700 54px 'Space Grotesk';display:block;}} .st span{{font-size:20px;color:#8B9DC3;}}
.br{{margin-left:auto;display:flex;gap:12px;align-items:center;font:700 28px 'Space Grotesk';}}
.sq{{width:38px;height:38px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 19px 'Space Grotesk';color:#3B82F6;}}
</style></head><body><div><div class='k'>Public Record · {n['matches']:,} T20 matches</div><h1>Does one T20 season predict the next?</h1></div>
<div class='row'><div class='st'><b>{abs(n['f1_sr']):.0f}%</b><span>more error from last season at face value</span></div>
<div class='st'><b>{n['k_sr']:,.0f}</b><span>balls before skill beats luck</span></div><div class='st'><b>{n['q5kept']:.0f}%</b><span>of a top season kept</span></div>
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
            el.screenshot(path=str(sd / f"r02-slide-{i:02d}.png"))
        pg.pdf(path=str(OUT / "r02-t20-linkedin-carousel.pdf"), width="1080px", height="1350px", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        if pub:
            og = b.new_page(viewport={"width": 1200, "height": 630})
            og.goto((pub / "og.html").resolve().as_uri())
            og.wait_for_timeout(300)
            og.screenshot(path=str(pub / "og.png"))
            (pub / "og.html").unlink()
        b.close()
    print("slides:", len(els))
