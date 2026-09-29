"""Temporary: explore the TEDB v5 web app to find its data API."""
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (prix-tabac-ue data refresh; +https://github.com/maxson1502/prix-tabac-ue)"}
BASE = "https://ec.europa.eu/taxation_customs/tedb/"


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=60, **kw)
    print(f"GET {url} -> {r.status_code} {r.headers.get('content-type')} {len(r.content)} bytes")
    return r


def main():
    home = get(BASE).text
    env = re.search(r'src="([^"]*angular-env\.js[^"]*)"', home)
    if env:
        print("==== angular-env.js")
        print(get(requests.compat.urljoin(BASE, env.group(1))).text[:3000])
    js = sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', home)))
    seen = set()
    queue = [requests.compat.urljoin(BASE, j) for j in js if "webtools" not in j and "europa.eu/wel" not in j]
    while queue:
        u = queue.pop(0)
        if u in seen or len(seen) > 40:
            continue
        seen.add(u)
        try:
            t = get(u).text
        except Exception as e:  # noqa: BLE001
            print("  error", e)
            continue
        for c in re.findall(r'["\'](\./)?(chunk-[A-Z0-9]+\.js)["\']', t):
            queue.append(requests.compat.urljoin(u, c[1]))
        hits = set()
        for m in re.finditer(r'["`\']([^"`\'\s]{0,120}(?:api|rest|/search|tax(?:es)?/|tobacco|excise|export|download|wap|weighted)[^"`\'\s]{0,120})["`\']', t, re.I):
            hits.add(m.group(1))
        for h in sorted(hits)[:150]:
            print("   str:", h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
