"""R02 independent re-computation of the headline numbers.

usage: python3 -I verify_independent.py <RAW_JSON_DIR> <REPORT_DATA_DIR>

A second code path written separately from steps 01-06: standard library only (json, math, collections),
no pandas/numpy, its own JSON reading, its own exclusion logic, its own season assignment, its own
aggregation and its own correlation arithmetic. It reads nothing produced by the main pipeline except, at the
end, the main pipeline's CSVs, to print both numbers side by side.
"""
import json, os, sys, glob, math, csv
from collections import defaultdict
from datetime import date as Date

RAW, DATA = sys.argv[1], sys.argv[2]
LEAGUE_FOLDERS = {'ipl': 'IPL', 'bbl': 'BBL', 'psl': 'PSL', 'cpl': 'CPL', 'sat': 'SA20', 'ilt': 'ILT20', 'ntb': 'BLAST', 'bpl': 'BPL',
                  'lpl': 'LPL', 'mlc': 'MLC', 'msl': 'MSL', 'npl': 'NPL', 'sma': 'SMAT', 'ssm_male': 'SSM', 'ctc': 'CSAT20', 'ipt': 'IRE-IPT',
                  'mct': 'SL-MCT', 'etpl': 'ETPL'}
ALL_FOLDERS = ['ipl', 'bbl', 'psl', 'cpl', 'sat', 'ilt', 'ntb', 'bpl', 'lpl', 'mlc', 'msl', 'npl', 'sma', 'ssm_male', 'ctc', 'ipt', 'mct', 'etpl',
               'hnd_male', 't20s_male', 'wpl', 'wbb', 'cec', 'wcl', 'wtb', 'wsl', 'blz', 'frb', 'wtc', 'ssm_female', 'hnd_female', 't20s_female']
FULL = {'Afghanistan', 'Australia', 'Bangladesh', 'England', 'India', 'Ireland', 'New Zealand', 'Pakistan', 'South Africa', 'Sri Lanka', 'West Indies', 'Zimbabwe'}
CREDIT = {'caught', 'bowled', 'lbw', 'stumped', 'caught and bowled', 'hit wicket'}
NOTOUT = {'retired hurt', 'retired not out'}


def pearson(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs); syy = sum((b - my) ** 2 for b in ys)
    return sxy / math.sqrt(sxx * syy)


def d(s):
    y, m, dd = s.split('-'); return Date(int(y), int(m), int(dd))


# ---------- pass 1: read every file, keep only clean matches
kept_matches = 0; kept_balls = 0
matches = []  # (comp, mid, date, is_t20i, per-player stats dict)
for folder in ALL_FOLDERS:
    for fp in sorted(glob.glob(os.path.join(RAW, folder, '*.json'))):
        mid = os.path.basename(fp)[:-5]
        with open(fp, encoding='utf-8') as fh:
            js = json.load(fh)
        inf = js['info']; oc = inf.get('outcome', {})
        inns = [i for i in js.get('innings', []) if not i.get('super_over')]
        if not inns or oc.get('result') == 'no result' or oc.get('method') in ('D/L', 'VJD', 'Awarded'):
            continue
        bpo = int(inf.get('balls_per_over', 6))
        ov = inf.get('overs', 20)
        if ov != 20 and not (ov == 50 and max(len(i.get('overs', [])) for i in inns) <= 20):
            continue
        if any((i.get('target') or {}).get('overs') is not None and float(i['target']['overs']) < 20 for i in inns):
            continue
        if folder.startswith('t20s'):
            okset = FULL if folder == 't20s_male' else FULL | {t + ' Women' for t in FULL}
            if not all(t in okset for t in inf.get('teams', [])):
                continue
        if len(inns) < 2:
            continue
        inns = inns[:2]
        # first innings must reach its full allocation unless bowled out
        legal1 = 0; outs1 = 0
        for o in inns[0]['overs']:
            for dl in o['deliveries']:
                ex = dl.get('extras') or {}
                if 'wides' not in ex and 'noballs' not in ex: legal1 += 1
                outs1 += sum(1 for w in dl.get('wickets', []) if w.get('kind') not in NOTOUT)
        if legal1 < (100 if bpo == 5 else 120) and outs1 < 10:
            continue
        reg = inf.get('registry', {}).get('people', {})
        teams = inf.get('teams', [])
        st = defaultdict(lambda: defaultdict(float))
        nb = 0
        for inn in inns:
            for o in inn['overs']:
                for dl in o['deliveries']:
                    nb += 1
                    bat = reg.get(dl['batter'], dl['batter']); bow = reg.get(dl['bowler'], dl['bowler']); ns = reg.get(dl['non_striker'], dl['non_striker'])
                    ex = dl.get('extras') or {}
                    r = dl['runs']
                    wide = 'wides' in ex; noball = 'noballs' in ex
                    if not wide:
                        st[bat]['bf'] += 1; st[bat]['runs'] += r['batter']
                    if not wide and not noball:
                        st[bow]['lb'] += 1
                    st[bow]['rc'] += r['total'] - ex.get('byes', 0) - ex.get('legbyes', 0)
                    ws = [w for w in dl.get('wickets', []) if w.get('kind') not in NOTOUT]
                    if ws:
                        po = reg.get(ws[0]['player_out'], ws[0]['player_out'])
                        if po == bat: st[bat]['outs'] += 1
                        elif po == ns: st[ns]['outs'] += 1
                        if any(w.get('kind') in CREDIT for w in ws): st[bow]['wk'] += 1
        kept_matches += 1; kept_balls += nb
        comp = LEAGUE_FOLDERS.get(folder, folder)
        matches.append((comp, mid, inf['dates'][0], folder.startswith('t20s'), folder in LEAGUE_FOLDERS, {k: dict(v) for k, v in st.items()}))
print('coverage: kept matches', kept_matches, 'balls', kept_balls)

# ---------- seasons: >90-day gap starts a new season; three suspended seasons rejoined; T20I = calendar year
bycomp = defaultdict(list)
for i, mt in enumerate(matches):
    bycomp[mt[0]].append(i)
season_of = {}
for comp, idx in bycomp.items():
    idx.sort(key=lambda i: (matches[i][2], matches[i][1]))
    if matches[idx[0]][3]:
        for i in idx: season_of[i] = (comp, matches[i][2][:4])
        continue
    clusters = []; prev = None
    for i in idx:
        dt = d(matches[i][2])
        if prev is None or (dt - prev).days > 90: clusters.append([])
        clusters[-1].append(i); prev = dt
    merged = []
    for c in clusters:
        first = matches[c[0]][2]
        rejoin = (comp == 'IPL' and first.startswith('2021-09')) or (comp == 'PSL' and (first.startswith('2020-11') or first.startswith('2021-06')))
        if rejoin: merged[-1].extend(c)
        else: merged.append(list(c))
    for c in merged:
        y0 = matches[c[0]][2][:4]; y1 = matches[c[-1]][2][:4]
        lab = y0 if y0 == y1 else y0 + '/' + y1[2:]
        for i in c: season_of[i] = (comp, lab)
order = {}
for comp in bycomp:
    labs = sorted({season_of[i][1] for i in bycomp[comp]}, key=lambda l: min(matches[i][2] for i in bycomp[comp] if season_of[i][1] == l))
    for k, l in enumerate(labs): order[(comp, l)] = k + 1
start = {}
for i in season_of:
    key = season_of[i]; start[key] = min(start.get(key, '9999'), matches[i][2])

# ---------- player-season and league-season totals
PSs = defaultdict(lambda: defaultdict(float)); LS = defaultdict(lambda: defaultdict(float))
for i, mt in enumerate(matches):
    key = season_of[i]
    for p, s in mt[5].items():
        for k, v in s.items():
            PSs[(p,) + key][k] += v; LS[key][k] += v


def rel(stats, key, metric):
    L = LS[key]
    if metric == 'sr':
        if stats.get('bf', 0) == 0: return None
        return 100 * stats.get('runs', 0) / stats['bf'] - 100 * L['runs'] / L['bf']
    if metric == 'econ':
        if stats.get('lb', 0) == 0: return None
        return 6 * stats.get('rc', 0) / stats['lb'] - 6 * L['rc'] / L['lb']
    if metric == 'wkt':
        if stats.get('lb', 0) == 0: return None
        return 24 * stats.get('wk', 0) / stats['lb'] - 24 * L['wk'] / L['lb']
    if metric == 'avg':
        if stats.get('outs', 0) == 0: return None
        return stats.get('runs', 0) / stats['outs'] - L['runs'] / L['outs']


def balls(stats, metric):
    return stats.get('bf', 0) if metric in ('sr', 'avg') else stats.get('lb', 0)


league_comps = set(LEAGUE_FOLDERS.values())
results = {}
for metric in ['sr', 'econ', 'wkt', 'avg']:
    for scope in ['men_leagues', 'IPL']:
        xs, ys, top = [], [], []
        for (p, comp, lab), s in PSs.items():
            if scope == 'IPL' and comp != 'IPL': continue
            if comp not in league_comps: continue
            k = order[(comp, lab)]
            nxt = [l for (c, l), kk in order.items() if c == comp and kk == k + 1]
            if not nxt: continue
            s2 = PSs.get((p, comp, nxt[0]))
            if not s2: continue
            if int(start[(comp, nxt[0])][:4]) - int(start[(comp, lab)][:4]) > 2: continue
            if balls(s, metric) < 120 or balls(s2, metric) < 120: continue
            a = rel(s, (comp, lab), metric); b = rel(s2, (comp, nxt[0]), metric)
            if a is None or b is None: continue
            xs.append(a); ys.append(b)
        results[(metric, scope)] = (pearson(xs, ys), len(xs))
        if metric == 'sr' and scope == 'men_leagues':
            pairs = sorted(zip(xs, ys))
            q = len(pairs) // 5
            topq = pairs[-q:]
            results['edge_top_quintile_sr'] = (sum(a for a, _ in topq) / len(topq), sum(b for _, b in topq) / len(topq), len(topq))

# ---------- split halves (alternate matches) for the men's leagues
for metric in ['sr', 'econ', 'wkt', 'avg']:
    per = defaultdict(list)
    for i, mt in enumerate(matches):
        comp, lab = season_of[i]
        if comp not in league_comps: continue
        for p, s in mt[5].items():
            if balls(s, metric) > 0: per[(p, comp, lab)].append((mt[2], mt[1], s))
    xs, ys, hs = [], [], []
    for key, lst in per.items():
        lst.sort(key=lambda t: (t[0], t[1]))
        h = [defaultdict(float), defaultdict(float)]
        for j, (_, _, s) in enumerate(lst):
            for k, v in s.items(): h[(j + 1) % 2][k] += v
        if balls(h[0], metric) < 60 or balls(h[1], metric) < 60: continue
        a = rel(h[1], key[1:], metric); b = rel(h[0], key[1:], metric)
        if a is None or b is None: continue
        xs.append(a); ys.append(b)
        n1, n0 = balls(h[1], metric), balls(h[0], metric); hs.append(2 * n1 * n0 / (n1 + n0))
    r = pearson(xs, ys); nh = sum(hs) / len(hs)
    results[('half', metric)] = (r, len(xs), nh * (1 - r) / r)

# ---------- forecast check (strike rate, men's leagues): last season as recorded vs pulled-toward-average
def fc_rows():
    out = []
    for (p, comp, lab), s in PSs.items():
        if comp not in league_comps or s.get('bf', 0) < 120: continue
        k = order[(comp, lab)]
        if k < 2: continue
        hist = []
        for kk in range(1, 13):
            l2 = [l for (c, l), o in order.items() if c == comp and o == k - kk]
            if not l2: break
            s2 = PSs.get((p, comp, l2[0]))
            if s2 and s2.get('bf', 0) > 0:
                L = LS[(comp, l2[0])]
                hist.append((kk, s2['runs'] - L['runs'] / L['bf'] * s2['bf'] if 'runs' in s2 else -L['runs'] / L['bf'] * s2['bf'], s2['bf'], l2[0]))
        last = [h for h in hist if h[0] == 1]
        if not last or last[0][2] < 60: continue
        if (d(start[(comp, lab)]) - d(start[(comp, last[0][3])])).days > 800: continue
        out.append((int(start[(comp, lab)][:4]), rel(s, (comp, lab), 'sr'), hist))
    return out


rows = fc_rows()
def f5(hist, lam, K):
    wrn = sum(lam ** (h[0] - 1) * h[1] for h in hist); wb = sum(lam ** (h[0] - 1) * h[2] for h in hist)
    return 100 * wrn / wb * wb / (wb + K) if wb > 0 else 0.0
train = [r for r in rows if r[0] <= 2019]; test = [r for r in rows if r[0] >= 2020]
LAMS = [0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0]; KS = [0, 25, 50, 100, 150, 200, 300, 400, 600, 800, 1200, 1600, 2400, 3200, 5000, 8000]
def mse(rs, fn): return sum((r[1] - fn(r[2])) ** 2 for r in rs) / len(rs)
best = min(((l, K) for l in LAMS for K in KS), key=lambda p: mse(train, lambda h: f5(h, p[0], p[1])))
m0 = mse(test, lambda h: 0.0)
m1 = mse(test, lambda h: f5([x for x in h if x[0] == 1], 1.0, 0))
m5 = mse(test, lambda h: f5(h, best[0], best[1]))
results['forecast_sr'] = (len(test), 100 * (1 - m1 / m0), 100 * (1 - m5 / m0), best)

# ---------- SMAT -> IPL strike-rate gap
ipl_t = [(p, lab, s) for (p, comp, lab), s in PSs.items() if comp == 'IPL' and s.get('bf', 0) >= 120]
smat_by_p = defaultdict(list)
for i, mt in enumerate(matches):
    if mt[0] == 'SMAT':
        for p, s in mt[5].items():
            if s.get('bf', 0) > 0: smat_by_p[p].append((mt[2], season_of[i], s))
gaps = []
for p, lab, s in ipl_t:
    st0 = d(start[('IPL', lab)])
    rn = 0.0; bf = 0
    for dt, key, s2 in smat_by_p.get(p, []):
        dd = (st0 - d(dt)).days
        if 0 < dd <= 365:
            L = LS[key]; rn += s2.get('runs', 0) - L['runs'] / L['bf'] * s2['bf']; bf += s2['bf']
    if bf >= 60:
        gaps.append(rel(s, ('IPL', lab), 'sr') - 100 * rn / bf)
results['smat_gap'] = (sum(gaps) / len(gaps), len(gaps))

# ---------- print side by side with the main pipeline
def main_val(fn, filt, col):
    with open(os.path.join(DATA, fn)) as f:
        for row in csv.DictReader(f):
            if all(row[k] == v for k, v in filt.items()): return float(row[col])
    return float('nan')

MS = {'sr': 'sr', 'econ': 'econ', 'wkt': 'wktrate', 'avg': 'avg'}
print('\n%-58s %12s %12s' % ('headline', 'independent', 'main'))
with open(os.path.join(DATA, 'verification_independent.csv'), 'w') as out:
    out.write('headline,independent,main\n')
    def show(name, a, b):
        print('%-58s %12.4f %12.4f' % (name, a, b)); out.write('"%s",%.6f,%.6f\n' % (name, a, b))
    show('kept matches', kept_matches, sum(1 for _ in open(os.path.join(DATA, 'seasons.csv'))) * 0 + main_val('coverage_by_competition.csv', {}, 'matches') * 0 + sum(float(r['matches']) for r in csv.DictReader(open(os.path.join(DATA, 'coverage_by_competition.csv')))))
    show('kept balls (all deliveries)', kept_balls, sum(float(r['balls']) for r in csv.DictReader(open(os.path.join(DATA, 'coverage_by_competition.csv')))))
    for m in MS:
        for scope, sc in [('men_leagues', 'Men: all franchise/domestic leagues'), ('IPL', 'IPL')]:
            r, n = results[(m, scope)]
            show('season-to-season r, %s, %s, >=120 balls' % (m, scope), r, main_val('yoy_repeatability.csv', {'metric': MS[m], 'scope': sc, 'min_balls': '120'}, 'r'))
            show('  pairs', n, main_val('yoy_repeatability.csv', {'metric': MS[m], 'scope': sc, 'min_balls': '120'}, 'pairs'))
        r, n, K = results[('half', m)]
        show('split-half r, %s, men leagues, >=60 balls per half' % m, r, main_val('split_half.csv', {'metric': MS[m], 'scope': 'Men: all franchise/domestic leagues', 'min_balls_season': '120'}, 'r_half'))
        show('  balls to half signal', K, main_val('split_half.csv', {'metric': MS[m], 'scope': 'Men: all franchise/domestic leagues', 'min_balls_season': '120'}, 'K_balls'))
    a, b, n = results['edge_top_quintile_sr']
    show('top-fifth SR, season N (vs league)', a, main_val('edge_kept_quintiles.csv', {'scope': 'Men: all franchise/domestic leagues', 'metric': 'sr', 'quintile': '5'}, 'mean_N'))
    show('top-fifth SR, season N+1 (vs league)', b, main_val('edge_kept_quintiles.csv', {'scope': 'Men: all franchise/domestic leagues', 'metric': 'sr', 'quintile': '5'}, 'mean_N1'))
    n, e1, e5, bp = results['forecast_sr']
    show('forecast SR test n', n, main_val('forecast_contest.csv', {'metric': 'sr', 'scope': 'Men: all franchise/domestic leagues', 'split': 'train<=2019,test>=2020', 'forecast': 'F1'}, 'n_test'))
    show('forecast SR: last season as recorded, %% explained', e1, main_val('forecast_contest.csv', {'metric': 'sr', 'scope': 'Men: all franchise/domestic leagues', 'split': 'train<=2019,test>=2020', 'forecast': 'F1'}, 'explained_pct'))
    show('forecast SR: weighted + pulled to average, %% explained', e5, main_val('forecast_contest.csv', {'metric': 'sr', 'scope': 'Men: all franchise/domestic leagues', 'split': 'train<=2019,test>=2020', 'forecast': 'F5'}, 'explained_pct'))
    print('   (independently tuned lam, K = %s)' % (bp,))
    g, n = results['smat_gap']
    show('SMAT->IPL strike-rate gap', g, main_val('cross_league.csv', {'metric': 'sr', 'target': 'IPL', 'source': 'SMAT'}, 'gap'))
    show('  n', n, main_val('cross_league.csv', {'metric': 'sr', 'target': 'IPL', 'source': 'SMAT'}, 'n'))
