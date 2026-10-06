import { CONFIG } from '../../config/app.js';
import { t } from '../../core/i18n.js';

// Camera QR scanning through the html5-qrcode library (loaded on demand from a CDN).
// The desk always keeps a manual code field, so a missing camera or library never blocks pickup.
let libPromise = null;

function loadLibrary() {
  if (window.Html5Qrcode) return Promise.resolve(window.Html5Qrcode);
  if (!libPromise) {
    libPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = CONFIG.cdn.qrScannerJs;
      script.onload = () => resolve(window.Html5Qrcode);
      script.onerror = () => { libPromise = null; reject(new Error(t('desk.scanner.unavailable'))); };
      document.head.append(script);
    });
  }
  return libPromise;
}

let counter = 0;

/** Starts scanning inside `container`. Resolves to { stop() }. `onCode(text)` fires once per decoded code. */
export async function startScanner(container, onCode) {
  const Html5Qrcode = await loadLibrary();
  container.id = container.id || `scanner-${++counter}`;
  const scanner = new Html5Qrcode(container.id);
  try {
    await scanner.start({ facingMode: 'environment' }, { fps: 10, qrbox: 240 }, (text) => onCode(text), () => {});
  } catch {
    throw new Error(t('desk.scanner.denied'));
  }
  return {
    async stop() {
      try { await scanner.stop(); scanner.clear(); } catch { /* already stopped */ }
    },
  };
}
