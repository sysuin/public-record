"""Parse DGCA-approved Winter Schedule 2026 PDFs into weekly departures per airline per airport.

Each PDF lists, station by station, every scheduled arrival and departure with
frequency (days of week 1-7) and effective-from / effective-to dates.
We count departures operating in one reference week (Mon 9 Nov - Sun 15 Nov 2026),
expanding the day-of-week frequency string and checking the effective window per day.

Usage: python3 -I 03_parse_schedules.py <sched_raw_dir> <out_csv>
"""
import sys, os, glob, datetime as dt, re, csv
import pdfplumber

REF_START = dt.date(2026, 11, 9)   # Monday
REF_DAYS = [REF_START + dt.timedelta(d) for d in range(7)]

def parse_date(s):
    return dt.datetime.strptime(s.strip(), "%d/%m/%Y").date()

def main(src, out):
    rows_out = []
    for f in sorted(glob.glob(os.path.join(src, "*.pdf"))):
        airline = os.path.basename(f)[:-4].replace("_", " ")
        station = None
        n_rows = n_bad = 0
        with pdfplumber.open(f) as pdf:
            for page in pdf.pages:
                for tbl in page.extract_tables():
                    for r in tbl:
                        if not r or r[0] is None: continue
                        c0 = (r[0] or "").strip()
                        if c0.startswith("Sl"): continue
                        if all(x in (None, "") for x in r[1:]):
                            station = c0.replace("\n", " "); continue
                        if not c0.isdigit(): continue
                        n_rows += 1
                        try:
                            freq = re.sub(r"\D", "", r[4] or "")
                            dep_to = (r[7] or "").strip()
                            arr_from = (r[5] or "").strip()
                            eff_from, eff_to = parse_date(r[9]), parse_date(r[10])
                        except Exception:
                            n_bad += 1; continue
                        days = sum(1 for d in REF_DAYS if str(d.isoweekday()) in freq and eff_from <= d <= eff_to)
                        rows_out.append(dict(airline=airline, station=station, flight=(r[1] or "").strip(),
                                             kind="dep" if dep_to else ("arr" if arr_from else "unk"),
                                             other=dep_to or arr_from, ref_week_ops=days))
        print(airline, "rows", n_rows, "unparsed", n_bad)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
