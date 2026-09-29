"""Temporary: explore the TEDB v5 REST API (Commission) to locate the cigarette WAP."""
import json
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (prix-tabac-ue data refresh; +https://github.com/maxson1502/prix-tabac-ue)"}
BASE = "https://ec.europa.eu/taxation_customs/tedb/"
API = BASE + "rest-api/"


def main():
    r = requests.get(API + "configurations", headers=UA, timeout=60)
    print("CONF", r.status_code, r.text[:2500].replace("\n", " "))
    r = requests.get(API + "translations?lang=en", headers=UA, timeout=60)
    print("TR", r.status_code, len(r.text))
    try:
        tr = r.json()
        flat = {}

        def walk(o, p=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, p + "." + k if p else k)
            else:
                flat[p] = o
        walk(tr)
        for k, v in flat.items():
            if re.search(r"weighted|WAP|average|tobacco|cigarette", str(v) + k, re.I):
                print("  tr:", k, "=", str(v)[:160])
    except ValueError:
        print(r.text[:500])
    for u in ["chunk-CBUUBX5B.js", "chunk-66BRNIPF.js"]:
        t = requests.get(BASE + "app/" + u, headers=UA, timeout=60).text
        for m in list(re.finditer(r"\.simpleSearch\(|searchCriterion\s*=|searchCriterion:", t))[:12]:
            print("   ctx:", u, t[max(0, m.start() - 400): m.end() + 400].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
