/**
 * TrendDetectiveLogo component (port of src/components/TrendDetectiveLogo.tsx).
 */

/**
 * Render the Trend Detective brand mark.
 * @param {'compact' | 'hero'} [presentation='compact']
 * @returns {string}
 */
export function renderLogo(presentation = 'compact') {
  const isFile = typeof window !== 'undefined' && window.location.protocol === 'file:'
  const inPages =
    typeof window !== 'undefined' &&
    window.location.pathname.replace(/\\/g, '/').includes('/pages/')
  const prefix = isFile ? (inPages ? '../assets' : './assets') : '/assets'

  return `
    <span class="project-logo project-logo-${presentation}">
      <span class="project-logo-mark" aria-hidden="true">
        <img src="${prefix}/images/logo_mode_claire.jpg" alt="" class="logo-img logo-img-light" />
        <img src="${prefix}/images/logo_mode_sombre.jpg" alt="" class="logo-img logo-img-dark" />
      </span>
      <span class="project-logo-copy">
        <small>EARTH SCIENCE PLATFORM</small>
        <span><strong>TREND</strong> DETECTIVE</span>
      </span>
    </span>
  `
}
