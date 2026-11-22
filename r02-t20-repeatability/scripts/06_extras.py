"""R02 step 6 - breakout seasons, era robustness, the SMAT selection check.

usage: python3 -I 06_extras.py <WORK_DIR> <REPORT_DATA_DIR>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from r02lib import METRICS, load_pm, league_means, metric_values, cluster_boot_corr

WORK, OUT = sys.argv[1], sys.argv[2]
PM = load_pm(WORK)
L = league_means(PM)
PS = pd.read_parquet(os.path.join(WORK, 'player_season.parquet'))
seasons = pd.read_csv(os.path.join(OUT, 'seasons.csv'), parse_dates=['start', 'end'])
men = (PS.gender == 'male') & (PS.group == 'league')


def boot_mean(v, pid, B=1000, seed=2):
    codes, u = pd.factorize(pid)
    s = np.bincount(codes, weights=v); c = np.bincount(codes)
    W = np.random.default_rng(seed).multinomial(len(u), np.full(len(u), 1 / len(u)), size=B)
    mb = (W @ s) / (W @ c)
    return np.percentile(mb, 2.5), np.percentile(mb, 97.5)


# ---- (a) breakout seasons: last season far above the player's own earlier record in that competition
rows = []
for m, jump in [('sr', 15.0), ('econ', -0.75), ('bndpct', 3.0)]:
    lab, side, bc, n, d, sc = METRICS[m]
    v, rel, b = metric_values(PS, m, L)
    T = PS[list(dict.fromkeys(['pid', 'comp', 'sno', 'gender', 'group', n, d, bc]))].copy(); T['rel'] = rel; T['b'] = b
    lr = L[n] / L[d].where(L[d] > 0)
    T['rn'] = PS[n] - PS.sid.map(lr) * PS[d]
    T = T.sort_values(['pid', 'comp', 'sno'])
    g = T.groupby(['pid', 'comp'])
    # career before season N (all earlier seasons in this competition)
    T['c_rn'] = g.rn.cumsum() - T.rn; T['c_den'] = g[d].cumsum() - T[d]; T['c_b'] = g.b.cumsum() - T.b
    T['nprev'] = g.cumcount()
    T['career_rel'] = sc * T.c_rn / T.c_den.where(T.c_den > 0)
    nx = T[['pid', 'comp', 'sno', 'rel', 'b']].copy(); nx['sno'] -= 1
    J = T.merge(nx, on=['pid', 'comp', 'sno'], suffixes=('', '_next'))
    for scope, mask in [('Men: all franchise/domestic leagues', (J.gender == 'male') & (J.group == 'league')), ('IPL', J.comp == 'IPL')]:
        k = mask & (J.b >= 120) & (J.b_next >= 120) & (J.c_b >= 240) & (J.nprev >= 2) & J.career_rel.notna()
        x = J[k].copy()
        x['jump'] = x.rel - x.career_rel
        sel = x[(x.jump >= jump) if jump > 0 else (x.jump <= jump)]
        kept = (sel.rel_next - sel.career_rel)
        lo, hi = boot_mean(kept.values, sel.pid.values)
        rows.append(dict(metric=m, scope=scope, rule='season N beats own earlier career by %s or more' % jump, n=len(sel),
                         career_before=sel.career_rel.mean(), season_N=sel.rel.mean(), season_N1=sel.rel_next.mean(),
                         jump=sel.jump.mean(), jump_kept=kept.mean(), jump_kept_lo=lo, jump_kept_hi=hi,
                         kept_pct=100 * kept.mean() / sel.jump.mean(), kept_pct_lo=100 * lo / sel.jump.mean(), kept_pct_hi=100 * hi / sel.jump.mean(),
                         all_eligible=len(x)))
BR = pd.DataFrame(rows); BR.to_csv(os.path.join(OUT, 'breakouts.csv'), index=False)
pd.set_option('display.width', 250)
print(BR.round(2).to_string())

# ---- (b) era robustness for core metrics: pairs where season N started before 2018 vs 2018 onward
nx = PS.copy(); nx['sno'] -= 1
P = PS.merge(nx, on=['pid', 'comp', 'sno', 'gender', 'group'], suffixes=('', '_n'))
P = P[(P.season_n - P.season) <= 2]
Pn = P[[c for c in P.columns if c.endswith('_n')]].copy(); Pn.columns = [c[:-2] for c in Pn.columns]; Pn.index = P.index
er = []
for m in ['sr', 'bndpct', 'dotpct', 'avg', 'batval', 'econ', 'wktrate', 'bowlval', 'sr_adj', 'econ_adj']:
    v0, r0, b0 = metric_values(P, m, L); v1, r1, b1 = metric_values(Pn, m, L)
    for era, em in [('season N before 2018', P.season < 2018), ('season N 2018 onward', P.season >= 2018)]:
        for scope, sm in [('Men: all franchise/domestic leagues', (P.gender == 'male') & (P.group == 'league')), ('IPL', P.comp == 'IPL')]:
            k = em & sm & (b0 >= 120) & (b1 >= 120) & r0.notna() & r1.notna()
            res = cluster_boot_corr(r0[k], r1[k], P.pid[k], B=1000)
            er.append(dict(metric=m, scope=scope, era=era, r=res['r'], lo=res['lo'], hi=res['hi'], pairs=res['n']))
ER = pd.DataFrame(er); ER.to_csv(os.path.join(OUT, 'era_robustness.csv'), index=False)
print(ER.pivot_table(index=['scope', 'metric'], columns='era', values='r').round(3).to_string())

# ---- (c) SMAT -> IPL: is the strike-rate gap league strength or selection?
# Players who were already IPL regulars (>=120 balls in the previous IPL season) were not picked on their SMAT form.
for m in ['sr', 'econ']:
    lab, side, bc, n, d, sc = METRICS[m]
    lr = L[n] / L[d].where(L[d] > 0)
    X = PM[['pid', 'comp', 'sid', 'date']].copy(); X['rn'] = PM[n] - PM.sid.map(lr) * PM[d]; X['den'] = PM[d]; X['b'] = PM[bc]
    T = X.groupby(['pid', 'comp', 'sid']).agg(rn=('rn', 'sum'), den=('den', 'sum'), b=('b', 'sum')).reset_index().merge(seasons[['sid', 'sno', 'start']], on='sid')
    T['y'] = sc * T.rn / T.den
    ipl = T[(T.comp == 'IPL')]
    prev = ipl[['pid', 'sno', 'b']].copy(); prev['sno'] += 1
    tg = ipl[ipl.b >= 120].merge(prev.rename(columns={'b': 'b_prev'}), on=['pid', 'sno'], how='left').fillna({'b_prev': 0})
    W = tg[['pid', 'sid', 'start', 'y', 'b_prev']].merge(X[X.comp == 'SMAT'], on='pid', suffixes=('', '_s'))
    W = W[(W.date < W.start) & (W.date >= W.start - pd.Timedelta(days=365))]
    S = W.groupby(['pid', 'sid']).agg(rn=('rn', 'sum'), den=('den', 'sum'), bs=('b', 'sum'), y=('y', 'first'), b_prev=('b_prev', 'first')).reset_index()
    S['x'] = sc * S.rn / S.den
    S = S[S.bs >= 60]
    for lab2, k in [('already IPL regulars (>=120 balls previous IPL season)', S.b_prev >= 120), ('new or fringe IPL players', S.b_prev < 120)]:
        g = S[k]
        if len(g) < 10: continue
        lo, hi = boot_mean((g.y - g.x).values, g.pid.values)
        print('SMAT->IPL', m, lab2, 'n=%d  SMAT %+.2f  IPL %+.2f  gap %+.2f [%.2f, %.2f]' % (len(g), g.x.mean(), g.y.mean(), (g.y - g.x).mean(), lo, hi))
        with open(os.path.join(OUT, 'smat_selection_check.csv'), 'a' if (m != 'sr' or 'fringe' in lab2) else 'w') as f:
            if m == 'sr' and 'regulars' in lab2: f.write('metric,group,n,smat_rel,ipl_rel,gap,gap_lo,gap_hi\n')
            f.write('%s,"%s",%d,%.3f,%.3f,%.3f,%.3f,%.3f\n' % (m, lab2, len(g), g.x.mean(), g.y.mean(), (g.y - g.x).mean(), lo, hi))

# ---- (d) PR#1's split (alternate deliveries) vs R02's split (alternate matches), IPL batters >=150 balls in a season
Bv = pd.read_parquet(os.path.join(WORK, 'balls_valued.parquet'), columns=['comp', 'sid', 'match_id', 'date', 'innings', 'batter', 'faced', 'runs_batter'])
Bv = Bv[(Bv.comp == 'IPL') & (Bv.faced == 1)].reset_index(drop=True)
Bv = Bv.sort_values(['batter', 'sid', 'date', 'match_id', 'innings'], kind='stable')
Bv['ballno'] = Bv.groupby(['batter', 'sid']).cumcount()
tot = Bv.groupby(['batter', 'sid']).faced.transform('sum')
Bv = Bv[tot >= 150]
Bv['mno'] = Bv.groupby(['batter', 'sid']).match_id.transform(lambda s: pd.factorize(s)[0])
out = []
for lab2, col in [('alternate deliveries (PR#1 method)', 'ballno'), ('alternate matches (R02 method)', 'mno')]:
    Bv['h'] = Bv[col] % 2
    g = Bv.groupby(['batter', 'sid', 'h']).agg(r=('runs_batter', 'sum'), b=('faced', 'sum')).reset_index()
    g['sr'] = 100 * g.r / g.b
    pv = g.pivot_table(index=['batter', 'sid'], columns='h', values='sr').dropna()
    res = cluster_boot_corr(pv[0].values, pv[1].values, pv.index.get_level_values(0).values, B=1000)
    out.append(dict(method=lab2, r_half=res['r'], lo=res['lo'], hi=res['hi'], n=res['n']))
    print('IPL SR split-half,', lab2, 'r=%.3f [%.3f, %.3f] n=%d' % (res['r'], res['lo'], res['hi'], res['n']))
pd.DataFrame(out).to_csv(os.path.join(OUT, 'split_method_check_ipl.csv'), index=False)
