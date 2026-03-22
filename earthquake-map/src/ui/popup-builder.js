/**
 * Escape a string for safe insertion into HTML.
 * Prevents XSS by escaping all HTML-significant characters.
 * @param {string} raw_text - Untrusted text from API response.
 * @returns {string} HTML-safe string.
 */
export function escapeHTML(raw_text) {
  const div = document.createElement('div');
  div.textContent = String(raw_text);
  return div.innerHTML;
}

/**
 * Build popup HTML content for an earthquake event.
 * All values are sanitized before DOM insertion.
 * @param {Object} earthquake_event - An EarthquakeEvent object.
 * @returns {string} HTML string for Leaflet popup.
 */
export function buildPopupContent(earthquake_event) {
  const magnitude_text = escapeHTML(earthquake_event.magnitude?.toFixed(1) ?? 'N/A');
  const location_text = escapeHTML(earthquake_event.location_name);
  const depth_text = escapeHTML(earthquake_event.depth_km?.toFixed(1) ?? 'N/A');
  const time_text = escapeHTML(earthquake_event.event_time_utc?.toISOString() ?? 'N/A');
  const detail_url = escapeHTML(earthquake_event.usgs_detail_url ?? '');

  return `
    <div class="earthquake-popup">
      <strong>M ${magnitude_text}</strong><br>
      <span>${location_text}</span><br>
      <span>Depth: ${depth_text} km</span><br>
      <span>Time: ${time_text}</span><br>
      <a href="${detail_url}" target="_blank" rel="noopener noreferrer">USGS Detail</a>
    </div>
  `;
}
