# Recon — Website Integration & Embedding Guide

This guide explains how to embed the **Recon Integration Readiness Engine** directly into your SaaS platform, developer portal, documentation site, or internal operations dashboard.

---

## 1. Quickest Method: Drop-in Embed Script (1 Line of HTML)

Add this single `<script>` tag before the closing `</body>` tag on any HTML page:

```html
<script src="https://integrate.yourdomain.com/embed.js"
        data-recon-url="https://integrate.yourdomain.com"
        data-theme="auto"
        data-position="bottom-right"
        data-btn-text="Integration Readiness">
</script>
```

### What this does automatically:
1. Injects a high-tech floating launcher pill (`[⚡ Integration Readiness // ENGINE]`) with Apple/Linear grade micro-interactions.
2. Clicking the launcher opens a full-screen blurred backdrop modal running Recon.
3. Automatically respects the user's OS dark/light mode preference.
4. Supports pressing <kbd>Esc</kbd> to close.

### Configuration Attributes

| Attribute | Default | Options | Description |
| :--- | :--- | :--- | :--- |
| `data-recon-url` | Script origin | Any valid URL | Base URL where your Recon instance is hosted |
| `data-theme` | `auto` | `auto`, `dark`, `light` | Theme calibration for the console |
| `data-position` | `bottom-right` | `bottom-right`, `bottom-left` | Screen placement of floating launcher |
| `data-btn-text` | `Integration Readiness`| Custom text string | Label rendered on the launcher button |
| `data-auto-open` | `false` | Presence attribute | Automatically open modal on initial page load |

---

## 2. Programmatic JavaScript API

Once `embed.js` is loaded on your page, you can open and close the Recon modal programmatically from your own custom buttons or workflows:

```javascript
// Open Recon modal with dark theme
window.ReconEmbed.open({ theme: 'dark' });

// Open Recon modal with light theme
window.ReconEmbed.open({ theme: 'light' });

// Close Recon modal
window.ReconEmbed.close();
```

### Example: Custom Navigation Bar Link

```html
<button class="nav-btn" onclick="window.ReconEmbed.open()">
  Verify Integration Schema
</button>
```

---

## 3. React & Next.js Component Wrapper

For React (Next.js App Router or Pages Router, Vite, Create React App), create a reusable `<ReconReadinessModal />` component:

```tsx
// components/ReconReadinessModal.tsx
'use client';

import React, { useState, useEffect } from 'react';

interface ReconModalProps {
  reconUrl?: string;
  theme?: 'dark' | 'light' | 'auto';
  isOpen: boolean;
  onClose: () => void;
}

export const ReconReadinessModal: React.FC<ReconModalProps> = ({
  reconUrl = 'https://integrate.yourdomain.com',
  theme = 'auto',
  isOpen,
  onClose,
}) => {
  useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const url = `${reconUrl}?embed=true&theme=${theme}`;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 999999,
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1360px',
          height: '92vh',
          background: '#0B0E14',
          border: '1px solid rgba(255, 255, 255, 0.14)',
          borderRadius: '14px',
          overflow: 'hidden',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8)',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            height: '42px',
            background: '#070A10',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 16px',
            color: '#94A3B8',
            fontSize: '12px',
          }}
        >
          <span style={{ fontWeight: 600, color: '#F8FAFC' }}>
            RECON // The Integration Readiness Engine
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94A3B8',
              fontSize: '20px',
              cursor: 'pointer',
            }}
          >
            &times;
          </button>
        </div>
        <iframe
          src={url}
          style={{ width: '100%', flex: 1, border: 'none' }}
          title="Recon Integration Cockpit"
        />
      </div>
    </div>
  );
};
```

---

## 4. Full Inline Dashboard Embed (iFrame)

To embed Recon directly as a tab or panel within your administrative dashboard:

```html
<div class="dashboard-panel" style="width: 100%; height: 850px; border-radius: 12px; overflow: hidden; border: 1px solid #1E293B;">
  <iframe
    src="https://integrate.yourdomain.com?embed=true&theme=dark"
    style="width: 100%; height: 100%; border: none;"
    title="Recon Integration Cockpit"
    allow="clipboard-write">
  </iframe>
</div>
```

---

## 5. Security & CSP (Content Security Policy)

When embedding across domains:
1. Ensure your reverse proxy (e.g. Nginx, Cloudflare) sets the proper `Content-Security-Policy`:
   ```http
   Content-Security-Policy: frame-ancestors 'self' https://yourdomain.com https://*.yourdomain.com;
   ```
2. Grant `allow="clipboard-write"` to enable the 1-click **Copy Adapter** feature in Screen 05.

---

## 6. Self-Hosting with Docker

Recon includes a production-ready `Dockerfile` and `docker-compose.yml`.

### Quick Start:
```bash
# Clone and run
docker compose up -d

# Verify service is running
curl http://localhost:8000/api/health
```
Your Recon instance is now accessible at `http://localhost:8000`.
