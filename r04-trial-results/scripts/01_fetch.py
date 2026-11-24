"""R04 step 1: download every study record from the ClinicalTrials.gov API v2 (NLM), selected fields only.

Usage: python3 -I 01_fetch.py <raw_dir>
Writes <raw_dir>/pages/page_NNNNN.json.gz, <raw_dir>/fetch_log.csv, <raw_dir>/meta/{version,metadata,size}_{start,end}.json
Resumable: re-running continues from the last saved page token.
Rate: one request every ~1.3 s (~46/min), below NLM's ~50/min guidance; exponential back-off on errors.
"""
import csv, gzip, json, os, sys, time, urllib.parse, urllib.request, hashlib

BASE = "https://clinicaltrials.gov/api/v2"
UA = "research; public-data report"
FIELDS = ",".join([
    "protocolSection.identificationModule.nctId",
    "protocolSection.statusModule",
    "protocolSection.designModule.studyType",
    "protocolSection.designModule.phases",
    "protocolSection.designModule.designInfo.primaryPurpose",
    "protocolSection.designModule.designInfo.allocation",
    "protocolSection.designModule.enrollmentInfo",
    "protocolSection.sponsorCollaboratorsModule.leadSponsor",
    "protocolSection.sponsorCollaboratorsModule.responsibleParty.type",
    "protocolSection.oversightModule",
    "protocolSection.contactsLocationsModule.locations.country",
    "protocolSection.armsInterventionsModule.interventions.type",
    "hasResults",
    "derivedSection.miscInfoModule",
    "annotationSection",
])
PAGE_SIZE = 1000
GAP = 1.3


def get(url, tries=8):
    delay = 5
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read()
        except Exception as e:  # noqa: BLE001
            print(f"  error {e!r}; retry {i+1}/{tries} in {delay}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 300)
    raise SystemExit(f"giving up on {url}")


def save_meta(raw, tag):
    os.makedirs(os.path.join(raw, "meta"), exist_ok=True)
    for name, path in [("version", "/version"), ("size", "/stats/size"), ("metadata", "/studies/metadata")]:
        st, body = get(BASE + path)
        with open(os.path.join(raw, "meta", f"{name}_{tag}.json"), "wb") as f:
            f.write(body)
        time.sleep(GAP)
    return json.load(open(os.path.join(raw, "meta", f"version_{tag}.json")))


def main():
    raw = sys.argv[1]
    pages = os.path.join(raw, "pages"); os.makedirs(pages, exist_ok=True)
    state_p = os.path.join(raw, "state.json")
    log_p = os.path.join(raw, "fetch_log.csv")
    if os.path.exists(state_p):
        state = json.load(open(state_p))
    else:
        v = save_meta(raw, "start")
        print("start", v, flush=True)
        state = {"page": 0, "token": None, "done": False, "start_version": v}
        with open(log_p, "w", newline="") as f:
            csv.writer(f).writerow(["page", "utc", "n_studies", "bytes", "sha256_16", "total_count", "url"])
    while not state["done"]:
        params = {"fields": FIELDS, "pageSize": PAGE_SIZE, "format": "json"}
        if state["page"] == 0:
            params["countTotal"] = "true"
        if state["token"]:
            params["pageToken"] = state["token"]
        url = BASE + "/studies?" + urllib.parse.urlencode(params)
        st, body = get(url)
        d = json.loads(body)
        n = len(d.get("studies", []))
        p = state["page"] + 1
        with gzip.open(os.path.join(pages, f"page_{p:05d}.json.gz"), "wb") as f:
            f.write(body)
        with open(log_p, "a", newline="") as f:
            csv.writer(f).writerow([p, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), n, len(body),
                                    hashlib.sha256(body).hexdigest()[:16], d.get("totalCount", ""),
                                    url.split("&pageToken")[0] if p > 1 else url])
        state["page"] = p
        state["token"] = d.get("nextPageToken")
        if p == 1:
            state["total_count"] = d.get("totalCount")
        if not state["token"]:
            state["done"] = True
        json.dump(state, open(state_p, "w"))
        if p % 25 == 0 or state["done"]:
            print(f"page {p} n={n} total={state.get('total_count')}", flush=True)
        time.sleep(GAP)
    v = save_meta(raw, "end")
    print("end", v, "start", state["start_version"], flush=True)
    if v.get("dataTimestamp") != state["start_version"].get("dataTimestamp"):
        print("WARNING: dataTimestamp changed during download", flush=True)


if __name__ == "__main__":
    main()
