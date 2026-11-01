-- MySQL equivalents: use INSERT IGNORE and DISTINCT selects

-- Regions
INSERT IGNORE INTO regions(region_code, region_name, country_id, general_locations_id)
SELECT DISTINCT regioncode, region, country_id, id FROM general;

-- Districts
INSERT IGNORE INTO districts(district_code, district_name, region_id, country_id, general_locations_id)
SELECT DISTINCT districtcode, district, regioncode, country_id, id FROM general;

-- Wards
INSERT IGNORE INTO wards(ward_code, ward_name, district_id, region_id, country_id, general_locations_id)
SELECT DISTINCT wardcode, ward, districtcode, regioncode, country_id, id FROM general;

-- Places: one row per distinct name within a ward, taken from both the
-- street and places columns. The comparison is case-sensitive (utf8mb4_bin),
-- which matches the upstream PostgreSQL import (75,020 places).
INSERT INTO places(place_name, ward_id, district_id, region_id, country_id, general_locations_id)
SELECT name, wardcode, MIN(districtcode), MIN(regioncode), MIN(country_id), MIN(id)
FROM (
  SELECT TRIM(street) COLLATE utf8mb4_bin AS name, wardcode, districtcode, regioncode, country_id, id
  FROM general WHERE street IS NOT NULL AND TRIM(street) <> ''
  UNION ALL
  SELECT TRIM(places) COLLATE utf8mb4_bin, wardcode, districtcode, regioncode, country_id, id
  FROM general WHERE places IS NOT NULL AND TRIM(places) <> ''
) AS p
GROUP BY name, wardcode;
