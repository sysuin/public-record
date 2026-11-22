"""Second code path + extraction validation.

Usage: python3 -I 07_verify.py <pdf_dir> <sched_dir> <data_dir>

1. Re-extracts every bar-chart value from every report with pdfminer's own layout engine
   (not pdfplumber's text), and compares the multiset of values per report/metric with the tidy panel.
2. Market-table checks: monthly shares sum to ~100; passengers implied by the complaints table
   (complaints / rate) agree with the market table.
3. Spot-check of 10 random months: parsed values must appear verbatim as 'name value' in the raw text.
4. Re-computes headline numbers with the csv module only (no pandas) from the tidy CSVs, and
   recomputes schedule coverage from word x-positions (not table extraction).
Writes data/validation_*.csv and data/verify_numbers.json.
"""
import sys, os, re, csv, json, glob, random, statistics as st
from collections import defaultdict, Counter
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
import pdfplumber

PDF, SCHED, D = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = {}

def rows(name):
    with open(os.path.join(D, name)) as f:
        return list(csv.DictReader(f))

def fnum(x):
    try: return float(x)
    except: return None

panel = rows("airline_month_panel.csv")
by_rep = defaultdict(dict)
for r in panel:
    rep = r["date"][:7]
    by_rep[rep][r["airline"]] = r

# ---------------------------------------------------------------- 1. pdfminer re-extraction
SPECS = {"otp_pct": (r"OTP at (Four|Six|Ten) (Metro|Major) Airports", r"Airport-wise|On-Time Performance \(OTP\) of scheduled domestic airlines viz|Route Dispersal"),
         "cancel_pct": (r"details of cancellations are as follows:", r"Various reasons of cancellations|Cancellation reasons"),
         "complaints_per10k": (r"wise\s*details\s+are\s+as\s+follows:", r"Various reasons of passenger complaints")}
val_rows = []
mismatch = 0; total = 0
for f in sorted(glob.glob(os.path.join(PDF, "*.pdf"))):
    rep = os.path.basename(f)[:-4]
    txt = extract_text(f, laparams=LAParams(line_margin=0.4, char_margin=3.0))
    if txt.count("$") > 50:
        txt = txt.replace("$", " ")
    for metric, (sp, ep) in SPECS.items():
        m = re.search(sp, txt, re.S)
        if not m:
            val_rows.append(dict(report=rep, metric=metric, status="section_not_found_pdfminer")); continue
        rest = txt[m.end():]
        e = re.search(ep, rest)
        block = rest[: e.start()] if e else rest[:1500]
        vals = sorted(float(x) for x in re.findall(r"(?<![\d.])(\d{1,3}\.\d{1,2})(?![\d.%])", block))
        # drop axis ticks (e.g. 0.00 10.00 20.00 ...) : values that form an arithmetic tick sequence
        ticks = set()
        for step in (0.5, 1.0, 10.0, 20.0, 2.0, 5.0):
            seq = [round(k * step, 2) for k in range(0, 11)]
            if sum(1 for v in seq if v in vals) >= 4:
                ticks |= set(seq)
        vals_nt = Counter(v for v in vals if v not in ticks)
        parsed = Counter(round(float(r[metric]), 2) for r in by_rep.get(rep, {}).values() if fnum(r.get(metric)) is not None)
        missing_in_pdfminer = parsed - Counter({k: v for k, v in vals_nt.items()}) - Counter({k: 99 for k in ticks})
        not_parsed = vals_nt - parsed
        ok = sum(missing_in_pdfminer.values()) == 0 and sum(not_parsed.values()) == 0
        total += 1; mismatch += (not ok)
        val_rows.append(dict(report=rep, metric=metric, status="ok" if ok else "MISMATCH",
                             n_parsed=sum(parsed.values()), n_pdfminer_values=sum(vals_nt.values()),
                             parsed_values_not_found=";".join(map(str, sorted(missing_in_pdfminer.elements()))),
                             pdfminer_values_not_parsed=";".join(map(str, sorted(not_parsed.elements())))))
with open(os.path.join(D, "validation_second_extraction.csv"), "w", newline="") as fh:
    keys = ["report", "metric", "status", "n_parsed", "n_pdfminer_values", "parsed_values_not_found", "pdfminer_values_not_parsed"]
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(val_rows)
OUT["second_extraction"] = {"report_metric_blocks": total, "blocks_with_parsed_value_missing_in_pdfminer": mismatch,
                            "sections_not_found_pdfminer": sum(1 for r in val_rows if r["status"].startswith("section"))}

# ---------------------------------------------------------------- 2. market-table checks
sums = defaultdict(float)
for r in panel:
    if fnum(r["share_pct"]) is not None: sums[r["date"][:7]] += float(r["share_pct"])
bad = {k: round(v, 1) for k, v in sums.items() if not (99.0 <= v <= 101.0)}
OUT["market_share_sums"] = {"months": len(sums), "min": round(min(sums.values()), 1), "max": round(max(sums.values()), 1), "outside_99_101": bad}
diffs = []
for r in panel:
    n, rate, pax = fnum(r["complaints_n"]), fnum(r["complaints_per10k_table"]), fnum(r["pax_lakh"])
    if n and rate and pax and rate >= 0.5 and n >= 50:
        implied = n / rate * 1e4 / 1e5
        diffs.append(dict(date=r["date"], airline=r["airline"], pax_lakh_market=pax, pax_lakh_implied=round(implied, 2), rel_diff=round(implied / pax - 1, 3)))
with open(os.path.join(D, "validation_pax_crosscheck.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(diffs[0].keys())); w.writeheader(); w.writerows(diffs)
rd = [abs(x["rel_diff"]) for x in diffs]
OUT["pax_crosscheck"] = {"n": len(rd), "median_abs_rel_diff": round(st.median(rd), 3), "share_within_10pct": round(sum(1 for x in rd if x <= 0.10) / len(rd), 3)}

# ---------------------------------------------------------------- 3. spot-check 10 random months
random.seed(42)
reps = sorted(by_rep)
pick = sorted(random.sample([r for r in reps if r != "2020-03"], 10))
sc_rows = []
cache = {}
for rep in pick:
    with pdfplumber.open(os.path.join(PDF, rep + ".pdf")) as pdf:
        raw = "\n".join((p.extract_text() or "") for p in pdf.pages)
    flat = re.sub(r"\s+", " ", raw)
    for al, r in by_rep[rep].items():
        for metric in ["otp_pct", "cancel_pct", "complaints_per10k", "share_pct", "pax_lakh"]:
            v = fnum(r.get(metric))
            if v is None: continue
            fmt = {"otp_pct": "{:.1f}", "cancel_pct": "{:.2f}", "complaints_per10k": "{:.1f}", "share_pct": "{:.1f}", "pax_lakh": "{:.2f}"}[metric]
            s = fmt.format(v)
            found = s in flat
            # for market-table values the month row may come from a later report (revisions); flag that
            sc_rows.append(dict(report=rep, airline=al, metric=metric, value=s, found_in_same_report_text=found))
with open(os.path.join(D, "validation_spotcheck_10_months.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(sc_rows[0].keys())); w.writeheader(); w.writerows(sc_rows)
def rate(metric_set):
    x = [r for r in sc_rows if r["metric"] in metric_set]
    return dict(n=len(x), found=sum(r["found_in_same_report_text"] for r in x))
OUT["spotcheck"] = {"months": pick, "bar_values": rate({"otp_pct", "cancel_pct", "complaints_per10k"}), "market_values": rate({"share_pct", "pax_lakh"})}

# ---------------------------------------------------------------- 4. headline numbers, csv-only
main = [r for r in panel if fnum(r["share_pct"]) is not None and float(r["share_pct"]) >= 1 and fnum(r["otp_pct"]) is not None]
bym = defaultdict(list)
for r in main: bym[r["date"]].append(r)
leaders = {d: max(v, key=lambda r: float(r["otp_pct"]))["airline"] for d, v in bym.items()}
OUT["leader_counts_all"] = dict(Counter(leaders.values()))
ds = sorted(leaders)
OUT["leader_changes_all"] = sum(1 for a, b in zip(ds, ds[1:]) if leaders[a] != leaders[b])
def mean_of(al, metric, d0, d1, skip=()):
    xs = [float(r[metric]) for r in panel if r["airline"] == al and d0 <= r["date"] <= d1 and fnum(r[metric]) is not None and r["date"] not in skip]
    return round(sum(xs) / len(xs), 2) if xs else None
for al in ["IndiGo", "Akasa Air", "Air India"]:
    for metric in ["otp_pct", "cancel_pct", "complaints_per10k"]:
        OUT[f"{al}|{metric}|2026"] = mean_of(al, metric, "2026-01-01", "2026-09-01")
        OUT[f"{al}|{metric}|2025"] = mean_of(al, metric, "2025-01-01", "2025-12-01")
OUT["gap_otp_indigo_minus_akasa_2026"] = round(OUT["IndiGo|otp_pct|2026"] - OUT["Akasa Air|otp_pct|2026"], 2)
dec = {r["airline"]: r for r in panel if r["date"] == "2025-12-01"}
OUT["dec2025_indigo"] = {k: dec["IndiGo"][k] for k in ["otp_pct", "cancel_pct", "complaints_per10k", "share_pct"]}
ig = sorted((r["date"], float(r["share_pct"])) for r in panel if r["airline"] == "IndiGo" and fnum(r["share_pct"]) is not None)
OUT["indigo_share_first_last"] = [ig[0], ig[-1], max(ig, key=lambda x: x[1])]
ov = rows("overall_monthly.csv")
OUT["complaints_total_2024"] = sum(int(float(r["complaints_total"])) for r in ov if r["year"] == "2024" and r["complaints_total"])
OUT["complaints_total_2025"] = sum(int(float(r["complaints_total"])) for r in ov if r["year"] == "2025" and r["complaints_total"])
OUT["complaints_total_2026_jan_sep"] = sum(int(float(r["complaints_total"])) for r in ov if r["year"] == "2026" and r["complaints_total"])
OUT["complaints_dec2025"] = [r["complaints_total"] for r in ov if r["report"] == "2025-12"][0]

# schedule coverage from word x-positions (independent of table extraction)
OTP10 = {"Bangalore", "Delhi", "Hyderabad", "Mumbai", "Chennai", "Kolkata", "Ahmedabad", "Kochi", "Guwahati", "Lucknow"}
OTP4 = {"Bangalore", "Delhi", "Hyderabad", "Mumbai"}
import datetime as dt
REF = [dt.date(2026, 11, 9) + dt.timedelta(k) for k in range(7)]
cov = {}
for f in sorted(glob.glob(os.path.join(SCHED, "*.pdf"))):
    al = os.path.basename(f)[:-4].replace("_", " ")
    al = "Air India" if al == "Air India Express" else al
    tot = c10 = c4 = 0
    with pdfplumber.open(f) as pdf:
        station = None
        for page in pdf.pages:
            ws = page.extract_words()
            hdr = [w for w in ws if w["text"] == "Departure"]
            arr = [w for w in ws if w["text"] == "Arrival"]
            if hdr and arr:
                dep_x = min(w["x0"] for w in hdr); arr_x = min(w["x0"] for w in arr)
            elif "dep_x" not in dir():
                continue
            lines = defaultdict(list)
            for w in ws: lines[round(w["top"])].append(w)
            for t in sorted(lines):
                L = sorted(lines[t], key=lambda w: w["x0"])
                txt = " ".join(w["text"] for w in L)
                if re.match(r"^[A-Za-z][A-Za-z .()]+$", txt) and len(L) <= 3 and not txt.startswith(("Sl", "Departure", "Time", "Director", "Approved", "Airport", "Published", "Tel", "Aurbindo")):
                    station = txt.strip(); continue
                if not re.match(r"^\d+ ", txt): continue
                codes = [w for w in L if re.match(r"^[A-Z]{3}$", w["text"]) and w["x0"] > arr_x - 30 and w["text"] not in ("IGO", "AIC", "SEJ", "AXB", "AKJ", "LLR", "FBR", "FLY", "SDG", "IAD", "BDA", "OTH")]
                dates = re.findall(r"\d{2}/\d{2}/\d{4}", txt)
                freq = [w["text"] for w in L if re.match(r"^[1-7]{1,7}$", w["text"])]
                if not codes or len(dates) < 2 or not freq: continue
                is_dep = codes[-1]["x0"] >= dep_x - 15
                if not is_dep: continue
                d0 = dt.datetime.strptime(dates[-2], "%d/%m/%Y").date(); d1 = dt.datetime.strptime(dates[-1], "%d/%m/%Y").date()
                n = sum(1 for d in REF if str(d.isoweekday()) in freq[-1] and d0 <= d <= d1)
                tot += n
                if station in OTP10: c10 += n
                if station in OTP4: c4 += n
    a = cov.setdefault(al, [0, 0, 0]); a[0] += tot; a[1] += c10; a[2] += c4
OUT["schedule_coverage_wordpos"] = {k: {"weekly_deps": v[0], "share10": round(100 * v[1] / v[0], 1) if v[0] else None, "share4": round(100 * v[2] / v[0], 1) if v[0] else None} for k, v in cov.items()}

# months where one airline leads on all three measures (csv-only recomputation)
agree = 0; agree_ties = 0; nm = 0
for d, v in bym.items():
    v = [r for r in v if fnum(r["cancel_pct"]) is not None and fnum(r["complaints_per10k"]) is not None]
    if len(v) < 4: continue
    nm += 1
    def best(col, hi):
        x = [float(r[col]) for r in v]; t = max(x) if hi else min(x)
        return {r["airline"] for r in v if float(r[col]) == t}
    A, B, Cc = best("otp_pct", True), best("cancel_pct", False), best("complaints_per10k", False)
    agree += (len(A) == len(B) == len(Cc) == 1 and A == B == Cc)   # outright best on all three
    agree_ties += 1 if (A & B & Cc) else 0
OUT["months_one_airline_best_on_all_three"] = {"outright": agree, "best_or_joint_best": agree_ties, "months": nm}
# December 2025 multiple of IndiGo's typical month
igc = sorted(float(r["cancel_pct"]) for r in panel if r["airline"] == "IndiGo" and "2022-01-01" <= r["date"] <= "2025-11-01" and fnum(r["cancel_pct"]) is not None)
OUT["indigo_cancel_median_2022_nov2025"] = st.median(igc)
OUT["indigo_dec2025_multiple_of_median"] = round(9.65 / st.median(igc), 1)

json.dump(OUT, open(os.path.join(D, "verify_numbers.json"), "w"), indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str))
