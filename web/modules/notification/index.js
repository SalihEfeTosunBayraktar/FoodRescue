import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime } from '../../core/format.js';
import { button, emptyState, toast } from '../../core/ui.js';

// Bell with an unread counter, shown in the header while logged in. Returns { el, destroy }.
// Başlıktaki zil ve okunmamış sayacı. Dönen nesnenin destroy() fonksiyonu zamanlayıcıyı kapatır
// (çıkış yapınca çağrılır).
function bellWidget() {
  // hidden: sayı sıfırken rozet görünmez.
  const counter = h('span', { class: 'bell-count', hidden: true });
  const el = h('a', { class: 'icon-btn bell', href: '#/notifications', 'aria-label': t('notifications.title') }, icon('bell'), counter);

  // Okunmamış sayısını çeker. Hata olursa son değer korunur (ağ kesintisinde zil yanıp sönmez).
  async function refresh() {
    try {
      const { unread } = await api('/notifications');
      counter.textContent = unread > 99 ? '99+' : String(unread);
      counter.hidden = unread === 0;
    } catch { /* offline or logged out: keep the last value */ }
  }
  refresh();
  // Düzenli sorgulama (polling). Anlık iletim için SSE/WebSocket gerekir (README alıştırması).
  const timer = setInterval(refresh, CONFIG.intervals.notifications);
  // Sayfa değişince de tazele: bildirim kutusunu okuyunca sayaç hemen düşer.
  window.addEventListener('hashchange', refresh);
  // Widget sözleşmesi: bir eleman ve bir temizlik fonksiyonu.
  return { el, destroy: () => { clearInterval(timer); window.removeEventListener('hashchange', refresh); } };
}

// Bildirim kutusu sayfası.
async function inboxPage() {
  const list = h('div', { class: 'stack' });

  // Bildirimleri çeker ve listeyi baştan çizer.
  async function load() {
    const { items, unread } = await api('/notifications');
    list.replaceChildren(...(items.length ? items.map((item) => h('article', {
      class: `card notification ${item.read_at ? '' : 'is-unread'}`,
      // Karta tıklayınca okundu işaretlenir (zaten okunduysa istek atılmaz).
      onClick: async () => { if (!item.read_at) { await api(`/notifications/${item.id}/read`, { method: 'POST' }); load(); } },
    },
      h('div', { class: 'card-head' }, h('strong', {}, item.title), h('span', { class: 'muted small' }, formatDateTime(item.created_at))),
      h('div', {}, item.body))) : [emptyState(t('notifications.empty'), 'bell')]));
    readAll.hidden = unread === 0;
  }

  const readAll = button(t('notifications.readAll'), { variant: 'ghost', iconName: 'check', onClick: async () => {
    await api('/notifications/read-all', { method: 'POST' });
    toast(t('common.saved'), 'success');
    load();
  } });

  await load();
  return h('section', { class: 'narrow' }, h('div', { class: 'page-head' }, h('h1', {}, t('notifications.title')), readAll), list);
}

// Modülün dışa açılan yüzeyi.
export default {
  name: 'notification',
  routes: [{ path: '/notifications', auth: true, render: inboxPage }],
  nav: () => [],
  // Ana kabuk (main.js) bu parçayı başlığa yerleştirir.
  headerWidget: bellWidget,
};
