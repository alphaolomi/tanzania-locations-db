FROM mysql:8.4.13

# SQL files live outside /docker-entrypoint-initdb.d so MySQL's entrypoint does not
# run them on its own. setup.sh is the only init script, and it runs them once,
# in order: schema -> countries -> CSV import -> extract.
COPY sql-scripts/tables_creation.sql /sql/01_tables.sql
COPY sql-scripts/countries.sql       /sql/02_countries.sql
COPY sql-scripts/extract.sql         /sql/04_extract.sql
COPY setup.sh /docker-entrypoint-initdb.d/03_setup.sh
RUN chmod +x /docker-entrypoint-initdb.d/03_setup.sh

COPY location-files /location_files
