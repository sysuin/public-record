"""R04 step 2: flatten raw API pages into one row per study.

Usage: python3 -I 02_parse.py <raw_dir> <out_parquet>
Reads <raw_dir>/pages/page_*.json.gz (JSON only; nothing is executed from raw_dir).
"""
import glob, gzip, json, os, sys
import pandas as pd

US_PLACES = {"United States", "Puerto Rico", "Guam", "Virgin Islands (U.S.)", "U.S. Virgin Islands",
             "American Samoa", "Northern Mariana Islands", "United States Minor Outlying Islands"}


def g(d, *path):
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def row(s):
    ps = s.get("protocolSection", {})
    st = ps.get("statusModule", {})
    de = ps.get("designModule", {})
    sp = ps.get("sponsorCollaboratorsModule", {})
    ov = ps.get("oversightModule", {})
    locs = g(ps, "contactsLocationsModule", "locations") or []
    countries = [l.get("country") for l in locs if l.get("country")]
    cset = set(countries)
    itypes = sorted({i.get("type") for i in (g(ps, "armsInterventionsModule", "interventions") or []) if i.get("type")})
    misc = g(s, "derivedSection", "miscInfoModule") or {}
    trk = misc.get("submissionTracking") or {}
    subs = trk.get("submissionInfos") or []
    ann = g(s, "annotationSection", "annotationModule") or {}
    unp = ann.get("unpostedAnnotation") or {}
    viol = g(ann, "violationAnnotation", "violationEvents") or []
    why = st.get("whyStopped")
    return {
        "nct_id": g(ps, "identificationModule", "nctId"),
        "study_type": de.get("studyType"),
        "phases": "|".join(de.get("phases") or []),
        "primary_purpose": g(de, "designInfo", "primaryPurpose"),
        "allocation": g(de, "designInfo", "allocation"),
        "enroll_count": g(de, "enrollmentInfo", "count"),
        "enroll_type": g(de, "enrollmentInfo", "type"),
        "overall_status": st.get("overallStatus"),
        "last_known_status": st.get("lastKnownStatus"),
        "why_stopped": why,
        "status_verified": st.get("statusVerifiedDate"),
        "start_date": g(st, "startDateStruct", "date"), "start_type": g(st, "startDateStruct", "type"),
        "pcd": g(st, "primaryCompletionDateStruct", "date"), "pcd_type": g(st, "primaryCompletionDateStruct", "type"),
        "cd": g(st, "completionDateStruct", "date"), "cd_type": g(st, "completionDateStruct", "type"),
        "first_submit": st.get("studyFirstSubmitDate"),
        "first_post": g(st, "studyFirstPostDateStruct", "date"),
        "results_first_submit": st.get("resultsFirstSubmitDate"),
        "results_first_submit_qc": st.get("resultsFirstSubmitQcDate"),
        "results_first_post": g(st, "resultsFirstPostDateStruct", "date"),
        "disp_first_submit": st.get("dispFirstSubmitDate"),
        "disp_first_post": g(st, "dispFirstPostDateStruct", "date"),
        "results_waived": st.get("resultsWaived"),
        "delayed_posting": st.get("delayedPosting"),
        "last_update_submit": st.get("lastUpdateSubmitDate"),
        "last_update_post": g(st, "lastUpdatePostDateStruct", "date"),
        "est_results_submit": trk.get("estimatedResultsFirstSubmitDate"),
        "first_mcp_post": g(trk, "firstMcpInfo", "postDateStruct", "date"),
        "n_submission_cycles": len(subs),
        "n_resets": sum(1 for x in subs if x.get("resetDate")),
        "sponsor": g(sp, "leadSponsor", "name"),
        "sponsor_class": g(sp, "leadSponsor", "class"),
        "resp_party_type": g(sp, "responsibleParty", "type"),
        "fda_drug": ov.get("isFdaRegulatedDrug"),
        "fda_device": ov.get("isFdaRegulatedDevice"),
        "unapproved_device": ov.get("isUnapprovedDevice"),
        "ppsd": ov.get("isPpsd"),
        "us_export": ov.get("isUsExport"),
        "has_dmc": ov.get("oversightHasDmc"),
        "fdaaa801_violation": ov.get("fdaaa801Violation"),
        "n_violation_events": len(viol),
        "violation_types": "|".join(sorted({v.get("type") for v in viol if v.get("type")})),
        "unposted_events": len(unp.get("unpostedEvents") or []),
        "n_locations": len(locs),
        "n_countries": len(cset),
        "has_us_site": bool(cset & US_PLACES),
        "has_nonus_site": bool(cset - US_PLACES),
        "countries": "|".join(sorted(cset)) if len(cset) <= 3 else "|".join(sorted(cset)[:3]) + f"|+{len(cset)-3}",
        "intervention_types": "|".join(itypes),
        "has_results": s.get("hasResults"),
    }


def main():
    raw, out = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(raw, "pages", "page_*.json.gz")))
    rows = []
    for f in files:
        d = json.loads(gzip.open(f).read())
        rows.extend(row(s) for s in d["studies"])
    df = pd.DataFrame(rows)
    n0 = len(df)
    dups = df.nct_id.duplicated().sum()
    df = df.drop_duplicates("nct_id")
    print(f"pages {len(files)} studies {n0} duplicates {dups} unique {len(df)}")
    df.to_parquet(out, index=False)


if __name__ == "__main__":
    main()
