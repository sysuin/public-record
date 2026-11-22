"""Download DGCA-approved domestic flight schedules (Winter Schedule 2026, effective
25 Oct 2026 - 27 Mar 2027), as linked from the DGCA portal page
  https://www.dgca.gov.in/digigov-portal/?page=4201/4200/servicename  (captured 2026-11-21)
Usage: python3 -I 01b_fetch_schedules.py <raw_dir>
"""
import sys, os, urllib.request, urllib.parse, time
BASE = "https://public-prd-dgca.s3.ap-south-1.amazonaws.com/InventoryList/airOperation/certification/scheduled/domestic/"
FILES = {"Air India": "AirIndiaLtd_SS_2027.pdf", "Air India Express": "AirIndiaExpressLimited_SS_2027.pdf",
         "Alliance Air": "AllianceAir_SS_2027.pdf", "IndiGo": "INTERGLOBE AVIATION LTD_2027.pdf",
         "SpiceJet": "SpiceJet_SS_2027.pdf", "Akasa Air": "AkasaAir_2027.pdf", "Fly91": "Fly91_2027.pdf",
         "IndiaOne Air": "IndiaOneAir_2027.pdf", "Star Air": "StarAir_2027.pdf"}
raw = sys.argv[1]; os.makedirs(raw, exist_ok=True)
for name, f in FILES.items():
    out = os.path.join(raw, name.replace(" ", "_") + ".pdf")
    if os.path.exists(out) and os.path.getsize(out) > 1000: print(name, "cached"); continue
    url = BASE + urllib.parse.quote(f)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; read-only)"})
    data = urllib.request.urlopen(req, timeout=90).read()
    print(name, len(data), data[:5]); 
    if data.startswith(b"%PDF"): open(out, "wb").write(data)
    time.sleep(0.5)
