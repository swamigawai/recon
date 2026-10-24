/**
 * Recon — The Integration Readiness Engine
 * Drop-in Embeddable Web Widget & Modal SDK (embed.js)
 *
 * Usage:
 *   <script src="https://your-recon-host.com/embed.js"
 *           data-recon-url="https://your-recon-host.com"
 *           data-theme="auto"
 *           data-position="bottom-right"></script>
 */

(function () {
  'use strict';

  // Prevent multiple initializations
  if (window.__RECON_EMBED_INITIALIZED__) return;
  window.__RECON_EMBED_INITIALIZED__ = true;

  // Extract config from current script tag
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName('script');
    for (let i = scripts.length - 1; i >= 0; i--) {
      if (scripts[i].src && scripts[i].src.includes('embed.js')) return scripts[i];
    }
    return null;
  })();

  const scriptSrc = currentScript ? currentScript.src : '';
  const defaultHost = scriptSrc ? new URL(scriptSrc).origin : window.location.origin;

  const config = {
    url: (currentScript && currentScript.getAttribute('data-recon-url')) || defaultHost,
    theme: (currentScript && currentScript.getAttribute('data-theme')) || 'auto',
    position: (currentScript && currentScript.getAttribute('data-position')) || 'bottom-right',
    buttonText: (currentScript && currentScript.getAttribute('data-btn-text')) || 'Integration Readiness',
    autoOpen: currentScript && currentScript.hasAttribute('data-auto-open'),
  };

  // Resolve auto theme
  function getResolvedTheme() {
    if (config.theme === 'light') return 'light';
    if (config.theme === 'dark') return 'dark';
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
  }

  // Inject Styles
  const styleEl = document.createElement('style');
  styleEl.id = 'recon-embed-styles';
  styleEl.textContent = `
    .recon-launcher-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999990;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 18px;
      background: #0B0E14;
      color: #F8FAFC;
      border: 1px solid rgba(255, 255, 255, 0.16);
      border-radius: 9999px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 16px rgba(59, 130, 246, 0.35);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      user-select: none;
      transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .recon-launcher-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 16px 32px -4px rgba(0, 0, 0, 0.5), 0 0 24px rgba(59, 130, 246, 0.5);
      border-color: #3B82F6;
    }
    .recon-launcher-btn:active {
      transform: translateY(0);
    }
    .recon-launcher-btn.bottom-left {
      right: auto;
      left: 24px;
    }
    .recon-launcher-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      color: #38BDF8;
    }
    .recon-launcher-badge {
      background: rgba(59, 130, 246, 0.2);
      color: #60A5FA;
      border: 1px solid rgba(59, 130, 246, 0.3);
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 4px;
      font-weight: 700;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    .recon-modal-overlay {
      position: fixed;
      inset: 0;
      z-index: 999999;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.24s cubic-bezier(0.16, 1, 0.3, 1);
      padding: 20px;
      box-sizing: border-box;
    }
    .recon-modal-overlay.is-active {
      opacity: 1;
      pointer-events: auto;
    }
    .recon-modal-container {
      width: 100%;
      max-width: 1320px;
      height: 92vh;
      background: #090D16;
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 35px rgba(59, 130, 246, 0.25);
      display: flex;
      flex-direction: column;
      transform: scale(0.96) translateY(12px);
      transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .recon-modal-overlay.is-active .recon-modal-container {
      transform: scale(1) translateY(0);
    }
    .recon-modal-header {
      height: 44px;
      background: #070A10;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #94A3B8;
      font-size: 12px;
      user-select: none;
    }
    .recon-modal-close {
      background: none;
      border: none;
      color: #94A3B8;
      font-size: 18px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }
    .recon-modal-close:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #F8FAFC;
    }
    .recon-iframe {
      width: 100%;
      flex: 1;
      border: none;
      background: transparent;
    }
  `;
  document.head.appendChild(styleEl);

  // Create Launcher Button
  const btn = document.createElement('div');
  btn.className = `recon-launcher-btn ${config.position === 'bottom-left' ? 'bottom-left' : ''}`;
  btn.setAttribute('role', 'button');
  btn.setAttribute('tabindex', '0');
  btn.setAttribute('title', 'Open Recon Integration Readiness Engine');
  btn.innerHTML = `
    <span class="recon-launcher-icon">
      <svg width="18" height="18" viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="9" width="22" height="16" rx="4" stroke="currentColor" stroke-width="4" fill="none"/>
        <rect x="8" y="47" width="22" height="16" rx="4" stroke-width="4" fill="none"/>
        <rect x="90" y="9" width="22" height="16" rx="4" stroke-width="4" fill="none"/>
        <rect x="90" y="47" width="22" height="16" rx="4" stroke-width="4" fill="none"/>
        <path d="M 30 17 H 38 C 45 17 44 36 49 36" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
        <path d="M 30 55 H 38 C 45 55 44 36 49 36" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
        <path d="M 71 36 C 76 36 75 17 82 17 H 90" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
        <path d="M 71 36 C 76 36 75 55 82 55 H 90" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
        <rect x="49" y="24" width="22" height="24" rx="5" fill="#3B82F6"/>
        <path d="M 54 36.5 L 58.5 41 L 66 31.5" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
    <span>${config.buttonText}</span>
    <span class="recon-launcher-badge">ENGINE</span>
  `;

  // Create Modal Overlay
  const overlay = document.createElement('div');
  overlay.className = 'recon-modal-overlay';
  overlay.innerHTML = `
    <div class="recon-modal-container">
      <div class="recon-modal-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <strong style="color:#F8FAFC; letter-spacing:0.04em;">RECON</strong>
          <span>— The Integration Readiness Engine</span>
        </div>
        <button class="recon-modal-close" aria-label="Close Recon">&times;</button>
      </div>
      <iframe class="recon-iframe" title="Recon Integration Cockpit"></iframe>
    </div>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(overlay);

  const iframe = overlay.querySelector('iframe');
  const closeBtn = overlay.querySelector('.recon-modal-close');

  function openRecon(options) {
    const theme = (options && options.theme) || getResolvedTheme();
    const url = new URL(config.url);
    url.searchParams.set('embed', 'true');
    url.searchParams.set('theme', theme);

    if (iframe.src !== url.href) {
      iframe.src = url.href;
    }

    overlay.classList.add('is-active');
    document.body.style.overflow = 'hidden';
  }

  function closeRecon() {
    overlay.classList.remove('is-active');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', () => openRecon());
  btn.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openRecon();
    }
  });

  closeBtn.addEventListener('click', closeRecon);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeRecon();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('is-active')) {
      closeRecon();
    }
  });

  // Public Global API
  window.ReconEmbed = {
    open: openRecon,
    close: closeRecon,
    version: '1.0.0'
  };

  if (config.autoOpen) {
    setTimeout(openRecon, 300);
  }
})();
