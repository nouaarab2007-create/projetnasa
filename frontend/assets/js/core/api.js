/**
 * REST API client for the Trend Detective FastAPI backend.
 *
 * All endpoints live under `/api/*` and return JSON. Errors are normalized
 * into standard `Error` instances carrying the backend's `error` message.
 */

let catalogCache = null

async function requestJson(url, options = {}, fallbackError = 'Request failed.') {
  const response = await fetch(url, options)
  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (!response.ok) {
    throw new Error((payload && payload.error) || fallbackError)
  }
  return payload
}

/**
 * Fetch the scientific catalogue (`/api/variables`, `/api/regions`, `/api/sources`)
 * once per page load and cache it in memory.
 */
export async function fetchCatalog() {
  if (!catalogCache) {
    catalogCache = Promise.all([
      requestJson('/api/variables', {}, 'Unable to load variables.'),
      requestJson('/api/regions', {}, 'Unable to load regions.'),
      requestJson('/api/sources', {}, 'Unable to load sources.'),
    ]).then(([varsPayload, regionsPayload, sourcesPayload]) => ({
      variables: varsPayload.variables ?? [],
      regions: regionsPayload.regions ?? [],
      regionNote: regionsPayload.note ?? '',
      sources: sourcesPayload.sources ?? [],
    }))
  }
  return catalogCache
}

/**
 * Run a single-region statistical trend investigation (`GET /api/analysis`).
 */
export async function fetchAnalysis({ parameter, latitude, longitude, start, end, mode, alpha, horizon }) {
  const params = {
    parameter: String(parameter),
    latitude: String(latitude),
    longitude: String(longitude),
    start: String(start),
    end: String(end),
    mode: String(mode),
  }
  if (alpha !== undefined) params.alpha = String(alpha)
  if (horizon !== undefined) params.horizon = String(horizon)
  const query = new URLSearchParams(params)
  return requestJson(`/api/analysis?${query}`, {}, 'Investigation failed.')
}

/**
 * Run a two-region comparison (`POST /api/comparison`).
 */
export async function fetchComparison({ parameter, start, end, mode, regionA, regionB }) {
  return requestJson(
    '/api/comparison',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parameter, start, end, mode, regionA, regionB }),
    },
    'Comparison failed.',
  )
}

/**
 * Geocode a place query through the backend Nominatim proxy (`GET /api/geocode`).
 */
export async function fetchGeocode(query) {
  return requestJson(
    `/api/geocode?q=${encodeURIComponent(query)}`,
    {},
    'Place search failed.',
  )
}
