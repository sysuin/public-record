"""Download AAI Traffic News 'Annexure-II' (aircraft movements by airport) PDFs listed on
https://www.aai.aero/en/business-opportunities/aai-traffic-news  (page listed Jan-Sep 2026 on 2026-11-21).
Usage: python3 -I 01c_fetch_aai.py <aai_raw_dir>
"""
import sys, os, re, time, urllib.request
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; read-only)"}
html = urllib.request.urlopen(urllib.request.Request("https://www.aai.aero/en/business-opportunities/aai-traffic-news", headers=UA), timeout=90).read().decode("utf-8", "ignore")
links = sorted(set(re.findall(r'href="(https://www\.aai\.aero/sites/default/files/traffic-news/[^"]*nnex_?2[^"]*\.pdf)"', html)))
for u in links:
    p = os.path.join(out, os.path.basename(u))
    if os.path.exists(p): continue
    data = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read()
    if data.startswith(b"%PDF"): open(p, "wb").write(data)
    print(os.path.basename(u), len(data)); time.sleep(0.5)
