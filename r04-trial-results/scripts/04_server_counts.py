"""R04 step 4: third check - ask NLM's own search engine for counts (filter.advanced + countTotal).

These counts never touch our download or parser; 05_verify.py compares them with the same
definitions computed from the raw pages.

Usage: python3 -I 04_server_counts.py <out_json>
~45 requests at one every 2 s.
"""
import json, sys, time, urllib.parse, urllib.request

BASE = "https://clinicaltrials.gov/api/v2/studies"
UA = "research; public-data report"
INT = "AREA[StudyType]INTERVENTIONAL"
COMP = "AREA[OverallStatus]COMPLETED"
RES = "AREA[HasResults]true"
FDA = "(AREA[IsFDARegulatedDrug]true OR AREA[IsFDARegulatedDevice]true)"
PCD_ACT = "AREA[PrimaryCompletionDateType]ACTUAL AND AREA[PrimaryCompletionDate]RANGE[2017-01-18,2024-11-20]"
NOTW = "NOT AREA[OverallStatus]WITHDRAWN"
USLOC = 'AREA[LocationCountry]"United States"'

Q = {
    "all_records": None,
    "interventional": INT,
    "int_completed": f"{INT} AND {COMP}",
    "int_completed_results": f"{INT} AND {COMP} AND {RES}",
    "int_completed_pcd2008_2023": f"{INT} AND {COMP} AND AREA[PrimaryCompletionDate]RANGE[2008-01-01,2023-12-31]",
    "int_completed_pcd2008_2023_results": f"{INT} AND {COMP} AND AREA[PrimaryCompletionDate]RANGE[2008-01-01,2023-12-31] AND {RES}",
    "int_unknown_status": f"{INT} AND AREA[OverallStatus]UNKNOWN",
    "int_withdrawn": f"{INT} AND AREA[OverallStatus]WITHDRAWN",
    "fda_us_actual_2017_2024": f"{INT} AND {FDA} AND {PCD_ACT} AND {NOTW} AND {USLOC}",
    "fda_us_actual_2017_2024_results": f"{INT} AND {FDA} AND {PCD_ACT} AND {NOTW} AND {USLOC} AND {RES}",
    "fdaaa801_violation": "AREA[FDAAA801Violation]true",
}
for y in range(2008, 2026):
    Q[f"int_completed_pcd{y}"] = f"{INT} AND {COMP} AND AREA[PrimaryCompletionDate]RANGE[{y}-01-01,{y}-12-31]"
    Q[f"int_completed_pcd{y}_results"] = f"{INT} AND {COMP} AND AREA[PrimaryCompletionDate]RANGE[{y}-01-01,{y}-12-31] AND {RES}"


def count(expr):
    params = {"countTotal": "true", "pageSize": 1, "fields": "NCTId"}
    if expr:
        params["filter.advanced"] = expr
    url = BASE + "?" + urllib.parse.urlencode(params)
    delay = 5
    for _ in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["totalCount"]
        except Exception as e:  # noqa: BLE001
            print("retry", e, flush=True); time.sleep(delay); delay *= 2
    return None


def main():
    out = {"queried_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "queries": Q, "counts": {}}
    vreq = urllib.request.Request("https://clinicaltrials.gov/api/v2/version", headers={"User-Agent": UA})
    out["version"] = json.load(urllib.request.urlopen(vreq, timeout=60))
    for k, q in Q.items():
        out["counts"][k] = count(q)
        print(k, out["counts"][k], flush=True)
        time.sleep(2)
    json.dump(out, open(sys.argv[1], "w"), indent=1)


if __name__ == "__main__":
    main()
