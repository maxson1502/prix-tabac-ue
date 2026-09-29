"""Temporary: explore the TEDB v5 REST API (Commission) to locate the cigarette WAP."""
import json
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (prix-tabac-ue data refresh; +https://github.com/maxson1502/prix-tabac-ue)"}
API = "https://ec.europa.eu/taxation_customs/tedb/rest-api/"


def main():
    conf = requests.get(API + "configurations", headers=UA, timeout=60).json()
    names = [t["name"] for k in conf["taxTypes"] for t in conf["taxTypes"][k]]
    print("TAXTYPES", names)
    tob = [n for n in names if "TOBAC" in n.upper()] or ["EDU_TOBACCO"]
    cs = conf["countries"]
    print("COUNTRY sample", json.dumps(cs[:2])[:600])
    ids = [c["id"] for c in cs]
    print("COUNTRIES", [(c["id"], c.get("defaultCountryCode")) for c in cs])
    ok = None
    for date in ("2026/07/01", "2026-07-01", "01/07/2026", ""):
        for ms in (ids, [str(i) for i in ids]):
            for hist in ("false", False):
                body = {"searchForm": {"selectedTaxTypes": tob, "selectedMemberStates": ms, "situationOn": date,
                                       "historized": hist, "keywords": ""},
                        "availableFacets": None, "selectedFacets": None, "sort": None}
                r = requests.post(API + "simpleSearch", json=body, headers=UA, timeout=120)
                print("SEARCH", repr(date), type(ms[0]).__name__, repr(hist), r.status_code, r.text[:300].replace("\n", " "))
                if r.status_code == 200 and not ok:
                    ok = r.json()
    if ok:
        res = ok.get("result") or []
        print("RESULT keys", list(ok.keys()), "n", len(res))
        for x in res[:30]:
            print("  row", json.dumps(x)[:400])
        for x in res[:2]:
            for sec in ("rate", "generic"):
                r = requests.get(API + f"tax/{sec}", params={"taxId": x["taxId"], "versionDate": x["versionDate"], "isEuro": "true"}, headers=UA, timeout=120)
                print("SECTION", sec, x.get("countryCode"), r.status_code, r.text[:6000].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
