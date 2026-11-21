-- The source files behind the data. sha256 is the hash of the file as published, as checked by scripts/fetch_sources.py.
-- The TCRA list has no hash: the base data comes from the per-region CSVs in location-files/.

INSERT INTO sources (name, publisher, url, licence, vintage, sha256) VALUES
('TCRA postcode list', 'Tanzania Communications Regulatory Authority (TCRA)', 'https://tcra.go.tz/services/publication-of-postcode-list',
 'No licence stated; statutory public list (Gazette Notice 240 of 22 Apr 2016)', '2016 list, base data from HackEAC/tanzania-locations-db', NULL),
('NBS 2022 vol 1a', 'National Bureau of Statistics (NBS), Tanzania', 'https://www.nbs.go.tz/statistics/subtopic/administrative-reports',
 'No licence stated; public statistics, cite NBS', '2022 Population and Housing Census, published 17 Dec 2022', '6f41eee70eefd764efaea876e0b13546666a69c5b91c1f50e5d9b38c3f78d1b9'),
('NBS 2022 vol 1b', 'National Bureau of Statistics (NBS), Tanzania', 'https://www.nbs.go.tz/statistics/subtopic/administrative-reports',
 'No licence stated; public statistics, cite NBS', '2022 Population and Housing Census, published 17 Dec 2022', 'fb715b4e9380056268b1b7eee5c87c54535f416a6cf75eebfbdc6fddf5980d15'),
('NBS 2022 vol 1c', 'National Bureau of Statistics (NBS), Tanzania', 'https://www.nbs.go.tz/statistics/subtopic/administrative-reports',
 'No licence stated; public statistics, cite NBS', '2022 Population and Housing Census, published 17 Dec 2022', 'bccf08bf8a2953b10a1ccb88c0827dcf22918c0e7d07bfb54052ad9f5950e851'),
('tanzaniapostcode.com', 'tanzaniapostcode.com', 'https://postal.datahub.io/tz/tz.csv',
 'No licence stated; postcodes are facts of the TCRA scheme', 'DataHub copy updated 27 Aug 2026 (Zanzibar rows only)', '351f070566e62e34138611065848f73f566c79c5bbe03dadc5d2dad0011758aa');
