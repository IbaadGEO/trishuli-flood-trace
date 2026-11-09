"""Before/after image pairs for key sites -> web/data/sites/*.webp and web/data/sites.json.

Reads openly licensed scenes over HTTP (no login) and warps a fixed square window around each site onto a
UTM 45N grid, so the before and after images align pixel for pixel:
  - Vantor Open Data Program, event "Nepal-Flooding-Aug-2026" (CC BY-NC 4.0)
  - Planet Crisis Response Program on Source Cooperative (CC BY-NC 4.0)
  - EOxCloudless 2025 (CC BY-NC-SA 4.0), only where no pre-event high-resolution scene covers the site
"Before" scenes are from after the July 2025 Purepu flood wherever one exists, so the pair isolates 2026 change.
Each image gets a 1-99 percentile contrast stretch for display (stated in the app). Run: python -P sites.py
"""
import io, json, os, sys, urllib.request
import numpy as np, rasterio
from rasterio.io import MemoryFile
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from pyproj import Transformer
from PIL import Image

os.environ.update(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "web", "data", "sites")
PX = 1200
V = "https://vantor-opendata.s3.amazonaws.com/events/Nepal-Flooding-Aug-2026/"
P = "https://data.source.coop/planet/disasterdata/nepal-flash-flood-2026-08-26/"
VANTOR = "© Vantor, Open Data Program (CC BY-NC 4.0)"
PLANET = "© Planet Labs PBC, Crisis Response Program (CC BY-NC 4.0)"
EOX = "EOxCloudless 2025 by EOX IT Services GmbH, CC BY-NC-SA 4.0 (contains modified Copernicus Sentinel data 2025)"

# Scene = (url, date, sensor and resolution, credit, scene id)
def vantor(i, date, sensor): return (V + i + ".tif", date, sensor, VANTOR, i)
def planet(path, date, sensor): return (P + path + "_visual.tif", date, sensor, PLANET, path.rsplit("/", 1)[1])
PS_MAY = "pre-event/planetscope-2026-05-27/items/"

# (id, name, lon, lat, window size in m, before scene, after scene)
SITES = [
    ("source", "Collapse source, Langtang Lirung", 85.520, 28.291, 3200,
     ("eox", "2025 mosaic", "EOxCloudless (Sentinel-2), 10 m", EOX, "s2cloudless-2025"),
     planet("post-event/pelican-2026-09-29/items/20260929_051336_88_300c/20260929_051336_88_300c", "2026-09-29", "Pelican, 0.6 m")),
    ("timure", "Rasuwagadhi and Timure", 85.374, 28.268, 2400,
     planet(PS_MAY + "20260527_053219_95_254a/20260527_053219_95_254a", "2026-05-27", "PlanetScope, 3.7 m"),
     planet("post-event/pelican-2026-09-01/items/20260901_050632_98_300b/20260901_050632_98_300b", "2026-09-01", "Pelican, 0.6 m")),
    ("syabrubesi", "Syabrubesi", 85.3394, 28.1683, 2000,
     planet(PS_MAY + "20260527_053221_96_254a/20260527_053221_96_254a", "2026-05-27", "PlanetScope, 3.7 m"),
     vantor("B1300011011E5610", "2026-09-07", "WorldView Legion, 0.35 m")),
    ("betrawati", "Betrawati", 85.18, 27.97, 2000,
     planet(PS_MAY + "20260527_053226_41_254a/20260527_053226_41_254a", "2026-05-27", "PlanetScope, 3.7 m"),
     vantor("B160001101DA4B10", "2026-09-07", "WorldView Legion, 0.39 m")),
    ("bidur", "Bidur and Trishuli Bazaar", 85.1466, 27.9182, 2000,
     vantor("B160001100CDB210", "2026-02-05", "WorldView Legion, 0.35 m"),
     vantor("B030001100EF5510", "2026-09-08", "WorldView-2, 0.48 m")),
]

to_utm = Transformer.from_crs(4326, 32645, always_xy=True)


def eox(tf):
    """EOxCloudless 2025 z14 tiles mosaicked in Web Mercator, then warped to the target grid."""
    z, R = 14, 20037508.342789244
    inv = Transformer.from_crs(32645, 3857, always_xy=True)
    x0, y1 = inv.transform(tf.c, tf.f); x1, y0 = inv.transform(tf.c + tf.a * PX, tf.f + tf.e * PX)
    ts = 2 * R / 2 ** z
    tx0, tx1, ty0, ty1 = int((x0 + R) // ts), int((x1 + R) // ts), int((R - y1) // ts), int((R - y0) // ts)
    mos = np.zeros((3, (ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256), np.uint8)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            b = urllib.request.urlopen(f"https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/GoogleMapsCompatible/{z}/{ty}/{tx}.jpg", timeout=60).read()
            mos[:, (ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = np.asarray(Image.open(io.BytesIO(b)).convert("RGB")).transpose(2, 0, 1)
    with MemoryFile() as mf, mf.open(driver="GTiff", width=mos.shape[2], height=mos.shape[1], count=3, dtype="uint8", crs=3857,
                                     transform=from_origin(tx0 * ts - R, R - ty0 * ts, ts / 256, ts / 256)) as d:
        d.write(mos)
        with WarpedVRT(d, crs=32645, transform=tf, width=PX, height=PX, resampling=Resampling.bilinear) as v:
            return v.read([1, 2, 3])


def read(scene, tf):
    if scene[0] == "eox": return eox(tf)
    with rasterio.open("/vsicurl/" + scene[0]) as s, WarpedVRT(s, crs=32645, transform=tf, width=PX, height=PX, resampling=Resampling.bilinear) as v:
        return v.read([1, 2, 3])


def stretch(a):
    valid = a.sum(0) > 0
    assert valid.mean() > 0.95, "scene does not fully cover the site window"
    lo, hi = np.percentile(a[:, valid], [1, 99])
    return (np.clip((a.astype(np.float32) - lo) / max(hi - lo, 1), 0, 1) * 255).astype(np.uint8)


meta = json.load(open(os.path.join(HERE, "web", "data", "meta.json"), encoding="utf-8"))
river = np.array([r[:4] for r in meta["river"]])
os.makedirs(OUT, exist_ok=True)
rows = []
for sid, name, lon, lat, size, pre, post in SITES:
    x, y = to_utm.transform(lon, lat)
    tf = from_origin(x - size / 2, y + size / 2, size / PX, size / PX)
    pair = {}
    for phase, scene in (("pre", pre), ("post", post)):
        Image.fromarray(stretch(read(scene, tf)).transpose(1, 2, 0)).save(os.path.join(OUT, f"{sid}_{phase}.webp"), quality=82)
        pair[phase] = {"img": f"data/sites/{sid}_{phase}.webp", "date": scene[1], "sensor": scene[2], "credit": scene[3], "scene": scene[4]}
    k = int(np.argmin((river[:, 0] - lon) ** 2 + (river[:, 1] - lat) ** 2))  # nearest route point gives the minute to open the panel
    rows.append({"id": sid, "name": name, "lon": lon, "lat": lat, "km": round(size / 1000, 1), "m": round(float(river[k, 3])), **pair})
    print(sid, "ok", rows[-1]["m"], "min")
with open(os.path.join(HERE, "web", "data", "sites.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
sys.stdout.flush()
os._exit(0)  # GDAL can hang on interpreter shutdown
