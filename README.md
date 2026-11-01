# Tanzania Geography

Tanzania's administrative geography as ready-to-use data: all **regions, districts, wards and
streets/places**, with their codes, loaded into MySQL with one command.

Use it to fill address forms, region and district pickers, delivery zones, or anything else that needs an
accurate list of Tanzanian locations.

| Level | Rows |
|---|---|
| Regions | 26 |
| Districts | 158 |
| Wards | 3,945 |
| Places (streets and named places, unique per ward) | 75,019 |
| Source rows (`general`) | 68,571 |

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
  UNION ALL SELECT 'places', COUNT(*) FROM places;"
```

The counts should match the table above. CI runs the same check on every push.

## Data model

```
countries ─┐
           └─ regions (region_code)
                └─ districts (district_code → region)
                     └─ wards (ward_code → district, region)
                          └─ places (id → ward, district, region)
```

- **`general`** is the raw import: one row per CSV line, with the region, district and ward names and
  codes, plus the street and place.
- **`regions`, `districts`, `wards`** hold one row per code, keyed by that code.
- **`places`** holds one row for each distinct street or place name within a ward. Names that differ
  only in case or accents count as one place.
- **`countries`** is a full ISO 3166 country list. Every location row points to Tanzania.

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

Some issues already exist in the source data. They are listed in
[`scripts/known-data-issues.txt`](scripts/known-data-issues.txt):

| Issue | Count |
|---|---|
| Duplicate rows | 116 |
| Ward code not under its district's code | 32 |
| Code with more than one name | 25 |

CI fails only on problems that are **not** in that list. After you fix some of them, regenerate the list:

```bash
python3 scripts/validate_csv.py --write-baseline
```

## Downloads

Each [release](../../releases) has the data attached, so you can use it without Docker:
- `tanzania-geography.sql.gz`: a full MySQL dump;
- `regions`, `districts`, `wards`, `places` and `countries`, each as `.csv` and `.json`;
- `SHA256SUMS`, to check the files.

## CI

| Job | What it checks |
|---|---|
| `validate-data` | The CSV checks above |
| `import` | Builds the image, imports everything and checks the row counts |
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
| `scripts/known-data-issues.txt` | Issues already in the data |
| `scripts/export.py` | Builds the CSV and JSON release files |
| `Dockerfile`, `docker-compose.yml` | MySQL 8.4 image and local stack |
| `.env.example` | Settings to copy to `.env` |

## Credits and licence

This project builds on [HackEAC/tanzania-locations-db](https://github.com/HackEAC/tanzania-locations-db)
and the work of its contributors. Changes in this fork:
- the import moved to MySQL 8.4;
- places are de-duplicated per ward;
- Docker defaults were hardened (localhost-only ports, pinned images, `.env.example`);
- the data is validated and the import is checked in CI;
- data files are attached to each release.

Licensed under the [GNU GPL v3.0](LICENSE), the same as the upstream project.
