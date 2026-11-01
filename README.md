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
| Places (streets and named places, unique per ward) | 75,013 |
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

**Found a wrong or missing location?** Edit the region's CSV and open a pull request. CI re-imports the
data and checks the counts. If the totals change on purpose, update them in the table above and in
`.github/workflows/verify-data.yml`.

## Project layout

| Path | What it is |
|---|---|
| `location-files/` | Source data, one CSV per region |
| `sql-scripts/tables_creation.sql` | Schema. **It drops and recreates the tables.** |
| `sql-scripts/countries.sql` | Country list |
| `sql-scripts/extract.sql` | Builds regions, districts, wards and places from `general` |
| `setup.sh` | Import script run inside the container |
| `Dockerfile`, `docker-compose.yml` | MySQL 8.4 image and local stack |
| `.env.example` | Settings to copy to `.env` |

## Credits and licence

This project builds on [HackEAC/tanzania-locations-db](https://github.com/HackEAC/tanzania-locations-db)
and the work of its contributors. Changes in this fork:
- the import moved to MySQL 8.4;
- places are de-duplicated per ward;
- Docker defaults were hardened (localhost-only ports, pinned images, `.env.example`);
- data import is checked in CI.

Licensed under the [GNU GPL v3.0](LICENSE), the same as the upstream project.
