"""Shared definitions for the main analysis path (03_analysis.py, 04_charts.py).
The verification path (05_verify.py) deliberately does NOT import this file."""
import numpy as np
import pandas as pd
from scipy import stats

T = pd.Timestamp("2026-11-20")          # API dataTimestamp 2026-11-20T10:00:05
RULE = pd.Timestamp("2017-01-18")       # 42 CFR Part 11 effective date
OPEN = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "SUSPENDED"}
PRODUCT_TYPES = {"DRUG", "BIOLOGICAL", "DEVICE", "GENETIC", "COMBINATION_PRODUCT", "RADIATION", "DIAGNOSTIC_TEST"}
SPONSOR_GROUP = {"INDUSTRY": "Industry", "NIH": "NIH", "FED": "Other US federal", "OTHER": "Universities, hospitals & non-profits",
                 "OTHER_GOV": "Non-US government", "NETWORK": "Networks", "INDIV": "Individuals"}


def pdate(s, how="end"):
    """Parse CT.gov dates. 'YYYY-MM' -> last day of month (how='end') or first day (how='start')."""
    s = s.astype("string")
    full = pd.to_datetime(s.where(s.str.len() == 10), errors="coerce", format="%Y-%m-%d")
    mon = pd.to_datetime(s.where(s.str.len() == 7) + "-01", errors="coerce", format="%Y-%m-%d")
    if how == "end":
        mon = mon + pd.offsets.MonthEnd(0)
    return full.fillna(mon)


def phase_group(p):
    return {"EARLY_PHASE1": "Phase 1", "PHASE1": "Phase 1", "PHASE1|PHASE2": "Phase 1/2", "PHASE2": "Phase 2",
            "PHASE2|PHASE3": "Phase 2/3", "PHASE3": "Phase 3", "PHASE4": "Phase 4", "NA": "Not applicable"}.get(p, "Missing")


def derive(df, how="end"):
    d = df.copy()
    for c in ["pcd", "cd", "start_date"]:
        d[c + "_dt"] = pdate(d[c], how)
    for c in ["results_first_submit", "est_results_submit", "results_first_post", "disp_first_submit",
              "first_submit", "last_update_submit"]:
        d[c + "_dt"] = pdate(d[c], "start")
    d["submit_dt"] = d.results_first_submit_dt.fillna(d.est_results_submit_dt)
    d["submitted"] = d.submit_dt.notna()
    d["posted"] = d.has_results.fillna(False).astype(bool)
    d["pending_qc"] = d.est_results_submit_dt.notna() & ~d.posted
    d["days_to_submit"] = (d.submit_dt - d.pcd_dt).dt.days
    d["days_since_pcd"] = (T - d.pcd_dt).dt.days
    d["pcd_year"] = d.pcd_dt.dt.year
    d["cd_year"] = d.cd_dt.dt.year
    d["phase_group"] = d.phases.fillna("").map(phase_group)
    it = d.intervention_types.fillna("")
    d["product_type"] = it.map(lambda x: bool(set(x.split("|")) & PRODUCT_TYPES))
    d["sponsor_group"] = d.sponsor_class.map(SPONSOR_GROUP).fillna("Unknown")
    d["is_int"] = d.study_type.eq("INTERVENTIONAL")
    d["fda_any"] = d.fda_drug.eq(True) | d.fda_device.eq(True)
    d["fda_missing"] = d.fda_drug.isna() & d.fda_device.isna()
    d["phase1_only"] = d.phases.isin(["PHASE1", "EARLY_PHASE1"])
    d["feasibility"] = d.primary_purpose.eq("DEVICE_FEASIBILITY") & ~d.fda_drug.eq(True)
    d["us_or_export"] = d.has_us_site | d.us_export.eq(True)
    d["product"] = np.select([d.fda_drug.eq(True) & d.fda_device.eq(True), d.fda_drug.eq(True), d.fda_device.eq(True)],
                             ["Drug and device", "Drug", "Device"], "Neither flagged")
    for m in (12, 24, 36):
        days = {12: 365, 24: 730, 36: 1095}[m]
        d[f"sub_{m}m"] = d.submitted & (d.days_to_submit <= days)
    # certification / extension filed before the 12-month deadline
    d["cert_before_deadline"] = d.disp_first_submit_dt.notna() & ((d.disp_first_submit_dt - d.pcd_dt).dt.days <= 365)
    d["sub12_or_cert"] = d.sub_12m | d.cert_before_deadline
    return d


def proxies(d):
    """'Probably required to report' proxies, built only from registry fields. Not a legal determination."""
    base = d.is_int & ~d.overall_status.isin(["WITHDRAWN", "WITHHELD"])
    main = base & d.fda_any & ~d.phase1_only & ~d.feasibility & d.us_or_export
    strict = main & d.has_us_site & (d.start_date_dt >= RULE) & d.phases.isin(
        ["PHASE1|PHASE2", "PHASE2", "PHASE2|PHASE3", "PHASE3", "PHASE4", "NA"])
    broad = base & ~d.phase1_only & ~d.feasibility & d.us_or_export & (d.fda_any | (d.fda_missing & d.product_type))
    noloc = base & d.fda_any & ~d.phase1_only & ~d.feasibility
    lite = base & d.product_type & ~d.phase1_only & ~d.primary_purpose.eq("DEVICE_FEASIBILITY") & d.has_us_site
    return {"main": main, "strict": strict, "broad": broad, "noloc": noloc, "lite": lite, "base": base}


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, c - h, c + h)


def newcombe(k1, n1, k2, n2):
    """Difference p1-p2 with Newcombe hybrid score interval."""
    p1, l1, u1 = wilson(k1, n1)
    p2, l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d, d - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def rate(mask_n, mask_k):
    n = int(mask_n.sum()); k = int((mask_n & mask_k).sum())
    p, lo, hi = wilson(k, n)
    return {"n": n, "k": k, "pct": round(100 * p, 2) if n else None,
            "lo": round(100 * lo, 2) if n else None, "hi": round(100 * hi, 2) if n else None}
