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

-- Places from street
INSERT INTO places(place_name, ward_id, district_id, region_id, country_id, general_locations_id)
SELECT DISTINCT street, wardcode, districtcode, regioncode, country_id, id
FROM general
WHERE street IS NOT NULL AND street <> '';

-- Places from places column
INSERT INTO places(place_name, ward_id, district_id, region_id, country_id, general_locations_id)
SELECT DISTINCT places, wardcode, districtcode, regioncode, country_id, id
FROM general
WHERE places IS NOT NULL AND places <> '';
