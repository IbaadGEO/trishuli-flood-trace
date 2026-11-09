# Data licences

The MIT licence in `LICENSE` covers the **code only**. Each data file published in `web/data/` keeps the terms of its source. This table records, from each source's published terms, what applies and what that requires of anyone reusing the files. Full source details are in `sources.csv`.

| Published file(s) | Derived from | Terms | What that requires |
|---|---|---|---|
| `meta.json` → `river` (route geometry, chainage) | OpenStreetMap waterways | **ODbL 1.0** | The route is a derivative database of OSM. It is made available under the ODbL; credit "© OpenStreetMap contributors"; share any further adaptation of it under the ODbL |
| `meta.json` → `river` elevation column; 3D terrain | Mapzen Terrarium tiles (SRTM and others, AWS Open Data) | Per underlying providers (see the AWS registry entry) | Credit the terrain tiles; check provider terms before redistributing elevation values in bulk |
| `meta.json` → timing fields; `anchors.csv` | This project, from the gauge and report sources below | MIT (as project output) plus source attribution | Cite the underlying evidence sources listed in `anchors.csv` |
| `unosat_extent.geojson`, `unosat_buildings.geojson`, `lakes.geojson`, `detachment.geojson`, `arrival.png` (rasterised extent) | UNOSAT product 4256 (and 4260 for lakes) | UNITAR terms of use | Credit UNOSAT with the product ID. UNITAR's terms distinguish extracts from substantial reproduction; this repo redistributes simplified extracts for non-commercial explanation. For any further reuse, check the terms directly |
| `observed.geojson` (landslides), `buildings.geojson`, `roads.geojson`, `aois.geojson` | Copernicus EMS EMSR927 | CC BY 4.0 (© 2026 European Union) | Credit "Copernicus Emergency Management Service (© 2026 European Union), EMSR927" and state that the data were modified (simplified, attributes reduced) |
| `gauges.json` | DHM river-watch record, archived by Acharya & Paudel (2026), Zenodo 10.5281/zenodo.22679444 | CC BY 4.0 (deposit); underlying DHM data | Cite the Zenodo DOI and DHM as the original source |
| `events.json` | Mixed: reports, papers, USGS, NDRRMA, the Guardian, Wikipedia | Facts with attribution; any quoted text stays under its publisher's terms | Keep the per-item source links; Wikipedia-derived wording is CC BY-SA 4.0 |
| `s2/` tiles, `s2.json` | Copernicus Sentinel-2 L2A (via Element84 Earth Search) | Copernicus Sentinel data terms | Credit "Contains modified Copernicus Sentinel data 2026" |
| Basemap (not stored here; streamed) and `web/og.jpg` (share image, which shows it) | EOxCloudless 2024 by EOX IT Services GmbH | **CC BY-NC-SA 4.0** | Non-commercial use only; credit EOX with a link to https://cloudless.eox.at; adaptations such as the share image are shared under CC BY-NC-SA 4.0 |

Notes:

- USGS ComCat data are US public domain; credit USGS.
- NDRRMA and CHWRR documents state no reuse licence. Only facts and figures are used here, with citations, and no document text is reproduced.
- "Public" is not the same as "openly licensed": where a source states no licence, nothing here grants one.
