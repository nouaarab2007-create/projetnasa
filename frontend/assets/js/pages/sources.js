/**
 * Data sources and missions catalogue controller (`/sources`).
 * Faithful Vanilla JS port of `src/components/SourceCatalogue.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { fetchCatalog } from '../core/api.js'
import { escapeHtml } from '../core/dom.js'
import { icon } from '../core/icons.js'

async function mountSources() {
  initLayout()

  const root = document.getElementById('sources-root')
  if (!root) return

  let sources = []
  try {
    const catalog = await fetchCatalog()
    sources = catalog.sources
  } catch (err) {
    root.innerHTML = `<div class="error-banner">${escapeHtml(err instanceof Error ? err.message : 'Unable to load sources.')}</div>`
    return
  }

  const topics = ['All', ...new Set(sources.flatMap((source) => source.topics))]
  let topic = 'All'

  root.innerHTML = `
    <div class="source-filters" id="source-filters"></div>
    <div class="source-grid" id="source-grid"></div>
  `

  const filtersEl = root.querySelector('#source-filters')
  const gridEl = root.querySelector('#source-grid')

  function renderFilters() {
    if (!filtersEl) return
    filtersEl.innerHTML = `
      ${icon('filter', { size: 17 })}
      ${topics
        .map(
          (item) => `
            <button type="button" data-topic="${escapeHtml(item)}" class="${topic === item ? 'active' : ''}">
              ${escapeHtml(item)}
            </button>
          `,
        )
        .join('')}
    `
    filtersEl.querySelectorAll('button[data-topic]').forEach((btn) => {
      btn.addEventListener('click', () => {
        topic = btn.getAttribute('data-topic') || 'All'
        renderFilters()
        renderGrid()
      })
    })
  }

  function renderGrid() {
    if (!gridEl) return
    const filtered = sources.filter((source) => topic === 'All' || source.topics.includes(topic))
    gridEl.innerHTML = filtered
      .map(
        (source) => `
          <article class="source-card">
            <div class="source-top">
              <span class="source-icon">${icon('database', { size: 20 })}</span>
              <span class="source-status ${source.status === 'FULLY INTEGRATED' ? 'live' : ''}">
                ${escapeHtml(source.status)}
              </span>
            </div>
            <span class="provider">${escapeHtml(source.provider)}</span>
            <h2>${escapeHtml(source.name)}</h2>
            <p>${escapeHtml(source.kind)}</p>
            <dl>
              <div>
                <dt>Coverage</dt>
                <dd>${escapeHtml(source.coverage)}</dd>
              </div>
              <div>
                <dt>Resolution</dt>
                <dd>${escapeHtml(source.resolution)}</dd>
              </div>
              <div>
                <dt>Access</dt>
                <dd>${escapeHtml(source.auth)}</dd>
              </div>
            </dl>
            <div class="topic-list">
              ${source.topics.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}
            </div>
            <a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">
              Official documentation ${icon('arrow-up-right', { size: 15 })}
            </a>
          </article>
        `,
      )
      .join('')
  }

  renderFilters()
  renderGrid()
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountSources)
} else {
  mountSources()
}
