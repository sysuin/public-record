"""Draft charts for R03 (PNG). Usage: python3 -I 06_charts.py <data_dir> <charts_dir>
Colour follows the airline (fixed order, validated palette); every series is direct-labelled,
so colour is never the only encoding. No red/green pairs carry meaning.
"""
import sys, os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

D, C = sys.argv[1], sys.argv[2]
os.makedirs(C, exist_ok=True)
COL = {"IndiGo": "#2a78d6", "Air India": "#eb6834", "Akasa Air": "#1baf7a", "SpiceJet": "#eda100",
       "Vistara": "#e87ba4", "AirAsia India": "#008300", "Go First": "#6250d6"}
GREY, INK, INK2, SURF = "#9a9893", "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#c9c8c3", "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.grid": True, "grid.color": "#ebeae6",
                     "grid.linewidth": 0.8, "axes.axisbelow": True})
SRC = "Source: DGCA monthly domestic traffic reports (dgca.gov.in), Jan 2018 - Sep 2026. Sartium analysis."
P = pd.read_csv(os.path.join(D, "airline_month_panel.csv"), parse_dates=["date"])
M = pd.read_csv(os.path.join(D, "main_airline_months.csv"), parse_dates=["date"])
H = json.load(open(os.path.join(D, "headline_numbers.json")))

def finish(fig, name, title, sub=None, src=SRC):
    fig.tight_layout(rect=(0, 0.04, 1, 0.88))
    fig.suptitle(title, x=0.01, ha="left", fontsize=15, fontweight="bold", color=INK, y=0.995)
    if sub: fig.text(0.01, 0.935, sub, ha="left", fontsize=10.5, color=INK2)
    fig.text(0.01, 0.01, src, ha="left", fontsize=8.5, color=INK2)
    fig.savefig(os.path.join(C, name), dpi=170, bbox_inches="tight", facecolor=SURF); plt.close(fig)

# 1 ---------------------------------------------------------------- scope
cov = pd.read_csv(os.path.join(D, "otp_scope_schedule_coverage_ws2026.csv"))
order = ["IndiGo", "Air India", "Akasa Air", "SpiceJet", "Alliance Air", "Star Air", "Fly91", "ALL"]
cv = cov[cov.airline.isin(order)].pivot(index="airline", columns="airport_set", values="share_pct").reindex(order)
fig, ax = plt.subplots(figsize=(10, 5.6))
y = np.arange(len(order))
ax.barh(y + 0.2, cv[4], height=0.38, color="#9fc1ea", label="4 airports measured 2018-2024")
ax.barh(y - 0.2, cv[10], height=0.38, color="#2a78d6", label="10 airports measured since Jan 2026")
for i, a in enumerate(order):
    ax.text(cv.loc[a, 4] + 1, i + 0.2, f'{cv.loc[a, 4]:.0f}%', va="center", fontsize=9.5, color=INK2)
    ax.text(cv.loc[a, 10] + 1, i - 0.2, f'{cv.loc[a, 10]:.0f}%', va="center", fontsize=9.5, color=INK)
ax.set_yticks(y); ax.set_yticklabels(["All airlines" if a == "ALL" else ("Air India Group" if a == "Air India" else a) for a in order])
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("Share of the airline's scheduled domestic departures (%)")
ax.legend(loc="upper right", frameon=False, fontsize=9.5); ax.grid(axis="y", visible=False)
finish(fig, "c1_otp_covers_part_of_the_network.png", "The on-time figure only counts some airports",
       "Share of each airline's departures leaving from the airports DGCA measures (approved winter 2026 schedule, week of 9 Nov 2026)",
       "Source: DGCA approved Winter Schedule 2026 (dgca.gov.in). Airport sets as stated in DGCA traffic reports. Sartium analysis.")

# 2 ---------------------------------------------------------------- leader strip
L = pd.read_csv(os.path.join(D, "otp_leader_by_month.csv"), parse_dates=["date"])
names = ["IndiGo", "Go First", "AirAsia India", "Akasa Air", "Vistara", "Air India", "SpiceJet"]
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
for i, n in enumerate(names):
    d = L[L.airline == n].date
    ax.scatter(d, [i] * len(d), s=46, marker="s", color=COL.get(n, GREY), edgecolor=SURF, linewidth=1)
    ax.text(L.date.max() + pd.Timedelta(days=40), i, f"{n}  {len(d)}", va="center", fontsize=9.5, color=INK)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
ax.axvspan(pd.Timestamp("2020-03-15"), pd.Timestamp("2021-12-31"), color="#f1f0ec", zorder=0)
ax.text(pd.Timestamp("2020-06-01"), 6.6, "Covid years", fontsize=9, color=INK2)
ax.set_title("Which airline topped DGCA's on-time list each month (airlines with at least 1% of passengers)", loc="left", fontsize=10.5, color=INK2)
ax2.bar(L.date, L.gap, width=22, color="#7f7d78")
ax2.axhline(1, color=INK2, lw=0.8, ls="--"); ax2.text(pd.Timestamp("2018-01-15"), 1.3, "1 point", fontsize=8.5, color=INK2)
ax2.set_ylabel("Lead over\nsecond place\n(points)"); ax2.set_ylim(0, 15)
ax2.xaxis.set_major_locator(mdates.YearLocator()); ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
finish(fig, "c2_number_one_keeps_changing.png", f"The 'most punctual airline' changed {H['leader']['all_2018-01_2026-09']['leader_changes']} times in 104 months",
       "Over 2018-19 and over 2022-24 the top two airlines' averages were less than 1 point apart - smaller than a normal monthly swing")

# 3 ---------------------------------------------------------------- OTP lines 2022-2026
fig, ax = plt.subplots(figsize=(12, 6))
X = M[M.date >= "2022-01-01"]
ends = []
for n in ["IndiGo", "Air India", "Akasa Air", "SpiceJet", "Vistara", "AirAsia India", "Go First"]:
    g = X[X.airline == n].sort_values("date")
    if g.empty: continue
    ax.plot(g.date, g.otp_pct, color=COL[n], lw=2)
    ends.append([g.date.iloc[-1], g.otp_pct.iloc[-1], n])
# nudge end labels that share an end date so they do not overlap (min 3.2 points apart)
for dd in set(e[0] for e in ends):
    grp = sorted([e for e in ends if e[0] == dd], key=lambda e: -e[1])
    for k in range(1, len(grp)):
        if grp[k - 1][1] - grp[k][1] < 3.2: grp[k][1] = grp[k - 1][1] - 3.2
for dd, yy, n in ends:
    ax.text(dd + pd.Timedelta(days=12), yy, n, color=INK, fontsize=9.5, va="center")
for x0, lab in [("2025-01-01", "6 airports"), ("2026-01-01", "10 airports")]:
    ax.axvline(pd.Timestamp(x0), color=INK2, lw=0.8, ls=":"); ax.text(pd.Timestamp(x0) + pd.Timedelta(days=8), 22, lab, fontsize=9, color=INK2)
ax.text(pd.Timestamp("2022-01-10"), 22, "4 airports measured", fontsize=9, color=INK2)
ax.set_ylim(10, 100); ax.set_ylabel("Flights leaving within 15 minutes of schedule (%)")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
finish(fig, "c3_on_time_by_airline_2022_2026.png", "Monthly on-time departures at the measured airports",
       "Airlines with at least 1% of domestic passengers in the month. The airport list changed twice.")

# 4 ---------------------------------------------------------------- three measures, 2026
X = M[(M.date >= "2026-01-01") & M.airline.isin(["IndiGo", "Air India", "Akasa Air"])]
fig, axs = plt.subplots(1, 3, figsize=(13, 4.8))
specs = [("otp_pct", "Left on time (%)", "higher is better"), ("cancel_pct", "Flights cancelled (%)", "lower is better"),
         ("complaints_per10k", "Complaints per 10,000 passengers", "lower is better")]
for ax, (col, lab, note) in zip(axs, specs):
    for i, n in enumerate(["IndiGo", "Air India", "Akasa Air"]):
        g = X[X.airline == n][col]
        ax.scatter(g, [i] * len(g), s=26, color=COL[n], alpha=0.55, edgecolor="none")
        ax.scatter([g.mean()], [i], s=120, color=COL[n], edgecolor=INK, linewidth=1, zorder=3)
        ax.text(g.mean(), i - 0.32, f"{g.mean():.2f}" if col == "cancel_pct" else f"{g.mean():.1f}", ha="center", fontsize=9.5, color=INK)
    ax.set_yticks(range(3)); ax.set_yticklabels(["IndiGo", "Air India Group", "Akasa Air"] if ax is axs[0] else [""] * 3)
    ax.set_ylim(2.6, -0.7); ax.set_title(f"{lab}\n({note})", fontsize=10.5, color=INK, loc="left"); ax.grid(axis="y", visible=False)
finish(fig, "c4_three_measures_disagree_2026.png", "Three measures, three different leaders (Jan-Sep 2026)",
       "Small dots: each month. Big dot: nine-month average. On-time is measured at 10 airports; cancellations and complaints cover the whole network.")

# 5 ---------------------------------------------------------------- weight sweep triangles
def sweep(window_mask, title, ax):
    X = M[window_mask & M.airline.isin(["IndiGo", "Air India", "Akasa Air"])].dropna(subset=["otp_pct", "cancel_pct", "complaints_per10k"])
    mu = X.groupby("airline")[["otp_pct", "cancel_pct", "complaints_per10k"]].mean()
    rk = pd.DataFrame({"otp": mu.otp_pct.rank(ascending=False), "can": mu.cancel_pct.rank(), "cmp": mu.complaints_per10k.rank()})
    step = 0.05; pts = []
    for a in np.arange(0, 1 + 1e-9, step):
        for b in np.arange(0, 1 + 1e-9, step):
            c = 1 - a - b
            if c < -1e-9: continue
            s = a * rk.otp + b * rk.can + c * rk.cmp
            w = s.idxmin()
            x = b + a / 2; y = a * np.sqrt(3) / 2
            pts.append((x, y, w))
    for x, y, w in pts:
        ax.scatter(x, y, s=70, marker="h", color=COL[w], edgecolor=SURF, linewidth=0.6)
    share = pd.Series([p[2] for p in pts]).value_counts(normalize=True)
    ax.text(0.5, np.sqrt(3) / 2 + 0.07, "All weight on\non-time", ha="center", fontsize=9, color=INK2)
    ax.text(-0.02, -0.08, "All weight on\ncomplaints", ha="left", fontsize=9, color=INK2)
    ax.text(1.02, -0.08, "All weight on\ncancellations", ha="right", fontsize=9, color=INK2)
    lab = "  ".join(f"{k}: {v*100:.0f}% of weightings" for k, v in share.items())
    ax.set_title(title + "\n" + lab, fontsize=9.8, color=INK, loc="left")
    ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-0.1, 1.1); ax.set_ylim(-0.18, 1.05)
fig, axs = plt.subplots(1, 2, figsize=(13, 6.2))
sweep((M.date >= "2025-10-01") & (M.date <= "2026-09-01"), "Oct 2025 - Sep 2026", axs[0])
sweep((M.date >= "2025-10-01") & (M.date <= "2026-09-01") & (M.date != "2025-12-01"), "Same 12 months without December 2025", axs[1])
for n in ["IndiGo", "Akasa Air", "Air India"]:
    axs[1].scatter([], [], s=70, marker="h", color=COL[n], label=n)
axs[1].legend(loc="upper right", frameon=False, fontsize=9.5)
finish(fig, "c5_who_wins_depends_on_weights_and_one_month.png", "Who is 'most reliable' depends on what you value - and on one month",
       "Each hexagon is one way of weighting on-time, cancellations and complaints; its colour is the airline that comes out on top (IndiGo, Air India Group, Akasa Air only).")

# 6 ---------------------------------------------------------------- IndiGo cancellations
g = P[(P.airline == "IndiGo") & (P.date >= "2018-01-01")].sort_values("date")
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(g.date, g.cancel_pct, width=22, color=COL["IndiGo"])
d = g[g.date == "2025-12-01"].iloc[0]
ax.annotate(f"December 2025: {d.cancel_pct:.2f}% of flights cancelled", (d.date, d.cancel_pct), xytext=(pd.Timestamp("2022-06-01"), 8.6),
            fontsize=10, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
j = g[g.date == "2024-01-01"].iloc[0]
ax.annotate(f"Jan 2024: {j.cancel_pct:.2f}%", (j.date, j.cancel_pct), xytext=(pd.Timestamp("2021-06-01"), 6.0), fontsize=9.5, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_ylabel("Share of IndiGo's flights cancelled (%)"); ax.set_ylim(0, 10.5)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
finish(fig, "c6_indigo_december_2025.png", "The most punctual airline also had the worst month in eight years of DGCA data",
       f"IndiGo's typical month (2022 - Nov 2025): {H['indigo_cancel']['median_2022_2025nov']}% cancelled")

# 7 ---------------------------------------------------------------- complaints
S = pd.read_csv(os.path.join(D, "system_monthly.csv"), parse_dates=["date"]).sort_values("date")
fig, ax = plt.subplots(figsize=(12, 5))
v = S.complaints_per10k_overall.clip(upper=8)
ax.bar(S.date, v, width=22, color="#6f6d68")
big = S[S.complaints_per10k_overall > 8]
for _, r in big.iterrows():
    ax.text(r.date, 8.1, f"{r.complaints_per10k_overall:.1f}\n(off scale)", ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 9.2); ax.set_ylabel("Complaints per 10,000 passengers (all airlines)")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
cy = H["complaints_median_monthly_rate_by_year_excl_dec2025"]
finish(fig, "c7_complaints_per_10k.png", "Complaint rates were low and steady until 2025, then stepped up",
       f"Typical month: {cy['2024']} per 10,000 in 2024, {cy['2026']} in 2026. The data does not say why.")

# 8 ---------------------------------------------------------------- airport effect 2026
ap = pd.Series(H["airport_all_2026_mean"]).sort_values()
NAMES = {"BOM": "Mumbai", "GAU": "Guwahati", "DEL": "Delhi", "LKO": "Lucknow", "COK": "Kochi", "AMD": "Ahmedabad",
         "CCU": "Kolkata", "BLR": "Bengaluru", "HYD": "Hyderabad", "MAA": "Chennai"}
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.barh([NAMES[k] for k in ap.index], ap.values, color="#7f7d78", height=0.6)
for i, (k, vv) in enumerate(ap.items()):
    ax.text(vv + 0.6, i, f"{vv:.1f}%", va="center", fontsize=9.5, color=INK)
ax.set_xlim(50, 100); ax.set_xlabel("Departures on time, all measured airlines, Jan-Sep 2026 average (%)"); ax.grid(axis="y", visible=False)
finish(fig, "c8_airport_matters.png", "Where you fly from moves the number almost as much as who you fly",
       "The gap between Chennai and Mumbai is bigger than the gap between the top three airlines")

# 9 ---------------------------------------------------------------- seasonality
se = pd.read_csv(os.path.join(D, "seasonality_month_of_year.csv"))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8))
mn = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
a1.bar(mn, se.otp_w, color=["#2a78d6" if m in (1, 12) else "#9fc1ea" for m in se.moy])
a1.set_ylim(50, 95); a1.set_title("Passenger-weighted on-time departures (%)", loc="left", fontsize=10.5, color=INK)
a2.bar(mn, se.cancel_weather_share, color=["#2a78d6" if m in (1, 12) else "#9fc1ea" for m in se.moy], label="Cancellations blamed on weather (%)")
a2.plot(mn, se.delay_wx_share, color=INK, marker="o", ms=4, lw=1.5)
a2.text(11.2, se.delay_wx_share.iloc[11] + 3, "Delays blamed\non weather", fontsize=9, color=INK, ha="right")
a2.text(1.6, 45, "Bars: cancellations\nblamed on weather", fontsize=9, color=INK)
a2.set_title("Share of causes recorded as weather (%)", loc="left", fontsize=10.5, color=INK)
for a in (a1, a2): a.grid(axis="x", visible=False)
finish(fig, "c9_fog_season.png", "December and January are worse - but weather is a small slice of recorded delay causes",
       "Average by calendar month, 2018-2026 excluding Mar 2020 - Dec 2021. Darker bars: December and January.")

# 10 ---------------------------------------------------------------- IndiGo share
sh = P[P.airline == "IndiGo"].sort_values("date")
fig, ax = plt.subplots(figsize=(12, 4.8))
ax.plot(sh.date, sh.share_pct, color=COL["IndiGo"], lw=2.2)
for d0, lab in [("2019-04-01", "Jet Airways stops"), ("2023-05-01", "Go First stops"), ("2025-12-01", "Dec 2025 disruption")]:
    r = sh[sh.date == d0].iloc[0]
    ax.annotate(lab, (r.date, r.share_pct), xytext=(r.date, r.share_pct - 9), fontsize=9, color=INK2, ha="center",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(sh.date.iloc[-1] + pd.Timedelta(days=15), sh.share_pct.iloc[-1], f"{sh.share_pct.iloc[-1]:.1f}%", va="center", fontsize=10, color=INK)
ax.text(sh.date.iloc[0], sh.share_pct.iloc[0] + 2.5, f"{sh.share_pct.iloc[0]:.1f}%", fontsize=10, color=INK)
ax.set_ylim(30, 75); ax.set_ylabel("IndiGo share of domestic passengers (%)")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
finish(fig, "c10_indigo_share.png", "Two in every three domestic passengers now fly IndiGo")
print("charts written:", sorted(os.listdir(C)))
