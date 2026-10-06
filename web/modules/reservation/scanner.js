import { CONFIG } from '../../config/app.js';
import { t } from '../../core/i18n.js';

// Camera QR scanning through the html5-qrcode library (loaded on demand from a CDN).
// The desk always keeps a manual code field, so a missing camera or library never blocks pickup.
// Kütüphane bir kez yüklenir.
let libPromise = null;

// html5-qrcode betiğini ihtiyaç anında yükler (tembel yükleme); yalnızca teslim masasında gerekir.
function loadLibrary() {
  // Zaten yüklüyse tekrar indirme.
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

// Her tarayıcı elemanına benzersiz bir id vermek için.
let counter = 0;

/** Starts scanning inside `container`. Resolves to { stop() }. `onCode(text)` fires once per decoded code. */
// Kamerayı açıp QR okumaya başlar. `onCode` her okunan metinde çağrılır.
export async function startScanner(container, onCode) {
  const Html5Qrcode = await loadLibrary();
  // Kütüphane eleman kimliği (id) ister.
  container.id = container.id || `scanner-${++counter}`;
  const scanner = new Html5Qrcode(container.id);
  try {
    // facingMode: 'environment' = arka kamera. İzin reddedilirse hata fırlar.
    await scanner.start({ facingMode: 'environment' }, { fps: 10, qrbox: 240 }, (text) => onCode(text), () => {});
  } catch {
    throw new Error(t('desk.scanner.denied'));
  }
  return {
    // Akışı durdurur ve ekranı temizler; zaten durmuşsa hata yutulur.
    async stop() {
      try { await scanner.stop(); scanner.clear(); } catch { /* already stopped */ }
    },
  };
}
