<div align="center">

# Trishuli Flood Trace

**Tracing the 26 August 2026 Lirung rock–ice avalanche and flood, 200 km from a Himalayan ice face to the plains of Nepal**

[![Live map](https://img.shields.io/badge/live_map-trishuli--flood--trace.vercel.app-1971c2?style=flat-square)](https://trishuli-flood-trace.vercel.app) ![MapLibre GL JS 6.17](https://img.shields.io/badge/MapLibre_GL_JS-6.17-396cb2?style=flat-square) ![Python 3.13](https://img.shields.io/badge/Python-3.13-3776ab?style=flat-square) ![Data: public and cited](https://img.shields.io/badge/data-public_%26_cited-2f9e44?style=flat-square) [![Code: MIT](https://img.shields.io/badge/code-MIT-868e96?style=flat-square)](LICENSE)

<a href="https://trishuli-flood-trace.vercel.app"><img src="docs/media/map_run.webp" width="820" alt="The 3D map following the flood front from the Lirung massif down the Lende Khola and Bhote Koshi gorges, with event captions"></a>

<sub>The live map following the flood front at its 4× playback setting, sped up further here (Lirung massif to Malekhu). Basemap: EOxCloudless 2025, CC BY-NC-SA 4.0.</sub>

</div>

## About

This is part of my wider learning in coding, data, machine learning and geoscience. It is not a professional or commissioned study. The map uses published, citable public data (satellite mapping, agency reports, gauge records and research papers) and derives its route, arrival estimates and display figures from them. Where sources disagree, the map shows both.

## The event

At about 08:37 Nepal time on 26 August 2026, roughly 100 million m³ of rock and glacier ice broke away from the north side of the Langtang Lirung massif at about 5,150–5,200 m (estimates vary by study: Roy et al., 2026; Li, H. et al., 2026; Clarke et al., 2026). Seismometers recorded a magnitude 5.2 landslide-classified signal at 08:37 (USGS, 2026a). This project uses that signal as its time reference; the exact moment the failure began cannot be read from it (Guo et al., 2026).

```mermaid
flowchart LR
  A["<b>Rock–ice avalanche</b><br/>~5,150–5,200 m<br/>08:37 NPT signal"] --> B["<b>Debris flow</b><br/>forms by ~4,000 m<br/>Lende Khola gorge"]
  B --> C["<b>Gyirong Port</b><br/>China–Nepal border<br/>08:44 NPT, ~22 km"]
  C --> D["<b>Water-laden flood</b><br/>Bhote Koshi → Trishuli<br/>gauges stop transmitting"]
  D --> E["<b>Devghat</b><br/>rise begins 14:30–14:40<br/>~200 km downstream"]
```

The falling mass turned into a debris flow that scoured the narrow Lende Khola gorge and reached the border crossing at Gyirong Port about seven minutes later, after roughly 22 km and 3,400 m of descent (Guo et al., 2026). Below Syabrubesi it began dropping its largest rock and continued as a more water-laden flood down the Bhote Koshi and Trishuli (Clarke et al., 2026). River gauges stopped transmitting one after another, so the timing upstream is bracketed rather than measured (Acharya and Paudel, 2026). The rising wave reached the Devghat gauge between 14:30 and 14:40. Xu (2026) attributes this first wave to the debris flow itself, possibly with a quick breach of debris dumped across the river. The barrier lakes formed during the cascade, were mapped on 28 August and only began overflowing that afternoon.

By 7 November 2026, 1,459 people were reported dead and 5,285 were still missing in Nepal (The Guardian, 7 November 2026). The figures are provisional.

## What the map does

<img src="docs/media/app.jpg" alt="The full app: 3D map with the flood front near Betrawati, an evidence panel on the right, a key-events list and three charts along the bottom">

- **Follows the front** along a 203 km river route in 3D, revealing the satellite-mapped flood extent (UNITAR-UNOSAT, 2026a) by estimated arrival time.
- **Interpolates timing between evidence windows:** a seismic origin, a border-port camera, and gauge onsets and telemetry losses. The map shows an earliest–latest envelope, and reported times that disagree with the gauges are marked as conflicts with their sources.
- **Separates what was observed from what is estimated**: mapped landslides and building damage (Copernicus EMS, 2026) are never given a time.
- **Steps through 17 key events**, each with a sourced caption, and links them to before/after imagery and published simulations.
- **Shows what was reported at the time:** a Reporting tab plays as a live feed, adding each news or responder report at the time that version went public, so early guesses about the cause appear as they were made. Times come from archived copies or from records that show no later edits.

<img src="docs/media/reporting.jpg" width="320" alt="The Reporting feed at 13:12 NPT: a status line showing 3 of 6 reports public, a Xinhua report that has just arrived with a note on what was unconfirmed at the time, and the earlier Red Cross field report below it">

### Charts that move with the timeline

<img src="docs/media/charts.gif" alt="Three charts updating as the flood front advances: estimated progression with evidence windows, the channel elevation profile, and gauge hydrographs from the DHM ten-minute record">

Left: estimated progression against the evidence windows. Centre: channel elevation profile from the Copernicus GLO-30 DEM (conditioned for display, not a surveyed bed). Right: river stage at six gauges from the Department of Hydrology and Meteorology (DHM) ten-minute record (Acharya and Paudel, 2026). A seventh gauge, Malekhu, comes from the BIPAD portal (NDRRMA, 2026c) and is used for timing only.

## Before and after

Open satellite imagery of four of the app's six comparisons (the app adds Betrawati and an ESA pair taken during the flood), resampled to a common grid so they line up. In the app, each panel also says what the images show and, separately, what the cited sources report happened there.

<table>
<tr>
<td width="50%"><img src="docs/media/wipe_source.webp" alt="Collapse source on the Lirung massif before and after: a bare failure surface replaces glacier ice"><br><b>Collapse source.</b> A bare failure surface where glacier ice was; the detached body covered about 0.72 km² (Guo et al., 2026).<br><sub>EOxCloudless 2025 (10 m mosaic) / Planet Pelican, 29 Sep 2026</sub></td>
<td width="50%"><img src="docs/media/wipe_timure.webp" alt="The Rasuwagadhi–Timure confluence before and after: riverside buildings gone and a much wider channel"><br><b>Rasuwagadhi–Gyirong border and Timure.</b> Riverside buildings gone and a far wider channel; part of the flow surged about 2 km up the side valley into China (Guo et al., 2026; Clarke et al., 2026).<br><sub>PlanetScope, 27 May 2026 / Planet Pelican, 1 Sep 2026</sub></td>
</tr>
<tr>
<td><img src="docs/media/wipe_syabrubesi.webp" alt="Syabrubesi before and after: flood deposits cover the low ground where the bazaar stood"><br><b>Syabrubesi.</b> Flood deposits over the low ground where the bazaar stood; Copernicus EMS graded 323 building points here as destroyed.<br><sub>PlanetScope, 27 May 2026 / Vantor WorldView Legion, 7 Sep 2026</sub></td>
<td><img src="docs/media/wipe_bidur.webp" alt="Bidur and Trishuli Bazaar before and after: the river and canal replaced by a broad sheet of sediment"><br><b>Bidur and Trishuli Bazaar.</b> The river and its canal replaced by a broad sheet of grey sediment, about 75 km along the river from the source.<br><sub>Vantor WorldView Legion, 5 Feb 2026 / Vantor WorldView-2, 8 Sep 2026</sub></td>
</tr>
</table>

<sub>Imagery © Planet Labs PBC (Crisis Response Program) and © Vantor (Open Data Program), CC BY-NC 4.0; EOxCloudless 2025 by EOX IT Services GmbH, CC BY-NC-SA 4.0. Cropped, warped and contrast-stretched. Scene IDs are in <a href="web/data/sites.json"><code>web/data/sites.json</code></a>.</sub>

## Published simulations

Other researchers have modelled the cascade, and the app shows their animations with the authors' own caveats. They are **model scenarios, not footage**, and are independent of this map's timeline: neither confirms the other.

<table>
<tr>
<td width="56%"><img src="docs/media/sim_huang_s7.webp" alt="Simulation of the first ten minutes: flow height of the rock, ice and water mass from the source to Gyirong"><br><b>The first ten minutes.</b> A rock–ice–water flow model (r.avaflow) from an imposed 200 million m³ release. With frictional melting included it reaches Gyirong at 457 s, close to the authors' benchmark of 458 s; runs without melting take 593 s or more.<br><sub>Huang, Chen and Wang (2026), Movie S7, CC BY 4.0. Paper in preparation.</sub></td>
<td width="44%"><img src="docs/media/sim_park_gorge.webp" alt="Oblique 3D view of a simulated flow descending the upper gorge from the source to Syabrubesi"><br><b>The upper gorge, first 24 minutes.</b> A 30 m rock–ice flow model from the source to Syabrubesi; flow thickness exaggerated four times for display.<br><sub>Park (2026), v2.0.0, CC BY 4.0. Preprint, not peer reviewed.</sub></td>
</tr>
</table>

<sub>Shown sped up (2×) and converted to animated WebP for this page; the app plays the original files unmodified. Two further full-corridor animations by Park are in the app's "Published simulations" panel.</sub>

## Method at a glance

<img src="docs/media/method.svg" alt="Method figure. Left: five stages, from raw observations to evidence anchors, temporal interpolation, uncertainty and 3D visualisation. Right: distance along the river route against time, showing the eight evidence windows coloured by basis, the interpolated arrival line, the earliest to latest envelope and two reports used only as checks, one of which conflicts">

**Figure 1. Methodological framework and temporal reconstruction of the 26th August 2026 Langtang Lirung flood.** The workflow illustrates the processing of observational data into evidence anchors, temporal interpolation, uncertainty estimates and 3D visualisation. The time-distance diagram shows eight evidence windows along the reconstructed river route, the interpolated flood arrival trajectory and its earliest-to-latest timing envelope. Two independently reported observations are included as validation checks, including one that conflicts with the reconstructed timing.

<sub>Drawn from the project's data by <a href="docs/method_figure.py"><code>docs/method_figure.py</code></a>. Full method and limits: <a href="METHODS.md">METHODS.md</a>.</sub>

## Observed, reported or estimated

| Layer | Status | Source |
|---|---|---|
| Flood extent, affected buildings, barrier lakes, detachment zone | Observed (satellite interpretation, 26–28 Aug) | UNITAR-UNOSAT (2026a, 2026b) |
| Mapped landslides; building and road damage grading | Observed (photo-interpreted, four mapping areas) | Copernicus EMS (2026) |
| River stage at seven gauges (six from the Zenodo archive, Malekhu from BIPAD) | Observed (DHM ten-minute record) | Acharya and Paudel (2026); NDRRMA (2026c) |
| Seismic signal time (the time reference, not the measured start of the failure) | Observed (seismic) | USGS (2026a) |
| Border-port arrival | Reported (camera, 10:59 Beijing = 08:44 NPT; clock not independently verified) | Guo et al. (2026) |
| Arrival time along the rest of the route | **Estimated** between evidence windows | this project, see [METHODS.md](METHODS.md) |
| Channel elevation profile | **Derived** from the GLO-30 DEM | this project |
| Source size, volume, precursors, weather | Reported, with ranges where studies differ | see references |

The app shows aggregate figures only and holds no names or personal details of victims.

### How to read it

The moving marker and the timed footprint are interpolated displays, not a hydraulic or runout model. Between evidence points the front position is interpolated, and each mapped pixel takes the time of its nearest river point. The simulation videos are other researchers' models, credited separately, and play no part in this timing.

**Not for emergency use.**

## Built with

- **Web:** MapLibre GL JS 6.17 with 3D terrain, sky and fog; plain JavaScript and SVG charts; no build step; hosted on Vercel.
- **Data pipeline:** Python (rasterio, GeoPandas, Shapely, NumPy, SciPy): OSM river routing with Dijkstra, evidence-window timing, DEM profiling, Sentinel-2 median composites and before/after scene alignment.
- **Terrain and basemap:** Copernicus GLO-30 via Mapterhorn; EOxCloudless 2025.

Method, limits and every timing decision: [METHODS.md](METHODS.md) · Evidence anchors: [anchors.csv](anchors.csv) · Full source list with versions and licences: [sources.csv](sources.csv) · Terms per data file: [DATA-LICENCES.md](DATA-LICENCES.md)

## References

**Research papers, preprints and reports**

- Acharya, S. and Paudel, A. (2026) *The Bhote Koshi-Trishuli flash flood of 26 August 2026, Rasuwa, Nepal: data and analysis code*. Version 3.0.0. Zenodo. doi:10.5281/zenodo.22679444.
- Clarke, B., Zachariah, M., Davies, B., Hock, R., Immerzeel, W. et al. (2026) *Rapid warming in the Himalaya exacerbates geohazard cascades beyond adaptation limits*. World Weather Attribution scientific report No. 92 (corrected 28 September 2026). doi:10.25560/136420.
- Guo, L., Xu, J., Wang, Y. et al. (2026) 'Progressive entrainment transformed a high-elevation ice–rock avalanche in Nepal into the 26 August debris flow in Gyirong, Xizang' [in Chinese], *Chinese Science Bulletin*, published online 1 September 2026. doi:10.1360/CSB-2026-1255.
- Huang, S., Chen, C.-M. and Wang, B. (2026) *Datasets and analysis scripts for 'The first minutes of the 2026 Nepal rock-ice avalanche and flash flood'*. Zenodo. doi:10.5281/zenodo.22884627.
- Li, H., Li, P., Hu, K., Liu, J., Liu, S., Kang, S., Su, P. and You, Y. (2026) 'The 26 August 2026 Chhochen Khola ice-rock avalanche–debris flow cascade on the Nepal–China border: dynamics, numerical computation, and causes', *Journal of Mountain Science*, 23(10), pp. 4663–4681. doi:10.1007/s11629-026-1482-y.
- Li, R. (2026) 'When a high-mountain slope failure cascades downstream: physical footprint and evolving exposure of the 2026 Gyirong mixed rock–ice cascade', *arXiv* preprint 2609.04563.
- Park, H. (2026) *Langtang 2026 rock-ice avalanche and flood: revised simulation animations and supporting outputs*. Version 2.0.0. Zenodo. doi:10.5281/zenodo.22566624.
- Roy, P., Majumdar, R., Chauhan, P. et al. (2026) '26 August 2026 rock–ice avalanche in Nepal: rapid assessment of the cascading disaster using satellite data', *Journal of the Indian Society of Remote Sensing*, 54(13), pp. 4901–4909. doi:10.1007/s12524-026-02611-x.
- Xu, D. (2026) 'The 26 August 2026 Langtang Lirung ice–rock avalanche and its transboundary cascade: a multi-source observational reconstruction in the Bhote Koshi basin', *EarthArXiv* preprint, version 2. doi:10.31223/X56793.

**Agency reports, mapping and records**

- CHWRR (2026) *Assessment Report II: Rasuwa-Bhote Koshi Flood Event 2026* (revised 13 September 2026). Kathmandu: Centre for Hydrological Warning and Risk Reduction, Government of Nepal.
- Copernicus EMS (2026) *EMSR927: Flood in Nepal, grading products for AOI01, AOI02, AOI03 and AOI05*. © 2026 European Union. Available at: https://mapping.emergency.copernicus.eu/activations/EMSR927/.
- ICIMOD (2026) *Second major Himalayan flood in seven weeks raises new questions about mountain risk*. Press release, 13 October 2026. Kathmandu: ICIMOD.
- International Charter Space and Major Disasters (2026) *Activation 1052: Flood in Nepal*.
- NDRRMA (2026a) *Rapid Damage and Needs Assessment: Rasuwa-Bhotekoshi Flood 2026*. Kathmandu: National Disaster Risk Reduction and Management Authority.
- NDRRMA (2026b) *Situation Report 19*, 20 September 2026. Kathmandu: NDRRMA.
- NDRRMA (2026c) *BIPAD portal river-station register and stage record, Trishuli at Furke Khola (Malekhu), station 261*. Available at: https://bipadportal.gov.np/.
- UNITAR-UNOSAT (2026a) *Product 4256: flood extent, affected buildings, detachment zone and barrier lakes, Rasuwa, Nepal (FL20260826NPL)*. Available at: https://unosat.org/products/4256.
- UNITAR-UNOSAT (2026b) *Product 4260: satellite-detected barrier lakes*. Available at: https://unosat.org/products/4260.
- USGS (2026a) *M 5.2 landslide, Nepal–China border region (us7000tbwb)*. ANSS Comprehensive Catalog.
- USGS (2026b) *M 4.2 landslide signal (us7000tc90)*. ANSS Comprehensive Catalog.

**Imagery, terrain and media**

- ESA (2026) *Nepal flash flood imaged by satellites*. Sentinel-2 (24 August) and Landsat 9 (26 August) renderings, published 31 August 2026.
- EOX IT Services GmbH (n.d.) *EOxCloudless 2025*. CC BY-NC-SA 4.0. Available at: https://cloudless.eox.at.
- Mapterhorn (n.d.) *Terrain tiles* (Copernicus GLO-30 DEM; © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the EU and ESA). Available at: https://mapterhorn.com.
- OpenStreetMap contributors (2026) *Waterways, Bhote Koshi–Trishuli corridor*. ODbL 1.0.
- Planet Labs PBC (2026) *Crisis Response Program: nepal-flash-flood-2026-08-26*. Source Cooperative. CC BY-NC 4.0.
- Vantor (2026) *Open Data Program: Nepal-Flooding-Aug-2026*. CC BY-NC 4.0.
- Wikimedia Commons (2026) *Mudslide at Gyirong Port 1.webm* (revision 1279062472).

Accessed 8–9 November 2026. Links, versions and licences for every source are in [sources.csv](sources.csv). Secondary summaries used for cross-checks (Wikipedia timeline; The Guardian, 7 November 2026) are listed there too.

## Run it locally

```bash
python -m http.server 5173 -d web
```

Open http://localhost:5173. The site is static files with no build step. The data can be rebuilt from the public inputs; the steps are in the [Reproducing](METHODS.md#reproducing) section of the methods.

## Licence

Code: [MIT](LICENSE). Data and imagery keep their sources' terms, several of them non-commercial; see [DATA-LICENCES.md](DATA-LICENCES.md). The animations and images in `docs/media/` are screen recordings of the app and adaptations of the imagery and simulations credited above, shared under the same terms.
