/**
 * Region explorer controller (`/regions`).
 * Faithful Vanilla JS port of `src/components/RegionMap.tsx`.
 */

import { initLayout } from '../components/layout.js'
import { fetchCatalog, fetchGeocode } from '../core/api.js'
import { escapeHtml } from '../core/dom.js'
import { icon } from '../core/icons.js'

async function mountRegions() {
  initLayout()

  const root = document.getElementById('regions-root')
  if (!root) return

  let regions = []
  try {
    const catalog = await fetchCatalog()
    regions = catalog.regions
  } catch (err) {
    root.innerHTML = `<div class="error-banner">${escapeHtml(err instanceof Error ? err.message : 'Unable to load regions.')}</div>`
    return
  }

  let latitude = 13.5
  let longitude = 2.1
  let place = 'Sahel / Niger'
  let searching = false
  let map = null
  let marker = null

  root.className = 'map-explorer'
  root.innerHTML = `
    <div class="map-sidebar">
      <div class="map-search">
        ${icon('search', { size: 17 })}
        <input type="text" id="place-query" placeholder="Search a city or place" />
        <button type="button" id="place-search-btn">Go</button>
      </div>
      <h3>Scientific regions</h3>
      <div class="region-list" id="region-list"></div>
    </div>
    <div class="map-stage">
      <div id="leaflet-map" class="leaflet-map"></div>
      <div class="coordinate-card">
        <span>Selected grid point</span>
        <strong id="selected-place">${escapeHtml(place)}</strong>
        <div>
          <label>
            Latitude
            <input type="number" id="coord-lat" min="-90" max="90" step=".01" value="${latitude}" />
          </label>
          <label>
            Longitude
            <input type="number" id="coord-lon" min="-180" max="180" step=".01" value="${longitude}" />
          </label>
          <button type="button" id="coord-update-btn">Update</button>
        </div>
        <p>
          NASA POWER reports the grid cell containing this point, not an exact measurement at the
          marker.
          <a href="/explorer?latitude=${latitude}&longitude=${longitude}" id="investigate-point-link" class="text-link" style="margin-left: 8px;">
            Investigate point &rarr;
          </a>
        </p>
      </div>
    </div>
  `

  const regionListEl = root.querySelector('#region-list')
  const placeLabel = root.querySelector('#selected-place')
  const latInput = root.querySelector('#coord-lat')
  const lonInput = root.querySelector('#coord-lon')
  const updateBtn = root.querySelector('#coord-update-btn')
  const queryInput = root.querySelector('#place-query')
  const searchBtn = root.querySelector('#place-search-btn')
  const investigateLink = root.querySelector('#investigate-point-link')
  const mapContainer = root.querySelector('#leaflet-map')

  function updateCoordinateUI() {
    if (placeLabel) placeLabel.textContent = place
    if (latInput) latInput.value = String(latitude)
    if (lonInput) lonInput.value = String(longitude)
    if (investigateLink) {
      investigateLink.setAttribute('href', `/explorer?latitude=${latitude}&longitude=${longitude}`)
    }
    renderRegionList()
  }

  function selectPoint(lat, lng, name = 'Custom point') {
    latitude = Number(Number(lat).toFixed(4))
    longitude = Number(Number(lng).toFixed(4))
    place = name
    updateCoordinateUI()
    if (map && marker) {
      map.flyTo([latitude, longitude], 5, { duration: 1.2 })
      marker.setLatLng([latitude, longitude])
    }
  }

  function renderRegionList() {
    if (!regionListEl) return
    regionListEl.innerHTML = regions
      .map(
        (region) => `
          <button
            type="button"
            data-region-id="${escapeHtml(region.id)}"
            class="${place === region.name ? 'active' : ''}"
          >
            <span>${icon('crosshair', { size: 15 })}</span>
            <div>
              <strong>${escapeHtml(region.name)}</strong>
              <small>${escapeHtml(region.biome)} · ${region.latitude}, ${region.longitude}</small>
            </div>
          </button>
        `,
      )
      .join('')

    regionListEl.querySelectorAll('button[data-region-id]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-region-id')
        const found = regions.find((r) => r.id === id)
        if (found) {
          selectPoint(found.latitude, found.longitude, found.name)
        }
      })
    })
  }

  async function runSearch() {
    const q = queryInput?.value?.trim()
    if (!q || searching) return
    searching = true
    if (searchBtn) searchBtn.textContent = '…'
    try {
      const payload = await fetchGeocode(q)
      if (payload?.results?.[0]) {
        const hit = payload.results[0]
        selectPoint(Number(hit.lat), Number(hit.lon), hit.display_name)
      }
    } catch {
      // Keep current selection if geocoding fails
    } finally {
      searching = false
      if (searchBtn) searchBtn.textContent = 'Go'
    }
  }

  searchBtn?.addEventListener('click', runSearch)
  queryInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runSearch()
  })

  updateBtn?.addEventListener('click', () => {
    const nextLat = Number(latInput?.value ?? latitude)
    const nextLon = Number(lonInput?.value ?? longitude)
    if (!Number.isNaN(nextLat) && !Number.isNaN(nextLon)) {
      selectPoint(Math.max(-90, Math.min(90, nextLat)), Math.max(-180, Math.min(180, nextLon)), 'Custom point')
    }
  })

  renderRegionList()

  if (window.L && mapContainer) {
    const L = window.L
    L.Icon.Default.imagePath = '/assets/vendor/leaflet/images/'
    map = L.map(mapContainer, { zoomControl: false, worldCopyJump: true }).setView([latitude, longitude], 2)
    L.tileLayer('/api/tiles/{z}/{x}/{y}', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map)
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    marker = L.marker([latitude, longitude]).addTo(map)
    map.on('click', (event) => {
      const lat = Number(event.latlng.lat.toFixed(4))
      const lng = Number(event.latlng.lng.toFixed(4))
      marker.setLatLng([lat, lng])
      latitude = lat
      longitude = lng
      place = 'Custom point'
      updateCoordinateUI()
    })
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountRegions)
} else {
  mountRegions()
}
