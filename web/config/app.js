// Central front-end configuration. Nothing else in web/ hard-codes URLs, intervals or limits.
export const CONFIG = {
  apiBase: '/api/v1',
  storageKey: 'foodrescue.session',
  defaultCenter: [39.7477, 37.0179],
  defaultZoom: 12,
  tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  tileAttribution: '&copy; OpenStreetMap',
  cdn: {
    leafletJs: 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    leafletCss: 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    qrScannerJs: 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
  },
  intervals: { notifications: 30000, feed: 30000, clock: 1000 },
  defaultRadiusKm: 10,
  radiusOptionsKm: [2, 5, 10, 25],
  qrPrefix: 'FR:',
  homeByRole: {
    DONOR: '#/donor',
    BENEFICIARY: '#/foods',
    SHELTER: '#/foods',
    ADMIN: '#/admin/overview',
  },
  categoryColors: { HUMAN: '#047857', ANIMAL: '#b45309' },
};
