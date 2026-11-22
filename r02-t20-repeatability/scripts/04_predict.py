"""R02 step 4 - what predicts next season best? Out-of-sample forecast contest.

usage: python3 -I 04_predict.py <WORK_DIR> <REPORT_DATA_DIR>

Target: a player's season in a competition with >= 120 balls (faced for batting metrics, bowled for bowling),
where the same player also had >= 60 balls in that competition's previous season.
All values are relative to the competition-season average, so "0" is "an average player in that league that year".

Forecasts (all built only from information available before the target season starts):
  F0 league average (predict 0)
  F1 last season, as recorded
  F2 career to date in this competition (all previous seasons, ball-weighted)
  F3 recency-weighted career in this competition (season k back gets weight lam^k), lam tuned on training seasons
  F4 last season pulled toward average: last * n/(n+K), K tuned on training seasons
  F5 recency-weighted AND pulled toward average (F3 then shrink with effective balls), lam and K tuned on training
  F6 F5 using every men's/women's T20 competition in the 3 years before the target season (cross-league history),
     each match measured against its own competition-season average, tuned on training
Train: target seasons starting 2019 or earlier. Test: target seasons starting 2020 or later. (Also run reversed.)
Score: root-mean-square error on test targets, and the share of next-season spread explained (1 - MSE/MSE(F0)).
Uncertainty: 1,000 resamples of players in the test set; differences between forecasts are paired.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from r02lib import METRICS, KEY, load_pm, league_means

WORK, OUT = sys.argv[1], sys.argv[2]
PM = load_pm(WORK)
L = league_means(PM)
PS = pd.read_parquet(os.path.join(WORK, 'player_season.parquet'))
seasons = pd.read_csv(os.path.join(OUT, 'seasons.csv'), parse_dates=['start', 'end'])
sstart = seasons.set_index('sid').start
PS['start'] = PS.sid.map(sstart)
PM_cross = PM.copy()

TARGET_MIN, LAST_MIN = 120, 60
METS = ['sr', 'bndpct', 'dotpct', 'avg', 'batval', 'econ', 'wktrate', 'bowlval', 'sr_adj', 'econ_adj']
SCOPES = {'Men: all franchise/domestic leagues': lambda d: (d.gender == 'male') & (d.group == 'league'),
          'IPL': lambda d: d.comp == 'IPL',
          'Women: all franchise/domestic leagues': lambda d: (d.gender == 'female') & (d.group == 'league')}
LAMS = [0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0]
KS = [0, 25, 50, 100, 150, 200, 300, 400, 600, 800, 1200, 1600, 2400, 3200, 5000, 8000]


def rel_num(df, m):
    lab, side, bc, n, d, sc = METRICS[m]
    lr = (L[n] / L[d].where(L[d] > 0))
    return df[n] - df.sid.map(lr) * df[d], df[d], df[bc], sc


def build(m):
    lab, side, bc, n, d, sc = METRICS[m]
    rn, den, balls, sc = rel_num(PS, m)
    T = PS[KEY + ['start']].copy(); T['rn'] = rn; T['den'] = den; T['balls'] = balls
    T['y'] = sc * T.rn / T.den.where(T.den > 0)
    tgt = T[(T.balls >= TARGET_MIN) & T.y.notna() & (T.sno >= 2)].copy()
    # within-competition history: up to 12 seasons back
    hist = []
    for lag in range(1, 13):
        h = T[['pid', 'comp', 'sno', 'rn', 'den', 'balls', 'start']].copy(); h['sno'] = h.sno + lag
        h = h.rename(columns={'rn': 'hrn', 'den': 'hden', 'balls': 'hb', 'start': 'hstart'}); h['lag'] = lag
        hist.append(tgt[['pid', 'comp', 'sno']].merge(h, on=['pid', 'comp', 'sno']))
    H = pd.concat(hist)
    last = H[H.lag == 1].set_index(['pid', 'comp', 'sno'])
    tgt = tgt.set_index(['pid', 'comp', 'sno'])
    tgt['last_b'] = last.hb.reindex(tgt.index)
    tgt['last_gap'] = (tgt.start - last.hstart.reindex(tgt.index)).dt.days
    tgt = tgt[(tgt.last_b >= LAST_MIN) & (tgt.last_gap <= 800)]
    H = H.set_index(['pid', 'comp', 'sno']).loc[lambda x: x.index.isin(tgt.index)].reset_index()
    # cross-competition history from matches in the 3 years before the target season start (same gender)
    rnm, denm, bm, _ = rel_num(PM_cross, m)
    X = PM_cross[['pid', 'gender', 'date']].copy(); X['rn'] = rnm; X['den'] = denm; X['b'] = bm
    X = X[X.b > 0]
    tg = tgt.reset_index()[['pid', 'comp', 'sno', 'start', 'gender']]
    XX = tg.merge(X, on=['pid', 'gender'])
    XX = XX[(XX.date < XX.start) & (XX.date >= XX.start - pd.Timedelta(days=3 * 365))]
    XX['yrs'] = (XX.start - XX.date).dt.days / 365.25
    return tgt.reset_index(), H, XX, sc


def preds(tgt, H, XX, sc, lam, K, lamx=None, Kx=None):
    idx = ['pid', 'comp', 'sno']
    w = lam ** (H.lag - 1)
    g = pd.DataFrame({'pid': H.pid, 'comp': H.comp, 'sno': H.sno, 'wrn': w * H.hrn, 'wden': w * H.hden, 'wb': w * H.hb,
                      'rn': H.hrn, 'den': H.hden, 'b': H.hb, 'l1rn': np.where(H.lag == 1, H.hrn, 0), 'l1den': np.where(H.lag == 1, H.hden, 0),
                      'l1b': np.where(H.lag == 1, H.hb, 0)}).groupby(idx).sum()
    t = tgt.set_index(idx)
    g = g.reindex(t.index)
    out = pd.DataFrame(index=t.index)
    out['y'] = t.y
    out['F0'] = 0.0
    out['F1'] = sc * g.l1rn / g.l1den.where(g.l1den > 0)
    out['F2'] = sc * g.rn / g.den.where(g.den > 0)
    out['F3'] = sc * g.wrn / g.wden.where(g.wden > 0)
    out['F4'] = out.F1 * g.l1b / (g.l1b + K)
    out['F5'] = out.F3 * g.wb / (g.wb + K)
    if lamx is not None:
        wx = lamx ** XX.yrs
        gx = pd.DataFrame({'pid': XX.pid, 'comp': XX.comp, 'sno': XX.sno, 'wrn': wx * XX.rn, 'wden': wx * XX.den, 'wb': wx * XX.b}).groupby(idx).sum().reindex(t.index)
        f6 = sc * gx.wrn / gx.wden.where(gx.wden > 0)
        out['F6'] = (f6 * gx.wb / (gx.wb + Kx)).fillna(0.0)
    for c in ['F1', 'F2', 'F3', 'F4', 'F5']:
        out[c] = out[c].fillna(0.0)
    out['season'] = t.season; out['start'] = t.start
    return out.reset_index()


def mse(o, c):
    return float(((o.y - o[c]) ** 2).mean())


rows, pick, store = [], [], []
for m in METS:
    tgt, H, XX, sc = build(m)
    for scope, f in SCOPES.items():
        T0 = tgt[f(tgt)]
        if len(T0) < 80:
            continue
        for split in ['train<=2019,test>=2020', 'train>=2020,test<=2019']:
            if split.startswith('train<=2019'):
                tr, te = T0[T0.season <= 2019], T0[T0.season >= 2020]
            else:
                tr, te = T0[T0.season >= 2020], T0[T0.season <= 2019]
            if len(tr) < 40 or len(te) < 40:
                continue
            ktr = tr.set_index(['pid', 'comp', 'sno']).index
            Htr = H[H.set_index(['pid', 'comp', 'sno']).index.isin(ktr)]
            Xtr = XX[XX.set_index(['pid', 'comp', 'sno']).index.isin(ktr)]
            # tune on training only
            best4 = min(KS, key=lambda K: mse(preds(tr, Htr, Xtr, sc, 1.0, K), 'F4'))
            best3 = min(LAMS, key=lambda l: mse(preds(tr, Htr, Xtr, sc, l, 0), 'F3'))
            best5 = min(((l, K) for l in LAMS for K in KS), key=lambda p: mse(preds(tr, Htr, Xtr, sc, p[0], p[1]), 'F5'))
            best6 = min(((l, K) for l in [0.2, 0.35, 0.5, 0.65, 0.8, 1.0] for K in KS),
                        key=lambda p: mse(preds(tr, Htr, Xtr, sc, 1.0, 0, p[0], p[1]), 'F6'))
            kte = te.set_index(['pid', 'comp', 'sno']).index
            Hte = H[H.set_index(['pid', 'comp', 'sno']).index.isin(kte)]
            Xte = XX[XX.set_index(['pid', 'comp', 'sno']).index.isin(kte)]
            o = preds(te, Hte, Xte, sc, best5[0], best5[1], best6[0], best6[1])
            o['F3'] = preds(te, Hte, Xte, sc, best3, 0)['F3'].values
            o['F4'] = preds(te, Hte, Xte, sc, 1.0, best4)['F4'].values
            o['F5'] = preds(te, Hte, Xte, sc, best5[0], best5[1])['F5'].values
            pick.append(dict(metric=m, scope=scope, split=split, K_F4=best4, lam_F3=best3, lam_F5=best5[0], K_F5=best5[1], lam_F6=best6[0], K_F6=best6[1],
                             n_train=len(tr), n_test=len(te)))
            # player-cluster bootstrap of test errors
            fc = ['F0', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6']
            E = np.stack([(o.y - o[c]).values ** 2 for c in fc])
            codes, uniq = pd.factorize(o.pid)
            S = np.stack([np.bincount(codes, weights=e, minlength=len(uniq)) for e in E])
            cnt = np.bincount(codes, minlength=len(uniq)).astype(float)
            rng = np.random.default_rng(11)
            W = rng.multinomial(len(uniq), np.full(len(uniq), 1 / len(uniq)), size=1000).astype(float)
            MB = (W @ S.T) / (W @ cnt)[:, None]  # B x forecasts
            base = MB[:, 0]
            for i, c in enumerate(fc):
                skill = 1 - MB[:, i] / base
                d1 = MB[:, i] - MB[:, 1]  # vs last season
                rows.append(dict(metric=m, label=METRICS[m][0], scope=scope, split=split, forecast=c, n_test=len(o), players=len(uniq),
                                 rmse=np.sqrt(E[i].mean()), rmse_lo=np.sqrt(np.percentile(MB[:, i], 2.5)), rmse_hi=np.sqrt(np.percentile(MB[:, i], 97.5)),
                                 explained_pct=100 * (1 - E[i].mean() / E[0].mean()), explained_lo=100 * np.percentile(skill, 2.5), explained_hi=100 * np.percentile(skill, 97.5),
                                 mse_minus_last=E[i].mean() - E[1].mean(), p_better_than_last=float((d1 < 0).mean()),
                                 corr=np.corrcoef(o.y, o[c])[0, 1] if o[c].std() > 0 else np.nan))
            if split.startswith('train<=2019'):
                o['metric'] = m; o['scope'] = scope; store.append(o)
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUT, 'forecast_contest.csv'), index=False)
pd.DataFrame(pick).to_csv(os.path.join(OUT, 'forecast_tuning.csv'), index=False)
pd.concat(store).to_csv(os.path.join(WORK, 'forecast_test_predictions.csv'), index=False)
pd.set_option('display.width', 250)
print(R[R.split.str.startswith('train<=2019')][['metric', 'scope', 'forecast', 'n_test', 'rmse', 'explained_pct', 'explained_lo', 'explained_hi', 'p_better_than_last', 'corr']].round(3).to_string())
print(pd.DataFrame(pick).to_string())
