import { parseGeoJSON } from '../domain/earthquake-model.js';
import { toUSGSParams } from '../domain/date-range.js';

const USGS_API_BASE_URL = 'https://earthquake.usgs.gov/fdsnws/event/1/query';
const USGS_EVENT_LIMIT = 20000;
const FETCH_TIMEOUT_MS = 30000;

/**
 * Build the USGS API query URL from filter state.
 * @param {{ start_date: Date, end_date: Date, minimum_magnitude: number }} filter
 * @returns {string} Full USGS API URL.
 */
export function buildQueryURL(filter) {
  const date_params = toUSGSParams(filter.start_date, filter.end_date);
  const params = new URLSearchParams({
    format: 'geojson',
    starttime: date_params.starttime,
    endtime: date_params.endtime,
    minmagnitude: String(filter.minimum_magnitude),
    limit: String(USGS_EVENT_LIMIT),
    orderby: 'time',
  });
  return `${USGS_API_BASE_URL}?${params.toString()}`;
}

/**
 * Fetch earthquake data from the USGS API.
 * Supports AbortSignal for cancellation.
 * @param {{ start_date: Date, end_date: Date, minimum_magnitude: number }} filter
 * @param {AbortSignal} [abort_signal] - Optional AbortSignal to cancel the request.
 * @returns {Promise<{ events: Object[], metadata_count: number, is_capped: boolean }>}
 */
export async function fetchEarthquakes(filter, abort_signal) {
  const url = buildQueryURL(filter);

  const timeout_controller = new AbortController();
  const timeout_id = setTimeout(() => timeout_controller.abort(), FETCH_TIMEOUT_MS);

  // Combine user-provided signal with timeout signal
  // Use a manual listener approach for jsdom compatibility (AbortSignal.any not universally available)
  if (abort_signal) {
    abort_signal.addEventListener('abort', () => timeout_controller.abort(), { once: true });
  }
  const combined_signal = timeout_controller.signal;

  try {
    const response = await fetch(url, { signal: combined_signal });
    clearTimeout(timeout_id);

    if (!response.ok) {
      throw new Error(`USGS API error: HTTP ${response.status}`);
    }

    let raw_geojson;
    try {
      raw_geojson = await response.json();
    } catch {
      throw new Error('USGS API returned unparseable response');
    }

    const { events, metadata_count } = parseGeoJSON(raw_geojson);
    const is_capped = metadata_count >= USGS_EVENT_LIMIT;

    return { events, metadata_count, is_capped };
  } catch (fetch_error) {
    clearTimeout(timeout_id);
    if (fetch_error.name === 'AbortError') {
      if (abort_signal?.aborted) {
        throw new Error('Request cancelled');
      }
      throw new Error('Request timed out after 30 seconds');
    }
    throw fetch_error;
  }
}
