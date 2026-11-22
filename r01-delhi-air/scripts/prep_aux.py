"""Turn raw auxiliary downloads into small derived CSVs.

Usage:
    python3 -I prep_aux.py RAW_DIR DATA_DIR

Outputs (DATA_DIR):
  weather_delhi_daily.csv   NASA POWER (MERRA-2 to Sep 2026, GEOS-IT from Oct 2026) at 28.61N 77.21E
  fires_firms_daily.csv     NASA FIRMS MODIS C6.1 fire detections per day, India only, inside the
                            Punjab-Haryana box 29.0-32.5N, 73.8-77.5E (type 0 = presumed vegetation fire)
  fires_creams_20nov.csv    ICAR-IARI CREAMS cumulative paddy-residue burning events to 20 Nov, by state
  diwali_dates.csv          Lakshmi Puja (main Diwali night) dates, Delhi, 2015-2026
"""
import csv
import glob
import json
import os
import re
import subprocess
import sys

import pandas as pd

BOX = dict(lat0=29.0, lat1=32.5, lon0=73.8, lon1=77.5)

# Main Diwali (Lakshmi Puja) night as observed in Delhi. Public calendar facts; each is checked in
# analysis.py against the bulletin (the 4 PM bulletin on the following day covers Diwali night).
DIWALI = {2015: "2015-11-11", 2016: "2016-10-30", 2017: "2017-10-19", 2018: "2018-11-07",
          2019: "2019-10-27", 2020: "2020-11-14", 2021: "2021-11-04", 2022: "2022-10-24",
          2023: "2023-11-12", 2024: "2024-10-31", 2025: "2025-10-20", 2026: "2026-11-08"}


def weather(raw, out):
    j = json.load(open(os.path.join(raw, "power", "power_delhi_daily.json")))
    P = j["properties"]["parameter"]
    df = pd.DataFrame({k: pd.Series(v) for k, v in P.items()})
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.replace(-999.0, float("nan"))
    df.index.name = "date"
    df["source_model"] = ["GEOS-IT" if d >= pd.Timestamp("2026-10-01") else "MERRA-2" for d in df.index]
    df.to_csv(os.path.join(out, "weather_delhi_daily.csv"), float_format="%.3f")
    return df


def firms(raw, out):
    rows = []
    for f in sorted(glob.glob(os.path.join(raw, "firms", "modis_*_India.csv"))):
        d = pd.read_csv(f, usecols=["latitude", "longitude", "acq_date", "confidence", "type", "daynight"])
        n_all = len(d)
        d = d[(d.latitude.between(BOX["lat0"], BOX["lat1"])) & (d.longitude.between(BOX["lon0"], BOX["lon1"]))]
        n_box = len(d)
        d = d[d["type"] == 0]
        g = d.groupby("acq_date").size()
        gh = d[d.confidence >= 50].groupby("acq_date").size()
        for day, n in g.items():
            rows.append(dict(date=day, fires=n, fires_conf50=int(gh.get(day, 0))))
        print(os.path.basename(f), "all", n_all, "box", n_box, "box&type0", len(d))
    fd = pd.DataFrame(rows).sort_values("date")
    fd.to_csv(os.path.join(out, "fires_firms_daily.csv"), index=False)
    return fd


def creams(raw, out):
    rows = []
    for f in sorted(glob.glob(os.path.join(raw, "creams", "creams_20Nov_*.pdf"))):
        y = int(re.search(r"(\d{4})", os.path.basename(f)).group(1))
        txt = subprocess.run(["pdftotext", "-f", "1", "-l", "3", f, "-"], capture_output=True, text=True).stdout
        txt = re.sub(r"\s+", " ", txt)
        m = re.search(r"Total (\d+) burning events were detected in the (\w+) [Ss]tates between ([\w-]+) and ([\w-]+), "
                      r"which are distributed as ([\d ,and]+?) in ([A-Za-z ,]+?),? respectively", txt)
        if not m:
            print("CREAMS parse fail", y)
            continue
        nums = [int(x) for x in re.findall(r"\d+", m.group(5))]
        states = [s.strip() for s in re.split(r",| and ", m.group(6)) if s.strip()]
        rec = dict(year=y, total=int(m.group(1)), n_states_word=m.group(2), window_start=m.group(3),
                   window_end=m.group(4))
        for s, n in zip(states, nums):
            rec[s] = n
        rec["check_sum_matches_total"] = sum(nums) == int(m.group(1))
        rows.append(rec)
    cd = pd.DataFrame(rows)
    cd.to_csv(os.path.join(out, "fires_creams_20nov.csv"), index=False)
    print(cd.to_string())
    return cd


def main():
    raw, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    weather(raw, out)
    firms(raw, out)
    creams(raw, out)
    pd.DataFrame([dict(year=y, diwali=d) for y, d in DIWALI.items()]).to_csv(os.path.join(out, "diwali_dates.csv"), index=False)


if __name__ == "__main__":
    main()
