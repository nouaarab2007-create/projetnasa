/**
 * Regional comparison controller (`/comparison`).
 * Faithful Vanilla JS port of `src/components/ComparisonClient.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { createTrendChart } from '../components/trend-chart.js'
import { fetchCatalog, fetchComparison } from '../core/api.js'
import { escapeHtml } from '../core/dom.js'
import { icon } from '../core/icons.js'

async function mountComparison() {
  initLayout()

  const root = document.getElementById('comparison-root')
  if (!root) return

  let variables = []
  let regions = []
  try {
    const catalog = await fetchCatalog()
    variables = catalog.variables
    regions = catalog.regions
  } catch (err) {
    root.innerHTML = `<div class="error-banner">${escapeHtml(err instanceof Error ? err.message : 'Unable to load catalogue.')}</div>`
    return
  }

  let regionA = 'svalbard'
  let regionB = 'amazon'
  let parameter = 'T2M'
  let loading = false
  let error = ''
  let result = null
  let charts = []

  const selectableVars = variables.filter((item) => item.selectable)

  root.className = 'comparison-tool'
  root.innerHTML = `
    <div class="comparison-controls">
      <label>
        Region A
        <select id="cmp-region-a">
          ${regions
            .map(
              (r) =>
                `<option value="${escapeHtml(r.id)}" ${r.id === regionA ? 'selected' : ''}>${escapeHtml(r.name)}</option>`,
            )
            .join('')}
        </select>
      </label>
      ${icon('arrow-right', { size: 20 })}
      <label>
        Region B
        <select id="cmp-region-b">
          ${regions
            .map(
              (r) =>
                `<option value="${escapeHtml(r.id)}" ${r.id === regionB ? 'selected' : ''}>${escapeHtml(r.name)}</option>`,
            )
            .join('')}
        </select>
      </label>
      <label>
        Variable
        <select id="cmp-parameter">
          ${selectableVars
            .map(
              (v) =>
                `<option value="${escapeHtml(v.code)}" ${v.code === parameter ? 'selected' : ''}>${escapeHtml(v.name)}</option>`,
            )
            .join('')}
        </select>
      </label>
      <button type="button" class="button primary" id="cmp-run-btn">
        ${icon('scale', { size: 17 })} Compare regions
      </button>
    </div>
    <div id="cmp-output"></div>
  `

  const selectA = root.querySelector('#cmp-region-a')
  const selectB = root.querySelector('#cmp-region-b')
  const selectParam = root.querySelector('#cmp-parameter')
  const runBtn = root.querySelector('#cmp-run-btn')
  const outputEl = root.querySelector('#cmp-output')

  selectA?.addEventListener('change', (e) => {
    regionA = e.target.value
  })
  selectB?.addEventListener('change', (e) => {
    regionB = e.target.value
  })
  selectParam?.addEventListener('change', (e) => {
    parameter = e.target.value
  })

  function destroyCharts() {
    charts.forEach((c) => c.destroy())
    charts = []
  }

  function renderOutput() {
    if (!outputEl) return
    destroyCharts()

    if (runBtn) {
      runBtn.disabled = loading
      runBtn.innerHTML = loading
        ? `${icon('loader-circle', { size: 17, className: 'spin' })} Compare regions`
        : `${icon('scale', { size: 17 })} Compare regions`
    }

    const errorHtml = error
      ? `<div class="error-banner">${escapeHtml(error)} No simulated data were substituted.</div>`
      : ''

    if (!result && !loading) {
      outputEl.innerHTML = `
        ${errorHtml}
        <div class="comparison-empty">
          ${icon('scale', { size: 40 })}
          <h2>One variable. Two places. Comparable evidence.</h2>
          <p>
            Run the same annual trend workflow for both regions to reveal spatial differences
            without implying causation.
          </p>
        </div>
      `
      return
    }

    if (loading && !result) {
      outputEl.innerHTML = `
        ${errorHtml}
        <div class="comparison-empty">
          ${icon('loader-circle', { size: 40, className: 'spin cyan' })}
          <h2>Retrieving comparative NASA POWER series…</h2>
          <p>Applying identical temporal aggregation and regression methods to both grid cells.</p>
        </div>
      `
      return
    }

    if (!result) return

    const definition = variables.find((item) => item.code === parameter) || variables[0]
    const first = regions.find((item) => item.id === regionA) || regions[0]
    const second = regions.find((item) => item.id === regionB) || regions[3]

    const pairs = [
      ['A', first, result.regionA, 'cmp-canvas-a'],
      ['B', second, result.regionB, 'cmp-canvas-b'],
    ]

    outputEl.innerHTML = `
      ${errorHtml}
      <div class="comparison-results">
        ${pairs
          .map(
            ([label, region, data, canvasId]) => `
              <article class="comparison-region">
                <div class="comparison-region-title">
                  <span>REGION ${escapeHtml(label)}</span>
                  <h2>${escapeHtml(region.name)}</h2>
                  <p>${region.latitude}, ${region.longitude} · NASA POWER grid cell</p>
                </div>
                <div class="mini-stats">
                  <div>
                    <small>Trend / decade</small>
                    <strong>
                      ${data.analysis.trendPerDecade > 0 ? '+' : ''}${data.analysis.trendPerDecade.toFixed(3)} ${escapeHtml(definition.unit)}
                    </strong>
                  </div>
                  <div>
                    <small>OLS p-value</small>
                    <strong>${Number(data.analysis.regression.pValue).toPrecision(3)}</strong>
                  </div>
                  <div>
                    <small>Verdict</small>
                    <strong>${escapeHtml(data.analysis.verdict)}</strong>
                  </div>
                  <div>
                    <small>Risk indicator</small>
                    <strong>${data.analysis.risk.score}% · ${escapeHtml(data.analysis.risk.level)}</strong>
                  </div>
                </div>
                <div class="comparison-chart">
                  <canvas id="${canvasId}"></canvas>
                </div>
              </article>
            `,
          )
          .join('')}
        <div class="comparison-verdict">
          <span>Difference in OLS trends</span>
          <strong>${result.differencePerDecade.toFixed(3)} ${escapeHtml(definition.unit)} / decade</strong>
          <p>${escapeHtml(result.interpretation)}</p>
        </div>
      </div>
    `

    pairs.forEach(([, , data, canvasId]) => {
      const canvas = outputEl.querySelector(`#${canvasId}`)
      if (canvas) {
        charts.push(
          createTrendChart(canvas, {
            points: data.points,
            fitted: data.analysis.regression.fitted,
            unit: definition.unit,
          }),
        )
      }
    })
  }

  async function compare() {
    loading = true
    error = ''
    renderOutput()

    const first = regions.find((item) => item.id === regionA) || regions[0]
    const second = regions.find((item) => item.id === regionB) || regions[3]

    try {
      result = await fetchComparison({
        parameter,
        start: 1990,
        end: 2024,
        mode: 'annual',
        regionA: first,
        regionB: second,
      })
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'Comparison failed.'
    } finally {
      loading = false
      renderOutput()
    }
  }

  runBtn?.addEventListener('click', compare)
  renderOutput()
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountComparison)
} else {
  mountComparison()
}
