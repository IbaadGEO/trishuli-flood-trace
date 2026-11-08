"""Build static data for the Trishuli flood viewer.

Inputs (cached under raw/): OSM rivers (Overpass), Terrarium DEM tiles (AWS open data),
Copernicus EMS EMSR927 grading vectors (raw/ems/), UNOSAT product 4256 geodatabase (raw/unosat/).
Outputs under web/data/. Run: python -P build.py
"""
import glob, heapq, io, json, math, os
import numpy as np, requests, geopandas as gpd, pandas as pd
from PIL import Image
from rasterio import features
from rasterio.transform import from_origin
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = os.path.join(HERE, "raw"), os.path.join(HERE, "web", "data")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "trishuli-flood-viewer/0.1 (research visualisation)"}

S, W, N, E = 27.68, 84.38, 28.36, 85.62  # corridor bbox
Z = 12  # DEM zoom (~34 m px at this latitude)
ZX = 12  # extent raster zoom (~34 m px); z13 exceeds the 4096 px texture limit on many phones
UNOSAT = glob.glob(os.path.join(RAW, "unosat", "**", "*.gdb"), recursive=True)[0]
unosat = lambda layer: gpd.read_file(UNOSAT, layer=f"UNOSAT_{layer}").set_crs(4326, allow_override=True)

# Anchors: observed times (NPT, minutes after 08:37 collapse) from the CHWRR / DHM technical report
# as summarised in Wikipedia "Timeline of the 2026 Nepal–Tibet floods". Coordinates approximate, snapped to river.
ANCHORS = [
    ("Collapse (Lirung massif)", 28.289, 85.521, 0, "08:37:10 seismic signal (USGS us7000tbwb, M5.2 landslide)"),  # UNOSAT detachment-zone centroid
    ("Gyirong Port / Rasuwagadhi", 28.276, 85.378, 7, "08:44 CCTV captures destruction"),
    ("Syabrubesi gauge", 28.161, 85.344, 13, "08:50 station stops transmitting (assumed hit)"),
    ("Betrawati gauge", 27.969, 85.187, 43, "09:20 station stops transmitting"),
    ("Malekhu / Phurke", 27.820, 84.834, 169, "11:26 above danger level; swept away 11:43"),
    ("Mugling", 27.853, 84.560, 263, "13:00 flood confirmed past Mugling (upper bound)"),
    ("Devghat", 27.743, 84.432, 403, "15:20 flood reaches Narayani confluence; peak 16:00"),
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
print("collapse snapped", round(hav(*ANCHORS[0][1:3], *src)), "m from anchor")
path = dijkstra(src, dst)
chain = np.concatenate([[0], np.cumsum([hav(*a, *b) for a, b in zip(path, path[1:])])])
# densify to ~40 m spacing for DEM sampling and arrival lookup
dense_c = np.arange(0, chain[-1], 40.0)
P = np.array(path)
dlat, dlon = np.interp(dense_c, chain, P[:, 0]), np.interp(dense_c, chain, P[:, 1])
print(f"river path {chain[-1] / 1000:.1f} km, {len(path)} vertices")

ptree = cKDTree(np.c_[dlat, dlon])
anc_c = [float(dense_c[ptree.query([la, lo])[1]]) for _, la, lo, *_ in ANCHORS]
anc_t = [a[3] for a in ANCHORS]
assert all(np.diff(anc_c) > 0), f"anchors out of order along river: {anc_c}"
arrival = np.interp(dense_c, anc_c, anc_t)  # minutes after 08:37, piecewise linear between observations

# ---------- 2. DEM mosaic (Terrarium, Web Mercator) ----------
def tx(lon): return (lon + 180) / 360 * 2 ** Z
def ty(lat): return (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2 ** Z

x0, x1, y0, y1 = int(tx(W)), int(tx(E)), int(ty(N)), int(ty(S))
dem = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        b = get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png", os.path.join(RAW, "dem", f"{Z}_{x}_{y}.png"))
        a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float32)
        dem[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
cols = np.array([(tx(lo) - x0) * 256 for lo in dlon]).astype(int)
rows = np.array([(ty(la) - y0) * 256 for la in dlat]).astype(int)
bed = ndimage.minimum_filter(dem, size=3)[rows, cols]
bed = np.minimum.accumulate(bed)  # river bed never rises downstream

# ---------- 3. observed extent (UNOSAT + Copernicus EMS) timed by interpolated arrival ----------
def slim(g):  # ~3 m simplification + 1e-5° grid keeps polygon files small for the browser
    import shapely
    return g.set_geometry(shapely.set_precision(g.geometry.simplify(0.00003).values, 1e-5))


def ems(kind):
    fs = sorted(glob.glob(os.path.join(RAW, "ems", "**", f"*_{kind}_v*.shp"), recursive=True))
    g = pd.concat([gpd.read_file(f).assign(aoi=os.path.basename(f).split("_")[1]) for f in fs], ignore_index=True)
    return gpd.GeoDataFrame(g[g.geometry.notna()], crs=4326)

obs = ems("observedEventA")[["obj_desc", "aoi", "geometry"]]
extent = unosat("Multisensor_20260826_20260828_FloodExtent")[["geometry"]]
R = 6378137.0
res = 2 * math.pi * R / 2 ** ZX / 256  # metres per px at the equator (Web Mercator units)
gx0, gx1, gy0, gy1 = int(tx(W) / 2 ** Z * 2 ** ZX), int(tx(E) / 2 ** Z * 2 ** ZX) + 1, int(ty(N) / 2 ** Z * 2 ** ZX), int(ty(S) / 2 ** Z * 2 ** ZX) + 1
mx0, my0 = gx0 * 256 * res - math.pi * R, math.pi * R - gy0 * 256 * res
shape = ((gy1 - gy0) * 256, (gx1 - gx0) * 256)
geoms = pd.concat([extent.geometry, obs.geometry]).to_crs(3857)
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
m = np.round(arrival[idx]).astype(np.uint16)
img[r_ - ra, c_ - ca, 0], img[r_ - ra, c_ - ca, 1] = m >> 8, m & 255
img[r_ - ra, c_ - ca, 2] = (255 * np.clip(1 - dist / 800, 0.35, 1)).astype(np.uint8)  # opacity: stronger near channel
img[r_ - ra, c_ - ca, 3] = 255
Image.fromarray(img, "RGBA").save(os.path.join(OUT, "arrival.png"), optimize=True)
lonx = lambda c: math.degrees((mx0 + c * res) / R)
latx = lambda r: math.degrees(2 * math.atan(math.exp((my0 - r * res) / R)) - math.pi / 2)
corners = [[lonx(ca), latx(ra)], [lonx(cb), latx(ra)], [lonx(cb), latx(rb)], [lonx(ca), latx(rb)]]
cell_ha = (res * math.cos(lat0)) ** 2 / 1e4
area_by_min = np.bincount(m, minlength=int(arrival.max()) + 1) * cell_ha

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
ems_counts = {a: bld[bld.aoi == a].d.value_counts().to_dict() for a in sorted(bld.aoi.unique())}

# ---------- 5. meta ----------
step = 1  # full 40 m path: coarser sampling cut corners across meanders and looked jagged on 3D terrain
meta = {
    "event": {"name": "Trishuli debris flow", "date": "2026-08-26", "t0": "2026-08-26T08:37:00+05:45", "tz": "NPT"},
    "bounds": [W, S, E, N],
    "arrival": {"corners": corners, "maxMin": int(arrival.max()), "cellHa": cell_ha},
    "river": [[round(float(lo), 5), round(float(la), 5), round(float(c)), round(float(t), 1), round(float(e))]
              for lo, la, c, t, e in zip(dlon[::step], dlat[::step], dense_c[::step], arrival[::step], bed[::step])],
    "anchors": [{"name": n, "lon": float(dlon[ptree.query([la, lo])[1]]), "lat": float(dlat[ptree.query([la, lo])[1]]),
                 "chain": c, "min": t, "note": note} for (n, la, lo, t, note), c in zip(ANCHORS, anc_c)],
    "areaByMin": [round(float(x), 1) for x in np.cumsum(area_by_min)],
    "emsCounts": ems_counts,
    "unosatBuildings": len(ub),
    "extentHa": round(float(extent.to_crs(32645).area.sum() / 1e4)),
}
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), separators=(",", ":"))
print(f"timed extent {area_by_min.sum():.0f} ha (UNOSAT alone {meta['extentHa']} ha), raster {img.shape[1]}x{img.shape[0]}")
assert abs(area_by_min.sum() - meta["extentHa"]) / meta["extentHa"] < 0.35, "timed extent drifted far from the observed area"
print("anchors km:", [round(c / 1000, 1) for c in anc_c])
print("EMS:", {k: sum(v.values()) for k, v in ems_counts.items()}, "observed polys", len(obs), "damaged roads", len(rds))
