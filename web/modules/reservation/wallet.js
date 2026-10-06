import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { bus } from '../../core/bus.js';
import { h, setChildren } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime, mapsLink, mmss } from '../../core/format.js';
import { badge, button, confirmDialog, emptyState, notice, toast } from '../../core/ui.js';

// Durum -> etiket rengi.
const STATUS_TONE = { PENDING: 'warn', COLLECTED: 'ok', CANCELLED: 'neutral', EXPIRED: 'bad' };

// SVG metnini <img src> için veri adresine (data URL) çevirir. <img> içindeki SVG betik
// çalıştıramaz; bu yüzden QR'ı doğrudan DOM'a gömmek yerine görsel olarak yükleriz (güvenlik).
const qrSource = (svg) => `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;

// Bekleyen rezervasyon: QR, PIN, geri sayım, yol tarifi ve iptal.
function pendingCard(res, onChange) {
  // Geri sayım metni; her saniye güncellenir.
  const countdown = h('strong', { class: 'countdown' }, mmss(res.expires_at));
  const card = h('article', { class: 'card ticket' },
    h('div', { class: 'ticket-qr' }, h('img', { src: qrSource(res.qr_svg), alt: t('wallet.qrAlt'), width: 200, height: 200 })),
    h('div', { class: 'ticket-body' },
      h('div', { class: 'card-head' }, h('h2', {}, res.food_title), badge(t(`reservation.status.${res.status}`), STATUS_TONE[res.status])),
      h('div', { class: 'muted' }, res.donor_name),
      h('div', { class: 'pin-box' }, h('span', { class: 'muted small' }, t('wallet.pin')), h('span', { class: 'pin' }, res.pin.split('').join(' '))),
      h('div', { class: 'meta-row' },
        h('span', { class: 'meta-item' }, icon('utensils', { size: 15 }), t('wallet.portions', { n: res.portions })),
        h('span', { class: 'meta-item' }, icon('clock', { size: 15 }), t('wallet.timeLeft'), ' ', countdown)),
      h('div', { class: 'meta-item' }, icon('pin', { size: 15 }), res.pickup_address),
      h('div', { class: 'row' },
        h('a', { class: 'btn btn-ghost', href: mapsLink(res.latitude, res.longitude), target: '_blank', rel: 'noopener' }, icon('navigate', { size: 18 }), t('food.detail.directions')),
        button(t('wallet.cancel'), { variant: 'danger', iconName: 'x', onClick: async () => {
          // İptalden önce onay.
          if (!(await confirmDialog(t('wallet.cancelConfirm', { title: res.food_title }), { danger: true }))) return;
          try { await api(`/reservations/${res.id}/cancel`, { method: 'POST' }); toast(t('wallet.cancelled'), 'success'); onChange(); }
          catch (err) { toast(err.message, 'error'); }
        } }))));
  // Karta bir güncelleme fonksiyonu iliştirilir; sayfa zamanlayıcısı hepsini çağırır (tek
  // zamanlayıcı, çok kart).
  card.tick = () => { countdown.textContent = mmss(res.expires_at); };
  return card;
}

// Geçmiş satırı. Teslim edilmiş rezervasyonda 'Sorun bildir' bulunur.
function historyRow(res) {
  return h('article', { class: 'card history-row' },
    h('div', { class: 'card-head' },
      h('div', {}, h('strong', {}, res.food_title), h('div', { class: 'muted small' }, `${res.donor_name} - ${t('wallet.portions', { n: res.portions })}`)),
      badge(t(`reservation.status.${res.status}`), STATUS_TONE[res.status])),
    h('div', { class: 'muted small' }, formatDateTime(res.collected_at ?? res.created_at)),
    res.status === 'COLLECTED'
      // Şikâyet penceresini impact modülü açar; bu dosya o modülü hiç tanımaz. Ön yüz olay yolu
      // sayesinde modüller gevşek bağlı kalır.
      ? button(t('wallet.complain'), { variant: 'ghost', iconName: 'flag', onClick: () => bus.emit('complaint:open', res) })
      : null);
}

// Cüzdan sayfası.
export function walletPage({ onCleanup }) {
  const root = h('section', {}, h('h1', {}, t('wallet.title')));
  const body = h('div', { class: 'stack' });
  root.append(body);
  // Geri sayımı güncellenecek kartlar.
  let tickers = [];

  // Rezervasyonları çeker; bekleyenleri ve geçmişi ayırır.
  async function load() {
    const items = await api('/reservations/mine');
    // filter: koşulu sağlayanları ayırır.
    const pending = items.filter((r) => r.status === 'PENDING');
    const history = items.filter((r) => r.status !== 'PENDING');
    const cards = pending.map((r) => pendingCard(r, load));
    // Yenilemede eski kartlar atılır, yenileri izlenir.
    tickers = cards;
    setChildren(body,
      pending.length ? h('div', { class: 'stack' }, h('h2', {}, t('wallet.active')), notice(t('wallet.showCode'), 'info'), cards)
        : emptyState(t('wallet.empty'), 'qr'),
      !pending.length ? h('a', { class: 'btn btn-primary', href: '#/foods' }, t('wallet.browse')) : null,
      history.length ? h('div', { class: 'stack' }, h('h2', {}, t('wallet.history')), history.map(historyRow)) : null);
  }

  // Saniyede bir geri sayımı günceller.
  const clock = setInterval(() => tickers.forEach((card) => card.tick()), CONFIG.intervals.clock);
  // 15 saniyede bir sunucudan yeniler: işletme teslimi onaylayınca kart kendiliğinden 'Teslim
  // edildi'ye döner.
  const refresh = setInterval(() => load().catch(() => {}), 15000);
  // Her iki zamanlayıcı sayfadan çıkarken durdurulur.
  onCleanup(() => { clearInterval(clock); clearInterval(refresh); });
  // İlk veri gelince sayfa gösterilir (router Promise bekler).
  return load().then(() => root);
}
