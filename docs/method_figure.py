"""Draw docs/media/method.svg, the README method figure, from web/data/meta.json.

Run from the repo root after build.py:  python -P docs/method_figure.py
"""
import json
import textwrap
from html import escape

m = json.load(open("web/data/meta.json", encoding="utf-8"))
anchors, checks, river = m["anchors"], m["checks"], m["river"][::25]  # river rows: lon, lat, chain m, min, elev, lo, hi
KM = anchors[-1]["chain"] / 1000
INK, MUTED, LINE, BG, WATER = "#1c262c", "#5a656b", "#dcd9d2", "#faf9f6", "#1c7fb8"
BASIS = {"observed": "#2f8f5b", "reported": "#b07a10", "inferred": "#7a5ea8", "assumed": "#8a8f93"}
n_obs = {b: sum(a["basis"] == b for a in anchors) for b in BASIS}

STAGES = [
    ("Raw observations", "USGS seismic signal, Gyirong Port camera, DHM ten-minute gauge records, UNOSAT and Copernicus EMS satellite mapping, OSM river network, GLO-30 DEM."),
    ("Evidence anchors", f"{len(anchors)} time windows placed on a {KM:.0f} km river route, each classed as observed, reported, inferred or assumed. {len(checks)} further reports are kept back as checks and never fitted."),
    ("Temporal interpolation", "Window midpoints are interpolated piecewise-linearly against route distance, giving an arrival minute at every 40 m route point."),
    ("Uncertainty", "Interpolating the earliest and latest bounds in the same way gives a scenario envelope. It is not a statistical confidence interval."),
    ("3D visualisation", "Each pixel (about 34 m) of the satellite-mapped extent takes the minute of its nearest route point and is revealed at that time on 3D terrain."),
]

W, H = 1000, 664
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13" fill="{INK}">',
     f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>',
     f'<defs><marker id="a" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>']

# stage cards, top to bottom
CX, CW, CH, GAP = 20, 318, 112, 16
for i, (title, body) in enumerate(STAGES):
    y = 20 + i * (CH + GAP)
    o.append(f'<rect x="{CX}" y="{y}" width="{CW}" height="{CH}" rx="8" fill="#fff" stroke="{LINE}"/>')
    o.append(f'<circle cx="{CX + 24}" cy="{y + 24}" r="12" fill="{INK}"/><text x="{CX + 24}" y="{y + 29}" text-anchor="middle" fill="#fff" font-weight="700">{i + 1}</text>')
    o.append(f'<text x="{CX + 46}" y="{y + 29}" font-size="15" font-weight="700">{title}</text>')
    for j, ln in enumerate(textwrap.wrap(body, 50)):
        o.append(f'<text x="{CX + 14}" y="{y + 54 + j * 17}" fill="{MUTED}">{escape(ln)}</text>')
    if i < len(STAGES) - 1:
        o.append(f'<line x1="{CX + CW / 2}" y1="{y + CH + 2}" x2="{CX + CW / 2}" y2="{y + CH + GAP - 4}" stroke="{MUTED}" stroke-width="1.5" marker-end="url(#a)"/>')

# distance-time plot of the real anchors, interpolation and envelope
X0, X1, Y0, Y1 = 420, 975, 600, 44
TMAX = 390  # minutes after 08:37, to 15:07
X = lambda t: X0 + t / TMAX * (X1 - X0)
Y = lambda km: Y0 - km / 210 * (Y0 - Y1)
o.append(f'<text x="{X0}" y="28" font-size="15" font-weight="700">Stages 2 to 4, drawn from the project\'s data</text>')
for km in range(0, 201, 50):
    o.append(f'<line x1="{X0}" x2="{X1}" y1="{Y(km):.1f}" y2="{Y(km):.1f}" stroke="{LINE}"/><text x="{X0 - 8}" y="{Y(km) + 4:.1f}" text-anchor="end" fill="{MUTED}">{km}</text>')
for hh in range(9, 16):
    t = hh * 60 - (8 * 60 + 37)
    o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{Y0}" y2="{Y0 + 5}" stroke="{MUTED}"/><text x="{X(t):.1f}" y="{Y0 + 20}" text-anchor="middle" fill="{MUTED}">{hh:02d}:00</text>')
o.append(f'<text x="{(X0 + X1) / 2}" y="{Y0 + 44}" text-anchor="middle" fill="{MUTED}">Time on 26 August 2026 (NPT)</text>')
o.append(f'<text transform="translate({X0 - 44},{(Y0 + Y1) / 2}) rotate(-90)" text-anchor="middle" fill="{MUTED}">Distance along the river route (km)</text>')
pts = lambda k: " ".join(f"{X(r[k]):.1f},{Y(r[2] / 1000):.1f}" for r in river)
env = " ".join(f"{X(r[5]):.1f},{Y(r[2] / 1000):.1f}" for r in river) + " " + " ".join(f"{X(r[6]):.1f},{Y(r[2] / 1000):.1f}" for r in reversed(river))
o.append(f'<polygon points="{env}" fill="{WATER}" opacity=".22"/><polyline points="{pts(3)}" fill="none" stroke="{WATER}" stroke-width="2"/>')
for a in anchors:
    y, x0, x1 = Y(a["chain"] / 1000), X(a["lo"]), X(a["hi"])
    o.append(f'<rect x="{x0:.1f}" y="{y - 4:.1f}" width="{max(x1 - x0, 3):.1f}" height="8" rx="2" fill="{BASIS[a["basis"]]}"/>')
    if a is anchors[-1]:  # no room to the right of the last anchor
        o.append(f'<text x="{x0 - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="12">{escape(a["name"])}</text>')
    else:  # the first label sits above the axis ticks
        o.append(f'<text x="{x1 + 8:.1f}" y="{y + (-5 if a is anchors[0] else 14):.1f}" font-size="12">{escape(a["name"])}</text>')
for c in checks:
    x, y, bad = X(c["min"]), Y(c["chain"] / 1000), c["status"] != "consistent"
    o.append(f'<path d="M{x - 6:.1f},{y - 12:.1f} h12 l-6,10 z" fill="{"#c8432b" if bad else "#fff"}" stroke="#c8432b" stroke-width="1.5"/>')
    if bad:
        o.append(f'<text x="{x - 10:.1f}" y="{y - 8:.1f}" text-anchor="end" font-size="12">{escape(c["name"])} report: conflict</text>')

# legend in the empty upper-left of the plot
lx, ly = X0 + 14, Y1 + 12
o.append(f'<text x="{lx}" y="{ly + 4}" font-weight="700">2  Evidence window, by basis</text>')
for i, (b, col) in enumerate(BASIS.items()):
    o.append(f'<rect x="{lx}" y="{ly + 14 + i * 19}" width="22" height="8" rx="2" fill="{col}"/><text x="{lx + 30}" y="{ly + 23 + i * 19}">{b} ({n_obs[b]})</text>')
y = ly + 14 + 4 * 19 + 14
o.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{y}" y2="{y}" stroke="{WATER}" stroke-width="2"/><text x="{lx + 30}" y="{y + 4}"><tspan font-weight="700">3</tspan>  Interpolated arrival</text>')
o.append(f'<rect x="{lx}" y="{y + 14}" width="22" height="10" fill="{WATER}" opacity=".22"/><text x="{lx + 30}" y="{y + 24}"><tspan font-weight="700">4</tspan>  Earliest to latest envelope</text>')
o.append(f'<path d="M{lx + 5},{y + 36} h12 l-6,10 z" fill="#fff" stroke="#c8432b" stroke-width="1.5"/><text x="{lx + 30}" y="{y + 46}">Report used only as a check</text>')
o.append("</svg>")
open("docs/media/method.svg", "w", encoding="utf-8", newline="\n").write("\n".join(o) + "\n")
print("wrote docs/media/method.svg:", len(anchors), "anchors,", len(checks), "checks,", f"{KM:.1f} km")
