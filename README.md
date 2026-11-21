# Tanzania Locations

Tanzania's administrative geography as ready-to-use data: all **regions, districts, wards and
streets/places** on the mainland and in Zanzibar, with their TCRA postcode-based codes, the 2022 census
administrative units (NBS), and a crosswalk between the two. It loads into MySQL with one command.

Use it to fill address forms, region and district pickers, delivery zones, or anything else that needs an
accurate list of Tanzanian locations.

| Level | Rows | Mainland | Zanzibar |
|---|---|---|---|
| Regions | 31 | 26 | 5 |
| Districts | 169 | 159 | 10 |
| Wards (a Zanzibar ward is a postcode area) | 4,061 | 3,921 | 140 |
| Places (streets and named places, unique per ward) | 75,326 | 74,998 | 328 |
| Source rows (`general`) | 68,775 | 68,447 | 328 |

| NBS 2022 table | Rows |
|---|---|
| `nbs_regions` | 31 |
| `nbs_councils` | 195 |
| `nbs_wards` (wards and shehia) | 4,344 |

| Crosswalk table | Rows |
|---|---|
| `crosswalk_regions` | 31 |
| `crosswalk_districts` | 200 |
| `crosswalk_wards` | 4,190 |

### What changed in the counts

The mainland numbers differ from the earlier release (26 regions, 158 districts, 3,945 wards, 75,019 places,
68,571 source rows) because the data was cleaned and Zanzibar was added:
- **Source rows 68,571 to 68,447 (mainland):** 124 exact duplicate rows were removed.
- **Wards 3,945 to 3,921:** wards whose code had been filled down a spreadsheet column, or whose name carried a
  counter (`OLJORO NAMBA 5`, `KITAMA 1`), were reset to one code and one name each.
- **Districts 158 to 159:** Madaba (Ruvuma, code 577) has its own district, as its ward Lituta was filed under Songea.
- **Zanzibar added:** 5 regions (codes 71 to 75), 10 districts, 140 postcode areas, 328 shehia.

Every change is listed with its reason in [`crosswalk/data-fixes.csv`](crosswalk/data-fixes.csv) and summarised in
[`crosswalk/REVIEW.md`](crosswalk/REVIEW.md).

## Quick start (Docker)

You need Docker with Compose.

```bash
cp .env.example .env          # then change both passwords in .env
docker compose up -d --build
```

The first start builds the image and imports everything, which takes a few minutes. Then:

- **MySQL** is on `127.0.0.1:3307` (database `locations`, user `locations`).
- **phpMyAdmin** is on <http://127.0.0.1:8081>.

Both ports listen on localhost only. You can change them in `.env` (`MYSQL_HOST_PORT`, `PMA_HOST_PORT`).

To start again from scratch:

```bash
docker compose down -v && docker compose up -d --build
```

## Check the import

```bash
docker compose exec db mysql -u locations -p locations -e "
  SELECT 'regions', COUNT(*) FROM regions
  UNION ALL SELECT 'districts', COUNT(*) FROM districts
  UNION ALL SELECT 'wards', COUNT(*) FROM wards
  UNION ALL SELECT 'places', COUNT(*) FROM places
  UNION ALL SELECT 'nbs_wards', COUNT(*) FROM nbs_wards
  UNION ALL SELECT 'crosswalk_wards', COUNT(*) FROM crosswalk_wards;"
```

The counts should match the table above. CI runs the same check on every push.

## Data model

```
countries -+
           +- regions (region_code)
                +- districts (district_code -> region)
                     +- wards (ward_code -> district, region)
                          +- places (id -> ward, district, region)

nbs_regions - nbs_councils - nbs_wards             (NBS 2022 census units)

crosswalk_regions   links regions   and nbs_regions
crosswalk_districts links districts and nbs_councils   (many to many)
crosswalk_wards     links wards     and nbs_wards
sources                                                (where each file comes from)
```

- **`general`** is the raw import: one row per CSV line, with the region, district and ward names and
  codes, plus the street and place.
- **`regions`, `districts`, `wards`** hold one row per code, keyed by that code.
- **`places`** holds one row for each distinct street or place name within a ward. Names that differ
  only in case or accents count as one place.
- **`countries`** is a full ISO 3166 country list. Every location row points to Tanzania.
- **`nbs_regions`, `nbs_councils`, `nbs_wards`** are the administrative units of the 2022 census, with population
  and households. Zanzibar rows in `nbs_wards` are shehia (`ward_type = 'shehia'`). NBS publishes names, not codes.
- **`crosswalk_regions`, `crosswalk_districts`, `crosswalk_wards`** link the TCRA codes to the NBS units. Each row has a
  `match_method` (`exact`, `normalised`, `fuzzy` or `manual`) and a `score`. A postal district and a council are not
  one-to-one, so `crosswalk_districts` is many to many. In Zanzibar one postcode covers several shehia, so
  `crosswalk_wards` has one row per shehia (`tcra_shehia`).
- **`sources`** lists the publisher, URL, licence, vintage and SHA256 of each source.

The new tables have a `source` column naming the publisher, except `sources`. The existing tables and columns are unchanged.

### Crosswalk match rates

| Level | TCRA side | NBS 2022 side |
|---|---|---|
| Regions | 31 of 31 | 31 of 31 |
| Districts and councils | 169 of 169 linked | 195 of 195 linked |
| Wards, mainland | 3,877 of 3,921 (98.9%) | 3,877 of 3,956 (98.0%) |
| Shehia, Zanzibar | 313 of 328 (95.4%) | 313 of 388 (80.7%) |

What is not matched, and why, is in [`crosswalk/REVIEW.md`](crosswalk/REVIEW.md). Corrections go in
`crosswalk/overrides.csv` (with a reason), then rebuild.

## Zanzibar

Zanzibar has five regions with TCRA region codes 71 (Mjini Magharibi), 72 (Kusini Unguja), 73 (Kaskazini Unguja),
74 (Kusini Pemba) and 75 (Kaskazini Pemba). The postcode source gives one postcode for a group of shehia and no postal
area names, so a Zanzibar `ward` is the list of its shehia, and each shehia is a `street` row under it.

## The source data

There is one CSV per region in [`location-files/`](location-files):

```
region,regioncode,district,districtcode,ward,wardcode,street,places
ARUSHA,23,ARUSHA CBD,231,SEKEI,23101,SANAWARI,
```

Most of the source files label the code column `POSTCODE`.

**Found a wrong or missing location?** Edit the region's CSV and open a pull request. CI then validates
the CSVs, re-imports the data and checks the counts. If the totals change on purpose, update them in the
table above and in `.github/workflows/verify-data.yml`.

### Data checks and known issues

`scripts/validate_csv.py` checks the CSVs before every import. It checks:
- UTF-8 encoding and LF line endings;
- 8 columns per row;
- numeric codes;
- each ward code starts with its district code, and each district code with its region code. 2-digit
  district codes are exempt, because Dar es Salaam's districts are their own zones;
- each code always has the same name;
- one region per file;
- no stray spaces and no duplicate rows.

The issues that used to be listed in `scripts/known-data-issues.txt` (116 duplicate rows, 32 ward codes not under
their district, 25 codes with more than one name) have all been fixed, so the list is empty and CI fails on
any problem. See [`crosswalk/data-fixes.csv`](crosswalk/data-fixes.csv) for each change and its reason.

## Downloads

Each [release](../../releases) has the data attached, so you can use it without Docker:
- `tanzania-locations.sql.gz`: a full MySQL dump;
- every table (`general`, `regions`, `districts`, `wards`, `places`, `countries`, `sources`, `nbs_*` and `crosswalk_*`),
  each as `.csv` and `.json`;
- `SHA256SUMS`, to check the files.

## Rebuild the sources and the crosswalk

The committed CSVs are enough to import. To rebuild what is in `sources/` and `crosswalk/` from the originals:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-build.txt
.venv/bin/python -I scripts/fetch_sources.py        # downloads the NBS PDFs and the Zanzibar postcodes, checks their SHA256
.venv/bin/python -I scripts/extract_nbs.py          # sources/nbs2022/*.csv, checked against the totals printed in the reports
python3 scripts/build_zanzibar.py                   # location-files/ for the five Zanzibar regions
.venv/bin/python -I scripts/build_crosswalk.py      # crosswalk/*.csv and crosswalk/REVIEW.md
python3 scripts/validate_sources.py
```

## CI

| Job | What it checks |
|---|---|
| `validate-data` | The CSV checks above, the Zanzibar files, the NBS sources and the crosswalk (referential integrity, no duplicate keys, rebuilds identically) |
| `import` | Builds the image, imports everything and checks the row count of every table |
| `lint` | shellcheck, hadolint, actionlint and zizmor (workflow security) |
| `scan` | Trivy scan of the image for fixable critical vulnerabilities |

Tools and images are pinned by version or digest. Dependabot proposes updates weekly.

## Project layout

| Path | What it is |
|---|---|
| `location-files/` | Source data, one CSV per region |
| `sql-scripts/tables_creation.sql` | Schema. **It drops and recreates the tables.** |
| `sql-scripts/countries.sql` | Country list |
| `sql-scripts/extract.sql` | Builds regions, districts, wards and places from `general` |
| `setup.sh` | Import script run inside the container |
| `scripts/validate_csv.py` | CSV checks (see above) |
| `scripts/known-data-issues.txt` | Issues already in the data (now empty) |
| `scripts/clean_data.py` | The one-off cleaning of the TCRA data; logs to `crosswalk/data-fixes.csv` |
| `scripts/fetch_sources.py`, `extract_nbs.py`, `build_zanzibar.py`, `build_crosswalk.py`, `validate_sources.py` | Build and check `sources/` and `crosswalk/` |
| `sources/` | NBS 2022 units and the Zanzibar postcodes, as small CSVs with a README each |
| `crosswalk/` | TCRA to NBS links, `overrides.csv`, `unmatched.csv`, `data-fixes.csv`, `REVIEW.md` |
| `sql-scripts/sources.sql` | The `sources` rows |
| `scripts/export.py` | Builds the CSV and JSON release files for every table |
| `Dockerfile`, `docker-compose.yml` | MySQL 8.4 image and local stack |
| `.env.example` | Settings to copy to `.env` |

## Sources and credits

- [HackEAC/tanzania-locations-db](https://github.com/HackEAC/tanzania-locations-db): the base of this project, and its contributors.
- **TCRA** (Tanzania Communications Regulatory Authority): the postcode list that the regions, districts, wards and codes follow.
- **NBS** (National Bureau of Statistics): the 2022 Population and Housing Census administrative units (regions,
  councils, wards and shehia, with population and households).
- **tanzaniapostcode.com**: the Zanzibar postcodes and shehia names.

URLs, hashes and terms of each source are in the `sources` table and in the README of each folder under `sources/`.

Changes from the upstream project:
- the import moved to MySQL 8.4 and places are de-duplicated per ward;
- the data was cleaned, Zanzibar was added, and the NBS 2022 tables and the crosswalk were added;
- Docker defaults were hardened (localhost-only ports, pinned images, `.env.example`);
- the data is validated and the import is checked in CI;
- data files are attached to each release.

Licensed under the [GNU GPL v3.0](LICENSE), the same as the upstream project.
