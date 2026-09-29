"""Temporary: print what the EC tobacco excise pages expose, to design the parser."""
import io
import re
import sys

import pdfplumber
import requests

UA = {"User-Agent": "Mozilla/5.0 (prix-tabac-ue data refresh; +https://github.com/maxson1502/prix-tabac-ue)"}
PAGES = [
    "https://taxation-customs.ec.europa.eu/taxation/excise-duties/excise-duties-tobacco_en",
    "https://taxation-customs.ec.europa.eu/taxation/excise-taxes/excise-duties-tobacco_en",
    "https://taxation-customs.ec.europa.eu/taxation/excise-duties/excise-duties-tobacco/excise-duty-tables_en",
    "https://ec.europa.eu/taxation_customs/tedb/",
]


def get(url):
    r = requests.get(url, headers=UA, timeout=60, allow_redirects=True)
    print(f"GET {url} -> {r.status_code} {r.headers.get('content-type')} {len(r.content)} bytes (final {r.url})")
    return r


def main():
    docs = []
    for p in PAGES:
        try:
            r = get(p)
        except Exception as e:  # noqa: BLE001
            print("  error", e)
            continue
        if r.status_code != 200:
            continue
        links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        for l in links:
            if re.search(r"(tobacco|tabac|excise|\.pdf|\.xlsx?|download|tedb|api)", l, re.I):
                print("   link:", l)
                if re.search(r"(\.pdf|\.xlsx?|download)", l, re.I) and re.search(r"(tobacco|part_iii|part-iii|excise)", l, re.I):
                    docs.append(requests.compat.urljoin(r.url, l))
        for s in sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', r.text)))[:20]:
            print("   script:", s)
    seen = set()
    for d in docs:
        if d in seen:
            continue
        seen.add(d)
        print("\n==== DOC", d)
        try:
            r = get(d)
        except Exception as e:  # noqa: BLE001
            print("  error", e)
            continue
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            print("  not a pdf, first bytes:", r.content[:200])
            continue
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            print("  pages:", len(pdf.pages))
            for i, page in enumerate(pdf.pages):
                t = page.extract_text() or ""
                if i < 2 or re.search(r"weighted average|WAP|average price", t, re.I):
                    print(f"  ---- page {i + 1}")
                    print(t[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
