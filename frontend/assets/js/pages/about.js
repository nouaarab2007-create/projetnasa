/**
 * About page controller (`/about`).
 * Faithful Vanilla JS port of `src/app/(frontend)/about/page.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { icon } from '../core/icons.js'

function mountAbout() {
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
  document.addEventListener('DOMContentLoaded', mountAbout)
} else {
  mountAbout()
}
