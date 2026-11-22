"""Fetch auxiliary primary datasets: NASA FIRMS (fires), NASA POWER (weather), ICAR-IARI CREAMS bulletins.

Usage:
    python3 -I fetch_aux.py RAW_DIR

Writes into RAW_DIR/firms, RAW_DIR/power, RAW_DIR/creams. Skips files already present.

Sources
- NASA FIRMS yearly country archive (MODIS Collection 6.1, standard processing), no key needed:
  https://firms.modaps.eosdis.nasa.gov/data/country/modis/{YEAR}/modis_{YEAR}_India.csv
  (2026 is not yet published as a yearly archive -> CREAMS used for 2026.)
- NASA POWER daily point API (MERRA-2 reanalysis; GEOS-IT for the most recent months):
  https://power.larc.nasa.gov/api/temporal/daily/point
- ICAR-IARI CREAMS paddy-residue burning bulletins (satellite fire events, 6 states):
  https://creams.iari.res.in/?page_id=1123  (list page) -> PDF per day
"""
import json
import os
import sys
import time
import urllib.request

UA = "Mozilla/5.0 (research; public-data report)"


def get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 500:
        return "cached"
    body = get(url)
    with open(path, "wb") as f:
        f.write(body)
    time.sleep(0.5)
    return len(body)


def main():
    raw = sys.argv[1]
    # FIRMS MODIS yearly, India
    fd = os.path.join(raw, "firms"); os.makedirs(fd, exist_ok=True)
    for y in range(2015, 2026):
        u = f"https://firms.modaps.eosdis.nasa.gov/data/country/modis/{y}/modis_{y}_India.csv"
        print("FIRMS", y, save(u, os.path.join(fd, f"modis_{y}_India.csv")), flush=True)

    # NASA POWER daily, central Delhi point (Safdarjung area) and a Punjab/Haryana-upwind point is not needed.
    pd_ = os.path.join(raw, "power"); os.makedirs(pd_, exist_ok=True)
    params = "WS10M,WS2M,WD10M,T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,PS,QV2M"
    for name, lat, lon in [("delhi", 28.61, 77.21)]:
        u = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=" + params +
             f"&community=RE&longitude={lon}&latitude={lat}&start=20150101&end=20261121&format=JSON")
        print("POWER", name, save(u, os.path.join(pd_, f"power_{name}_daily.json")), flush=True)

    # CREAMS: bulletin issued for events of 20 Nov each year (comparable cumulative window 15 Sep -> 20 Nov)
    cd = os.path.join(raw, "creams"); os.makedirs(cd, exist_ok=True)
    listing = os.path.join(cd, "_bulletin_page.html")
    if not os.path.exists(listing):
        with open(listing, "wb") as f:
            f.write(get("https://creams.iari.res.in/?page_id=1123"))
    import re
    html = open(listing, errors="replace").read()
    links = re.findall(r'["\'](/Creams_website_bulletin/[^"\']+\.pdf)["\']', html, re.I)
    want = {}
    for l in links:
        m = re.search(r'RiceResidueFireBulletin_(\d{2})Nov_(\d{4})', l)
        if m and m.group(1) == "20":
            want[m.group(2)] = l
    with open(os.path.join(cd, "_selected.json"), "w") as f:
        json.dump(want, f, indent=1)
    for y, l in sorted(want.items()):
        u = "https://creams.iari.res.in" + l
        print("CREAMS", y, save(u, os.path.join(cd, f"creams_20Nov_{y}.pdf")), flush=True)


if __name__ == "__main__":
    main()
