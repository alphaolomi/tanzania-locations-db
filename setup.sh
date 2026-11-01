#!/bin/bash
# Imports the Tanzania geography data. MySQL's entrypoint runs this once, on first start.
set -euo pipefail

DB_NAME="${MYSQL_DATABASE:-locations}"
DB_USER="${MYSQL_USER:-root}"
export MYSQL_PWD="${MYSQL_PASSWORD:-$MYSQL_ROOT_PASSWORD}"  # keeps the password off the command line
MYSQL_SOCKET="/var/run/mysqld/mysqld.sock"
DATA_DIR="/location_files"
SQL_DIR="/sql"

echo "Setting up the Tanzania geography database..."

until [ -S "$MYSQL_SOCKET" ]; do
  echo "Waiting for the MySQL socket..."
  sleep 2
done

mysql_cli() {
  mysql --protocol=socket -S "$MYSQL_SOCKET" -u"$DB_USER" "$@"
}

mysql_cli -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "Creating tables..."
mysql_cli "$DB_NAME" < "$SQL_DIR/01_tables.sql"

echo "Inserting countries..."
mysql_cli "$DB_NAME" < "$SQL_DIR/02_countries.sql"

echo "Importing CSVs from $DATA_DIR..."
shopt -s nullglob
CSV_FILES=("$DATA_DIR"/*.csv)
if [ ${#CSV_FILES[@]} -eq 0 ]; then
  echo "No CSV files found in $DATA_DIR" >&2
  exit 1
fi

for csv_file in "${CSV_FILES[@]}"; do
  echo "  importing $(basename "$csv_file")"
  mysql_cli --local-infile=1 "$DB_NAME" -e "LOAD DATA LOCAL INFILE '$csv_file' INTO TABLE general
    FIELDS TERMINATED BY ',' ENCLOSED BY '\"'
    LINES TERMINATED BY '\n' IGNORE 1 ROWS
    (region, regioncode, district, districtcode, ward, wardcode, street, places);"
done

echo "Setting country_id..."
mysql_cli "$DB_NAME" -e "UPDATE general SET country_id = 210;"

echo "Building regions, districts, wards and places..."
mysql_cli "$DB_NAME" < "$SQL_DIR/04_extract.sql"

echo "Tanzania geography database is ready."
