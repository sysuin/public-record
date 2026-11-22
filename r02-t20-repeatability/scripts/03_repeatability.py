"""R02 step 3 - season-to-season repeatability, split-half reliability, balls-to-half-signal, edge kept.

usage: python3 -I 03_repeatability.py <WORK_DIR> <REPORT_DATA_DIR>

Every metric is measured relative to its competition-season average (so a strike rate of 150 in a 140 league
is +10), which removes league and era scoring levels from all comparisons.
Season pairs: same player, same competition, consecutive seasons (next season starting within 2 calendar years).
Split-half: within one season, the player's 1st, 3rd, 5th... matches against his 2nd, 4th, 6th...
(PR#1 split alternate deliveries, which shares match conditions across halves and overstates reliability.)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from r02lib import METRICS, CORE, KEY, load_pm, player_seasons, league_means, metric_values, cluster_boot_corr

WORK, OUT = sys.argv[1], sys.argv[2]
PM = load_pm(WORK)
PS = player_seasons(PM)
L = league_means(PM)
seasons = pd.read_csv(os.path.join(OUT, 'seasons.csv'))
PS.to_parquet(os.path.join(WORK, 'player_season.parquet'), index=False)

MEN_LEAGUES = PS[(PS.gender == 'male') & (PS.group == 'league')].comp.unique().tolist()
WOMEN_LEAGUES = PS[(PS.gender == 'female') & (PS.group == 'league')].comp.unique().tolist()
SCOPES = {'Men: all franchise/domestic leagues': ('male', ['league']),
          'Women: all franchise/domestic leagues': ('female', ['league']),
          'Men: leagues + Hundred + T20I': ('male', ['league', 'hundred', 't20i']),
          'Women: leagues + Hundred + T20I': ('female', ['league', 'hundred', 't20i'])}

# --- pairs table (N, N+1)
nx = PS.copy(); nx['sno'] = nx.sno - 1
P = PS.merge(nx, on=['pid', 'comp', 'sno', 'gender', 'group'], suffixes=('', '_n'))
P = P[(P.season_n - P.season) <= 2]
print('season pairs (any balls):', len(P))


def scope_mask(df, scope):
    if scope in SCOPES:
        g, groups = SCOPES[scope]
        return (df.gender == g) & df.group.isin(groups)
    return df.comp == scope


rows = []
THR = [30, 60, 120, 180, 240, 300, 400]
comps = sorted(PS.comp.unique())
for m in METRICS:
    lab, side, bc, n, d, sc = METRICS[m]
    v0, r0, b0 = metric_values(P, m, L)
    Pn = P[[c for c in P.columns if c.endswith('_n')]].copy()
    Pn.columns = [c[:-2] for c in Pn.columns]
    v1, r1, b1 = metric_values(Pn.set_index(P.index), m, L)
    for scope in list(SCOPES) + comps:
        sm = scope_mask(P, scope)
        thr = THR if (scope in SCOPES or scope == 'IPL') else [60, 120, 240]
        if m not in CORE and scope not in SCOPES and scope != 'IPL':
            continue
        for T in thr:
            k = sm & (b0 >= T) & (b1 >= T) & r0.notna() & r1.notna()
            if k.sum() < 20:
                continue
            res = cluster_boot_corr(r0[k], r1[k], P.pid[k], B=1000 if scope in SCOPES or scope == 'IPL' else 400, slope=True)
            rows.append(dict(metric=m, label=lab, side=side, scope=scope, min_balls=T, r=res['r'], lo=res['lo'], hi=res['hi'],
                             slope=res['slope'], slope_lo=res['slope_lo'], slope_hi=res['slope_hi'], pairs=res['n'], players=res['players'],
                             mean_balls_N=float(b0[k].mean()), mean_balls_N1=float(b1[k].mean())))
Y = pd.DataFrame(rows)
Y.to_csv(os.path.join(OUT, 'yoy_repeatability.csv'), index=False)
print('yoy rows', len(Y))

# --- split halves by alternate matches within a season
PM = PM.sort_values(['pid', 'sid', 'date', 'match_id'])
PM['k_bat'] = PM.groupby(['pid', 'sid']).bf.transform(lambda s: (s > 0).cumsum())
PM['k_bowl'] = PM.groupby(['pid', 'sid']).lb.transform(lambda s: (s > 0).cumsum())
num = [c for c in PM.columns if c not in KEY + ['match_id', 'date', 'bat_pos', 'k_bat', 'k_bowl']]
H = {}
for side, kc in [('bat', 'k_bat'), ('bowl', 'k_bowl')]:
    x = PM[PM[kc] > 0].copy()
    if side == 'bat':
        x = x[x.bf > 0]
    else:
        x = x[x.lb > 0]
    x['half'] = x[kc] % 2
    H[side] = x.groupby(KEY + ['half'])[num].sum().reset_index()

srows = []
for m in METRICS:
    lab, side, bc, n, d, sc = METRICS[m]
    h = H[side]
    a = h[h.half == 1].set_index(KEY); b = h[h.half == 0].set_index(KEY)
    j = a.join(b, how='inner', lsuffix='', rsuffix='_b')
    ja = j[[c for c in j.columns if not c.endswith('_b')]].reset_index()
    jb = j[[c[:-2] for c in j.columns if c.endswith('_b')]].copy() if False else None
    jb = j[[c for c in j.columns if c.endswith('_b')]].copy(); jb.columns = [c[:-2] for c in jb.columns]; jb = jb.reset_index()
    va, ra, ba = metric_values(ja, m, L)
    vb, rb, bb = metric_values(jb, m, L)
    for scope in list(SCOPES) + (comps if m in CORE else ['IPL']):
        sm = scope_mask(ja, scope)
        for T in (THR if (scope in SCOPES or scope == 'IPL') else [120, 240]):
            k = sm & (ba >= T / 2) & (bb >= T / 2) & ra.notna() & rb.notna()
            if k.sum() < 20:
                continue
            res = cluster_boot_corr(ra[k], rb[k], ja.pid[k], B=1000 if scope in SCOPES or scope == 'IPL' else 400)
            nh = float((2 * ba[k] * bb[k] / (ba[k] + bb[k])).mean())  # typical balls per half
            K = nh * (1 - res['r']) / res['r'] if res['r'] > 0 else np.inf
            Klo = nh * (1 - res['hi']) / res['hi'] if res['hi'] > 0 else np.inf
            Khi = nh * (1 - res['lo']) / res['lo'] if res['lo'] > 0 else np.inf
            srows.append(dict(metric=m, label=lab, side=side, scope=scope, min_balls_season=T, r_half=res['r'], lo=res['lo'], hi=res['hi'],
                              n=res['n'], players=res['players'], balls_per_half=nh, K_balls=K, K_lo=Klo, K_hi=Khi,
                              r_fullseason_sb=2 * res['r'] / (1 + res['r'])))
S = pd.DataFrame(srows)
S.to_csv(os.path.join(OUT, 'split_half.csv'), index=False)

# --- summary at the main threshold (120 balls in each season / 60 in each half)
MAIN = 120
summ = []
for m in METRICS:
    for scope in list(SCOPES) + ['IPL', 'BLAST', 'BBL', 'PSL', 'CPL', 'SMAT', 'T20I', 'HUNDRED', 'WBBL', 'T20IW']:
        y = Y[(Y.metric == m) & (Y.scope == scope) & (Y.min_balls == MAIN)]
        s = S[(S.metric == m) & (S.scope == scope) & (S.min_balls_season == MAIN)]
        if y.empty or s.empty:
            continue
        y = y.iloc[0]; s = s.iloc[0]
        K = s.K_balls
        relN = y.mean_balls_N / (y.mean_balls_N + K); relN1 = y.mean_balls_N1 / (y.mean_balls_N1 + K)
        rel = np.sqrt(relN * relN1)
        summ.append(dict(metric=m, label=y.label, scope=scope, r_yoy=y.r, yoy_lo=y.lo, yoy_hi=y.hi, pairs=y.pairs, players=y.players,
                         share_explained_pct=100 * y.r ** 2, edge_kept=y.slope, edge_kept_lo=y.slope_lo, edge_kept_hi=y.slope_hi,
                         r_half=s.r_half, half_lo=s.lo, half_hi=s.hi, balls_to_half_signal=K, K_lo=s.K_lo, K_hi=s.K_hi,
                         typical_season_balls=y.mean_balls_N, reliability_typical_season=rel,
                         talent_carryover=y.r / rel if rel > 0 else np.nan))
SU = pd.DataFrame(summ)
SU.to_csv(os.path.join(OUT, 'signal_summary_main.csv'), index=False)
pd.set_option('display.width', 250)
print(SU[SU.scope.isin(['Men: all franchise/domestic leagues', 'IPL', 'Women: all franchise/domestic leagues'])][
    ['metric', 'scope', 'r_yoy', 'yoy_lo', 'yoy_hi', 'pairs', 'edge_kept', 'r_half', 'balls_to_half_signal', 'typical_season_balls',
     'reliability_typical_season', 'talent_carryover']].round(3).to_string())

# --- edge kept by quintile of season N (men's leagues, IPL, women's leagues), main threshold
er = []
for scope in ['Men: all franchise/domestic leagues', 'IPL', 'Women: all franchise/domestic leagues']:
    for m in ['sr', 'econ', 'batval', 'bowlval', 'bndpct', 'wktrate', 'avg', 'dotpct']:
        v0, r0, b0 = metric_values(P, m, L)
        Pn = P[[c for c in P.columns if c.endswith('_n')]].copy(); Pn.columns = [c[:-2] for c in Pn.columns]
        v1, r1, b1 = metric_values(Pn.set_index(P.index), m, L)
        k = scope_mask(P, scope) & (b0 >= MAIN) & (b1 >= MAIN) & r0.notna() & r1.notna()
        q = pd.qcut(r0[k], 5, labels=[1, 2, 3, 4, 5])
        g = pd.DataFrame({'q': q, 'r0': r0[k], 'r1': r1[k], 'pid': P.pid[k]})
        for qq, gg in g.groupby('q', observed=True):
            # bootstrap the N+1 mean by player
            rng = np.random.default_rng(3)
            pids = gg.pid.values; u, inv = np.unique(pids, return_inverse=True)
            s1 = np.bincount(inv, weights=gg.r1.values); s0 = np.bincount(inv, weights=gg.r0.values); c = np.bincount(inv)
            W = rng.multinomial(len(u), np.full(len(u), 1 / len(u)), size=1000)
            m1 = (W @ s1) / (W @ c); kept = m1 / ((W @ s0) / (W @ c))
            er.append(dict(scope=scope, metric=m, quintile=int(qq), n=len(gg), mean_N=gg.r0.mean(), mean_N1=gg.r1.mean(),
                           N1_lo=np.percentile(m1, 2.5), N1_hi=np.percentile(m1, 97.5),
                           kept_pct=100 * gg.r1.mean() / gg.r0.mean(), kept_lo=100 * np.percentile(kept, 2.5), kept_hi=100 * np.percentile(kept, 97.5)))
E = pd.DataFrame(er)
E.to_csv(os.path.join(OUT, 'edge_kept_quintiles.csv'), index=False)
print(E[E.metric.isin(['sr', 'econ'])].round(2).to_string())

# --- who comes back? (survivorship) men's leagues, batting >=120 balls in N
sv = []
for scope in ['Men: all franchise/domestic leagues', 'IPL']:
    for m in ['sr', 'econ']:
        lab, side, bc, n, d, sc = METRICS[m]
        cur = PS[scope_mask(PS, scope)].copy()
        v, r, b = metric_values(cur, m, L)
        cur['rel'] = r; cur['b'] = b
        cur = cur[(cur.b >= MAIN) & cur.rel.notna()]
        nextexists = seasons.copy(); nextexists['sno'] = nextexists.sno - 1
        cur = cur.merge(nextexists[['comp', 'sno']].assign(has_next=1), on=['comp', 'sno'], how='inner')
        nx2 = PS[['pid', 'comp', 'sno', bc]].copy(); nx2['sno'] -= 1
        cur = cur.merge(nx2.rename(columns={bc: 'b_next'}), on=['pid', 'comp', 'sno'], how='left')
        cur['b_next'] = cur.b_next.fillna(0)
        cur['q'] = pd.qcut(cur.rel if side == 'bat' else -cur.rel, 5, labels=[1, 2, 3, 4, 5])
        for qq, gg in cur.groupby('q', observed=True):
            sv.append(dict(scope=scope, metric=m, quintile_best5=int(qq), n=len(gg), back_any=(gg.b_next > 0).mean(),
                           back_main=(gg.b_next >= MAIN).mean()))
SV = pd.DataFrame(sv)
SV.to_csv(os.path.join(OUT, 'survivorship.csv'), index=False)
print(SV.round(3).to_string())
