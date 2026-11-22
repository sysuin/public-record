"""R02 step 5 - does performance elsewhere predict the IPL (and other leagues)?

usage: python3 -I 05_crossleague.py <WORK_DIR> <REPORT_DATA_DIR>

For each target season of competition B (IPL first, then a matrix of major men's competitions, and the WPL):
  target  = player's value in B that season, relative to B's season average, >= 120 balls
  source  = the same player's value in competition A over the 365 days before B's season started, relative to
            A's own season averages, >= 60 balls
We report how closely source tracks target (cluster-bootstrapped by player), the same figure corrected for the
size of both samples (using each metric's balls-to-half-signal from step 3, pooled men's leagues), and the
average gap (target minus source) - a rough read of how much harder B is than A for the players who play both.
Baseline row: A = B's own previous season (same window rule).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from r02lib import METRICS, load_pm, league_means, cluster_boot_corr

WORK, OUT = sys.argv[1], sys.argv[2]
PM = load_pm(WORK)
L = league_means(PM)
seasons = pd.read_csv(os.path.join(OUT, 'seasons.csv'), parse_dates=['start', 'end'])
SU = pd.read_csv(os.path.join(OUT, 'signal_summary_main.csv'))
Kmap = SU[SU.scope == 'Men: all franchise/domestic leagues'].set_index('metric').balls_to_half_signal
KmapW = SU[SU.scope == 'Women: all franchise/domestic leagues'].set_index('metric').balls_to_half_signal
METS = ['sr', 'bndpct', 'dotpct', 'econ', 'sr_adj', 'econ_adj', 'batval', 'bowlval', 'wktrate', 'avg']
TMIN, SMIN = 120, 60

def relcols(m):
    lab, side, bc, n, d, sc = METRICS[m]
    lr = L[n] / L[d].where(L[d] > 0)
    return PM[n] - PM.sid.map(lr) * PM[d], PM[d], PM[bc], sc

rows, gaprows = [], []
TARGETS = ['IPL', 'BBL', 'PSL', 'CPL', 'SA20', 'ILT20', 'BLAST', 'T20I', 'HUNDRED', 'MLC', 'WPL', 'WBBL', 'HUNDREDW']
for m in METS:
    rn, den, b, sc = relcols(m)
    X = PM[['pid', 'comp', 'sid', 'date', 'gender']].copy(); X['rn'] = rn; X['den'] = den; X['b'] = b
    X = X[X.b > 0]
    T = X.groupby(['pid', 'comp', 'sid']).agg(rn=('rn', 'sum'), den=('den', 'sum'), b=('b', 'sum')).reset_index()
    T['y'] = sc * T.rn / T.den.where(T.den > 0)
    T = T.merge(seasons[['sid', 'start', 'sno']], on='sid')
    for tc in TARGETS:
        tg = T[(T.comp == tc) & (T.b >= TMIN) & T.y.notna()]
        if tg.empty: continue
        W = tg[['pid', 'sid', 'sno', 'start', 'y', 'b']].merge(X, on='pid', suffixes=('', '_src'))
        W = W[(W.date < W.start) & (W.date >= W.start - pd.Timedelta(days=365))]
        S = W.groupby(['pid', 'sid', 'comp']).agg(rn=('rn', 'sum'), den=('den', 'sum'), bs=('b_src', 'sum') if 'b_src' in W else ('b', 'sum')).reset_index()
        S = S.merge(tg[['pid', 'sid', 'y', 'b']], on=['pid', 'sid'])
        S['x'] = sc * S.rn / S.den.where(S.den > 0)
        S = S[(S.bs >= SMIN) & S.x.notna()]
        gender = 'female' if tc in ('WPL', 'WBBL', 'HUNDREDW') else 'male'
        K = (KmapW if gender == 'female' else Kmap).get(m, np.nan)
        # grouped sources for the IPL: own previous season / Indian domestic / internationals / all overseas leagues
        if tc == 'IPL':
            W2 = W.copy()
            W2['comp'] = np.select([W2.comp == 'IPL', W2.comp == 'SMAT', W2.comp == 'T20I'], ['IPL', 'GROUP: SMAT', 'GROUP: T20I'], 'GROUP: overseas leagues + Hundred')
            S2 = W2.groupby(['pid', 'sid', 'comp']).agg(rn=('rn', 'sum'), den=('den', 'sum'), bs=('b_src', 'sum')).reset_index()
            S2 = S2.merge(tg[['pid', 'sid', 'y', 'b']], on=['pid', 'sid'])
            S2['x'] = sc * S2.rn / S2.den.where(S2.den > 0)
            S2 = S2[(S2.bs >= SMIN) & S2.x.notna() & S2.comp.str.startswith('GROUP')]
            S = pd.concat([S, S2])
        for sc_comp, g in S.groupby('comp'):
            if len(g) < 25: continue
            res = cluster_boot_corr(g.x, g.y, g.pid, B=1000, slope=True)
            relS = (g.bs / (g.bs + K)).mean(); relT = (g.b / (g.b + K)).mean()
            gap = (g.y - g.x).values
            codes, u = pd.factorize(g.pid)
            rng = np.random.default_rng(5)
            Wt = rng.multinomial(len(u), np.full(len(u), 1 / len(u)), size=1000)
            gs = (Wt @ np.bincount(codes, weights=gap)) / (Wt @ np.bincount(codes))
            rows.append(dict(metric=m, target=tc, source=sc_comp, same_comp=sc_comp == tc, n=res['n'], players=res['players'],
                             r=res['r'], lo=res['lo'], hi=res['hi'], slope=res['slope'], slope_lo=res['slope_lo'], slope_hi=res['slope_hi'],
                             mean_src_balls=g.bs.mean(), mean_tgt_balls=g.b.mean(),
                             r_size_corrected=res['r'] / np.sqrt(relS * relT) if relS > 0 and relT > 0 else np.nan,
                             mean_source=g.x.mean(), mean_target=g.y.mean(), gap=gap.mean(),
                             gap_lo=np.percentile(gs, 2.5), gap_hi=np.percentile(gs, 97.5)))
R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, 'cross_league.csv'), index=False)
pd.set_option('display.width', 250)
for m in ['sr', 'econ', 'bndpct']:
    print(m)
    print(R[(R.target == 'IPL') & (R.metric == m)].sort_values('r', ascending=False)[
        ['source', 'n', 'players', 'r', 'lo', 'hi', 'r_size_corrected', 'slope', 'mean_source', 'mean_target', 'gap', 'gap_lo', 'gap_hi']].round(3).to_string(index=False))
print(R[(R.target == 'WPL')][['metric', 'source', 'n', 'r', 'lo', 'hi', 'gap']].round(3).to_string(index=False))
