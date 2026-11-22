"""Robustness grid: does each headline survive alternative choices?

Usage:
    python3 -I robustness.py BULLETIN_A_CSV DATA_DIR

For every combination of (window, metric, year set, exclusions) it computes
  (a) 2026 minus the average of 2016-2025 (and of 2018-2025)
  (b) 2022-26 average minus 2016-20 average
  (c) rank of 2026 among the years (1 = worst)
with 95% moving-block bootstrap intervals, and writes DATA_DIR/robustness_grid.csv.
"""
import os
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)
NB = 3000


def block_boot(x, stat, block=7):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    b = min(block, n)
    k = int(np.ceil(n / b))
    st = RNG.integers(0, n - b + 1, size=(NB, k))
    idx = (st[:, :, None] + np.arange(b)[None, None, :]).reshape(NB, -1)[:, :n]
    return stat(x[idx])


METRICS = {
    "mean AQI": (lambda v: np.nanmean(v), lambda m: m.mean(axis=1)),
    "median AQI": (lambda v: np.nanmedian(v), lambda m: np.median(m, axis=1)),
    "share of days Very Poor+ (>300)": (lambda v: np.nanmean(v > 300), lambda m: (m > 300).mean(axis=1)),
    "share of days Severe (>400)": (lambda v: np.nanmean(v > 400), lambda m: (m > 400).mean(axis=1)),
    "share of days Poor+ (>200)": (lambda v: np.nanmean(v > 200), lambda m: (m > 200).mean(axis=1)),
    "90th percentile day": (lambda v: np.nanpercentile(v, 90), lambda m: np.percentile(m, 90, axis=1)),
}
WINDOWS = {
    "Oct 1-Nov 20": ((10, 1), (11, 20)),
    "Nov 1-20": ((11, 1), (11, 20)),
    "Oct 15-Nov 15": ((10, 15), (11, 15)),
    "Oct 1-31": ((10, 1), (10, 31)),
    "Nov 1-15": ((11, 1), (11, 15)),
}


def main():
    bull, data = sys.argv[1], sys.argv[2]
    b = pd.read_csv(bull, parse_dates=["date"])
    b = b[(b.header_date.isna()) | (b.header_date == b.file_date)]
    dw = pd.read_csv(os.path.join(data, "diwali_dates.csv"), parse_dates=["diwali"])
    dwd = {int(r.year): r.diwali for _, r in dw.iterrows()}
    rows = []
    for city in ["Delhi", "NCR-5 average"]:
        if city == "Delhi":
            s = b[b.city == "Delhi"].set_index("date").aqi
        else:
            p = b[b.city.isin(["Delhi", "Gurugram", "Noida", "Ghaziabad", "Faridabad"])].pivot(index="date", columns="city", values="aqi")
            p = p[p.notna().sum(axis=1) == 5]  # only days when all five cities published
            s = p.mean(axis=1)
        s = s.sort_index()
        for wn, ((m0, d0), (m1, d1)) in WINDOWS.items():
            for excl in ["none", "drop Diwali night +2 days"]:
                def series(y):
                    x = s.loc[pd.Timestamp(y, m0, d0):pd.Timestamp(y, m1, d1)]
                    if excl != "none":
                        dv = dwd[y]
                        x = x.drop([dv + pd.Timedelta(days=k) for k in (1, 2, 3)], errors="ignore")
                    return x.values
                for mname, (f, fb) in METRICS.items():
                    vals = {y: series(y) for y in range(2016, 2027)}
                    vals = {y: v for y, v in vals.items() if len(v) >= 0.6 * ((pd.Timestamp(y, m1, d1) - pd.Timestamp(y, m0, d0)).days + 1)}
                    if 2026 not in vals:
                        continue
                    pt = {y: f(v) for y, v in vals.items()}
                    boots = {y: block_boot(v, fb) for y, v in vals.items()}
                    for base_name, base_years in [("2016-2025", range(2016, 2026)), ("2018-2025 (36-station era)", range(2018, 2026)),
                                                  ("2016-2025 without 2020", [y for y in range(2016, 2026) if y != 2020])]:
                        by = [y for y in base_years if y in vals]
                        diff = pt[2026] - np.mean([pt[y] for y in by])
                        bd = boots[2026] - np.mean([boots[y] for y in by], axis=0)
                        order = sorted([y for y in vals if y in by or y == 2026], key=lambda k: -pt[k])
                        rows.append(dict(city=city, window=wn, exclusion=excl, metric=mname, comparison=f"2026 vs mean of {base_name}",
                                         value_2026=pt[2026], value_base=float(np.mean([pt[y] for y in by])), diff=diff,
                                         ci_lo=float(np.percentile(bd, 2.5)), ci_hi=float(np.percentile(bd, 97.5)),
                                         rank_2026_worst_first=order.index(2026) + 1, n_years=len(order)))
                    A = [y for y in range(2016, 2021) if y in vals]
                    B = [y for y in range(2022, 2027) if y in vals]
                    if len(A) >= 4 and len(B) >= 4:
                        diff = np.mean([pt[y] for y in B]) - np.mean([pt[y] for y in A])
                        bd = np.mean([boots[y] for y in B], axis=0) - np.mean([boots[y] for y in A], axis=0)
                        rows.append(dict(city=city, window=wn, exclusion=excl, metric=mname, comparison="2022-26 mean vs 2016-20 mean",
                                         value_2026=np.mean([pt[y] for y in B]), value_base=np.mean([pt[y] for y in A]), diff=diff,
                                         ci_lo=float(np.percentile(bd, 2.5)), ci_hi=float(np.percentile(bd, 97.5)),
                                         rank_2026_worst_first=np.nan, n_years=len(A) + len(B)))
    G = pd.DataFrame(rows)
    G["direction"] = np.where(G.ci_hi < 0, "lower (clear)", np.where(G.ci_lo > 0, "higher (clear)", "no clear difference"))
    G.to_csv(os.path.join(data, "robustness_grid.csv"), index=False, float_format="%.4f")
    print(G.groupby(["comparison", "direction"]).size())


if __name__ == "__main__":
    main()
