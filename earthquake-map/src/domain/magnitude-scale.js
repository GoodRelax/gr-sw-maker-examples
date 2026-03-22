/**
 * Convert earthquake magnitude to a circle marker radius in pixels.
 * Uses a stepped scale for visual clarity.
 * @param {number} magnitude - Earthquake magnitude value.
 * @returns {number} Radius in pixels.
 */
export function magnitudeToRadius(magnitude) {
  if (magnitude < 3.0) return 4;
  if (magnitude < 5.0) return 7;
  if (magnitude < 7.0) return 11;
  return 16;
}

/**
 * Convert earthquake magnitude to a hex color string.
 * Green (<3), yellow (3-4.9), orange (5-6.9), red (>=7).
 * @param {number} magnitude - Earthquake magnitude value.
 * @returns {string} Hex color string.
 */
export function magnitudeToColor(magnitude) {
  if (magnitude < 3.0) return '#00CC00';
  if (magnitude < 5.0) return '#CCCC00';
  if (magnitude < 7.0) return '#FF8800';
  return '#CC0000';
}
