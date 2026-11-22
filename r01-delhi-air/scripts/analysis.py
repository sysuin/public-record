"""Main analysis for R01 "Is Delhi NCR's air actually getting worse?"

Usage:
    python3 -I analysis.py BULLETIN_CSV DATA_DIR

BULLETIN_CSV : output of parse_bulletins.py (method A, pdftotext path)
DATA_DIR     : report data/ folder (reads the aux CSVs written by prep_aux.py, writes derived CSVs
               and results.json with every headline number)

All bootstrap intervals are 95% moving-block bootstrap intervals (7-day blocks, resampled within
each year's window), because consecutive days of air quality are not independent.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261121)
NBOOT = 4000
BLOCK = 7
CITIES = ["Delhi", "Gurugram", "Noida", "Ghaziabad", "Faridabad", "Greater Noida"]
BANDS = [(0, 50, "Good"), (51, 100, "Satisfactory"), (101, 200, "Moderate"), (201, 300, "Poor"),
         (301, 400, "Very Poor"), (401, 500, "Severe")]
RES = {}
EXCL = []


def band(a):
    for lo, hi, n in BANDS:
        if lo <= a <= hi:
            return n
    return "out-of-range"


# ----------------------------------------------------------------------------------- bootstrap
def block_boot(x, stat, nboot=NBOOT, block=BLOCK, rng=RNG):
    """Moving-block bootstrap of a 1-D series (NaNs dropped). Returns array of stat over replicates."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return np.full(nboot, np.nan)
    b = min(block, n)
    nblocks = int(np.ceil(n / b))
    starts = rng.integers(0, n - b + 1, size=(nboot, nblocks))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(nboot, -1)[:, :n]
    return stat(x[idx])


def ci(a):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return [np.nan, np.nan]
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def mean_rows(m):
    return m.mean(axis=1)


def share_above(th):
    return lambda m: (m > th).mean(axis=1)


# ----------------------------------------------------------------------------------- load
def load(bull_csv, data_dir):
    b = pd.read_csv(bull_csv, parse_dates=["date"])
    n0 = len(b)
    bad_hdr = b[(b.header_date.notna()) & (b.header_date != b.file_date)]
    for _, r in bad_hdr.iterrows():
        EXCL.append(dict(item=f"{r.city} {r.file_date}", rule="bulletin header date differs from file date",
                         detail=f"header says {r.header_date}", action="dropped"))
    b = b.drop(bad_hdr.index)
    no_hdr = b[b.header_date.isna()]
    for d in sorted(no_hdr.file_date.unique()):
        EXCL.append(dict(item=f"all cities {d}", rule="header date unreadable", detail="kept: file name date used",
                         action="kept"))
    b["band_calc"] = b.aqi.apply(band)
    mis = b[b.band_calc != b.category]
    for _, r in mis.iterrows():
        EXCL.append(dict(item=f"{r.city} {r.file_date}", rule="printed category disagrees with printed AQI value",
                         detail=f"AQI {r.aqi} printed as {r.category}", action="kept (AQI value used)"))
    oor = b[(b.aqi < 0) | (b.aqi > 500)]
    for _, r in oor.iterrows():
        EXCL.append(dict(item=f"{r.city} {r.file_date}", rule="AQI outside 0-500", detail=str(r.aqi), action="dropped"))
    b = b.drop(oor.index)
    RES["rows_parsed"] = int(n0)
    RES["rows_used"] = int(len(b))
    w = pd.read_csv(os.path.join(data_dir, "weather_delhi_daily.csv"), parse_dates=["date"]).set_index("date")
    f = pd.read_csv(os.path.join(data_dir, "fires_firms_daily.csv"), parse_dates=["date"]).set_index("date")
    cr = pd.read_csv(os.path.join(data_dir, "fires_creams_20nov.csv"))
    dw = pd.read_csv(os.path.join(data_dir, "diwali_dates.csv"), parse_dates=["diwali"])
    return b, w, f, cr, dw


def city_series(b, city):
    s = b[b.city == city].set_index("date").sort_index()
    full = pd.date_range("2015-04-01", "2026-11-21", freq="D")
    return s.reindex(full)


def window(s, y, m0, d0, m1, d1, y1=None):
    y1 = y if y1 is None else y1
    return s.loc[pd.Timestamp(y, m0, d0):pd.Timestamp(y1, m1, d1)]


# ----------------------------------------------------------------------------------- summaries
def summarise(x, ndays):
    x = np.asarray(x, float)
    v = x[~np.isnan(x)]
    out = dict(n_days_window=int(ndays), n_days_data=int(len(v)), coverage=float(len(v) / ndays) if ndays else np.nan)
    if len(v) == 0:
        return out
    out["mean"] = float(v.mean())
    out["median"] = float(np.median(v))
    out["mean_ci"] = ci(block_boot(v, mean_rows))
    for th, nm in [(400, "severe"), (300, "vpoor_or_worse"), (200, "poor_or_worse"), (100, "above_100")]:
        out[f"days_{nm}"] = int((v > th).sum())
        sh = (v > th).mean()
        out[f"share_{nm}"] = float(sh)
        out[f"share_{nm}_ci"] = ci(block_boot(v, share_above(th)))
    out["days_450plus"] = int((v >= 450).sum())
    out["max"] = float(v.max())
    return out


def diff_boot(x, y, stat=mean_rows):
    """Unpaired: each window resampled on its own. Conservative, because resampling blocks inside a window
    that rises steeply from October into November mixes early and late days."""
    bx = block_boot(x, stat)
    by = block_boot(y, stat)
    return bx - by


def paired_boot(x, y, ratio=False):
    """Paired by calendar day: same date in both years, resample 7-day blocks of dates.
    Removes the shared seasonal ramp. Returns replicate differences (or ratios - 1)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    ok = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[ok], y[ok]
    m = len(x)
    b = min(BLOCK, m)
    k = int(np.ceil(m / b))
    st = RNG.integers(0, m - b + 1, size=(NBOOT, k))
    idx = (st[:, :, None] + np.arange(b)[None, None, :]).reshape(NBOOT, -1)[:, :m]
    if ratio:
        return x[idx].mean(axis=1) / y[idx].mean(axis=1) - 1
    return x[idx].mean(axis=1) - y[idx].mean(axis=1)


def main():
    bull_csv, data_dir = sys.argv[1], sys.argv[2]
    b, w, f, cr, dw = load(bull_csv, data_dir)
    S = {c: city_series(b, c) for c in CITIES}
    dl = S["Delhi"]

    # ---------------- coverage of the bulletin archive
    files = pd.read_csv(bull_csv.replace(".csv", "_files.csv"), parse_dates=["file_date"])
    allDays = pd.date_range("2015-04-01", "2026-11-21", freq="D")
    have = set(files.file_date)
    missing_files = [d for d in allDays if d not in have]
    RES["bulletin_files"] = int(len(files))
    RES["bulletin_days_in_range"] = int(len(allDays))
    RES["bulletin_missing_files"] = int(len(missing_files))
    delhi_missing = dl.aqi.isna()
    RES["delhi_days_with_value"] = int((~delhi_missing).sum())
    pd.DataFrame({"date": missing_files}).to_csv(os.path.join(data_dir, "excl_missing_bulletin_files.csv"), index=False)
    first_delhi = dl.aqi.first_valid_index()
    RES["delhi_first_date"] = str(first_delhi.date())

    # ---------------- H1: same-window comparisons
    years = list(range(2015, 2027))
    rows = []
    for c in CITIES:
        s = S[c].aqi
        for y in years:
            for nm, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20))]:
                x = window(s, y, *args)
                r = summarise(x.values, len(x))
                st = window(S[c].n_part, y, *args)
                r.update(city=c, year=y, window=nm, stations_median=float(st.median()) if st.notna().any() else np.nan,
                         stations_min=float(st.min()) if st.notna().any() else np.nan,
                         stations_max=float(st.max()) if st.notna().any() else np.nan)
                rows.append(r)
            if y <= 2025:
                x = window(s, y, 10, 1, 1, 31, y + 1)
                r = summarise(x.values, len(x))
                st = window(S[c].n_part, y, 10, 1, 1, 31, y + 1)
                r.update(city=c, year=y, window="oct_jan", stations_median=float(st.median()) if st.notna().any() else np.nan,
                         stations_min=float(st.min()) if st.notna().any() else np.nan,
                         stations_max=float(st.max()) if st.notna().any() else np.nan)
                rows.append(r)
            if 2016 <= y <= 2025:
                x = window(s, y, 1, 1, 12, 31)
                r = summarise(x.values, len(x))
                r.update(city=c, year=y, window="calendar_year")
                rows.append(r)
    T = pd.DataFrame(rows)
    flat = T.copy()
    for col in [k for k in T.columns if k.endswith("_ci")]:
        flat[col + "_lo"] = T[col].apply(lambda v: v[0] if isinstance(v, list) else np.nan)
        flat[col + "_hi"] = T[col].apply(lambda v: v[1] if isinstance(v, list) else np.nan)
        flat = flat.drop(columns=col)
    flat.to_csv(os.path.join(data_dir, "season_summary_by_city.csv"), index=False, float_format="%.4f")

    def get(c, y, wn):
        r = T[(T.city == c) & (T.year == y) & (T.window == wn)]
        return r.iloc[0].to_dict() if len(r) else None

    # Delhi headline table
    for wn in ["oct1_nov20", "nov1_20", "oct_jan", "calendar_year"]:
        RES[f"delhi_{wn}"] = {int(y): {k: v for k, v in (get("Delhi", y, wn) or {}).items()
                                       if k not in ("city", "year", "window")} for y in years if get("Delhi", y, wn)}

    # 2026 vs each year and vs the average of earlier years (Oct 1-Nov 20 and Nov 1-20)
    for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20))]:
        x26 = window(dl.aqi, 2026, *args).values
        comp = {}
        for y in years[:-1]:
            xy = window(dl.aqi, y, *args).values
            if np.isnan(xy).all():
                continue
            d = diff_boot(x26, xy)
            comp[y] = dict(diff=float(np.nanmean(x26) - np.nanmean(xy)), ci=ci(d),
                           pct=float(np.nanmean(x26) / np.nanmean(xy) - 1),
                           paired_pct_ci=ci(paired_boot(x26, xy, ratio=True)),
                           paired_diff_ci=ci(paired_boot(x26, xy)))
        RES[f"delhi_2026_vs_year_{wn}"] = comp
        # vs mean of 2016-2025 (each year bootstrapped separately, then averaged)
        base_years = list(range(2016, 2026))
        boots = np.mean([block_boot(window(dl.aqi, y, *args).values, mean_rows) for y in base_years], axis=0)
        b26 = block_boot(x26, mean_rows)
        base_mean = float(np.mean([np.nanmean(window(dl.aqi, y, *args).values) for y in base_years]))
        base_daily = np.nanmean(np.vstack([window(dl.aqi, y, *args).values[:len(x26)] for y in base_years]), axis=0)
        RES[f"delhi_2026_vs_2016_2025_{wn}"] = dict(mean_2026=float(np.nanmean(x26)), mean_base=base_mean,
                                                    diff=float(np.nanmean(x26) - base_mean), ci=ci(b26 - boots),
                                                    paired_diff_ci=ci(paired_boot(x26, base_daily)),
                                                    paired_pct=float(np.nanmean(x26) / np.nanmean(base_daily) - 1),
                                                    paired_pct_ci=ci(paired_boot(x26, base_daily, ratio=True)))
        base18 = np.nanmean(np.vstack([window(dl.aqi, y, *args).values[:len(x26)] for y in range(2018, 2026)]), axis=0)
        RES[f"delhi_2026_vs_2018_2025_{wn}"] = dict(mean_base=float(np.nanmean(base18)),
                                                    pct=float(np.nanmean(x26) / np.nanmean(base18) - 1),
                                                    paired_pct_ci=ci(paired_boot(x26, base18, ratio=True)))
        # rank of 2026 among years 2016-2026 (1 = worst)
        means = {y: np.nanmean(window(dl.aqi, y, *args).values) for y in range(2016, 2027)}
        order = sorted(means, key=lambda k: -means[k])
        RES[f"delhi_rank_2026_{wn}"] = dict(rank_worst_first=order.index(2026) + 1, of=len(order),
                                            order=[int(o) for o in order],
                                            means={int(k): float(v) for k, v in means.items()})
        # year-on-year: 2026 vs 2025 day counts
    # trend across years: OLS slope of yearly window means (2016-2026 and 2018-2026), CI from year-level residuals
    from scipy import stats
    for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20))]:
        for y0 in (2016, 2018):
            ys = np.arange(y0, 2027)
            ms = np.array([np.nanmean(window(dl.aqi, y, *args).values) for y in ys])
            lr = stats.linregress(ys, ms)
            tcrit = stats.t.ppf(0.975, len(ys) - 2)
            ts = stats.theilslopes(ms, ys)
            RES[f"delhi_trend_{wn}_{y0}_2026"] = dict(slope_per_year=float(lr.slope),
                                                      ci=[float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)],
                                                      theil_sen=float(ts[0]), theil_ci=[float(ts[2]), float(ts[3])],
                                                      n_years=int(len(ys)))
        for y0 in (2016, 2018):
            ys = np.arange(y0, 2027)
            sv = np.array([np.nansum(window(dl.aqi, y, *args).values > 300) for y in ys], float)
            lr = stats.linregress(ys, sv)
            tcrit = stats.t.ppf(0.975, len(ys) - 2)
            RES[f"delhi_trend_vpoor_days_{wn}_{y0}_2026"] = dict(slope_per_year=float(lr.slope),
                                                                 ci=[float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)])
    for y0 in (2016, 2018):
        ys = np.arange(y0, 2026)
        ms = np.array([np.nanmean(window(dl.aqi, y, 10, 1, 1, 31, y + 1).values) for y in ys])
        lr = stats.linregress(ys, ms)
        tcrit = stats.t.ppf(0.975, len(ys) - 2)
        RES[f"delhi_trend_oct_jan_{y0}_2025"] = dict(slope_per_year=float(lr.slope),
                                                     ci=[float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)])
        ys = np.arange(max(y0, 2016), 2026)
        ms = np.array([np.nanmean(window(dl.aqi, y, 1, 1, 12, 31).values) for y in ys])
        lr = stats.linregress(ys, ms)
        tcrit = stats.t.ppf(0.975, len(ys) - 2)
        RES[f"delhi_trend_calendar_{y0}_2025"] = dict(slope_per_year=float(lr.slope),
                                                      ci=[float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)])

    # stable-network era only (Delhi 33-40 stations): 2019-2025, i.e. excluding 2026's expansion
    for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20)), ("calendar", (1, 1, 12, 31))]:
        ys = np.arange(2019, 2026)
        ms = np.array([np.nanmean(window(dl.aqi, y, *args).values) for y in ys])
        lr = stats.linregress(ys, ms)
        tcrit = stats.t.ppf(0.975, len(ys) - 2)
        RES[f"delhi_trend_{wn}_stable_network_2019_2025"] = dict(
            slope_per_year=float(lr.slope), ci=[float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)],
            means={int(y): float(m) for y, m in zip(ys, ms)}, spread_min=float(ms.min()), spread_max=float(ms.max()))

    # every city, 2020-2025 (all six cities in the bulletin with 2-4+ stations; Delhi 33-39)
    city_tr = {}
    for c in CITIES:
        for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20)), ("calendar", (1, 1, 12, 31))]:
            ys, ms = [], []
            for y in range(2020, 2026):
                x = window(S[c].aqi, y, *args).values
                if np.mean(~np.isnan(x)) >= 0.6:
                    ys.append(y); ms.append(np.nanmean(x))
            if len(ys) >= 5:
                lr = stats.linregress(ys, ms)
                tcrit = stats.t.ppf(0.975, len(ys) - 2)
                city_tr[f"{c}|{wn}"] = dict(slope=float(lr.slope), ci=[float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)],
                                            n_years=len(ys), means=[float(m) for m in ms])
    RES["city_trends_2020_2025"] = city_tr

    # first-half vs second-half block comparison (Oct1-Nov20): 2016-2020 vs 2022-2026
    for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20)), ]:
        A = [window(dl.aqi, y, *args).values for y in range(2016, 2021)]
        B = [window(dl.aqi, y, *args).values for y in range(2022, 2027)]
        bA = np.mean([block_boot(a, mean_rows) for a in A], axis=0)
        bB = np.mean([block_boot(a, mean_rows) for a in B], axis=0)
        mA = float(np.mean([np.nanmean(a) for a in A])); mB = float(np.mean([np.nanmean(a) for a in B]))
        vA = [block_boot(a, share_above(300)) for a in A]; vB = [block_boot(a, share_above(300)) for a in B]
        sA = float(np.mean([np.nanmean(a > 300) for a in A])); sB = float(np.mean([np.nanmean(a > 300) for a in B]))
        svA = float(np.mean([np.nanmean(a > 400) for a in A])); svB = float(np.mean([np.nanmean(a > 400) for a in B]))
        RES[f"delhi_2016_20_vs_2022_26_{wn}"] = dict(mean_2016_20=mA, mean_2022_26=mB, diff=mB - mA,
                                                     pct=mB / mA - 1, ci=ci(bB - bA),
                                                     share_vpoor_2016_20=sA, share_vpoor_2022_26=sB,
                                                     share_vpoor_diff_ci=ci(np.mean(vB, axis=0) - np.mean(vA, axis=0)),
                                                     share_severe_2016_20=svA, share_severe_2022_26=svB)

    # monthly heatmap data
    m = dl.aqi.groupby([dl.index.year, dl.index.month]).agg(["mean", "count"])
    m.index.names = ["year", "month"]
    m.reset_index().to_csv(os.path.join(data_dir, "delhi_monthly_mean_aqi.csv"), index=False, float_format="%.2f")

    # daily chart-ready file for NCR cities Oct-Jan
    daily = pd.DataFrame({c: S[c].aqi for c in CITIES})
    for c in CITIES:
        daily[c + "_stations"] = S[c].n_part
        daily[c + "_stations_total"] = S[c].n_total
    daily["Delhi_pollutant"] = dl.pollutant
    daily.index.name = "date"
    daily.to_csv(os.path.join(data_dir, "ncr_daily_aqi.csv"), float_format="%.0f")

    # ---------------- H2: detection / station composition
    st = dl.n_part.groupby(dl.index.year).agg(["median", "min", "max"])
    RES["delhi_stations_by_year"] = {int(k): {kk: float(vv) for kk, vv in r.items()} for k, r in st.iterrows()}
    ncity = b.groupby("date").n_cities_in_bulletin.max()
    RES["bulletin_cities_by_year_median"] = {int(k): float(v) for k, v in ncity.groupby(ncity.index.year).median().items()}
    for c in CITIES:
        RES[f"{c}_stations_by_year_median"] = {int(k): float(v) for k, v in S[c].n_part.groupby(S[c].index.year).median().items() if not np.isnan(v)}

    # step detection on Delhi participating-station count
    npart = dl.n_part
    med_before = npart.rolling(21, min_periods=10).median()
    med_after = npart[::-1].rolling(21, min_periods=10).median()[::-1]
    jump = (med_after.shift(-1) - med_before)
    cand = jump[jump >= 4].index
    steps = []
    for d in cand:
        if not steps or (d - steps[-1]).days > 45:
            steps.append(d)
    # refine: within each cluster choose the day of max jump
    refined = []
    for s0 in steps:
        seg = jump.loc[s0 - pd.Timedelta(days=0): s0 + pd.Timedelta(days=45)]
        m_ = seg.idxmax()
        if not refined or (m_ - refined[-1]).days > 20:
            refined.append(m_)
    # neighbour reference: mean of log AQI of NCR cities (other than Delhi) with data that day
    others = [c for c in CITIES if c != "Delhi"]
    logo = pd.DataFrame({c: np.log(S[c].aqi) for c in others})
    nb_ref = logo.mean(axis=1)
    lr_ = np.log(dl.aqi) - nb_ref  # Delhi relative to its neighbours, removes shared weather
    ev = []
    for d in refined:
        pre = lr_.loc[d - pd.Timedelta(days=30): d - pd.Timedelta(days=1)].values
        post = lr_.loc[d + pd.Timedelta(days=1): d + pd.Timedelta(days=30)].values
        n_pre = npart.loc[d - pd.Timedelta(days=30): d - pd.Timedelta(days=1)].median()
        n_post = npart.loc[d + pd.Timedelta(days=1): d + pd.Timedelta(days=30)].median()
        if np.isnan(pre).all() or np.isnan(post).all():
            continue
        dd = diff_boot(post, pre)
        # seasonal placebo: same calendar date in every other year (Delhi/neighbour ratio has a seasonal rhythm)
        same_day = []
        for yy in range(2016, 2027):
            if yy == d.year:
                continue
            try:
                d2 = d.replace(year=yy)
            except ValueError:
                continue
            if any(abs((d2 - s_).days) < 45 for s_ in refined):
                continue
            p2 = lr_.loc[d2 - pd.Timedelta(days=30): d2 - pd.Timedelta(days=1)]
            q2 = lr_.loc[d2 + pd.Timedelta(days=1): d2 + pd.Timedelta(days=30)]
            if p2.notna().sum() >= 15 and q2.notna().sum() >= 15:
                same_day.append(float(np.exp(q2.mean() - p2.mean()) - 1))
        ev.append(dict(step_date=str(d.date()), stations_before=float(n_pre), stations_after=float(n_post),
                       same_date_other_years_mean_pct=float(np.mean(same_day)) if same_day else np.nan,
                       same_date_other_years_range=[float(min(same_day)), float(max(same_day))] if same_day else None,
                       delhi_vs_neighbours_change_pct=float(np.exp(np.nanmean(post) - np.nanmean(pre)) - 1),
                       ci_pct=[float(np.exp(v) - 1) for v in ci(dd)], n_pre=int((~np.isnan(pre)).sum()),
                       n_post=int((~np.isnan(post)).sum())))
    # placebo: same statistic at every non-step date (2017-2026) with data on both sides
    plac = []
    stepset = set(refined)
    for d in pd.date_range("2016-06-01", "2026-10-01", freq="7D"):
        if any(abs((d - s).days) < 60 for s in stepset):
            continue
        pre = lr_.loc[d - pd.Timedelta(days=30): d - pd.Timedelta(days=1)]
        post = lr_.loc[d + pd.Timedelta(days=1): d + pd.Timedelta(days=30)]
        if pre.notna().sum() < 15 or post.notna().sum() < 15:
            continue
        plac.append(float(np.exp(post.mean() - pre.mean()) - 1))
    RES["station_steps"] = ev
    RES["station_step_placebo"] = dict(n=len(plac), p2_5=float(np.percentile(plac, 2.5)),
                                       p97_5=float(np.percentile(plac, 97.5)), median=float(np.median(plac)))
    pd.DataFrame(ev).to_csv(os.path.join(data_dir, "station_step_events.csv"), index=False)

    # within-season: on days when fewer Delhi stations report than usual, is Delhi relatively higher/lower?
    dev = npart - npart.rolling(31, center=True, min_periods=10).median()
    dfw = pd.DataFrame({"lr": lr_, "dev": dev}).dropna()
    dfw = dfw[dfw.index.month.isin([10, 11, 12, 1])]
    dfw = dfw[dfw.index >= "2018-01-01"]
    sl = stats.linregress(dfw.dev, dfw.lr)
    RES["delhi_relative_vs_station_dropout"] = dict(pct_per_station=float(np.exp(sl.slope) - 1),
                                                    ci_pct=[float(np.exp(sl.slope - 1.96 * sl.stderr) - 1),
                                                            float(np.exp(sl.slope + 1.96 * sl.stderr) - 1)],
                                                    n=int(len(dfw)), dev_sd=float(dfw.dev.std()))

    # ---- 2026 network expansion test. In Oct-Nov 2026 Delhi (46->59 listed stations), Noida (4->7),
    # Ghaziabad (7->9) and Greater Noida (2->5) all grew; Gurugram (4) did not; Faridabad lost one (4->3).
    # (a) year-on-year change by city, against the history of the same comparison
    yoy = []
    for c in CITIES:
        for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20)), ("oct14_nov20", (10, 14, 11, 20))]:
            for y in range(2017, 2027):
                a1 = window(S[c].aqi, y, *args).values
                a0 = window(S[c].aqi, y - 1, *args).values
                if np.isnan(a1).mean() > 0.4 or np.isnan(a0).mean() > 0.4:
                    continue
                t1 = window(S[c].n_total, y, *args); t0 = window(S[c].n_total, y - 1, *args)
                p1 = window(S[c].n_part, y, *args); p0 = window(S[c].n_part, y - 1, *args)
                bd = block_boot(a1, mean_rows) / block_boot(a0, mean_rows) - 1
                yoy.append(dict(city=c, window=wn, year=y, pct_change=float(np.nanmean(a1) / np.nanmean(a0) - 1),
                                ci=ci(bd), paired_ci=ci(paired_boot(a1, a0, ratio=True)), stations_now=float(p1.max()), stations_prev=float(p0.max()),
                                listed_now=float(t1.max()) if t1.notna().any() else np.nan,
                                listed_prev=float(t0.max()) if t0.notna().any() else np.nan))
    Y = pd.DataFrame(yoy)
    g = Y[Y.city == "Gurugram"].set_index(["window", "year"])["pct_change"]
    Y["minus_gurugram_pts"] = [(r.pct_change - g.get((r.window, r.year), np.nan)) * 100 for r in Y.itertuples()]
    Yf = Y.copy()
    Yf["ci_lo"] = Yf.ci.apply(lambda v: v[0]); Yf["ci_hi"] = Yf.ci.apply(lambda v: v[1])
    Yf["paired_ci_lo"] = Yf.paired_ci.apply(lambda v: v[0]); Yf["paired_ci_hi"] = Yf.paired_ci.apply(lambda v: v[1])
    Yf = Yf.drop(columns=["ci", "paired_ci"])
    Yf.to_csv(os.path.join(data_dir, "yoy_change_by_city.csv"), index=False, float_format="%.4f")
    RES["yoy_2026"] = Y[Y.year == 2026].to_dict(orient="records")
    hist = {}
    for c in CITIES:
        if c == "Gurugram":
            continue
        for wn in ["oct1_nov20", "nov1_20", "oct14_nov20"]:
            h = Y[(Y.city == c) & (Y.window == wn) & (Y.year < 2026)]["minus_gurugram_pts"].dropna()
            now = Y[(Y.city == c) & (Y.window == wn) & (Y.year == 2026)].minus_gurugram_pts
            if len(h) and len(now):
                hist[f"{c}|{wn}"] = dict(now=float(now.iloc[0]), hist_min=float(h.min()), hist_max=float(h.max()),
                                         hist_sd=float(h.std()), n_hist=int(len(h)),
                                         rank_most_negative=int((h < now.iloc[0]).sum()) + 1)
    RES["yoy_2026_vs_history_relative_to_gurugram"] = hist
    # (b) event study around each 2026 expansion, against Gurugram only (unchanged network), with
    #     same-calendar-date placebo from 2019-2025
    lg = np.log(S["Gurugram"].aqi)
    ev26 = []
    for c, d in [("Delhi", "2026-10-11"), ("Noida", "2026-10-27"), ("Delhi", "2026-02-19")]:
        d = pd.Timestamp(d)
        rel = np.log(S[c].aqi) - lg
        def prepost(dd, k=14):
            pre = rel.loc[dd - pd.Timedelta(days=k): dd - pd.Timedelta(days=1)]
            post = rel.loc[dd + pd.Timedelta(days=1): dd + pd.Timedelta(days=k)]
            return pre, post
        pre, post = prepost(d)
        bd = diff_boot(post.values, pre.values)
        plac = []
        for yy in range(2019, 2026):
            p2, q2 = prepost(d.replace(year=yy))
            if p2.notna().sum() >= 8 and q2.notna().sum() >= 8:
                plac.append(float(np.exp(q2.mean() - p2.mean()) - 1))
        ev26.append(dict(city=c, date=str(d.date()), change_vs_gurugram_pct=float(np.exp(post.mean() - pre.mean()) - 1),
                         ci=[float(np.exp(v) - 1) for v in ci(bd)], placebo_same_dates=plac,
                         placebo_mean=float(np.mean(plac)) if plac else None))
    RES["events_2026_vs_gurugram"] = ev26

    # constant-network era: compare the trend using only years where Delhi median stations >= 30
    era = [y for y in range(2016, 2027) if RES["delhi_stations_by_year"].get(y, {}).get("median", 0) >= 30]
    RES["constant_network_years"] = era

    # ---------------- H4: weather + fires + Diwali model (Oct 1 - Nov 20 window)
    wx = w.copy()
    wcols = ["WS10M", "PRECTOTCORR", "T2M_MIN", "T2M_MAX", "RH2M", "WD10M"]
    # 4 PM bulletin covers 4 PM previous day -> 4 PM today: weight weather 1/3 previous day, 2/3 today
    wb = wx[wcols].shift(1) * (1 / 3) + wx[wcols] * (2 / 3)
    wb["rain_today"] = (wx.PRECTOTCORR > 1.0).astype(float)
    wb["rain_prev"] = (wx.PRECTOTCORR.shift(1) > 1.0).astype(float)
    wb["dtr"] = wb.T2M_MAX - wb.T2M_MIN
    wb["lnws"] = np.log(wb.WS10M.clip(lower=0.3))
    wd = wx.WD10M
    wb["nw_wind"] = ((wd >= 270) | (wd <= 0)).astype(float)
    fires = f.fires.reindex(pd.date_range("2015-01-01", "2025-12-31")).fillna(0)
    fire2 = fires.shift(1) + fires.shift(2)
    dset = []
    for y in range(2015, 2027):
        idx = pd.date_range(f"{y}-10-01", f"{y}-11-20")
        dv = pd.Timestamp(dw.loc[dw.year == y, "diwali"].iloc[0])
        part = pd.DataFrame(index=idx)
        part["y"] = np.log(dl.aqi.reindex(idx))
        part["aqi"] = dl.aqi.reindex(idx)
        for c in ["lnws", "rain_today", "rain_prev", "T2M_MIN", "dtr", "RH2M", "nw_wind"]:
            part[c] = wb[c].reindex(idx)
        part["fire_ln"] = np.log1p(fire2.reindex(idx)) if y <= 2025 else np.nan
        part["diwali1"] = (idx == dv + pd.Timedelta(days=1)).astype(float)
        part["diwali2"] = (idx == dv + pd.Timedelta(days=2)).astype(float)
        part["week"] = ((idx - idx[0]).days // 7).astype(int)
        part["year"] = y
        dset.append(part)
    D = pd.concat(dset)
    D.to_csv(os.path.join(data_dir, "model_dataset_oct1_nov20.csv"), float_format="%.4f")

    def fit(df, xcols, with_year=True):
        X = [np.ones(len(df))]
        names = ["const"]
        for c in xcols:
            X.append(df[c].values); names.append(c)
        for wk in sorted(df.week.unique())[1:]:
            X.append((df.week == wk).astype(float).values); names.append(f"wk{wk}")
        yrs = sorted(df.year.unique())
        if with_year:
            for yy in yrs[1:]:
                X.append((df.year == yy).astype(float).values); names.append(f"y{yy}")
        X = np.column_stack(X)
        beta, *_ = np.linalg.lstsq(X, df.y.values, rcond=None)
        resid = df.y.values - X @ beta
        r2 = 1 - resid.var() / df.y.values.var()
        return dict(zip(names, beta)), r2, resid

    weather_cols = ["lnws", "rain_today", "rain_prev", "T2M_MIN", "dtr", "RH2M", "nw_wind", "diwali1", "diwali2"]
    models = {}
    for mname, cols, yrs in [("weather", weather_cols, range(2015, 2027)),
                             ("weather_fire", weather_cols + ["fire_ln"], range(2015, 2026)),
                             ("weather_2016on", weather_cols, range(2016, 2027))]:
        df = D[D.year.isin(list(yrs))].dropna(subset=["y"] + cols)
        beta, r2, resid = fit(df, cols)
        # adjusted year index: year effect relative to the mean over years
        yrs_l = sorted(df.year.unique())
        fe = np.array([0.0] + [beta[f"y{yy}"] for yy in yrs_l[1:]])
        raw = df.groupby("year").y.mean().reindex(yrs_l).values
        # weather-only predicted contribution per year = raw mean - (const + FE + week effects mean)
        share = 1 - np.var(fe - fe.mean()) / np.var(raw - raw.mean())
        # cluster bootstrap by year-week blocks
        bshare, bfe = [], []
        df = df.copy()
        df["blk"] = df.year.astype(str) + "_" + df.week.astype(str)
        blks = df.blk.unique()
        groups = {k: g for k, g in df.groupby("blk")}
        for _ in range(400):
            pick = RNG.choice(blks, size=len(blks), replace=True)
            bd = pd.concat([groups[k] for k in pick])
            try:
                bb, _, _ = fit(bd, cols)
            except Exception:
                continue
            yl = sorted(bd.year.unique())
            if yl != yrs_l:
                continue
            fe_b = np.array([0.0] + [bb.get(f"y{yy}", np.nan) for yy in yrs_l[1:]])
            raw_b = bd.groupby("year").y.mean().reindex(yrs_l).values
            bshare.append(1 - np.var(fe_b - fe_b.mean()) / np.var(raw_b - raw_b.mean()))
            bfe.append(fe_b - fe_b.mean())
        bfe = np.array(bfe)
        adj = {int(yy): dict(raw_index=float(np.exp(raw[i] - raw.mean())),
                             adjusted_index=float(np.exp(fe[i] - fe.mean())),
                             adjusted_ci=[float(np.exp(np.percentile(bfe[:, i], 2.5))),
                                          float(np.exp(np.percentile(bfe[:, i], 97.5)))])
               for i, yy in enumerate(yrs_l)}
        models[mname] = dict(n=int(len(df)), r2=float(r2),
                             coef={k: float(v) for k, v in beta.items() if not k.startswith(("y", "wk")) or k == "y"},
                             share_between_year_variance_removed=float(share),
                             share_ci=ci(bshare), years=adj)
    RES["models"] = models
    rows = []
    for mname, mm in models.items():
        for yy, v in mm["years"].items():
            rows.append(dict(model=mname, year=yy, raw_index=v["raw_index"], adjusted_index=v["adjusted_index"],
                             adj_lo=v["adjusted_ci"][0], adj_hi=v["adjusted_ci"][1]))
    pd.DataFrame(rows).to_csv(os.path.join(data_dir, "weather_adjusted_year_index.csv"), index=False, float_format="%.4f")

    # season-level weather summary (is 2026 a calm, still year?)
    wsum = []
    for y in range(2015, 2027):
        sl_ = wx.loc[f"{y}-10-01":f"{y}-11-18"]
        wsum.append(dict(year=y, mean_wind_ms=float(sl_.WS10M.mean()), rain_mm=float(sl_.PRECTOTCORR.sum()),
                         rain_days=int((sl_.PRECTOTCORR > 1).sum()), mean_tmin=float(sl_.T2M_MIN.mean()),
                         calm_days_ws_lt_2=int((sl_.WS10M < 2).sum()), model=sl_.source_model.iloc[-1]))
    pd.DataFrame(wsum).to_csv(os.path.join(data_dir, "weather_season_summary_oct1_nov18.csv"), index=False, float_format="%.3f")
    RES["weather_season_summary"] = wsum

    # ---------------- Diwali
    dv_rows = []
    for _, r in dw.iterrows():
        d = pd.Timestamp(r.diwali)
        nxt = dl.aqi.get(d + pd.Timedelta(days=1), np.nan)
        base = dl.aqi.loc[d - pd.Timedelta(days=7): d - pd.Timedelta(days=1)].mean()
        dv_rows.append(dict(year=int(r.year), diwali=str(d.date()), month=d.month, aqi_day_after=float(nxt),
                            aqi_prev7_mean=float(base), jump=float(nxt - base),
                            nb_day_after=float(np.exp(nb_ref.get(d + pd.Timedelta(days=1), np.nan)))))
    DV = pd.DataFrame(dv_rows)
    DV.to_csv(os.path.join(data_dir, "diwali_check.csv"), index=False, float_format="%.1f")
    RES["diwali"] = dv_rows
    RES["diwali_jump_mean"] = float(DV.jump.mean())
    RES["diwali_jump_positive_years"] = int((DV.jump > 0).sum())

    # ---------------- fires vs Delhi (CREAMS, cumulative to 20 Nov)
    cr = cr.copy()
    cr["punjab_haryana"] = cr.Punjab + cr.Haryana
    cr["delhi_oct1_nov20_mean"] = [np.nanmean(window(dl.aqi, y, 10, 1, 11, 20).values) for y in cr.year]
    cr["delhi_nov1_20_mean"] = [np.nanmean(window(dl.aqi, y, 11, 1, 11, 20).values) for y in cr.year]
    cr["delhi_oct1_nov20_vpoor_days"] = [int(np.nansum(window(dl.aqi, y, 10, 1, 11, 20).values > 300)) for y in cr.year]
    # FIRMS Oct1-Nov20 box totals for cross-check
    cr["firms_box_oct1_nov20"] = [float(fires.loc[f"{y}-10-01":f"{y}-11-20"].sum()) if y <= 2025 else np.nan for y in cr.year]
    cr.to_csv(os.path.join(data_dir, "fires_vs_delhi.csv"), index=False, float_format="%.1f")
    RES["fires_vs_delhi"] = cr.to_dict(orient="records")
    fy = pd.DataFrame(dict(year=range(2015, 2026),
                           firms_box_oct1_nov20=[float(fires.loc[f"{y}-10-01":f"{y}-11-20"].sum()) for y in range(2015, 2026)],
                           delhi_oct1_nov20=[float(np.nanmean(window(dl.aqi, y, 10, 1, 11, 20).values)) for y in range(2015, 2026)]))
    fy.to_csv(os.path.join(data_dir, "firms_vs_delhi_by_year.csv"), index=False, float_format="%.1f")
    RES["firms_by_year"] = fy.to_dict(orient="records")
    # CREAMS vs FIRMS consistency
    mrg = cr.dropna(subset=["firms_box_oct1_nov20"])
    RES["creams_firms_corr"] = float(np.corrcoef(mrg.punjab_haryana, mrg.firms_box_oct1_nov20)[0, 1])

    # ---------------- NCR comparison table for 2026 vs 2025 vs 2016-2025 mean
    ncr = []
    for c in CITIES:
        for wn, args in [("oct1_nov20", (10, 1, 11, 20)), ("nov1_20", (11, 1, 11, 20))]:
            x26 = window(S[c].aqi, 2026, *args).values
            x25 = window(S[c].aqi, 2025, *args).values
            d = diff_boot(x26, x25)
            yrs_av = [y for y in range(2016, 2026) if not np.isnan(window(S[c].aqi, y, *args).values).all()]
            means = {y: float(np.nanmean(window(S[c].aqi, y, *args).values)) for y in yrs_av + [2026]}
            order = sorted(means, key=lambda k: -means[k])
            ncr.append(dict(city=c, window=wn, mean_2026=float(np.nanmean(x26)), mean_2025=float(np.nanmean(x25)),
                            diff_26_25=float(np.nanmean(x26) - np.nanmean(x25)), ci=ci(d),
                            rank_2026_worst_first=order.index(2026) + 1, n_years=len(order),
                            first_year=min(yrs_av) if yrs_av else None,
                            stations_2026=float(np.nanmedian(window(S[c].n_part, 2026, *args).values)),
                            stations_2016=float(np.nanmedian(window(S[c].n_part, 2016, *args).values)) if not np.isnan(window(S[c].n_part, 2016, *args).values).all() else None))
    RES["ncr_2026"] = ncr

    # ---------------- AQI ceiling and city-average dampening
    RES["delhi_days_at_500"] = int((dl.aqi >= 500).sum())
    RES["delhi_max_by_year"] = {int(k): float(v) for k, v in dl.aqi.groupby(dl.index.year).max().items() if not np.isnan(v)}
    pol = dl.pollutant.dropna()
    winter = pol[pol.index.month.isin([10, 11, 12, 1])]
    RES["delhi_winter_pm25_prominent_share_by_year"] = {int(k): float(v) for k, v in
                                                       winter.str.contains("PM25").groupby(winter.index.year).mean().items()}

    pd.DataFrame(EXCL).to_csv(os.path.join(data_dir, "exclusion_log_rows.csv"), index=False)
    RES["exclusions_count"] = len(EXCL)

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if np.isnan(o) else round(float(o), 4)
        if isinstance(o, (np.integer,)):
            return int(o)
        return o

    json.dump(clean(RES), open(os.path.join(data_dir, "results.json"), "w"), indent=1)
    print("done; exclusions:", len(EXCL))


if __name__ == "__main__":
    main()
