FROM mysql:8.4.13

# MySQL Shell is not used by the import. Removing it shrinks the image and drops
# its bundled Python packages (e.g. certifi, flagged by the Trivy scan).
RUN microdnf remove -y mysql-shell && microdnf clean all

# SQL files live outside /docker-entrypoint-initdb.d so MySQL's entrypoint does not
# run them on its own. setup.sh is the only init script, and it runs them once,
# in order: schema -> countries -> CSV import -> extract -> sources, NBS and crosswalk tables.
COPY sql-scripts/tables_creation.sql /sql/01_tables.sql
COPY sql-scripts/countries.sql       /sql/02_countries.sql
COPY sql-scripts/extract.sql         /sql/04_extract.sql
COPY sql-scripts/sources.sql         /sql/05_sources.sql
COPY setup.sh /docker-entrypoint-initdb.d/03_setup.sh
RUN chmod +x /docker-entrypoint-initdb.d/03_setup.sh

COPY location-files /location_files
COPY sources/nbs2022/regions.csv sources/nbs2022/councils.csv sources/nbs2022/wards.csv /source_files/nbs2022/
COPY crosswalk/regions.csv crosswalk/districts.csv crosswalk/wards.csv /crosswalk_files/
