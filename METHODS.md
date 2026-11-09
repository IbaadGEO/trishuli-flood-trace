# Methods

Trishuli Flood Trace is a personal, non-commercial reconstruction of the 26 August 2026 rock-ice avalanche, debris flow and flood that travelled from the Lirung massif (Langtang) down the Lende Khola, Bhote Koshi and Trishuli to the Narayani at Devghat. It uses only public, citable data (see `sources.csv`). It is an **illustrative reconstruction**, not a hydraulic or runout model, and not a validated flood-propagation dataset.

## What is observed and what is constructed

| Element | Status |
|---|---|
| Mapped extent (UNOSAT 4256) | Observed: preliminary satellite interpretation (Sentinel-2, Planet; 26–28 Aug), not field-validated |
| Mapped landslides, building and road grading (Copernicus EMS EMSR927) | Observed: photo-interpreted, within four mapped areas only. Shown separately, never timed |
| Gauge stage series (DHM, ten-minute) | Observed: instrument record archived on Zenodo (10.5281/zenodo.22679444). Stage is relative to each station's datum, not water depth |
| Barrier lakes (UNOSAT 4260) | Observed on 28 Aug (Cartosat-3). Formed after the event |
| Progression marker, extent reveal, implied rate | **Constructed** (below) |
| Channel elevation profile | **Derived** from a DEM (below), not a surveyed bed |

## Route

1. OSM waterways in the corridor (Overpass) form an undirected graph. Dijkstra's shortest path runs from the node nearest the UNOSAT detachment-zone centroid to the node nearest the Devghat gauge.
2. The route origin is ~0.9 km from the mapped source reference, at ~3,800 m DEM elevation, while the failure began at ~5,100–5,200 m. **The source-to-channel runout is not part of the route and is not timed.** The map draws it as a dashed red line: the shortest gap (~209 m) from the UNOSAT detachment-zone edge to the route origin, a schematic link, not a mapped flow path. Distances ("km along route") start at the route origin.
3. The path is densified to 40 m spacing. Shortest-path routing does not verify hydrological direction or the event's actual flow path at confluences.

## Timing evidence

Each piece of evidence is a time **window** (`anchors.csv`), typed by what it actually constrains:

| Evidence type | Meaning |
|---|---|
| Seismic origin time | USGS us7000tbwb, 02:52:10 UTC = 08:37 NPT. Applied at the route origin with a 0–2 min window, an assumption since the runout is untimed |
| Impact (CCTV, reported) | Gyirong Port, 08:44 reported; clock basis unverified (±1 min window) |
| Telemetry loss | Destroyed gauge (Syabrubesi, Betrawati): last transmission → next report absent. Brackets arrival **only if** the flood caused the loss |
| Rising-wave onset | Gauge (Galchhi, Malekhu, Kali Khola, Devghat): last sample at local background → first clearly risen sample. Malekhu (Phurke) is from the BIPAD river record (station 261, series 31967): background 3.35 m at 11:10, risen 3.96 m at 11:20, then lost after 11:40 |

These are reports used **only as checks**, never fitted:

| Report | Check result |
|---|---|
| Rasuwagadhi telemetry loss (08:40–08:50) | consistent |
| Malekhu/Phurke warning-level crossing 11:26 (CHWRR) | consistent with the gauge's own record: warning 7.0 m crossed 11:20–11:30, danger 8.0 m 11:30–11:40 |
| "Past Mugling by 13:00" (upper bound) | **conflict**: the instrument onset at Kali Khola, ~3 km downstream, is 13:10–13:20. The map follows the instrument record |

Peaks, threshold crossings, alerts and forecasts appear in the chronology but never constrain the timing.

## Interpolation

- The estimated minute at each route point is a piecewise-linear interpolation of window **midpoints** against route distance.
- Interpolating the window **earliest** and **latest** values gives a deterministic scenario envelope. It is not a statistical confidence interval, and it ignores route and location uncertainty.
- The "implied average rate" is the slope of this interpolation: a reach-average rate implied by the chosen windows, **not** a measured flow velocity or wave celerity.

## Extent reveal

1. UNOSAT 4256 extent polygons are rasterised on a Web Mercator zoom-12 grid (~34 m, `all_touched=True`).
2. Each pixel takes the estimated minute of its **nearest route point** (Euclidean). Pixels more than 3 km from the route are dropped.
3. Pixels whose nearest route point is the route origin are ground upstream of the timed route (the source/runout zone, ~158 ha). They are shown as **untimed** grey and never animated.
4. The reveal is **cumulative**: once revealed, a pixel stays. This is the mapped affected footprint appearing at its estimated time, not instantaneous inundation or depth. The fade from pale to brown over 25 min is illustrative only.

Known limits: nearest-point assignment can mis-time pixels across meander necks, on tributary backwater or on slope deposits, and the 3 km cutoff is an inclusion rule, not a connectivity test. Rasterisation and clipping make the revealed total (~6,556 ha timed + 158 ha untimed) differ slightly from UNOSAT's vector area (6,491 ha).

## Channel elevation profile

Terrarium DEM (zoom 12), a 3×3 minimum filter at each route point, then forced non-increasing downstream (`np.minimum.accumulate`) for display. Real channel beds have pools, steps and local adverse slopes, so this is **not** a bed survey. "m above DEM channel" in the tooltip uses this conditioned profile.

## Imagery

- The "before" and "after" layers are per-pixel **median** composites of the rendered Sentinel-2 L2A true-colour (TCI) assets. Pixels are kept if the scene classification is not cloud, shadow or cirrus and the blue band is below 150; the bright pixels are a fallback only. They use up to 16 scenes nearest the event within the windows shown in the app.
- They are for orientation only, not a reflectance change-analysis product.
- Gaps in "after" show the 2024 EOxCloudless basemap, which is pre-event.
- Scene IDs and valid-observation counts are not yet exported (planned).

## Reproducing

```bash
pip install -r requirements.txt
python -P build.py      # data; downloads are cached in raw/ (not committed)
python -P imagery.py    # imagery (~40 min)
```

Inputs placed by hand in `raw/`: EMSR927 vector zips (`raw/ems/`), the UNOSAT 4256 geodatabase (`raw/unosat/`) and the Zenodo 22679444 archive (`raw/zenodo/`). `inputs_manifest.json` records the SHA-256 of each input used.
