#!/usr/bin/env python3
"""Download the pinned source files into a cache directory and verify their SHA256.

Usage: fetch_sources.py [--cache DIR]      (default cache: .cache/sources, git-ignored)

Sources:
- NBS 2022 Administrative Units Population Distribution Reports, vol 1a/1b/1c (PDF).
- tanzaniapostcode.com postcodes, as published by DataHub (CSV). Only the five Zanzibar
  regions are kept (written to <cache>/zanzibar-postcodes.csv); the full file is hashed too.

Nothing downloaded is committed. If a hash differs the script fails and prints the new hash:
check what changed upstream before updating the pin below.
"""
import csv
import hashlib
import os
import sys
import urllib.request

NBS = "https://www.nbs.go.tz/uploads/statistics/documents/"
SOURCES = [
    ("vol1a.pdf", NBS + "en-1705484562-Administrative_units_Population_Distribution_Report_Tanzania_volume1a.pdf",
     "6f41eee70eefd764efaea876e0b13546666a69c5b91c1f50e5d9b38c3f78d1b9"),
    ("vol1b.pdf", NBS + "en-1705484561-Administrative_units_Population_Distribution_Report_Tanzania_Mainland_volume1b.pdf",
     "fb715b4e9380056268b1b7eee5c87c54535f416a6cf75eebfbdc6fddf5980d15"),
    ("vol1c.pdf", NBS + "en-1705484561-Administrative_units_Population_Distribution_Report_Tanzania_Zanzibar_volume1c.pdf",
     "bccf08bf8a2953b10a1ccb88c0827dcf22918c0e7d07bfb54052ad9f5950e851"),
    ("tz.csv", "https://postal.datahub.io/tz/tz.csv",
     "351f070566e62e34138611065848f73f566c79c5bbe03dadc5d2dad0011758aa"),
]
ZANZIBAR_REGIONS = {"Mjini Magharibi", "Kaskazini Unguja", "Kusini Unguja", "Kaskazini Pemba", "Kusini Pemba"}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    args = sys.argv[1:]
    cache = args[args.index("--cache") + 1] if "--cache" in args else ".cache/sources"
    os.makedirs(cache, exist_ok=True)
    bad = 0
    for name, url, want in SOURCES:
        path = os.path.join(cache, name)
        if not os.path.exists(path) or sha256(path) != want:
            print(f"downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "tanzania-locations-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as fh:
                while chunk := r.read(1 << 20):
                    fh.write(chunk)
        got = sha256(path)
        if got == want:
            print(f"ok   {name}  {got}")
        else:
            print(f"FAIL {name}  expected {want}  got {got}")
            bad += 1
    if bad:
        return 1
    with open(os.path.join(cache, "tz.csv"), encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["admin_name1"] in ZANZIBAR_REGIONS]
    out = os.path.join(cache, "zanzibar-postcodes.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["postal_code", "place_name", "admin_name1", "admin_name2", "admin_name3"])
        for r in rows:
            w.writerow([r["postal_code"], r["place_name"], r["admin_name1"], r["admin_name2"], r["admin_name3"]])
    print(f"wrote {out}: {len(rows)} Zanzibar rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
