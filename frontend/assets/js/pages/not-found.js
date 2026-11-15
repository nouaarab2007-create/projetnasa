/**
 * 404 Not Found page controller.
 */

import { initLayout } from '../components/layout.js'

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLayout)
} else {
  initLayout()
}
