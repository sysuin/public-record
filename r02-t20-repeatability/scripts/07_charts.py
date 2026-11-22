"""R02 step 7 - draft charts (PNG). Plain-language titles, direct labels, no red/green-only encoding.

usage: python3 -I 07_charts.py <REPORT_DATA_DIR> <CHARTS_DIR>
"""
import os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, AQUA, YELLOW, VIOLET, GREY = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#6250d6', '#8a8984'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e6e5e0'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.facecolor': '#fcfcfb'})
MEN = 'Men: all franchise/domestic leagues'
SRC = 'Source: Cricsheet ball-by-ball data (cricsheet.org), men\'s franchise & domestic T20 leagues; Sartium analysis.'
NAMES = {'sr': 'Strike rate', 'avg': 'Batting average', 'bndpct': 'Boundary %', 'dotpct': 'Dot-ball % (batting)',
         'batval': 'Batting runs added', 'econ': 'Economy rate', 'wktrate': 'Wicket rate', 'bdotpct': 'Dot-ball % (bowling)',
         'bndcpct': 'Boundaries conceded', 'bowlval': 'Bowling runs saved', 'sr_adj': 'Strike rate, situation-adjusted',
         'econ_adj': 'Economy, situation-adjusted', 'wkt_adj': 'Wickets, situation-adjusted', 'outrate': 'Dismissal rate'}


def finish(fig, ax, title, sub, fn, src=SRC):
    fig.suptitle(title, x=0.02, ha='left', fontsize=15, fontweight='bold', color=INK, y=0.985)
    fig.text(0.02, 0.925, sub, ha='left', fontsize=10.5, color=INK2)
    fig.text(0.02, 0.015, src, ha='left', fontsize=8, color=INK2)
    fig.savefig(os.path.join(OUT, fn), dpi=160)
    plt.close(fig)


SU = pd.read_csv(os.path.join(DATA, 'signal_summary_main.csv'))
Y = pd.read_csv(os.path.join(DATA, 'yoy_repeatability.csv'))

# 1. how much of a season carries into the next
mets = ['bndcpct', 'bdotpct', 'bndpct', 'dotpct', 'econ', 'sr', 'econ_adj', 'outrate', 'wktrate', 'batval', 'bowlval', 'avg', 'wkt_adj']
d = SU[(SU.scope == MEN) & SU.metric.isin(mets)].set_index('metric').loc[mets[::-1]]
fig, ax = plt.subplots(figsize=(10, 7.2)); fig.subplots_adjust(left=0.30, top=0.86, bottom=0.12, right=0.95)
yy = np.arange(len(d))
ax.hlines(yy, d.yoy_lo, d.yoy_hi, color=BLUE, lw=2)
ax.plot(d.r_yoy, yy, 'o', color=BLUE, ms=9, mec='#fcfcfb', mew=2)
for i, (m, r) in enumerate(d.iterrows()):
    ax.text(r.yoy_hi + 0.012, i, '%.2f' % r.r_yoy, va='center', fontsize=10, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([NAMES[m] for m in d.index])
ax.set_xlim(0, 0.75); ax.axvline(0, color=GRID); ax.grid(axis='x', color=GRID); ax.set_axisbelow(True)
ax.set_xlabel('How closely a player\'s next season tracks this one  (0 = not at all, 1 = exactly)')
finish(fig, ax, 'What a T20 season tells you about the next one', 'Same player, same league, consecutive seasons, at least 120 balls in both. Line = range of plausible values.', 'chart01_season_to_season.png')

# 2. balls before a number is half skill
mets2 = ['bdotpct', 'bndpct', 'bndcpct', 'sr_adj', 'dotpct', 'sr', 'econ', 'batval', 'econ_adj', 'outrate', 'wktrate', 'bowlval', 'avg']
d = SU[(SU.scope == MEN) & SU.metric.isin(mets2)].set_index('metric').loc[mets2[::-1]]
fig, ax = plt.subplots(figsize=(10, 7.2)); fig.subplots_adjust(left=0.30, top=0.86, bottom=0.12, right=0.93)
yy = np.arange(len(d))
ax.barh(yy, d.balls_to_half_signal, color=[ORANGE if m in ('avg', 'wktrate', 'bowlval', 'outrate') else BLUE for m in d.index], height=0.6)
ax.hlines(yy, d.K_lo, d.K_hi.clip(upper=4000), color=INK2, lw=1)
for i, (m, r) in enumerate(d.iterrows()):
    ax.text(min(r.K_hi, 4000) + 40, i, '%d balls' % round(r.balls_to_half_signal, -1), va='center', fontsize=10, color=INK)
ax.axvline(220, color=INK2, ls='--', lw=1)
ax.text(240, -0.9, '<- a typical regular\'s season (~220 balls)', fontsize=9, color=INK2, va='center')
ax.set_yticks(yy); ax.set_yticklabels([NAMES[m] for m in d.index]); ax.set_xlim(0, 4600); ax.set_ylim(-1.4, len(d) - 0.5)
ax.set_xlabel('Balls a player needs before the number is more skill than luck')
ax.grid(axis='x', color=GRID); ax.set_axisbelow(True)
finish(fig, ax, 'Some numbers settle in a season. Others take five.', 'Balls needed before half of what you see is the player rather than chance. Orange: needs more than three seasons.', 'chart02_balls_to_signal.png')

# 3. forecast contest
F = pd.read_csv(os.path.join(DATA, 'forecast_contest.csv'))
F = F[F.split.str.startswith('train<=2019')]
lab = {'F1': 'Last season, as recorded', 'F2': 'Career to date', 'F4': 'Last season, pulled\ntoward average', 'F5': 'Recent seasons weighted,\npulled toward average', 'F6': '...plus every T20 league\nin the last 3 years'}
fig, axes = plt.subplots(1, 3, figsize=(13, 6.4), sharey=True); fig.subplots_adjust(left=0.20, top=0.80, bottom=0.14, right=0.97, wspace=0.12)
for ax, (m, t) in zip(axes, [('sr', 'Strike rate'), ('econ', 'Economy'), ('wktrate', 'Wicket rate')]):
    d = F[(F.scope == MEN) & (F.metric == m)].set_index('forecast').loc[['F6', 'F5', 'F4', 'F2', 'F1']]
    yy = np.arange(len(d))
    cols = [ORANGE if v < 0 else BLUE for v in d.explained_pct]
    ax.barh(yy, d.explained_pct, color=cols, height=0.6)
    ax.hlines(yy, d.explained_lo, d.explained_hi, color=INK2, lw=1)
    for i, v in enumerate(d.explained_pct):
        ax.text(v + (2 if v >= 0 else -2), i + 0.33, '%+.0f%%' % v, ha='left' if v >= 0 else 'right', va='center', fontsize=10, color=INK)
    ax.axvline(0, color=INK, lw=1); ax.set_title(t, loc='left', fontsize=12, color=INK)
    ax.set_xlim(-110, 45); ax.grid(axis='x', color=GRID); ax.set_axisbelow(True)
axes[0].set_yticks(yy); axes[0].set_yticklabels([lab[k] for k in d.index])
axes[1].set_xlabel('Better (+) or worse (-) than predicting every player is league-average, % of error removed')
finish(fig, axes[0], 'Taking last season at face value is worse than assuming everyone is average',
       'Predicting 2020-2026 seasons using only earlier data (settings chosen on 2008-2019). 1,613 batter-seasons, 1,701 bowler-seasons.', 'chart03_forecast_contest.png')

# 4. edge kept
E = pd.read_csv(os.path.join(DATA, 'edge_kept_quintiles.csv'))
fig, axes = plt.subplots(1, 2, figsize=(12, 6.2)); fig.subplots_adjust(left=0.07, top=0.80, bottom=0.14, right=0.97, wspace=0.28)
for ax, (m, t, unit, inv) in zip(axes, [('sr', 'Strike rate vs league average', 'runs per 100 balls', False), ('econ', 'Economy vs league average', 'runs per over (lower = better)', True)]):
    d = E[(E.scope == MEN) & (E.metric == m)].sort_values('quintile')
    for _, r in d.iterrows():
        ax.plot([0, 1], [r.mean_N, r.mean_N1], color=BLUE if r.quintile in (1, 5) else GREY, lw=2 if r.quintile in (1, 5) else 1.2)
        ax.plot([0, 1], [r.mean_N, r.mean_N1], 'o', color=BLUE if r.quintile in (1, 5) else GREY, ms=7)
        ax.text(-0.04, r.mean_N, '%+.1f' % r.mean_N, ha='right', va='center', fontsize=10, color=INK)
        ax.text(1.04, r.mean_N1, '%+.1f' % r.mean_N1, ha='left', va='center', fontsize=10, color=INK)
    best = d[d.quintile == (1 if inv else 5)].iloc[0]
    ax.text(1.04, best.mean_N1 + (0.12 if inv else -1) * (-1 if inv else 1) * 0 + (-0.25 if inv else 4.5), 'best fifth keeps %d%%\nof its edge' % round(best.kept_pct), ha='left', fontsize=9.5, color=BLUE,
            va='center')
    ax.axhline(0, color=INK2, lw=0.8, ls=':')
    ax.set_xticks([0, 1]); ax.set_xticklabels(['Season N', 'Season N+1']); ax.set_xlim(-0.35, 1.6)
    ax.set_title(t, loc='left', fontsize=12, color=INK); ax.set_ylabel(unit)
    if inv: ax.invert_yaxis()
finish(fig, axes[0], 'The best seasons fall back about halfway, or further',
       'Players split into fifths by season N; lines show the same players the next season (>=120 balls both years).', 'chart04_edge_kept.png')

# 5. the job repeats, the performance much less
mets5 = [('bowl_pp_share', 'Share of overs in powerplay'), ('bat_pp_share', 'Share of balls faced in powerplay'), ('bowl_death_share', 'Share of overs at the death'),
         ('bat_death_share', 'Share of balls faced at the death'), ('econ', 'Economy'), ('sr', 'Strike rate'), ('econ_adj', 'Economy, situation-adjusted'),
         ('wktrate', 'Wicket rate'), ('wkt_adj', 'Wickets, situation-adjusted')]
d = SU[SU.scope == MEN].set_index('metric').loc[[m for m, _ in mets5][::-1]]
fig, ax = plt.subplots(figsize=(10, 6.4)); fig.subplots_adjust(left=0.33, top=0.84, bottom=0.12, right=0.95)
yy = np.arange(len(d)); job = [m.endswith('share') for m in d.index]
ax.hlines(yy, d.yoy_lo, d.yoy_hi, color=[VIOLET if j else BLUE for j in job], lw=2)
ax.scatter(d.r_yoy, yy, marker='s', c=[VIOLET if j else BLUE for j in job], s=70, zorder=3)
for i, (m, r) in enumerate(d.iterrows()):
    ax.text(r.yoy_hi + 0.015, i, '%.2f' % r.r_yoy, va='center', fontsize=10, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([dict(mets5)[m] for m in d.index]); ax.set_xlim(0, 1)
ax.text(0.45, 6.6, 'THE JOB (when a coach uses them)', color=VIOLET, fontsize=10, ha='center')
ax.text(0.62, 1.2, 'THE PERFORMANCE', color=BLUE, fontsize=10, ha='center')
ax.grid(axis='x', color=GRID); ax.set_axisbelow(True)
ax.set_xlabel('How closely next season tracks this one (0 = not at all, 1 = exactly)')
finish(fig, ax, 'What repeats is the job, not the output', 'Men\'s leagues, consecutive seasons, >=120 balls both years.', 'chart05_job_vs_performance.png')

# 6. cross-league into the IPL
C = pd.read_csv(os.path.join(DATA, 'cross_league.csv'))
srcs = [('IPL', 'IPL, previous season'), ('GROUP: overseas leagues + Hundred', 'Overseas leagues + Hundred'), ('GROUP: T20I', 'T20 internationals'), ('GROUP: SMAT', 'Syed Mushtaq Ali (Indian domestic)')]
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6), sharey=True); fig.subplots_adjust(left=0.24, top=0.80, bottom=0.15, right=0.97, wspace=0.1)
for ax, (m, t) in zip(axes, [('sr', 'Strike rate'), ('econ', 'Economy')]):
    d = C[(C.target == 'IPL') & (C.metric == m)].set_index('source').loc[[s for s, _ in srcs][::-1]]
    yy = np.arange(len(d))
    ax.hlines(yy, d.lo, d.hi, color=BLUE, lw=2); ax.plot(d.r, yy, 'o', color=BLUE, ms=9, mec='#fcfcfb', mew=2)
    for i, (s, r) in enumerate(d.iterrows()):
        ax.text(r.hi + 0.02, i, '%.2f  (n=%d)' % (r.r, r.n), va='center', fontsize=9.5, color=INK)
    ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-0.3, 0.95); ax.set_title(t, loc='left', fontsize=12, color=INK)
    ax.grid(axis='x', color=GRID); ax.set_axisbelow(True)
axes[0].set_yticks(yy); axes[0].set_yticklabels([dict(srcs)[s] for s in d.index])
axes[0].set_xlabel('How closely IPL season tracks the source (0 = not at all)')
finish(fig, axes[0], 'Form elsewhere predicts the IPL about as well as the IPL does - except Indian domestic bowling',
       'Source = the player\'s matches in the 365 days before the IPL season (>=60 balls); target = that IPL season (>=120 balls), 2009-2026.',
       'chart06_cross_league_ipl.png', src='Source: Cricsheet ball-by-ball data (cricsheet.org); Sartium analysis.')

# 7. threshold robustness
fig, ax = plt.subplots(figsize=(10, 6)); fig.subplots_adjust(left=0.09, top=0.84, bottom=0.12, right=0.80)
for m, c in [('econ', BLUE), ('sr', ORANGE), ('wktrate', AQUA), ('avg', VIOLET)]:
    d = Y[(Y.metric == m) & (Y.scope == MEN)].sort_values('min_balls')
    ax.fill_between(d.min_balls, d.lo, d.hi, color=c, alpha=0.12, lw=0)
    ax.plot(d.min_balls, d.r, '-o', color=c, lw=2, ms=5)
    ax.text(d.min_balls.iloc[-1] + 10, d.r.iloc[-1], NAMES[m], color=INK, va='center', fontsize=10)
ax.set_xlabel('Minimum balls in BOTH seasons to be counted'); ax.set_ylabel('Season-to-season tracking')
ax.grid(color=GRID); ax.set_axisbelow(True); ax.set_ylim(0, 0.75)
finish(fig, ax, 'Bigger samples repeat more - but never by much', 'Men\'s leagues. Shaded = range of plausible values. Fewer players qualify at higher bars (6,141 pairs at 30 balls, ~100 at 300).', 'chart07_threshold.png')

# 8. by league
fig, axes = plt.subplots(1, 2, figsize=(12.5, 7.4), sharey=False); fig.subplots_adjust(left=0.10, top=0.85, bottom=0.10, right=0.97, wspace=0.35)
for ax, m, t in zip(axes, ['sr', 'econ'], ['Strike rate', 'Economy']):
    WOM = ['WBBL', 'T20IW', 'SSMW', 'HUNDREDW', 'WPL', 'CEC', 'WBLAST', 'KSL', 'WCPL', 'BLAZE', 'FAIRBREAK', 'WT20C']
    d = Y[(Y.metric == m) & (Y.min_balls == 120) & (~Y.scope.str.contains(':')) & (~Y.scope.isin(WOM)) & (Y.pairs >= 40)].sort_values('r')
    yy = np.arange(len(d))
    ax.hlines(yy, d.lo, d.hi, color=BLUE, lw=1.6); ax.plot(d.r, yy, 'o', color=BLUE, ms=7)
    pooled = SU[(SU.scope == MEN) & (SU.metric == m)].r_yoy.iloc[0]
    ax.axvline(pooled, color=ORANGE, ls='--', lw=1.2); ax.text(pooled + 0.01, len(d) - 0.3, 'all men\'s leagues %.2f' % pooled, color=INK2, fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(['%s (%d)' % (s, n) for s, n in zip(d.scope, d.pairs)], fontsize=9.5)
    ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-0.4, 0.9); ax.set_title(t, loc='left', fontsize=12, color=INK)
    ax.grid(axis='x', color=GRID); ax.set_axisbelow(True)
finish(fig, axes[0], 'The pattern holds league by league', 'Men. Season-to-season tracking by competition (pairs of seasons in brackets; competitions with at least 40 pairs).', 'chart08_by_league.png',
       src='Source: Cricsheet ball-by-ball data (cricsheet.org); Sartium analysis.')
print('charts written:', sorted(os.listdir(OUT)))
