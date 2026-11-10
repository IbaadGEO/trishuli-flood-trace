"""Build static data for the Trishuli flood viewer.

Inputs (cached under raw/): OSM rivers (Overpass), Mapterhorn terrain tiles (Copernicus GLO-30 over Nepal),
Copernicus EMS EMSR927 grading vectors (raw/ems/), UNOSAT product 4256 geodatabase (raw/unosat/),
DHM gauge series from Zenodo 22679444 (raw/zenodo/), BIPAD Malekhu readings (raw/bipad/).
Outputs under web/data/. Run: python -P build.py  (add --update-manifest after deliberately replacing an input)
"""
import csv, glob, hashlib, heapq, io, json, math, os, sys
import numpy as np, requests, geopandas as gpd, pandas as pd, shapely
from PIL import Image
from rasterio import features
from rasterio.transform import from_origin
from scipy import ndimage
from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.ops import nearest_points

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = os.path.join(HERE, "raw"), os.path.join(HERE, "web", "data")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "trishuli-flood-viewer/0.1 (research visualisation)"}

S, W, N, E = 27.68, 84.38, 28.36, 85.62  # corridor bbox
Z = 12  # DEM zoom (~34 m px at this latitude)
ZX = 12  # extent raster zoom (~34 m px); z13 exceeds the 4096 px texture limit on many phones


def need(pattern, hint):  # one hand-placed input, or stop with instructions
    hit = glob.glob(os.path.join(RAW, pattern), recursive=True)
    if not hit: sys.exit(f"Missing input raw/{pattern}\n  {hint}\n  See README > Rebuild the data.")
    return hit[0]


def sha(p):  # a file's SHA-256, or a folder's: hash of "relative path  file SHA-256" lines, like sha256sum output
    if not os.path.isdir(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
    fs = sorted(f for f in glob.glob(os.path.join(p, "**", "*"), recursive=True) if os.path.isfile(f))
    return hashlib.sha256("".join(f"{sha(f)}  {os.path.relpath(f, p).replace(os.sep, '/')}\n" for f in fs).encode()).hexdigest()


def inputs():  # the downloads, plus the extracted files the build actually reads
    g = lambda *a: sorted(glob.glob(os.path.join(RAW, *a), recursive=True))
    return (g("ems", "*.zip") + [d for d in g("ems", "EMSR927_*") if os.path.isdir(d)] + g("unosat", "*.zip") + g("unosat", "*.gdb")
            + g("zenodo", "*.zip") + g("zenodo", "extracted", "**", "gauge_timeseries.json") + g("bipad", "*.json") + g("osm_rivers.json") + g("dem"))


UNOSAT = need("unosat/**/*.gdb", "Download product 4256 (FL20260826NPL.gdb.zip) from https://unosat.org/products/4256 and unzip it into raw/unosat/")
ZEN = need("zenodo/extracted/**/gauge_timeseries.json", "Download zenodo_upload.zip from https://doi.org/10.5281/zenodo.22679444 into raw/zenodo/ and unzip it into raw/zenodo/extracted/")

relp = lambda p: os.path.relpath(p, HERE).replace(os.sep, "/")
MANIFEST = os.path.join(HERE, "inputs_manifest.json")
if os.path.exists(MANIFEST) and "--update-manifest" not in sys.argv:  # same inputs as the committed build, or stop
    want, have = json.load(open(MANIFEST))["files"], {relp(p): sha(p) for p in inputs()}
    bad = {f: "missing" if f not in have else "not in manifest" if f not in want else "changed" for f in want.keys() | have.keys() if want.get(f) != have.get(f)}
    if bad: sys.exit(f"Inputs differ from inputs_manifest.json: {bad}\n  Rerun with --update-manifest if the change is deliberate.")


def unosat(layer):
    g = gpd.read_file(UNOSAT, layer=f"UNOSAT_{layer}")
    assert g.crs is not None and g.crs.to_2d().to_epsg() == 4326, f"{layer}: expected WGS 84 (EPSG:4326) horizontal CRS, got {g.crs}"
    return g.set_crs(4326, allow_override=True)  # drop the EGM96 vertical part (compound EPSG:9707)

# Timing evidence, minutes after the 08:37 NPT seismic signal (a time reference, not the measured detachment time), as brackets (earliest, latest). Interpolation uses the
# bracket midpoints; the earliest/latest bounds give a deterministic scenario envelope, not a statistical interval.
# Gauge brackets and coordinates: DHM ten-minute record as archived in Acharya & Paudel (2026), Zenodo
# 10.5281/zenodo.22679444 v3.0.0 (onset = last background sample -> first risen sample; destroyed stations:
# last transmission -> next absent report, assuming the flood caused the loss).
# How strong each kind of bound is, and why it is where it is
BASIS = {
    "seismic origin time": ("assumed", "The 08:37 seismic signal is a time reference, not a measured detachment or arrival time; a 0-2 min window is assumed at the route origin"),
    "impact (surveillance camera)": ("reported", "Camera time from published reports; the +-1 min margin is chosen for an unverified camera clock"),
    "telemetry loss": ("inferred", "Brackets arrival only if the flood caused the loss of transmission"),
    "rising-wave onset": ("observed", "Bounded by two consecutive ten-minute gauge samples"),
}
# (name, lat, lon, earliest, latest, evidence type, note, source)
ANCHORS = [
    ("Route origin", 28.289, 85.521, 0, 2, "seismic origin time", "Collapse signal 02:52:10 UTC (USGS us7000tbwb); route starts at the OSM network ~0.9 km from the mapped source, so the source-to-channel runout is not timed", "USGS ComCat"),
    ("Gyirong Port", 28.276, 85.378, 6, 8, "impact (surveillance camera)", "Gyirong Port surveillance video 10:59 Beijing time = 08:44 NPT (Guo et al. 2026, peer reviewed); CHWRR gives the same time. Camera clock not independently verified", "Guo et al. (2026) Chin Sci Bull; CHWRR via WWA report 92"),
    ("Syabrubesi gauge", 28.170650, 85.342554, 13, 23, "telemetry loss", "Last report 08:50 (3.80 m), next report absent by 09:00", "DHM via Zenodo 22679444"),
    ("Betrawati gauge", 27.970000, 85.180000, 43, 53, "telemetry loss", "Last report 09:20 (3.55 m), next report absent by 09:30", "DHM via Zenodo 22679444"),
    ("Galchhi gauge", 27.802328, 85.003050, 103, 113, "rising-wave onset", "Last background sample 10:20, first risen 10:30", "DHM via Zenodo 22679444"),
    ("Malekhu (Phurke) gauge", 27.802439, 84.844102, 153, 163, "rising-wave onset", "Last background sample 11:10 (3.35 m), first risen 11:20 (3.96 m); warning 7.0 m crossed 11:20-11:30 (7.78 m), danger 8.0 m 11:30-11:40 (10.48 m); no transmission after 11:40. CHWRR reports warning 11:26, consistent", "DHM via BIPAD river API, station 261 (series 31967)"),
    ("Kali Khola gauge", 27.833000, 84.546000, 273, 283, "rising-wave onset", "Last background sample 13:10, first risen 13:20", "DHM via Zenodo 22679444"),
    ("Devghat gauge", 27.710000, 84.430000, 353, 363, "rising-wave onset", "Last background sample 14:30, first risen 14:40", "DHM via Zenodo 22679444"),
]
# Reports that are not arrival observations: checked against the fitted onset, never fitted. (name, lat, lon, minute, relation, note, source)
CHECKS = [
    ("Rasuwagadhi gauge", 28.271297, 85.377649, 13, "onset by", "Last report 08:40 (1.62 m), next absent by 08:50", "DHM via Zenodo 22679444"),
    ("Mugling", 27.853, 84.560, 263, "onset by", "CHWRR: wave crossed Mugling at 13:00 (an upper bound). The Kali Khola gauge onset 3 km downstream (13:10-13:20) is consistent with it", "CHWRR Assessment Report II Table 2"),
]


def get(url, path, **kw):
    if not os.path.exists(path):
        r = requests.get(url, headers=UA, timeout=120, **kw); r.raise_for_status()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(r.content)
    return open(path, "rb").read()


def hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(a))


# ---------- 1. river path from collapse to Devghat ----------
q = f"""[out:json][timeout:120];
(way["waterway"="river"]({S},{W},{N},{E});
 way["waterway"~"river|stream"](28.15,85.33,{N},{E}););
out geom;"""
osm = json.loads(get("https://overpass-api.de/api/interpreter", os.path.join(RAW, "osm_rivers.json"), params={"data": q}))
adj = {}
for el in osm["elements"]:
    pts = [(round(g["lat"], 6), round(g["lon"], 6)) for g in el.get("geometry", [])]
    for a, b in zip(pts, pts[1:]):
        d = hav(*a, *b)
        adj.setdefault(a, []).append((b, d)); adj.setdefault(b, []).append((a, d))
nodes = list(adj)
ntree = cKDTree(np.array(nodes))


def nearest(lat, lon):
    return nodes[ntree.query([lat, lon])[1]]


def dijkstra(src, dst):
    dist, prev, pq = {src: 0}, {}, [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == dst: break
        if d > dist[u]: continue
        for v, w in adj[u]:
            if d + w < dist.get(v, 1e18):
                dist[v], prev[v] = d + w, u; heapq.heappush(pq, (d + w, v))
    path = [dst]
    while path[-1] != src: path.append(prev[path[-1]])
    return path[::-1]


src, dst = nearest(*ANCHORS[0][1:3]), nearest(*ANCHORS[-1][1:3])
# The route starts at the OSM river node nearest the source reference point (ANCHORS[0]), not at the detachment zone itself
origin = {"reference": [ANCHORS[0][2], ANCHORS[0][1]], "snapped": [src[1], src[0]], "snapM": round(hav(*ANCHORS[0][1:3], *src))}
print("route origin snapped", origin["snapM"], "m from the reference point")
path = dijkstra(src, dst)
chain = np.concatenate([[0], np.cumsum([hav(*a, *b) for a, b in zip(path, path[1:])])])
# densify to ~40 m spacing for DEM sampling and arrival lookup
dense_c = np.arange(0, chain[-1], 40.0)
P = np.array(path)
dlat, dlon = np.interp(dense_c, chain, P[:, 0]), np.interp(dense_c, chain, P[:, 1])
print(f"river path {chain[-1] / 1000:.1f} km, {len(path)} vertices")

ptree = cKDTree(np.c_[dlat, dlon])
snap = lambda la, lo: ptree.query([la, lo])
anc_i = [snap(a[1], a[2])[1] for a in ANCHORS]  # each anchor's nearest route point
anc_c = [float(dense_c[i]) for i in anc_i]
anc_snap = [round(hav(a[1], a[2], dlat[i], dlon[i])) for a, i in zip(ANCHORS, anc_i)]  # m from given point to route
assert all(np.diff(anc_c) > 0), f"anchors out of order along river: {anc_c}"
lo_t, hi_t = [a[3] for a in ANCHORS], [a[4] for a in ANCHORS]
mid_t = [(a + b) / 2 for a, b in zip(lo_t, hi_t)]
arrival = np.interp(dense_c, anc_c, mid_t)  # minutes after 08:37: piecewise linear between bracket midpoints
arr_lo, arr_hi = np.interp(dense_c, anc_c, lo_t), np.interp(dense_c, anc_c, hi_t)  # scenario envelope
check_rows = []
for name, la, lo, m, rel, note, srcname in CHECKS:
    i = snap(la, lo)[1]; c = float(dense_c[i]); est = float(np.interp(c, anc_c, mid_t)); earliest = float(np.interp(c, anc_c, lo_t))
    status = "consistent" if est <= m else ("consistent within envelope" if earliest <= m else "CONFLICT")
    check_rows.append((name, la, lo, c, m, rel, round(est, 1), status, note, srcname, round(hav(la, lo, dlat[i], dlon[i]))))
    print(f"check {name}: reported {rel} {m} min, estimated onset {est:.0f} (earliest {earliest:.0f}) -> {status}")

# ---------- 2. DEM mosaic (Mapterhorn Copernicus GLO-30, Terrarium-encoded, Web Mercator) ----------
def tx(lon): return (lon + 180) / 360 * 2 ** Z
def ty(lat): return (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2 ** Z

x0, x1, y0, y1 = int(tx(W)), int(tx(E)), int(ty(N)), int(ty(S))
dem = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        # one 512 px Mapterhorn tile at Z-1 covers 2x2 of our 256 px Z tiles: take this tile's quadrant
        b = get(f"https://tiles.mapterhorn.com/{Z - 1}/{x // 2}/{y // 2}.webp", os.path.join(RAW, "dem", f"mt_{Z - 1}_{x // 2}_{y // 2}.webp"))
        a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float32)[(y % 2) * 256:(y % 2 + 1) * 256, (x % 2) * 256:(x % 2 + 1) * 256]
        dem[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
cols = np.array([(tx(lo) - x0) * 256 for lo in dlon]).astype(int)
rows = np.array([(ty(la) - y0) * 256 for la in dlat]).astype(int)
bed = ndimage.minimum_filter(dem, size=3)[rows, cols]
bed = np.minimum.accumulate(bed)  # display conditioning of a DEM channel profile, not a surveyed bed (real beds have local adverse slopes)

# ---------- 3. observed extent (UNOSAT + Copernicus EMS) timed by interpolated arrival ----------
def slim(g):  # ~3 m simplification + 1e-5° grid keeps polygon files small for the browser
    return g.set_geometry(shapely.set_precision(g.geometry.simplify(0.00003).values, 1e-5))


# The exact EMSR927 deliveries used (one per AOI): latest grading available for each area when downloaded.
EMS_PRODUCTS = ["EMSR927_AOI01_GRA_PRODUCT_v1", "EMSR927_AOI02_GRA_PRODUCT_v2", "EMSR927_AOI03_GRA_MONIT01_v1", "EMSR927_AOI05_GRA_MONIT01_v2"]


def ems(kind):
    fs = []
    for prod in EMS_PRODUCTS:
        if not os.path.isdir(os.path.join(RAW, "ems", prod)):
            sys.exit(f"Missing input raw/ems/{prod}/\n  Download its vector zip from https://mapping.emergency.copernicus.eu/activations/EMSR927/ and unzip it there.")
        hit = glob.glob(os.path.join(RAW, "ems", prod, "**", f"*_{kind}_v*.shp"), recursive=True)
        assert len(hit) <= 1, f"{prod}: expected at most one {kind} layer, found {hit}"
        fs += hit
    stray = set(os.listdir(os.path.join(RAW, "ems"))) - set(EMS_PRODUCTS) - {p + ".zip" for p in EMS_PRODUCTS}
    assert not stray, f"unlisted EMS inputs in raw/ems (add to EMS_PRODUCTS or remove): {stray}"
    parts = [gpd.read_file(f).assign(aoi=os.path.basename(f).split("_")[1]) for f in fs]
    bad = [f for f, g in zip(fs, parts) if g.crs is None or g.crs.to_epsg() != 4326]
    assert not bad, f"EMS layers not in EPSG:4326: {bad}"
    g = pd.concat(parts, ignore_index=True)
    return gpd.GeoDataFrame(g[g.geometry.notna()], crs=4326)

obs = ems("observedEventA")[["obj_desc", "aoi", "geometry"]]
extent = unosat("Multisensor_20260826_20260828_FloodExtent")[["geometry"]]
R = 6378137.0
res = 2 * math.pi * R / 2 ** ZX / 256  # metres per px at the equator (Web Mercator units)
gx0, gx1, gy0, gy1 = int(tx(W) / 2 ** Z * 2 ** ZX), int(tx(E) / 2 ** Z * 2 ** ZX) + 1, int(ty(N) / 2 ** Z * 2 ** ZX), int(ty(S) / 2 ** Z * 2 ** ZX) + 1
mx0, my0 = gx0 * 256 * res - math.pi * R, math.pi * R - gy0 * 256 * res
shape = ((gy1 - gy0) * 256, (gx1 - gx0) * 256)
geoms = extent.geometry.to_crs(3857)  # UNOSAT extent only: every EMS observedEvent polygon is a mapped landslide, not inundation
wet = features.rasterize(((g, 1) for g in geoms if g is not None and not g.is_empty), out_shape=shape,
                         transform=from_origin(mx0, my0, res, res), dtype="uint8", all_touched=True).astype(bool)
r_, c_ = np.nonzero(wet)
lon_w = np.degrees((mx0 + (c_ + 0.5) * res) / R)
lat_w = np.degrees(2 * np.arctan(np.exp((my0 - (r_ + 0.5) * res) / R)) - math.pi / 2)
lat0 = math.radians((S + N) / 2)
kx, ky = 111320 * math.cos(lat0), 110540
dist, idx = cKDTree(np.c_[dlon * kx, dlat * ky]).query(np.c_[lon_w * kx, lat_w * ky], distance_upper_bound=3000)
ok = np.isfinite(dist)  # drop mapped water far from the modelled flow path (e.g. unrelated tributaries)
r_, c_, idx, dist = r_[ok], c_[ok], idx[ok], dist[ok]
print(f"observed px kept {ok.sum()} / {ok.size}")

ra, rb, ca, cb = r_.min(), r_.max() + 1, c_.min(), c_.max() + 1
img = np.zeros((rb - ra, cb - ca, 4), np.uint8)
# untimed: source/runout ground upstream of the timed route (nearest route point is the origin) or inside the mapped detachment zone
det_px = features.rasterize(((g, 1) for g in unosat("Landsat9_20260826_DetachmentZone").geometry.to_crs(3857)), out_shape=shape,
                            transform=from_origin(mx0, my0, res, res), dtype="uint8", all_touched=True).astype(bool)
untimed = (idx == 0) | det_px[r_, c_]
print(f"untimed px {untimed.sum()} ({det_px[r_, c_].sum()} inside the detachment zone)")
m = np.round(arrival[idx]).astype(np.uint16)
img[r_ - ra, c_ - ca, 0], img[r_ - ra, c_ - ca, 1] = m >> 8, m & 255
# B channel: display opacity (89-255, stronger near channel); the value 1 flags untimed source-zone pixels
img[r_ - ra, c_ - ca, 2] = np.where(untimed, 1, 255 * np.clip(1 - dist / 800, 0.35, 1)).astype(np.uint8)
img[r_ - ra, c_ - ca, 3] = 255
Image.fromarray(img, "RGBA").save(os.path.join(OUT, "arrival.png"), optimize=True)
lonx = lambda c: math.degrees((mx0 + c * res) / R)
latx = lambda r: math.degrees(2 * math.atan(math.exp((my0 - r * res) / R)) - math.pi / 2)
corners = [[lonx(ca), latx(ra)], [lonx(cb), latx(ra)], [lonx(cb), latx(rb)], [lonx(ca), latx(rb)]]
cell_ha = (res * math.cos(lat0)) ** 2 / 1e4
area_by_min = np.bincount(m[~untimed], minlength=int(arrival.max()) + 1) * cell_ha
untimed_ha = float(untimed.sum() * cell_ha)

# ---------- 4. observed vectors ----------
for name, layer in [("unosat_extent", "Multisensor_20260826_20260828_FloodExtent"),
                    ("lakes", "Cartosat3_20260828_BarrierLakes"),
                    ("detachment", "Landsat9_20260826_DetachmentZone")]:
    g = unosat(layer)[["geometry"]]
    open(os.path.join(OUT, f"{name}.geojson"), "w").write(slim(g).to_json(drop_id=True))
ub = unosat("Multisensor_20260826_20260828_AffectedBuildings")[["geometry"]]
open(os.path.join(OUT, "unosat_buildings.geojson"), "w").write(ub.to_json(drop_id=True))
bld = ems("builtUpP")
bld = bld.assign(d=bld.damage_gra.fillna("Unknown"))[["d", "aoi", "geometry"]]
rds = ems("transportationL")
rds = rds[rds.damage_gra.isin(["Destroyed", "Damaged", "Possibly damaged"])].assign(d=lambda g: g.damage_gra)[["d", "geometry"]]
aoi = ems("areaOfInterestA")[["area_id", "locality", "geometry"]]
for name, g in [("observed", slim(obs)), ("buildings", bld), ("roads", slim(rds)), ("aois", aoi)]:
    open(os.path.join(OUT, f"{name}.geojson"), "w").write(g.to_json(drop_id=True, to_wgs84=True))
# Untimed source-to-channel connector: the shortest gap from the mapped detachment zone to the route origin (schematic, not a flow path)
det = unosat("Landsat9_20260826_DetachmentZone").to_crs(32645).union_all()
o = gpd.GeoSeries([Point(float(dlon[0]), float(dlat[0]))], crs=4326).to_crs(32645)[0]
a_pt = gpd.GeoSeries([nearest_points(det, o)[0]], crs=32645).to_crs(4326)[0]
connector = {"coords": [[round(a_pt.x, 5), round(a_pt.y, 5)], [round(float(dlon[0]), 5), round(float(dlat[0]), 5)]], "m": round(det.distance(o))}
print(f"source-to-channel connector {connector['m']} m (untimed)")
ems_counts = {a: bld[bld.aoi == a].d.value_counts().to_dict() for a in sorted(bld.aoi.unique())}

# ---------- 5. meta ----------
meta = {
    "event": {"name": "Trishuli debris flow", "date": "2026-08-26", "t0": "2026-08-26T08:37:00+05:45", "tz": "NPT"},
    "bounds": [W, S, E, N],
    "arrival": {"corners": corners, "maxMin": int(arrival.max()), "cellHa": cell_ha},
    # [lon, lat, chainage m, estimated minute (midpoint fit), DEM channel elevation, earliest minute, latest minute]
    # every 40 m point is kept: coarser sampling cut corners across meanders and looked jagged on 3D terrain
    "river": [[round(float(lo), 5), round(float(la), 5), round(float(c)), round(float(t), 1), round(float(e)), round(float(a), 1), round(float(b), 1)]
              for lo, la, c, t, e, a, b in zip(dlon, dlat, dense_c, arrival, bed, arr_lo, arr_hi)],
    "anchors": [{"name": n, "lon": float(dlon[i]), "lat": float(dlat[i]), "chain": c, "snapM": sm, "lo": a, "hi": b, "min": (a + b) / 2, "type": ty, "basis": BASIS[ty][0], "note": note, "src": s}
                for (n, la, lo, a, b, ty, note, s), c, sm, i in zip(ANCHORS, anc_c, anc_snap, anc_i)],
    "checks": [{"name": n, "chain": c, "min": m, "relation": rel, "estimated": est, "status": st, "note": note, "src": s}
               for n, la, lo, c, m, rel, est, st, note, s, _ in check_rows],
    "connector": connector,
    "origin": origin,
    "untimedHa": round(untimed_ha),
    "areaByMin": [round(float(x), 1) for x in np.cumsum(area_by_min)],
    "emsCounts": ems_counts,
    "unosatBuildings": len(ub),
    "extentHa": round(float(extent.to_crs(32645).area.sum() / 1e4)),
}
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), separators=(",", ":"))
print(f"timed extent {area_by_min.sum():.0f} ha + untimed source zone {untimed_ha:.0f} ha (UNOSAT alone {meta['extentHa']} ha), raster {img.shape[1]}x{img.shape[0]}")
assert abs(area_by_min.sum() + untimed_ha - meta["extentHa"]) / meta["extentHa"] < 0.35, "rasterised extent drifted far from the mapped area"

# ---------- 6. gauge hydrographs, anchor table, input manifest ----------
gts = json.load(open(ZEN, encoding="utf-8"))["stations"]
hydro = []
for key in ["Rasuwagadhi", "Syabrubesi", "Betrawati", "Galchhi", "Kali Khola", "Devghat"]:
    s = gts[key]; a = s.get("arrival") or {}
    base = a.get("local_level_m", a.get("background_m"))
    ser = [[hh, v] for hh, v in s["series_26aug"] if "06:00" <= hh <= "20:00"]
    peak = max(ser, key=lambda r: r[1])
    hydro.append({"name": key, "dhm_station_id": s["station_id"], "series_id": s["series_id"], "lat": s["lat"], "lon": s["lon"],
                  "warning_m": s["warning_m"], "danger_m": s["danger_m"], "base_m": base, "destroyed": not s["reported_through_end_of_day"],
                  "onset": [a.get("after_npt"), a.get("by_npt")], "peak": peak, "series": ser})
json.dump({"source": "DHM river-watch ten-minute stage, archived in Acharya & Paudel (2026), Zenodo 10.5281/zenodo.22679444 v3.0.0, CC BY 4.0",
           "units": "stage, metres, station datum (not comparable between stations)", "stations": hydro},
          open(os.path.join(OUT, "gauges.json"), "w"), separators=(",", ":"))
with open(os.path.join(HERE, "anchors.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["name", "lat", "lon", "chainage_km", "snap_m", "earliest_npt", "latest_npt", "use", "evidence_type", "basis", "bound_reason", "note", "source"])
    hm = lambda x: f"{(8 * 60 + 37 + int(round(x))) // 60:02d}:{(8 * 60 + 37 + int(round(x))) % 60:02d}"
    for (n, la, lo, a, b, ty, note, s), c, sm in zip(ANCHORS, anc_c, anc_snap):
        w.writerow([n, la, lo, round(c / 1000, 2), sm, hm(a), hm(b), "fitted (bracket midpoint)", ty, *BASIS[ty], note, s])
    for n, la, lo, c, m_, rel, est, st, note, s, sm in check_rows:
        w.writerow([n, la, lo, round(c / 1000, 2), sm, "", hm(m_), f"check only: {st}", rel, "check", "Used only to test the interpolation, never fitted", note, s])
manifest = {relp(p): sha(p) for p in inputs()}
requests_used = {"raw/bipad/malekhu_station261_20260826.json": {  # saved by hand; BIPAD serves the current record, which can change
    "url": "https://bipadportal.gov.np/api/v1/river/?format=json&limit=300&station=261&water_level_on__gt=2026-08-26T09:00&water_level_on__lt=2026-08-27",
    "retrieved": "2026-11-09", "readings_copy": "archive/bipad_malekhu_261_20260826.csv"}}
json.dump({"note": "SHA-256 of the downloaded inputs this build used (raw/ is not committed; see sources.csv for URLs)", "files": manifest,
           "requests": requests_used},
          open(os.path.join(HERE, "inputs_manifest.json"), "w"), indent=1)
print("anchors km:", [round(c / 1000, 1) for c in anc_c])
print("EMS:", {k: sum(v.values()) for k, v in ems_counts.items()}, "observed polys", len(obs), "damaged roads", len(rds))
