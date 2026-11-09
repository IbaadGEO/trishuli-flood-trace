// Copy to config.js (git-ignored) to add an optional ArcGIS API key for local use; the public site ships this file with no key.
// Use a key with only the basemap privilege, restricted by HTTP referrer to your site and localhost.
// Without a key the app still works: Sentinel-2 imagery along the corridor, hillshade elsewhere, no Esri labels.
export default { arcgisKey: "" };
