"""Parse AAI 'Traffic News' Annexure-II B (Domestic Aircraft Movements, by airport).

Source page: https://www.aai.aero/en/business-opportunities/aai-traffic-news (pulled 2026-11-21);
files https://www.aai.aero/sites/default/files/traffic-news/<Mon>2k26Annex2*.pdf
Each file gives, per airport, domestic movements for the month (this year, last year).
Usage: python3 -I 03b_parse_aai.py <aai_raw_dir> <out_csv>
"""
import sys, os, re, glob, csv
import pdfplumber
MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9}
ROW = re.compile(r"^\d+\s*[^A-Z]*?([A-Z][A-Z .()\-]+?)\s+(\d+)\s+(\d+)\s+(-?[\d.]+%|-)\s+(\d+)\s+(\d+)\s+(-?[\d.]+%|-)$")
out = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*nnex*2*.pdf"))):
    m = MON[os.path.basename(f)[:3].lower()]
    with pdfplumber.open(f) as pdf:
        texts = [p.extract_text() or "" for p in pdf.pages]
    # domestic section: from 'Domestic Aircraft Movement' up to 'TOTAL AIRCRAFT MOVEMENTS'
    full = "\n".join(texts)
    s = full.index("Domestic Aircraft Movement"); e = full.index("TOTAL AIRCRAFT MOVEMENTS")
    grand = None
    for line in full[s:e].split("\n"):
        line = line.strip()
        g = re.search(r"Grand Total\s+(\d+)\s+(\d+)", line)
        if g: grand = (int(g.group(1)), int(g.group(2)))
        r = ROW.match(line)
        if r:
            out.append(dict(month=m, airport=r.group(1).strip(), dom_mvts_2026=int(r.group(2)), dom_mvts_2025=int(r.group(3))))
    out.append(dict(month=m, airport="GRAND TOTAL (as printed)", dom_mvts_2026=grand[0], dom_mvts_2025=grand[1]))
    print(os.path.basename(f), m, "grand", grand, "sum rows", sum(r["dom_mvts_2026"] for r in out if r["month"] == m and not r["airport"].startswith("GRAND")))
with open(sys.argv[2], "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
