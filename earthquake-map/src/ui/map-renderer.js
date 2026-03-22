import { magnitudeToRadius, magnitudeToColor } from '../domain/magnitude-scale.js';
import { buildPopupContent } from './popup-builder.js';

const MAP_CENTER = [20.0, 0.0];
const MAP_INITIAL_ZOOM = 2;
const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

let map_instance = null;
let marker_layer = null;

/**
 * Initialize the Leaflet map.
 * @param {string} container_id - DOM element ID for the map container.
 * @returns {Object} The Leaflet map instance.
 */
export function initializeMap(container_id) {
  /* global L */
  map_instance = L.map(container_id).setView(MAP_CENTER, MAP_INITIAL_ZOOM);
  L.tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION }).addTo(map_instance);
  marker_layer = L.layerGroup().addTo(map_instance);
  return map_instance;
}

/**
 * Clear all earthquake markers from the map.
 */
export function clearMarkers() {
  if (marker_layer) {
    marker_layer.clearLayers();
  }
}

/**
 * Render earthquake events as circle markers on the map.
 * @param {Object[]} earthquake_events - Array of EarthquakeEvent objects.
 */
export function renderMarkers(earthquake_events) {
  clearMarkers();
  for (const event of earthquake_events) {
    const radius = magnitudeToRadius(event.magnitude);
    const color = magnitudeToColor(event.magnitude);
    const circle = L.circleMarker([event.latitude, event.longitude], {
      radius,
      fillColor: color,
      color: '#333',
      weight: 1,
      opacity: 0.8,
      fillOpacity: 0.6,
    });
    circle.bindPopup(buildPopupContent(event));
    marker_layer.addLayer(circle);
  }
}
