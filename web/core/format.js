import { t } from './i18n.js';

// Intl.DateTimeFormat: tarayıcının yerleşik biçimlendiricisi. 'tr-TR' yerel ayarı ay adlarını ve
// saat biçimini Türkçe yapar; sunucu UTC gönderir, tarayıcı kullanıcının saat dilimine çevirir.
const dateTime = new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
const timeOnly = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' });

// ISO metnini (2026-10-06T21:00:00Z) kullanıcıya okunur tarihe çevirir.
export const formatDateTime = (iso) => dateTime.format(new Date(iso));
export const formatTime = (iso) => timeOnly.format(new Date(iso));

// 1 km altı metre, üstü kilometre gösterir.
export function formatDistance(km) {
  if (km == null) return '';
  return km < 1 ? t('format.meters', { n: Math.round(km * 1000) }) : t('format.km', { n: km.toFixed(1) });
}

// "1 sa 20 dk" / "12 dk" / "süresi doldu"
// Kalan süreyi 'saat dakika' biçiminde verir; geçmişse 'süresi doldu'.
export function timeLeft(iso, now = Date.now()) {
  // Tarihler arası fark milisaniye cinsindendir.
  const ms = new Date(iso).getTime() - now;
  if (ms <= 0) return t('format.expired');
  // Math.ceil: 3 dakika 10 saniye kaldıysa '4 dk' göster (hiçbir zaman gerçekten kalandan az
  // göstermemek için yukarı yuvarla).
  const totalMinutes = Math.ceil(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? t('format.hoursMinutes', { h: hours, m: minutes }) : t('format.minutes', { m: minutes });
}

// Geri sayım sayacı için 'dd:ss' biçimi (padStart ile iki haneye tamamlanır).
export function mmss(iso, now = Date.now()) {
  const secs = Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000));
  return `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;
}

// OpenStreetMap'te konumu açan bağlantı (yol tarifi için). API anahtarı gerekmez.
export const mapsLink = (lat, lon) => `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
