/**
 * Scientific variable catalogue controller (`/variables`).
 * Faithful Vanilla JS port of `src/components/VariableCatalogue.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { fetchCatalog } from '../core/api.js'
import { escapeHtml } from '../core/dom.js'
import { icon } from '../core/icons.js'

const QUESTIONS = [
  ['Is the climate warming in this region?', 'T2M'],
  ['Is rainfall increasing or decreasing?', 'PRECTOTCORR'],
  ['Are soils becoming drier?', 'GWETROOT'],
  ['Is solar radiation changing?', 'ALLSKY_SFC_SW_DWN'],
  ['Is wind speed changing?', 'WS10M'],
]

async function mountVariables() {
  initLayout()

  const root = document.getElementById('variables-root')
  if (!root) return

  let variables = []
  try {
    const catalog = await fetchCatalog()
    variables = catalog.variables
  } catch (err) {
    root.innerHTML = `<div class="error-banner">${escapeHtml(err instanceof Error ? err.message : 'Unable to load variables.')}</div>`
    return
  }

  const categories = ['All', ...new Set(variables.map((item) => item.category))]
  let search = ''
  let category = 'All'
  let selected = 'T2M'

  root.innerHTML = `
    <section class="question-strip" id="question-strip"></section>
    <div class="catalogue-tools">
      <div class="search-field">
        ${icon('search', { size: 17 })}
        <input type="text" id="variable-search" placeholder="Search variables or NASA codes" />
      </div>
      <div class="filter-tabs" id="category-tabs"></div>
    </div>
    <div class="variable-grid" id="variable-grid"></div>
  `

  const questionStrip = root.querySelector('#question-strip')
  const searchInput = root.querySelector('#variable-search')
  const categoryTabs = root.querySelector('#category-tabs')
  const variableGrid = root.querySelector('#variable-grid')

  function renderQuestions() {
    if (!questionStrip) return
    questionStrip.innerHTML = `
      <div>
        ${icon('sparkles', { size: 18 })}
        <span>Start with a scientific question</span>
      </div>
      ${QUESTIONS.map(
        ([question, code]) => `
          <button type="button" data-code="${escapeHtml(code)}" class="${selected === code ? 'active' : ''}">
            ${escapeHtml(question)}
          </button>
        `,
      ).join('')}
    `
    questionStrip.querySelectorAll('button[data-code]').forEach((btn) => {
      btn.addEventListener('click', () => {
        selected = btn.getAttribute('data-code') || 'T2M'
        renderQuestions()
        renderGrid()
      })
    })
  }

  function renderTabs() {
    if (!categoryTabs) return
    categoryTabs.innerHTML = categories
      .map(
        (item) => `
          <button type="button" data-cat="${escapeHtml(item)}" class="${category === item ? 'active' : ''}">
            ${escapeHtml(item)}
          </button>
        `,
      )
      .join('')
    categoryTabs.querySelectorAll('button[data-cat]').forEach((btn) => {
      btn.addEventListener('click', () => {
        category = btn.getAttribute('data-cat') || 'All'
        renderTabs()
        renderGrid()
      })
    })
  }

  function renderGrid() {
    if (!variableGrid) return
    const query = search.toLowerCase()
    const filtered = variables.filter(
      (item) =>
        (category === 'All' || item.category === category) &&
        `${item.name} ${item.code} ${item.definition}`.toLowerCase().includes(query),
    )

    variableGrid.innerHTML = filtered
      .map((variable) => {
        const isSelected = selected === variable.code
        return `
          <article
            class="${isSelected ? 'variable-card selected' : 'variable-card'}"
            data-var-code="${escapeHtml(variable.code)}"
            data-selectable="${variable.selectable ? 'true' : 'false'}"
          >
            <div>
              <span class="code">${escapeHtml(variable.code)}</span>
              ${
                variable.selectable
                  ? '<span class="status integrated">LIVE</span>'
                  : '<span class="status planned">CATALOGUED</span>'
              }
            </div>
            <h3>${escapeHtml(variable.name)}</h3>
            <p>${escapeHtml(variable.definition)}</p>
            <dl>
              <div>
                <dt>Unit</dt>
                <dd>${escapeHtml(variable.unit)}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>${escapeHtml(variable.source)}</dd>
              </div>
            </dl>
            <aside>
              <strong>Why it matters</strong>
              ${escapeHtml(variable.why)}
            </aside>
            ${
              isSelected && variable.selectable
                ? `<a href="/explorer?parameter=${encodeURIComponent(variable.code)}" class="selected-indicator">
                    ${icon('check', { size: 14 })} Selected · Investigate &rarr;
                  </a>`
                : ''
            }
            ${
              !variable.selectable
                ? '<span class="future-note">Retrieval workflow not yet integrated</span>'
                : ''
            }
          </article>
        `
      })
      .join('')

    variableGrid.querySelectorAll('article[data-selectable="true"]').forEach((card) => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('a')) return
        const code = card.getAttribute('data-var-code')
        if (code) {
          selected = code
          renderQuestions()
          renderGrid()
        }
      })
    })
  }

  searchInput?.addEventListener('input', (e) => {
    search = e.target.value
    renderGrid()
  })

  renderQuestions()
  renderTabs()
  renderGrid()
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountVariables)
} else {
  mountVariables()
}
