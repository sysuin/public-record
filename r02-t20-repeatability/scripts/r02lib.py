"""Shared helpers for R02: metric definitions, player-season table, cluster bootstrap."""
import os
import numpy as np, pandas as pd

KEY = ['pid', 'comp', 'sid', 'sno', 'season', 'gender', 'group']

# key: (label, side, balls column used for thresholds, numerator, denominator, scale)
METRICS = {
    'sr':      ('Strike rate (runs per 100 balls)', 'bat', 'bf', 'runs', 'bf', 100.0),
    'avg':     ('Batting average (runs per dismissal)', 'bat', 'bf', 'runs', 'outs', 1.0),
    'bndpct':  ('Boundary % (4s+6s per ball faced)', 'bat', 'bf', 'bnd', 'bf', 100.0),
    'dotpct':  ('Dot-ball % (batting)', 'bat', 'bf', 'dots', 'bf', 100.0),
    'outrate': ('Dismissals per 100 balls faced', 'bat', 'bf', 'outs', 'bf', 100.0),
    'batval':  ('Batting runs added per 100 balls', 'bat', 'bf', 'bat_val', 'bf', 100.0),
    'econ':    ('Economy (runs per 6 balls)', 'bowl', 'lb', 'rc', 'lb', 6.0),
    'wktrate': ('Wickets per 24 balls', 'bowl', 'lb', 'wkts', 'lb', 24.0),
    'bdotpct': ('Dot-ball % (bowling)', 'bowl', 'lb', 'bdots', 'lb', 100.0),
    'bndcpct': ('Boundaries conceded per 100 balls', 'bowl', 'lb', 'bndc', 'lb', 100.0),
    'bowlval': ('Bowling runs saved per 100 balls', 'bowl', 'lb', 'bowl_val', 'lb', 100.0),
    # situation-adjusted versions: compared with an average player in the same over and wickets-down state
    'sr_adj':  ('Strike rate vs same-situation average (runs per 100 balls)', 'bat', 'bf', 'bat_rx', 'bf', 100.0),
    'econ_adj': ('Economy vs same-situation average (runs per 6 balls)', 'bowl', 'lb', 'bowl_rx', 'lb', 6.0),
    'wkt_adj': ('Wickets vs same-situation average (per 24 balls)', 'bowl', 'lb', 'bowl_wx', 'lb', 24.0),
    # the job, not the performance: share of balls in each phase
    'bat_pp_share': ('Share of balls faced in the powerplay', 'bat', 'bf', 'bf_pp', 'bf', 100.0),
    'bat_death_share': ('Share of balls faced at the death', 'bat', 'bf', 'bf_death', 'bf', 100.0),
    'bowl_pp_share': ('Share of balls bowled in the powerplay', 'bowl', 'lb', 'lb_pp', 'lb', 100.0),
    'bowl_death_share': ('Share of balls bowled at the death', 'bowl', 'lb', 'lb_death', 'lb', 100.0),
}
for ph, nm in [('pp', 'powerplay (overs 1-6)'), ('mid', 'middle (overs 7-15)'), ('death', 'death (overs 16-20)')]:
    METRICS['sr_' + ph] = ('Strike rate, ' + nm, 'bat', 'bf_' + ph, 'runs_' + ph, 'bf_' + ph, 100.0)
    METRICS['econ_' + ph] = ('Economy, ' + nm, 'bowl', 'lb_' + ph, 'rc_' + ph, 'lb_' + ph, 6.0)
    METRICS['wkt_' + ph] = ('Wickets per 24 balls, ' + nm, 'bowl', 'lb_' + ph, 'wk_' + ph, 'lb_' + ph, 24.0)
for r, nm in [('open', 'openers (No. 1-2)'), ('top', 'No. 3-4'), ('fin', 'finishers (No. 5-7)')]:
    METRICS['sr_' + r] = ('Strike rate, ' + nm, 'bat', 'bf_' + r, 'runs_' + r, 'bf_' + r, 100.0)

CORE = ['sr', 'avg', 'bndpct', 'dotpct', 'batval', 'econ', 'wktrate', 'bowlval', 'sr_adj', 'econ_adj']


def load_pm(work):
    PM = pd.read_parquet(os.path.join(work, 'player_match.parquet'))
    PM['date'] = pd.to_datetime(PM.date)
    for r, lo, hi in [('open', 1, 2), ('top', 3, 4), ('fin', 5, 7)]:
        m = PM.bat_pos.between(lo, hi)
        PM['bf_' + r] = np.where(m, PM.bf, 0)
        PM['runs_' + r] = np.where(m, PM.runs, 0)
    return PM


def player_seasons(PM):
    num = [c for c in PM.columns if c not in KEY + ['match_id', 'date', 'bat_pos']]
    PS = PM.groupby(KEY)[num].sum().reset_index()
    PS['m_bat'] = PM[PM.bf > 0].groupby(KEY).size().reindex(pd.MultiIndex.from_frame(PS[KEY])).fillna(0).values
    PS['m_bowl'] = PM[PM.lb > 0].groupby(KEY).size().reindex(pd.MultiIndex.from_frame(PS[KEY])).fillna(0).values
    return PS


def league_means(PM):
    num = [c for c in PM.columns if c not in KEY + ['match_id', 'date', 'bat_pos']]
    return PM.groupby('sid')[num].sum()


def metric_values(df, m, L=None):
    """Return (value, relative-to-competition-season value, balls) for metric m on table df."""
    lab, side, bc, n, d, sc = METRICS[m]
    den = df[d].astype(float)
    v = sc * df[n] / den.where(den > 0)
    rel = None
    if L is not None:
        lv = sc * L[n] / L[d].where(L[d] > 0)
        rel = v - df.sid.map(lv)
    return v, rel, df[bc]


def corr_from_sums(S):
    n, sx, sy, sxx, syy, sxy = S
    cov = sxy - sx * sy / n
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    return cov / np.sqrt(vx * vy)


def cluster_boot_corr(x, y, cl, B=1000, seed=7, slope=False):
    """Pearson r with a percentile 95% interval from resampling clusters (players) with replacement.
    Players appear in several season-pairs, so resampling pairs would understate uncertainty."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, cl = x[ok], y[ok], np.asarray(cl)[ok]
    if len(x) < 10:
        return dict(r=np.nan, lo=np.nan, hi=np.nan, n=len(x), players=len(set(cl)))
    codes, uniq = pd.factorize(cl)
    k = len(uniq)
    agg = np.zeros((6, k))
    for j, arr in enumerate([np.ones_like(x), x, y, x * x, y * y, x * y]):
        agg[j] = np.bincount(codes, weights=arr, minlength=k)
    r = corr_from_sums(agg.sum(1))
    rng = np.random.default_rng(seed)
    W = rng.multinomial(k, np.full(k, 1.0 / k), size=B).astype(float)
    S = W @ agg.T  # B x 6
    rb = corr_from_sums(S.T)
    out = dict(r=r, lo=np.nanpercentile(rb, 2.5), hi=np.nanpercentile(rb, 97.5), n=len(x), players=k)
    if slope:
        n_, sx, sy, sxx, syy, sxy = agg.sum(1)
        out['slope'] = (sxy - sx * sy / n_) / (sxx - sx * sx / n_)
        sb = (S[:, 5] - S[:, 1] * S[:, 2] / S[:, 0]) / (S[:, 3] - S[:, 1] ** 2 / S[:, 0])
        out['slope_lo'], out['slope_hi'] = np.nanpercentile(sb, 2.5), np.nanpercentile(sb, 97.5)
    return out


def season_pairs(PS, seasons, max_gap_years=2):
    """(comp, sno) -> next season (comp, sno+1) if it started within max_gap_years."""
    s = seasons.set_index('sid')
    PS = PS.copy()
    PS['start'] = PS.sid.map(pd.to_datetime(s.start))
    return PS
