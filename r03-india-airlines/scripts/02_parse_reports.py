"""Parse DGCA monthly domestic traffic reports (PDF) into tidy CSVs.

Usage:
  python3 -I 02_parse_reports.py <pdf_dir> <text_cache_dir> <out_data_dir>

<pdf_dir> holds files named YYYY-MM.pdf (written by 01_fetch.py).
Outputs (in <out_data_dir>):
  bars_long.csv        airline x month x metric, from the report's bar charts
                       metrics: otp_pct, cancel_pct, complaints_per10k, delay2h_pct
  airport_otp.csv      airline x airport x month OTP (%), plus 'ALL' (2026 airport chart)
  market_table.csv     pax carried (lakh) and market share (%) per airline per month,
                       one row per (report, month, airline) so revisions can be traced
  loadfactor_table.csv load factor (%) per airline per month, per report
  complaints_table.csv Table 'Complaints Redressal Status' per airline
  pies.csv             complaint / cancellation / delay reason shares (all airlines)
  overall.csv          one row per report: headline numbers in the narrative text
  parse_log.csv        what was and wasn't found per report
"""
import sys, os, re, glob, csv, json
import pdfplumber
import numpy as np
from scipy.optimize import linear_sum_assignment

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BOILER = re.compile(r"Traffic report is being prepared|^=== PAGE|^\d{1,2}$|^OTP \(%\)$|Airport-wise On-Time|Route Dispersal|complying with|is as follows|^Note")
NUM_ONLY = re.compile(r"^-?\d+(\.\d+)?$")
AXIS = re.compile(r"^(-?\d+(\.\d+)?\s+){2,}-?\d+(\.\d+)?$")


# ------------------------------------------------------------------ text
def page_texts(pdf_path, cache_dir):
    key = os.path.basename(pdf_path)[:-4]
    cpath = os.path.join(cache_dir, key + ".json")
    if os.path.exists(cpath):
        return json.load(open(cpath))
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            out.append(pg.extract_text() or "")
    json.dump(out, open(cpath, "w"))
    return out


def normalise(t):
    # March 2020 report uses '$' for spaces, '@'/'<' for '-', '.' as filler in headings
    if t.count("$") > 50:
        t = t.replace("$", " ").replace("@", "-").replace("<", "-")
    return t


# ------------------------------------------------------------------ bar charts
def bar_block(text, start_pat, end_pat):
    used_nums = set()
    m = re.search(start_pat, text, flags=re.I | re.S)
    if not m:
        return None
    rest = text[m.end():]
    e = re.search(end_pat, rest, flags=re.I)
    block = rest[: e.start()] if e else rest[:1500]
    vals = []
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    NAME = r"[A-Za-z][A-Za-z0-9 .()&'+*\-]*?"
    pending = None   # a name-only line waiting for its value
    i = 0
    while i < len(lines):
        l = lines[i]
        if AXIS.match(l) or BOILER.search(l) or l.startswith("*"):
            i += 1; continue
        mm = re.match(r"^(" + NAME + r")\s+(-?\d+(?:\.\d+)?)(?:\s+(-?\d+(?:\.\d+)?))?$", l)
        if mm:
            vals.append((mm.group(1).strip(), float(mm.group(2))))
            if mm.group(3) and pending:            # 'Trujet 11.44 100.00' after a bare 'Air Taxi'
                vals.append((pending, float(mm.group(3)))); pending = None
        elif re.match(r"^" + NAME + r"$", l):
            if i + 1 < len(lines) and NUM_ONLY.match(lines[i + 1]):
                vals.append((l, float(lines[i + 1]))); i += 1
            elif i > 0 and NUM_ONLY.match(lines[i - 1]) and not AXIS.match(lines[i - 1]) and lines[i - 1] not in used_nums:
                vals.append((l, float(lines[i - 1])))   # value printed above the label
            else:
                pending = l
        i += 1
    return vals


def airport_blocks(text):
    """Per-airline airport OTP charts. Returns list of (airline, airport, value or None)."""
    s = re.search(r"Route Dispersal Guidelines is as follows:", text)
    if not s:
        s = re.search(r"Airport-wise On-Time Performance", text)
    if not s:
        return []
    e = re.search(r"Reasons for delay", text[s.end():])
    block = text[s.end(): s.end() + (e.start() if e else 6000)]
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    out, cur, i = [], None, 0
    while i < len(lines):
        l = lines[i]
        if AXIS.match(l) or BOILER.search(l):
            i += 1; continue
        m = re.match(r"^([A-Z]{3})\s+(\d+(?:\.\d+)?)$", l)
        if m and cur:
            out.append((cur, m.group(1), float(m.group(2))))
        elif re.match(r"^[A-Z]{3}$", l) and cur:
            if i + 1 < len(lines) and NUM_ONLY.match(lines[i + 1]):
                out.append((cur, l, float(lines[i + 1]))); i += 1
            else:
                out.append((cur, l, None))
        elif re.match(r"^[A-Za-z][A-Za-z .()&+*\-]+$", l) and not re.match(r"^[A-Z]{3}$", l):
            cur = l
        i += 1
    return out


# ------------------------------------------------------------------ geometric helpers
def page_words(pdf, idx):
    return pdf.pages[idx].extract_words(keep_blank_chars=False, use_text_flow=False)


def pie_shares(pdf, idx, start_pat, end_pat, labels):
    """Assign percentage tokens to category labels on a pie chart by geometry."""
    words = page_words(pdf, idx)
    # vertical window: between start phrase line and end phrase line
    text_lines = {}
    for w in words:
        text_lines.setdefault(round(w["top"]), []).append(w)
    tops = sorted(text_lines)
    def line_text(t):
        return " ".join(x["text"] for x in sorted(text_lines[t], key=lambda z: z["x0"]))
    y0 = y1 = None
    for t in tops:
        lt = line_text(t)
        if y0 is None and re.search(start_pat, lt, re.I):
            y0 = t
        elif y0 is not None and re.search(end_pat, lt, re.I):
            y1 = t; break
    if y0 is None:
        return None
    y1 = y1 if y1 is not None else 1e9
    W = [w for w in words if y0 + 5 < w["top"] < y1 - 1]
    # drop legend lines that contain >=5 labels
    by_line = {}
    for w in W:
        by_line.setdefault(round(w["top"]), []).append(w)
    keep = []
    for t, ws in by_line.items():
        txt = " ".join(x["text"] for x in ws)
        if sum(1 for lab in labels if re.search(r"\b" + re.escape(lab.split()[0]) + r"\b", txt)) >= 5 and "%" not in txt:
            continue
        keep += ws
    W = sorted(keep, key=lambda w: (round(w["top"]), w["x0"]))
    # split glued tokens like 'Reactionary65%' or 'Misc18.1%'
    toks = []
    for w in W:
        m = re.match(r"^([A-Za-z]+)(\d+(?:\.\d+)?%)$", w["text"])
        if m:
            frac = len(m.group(1)) / len(w["text"])
            xm = w["x0"] + frac * (w["x1"] - w["x0"])
            toks.append(dict(text=m.group(1), x0=w["x0"], x1=xm, top=w["top"], bottom=w["bottom"]))
            toks.append(dict(text=m.group(2), x0=xm, x1=w["x1"], top=w["top"], bottom=w["bottom"]))
        else:
            toks.append(dict(w))
    pcts = [t for t in toks if re.match(r"^\d+(\.\d+)?%$", t["text"])]
    # label anchors (multi-word labels: match first word then check second)
    anchors = []
    used = set()
    for lab in labels:
        parts = lab.split()
        for i, t in enumerate(toks):
            if i in used or t["text"].lower() != parts[0].lower():
                continue
            if len(parts) == 2:
                # second word: same line to the right, or next line below roughly same x
                cand = [j for j, u in enumerate(toks) if u["text"].lower().startswith(parts[1].lower()[:4]) and j not in used and (
                    (abs(u["top"] - t["top"]) < 3 and 0 <= u["x0"] - t["x1"] < 15) or (0 < u["top"] - t["bottom"] < 14 and abs(u["x0"] - t["x0"]) < 40))]
                if not cand:
                    continue
                u = toks[cand[0]]; used.add(cand[0])
                box = dict(x0=min(t["x0"], u["x0"]), x1=max(t["x1"], u["x1"]), top=t["top"], bottom=max(t["bottom"], u["bottom"]))
            else:
                box = dict(x0=t["x0"], x1=t["x1"], top=t["top"], bottom=t["bottom"])
            used.add(i)
            anchors.append((lab, box)); break
    if not anchors or not pcts:
        return None
    C = np.zeros((len(anchors), len(pcts)))
    for a, (lab, b) in enumerate(anchors):
        for p, q in enumerate(pcts):
            same_line = abs(q["top"] - b["top"]) < 4 and q["x0"] >= b["x1"] - 2
            if same_line:
                d = (q["x0"] - b["x1"]) * 0.8
            else:
                dy = q["top"] - b["bottom"]
                dx = abs((q["x0"] + q["x1"]) / 2 - (b["x0"] + b["x1"]) / 2)
                d = (abs(dy) * (1 if dy >= -1 else 3)) + dx * 0.6 + 4
            C[a, p] = d
    r, c = linear_sum_assignment(C)
    res = {}
    for a, p in zip(r, c):
        if C[a, p] < 80:
            res[anchors[a][0]] = float(pcts[p]["text"].rstrip("%"))
    return res


def column_table(pdf, idx, row_regex_first, header_stop_pat, value_rows):
    """Generic parser for DGCA columnar tables whose header names wrap over lines.
    Finds numeric columns from data rows, then assigns header words to nearest column."""
    words = sorted(page_words(pdf, idx), key=lambda w: w["top"])
    lines = {}
    cur_top = None
    for w in words:
        if cur_top is None or w["top"] - cur_top > 3.5:
            cur_top = w["top"]
        lines.setdefault(cur_top, []).append(w)
    tops = sorted(lines)
    data_lines = []
    for t in tops:
        ws = sorted(lines[t], key=lambda z: z["x0"])
        txt = " ".join(w["text"] for w in ws)
        if re.search(row_regex_first, txt) and not re.search(r"Lakhs|MARKET SHARE OF|SEAT FACTOR", txt):
            data_lines.append((t, ws, txt))
    if not data_lines:
        return None, None
    first_top = data_lines[0][0]
    # numeric x-centers
    centers = []
    for t, ws, txt in data_lines:
        nums = [w for w in ws if re.match(r"^(-?\d+(\.\d+)?|-)$", w["text"])]
        for w in nums:
            centers.append((w["x0"] + w["x1"]) / 2)
    if not centers:
        return None, None
    centers = sorted(centers)
    clusters = [[centers[0]]]
    for c in centers[1:]:
        if c - np.mean(clusters[-1]) < 14:
            clusters[-1].append(c)
        else:
            clusters.append([c])
    cols = [np.mean(c) for c in clusters if len(c) >= 2]
    if not cols:
        return None, None
    # header: lines above first data line, below the stop pattern line
    hdr_tops = [t for t in tops if t < first_top]
    start = None
    for t in hdr_tops:
        txt = " ".join(w["text"] for w in lines[t])
        if re.search(header_stop_pat, txt, re.I):
            start = t
    hdr_words = [w for t in hdr_tops if (start is None or t > start) for w in lines[t]
                 if w["text"] not in ("Month", "&", "Year", "Airline")]
    names = {i: [] for i in range(len(cols))}
    for w in hdr_words:
        xc = (w["x0"] + w["x1"]) / 2
        j = int(np.argmin([abs(xc - c) for c in cols]))
        if abs(xc - cols[j]) < 45:
            names[j].append(w)
    colnames = []
    for j in range(len(cols)):
        ws = sorted(names[j], key=lambda w: (round(w["top"]), w["x0"]))
        colnames.append(" ".join(w["text"] for w in ws).strip())
    for j in range(len(colnames)):
        if colnames[j] == "":
            left = colnames[j - 1] if j > 0 else ""
            right = colnames[j + 1] if j + 1 < len(colnames) else ""
            colnames[j] = f"COMBINED[{left}+{right}]"
    rows = []
    for t, ws, txt in data_lines:
        nums = [w for w in ws if re.match(r"^(-?\d+(\.\d+)?|-)$", w["text"])]
        lab = " ".join(w["text"] for w in ws if w not in nums)
        rec = {"_label": lab, "_top": t}
        for w in nums:
            xc = (w["x0"] + w["x1"]) / 2
            j = int(np.argmin([abs(xc - c) for c in cols]))
            if abs(xc - cols[j]) < 14:
                rec[colnames[j]] = None if w["text"] == "-" else float(w["text"])
        rows.append(rec)
    return colnames, rows


# ------------------------------------------------------------------ main
def find_page(texts, pat):
    for i, t in enumerate(texts):
        if re.search(pat, t, re.I):
            return i
    return None


def main(pdf_dir, cache_dir, out_dir):
    os.makedirs(cache_dir, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    bars, apt, mkt, lf, comp, pies, overall, plog = [], [], [], [], [], [], [], []
    for f in sorted(glob.glob(os.path.join(pdf_dir, "*.pdf"))):
        rep = os.path.basename(f)[:-4]
        ry, rm = int(rep[:4]), int(rep[5:7])
        texts = [normalise(t) for t in page_texts(f, cache_dir)]
        full = "\n".join(texts)
        log = {"report": rep}
        # --- headline narrative numbers
        o = {"report": rep}
        m = re.search(r"cancellation rate of scheduled domestic airlines for the month of\s+[A-Za-z]+\s*\d{4}\s+has been\s+(\d+\.?\d*)\s*%", full, re.S)
        o["cancel_overall_pct"] = float(m.group(1)) if m else None
        m = re.search(r"a total of\s+(\d+)\s+passenger", full)
        o["complaints_total"] = int(m.group(1)) if m else None
        m = re.search(r"carried for the month of\s+[A-Za-z]+\s*\d{4}\s+has been around\s+(\d+\.?\d*)", full, re.S)
        o["complaints_per10k_overall"] = float(m.group(1).rstrip(".")) if m else None
        m = re.search(r"during\s+(?:the month of\s+)?[A-Za-z]+\s*[-–]?\s*[A-Za-z]*\s*\d{4}\s+were\s+(\d+\.?\d*)\s*\.?\s*lakhs", full, re.S | re.I)
        o["pax_ytd_lakh"] = float(m.group(1)) if m else None
        m = re.search(r"computed\s+for\s+(four|six|ten)\s+(metro|major)\s+airports\s+viz\.?\s*([A-Za-z ,]+?)\.", full, re.S)
        o["otp_scope"] = (m.group(1) + ": " + re.sub(r"\s+", " ", m.group(3))) if m else None
        m = re.search(r"around\s+(\d+\.?\d*)\s*%\s+of the flights were delayed by more than two hours", full)
        o["delay2h_overall_pct"] = float(m.group(1)) if m else None
        overall.append(o)

        # --- bar charts
        specs = [
            ("cancel_pct", r"Airline-?\s*wise details of cancellations are as follows:", r"Cancellation Rate"),
            ("complaints_per10k", r"airline-?\s*wise\s*details\s+are\s+as\s+follows:", r"No\.\s*of Complaints"),
            ("otp_pct", r"OTP at (Four|Six|Ten) (Metro|Major) Airports", r"OTP \(%\)"),
            ("delay2h_pct", r"delayed by more than two hours is as\s+follows\.?", r"Flights delayed by more than 2 hours"),
            ("airport_otp_all", r"OTP of (Four|Six|Ten) (Metro|Major) Airports", r"OTP \(%\)"),
        ]
        for metric, sp, ep in specs:
            v = bar_block(full, sp, ep)
            log[metric] = len(v) if v else 0
            for name, val in (v or []):
                if metric == "airport_otp_all":
                    apt.append(dict(report=rep, airline="ALL", airport=name, otp_pct=val))
                else:
                    bars.append(dict(report=rep, year=ry, month=rm, airline_raw=name, metric=metric, value=val))
        # --- airport-wise per airline
        ab = airport_blocks(full)
        log["airport_rows"] = len(ab)
        log["airport_missing_values"] = sum(1 for x in ab if x[2] is None)
        for a, ap, v in ab:
            apt.append(dict(report=rep, airline=a, airport=ap, otp_pct=v))
        # --- complaints table
        pi = find_page(texts, r"Complaints Redressal Status")
        n = 0
        if pi is not None:
            seg = texts[pi].split("Complaints Redressal Status", 1)[1]
            lines = [l.strip() for l in seg.split("\n") if l.strip()]
            pend = None
            for l in lines:
                m1 = re.match(r"^(.*?[A-Za-z*)][A-Za-z ()*.]*?)\s+(\d+)\s+(\d+\.?\d*)\s+(\d+)\s+(\d+)$", l)
                m2 = re.match(r"^(\d+)\s+(\d+\.?\d*)\s+(\d+)\s+(\d+)$", l)
                if m1:
                    comp.append(dict(report=rep, airline_raw=m1.group(1).strip(), total=int(m1.group(2)), per10k=float(m1.group(3)), closed=int(m1.group(4)), open=int(m1.group(5)))); n += 1
                elif m2:
                    pend = m2.groups()
                elif pend and re.match(r"^[A-Za-z][A-Za-z ()*.]+$", l) and "Traffic report" not in l and not l.startswith("Carried"):
                    comp.append(dict(report=rep, airline_raw=l, total=int(pend[0]), per10k=float(pend[1]), closed=int(pend[2]), open=int(pend[3]))); n += 1; pend = None
        log["complaints_table_rows"] = n
        # --- geometric: pies, market table, load factor
        with pdfplumber.open(f) as pdf:
            pc = find_page(texts, r"reasons of passenger complaints")
            if pc is not None:
                r = pie_shares(pdf, pc, r"reasons of passenger complaints", r"^Note|major reasons? for complaints|Traffic report is being",
                               ["Fare", "Refund", "Flight Problem", "Baggage", "Customer Service", "Disability", "Staff Behaviour", "Catering", "Others"])
                for k, v in (r or {}).items():
                    pies.append(dict(report=rep, chart="complaint_reason", category=k, pct=v))
                log["pie_complaints_sum"] = round(sum((r or {}).values()), 1)
            pcn = find_page(texts, r"reasons of cancellations")
            if pcn is not None:
                r = pie_shares(pdf, pcn, r"reasons of cancellations", r"Traffic report is being|^\*",
                               ["Technical", "Weather", "Commercial", "Operational", "Misc", "Conse/Misc", "Consequential", "Others"])
                for k, v in (r or {}).items():
                    pies.append(dict(report=rep, chart="cancel_reason", category=k, pct=v))
                log["pie_cancel_sum"] = round(sum((r or {}).values()), 1)
            pdl = find_page(texts, r"Reasons for delay have been analysed")
            if pdl is not None:
                r = pie_shares(pdf, pdl, r"attributed to", r"Note:|Traffic report is being|^Pax Ramp",
                               ["Pax", "Ramp", "Tech", "Ops", "Reactionary", "Airport", "Wx", "ATC", "Misc"])
                for k, v in (r or {}).items():
                    pies.append(dict(report=rep, chart="delay_reason", category=k, pct=v))
                log["pie_delay_sum"] = round(sum((r or {}).values()), 1)
            pm = find_page(texts, r"MARKET SHARE OF SCHEDULE")
            nm = 0
            if pm is not None:
                cols, rows = column_table(pdf, pm, r"(Pax Carried|Market Share)", r"Passengers Carried \(in Lakhs\)", None)
                ORDER = ["Jan", "Feb", "Mar", "Q1", "Apr", "May", "Jun", "Q2", "Jul", "Aug", "Sep", "Q3",
                         "Oct", "Nov", "Dec", "Q4", "TOTAL"]
                paxrows = [rr for rr in (rows or []) if "Pax" in rr["_label"]]
                shrows = [rr for rr in (rows or []) if "Share" in rr["_label"]]
                log["market_rowpairs"] = f"{len(paxrows)}/{len(shrows)}"
                if len(paxrows) == 17 and len(shrows) == 17:
                    for k, lab in enumerate(ORDER):
                        if lab not in MON: continue
                        mon = MON.index(lab) + 1
                        for kind, rr in (("pax_lakh", paxrows[k]), ("share_pct", shrows[k])):
                            for c in cols:
                                if c in rr and rr[c] is not None:
                                    mkt.append(dict(report=rep, year=ry, month=mon, airline_raw=c, field=kind, value=rr[c])); nm += 1
                log["market_cells"] = nm
                log["market_cols"] = "|".join(cols or [])
            pl = find_page(texts, r"MONTH-?WISE SEAT FACTOR")
            nl = 0
            if pl is not None:
                cols, rows = column_table(pdf, pl, r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+-?\d", r"PASSENGER LOAD FACTOR", None)
                for rr in (rows or []):
                    mon = next((i + 1 for i, mm in enumerate(MON) if rr["_label"].startswith(mm)), None)
                    if not mon: continue
                    for c in cols:
                        if c in rr and rr[c] is not None:
                            lf.append(dict(report=rep, year=ry, month=mon, airline_raw=c, value=rr[c])); nl += 1
                log["lf_cells"] = nl
                log["lf_cols"] = "|".join(cols or [])
        plog.append(log)
        print(rep, {k: v for k, v in log.items() if k not in ("report", "market_cols", "lf_cols")})

    def dump(name, rows):
        if not rows: return
        keys = []
        for r in rows:
            for k in r:
                if k not in keys: keys.append(k)
        with open(os.path.join(out_dir, name), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    dump("bars_long_raw.csv", bars); dump("airport_otp_raw.csv", apt); dump("market_table_raw.csv", mkt)
    dump("loadfactor_table_raw.csv", lf); dump("complaints_table_raw.csv", comp); dump("pies.csv", pies)
    dump("overall.csv", overall); dump("parse_log.csv", plog)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
