"""R02 step 2 - seasons from dates, run-value model, player-match table.

usage: python3 -I 02_build.py <WORK_DIR> <REPORT_DATA_DIR>

Seasons: within each competition, matches sorted by date; a gap of more than 90 days starts a new season.
Three documented merges for seasons that were suspended and resumed (COVID):
  IPL 2021 (Apr-May + Sep-Oct 2021), PSL 2020 (Feb-Mar + playoffs Nov 2020), PSL 2021 (Feb-Mar + Jun 2021).
T20 internationals have no season: calendar year is used.
Season label = start year of the first match ("2023" or "2023/24" when the season crosses New Year).

Value model (fixes vs PR#1 noted inline):
  - players keyed by Cricsheet registry id, not by name (PR#1 used names; names collide across leagues)
  - baselines per competition-season and match state (over, wickets down), shrunk to the competition-season over mean
  - wicket cost from a run-expectancy surface fitted per format x gender x era on first innings,
    scaled to each competition-season's scoring level
  - dismissals charged to the player who is out (PR#1 ignored non-striker run-outs); retired hurt not a dismissal
"""
import os, sys
import numpy as np, pandas as pd
from scipy.optimize import curve_fit

WORK, OUT = sys.argv[1], sys.argv[2]
B = pd.read_parquet(os.path.join(WORK, 'balls.parquet'))
M = pd.read_csv(os.path.join(WORK, 'matches.csv'), dtype={'season_label': str, 'match_id': str})
B['match_id'] = B.match_id.astype(str)
M['date'] = pd.to_datetime(M.date)
M = M[M.excluded.isna()].copy()
xlog = []

# ---------- unrecorded reductions: first innings ended short of its full allocation without being bowled out
full = M.set_index('match_id').bpo.map({6: 120, 5: 100})
g1 = B[B.innings == 1].groupby('match_id').agg(legal=('legal_before', 'max'), wk=('wkts_before', 'max'),
                                                lastd=('n_dismissals', 'last'))
last = B[B.innings == 1].sort_values(['match_id', 'seq']).groupby('match_id').tail(1).set_index('match_id')
leg = last.legal_before + ((last.wide == 0) & (last.noball == 0)).astype(int)
wk = last.wkts_before + last.n_dismissals
short = leg[(leg < full.reindex(leg.index)) & (wk < 10)].index
# a side can be "all out" with fewer than 10 dismissals when players are absent hurt; allow 9 dismissals
# plus fewer than 11 batters used? keep it simple and conservative: drop all such matches, log them.
two = B.groupby('match_id').innings.max()
one_inn = two[two < 2].index
for mid in short:
    xlog.append((M.set_index('match_id').comp.get(mid, ''), mid, 'match', 'first innings ended short of full overs without 10 wickets (unrecorded reduction or data gap)'))
for mid in one_inn:
    if mid not in short:
        xlog.append((M.set_index('match_id').comp.get(mid, ''), mid, 'match', 'only one innings in ball data'))
drop = set(short) | set(one_inn)
M = M[~M.match_id.isin(drop)]
B = B[B.match_id.isin(set(M.match_id))].copy()

# ---------- seasons
M = M.sort_values(['comp', 'date', 'match_id'])
M['gapnew'] = M.groupby('comp').date.diff().dt.days.fillna(9999) > 90
M['cl'] = M.groupby('comp').gapnew.cumsum()
first = M.groupby(['comp', 'cl']).date.transform('min')
M['cl_start'] = first
MERGE = [('IPL', '2021-09-01', '2021-04-01'), ('PSL', '2020-11-01', '2020-02-01'), ('PSL', '2021-06-01', '2021-02-01')]
for comp, later, earlier in MERGE:
    cs = M[(M.comp == comp)]
    lc = cs[(cs.date >= later)].cl.min(); ec = cs[(cs.date >= earlier)].cl.min()
    M.loc[(M.comp == comp) & (M.cl == lc), 'cl'] = ec
sb = M.groupby(['comp', 'cl']).date.agg(['min', 'max']).reset_index()
sb['season'] = sb['min'].dt.year
sb['season_label'] = np.where(sb['max'].dt.year > sb['min'].dt.year,
                              sb['min'].dt.year.astype(str) + '/' + (sb['max'].dt.year % 100).astype(str).str.zfill(2),
                              sb['min'].dt.year.astype(str))
M = M.drop(columns=['season_label']).merge(sb[['comp', 'cl', 'season', 'season_label']], on=['comp', 'cl'])
t20i = M.group == 't20i'
M.loc[t20i, 'season'] = M.loc[t20i, 'date'].dt.year
M.loc[t20i, 'season_label'] = M.loc[t20i, 'season'].astype(str)
# two seasons can start in the same calendar year (e.g. SA20 Jan 2025 and Dec 2025), so the unique key is the
# full label ("2025" vs "2025/26") and order is an explicit ordinal, never a sliced string.
dup = M.groupby(['comp', 'season_label']).cl.nunique() if 'cl' in M else None
M['sid'] = M.comp + ':' + M.season_label
st = M.groupby(['comp', 'sid']).date.min().reset_index().sort_values(['comp', 'date'])
st['sno'] = st.groupby('comp').cumcount() + 1
M = M.merge(st[['sid', 'sno']], on='sid')
B = B.merge(M[['match_id', 'season', 'sid', 'sno', 'group', 'bpo']], on='match_id')
B['date'] = pd.to_datetime(B.date)

# ---------- per-ball basics
B['faced'] = (B.wide == 0).astype(np.int8)
B['legal'] = ((B.wide == 0) & (B.noball == 0)).astype(np.int8)
B['bowler_runs'] = (B.runs_total - B.byes - B.legbyes).astype(np.int16)
B['striker_out'] = ((B.player_out == B.batter) & (B.n_dismissals > 0)).astype(np.int8)
B['nonstriker_out'] = ((B.player_out == B.non_striker) & (B.n_dismissals > 0)).astype(np.int8)
B['dot_bat'] = ((B.faced == 1) & (B.runs_batter == 0)).astype(np.int8)
B['dot_bowl'] = ((B.legal == 1) & (B.bowler_runs == 0)).astype(np.int8)
B['ov'] = B.over.clip(0, 19)
B['wk'] = B.wkts_before.clip(0, 9)
B['phase'] = np.where(B.ov < 6, 'pp', np.where(B.ov < 15, 'mid', 'death'))
B['fmt'] = np.where(B.bpo == 5, 'H', 'T')
B['era'] = pd.cut(B.season, [0, 2012, 2017, 2021, 9999], labels=['-2012', '2013-17', '2018-21', '2022-']).astype(str)
# thin cells: women's T20 before 2013 merged into 2013-17; The Hundred (2021-) fitted as one era
B.loc[(B.gender == 'female') & (B.fmt == 'T') & (B.era == '-2012'), 'era'] = '2013-17'
B.loc[B.fmt == 'H', 'era'] = '2021-'

# ---------- wicket cost: run-expectancy surface per format x gender x era (first innings)
B = B.sort_values(['match_id', 'innings', 'seq']).reset_index(drop=True)
tot = B.groupby(['match_id', 'innings']).runs_total.transform('sum')
B['runs_rem'] = tot - B.runs_before

def surf(X, C, bb, gg):
    Br, wih = X
    return C * (1 - np.exp(-bb * Br / 120.0)) * (wih / 10.0) ** gg

fits = []
for (fmt, gen, era), e in B[B.innings == 1].groupby(['fmt', 'gender', 'era']):
    # state at the start of each over (first delivery of the over)
    st = e.drop_duplicates(['match_id', 'over'])
    rr = st.groupby(['ov', 'wk']).runs_rem.agg(m='mean', n='count').reset_index()
    rr = rr[rr.n >= 25]
    bpo = 5 if fmt == 'H' else 6
    X = ((20 - rr.ov.values) * bpo * 1.0, 10.0 - rr.wk.values)
    try:
        p, _ = curve_fit(surf, X, rr.m.values, p0=[200, 1.0, 0.6], sigma=1 / np.sqrt(rr.n.values), maxfev=20000)
        pred = surf(X, *p); w = rr.n.values
        r2 = 1 - (w * (rr.m.values - pred) ** 2).sum() / (w * (rr.m.values - np.average(rr.m.values, weights=w)) ** 2).sum()
    except Exception:
        p, r2 = [np.nan] * 3, np.nan
    rpb = e.runs_total.sum() / max(e.legal.sum(), 1)
    fits.append(dict(fmt=fmt, gender=gen, era=era, C=p[0], b=p[1], g=p[2], r2=r2, cells=len(rr), rpb=rpb))
F = pd.DataFrame(fits)
F.to_csv(os.path.join(OUT, 'wicket_cost_fits.csv'), index=False)
print(F.round(3).to_string())
# wicket cost table
rows = []
for f in F.itertuples():
    bpo = 5 if f.fmt == 'H' else 6
    for o in range(20):
        for w in range(10):
            a = surf((np.array([(20 - o) * bpo * 1.0]), np.array([10.0 - w])), f.C, f.b, f.g)[0]
            c = surf((np.array([(20 - o) * bpo * 1.0]), np.array([9.0 - w])), f.C, f.b, f.g)[0] if w < 9 else 0.0
            rows.append((f.fmt, f.gender, f.era, o, w, max(a - c, 0.5), f.rpb))
WC = pd.DataFrame(rows, columns=['fmt', 'gender', 'era', 'ov', 'wk', 'wc_base', 'era_rpb'])
WC[WC.wk.isin([0, 2, 5])].to_csv(os.path.join(OUT, 'wicket_cost_table.csv'), index=False)
B = B.merge(WC, on=['fmt', 'gender', 'era', 'ov', 'wk'], how='left')
srpb = B.groupby('sid').runs_total.transform('sum') / B.groupby('sid').legal.transform('sum')
B['wc'] = B.wc_base * (srpb / B.era_rpb)

# ---------- competition-season state baselines
# Each (competition-season, over, wickets) cell is shrunk toward the same cell in the pooled format x gender x era
# table, rescaled to this competition-season's level for that over. (PR#1 shrank toward the over mean, which
# biases thin high-wicket cells upward and made batting value net negative.)
B['any_out'] = (B.n_dismissals > 0).astype(np.int8)
def grid(col, mask, K=40.0):
    src = B[mask] if mask is not None else B
    g = src.groupby(['sid', 'fmt', 'gender', 'era', 'ov', 'wk'])[col].agg(m='mean', n='count').reset_index()
    pe = src.groupby(['fmt', 'gender', 'era', 'ov', 'wk'])[col].mean().rename('pe').reset_index()
    so = src.groupby(['sid', 'ov'])[col].mean().rename('so').reset_index()
    eo = src.groupby(['fmt', 'gender', 'era', 'ov'])[col].mean().rename('eo').reset_index()
    g = g.merge(pe, on=['fmt', 'gender', 'era', 'ov', 'wk']).merge(so, on=['sid', 'ov']).merge(eo, on=['fmt', 'gender', 'era', 'ov'])
    prior = g.pe * np.where(g.eo > 0, g.so / g.eo, 1.0)
    g[col + '_x'] = (g.m * g.n + prior * K) / (g.n + K)
    return g[['sid', 'ov', 'wk', col + '_x']]

for col, mask in [('runs_batter', B.faced == 1), ('any_out', B.faced == 1), ('bowler_runs', None), ('bowler_wkt', None)]:
    B = B.merge(grid(col, mask), on=['sid', 'ov', 'wk'], how='left')
    B[col + '_x'] = B[col + '_x'].fillna(B.groupby(['sid', 'ov'])[col].transform('mean'))
# batting: the striker carries the baseline risk of a dismissal on every ball faced; whoever is actually out
# (striker or non-striker) pays the wicket cost. Sums to ~0 within each cell.
B['bat_val'] = np.where(B.faced == 1, (B.runs_batter - B.runs_batter_x) + B.any_out_x * B.wc, 0.0) - B.striker_out * B.wc
B['ns_val'] = -B.nonstriker_out * B.wc
B['bowl_val'] = (B.bowler_runs_x - B.bowler_runs) + (B.bowler_wkt - B.bowler_wkt_x) * B.wc
# situation-adjusted components (no wicket pricing): runs above what an average player makes in the same over/wickets state
B['bat_rx'] = np.where(B.faced == 1, B.runs_batter - B.runs_batter_x, 0.0)
B['bowl_rx'] = B.bowler_runs - B.bowler_runs_x          # runs conceded above expected (higher = worse, like economy)
B['bowl_wx'] = B.bowler_wkt - B.bowler_wkt_x            # wickets above expected
chk = B.groupby('sid').agg(bat=('bat_val', 'sum'), ns=('ns_val', 'sum'), bowl=('bowl_val', 'sum'), balls=('legal', 'sum'))
chk['bat_per100'] = 100 * (chk.bat + chk.ns) / chk.balls; chk['bowl_per100'] = 100 * chk.bowl / chk.balls
chk.to_csv(os.path.join(WORK, 'value_sanity_by_season.csv'))
print('value sanity (per 100 balls, should be ~0): bat median %.2f [%.2f,%.2f]  bowl median %.2f [%.2f,%.2f]' % (
    chk.bat_per100.median(), chk.bat_per100.min(), chk.bat_per100.max(), chk.bowl_per100.median(), chk.bowl_per100.min(), chk.bowl_per100.max()))

# ---------- player-match table
B['role'] = pd.cut(B.bat_pos, [0, 2, 4, 7, 99], labels=['open', 'top', 'fin', 'tail']).astype(str)
# all deliveries, not only balls faced: a striker can be stumped or run out off a wide, and that dismissal
# (and its wicket cost) belongs to him. Caught by the independent re-computation (verify_independent.py).
fb = B
key = ['comp', 'sid', 'sno', 'season', 'gender', 'group', 'match_id', 'date']
bat = fb.groupby(key + ['batter']).agg(bf=('faced', 'sum'), runs=('runs_batter', 'sum'), souts=('striker_out', 'sum'),
                                        dots=('dot_bat', 'sum'), bnd=('boundary', 'sum'), bat_val=('bat_val', 'sum'), bat_rx=('bat_rx', 'sum'),
                                        bat_pos=('bat_pos', 'min')).reset_index().rename(columns={'batter': 'pid'})
for ph in ['pp', 'mid', 'death']:
    x = fb[fb.phase == ph].groupby(key + ['batter']).agg(**{'bf_' + ph: ('faced', 'sum'), 'runs_' + ph: ('runs_batter', 'sum'),
                                                          'bval_' + ph: ('bat_val', 'sum')}).reset_index().rename(columns={'batter': 'pid'})
    bat = bat.merge(x, on=key + ['pid'], how='left')
nso = B[B.nonstriker_out == 1].groupby(key + ['non_striker']).agg(nsouts=('nonstriker_out', 'sum'), ns_val=('ns_val', 'sum')).reset_index().rename(columns={'non_striker': 'pid'})
bat = bat.merge(nso, on=key + ['pid'], how='outer')
bowl = B.groupby(key + ['bowler']).agg(lb=('legal', 'sum'), deliv=('legal', 'size'), rc=('bowler_runs', 'sum'), wkts=('bowler_wkt', 'sum'),
                                       bdots=('dot_bowl', 'sum'), bndc=('boundary', 'sum'), bowl_val=('bowl_val', 'sum'), bowl_rx=('bowl_rx', 'sum'), bowl_wx=('bowl_wx', 'sum')).reset_index().rename(columns={'bowler': 'pid'})
for ph in ['pp', 'mid', 'death']:
    x = B[B.phase == ph].groupby(key + ['bowler']).agg(**{'lb_' + ph: ('legal', 'sum'), 'rc_' + ph: ('bowler_runs', 'sum'),
                                                          'wk_' + ph: ('bowler_wkt', 'sum'), 'wval_' + ph: ('bowl_val', 'sum')}).reset_index().rename(columns={'bowler': 'pid'})
    bowl = bowl.merge(x, on=key + ['pid'], how='left')
PM = bat.merge(bowl, on=key + ['pid'], how='outer')
num = [c for c in PM.columns if c not in key + ['pid']]
PM[num] = PM[num].fillna(0)
PM['bat_pos'] = PM.bat_pos.replace(0, np.nan)
PM['outs'] = PM.souts + PM.nsouts
PM['bat_val'] = PM.bat_val + PM.ns_val
PM.to_parquet(os.path.join(WORK, 'player_match.parquet'), index=False)
M.to_csv(os.path.join(WORK, 'matches_kept.csv'), index=False)
pd.DataFrame(xlog, columns=['comp', 'match_id', 'level', 'reason']).to_csv(os.path.join(WORK, 'exclusions_build.csv'), index=False)
B[['comp', 'sid', 'season', 'gender', 'match_id', 'date', 'innings', 'ov', 'wk', 'phase', 'batter', 'bowler', 'faced', 'legal',
   'runs_batter', 'bowler_runs', 'striker_out', 'bowler_wkt', 'boundary', 'bat_val', 'bowl_val', 'wc']].to_parquet(os.path.join(WORK, 'balls_valued.parquet'), index=False)
# coverage table
cov = M.groupby(['gender', 'group', 'comp']).agg(matches=('match_id', 'size'), seasons=('sid', 'nunique'),
                                                first=('season', 'min'), last=('season', 'max')).reset_index()
bc = B.groupby('comp').agg(balls=('legal', 'size'), legal_balls=('legal', 'sum')).reset_index()
cov = cov.merge(bc, on='comp')
cov.to_csv(os.path.join(OUT, 'coverage_by_competition.csv'), index=False)
sb2 = M.groupby(['comp', 'sid', 'sno', 'season', 'season_label']).agg(matches=('match_id', 'size'), start=('date', 'min'), end=('date', 'max')).reset_index()
sb2.to_csv(os.path.join(OUT, 'seasons.csv'), index=False)
print(cov.to_string())
print('kept matches', len(M), 'balls', len(B), 'player-match rows', len(PM), 'extra exclusions', len(drop))

# ---------- combined exclusion log (every dropped match/innings and every metadata repair) -> report data/
xp = pd.read_csv(os.path.join(WORK, 'exclusions_parse.csv'), dtype={'match_id': str})
xb = pd.read_csv(os.path.join(WORK, 'exclusions_build.csv'), dtype={'match_id': str})
xb['date'] = ''
XL = pd.concat([xp, xb[['comp', 'match_id', 'date', 'level', 'reason']]], ignore_index=True)
XL['reason_group'] = XL.reason.str.replace(r'\(target overs [0-9.]+\)', '', regex=True).str.replace(r'^\d+ super-over', 'super-over', regex=True).str.strip()
XL.to_csv(os.path.join(OUT, 'exclusion_log.csv'), index=False)
XS = XL.groupby(['level', 'reason_group']).size().rename('count').reset_index().sort_values(['level', 'count'], ascending=[True, False])
XS.to_csv(os.path.join(OUT, 'exclusion_summary.csv'), index=False)
print(XS.to_string(index=False))
