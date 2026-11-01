#!/bin/bash
set -e

DB_NAME="${MYSQL_DATABASE:-locations}"
DB_USER="${MYSQL_USER:-root}"
DB_PASSWORD="${MYSQL_PASSWORD:-$MYSQL_ROOT_PASSWORD}"
MYSQL_SOCKET="/var/run/mysqld/mysqld.sock"

DATA_DIR="/location_files"

echo "🌍 Setting up Tanzania Locations DB (MySQL)..."

echo "Waiting for DB socket..."
until [ -S "$MYSQL_SOCKET" ]; do
  echo "Waiting for MySQL socket..."
  sleep 2
done

# Wait a bit more for MySQL to be fully ready
sleep 3

mysql_exec() {
  mysql --protocol=socket -S "$MYSQL_SOCKET" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "$1" 2>/dev/null
}

mysql_run_file() {
  mysql --protocol=socket -S "$MYSQL_SOCKET" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$1" 2>/dev/null
}

echo "Creating database if not exists..."
mysql --protocol=socket -S "$MYSQL_SOCKET" -u"$DB_USER" -p"$DB_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null

echo "Creating tables..."
mysql_run_file /docker-entrypoint-initdb.d/01_tables.sql

echo "Inserting countries..."
mysql_run_file /docker-entrypoint-initdb.d/02_countries.sql

echo "📄 Importing CSVs from: $DATA_DIR"

shopt -s nullglob
CSV_FILES=("$DATA_DIR"/*.csv)
if [ ${#CSV_FILES[@]} -eq 0 ]; then
  echo "❌ No CSV files found in $DATA_DIR"
  exit 1
fi

for csv_file in "${CSV_FILES[@]}"; do
  region_file=$(basename "$csv_file")
  echo "  ➕ Importing $region_file..."
  mysql --local-infile=1 --protocol=socket -S "$MYSQL_SOCKET" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
    -e "LOAD DATA LOCAL INFILE '$csv_file' INTO TABLE general \
        FIELDS TERMINATED BY ',' ENCLOSED BY '\"' \
        LINES TERMINATED BY '\n' IGNORE 1 ROWS \
        (region, regioncode, district, districtcode, ward, wardcode, street, places);" 2>/dev/null
done

echo "🛠 Updating country_id..."
mysql_exec "UPDATE general SET country_id = 210;"

echo "🧠 Running extract.sql..."
mysql_run_file /docker-entrypoint-initdb.d/04_extract.sql

echo "✅ Tanzania Locations DB setup complete (MySQL)!"