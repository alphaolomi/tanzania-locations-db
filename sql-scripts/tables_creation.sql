-- Clean up (MySQL)

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
