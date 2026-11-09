# Trishuli Flood Trace

3D reconstruction of the 26 August 2026 Nepal–Tibet debris flow: from the rock-ice avalanche on the Lirung massif (08:37 NPT) down the Lende Khola, Bhote Koshi and Trishuli to Devghat (~200 km of river; the rising wave reached the Devghat gauge about 6 h after the collapse).

> **Scope:** a personal passion project, not a professional or commissioned study. It uses only already available, widely used, citable public data (satellite mapping products, agency reports, published papers, open datasets). Where sources conflict, both are shown and cited; no unpublished data or agency correspondence is involved.
>
> Independent, non-commercial reconstruction for education and understanding. Not an official product and not for emergency use. The extent is a preliminary satellite interpretation (UNOSAT), and the timing between gauge and report evidence is estimated.

Documentation: [METHODS.md](METHODS.md) (how everything is built and its limits) · [sources.csv](sources.csv) (every source, version, licence) · [DATA-LICENCES.md](DATA-LICENCES.md) (terms per data file) · [anchors.csv](anchors.csv) (timing evidence and checks) · [inputs_manifest.json](inputs_manifest.json) (input checksums) · [requirements.txt](requirements.txt).

Share image (`web/og.jpg`): screenshot of this app over the EOxCloudless 2024 basemap by EOX IT Services GmbH ([cloudless.eox.at](https://cloudless.eox.at)), licensed [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/); also contains modified Copernicus Sentinel data and UNOSAT-derived mapping.

## Deploy (Vercel)

The site is the static `web/` folder. `vercel.json` sets it as the output directory, creates `web/config.js` from the example if absent, and sets cache headers (7 days for imagery tiles; data files are revalidated on every load so they always match the code). Import the GitHub repository in Vercel with the default settings; no environment variables are needed.

## Run locally

```bash
python -m http.server 5173 -d web
```

Open http://localhost:5173. Static files only, no build step.

### Optional ArcGIS basemap

By default the map uses the keyless EOxCloudless 2025 mosaic. The code can instead use Esri World Imagery and imagery labels with a personal ArcGIS API key (basemap privilege only, referrer-restricted): copy `web/config.example.js` to `web/config.js` and paste the key. `config.js` is git-ignored. Browser map keys are visible to anyone who opens the page; the referrer restriction is what limits their use.

## Rebuild data

```bash
python -P build.py
```

Needs the packages in `requirements.txt`. Downloads are cached in `raw/`. Two inputs must be placed by hand:
- `raw/ems/`: the Copernicus EMS EMSR927 grading products ("vectors" zips, unzipped)
- `raw/unosat/`: the UNOSAT product 4256 geodatabase (`FL20260826NPL.gdb.zip`, unzipped)
- `raw/zenodo/`: the Zenodo 22679444 archive (`zenodo_upload.zip`, unzipped into `raw/zenodo/extracted/`)

Build the before/after site comparisons (reads open Vantor and Planet scenes over HTTP, a few minutes):

```bash
python -P sites.py
```

Then build the before/after Sentinel-2 imagery (about 40 minutes; reads Sentinel-2 L2A COGs from AWS, no login):

```bash
python -P imagery.py
```

The "before" and "after" composites are per-pixel medians of the clear observations from the scenes nearest the event, from late July to late September. Monsoon cloud makes single-date images unusable. The scene-classification cloud mask is applied plus a brightness filter for haze; tiles cover only a ~1.5 km buffer around the flood corridor.

## What is observed and what is estimated

| Layer | Status | Source |
|---|---|---|
| Corridor flood extent, affected buildings, barrier lakes, detachment zone | Observed (satellite) | UNOSAT product 4256 (UNITAR terms of use) |
| Mapped landslides (shown separately, not timed), building and road damage grading (4 areas) | Observed (photo-interpreted) | Copernicus EMS Rapid Mapping EMSR927, © 2026 European Union, CC BY |
| Gauge stage series, station IDs/coordinates, thresholds | Observed (DHM ten-minute record; stage relative to station datum) | Acharya & Paudel (2026), Zenodo [10.5281/zenodo.22679444](https://doi.org/10.5281/zenodo.22679444), CC BY 4.0; Phurke values from CHWRR Assessment Report II |
| Times at Gyirong Port, Syabrubesi, Betrawati, Malekhu, Mugling, Devghat | Reported | CHWRR/DHM reports, via Wikipedia timeline |
| Malekhu (Phurke) ten-minute stage, 26 Aug | Observed (DHM telemetry) | NDRRMA BIPAD river API, station 261 (series 31967) |
| When each part of the mapped extent was reached | **Estimated**: interpolated between the midpoints of typed evidence windows (gauge onsets and telemetry losses, USGS origin, Gyirong Port camera time), with an earliest/latest scenario envelope; reports such as threshold crossings are checks only. See [METHODS.md](METHODS.md) and [anchors.csv](anchors.csv) | this repo |
| Channel elevation profile | **Derived**: DEM samples, minimum-filtered and forced non-increasing for display; not a surveyed bed | this repo |
| Source parameters, precursor, rainfall, district deaths | Reported (ranges where studies disagree) | USGS, JMS, JISRS, ICIMOD, arXiv 2609.04563, NDRRMA SitRep 19 |
| River path | OpenStreetMap contributors (ODbL) | Overpass |
| Terrain | Copernicus GLO-30 DEM (30 m) | Mapterhorn terrain tiles; GLO-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA |
| Satellite basemap (default) | Observed (2025 cloud-free mosaic, pre-event) | EOxCloudless 2025 by EOX IT Services GmbH, CC BY-NC-SA 4.0, free for non-commercial use with attribution; contains modified Copernicus Sentinel data 2025 |
| Before/after imagery | Observed (median composites, date ranges shown in the app) | Contains modified Copernicus Sentinel data 2026, via Element84 Earth Search |
| Before/after site comparisons (5 sites) | Observed (single scenes; dates, sensors and scene IDs shown in each panel) | Vantor Open Data Program and Planet Crisis Response Program, both CC BY-NC 4.0; source-area "before" from EOxCloudless 2025 (CC BY-NC-SA 4.0). Built by `sites.py` |

The app shows aggregate figures only. It holds no names or personal details of victims.
