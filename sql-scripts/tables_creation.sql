-- Clean up (MySQL)

DROP TABLE IF EXISTS crosswalk_wards;
DROP TABLE IF EXISTS crosswalk_districts;
DROP TABLE IF EXISTS crosswalk_regions;
DROP TABLE IF EXISTS nbs_wards;
DROP TABLE IF EXISTS nbs_councils;
DROP TABLE IF EXISTS nbs_regions;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS wards;
DROP TABLE IF EXISTS districts;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS general;
DROP TABLE IF EXISTS countries;

-- Create Tables

CREATE TABLE countries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  iso CHAR(2) NOT NULL,
  name TEXT NOT NULL,
  nicename TEXT NOT NULL,
  iso3 CHAR(3) DEFAULT NULL,
  numcode INT DEFAULT NULL,
  phonecode INT NOT NULL
);

CREATE TABLE general (
  id INT AUTO_INCREMENT PRIMARY KEY,
  country_id INT,
  region VARCHAR(255) NOT NULL,
  regioncode INT NOT NULL,
  district VARCHAR(255) NOT NULL,
  districtcode INT NOT NULL,
  ward VARCHAR(255) NOT NULL,
  wardcode INT NOT NULL,
  street VARCHAR(255),
  places VARCHAR(255)
);

CREATE TABLE regions (
  region_name TEXT,
  region_code INT NOT NULL,
  general_locations_id INT,
  country_id INT,
  PRIMARY KEY(region_code)
);

CREATE TABLE districts (
  district_name TEXT,
  district_code INT NOT NULL,
  general_locations_id INT,
  region_id INT,
  country_id INT,
  PRIMARY KEY(district_code)
);

CREATE TABLE wards (
  ward_name TEXT,
  ward_code INT NOT NULL,
  district_id INT,
  region_id INT,
  country_id INT,
  general_locations_id INT,
  PRIMARY KEY(ward_code)
);

CREATE TABLE places (
  id INT AUTO_INCREMENT PRIMARY KEY,
  place_name TEXT,
  ward_id INT,
  district_id INT,
  region_id INT,
  country_id INT,
  general_locations_id INT
);

-- INDEXES

-- Countries
CREATE UNIQUE INDEX idx_countries_iso ON countries (iso);

-- Regions
CREATE INDEX idx_regions_country_id ON regions (country_id);
CREATE INDEX idx_regions_general_id ON regions (general_locations_id);

-- Districts
CREATE INDEX idx_districts_region_id ON districts (region_id);
CREATE INDEX idx_districts_country_id ON districts (country_id);
CREATE INDEX idx_districts_general_id ON districts (general_locations_id);

-- Wards
CREATE INDEX idx_wards_district_id ON wards (district_id);
CREATE INDEX idx_wards_region_id ON wards (region_id);
CREATE INDEX idx_wards_country_id ON wards (country_id);
CREATE INDEX idx_wards_general_id ON wards (general_locations_id);

-- Places
CREATE INDEX idx_places_ward_id ON places (ward_id);
CREATE INDEX idx_places_district_id ON places (district_id);
CREATE INDEX idx_places_region_id ON places (region_id);
CREATE INDEX idx_places_country_id ON places (country_id);
CREATE INDEX idx_places_general_id ON places (general_locations_id);

-- NBS 2022 census administrative units (sources/nbs2022). The source column names the publisher.

CREATE TABLE sources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  publisher VARCHAR(255) NOT NULL,
  url VARCHAR(500) NOT NULL,
  licence VARCHAR(500) NOT NULL,
  vintage VARCHAR(100) NOT NULL,
  sha256 CHAR(64) DEFAULT NULL,
  UNIQUE KEY uq_sources_name (name)
);

CREATE TABLE nbs_regions (
  region VARCHAR(100) NOT NULL PRIMARY KEY,
  zone VARCHAR(20) NOT NULL,
  population INT NOT NULL,
  households INT NOT NULL,
  councils INT NOT NULL,
  source VARCHAR(100) NOT NULL
);

CREATE TABLE nbs_councils (
  id INT AUTO_INCREMENT PRIMARY KEY,
  region VARCHAR(100) NOT NULL,
  seq INT NOT NULL,
  council VARCHAR(150) NOT NULL,
  council_type VARCHAR(20) NOT NULL,
  population INT NOT NULL,
  households INT NOT NULL,
  wards INT NOT NULL,
  source VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_nbs_councils (region, council),
  KEY idx_nbs_councils_type (council_type),
  CONSTRAINT fk_nbs_councils_region FOREIGN KEY (region) REFERENCES nbs_regions (region)
);

CREATE TABLE nbs_wards (
  id INT AUTO_INCREMENT PRIMARY KEY,
  region VARCHAR(100) NOT NULL,
  council VARCHAR(150) NOT NULL,
  seq INT NOT NULL,
  ward VARCHAR(150) NOT NULL,
  ward_type VARCHAR(10) NOT NULL,
  population INT NOT NULL,
  households INT NOT NULL,
  source VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_nbs_wards (region, council, ward),
  KEY idx_nbs_wards_ward (ward),
  CONSTRAINT fk_nbs_wards_council FOREIGN KEY (region, council) REFERENCES nbs_councils (region, council)
);

-- Crosswalk between the TCRA tables (regions, districts, wards) and the NBS 2022 tables (crosswalk/).

CREATE TABLE crosswalk_regions (
  tcra_region_code INT NOT NULL PRIMARY KEY,
  tcra_region VARCHAR(100) NOT NULL,
  nbs_region VARCHAR(100) NOT NULL,
  nbs_zone VARCHAR(20) NOT NULL,
  match_method ENUM('exact','normalised','fuzzy','manual') NOT NULL,
  score INT NOT NULL,
  source VARCHAR(100) NOT NULL,
  KEY idx_crosswalk_regions_nbs (nbs_region),
  CONSTRAINT fk_cw_regions_tcra FOREIGN KEY (tcra_region_code) REFERENCES regions (region_code),
  CONSTRAINT fk_cw_regions_nbs FOREIGN KEY (nbs_region) REFERENCES nbs_regions (region)
);

CREATE TABLE crosswalk_districts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tcra_district_code INT NOT NULL,
  tcra_district VARCHAR(150) NOT NULL,
  nbs_region VARCHAR(100) NOT NULL,
  nbs_council VARCHAR(150) NOT NULL,
  nbs_council_type VARCHAR(20) NOT NULL,
  match_method ENUM('exact','normalised','fuzzy','manual') NOT NULL,
  score INT NOT NULL,
  shared_units INT NOT NULL,
  tcra_units INT NOT NULL,
  nbs_wards INT NOT NULL,
  source VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_cw_districts (tcra_district_code, nbs_region, nbs_council),
  KEY idx_cw_districts_nbs (nbs_region, nbs_council),
  CONSTRAINT fk_cw_districts_tcra FOREIGN KEY (tcra_district_code) REFERENCES districts (district_code),
  CONSTRAINT fk_cw_districts_nbs FOREIGN KEY (nbs_region, nbs_council) REFERENCES nbs_councils (region, council)
);

CREATE TABLE crosswalk_wards (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tcra_ward_code INT NOT NULL,
  tcra_ward VARCHAR(255) NOT NULL,
  tcra_shehia VARCHAR(150) NOT NULL DEFAULT '',
  tcra_district_code INT NOT NULL,
  nbs_region VARCHAR(100) NOT NULL,
  nbs_council VARCHAR(150) NOT NULL,
  nbs_ward VARCHAR(150) NOT NULL,
  match_method ENUM('exact','normalised','fuzzy','manual') NOT NULL,
  score INT NOT NULL,
  source VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_cw_wards (tcra_ward_code, tcra_shehia, nbs_region, nbs_council, nbs_ward),
  KEY idx_cw_wards_tcra (tcra_ward_code),
  KEY idx_cw_wards_district (tcra_district_code),
  KEY idx_cw_wards_nbs (nbs_region, nbs_council, nbs_ward),
  CONSTRAINT fk_cw_wards_tcra FOREIGN KEY (tcra_ward_code) REFERENCES wards (ward_code),
  CONSTRAINT fk_cw_wards_nbs FOREIGN KEY (nbs_region, nbs_council, nbs_ward) REFERENCES nbs_wards (region, council, ward)
);
