#!/usr/bin/env python3
"""Turn tab-separated table dumps (from `mysql -B`) into CSV and JSON release files.

Usage: export.py <tsv-dir> <out-dir>. Each <table>.tsv becomes <table>.csv and <table>.json.
"""
import csv
import json
import os
import sys

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for name in sorted(os.listdir(src)):
    if not name.endswith(".tsv"):
        continue
    table = name[:-4]
    with open(os.path.join(src, name), encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))
    header, data = rows[0], rows[1:]
    data = [[None if v == "NULL" else v for v in r] for r in data]
    with open(os.path.join(out, f"{table}.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows([["" if v is None else v for v in r] for r in data])
    with open(os.path.join(out, f"{table}.json"), "w", encoding="utf-8") as fh:
        json.dump([dict(zip(header, r)) for r in data], fh, ensure_ascii=False, indent=1)
    print(f"{table}: {len(data)} rows")
