import { fromPreset, isValid } from '../domain/date-range.js';

/**
 * Initialize the control panel and wire up event listeners.
 * @param {Function} on_filter_change - Callback invoked with { start_date, end_date, minimum_magnitude }.
 * @param {{ default_preset: string, default_minimum_magnitude: number }} defaults
 */
export function initializeControls(on_filter_change, defaults) {
  const magnitude_slider = document.getElementById('magnitude-slider');
  const magnitude_display = document.getElementById('magnitude-display');
  const custom_start = document.getElementById('custom-start-date');
  const custom_end = document.getElementById('custom-end-date');
  const preset_buttons = document.querySelectorAll('.time-preset');

  let current_minimum_magnitude = defaults.default_minimum_magnitude;
  let current_date_range = fromPreset(defaults.default_preset);
  let active_preset = defaults.default_preset;

  // Set initial slider value
  if (magnitude_slider) {
    magnitude_slider.value = String(current_minimum_magnitude);
  }
  if (magnitude_display) {
    magnitude_display.textContent = current_minimum_magnitude.toFixed(1);
  }

  // Highlight active preset
  updateActivePreset(active_preset, preset_buttons);

  /**
   * Build and emit the current filter state.
   */
  function emitFilter() {
    on_filter_change({
      start_date: current_date_range.start_date,
      end_date: current_date_range.end_date,
      minimum_magnitude: current_minimum_magnitude,
    });
  }

  // Preset button handlers
  for (const button of preset_buttons) {
    button.addEventListener('click', () => {
      const preset_key = button.dataset.range;
      current_date_range = fromPreset(preset_key);
      active_preset = preset_key;
      updateActivePreset(active_preset, preset_buttons);
      clearCustomDateInputs(custom_start, custom_end);
    });
  }

  // Custom date range handler
  function handleCustomDateChange() {
    if (!custom_start.value || !custom_end.value) return;
    const start_date = new Date(custom_start.value);
    const end_date = new Date(custom_end.value + 'T23:59:59');
    const validation = isValid(start_date, end_date);
    if (!validation.valid) {
      const error_el = document.getElementById('error-message');
      if (error_el) {
        error_el.textContent = validation.error_message;
        error_el.style.display = 'block';
      }
      return;
    }
    current_date_range = { start_date, end_date };
    active_preset = null;
    updateActivePreset(null, preset_buttons);
  }

  if (custom_start) custom_start.addEventListener('change', handleCustomDateChange);
  if (custom_end) custom_end.addEventListener('change', handleCustomDateChange);

  // Magnitude slider handler
  if (magnitude_slider) {
    magnitude_slider.addEventListener('input', () => {
      current_minimum_magnitude = parseFloat(magnitude_slider.value);
      if (magnitude_display) {
        magnitude_display.textContent = current_minimum_magnitude.toFixed(1);
      }
    });
    magnitude_slider.addEventListener('change', () => {
      current_minimum_magnitude = parseFloat(magnitude_slider.value);
    });
  }

  // Update button handler
  const update_button = document.getElementById('update-button');
  if (update_button) {
    update_button.addEventListener('click', () => {
      emitFilter();
    });
  }

  return { emitFilter };
}

/**
 * Update the visual state of preset buttons.
 * @param {string|null} active_key
 * @param {NodeList} buttons
 */
function updateActivePreset(active_key, buttons) {
  for (const button of buttons) {
    if (button.dataset.range === active_key) {
      button.classList.add('active');
    } else {
      button.classList.remove('active');
    }
  }
}

/**
 * Clear custom date input values.
 * @param {HTMLInputElement} start_input
 * @param {HTMLInputElement} end_input
 */
function clearCustomDateInputs(start_input, end_input) {
  if (start_input) start_input.value = '';
  if (end_input) end_input.value = '';
}
