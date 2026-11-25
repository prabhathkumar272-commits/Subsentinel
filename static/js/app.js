/**
 * SubSentinel — app.js
 * Client-side utilities: count-up, CSRF, toast manager, dark mode, HTMX hooks
 */

'use strict';

/* ----------------------------------------------------------
   1. Count-Up Animation
   ---------------------------------------------------------- */

/**
 * Animates a numeric element from 0 to its [data-countup] value.
 * @param {string|Element} selector - CSS selector or DOM element
 * @param {number} [duration=1200] - animation duration in ms
 */
function initCountUp(selector, duration = 1200) {
  const elements = typeof selector === 'string'
    ? document.querySelectorAll(selector)
    : [selector];

  elements.forEach((el) => {
    if (!el || el.dataset.countupDone) return;

    const target = parseFloat(el.dataset.countup);
    if (isNaN(target)) return;

    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const decimals = el.dataset.decimals !== undefined
      ? parseInt(el.dataset.decimals, 10)
      : (target % 1 !== 0 ? 2 : 0);

    const start = performance.now();

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = eased * target;

      el.textContent = prefix + current.toFixed(decimals) + suffix;

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = prefix + target.toFixed(decimals) + suffix;
        el.dataset.countupDone = 'true';
      }
    }

    requestAnimationFrame(update);
  });
}

/* ----------------------------------------------------------
   2. CSRF Cookie Helper
   ---------------------------------------------------------- */

/**
 * Reads the value of a cookie by name.
 * @param {string} name - cookie name, e.g. 'csrftoken'
 * @returns {string|null}
 */
function getCookie(name) {
  if (!document.cookie) return null;
  const match = document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(name + '='));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

/* ----------------------------------------------------------
   3. Toast Manager
   ---------------------------------------------------------- */

const ToastManager = (() => {
  let container = null;

  function getContainer() {
    if (!container) {
      container = document.getElementById('toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
      }
    }
    return container;
  }

  const ICONS = {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    'ℹ️',
  };

  /**
   * Display a toast notification.
   * @param {string} message - Main message text
   * @param {'success'|'error'|'warning'|'info'} [type='info'] - Toast variant
   * @param {object} [options]
   * @param {string} [options.title] - Optional bold title above message
   * @param {number} [options.duration=5000] - Auto-dismiss delay in ms (0 = no auto-dismiss)
   */
  function showToast(message, type = 'info', options = {}) {
    const { title, duration = 5000 } = options;
    const c = getContainer();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} relative`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    toast.innerHTML = `
      <span class="toast-icon" aria-hidden="true">${ICONS[type] || ICONS.info}</span>
      <div class="toast-content">
        ${title ? `<div class="toast-title">${title}</div>` : ''}
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close notification" onclick="this.closest('.toast').remove()">×</button>
      ${duration > 0 ? `<div class="toast-progress" style="width:100%;transition-duration:${duration}ms"></div>` : ''}
    `;

    c.appendChild(toast);

    // Animate the progress bar to 0 width to signal remaining time
    if (duration > 0) {
      const bar = toast.querySelector('.toast-progress');
      if (bar) {
        // Trigger reflow so the transition starts properly
        void bar.offsetWidth;
        bar.style.width = '0%';
      }
    }

    if (duration > 0) {
      setTimeout(() => dismissToast(toast), duration);
    }

    return toast;
  }

  function dismissToast(toast) {
    if (!toast || !toast.parentNode) return;
    toast.classList.add('toast-hiding');
    setTimeout(() => toast.remove(), 350);
  }

  return { showToast, dismissToast };
})();

// Global shorthand
function showToast(message, type, options) {
  return ToastManager.showToast(message, type, options);
}

/* ----------------------------------------------------------
   4. HTMX Integration
   ---------------------------------------------------------- */

// Re-initialize count-up after HTMX swaps in new content
document.addEventListener('htmx:afterSettle', (event) => {
  const target = event.detail.elt;
  if (target) {
    // Re-run count-up on newly settled elements
    target.querySelectorAll('[data-countup]:not([data-countup-done])').forEach((el) => {
      initCountUp(el);
    });
  }
});

// Forward HTMX request errors to toast
document.addEventListener('htmx:responseError', (event) => {
  const status = event.detail.xhr.status;
  if (status >= 500) {
    showToast('Something went wrong. Please try again.', 'error', { title: 'Server Error' });
  } else if (status === 403) {
    showToast('Your session may have expired. Please refresh.', 'warning', { title: 'Session Issue' });
  }
});

// HTMX CSRF header injection
document.addEventListener('htmx:configRequest', (event) => {
  const token = getCookie('csrftoken');
  if (token) {
    event.detail.headers['X-CSRFToken'] = token;
  }
});

/* ----------------------------------------------------------
   5. Dark Mode
   ---------------------------------------------------------- */

const DarkMode = (() => {
  const STORAGE_KEY = 'subsentinel-dark-mode';
  const html = document.documentElement;

  function isDark() {
    return html.classList.contains('dark');
  }

  function setDark(value) {
    html.classList.toggle('dark', value);
    try { localStorage.setItem(STORAGE_KEY, value ? '1' : '0'); } catch (_) {}
    // Dispatch event for Alpine or other listeners
    document.dispatchEvent(new CustomEvent('darkmode:change', { detail: { dark: value } }));
  }

  function toggle() {
    setDark(!isDark());
  }

  function init() {
    // 1. Respect stored preference
    let stored;
    try { stored = localStorage.getItem(STORAGE_KEY); } catch (_) {}

    if (stored !== null) {
      setDark(stored === '1');
    } else {
      // 2. Fall back to OS preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDark(prefersDark);
    }

    // Listen to OS preference changes (only when no stored preference)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      let pref;
      try { pref = localStorage.getItem(STORAGE_KEY); } catch (_) {}
      if (pref === null) setDark(e.matches);
    });
  }

  return { init, toggle, setDark, isDark };
})();

/* ----------------------------------------------------------
   6. DOMContentLoaded — Bootstrap
   ---------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  // Dark mode
  DarkMode.init();

  // Wire up any dark-mode toggle buttons
  document.querySelectorAll('[data-dark-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => DarkMode.toggle());
  });

  // Count-up for all elements with data-countup
  initCountUp('[data-countup]');

  // Auto-dismiss any server-rendered flash messages
  document.querySelectorAll('[data-flash-message]').forEach((el) => {
    const type = el.dataset.flashType || 'info';
    const msg  = el.dataset.flashMessage;
    if (msg) {
      showToast(msg, type);
      el.remove();
    }
  });
});

/* ----------------------------------------------------------
   7. Expose globals for inline usage & Alpine.js
   ---------------------------------------------------------- */

window.SubSentinel = {
  initCountUp,
  getCookie,
  showToast,
  ToastManager,
  DarkMode,
};
