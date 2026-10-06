import { t } from './i18n.js';

const dateTime = new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
const timeOnly = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' });

export const formatDateTime = (iso) => dateTime.format(new Date(iso));
export const formatTime = (iso) => timeOnly.format(new Date(iso));

export function formatDistance(km) {
  if (km == null) return '';
  return km < 1 ? t('format.meters', { n: Math.round(km * 1000) }) : t('format.km', { n: km.toFixed(1) });
}

// "1 sa 20 dk" / "12 dk" / "süresi doldu"
export function timeLeft(iso, now = Date.now()) {
  const ms = new Date(iso).getTime() - now;
  if (ms <= 0) return t('format.expired');
  const totalMinutes = Math.ceil(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? t('format.hoursMinutes', { h: hours, m: minutes }) : t('format.minutes', { m: minutes });
}

export function mmss(iso, now = Date.now()) {
  const secs = Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000));
  return `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;
}

export const mapsLink = (lat, lon) => `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
