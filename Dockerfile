FROM mysql:8.4.13

WORKDIR /docker-entrypoint-initdb.d

# Ensure init order: 01 schema -> 02 countries -> 03 setup (CSV) -> 04 extract
COPY sql-scripts/tables_creation.sql ./01_tables.sql
COPY sql-scripts/countries.sql ./02_countries.sql
COPY setup.sh ./03_setup.sh
COPY sql-scripts/extract.sql ./04_extract.sql
RUN chmod +x ./03_setup.sh

WORKDIR /
COPY location-files /location_files
