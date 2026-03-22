/**
 * Factory function to create an EarthquakeEvent from a USGS GeoJSON feature.
 * @param {Object} feature - A single feature from the USGS GeoJSON response.
 * @returns {Object} EarthquakeEvent with normalized fields.
 */
export function createEarthquakeEvent(feature) {
  const { properties, geometry, id } = feature;
  return {
    earthquake_id: id,
    magnitude: properties.mag,
    location_name: properties.place || 'Unknown location',
    depth_km: geometry.coordinates[2],
    event_time_utc: new Date(properties.time),
    latitude: geometry.coordinates[1],
    longitude: geometry.coordinates[0],
    usgs_detail_url: properties.url,
  };
}

/**
 * Parse a full USGS GeoJSON response into an array of EarthquakeEvents.
 * @param {Object} geojson - The full USGS GeoJSON response object.
 * @returns {{ events: Object[], metadata_count: number }}
 */
export function parseGeoJSON(geojson) {
  if (!geojson || !Array.isArray(geojson.features)) {
    throw new Error('Invalid GeoJSON: missing features array');
  }
  const events = geojson.features.map(createEarthquakeEvent);
  const metadata_count = geojson.metadata?.count ?? events.length;
  return { events, metadata_count };
}
