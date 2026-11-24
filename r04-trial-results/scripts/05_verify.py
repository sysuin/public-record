"""R04 step 5: second, independent code path.

Reads the raw API pages directly (json + gzip + csv only; no pandas, no shared code with 02/03),
re-implements every cohort and outcome from the field definitions, recomputes the headline numbers,
and compares them with data/headline_numbers.json.

Usage: python3 -I 05_verify.py <raw_dir> <data_dir>
Writes <data_dir>/verify_numbers.json and <data_dir>/verification_table.csv
"""
import calendar, csv, datetime as dt, glob, gzip, json, os, sys
from collections import Counter, defaultdict

REF = dt.date(2026, 11, 20)
RULE = dt.date(2017, 1, 18)
US = {"United States", "Puerto Rico", "Guam", "Virgin Islands (U.S.)", "U.S. Virgin Islands", "American Samoa",
      "Northern Mariana Islands", "United States Minor Outlying Islands"}
OPEN = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "SUSPENDED"}
PRODUCT = {"DRUG", "BIOLOGICAL", "DEVICE", "GENETIC", "COMBINATION_PRODUCT", "RADIATION", "DIAGNOSTIC_TEST"}


def to_date(s, end=True):
    if not s:
        return None
    parts = s.split("-")
    try:
        y, m = int(parts[0]), int(parts[1])
        if len(parts) == 3:
            return dt.date(y, m, int(parts[2]))
        return dt.date(y, m, calendar.monthrange(y, m)[1] if end else 1)
    except (ValueError, IndexError):
        return None


def pct(k, n):
    return round(100.0 * k / n, 2) if n else None


def walk(raw):
    for f in sorted(glob.glob(os.path.join(raw, "pages", "page_*.json.gz"))):
        with gzip.open(f) as fh:
            for s in json.load(fh)["studies"]:
                yield s


def main():
    raw, data = sys.argv[1], sys.argv[2]
    C = Counter()
    seen = set()
    spons = defaultdict(lambda: [0, 0, 0, 0])  # n, sub12, sub24, overdue (no results, no certification) in main like cohort
    for s in walk(raw):
        ps = s.get("protocolSection", {})
        nct = ps.get("identificationModule", {}).get("nctId")
        if nct in seen:
            C["dup"] += 1
            continue
        seen.add(nct)
        C["records"] += 1
        stm = ps.get("statusModule", {})
        des = ps.get("designModule", {})
        ovs = ps.get("oversightModule", {})
        status = stm.get("overallStatus")
        stype = des.get("studyType")
        phases = des.get("phases") or []
        purpose = (des.get("designInfo") or {}).get("primaryPurpose")
        pcd_s = (stm.get("primaryCompletionDateStruct") or {}).get("date")
        pcd_t = (stm.get("primaryCompletionDateStruct") or {}).get("type")
        pcd = to_date(pcd_s)
        rfs = to_date(stm.get("resultsFirstSubmitDate"), end=False)
        trk = ((s.get("derivedSection") or {}).get("miscInfoModule") or {}).get("submissionTracking") or {}
        est = to_date(trk.get("estimatedResultsFirstSubmitDate"), end=False)
        posted = bool(s.get("hasResults"))
        sub_date = rfs or est
        submitted = sub_date is not None
        pending = (est is not None) and not posted
        delay = (sub_date - pcd).days if (submitted and pcd) else None
        s12 = submitted and delay is not None and delay <= 365
        s24 = submitted and delay is not None and delay <= 730
        disp = to_date(stm.get("dispFirstSubmitDate"), end=False)
        cert = disp is not None and pcd is not None and (disp - pcd).days <= 365
        locs = (ps.get("contactsLocationsModule") or {}).get("locations") or []
        countries = {l.get("country") for l in locs if l.get("country")}
        us_site = bool(countries & US)
        itypes = {i.get("type") for i in (ps.get("armsInterventionsModule") or {}).get("interventions") or []}
        drug, dev = ovs.get("isFdaRegulatedDrug"), ovs.get("isFdaRegulatedDevice")
        export = ovs.get("isUsExport") is True
        cls = (ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor", {}).get("class")
        name = (ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor", {}).get("name")
        if ovs.get("fdaaa801Violation") is True:
            C["fda_violation_flag"] += 1
        if stype != "INTERVENTIONAL":
            continue
        C["int"] += 1
        if pending:
            C["pending_int"] += 1
        if status == "UNKNOWN":
            C["srv_int_unknown_status"] += 1
        if status == "WITHDRAWN":
            C["srv_int_withdrawn"] += 1
        if (drug is True or dev is True) and pcd_t == "ACTUAL" and pcd and RULE <= pcd <= dt.date(2024, 11, 20) \
                and status != "WITHDRAWN" and "United States" in countries:
            C["srv_fda_us_actual_2017_2024"] += 1; C["srv_fda_us_actual_2017_2024_results"] += posted
        if status == "COMPLETED":
            C["comp"] += 1; C["comp_posted"] += posted; C["comp_sub"] += submitted
            if pcd:
                C[f"srv_int_completed_pcd{pcd.year}"] += 1; C[f"srv_int_completed_pcd{pcd.year}_results"] += posted
            if pcd and 2008 <= pcd.year <= 2023:
                C["win"] += 1; C["win_sub"] += submitted; C["win_posted"] += posted
        if status in ("WITHDRAWN", "WITHHELD"):
            continue
        ph1 = phases in (["PHASE1"], ["EARLY_PHASE1"])
        feas = purpose == "DEVICE_FEASIBILITY" and drug is not True
        req = (drug is True or dev is True) and not ph1 and not feas and (us_site or export)
        lite = bool(itypes & PRODUCT) and not ph1 and purpose != "DEVICE_FEASIBILITY" and us_site
        # like cohort: actual PCD between rule date and REF-730
        if pcd_t == "ACTUAL" and pcd and RULE <= pcd and (REF - pcd).days >= 730:
            g = "req" if req else "oth"
            C[f"like_{g}"] += 1; C[f"like_{g}_s12"] += s12; C[f"like_{g}_s24"] += s24; C[f"like_{g}_ever"] += submitted
            if req:
                C[f"like_req_{cls}"] += 1; C[f"like_req_{cls}_s12"] += s12; C[f"like_req_{cls}_s24"] += s24
                C["like_req_s12_or_cert"] += (s12 or cert)
                spons[name][0] += 1; spons[name][1] += s12; spons[name][2] += s24
                spons[name][3] += (not submitted and disp is None)
            nonus = bool(countries - US)
            seg = "req" if req else ("us" if us_site else ("nonus" if nonus else "noloc"))
            C["like_all"] += 1; C[f"seg_{seg}"] += 1
            if not s24:
                C["like_nos24"] += 1; C[f"seg_{seg}_nos24"] += 1
        if pcd_t == "ACTUAL" and pcd and RULE <= pcd and (REF - pcd).days >= 365 and req:
            C["due_req"] += 1; C["due_req_s12"] += s12; C["due_req_ever"] += submitted; C["due_req_cert"] += cert
            C["due_req_none_nocert"] += (not submitted and disp is None)
        if pcd_t == "ACTUAL" and pcd and lite and status in ("COMPLETED", "TERMINATED", "ACTIVE_NOT_RECRUITING", "UNKNOWN", "SUSPENDED", "ENROLLING_BY_INVITATION", "RECRUITING"):
            if 2014 <= pcd.year <= 2016:
                C["lite_pre"] += 1; C["lite_pre_s12"] += s12
            if 2018 <= pcd.year <= 2020:
                C["lite_post"] += 1; C["lite_post_s12"] += s12
        # status rot: PCD (any type) at least 2 years before REF
        if pcd and (REF - pcd).days >= 730:
            grp = ("Completed" if status == "COMPLETED" else "Terminated" if status == "TERMINATED" else
                   "Unknown status" if status == "UNKNOWN" else "Still marked open/active" if status in OPEN else "Other")
            C["ended"] += 1; C[f"ended_{grp}"] += 1; C["ended_sub"] += submitted
            if not submitted:
                C["nores"] += 1; C[f"nores_{grp}"] += 1
    V = {
        "records": C["records"], "duplicates": C["dup"], "interventional": C["int"],
        "completed_int": C["comp"], "completed_int_posted_pct": pct(C["comp_posted"], C["comp"]),
        "completed_int_submitted_pct": pct(C["comp_sub"], C["comp"]),
        "win_n": C["win"], "win_submitted_pct": pct(C["win_sub"], C["win"]), "win_posted_pct": pct(C["win_posted"], C["win"]),
        "like_req_n": C["like_req"], "like_req_s12_pct": pct(C["like_req_s12"], C["like_req"]),
        "like_req_s24_pct": pct(C["like_req_s24"], C["like_req"]), "like_req_ever_pct": pct(C["like_req_ever"], C["like_req"]),
        "like_oth_n": C["like_oth"], "like_oth_s12_pct": pct(C["like_oth_s12"], C["like_oth"]),
        "like_oth_s24_pct": pct(C["like_oth_s24"], C["like_oth"]), "like_oth_ever_pct": pct(C["like_oth_ever"], C["like_oth"]),
        "like_req_s12_or_cert_pct": pct(C["like_req_s12_or_cert"], C["like_req"]),
        "due_req_n": C["due_req"], "due_req_s12_pct": pct(C["due_req_s12"], C["due_req"]),
        "due_req_ever_pct": pct(C["due_req_ever"], C["due_req"]), "due_req_cert_pct": pct(C["due_req_cert"], C["due_req"]),
        "due_req_none_nocert": C["due_req_none_nocert"],
        "lite_pre_s12_pct": pct(C["lite_pre_s12"], C["lite_pre"]), "lite_post_s12_pct": pct(C["lite_post_s12"], C["lite_post"]),
        "lite_pre_n": C["lite_pre"], "lite_post_n": C["lite_post"],
        "ended_n": C["ended"], "ended_sub_pct": pct(C["ended_sub"], C["ended"]),
        "pending_int": C["pending_int"], "fda_violation_flag": C["fda_violation_flag"],
    }
    for grp in ["Completed", "Terminated", "Unknown status", "Still marked open/active"]:
        V[f"ended_{grp}"] = C[f"ended_{grp}"]
        V[f"nores_share_{grp}"] = pct(C[f"nores_{grp}"], C["nores"])
    for cls in ["INDUSTRY", "NIH", "FED", "OTHER"]:
        V[f"like_req_{cls}_n"] = C[f"like_req_{cls}"]
        V[f"like_req_{cls}_s12_pct"] = pct(C[f"like_req_{cls}_s12"], C[f"like_req_{cls}"])
        V[f"like_req_{cls}_s24_pct"] = pct(C[f"like_req_{cls}_s24"], C[f"like_req_{cls}"])
    for seg in ["req", "us", "nonus", "noloc"]:
        V[f"seg_{seg}_pct_of_cohort"] = pct(C[f"seg_{seg}"], C["like_all"])
        V[f"seg_{seg}_pct_of_no_results_pile"] = pct(C[f"seg_{seg}_nos24"], C["like_nos24"])
    od_total = sum(v[3] for v in spons.values())
    V["overdue_like_total"] = od_total
    V["overdue_share_sponsors_100plus"] = pct(sum(v[3] for v in spons.values() if v[0] >= 100), od_total)
    V["overdue_share_sponsors_1to4"] = pct(sum(v[3] for v in spons.values() if v[0] <= 4), od_total)
    top = sorted(((v[0], k) for k, v in spons.items() if v[0] >= 100), reverse=True)
    V["sponsors_ge100"] = {k: {"n": spons[k][0], "s12_pct": pct(spons[k][1], spons[k][0]), "s24_pct": pct(spons[k][2], spons[k][0])} for _, k in top}

    # ---------------------------------------------------------------- compare with main path
    H = json.load(open(os.path.join(data, "headline_numbers.json")))
    who = {(r["dimension"], r["group"]): r for r in H["h4_who"]}
    sr = {r["status"]: r for r in H["h5_status_rot"]}
    pairs = [
        ("Records downloaded", V["records"], H["coverage"]["All records in API download"]),
        ("Interventional records", V["interventional"], H["coverage"]["Interventional"]),
        ("Completed interventional", V["completed_int"], H["h1_completed_int_posted"]["n"]),
        ("Completed interventional: % results posted", V["completed_int_posted_pct"], H["h1_completed_int_posted"]["pct"]),
        ("Completed interventional: % results submitted", V["completed_int_submitted_pct"], H["h1_completed_int_submitted"]["pct"]),
        ("Completed, PCD 2008-2023: n", V["win_n"], H["h1_completed_int_pcd2008_2023_submitted"]["n"]),
        ("Completed, PCD 2008-2023: % submitted", V["win_submitted_pct"], H["h1_completed_int_pcd2008_2023_submitted"]["pct"]),
        ("Completed, PCD 2008-2023: % posted", V["win_posted_pct"], H["h1_completed_int_pcd2008_2023_posted"]["pct"]),
        ("Probably required (like cohort): n", V["like_req_n"], H["h2_main"]["required_n"]),
        ("Probably required: % within 12 months", V["like_req_s12_pct"], H["h2_main"]["required_sub12"]["pct"]),
        ("Probably required: % within 24 months", V["like_req_s24_pct"], H["h2_main"]["required_sub24"]["pct"]),
        ("Probably required: % ever", V["like_req_ever_pct"], H["h2_main"]["required_ever"]["pct"]),
        ("Everything else (like cohort): n", V["like_oth_n"], H["h2_main"]["other_n"]),
        ("Everything else: % within 12 months", V["like_oth_s12_pct"], H["h2_main"]["other_sub12"]["pct"]),
        ("Everything else: % within 24 months", V["like_oth_s24_pct"], H["h2_main"]["other_sub24"]["pct"]),
        ("Everything else: % ever", V["like_oth_ever_pct"], H["h2_main"]["other_ever"]["pct"]),
        ("Due cohort (main proxy): n", V["due_req_n"], H["h2_main_due_all"]["n"]),
        ("Due cohort: % within 12 months", V["due_req_s12_pct"], H["h2_main_due_all"]["sub12"]["pct"]),
        ("Due cohort: % ever", V["due_req_ever_pct"], H["h2_main_due_all"]["ever"]["pct"]),
        ("Due cohort: % certification before deadline", V["due_req_cert_pct"], H["h2_main_due_all"]["cert_before_deadline"]["pct"]),
        ("Due cohort: no results and no certification (count)", V["due_req_none_nocert"], H["h7_main_due_not_submitted_no_cert"]),
        ("Drug/device + US site, PCD 2014-16: % within 12 months", V["lite_pre_s12_pct"], H["h3_lite_pre_2014_16_sub12"]["pct"]),
        ("Drug/device + US site, PCD 2018-20: % within 12 months", V["lite_post_s12_pct"], H["h3_lite_post_2018_20_sub12"]["pct"]),
        ("Trials >=2y past PCD: n", V["ended_n"], H["h5_ended_n"]),
        ("Trials >=2y past PCD: % submitted", V["ended_sub_pct"], H["h5_ended_submitted"]["pct"]),
        ("Trials >=2y past PCD: unknown status (count)", V["ended_Unknown status"], sr["Unknown status"]["n"]),
        ("No-results pile: % unknown status", V["nores_share_Unknown status"], sr["Unknown status"]["pct_of_no_results_pile"]),
        ("No-results pile: % still marked open", V["nores_share_Still marked open/active"], sr["Still marked open/active"]["pct_of_no_results_pile"]),
        ("Pending QC (interventional)", V["pending_int"], H["coverage"]["Interventional: results submitted but not yet posted (in QC)"]),
        ("FDAAA 801 violation flag (all records)", V["fda_violation_flag"], H["h7_fda_violation_flag_n"]),
        ("Industry, probably required: % within 12 months", V["like_req_INDUSTRY_s12_pct"], who[("Lead sponsor", "Industry")]["pct_12m"]),
        ("Industry, probably required: % within 24 months", V["like_req_INDUSTRY_s24_pct"], who[("Lead sponsor", "Industry")]["pct_24m"]),
        ("NIH, probably required: % within 24 months", V["like_req_NIH_s24_pct"], who[("Lead sponsor", "NIH")]["pct_24m"]),
        ("Universities etc., probably required: % within 12 months", V["like_req_OTHER_s12_pct"], who[("Lead sponsor", "Universities, hospitals & non-profits")]["pct_12m"]),
        ("Universities etc., probably required: % within 24 months", V["like_req_OTHER_s24_pct"], who[("Lead sponsor", "Universities, hospitals & non-profits")]["pct_24m"]),
    ]
    seg = {r["segment"]: r for r in H["h2_segments"] if r["sponsor_group"] == "All"}
    size = {r["sponsor_size"]: r for r in H["h6_by_sponsor_size"]}
    pairs += [
        ("Like cohort: probably required, % of cohort", V["seg_req_pct_of_cohort"], seg["Probably required"]["pct_of_cohort"]),
        ("Like cohort: non-US-only, not required, % of cohort", V["seg_nonus_pct_of_cohort"], seg["Not required, non-US sites only"]["pct_of_cohort"]),
        ("No-results-at-24m pile: % probably required", V["seg_req_pct_of_no_results_pile"], seg["Probably required"]["pct_of_no_results_pile"]),
        ("No-results-at-24m pile: % not required, US site", V["seg_us_pct_of_no_results_pile"], seg["Not required, has a US site"]["pct_of_no_results_pile"]),
        ("No-results-at-24m pile: % non-US-only, not required", V["seg_nonus_pct_of_no_results_pile"], seg["Not required, non-US sites only"]["pct_of_no_results_pile"]),
        ("Probably required, no results and no certificate (count)", V["overdue_like_total"], H["h6_like_no_results_no_cert_n"]),
        ("... share with sponsors of 100+ such trials", V["overdue_share_sponsors_100plus"], size["100+ trials"]["pct_of_no_results_no_cert"]),
        ("... share with sponsors of 1-4 such trials", V["overdue_share_sponsors_1to4"], size["1-4 trials"]["pct_of_no_results_no_cert"]),
    ]
    # sponsor table
    sp_main = {}
    with open(os.path.join(data, "h6_largest_sponsors_probably_required.csv")) as f:
        for r in csv.DictReader(f):
            sp_main[r["sponsor"]] = r
    for k, v in V["sponsors_ge100"].items():
        m = sp_main.get(k)
        pairs.append((f"Sponsor '{k}': n", v["n"], int(m["n"]) if m else None))
        pairs.append((f"Sponsor '{k}': % within 24 months", round(100.0 * spons[k][2] / spons[k][0], 1), float(m["pct_24m"]) if m else None))
    # server-side counts from NLM's own search engine (04_server_counts.py)
    srv_p = os.path.join(data, "server_counts.json")
    srv_rows = []
    if os.path.exists(srv_p):
        S = json.load(open(srv_p))["counts"]
        local = {"all_records": V["records"], "interventional": V["interventional"], "int_completed": V["completed_int"],
                 "int_completed_results": C["comp_posted"], "int_completed_pcd2008_2023": V["win_n"],
                 "int_completed_pcd2008_2023_results": C["win_posted"], "fdaaa801_violation": V["fda_violation_flag"]}
        for k in S:
            if k not in local:
                local[k] = C.get("srv_" + k, 0)
        for k, sv in S.items():
            lv = local.get(k)
            dif = None if sv is None or lv is None else lv - sv
            srv_rows.append({"query": k, "nlm_server_count": sv, "our_download_count": lv, "difference": dif,
                             "pct_difference": round(100.0 * dif / sv, 3) if sv else None})
        with open(os.path.join(data, "verification_server_counts.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(srv_rows[0].keys())); w.writeheader(); w.writerows(srv_rows)
        V["server_max_abs_pct_difference"] = max(abs(r["pct_difference"]) for r in srv_rows if r["pct_difference"] is not None)
    rows, bad = [], 0
    for label, a, b in pairs:
        ok = a is not None and b is not None and abs(float(a) - float(b)) <= 0.051
        bad += (not ok)
        rows.append({"quantity": label, "second_path": a, "main_path": b, "match": "yes" if ok else "NO"})
    with open(os.path.join(data, "verification_table.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["quantity", "second_path", "main_path", "match"])
        w.writeheader(); w.writerows(rows)
    V["n_compared"] = len(rows); V["n_mismatch"] = bad
    json.dump(V, open(os.path.join(data, "verify_numbers.json"), "w"), indent=1)
    print(f"compared {len(rows)} quantities; mismatches {bad}")
    for r in rows:
        if r["match"] == "NO":
            print("  MISMATCH", r)


if __name__ == "__main__":
    main()
