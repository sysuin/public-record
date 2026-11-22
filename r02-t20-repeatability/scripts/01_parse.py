"""R02 step 1 - parse Cricsheet JSON into one ball table, one match table, one exclusion log.

usage: python3 -I 01_parse.py <RAW_JSON_DIR> <WORK_DIR>

RAW_JSON_DIR holds one sub-folder per Cricsheet zip (folder name = zip stem, e.g. ipl, bbl, t20s_male).
Untrusted input: we only json.load() it; nothing in it is executed.

Exclusion rules (match level, applied here and logged):
  - no innings at all (abandoned / awarded without play)
  - outcome.result == 'no result'
  - outcome.method in D/L, VJD, Awarded  (interrupted or decided off the field)
  - any innings carrying a reduced target (target.overs < scheduled)  -> reduced-overs match
  - balls_per_over not in (5, 6)
  - T20Is not between two of the 12 ICC full members (associate cricket kept out of the T20I group)
Innings level: super-over innings dropped (match kept).
Metadata repair (logged): 18 T20I files carry info.overs = 50; treated as 20-over matches when no innings
  exceeds 20 overs (they are T20Is by match_type, and the ball data confirms 20-over innings).
"""
import json, os, sys, glob, csv
import pandas as pd

RAW, WORK = sys.argv[1], sys.argv[2]
os.makedirs(WORK, exist_ok=True)

COMP = {  # folder -> (competition code, label, gender, group)
    'ipl': ('IPL', 'Indian Premier League', 'male', 'league'),
    'bbl': ('BBL', 'Big Bash League', 'male', 'league'),
    'psl': ('PSL', 'Pakistan Super League', 'male', 'league'),
    'cpl': ('CPL', 'Caribbean Premier League', 'male', 'league'),
    'sat': ('SA20', 'SA20', 'male', 'league'),
    'ilt': ('ILT20', 'International League T20', 'male', 'league'),
    'ntb': ('BLAST', 'T20 Blast (England)', 'male', 'league'),
    'bpl': ('BPL', 'Bangladesh Premier League', 'male', 'league'),
    'lpl': ('LPL', 'Lanka Premier League', 'male', 'league'),
    'mlc': ('MLC', 'Major League Cricket', 'male', 'league'),
    'msl': ('MSL', 'Mzansi Super League', 'male', 'league'),
    'npl': ('NPL', 'Nepal Premier League', 'male', 'league'),
    'sma': ('SMAT', 'Syed Mushtaq Ali Trophy', 'male', 'league'),
    'ssm_male': ('SSM', 'Super Smash (NZ)', 'male', 'league'),
    'ctc': ('CSAT20', 'CSA T20 Challenge', 'male', 'league'),
    'ipt': ('IRE-IPT', 'Ireland Inter-Provincial T20', 'male', 'league'),
    'mct': ('SL-MCT', 'Sri Lanka Major Clubs T20', 'male', 'league'),
    'etpl': ('ETPL', 'European T20 Premier League', 'male', 'league'),
    'hnd_male': ('HUNDRED', 'The Hundred (men)', 'male', 'hundred'),
    't20s_male': ('T20I', 'T20 internationals (men, full members)', 'male', 't20i'),
    'wpl': ('WPL', "Women's Premier League", 'female', 'league'),
    'wbb': ('WBBL', "Women's Big Bash League", 'female', 'league'),
    'cec': ('CEC', 'Charlotte Edwards Cup', 'female', 'league'),
    'wcl': ('WCPL', "Women's Caribbean Premier League", 'female', 'league'),
    'wtb': ('WBLAST', "Women's T20 Blast", 'female', 'league'),
    'wsl': ('KSL', "Women's Cricket Super League", 'female', 'league'),
    'blz': ('BLAZE', 'T20 Blaze (WI women)', 'female', 'league'),
    'frb': ('FAIRBREAK', 'FairBreak Invitational', 'female', 'league'),
    'wtc': ('WT20C', "Women's T20 Challenge (India)", 'female', 'league'),
    'ssm_female': ('SSMW', 'Super Smash (NZ women)', 'female', 'league'),
    'hnd_female': ('HUNDREDW', 'The Hundred (women)', 'female', 'hundred'),
    't20s_female': ('T20IW', 'T20 internationals (women, full members)', 'female', 't20i'),
}
FULL = {'Afghanistan', 'Australia', 'Bangladesh', 'England', 'India', 'Ireland', 'New Zealand', 'Pakistan',
        'South Africa', 'Sri Lanka', 'West Indies', 'Zimbabwe'}
FULLW = {t + ' Women' for t in FULL} | FULL
BOWLER_KINDS = {'caught', 'bowled', 'lbw', 'stumped', 'caught and bowled', 'hit wicket'}
NOT_DISMISSAL = {'retired hurt', 'retired not out'}

balls, matches, excl, people = [], [], [], {}
nfiles = 0
for folder, (code, label, gender, group) in COMP.items():
    files = sorted(glob.glob(os.path.join(RAW, folder, '*.json')))
    for fp in files:
        nfiles += 1
        mid = os.path.basename(fp)[:-5]
        try:
            d = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            excl.append((code, mid, '', 'match', 'unreadable json')); continue
        info = d.get('info', {})
        date = (info.get('dates') or [''])[0]
        teams = info.get('teams', [])
        oc = info.get('outcome', {})
        bpo = int(info.get('balls_per_over', 6))
        sched = info.get('overs', 20)
        inns = [x for x in d.get('innings', []) if not x.get('super_over')]
        n_super = sum(1 for x in d.get('innings', []) if x.get('super_over'))
        reason = None
        if not inns: reason = 'no innings (abandoned/awarded without play)'
        elif oc.get('result') == 'no result': reason = 'no result'
        elif oc.get('method') in ('D/L', 'VJD', 'Awarded'): reason = 'decided by %s (interrupted/reduced)' % oc.get('method')
        elif bpo not in (5, 6): reason = 'balls_per_over=%s' % bpo
        if reason is None and sched != 20:
            mx = max(len(x.get('overs', [])) for x in inns)
            if sched == 50 and mx <= 20:
                excl.append((code, mid, date, 'repair', 'info.overs=50 on a T20 file; ball data shows <=20 overs; treated as 20'))
                sched = 20
            else:
                reason = 'scheduled overs=%s' % sched
        if reason is None:
            for x in inns:
                t = x.get('target') or {}
                if t.get('overs') is not None and float(t['overs']) < 20:
                    reason = 'reduced-overs innings (target overs %s)' % t['overs']; break
        if reason is None and group == 't20i':
            ok = FULL if gender == 'male' else FULLW
            if not all(t in ok for t in teams): reason = 'T20I involving an associate member'
        reg = info.get('registry', {}).get('people', {})
        for nm, pid in reg.items():
            people.setdefault(pid, nm)
        matches.append(dict(comp=code, match_id=mid, date=date, gender=gender, group=group,
                            season_label=str(info.get('season', '')), team1=teams[0] if teams else '',
                            team2=teams[1] if len(teams) > 1 else '', winner=oc.get('winner', oc.get('result', '')),
                            method=oc.get('method', ''), bpo=bpo, n_super_innings=n_super,
                            event=info.get('event', {}).get('name', ''), excluded=reason or ''))
        if reason:
            excl.append((code, mid, date, 'match', reason)); continue
        if n_super:
            excl.append((code, mid, date, 'innings', '%d super-over innings dropped (match kept)' % n_super))
        for ii, inn in enumerate(inns, start=1):
            if ii > 2:
                excl.append((code, mid, date, 'innings', 'innings %d beyond 2 dropped' % ii)); break
            bat = inn.get('team', '')
            bowl = [t for t in teams if t != bat]; bowl = bowl[0] if bowl else ''
            order = {}
            legal_before = 0; seq = 0; wk_before = 0; runs_before = 0
            for ov in inn.get('overs', []):
                o = int(ov.get('over', 0))
                for dl in ov.get('deliveries', []):
                    seq += 1
                    b = reg.get(dl.get('batter', ''), dl.get('batter', ''))
                    ns = reg.get(dl.get('non_striker', ''), dl.get('non_striker', ''))
                    bw = reg.get(dl.get('bowler', ''), dl.get('bowler', ''))
                    for p in (b, ns):
                        if p not in order: order[p] = len(order) + 1
                    r = dl.get('runs', {}); ex = dl.get('extras', {}) or {}
                    wide = int('wides' in ex); nb = int('noballs' in ex)
                    bye = int(ex.get('byes', 0)); lb = int(ex.get('legbyes', 0))
                    rb = int(r.get('batter', 0)); rt = int(r.get('total', 0))
                    boundary = int(rb in (4, 6) and not r.get('non_boundary', False))
                    wk = dl.get('wickets', []) or []
                    out_id, kind, bcredit, ndis = '', '', 0, 0
                    for w in wk:
                        k = w.get('kind', '')
                        if k in NOT_DISMISSAL: continue
                        ndis += 1
                        if not out_id:
                            out_id = reg.get(w.get('player_out', ''), w.get('player_out', '')); kind = k
                        if k in BOWLER_KINDS: bcredit = 1
                    balls.append((code, mid, date, gender, ii, bat, bowl, o, seq, legal_before, wk_before, runs_before,
                                  b, ns, bw, order[b], rb, rt, wide, nb, bye, lb, boundary, ndis, out_id, kind, bcredit))
                    if not wide and not nb: legal_before += 1
                    wk_before += ndis; runs_before += rt

cols = ['comp', 'match_id', 'date', 'gender', 'innings', 'bat_team', 'bowl_team', 'over', 'seq', 'legal_before',
        'wkts_before', 'runs_before', 'batter', 'non_striker', 'bowler', 'bat_pos', 'runs_batter', 'runs_total',
        'wide', 'noball', 'byes', 'legbyes', 'boundary', 'n_dismissals', 'player_out', 'wicket_kind', 'bowler_wkt']
B = pd.DataFrame(balls, columns=cols)
for c in ['innings', 'over', 'seq', 'legal_before', 'wkts_before', 'runs_before', 'bat_pos', 'runs_batter',
          'runs_total', 'wide', 'noball', 'byes', 'legbyes', 'boundary', 'n_dismissals', 'bowler_wkt']:
    B[c] = pd.to_numeric(B[c], downcast='integer')
B.to_parquet(os.path.join(WORK, 'balls.parquet'), index=False)
pd.DataFrame(matches).to_csv(os.path.join(WORK, 'matches.csv'), index=False)
pd.DataFrame(excl, columns=['comp', 'match_id', 'date', 'level', 'reason']).to_csv(os.path.join(WORK, 'exclusions_parse.csv'), index=False)
pd.DataFrame(sorted(people.items()), columns=['pid', 'name']).to_csv(os.path.join(WORK, 'people.csv'), index=False)
M = pd.DataFrame(matches)
print('files read', nfiles, '| matches kept', (M.excluded == '').sum(), '| excluded', (M.excluded != '').sum(), '| balls', len(B))
