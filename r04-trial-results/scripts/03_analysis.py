"""R04 step 3: main analysis (pandas path).

Usage: python3 -I 03_analysis.py <studies_parquet> <data_dir>
Writes chart-ready CSVs and headline_numbers.json into <data_dir>.
"""
import json, os, sys, warnings
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import T, RULE, OPEN, derive, proxies, wilson, newcombe, rate  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 20261122
H = {"data_timestamp": "2026-11-20T10:00:05", "api_version": "2.0.5", "reference_date": str(T.date())}


def r2(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 2)


def diff(m1, m2, outcome):
    k1, n1 = int((m1 & outcome).sum()), int(m1.sum())
    k2, n2 = int((m2 & outcome).sum()), int(m2.sum())
    dd, lo, hi = newcombe(k1, n1, k2, n2)
    return {"pp_diff": r2(100 * dd), "lo": r2(100 * lo), "hi": r2(100 * hi),
            "ratio": r2((k1 / n1) / (k2 / n2)) if n1 and n2 and k2 else None}


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    raw = pd.read_parquet(src)
    d = derive(raw)
    P = proxies(d)
    INT = d.is_int
    due_cut = T - pd.Timedelta(days=365)       # 12-month window fully elapsed
    like_cut = T - pd.Timedelta(days=730)      # 24-month window fully elapsed

    # ------------------------------------------------------------------ exclusion log / coverage
    ex = []
    def log(step, n, note=""):
        ex.append({"step": step, "n": int(n), "note": note})
    log("All records in API download", len(d), "API v2.0.5, dataTimestamp 2026-11-20")
    log("Interventional", INT.sum())
    log("Observational (excluded)", d.study_type.eq("OBSERVATIONAL").sum())
    log("Expanded access (excluded)", d.study_type.eq("EXPANDED_ACCESS").sum())
    log("Study type missing (withheld device records, excluded)", d.study_type.isna().sum())
    log("Interventional: WITHDRAWN (never enrolled; excluded from 'due' cohorts)", (INT & d.overall_status.eq("WITHDRAWN")).sum())
    log("Interventional: COMPLETED", (INT & d.overall_status.eq("COMPLETED")).sum())
    log("Interventional COMPLETED: primary completion date missing", (INT & d.overall_status.eq("COMPLETED") & d.pcd_dt.isna()).sum())
    log("Interventional COMPLETED: primary completion date type missing (old records)",
        (INT & d.overall_status.eq("COMPLETED") & d.pcd_type.isna() & d.pcd_dt.notna()).sum(), "kept in headline; dropped in robustness")
    log("Interventional COMPLETED: primary completion still marked ESTIMATED",
        (INT & d.overall_status.eq("COMPLETED") & d.pcd_type.eq("ESTIMATED")).sum(), "kept in headline; dropped in robustness")
    log("Interventional: month-only primary completion date", (INT & d.pcd.str.len().eq(7)).sum(), "set to last day of month; first-day sensitivity")
    log("Interventional: results submitted before primary completion date (negative delay)",
        (INT & d.days_to_submit.lt(0)).sum(), "counted as on time")
    log("Interventional: results submitted but not yet posted (in QC)", (INT & d.pending_qc).sum(), "counted as submitted")
    log("hasResults=true but no results-first-submitted date", (d.posted & d.results_first_submit_dt.isna()).sum())
    log("Interventional: results waived flag", (INT & d.results_waived.eq(True)).sum())
    for k in ["main", "strict", "broad", "noloc", "lite"]:
        log(f"Proxy '{k}': trials (any date)", P[k].sum())
    pd.DataFrame(ex).to_csv(os.path.join(out, "exclusion_log.csv"), index=False)
    H["coverage"] = {r["step"]: r["n"] for r in ex}

    # ------------------------------------------------------------------ H1 headline
    comp = INT & d.overall_status.eq("COMPLETED")
    H["h1_all_records_posted"] = rate(pd.Series(True, index=d.index), d.posted)
    H["h1_interventional_posted"] = rate(INT, d.posted)
    H["h1_completed_int_posted"] = rate(comp, d.posted)
    H["h1_completed_int_submitted"] = rate(comp, d.submitted)
    win = comp & d.pcd_year.between(2008, 2023)
    H["h1_completed_int_pcd2008_2023_posted"] = rate(win, d.posted)
    H["h1_completed_int_pcd2008_2023_submitted"] = rate(win, d.submitted)
    H["h1_completed_or_terminated_pcd2008_2023_submitted"] = rate(
        INT & d.overall_status.isin(["COMPLETED", "TERMINATED"]) & d.pcd_year.between(2008, 2023), d.submitted)
    rows = []
    for y in range(2000, 2027):
        m = comp & d.pcd_year.eq(y)
        a, b = rate(m, d.posted), rate(m, d.submitted)
        mp = m & P["main"]
        c = rate(mp, d.submitted)
        mo = m & ~P["main"]
        e = rate(mo, d.submitted)
        nonus = m & ~d.has_us_site & d.has_nonus_site
        rows.append({"pcd_year": y, "n_completed": a["n"], "pct_posted": a["pct"], "pct_submitted": b["pct"],
                     "lo": b["lo"], "hi": b["hi"], "n_probably_required": c["n"], "pct_submitted_probably_required": c["pct"],
                     "n_other": e["n"], "pct_submitted_other": e["pct"],
                     "pct_nonus_only": r2(100 * nonus.sum() / m.sum()) if m.sum() else None,
                     "pct_us_site": r2(100 * (m & d.has_us_site).sum() / m.sum()) if m.sum() else None,
                     "pct_submitted_us_site": rate(m & d.has_us_site, d.submitted)["pct"],
                     "pct_submitted_nonus_only": rate(nonus, d.submitted)["pct"],
                     "pct_lite": r2(100 * (m & P["lite"]).sum() / m.sum()) if m.sum() else None,
                     "pct_submitted_lite": rate(m & P["lite"], d.submitted)["pct"],
                     "pct_submitted_not_lite": rate(m & ~P["lite"], d.submitted)["pct"]})
    h1y = pd.DataFrame(rows)
    # mix standardisation: hold each year's location mix (US site / non-US only / none listed) at the 2008 mix
    loc3 = np.select([d.has_us_site, d.has_nonus_site], ["us", "nonus"], "none")
    base_m = comp & d.pcd_year.eq(2008)
    w08 = pd.Series(loc3[base_m.values]).value_counts(normalize=True)
    std = []
    for y in h1y.pcd_year:
        m = comp & d.pcd_year.eq(y)
        rates = {g: d.loc[m & (loc3 == g), "submitted"].mean() for g in ["us", "nonus", "none"]}
        std.append(r2(100 * sum(w08.get(g, 0) * (rates[g] if not np.isnan(rates[g]) else 0) for g in w08.index)))
    h1y["pct_submitted_2008_location_mix"] = std
    h1y.to_csv(os.path.join(out, "h1_completed_by_pcd_year.csv"), index=False)
    yy = h1y.set_index("pcd_year")
    H["h1_mix"] = {"w2008": {k: r2(100 * v) for k, v in w08.items()},
                   "2023_actual": yy.loc[2023, "pct_submitted"], "2023_at_2008_mix": yy.loc[2023, "pct_submitted_2008_location_mix"],
                   "2008_actual": yy.loc[2008, "pct_submitted"],
                   "share_of_drop_from_mix_pct": r2(100 * (yy.loc[2023, "pct_submitted_2008_location_mix"] - yy.loc[2023, "pct_submitted"]) /
                                                    (yy.loc[2008, "pct_submitted"] - yy.loc[2023, "pct_submitted"]))}
    H["h1_trend"] = {str(y): {k: yy.loc[y, k] for k in ["n_completed", "pct_submitted", "pct_nonus_only", "pct_submitted_us_site", "pct_submitted_nonus_only", "pct_lite", "pct_submitted_lite"]}
                     for y in [2008, 2012, 2016, 2019, 2022, 2023]}
    h1y.to_csv(os.path.join(out, "h1_completed_by_pcd_year.csv"), index=False)
    # by study completion year too
    rows = []
    for y in range(2000, 2027):
        m = comp & d.cd_year.eq(y)
        b = rate(m, d.submitted)
        rows.append({"cd_year": y, "n_completed": b["n"], "pct_submitted": b["pct"]})
    pd.DataFrame(rows).to_csv(os.path.join(out, "h1_completed_by_cd_year.csv"), index=False)
    # composition of the completed pile
    H["h1_completed_composition"] = {
        "share_product_type_pct": r2(100 * (comp & d.product_type).sum() / comp.sum()),
        "share_us_site_pct": r2(100 * (comp & d.has_us_site).sum() / comp.sum()),
        "share_probably_required_main_pct": r2(100 * (comp & P["main"]).sum() / comp.sum()),
        "share_phase1_only_pct": r2(100 * (comp & d.phase1_only).sum() / comp.sum()),
        "share_phase_NA_pct": r2(100 * (comp & d.phases.eq("NA")).sum() / comp.sum()),
        "share_sponsor_other_pct": r2(100 * (comp & d.sponsor_class.eq("OTHER")).sum() / comp.sum()),
    }

    # ------------------------------------------------------------------ H2 denominator turn
    due = P["base"] & d.pcd_type.eq("ACTUAL") & (d.pcd_dt >= RULE) & (d.pcd_dt <= due_cut)
    like = due & (d.pcd_dt <= like_cut)
    H["h2_due_cohort_n"] = int(due.sum())
    H["h2_like_cohort_n"] = int(like.sum())
    for nm in ["main", "strict", "broad", "noloc"]:
        req, oth = like & P[nm], like & ~P[nm]
        H[f"h2_{nm}"] = {
            "required_n": int(req.sum()), "other_n": int(oth.sum()),
            "required_sub12": rate(req, d.sub_12m), "other_sub12": rate(oth, d.sub_12m),
            "required_sub24": rate(req, d.sub_24m), "other_sub24": rate(oth, d.sub_24m),
            "required_ever": rate(req, d.submitted), "other_ever": rate(oth, d.submitted),
            "diff_sub12": diff(req, oth, d.sub_12m), "diff_sub24": diff(req, oth, d.sub_24m),
            "diff_ever": diff(req, oth, d.submitted),
        }
    # whole due cohort (PCD 2017-01-18 .. T-365), main proxy
    req = due & P["main"]
    H["h2_main_due_all"] = {"n": int(req.sum()), "sub12": rate(req, d.sub_12m), "ever": rate(req, d.submitted),
                            "posted": rate(req, d.posted), "pending_qc": rate(req, d.pending_qc),
                            "cert_before_deadline": rate(req, d.cert_before_deadline),
                            "sub12_or_cert": rate(req, d.sub_12m | d.cert_before_deadline),
                            "not_submitted_no_cert": rate(req, ~d.submitted & ~d.disp_first_submit_dt.notna())}
    # share of all completed interventional trials that are 'probably required'
    H["h2_share_of_like_cohort_probably_required_pct"] = r2(100 * (like & P["main"]).sum() / like.sum())
    # why 'others' are not in the proxy
    oth = like & ~P["main"]
    reasons = pd.Series(np.select(
        [~oth, d.fda_missing, ~d.fda_any, d.phase1_only, d.feasibility, ~d.us_or_export],
        ["-", "FDA-regulated flags missing", "Not an FDA-regulated product (flags = No)", "Phase 1 only",
         "Device feasibility", "No US site and not exported"], "other"), index=d.index)[oth]
    rs = reasons.value_counts().rename_axis("reason").reset_index(name="n")
    rs["pct"] = (100 * rs.n / rs.n.sum()).round(2)
    rs.to_csv(os.path.join(out, "h2_why_not_probably_required.csv"), index=False)
    H["h2_why_not_required"] = rs.set_index("reason").pct.to_dict()
    # composition of the like cohort and of its no-results pile
    seg = pd.Series(np.select(
        [like & P["main"], like & d.has_us_site, like & ~d.has_us_site & d.has_nonus_site, like],
        ["Probably required", "Not required, has a US site", "Not required, non-US sites only", "Not required, no location listed"],
        "-"), index=d.index)
    rows = []
    for g in ["Probably required", "Not required, has a US site", "Not required, non-US sites only", "Not required, no location listed"]:
        for sg in [None, "Industry", "Universities, hospitals & non-profits", "NIH", "Other US federal", "Non-US government"]:
            m = seg.eq(g) & (d.sponsor_group.eq(sg) if sg else True)
            if m.sum() == 0:
                continue
            rows.append({"segment": g, "sponsor_group": sg or "All", "n": int(m.sum()),
                         "pct_of_cohort": r2(100 * m.sum() / like.sum()),
                         "pct_sub24": rate(m, d.sub_24m)["pct"], "pct_ever": rate(m, d.submitted)["pct"],
                         "pct_of_no_results_pile": r2(100 * (m & ~d.sub_24m).sum() / (like & ~d.sub_24m).sum())})
    seg_df = pd.DataFrame(rows)
    seg_df.to_csv(os.path.join(out, "h2_cohort_segments.csv"), index=False)
    H["h2_segments"] = seg_df.to_dict("records")
    # by PCD year, proxy vs other, among like cohort and due cohort
    rows = []
    for y in range(2017, 2026):
        for nm, m in [("Probably required", due & P["main"]), ("Everything else", due & ~P["main"])]:
            mm = m & d.pcd_year.eq(y)
            rows.append({"pcd_year": y, "group": nm, **{f"sub12_{k}": v for k, v in rate(mm, d.sub_12m).items()},
                         "sub24_pct": rate(mm, d.sub_24m)["pct"] if y <= 2023 else None,
                         "ever_pct": rate(mm, d.submitted)["pct"]})
    pd.DataFrame(rows).to_csv(os.path.join(out, "h2_required_vs_other_by_year.csv"), index=False)

    # ------------------------------------------------------------------ H3 timeliness
    actual = P["base"] & d.pcd_type.eq("ACTUAL") & d.overall_status.isin(["COMPLETED", "TERMINATED", "ACTIVE_NOT_RECRUITING", "UNKNOWN", "SUSPENDED", "ENROLLING_BY_INVITATION", "RECRUITING"])
    rows = []
    for y in range(2008, 2026):
        for nm, m in [("Drug/device trials with a US site, beyond phase 1", actual & P["lite"]),
                      ("Probably required (main proxy)", actual & P["main"]),
                      ("All other interventional", actual & ~P["lite"]),
                      ("All interventional", actual)]:
            mm = m & d.pcd_year.eq(y)
            fu = (T - pd.Timestamp(f"{y}-12-31")).days
            rows.append({"pcd_year": y, "group": nm, "n": int(mm.sum()),
                         "pct_12m": rate(mm, d.sub_12m)["pct"] if fu >= 365 else None,
                         "pct_24m": rate(mm, d.sub_24m)["pct"] if fu >= 730 else None,
                         "pct_36m": rate(mm, d.sub_36m)["pct"] if fu >= 1095 else None,
                         "pct_ever": rate(mm, d.submitted)["pct"],
                         "lo_12m": rate(mm, d.sub_12m)["lo"], "hi_12m": rate(mm, d.sub_12m)["hi"]})
    tl = pd.DataFrame(rows)
    # selection check: trials whose PCD year has passed but whose PCD is still marked ESTIMATED (record not updated)
    est = P["base"] & d.pcd_type.eq("ESTIMATED") & (d.pcd_dt <= due_cut)
    extra = []
    for y in range(2008, 2026):
        for nm, grp in [("Drug/device trials with a US site, beyond phase 1", P["lite"]), ("Probably required (main proxy)", P["main"]),
                        ("All other interventional", ~P["lite"]), ("All interventional", P["base"])]:
            me = est & grp & d.pcd_year.eq(y)
            ma = actual & grp & d.pcd_year.eq(y)
            both = me | ma
            extra.append({"pcd_year": y, "group": nm, "n_pcd_still_estimated": int(me.sum()),
                          "pct_still_estimated": r2(100 * me.sum() / both.sum()) if both.sum() else None,
                          "pct_12m_incl_estimated": rate(both, d.sub_12m)["pct"]})
    tl = tl.merge(pd.DataFrame(extra), on=["pcd_year", "group"], how="left")
    tl.to_csv(os.path.join(out, "h3_timeliness_by_pcd_year.csv"), index=False)
    H["h3_lite_2024_sub12_actual_only"] = rate(actual & P["lite"] & d.pcd_year.eq(2024), d.sub_12m)
    H["h3_lite_2024_sub12_incl_estimated"] = rate((actual | est) & P["lite"] & d.pcd_year.eq(2024), d.sub_12m)
    H["h3_lite_2023_sub12_actual_only"] = rate(actual & P["lite"] & d.pcd_year.eq(2023), d.sub_12m)
    H["h3_lite_2023_sub12_incl_estimated"] = rate((actual | est) & P["lite"] & d.pcd_year.eq(2023), d.sub_12m)
    # cumulative share submitted by months since PCD, by cohort, for lite group
    rows = []
    for y in range(2010, 2026):
        mm = actual & P["lite"] & d.pcd_year.eq(y)
        fu_m = int((T - pd.Timestamp(f"{y}-12-31")).days // 30.44)
        dts = d.loc[mm, "days_to_submit"]
        n = int(mm.sum())
        for mth in range(0, min(fu_m, 120) + 1, 3):
            rows.append({"pcd_year": y, "months": mth, "n": n,
                         "pct_submitted": round(100 * ((dts <= mth * 30.44) & dts.notna()).sum() / n, 2)})
    pd.DataFrame(rows).to_csv(os.path.join(out, "h3_cumulative_by_cohort_lite.csv"), index=False)
    # pre vs post rule comparison
    pre = actual & P["lite"] & d.pcd_year.between(2014, 2016)
    post = actual & P["lite"] & d.pcd_year.between(2018, 2020)
    H["h3_lite_pre_2014_16_sub12"] = rate(pre, d.sub_12m)
    H["h3_lite_post_2018_20_sub12"] = rate(post, d.sub_12m)
    H["h3_lite_post_minus_pre_sub12"] = diff(post, pre, d.sub_12m)
    H["h3_lite_pre_2014_16_sub24"] = rate(pre, d.sub_24m)
    H["h3_lite_post_2018_20_sub24"] = rate(post, d.sub_24m)
    H["h3_lite_post_minus_pre_sub24"] = diff(post, pre, d.sub_24m)
    H["h3_lite_2008_2010_sub12"] = rate(actual & P["lite"] & d.pcd_year.between(2008, 2010), d.sub_12m)
    H["h3_lite_2022_2024_sub12"] = rate(actual & P["lite"] & d.pcd_year.between(2022, 2024), d.sub_12m)
    H["h3_main_2018_2024_sub12"] = rate(actual & P["main"] & d.pcd_year.between(2018, 2024) & (d.pcd_dt <= due_cut), d.sub_12m)
    # control group: other interventional trials, same years (difference-in-differences, descriptive)
    preo = actual & ~P["lite"] & d.pcd_year.between(2014, 2016)
    posto = actual & ~P["lite"] & d.pcd_year.between(2018, 2020)
    H["h3_other_pre_sub12"] = rate(preo, d.sub_12m)
    H["h3_other_post_sub12"] = rate(posto, d.sub_12m)
    # median delay among those who submitted within 36 months (both groups, PCD 2018-2022)
    m = actual & P["main"] & d.pcd_year.between(2018, 2022) & d.sub_36m
    H["h3_main_2018_22_median_days_to_submit_among_sub36"] = r2(d.loc[m, "days_to_submit"].median())
    m2 = actual & P["main"] & d.pcd_year.between(2018, 2022)
    H["h3_main_2018_22_by_window"] = {k: rate(m2, d[f"sub_{k}"]) for k in ["12m", "24m", "36m"]}
    H["h3_main_2018_22_ever"] = rate(m2, d.submitted)
    # within 13 months (30-day slack) sensitivity
    H["h3_main_like_sub13"] = rate(like & P["main"], d.submitted & (d.days_to_submit <= 395))

    # ------------------------------------------------------------------ H4 who reports (main proxy, like cohort)
    L = like & P["main"]
    rows = []
    def grp_rows(col, label, mask=L):
        for g, sub in d[mask].groupby(col):
            m = mask & d[col].eq(g)
            a, b = rate(m, d.sub_12m), rate(m, d.sub_24m)
            rows.append({"dimension": label, "group": g, "n": a["n"], "pct_12m": a["pct"], "lo_12m": a["lo"], "hi_12m": a["hi"],
                         "pct_24m": b["pct"], "lo_24m": b["lo"], "hi_24m": b["hi"],
                         "pct_cert_before_deadline": rate(m, d.cert_before_deadline)["pct"],
                         "pct_12m_or_cert": rate(m, d.sub12_or_cert)["pct"], "lo_12m_or_cert": rate(m, d.sub12_or_cert)["lo"],
                         "hi_12m_or_cert": rate(m, d.sub12_or_cert)["hi"]})
    grp_rows("sponsor_group", "Lead sponsor")
    grp_rows("phase_group", "Phase")
    grp_rows("product", "Product")
    grp_rows("overall_status", "Status")
    NL = like & P["noloc"]
    d["us_label"] = np.where(d.has_us_site, "Has a US site", np.where(d.us_export.eq(True), "No US site, US-exported product", "No US site, not exported"))
    grp_rows("us_label", "Location (no-location proxy)", NL)
    who = pd.DataFrame(rows)
    who.to_csv(os.path.join(out, "h4_who_reports.csv"), index=False)
    H["h4_who"] = who.to_dict("records")
    # adjusted comparison: logistic model + standardisation (g-computation)
    import statsmodels.formula.api as smf
    dm = d[L].copy()
    dm["y12"] = dm.sub_12m.astype(int); dm["y24"] = dm.sub_24m.astype(int); dm["y12c"] = dm.sub12_or_cert.astype(int)
    dm["sg"] = dm.sponsor_group.where(dm.sponsor_group.isin(["Industry", "NIH", "Other US federal", "Universities, hospitals & non-profits"]), "Other")
    dm["us"] = dm.has_us_site.astype(int)
    dm["yr"] = dm.pcd_year.astype(str)
    adj = {}
    groups = ["Industry", "NIH", "Other US federal", "Universities, hospitals & non-profits", "Other"]
    rng = np.random.default_rng(SEED)
    for yv in ["y12", "y24", "y12c"]:
        f = f"{yv} ~ C(sg) + C(phase_group) + C(product) + C(yr) + us"
        fit = smf.logit(f, dm).fit(disp=0)
        def std(fitm, data):
            res = {}
            for g in groups:
                tmp = data.copy(); tmp["sg"] = g
                res[g] = float(fitm.predict(tmp).mean())
            return res
        point = std(fit, dm)
        boots = []
        for b in range(200):
            idx = rng.integers(0, len(dm), len(dm))
            bd = dm.iloc[idx]
            try:
                bf = smf.logit(f, bd).fit(disp=0)
                boots.append(std(bf, dm))
            except Exception:  # noqa: BLE001
                pass
        bdf = pd.DataFrame(boots)
        crude = dm.groupby("sg")[yv].mean().to_dict()
        adj[yv] = {g: {"crude_pct": r2(100 * crude.get(g, np.nan)), "standardised_pct": r2(100 * point[g]),
                       "lo": r2(100 * bdf[g].quantile(0.025)), "hi": r2(100 * bdf[g].quantile(0.975)),
                       "n": int((dm.sg == g).sum())} for g in groups}
        di = 100 * (bdf["Industry"] - bdf["Universities, hospitals & non-profits"])
        adj[yv]["industry_minus_univ_std_pp"] = {"point": r2(100 * (point["Industry"] - point["Universities, hospitals & non-profits"])),
                                                  "lo": r2(di.quantile(0.025)), "hi": r2(di.quantile(0.975))}
        dn = 100 * (bdf["Industry"] - bdf["NIH"])
        adj[yv]["industry_minus_nih_std_pp"] = {"point": r2(100 * (point["Industry"] - point["NIH"])), "lo": r2(dn.quantile(0.025)), "hi": r2(dn.quantile(0.975))}
        adj[yv]["n_boot_ok"] = len(bdf)
    H["h4_adjusted"] = adj
    pd.DataFrame([{"outcome": yv, "group": g, **adj[yv][g]} for yv in adj for g in groups]).to_csv(
        os.path.join(out, "h4_sponsor_adjusted.csv"), index=False)
    # sponsor mix: share of phase 3 and drug among industry vs univ
    H["h4_mix"] = {g: {"share_phase3_pct": r2(100 * (dm[dm.sg == g].phase_group == "Phase 3").mean()),
                       "share_phaseNA_pct": r2(100 * (dm[dm.sg == g].phase_group == "Not applicable").mean()),
                       "share_us_pct": r2(100 * dm[dm.sg == g].us.mean())} for g in groups}
    # non-required trials by sponsor
    O = like & ~P["main"]
    H["h4_other_by_sponsor"] = {g: rate(O & d.sponsor_group.eq(g), d.sub_24m) for g in ["Industry", "NIH", "Other US federal", "Universities, hospitals & non-profits", "Non-US government"]}

    # ------------------------------------------------------------------ H5 status rot
    B = P["base"]
    stale_cut = T - pd.Timedelta(days=730)
    ended = B & d.pcd_dt.notna() & (d.pcd_dt <= stale_cut)
    st = pd.Series(np.select([d.overall_status.eq("COMPLETED"), d.overall_status.eq("TERMINATED"), d.overall_status.eq("UNKNOWN"),
                              d.overall_status.isin(OPEN)], ["Completed", "Terminated", "Unknown status", "Still marked open/active"], "Other"), index=d.index)
    d["status4"] = st
    rows = []
    for g in ["Completed", "Terminated", "Unknown status", "Still marked open/active", "Other"]:
        m = ended & st.eq(g)
        rows.append({"status": g, "n": int(m.sum()), "pct_of_ended": r2(100 * m.sum() / ended.sum()),
                     "pct_submitted": rate(m, d.submitted)["pct"],
                     "n_no_results": int((m & ~d.submitted).sum())})
    sr = pd.DataFrame(rows)
    sr["pct_of_no_results_pile"] = (100 * sr.n_no_results / sr.n_no_results.sum()).round(2)
    sr.to_csv(os.path.join(out, "h5_status_of_trials_past_completion.csv"), index=False)
    H["h5_status_rot"] = sr.to_dict("records")
    H["h5_ended_n"] = int(ended.sum())
    H["h5_ended_submitted"] = rate(ended, d.submitted)
    H["h5_completed_terminated_only_submitted"] = rate(ended & st.isin(["Completed", "Terminated"]), d.submitted)
    # open trials: years since estimated pcd and since last update
    op = ended & st.eq("Still marked open/active")
    H["h5_open_median_years_past_pcd"] = r2(((T - d.loc[op, "pcd_dt"]).dt.days / 365.25).median())
    H["h5_open_median_years_since_update"] = r2(((T - d.loc[op, "last_update_submit_dt"]).dt.days / 365.25).median())
    un = ended & st.eq("Unknown status")
    H["h5_unknown_median_years_since_update"] = r2(((T - d.loc[un, "last_update_submit_dt"]).dt.days / 365.25).median())
    H["h5_unknown_last_known"] = d.loc[un, "last_known_status"].value_counts(normalize=True).mul(100).round(2).to_dict()
    # proxy-like trials with stale status (excluded from 'due' because PCD not marked actual)
    stale_req = P["main"] & (d.pcd_dt >= RULE) & (d.pcd_dt <= stale_cut) & ~d.pcd_type.eq("ACTUAL")
    H["h5_probably_required_stale_n"] = int(stale_req.sum())
    H["h5_probably_required_stale_status"] = d.loc[stale_req, "overall_status"].value_counts().to_dict()
    H["h5_probably_required_stale_submitted"] = rate(stale_req, d.submitted)
    # sensitivity: add them to the like cohort
    L2 = L | stale_req
    H["h5_main_like_plus_stale_sub24"] = rate(L2, d.sub_24m)
    # by sponsor and region: unknown-status share among ended
    rows = []
    for g in ["Industry", "NIH", "Other US federal", "Universities, hospitals & non-profits", "Non-US government"]:
        m = ended & d.sponsor_group.eq(g)
        rows.append({"sponsor_group": g, "n_ended": int(m.sum()),
                     "pct_unknown": r2(100 * (m & st.eq("Unknown status")).sum() / m.sum()),
                     "pct_open": r2(100 * (m & st.eq("Still marked open/active")).sum() / m.sum())})
    pd.DataFrame(rows).to_csv(os.path.join(out, "h5_stale_by_sponsor.csv"), index=False)
    H["h5_stale_by_sponsor"] = rows
    m_us, m_non = ended & d.has_us_site, ended & ~d.has_us_site & d.has_nonus_site
    H["h5_unknown_pct_us_sites"] = rate(m_us, st.eq("Unknown status"))
    H["h5_unknown_pct_nonus_only"] = rate(m_non, st.eq("Unknown status"))

    # ------------------------------------------------------------------ H6 named sponsors
    S = L.copy()
    sp = d[S].groupby("sponsor").agg(n=("nct_id", "size"), k12=("sub_12m", "sum"), k24=("sub_24m", "sum"),
                                      kcert=("cert_before_deadline", "sum"), kever=("submitted", "sum"),
                                      cls=("sponsor_class", "first")).reset_index()
    k12c = d[S].groupby("sponsor").sub12_or_cert.sum()
    sp["k12_or_cert"] = sp.sponsor.map(k12c)
    big = sp[sp.n >= 100].sort_values("n", ascending=False).copy()
    for c, k in [("12m", "k12"), ("24m", "k24"), ("12m_or_cert", "k12_or_cert"), ("ever", "kever")]:
        w = big.apply(lambda r: wilson(r[k], r.n), axis=1)
        big[f"pct_{c}"] = [round(100 * x[0], 1) for x in w]
        big[f"lo_{c}"] = [round(100 * x[1], 1) for x in w]
        big[f"hi_{c}"] = [round(100 * x[2], 1) for x in w]
    big.to_csv(os.path.join(out, "h6_largest_sponsors_probably_required.csv"), index=False)
    H["h6_n_sponsors_ge100"] = int(len(big))
    H["h6_share_of_cohort_pct"] = r2(100 * big.n.sum() / S.sum())
    # sponsor size: how much of the overdue pile sits with small vs large sponsors (like cohort, main proxy)
    size = d[S].groupby("sponsor").nct_id.transform("size")
    d["sponsor_size"] = pd.cut(size, [0, 4, 19, 99, 1e9], labels=["1-4 trials", "5-19 trials", "20-99 trials", "100+ trials"]).reindex(d.index)
    overdue_like = S & ~d.submitted & d.disp_first_submit_dt.isna()
    rows = []
    for g in ["1-4 trials", "5-19 trials", "20-99 trials", "100+ trials"]:
        m = S & d.sponsor_size.eq(g)
        rows.append({"sponsor_size": g, "n_sponsors": int(d.loc[m, "sponsor"].nunique()), "n_trials": int(m.sum()),
                     "pct_of_trials": r2(100 * m.sum() / S.sum()), "pct_12m_or_cert": rate(m, d.sub12_or_cert)["pct"],
                     "pct_24m": rate(m, d.sub_24m)["pct"], "pct_ever": rate(m, d.submitted)["pct"],
                     "n_no_results_no_cert": int((m & overdue_like).sum()),
                     "pct_of_no_results_no_cert": r2(100 * (m & overdue_like).sum() / overdue_like.sum())})
    pd.DataFrame(rows).to_csv(os.path.join(out, "h6_by_sponsor_size.csv"), index=False)
    H["h6_by_sponsor_size"] = rows
    H["h6_like_no_results_no_cert_n"] = int(overdue_like.sum())
    # robustness of sponsor ranks: proxy variants
    rk = []
    for nm in ["main", "strict", "broad"]:
        m = like & P[nm]
        g = d[m].groupby("sponsor").agg(n=("nct_id", "size"), p24=("sub_24m", "mean"))
        g = g[g.index.isin(big.sponsor)]
        rk.append(g.p24.rename(nm))
    rkd = pd.concat(rk, axis=1)
    rkd.to_csv(os.path.join(out, "h6_sponsor_rate_by_proxy.csv"))
    H["h6_rank_corr_main_vs_strict"] = r2(rkd["main"].corr(rkd["strict"], method="spearman"))
    H["h6_rank_corr_main_vs_broad"] = r2(rkd["main"].corr(rkd["broad"], method="spearman"))
    H["h6_max_abs_change_pp_main_vs_strict"] = r2(100 * (rkd["main"] - rkd["strict"]).abs().max())

    # ------------------------------------------------------------------ H7 other
    # QC lag (submission -> posting) by year of first submission
    pq = d.posted & d.results_first_submit_dt.notna() & pd.to_datetime(d.results_first_post, errors="coerce").notna()
    d["post_dt"] = pd.to_datetime(d.results_first_post, errors="coerce")
    d["qc_days"] = (d.post_dt - d.results_first_submit_dt).dt.days
    rows = []
    for y in range(2008, 2027):
        m = pq & d.results_first_submit_dt.dt.year.eq(y)
        pend = d.pending_qc & d.est_results_submit_dt.dt.year.eq(y)
        rows.append({"submit_year": y, "n_posted": int(m.sum()), "median_days_submit_to_post": r2(d.loc[m, "qc_days"].median()),
                     "p90_days": r2(d.loc[m, "qc_days"].quantile(0.9)), "n_still_pending": int(pend.sum())})
    qc = pd.DataFrame(rows)
    qc.to_csv(os.path.join(out, "h7_qc_lag_by_submit_year.csv"), index=False)
    H["h7_qc"] = qc.to_dict("records")
    pend = d.pending_qc
    H["h7_pending_total"] = int(pend.sum())
    H["h7_pending_median_days_waiting"] = r2((T - d.loc[pend, "est_results_submit_dt"]).dt.days.median())
    H["h7_pending_over_1yr"] = int((pend & ((T - d.est_results_submit_dt).dt.days > 365)).sum())
    H["h7_pending_with_resets"] = int((pend & d.n_resets.gt(0)).sum())
    H["h7_pending_int"] = int((pend & d.is_int).sum())
    old = pend & ((T - d.est_results_submit_dt).dt.days > 365)
    H["h7_pending_over_1yr_with_resets_pct"] = r2(100 * (old & d.n_resets.gt(0)).sum() / old.sum())
    H["h7_pending_in_main_due"] = int((pend & due & P["main"]).sum())
    # comparison window of DeVito et al. (Lancet 2020): due Mar 2018 - Sep 2019 -> PCD Mar 2017 - Sep 2018
    dv = due & P["main"] & (d.pcd_dt >= pd.Timestamp("2017-03-01")) & (d.pcd_dt <= pd.Timestamp("2018-09-16"))
    H["h7_devito_window_main"] = {"n": int(dv.sum()), "sub12": rate(dv, d.sub_12m), "sub12_or_cert": rate(dv, d.sub12_or_cert),
                                  "ever": rate(dv, d.submitted),
                                  "by_sponsor_sub12": {g: rate(dv & d.sponsor_group.eq(g), d.sub_12m)
                                                       for g in ["Industry", "NIH", "Other US federal", "Universities, hospitals & non-profits"]}}
    # FDA notices of non-compliance shown on the registry
    v = d.fdaaa801_violation.eq(True)
    H["h7_fda_violation_flag_n"] = int(v.sum())
    H["h7_fda_violation_types"] = d.loc[v, "violation_types"].value_counts().to_dict()
    H["h7_fda_violation_sponsor_class"] = d.loc[v, "sponsor_class"].value_counts().to_dict()
    H["h7_main_due_not_submitted_no_cert"] = int((due & P["main"] & ~d.submitted & d.disp_first_submit_dt.isna()).sum())
    # terminated vs completed within like cohort, main proxy
    H["h7_main_like_completed_sub24"] = rate(L & d.overall_status.eq("COMPLETED"), d.sub_24m)
    H["h7_main_like_terminated_sub24"] = rate(L & d.overall_status.eq("TERMINATED"), d.sub_24m)
    # enrolment size
    rows = []
    bins = [-1, 0, 20, 50, 100, 300, 1000, 1e9]
    labs = ["0", "1-20", "21-50", "51-100", "101-300", "301-1000", ">1000"]
    d["enroll_bin"] = pd.cut(d.enroll_count, bins, labels=labs)
    for g in labs:
        m = L & d.enroll_bin.eq(g)
        rows.append({"enrolment": g, **rate(m, d.sub_24m)})
    pd.DataFrame(rows).to_csv(os.path.join(out, "h7_by_enrolment.csv"), index=False)
    H["h7_by_enrolment"] = rows
    # certification usage
    H["h7_main_like_cert_by_sponsor"] = {g: rate(L & d.sponsor_group.eq(g), d.cert_before_deadline)["pct"]
                                         for g in ["Industry", "NIH", "Universities, hospitals & non-profits"]}
    # of certified trials in like cohort, share submitted by now
    H["h7_main_like_certified_submitted_ever"] = rate(L & d.cert_before_deadline, d.submitted)
    # main-proxy due cohort with no submission and no certification: by sponsor group
    nn = due & P["main"] & ~d.submitted & d.disp_first_submit_dt.isna()
    H["h7_overdue_by_sponsor"] = d.loc[nn, "sponsor_group"].value_counts().to_dict()

    # ------------------------------------------------------------------ Robustness grid
    rob = []
    def addrob(claim, variant, m, outcome):
        r = rate(m, outcome)
        rob.append({"claim": claim, "variant": variant, **r})
    # Headline variants
    addrob("Headline: completed interventional with results", "Main: COMPLETED, PCD 2008-2023, submitted", win, d.submitted)
    addrob("Headline: completed interventional with results", "Posted only (excludes QC queue)", win, d.posted)
    addrob("Headline: completed interventional with results", "All completed, any PCD year", comp, d.submitted)
    addrob("Headline: completed interventional with results", "PCD type ACTUAL only", win & d.pcd_type.eq("ACTUAL"), d.submitted)
    addrob("Headline: completed interventional with results", "Study completion date 2008-2023 instead of PCD", comp & d.cd_year.between(2008, 2023), d.submitted)
    addrob("Headline: completed interventional with results", "PCD 2010-2020", comp & d.pcd_year.between(2010, 2020), d.submitted)
    addrob("Headline: completed interventional with results", "PCD 2017-2023", comp & d.pcd_year.between(2017, 2023), d.submitted)
    addrob("Headline: completed interventional with results", "Completed + terminated, PCD 2008-2023",
           INT & d.overall_status.isin(["COMPLETED", "TERMINATED"]) & d.pcd_year.between(2008, 2023), d.submitted)
    addrob("Headline: completed interventional with results", "All trials past PCD by 2y incl. unknown/stale (PCD 2008-2023)",
           ended & d.pcd_year.between(2008, 2023), d.submitted)
    # Proxy variants
    for nm in ["main", "strict", "broad", "noloc"]:
        addrob("Probably required: submitted within 24 months (PCD 2017-01-18 to 2024-11-20)", nm, like & P[nm], d.sub_24m)
        addrob("Probably required: submitted within 12 months", nm, like & P[nm], d.sub_12m)
        addrob("Everything else: submitted within 24 months", nm, like & ~P[nm], d.sub_24m)
    addrob("Probably required: submitted within 24 months (PCD 2017-01-18 to 2024-11-20)", "main + stale-status trials", L2, d.sub_24m)
    addrob("Probably required: submitted within 12 months", "main, 13-month slack", like & P["main"], d.submitted & (d.days_to_submit <= 395))
    addrob("Probably required: submitted within 12 months", "main, unposted submissions counted as not submitted", like & P["main"], d.sub_12m & d.posted)
    addrob("Probably required: submitted within 24 months (PCD 2017-01-18 to 2024-11-20)", "main, unposted submissions counted as not submitted", like & P["main"], d.sub_24m & d.posted)
    addrob("Everything else: submitted within 24 months", "main, unposted submissions counted as not submitted", like & ~P["main"], d.sub_24m & d.posted)
    addrob("Probably required: submitted within 12 months", "main, 12m or certification filed in time", like & P["main"], d.sub_12m | d.cert_before_deadline)
    addrob("Probably required: submitted within 12 months", "main, completed status only", like & P["main"] & d.overall_status.eq("COMPLETED"), d.sub_12m)
    addrob("Probably required: submitted within 12 months", "main, PCD 2019-2023 only", like & P["main"] & d.pcd_year.between(2019, 2023), d.sub_12m)
    # month-only date convention
    d2 = derive(raw, how="start"); P2 = proxies(d2)
    like2 = P2["base"] & d2.pcd_type.eq("ACTUAL") & (d2.pcd_dt >= RULE) & (d2.pcd_dt <= like_cut)
    r = rate(like2 & P2["main"], d2.sub_12m)
    rob.append({"claim": "Probably required: submitted within 12 months", "variant": "main, month-only dates = first of month", **r})
    r = rate(P2["base"] & d2.overall_status.eq("COMPLETED") & d2.pcd_year.between(2008, 2023), d2.submitted)
    rob.append({"claim": "Headline: completed interventional with results", "variant": "Month-only dates = first of month", **r})
    pd.DataFrame(rob).to_csv(os.path.join(out, "robustness_grid.csv"), index=False)
    H["robustness"] = rob

    # ------------------------------------------------------------------ compact per-trial file for re-verification
    keep = ["nct_id", "study_type", "overall_status", "phases", "primary_purpose", "sponsor_class", "pcd", "pcd_type", "cd", "cd_type",
            "start_date", "results_first_submit", "est_results_submit", "results_first_post", "disp_first_submit", "has_results",
            "fda_drug", "fda_device", "us_export", "has_us_site", "has_nonus_site", "intervention_types", "last_update_submit",
            "last_known_status", "enroll_count"]
    small = raw.loc[d.is_int, keep].copy()
    small["proxy_main"] = P["main"][d.is_int].values
    for c in ["study_type", "overall_status", "phases", "primary_purpose", "sponsor_class", "pcd_type", "cd_type", "intervention_types", "last_known_status"]:
        small[c] = small[c].astype("category")
    small.to_parquet(os.path.join(out, "interventional_trials.parquet"), index=False, compression="zstd")
    # sponsor names only for the probably-required like cohort (for H6 re-verification)
    d.loc[L, ["nct_id", "sponsor"]].to_csv(os.path.join(out, "probably_required_like_cohort_sponsors.csv"), index=False)

    with open(os.path.join(out, "headline_numbers.json"), "w") as f:
        json.dump(H, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({k: H[k] for k in ["h1_completed_int_pcd2008_2023_submitted", "h2_like_cohort_n"]}, default=str))


if __name__ == "__main__":
    main()
