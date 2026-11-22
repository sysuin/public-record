"""Parse CPCB daily AQI bulletin PDFs into a tidy city-day table.

Two independent extraction paths (run both, then compare with check_parse.py):
  A  poppler `pdftotext -layout` + a line regex
  B  pdfplumber table extraction (cell-based, no regex on whole lines)

Usage:
    python3 -I parse_bulletins.py METHOD OUT_CSV PDF_DIR [PDF_DIR ...]

Output columns: date, file_date, header_date, city, category, aqi, pollutant, n_part, n_total,
                n_cities_in_bulletin, method
City names are normalised: Gurgaon -> Gurugram.
"""
import csv
import datetime as dt
import glob
import os
import re
import subprocess
import sys
from multiprocessing import Pool

CITIES = ["Delhi", "Gurugram", "Gurgaon", "Noida", "Greater Noida", "Ghaziabad", "Faridabad"]
NORM = {"Gurgaon": "Gurugram"}
CANON = {c.lower(): NORM.get(c, c) for c in CITIES}  # case-insensitive: bulletins print e.g. "Greater noida"
CATS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
HDR = re.compile(r"Air Quality Index on\s+([A-Z][a-z]{2})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})")
CATRE = "((?i:Good|Satisfactory|Moderate|Poor|Very Poor|Severe))"
ROW_A = re.compile(r"^\s*(?:\d+\s+)?((?i:" + "|".join(c.replace(" ", r"\s+") for c in sorted(CITIES, key=len, reverse=True)) + r"))\s+" + CATRE +
                   r"\s+(\d{1,3})\s+(.+?)(?:\s+(\d{1,3})\s*#?\s*(?:/\s*(\d{1,3}))?\s*#?)?\s*$")
ANYROW = re.compile(r"^\s*(?:\d+\s+)?[A-Z][A-Za-z .()&-]+?\s+" + CATRE + r"\s+\d{1,3}\s+")


def catnorm(c):
    c = re.sub(r"\s+", " ", c.strip()).lower()
    return {x.lower(): x for x in CATS}.get(c, c)


def header_date(text):
    m = HDR.search(text)
    if not m:
        return ""
    try:
        return dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()
    except Exception:
        return ""


def norm_pol(s):
    s = s.replace("\n", " ")
    s = re.sub(r"PM\s*,\s*PM\s+2\.5\s+10", "PM2.5,PM10", s)
    s = re.sub(r"PM\s*,\s*PM\s+10\s+2\.5", "PM10,PM2.5", s)
    s = re.sub(r"\s+", "", s)
    s = s.replace("PM2.5", "PM25")
    # pdfplumber puts subscripts on a second line: 'PM2.5' arrives as 'PM' + '2.5'
    return s


def file_date(path):
    m = re.search(r"(\d{8})", os.path.basename(path))
    return dt.datetime.strptime(m.group(1), "%Y%m%d").date().isoformat()


def parse_A(path):
    try:
        txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return []
    hd = header_date(txt)
    ncity = sum(1 for ln in txt.split("\n") if ANYROW.match(ln))
    out, seen = [], set()
    for ln in txt.split("\n"):
        m = ROW_A.match(ln)
        if not m:
            continue
        city = CANON[re.sub(r"\s+", " ", m.group(1)).lower()]
        if city in seen:
            continue
        seen.add(city)
        out.append(dict(file_date=file_date(path), header_date=hd, city=city, category=catnorm(m.group(2)),
                        aqi=int(m.group(3)), pollutant=norm_pol(m.group(4)),
                        n_part=int(m.group(5)) if m.group(5) else "",
                        n_total=int(m.group(6)) if m.group(6) else "", n_cities_in_bulletin=ncity, method="A"))
    return out


def parse_B(path):
    import pdfplumber
    out, seen, hd, ncity = [], set(), "", 0
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i == 0:
                    hd = header_date(page.extract_text() or "")
                for tb in page.extract_tables():
                    for row in tb:
                        cells = [(c or "").replace("\n", " ").strip() for c in row]
                        cells = [c for c in cells if c != ""]
                        # locate the category cell, everything is positioned relative to it
                        idx = [k for k, c in enumerate(cells) if catnorm(c) in CATS]
                        if not idx:
                            continue
                        k = idx[0]
                        ncity += 1
                        if k < 1 or len(cells) < k + 3:
                            continue
                        city_raw = re.sub(r"\s+", " ", cells[k - 1]).lower()
                        if city_raw not in CANON:
                            continue
                        city = CANON[city_raw]
                        if city in seen:
                            continue
                        try:
                            aqi = int(re.sub(r"\D", "", cells[k + 1]))
                        except ValueError:
                            continue
                        st = cells[-1]
                        ms = re.match(r"^(\d{1,3})\s*#?\s*(?:/\s*(\d{1,3}))?\s*#?$", st) if len(cells) > k + 2 else None
                        if ms:
                            pol = cells[k + 2] if len(cells) > k + 3 else ""
                        else:
                            pol = cells[k + 2] if len(cells) > k + 2 else ""
                        seen.add(city)
                        out.append(dict(file_date=file_date(path), header_date=hd, city=city, category=catnorm(cells[k]),
                                        aqi=aqi, pollutant=norm_pol(pol), n_part=int(ms.group(1)) if ms else "",
                                        n_total=int(ms.group(2)) if ms and ms.group(2) else "", n_cities_in_bulletin=0,
                                        method="B"))
    except Exception:
        return []
    for r in out:
        r["n_cities_in_bulletin"] = ncity
    return out


def main():
    method, out_csv, dirs = sys.argv[1], sys.argv[2], sys.argv[3:]
    files = sorted(f for d in dirs for f in glob.glob(os.path.join(d, "AQI_Bulletin_*.pdf")))
    fn = parse_A if method == "A" else parse_B
    with Pool(7) as pool:
        res = pool.map(fn, files, chunksize=8)
    cols = ["date", "file_date", "header_date", "city", "category", "aqi", "pollutant", "n_part", "n_total",
            "n_cities_in_bulletin", "method"]
    nrows = 0
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rows in res:
            for r in rows:
                r["date"] = r["file_date"]
                w.writerow(r)
                nrows += 1
    # per-file inventory (files with zero NCR rows are logged for the exclusion log)
    inv = out_csv.replace(".csv", "_files.csv")
    with open(inv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_date", "n_rows"])
        for p, rows in zip(files, res):
            w.writerow([file_date(p), len(rows)])
    print(method, len(files), "files", nrows, "rows")


if __name__ == "__main__":
    main()
