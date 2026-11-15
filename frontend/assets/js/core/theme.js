/**
 * Theme management (light/dark) persisted in localStorage under 'td-theme-v2',
 * matching SiteHeader.tsx in the Figma Make reference.
 */

const STORAGE_KEY = 'td-theme-v2'

/**
 * Return true when the active theme is light (the default).
 * @returns {boolean}
 */
export function isLightTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) !== 'dark'
  } catch {
    return document.documentElement.dataset.theme !== 'dark'
  }
}

/**
 * Apply the saved theme to `<html data-theme="...">` and return whether it is light.
 * @returns {boolean}
 */
export function initTheme() {
  const light = isLightTheme()
  document.documentElement.dataset.theme = light ? 'light' : 'dark'
  return light
}

/**
 * Persist and apply a new theme choice.
 * @param {boolean} nextLight - true for 'light', false for 'dark'.
 */
export function setTheme(nextLight) {
  const theme = nextLight ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Ignore storage quota / privacy mode errors.
  }
}
