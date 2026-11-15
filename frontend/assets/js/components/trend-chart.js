/**
 * TrendChart wrapper around Chart.js (port of src/components/TrendChart.tsx).
 *
 * Automatically adapts its colour palette when `<html data-theme="...">`
 * switches between light and dark themes via a MutationObserver.
 */

const PALETTES = {
  light: {
    observed: '#527c45',
    observedFill: 'rgba(82,124,69,.13)',
    trend: '#b07836',
    text: '#637060',
    title: '#203521',
    grid: 'rgba(53,88,45,.1)',
  },
  dark: {
    observed: '#8fbe62',
    observedFill: 'rgba(143,190,98,.12)',
    trend: '#d6a858',
    text: '#a2ae99',
    title: '#f1f7fb',
    grid: 'rgba(132,167,116,.09)',
  },
}

function getPalette() {
  return document.documentElement.dataset.theme === 'dark' ? PALETTES.dark : PALETTES.light
}

function buildConfig({ points, fitted, unit, title }, palette) {
  const datasets = [
    {
      label: 'Observed',
      data: points.map((point) => point.value),
      borderColor: palette.observed,
      backgroundColor: palette.observedFill,
      pointRadius: points.length > 80 ? 0 : 2,
      borderWidth: 2,
      tension: 0.15,
      fill: true,
    },
  ]
  if (Array.isArray(fitted)) {
    datasets.push({
      label: 'OLS trend',
      data: fitted,
      borderColor: palette.trend,
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderDash: [7, 6],
      borderWidth: 2,
    })
  }
  return {
    type: 'line',
    data: {
      labels: points.map((point) => point.date),
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: palette.text, usePointStyle: true } },
        title: { display: Boolean(title), text: title, color: palette.title },
      },
      scales: {
        x: {
          ticks: { color: palette.text, maxTicksLimit: 10 },
          grid: { color: palette.grid },
          title: { display: true, text: 'Time', color: palette.text },
        },
        y: {
          ticks: { color: palette.text },
          grid: { color: palette.grid },
          title: { display: true, text: unit, color: palette.text },
        },
      },
    },
  }
}

/**
 * Mount a Chart.js line chart inside `container` and return a controller with
 * `toBase64Image()` and `destroy()` methods.
 *
 * @param {HTMLElement} container
 * @param {{ points: {date: string, value: number}[], fitted?: number[], unit: string, title?: string }} params
 */
export function createTrendChart(container, params) {
  container.innerHTML = ''
  const canvas = document.createElement('canvas')
  container.appendChild(canvas)

  const ChartCtor = window.Chart
  if (!ChartCtor) {
    throw new Error('Chart.js is not loaded.')
  }

  const chart = new ChartCtor(canvas, buildConfig(params, getPalette()))

  const observer = new MutationObserver(() => {
    const palette = getPalette()
    if (chart.data.datasets[0]) {
      chart.data.datasets[0].borderColor = palette.observed
      chart.data.datasets[0].backgroundColor = palette.observedFill
    }
    if (chart.data.datasets[1]) {
      chart.data.datasets[1].borderColor = palette.trend
    }
    chart.options.plugins.legend.labels.color = palette.text
    chart.options.plugins.title.color = palette.title
    chart.options.scales.x.ticks.color = palette.text
    chart.options.scales.x.grid.color = palette.grid
    chart.options.scales.x.title.color = palette.text
    chart.options.scales.y.ticks.color = palette.text
    chart.options.scales.y.grid.color = palette.grid
    chart.options.scales.y.title.color = palette.text
    chart.update('none')
  })

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })

  return {
    chart,
    toBase64Image() {
      return chart.toBase64Image()
    },
    destroy() {
      observer.disconnect()
      chart.destroy()
    },
  }
}
