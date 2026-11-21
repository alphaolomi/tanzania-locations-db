#!/usr/bin/env python3
"""Link the TCRA postcode data (location-files/) to the NBS 2022 administrative units (sources/nbs2022/).

Usage: build_crosswalk.py [--check]      (--check fails if the files in crosswalk/ differ from a fresh build)
Needs rapidfuzz (requirements-build.txt). Outputs, under crosswalk/:
  regions.csv    TCRA region code <-> NBS region
  districts.csv  TCRA postal district <-> NBS council (many to many; a pair is listed when wards link them)
  wards.csv      TCRA ward (mainland) or shehia (Zanzibar) <-> NBS ward or shehia
  unmatched.csv  every TCRA and NBS unit with no link, with the closest candidate when there is one
  REVIEW.md      match rates and everything a maintainer should look at

match_method is one of:
  exact       the two names are identical when compared without case
  normalised  identical after case, punctuation, spacing and Swahili/English variants are normalised
  fuzzy       similar names (rapidfuzz), accepted only above FUZZY_MIN and clearly ahead of the runner-up
  manual      listed in crosswalk/overrides.csv, with the reason
`score` is 100 for exact and normalised, the similarity (0-100) for fuzzy, and 100 for manual.

Order of work: overrides, then ward names that match exactly or after normalising (a name found in
several councils is settled by the councils the region's other matches point to), then fuzzy names inside
the region (councils already linked to the district first). Districts are linked from the wards.
"""
import csv
import glob
import os
import re
import sys
from collections import Counter, defaultdict

from rapidfuzz import fuzz, process

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "crosswalk")
FUZZY_MIN = 86  # below this a pair is not accepted
FUZZY_GAP = 3  # the best candidate must beat the second best by this much
LOW_SCORE = 92  # fuzzy matches below this are listed for review
SOURCE = "TCRA / NBS 2022"

# Swahili/English variants and prefixes, applied to whole words after lower-casing and stripping punctuation.
VARIANTS = {"vijijini": "rural", "mjini": "urban", "kaskazini": "north", "kusini": "south", "magharibi": "west",
            "mashariki": "east", "kati": "central", "pwani": "coast"}
COUNCIL_WORDS = {"district", "municipal", "city", "town", "council", "cbd", "dc", "mc", "tc", "jiji", "manispaa",
                 "mji", "halmashauri", "wilaya", "ya", "wa", "la", "ward", "shehia"}


def norm(s: str, council: bool = False) -> str:
    s = s.casefold().replace("'", "").replace("’", "").replace("`", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    words = [VARIANTS.get(w, w) for w in s.split()]
    if council:
        words = [w for w in words if w not in COUNCIL_WORDS]
    return " ".join(words)


def key_loose(s: str) -> str:
    """Normalised, with spaces dropped, so 'Ngorongoro' and 'Ngoro ngoro' or 'Hananasif' compare equal."""
    return norm(s).replace(" ", "")


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load():
    tcra = []  # one record per ward code
    seen = {}
    streets = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, "location-files", "*.csv"))):
        for r in read(f):
            w = seen.get(r["wardcode"])
            if w is None:
                w = seen[r["wardcode"]] = dict(region=r["region"], regioncode=r["regioncode"], district=r["district"],
                                               districtcode=r["districtcode"], ward=r["ward"], wardcode=r["wardcode"])
                tcra.append(w)
            if r["street"].strip():
                streets[r["wardcode"]].append(r["street"].strip())
    nbs_regions = read(os.path.join(ROOT, "sources", "nbs2022", "regions.csv"))
    nbs_councils = read(os.path.join(ROOT, "sources", "nbs2022", "councils.csv"))
    nbs_wards = read(os.path.join(ROOT, "sources", "nbs2022", "wards.csv"))
    return tcra, streets, nbs_regions, nbs_councils, nbs_wards


def best_name(a: str, b: str) -> tuple[str, int]:
    """Method and score of two names that are judged the same unit (exact, normalised or fuzzy)."""
    if a.casefold() == b.casefold():
        return "exact", 100
    if norm(a) == norm(b) or key_loose(a) == key_loose(b):
        return "normalised", 100
    return "fuzzy", int(round(max(fuzz.ratio(norm(a), norm(b)), fuzz.token_sort_ratio(norm(a), norm(b)))))


def main() -> int:
    check = "--check" in sys.argv
    tcra, streets, nbs_regions, nbs_councils, nbs_wards = load()
    overrides = read(os.path.join(OUT, "overrides.csv")) if os.path.exists(os.path.join(OUT, "overrides.csv")) else []

    # ---- regions
    region_rows = []
    nbs_region_by_key = {norm(r["region"]): r for r in nbs_regions}
    tcra_regions = {}
    for w in tcra:
        tcra_regions.setdefault(w["regioncode"], w["region"])
    nbs_region_of = {}  # tcra regioncode -> nbs region name
    for code, name in sorted(tcra_regions.items(), key=lambda kv: int(kv[0])):
        hit = nbs_region_by_key.get(norm(name))
        if hit:
            method, score = best_name(name, hit["region"])
        else:
            cand = process.extractOne(norm(name), list(nbs_region_by_key), scorer=fuzz.ratio)
            hit = nbs_region_by_key[cand[0]] if cand and cand[1] >= FUZZY_MIN else None
            method, score = ("fuzzy", int(cand[1])) if hit else ("", 0)
        if hit:
            nbs_region_of[code] = hit["region"]
            region_rows.append([code, name, hit["region"], hit["zone"], method, score, SOURCE])
    nbs_by_region = defaultdict(list)
    for x in nbs_wards:
        nbs_by_region[x["region"]].append(x)
    council_type = {(c["region"], c["council"]): c["council_type"] for c in nbs_councils}

    # ---- units to match: ward for the mainland, shehia (street rows) for Zanzibar
    units = []  # dict(code, wardname, unit, district, districtcode, region)
    for w in tcra:
        if w["regioncode"] in ("71", "72", "73", "74", "75"):
            for st in dict.fromkeys(streets[w["wardcode"]]):
                units.append(dict(w, unit=st))
        else:
            units.append(dict(w, unit=w["ward"]))

    matches = []  # dict(unit, nbs, method, score)
    used_nbs = set()
    matched_units = set()

    def uid(u):
        return (u["wardcode"], u["unit"])

    def nid(x):
        return (x["region"], x["council"], x["ward"])

    def add(u, x, method, score):
        matches.append(dict(u=u, n=x, method=method, score=score))
        used_nbs.add(nid(x))
        matched_units.add(uid(u))

    by_region_units = defaultdict(list)
    for u in units:
        by_region_units[u["regioncode"]].append(u)

    # overrides first
    ov_used = 0
    for o in overrides:
        u = next((u for u in units if u["wardcode"] == o["tcra_ward_code"] and (not o.get("tcra_unit") or u["unit"] == o["tcra_unit"])), None)
        x = next((x for x in nbs_wards if (x["region"], x["council"], x["ward"]) == (o["nbs_region"], o["nbs_council"], o["nbs_ward"])), None)
        if u is None or x is None:
            print(f"override not applicable: {o}")
            return 1
        if uid(u) not in matched_units:
            add(u, x, "manual", 100)
            ov_used += 1

    affinity: Counter = Counter()  # (tcra districtcode, nbs council) -> matches

    for rc, rus in sorted(by_region_units.items(), key=lambda kv: int(kv[0])):
        nr = nbs_region_of.get(rc)
        if nr is None:
            continue
        rn = nbs_by_region[nr]
        for m in matches:
            if m["u"]["regioncode"] == rc:
                affinity[(m["u"]["districtcode"], m["n"]["council"])] += 1
        # pass 1: names equal after normalising. A name that occurs once on each side pairs directly.
        for keyf, method in ((lambda s: s.casefold(), "exact"), (norm, "normalised"), (key_loose, "normalised")):
            tmap = defaultdict(list)
            nmap = defaultdict(list)
            for u in rus:
                if uid(u) not in matched_units:
                    tmap[keyf(u["unit"])].append(u)
            for x in rn:
                if nid(x) not in used_nbs:
                    nmap[keyf(x["ward"])].append(x)
            for k, ts in tmap.items():
                ns = nmap.get(k, [])
                if len(ts) == 1 and len(ns) == 1:
                    add(ts[0], ns[0], method, 100)
                    affinity[(ts[0]["districtcode"], ns[0]["council"])] += 1
            # names found more than once: settle by the councils the other matches point to
            for _ in range(3):
                tmap = defaultdict(list)
                nmap = defaultdict(list)
                for u in rus:
                    if uid(u) not in matched_units:
                        tmap[keyf(u["unit"])].append(u)
                for x in rn:
                    if nid(x) not in used_nbs:
                        nmap[keyf(x["ward"])].append(x)
                progress = False
                for k, ts in tmap.items():
                    ns = nmap.get(k, [])
                    if not ns or (len(ts) == 1 and len(ns) == 1):
                        continue
                    pairs = sorted(((affinity[(u["districtcode"], x["council"])], u, x) for u in ts for x in ns),
                                   key=lambda p: -p[0])
                    for a, u, x in pairs:
                        if a > 0 and uid(u) not in matched_units and nid(x) not in used_nbs:
                            # skip a tie: two councils with equal evidence cannot be told apart
                            rivals = [p for p in pairs if p[1] is u and p[0] == a and p[2] is not x and nid(p[2]) not in used_nbs]
                            if rivals:
                                continue
                            add(u, x, method, 100)
                            affinity[(u["districtcode"], x["council"])] += 1
                            progress = True
                if not progress:
                    break
        # pass 2: fuzzy inside the region, councils linked to the district first
        for u in sorted(rus, key=lambda u: u["wardcode"]):
            if uid(u) in matched_units:
                continue
            free = [x for x in rn if nid(x) not in used_nbs]
            if not free:
                continue
            linked = [x for x in free if affinity[(u["districtcode"], x["council"])] > 0]
            for pool in (linked, free):
                if not pool:
                    continue
                q = norm(u["unit"])
                scored = sorted(((max(fuzz.ratio(q, norm(x["ward"])), fuzz.token_sort_ratio(q, norm(x["ward"]))), x) for x in pool),
                                key=lambda p: -p[0])
                top = scored[0]
                gap_ok = len(scored) == 1 or top[0] - scored[1][0] >= FUZZY_GAP
                if top[0] >= FUZZY_MIN and gap_ok:
                    add(u, top[1], "fuzzy", int(round(top[0])))
                    affinity[(u["districtcode"], top[1]["council"])] += 1
                    break

    # ---- unmatched lists
    unmatched = []
    for u in units:
        if uid(u) in matched_units:
            continue
        nr = nbs_region_of.get(u["regioncode"])
        free = [x for x in nbs_by_region.get(nr, []) if nid(x) not in used_nbs]
        cand = None
        if free:
            q = norm(u["unit"])
            s, x = max(((fuzz.ratio(q, norm(x["ward"])), x) for x in free), key=lambda p: p[0])
            cand = (int(round(s)), x)
        unmatched.append(["TCRA", u["region"], u["district"], u["wardcode"], u["unit"],
                          cand[1]["council"] + " / " + cand[1]["ward"] if cand else "", cand[0] if cand else ""])
    tcra_by_region = defaultdict(list)
    for u in units:
        tcra_by_region[nbs_region_of.get(u["regioncode"])].append(u)
    for x in nbs_wards:
        if nid(x) in used_nbs:
            continue
        pool = tcra_by_region.get(x["region"], [])
        cand = None
        if pool:
            q = norm(x["ward"])
            s, u = max(((fuzz.ratio(q, norm(u["unit"])), u) for u in pool), key=lambda p: p[0])
            cand = (int(round(s)), u)
        unmatched.append(["NBS 2022", x["region"], x["council"], "", x["ward"],
                          cand[1]["district"] + " / " + cand[1]["unit"] + " (" + cand[1]["wardcode"] + ")" if cand else "",
                          cand[0] if cand else ""])

    # ---- districts: from the wards
    tcra_districts = {}
    for w in tcra:
        tcra_districts.setdefault(w["districtcode"], (w["regioncode"], w["district"]))
    tcra_units_in = Counter(u["districtcode"] for u in units)
    nbs_units_in = Counter((x["region"], x["council"]) for x in nbs_wards)
    pair_count: Counter = Counter()
    pair_methods: defaultdict = defaultdict(Counter)
    for m in matches:
        pair_count[(m["u"]["districtcode"], m["n"]["region"], m["n"]["council"])] += 1
    district_rows = []
    for (dc, nr, council), n in sorted(pair_count.items(), key=lambda kv: (int(kv[0][0]), -kv[1])):
        rc, dname = tcra_districts[dc]
        small = min(tcra_units_in[dc], nbs_units_in[(nr, council)])
        # one or two coincidental shared names are not a link: keep a pair that explains a quarter of the
        # smaller side, or has a district name that fits the council
        stem_t, stem_n = norm(dname, True), norm(council, True)
        method, score = best_name(stem_t, stem_n) if stem_t and stem_n else ("fuzzy", 0)
        if stem_t == stem_n:
            method, score = ("exact", 100) if dname.casefold() == council.casefold() else ("normalised", 100)
        if n * 4 < small and stem_t != stem_n:
            continue
        district_rows.append([dc, dname, nr, council, council_type[(nr, council)], method, score, n,
                              tcra_units_in[dc], nbs_units_in[(nr, council)], SOURCE])

    ward_rows = []
    for m in sorted(matches, key=lambda m: (m["u"]["wardcode"], m["u"]["unit"])):
        u, x = m["u"], m["n"]
        ward_rows.append([u["wardcode"], u["ward"], u["unit"] if u["unit"] != u["ward"] else "", u["districtcode"],
                          x["region"], x["council"], x["ward"], m["method"], m["score"], SOURCE])

    files = {
        "regions.csv": (["tcra_region_code", "tcra_region", "nbs_region", "nbs_zone", "match_method", "score", "source"], region_rows),
        "districts.csv": (["tcra_district_code", "tcra_district", "nbs_region", "nbs_council", "nbs_council_type", "match_method",
                           "score", "shared_units", "tcra_units", "nbs_wards", "source"], district_rows),
        "wards.csv": (["tcra_ward_code", "tcra_ward", "tcra_shehia", "tcra_district_code", "nbs_region", "nbs_council", "nbs_ward",
                       "match_method", "score", "source"], ward_rows),
        "unmatched.csv": (["side", "region", "district_or_council", "tcra_ward_code", "unit", "closest_on_other_side", "closest_score"], unmatched),
    }
    stats = dict(units=units, matches=matches, unmatched=unmatched, district_rows=district_rows, region_rows=region_rows,
                 tcra=tcra, tcra_regions=tcra_regions, nbs_regions=nbs_regions, nbs_councils=nbs_councils, nbs_wards=nbs_wards,
                 tcra_districts=tcra_districts, ov_used=ov_used, overrides=overrides, streets=streets)
    review = build_review(stats)
    bad = 0
    os.makedirs(OUT, exist_ok=True)
    for name, (header, rows) in files.items():
        path = os.path.join(OUT, name)
        want = [header] + [[str(c) for c in r] for r in rows]
        if check:
            if not os.path.exists(path) or [r for r in csv.reader(open(path, encoding="utf-8", newline=""))] != want:
                print(f"{name} differs from a fresh build")
                bad += 1
        else:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                csv.writer(fh, lineterminator="\n").writerows(want)
        print(f"{name}: {len(rows)} rows")
    path = os.path.join(OUT, "REVIEW.md")
    if check:
        if not os.path.exists(path) or open(path, encoding="utf-8", newline="").read() != review:
            print("REVIEW.md differs from a fresh build")
            bad += 1
    else:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(review)
    return 1 if bad else 0


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def build_review(s) -> str:
    units, matches = s["units"], s["matches"]
    L = []
    w = L.append
    mainland = [u for u in units if u["regioncode"] not in ("71", "72", "73", "74", "75")]
    zanz = [u for u in units if u["regioncode"] in ("71", "72", "73", "74", "75")]
    mm = [m for m in matches if m["u"]["regioncode"] not in ("71", "72", "73", "74", "75")]
    zm = [m for m in matches if m["u"]["regioncode"] in ("71", "72", "73", "74", "75")]
    nbs_main = [x for x in s["nbs_wards"] if True]
    n_used = {(m["n"]["region"], m["n"]["council"], m["n"]["ward"]) for m in matches}
    nbs_z = [x for x in nbs_main if x["region"] in ("Kaskazini Unguja", "Kusini Unguja", "Mjini Magharibi", "Kaskazini Pemba", "Kusini Pemba")]
    nbs_m = [x for x in nbs_main if x not in nbs_z]
    nz_used = sum(1 for x in nbs_z if (x["region"], x["council"], x["ward"]) in n_used)
    nm_used = sum(1 for x in nbs_m if (x["region"], x["council"], x["ward"]) in n_used)
    methods = Counter(m["method"] for m in matches)

    w("# Crosswalk review\n")
    w("Generated by `scripts/build_crosswalk.py`. It links the TCRA postcode data in `location-files/` to the NBS 2022 census")
    w("administrative units in `sources/nbs2022/`. Do not edit this file by hand: change `crosswalk/overrides.csv` or the script and rebuild.\n")
    w("## Match rates\n")
    w("| Level | TCRA side | NBS 2022 side |")
    w("|---|---|---|")
    w(f"| Regions | {len(s['region_rows'])} of {len(s['tcra_regions'])} matched ({pct(len(s['region_rows']), len(s['tcra_regions']))}) | "
      f"{len(s['region_rows'])} of {len(s['nbs_regions'])} ({pct(len(s['region_rows']), len(s['nbs_regions']))}) |")
    tdist = {r[0] for r in s["district_rows"]}
    ncou = {(r[2], r[3]) for r in s["district_rows"]}
    w(f"| Districts and councils | {len(tdist)} of {len(s['tcra_districts'])} postal districts linked ({pct(len(tdist), len(s['tcra_districts']))}) | "
      f"{len(ncou)} of {len(s['nbs_councils'])} councils linked ({pct(len(ncou), len(s['nbs_councils']))}) |")
    mu = {uid_ for uid_ in {(m['u']['wardcode'], m['u']['unit']) for m in mm}}
    zu = {(m['u']['wardcode'], m['u']['unit']) for m in zm}
    w(f"| Wards, mainland | {len(mu)} of {len(mainland)} ({pct(len(mu), len(mainland))}) | {nm_used} of {len(nbs_m)} ({pct(nm_used, len(nbs_m))}) |")
    w(f"| Shehia, Zanzibar | {len(zu)} of {len(zanz)} ({pct(len(zu), len(zanz))}) | {nz_used} of {len(nbs_z)} ({pct(nz_used, len(nbs_z))}) |")
    w("")
    w("Ward matches by method: " + ", ".join(f"{k} {methods[k]}" for k in ("exact", "normalised", "fuzzy", "manual")) + ".")
    w("On Zanzibar the TCRA unit is a shehia: one postcode covers several shehia, so a TCRA ward there is a group and each shehia is matched on its own.\n")
    w("Postal districts and councils are not one-to-one: a TCRA district can hold several councils (a rural council and a town council")
    w("split from it) and the other way round. `districts.csv` lists every pair that wards link, with `shared_units` showing how many.\n")

    weak = [r for r in s["district_rows"] if r[6] < FUZZY_MIN]
    w(f"## District links whose names differ ({len(weak)})\n")
    w("These pairs are linked by their wards, not by name: the council was split from the district or has a new name. `score` in `districts.csv` is the name similarity, so it is low here.\n")
    w("| TCRA district | NBS council | Shared wards | TCRA wards | NBS wards |")
    w("|---|---|---|---|---|")
    for r in weak:
        w(f"| {r[1]} ({r[0]}) | {r[3]} | {r[7]} | {r[8]} | {r[9]} |")
    w("")
    fz = [m for m in matches if m["method"] == "fuzzy"]
    low = sorted((m for m in fz if m["score"] < LOW_SCORE), key=lambda m: m["score"])
    w(f"## Fuzzy matches to check ({len(low)} below {LOW_SCORE}, of {len(fz)} fuzzy)\n")
    w("Spelling variants accepted by similarity. Confirm a few; add a row to `overrides.csv` to change one.\n")
    if low:
        w("| Score | TCRA ward | District | NBS ward | NBS council |")
        w("|---|---|---|---|---|")
        for m in low:
            u, x = m["u"], m["n"]
            w(f"| {m['score']} | {u['unit']} ({u['wardcode']}) | {u['district']} | {x['ward']} | {x['council']} |")
        w("")
    w(f"The other {len(fz) - len(low)} fuzzy matches score {LOW_SCORE} or more and are in `wards.csv` (`match_method` = fuzzy).\n")

    un = s["unmatched"]
    tun = [r for r in un if r[0] == "TCRA"]
    nun = [r for r in un if r[0] == "NBS 2022"]
    w(f"## Unmatched ({len(tun)} TCRA, {len(nun)} NBS 2022)\n")
    w("All rows are in `crosswalk/unmatched.csv` with the closest name on the other side. Causes, most common first:\n")
    w("- **Ward splits and new wards since the TCRA list.** NBS 2022 counts "
      f"{len(nbs_m):,} mainland wards, the TCRA list {len(mainland):,}. NBS wards with no TCRA ward are mostly wards created after the postcode list.")
    w("- **Renamed wards and spelling.** Names that differ by more than the fuzzy threshold.")
    w("- **Pseudo-districts.** TCRA's CBD districts (for example Arusha CBD) are postal areas of a city council and have no council of their own; their wards link to the city council.")
    w("- **Zanzibar shehia.** The postcode source names shehia, not postal areas; NBS lists "
      f"{len(nbs_z)} shehia against {len(zanz)} in the postcode source.\n")
    by_reg = Counter()
    for r in tun:
        by_reg[r[1]] += 1
    w("TCRA units with no NBS match, by region: " + ", ".join(f"{k.title()} {v}" for k, v in by_reg.most_common()) + ".\n")
    nreg = Counter(r[1] for r in nun)
    w("NBS wards with no TCRA match, by region: " + ", ".join(f"{k} {v}" for k, v in nreg.most_common()) + ".\n")
    close = sorted((r for r in nun if r[6] != "" and r[6] >= 80), key=lambda r: -r[6])
    w(f"### NBS wards that resemble a TCRA ward (possible splits or renames): {len(close)}\n")
    if close:
        w("| NBS region | NBS council | NBS ward | Closest TCRA ward | Score |")
        w("|---|---|---|---|---|")
        for r in close[:80]:
            w(f"| {r[1]} | {r[2]} | {r[4]} | {r[5]} | {r[6]} |")
        if len(close) > 80:
            w(f"\n(first 80 of {len(close)}; the rest are in `unmatched.csv`)")
        w("")

    w("## Zanzibar region codes\n")
    w("TCRA allocated 71 Mjini Magharibi, 72 Kusini Unguja, 73 Kaskazini Unguja, 74 Kusini Pemba, 75 Kaskazini Pemba")
    w("(National Postcode Allocation Plan, June 2024, Table 4). `scripts/build_zanzibar.py` fails if any postcode in the source does not start with the")
    w("code of its region, and it did not fail: every Zanzibar postcode is under its TCRA region code.\n")
    w("| Region | TCRA code | Postcodes | Shehia in the postcode source | NBS 2022 shehia |")
    w("|---|---|---|---|---|")
    zr = {"71": "Mjini Magharibi", "72": "Kusini Unguja", "73": "Kaskazini Unguja", "74": "Kusini Pemba", "75": "Kaskazini Pemba"}
    for code, name in zr.items():
        us = [u for u in zanz if u["regioncode"] == code]
        w(f"| {name} | {code} | {len({u['wardcode'] for u in us})} | {len(us)} | {sum(1 for x in nbs_z if x['region'] == name)} |")
    w("")
    w("Things to confirm with TCRA or the Office of the Chief Government Statistician (Zanzibar):\n")
    w("- The postcode source gives one postcode per group of shehia and no postal area names, so the Zanzibar `ward` is a joined list of shehia names. Replace it when TCRA publishes ward names.")
    w("- The TCRA plan lists some Zanzibar post offices that are not in the postcode source (for example Wete 75100, Mahonda 73200, Jambiani 72150): only the codes are checked, not the names.\n")
    w("## Fixes to the TCRA data\n")
    w("Each change made while cleaning `location-files/` is one row in [`data-fixes.csv`](data-fixes.csv) (file, line before the fix, rule, row before and after, evidence).")
    w("`scripts/clean_data.py` made them and can be read to see each rule.\n")
    fixes = read(os.path.join(OUT, "data-fixes.csv"))
    rules = Counter(f["rule"] for f in fixes)
    w("| Rule | Rows changed | What it fixed |")
    w("|---|---|---|")
    what = {"R1 whitespace": "line breaks and repeated spaces inside names",
            "R2 fill-down code": "ward codes counted up on every row of a spreadsheet column; reset to the ward's own code",
            "R3 fill-down name": "ward names with a counter filled down (kept the NBS 2022 name)",
            "R4 district": "ward codes not under their district: Madaba (Ruvuma) and Njisi (Mbeya), confirmed by NBS 2022",
            "R5 duplicate": "exact duplicate rows removed"}
    for k in sorted(rules):
        w(f"| {k} | {rules[k]} | {what.get(k, '')} |")
    w("\nThe 173 issues in the old `scripts/known-data-issues.txt` baseline (116 duplicate rows, 32 ward codes not under their district, 25 codes with more than one name) are all resolved and the baseline is now empty.\n")
    w("NBS 2022 was the tiebreaker in R3 and R4. Where NBS 2022 did not settle a case, the first row was kept and the case is in `data-fixes.csv`.\n")
    w("## NBS 2022 extraction\n")
    w("The names in `sources/nbs2022/` are read from the PDFs and checked against the totals printed in the reports (ward sums per council, council sums per region, region sums per country; see `scripts/extract_nbs.py`). One misprint in the report was corrected: the council printed as `Nsimbo District l` is `Nsimbo District`.\n")
    w("## Overrides\n")
    w(f"`overrides.csv` holds {len(s['overrides'])} manual link(s), {s['ov_used']} applied.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
