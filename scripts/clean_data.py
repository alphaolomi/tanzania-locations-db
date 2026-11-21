#!/usr/bin/env python3
"""Fix the known problems in location-files/ and log every change.

This was run once to clean the TCRA-derived data; it is kept so each change can be re-checked.
Running it on already-clean files changes nothing. Usage: clean_data.py [--dry-run]

Output: crosswalk/data-fixes.csv, one row per changed or removed row, with the rule and the evidence.

Rules, in the order they run:
  R1 whitespace      A line break inside a name becomes a space; runs of spaces become one.
  R2 fill-down code  The code of a ward was filled down a spreadsheet column: a run of rows with the
                     same ward name whose code goes up by exactly 1 on every row. The first code is
                     the ward's own (it is also the code of the next ward's rows); the run is reset to it.
  R3 fill-down name  Same, on the name: "OLJORO NAMBA 5", "OLJORO NAMBA 6", ... on one code. The first
                     name is kept; NBS 2022 lists a single ward with that name ("Oljoro No.5", "Kitama 1").
  R4 district        Rows whose ward code does not start with their district's code are moved to the
                     district the code belongs to (Madaba, Ruvuma) or the code is corrected (Njisi, Mbeya).
                     NBS 2022 confirms both (see the evidence column).
  R5 duplicates      Exact duplicate rows are removed (first one kept), after R1 to R4.
  R6 headers         The header row is written the same way in every file.
"""
import csv
import glob
import os
import re
import sys

HEADER = ["region", "regioncode", "district", "districtcode", "ward", "wardcode", "street", "places"]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DRY = "--dry-run" in sys.argv

# R4: explicit corrections, each backed by NBS 2022 (sources/nbs2022).
DISTRICT_MOVES = {
    # (file, ward, wardcode) -> (new district name, new district code, new ward code, evidence)
    ("ruvuma.csv", "LITUTA", "57731"): (
        "MADABA", "577", "57731",
        "Code 57731 is not under Songea (572). NBS 2022 lists Lituta in Madaba District Council (Ruvuma, 8 wards), "
        "which was split from Songea District and takes the next district code 577"),
    ("mbeya.csv", "NJISI", "73733"): (
        None, None, "53733",
        "Code 73733 is not under Kyela (537) or Mbeya (53). Kyela's other 32 wards run 53701 to 53732 and NBS 2022 "
        "lists 33 wards in Kyela District including Njisi, so 53733 is the missing code"),
}

# R3: ward names with a counter filled down; kept = the NBS 2022 name.
FILLDOWN_NAMES = [
    (re.compile(r"^OLJORO NAMBA \d+$"), "27612", "OLJORO NAMBA 5", "NBS 2022 lists one ward, Oljoro No.5, in Simanjiro District"),
    (re.compile(r"^KITAMA \d+$"), "63302", "KITAMA 1", "NBS 2022 lists one ward, Kitama 1, in Tandahimba District"),
]

fixes: list[list[str]] = []
headers_fixed = 0


def log(name, line, rule, before, after, evidence=""):
    fixes.append([name, str(line), rule, ",".join(before), ",".join(after) if after else "(removed)", evidence])


def main() -> int:
    global headers_fixed
    for path in sorted(glob.glob(os.path.join(ROOT, "location-files", "*.csv"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            first = next(reader)
            recs = []
            for row in reader:
                recs.append({"row": row, "line": reader.line_num, "orig": list(row)})
        if first != HEADER:
            headers_fixed += 1

        # R1 whitespace: names (columns 0-5) lose repeated spaces; every field loses line breaks and tabs
        for r in recs:
            new = []
            for k, v in enumerate(r["row"]):
                v = re.sub(r"\s+", " ", v).strip() if k < 6 else re.sub(r"[\r\n\t]+", " ", v).strip()
                new.append(v)
            if new != r["row"]:
                log(name, r["line"], "R1 whitespace", r["row"], new)
                r["row"] = new

        # R2 fill-down code
        owners: dict[str, set[str]] = {}
        for x in recs:
            owners.setdefault(x["row"][5], set()).add(x["row"][4])
        i = 0
        while i < len(recs):
            j = i + 1
            r = recs[i]["row"]
            while (j < len(recs) and recs[j]["row"][3] == r[3] and recs[j]["row"][4] == r[4]
                   and recs[j]["row"][5].isdigit() and recs[j]["row"][5] == str(int(recs[j - 1]["row"][5]) + 1)):
                j += 1
            # only a run that takes codes another ward in the district owns is a fill-down error
            clash = any(owners[recs[k]["row"][5]] - {r[4]} for k in range(i + 1, j)) if j - i >= 2 else False
            if clash and r[5].isdigit():
                for k in range(i + 1, j):
                    old = list(recs[k]["row"])
                    recs[k]["row"][5] = r[5]
                    log(name, recs[k]["line"], "R2 fill-down code", old, recs[k]["row"],
                        f"ward {r[4]} keeps its own code {r[5]}; the code was counted up on each row")
            i = j

        # R3 fill-down name
        for rx, code, keep, why in FILLDOWN_NAMES:
            for r in recs:
                if r["row"][5] == code and rx.match(r["row"][4]) and r["row"][4] != keep:
                    old = list(r["row"])
                    r["row"][4] = keep
                    log(name, r["line"], "R3 fill-down name", old, r["row"], why)

        # R4 district / code corrections
        for r in recs:
            key = (name, r["row"][4], r["row"][5])
            if key in DISTRICT_MOVES:
                dname, dcode, wcode, why = DISTRICT_MOVES[key]
                old = list(r["row"])
                if dname:
                    r["row"][2], r["row"][3] = dname, dcode
                r["row"][5] = wcode
                log(name, r["line"], "R4 district", old, r["row"], why)

        # R5 duplicates
        seen: dict[tuple, int] = {}
        kept = []
        for r in recs:
            key = tuple(r["row"])
            if key in seen:
                log(name, r["line"], "R5 duplicate", r["orig"], None, f"same as line {seen[key]}")
                continue
            seen[key] = r["line"]
            kept.append(r["row"])

        if not DRY:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh, lineterminator="\n")
                w.writerow(HEADER)
                w.writerows(kept)

    summary: dict[str, int] = {}
    for f in fixes:
        summary[f[2]] = summary.get(f[2], 0) + 1
    summary["R6 headers (files)"] = headers_fixed
    for k in sorted(summary):
        print(f"{k}: {summary[k]}")
    if not DRY:
        os.makedirs(os.path.join(ROOT, "crosswalk"), exist_ok=True)
        out = os.path.join(ROOT, "crosswalk", "data-fixes.csv")
        existing = []
        if os.path.exists(out):
            with open(out, encoding="utf-8", newline="") as fh:
                existing = list(csv.reader(fh))[1:]
        rows = existing + fixes if fixes else existing
        with open(out, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["file", "line", "rule", "before", "after", "evidence"])
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
