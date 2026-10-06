import { CONFIG } from '../config/app.js';
import { h } from './dom.js';
import { t } from './i18n.js';

// Leaflet is loaded on demand from a CDN. If it cannot be loaded (offline), callers get a clear
// fallback message and the rest of the page keeps working.
let leafletPromise = null;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`failed to load ${src}`));
    document.head.append(script);
  });
}

export function loadLeaflet() {
  if (!leafletPromise) {
    leafletPromise = (async () => {
      const css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = CONFIG.cdn.leafletCss;
      document.head.append(css);
      await loadScript(CONFIG.cdn.leafletJs);
      return window.L;
    })().catch((error) => {
      leafletPromise = null; // allow a retry later
      throw error;
    });
  }
  return leafletPromise;
}

function pinIcon(L, color) {
  const html =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="30" height="40">` +
    `<path d="M12 0C5.4 0 0 5.2 0 11.6 0 20 12 32 12 32s12-12 12-20.4C24 5.2 18.6 0 12 0z" fill="${color}"/>` +
    `<circle cx="12" cy="11.5" r="4.5" fill="#fff"/></svg>`;
  return L.divIcon({ html, className: 'map-pin', iconSize: [30, 40], iconAnchor: [15, 40], popupAnchor: [0, -36] });
}

// A page builds its elements before the router attaches them to the document. Leaflet needs a
// connected container (it measures it), so wait a few frames until the element is in the DOM.
function whenConnected(el, frames = 120) {
  return new Promise((resolve, reject) => {
    const check = (left) => {
      if (el.isConnected) resolve();
      else if (left <= 0) reject(new Error('map container was never attached'));
      else requestAnimationFrame(() => check(left - 1));
    };
    check(frames);
  });
}

export function mapUnavailable() {
  return h('div', { class: 'notice notice-info' }, t('map.unavailable'));
}

// Returns { update(foods), focus(id), destroy() }. `onSelect(food)` fires on marker click.
export async function createFoodMap(container, { center = CONFIG.defaultCenter, onSelect } = {}) {
  const L = await loadLeaflet();
  await whenConnected(container);
  const map = L.map(container, { zoomControl: true }).setView(center, CONFIG.defaultZoom);
  L.tileLayer(CONFIG.tileUrl, { maxZoom: 19, attribution: CONFIG.tileAttribution }).addTo(map);
  const layer = L.layerGroup().addTo(map);
  const markers = new Map();
  let alive = true;
  setTimeout(() => { if (alive) map.invalidateSize(); }, 0);

  return {
    update(foods, { fit = true } = {}) {
      if (!alive) return;
      layer.clearLayers();
      markers.clear();
      foods.forEach((food) => {
        const marker = L.marker([food.latitude, food.longitude], { icon: pinIcon(L, CONFIG.categoryColors[food.category]) });
        const popup = h('div', { class: 'map-popup' }, h('strong', {}, food.title), h('div', {}, food.donor_name));
        marker.bindPopup(popup);
        marker.on('click', () => onSelect?.(food));
        marker.addTo(layer);
        markers.set(food.id, marker);
      });
      if (fit && foods.length) {
        map.fitBounds(L.latLngBounds(foods.map((f) => [f.latitude, f.longitude])).pad(0.25), { maxZoom: 15, animate: false });
      }
    },
    focus(id) {
      const marker = markers.get(id);
      if (alive && marker) { map.setView(marker.getLatLng(), 15, { animate: false }); marker.openPopup(); }
    },
    destroy() { alive = false; map.remove(); },
  };
}

// Click-to-place location picker used by donor registration.
export async function createLocationPicker(container, { initial, onChange }) {
  const L = await loadLeaflet();
  await whenConnected(container);
  const start = initial ?? CONFIG.defaultCenter;
  const map = L.map(container).setView(start, CONFIG.defaultZoom);
  L.tileLayer(CONFIG.tileUrl, { maxZoom: 19, attribution: CONFIG.tileAttribution }).addTo(map);
  let marker = null;
  const place = (lat, lon) => {
    if (marker) marker.setLatLng([lat, lon]);
    else marker = L.marker([lat, lon], { icon: pinIcon(L, CONFIG.categoryColors.HUMAN) }).addTo(map);
    onChange({ lat, lon });
  };
  map.on('click', (event) => place(event.latlng.lat, event.latlng.lng));
  let alive = true;
  setTimeout(() => { if (alive) map.invalidateSize(); }, 0);
  return {
    set(lat, lon) { if (alive) { place(lat, lon); map.setView([lat, lon], 15, { animate: false }); } },
    destroy() { alive = false; map.remove(); },
  };
}

export function currentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error(t('map.noGeolocation')));
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => reject(new Error(t('map.geolocationDenied'))),
      { timeout: 8000 },
    );
  });
}
