"""Independent recomputation of every headline number.

Path 2 deliberately shares no code with analysis.py:
  - bulletin values come from the pdfplumber table parse (method B), not the pdftotext parse (method A)
  - aggregation uses only the Python standard library (csv, statistics, datetime), no pandas/numpy
  - FIRMS totals are recounted from the raw yearly CSVs with the csv module
  - CREAMS totals are re-read with pdfplumber instead of pdftotext

Usage:
    python3 -I verify.py BULLETIN_A_CSV BULLETIN_B_CSV RAW_DIR DATA_DIR

Prints a PASS/FAIL table and writes DATA_DIR/verification.csv.
"""
import csv
import datetime as dt
import json
import os
import re
import statistics as st
import sys


def load(path):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["header_date"] and r["header_date"] != r["file_date"]:
                continue
            a = int(r["aqi"])
            if not 0 <= a <= 500:
                continue
            out[(r["file_date"], r["city"])] = (a, int(r["n_part"]) if r["n_part"] else None)
    return out


def days(y0, m0, d0, y1, m1, d1):
    d = dt.date(y0, m0, d0)
    e = dt.date(y1, m1, d1)
    while d <= e:
        yield d.isoformat()
        d += dt.timedelta(days=1)


def vals(B, city, rng):
    return [B[(d, city)][0] for d in rng if (d, city) in B]


def main():
    a_csv, b_csv, raw, data = sys.argv[1:5]
    A = load(a_csv)
    B = load(b_csv)
    R = json.load(open(os.path.join(data, "results.json")))
    checks = []

    def chk(name, v_main, v_ind, tol=0.01):
        ok = (v_main is None and v_ind is None) or (v_main is not None and v_ind is not None and abs(v_main - v_ind) <= tol)
        checks.append((name, v_main, v_ind, "PASS" if ok else "FAIL"))

    # row-level agreement between the two extraction paths
    common = set(A) & set(B)
    agree_aqi = sum(1 for k in common if A[k][0] == B[k][0])
    agree_st = sum(1 for k in common if A[k][1] == B[k][1])
    onlyA = sorted(set(A) - set(B))
    onlyB = sorted(set(B) - set(A))
    print(f"rows A={len(A)} B={len(B)} common={len(common)} aqi_agree={agree_aqi} stations_agree={agree_st}")
    print("only in A (first 10):", onlyA[:10], len(onlyA))
    print("only in B (first 10):", onlyB[:10], len(onlyB))
    dis = [(k, A[k], B[k]) for k in sorted(common) if A[k] != B[k]]
    print("disagreements (first 10):", dis[:10], len(dis))

    for y in range(2015, 2027):
        x = vals(B, "Delhi", days(y, 10, 1, y, 11, 20))
        r = R["delhi_oct1_nov20"].get(str(y), {})
        if x:
            chk(f"Delhi Oct1-Nov20 {y} mean", r.get("mean"), st.mean(x))
            chk(f"Delhi Oct1-Nov20 {y} days>300", r.get("days_vpoor_or_worse"), sum(v > 300 for v in x), 0)
            chk(f"Delhi Oct1-Nov20 {y} days>400", r.get("days_severe"), sum(v > 400 for v in x), 0)
            chk(f"Delhi Oct1-Nov20 {y} n days", r.get("n_days_data"), len(x), 0)
        x = vals(B, "Delhi", days(y, 11, 1, y, 11, 20))
        r = R["delhi_nov1_20"].get(str(y), {})
        if x:
            chk(f"Delhi Nov1-20 {y} mean", r.get("mean"), st.mean(x))
            chk(f"Delhi Nov1-20 {y} days>300", r.get("days_vpoor_or_worse"), sum(v > 300 for v in x), 0)
        if y <= 2025:
            x = vals(B, "Delhi", days(y, 10, 1, y + 1, 1, 31))
            r = R["delhi_oct_jan"].get(str(y), {})
            if x:
                chk(f"Delhi Oct-Jan {y}-{y+1} mean", r.get("mean"), st.mean(x))
                chk(f"Delhi Oct-Jan {y}-{y+1} days>300", r.get("days_vpoor_or_worse"), sum(v > 300 for v in x), 0)
        if 2016 <= y <= 2025:
            x = vals(B, "Delhi", days(y, 1, 1, y, 12, 31))
            r = R["delhi_calendar_year"].get(str(y), {})
            chk(f"Delhi calendar {y} mean", r.get("mean"), st.mean(x))
        stn = [B[(d, "Delhi")][1] for d in days(y, 1, 1, y, 12, 31) if (d, "Delhi") in B and B[(d, "Delhi")][1] is not None]
        if stn:
            chk(f"Delhi stations median {y}", R["delhi_stations_by_year"][str(y)]["median"], st.median(stn))

    # block comparison 2016-20 vs 2022-26
    for wn, (m0, d0, m1, d1) in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20))]:
        mA = st.mean([st.mean(vals(B, "Delhi", days(y, m0, d0, y, m1, d1))) for y in range(2016, 2021)])
        mB = st.mean([st.mean(vals(B, "Delhi", days(y, m0, d0, y, m1, d1))) for y in range(2022, 2027)])
        r = R[f"delhi_2016_20_vs_2022_26_{wn}"]
        chk(f"Delhi {wn} mean 2016-20", r["mean_2016_20"], mA)
        chk(f"Delhi {wn} mean 2022-26", r["mean_2022_26"], mB)
        base = st.mean([st.mean(vals(B, "Delhi", days(y, m0, d0, y, m1, d1))) for y in range(2016, 2026)])
        chk(f"Delhi {wn} mean of 2016-2025", R[f"delhi_2026_vs_2016_2025_{wn}"]["mean_base"], base)

    for row in R["ncr_2026"]:
        c, wn = row["city"], row["window"]
        m0, d0, m1, d1 = (10, 1, 11, 20) if wn == "oct1_nov20" else (11, 1, 11, 20)
        x26 = vals(B, c, days(2026, m0, d0, 2026, m1, d1))
        x25 = vals(B, c, days(2025, m0, d0, 2025, m1, d1))
        if x26:
            chk(f"{c} {wn} 2026 mean", row["mean_2026"], st.mean(x26))
        if x25:
            chk(f"{c} {wn} 2025 mean", row["mean_2025"], st.mean(x25))

    # FIRMS box totals, recounted from raw CSVs with the csv module
    for fy in R["firms_by_year"]:
        y = int(fy["year"])
        n = 0
        with open(os.path.join(raw, "firms", f"modis_{y}_India.csv")) as f:
            for r in csv.DictReader(f):
                if r["type"] != "0":
                    continue
                la, lo = float(r["latitude"]), float(r["longitude"])
                if 29.0 <= la <= 32.5 and 73.8 <= lo <= 77.5:
                    dd = r["acq_date"]
                    # analysis sums fires on d-1 and d-2? no: the box total is the plain Oct1-Nov20 count
                    if f"{y}-10-01" <= dd <= f"{y}-11-20":
                        n += 1
        chk(f"FIRMS box Oct1-Nov20 {y}", fy["firms_box_oct1_nov20"], n, 0)

    # CREAMS via pdfplumber
    import pdfplumber
    for rec in R["fires_vs_delhi"]:
        y = int(rec["year"])
        with pdfplumber.open(os.path.join(raw, "creams", f"creams_20Nov_{y}.pdf")) as p:
            txt = " ".join((p.pages[i].extract_text() or "") for i in range(min(3, len(p.pages))))
        txt = re.sub(r"\s+", " ", txt)
        m = re.search(r"distributed as ([\d ,and]+?) in Punjab", txt)
        if m:
            nums = [int(v) for v in re.findall(r"\d+", m.group(1))]
            chk(f"CREAMS {y} Punjab", rec["Punjab"], nums[0], 0)
            chk(f"CREAMS {y} Haryana", rec["Haryana"], nums[1], 0)
        else:
            checks.append((f"CREAMS {y}", rec["Punjab"], None, "FAIL"))


    # trend slopes (stdlib linear regression on path-B yearly means)
    def ymean(city, y, m0, d0, m1, d1):
        v = vals(B, city, days(y, m0, d0, y, m1, d1))
        return st.mean(v)
    for key, (y0, y1), (m0, d0, m1, d1) in [("delhi_trend_oct1_nov20_2016_2026", (2016, 2026), (10, 1, 11, 20)),
                                             ("delhi_trend_nov1_20_2016_2026", (2016, 2026), (11, 1, 11, 20)),
                                             ("delhi_trend_oct1_nov20_2018_2026", (2018, 2026), (10, 1, 11, 20)),
                                             ("delhi_trend_oct1_nov20_stable_network_2019_2025", (2019, 2025), (10, 1, 11, 20)),
                                             ("delhi_trend_nov1_20_stable_network_2019_2025", (2019, 2025), (11, 1, 11, 20)),
                                             ("delhi_trend_calendar_stable_network_2019_2025", (2019, 2025), (1, 1, 12, 31))]:
        ys = list(range(y0, y1 + 1))
        slope = st.linear_regression(ys, [ymean("Delhi", y, m0, d0, m1, d1) for y in ys]).slope
        chk(f"slope {key}", R[key]["slope_per_year"], slope)

    # 2026 vs 2025 change by city (point estimates) and zero Severe days in 2026
    for r in R["yoy_2026"]:
        m0, d0, m1, d1 = {"oct1_nov20": (10, 1, 11, 20), "nov1_20": (11, 1, 11, 20), "oct14_nov20": (10, 14, 11, 20)}[r["window"]]
        pc = ymean(r["city"], 2026, m0, d0, m1, d1) / ymean(r["city"], 2025, m0, d0, m1, d1) - 1
        chk(f"yoy {r['city']} {r['window']}", r["pct_change"], pc, 0.0005)
    for c in ["Delhi", "Gurugram", "Noida", "Ghaziabad", "Faridabad", "Greater Noida"]:
        v = vals(B, c, days(2026, 10, 1, 2026, 11, 20))
        chk(f"{c} 2026 Oct1-Nov20 days>400", 0, sum(x > 400 for x in v), 0)
    allDelhi = [v[0] for k, v in B.items() if k[1] == "Delhi"]
    chk("Delhi archive max", max(R["delhi_max_by_year"].values()), max(allDelhi), 0)
    chk("Delhi days at 500", R["delhi_days_at_500"], sum(x >= 500 for x in allDelhi), 0)

    # weather model share, refitted with statsmodels (different fitting code, same model dataset)
    try:
        import pandas as pd
        import statsmodels.formula.api as smf
        D = pd.read_csv(os.path.join(data, "model_dataset_oct1_nov20.csv"))
        cols = ["lnws", "rain_today", "rain_prev", "T2M_MIN", "dtr", "RH2M", "nw_wind", "diwali1", "diwali2"]
        D = D.dropna(subset=["y"] + cols)
        f = smf.ols("y ~ " + " + ".join(cols) + " + C(week) + C(year)", data=D).fit()
        yrs = sorted(D.year.unique())
        fe = [0.0] + [f.params[f"C(year)[T.{y}]"] for y in yrs[1:]]
        raw_ = D.groupby("year").y.mean().reindex(yrs).values
        mfe = sum(fe) / len(fe); mraw = raw_.mean()
        share = 1 - (sum((x - mfe) ** 2 for x in fe) / len(fe)) / (((raw_ - mraw) ** 2).mean())
        chk("weather share (statsmodels refit)", R["models"]["weather"]["share_between_year_variance_removed"], share, 0.001)
        chk("weather coef lnws (statsmodels)", R["models"]["weather"]["coef"]["lnws"], f.params["lnws"], 0.001)
        adj26 = __import__("math").exp(fe[-1] - mfe)
        chk("weather-adjusted 2026 index (statsmodels)", R["models"]["weather"]["years"]["2026"]["adjusted_index"], adj26, 0.001)
    except Exception as e:
        checks.append(("statsmodels refit", None, str(e), "FAIL"))

    with open(os.path.join(data, "verification.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["check", "analysis_value", "independent_value", "result"])
        w.writerows(checks)
    npass = sum(c[3] == "PASS" for c in checks)
    print(f"{npass}/{len(checks)} checks PASS")
    for c in checks:
        if c[3] != "PASS":
            print("FAIL", c)


if __name__ == "__main__":
    main()
