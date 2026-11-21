# Zanzibar postcodes

- **Publisher:** tanzaniapostcode.com, which lists the postcode of each shehia (the Zanzibar equivalent of a ward).
- **Retrieved from:** the DataHub copy, <https://postal.datahub.io/tz/tz.csv> (updated 27 Aug 2026).
  Only the five Zanzibar regions are kept (328 of 74,139 rows); `fetch_sources.py` does the filtering.
- **Licence:** the publisher states none. The postcode numbers and names are facts of the national
  postcode scheme (regions 71 to 75 in TCRA's National Postcode Allocation Plan). Confirm terms with the
  publisher or TCRA before relying on this file commercially.
- **Columns:** `postcode`, `shehia`, `region`, `district`, `source`.

One postcode covers several shehia (140 postcodes for 328 shehia). The source does not name the postal area,
so `scripts/build_zanzibar.py` names each Zanzibar postal ward after the shehia it covers.

SHA256 of the original file (full Tanzania CSV):

```
351f070566e62e34138611065848f73f566c79c5bbe03dadc5d2dad0011758aa  tz.csv
```
