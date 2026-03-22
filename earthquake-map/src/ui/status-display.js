/**
 * StatusDisplay manages the loading indicator, error messages, and earthquake count.
 */

/**
 * Show loading state: disable update button and show spinner.
 */
export function showLoading() {
  const error_el = document.getElementById('error-message');
  if (error_el) error_el.style.display = 'none';
  setUpdateButtonLoading(true);
}

/**
 * Hide loading state: re-enable update button and hide spinner.
 */
export function hideLoading() {
  setUpdateButtonLoading(false);
}

/**
 * Set the update button loading state.
 * @param {boolean} is_loading - Whether the button should show loading state.
 */
export function setUpdateButtonLoading(is_loading) {
  const button = document.getElementById('update-button');
  if (!button) return;
  const spinner = button.querySelector('.update-button-spinner');
  const label = button.querySelector('.update-button-label');
  button.disabled = is_loading;
  if (spinner) spinner.hidden = !is_loading;
  if (label) label.textContent = is_loading ? 'Loading...' : 'Update';
}

/**
 * Show an error message.
 * @param {string} error_message - The error message to display.
 */
export function showError(error_message) {
  const error_el = document.getElementById('error-message');
  if (error_el) {
    error_el.textContent = error_message;
    error_el.style.display = 'block';
  }
}

/**
 * Update the earthquake count display.
 * @param {number} count - Number of earthquakes currently displayed.
 * @param {boolean} is_capped - Whether results are capped at API limit.
 */
export function updateCount(count, is_capped) {
  const count_el = document.getElementById('earthquake-count');
  if (count_el) {
    const cap_warning = is_capped ? ' (results capped at 20,000)' : '';
    count_el.textContent = `${count} earthquakes${cap_warning}`;
  }
}
