"""R04 step 6: draft charts from data/ CSVs.

Usage: python3 -I 06_charts.py <data_dir> <charts_dir>
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

D, C = sys.argv[1], sys.argv[2]
os.makedirs(C, exist_ok=True)
BLUE, ORANGE, AQUA, YELLOW, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"
LIGHTBLUE = "#9fc1ea"
GREY, INK, INK2, SURF = "#9a9893", "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#c9c8c3", "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.grid": True, "grid.color": "#ebeae6",
                     "grid.linewidth": 0.8, "axes.axisbelow": True})
SRC = "Source: ClinicalTrials.gov API v2 (US National Library of Medicine), data as of 20 Nov 2026. Interventional trials only. Sartium analysis."
H = json.load(open(os.path.join(D, "headline_numbers.json")))


def finish(fig, name, title, sub=None, src=SRC):
    h = fig.get_figheight()
    fig.tight_layout(rect=(0, 0.35 / h, 1, 1 - 0.95 / h))
    fig.suptitle(title, x=0.01, ha="left", fontsize=15, fontweight="bold", color=INK, y=1 - 0.05 / h, va="top")
    if sub:
        fig.text(0.01, 1 - 0.45 / h, sub, ha="left", fontsize=10.5, color=INK2, va="top")
    fig.text(0.01, 0.05 / h, src, ha="left", fontsize=8.5, color=INK2)
    fig.savefig(os.path.join(C, name), dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


# 1 ------------------------------------------------------------- the obvious number
h1 = pd.read_csv(os.path.join(D, "h1_completed_by_pcd_year.csv"))
h1 = h1[h1.pcd_year.between(2005, 2025)]
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.bar(h1.pcd_year, h1.pct_submitted, color=BLUE, width=0.72)
for _, r in h1.iterrows():
    if r.pcd_year % 2 == 0 or r.pcd_year == 2025:
        ax.text(r.pcd_year, r.pct_submitted + 0.8, f"{r.pct_submitted:.0f}%", ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 60); ax.set_ylabel("% with results on ClinicalTrials.gov")
ax.set_xlabel("Year the trial finished collecting its main result")
w = H["h1_completed_int_pcd2008_2023_submitted"]
ax.text(2005.2, 54, f"Finished 2008-2023: {w['pct']:.0f}% have results ({w['k']:,} of {w['n']:,}).\nSo about {100-w['pct']:.0f}% do not.",
        fontsize=10.5, color=INK, va="top")
ax.annotate("recent trials have\nhad less time", xy=(2025, h1[h1.pcd_year == 2025].pct_submitted.iloc[0] + 1), xytext=(2022.3, 40),
            fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
finish(fig, "c1_the_obvious_number.png", "Most completed trials on ClinicalTrials.gov have no results there",
       "Completed interventional trials, by year they finished; results submitted (posted or in NLM review)")

# 2 ------------------------------------------------------------- denominator turn
m = H["h2_main"]
fig, ax = plt.subplots(figsize=(10, 5.4))
labels = ["Within 12 months\n(the legal deadline)", "Within 24 months", "By Nov 2026"]
req = [m["required_sub12"]["pct"], m["required_sub24"]["pct"], m["required_ever"]["pct"]]
oth = [m["other_sub12"]["pct"], m["other_sub24"]["pct"], m["other_ever"]["pct"]]
x = np.arange(3)
ax.bar(x - 0.2, req, width=0.38, color=BLUE)
ax.bar(x + 0.2, oth, width=0.38, color=GREY)
for i in range(3):
    ax.text(x[i] - 0.2, req[i] + 1.2, f"{req[i]:.0f}%", ha="center", fontsize=11, color=INK, fontweight="bold")
    ax.text(x[i] + 0.2, oth[i] + 1.2, f"{oth[i]:.0f}%", ha="center", fontsize=11, color=INK)
ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylim(0, 100); ax.set_ylabel("% with results submitted")
ax.text(-0.42, 96, f"Probably required by US law: {m['required_n']:,} trials", color=BLUE, fontsize=10.5, fontweight="bold", va="top")
ax.text(-0.42, 90, f"Everything else: {m['other_n']:,} trials", color=INK2, fontsize=10.5, fontweight="bold", va="top")
ax.grid(axis="x", visible=False)
finish(fig, "c2_the_denominator_turn.png", "Trials the law probably covers report five times as often as the rest",
       "Interventional trials that finished 18 Jan 2017 - 20 Nov 2024; 'probably required' is our estimate from registry fields, not a legal ruling")

# 3 ------------------------------------------------------------- timeliness over time
t = pd.read_csv(os.path.join(D, "h3_timeliness_by_pcd_year.csv"))
fig, ax = plt.subplots(figsize=(10, 5.6))
for g, col, lab in [("Drug/device trials with a US site, beyond phase 1", BLUE, "Drug/device trials with a US site, beyond phase 1"),
                    ("All other interventional", GREY, "All other interventional trials")]:
    s = t[(t.group == g) & t.pcd_year.between(2008, 2025)]
    ax.plot(s.pcd_year, s.pct_12m, color=col, lw=2, marker="o", ms=5)
    s24 = s.dropna(subset=["pct_24m"])
    ax.plot(s24.pcd_year, s24.pct_24m, color=col, lw=2, ls="--")
    last = s.dropna(subset=["pct_12m"]).iloc[-1]
    ax.text(last.pcd_year + 0.2, last.pct_12m, "within 12 months", fontsize=9, color=col, va="center")
    ax.text(s24.pcd_year.iloc[-1] + 0.2, s24.pct_24m.iloc[-1], "within 24 months", fontsize=9, color=col, va="center")
    ax.text({BLUE: 2008, GREY: 2017.4}[col], {BLUE: 76, GREY: 16}[col], lab, fontsize=10, color=col, fontweight="bold")
ax.axvline(2017.05, color=INK2, lw=0.8, ls=":")
ax.text(2017.15, 29, "Final Rule in force 18 Jan 2017;\ntrials finishing in 2016 were\nthe first due under it", fontsize=9, color=INK2, va="top")
ax.set_ylim(0, 80); ax.set_xlim(2007.5, 2027.8); ax.set_ylabel("% with results submitted")
ax.set_xticks(range(2008, 2026, 2)); ax.set_xticklabels([str(v) for v in range(2008, 2026, 2)])
ax.set_xlabel("Year of primary completion")
finish(fig, "c3_on_time_reporting_by_year.png", "On-time reporting has crept up for 15 years and is still under half",
       "Share submitting results within 12 and 24 months of finishing (trials with an actual completion date; 2024 is provisional)")

# 4 ------------------------------------------------------------- cumulative curves
cu = pd.read_csv(os.path.join(D, "h3_cumulative_by_cohort_lite.csv"))
fig, ax = plt.subplots(figsize=(10, 5.6))
cohorts = [(2012, LIGHTBLUE), (2015, VIOLET), (2018, BLUE), (2021, ORANGE), (2023, AQUA)]
for y, col in cohorts:
    s = cu[(cu.pcd_year == y) & (cu.months <= 96)]
    ax.plot(s.months, s.pct_submitted, color=col, lw=2)
    ax.text(s.months.iloc[-1] + 1, s.pct_submitted.iloc[-1], str(y), color=INK, fontsize=10, va="center")
ax.axvline(12, color=INK2, lw=0.8, ls=":"); ax.text(12.8, 4, "12-month deadline", fontsize=9, color=INK2)
ax.set_xlabel("Months after the trial finished collecting its main result"); ax.set_ylabel("% with results submitted")
ax.set_xlim(0, 104); ax.set_ylim(0, 100)
finish(fig, "c4_how_fast_results_arrive.png", "Results keep arriving years after the deadline",
       "Drug/device trials with a US site, beyond phase 1, by year they finished (each line stops where the data does)")

# 5 ------------------------------------------------------------- who reports
adj = pd.read_csv(os.path.join(D, "h4_sponsor_adjusted.csv"))
order = ["Industry", "Universities, hospitals & non-profits", "NIH", "Other US federal"]
fig, axes = plt.subplots(1, 3, figsize=(12, 5.6), sharey=True)
for ax, (yv, lab) in zip(axes, [("y12", "Within 12 months"), ("y12c", "Within 12 months, or a\ndelay certificate filed in time"), ("y24", "Within 24 months")]):
    s = adj[adj.outcome == yv].set_index("group").reindex(order)
    yy = np.arange(len(order))[::-1]
    ax.hlines(yy, s.lo, s.hi, color=BLUE, lw=2)
    ax.scatter(s.standardised_pct, yy, s=70, color=BLUE, zorder=3, label="Same trial mix for everyone")
    ax.scatter(s.crude_pct, yy, s=50, facecolor=SURF, edgecolor=INK2, zorder=4, marker="D", label="As recorded")
    for i, g in enumerate(order):
        ax.text(s.loc[g, "standardised_pct"], yy[i] + 0.25, f"{s.loc[g, 'standardised_pct']:.0f}%", ha="center", fontsize=9.5, color=INK)
    ax.set_title(lab, fontsize=11, color=INK, loc="left", pad=14); ax.set_xlim(0, 100); ax.set_ylim(-0.6, len(order) - 0.4)
    ax.grid(axis="y", visible=False)
axes[0].set_yticks(np.arange(len(order))[::-1])
axes[0].set_yticklabels([f"{g}\n(n={int(adj[(adj.outcome=='y12') & (adj.group==g)].n.iloc[0]):,})" for g in order])
axes[2].legend(loc="lower left", fontsize=8.5, frameon=False, bbox_to_anchor=(0, -0.28), ncol=2)
finish(fig, "c5_who_reports.png", "At the 12-month deadline, industry and universities tie; NIH is fastest",
       "Trials probably required to report, finished 18 Jan 2017 - 20 Nov 2024. Bars: range of plausible values")

# 6 ------------------------------------------------------------- status rot
sr = pd.read_csv(os.path.join(D, "h5_status_of_trials_past_completion.csv"))
sr = sr[sr.n > 0]
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.set_ylim(-0.5, 0.8)
left = 0
cols = {"Completed": BLUE, "Terminated": LIGHTBLUE, "Unknown status": ORANGE, "Still marked open/active": YELLOW, "Other": GREY}
for _, r in sr.iterrows():
    ax.barh(0, r.pct_of_no_results_pile, left=left, color=cols[r.status], edgecolor=SURF, linewidth=2)
    if r.pct_of_no_results_pile > 4:
        ax.text(left + r.pct_of_no_results_pile / 2, 0, f"{r.status}\n{r.pct_of_no_results_pile:.0f}%", ha="center", va="center",
                fontsize=10, color=INK)
    else:
        ax.annotate(f"{r.status} {r.pct_of_no_results_pile:.1f}%", xy=(left + r.pct_of_no_results_pile / 2, 0.42),
                    xytext=(left - 2, 0.62), ha="right", fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    left += r.pct_of_no_results_pile
ax.set_xlim(0, 100); ax.set_yticks([]); ax.grid(visible=False); ax.spines["left"].set_visible(False)
ax.set_xlabel("% of trials with no results, at least two years past their primary completion date")
nores = int(sr.n_no_results.sum())
finish(fig, "c6_where_the_missing_results_sit.png", "A quarter of the missing results sit in records nobody updated",
       f"{nores:,} interventional trials with no results; registry status as of 20 Nov 2026")

# 7 ------------------------------------------------------------- QC lag
qc = pd.read_csv(os.path.join(D, "h7_qc_lag_by_submit_year.csv"))
qc = qc[qc.submit_year.between(2009, 2026) & (qc.n_posted >= 50)]
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(qc.submit_year, qc.median_days_submit_to_post, color=BLUE, lw=2, marker="o", ms=5)
for _, r in qc.iterrows():
    if r.submit_year in (2010, 2015, 2018, 2020, 2022, 2024, 2025, 2026):
        ax.text(r.submit_year, r.median_days_submit_to_post + 6, f"{r.median_days_submit_to_post:.0f}", ha="center", fontsize=9, color=INK)
ax.set_ylabel("Median days from submission to public posting"); ax.set_xlabel("Year results were first submitted")
ax.set_ylim(0, max(qc.median_days_submit_to_post) * 1.25)
finish(fig, "c7_review_queue.png", "How long results wait in NLM's review queue",
       "Results posted on ClinicalTrials.gov; recent years include only results already posted (faster ones)")

# 8 ------------------------------------------------------------- named sponsors
sp = pd.read_csv(os.path.join(D, "h6_largest_sponsors_probably_required.csv")).sort_values("pct_24m")
fig, ax = plt.subplots(figsize=(10, max(4, 0.42 * len(sp) + 1.5)))
yy = np.arange(len(sp))
ax.hlines(yy, sp.lo_24m, sp.hi_24m, color=BLUE, lw=2)
ax.scatter(sp.pct_24m, yy, s=60, color=BLUE, zorder=3, label="Within 24 months")
ax.scatter(sp.pct_12m_or_cert, yy, s=46, facecolor=SURF, edgecolor=INK2, marker="D", zorder=4, label="Within 12 months or delay certificate filed")
ax.set_yticks(yy); ax.set_yticklabels([f"{s} ({n})" for s, n in zip(sp.sponsor, sp.n)], fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("% of the sponsor's probably-required trials"); ax.grid(axis="y", visible=False)
ax.legend(loc="lower right", fontsize=9, frameon=False)
finish(fig, "c8_largest_sponsors.png", "Largest sponsors of probably-required trials",
       "Lead sponsors with 100+ such trials finished 18 Jan 2017 - 20 Nov 2024 (name as registered; bars = plausible range)")

# 9 ------------------------------------------------------------- where the missing results come from
sg = pd.read_csv(os.path.join(D, "h2_cohort_segments.csv"))
sg = sg[sg.sponsor_group == "All"].set_index("segment")
segs = ["Probably required", "Not required, has a US site", "Not required, non-US sites only", "Not required, no location listed"]
fig, ax = plt.subplots(figsize=(10, 4.8))
for row, (colname, lab) in enumerate([("pct_of_cohort", "All trials that finished\n18 Jan 2017 - 20 Nov 2024"),
                                      ("pct_of_no_results_pile", "Those with no results\n24 months after finishing")]):
    left = 0
    for seg, col in zip(segs, [BLUE, LIGHTBLUE, ORANGE, GREY]):
        v = sg.loc[seg, colname]
        ax.barh(row, v, left=left, color=col, edgecolor=SURF, linewidth=2, height=0.6)
        if v > 6:
            ax.text(left + v / 2, row, f"{v:.0f}%", ha="center", va="center", fontsize=10.5, color=INK)
        left += v
ax.set_yticks([1, 0]); ax.set_yticklabels(["Those with no results\n24 months after finishing", "All trials that finished\n18 Jan 2017 - 20 Nov 2024"])
ax.set_ylim(1.75, -0.6); ax.set_xlim(0, 100); ax.grid(visible=False); ax.set_xlabel("% of trials")
xs = 1.5
for seg, col in zip(segs, [BLUE, LIGHTBLUE, ORANGE, GREY]):
    ax.scatter([xs], [1.55], s=90, marker="s", color=col)
    ax.text(xs + 1.5, 1.55, seg, va="center", fontsize=9, color=INK)
    xs += {"Probably required": 20, "Not required, has a US site": 27, "Not required, non-US sites only": 29}.get(seg, 0)
finish(fig, "c9_where_the_missing_results_come_from.png", "Most missing results are from trials US law doesn't cover",
       f"{int(H['h2_like_cohort_n']):,} interventional trials registered on ClinicalTrials.gov; 'probably required' is our estimate, not a legal ruling")

# 10 ------------------------------------------------------------- the headline falls because the mix changes
h1 = pd.read_csv(os.path.join(D, "h1_completed_by_pcd_year.csv"))
h1 = h1[h1.pcd_year.between(2008, 2023)]
fig, ax = plt.subplots(figsize=(10, 5.4))
for col, c, lab in [("pct_submitted_us_site", BLUE, "Trials with a US site"), ("pct_submitted", INK2, "All completed trials"),
                    ("pct_submitted_nonus_only", ORANGE, "Trials with non-US sites only")]:
    ax.plot(h1.pcd_year, h1[col], color=c, lw=2, marker="o", ms=4)
    ax.text(2023.3, h1[col].iloc[-1], f"{lab}  {h1[col].iloc[-1]:.0f}%", va="center", fontsize=9.5, color=INK)
ax2y = h1.pct_nonus_only
ax.text(2008, 75, f"Share of completed trials with non-US sites only: {ax2y.iloc[0]:.0f}% (2008) -> {ax2y.iloc[-1]:.0f}% (2023)", fontsize=10, color=INK)
ax.set_ylim(0, 80); ax.set_xlim(2007.5, 2029.5); ax.set_ylabel("% with results submitted"); ax.set_xlabel("Year of primary completion")
ax.set_xticks(range(2008, 2024, 3))
finish(fig, "c10_the_mix_moved.png", "The headline falls as the registry fills with trials run outside the US",
       "Completed interventional trials, % with results submitted by 20 Nov 2026, by where the trial ran")

# 11 ------------------------------------------------------------- small sponsors hold the overdue pile
sz = pd.read_csv(os.path.join(D, "h6_by_sponsor_size.csv"))
fig, ax = plt.subplots(figsize=(10, 4.8))
yy = np.arange(len(sz))[::-1]
ax.barh(yy + 0.19, sz.pct_of_trials, height=0.36, color=LIGHTBLUE)
ax.barh(yy - 0.19, sz.pct_of_no_results_no_cert, height=0.36, color=ORANGE)
for i, r in sz.iterrows():
    ax.text(r.pct_of_trials + 0.8, yy[i] + 0.19, f"{r.pct_of_trials:.0f}% of trials", va="center", fontsize=9.5, color=INK)
    ax.text(r.pct_of_no_results_no_cert + 0.8, yy[i] - 0.19, f"{r.pct_of_no_results_no_cert:.0f}% of trials with no results and no delay certificate",
            va="center", fontsize=9.5, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([f"Sponsors with {a}\n({b:,} sponsors)" for a, b in zip(sz.sponsor_size, sz.n_sponsors)])
ax.set_xlim(0, 100); ax.grid(axis="y", visible=False); ax.set_xlabel("%")
finish(fig, "c11_small_sponsors_hold_the_overdue_pile.png", "The overdue pile sits with sponsors who run few trials",
       f"Trials probably required to report, finished 18 Jan 2017 - 20 Nov 2024 ({int(sz.n_trials.sum()):,}); sponsor size = such trials under that lead-sponsor name")
print("charts written")
