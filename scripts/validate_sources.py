#!/usr/bin/env python3
"""Validate the NBS 2022 source CSVs (sources/) and the crosswalk (crosswalk/), using only the standard library.

Checks: expected headers, no duplicate keys, every council under a known region, every ward under a known council,
council and region totals equal the sum of their children (population, households, ward and council counts),
every crosswalk row points at a TCRA code in location-files/ and an NBS unit that exists, match_method is one of
exact/normalised/fuzzy/manual with a score from 0 to 100, and every override has a reason.
Exits non-zero on any problem.
"""
import csv
import glob
import os
import sys
from collections import Counter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
errors: list[str] = []


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def err(msg):
    errors.append(msg)


def unique(rows, key, label):
    c = Counter(tuple(r[k] for k in key) for r in rows)
    for k, n in c.items():
        if n > 1:
            err(f"{label}: duplicate key {k} ({n} rows)")


def header(path, want):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        got = fh.readline().rstrip("\n").split(",")
    if got != want:
        err(f"{path}: header {got}, expected {want}")


header("sources/nbs2022/regions.csv", ["region", "zone", "population", "households", "councils", "source"])
header("sources/nbs2022/councils.csv", ["region", "seq", "council", "council_type", "population", "households", "wards", "source"])
header("sources/nbs2022/wards.csv", ["region", "council", "seq", "ward", "ward_type", "population", "households", "source"])
nr, nc, nw = (read("sources", "nbs2022", f"{n}.csv") for n in ("regions", "councils", "wards"))
unique(nr, ("region",), "nbs regions")
unique(nc, ("region", "council"), "nbs councils")
unique(nw, ("region", "council", "ward"), "nbs wards")
regions = {r["region"]: r for r in nr}
councils = {(c["region"], c["council"]): c for c in nc}
for c in nc:
    if c["region"] not in regions:
        err(f"council {c['council']}: unknown region {c['region']}")
for w in nw:
    if (w["region"], w["council"]) not in councils:
        err(f"ward {w['ward']}: unknown council {w['region']} / {w['council']}")
for (r, name), c in councils.items():
    ws = [w for w in nw if w["region"] == r and w["council"] == name]
    if len(ws) != int(c["wards"]):
        err(f"council {name}: {len(ws)} wards listed, {c['wards']} recorded")
    for f in ("population", "households"):
        if sum(int(w[f]) for w in ws) != int(c[f]):
            err(f"council {name}: ward {f} do not add up to the council total")
for r, row in regions.items():
    cs = [c for (rr, _), c in councils.items() if rr == r]
    if len(cs) != int(row["councils"]):
        err(f"region {r}: {len(cs)} councils listed, {row['councils']} recorded")
    for f in ("population", "households"):
        if sum(int(c[f]) for c in cs) != int(row[f]):
            err(f"region {r}: council {f} do not add up to the region total")

# TCRA side
tr, td, tw = {}, {}, {}
for f in glob.glob(os.path.join(ROOT, "location-files", "*.csv")):
    with open(f, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            tr[r["regioncode"]] = r["region"]
            td[r["districtcode"]] = r["district"]
            tw[r["wardcode"]] = r["district"]

cwr = read("crosswalk", "regions.csv")
cwd = read("crosswalk", "districts.csv")
cww = read("crosswalk", "wards.csv")
unique(cwr, ("tcra_region_code",), "crosswalk regions")
unique(cwd, ("tcra_district_code", "nbs_region", "nbs_council"), "crosswalk districts")
unique(cww, ("tcra_ward_code", "tcra_shehia", "nbs_region", "nbs_council", "nbs_ward"), "crosswalk wards")
for label, rows in (("regions", cwr), ("districts", cwd), ("wards", cww)):
    for r in rows:
        if r["match_method"] not in ("exact", "normalised", "fuzzy", "manual"):
            err(f"crosswalk {label}: bad match_method {r['match_method']!r}")
        if not r["score"].isdigit() or not 0 <= int(r["score"]) <= 100:
            err(f"crosswalk {label}: bad score {r['score']!r}")
for r in cwr:
    if r["tcra_region_code"] not in tr:
        err(f"crosswalk regions: unknown TCRA region code {r['tcra_region_code']}")
    if r["nbs_region"] not in regions:
        err(f"crosswalk regions: unknown NBS region {r['nbs_region']}")
for r in cwd:
    if r["tcra_district_code"] not in td:
        err(f"crosswalk districts: unknown TCRA district code {r['tcra_district_code']}")
    if (r["nbs_region"], r["nbs_council"]) not in councils:
        err(f"crosswalk districts: unknown NBS council {r['nbs_region']} / {r['nbs_council']}")
nbs_ward_keys = {(w["region"], w["council"], w["ward"]) for w in nw}
for r in cww:
    if r["tcra_ward_code"] not in tw:
        err(f"crosswalk wards: unknown TCRA ward code {r['tcra_ward_code']}")
    elif not r["tcra_ward_code"].startswith(r["tcra_district_code"]):
        err(f"crosswalk wards: ward {r['tcra_ward_code']} is not under district {r['tcra_district_code']}")
    if (r["nbs_region"], r["nbs_council"], r["nbs_ward"]) not in nbs_ward_keys:
        err(f"crosswalk wards: unknown NBS ward {r['nbs_region']} / {r['nbs_council']} / {r['nbs_ward']}")
ov = os.path.join(ROOT, "crosswalk", "overrides.csv")
for r in read("crosswalk", "overrides.csv") if os.path.exists(ov) else []:
    if not r.get("reason", "").strip():
        err(f"overrides.csv: row for ward {r.get('tcra_ward_code')} has no reason")

print(f"{len(nr)} NBS regions, {len(nc)} councils, {len(nw)} wards; crosswalk {len(cwr)} regions, {len(cwd)} districts, {len(cww)} wards")
if errors:
    for e in errors:
        print("ERROR:", e)
    sys.exit(1)
print("ok: sources and crosswalk are consistent")
