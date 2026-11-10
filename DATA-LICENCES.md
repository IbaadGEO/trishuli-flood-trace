# Data licences

Trishuli Flood Trace is created and maintained by **Ibaad Sidik**. © 2026 Ibaad Sidik for the original code and project text. This ownership notice does not claim ownership of the third-party material listed below or replace its licences and required credits.

The MIT licence in `LICENSE` covers the **code only**. Each data file published in `web/data/` keeps the terms of its source. This table records, from each source's published terms, what applies and what that requires of anyone reusing the files. Full source details are in `sources.csv`.

| Published file(s) | Derived from | Terms | What that requires |
|---|---|---|---|
| `meta.json` → `river` (route geometry, chainage) | OpenStreetMap waterways | **ODbL 1.0** | The route is a derivative database of OSM. It is made available under the ODbL; credit "© OpenStreetMap contributors"; share any further adaptation of it under the ODbL |
| `meta.json` → `river` elevation column; 3D terrain | Mapterhorn terrain tiles: Copernicus GLO-30 (© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA) | Copernicus full, free and open licence (Mapterhorn code BSD-3) | Credit Copernicus GLO-30 with the producer line and Mapterhorn (https://mapterhorn.com/attribution) |
| `meta.json` → timing fields; `anchors.csv` | This project, from the gauge and report sources below | MIT (as project output) plus source attribution | Cite the underlying evidence sources listed in `anchors.csv` |
| `unosat_extent.geojson`, `unosat_buildings.geojson`, `lakes.geojson`, `detachment.geojson`, `arrival.png` (rasterised extent) | UNOSAT product 4256 (and 4260 for lakes) | UNITAR terms of use | Credit UNOSAT with the product ID. UNITAR's terms distinguish extracts from substantial reproduction; this repo redistributes simplified extracts for non-commercial explanation. That is my reading of the terms, not a permission from UNITAR; for any further reuse, check the terms directly |
| `observed.geojson` (landslides), `buildings.geojson`, `roads.geojson`, `aois.geojson` | Copernicus EMS EMSR927 | CC BY 4.0 (© 2026 European Union) | Credit "Copernicus Emergency Management Service (© 2026 European Union), EMSR927" and state that the data were modified (simplified, attributes reduced) |
| `gauges.json` | DHM river-watch record, archived by Acharya & Paudel (2026), Zenodo 10.5281/zenodo.22679444 | CC BY 4.0 (deposit); underlying DHM data | Cite the Zenodo DOI and DHM as the original source |
| `archive/bipad_malekhu_261_20260826.csv` | NDRRMA BIPAD river API (DHM data), station 261, retrieved 9 Nov 2026 | Terms not stated | Ten-minute stage readings kept as a factual record of the evidence used; credit DHM and BIPAD |
| `events.json` | Mixed: reports, papers, USGS, NDRRMA, the Guardian, Wikipedia | Facts with attribution; any quoted text stays under its publisher's terms | Keep the per-item source links; Wikipedia-derived wording is CC BY-SA 4.0 |
| `s2/` tiles, `s2.json` | Copernicus Sentinel-2 L2A (via Element84 Earth Search) | Copernicus Sentinel data terms | Credit "Contains modified Copernicus Sentinel data 2026" |
| `sites/*.webp`, `sites.json` (before/after site comparisons) | Vantor Open Data Program and Planet Crisis Response Program scenes; source-area "before" from EOxCloudless 2025 | **CC BY-NC 4.0** (Vantor, Planet); **CC BY-NC-SA 4.0** for `source_pre.webp` | Non-commercial use; credit "© Vantor, Open Data Program" or "© Planet Labs PBC" with the scene ID; the crops are modified (warped, cropped, contrast-stretched); share adaptations of `source_pre.webp` under CC BY-NC-SA 4.0 |
| `media/gyirong_cctv1.mp4` and poster | Wikimedia Commons file "Mudslide at Gyirong Port 1.webm" (revision 1279062472) | Classified public domain on Commons (automated recording). This is the platform's assessment, not a release by an identified owner | Keep the source link and the "camera operator unidentified" note; re-encoded to MP4, no other changes |
| `media/model_s7.mp4` and poster | Huang, Chen & Wang (2026), Zenodo 10.5281/zenodo.22884627 | **CC BY 4.0** | Cite the authors and DOI; label it as a model scenario |
| `media/park_*.mp4` and posters | Park (2026), Zenodo 10.5281/zenodo.22566624 v2.0.0 | **CC BY 4.0** | Cite the author, version DOI and file name; label as model scenarios; keep the preprint caveat |
| `sites/esa_pre.webp`, `sites/esa_post.webp` | ESA renderings via Wikimedia Commons: Sentinel-2 24 Aug 2026; Landsat 9 26 Aug 2026 | **CC BY-SA 3.0 IGO** (24 Aug) and **CC BY 4.0** (26 Aug) | Credit ESA (and Copernicus / USGS-NASA for the data); resized only; share adaptations of the 24 Aug image under CC BY-SA 3.0 IGO |
| `docs/media/` (README animations and images) | Screen recordings of this app (EOxCloudless 2025 basemap, UNOSAT and EMS layers); before/after wipes from `sites/*.webp`; sped-up excerpts of `media/model_s7.mp4` and `media/park_gorge_oblique_5s.mp4` | **CC BY-NC-SA 4.0** for the app recordings and the source-site wipe; **CC BY-NC 4.0** for the other wipes; **CC BY 4.0** for the simulation excerpts | Same credits as the files they come from; these are adaptations (cropped, resized, sped up, re-encoded as animated WebP/GIF) |
| Basemap (not stored here; streamed) and `web/og.jpg` (share image) | EOxCloudless 2025 by EOX IT Services GmbH | **CC BY-NC-SA 4.0** | Non-commercial use only; credit EOX with a link to https://cloudless.eox.at; adaptations such as the share image are shared under CC BY-NC-SA 4.0 |

Notes:

- USGS ComCat data are US public domain; credit USGS.
- NDRRMA and CHWRR documents state no reuse licence. Only facts and figures are used here, with citations, and no document text is reproduced.
- "Public" is not the same as "openly licensed": where a source states no licence, nothing here grants one.
