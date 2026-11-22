"""Normalise airline names and build chart-ready tidy CSVs.

Usage: python3 -I 04_tidy.py <data_dir>
Reads <data_dir>/raw/*.csv (from 02_parse_reports.py); writes tidy CSVs into <data_dir>.
"""
import sys, os, re
import pandas as pd
import numpy as np

D = sys.argv[1]
RAW = os.path.join(D, "raw")


def canon(raw):
    s = str(raw).strip()
    if s.startswith("COMBINED[") and "Air India" in s and "Alliance" in s:
        return "Air India"          # Air India incl. Alliance Air (market table to Sep 2021)
    s = re.sub(r"\*", "", s)
    s = re.sub(r"^((Private\s+)?(Air\s+)?Carriers|Private Air|Private)\s+", "", s).strip()
    l = s.lower().replace(" ", "")
    rules = [
        (r"^(airindiagroup|airindia(\(dom.*\)|\(domestic\))?|ai|airindia\+allianceair)$", "Air India"),
        (r"^alliance", "Alliance Air"), (r"^spice", "SpiceJet"), (r"^indigo", "IndiGo"),
        (r"^(goair|gofirst)", "Go First"), (r"^(airasia|aixconnect)", "AirAsia India"),
        (r"^vistara", "Vistara"), (r"^jetairways", "Jet Airways"), (r"^jetlite", "JetLite"),
        (r"^akasa", "Akasa Air"), (r"^starair", "Star Air"), (r"^(trujet|turbomegha)", "TruJet"),
        (r"^flybig", "Flybig"), (r"^fly91", "Fly91"), (r"^indiaone", "IndiaOne Air"),
        (r"^airdeccan", "Air Deccan"), (r"^pawanhans", "Pawan Hans"), (r"^airodisha", "Air Odisha"),
        (r"^(airheritage|heritage)", "Air Heritage"), (r"^zo+m", "Zoom Air"), (r"^airtaxi", "Air Taxi"),
    ]
    for pat, name in rules:
        if re.match(pat, l):
            return name
    return "UNMAPPED:" + s


def ym(df):
    df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=1))
    return df


unmapped = set()

# ---------------- bar charts -> airline x month x metric
b = pd.read_csv(os.path.join(RAW, "bars_long_raw.csv"))
b["airline"] = b.airline_raw.map(canon)
unmapped |= set(b.airline[b.airline.str.startswith("UNMAPPED")])
b = b[~b.airline.str.startswith("UNMAPPED")]
dup = b.duplicated(["year", "month", "airline", "metric"], keep=False)
if dup.any():
    print("WARNING duplicate airline-month-metric rows:\n", b[dup])
b = b.drop_duplicates(["year", "month", "airline", "metric"], keep="first")
wide = b.pivot_table(index=["year", "month", "airline"], columns="metric", values="value", aggfunc="first").reset_index()
wide = ym(wide)

# ---------------- market table: take latest report for each (year, month, airline, field)
m = pd.read_csv(os.path.join(RAW, "market_table_raw.csv"))
m["airline"] = m.airline_raw.map(canon)
unmapped |= set(m.airline[m.airline.str.startswith("UNMAPPED")])
m = m[~m.airline.str.startswith("UNMAPPED")]
m["combined_ai_alliance"] = m.airline_raw.str.startswith("COMBINED[")
m = m[m.report.str[:4].astype(int) == m.year]
# revision tracing: same cell as published in the month's own report vs. latest report
m["rep_month"] = m.report.str[5:7].astype(int)
own = m[m.rep_month == m.month].set_index(["year", "month", "airline", "field"]).value
m = m.sort_values("report")
latest = m.groupby(["year", "month", "airline", "field"]).agg(value=("value", "last"), report=("report", "last"),
                                                            combined_ai_alliance=("combined_ai_alliance", "last")).reset_index()
latest["value_in_own_month_report"] = latest.set_index(["year", "month", "airline", "field"]).index.map(own.to_dict())
mk = latest.pivot_table(index=["year", "month", "airline"], columns="field", values="value", aggfunc="first").reset_index()
mk = ym(mk)
mk.to_csv(os.path.join(D, "market_share_monthly.csv"), index=False)
latest.to_csv(os.path.join(D, "market_table_revisions.csv"), index=False)

# ---------------- load factor
lf = pd.read_csv(os.path.join(RAW, "loadfactor_table_raw.csv"))
lf["airline"] = lf.airline_raw.map(canon)
lf = lf[~lf.airline.str.startswith("UNMAPPED")]
lf = lf[lf.report.str[:4].astype(int) == lf.year].sort_values("report")
lf = lf.groupby(["year", "month", "airline"]).value.last().rename("load_factor_pct").reset_index()

# ---------------- complaints table
c = pd.read_csv(os.path.join(RAW, "complaints_table_raw.csv"))
c["airline"] = c.airline_raw.map(canon)
c = c[~c.airline.str.startswith("UNMAPPED") & (c.airline_raw.str.lower() != "total")]
c["year"] = c.report.str[:4].astype(int); c["month"] = c.report.str[5:7].astype(int)
c = c.drop_duplicates(["year", "month", "airline"])
c = c.rename(columns={"total": "complaints_n", "per10k": "complaints_per10k_table"})[["year", "month", "airline", "complaints_n", "complaints_per10k_table", "closed", "open"]]

# ---------------- merge into the master panel
panel = wide.merge(mk.drop(columns="date"), on=["year", "month", "airline"], how="outer") \
            .merge(lf, on=["year", "month", "airline"], how="left") \
            .merge(c, on=["year", "month", "airline"], how="left")
panel = ym(panel)
# scope of the OTP measurement, from the report text
def scope(r):
    if r.year <= 2024: return "4 airports (BLR, DEL, HYD, BOM)"
    if r.year == 2025: return "6 airports (+MAA, CCU)"
    return "10 airports (+AMD, COK, GAU, LKO)"
panel["otp_scope"] = panel.apply(scope, axis=1)
panel["air_india_definition"] = np.where(panel.airline != "Air India", "",
    np.where(panel.date < "2021-10-01", "Air India (market table combines Alliance Air to Sep 2021)",
    np.where(panel.date < "2024-10-01", "Air India", "Air India Group (incl. Air India Express; AIX Connect from Oct 2024; Vistara from 12 Nov 2024)")))
cols = ["date", "year", "month", "airline", "otp_pct", "cancel_pct", "complaints_per10k", "delay2h_pct",
        "pax_lakh", "share_pct", "load_factor_pct", "complaints_n", "complaints_per10k_table", "closed", "open",
        "otp_scope", "air_india_definition"]
for k in cols:
    if k not in panel: panel[k] = np.nan
panel = panel[cols].sort_values(["date", "airline"])
panel.to_csv(os.path.join(D, "airline_month_panel.csv"), index=False)

# long version (airline x month x metric)
long = panel.melt(id_vars=["date", "year", "month", "airline", "otp_scope"],
                  value_vars=["otp_pct", "cancel_pct", "complaints_per10k", "delay2h_pct", "pax_lakh", "share_pct", "load_factor_pct", "complaints_n"],
                  var_name="metric", value_name="value").dropna(subset=["value"])
long.to_csv(os.path.join(D, "airline_month_metric_long.csv"), index=False)

# ---------------- airport OTP
a = pd.read_csv(os.path.join(RAW, "airport_otp_raw.csv"))
a["airline"] = np.where(a.airline == "ALL", "ALL", a.airline.map(canon))
unmapped |= set(a.airline[a.airline.str.startswith("UNMAPPED")])
a["year"] = a.report.str[:4].astype(int); a["month"] = a.report.str[5:7].astype(int)
a = a[~a.airline.str.startswith("UNMAPPED")]
a = a.drop_duplicates(["year", "month", "airline", "airport"])
a = ym(a)[["date", "year", "month", "airline", "airport", "otp_pct"]]
a.to_csv(os.path.join(D, "airport_airline_otp.csv"), index=False)

# ---------------- pies + overall
p = pd.read_csv(os.path.join(RAW, "pies.csv"))
p["category"] = p.category.replace({"Conse/Misc": "Misc", "Consequential": "Misc"})
p = p.groupby(["report", "chart", "category"]).pct.sum().reset_index()
p["year"] = p.report.str[:4].astype(int); p["month"] = p.report.str[5:7].astype(int)
p = ym(p)
p.to_csv(os.path.join(D, "reason_shares.csv"), index=False)
o = pd.read_csv(os.path.join(RAW, "overall.csv"))
o["year"] = o.report.str[:4].astype(int); o["month"] = o.report.str[5:7].astype(int)
ym(o).to_csv(os.path.join(D, "overall_monthly.csv"), index=False)

print("unmapped names:", unmapped)
print("panel rows", len(panel), "airlines", sorted(panel.airline.unique()))
