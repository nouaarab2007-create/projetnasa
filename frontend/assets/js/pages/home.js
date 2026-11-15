/**
 * Home page controller (`/` -> `pages/index.html`).
 * Faithful Vanilla JS port of `src/app/(frontend)/page.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { icon } from '../core/icons.js'

const OBJECTIVES = [
  {
    number: '01',
    iconName: 'satellite',
    title: 'Choose the variable',
    text: 'Select a measurable NASA Earth system parameter.',
  },
  {
    number: '02',
    iconName: 'map-pin',
    title: 'Choose the region',
    text: 'Investigate any NASA POWER grid cell on Earth.',
  },
  {
    number: '03',
    iconName: 'trending-up',
    title: 'Select the period',
    text: 'Define the time range and temporal processing mode.',
  },
  {
    number: '04',
    iconName: 'microscope',
    title: 'Examine the series',
    text: 'Visualize observations and measure trend magnitude.',
  },
  {
    number: '05',
    iconName: 'shield-alert',
    title: 'Test and assess risk',
    text: 'Test significance and estimate a five-year phenomenon risk score.',
  },
]

function mountHome() {
  initLayout()

  document.querySelectorAll('[data-icon]').forEach((el) => {
    const name = el.getAttribute('data-icon')
    const size = Number(el.getAttribute('data-icon-size') || 16)
    if (name) {
      el.outerHTML = icon(name, { size })
    }
  })

  const grid = document.getElementById('objective-grid')
  if (grid && !grid.children.length) {
    grid.innerHTML = OBJECTIVES.map(
      (item) => `
        <article>
          <span class="objective-number">${item.number}</span>
          <div class="objective-icon">${icon(item.iconName, { size: 24 })}</div>
          <h3>${item.title}</h3>
          <p>${item.text}</p>
        </article>
      `,
    ).join('')
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountHome)
} else {
  mountHome()
}
