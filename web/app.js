// Trishuli Flood Trace: static reconstruction of the 26 Aug 2026 debris flow.
const T0 = 8 * 60 + 37; // 08:37 NPT, minutes of day
const $ = (s) => document.querySelector(s);
const fmt = (m) => { const x = Math.round(T0 + m); return `${String(Math.floor(x / 60) % 24).padStart(2, "0")}:${String(x % 60).padStart(2, "0")}`; };
const toMin = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m - T0; };
const n = (x) => Math.round(x).toLocaleString("en-GB");
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

const [meta, ev, gauges] = await Promise.all(["data/meta.json", "data/events.json", "data/gauges.json"].map((u) => fetch(u, { cache: "no-cache" }).then((r) => r.json()))); // revalidate: data must match this app.js
const river = meta.river; // [lon, lat, chain_m, minutes, bedElev]
const T_END = +$("#t").max;
let t = 0;

// ---------- ArcGIS basemap (optional) ----------
// config.js is not committed; locally you paste a key, the deploy workflow writes it from a repository secret.
const cfg = (await import("./config.js").catch(() => ({ default: {} }))).default;
const KEY = cfg.arcgisKey || "";
const esri = KEY ? await fetch(`https://basemapstyles-api.arcgis.com/arcgis/rest/services/styles/v2/styles/arcgis/imagery/labels?token=${encodeURIComponent(KEY)}`)
  .then((r) => r.json()).then((s) => (s.layers ? s : (console.warn("ArcGIS labels unavailable:", s.error?.message), null))).catch(() => null) : null;
const esriIds = esri ? esri.layers.map((l) => l.id) : [];
const FONT = esri?.layers.find((l) => l.layout?.["text-font"])?.layout["text-font"] ?? ["Open Sans Semibold"]; // one glyph server per style

// ---------- map ----------
const RM = matchMedia("(prefers-reduced-motion: reduce)").matches; // no follow camera or animated flights
const glProbe = document.createElement("canvas");
if (!(glProbe.getContext("webgl2") || glProbe.getContext("webgl"))) {
  const repo = "https://github.com/IbaadGEO/trishuli-flood-trace/blob/main";
  $("#map").innerHTML = `<div class="nogl"><b>This 3D map needs WebGL, which isn't available in this browser.</b>
    <p>The reconstruction's method, evidence and sources are readable without it: <a href="${repo}/METHODS.md">METHODS.md</a> ·
    <a href="${repo}/anchors.csv">timing evidence (anchors.csv)</a> · <a href="${repo}/sources.csv">sources.csv</a> · <a href="${repo}/README.md">README</a>.</p></div>`;
  throw new Error("WebGL unavailable: static fallback shown");
}
const map = new maplibregl.Map({
  container: "map",
  center: [85.37, 28.2], zoom: 10.6, pitch: 62, bearing: -20, maxPitch: 80,
  attributionControl: { compact: true }, // full credits line overlapped the story caption on narrower screens
  // imagery and terrain are ~10 m (zoom 14); beyond 15 they only blur, and outside this box there is nothing to see
  maxZoom: 15, minZoom: 8, maxBounds: [[83.6, 27.1], [86.4, 28.95]],
  style: {
    version: 8,
    glyphs: esri?.glyphs ?? "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    ...(esri?.sprite ? { sprite: esri.sprite } : {}),
    sources: {
      sat: KEY
        ? { type: "raster", tileSize: 256, maxzoom: 19, attribution: "Powered by Esri | Esri, Maxar, Earthstar Geographics, and the GIS User Community",
          tiles: [`https://ibasemaps-api.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?token=${encodeURIComponent(KEY)}`] }
        : { type: "raster", tileSize: 256, maxzoom: 14, // free for non-commercial use, no key or account
          attribution: '<a href="https://cloudless.eox.at" target="_blank" rel="noopener">EOxCloudless 2024</a> by EOX IT Services GmbH, CC BY-NC-SA 4.0 (contains modified Copernicus Sentinel data 2024)',
          tiles: ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg"] },
      dem: { type: "raster-dem", encoding: "terrarium", tileSize: 256, maxzoom: 14, attribution: "Terrain: Mapzen Terrarium (AWS Open Data)",
        tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"] },
      demHill: { type: "raster-dem", encoding: "terrarium", tileSize: 256, maxzoom: 14,
        tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"] },
      ...(esri?.sources ?? {}),
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#c9cfc4" } }, // shown only where no imagery
      { id: "sat", type: "raster", source: "sat", paint: { "raster-fade-duration": 150 } },
      { id: "hill", type: "hillshade", source: "demHill", paint: { "hillshade-exaggeration": 0.3, "hillshade-shadow-color": "#000" } },
      ...(esri?.layers ?? []),
    ],
  },
});
const BEFORE = esriIds[0]; // our layers go under Esri's labels
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-left");
map.addControl(new maplibregl.ScaleControl(), "bottom-left");
await new Promise((r) => map.on("load", r));
$(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show"); // compact credits start expanded until the first drag
map.setTerrain({ source: "dem", exaggeration: 1.2 });

// Flood-arrival raster, split into 500 px chunks (only those with flooded pixels). Each repaint re-uploads just
// the chunks whose colours change, i.e. near the front, instead of the whole 3264x2067 canvas.
const img = new Image(); img.src = URL.createObjectURL(await fetch("data/arrival.png", { cache: "no-cache" }).then((r) => r.blob())); await img.decode();
const full = document.createElement("canvas"); full.width = img.width; full.height = img.height;
const fctx = full.getContext("2d", { willReadFrequently: true }); fctx.drawImage(img, 0, 0);
const src = fctx.getImageData(0, 0, full.width, full.height).data;
const cv = { width: full.width, height: full.height };
const mercY = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
const latOfMercY = (y) => (360 / Math.PI) * Math.atan(Math.exp(y)) - 90;
const [cTL, , cBR] = meta.arrival.corners;
const lonAt = (x) => cTL[0] + (cBR[0] - cTL[0]) * (x / cv.width);
const latAt = (y) => latOfMercY(mercY(cTL[1]) + (mercY(cBR[1]) - mercY(cTL[1])) * (y / cv.height));
// CH must not be a power of two: MapLibre samples power-of-two raster textures with mipmaps, which canvas
// sources never generate, so a 512x512 chunk rendered solid black when zoomed out.
const CH = 500, AGE = 25; // AGE: minutes over which fresh water fades to mud colour
const chunks = [];
for (let y0 = 0; y0 < cv.height; y0 += CH) for (let x0 = 0; x0 < cv.width; x0 += CH) {
  const w = Math.min(CH, cv.width - x0), h = Math.min(CH, cv.height - y0), px = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const si = ((y0 + y) * cv.width + x0 + x) * 4; if (src[si + 3]) px.push(si, (y * w + x) * 4); }
  if (!px.length) continue;
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const id = `arrival-${chunks.length}`, ctx = c.getContext("2d");
  const ams = Float32Array.from({ length: px.length / 2 }, (_, k) => (src[px[2 * k]] << 8) | src[px[2 * k] + 1]).sort();
  chunks.push({ id, ctx, px: Int32Array.from(px), ams, out: ctx.createImageData(w, h) });
  map.addSource(id, { type: "canvas", canvas: c, animate: false,
    coordinates: [[lonAt(x0), latAt(y0)], [lonAt(x0 + w), latAt(y0)], [lonAt(x0 + w), latAt(y0 + h)], [lonAt(x0), latAt(y0 + h)]] });
}
const chunkIds = chunks.map((c) => c.id);

const geo = (id, url) => map.addSource(id, { type: "geojson", data: `data/${url}` });
geo("observed", "observed.geojson"); geo("buildings", "buildings.geojson"); geo("roads", "roads.geojson"); geo("aois", "aois.geojson");
geo("unosat_extent", "unosat_extent.geojson"); geo("unosat_buildings", "unosat_buildings.geojson"); geo("lakes", "lakes.geojson"); geo("detachment", "detachment.geojson");
const fc = (rows) => ({ type: "FeatureCollection", features: rows.filter((r) => r.lon).map((r) => ({ type: "Feature", properties: r, geometry: { type: "Point", coordinates: [r.lon, r.lat] } })) });
map.addSource("gauges", { type: "geojson", data: fc(ev.gauges) });
const s2 = await fetch("data/s2.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).catch(() => null); // absent until imagery.py has run
const span = (d) => (d.length > 1 ? `${d[0].slice(5)} → ${d.at(-1).slice(5)}` : d[0]?.slice(5) ?? "");
if (s2) {
  // tiles exist only along the corridor: serve a blank tile for the rest instead of 404ing
  const have = { pre: new Set(s2.pre.tiles), post: new Set(s2.post.tiles) };
  const blank = await new Promise((r) => { const c = document.createElement("canvas"); c.width = c.height = 1; c.toBlob((b) => b.arrayBuffer().then(r)); });
  maplibregl.addProtocol("s2", async (p) => {
    const [, k, key] = p.url.match(/^s2:\/\/(pre|post)\/(.+)$/);
    if (!have[k].has(key)) return { data: blank.slice(0) };
    const res = await fetch(`data/s2/${k}/${key}.webp`);
    return { data: await res.arrayBuffer() };
  });
  for (const k of ["pre", "post"]) map.addSource(`s2${k}`, { type: "raster", tileSize: 256, minzoom: s2.zmin, maxzoom: s2.zmax, bounds: s2.bounds,
    attribution: "Contains modified Copernicus Sentinel data 2026", tiles: [`s2://${k}/{z}/{x}/{y}`] });
}
map.addSource("lake-pts", { type: "geojson", data: fc(ev.lakes) });
map.addSource("river", { type: "geojson", data: { type: "Feature", geometry: { type: "LineString", coordinates: river.map((r) => [r[0], r[1]]) } } });
// The front is a DOM marker: it moves synchronously every frame (a GeoJSON source would round-trip through the worker and lag)
const frontEl = document.createElement("div"); frontEl.className = "front-marker"; frontEl.setAttribute("aria-label", "Flow front");
const frontMarker = new maplibregl.Marker({ element: frontEl }).setLngLat([river[0][0], river[0][1]]).addTo(map);
map.addSource("reached", { type: "geojson", data: line([]) });
// Selected-event callout: a DOM card anchored above the spot (cleaner than a haloed map label)
const evEl = document.createElement("div"); evEl.className = "ev-callout"; evEl.hidden = true;
const evMarker = new maplibregl.Marker({ element: evEl, anchor: "bottom", offset: [0, -12] }).setLngLat([river[0][0], river[0][1]]).addTo(map);
const HOURS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"];
map.addSource("waypoints", { type: "geojson", data: { type: "FeatureCollection", features: HOURS.map((h) => ({ ...pt(at(toMin(h))), properties: { label: h } })) } });
map.addSource("connector", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: meta.connector.coords } } });
map.addSource("anchors", { type: "geojson", data: { type: "FeatureCollection", features: meta.anchors.map((a) => ({ type: "Feature", properties: a, geometry: { type: "Point", coordinates: [a.lon, a.lat] } })) } });

const DMG = ["match", ["get", "d"], "Destroyed", "#c8432b", "Damaged", "#e8873a", "Possibly damaged", "#f1c24b", "#9aa7b0"];
const LAYERS = [
  { group: "Base" },
  { id: "sat", name: "Satellite basemap", note: KEY ? "Esri World Imagery (pre-event)" : "EOxCloudless 2024 Sentinel-2 mosaic", on: true },
  { id: "hill", name: "Hillshade", on: true },
  ...(s2 ? [
    { id: "s2pre", name: "Sentinel-2 before", note: `Cloud-masked composite, ${span(s2.pre.dates)} · ${Math.round(s2.pre.coverage * 100)}% of corridor`, sw: "#5a7d4a", on: true,
      add: { type: "raster", source: "s2pre", paint: { "raster-fade-duration": 0 } } },
    { id: "s2post", name: "Sentinel-2 after", note: `Cloud-masked composite, ${span(s2.post.dates)} · ${Math.round(s2.post.coverage * 100)}% of corridor`, sw: "#9a7b55", on: true,
      add: { type: "raster", source: "s2post", paint: { "raster-opacity": 0, "raster-fade-duration": 0 } } }] : []),
  ...(esri ? [{ id: "esri-labels", name: "Place labels", note: "Esri imagery labels (vector)", on: true }] : []),
  { id: "terrain", name: "Terrain (3D)", note: "Terrarium DEM, 1.2× exaggeration", on: true },
  { group: "Reconstruction" },
  { id: "river", name: "Flow path", note: "OSM rivers, collapse → Devghat; solid = reached", sw: "#36c5f0", on: true,
    add: { type: "line", source: "river", layout: { "line-join": "round" },
      paint: { "line-color": "#bfefff", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.6, 13, 1.2, 16, 2], "line-opacity": 0.6, "line-dasharray": [3, 3] } } },
  { id: "reached", name: "Path reached", est: true, sw: "#36c5f0", on: true,
    add: { type: "line", source: "reached", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": "#36c5f0", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1, 12, 1.8, 15, 3], "line-blur": 0.4 } } },
  { id: "flow-arrows", name: "Flow direction", on: true,
    add: { type: "symbol", source: "river", layout: { "symbol-placement": "line", "symbol-spacing": 90, "text-field": "›", "text-size": 22, "text-font": FONT, "text-keep-upright": false, "text-allow-overlap": true },
      paint: { "text-color": "#bfefff", "text-halo-color": "#06364d", "text-halo-width": 1 } } },
  { id: "waypoints", name: "Hourly front positions", est: true, sw: "#ffd166", on: true,
    add: { type: "circle", source: "waypoints", paint: { "circle-radius": 4.5, "circle-color": "#ffd166", "circle-stroke-width": 2, "circle-stroke-color": "#3a2a00" } } },
  { id: "waypoint-labels", name: "Hourly labels", on: true,
    add: { type: "symbol", source: "waypoints", layout: { "text-field": ["get", "label"], "text-size": 12, "text-offset": [0.9, 0], "text-anchor": "left", "text-font": FONT },
      paint: { "text-color": "#fff4d6", "text-halo-color": "rgba(0,0,0,0.7)", "text-halo-width": 1.3, "text-halo-blur": 0.6 } } },
  { id: "arrival", name: "Mapped extent, revealed over time", est: true, note: "UNOSAT satellite-mapped extent, shown cumulatively by estimated arrival time. Not water depth; colour change is illustrative", sw: "#8a5a2b", on: true,
    add: { type: "raster", paint: { "raster-opacity": 0.9, "raster-resampling": "linear", "raster-fade-duration": 0 } } }, // one layer per chunk source
  { id: "anchors", name: "Observation points", note: "Gauges and reported impact times", sw: "#2f8f5b", on: true,
    add: { type: "circle", source: "anchors", paint: { "circle-radius": 5, "circle-color": "#2f8f5b", "circle-stroke-width": 1.5, "circle-stroke-color": "#fff" } } },
  { id: "anchor-labels", name: "Observation labels", on: true,
    add: { type: "symbol", source: "anchors", layout: { "text-field": ["get", "name"], "text-size": 11, "text-offset": [0, 1.2], "text-anchor": "top", "text-font": FONT },
      paint: { "text-color": "#fff", "text-halo-color": "#000", "text-halo-width": 1.2 } } },
  { group: "Observed · UNOSAT (product 4256)" },
  { id: "unosat_extent", name: "Mapped extent outline", note: "Preliminary satellite interpretation (Sentinel-2 + Planet, 26–28 Aug), not field-validated", sw: "#9fd8f5", on: true,
    add: { type: "line", source: "unosat_extent", paint: { "line-color": "#9fd8f5", "line-width": 1, "line-opacity": 0.8 } } },
  { id: "connector", name: "Source to channel", note: `${meta.connector.m} m gap, not timed`, sw: "#e2483d", on: true,
    add: { type: "line", source: "connector", paint: { "line-color": "#e2483d", "line-width": 2, "line-dasharray": [1, 1.5] } } },
  { id: "detachment", name: "Detachment zone", note: "Landsat-9, 26 Aug", sw: "#e2483d", on: true,
    add: { type: "fill", source: "detachment", paint: { "fill-color": "#e2483d", "fill-opacity": 0.55, "fill-outline-color": "#fff" } } },
  { id: "lakes", name: "Barrier lakes", note: "Cartosat-3, 28 Aug", sw: "#2f6fd6", on: true,
    add: { type: "fill", source: "lakes", paint: { "fill-color": "#2f6fd6", "fill-opacity": 0.75, "fill-outline-color": "#fff" } } },
  { id: "lake-labels", name: "Barrier lake labels", on: true,
    add: { type: "symbol", source: "lake-pts", layout: { "text-field": ["get", "name"], "text-size": 11, "text-offset": [0, 1], "text-anchor": "top", "text-font": FONT },
      paint: { "text-color": "#cfe0ff", "text-halo-color": "#000", "text-halo-width": 1.2 } } },
  { id: "unosat_buildings", name: "Potentially affected buildings", note: "5,048 points in or near mapped impacts; not confirmed damage", sw: "#ff7ab8", on: false,
    add: { type: "circle", source: "unosat_buildings", minzoom: 11, paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 1.5, 16, 5], "circle-color": "#ff7ab8", "circle-stroke-width": 0.5, "circle-stroke-color": "#000" } } },
  { group: "Observed · DHM / CHWRR gauges" },
  { id: "gauges", name: "River gauges", note: "Red = destroyed by the flood", sw: "#2f8f5b", on: true,
    add: { type: "circle", source: "gauges", paint: { "circle-radius": 6, "circle-color": ["match", ["get", "status"], "destroyed", "#c8432b", "#2f8f5b"], "circle-stroke-width": 2, "circle-stroke-color": "#fff" } } },
  { group: "Observed · Copernicus EMS EMSR927" },
  { id: "aois", name: "Mapped areas", note: "Syapru Besi, Timure, Bidur, Phosretar", sw: "#ffffff", on: false,
    add: { type: "line", source: "aois", paint: { "line-color": "#fff", "line-width": 1.2, "line-dasharray": [2, 2] } } },
  { id: "observed", name: "Mapped landslides", note: "Copernicus EMS 'Landslide' features, photo-interpreted; not timed", sw: "#6d3fb3", on: false,
    add: { type: "fill", source: "observed", paint: { "fill-color": "#6d3fb3", "fill-opacity": 0.35, "fill-outline-color": "#b9a2e3" } } },
  { id: "roads", name: "Damaged roads", sw: "#e8873a", on: true,
    add: { type: "line", source: "roads", paint: { "line-color": DMG, "line-width": 2.5 } } },
  { id: "buildings", name: "Building damage", note: "Destroyed · Damaged · Possibly · None visible", sw: "#c8432b", on: true,
    add: { type: "circle", source: "buildings", minzoom: 11, paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 1.5, 16, 5], "circle-color": DMG, "circle-stroke-width": 0.5, "circle-stroke-color": "#000" } } },
];
// Views: each shows only the overlays its question needs. Base layers (imagery, hillshade, terrain, labels) stay as set.
const OVERLAYS = LAYERS.filter((L) => L.add && !L.id.startsWith("s2")).map((L) => L.id);
const VIEWS = {
  story: ["river", "reached", "waypoints", "waypoint-labels", "arrival", "gauges", "detachment", "connector", "lakes"],
  damage: ["reached", "unosat_extent", "buildings", "roads", "gauges", "detachment", "connector", "lakes", "lake-labels"],
  imagery: ["unosat_extent"],
  all: OVERLAYS,
};
for (const L of LAYERS) if (OVERLAYS.includes(L.id)) L.on = VIEWS.story.includes(L.id);
const idsOf = (id) => (id === "arrival" ? chunkIds : id === "esri-labels" ? esriIds : [id]); // panel entries that map to several map layers
for (const L of LAYERS) if (L.add) for (const id of idsOf(L.id))
  map.addLayer({ id, ...L.add, ...(L.id === "arrival" ? { source: id } : {}), layout: { ...(L.add.layout || {}), visibility: L.on ? "visible" : "none" } }, BEFORE);

function setVis(id, on) {
  if (id === "terrain") return map.setTerrain(on ? { source: "dem", exaggeration: 1.2 } : null);
  idsOf(id).forEach((x) => map.setLayoutProperty(x, "visibility", on ? "visible" : "none"));
}
const OPROP = { raster: "raster-opacity", fill: "fill-opacity", line: "line-opacity", circle: "circle-opacity", symbol: "text-opacity" };
const opOf = (L) => L.add && L.id !== "s2post" && OPROP[L.add.type]; // s2post opacity belongs to the before/after blend
$("#layers").innerHTML = LAYERS.map((L) => L.group ? `<div class="layer"><h5>${L.group}</h5></div>` :
  `<label class="layer"><input type="checkbox" data-id="${L.id}" ${L.on ? "checked" : ""}><span>${L.sw ? `<i class="sw" style="background:${L.sw}"></i>` : ""}${L.name}${L.est ? '<span class="est">EST.</span>' : ""}${L.note ? `<small>${L.note}</small>` : ""}${opOf(L) ? `<span class="op"><input type="range" min="0" max="100" value="${Math.round(100 * (map.getPaintProperty(idsOf(L.id)[0], opOf(L)) ?? 1))}" data-op="${L.id}" aria-label="${L.name} opacity"><output>${Math.round(100 * (map.getPaintProperty(idsOf(L.id)[0], opOf(L)) ?? 1))}%</output></span>` : ""}</span></label>`).join("")
  + `<p class="note">This retrospective reconstruction combines satellite-interpreted impacts with reported observations. The moving marker and the extent reveal are interpolated between the midpoints of evidence windows (gauge onsets and telemetry losses from the DHM record, the USGS origin time, a reported time-stamped image); reports such as threshold crossings are used only as checks. They do not represent measured water depth, local flow velocity or a validated hydraulic simulation. Distances start at the OSM route origin, ~0.9 km from the mapped source; the source-to-channel runout (dashed red) is not timed.</p>`;
document.querySelector(".tabs").onclick = (e) => { const k = e.target.dataset.tab; if (!k) return;
  document.querySelectorAll(".tabs button").forEach((b) => { b.classList.toggle("on", b === e.target); b.setAttribute("aria-selected", b === e.target); });
  document.querySelectorAll("#side .tab").forEach((s) => s.classList.toggle("on", s.id === k)); };
$("#layers").addEventListener("change", (e) => e.target.dataset.id && setVis(e.target.dataset.id, e.target.checked));
$("#layers").addEventListener("input", (e) => { const id = e.target.dataset.op; if (!id) return;
  idsOf(id).forEach((x) => map.setPaintProperty(x, opOf(LAYERS.find((L) => L.id === id)), e.target.value / 100)); e.target.nextElementSibling.value = `${e.target.value}%`; });

if (s2) {
  const box = document.createElement("div");
  box.className = "fade";
  box.innerHTML = `<b>Corridor imagery</b><div class="fade-row"><span>Before<small>${span(s2.pre.dates)}</small></span>
    <input type="range" min="0" max="100" value="0" aria-label="Blend before and after Sentinel-2 imagery"><span>After<small>${span(s2.post.dates)}</small></span></div>
    <small class="note">Cloud-masked median composites over the date windows shown, for orientation only. Gaps in "after" show the 2024 basemap, which is pre-event.</small>`;
  document.querySelector("#map").appendChild(box);
  box.querySelector("input").oninput = (e) => { const v = e.target.value / 100;
    map.setPaintProperty("s2post", "raster-opacity", v); map.setPaintProperty("s2pre", "raster-opacity", 1 - v); }; // so post-event gaps never show the "before" composite
}
map.on("click", "buildings", (e) => new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${e.features[0].properties.d}</b><br><span class="muted">Copernicus EMS ${e.features[0].properties.aoi}</span>`).addTo(map));
map.on("click", "gauges", (e) => { const p = e.features[0].properties; new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${p.name} gauge</b><br>${p.reading}${p.danger ? `<br><span class="muted">warning ${p.warn ?? "–"} m · danger ${p.danger} m</span>` : ""}<br><span class="muted">${p.status}</span>`).addTo(map); });
map.on("click", "lakes", (e) => { const l = ev.lakes.reduce((a, b) => Math.hypot(b.lon - e.lngLat.lng, b.lat - e.lngLat.lat) < Math.hypot(a.lon - e.lngLat.lng, a.lat - e.lngLat.lat) ? b : a);
  new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${l.name}</b><br>${l.area}<br><span class="muted">${l.note}</span>`).addTo(map); });
map.on("click", "anchors", (e) => { const p = e.features[0].properties; new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${p.name}</b><br>${p.note}<br><span class="muted">${(p.chain / 1000).toFixed(1)} km downstream</span>`).addTo(map); });
for (const id of ["buildings", "anchors", "gauges", "lakes"]) { map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer")); map.on("mouseleave", id, () => (map.getCanvas().style.cursor = "")); }

// ---------- time model ----------
function at(m) { // interpolate river position for minute m
  let i = river.findIndex((r) => r[3] > m);
  if (i <= 0) return i === 0 ? river[0] : river[river.length - 1];
  const a = river[i - 1], b = river[i], f = (m - a[3]) / (b[3] - a[3] || 1);
  return a.map((v, k) => v + (b[k] - v) * f);
}
function pt(r) { return { type: "Feature", geometry: { type: "Point", coordinates: [r[0], r[1]] } }; }
function line(c) { return { type: "Feature", geometry: { type: "LineString", coordinates: c } }; }
const nearestIdx = (lon, lat) => { let bi = 0, bd = Infinity; const k = Math.cos((lat * Math.PI) / 180);
  for (let i = 0; i < river.length; i++) { const d = ((river[i][0] - lon) * k) ** 2 + (river[i][1] - lat) ** 2; if (d < bd) { bd = d; bi = i; } }
  return [bi, Math.sqrt(bd) * 111320]; };
const fresh = [214, 245, 255], old = [122, 82, 45];
const anyIn = (a, lo, hi) => { let l = 0, h = a.length; while (l < h) { const mid = (l + h) >> 1; if (a[mid] <= lo) l = mid + 1; else h = mid; } return l < a.length && a[l] <= hi; };
let painted = null;
function paintArrival(m) {
  const lo = painted === null ? -Infinity : Math.min(m, painted) - AGE, hi = painted === null ? Infinity : Math.max(m, painted);
  const played = [];
  for (const ch of chunks) {
    if (!anyIn(ch.ams, lo, hi)) continue; // a pixel's colour only changes while it is between arrival and fully aged
    const d = ch.out.data; d.fill(0);
    for (let k = 0; k < ch.px.length; k += 2) {
      const si = ch.px[k], di = ch.px[k + 1], am = (src[si] << 8) | src[si + 1];
      if (src[si + 2] === 1) { d[di] = 176; d[di + 1] = 168; d[di + 2] = 156; d[di + 3] = 150; continue; } // untimed source-zone ground: shown, never animated
      if (am > m) continue;
      const age = Math.min(1, (m - am) / AGE);
      d[di] = fresh[0] + (old[0] - fresh[0]) * age; d[di + 1] = fresh[1] + (old[1] - fresh[1]) * age; d[di + 2] = fresh[2] + (old[2] - fresh[2]) * age;
      d[di + 3] = 90 + 0.65 * src[si + 2];
    }
    ch.ctx.putImageData(ch.out, 0, 0);
    const s = map.getSource(ch.id); s.play(); played.push(s);
  }
  painted = m;
  if (played.length) requestAnimationFrame(() => requestAnimationFrame(() => played.forEach((s) => s.pause())));
}
const events = ev.events.map((e) => ({ ...e, m: toMin(e.t) }));

let follow = !RM, cam = null; // cam: eased camera state {c:[lon,lat], b:bearing, ts}
function atChain(c) { // river point `c` metres from the source
  let i = river.findIndex((r) => r[2] > c);
  if (i <= 0) return i === 0 ? river[0] : river.at(-1);
  const a = river[i - 1], b = river[i], f = (c - a[2]) / (b[2] - a[2] || 1);
  return a.map((v, k) => v + (b[k] - v) * f);
}
function bearingAt(m) { // heading from the front to a point 1.5 km further down the river
  const a = at(m), b = atChain(a[2] + 1500), k = Math.cos((a[1] * Math.PI) / 180);
  return (Math.atan2((b[0] - a[0]) * k, b[1] - a[1]) * 180) / Math.PI;
}
// Lower pitch over the first 20 km: in the deep source gorge a steep camera dipped behind the valley walls
const camPitch = (r, steep = 58) => (!map.getTerrain() ? 0 : r[2] < 20000 ? 40 : steep);
function followCam(r) {
  const now = performance.now();
  if (!cam) cam = { c: map.getCenter().toArray(), b: map.getBearing(), ts: now };
  const dt = Math.min(0.1, (now - cam.ts) / 1000); cam.ts = now;
  const kc = 1 - Math.exp(-dt / 0.45), kb = 1 - Math.exp(-dt / 1.2); // frame-rate independent easing (time constants in s)
  cam.c = [cam.c[0] + (r[0] - cam.c[0]) * kc, cam.c[1] + (r[1] - cam.c[1]) * kc];
  cam.b += ((((bearingAt(t) - cam.b) % 360) + 540) % 360 - 180) * kb;
  map.jumpTo({ center: cam.c, bearing: cam.b, pitch: camPitch(r) });
}
function frontCard(r) {
  const km = r[2] / 1000, done = t >= river.at(-1)[3];
  const v = done ? 0 : ((at(t + 1)[2] - r[2]) / 60) * 3.6; // km/h over the next minute
  const win = (a) => (a.lo === a.hi ? fmt(a.lo) : `${fmt(a.lo)}–${fmt(a.hi)}`);
  const prev = meta.anchors.filter((a) => a.lo <= t).at(-1), next = meta.anchors.find((a) => a.lo > t); // only evidence already in the past is shown as passed
  $("#front-card").innerHTML = `<h4>Estimated progression <span>${fmt(t)} NPT <span class="est">EST.</span></span></h4><div class="stats">
    <div><b>${km.toFixed(1)} km</b><span>along route</span></div><div><b>${done ? "–" : Math.round(v)}</b><span>km/h implied average rate</span></div><div><b>${n(r[4])} m</b><span>DEM channel elevation</span></div></div>
    <p class="note" style="margin:6px 0 0">Envelope at this point: ${fmt(r[5])}–${fmt(r[6])}</p>
    <dl style="margin-top:6px"><dt>Last evidence</dt><dd>${prev ? `${prev.name}: ${prev.type}, ${win(prev)}` : "none yet"}</dd>
    <dt>Next evidence</dt><dd>${next ? `${next.name} (${next.type}, ${win(next)})` : "none: end of route"}</dd></dl>`;
}

// During playback the camera, front marker and clock update every frame; the costly redraws
// (flood raster upload, charts, panel, reached path) run at most every HEAVY_MS.
const HEAVY_MS = 90;
let lastHeavy = 0;
function setTime(m, fly) {
  t = Math.max(0, Math.min(T_END, m));
  $("#t").value = t;
  const r = at(t);
  frontMarker.setLngLat([r[0], r[1]]);
  if (playing && follow) followCam(r);
  $("#clock").textContent = `${fmt(t)} NPT`;
  const now = performance.now();
  if (playing && now - lastHeavy < HEAVY_MS && !fly) return;
  lastHeavy = now;
  const upto = river.filter((x) => x[3] <= t).map((x) => [x[0], x[1]]);
  map.getSource("reached").setData(line(upto.length > 1 ? [...upto, [r[0], r[1]]] : []));
  document.querySelectorAll("#ticks i").forEach((i) => i.classList.toggle("past", +i.dataset.m <= t));
  frontCard(r);
  paintArrival(t);
  const reached = t >= river[river.length - 1][3];
  const rate = minPerSec(t, +$("#speed").value), rateTxt = rate < 1 ? `${Math.round(rate * 60)} s` : `${rate.toFixed(rate < 3 ? 1 : 0)} min`;
  $("#clock-sub").textContent = (t === 0 ? "collapse" : reached ? `front past Devghat · +${Math.floor(t / 60)}h ${Math.round(t % 60)}m` : `front at ${(r[2] / 1000).toFixed(0)} km (est.) · +${Math.floor(t / 60)}h ${Math.round(t % 60)}m`)
    + (playing ? ` · playback 1 s = ${rateTxt}` : "");
  story(t);
  document.querySelectorAll("#ev li").forEach((li) => { const em = +li.dataset.m; li.classList.toggle("future", em > t); li.classList.toggle("now", em <= t && em > t - 15); });
  drawCharts(r);
  $("#area").textContent = n(meta.areaByMin[Math.min(Math.floor(t), meta.areaByMin.length - 1)]);
  if (fly) map.flyTo({ center: [r[0], r[1]], zoom: 11.8, pitch: camPitch(r, 45), bearing: bearingAt(t), duration: RM ? 0 : 1500 }); // camera looks downstream; lower pitch keeps the valley floor in view
}
// ---------- plain-English story caption + legend ----------
const storyBox = document.createElement("div"); storyBox.className = "story"; storyBox.setAttribute("aria-live", "polite"); $("#map").appendChild(storyBox);
let storyKey = "";
function story(m) {
  const s = ev.story.filter((x) => x.m <= m).at(-1), e = events.filter((x) => x.m <= m && x.m > m - 12).at(-1); // event "just happened" for 12 min
  const key = `${s?.m}|${e?.m}`; if (key === storyKey) return; storyKey = key;
  storyBox.innerHTML = (e ? `<div class="just"><i class="k-${e.kind}"></i>${e.t} · ${e.title}</div>` : "") + `<b>${s.title}</b><p>${s.text}</p>`;
}
const legend = document.createElement("details"); legend.className = "legend"; legend.open = true;
legend.innerHTML = `<summary>Legend</summary>
  <div data-for="always"><i class="lg-dot" style="background:#36c5f0"></i>Estimated progression along the mapped route</div>
  <div data-for="arrival"><i class="lg-box fill" style="background:#b0a89c"></i>Mapped source-zone ground (untimed)</div>
  <div data-for="arrival"><i class="lg-grad"></i>Reached (est.): just now → earlier</div>
  <div data-for="reached"><i class="lg-line"></i>River already reached</div>
  <div data-for="river"><i class="lg-line dash"></i>River not reached yet</div>
  <div data-for="waypoints"><i class="lg-dot" style="background:#ffd166"></i>Front position each hour</div>
  <div data-for="unosat_extent"><i class="lg-box" style="border-color:#9fd8f5"></i>Mapped extent (satellite, preliminary)</div>
  <div data-for="buildings"><i class="lg-dot" style="background:#c8432b"></i>Destroyed · <i class="lg-dot" style="background:#e8873a;margin-left:4px"></i>damaged · <i class="lg-dot" style="background:#f1c24b;margin-left:4px"></i>possibly</div>
  <div data-for="roads"><i class="lg-line" style="border-color:#e8873a"></i>Damaged road</div>
  <div data-for="gauges"><i class="lg-dot" style="background:#c8432b"></i>Gauge destroyed · <i class="lg-dot" style="background:#2f8f5b;margin-left:4px"></i>survived</div>
  <div data-for="connector"><i class="lg-line dash" style="border-color:#e2483d"></i>Source to channel (shortest gap, not timed)</div>
  <div data-for="detachment lakes"><i class="lg-box fill" style="background:#e2483d"></i>Collapse source · <i class="lg-box fill" style="background:#2f6fd6;margin-left:4px"></i>barrier lake</div>`;
$("#map").appendChild(legend);
const visible = (id) => id === "always" || ((x) => map.getLayer(x) && map.getLayoutProperty(x, "visibility") !== "none")(idsOf(id)[0]);
const syncLegend = () => legend.querySelectorAll("[data-for]").forEach((d) => (d.hidden = !d.dataset.for.split(" ").some(visible)));
function applyView(v) {
  for (const id of OVERLAYS) { const on = VIEWS[v].includes(id); setVis(id, on); const cb = $(`#layers input[data-id="${id}"]`); if (cb) cb.checked = on; }
  document.querySelectorAll("#views button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  const fade = $(".fade"); if (fade) fade.hidden = !(v === "imagery" || v === "all");
  syncLegend();
}
$("#views").onclick = (e) => e.target.dataset.view && applyView(e.target.dataset.view);
$("#layers").addEventListener("change", syncLegend);
applyView("story");

function pinEvent(e) { // pinned where it happened; non-spatial events (alerts, forecasts) get no map pin
  evEl.hidden = !e.at;
  if (!e.at) return;
  evEl.dataset.kind = e.kind ?? "alert";
  evEl.innerHTML = `<time>${e.t ?? e.d}</time><span>${e.title}</span>`;
  evMarker.setLngLat(e.at);
}

// ---------- timeline ----------
const KCOL = { origin: css("--mud"), impact: css("--impact"), gauge: css("--gauge"), alert: css("--alert") };
$("#ticks").innerHTML = events.map((e, k) => `<i class="tk-${e.kind}" title="${e.t} ${e.title}" data-k="${k}" data-m="${e.m}" style="left:${(e.m / T_END) * 100}%;background:${KCOL[e.kind]}"></i>`).join("");
$("#ticks").onclick = (e) => { const k = e.target.dataset.k; if (k === undefined) return; toggle(false); pinEvent(events[k]); setTime(events[k].m, true); };
$("#t").oninput = (e) => setTime(+e.target.value);
// Distance-paced playback: at 1× the front moves ~0.75 km of river per second, so the 180 km/h gorge
// plays slowly and the slow lower river speeds up; after Devghat the clock runs at 10 min/s.
const KM_PER_S = 0.75;
function minPerSec(m, speed) {
  const v = (at(m + 1)[2] - at(m)[2]) / 1000; // km per minute at the front
  return (v > 0.01 ? Math.min(10, KM_PER_S / v) : 10) * speed;
}
let playing = false, last, holdUntil = 0;
function loop(ts) {
  if (!playing) return;
  if (last && ts >= holdUntil) {
    const sp = +$("#speed").value, next = t + ((ts - last) / 1000) * minPerSec(t, sp);
    const hit = events.find((e) => e.m > t && e.m <= next);
    if (hit) { lastHeavy = 0; setTime(hit.m); pinEvent(hit); holdUntil = ts + 3500 / Math.sqrt(sp); } // pause on each key event, fully redrawn
    else setTime(next);
  }
  last = ts;
  if (t >= T_END) return toggle(false);
  requestAnimationFrame(loop);
}
function toggle(on) {
  playing = on; last = null; cam = null;
  $("#play").textContent = on ? "⏸" : "▶"; $("#play").setAttribute("aria-label", on ? "Pause" : "Play");
  if (!on) return setTime(t); // full redraw at the paused moment
  if (t >= T_END) setTime(0);
  if (follow) { const r = at(t); map.easeTo({ center: [r[0], r[1]], zoom: Math.max(map.getZoom(), 12.2), pitch: camPitch(r), bearing: bearingAt(t), duration: 900 }); }
  setTimeout(() => playing && requestAnimationFrame(loop), follow ? 950 : 0);
}
$("#play").onclick = () => toggle(!playing);
$("#restart").onclick = () => { toggle(false); evEl.hidden = true; setTime(0, true); };
// Step through key events one at a time (also ← / → when not typing in a field)
const stepEvent = (dir) => {
  const e = dir > 0 ? events.find((x) => x.m > t + 0.01) : events.findLast((x) => x.m < t - 0.01);
  toggle(false); if (e) { pinEvent(e); setTime(e.m, true); }
};
$("#prev").onclick = () => stepEvent(-1); $("#next").onclick = () => stepEvent(1);
document.addEventListener("keydown", (e) => {
  if (e.target.closest("input, select, textarea, [role=button], li") || e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); stepEvent(e.key === "ArrowRight" ? 1 : -1); }
});
const setFollow = (on) => { follow = on; cam = null; $("#follow").classList.toggle("on", on); $("#follow").setAttribute("aria-pressed", on); };
$("#follow").onclick = () => setFollow(!follow);
setFollow(follow); // reflect the reduced-motion default in the button
map.on("dragstart", (e) => e.originalEvent && follow && playing && setFollow(false)); // user took the camera
$("#dim").onclick = (e) => { const v = e.target.dataset.v; if (!v) return; $("#dim").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === e.target)); map.easeTo({ pitch: v === "3" ? 62 : 0, bearing: v === "3" ? -20 : 0 }); setVis("terrain", v === "3"); };

// ---------- key events ----------
$("#ev").innerHTML = events.map((e) => `<li data-m="${e.m}" tabindex="0" role="button"><i class="k-${e.kind}" aria-hidden="true"></i><span>${e.title}${e.detail ? `<small>${e.detail}</small>` : ""}</span><time>${e.t}</time></li>`).join("")
  + ev.after.map((e) => `<li data-m="${T_END}" tabindex="0" role="button"><i class="k-alert" aria-hidden="true"></i><span>${e.title}${e.detail ? `<small>${e.detail}</small>` : ""}</span><time>${e.d}</time></li>`).join("");
$("#ev").onkeydown = (e) => { if ((e.key === "Enter" || e.key === " ") && e.target.matches("li")) { e.preventDefault(); e.target.click(); } };
$("#ev").onclick = (e) => { const li = e.target.closest("li"); if (!li) return;
  toggle(false); const k = [...$("#ev").children].indexOf(li);
  if (k < events.length) pinEvent(events[k]);
  setTime(Math.min(+li.dataset.m, T_END), true); };

// ---------- charts (plain SVG) ----------
function chart(svg, { xs, ys, xmax, ymax, fill, dots = [], bars = [], lines = [], marks = [], cursor, xfmt, yfmt }) {
  const W = svg.clientWidth || 300, H = svg.clientHeight || 120, L = 34, B = 16;
  const X = (x) => L + (x / xmax) * (W - L - 6), Y = (y) => H - B - (y / ymax) * (H - B - 6);
  const line = xs.map((x, i) => `${i ? "L" : "M"}${X(x).toFixed(1)},${Y(ys[i]).toFixed(1)}`).join("");
  const ticksY = [0, ymax / 2, ymax].map((v) => `<text x="${L - 4}" y="${Y(v) + 3}" text-anchor="end">${yfmt(v)}</text><line x1="${L}" x2="${W - 6}" y1="${Y(v)}" y2="${Y(v)}" stroke="${css("--line")}"/>`).join("");
  const ticksX = [0, xmax / 2, xmax].map((v) => `<text x="${X(v)}" y="${H - 3}" text-anchor="middle">${xfmt(v)}</text>`).join("");
  const cx = cursor ? X(cursor[0]) : W, clip = `cp-${svg.id}`; // solid up to the playhead, dashed and faded after it
  const area = fill ? `<path d="${line}L${X(xs.at(-1))},${Y(0)}L${X(xs[0])},${Y(0)}Z" fill="${fill}"` : "";
  svg.innerHTML = `<defs><clipPath id="${clip}"><rect x="0" y="0" width="${cx}" height="${H}"/></clipPath></defs>` + ticksY + ticksX
    + (fill ? `${area} opacity=".08"/>${area} opacity=".3" clip-path="url(#${clip})"/>` : "")
    + `<path d="${line}" fill="none" stroke="${css("--water")}" stroke-width="1.3" stroke-dasharray="4 3" opacity=".45"/>`
    + `<path d="${line}" fill="none" stroke="${css("--water")}" stroke-width="1.8" clip-path="url(#${clip})"/>`
    + lines.map((l) => `<path d="${l.xs.map((x, i) => `${i ? "L" : "M"}${X(x).toFixed(1)},${Y(l.ys[i]).toFixed(1)}`).join("")}" fill="none" stroke="${css("--water")}" stroke-width="1" opacity=".35"/>`).join("")
    + bars.map(([x1, x2, y]) => `<line x1="${X(x1)}" x2="${Math.max(X(x2), X(x1) + 3)}" y1="${Y(y)}" y2="${Y(y)}" stroke="${css("--gauge")}" stroke-width="5" stroke-linecap="round"/>`).join("")
    + marks.map(([x, y]) => `<path d="M${X(x) - 4},${Y(y) - 4}L${X(x)},${Y(y) + 3}L${X(x) + 4},${Y(y) - 4}Z" fill="none" stroke="${css("--alert")}" stroke-width="1.5"/>`).join("")
    + dots.map(([x, y]) => `<circle cx="${X(x)}" cy="${Y(y)}" r="3" fill="${css("--gauge")}"/>`).join("")
    + (cursor ? `<line x1="${X(cursor[0])}" x2="${X(cursor[0])}" y1="6" y2="${H - B}" stroke="${css("--ink")}" stroke-dasharray="3 2"/><circle cx="${X(cursor[0])}" cy="${Y(cursor[1])}" r="4" fill="${css("--front")}" stroke="#fff"/>` : "");
}
const step = Math.ceil(river.length / 200), rs = river.filter((_, i) => i % step === 0);
const kmMax = river.at(-1)[2] / 1000, elevMax = Math.ceil(Math.max(...river.map((r) => r[4])) / 500) * 500;
const tf = (m) => fmt(m), kf = (v) => `${Math.round(v)} km`;
function drawCharts(r) {
  const km = r[2] / 1000;
  chart($("#c-front"), { xs: rs.map((x) => x[3]), ys: rs.map((x) => x[2] / 1000), xmax: T_END, ymax: Math.ceil(kmMax / 50) * 50,
    lines: [5, 6].map((k) => ({ xs: rs.map((x) => x[k]), ys: rs.map((x) => x[2] / 1000) })), // earliest / latest scenario
    bars: meta.anchors.map((a) => [a.lo, a.hi, a.chain / 1000]), marks: meta.checks.map((c) => [c.min, c.chain / 1000]),
    cursor: [t, km], xfmt: tf, yfmt: kf });
  chart($("#c-profile"), { xs: rs.map((x) => x[2] / 1000), ys: rs.map((x) => x[4]), xmax: kmMax, ymax: elevMax, fill: css("--mud"),
    dots: meta.anchors.map((a) => [a.chain / 1000, at(a.min)[4]]), cursor: [km, r[4]], xfmt: kf, yfmt: (v) => `${(v / 1000).toFixed(1)}k m` });
  hydrograph($("#c-area"));
}
// Observed stage at each gauge, as rise above its own pre-event level (station datums are not comparable)
const HCOL = { Rasuwagadhi: "#c8432b", Syabrubesi: "#e8873a", Betrawati: "#b07a10", Galchhi: "#2f8f5b", "Kali Khola": "#1c7fb8", Devghat: "#6d3fb3" };
const minOf = (hh) => toMin(hh);
function hydrograph(svg) {
  const W = svg.clientWidth || 300, H = svg.clientHeight || 120, L = 30, B = 16, top = 10;
  const X0 = minOf("06:00"), X1 = minOf("20:00"), X = (m) => L + ((m - X0) / (X1 - X0)) * (W - L - 6);
  const Y = (y) => H - B - ((y + 1) / (top + 1)) * (H - B - 6);
  const grid = [0, 5, 10].map((v) => `<text x="${L - 4}" y="${Y(v) + 3}" text-anchor="end">${v} m</text><line x1="${L}" x2="${W - 6}" y1="${Y(v)}" y2="${Y(v)}" stroke="${css("--line")}"/>`).join("")
    + ["06:00", "12:00", "18:00"].map((h) => `<text x="${X(minOf(h))}" y="${H - 3}" text-anchor="middle">${h}</text>`).join("");
  const series = gauges.stations.map((s) => {
    const pts = s.series.map(([hh, v]) => [minOf(hh), v - s.base_m]);
    const d = pts.map(([m, y], i) => `${i ? "L" : "M"}${X(m).toFixed(1)},${Y(Math.min(y, top)).toFixed(1)}`).join("");
    const end = pts.at(-1), lost = s.destroyed ? `<text x="${X(end[0]) + 2}" y="${Y(end[1]) - 3}" fill="${HCOL[s.name]}" font-size="11">✕</text>` : "";
    return `<path d="${d}" fill="none" stroke="${HCOL[s.name]}" stroke-width="1.4"><title>${s.name}</title></path>${lost}`;
  }).join("");
  const colW = (W - L - 10) / 3;
  const key = gauges.stations.map((s, i) => `<text x="${L + 4 + (i % 3) * colW}" y="${12 + Math.floor(i / 3) * 12}" fill="${HCOL[s.name]}" font-size="9.5" stroke="${css("--panel")}" stroke-width="3" paint-order="stroke">${s.name}${s.destroyed ? " ✕" : ""}</text>`).join("");
  svg.innerHTML = grid + series + key + `<line x1="${X(t)}" x2="${X(t)}" y1="6" y2="${H - B}" stroke="${css("--ink")}" stroke-dasharray="3 2"/>`;
}
addEventListener("resize", () => drawCharts(at(t)));

// ---------- overview panel ----------
const src_ = (k) => `<a href="${ev.sources[k].url}" target="_blank" rel="noopener">${ev.sources[k].label}</a>`;
const ems = Object.values(meta.emsCounts).reduce((acc, o) => { for (const [k, v] of Object.entries(o)) acc[k] = (acc[k] || 0) + v; return acc; }, {});
const D = ev.deathsByDistrict, bmax = Math.max(...D.rows.map((r) => r[1]));
$("#overview").innerHTML = `
<div class="card front" id="front-card"></div>
<div class="card"><h4>Incident overview <span>Reconstruction</span></h4><dl>
  <dt>Event</dt><dd>Rock-ice avalanche → debris flow → flood</dd>
  <dt>Date</dt><dd>26 Aug 2026, 08:37 NPT</dd>
  <dt>Origin</dt><dd>Lirung massif, Langtang NP (~5,200 m)</dd>
  <dt>Path</dt><dd>Lende Khola → Bhote Koshi → Trishuli → Narayani, ${kmMax.toFixed(0)} km to Devghat</dd>
  <dt>Districts</dt><dd>Rasuwa, Nuwakot, Dhading, Gorkha, Chitwan (+ Gyirong County, Tibet)</dd>
  <dt>Timing</dt><dd>Rising-wave onset at the Devghat gauge 14:30–14:40, about 6 h after the collapse; stage peaked 6.57 m at 16:00 (DHM record)</dd></dl>
  <p class="note">Independent reconstruction for education and understanding. Not an official product and not for emergency use. The moving front and the extent reveal are estimates between reported observations, not measured depth, velocity or a hydraulic simulation.</p></div>
<div class="card"><h4>Human impact <span>${ev.totals.asOf}</span></h4><div class="stats">
  <div><b>${ev.totals.deaths}</b><span>deaths reported</span></div><div><b>${ev.totals.missing}</b><span>still missing</span></div><div><b>${ev.totals.houses}</b><span>private buildings affected (RDNA est.)</span></div>
  <div><b>${ev.totals.bridges}</b><span>motorable bridges + 68 trail-bridge spans (RDNA)</span></div><div><b>${ev.totals.roadKm} km</b><span>road damaged (reported)</span></div><div><b id="area">0</b><span>ha of mapped area revealed <span class="est">EST. TIMING</span></span></div>
  <div><b>${ev.totals.effects}</b><span>damage and losses (RDNA, Sep)</span></div><div><b>${ev.totals.needs}</b><span>recovery needs (RDNA, Sep)</span></div><div><b>${n(meta.extentHa)}</b><span>ha mapped extent (UNOSAT, preliminary)</span></div></div>
  <p class="note">Aggregate figures only. Sources: ${src_("article")}; ${src_("rdna")}; The Guardian, 7 Nov 2026.</p></div>
<div class="card"><h4>Source collapse <span>ranges across studies</span></h4><dl>
  ${ev.source.rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
  <p class="note">${ev.source.precursor} ${ev.source.rain}</p>
  <p class="note">${ev.source.conflicts} ${src_("usgs")}; ${src_("jms")}; ${src_("jisrs")}; ${src_("icimod")}; ${src_("imerg")}; ${src_("wwa")}; ${src_("xu")}.</p></div>
<div class="card"><h4>River gauges <span>26 Aug, DHM ten-minute record</span></h4><dl>
  ${ev.gauges.map((g) => `<dt>${g.name}</dt><dd>${g.reading}${g.status === "destroyed" ? ' <span class="est" style="color:var(--impact)">LOST</span>' : ""}</dd>`).join("")}</dl>
  <p class="note">Stages are relative to each station's own datum, not water depth, and are not comparable between stations. Gauges that stopped transmitting only bracket arrival, assuming the flood caused the loss. Source: <a href="https://doi.org/10.5281/zenodo.22679444" target="_blank" rel="noopener">DHM record archived on Zenodo (Acharya &amp; Paudel 2026, CC BY 4.0)</a>; Phurke values from ${src_("chwrr")}.</p></div>
<div class="card"><h4>Building damage <span>Copernicus EMS, 4 areas</span></h4><div class="bars">
  ${["Destroyed", "Damaged", "Possibly damaged"].map((k) => `<div><span>${k}</span><i style="width:${(100 * (ems[k] || 0)) / Math.max(...Object.values(ems))}%;background:${{ Destroyed: "#c8432b", Damaged: "#e8873a", "Possibly damaged": "#f1c24b" }[k] || "#9aa7b0"}"></i><em>${n(ems[k] || 0)}</em></div>`).join("")}
  </div><p class="note">Graded building points within the four EMS mapped areas only, not a corridor-wide count. ${src_("ems")}. UNOSAT separately flags ${n(meta.unosatBuildings)} buildings in or near mapped impacts (exposure, not confirmed damage; ${src_("unosat")}).</p></div>
<div class="card"><h4>Deaths by reporting district <span>${D.asOf}</span></h4><div class="bars">
  ${D.rows.map(([d, v]) => `<div><span>${d}</span><i style="width:${(100 * v) / bmax}%"></i><em>${v}</em></div>`).join("")}
  </div><p class="note">Districts where deaths were reported, largely reflecting recovery location rather than where people were lost. Rows total ${n(D.rows.reduce((s, r) => s + r[1], 0))} of 1,451; the remainder died during treatment in Kathmandu. Figures are provisional. ${src_("ndrrma")}.</p></div>
<div class="card"><h4>Method & sources</h4><p class="note">
  Mapped extent: ${src_("unosat")} (preliminary satellite interpretation, not field-validated). Landslides and building grading: ${src_("ems")}. Timing: DHM gauge brackets (<a href="https://doi.org/10.5281/zenodo.22679444" target="_blank" rel="noopener">Zenodo 22679444</a>; Malekhu from the <a href="https://bipadportal.gov.np/" target="_blank" rel="noopener">BIPAD</a> river record), USGS origin time and reported time-stamped images at Gyirong; ${src_("chwrr")} and ${src_("timeline")} for reports. River path: © OpenStreetMap contributors (ODbL). Terrain: Mapzen Terrarium (AWS Open Data).
  Both are uncertain: the extent is a satellite interpretation, and the timing is interpolated between bracket midpoints of mixed evidence, with an earliest/latest scenario envelope. Full method: <a href="https://github.com/IbaadGEO/trishuli-flood-trace/blob/main/METHODS.md" target="_blank" rel="noopener">METHODS.md</a>.</p></div>`;
// keep the panel short: front, overview and impact stay open; the detail cards fold away
[...$("#overview").children].slice(3).forEach((card) => {
  const d = document.createElement("details"), s = document.createElement("summary"), h = card.querySelector("h4");
  d.className = "card fold"; s.append(...h.childNodes); h.remove(); d.append(s, ...card.childNodes); card.replaceWith(d);
});

// ---------- terrain hover tooltip ----------
const tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; $("#map").appendChild(tip);
function extentMinute(ll) { // arrival minute of the mapped-extent pixel under the cursor, or null
  const fx = (ll.lng - cTL[0]) / (cBR[0] - cTL[0]), fy = (mercY(cTL[1]) - mercY(ll.lat)) / (mercY(cTL[1]) - mercY(cBR[1]));
  if (fx < 0 || fx >= 1 || fy < 0 || fy >= 1) return null;
  const i = (Math.floor(fy * cv.height) * cv.width + Math.floor(fx * cv.width)) * 4;
  return src[i + 3] ? (src[i] << 8) | src[i + 1] : null;
}
let tipQ = null;
map.on("mousemove", (e) => { tipQ = e; requestAnimationFrame(() => { if (tipQ !== e) return;
  const [i, d] = nearestIdx(e.lngLat.lng, e.lngLat.lat);
  if (d > 4000) { tip.hidden = true; return; }
  const r = river[i], z = map.getTerrain() ? map.queryTerrainElevation(e.lngLat) : null;
  // queryTerrainElevation is relative to the screen-centre elevation and includes exaggeration
  const elev = z == null ? null : (z + map.transform.elevation) / map.getTerrain().exaggeration, am = extentMinute(e.lngLat);
  tip.innerHTML = (elev == null ? "" : `<b>${n(elev)} m</b> · ${n(Math.max(0, elev - r[4]))} m above DEM channel<br>`)
    + `${(r[2] / 1000).toFixed(1)} km downstream · ${(d / 1000).toFixed(1)} km from channel<br>`
    + (am == null ? `<span class="muted">Outside the mapped flood extent</span>` : `<span class="hit">● Flooded</span> · est. reached <b>${fmt(am)}</b>${am > t ? " (not yet)" : ""}`)
    + `<br><span class="muted">${e.lngLat.lat.toFixed(4)}°N ${e.lngLat.lng.toFixed(4)}°E</span>`;
  tip.style.left = `${e.point.x + 14}px`; tip.style.top = `${e.point.y + 14}px`; tip.hidden = false; }); });
map.getCanvas().addEventListener("mouseleave", () => (tip.hidden = true));

setTime(0);
