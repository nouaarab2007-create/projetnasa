/**
 * Shared site layout: SiteHeader, SiteFooter and PageHero.
 * Faithful port of SiteHeader.tsx, SiteFooter.tsx and PageHero.tsx.
 */

import { escapeHtml } from '../core/dom.js'
import { icon } from '../core/icons.js'
import { initTheme, setTheme } from '../core/theme.js'
import { renderLogo } from './logo.js'

const NAV_LINKS = [
  ['/', 'Home'],
  ['/explorer', 'Investigate'],
  ['/variables', 'Variables'],
  ['/regions', 'Regions'],
  ['/comparison', 'Compare'],
  ['/sources', 'Sources'],
  ['/methodology', 'Science'],
  ['/about', 'About'],
]

function normalizePathname(pathname) {
  const cleaned = (pathname || '/').replace(/\.html$/, '')
  if (cleaned === '/index' || cleaned === '') return '/'
  return cleaned.length > 1 && cleaned.endsWith('/') ? cleaned.slice(0, -1) : cleaned
}

/**
 * Mount the sticky site header and wire navigation + theme toggle.
 * @param {HTMLElement | null} target
 */
export function mountHeader(target = document.getElementById('site-header')) {
  const lightInitial = initTheme()
  if (!target) return

  const currentPath = normalizePathname(window.location.pathname)
  let open = false
  let light = lightInitial

  target.className = 'site-header'
  target.innerHTML = `
    <a href="/" class="brand" aria-label="Trend Detective home">
      ${renderLogo('compact')}
    </a>
    <nav class="main-nav" aria-label="Main navigation">
      ${NAV_LINKS.map(
        ([href, label]) =>
          `<a href="${href}" class="${currentPath === href ? 'active' : ''}">${escapeHtml(label)}</a>`,
      ).join('')}
    </nav>
    <div class="header-actions">
      <span class="header-status" title="NASA POWER API connected">
        <span class="live-dot"></span>
        <span>NASA POWER</span>
      </span>
      <button
        type="button"
        class="icon-button theme-toggle-btn"
        data-role="theme-toggle"
        aria-pressed="${!light}"
        aria-label="${light ? 'Switch to dark theme' : 'Switch to light theme'}"
      >
        ${light ? `${icon('moon', { size: 15 })}<span>Dark</span>` : `${icon('sun', { size: 15 })}<span>Light</span>`}
      </button>
      <a href="/explorer" class="button primary header-cta">
        Investigate ${icon('arrow-right', { size: 14 })}
      </a>
      <button
        type="button"
        class="icon-button menu-button"
        data-role="menu-toggle"
        aria-label="Toggle navigation"
      >
        ${icon('menu', { size: 19 })}
      </button>
    </div>
  `

  const nav = target.querySelector('.main-nav')
  const themeBtn = target.querySelector('[data-role="theme-toggle"]')
  const menuBtn = target.querySelector('[data-role="menu-toggle"]')

  themeBtn?.addEventListener('click', () => {
    light = !light
    setTheme(light)
    themeBtn.setAttribute('aria-pressed', String(!light))
    themeBtn.setAttribute('aria-label', light ? 'Switch to dark theme' : 'Switch to light theme')
    themeBtn.innerHTML = light
      ? `${icon('moon', { size: 15 })}<span>Dark</span>`
      : `${icon('sun', { size: 15 })}<span>Light</span>`
  })

  menuBtn?.addEventListener('click', () => {
    open = !open
    nav?.classList.toggle('is-open', open)
    menuBtn.innerHTML = open ? icon('x', { size: 19 }) : icon('menu', { size: 19 })
  })

  nav?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      open = false
      nav.classList.remove('is-open')
      if (menuBtn) menuBtn.innerHTML = icon('menu', { size: 19 })
    })
  })
}

/**
 * Mount the shared site footer.
 * @param {HTMLElement | null} target
 */
export function mountFooter(target = document.getElementById('site-footer')) {
  if (!target) return
  target.className = 'site-footer'
  target.innerHTML = `
    <div class="footer-inner">
      <div class="footer-grid">
        <div class="footer-col-brand">
          <a href="/" class="brand" aria-label="Trend Detective home">
            ${renderLogo('compact')}
          </a>
          <p>
            Built for the NASA International Space Apps Challenge. An open, reproducible Earth
            science platform transforming satellite and reanalysis observations into transparent
            statistical evidence.
          </p>
          <div class="footer-badges">
            <span class="footer-badge"><span class="live-dot"></span> NASA POWER API · Live</span>
            <span class="footer-badge">${icon('shield-check', { size: 13 })} 0% Simulated Data</span>
          </div>
        </div>
        <div class="footer-col">
          <h4>Platform</h4>
          <div class="footer-links">
            <a href="/">Home Overview</a>
            <a href="/explorer">Investigation Workspace</a>
            <a href="/variables">Scientific Variables</a>
            <a href="/regions">Interactive Region Map</a>
            <a href="/comparison">Regional Comparison</a>
          </div>
        </div>
        <div class="footer-col">
          <h4>Science &amp; Rigor</h4>
          <div class="footer-links">
            <a href="/methodology">Statistical Methodology</a>
            <a href="/sources">Data Sources &amp; Missions</a>
            <a href="/about">About Trend Detective</a>
            <a href="/methodology">OLS &amp; Mann–Kendall</a>
            <a href="/methodology">5-Year Risk Screening</a>
          </div>
        </div>
        <div class="footer-col">
          <h4>Official Resources</h4>
          <div class="footer-links">
            <a href="https://power.larc.nasa.gov/" target="_blank" rel="noreferrer">
              NASA POWER Portal ${icon('arrow-up-right', { size: 13 })}
            </a>
            <a href="https://giovanni.gsfc.nasa.gov/giovanni/" target="_blank" rel="noreferrer">
              NASA Giovanni ${icon('arrow-up-right', { size: 13 })}
            </a>
            <a href="https://appeears.earthdatacloud.nasa.gov/" target="_blank" rel="noreferrer">
              NASA AppEEARS ${icon('arrow-up-right', { size: 13 })}
            </a>
            <a href="https://www.openstreetmap.org/" target="_blank" rel="noreferrer">
              OpenStreetMap ${icon('arrow-up-right', { size: 13 })}
            </a>
            <a href="https://www.spaceappschallenge.org/" target="_blank" rel="noreferrer">
              NASA Space Apps ${icon('arrow-up-right', { size: 13 })}
            </a>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>
          &copy; Trend Detective · NASA International Space Apps Challenge. Independent educational
          project; not an official NASA product.
        </p>
        <div class="footer-bottom-actions">
          <a href="/methodology">Methodology</a>
          <a href="/sources">Sources</a>
          <button type="button" class="footer-top-btn" data-action="scroll-top">
            Back to top &uarr;
          </button>
        </div>
      </div>
    </div>
  `
  target.querySelector('[data-action="scroll-top"]')?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

/**
 * Render a PageHero section (port of src/components/PageHero.tsx).
 */
export function renderPageHero({ eyebrow, title, description, extraHtml = '' }) {
  return `
    <section class="page-hero">
      <div>
        <span class="eyebrow">${escapeHtml(eyebrow)}</span>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(description)}</p>
      </div>
      ${extraHtml}
    </section>
  `
}

/**
 * Initialize header and footer on the current page.
 */
export function initLayout() {
  mountHeader()
  mountFooter()
}
