// Central front-end configuration. Nothing else in web/ hard-codes URLs, intervals or limits.
export const CONFIG = {
  // API'nin kök yolu; sürüm numarası (v1) yolun parçasıdır, ileride v2 yan yana çalışabilir.
  apiBase: '/api/v1',
  // Oturumun tarayıcıda saklandığı anahtar.
  storageKey: 'foodrescue.session',
  // Harita varsayılan merkezi (Sivas) [enlem, boylam].
  defaultCenter: [39.7477, 37.0179],
  defaultZoom: 12,
  // OpenStreetMap harita karoları: ücretsiz ve anahtarsız, ama yoğun kullanımda kullanım
  // politikasına uyulmalı.
  tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  tileAttribution: '&copy; OpenStreetMap',
  // Dışarıdan yüklenen kütüphaneler tek yerde. İnternet yoksa yüklenemez; uygulama bunu zarifçe
  // karşılar.
  cdn: {
    leafletJs: 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    leafletCss: 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    qrScannerJs: 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
  },
  // Periyodik yenileme süreleri (milisaniye). Çok kısa tutmak sunucuyu gereksiz yorar.
  intervals: { notifications: 30000, feed: 30000, clock: 1000 },
  defaultRadiusKm: 10,
  radiusOptionsKm: [2, 5, 10, 25],
  qrPrefix: 'FR:',
  // Girişten sonra her rolün gideceği ilk sayfa.
  homeByRole: {
    DONOR: '#/donor',
    BENEFICIARY: '#/foods',
    SHELTER: '#/foods',
    ADMIN: '#/admin/overview',
  },
  // Harita işaretçi renkleri (kategoriye göre).
  categoryColors: { HUMAN: '#047857', ANIMAL: '#b45309' },
};
