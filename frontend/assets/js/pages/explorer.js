/**
 * Investigation workspace controller (`/explorer` & `/analysis`).
 * Faithful Vanilla JS port of `src/components/ExplorerClient.tsx` with
 * expanded options for significance threshold (alpha), risk forecast horizon,
 * and structured JSON export for future database & AI pipeline integration.
 */

import { initLayout } from '../components/layout.js'
import { createTrendChart } from '../components/trend-chart.js'
import { fetchAnalysis, fetchCatalog } from '../core/api.js'
import { escapeHtml } from '../core/dom.js'
import { icon } from '../core/icons.js'

function parseInitialParams(variables, regions) {
  const params = new URLSearchParams(window.location.search)
  const selectable = variables.filter((item) => item.selectable)
  const paramCode = params.get('parameter')
  const validParam = selectable.some((item) => item.code === paramCode) ? paramCode : 'T2M'

  const regionId = params.get('region') || 'svalbard'
  const matchedRegion = regions.find((item) => item.id === regionId) || regions[0]

  const latParam = params.get('latitude') ?? params.get('lat')
  const lonParam = params.get('longitude') ?? params.get('lon')
  const latitude = latParam !== null && !Number.isNaN(Number(latParam)) ? Number(latParam) : matchedRegion.latitude
  const longitude = lonParam !== null && !Number.isNaN(Number(lonParam)) ? Number(lonParam) : matchedRegion.longitude

  const start = Number(params.get('start')) || 1990
  const end = Number(params.get('end')) || 2024
  const mode = ['annual', 'anomaly', 'raw'].includes(params.get('mode')) ? params.get('mode') : 'annual'
  const alpha = ['0.01', '0.05', '0.10'].includes(params.get('alpha')) ? params.get('alpha') : '0.05'
  const horizon = ['5', '10', '15', '20'].includes(params.get('horizon')) ? params.get('horizon') : '5'
  const autostart = params.get('autostart') === '1'

  return {
    parameter: validParam,
    regionId: matchedRegion.id,
    latitude,
    longitude,
    start,
    end,
    mode,
    alpha,
    horizon,
    autostart,
  }
}

async function mountExplorer() {
  initLayout()

  const root = document.getElementById('explorer-root')
  if (!root) return

  let catalog
  try {
    catalog = await fetchCatalog()
  } catch (err) {
    root.innerHTML = `
      <div class="error-state">
        ${icon('triangle-alert', { size: 30 })}
        <h2>Catalogue unavailable</h2>
        <p>${escapeHtml(err instanceof Error ? err.message : 'Unable to load scientific catalogue.')}</p>
      </div>
    `
    return
  }

  const available = catalog.variables.filter((item) => item.selectable)
  const regions = catalog.regions
  const state = {
    ...parseInitialParams(catalog.variables, regions),
    loading: false,
    error: '',
    result: null,
  }

  let activeChart = null

  function getDefinition() {
    return available.find((item) => item.code === state.parameter) || available[0]
  }

  root.className = 'investigation-layout'
  root.innerHTML = `
    <aside class="control-panel">
      <div class="panel-heading">
        ${icon('flask-conical', { size: 18 })}
        <div>
          <span>Investigation setup</span>
          <small>NASA POWER monthly point data</small>
        </div>
      </div>
      <label>
        1. Scientific variable
        <select data-field="parameter">
          ${available
            .map(
              (item) =>
                `<option value="${escapeHtml(item.code)}" ${
                  item.code === state.parameter ? 'selected' : ''
                }>${escapeHtml(item.name)} · ${escapeHtml(item.code)}</option>`,
            )
            .join('')}
        </select>
      </label>
      <label>
        2. Predefined region
        <select data-field="region">
          ${regions
            .map(
              (region) =>
                `<option value="${escapeHtml(region.id)}" ${
                  region.id === state.regionId ? 'selected' : ''
                }>${escapeHtml(region.name)}</option>`,
            )
            .join('')}
        </select>
      </label>
      <div class="field-grid">
        <label>
          Latitude
          <input
            type="number"
            min="-90"
            max="90"
            step="0.01"
            data-field="latitude"
            value="${state.latitude}"
          />
        </label>
        <label>
          Longitude
          <input
            type="number"
            min="-180"
            max="180"
            step="0.01"
            data-field="longitude"
            value="${state.longitude}"
          />
        </label>
      </div>
      <div class="field-grid">
        <label>
          3. Start year
          <input
            type="number"
            min="1981"
            max="2025"
            data-field="start"
            value="${state.start}"
          />
        </label>
        <label>
          End year
          <input
            type="number"
            min="1981"
            max="2025"
            data-field="end"
            value="${state.end}"
          />
        </label>
      </div>
      <label>
        4. Analysis mode
        <select data-field="mode">
          <option value="annual" ${state.mode === 'annual' ? 'selected' : ''}>Annual averages</option>
          <option value="anomaly" ${state.mode === 'anomaly' ? 'selected' : ''}>Monthly anomalies</option>
          <option value="raw" ${state.mode === 'raw' ? 'selected' : ''}>Raw monthly values</option>
        </select>
      </label>
      <div class="field-grid">
        <label>
          5. Significance (α)
          <select data-field="alpha">
            <option value="0.01" ${state.alpha === '0.01' ? 'selected' : ''}>α = 0.01 (99%)</option>
            <option value="0.05" ${state.alpha === '0.05' ? 'selected' : ''}>α = 0.05 (95%)</option>
            <option value="0.10" ${state.alpha === '0.10' ? 'selected' : ''}>α = 0.10 (90%)</option>
          </select>
        </label>
        <label>
          Risk horizon
          <select data-field="horizon">
            <option value="5" ${state.horizon === '5' ? 'selected' : ''}>5 years</option>
            <option value="10" ${state.horizon === '10' ? 'selected' : ''}>10 years</option>
            <option value="15" ${state.horizon === '15' ? 'selected' : ''}>15 years</option>
            <option value="20" ${state.horizon === '20' ? 'selected' : ''}>20 years</option>
          </select>
        </label>
      </div>
      <div class="mode-note">
        ${icon('map-pin', { size: 15 })} Values represent a grid cell, not an exact ground measurement.
      </div>
      <button type="button" class="button primary full" data-action="investigate">
        ${icon('play', { size: 17, fill: 'currentColor' })} Launch investigation
      </button>
    </aside>
    <section class="results-panel" id="results-panel"></section>
  `

  const paramSelect = root.querySelector('[data-field="parameter"]')
  const regionSelect = root.querySelector('[data-field="region"]')
  const latInput = root.querySelector('[data-field="latitude"]')
  const lonInput = root.querySelector('[data-field="longitude"]')
  const startInput = root.querySelector('[data-field="start"]')
  const endInput = root.querySelector('[data-field="end"]')
  const modeSelect = root.querySelector('[data-field="mode"]')
  const alphaSelect = root.querySelector('[data-field="alpha"]')
  const horizonSelect = root.querySelector('[data-field="horizon"]')
  const launchBtn = root.querySelector('[data-action="investigate"]')
  const resultsPanel = root.querySelector('#results-panel')

  paramSelect?.addEventListener('change', (e) => {
    state.parameter = e.target.value
  })

  regionSelect?.addEventListener('change', (e) => {
    const region = regions.find((item) => item.id === e.target.value)
    if (region) {
      state.regionId = region.id
      state.latitude = region.latitude
      state.longitude = region.longitude
      if (latInput) latInput.value = String(region.latitude)
      if (lonInput) lonInput.value = String(region.longitude)
    }
  })

  latInput?.addEventListener('input', (e) => {
    state.latitude = Number(e.target.value)
  })
  lonInput?.addEventListener('input', (e) => {
    state.longitude = Number(e.target.value)
  })
  startInput?.addEventListener('input', (e) => {
    state.start = Number(e.target.value)
  })
  endInput?.addEventListener('input', (e) => {
    state.end = Number(e.target.value)
  })
  modeSelect?.addEventListener('change', (e) => {
    state.mode = e.target.value
  })
  alphaSelect?.addEventListener('change', (e) => {
    state.alpha = e.target.value
  })
  horizonSelect?.addEventListener('change', (e) => {
    state.horizon = e.target.value
  })

  function downloadCsv() {
    if (!state.result) return
    const definition = getDefinition()
    const csv = [
      `date,${state.parameter}_${definition.unit}`,
      ...state.result.points.map((point) => `${point.date},${point.value}`),
    ].join('\n')
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    link.download = `trend-detective-${state.parameter}-${state.latitude}-${state.longitude}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  function downloadPng() {
    const url = activeChart?.toBase64Image()
    if (!url) return
    const link = document.createElement('a')
    link.href = url
    link.download = `trend-detective-${state.parameter}.png`
    link.click()
  }

  function downloadJson() {
    if (!state.result) return
    const payload = JSON.stringify(state.result, null, 2)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([payload], { type: 'application/json' }))
    link.download = `trend-detective-session-${state.parameter}-${state.latitude}-${state.longitude}.json`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  function updateLaunchButton() {
    if (!launchBtn) return
    launchBtn.disabled = state.loading
    launchBtn.innerHTML = state.loading
      ? `${icon('loader-circle', { size: 18, className: 'spin' })} Retrieving NASA data…`
      : `${icon('play', { size: 17, fill: 'currentColor' })} Launch investigation`
  }

  function renderResults() {
    if (!resultsPanel) return
    if (activeChart) {
      activeChart.destroy()
      activeChart = null
    }

    if (state.loading) {
      resultsPanel.innerHTML = `
        <div class="empty-state">
          ${icon('loader-circle', { size: 40, className: 'spin cyan' })}
          <h2>Contacting NASA POWER</h2>
          <p>
            Retrieving and validating monthly observations. No simulated values will be
            substituted.
          </p>
        </div>
      `
      return
    }

    if (state.error) {
      resultsPanel.innerHTML = `
        <div class="error-state">
          ${icon('triangle-alert', { size: 30 })}
          <h2>Real data unavailable</h2>
          <p>${escapeHtml(state.error)}</p>
          <p>No simulated observations were inserted. Adjust the query or try again later.</p>
          <button type="button" class="button secondary" data-action="retry">
            ${icon('rotate-ccw', { size: 16 })} Retry
          </button>
        </div>
      `
      resultsPanel.querySelector('[data-action="retry"]')?.addEventListener('click', investigate)
      return
    }

    if (!state.result) {
      resultsPanel.innerHTML = `
        <div class="empty-state">
          <div class="radar">
            <span></span>
          </div>
          <h2>Your evidence will appear here</h2>
          <p>
            Configure a variable, place, and period. We will retrieve real NASA POWER observations
            and run three trend methods.
          </p>
        </div>
      `
      return
    }

    const { result } = state
    const definition = getDefinition()
    const firstPoint = result.points[0]
    const lastPoint = result.points[result.points.length - 1]
    const trendPerDecade = result.analysis.trendPerDecade
    const risk = result.analysis.risk
    const reg = result.analysis.regression
    const mk = result.analysis.mannKendall
    const alphaNum = Number(result.analysis.alpha ?? state.alpha ?? 0.05)
    const isSignificant = reg.pValue < alphaNum && mk.significant

    const provenanceItems = Object.entries(result.metadata || {})
      .filter(([key]) => key !== 'simulated')
      .map(
        ([key, value]) => `
          <p>
            <span>${escapeHtml(key.replace(/([A-Z])/g, ' $1'))}</span>
            <strong>${escapeHtml(String(value))}</strong>
          </p>
        `,
      )
      .join('')

    resultsPanel.innerHTML = `
      <div class="result-toolbar">
        <div>
          <span class="live-dot"></span> NASA POWER · verified response
        </div>
        <div>
          <button type="button" data-action="download-csv">
            ${icon('download', { size: 15 })} CSV
          </button>
          <button type="button" data-action="download-png">
            ${icon('download', { size: 15 })} PNG
          </button>
          <button type="button" data-action="download-json" title="Export structured session JSON for database / AI">
            ${icon('database', { size: 15 })} JSON
          </button>
        </div>
      </div>
      <div class="summary-grid">
        <article>
          <small>First value</small>
          <strong>
            ${firstPoint.value.toFixed(2)} <em>${escapeHtml(definition.unit)}</em>
          </strong>
          <span>${escapeHtml(firstPoint.date)}</span>
        </article>
        <article>
          <small>Last value</small>
          <strong>
            ${lastPoint.value.toFixed(2)} <em>${escapeHtml(definition.unit)}</em>
          </strong>
          <span>${escapeHtml(lastPoint.date)}</span>
        </article>
        <article>
          <small>OLS trend / decade</small>
          <strong class="${trendPerDecade >= 0 ? 'warm' : 'cyan'}">
            ${trendPerDecade > 0 ? '+' : ''}${trendPerDecade.toFixed(3)} <em>${escapeHtml(definition.unit)}</em>
          </strong>
          <span>95% CI available below</span>
        </article>
        <article>
          <small>Valid observations</small>
          <strong>${result.analysis.validObservations}</strong>
          <span>Missing values excluded</span>
        </article>
      </div>
      <section class="risk-panel" aria-labelledby="risk-heading">
        <div class="risk-score">
          <div class="risk-gauge" aria-label="${risk.score} percent">
            <svg viewBox="0 0 42 42" role="img">
              <circle class="risk-track" cx="21" cy="21" r="15.9"></circle>
              <circle
                class="risk-progress"
                cx="21"
                cy="21"
                r="15.9"
                pathLength="100"
                stroke-dasharray="${risk.score} 100"
              ></circle>
            </svg>
            <strong>${risk.score}%</strong>
          </div>
          <div>
            <span>Risk screening score</span>
            <h2 id="risk-heading">${escapeHtml(risk.phenomenon)}</h2>
            <p>
              ${escapeHtml(risk.level)} signal · approximately ±${risk.uncertainty} points
            </p>
          </div>
        </div>
        <div class="risk-details">
          <div>
            <small>Forecast horizon</small>
            <strong>${risk.horizonYears} years</strong>
            <span>
              Linear projected change: ${risk.projectedChange > 0 ? '+' : ''}${risk.projectedChange.toFixed(2)} ${escapeHtml(definition.unit)}
            </span>
          </div>
          <div>
            <small>Adverse trend signal</small>
            <meter min="0" max="100" value="${risk.trendComponent}"></meter>
            <span>${risk.trendComponent}% contribution strength</span>
          </div>
          <div>
            <small>Recent shift signal</small>
            <meter min="0" max="100" value="${risk.recentComponent}"></meter>
            <span>${risk.recentComponent}% contribution strength</span>
          </div>
          <div>
            <small>Statistical evidence</small>
            <meter min="0" max="100" value="${risk.evidenceConfidence}"></meter>
            <span>${risk.evidenceConfidence}% evidence score</span>
          </div>
        </div>
        <div class="risk-explanation">
          ${icon('shield-alert', { size: 18 })}
          <div>
            <strong>${escapeHtml(risk.interpretation)}</strong>
            <p>${escapeHtml(risk.method)}</p>
            <p class="risk-warning">${escapeHtml(risk.disclaimer)}</p>
          </div>
        </div>
      </section>
      <div class="chart-card">
        <div class="chart-title">
          <div>
            <span class="eyebrow">Observed evidence</span>
            <h2>${escapeHtml(definition.name)} trend</h2>
          </div>
          <span>${state.latitude.toFixed(2)}°, ${state.longitude.toFixed(2)}°</span>
        </div>
        <div class="chart-wrap">
          <canvas id="trend-canvas"></canvas>
        </div>
      </div>
      <div class="analysis-grid">
        <article class="analysis-card">
          <span class="method-tag">PARAMETRIC</span>
          <h3>Linear regression</h3>
          <dl>
            <div>
              <dt>Slope / observation</dt>
              <dd>${reg.slope.toFixed(5)}</dd>
            </div>
            <div>
              <dt>R²</dt>
              <dd>${reg.rSquared.toFixed(3)}</dd>
            </div>
            <div>
              <dt>p-value</dt>
              <dd>${Number(reg.pValue).toPrecision(3)}</dd>
            </div>
            <div>
              <dt>95% confidence interval</dt>
              <dd>${reg.confidenceInterval.map((v) => Number(v).toFixed(5)).join(' to ')}</dd>
            </div>
          </dl>
        </article>
        <article class="analysis-card">
          <span class="method-tag cyan-tag">RANK-BASED</span>
          <h3>Mann–Kendall + Sen</h3>
          <dl>
            <div>
              <dt>Kendall’s tau</dt>
              <dd>${mk.tau.toFixed(3)}</dd>
            </div>
            <div>
              <dt>Z statistic</dt>
              <dd>${mk.z.toFixed(3)}</dd>
            </div>
            <div>
              <dt>p-value</dt>
              <dd>${Number(mk.pValue).toPrecision(3)}</dd>
            </div>
            <div>
              <dt>Sen slope / decade</dt>
              <dd>${result.analysis.senPerDecade.toFixed(3)} ${escapeHtml(definition.unit)}</dd>
            </div>
          </dl>
        </article>
      </div>
      <div class="${isSignificant ? 'verdict significant' : 'verdict'}">
        ${icon('circle-check', { size: 25 })}
        <div>
          <span>Scientific verdict · α = ${alphaNum}</span>
          <h3>${escapeHtml(result.analysis.verdict)}</h3>
          <p>
            A p-value below ${alphaNum} is evidence against a no-trend null hypothesis. A
            non-significant result is not proof that no change exists.
          </p>
        </div>
      </div>
      <div class="provenance">
        <h3>Data provenance</h3>
        <div>${provenanceItems}</div>
        <aside>
          ${icon('triangle-alert', { size: 16 })} Monthly observations can be autocorrelated, making
          conventional p-values too optimistic. Statistical significance does not establish
          causation.
        </aside>
      </div>
    `

    resultsPanel.querySelector('[data-action="download-csv"]')?.addEventListener('click', downloadCsv)
    resultsPanel.querySelector('[data-action="download-png"]')?.addEventListener('click', downloadPng)
    resultsPanel.querySelector('[data-action="download-json"]')?.addEventListener('click', downloadJson)

    const canvas = resultsPanel.querySelector('#trend-canvas')
    if (canvas) {
      activeChart = createTrendChart(canvas, {
        points: result.points,
        fitted: reg.fitted,
        unit: definition.unit,
      })
    }
  }

  async function investigate() {
    state.loading = true
    state.error = ''
    state.result = null
    updateLaunchButton()
    renderResults()

    try {
      const payload = await fetchAnalysis({
        parameter: state.parameter,
        latitude: state.latitude,
        longitude: state.longitude,
        start: state.start,
        end: state.end,
        mode: state.mode,
        alpha: state.alpha,
        horizon: state.horizon,
      })
      state.result = payload
    } catch (caught) {
      state.error = caught instanceof Error ? caught.message : 'Investigation failed.'
    } finally {
      state.loading = false
      updateLaunchButton()
      renderResults()
    }
  }

  launchBtn?.addEventListener('click', investigate)
  renderResults()

  if (state.autostart) {
    investigate()
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountExplorer)
} else {
  mountExplorer()
}
