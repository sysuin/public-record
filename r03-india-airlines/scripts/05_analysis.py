"""All analyses for R03. Writes derived CSVs and data/headline_numbers.json.

Usage: python3 -I 05_analysis.py <data_dir>
Inputs (from 03/03b/04): airline_month_panel.csv, airport_airline_otp.csv, reason_shares.csv,
overall_monthly.csv, schedule_rows_ws2026.csv, aai_domestic_movements_2026.csv
"""
import sys, os, json, itertools
import numpy as np
import pandas as pd
from scipy import stats

D = sys.argv[1]
RNG = np.random.default_rng(20261121)
OUT = {}
P = pd.read_csv(os.path.join(D, "airline_month_panel.csv"), parse_dates=["date"])
A = pd.read_csv(os.path.join(D, "airport_airline_otp.csv"), parse_dates=["date"])
R = pd.read_csv(os.path.join(D, "reason_shares.csv"), parse_dates=["date"])
O = pd.read_csv(os.path.join(D, "overall_monthly.csv"), parse_dates=["date"])
SCH = pd.read_csv(os.path.join(D, "schedule_rows_ws2026.csv"))
AAI = pd.read_csv(os.path.join(D, "aai_domestic_movements_2026.csv"))

# "main" airline-months: at least 1% of domestic passengers that month and an OTP figure
P["main"] = (P.share_pct >= 1.0) & P.otp_pct.notna()
M = P[P.main].copy()
WINDOWS = {
    "all_2018-01_2026-09": ("2018-01-01", "2026-09-01"),
    "pre_covid_2018-2019": ("2018-01-01", "2019-12-01"),
    "post_covid_2022-01_2026-09": ("2022-01-01", "2026-09-01"),
    "4apt_era_2022-2024": ("2022-01-01", "2024-12-01"),
    "6apt_2025": ("2025-01-01", "2025-12-01"),
    "10apt_2026-01_2026-09": ("2026-01-01", "2026-09-01"),
    "last12_2025-10_2026-09": ("2025-10-01", "2026-09-01"),
}
def win(df, w):
    a, b = WINDOWS[w]; return df[(df.date >= a) & (df.date <= b)]

# ======================================================== coverage
cov = {"months_with_report": int(P.date.nunique()),
       "first": str(P.date.min().date()), "last": str(P.date.max().date()),
       "airlines_seen": sorted(P.airline.unique().tolist()),
       "main_airlines_seen": sorted(M.airline.unique().tolist()),
       "airline_months_with_otp": int(P.otp_pct.notna().sum()),
       "airline_months_with_cancel": int(P.cancel_pct.notna().sum()),
       "airline_months_with_complaints": int(P.complaints_per10k.notna().sum())}
OUT["coverage"] = cov

# ======================================================== T1 scope: schedules + AAI
OTP10 = {"Bangalore": "BLR", "Delhi": "DEL", "Hyderabad": "HYD", "Mumbai": "BOM", "Chennai": "MAA", "Kolkata": "CCU",
         "Ahmedabad": "AMD", "Kochi": "COK", "Guwahati": "GAU", "Lucknow": "LKO"}
SETS = {"4": ["BLR", "DEL", "HYD", "BOM"], "6": ["BLR", "DEL", "HYD", "BOM", "MAA", "CCU"],
        "10": ["BLR", "DEL", "HYD", "BOM", "MAA", "CCU", "AMD", "COK", "GAU", "LKO"]}
dep = SCH[SCH.kind == "dep"].copy()
dep["iata"] = dep.station.map(OTP10)
dep["airline_grp"] = dep.airline.replace({"Air India Express": "Air India"})  # DGCA reports 'Air India Group'
tot = dep.groupby("airline_grp").ref_week_ops.sum()
rows = []
for k, s in SETS.items():
    inside = dep[dep.iata.isin(s)].groupby("airline_grp").ref_week_ops.sum()
    for al in tot.index:
        rows.append(dict(airline=al, airport_set=k, weekly_deps=int(tot[al]), deps_at_otp_airports=int(inside.get(al, 0)),
                         share_pct=round(100 * inside.get(al, 0) / tot[al], 1)))
    allin = dep[dep.iata.isin(s)].ref_week_ops.sum()
    rows.append(dict(airline="ALL", airport_set=k, weekly_deps=int(dep.ref_week_ops.sum()), deps_at_otp_airports=int(allin),
                     share_pct=round(100 * allin / dep.ref_week_ops.sum(), 1)))
covdf = pd.DataFrame(rows)
covdf.to_csv(os.path.join(D, "otp_scope_schedule_coverage_ws2026.csv"), index=False)
OUT["scope_schedule"] = {f"{r.airline}|{r.airport_set}": r.share_pct for r in covdf.itertuples()}
OUT["scope_schedule_weekly_deps_total"] = int(dep.ref_week_ops.sum())
# airport mix inside the 10 (schedule weights), for the reconstruction test
mix = dep[dep.iata.notna()].groupby(["airline_grp", "iata"]).ref_week_ops.sum().unstack(fill_value=0)
mixw = mix.div(mix.sum(axis=1), axis=0)
mixw.to_csv(os.path.join(D, "airport_mix_ws2026.csv"))

# AAI: share of domestic aircraft movements at OTP airports (all airlines)
AAIN = {"BENGALURU (BIAL)": "BLR", "DELHI (DIAL)": "DEL", "HYDERABAD (GHIAL)": "HYD", "MUMBAI (MIAL)": "BOM",
        "CHENNAI": "MAA", "KOLKATA": "CCU", "AHMEDABAD": "AMD", "KOCHI": "COK", "GUWAHATI": "GAU", "LUCKNOW": "LKO"}
aai = AAI[~AAI.airport.str.startswith("GRAND")].copy()
aai["iata"] = aai.airport.map(AAIN)
found = sorted(aai.iata.dropna().unique())
arows = []
for mth, g in aai.groupby("month"):
    for k, s in SETS.items():
        for yr in (2025, 2026):
            col = f"dom_mvts_{yr}"
            arows.append(dict(year=yr, month=mth, airport_set=k, share_pct=round(100 * g[g.iata.isin(s)][col].sum() / g[col].sum(), 1),
                              total_dom_mvts=int(g[col].sum())))
aaidf = pd.DataFrame(arows)
aaidf.to_csv(os.path.join(D, "otp_scope_aai_movement_share.csv"), index=False)
OUT["scope_aai"] = {"airports_matched": found,
                    "share_2026_jan_sep_by_set": aaidf[aaidf.year == 2026].groupby("airport_set").share_pct.mean().round(1).to_dict(),
                    "share_2025_jan_sep_by_set": aaidf[aaidf.year == 2025].groupby("airport_set").share_pct.mean().round(1).to_dict()}

# ======================================================== T1b network mix: airport effects
Aa = A[(A.airline != "ALL") & A.otp_pct.notna()].copy()
# airport difficulty within month: airport OTP minus that airline's mean across airports that month (two-way demeaning)
def two_way(g):
    g = g.copy()
    g["air_mean"] = g.groupby("airline").otp_pct.transform("mean")
    g["apt_eff"] = g.otp_pct - g.air_mean
    return g
Aa = Aa.groupby("date", group_keys=False).apply(two_way)
apt_eff = Aa.groupby("airport").apt_eff.agg(["mean", "count"]).sort_values("mean")
apt_eff.to_csv(os.path.join(D, "airport_effect.csv"))
OUT["airport_effect_pts"] = apt_eff["mean"].round(1).to_dict()
# variance share: airline vs airport (4 original airports, main airlines, per month)
m4 = Aa[Aa.airport.isin(SETS["4"])].merge(M[["date", "airline"]], on=["date", "airline"])
vs = []
for d, g in m4.groupby("date"):
    piv = g.pivot_table(index="airline", columns="airport", values="otp_pct")
    piv = piv.dropna()
    if piv.shape[0] < 3 or piv.shape[1] < 4: continue
    grand = piv.values.mean()
    ss_air = piv.shape[1] * ((piv.mean(axis=1) - grand) ** 2).sum()
    ss_apt = piv.shape[0] * ((piv.mean(axis=0) - grand) ** 2).sum()
    ss_tot = ((piv.values - grand) ** 2).sum()
    vs.append(dict(date=d, airline_share=ss_air / ss_tot, airport_share=ss_apt / ss_tot, resid=1 - (ss_air + ss_apt) / ss_tot))
vs = pd.DataFrame(vs)
vs.to_csv(os.path.join(D, "variance_split_airline_vs_airport.csv"), index=False)
OUT["variance_split_median"] = vs[["airline_share", "airport_share", "resid"]].median().round(3).to_dict()
OUT["variance_split_months"] = int(len(vs))

# equal-weight standardised OTP on the original 4 airports; rank change vs published
std_rows = []
for d, g in m4.groupby("date"):
    piv = g.pivot_table(index="airline", columns="airport", values="otp_pct").dropna()
    for al, r in piv.iterrows():
        std_rows.append(dict(date=d, airline=al, otp_equal_weight_4=r.mean()))
STD = pd.DataFrame(std_rows).merge(M[["date", "airline", "otp_pct"]], on=["date", "airline"])
def leader(df, col, higher=True):
    idx = df.groupby("date")[col].idxmax() if higher else df.groupby("date")[col].idxmin()
    return df.loc[idx, ["date", "airline"]].set_index("date").airline
common = STD.groupby("date").filter(lambda g: len(g) >= 3)
l_pub, l_std = leader(common, "otp_pct"), leader(common, "otp_equal_weight_4")
OUT["mix_test_4apt"] = {"months": int(len(l_pub)), "leader_changes_when_equal_weighting": int((l_pub != l_std).sum()),
                        "mean_abs_shift_pts": round(float((common.otp_equal_weight_4 - common.otp_pct).abs().mean()), 2)}
STD.to_csv(os.path.join(D, "otp_equal_weight_4apt.csv"), index=False)

# 2026: reconstruct published OTP from airport OTP using schedule mix; then counterfactual mixes
rec = []
A26 = Aa[(Aa.date >= "2026-01-01")]
for (d, al), g in A26.groupby(["date", "airline"]):
    if al not in mixw.index: continue
    w = mixw.loc[al]
    g = g.set_index("airport").otp_pct
    common_apts = [x for x in w.index if x in g.index and w[x] > 0]
    if not common_apts: continue
    ww = w[common_apts] / w[common_apts].sum()
    own = float((g[common_apts] * ww).sum())
    out = dict(date=d, airline=al, otp_rebuilt_own_mix=own, coverage_of_mix=float(w[common_apts].sum()))
    for other in ["IndiGo", "Air India", "Akasa Air"]:
        wo = mixw.loc[other][common_apts]
        if wo.sum() > 0:
            out[f"otp_with_{other}_mix"] = float((g[common_apts] * wo / wo.sum()).sum())
    rec.append(out)
REC = pd.DataFrame(rec).merge(P[["date", "airline", "otp_pct"]], on=["date", "airline"], how="left")
REC.to_csv(os.path.join(D, "otp_mix_counterfactual_2026.csv"), index=False)
mm = REC[REC.airline.isin(["IndiGo", "Air India", "Akasa Air"])]
OUT["mix_2026"] = {
    "rebuild_mean_abs_err_pts": round(float((mm.otp_rebuilt_own_mix - mm.otp_pct).abs().mean()), 2),
    "akasa_own_vs_indigo_mix_mean_diff": round(float((REC[REC.airline == "Akasa Air"]["otp_with_IndiGo_mix"] - REC[REC.airline == "Akasa Air"].otp_rebuilt_own_mix).mean()), 2),
    "airindia_own_vs_indigo_mix_mean_diff": round(float((REC[REC.airline == "Air India"]["otp_with_IndiGo_mix"] - REC[REC.airline == "Air India"].otp_rebuilt_own_mix).mean()), 2),
    "indigo_own_vs_akasa_mix_mean_diff": round(float((REC[REC.airline == "IndiGo"]["otp_with_Akasa Air_mix"] - REC[REC.airline == "IndiGo"].otp_rebuilt_own_mix).mean()), 2),
}

# ======================================================== T2 rank stability
lead = M.loc[M.groupby("date").otp_pct.idxmax(), ["date", "airline", "otp_pct"]].set_index("date")
second = M.sort_values("otp_pct", ascending=False).groupby("date").nth(1).set_index("date")[["airline", "otp_pct"]]
lead = lead.join(second, rsuffix="_2")
lead["gap"] = lead.otp_pct - lead.otp_pct_2
lead["n_main"] = M.groupby("date").size()
lead.to_csv(os.path.join(D, "otp_leader_by_month.csv"))
st = {}
for w in WINDOWS:
    L = win(lead.reset_index(), w)
    ch = (L.airline != L.airline.shift()).iloc[1:].sum()
    st[w] = dict(months=int(len(L)), leader_counts=L.airline.value_counts().to_dict(), leader_changes=int(ch),
                 change_rate=round(ch / max(len(L) - 1, 1), 2), median_gap_pts=round(float(L.gap.median()), 1),
                 share_months_gap_under_1pt=round(float((L.gap < 1).mean()), 2))
OUT["leader"] = st
# month-to-month noise: typical absolute month-on-month change in an airline's OTP
M = M.sort_values("date")
M["d_otp"] = M.groupby("airline").otp_pct.diff()
noise = M[M.date >= "2022-01-01"].groupby("airline").d_otp.apply(lambda x: x.abs().median())
OUT["otp_median_abs_month_change_post2022"] = noise.round(1).to_dict()

# block bootstrap over months for P(#1) and CI of the top-two difference
def boot_window(w, metric="otp_pct", higher=True, airlines=None, B=4000, block=3):
    X = win(M, w).pivot_table(index="date", columns="airline", values=metric)
    if airlines is None:
        airlines = [c for c in X.columns if X[c].notna().mean() >= 0.9]
    X = X[airlines].dropna(how="all")
    n = len(X)
    if n < 6 or len(airlines) < 2: return None
    nb = int(np.ceil(n / block)); wins = {a: 0 for a in airlines}
    means = X.mean().sort_values(ascending=not higher)
    top2 = list(means.index[:2]); diffs = []
    starts_all = np.arange(n - block + 1)
    for _ in range(B):
        st_ = RNG.choice(starts_all, nb)
        idx = np.concatenate([np.arange(s, s + block) for s in st_])[:n]
        Xi = X.iloc[idx]
        mu = Xi.mean()
        best = mu.idxmax() if higher else mu.idxmin()
        wins[best] += 1
        both = Xi[top2].dropna()
        diffs.append((both[top2[0]] - both[top2[1]]).mean())
    diffs = np.array(diffs)
    return dict(months=n, airlines=airlines, means=means.round(2).to_dict(),
                p_first={a: round(v / B, 3) for a, v in wins.items()},
                coverage={a: round(float(X[a].notna().mean()), 2) for a in airlines},
                top2=top2, top2_diff=round(float((X[top2].dropna()[top2[0]] - X[top2].dropna()[top2[1]]).mean()), 2),
                top2_diff_ci95=[round(float(np.percentile(diffs, 2.5)), 2), round(float(np.percentile(diffs, 97.5)), 2)])
OUT["bootstrap_otp"] = {w: boot_window(w) for w in WINDOWS}
OUT["bootstrap_cancel"] = {w: boot_window(w, "cancel_pct", higher=False) for w in WINDOWS}
OUT["bootstrap_complaints"] = {w: boot_window(w, "complaints_per10k", higher=False) for w in WINDOWS}

# ======================================================== T3 metric agreement
M["flights_on_time_per100_scheduled"] = (100 - M.cancel_pct) * M.otp_pct / 100
rho = []
for d, g in M.groupby("date"):
    g = g.dropna(subset=["otp_pct", "cancel_pct", "complaints_per10k"])
    if len(g) < 4: continue
    r1 = stats.spearmanr(g.otp_pct, g.cancel_pct).statistic
    r2 = stats.spearmanr(g.otp_pct, g.complaints_per10k).statistic
    r3 = stats.spearmanr(g.cancel_pct, g.complaints_per10k).statistic
    top_otp = g.loc[g.otp_pct.idxmax(), "airline"]; low_can = g.loc[g.cancel_pct.idxmin(), "airline"]; low_cmp = g.loc[g.complaints_per10k.idxmin(), "airline"]
    sets = [set(g[g.otp_pct == g.otp_pct.max()].airline), set(g[g.cancel_pct == g.cancel_pct.min()].airline), set(g[g.complaints_per10k == g.complaints_per10k.min()].airline)]
    outright = all(len(x) == 1 for x in sets) and sets[0] == sets[1] == sets[2]
    joint = bool(sets[0] & sets[1] & sets[2])
    rho.append(dict(date=d, n=len(g), all_three_outright=outright, all_three_joint=joint, rho_otp_cancel=r1, rho_otp_complaints=r2, rho_cancel_complaints=r3,
                    best_otp=top_otp, best_cancel=low_can, best_complaints=low_cmp, all_three_agree=(top_otp == low_can == low_cmp)))
RHO = pd.DataFrame(rho)
RHO.to_csv(os.path.join(D, "metric_agreement_by_month.csv"), index=False)
OUT["agreement"] = {"months": int(len(RHO)),
                    "median_rho_otp_cancel": round(float(RHO.rho_otp_cancel.median()), 2),
                    "median_rho_otp_complaints": round(float(RHO.rho_otp_complaints.median()), 2),
                    "median_rho_cancel_complaints": round(float(RHO.rho_cancel_complaints.median()), 2),
                    "share_months_same_best_all_three": round(float(RHO.all_three_agree.mean()), 2),
                    "months_outright_best_all_three": int(RHO.all_three_outright.sum()),
                    "months_best_or_joint_best_all_three": int(RHO.all_three_joint.sum()),
                    "share_months_best_otp_eq_best_cancel": round(float((RHO.best_otp == RHO.best_cancel).mean()), 2)}
# punctual by cancelling? within-airline monthly deviations
W = M.dropna(subset=["otp_pct", "cancel_pct"]).copy()
W = W[~W.date.between("2020-03-01", "2021-12-01")]
W["otp_dev"] = W.otp_pct - W.groupby("airline").otp_pct.transform("mean")
W["can_dev"] = W.cancel_pct - W.groupby("airline").cancel_pct.transform("mean")
r = stats.spearmanr(W.otp_dev, W.can_dev)
OUT["punctual_by_cancelling_within_airline"] = {"n_airline_months": int(len(W)), "spearman": round(float(r.statistic), 2), "p": float(r.pvalue)}

# composite with weight sweep (window means; rank-based and range-scaled)
def composite(w, airlines=None, step=0.05):
    X = win(M, w).dropna(subset=["otp_pct", "cancel_pct", "complaints_per10k"])
    cnt = X.groupby("airline").size()
    nmon = X.date.nunique()
    keep = cnt[cnt >= 0.75 * nmon].index if airlines is None else airlines
    X = X[X.airline.isin(keep)]
    mu = X.groupby("airline")[["otp_pct", "cancel_pct", "complaints_per10k"]].mean()
    mu["on_time_per100"] = X.groupby("airline").flights_on_time_per100_scheduled.mean()
    # scale 0..1, higher = better
    sc = pd.DataFrame(index=mu.index)
    sc["otp"] = (mu.otp_pct - mu.otp_pct.min()) / (mu.otp_pct.max() - mu.otp_pct.min())
    sc["can"] = (mu.cancel_pct.max() - mu.cancel_pct) / (mu.cancel_pct.max() - mu.cancel_pct.min())
    sc["cmp"] = (mu.complaints_per10k.max() - mu.complaints_per10k) / (mu.complaints_per10k.max() - mu.complaints_per10k.min())
    rk = pd.DataFrame({"otp": mu.otp_pct.rank(ascending=False), "can": mu.cancel_pct.rank(), "cmp": mu.complaints_per10k.rank()})
    wins_s = {a: 0 for a in mu.index}; wins_r = {a: 0 for a in mu.index}; nw = 0
    grid = np.arange(0, 1 + 1e-9, step)
    for a in grid:
        for b in grid:
            c = 1 - a - b
            if c < -1e-9: continue
            nw += 1
            s = a * sc.otp + b * sc.can + c * sc.cmp
            wins_s[s.idxmax()] += 1
            rr = a * rk.otp + b * rk.can + c * rk.cmp
            wins_r[rr.idxmin()] += 1
    return dict(airlines=list(mu.index), months=int(nmon), means=mu.round(2).to_dict(orient="index"),
                n_weightings=nw, share_won_scaled={k: round(v / nw, 3) for k, v in wins_s.items()},
                share_won_rank={k: round(v / nw, 3) for k, v in wins_r.items()},
                equal_weight_scaled=(sc.mean(axis=1)).round(3).to_dict())
OUT["composite"] = {w: composite(w) for w in WINDOWS}
TOP3 = ["IndiGo", "Air India", "Akasa Air"]
OUT["composite_top3_only"] = {w: composite(w, airlines=TOP3) for w in ["post_covid_2022-01_2026-09", "6apt_2025", "10apt_2026-01_2026-09", "last12_2025-10_2026-09"]}
# robustness: drop December 2025 from the last-12 window
_M = M
M = _M[_M.date != "2025-12-01"]
OUT["composite_last12_excl_dec2025"] = composite("last12_2025-10_2026-09", airlines=TOP3)
OUT["bootstrap_otp_last12_excl_dec2025"] = boot_window("last12_2025-10_2026-09", airlines=TOP3)
OUT["bootstrap_complaints_last12_excl_dec2025"] = boot_window("last12_2025-10_2026-09", "complaints_per10k", higher=False, airlines=TOP3)
M = _M
# monthly equal-weight rank composite leader (main airlines with all three metrics)
cl = []
for d, g in M.dropna(subset=["otp_pct", "cancel_pct", "complaints_per10k"]).groupby("date"):
    if len(g) < 3: continue
    sc = g.otp_pct.rank(ascending=False) + g.cancel_pct.rank() + g.complaints_per10k.rank()
    cl.append(dict(date=d, composite_leader=g.loc[sc.idxmin(), "airline"], otp_leader=g.loc[g.otp_pct.idxmax(), "airline"]))
CL = pd.DataFrame(cl)
CL.to_csv(os.path.join(D, "composite_leader_by_month.csv"), index=False)
OUT["composite_monthly"] = {"months": int(len(CL)), "same_as_otp_leader": round(float((CL.composite_leader == CL.otp_leader).mean()), 2),
    "composite_leader_counts_post2022": CL[CL.date >= "2022-01-01"].composite_leader.value_counts().to_dict(),
    "otp_leader_counts_post2022": CL[CL.date >= "2022-01-01"].otp_leader.value_counts().to_dict()}
# mix-test leader changes by era
lc = (l_pub != l_std)
OUT["mix_test_4apt_by_era"] = {"2018-2019": int(lc["2018":"2019"].sum()), "2018-2019_months": int(lc["2018":"2019"].size),
                               "2022-2024": int(lc["2022":"2024"].sum()), "2022-2024_months": int(lc["2022":"2024"].size),
                               "2025-2026": int(lc["2025":"2026"].sum()), "2025-2026_months": int(lc["2025":"2026"].size)}

# ======================================================== T4 size
sh = P.pivot_table(index="date", columns="airline", values="share_pct")
hhi = (sh.fillna(0) ** 2).sum(axis=1)
SIZE = pd.DataFrame({"indigo_share": sh["IndiGo"], "hhi": hhi})
SIZE.to_csv(os.path.join(D, "market_concentration.csv"))
OUT["size"] = {"indigo_share_first": float(sh["IndiGo"].iloc[0]), "indigo_share_first_date": str(sh.index[0].date()),
               "indigo_share_max": float(sh["IndiGo"].max()), "indigo_share_max_date": str(sh["IndiGo"].idxmax().date()),
               "indigo_share_last": float(sh["IndiGo"].iloc[-1]), "hhi_first": round(float(hhi.iloc[0])), "hhi_last": round(float(hhi.iloc[-1])),
               "indigo_share_2019_mean": round(float(sh.loc["2019", "IndiGo"].mean()), 1),
               "indigo_share_2026_mean": round(float(sh.loc["2026", "IndiGo"].mean()), 1)}
# cross-airline: share vs reliability (main airlines, window means), and within-IndiGo over time
for w in ["post_covid_2022-01_2026-09", "pre_covid_2018-2019"]:
    X = win(M, w).groupby("airline")[["share_pct", "otp_pct", "cancel_pct", "complaints_per10k"]].mean().dropna()
    OUT.setdefault("size_cross", {})[w] = {k: round(float(stats.spearmanr(X.share_pct, X[k]).statistic), 2) for k in ["otp_pct", "cancel_pct", "complaints_per10k"]} | {"n_airlines": int(len(X))}
ig = M[(M.airline == "IndiGo") & ~M.date.between("2020-03-01", "2021-12-01")].dropna(subset=["share_pct", "otp_pct"])
OUT["size_within_indigo"] = {"n": int(len(ig)), "rho_share_otp": round(float(stats.spearmanr(ig.share_pct, ig.otp_pct).statistic), 2),
                             "rho_share_cancel": round(float(stats.spearmanr(ig.share_pct, ig.cancel_pct).statistic), 2)}

# ======================================================== T5 events + seasonality
# passenger-weighted system OTP & cancellation (main airlines)
def wavg(g, col):
    g = g.dropna(subset=[col, "pax_lakh"]); return np.average(g[col], weights=g.pax_lakh) if len(g) else np.nan
sysm = M.groupby("date").apply(lambda g: pd.Series({"otp_w": wavg(g, "otp_pct"), "cancel_w": wavg(g, "cancel_pct"), "cmp_w": wavg(g, "complaints_per10k")}))
sysm = sysm.join(O.set_index("date")[["cancel_overall_pct", "complaints_per10k_overall", "complaints_total", "delay2h_overall_pct"]])
wx = R[(R.chart == "delay_reason") & (R.category == "Wx")].set_index("date").pct.rename("delay_wx_share")
react = R[(R.chart == "delay_reason") & (R.category == "Reactionary")].set_index("date").pct.rename("delay_reactionary_share")
cwx = R[(R.chart == "cancel_reason") & (R.category == "Weather")].set_index("date").pct.rename("cancel_weather_share")
sysm = sysm.join(wx).join(react).join(cwx)
sysm.to_csv(os.path.join(D, "system_monthly.csv"))
S = sysm[~((sysm.index >= "2020-03-01") & (sysm.index <= "2021-12-01"))].copy()
S["moy"] = S.index.month
season = S.groupby("moy")[["otp_w", "cancel_overall_pct", "delay_wx_share", "cancel_weather_share", "delay_reactionary_share"]].mean().round(2)
season.to_csv(os.path.join(D, "seasonality_month_of_year.csv"))
OUT["seasonality"] = season.to_dict(orient="index")
# is a bad month mostly fog? Compare Dec/Jan vs rest
fog = S[S.moy.isin([12, 1])]; rest = S[~S.moy.isin([12, 1])]
OUT["fog"] = {"otp_w_decjan": round(float(fog.otp_w.mean()), 1), "otp_w_rest": round(float(rest.otp_w.mean()), 1),
              "delay_wx_share_decjan": round(float(fog.delay_wx_share.mean()), 1), "delay_wx_share_rest": round(float(rest.delay_wx_share.mean()), 1),
              "delay_reactionary_decjan": round(float(fog.delay_reactionary_share.mean()), 1), "delay_reactionary_rest": round(float(rest.delay_reactionary_share.mean()), 1),
              "cancel_weather_decjan": round(float(fog.cancel_weather_share.mean()), 1), "cancel_weather_rest": round(float(rest.cancel_weather_share.mean()), 1)}
# worst 10 months by weighted OTP (excluding covid)
OUT["worst_otp_months"] = S.otp_w.nsmallest(10).round(1).rename(lambda d: str(d.date())).to_dict()
OUT["worst_cancel_months"] = S.cancel_overall_pct.nlargest(8).round(2).rename(lambda d: str(d.date())).to_dict()
# December 2025
def g(al, d, col):
    v = P[(P.airline == al) & (P.date == d)][col]
    return None if v.empty or pd.isna(v.iloc[0]) else float(v.iloc[0])
OUT["dec2025"] = {k: {c: g(k, "2025-12-01", c) for c in ["otp_pct", "cancel_pct", "complaints_per10k", "share_pct", "pax_lakh"]}
                  for k in ["IndiGo", "Air India", "Akasa Air", "SpiceJet"]}
OUT["nov2025_indigo"] = {c: g("IndiGo", "2025-11-01", c) for c in ["otp_pct", "cancel_pct", "complaints_per10k", "share_pct", "pax_lakh"]}
OUT["dec2025_overall"] = O[O.date == "2025-12-01"][["cancel_overall_pct", "complaints_total", "complaints_per10k_overall"]].iloc[0].to_dict()
OUT["dec2025_cancel_reasons"] = R[(R.date == "2025-12-01") & (R.chart == "cancel_reason")].set_index("category").pct.to_dict()
OUT["dec2025_complaint_reasons"] = R[(R.date == "2025-12-01") & (R.chart == "complaint_reason")].set_index("category").pct.to_dict()
# IndiGo's cancellation rate history: how unusual was Dec 2025?
igc = P[(P.airline == "IndiGo")].set_index("date").cancel_pct
OUT["indigo_cancel"] = {"median_2022_2025nov": round(float(igc["2022-01-01":"2025-11-01"].median()), 2),
                        "max_before_dec2025": round(float(igc[:"2025-11-01"].max()), 2), "max_before_date": str(igc[:"2025-11-01"].idxmax().date()),
                        "dec2025": float(igc["2025-12-01"])}
# Go First exit
OUT["gofirst"] = {str(d.date()): {"share": float(r.share_pct) if pd.notna(r.share_pct) else None, "otp": r.otp_pct, "cancel": r.cancel_pct}
                  for d, r in P[(P.airline == "Go First") & (P.date >= "2023-01-01")].set_index("date").iterrows()}
# SpiceJet 2026
sj = P[(P.airline == "SpiceJet") & (P.date >= "2025-01-01")].set_index("date")[["otp_pct", "cancel_pct", "delay2h_pct", "share_pct", "complaints_per10k"]]
OUT["spicejet_2025_2026"] = {str(d.date()): r.dropna().to_dict() for d, r in sj.iterrows()}

# ======================================================== T6 complaints
cr = R[R.chart == "complaint_reason"].merge(O[["date", "complaints_total"]], on="date")
cr["n"] = cr.pct / 100 * cr.complaints_total
cr["year"] = cr.date.dt.year
cy = cr.groupby(["year", "category"]).n.sum().unstack()
cy_pct = (cy.div(cy.sum(axis=1), axis=0) * 100).round(1)
cy_pct.to_csv(os.path.join(D, "complaint_reasons_by_year.csv"))
OUT["complaint_reasons_by_year_pct"] = cy_pct.to_dict(orient="index")
oy = O.copy(); oy["year"] = oy.date.dt.year
ann = oy.groupby("year").agg(complaints=("complaints_total", "sum"))
paxy = P.groupby(P.date.dt.year).pax_lakh.sum()
ann["pax_lakh"] = paxy
ann["per10k"] = (ann.complaints / (ann.pax_lakh * 1e5) * 1e4).round(2)
ann.to_csv(os.path.join(D, "complaints_by_year.csv"))
OUT["complaints_by_year"] = ann.to_dict(orient="index")
ex = oy[oy.date != "2025-12-01"].groupby("year").complaints_per10k_overall.median()
OUT["complaints_median_monthly_rate_by_year_excl_dec2025"] = ex.round(2).to_dict()
cpa = M[M.date.dt.year.isin([2019, 2023, 2024, 2025, 2026])].copy()
cpa["year"] = cpa.date.dt.year
OUT["complaints_airline_year_median"] = cpa.groupby(["airline", "year"]).complaints_per10k.median().round(2).unstack().to_dict(orient="index")

# ======================================================== T7 extras
A26all = A[(A.airline == "ALL")]
OUT["airport_all_2026_mean"] = A26all.groupby("airport").otp_pct.mean().round(1).sort_values().to_dict()
d2 = P[P.date >= "2026-01-01"].groupby("airline").delay2h_pct.mean().dropna().round(2)
OUT["delay2h_2026_mean"] = d2.to_dict()
OUT["last12_means"] = win(M, "last12_2025-10_2026-09").groupby("airline")[["otp_pct", "cancel_pct", "complaints_per10k", "share_pct", "flights_on_time_per100_scheduled"]].mean().round(2).to_dict(orient="index")
OUT["sep2026"] = P[P.date == "2026-09-01"].set_index("airline")[["otp_pct", "cancel_pct", "complaints_per10k", "delay2h_pct", "share_pct"]].dropna(how="all").to_dict(orient="index")

M.to_csv(os.path.join(D, "main_airline_months.csv"), index=False)

def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else round(float(o), 3)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, float) and np.isnan(o): return None
    if isinstance(o, (np.bool_,)): return bool(o)
    return o
json.dump(clean(OUT), open(os.path.join(D, "headline_numbers.json"), "w"), indent=1)
print(json.dumps(clean(OUT), indent=1)[:200])
