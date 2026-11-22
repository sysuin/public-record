"""Download DGCA monthly domestic traffic reports listed in manifest.json.

Manifest captured 2026-11-21 from the DGCA portal page
  https://www.dgca.gov.in/digigov-portal/?page=4264/4206/sericename
  (Data & Reports > Aviation Data & Statistics > Air Transport > Domestic > Air Traffic).
The portal serves each file from its public document store:
  https://public-prd-dgca.s3.ap-south-1.amazonaws.com/InventoryList/dataReports/aviationDataStatistics/airTransport/domestic/airTraffic/<file>
(the portal's own JS strips the 'jsp/dgca/' prefix from the link path).

Usage: python3 -I 01_fetch.py <manifest.json> <raw_dir>
"""
import json, sys, os, time, urllib.request, urllib.parse, hashlib, csv

BASE = "https://public-prd-dgca.s3.ap-south-1.amazonaws.com/InventoryList/dataReports/aviationDataStatistics/airTransport/domestic/airTraffic/"
MONTHS = {m[:3].lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}

def main(manifest, raw):
    os.makedirs(raw, exist_ok=True)
    rows = json.load(open(manifest))
    log = []
    for year, label, fname in rows:
        m = MONTHS[label.strip()[:3].lower()]
        out = os.path.join(raw, f"{year}-{m:02d}.pdf")
        url = BASE + urllib.parse.quote(fname)
        status = "cached"
        if not os.path.exists(out) or os.path.getsize(out) < 1000:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; read-only)"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                if not data.startswith(b"%PDF"):
                    status = "not_pdf"
                else:
                    open(out, "wb").write(data); status = "ok"
                time.sleep(0.5)
            except Exception as e:
                status = f"error:{e}"
        sha = hashlib.sha256(open(out, "rb").read()).hexdigest()[:16] if os.path.exists(out) else ""
        log.append(dict(year=year, month=m, label=label, file=fname, url=url, local=os.path.basename(out), status=status, sha256_16=sha))
        print(year, m, status)
    with open(os.path.join(raw, "fetch_log.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0].keys())); w.writeheader(); w.writerows(log)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
