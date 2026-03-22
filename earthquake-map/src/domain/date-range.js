/**
 * Time range preset definitions.
 * Each preset maps to a duration in milliseconds.
 */
const PRESETS = {
  '1h': 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
};

/**
 * Create a DateRange from a preset key.
 * @param {string} preset_key - One of '1h', '24h', '7d', '30d'.
 * @returns {{ start_date: Date, end_date: Date }}
 */
export function fromPreset(preset_key) {
  const duration_ms = PRESETS[preset_key];
  if (!duration_ms) {
    throw new Error(`Unknown preset: ${preset_key}`);
  }
  const end_date = new Date();
  const start_date = new Date(end_date.getTime() - duration_ms);
  return { start_date, end_date };
}

/**
 * Validate a date range.
 * @param {Date} start_date
 * @param {Date} end_date
 * @returns {{ valid: boolean, error_message: string|null }}
 */
export function isValid(start_date, end_date) {
  if (!(start_date instanceof Date) || isNaN(start_date.getTime())) {
    return { valid: false, error_message: 'Invalid start date' };
  }
  if (!(end_date instanceof Date) || isNaN(end_date.getTime())) {
    return { valid: false, error_message: 'Invalid end date' };
  }
  if (end_date < start_date) {
    return { valid: false, error_message: 'End date must not precede start date' };
  }
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(0, 0, 0, 0);
  if (end_date >= tomorrow) {
    return { valid: false, error_message: 'End date must not be in the future' };
  }
  return { valid: true, error_message: null };
}

/**
 * Convert a date range to USGS API query parameters.
 * @param {Date} start_date
 * @param {Date} end_date
 * @returns {{ starttime: string, endtime: string }}
 */
export function toUSGSParams(start_date, end_date) {
  return {
    starttime: start_date.toISOString(),
    endtime: end_date.toISOString(),
  };
}

/**
 * Get available preset keys.
 * @returns {string[]}
 */
export function getPresetKeys() {
  return Object.keys(PRESETS);
}
