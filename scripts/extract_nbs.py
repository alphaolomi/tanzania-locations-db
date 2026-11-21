#!/usr/bin/env python3
"""Extract regions, councils and wards (shehia in Zanzibar) from the NBS 2022 census reports.

Usage: extract_nbs.py [--cache DIR] [--out DIR]
Reads vol1a/1b/1c PDFs from the cache (see fetch_sources.py), writes
regions.csv, councils.csv and wards.csv under --out (default sources/nbs2022).

Every table in the reports prints a total row, and the extraction is checked against them:
- the wards of a council add up to the council's printed population and household total;
- the councils of a region add up to the region's printed total;
- the regions add up to Tanzania Mainland and Tanzania Zanzibar, and match vol 1a's region table;
- item numbers run 1..n without gaps, and every council has a ward table.
The script exits non-zero on any mismatch. Needs: pdfplumber (requirements-build.txt).
"""
import csv
import os
import re
import sys

import pdfplumber

NUM = r"[\d,]+(?:\.0)?"
ROW = re.compile(rf"^(?:(\d+)[.,]+\s*)?(.+?)\s+({NUM})\s+({NUM})\s+({NUM})\s+(\d+)\s+({NUM})\s+([\d.]+)$")
errors: list[str] = []
notes: list[str] = []


def n(s: str) -> int:
    s = s.replace(",", "")
    return int(s[:-2] if s.endswith(".0") else s)


def page_lines(path: str):
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            for line in (page.extract_text() or "").split("\n"):
                yield i + 1, line.strip()


TITLE = re.compile(r"(?:Ward|Shehia),\s*(.+?)\s*;?\s*2022 PHC")
LOOSE_ROW = re.compile(rf"^(\d+)['.,]*\s*([A-Za-z].*?)\s+({NUM})\s+({NUM})\s+({NUM})\s+(\d+)\s+({NUM})\s+([\d.]+)$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).casefold().strip()


def parse_volume(path: str, zone: str):
    """Return (regions, councils, wards) for one volume.

    The region table (Table X.0) lists the councils of region X. A ward table is attached to its
    council by its title line ("... by Ward, Kondoa District Council; 2022 PHC") or by its printed
    total row (same population and households as the council's row in the region table). The
    heading numbers and item numbers of the report are not trusted (some are missing, wrong or
    lose their dot); the sums are checked instead.
    """
    regions: list[dict] = []
    councils: list[dict] = []
    wards: list[dict] = []
    region = None
    council = None
    mode = None        # "regions" | "wards"

    def switch(c):
        nonlocal council, mode
        if c is not council and c["wards"]:
            errors.append(f"{zone}: a second ward table was attached to {c['region']} / {c['name']}")
        council, mode = c, "wards"

    for page, line in page_lines(path):
        t = TITLE.search(line)
        if t and region is not None:
            want = norm(t.group(1))
            for c in region["councils"]:
                if want in (norm(c["name"] + " Council"), norm(c["name"])):
                    switch(c)
                    break
            continue
        m = ROW.match(line)
        loose = False
        if mode in ("wards", "regions") and (not m or m.group(1) is None):
            # item numbers with a stray quote or no dot ("14' Chanzuru", "21 Mkwatani")
            lm = LOOSE_ROW.match(line)
            if lm:
                m, loose = lm, True
        if not m:
            continue
        seq, name, both, male, female, ratio, hh, size = m.groups()
        both, male, female, hh = n(both), n(male), n(female), n(hh)
        rec = dict(name=name.strip(), population=both, male=male, female=female, households=hh, page=page)
        if seq is None and not loose:
            if name.endswith(" Region"):
                rname = name[: -len(" Region")].strip()
                existing = [r for r in regions if r["name"] == rname]
                if existing:
                    region = existing[0]
                else:
                    region = dict(rec, name=rname, zone=zone, councils=[])
                    regions.append(region)
                mode = "regions"
            elif region is not None:
                for c in region["councils"]:
                    if (c["population"], c["households"]) == (both, hh):
                        if c is not council:
                            switch(c)
                        break
            continue
        if not regions:
            continue
        if mode == "regions":
            c = dict(rec, seq=int(seq), region=region["name"], zone=zone, wards=[])
            if c["seq"] != len(region["councils"]) + 1:
                errors.append(f"p{page}: council seq {seq} out of order in {region['name']}")
            region["councils"].append(c)
            councils.append(c)
        elif mode == "wards":
            if abs(male + female - both) > 1:
                errors.append(f"p{page}: {name}: male+female != total")
            expected = len(council["wards"]) + 1
            fix = re.match(r"^(\d)\s+(\S.*)$", name)
            if fix and int(seq + fix.group(1)) == expected:
                # a typo in the report: "3.2 Kisiwani" printed for "32. Kisiwani"
                seq, rec["name"] = seq + fix.group(1), fix.group(2).strip()
            w = dict(rec, seq=expected, printed_seq=int(seq), region=region["name"],
                     council=council["name"], zone=zone)
            if w["printed_seq"] != w["seq"]:
                notes.append(f"p{page}: {council['name']}: item number {seq} printed where {w['seq']} was expected ({rec['name']})")
            council["wards"].append(w)
            wards.append(w)
    return regions, councils, wards


def country_total(path: str, label: str, first_pages: int = 80):
    """Find the 'Tanzania ...' total row of the region table (Table 3) in a volume."""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:first_pages]:
            text = page.extract_text() or ""
            if "by Region" not in text:
                continue
            for line in text.split("\n"):
                m = ROW.match(line.strip())
                if m and m.group(1) is None and m.group(2).strip() == label:
                    return n(m.group(3)), n(m.group(7))
    return None


def check(regions, councils, label, total):
    if total is None:
        errors.append(f"{label}: no printed country total found")
    for c in councils:
        if not c["wards"]:
            errors.append(f"{label}: council {c['region']} / {c['name']} has no ward table")
            continue
        sp = sum(w["population"] for w in c["wards"])
        sh = sum(w["households"] for w in c["wards"])
        if sp != c["population"] or sh != c["households"]:
            errors.append(f"{label}: {c['region']} / {c['name']}: wards sum to {sp:,} people / {sh:,} households, printed {c['population']:,} / {c['households']:,}")
    for r in regions:
        sp = sum(c["population"] for c in r["councils"])
        sh = sum(c["households"] for c in r["councils"])
        if sp != r["population"] or sh != r["households"]:
            errors.append(f"{label}: region {r['name']}: councils sum to {sp:,} / {sh:,}, printed {r['population']:,} / {r['households']:,}")
    if total:
        sp = sum(r["population"] for r in regions)
        sh = sum(r["households"] for r in regions)
        if (sp, sh) != total:
            errors.append(f"{label}: regions sum to {sp:,} / {sh:,}, printed {total[0]:,} / {total[1]:,}")


def vol1a_regions(path: str):
    """Region rows (name -> population, households) from Table 3 of the whole-country volume."""
    out = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:80]:
            text = page.extract_text() or ""
            if "Both Sexes" not in text or "Tanzania Zanzibar" not in text or "Tanzania Mainland" not in text:
                continue
            for line in text.split("\n"):
                m = ROW.match(line.strip())
                if m and m.group(1) is None:
                    out.setdefault(m.group(2).strip(), (n(m.group(3)), n(m.group(7))))
            if out:
                break
    return out


# Typos printed in the report. The row is read as printed, then the name is corrected here.
NAME_FIXES = {"Nsimbo District l": "Nsimbo District"}


def write(out_dir, regions, councils, wards):
    os.makedirs(out_dir, exist_ok=True)
    for c in councils:
        c["name"] = NAME_FIXES.get(c["name"], c["name"])
    for x in wards:
        x["council"] = NAME_FIXES.get(x["council"], x["council"])

    def w(name, header, rows):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            cw = csv.writer(fh, lineterminator="\n")
            cw.writerow(header)
            cw.writerows(rows)

    w("regions.csv", ["region", "zone", "population", "households", "councils", "source"],
      [[r["name"], r["zone"], r["population"], r["households"], len(r["councils"]), "NBS 2022"] for r in regions])
    w("councils.csv", ["region", "seq", "council", "council_type", "population", "households", "wards", "source"],
      [[c["region"], c["seq"], c["name"], c["name"].rsplit(" ", 1)[-1], c["population"], c["households"], len(c["wards"]), "NBS 2022"]
       for c in councils])
    w("wards.csv", ["region", "council", "seq", "ward", "ward_type", "population", "households", "source"],
      [[x["region"], x["council"], x["seq"], x["name"], "shehia" if x["zone"] == "zanzibar" else "ward",
        x["population"], x["households"], "NBS 2022"] for x in wards])


def main() -> int:
    a = sys.argv[1:]
    cache = a[a.index("--cache") + 1] if "--cache" in a else ".cache/sources"
    out = a[a.index("--out") + 1] if "--out" in a else "sources/nbs2022"
    allr, allc, allw = [], [], []
    for vol, zone, label in (("vol1b", "mainland", "Tanzania Mainland"), ("vol1c", "zanzibar", "Tanzania Zanzibar")):
        path = os.path.join(cache, f"{vol}.pdf")
        regions, councils, wards = parse_volume(path, zone)
        check(regions, councils, vol, country_total(path, label))
        print(f"{vol}: {len(regions)} regions, {len(councils)} councils, {len(wards)} wards/shehia")
        allr += regions
        allc += councils
        allw += wards
    ta = vol1a_regions(os.path.join(cache, "vol1a.pdf"))
    if not ta:
        errors.append("vol1a: no region table found")
    for r in allr:
        got = ta.get(r["name"])
        if got != (r["population"], r["households"]):
            errors.append(f"vol1a: region {r['name']}: printed {got}, vol1b/1c give {(r['population'], r['households'])}")
    if errors:
        print(f"\n{len(errors)} validation error(s):")
        for e in errors:
            print("  " + e)
        return 1
    if notes:
        print(f"{len(notes)} note(s): item numbers in the report that skip or repeat (the sums still match):")
        for x in notes:
            print("  " + x)
    write(out, allr, allc, allw)
    print(f"ok: validated against printed totals; wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
