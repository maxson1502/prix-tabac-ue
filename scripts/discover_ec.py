"""Temporary: explore the TEDB v5 REST API (Commission) to locate the cigarette WAP."""
import json
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (prix-tabac-ue data refresh; +https://github.com/maxson1502/prix-tabac-ue)"}
BASE = "https://ec.europa.eu/taxation_customs/tedb/"
API = BASE + "rest-api/"


def show(label, r, n=2500):
    print(label, r.status_code, r.headers.get("content-type"), r.text[:n].replace("\n", " "))


def main():
    conf = requests.get(API + "configurations", headers=UA, timeout=60).json()
    print("CONF keys", list(conf.keys()))
    for k, v in conf.items():
        s = json.dumps(v)
        if re.search(r"TOBACCO|taxType|memberState", k + s[:20000], re.I):
            print("  conf", k, s[:1500])
    t = requests.get(BASE + "app/chunk-ANML7FQG.js", headers=UA, timeout=60).text
    for m in list(re.finditer(r"BENEFICIARY\s*=|taxSection\s*=\s*\"|\.RATES?\s*=|\"rates?\"", t))[:6]:
        print("   sect:", t[max(0, m.start() - 300): m.end() + 900].replace("\n", " "))
    t = requests.get(BASE + "app/chunk-CBUUBX5B.js", headers=UA, timeout=60).text
    for m in list(re.finditer(r"situationOn|selectedTaxTypes|taxTypes", t))[:8]:
        print("   form:", t[max(0, m.start() - 250): m.end() + 250].replace("\n", " "))
    for date in ("2026/07/01", "2026-07-01"):
        for tt in (["EDU_TOBACCO"], ["edu_tobacco"]):
            body = {"searchForm": {"selectedTaxTypes": tt, "selectedMemberStates": [], "situationOn": date,
                                   "historized": False, "keywords": ""},
                    "availableFacets": None, "selectedFacets": None, "sort": None}
            r = requests.post(API + "simpleSearch", json=body, headers=UA, timeout=120)
            show(f"SEARCH {date} {tt}", r, 3000)
    return 0


if __name__ == "__main__":
    sys.exit(main())
