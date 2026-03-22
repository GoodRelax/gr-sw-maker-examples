import { initializeMap, renderMarkers, clearMarkers } from './ui/map-renderer.js';
import { initializeControls } from './ui/control-panel.js';
import { showLoading, hideLoading, showError, updateCount } from './ui/status-display.js';
import { fetchEarthquakes } from './adapter/usgs-client.js';
import { fromPreset } from './domain/date-range.js';

const DEFAULT_PRESET = '7d';
const DEFAULT_MINIMUM_MAGNITUDE = 1.0;

let current_abort_controller = null;

/**
 * Handle filter changes: cancel in-flight request, fetch new data, render markers.
 * @param {{ start_date: Date, end_date: Date, minimum_magnitude: number }} filter
 */
async function handleFilterChange(filter) {
  // Cancel any in-flight request (FR-17)
  if (current_abort_controller) {
    current_abort_controller.abort();
  }
  current_abort_controller = new AbortController();

  showLoading();
  clearMarkers();

  try {
    const { events, metadata_count, is_capped } = await fetchEarthquakes(
      filter,
      current_abort_controller.signal
    );
    hideLoading();
    updateCount(metadata_count, is_capped);
    renderMarkers(events);
  } catch (fetch_error) {
    hideLoading();
    if (fetch_error.message === 'Request cancelled') {
      // Silently ignore cancelled requests — a new one is already in flight
      return;
    }
    showError(fetch_error.message);
  }
}

/**
 * Initialize the application.
 */
function initializeApp() {
  initializeMap('earthquake-map');

  const { emitFilter } = initializeControls(handleFilterChange, {
    default_preset: DEFAULT_PRESET,
    default_minimum_magnitude: DEFAULT_MINIMUM_MAGNITUDE,
  });

  // Trigger initial data load
  emitFilter();
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}
