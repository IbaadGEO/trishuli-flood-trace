"""Cloud-masked Sentinel-2 before/after composites, cut into XYZ WebP tiles along the flood corridor.

Before/after = per-pixel median of clear observations (SCL mask + blue-brightness filter) from the scenes nearest the event,
built from the rendered TCI visual assets: for orientation, not a reflectance change-analysis product.
Reads Sentinel-2 L2A COGs straight from AWS (Element84 Earth Search), no login.
Run after build.py:  python -P imagery.py
"""
import json, math, os, threading
from concurrent.futures import ThreadPoolExecutor
os.environ.update(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_CACHEMAX="2048",
                  VSI_CACHE="TRUE", GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_HTTP_MAX_RETRY="4")
import numpy as np, requests, rasterio, geopandas as gpd, shapely
from rasterio import features
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "web", "data")
ZMAX, ZMIN = 14, 9
BAD_SCL = {0, 1, 3, 8, 9, 10}  # no data, saturated, cloud shadow, cloud (med/high), cirrus
EVENT = "2026-08-26"
R = 6378137.0

# corridor = observed extent + river path, buffered ~1.5 km
meta = json.load(open(os.path.join(DATA, "meta.json")))
river = shapely.LineString([(r[0], r[1]) for r in meta["river"]])
ext = gpd.read_file(os.path.join(DATA, "unosat_extent.geojson")).union_all()
corridor = gpd.GeoSeries([shapely.union(ext, river)], crs=4326).to_crs(3857).buffer(1500).union_all()

items = requests.post("https://earth-search.aws.element84.com/v1/search", timeout=60, json={
    "collections": ["sentinel-2-l2a"], "bbox": list(gpd.GeoSeries([corridor], crs=3857).to_crs(4326).total_bounds),
    "datetime": "2026-07-25T00:00:00Z/2026-09-30T23:59:59Z", "limit": 200}).json()["features"]
scenes = [{"id": f["id"], "date": f["properties"]["datetime"][:10], "visual": f["assets"]["visual"]["href"], "scl": f["assets"]["scl"]["href"],
           "bbox": gpd.GeoSeries([shapely.box(*f["bbox"])], crs=4326).to_crs(3857).iloc[0]} for f in items]
pre = sorted([s for s in scenes if s["date"] < EVENT], key=lambda s: s["date"], reverse=True)
post = sorted([s for s in scenes if s["date"] > EVENT], key=lambda s: s["date"])
print(f"{len(pre)} pre scenes, {len(post)} post scenes")


def tile_bounds(z, x, y):
    s = 2 * math.pi * R / 2 ** z
    return (-math.pi * R + x * s, math.pi * R - (y + 1) * s, -math.pi * R + (x + 1) * s, math.pi * R - y * s)


minx, miny, maxx, maxy = corridor.bounds
s14 = 2 * math.pi * R / 2 ** ZMAX
tiles = [(x, y) for x in range(int((minx + math.pi * R) // s14), int((maxx + math.pi * R) // s14) + 1)
         for y in range(int((math.pi * R - maxy) // s14), int((math.pi * R - miny) // s14) + 1)
         if corridor.intersects(shapely.box(*tile_bounds(ZMAX, x, y)))]
print(f"{len(tiles)} z{ZMAX} tiles")

local = threading.local()


def warp(href, b, resampling):  # warp one COG onto this tile's 256x256 Web Mercator grid (0 outside the scene)
    cache = local.__dict__.setdefault("c", {})  # one open dataset per thread per COG
    if href not in cache:
        cache[href] = rasterio.open(href)
    ds = cache[href]
    with WarpedVRT(ds, crs="EPSG:3857", transform=from_bounds(*b, 256, 256), width=256, height=256, resampling=resampling, nodata=0) as v:
        return v.read()


K = 16  # scenes per tile, nearest to the event first
BRIGHT = 150  # TCI blue above this is almost always cloud/haze in this corridor; only used as a fallback (snow, ice)


def composite(x, y, order):
    """Per-pixel median of the clear observations in the K scenes nearest the event: removes monsoon haze and
    stray cloud the SCL mask misses, while persistent changes (the debris scar) survive."""
    b = tile_bounds(ZMAX, x, y); box = shapely.box(*b)
    want = features.rasterize([corridor], out_shape=(256, 256), transform=from_bounds(*b, 256, 256)).astype(bool)
    strict, loose, used = [], [], set()
    for s in [s for s in order if s["bbox"].intersects(box)][:K]:
        try:
            px = warp(s["visual"], b, Resampling.bilinear)[:3].astype(np.float32)
            c = warp(s["scl"], b, Resampling.nearest)[0]
        except (rasterio.errors.RasterioIOError, rasterio.errors.WarpOperationError) as e:
            print("skip", s["id"], e); continue
        ok = want & ~np.isin(c, list(BAD_SCL)) & (px.max(0) > 0)
        if not ok.any(): continue
        used.add((s["date"], s["id"]))
        lo = px.copy(); lo[:, ~ok] = np.nan; loose.append(lo)
        st = px.copy(); st[:, ~(ok & (px[2] < BRIGHT) & (c != 7))] = np.nan; strict.append(st)  # 7 = unclassified (often haze)
    if not loose:
        return np.zeros((256, 256, 3), np.uint8), np.zeros((256, 256), bool), want, used
    with np.errstate(all="ignore"):
        med = np.nanmedian(np.stack(strict), axis=0)  # (3, 256, 256)
        gap = np.isnan(med[0])
        if gap.any(): med[:, gap] = np.nanmedian(np.stack(loose), axis=0)[:, gap]
    done = ~np.isnan(med[0])
    return np.moveaxis(np.nan_to_num(med), 0, -1).astype(np.uint8), done, want, used


def save(arr, alpha, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.dstack([arr, alpha.astype(np.uint8) * 255]), "RGBA").save(path, "WEBP", quality=72, method=5)


def run(name, order):
    out = os.path.join(DATA, "s2", name)
    stats = {"want": 0, "done": 0, "used": set()}

    def one(t):
        rgb, done, want, used = composite(*t, order)
        if done.any(): save(rgb, done, os.path.join(out, str(ZMAX), str(t[0]), f"{t[1]}.webp"))
        return want.sum(), done.sum(), used

    with ThreadPoolExecutor(8) as ex:
        for i, (w, d, u) in enumerate(ex.map(one, tiles)):
            stats["want"] += w; stats["done"] += d; stats["used"] |= u
            if i % 50 == 0: print(f"  {name} {i}/{len(tiles)}")
    # lower zooms: 2x2 downsample from the level above
    for z in range(ZMAX - 1, ZMIN - 1, -1):
        parents = {(x // 2, y // 2) for x, y in ((int(d), int(f[:-5])) for d in os.listdir(os.path.join(out, str(z + 1))) for f in os.listdir(os.path.join(out, str(z + 1), d)))}
        for px, py in parents:
            canvas = Image.new("RGBA", (512, 512))
            for dx in (0, 1):
                for dy in (0, 1):
                    p = os.path.join(out, str(z + 1), str(px * 2 + dx), f"{py * 2 + dy}.webp")
                    if os.path.exists(p): canvas.paste(Image.open(p), (dx * 256, dy * 256))
            os.makedirs(os.path.join(out, str(z), str(px)), exist_ok=True)
            canvas.resize((256, 256), Image.LANCZOS).save(os.path.join(out, str(z), str(px), f"{py}.webp"), "WEBP", quality=72, method=5)
    cov = stats["done"] / stats["want"]
    dates = sorted({d for d, _ in stats["used"]})
    print(f"{name}: coverage {cov:.1%}, dates {dates}")
    index = sorted(f"{z}/{x}/{f[:-5]}" for z in os.listdir(out) for x in os.listdir(os.path.join(out, z)) for f in os.listdir(os.path.join(out, z, x)))
    return {"coverage": round(cov, 3), "dates": dates, "scenes": sorted(i for _, i in stats["used"]), "tiles": index}  # index lets the app skip requests outside the corridor


result = {"pre": run("pre", pre), "post": run("post", post), "zmin": ZMIN, "zmax": ZMAX,
          "params": {"stac": "earth-search v1 sentinel-2-l2a, visual (TCI) + scl assets", "scenesPerTile": K, "blueMax": BRIGHT, "maskedSCL": sorted(BAD_SCL)},
          "bounds": list(gpd.GeoSeries([corridor], crs=3857).to_crs(4326).total_bounds.round(4))}
json.dump(result, open(os.path.join(DATA, "s2.json"), "w"))
ok = result["pre"]["coverage"] > 0.5 and result["post"]["coverage"] > 0.5
if not ok: print("composites mostly empty: check cloud mask / scene search")
os._exit(0 if ok else 1)  # hard exit: open /vsicurl handles in worker threads can hang interpreter shutdown
