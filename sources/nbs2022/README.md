# NBS 2022 administrative units

- **Publisher:** National Bureau of Statistics (NBS), Tanzania, with the Office of the Chief Government
  Statistician for Zanzibar.
- **Document:** 2022 Population and Housing Census, Administrative Units Population Distribution Report,
  volumes 1a (Tanzania), 1b (Mainland) and 1c (Zanzibar). Published 17 Dec 2022; census night 22/23 Aug 2022.
- **Listing:** <https://www.nbs.go.tz/statistics/subtopic/administrative-reports>
- **Licence:** NBS states no licence for the reports. They are public statistics: cite NBS.
  Only names, hierarchy and the printed population and household counts are extracted.

| File | Rows | Content |
|---|---|---|
| `regions.csv` | 31 | 26 Mainland and 5 Zanzibar regions |
| `councils.csv` | 195 | Councils (District, Town, Municipal, City) in each region |
| `wards.csv` | 4,344 | Wards (Mainland) and shehia (Zanzibar) in each council |

The reports give names and sequence numbers only, with no numeric codes and nothing below ward or shehia.

Built by `scripts/extract_nbs.py` from the PDFs that `scripts/fetch_sources.py` downloads. The extraction
is checked against the totals printed in the reports (wards add up to their council, councils to their
region, regions to Tanzania Mainland, Tanzania Zanzibar and vol 1a) and fails if any differ.

SHA256 of the original files:

```
6f41eee70eefd764efaea876e0b13546666a69c5b91c1f50e5d9b38c3f78d1b9  vol1a (Tanzania)
fb715b4e9380056268b1b7eee5c87c54535f416a6cf75eebfbdc6fddf5980d15  vol1b (Mainland)
bccf08bf8a2953b10a1ccb88c0827dcf22918c0e7d07bfb54052ad9f5950e851  vol1c (Zanzibar)
```
