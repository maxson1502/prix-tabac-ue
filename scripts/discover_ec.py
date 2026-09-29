"""Temporary: explore the TEDB v5 web app to find its data API."""
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (prix-tabac-ue data refresh; +https://github.com/maxson1502/prix-tabac-ue)"}
BASE = "https://ec.europa.eu/taxation_customs/tedb/"
API = BASE + "rest-api/"
PATS = [r"baseUrl", r"rest-api", r"i18n", r"tobaccoConsumption", r"[Ww]eighted", r"WAP", r"\.get\(", r"\.post\("]


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=60, **kw)
    return r


def main():
    home = get(BASE).text
    js = sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', home)))
    seen, queue = set(), [requests.compat.urljoin(BASE, j) for j in js if j.startswith("/taxation")]
    while queue:
        u = queue.pop(0)
        if u in seen or len(seen) > 40:
            continue
        seen.add(u)
        t = get(u).text
        for c in re.findall(r'["\'](?:\./)?(chunk-[A-Z0-9]+\.js)["\']', t):
            queue.append(requests.compat.urljoin(u, c))
        if "polyfills" in u or "scripts-" in u:
            continue
        for m in re.finditer(r"TRANSLATIONS\s*[:=]\s*\"", t):
            print("   const:", u.split("/")[-1], t[max(0, m.start() - 2500): m.end() + 2500].replace("\n", " "))
        for m in list(re.finditer(r"\.setPath\(", t))[:80]:
            print("   path:", u.split("/")[-1], t[max(0, m.start() - 80): m.end() + 220].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
