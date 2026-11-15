/**
 * Methodology and science page controller (`/methodology`).
 * Faithful Vanilla JS port of `src/app/(frontend)/methodology/page.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { icon } from '../core/icons.js'

function mountMethodology() {
  initLayout()

  document.querySelectorAll('[data-icon]').forEach((el) => {
    const name = el.getAttribute('data-icon')
    const size = Number(el.getAttribute('data-icon-size') || 24)
    if (name) {
      el.outerHTML = icon(name, { size })
    }
  })
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountMethodology)
} else {
  mountMethodology()
}
