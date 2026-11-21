#!/usr/bin/env python3
"""Build the five Zanzibar region CSVs in location-files/ from sources/zanzibar-postcodes/zanzibar.csv.

Usage: build_zanzibar.py [--check]      (--check fails if the files in location-files/ differ)

Same 8 columns as the mainland files: region, regioncode, district, districtcode, ward, wardcode, street, places.
- regioncode is TCRA's allocation for Zanzibar (National Postcode Allocation Plan, Table 4); it must equal
  the first two digits of every postcode in the source, and the script fails if one does not.
- districtcode is the first three digits of the postcode, as on the mainland.
- wardcode is the postcode. One postcode covers several shehia, and the source does not name the postal area,
  so the ward is named after the shehia it covers ("KIPONDA / MKUNAZINI / SHANGANI") and each shehia is a
  `street` row under it. Rename the wards if TCRA publishes names for these areas.
"""
import csv
import os
import sys
from collections import OrderedDict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "sources", "zanzibar-postcodes", "zanzibar.csv")
HEADER = ["region", "regioncode", "district", "districtcode", "ward", "wardcode", "street", "places"]
# TCRA National Postcode Allocation Plan (June 2024), Table 4: region codes of Zanzibar.
TCRA_REGION_CODES = {
    "Mjini Magharibi": "71", "Kusini Unguja": "72", "Kaskazini Unguja": "73",
    "Kusini Pemba": "74", "Kaskazini Pemba": "75",
}
FILES = {r: r.lower().replace(" ", "-") + ".csv" for r in TCRA_REGION_CODES}


def main() -> int:
    check = "--check" in sys.argv
    with open(SRC, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    by_region: dict[str, list] = {r: [] for r in TCRA_REGION_CODES}
    problems = []
    for r in rows:
        code = TCRA_REGION_CODES[r["region"]]
        if not r["postcode"].startswith(code):
            problems.append(f"postcode {r['postcode']} ({r['shehia']}) is not under {r['region']} (code {code})")
        by_region[r["region"]].append(r)
    if problems:
        print("\n".join(problems))
        return 1
    bad = 0
    for region, items in by_region.items():
        groups: "OrderedDict[str, list]" = OrderedDict()
        for it in sorted(items, key=lambda x: (x["postcode"], x["shehia"])):
            groups.setdefault(it["postcode"], []).append(it)
        out = []
        for pc, members in groups.items():
            district = members[0]["district"].upper()
            ward = " / ".join(m["shehia"].upper() for m in members)
            for m in members:
                out.append([region.upper(), TCRA_REGION_CODES[region], district, pc[:3], ward, pc, m["shehia"].upper(), ""])
        path = os.path.join(ROOT, "location-files", FILES[region])
        text_rows = [HEADER] + out
        if check:
            with open(path, encoding="utf-8", newline="") as fh:
                if list(csv.reader(fh)) != text_rows:
                    print(f"{FILES[region]} differs from the source")
                    bad += 1
        else:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                csv.writer(fh, lineterminator="\n").writerows(text_rows)
        print(f"{FILES[region]}: {len(out)} rows, {len(groups)} postcodes")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
