"""Fetch CPCB daily National AQI bulletins (PDF) for a date range.

Source: Central Pollution Control Board, daily AQI bulletin (4 PM, average of past 24 h).
URL pattern (linked from the CPCB CCR portal and cpcb.nic.in/AQI_Bulletin.php):
    https://www.cpcb.gov.in/upload/Downloads/AQI_Bulletin_YYYYMMDD.pdf
(cpcb.nic.in serves the same files, but its TLS certificate expired on 17 Nov 2026,
so we use the www.cpcb.gov.in host, which has a valid certificate.)

Usage:
    python3 -I fetch_cpcb_bulletins.py OUT_DIR [START YYYY-MM-DD] [END YYYY-MM-DD]

Polite: one request at a time, small pause, skips files already present.
Writes OUT_DIR/_fetch_log.csv with date, http status, bytes.
"""
import csv
import datetime as dt
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://www.cpcb.gov.in/upload/Downloads/AQI_Bulletin_{}.pdf"
UA = "Mozilla/5.0 (research; public-data report)"


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def main():
    out = sys.argv[1]
    start = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2015, 4, 1)
    end = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
    os.makedirs(out, exist_ok=True)
    logp = os.path.join(out, "_fetch_log.csv")
    new = not os.path.exists(logp)
    with open(logp, "a", newline="") as lf:
        w = csv.writer(lf)
        if new:
            w.writerow(["date", "status", "bytes", "fetched_utc"])
        d = start
        while d <= end:
            ymd = d.strftime("%Y%m%d")
            fp = os.path.join(out, f"AQI_Bulletin_{ymd}.pdf")
            if os.path.exists(fp) and os.path.getsize(fp) > 1000:
                d += dt.timedelta(days=1)
                continue
            status, nbytes = None, 0
            for attempt in range(3):
                try:
                    status, body = fetch(BASE.format(ymd))
                    if body[:4] == b"%PDF":
                        with open(fp, "wb") as f:
                            f.write(body)
                        nbytes = len(body)
                    else:
                        status = f"{status}-notpdf"
                    break
                except urllib.error.HTTPError as e:
                    status = e.code
                    break
                except Exception as e:  # network hiccup, retry
                    status = f"err:{type(e).__name__}"
                    time.sleep(3 * (attempt + 1))
            w.writerow([d.isoformat(), status, nbytes, dt.datetime.utcnow().isoformat(timespec="seconds")])
            lf.flush()
            time.sleep(0.25)
            d += dt.timedelta(days=1)


if __name__ == "__main__":
    main()
