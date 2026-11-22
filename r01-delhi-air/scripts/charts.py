"""Draft charts for R01. Reads DATA_DIR (derived CSVs + results.json), writes PNGs to CHART_DIR.

Usage:
    python3 -I charts.py DATA_DIR CHART_DIR

Plain-language titles (house style), direct labels, no red/green-only encoding.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.dpi": 160})
SRC = "Source: CPCB daily National AQI bulletins (cpcb.gov.in), 4 PM, 24-hour average. Analysis: Sartium."


def title(ax, t, sub=None):
    ax.set_title(t, loc="left", fontsize=14, fontweight="bold", color=INK, pad=22 if sub else 8)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10, color=INK2, va="bottom")


def foot(fig, extra=""):
    fig.text(0.01, 0.01, SRC + (" " + extra if extra else ""), fontsize=7.5, color=MUTED)


def main():
    data, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    R = json.load(open(os.path.join(data, "results.json")))
    S = pd.read_csv(os.path.join(data, "season_summary_by_city.csv"))
    dl = S[S.city == "Delhi"]

    # 1. Same window every year: mean AQI with intervals
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, wn, lab in [(axes[0], "oct1_nov20", "1 October to 20 November"), (axes[1], "nov1_20", "1 to 20 November")]:
        d = dl[(dl.window == wn) & (dl.year >= 2016)].sort_values("year")
        col = [ORANGE if y == 2026 else BLUE for y in d.year]
        ax.errorbar(d.year, d["mean"], yerr=[d["mean"] - d.mean_ci_lo, d.mean_ci_hi - d["mean"]], fmt="none",
                    ecolor=MUTED, elinewidth=1.5, capsize=0)
        ax.scatter(d.year, d["mean"], c=col, s=60, zorder=3, edgecolor="white", linewidth=1.5)
        for y, m in zip(d.year, d["mean"]):
            ax.text(y, m + 14, f"{m:.0f}", ha="center", fontsize=8.5, color=INK2)
        ax.set_xticks(d.year)
        ax.set_xticklabels([str(y)[2:] if y != 2026 else "2026" for y in d.year])
        ax.set_title(lab, loc="left", fontsize=11, color=INK2)
        ax.axhline(300, color=MUTED, lw=0.8, ls=":")
        ax.text(2015.6, 296, "Very Poor starts at 301", fontsize=8, color=MUTED, va="top")
    axes[0].set_ylabel("Delhi average AQI over the window")
    fig.suptitle("Delhi's air this autumn, against the same dates in every year since 2016", x=0.01, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    fig.text(0.01, 0.905, "Dot = average of the daily city AQI; bar = range the average could plausibly take given day-to-day swings. 2026 in orange.",
             fontsize=9.5, color=INK2)
    foot(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 0.9])
    fig.savefig(os.path.join(out, "c1_same_window_each_year.png"))
    plt.close(fig)

    # 2. Days Very Poor or worse / Severe in Oct1-Nov20
    d = dl[(dl.window == "oct1_nov20") & (dl.year >= 2016)].sort_values("year")
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(d))
    vp_only = d.days_vpoor_or_worse - d.days_severe
    ax.bar(x, d.days_severe, color=VIOLET, width=0.7, label="Severe (AQI 401+)")
    ax.bar(x, vp_only, bottom=d.days_severe, color=BLUE, width=0.7, label="Very Poor (301-400)",
           edgecolor="#fcfcfb", linewidth=2)
    for i, (s, v, n) in enumerate(zip(d.days_severe, d.days_vpoor_or_worse, d.n_days_data)):
        ax.text(i, v + 0.6, f"{v:.0f}", ha="center", fontsize=9, color=INK)
        ax.text(i, -3.2, f"of {n:.0f}", ha="center", fontsize=7.5, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels(d.year.astype(str))
    ax.set_ylim(-5, max(d.days_vpoor_or_worse) + 6)
    ax.set_ylabel("days")
    ax.legend(frameon=False, loc="upper right")
    title(ax, "Bad-air days between 1 Oct and 20 Nov, Delhi",
          "Number of days the CPCB city AQI was Very Poor or Severe. 'of N' = days with a published value.")
    foot(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(out, "c2_bad_days_each_year.png"))
    plt.close(fig)

    # 3. Station count over time
    daily = pd.read_csv(os.path.join(data, "ncr_daily_aqi.csv"), parse_dates=["date"]).set_index("date")
    fig, ax = plt.subplots(figsize=(11, 4.8))
    st = daily["Delhi_stations"].rolling(15, min_periods=5).median()
    ax.plot(st.index, st, color=BLUE, lw=2)
    for c, col in [("Gurugram", ORANGE), ("Noida", AQUA), ("Faridabad", VIOLET)]:
        s2 = daily[c + "_stations"].rolling(15, min_periods=5).median()
        ax.plot(s2.index, s2, color=col, lw=1.6)
        off = {"Gurugram": 1.6, "Noida": 1.2, "Faridabad": -2.2}[c]
        ax.text(s2.dropna().index[-1], s2.dropna().iloc[-1] + off, c, color=INK2, fontsize=9, ha="right")
    ax.text(st.dropna().index[-1], st.dropna().iloc[-1] + 1.2, "Delhi", color=INK, fontsize=10, ha="right", fontweight="bold")
    ax.set_ylabel("stations behind the city number")
    title(ax, "The Delhi number came from 6 monitors in 2016, about 36 for 2019-25, and 59 since mid-October",
          "Stations contributing to each city's daily AQI in the CPCB bulletin (15-day median).")
    foot(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(out, "c3_station_count.png"))
    plt.close(fig)

    # 4. Station-step test
    ev = pd.DataFrame(R["station_steps"])
    pl = R["station_step_placebo"]
    if len(ev):
        fig, ax = plt.subplots(figsize=(10, 4.6))
        ax.axhspan(pl["p2_5"] * 100, pl["p97_5"] * 100, color=GRID, alpha=0.9)
        ax.text(len(ev) - 0.5, pl["p97_5"] * 100 + 0.8, "normal month-to-month drift (95% of ordinary dates)",
                fontsize=8.5, color=INK2, ha="right")
        for i, r in ev.iterrows():
            lo, hi = r.ci_pct[0] * 100, r.ci_pct[1] * 100
            ax.plot([i, i], [lo, hi], color=MUTED, lw=1.5)
            ax.scatter(i, r.delhi_vs_neighbours_change_pct * 100, color=BLUE, s=60, zorder=3)
            ax.text(i + 0.08, r.delhi_vs_neighbours_change_pct * 100,
                    f"{r.stations_before:.0f}->{r.stations_after:.0f} stations", fontsize=8.5, color=INK2, va="center")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(range(len(ev)))
        ax.set_xticklabels(ev.step_date, rotation=40, ha="right", fontsize=9)
        ax.set_ylabel("change in Delhi relative to\nneighbouring NCR cities (%)")
        title(ax, "When Delhi added monitors, did its number jump?",
              "Delhi's AQI relative to the other NCR cities, 30 days after vs 30 days before each jump in reporting stations.")
        foot(fig)
        fig.tight_layout(rect=[0, 0.03, 1, 1])
        fig.savefig(os.path.join(out, "c4_station_step_test.png"))
        plt.close(fig)

    # 5. Raw vs weather-adjusted
    W = pd.read_csv(os.path.join(data, "weather_adjusted_year_index.csv"))
    w = W[W.model == "weather"]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(w.year, (w.raw_index - 1) * 100, color=MUTED, marker="o", lw=1.5, ms=6, label="as measured")
    ax.errorbar(w.year, (w.adjusted_index - 1) * 100, yerr=[(w.adjusted_index - w.adj_lo) * 100, (w.adj_hi - w.adjusted_index) * 100],
                color=BLUE, marker="o", lw=2, ms=7, capsize=0, label="after allowing for wind, rain, temperature, humidity and Diwali")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(w.year)
    ax.set_ylabel("% above / below the 2015-2026 average")
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    sh = R["models"]["weather"]["share_between_year_variance_removed"]
    title(ax, "Take the weather out and the years look more alike",
          f"Delhi, 1 Oct-20 Nov. Weather accounts for roughly {sh*100:.0f}% of the year-to-year spread.\n2026 weather comes from a different NASA model (GEOS-IT) than earlier years (MERRA-2).")
    foot(fig, "Weather: NASA POWER (MERRA-2; GEOS-IT from Oct 2026).")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(out, "c5_weather_adjusted.png"))
    plt.close(fig)

    # 6. Fires vs Delhi (two panels, no dual axis)
    F = pd.read_csv(os.path.join(data, "fires_vs_delhi.csv")).sort_values("year")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ax = axes[0]
    ax.bar(F.year.astype(str), F.punjab_haryana / 1000, color=ORANGE, width=0.6)
    for i, v in enumerate(F.punjab_haryana):
        ax.text(i, v / 1000 + 1.2, f"{v/1000:.1f}k", ha="center", fontsize=9, color=INK)
    ax.set_title("Farm fires counted by satellite, Punjab + Haryana,\nseason to 20 Nov (ICAR-IARI CREAMS)", loc="left", fontsize=11, color=INK2)
    ax.set_ylabel("thousand fire events")
    ax = axes[1]
    ax.bar(F.year.astype(str), F.delhi_oct1_nov20_mean, color=BLUE, width=0.6)
    for i, v in enumerate(F.delhi_oct1_nov20_mean):
        ax.text(i, v + 5, f"{v:.0f}", ha="center", fontsize=9, color=INK)
    ax.set_title("Delhi average AQI, 1 Oct-20 Nov\n(CPCB)", loc="left", fontsize=11, color=INK2)
    ax.set_ylim(0, 420)
    fig.suptitle("Counted farm fires fell by about nine-tenths. Delhi's autumn air did not", x=0.01, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    foot(fig, "Fires: ICAR-IARI CREAMS bulletin of 20 Nov each year; season starts 30 Sep (2018), 1 Oct (2020), 15 Sep (other years). No 20 Nov bulletin listed for 2019, 2022.")
    fig.tight_layout(rect=[0, 0.03, 1, 0.93])
    fig.savefig(os.path.join(out, "c6_fires_vs_delhi.png"))
    plt.close(fig)

    # 7. NCR cities, small multiples
    cities = ["Delhi", "Gurugram", "Noida", "Ghaziabad", "Faridabad", "Greater Noida"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharey=True)
    for ax, c in zip(axes.flat, cities):
        d = S[(S.city == c) & (S.window == "oct1_nov20") & (S.year >= 2016)].sort_values("year")
        d = d[d.coverage >= 0.6]
        col = [ORANGE if y == 2026 else BLUE for y in d.year]
        ax.bar(d.year.astype(int), d["mean"], color=col, width=0.7)
        for y, m, s_ in zip(d.year, d["mean"], d.stations_median):
            ax.text(y, 8, f"{s_:.0f}", ha="center", fontsize=7, color="white")
        ax.set_title(c, loc="left", fontsize=11, fontweight="bold", color=INK)
        ax.set_xticks([2016, 2018, 2020, 2022, 2024, 2026])
        ax.set_xticklabels(["16", "18", "20", "22", "24", "26"])
    fig.suptitle("Every NCR city, same window (1 Oct-20 Nov), every year it was in the bulletin", x=0.01, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    fig.text(0.01, 0.92, "Bar = average city AQI; white number = monitoring stations behind it; 2026 in orange. Years with under 60% of days published are left out.",
             fontsize=9.5, color=INK2)
    foot(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 0.91])
    fig.savefig(os.path.join(out, "c7_ncr_cities.png"))
    plt.close(fig)

    # 8. Monthly heatmap Delhi (sequential, one hue)
    M = pd.read_csv(os.path.join(data, "delhi_monthly_mean_aqi.csv"))
    M = M[(M["count"] >= 15) & (M.year >= 2016)]
    P = M.pivot(index="year", columns="month", values="mean")
    fig, ax = plt.subplots(figsize=(11, 5.6))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blues", ["#f1f6fc", "#9cc2ef", "#2a78d6", "#0d2f5c"])
    im = ax.imshow(P.values, aspect="auto", cmap=cmap, vmin=50, vmax=420)
    for i in range(P.shape[0]):
        for j in range(P.shape[1]):
            v = P.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 230 else INK)
    ax.set_xticks(range(P.shape[1]))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][:P.shape[1]])
    ax.set_yticks(range(P.shape[0]))
    ax.set_yticklabels(P.index)
    ax.grid(False)
    title(ax, "Delhi's average AQI, every month since 2016", "Darker = worse. Months with fewer than 15 published days are blank.")
    foot(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(out, "c8_monthly_heatmap.png"))
    plt.close(fig)

    # 9. The turn: 2025 -> 2026 change by city against monitors added
    Y = pd.read_csv(os.path.join(data, "yoy_change_by_city.csv")).rename(columns={"pct_change": "pct"})
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    order = ["Gurugram", "Faridabad", "Delhi", "Noida", "Ghaziabad", "Greater Noida"]
    for ax, wn, lab in [(axes[0], "oct1_nov20", "1 Oct-20 Nov"), (axes[1], "nov1_20", "1-20 Nov")]:
        d = Y[(Y.window == wn) & (Y.year == 2026)].set_index("city").reindex(order)
        yy = np.arange(len(order))[::-1]
        grew = d.listed_now > d.listed_prev
        cols = [BLUE if g else MUTED for g in grew]
        ax.barh(yy, d.pct * 100, color=cols, height=0.6)
        ax.errorbar(d.pct * 100, yy, xerr=[(d.pct - d.paired_ci_lo) * 100, (d.paired_ci_hi - d.pct) * 100],
                    fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
        for y_, (c, r) in zip(yy, d.iterrows()):
            tag = f"{r.listed_prev:.0f} -> {r.listed_now:.0f} monitors" + ("" if r.listed_now > r.listed_prev else " (no new monitors)")
            ax.text(1 if r.pct < 0 else r.pct * 100 + 1, y_ + 0.32, tag, fontsize=8, color=INK2)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_yticks(yy)
        ax.set_yticklabels(order)
        ax.set_xlabel("% change in average AQI, 2026 vs 2025")
        ax.set_title(lab, loc="left", fontsize=11, color=INK2)
        ax.grid(axis="y", visible=False)
    fig.suptitle("This autumn's improvement shows up where new monitors were added", x=0.01, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    fig.text(0.01, 0.905, "Blue = city whose CPCB monitor list grew during Oct-Nov 2026; grey = it did not. Line = plausible range from day-to-day swings (same dates compared).",
             fontsize=9.5, color=INK2)
    foot(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 0.89])
    fig.savefig(os.path.join(out, "c9_change_vs_new_monitors.png"))
    plt.close(fig)
    print("charts written")


if __name__ == "__main__":
    main()
