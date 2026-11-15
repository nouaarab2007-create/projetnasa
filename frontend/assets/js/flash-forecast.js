/**
 * Flash-drought AI early warning (trained LightGBM + SHAP model).
 *
 * Standalone script loaded after app.bundle.js on the Explorer / Analysis pages.
 * It adds a card at the top of the results panel showing, for the chosen place, the
 * probability that a flash drought STARTS within the next 7, 14 and 30 days
 * (GET /api/flash-forecast), plus the main SHAP drivers. It re-runs whenever the
 * latitude / longitude changes and survives the panel being re-rendered.
 */
;(function () {
  'use strict'

  var CARD_ID = 'ml-forecast-card'
  var HORIZONS = [7, 14, 30]
  var LEVEL_COLORS = { LOW: '#2e7d32', MODERATE: '#F28C28', HIGH: '#FC3D21', CRITICAL: '#a30000' }

  var st = { key: '', loading: false, error: '', data: null, horizon: 14, run: 0 }
  var timer = null

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    })
  }

  function injectStyles() {
    if (document.getElementById('ml-forecast-style')) return
    var css =
      '#' + CARD_ID + '{border:1px solid var(--line-bright,#0B3D91);border-radius:14px;padding:18px 20px;margin-bottom:18px;background:var(--panel,#fff);color:var(--text,#061F4A);box-shadow:var(--shadow,none)}' +
      '#' + CARD_ID + ' h2{margin:2px 0 4px;font-size:1.15rem}' +
      '#' + CARD_ID + ' .mlf-eyebrow{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted,#3d5680);font-weight:700}' +
      '#' + CARD_ID + ' .mlf-sub{margin:0 0 12px;color:var(--muted,#3d5680);font-size:.88rem}' +
      '#' + CARD_ID + ' .mlf-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:12px}' +
      '#' + CARD_ID + ' .mlf-tab{cursor:pointer;text-align:left;border:1px solid var(--line,#ccd);border-radius:12px;padding:10px 12px;background:transparent;color:inherit;font:inherit}' +
      '#' + CARD_ID + ' .mlf-tab.is-active{border-color:var(--line-bright,#0B3D91);box-shadow:inset 0 0 0 1px var(--line-bright,#0B3D91)}' +
      '#' + CARD_ID + ' .mlf-tab small{display:block;color:var(--muted,#3d5680)}' +
      '#' + CARD_ID + ' .mlf-tab strong{display:block;font-size:1.6rem;line-height:1.2}' +
      '#' + CARD_ID + ' .mlf-tag{display:inline-block;font-size:.7rem;font-weight:700;border:1px solid currentColor;border-radius:99px;padding:1px 8px}' +
      '#' + CARD_ID + ' ul{margin:8px 0 0;padding-left:18px}' +
      '#' + CARD_ID + ' li{margin:4px 0;font-size:.88rem}' +
      '#' + CARD_ID + ' .mlf-note{margin:10px 0 0;font-size:.78rem;color:var(--muted,#3d5680)}' +
      '#' + CARD_ID + ' .mlf-state{margin:6px 0;font-size:.92rem}' +
      '#' + CARD_ID + ' .mlf-warn{color:#b45f06}' +
      '.step-tag{display:inline-block;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;font-weight:700;color:var(--cyan,#0B3D91)}' +
      '.step-lead{margin:4px 0 0;color:var(--muted,#3d5680);font-size:.95rem}' +
      '.step-verdict{border:1px solid var(--line,#ccd);border-left:4px solid #F28C28;border-radius:12px;padding:14px 18px;background:var(--panel,#fff)}' +
      '.step-verdict.is-sig{border-left-color:#FC3D21}' +
      '.step-verdict h3{margin:4px 0}.step-verdict p{margin:0;color:var(--muted,#3d5680);font-size:.9rem}'
    var el = document.createElement('style')
    el.id = 'ml-forecast-style'
    el.textContent = css
    document.head.appendChild(el)
  }

  function readCoords() {
    var lat = document.querySelector('#explorer-root [data-field="latitude"]')
    var lon = document.querySelector('#explorer-root [data-field="longitude"]')
    if (!lat || !lon) return null
    var la = Number(lat.value)
    var lo = Number(lon.value)
    if (lat.value === '' || lon.value === '' || !isFinite(la) || !isFinite(lo)) return null
    if (la < -90 || la > 90 || lo < -180 || lo > 180) return null
    return { lat: Math.round(la * 100) / 100, lon: Math.round(lo * 100) / 100 }
  }

  function bases() {
    return window.location.protocol === 'file:' ? ['http://127.0.0.1:8000'] : ['', 'http://127.0.0.1:8000']
  }

  async function fetchForecast(c) {
    var q = new URLSearchParams({ latitude: String(c.lat), longitude: String(c.lon) })
    var lastError = null
    var list = bases()
    for (var i = 0; i < list.length; i++) {
      try {
        var res = await fetch(list[i] + '/api/flash-forecast?' + q)
        var data = await res.json()
        if (res.ok) return data
        lastError = new Error((data && data.error) || 'Forecast failed.')
        break
      } catch (err) {
        lastError = err
      }
    }
    if (lastError && /fetch|network|load failed/i.test(String(lastError.message))) {
      throw new Error('The backend is not reachable. Start it with: python -m uvicorn app.main:app --app-dir backend --port 8000, then open http://127.0.0.1:8000/explorer')
    }
    throw lastError || new Error('Forecast failed.')
  }

  function levelColor(level) {
    return LEVEL_COLORS[String(level || '').toUpperCase()] || '#0B3D91'
  }

  function tabHtml(h) {
    var f = st.data && st.data.forecasts && st.data.forecasts['H' + h]
    var active = h === st.horizon ? ' is-active' : ''
    var body
    if (st.loading) body = '<strong>…</strong><small>computing</small>'
    else if (f && f.status === 'ok') {
      body =
        '<strong style="color:' + levelColor(f.risk_level) + '">' + esc(f.risk_percentage) + '%</strong>' +
        '<span class="mlf-tag" style="color:' + levelColor(f.risk_level) + '">' + esc(f.risk_level) + '</span>'
    } else body = '<strong>–</strong><small>n/a</small>'
    return '<button type="button" class="mlf-tab' + active + '" data-h="' + h + '"><small>next ' + h + ' days</small>' + body + '</button>'
  }

  function detailHtml() {
    if (st.loading) return '<p class="mlf-state">Pulling the latest NASA POWER days and running the model…</p>'
    if (st.error) return '<p class="mlf-state mlf-warn">' + esc(st.error) + '</p>'
    var f = st.data && st.data.forecasts && st.data.forecasts['H' + st.horizon]
    if (!f) return ''
    if (f.status !== 'ok') {
      return '<p class="mlf-state mlf-warn">' + esc(f.why || f.status || 'Forecast unavailable for this place/date.') + '</p>'
    }
    var html = '<p class="mlf-state"><strong>' + esc(f.risk_percentage) + '%</strong> chance that a flash drought starts in the next ' +
      esc(f.horizon_days) + ' days (date of data: ' + esc(f.date) + '), i.e. <strong>' + esc(f.risk_ratio_vs_usual) +
      '×</strong> the usual rate of ' + esc(f.usual_percentage) + '%.</p>'
    if (/ALREADY_DRY/.test(f.state || '')) {
      html += '<p class="mlf-state mlf-warn">Soil is already at or below the 15th percentile: this place is already dry, so an <em>onset</em> risk is less meaningful.</p>'
    }
    var drivers = f.top_drivers || []
    if (drivers.length) {
      html += '<strong>Main risk drivers (SHAP)</strong><ul>' + drivers.map(function (d) {
        return '<li><strong>' + esc(String(d.feature).replace(/_/g, ' ')) + '</strong> (' + esc(d.impact_score) + ') — ' + esc(d.reason) + '</li>'
      }).join('') + '</ul>'
    }
    var relief = (f.relief_factors || [])[0]
    if (relief) html += '<p class="mlf-note">Lowering the risk: ' + esc(relief.reason) + '</p>'
    return html
  }

  function cardInner() {
    return '<span class="mlf-eyebrow">Bonus · AI prediction (trained model)</span>' +
      '<h2>Flash drought onset risk — next 7, 14 and 30 days</h2>' +
      '<p class="mlf-sub">LightGBM model trained on NASA POWER daily data (2005–2024), explained with SHAP.</p>' +
      '<div class="mlf-tabs">' + HORIZONS.map(tabHtml).join('') + '</div>' +
      detailHtml() +
      '<p class="mlf-note">' + esc((st.data && st.data.note) || 'Statistical association from past data, not a weather forecast.') + '</p>'
  }

  function paint() {
    var card = document.getElementById(CARD_ID)
    if (card) card.innerHTML = cardInner()
  }

  function ensureCard() {
    var panel = document.getElementById('results-panel')
    if (!panel || document.getElementById(CARD_ID)) return
    var card = document.createElement('section')
    card.id = CARD_ID
    card.setAttribute('aria-live', 'polite')
    card.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.mlf-tab') : null
      if (!btn) return
      st.horizon = Number(btn.getAttribute('data-h'))
      paint()
    })
    panel.appendChild(card)
    card.innerHTML = cardInner()
  }

  async function refresh() {
    var c = readCoords()
    if (!c) return
    var key = c.lat + '|' + c.lon
    if (key === st.key) return
    st.key = key
    st.loading = true
    st.error = ''
    st.data = null
    var run = ++st.run
    paint()
    try {
      var data = await fetchForecast(c)
      if (run !== st.run) return
      st.data = data
    } catch (err) {
      if (run !== st.run) return
      st.error = err instanceof Error ? err.message : 'Forecast failed.'
    } finally {
      if (run === st.run) {
        st.loading = false
        paint()
      }
    }
  }

  function schedule() {
    clearTimeout(timer)
    timer = setTimeout(function () {
      ensureCard()
      refresh()
    }, 400)
  }

  function boot() {
    var root = document.getElementById('explorer-root')
    if (!root) return
    injectStyles()
    new MutationObserver(function () {
      if (!document.getElementById(CARD_ID)) ensureCard()
    }).observe(root, { childList: true, subtree: true })
    root.addEventListener('input', schedule)
    root.addEventListener('change', schedule)
    root.addEventListener('click', schedule)
    schedule()
    // the explorer builds its form asynchronously: retry a few times until coordinates exist
    var tries = 0
    var poll = setInterval(function () {
      tries += 1
      ensureCard()
      refresh()
      if (st.key || tries > 40) clearInterval(poll)
    }, 500)
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot)
  else boot()
})()
