#!/usr/bin/env python3
"""Refresh the page data: Commission releases (data/ec.json) and Eurostat indices (data/hicp.json).

Run daily by .github/workflows/update-data.yml. The page loads these two files at every opening;
their copies embedded in index.html (fallback when the site is unreachable) are refreshed too.
Nothing is written unless the new data pass every check; a failing source makes the script exit 1
(GitHub then e-mails the repository owner) while the other source is still updated.

  python scripts/update_data.py            # fetch, check, write
  python scripts/update_data.py --dry-run  # fetch, check, print what would change
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EC_PATH = ROOT / "data" / "ec.json"
HICP_PATH = ROOT / "data" / "hicp.json"
PAGE_PATH = ROOT / "index.html"
UA = {"User-Agent": "prix-tabac-ue data refresh (+https://github.com/maxson1502/prix-tabac-ue)"}

GEO = {"AT": "Autriche", "BE": "Belgique", "BG": "Bulgarie", "HR": "Croatie", "CY": "Chypre", "CZ": "Tchéquie",
       "DK": "Danemark", "EE": "Estonie", "FI": "Finlande", "FR": "France", "DE": "Allemagne", "EL": "Grèce",
       "HU": "Hongrie", "IE": "Irlande", "IT": "Italie", "LV": "Lettonie", "LT": "Lituanie", "LU": "Luxembourg",
       "MT": "Malte", "NL": "Pays-Bas", "PL": "Pologne", "PT": "Portugal", "RO": "Roumanie", "SK": "Slovaquie",
       "SI": "Slovénie", "ES": "Espagne", "SE": "Suède"}
COUNTRIES = sorted(GEO.values())


class DataError(Exception):
    pass


def today():
    return dt.date.today().isoformat()


def http_get(url, **kw):
    r = requests.get(url, headers=UA, timeout=120, **kw)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- Eurostat (HICP, monthly)

EUROSTAT_URL = ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/prc_hicp_minr/"
                "M.I25.TOTAL+CP023+CP02301.?format=SDMX-CSV&startPeriod=2023-01")
POSTES = {"CP02301": "cig", "CP023": "tob", "TOTAL": "tot"}
EUROSTAT_GEO = dict(GEO, EU27_2020="UE-27")


def parse_eurostat(text):
    """SDMX-CSV 1.0 -> {"months", "cig", "tob", "tot", "meta"}; same checks as the page's former CSV import."""
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if len(rows) < 2:
        raise DataError("Eurostat : réponse vide")
    head = [h.strip().lower() for h in rows[0]]

    def col(*names):
        for n in names:
            if n in head:
                return head.index(n)
        return -1

    c_p, c_g, c_t, c_v = col("coicop18", "coicop"), col("geo"), col("time_period", "time"), col("obs_value", "value")
    c_u, c_l = col("unit"), col("last update")
    if min(c_p, c_g, c_t, c_v) < 0:
        raise DataError(f"Eurostat : colonnes inattendues {rows[0]}")
    data, months, last = {"cig": {}, "tob": {}, "tot": {}}, set(), None
    for x in rows[1:]:
        if len(x) <= c_v or (c_u >= 0 and x[c_u].strip() != "I25"):
            continue
        p, g, t = POSTES.get(x[c_p].strip()), EUROSTAT_GEO.get(x[c_g].strip()), x[c_t].strip().replace("M", "-")
        try:
            v = float(x[c_v])
        except ValueError:
            continue
        if not p or not g or not re.fullmatch(r"\d{4}-\d{2}", t) or t < "2023-01":
            continue
        data[p].setdefault(g, {})[t] = v
        months.add(t)
        if c_l >= 0:
            m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", x[c_l].strip())
            if m:
                y = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
                d = f"{y:04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
                last = max(last or d, d)
    need = COUNTRIES + ["UE-27"]
    miss = [f"{g} ({p})" for p in data for g in need if g not in data[p]]
    if miss:
        raise DataError("Eurostat : séries manquantes " + ", ".join(miss[:6]))
    out, y, m = [], 2023, 1
    while True:
        k = f"{y}-{m:02d}"
        if k not in months or not all(k in data[p][g] for p in data for g in need):
            break
        out.append(k)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    if "2024-12" not in out:
        raise DataError("Eurostat : les mois de janvier 2023 à décembre 2024 doivent être complets")
    h = {"months": out}
    for p in ("cig", "tob", "tot"):
        h[p] = {g: [round(data[p][g][k], 2) for k in out] for g in need}
    h["meta"] = {"eurostat": last}
    return h


def update_eurostat(old):
    new = parse_eurostat(http_get(EUROSTAT_URL).content.decode("utf-8"))
    if len(new["months"]) < len(old["months"]):
        raise DataError(f"Eurostat : {len(new['months'])} mois reçus, {len(old['months'])} déjà publiés ; rien n'est remplacé")
    new["meta"]["eurostat"] = new["meta"]["eurostat"] or old.get("meta", {}).get("eurostat")
    same = all(new[k] == old[k] for k in ("months", "cig", "tob", "tot")) and new["meta"]["eurostat"] == old["meta"].get("eurostat")
    if same:
        return old, "Eurostat : aucun changement"
    new["meta"]["updated"] = today()
    return new, f"Eurostat : {old['months'][-1]} -> {new['months'][-1]}, mise à jour Eurostat du {new['meta']['eurostat']}"


# ---------------------------------------------------------------- Commission (WAP of cigarettes, twice a year)

def fetch_ec_latest():
    """Return (release date 'YYYY-MM', {country: € per pack of 20}) for the latest Commission release."""
    raise DataError("Commission : lecture de la source pas encore disponible")


def update_ec(old):
    date, wap = fetch_ec_latest()
    if sorted(wap) != COUNTRIES:
        raise DataError(f"Commission : pays attendus {len(COUNTRIES)}, reçus {len(wap)} ({', '.join(sorted(set(COUNTRIES) ^ set(wap)))})")
    bad = {k: v for k, v in wap.items() if not 1 <= v <= 40}
    if bad:
        raise DataError(f"Commission : valeurs hors plage {bad}")
    rel = {r["date"]: r for r in old["releases"]}
    last = max(rel)
    if date < last and date not in rel:
        return old, f"Commission : relevé {date} plus ancien que le dernier connu ({last}), ignoré"
    if date in rel:
        diff = {k: (rel[date]["wap"][k], v) for k, v in wap.items() if abs(rel[date]["wap"][k] - v) > 0.02}
        if diff:
            raise DataError(f"Commission : le relevé {date} déjà enregistré diffère de la source {diff} ; vérification manuelle nécessaire")
        return old, f"Commission : relevé {date} déjà à jour"
    new = dict(old, updated=today(), releases=old["releases"] + [{"date": date, "wap": {k: wap[k] for k in COUNTRIES}}])
    return new, f"Commission : nouveau relevé {date} ajouté"


# ---------------------------------------------------------------- writing

def dump_ec(ec):
    lines = ",\n".join("  " + json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in ec["releases"])
    head = json.dumps({k: v for k, v in ec.items() if k != "releases"}, ensure_ascii=False, indent=1)[:-2]
    return head + ',\n "releases": [\n' + lines + "\n ]\n}\n"


def dump_hicp(h):
    return json.dumps(h, ensure_ascii=False, separators=(",", ":")) + "\n"


def embed(page, id_, obj):
    blob = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    pat = re.compile(r'(<script type="application/json" id="%s">)(.*?)(</script>)' % id_, re.S)
    if not pat.search(page):
        raise DataError(f"index.html : bloc {id_} introuvable")
    return pat.sub(lambda m: m.group(1) + blob + m.group(3), page, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-ec", action="store_true")
    ap.add_argument("--skip-eurostat", action="store_true")
    a = ap.parse_args()
    ec = json.loads(EC_PATH.read_text(encoding="utf-8"))
    h = json.loads(HICP_PATH.read_text(encoding="utf-8"))
    errors = []
    for name, skip, fn in (("ec", a.skip_ec, update_ec), ("hicp", a.skip_eurostat, update_eurostat)):
        if skip:
            continue
        try:
            new, msg = fn(ec if name == "ec" else h)
            print(msg)
            if name == "ec":
                ec = new
            else:
                h = new
        except (DataError, requests.RequestException) as e:
            print(f"ERREUR {e}", file=sys.stderr)
            errors.append(str(e))
    if a.dry_run:
        print("(essai : rien n'est écrit)")
    else:
        EC_PATH.write_text(dump_ec(ec), encoding="utf-8")
        HICP_PATH.write_text(dump_hicp(h), encoding="utf-8")
        page = PAGE_PATH.read_text(encoding="utf-8")
        PAGE_PATH.write_text(embed(embed(page, "ec-data", ec), "hicp-data", h), encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
