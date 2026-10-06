import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { h, setChildren } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime, mmss } from '../../core/format.js';
import { badge, button, emptyState, field, notice, withBusy } from '../../core/ui.js';
import { startScanner } from './scanner.js';

// Durum -> etiket rengi.
const STATUS_TONE = { PENDING: 'warn', COLLECTED: 'ok', CANCELLED: 'neutral', EXPIRED: 'bad' };

// Pickup desk for donors: scan a QR with the camera or type the 6-digit PIN.
// Teslim masası: yararlanıcının kodunu doğrulayan işletme ekranı. Üç giriş yolu: QR'ı kamerayla
// okut, QR içeriğini yaz, 6 haneli PIN gir.
export function deskPage({ onCleanup }) {
  const result = h('div', { 'aria-live': 'polite' });
  const incoming = h('div', { class: 'stack' });
  const scannerBox = h('div', { class: 'scanner-box', hidden: true });
  const input = h('input', { name: 'code', inputmode: 'text', autocomplete: 'off', required: true, placeholder: t('desk.placeholder'), maxlength: 80 });
  const submit = button(t('desk.verify'), { type: 'submit', iconName: 'check' });
  // Çalışan kamera tarayıcısı (yoksa null).
  let scanner = null;
  // Aynı kod kamera tarafından saniyede birkaç kez okunabilir; doğrulama sürerken yeni okumalar yok
  // sayılır (kilit bayrağı).
  let busy = false;

  // Kodu sunucuya gönderir ve sonucu gösterir. Kamera ve elle giriş aynı fonksiyonu kullanır.
  async function verify(code) {
    // Çift gönderimi engelle.
    if (busy) return;
    busy = true;
    try {
      // Tüm güvenlik kararı (sahiplik, hız sınırı, tek kullanımlık kod) sunucudadır; burası
      // yalnızca iletir.
      const done = await api('/reservations/verify', { method: 'POST', body: { code } });
      result.replaceChildren(h('div', { class: 'notice notice-success verified' },
        icon('check', { size: 28 }),
        h('div', {}, h('strong', {}, t('desk.success')), h('div', {}, t('desk.successDetail', { title: done.food_title, n: done.portions, name: done.beneficiary_label })))));
      input.value = '';
      // Başarılı okumadan sonra kamerayı kapat.
      await stopScanner();
      await loadIncoming();
    } catch (err) {
      result.replaceChildren(notice(err.message, 'error'));
    } finally {
      busy = false;
    }
  }

  // Kamera akışını durdurur ve düğmeyi eski haline getirir.
  async function stopScanner() {
    if (scanner) { await scanner.stop(); scanner = null; }
    scannerBox.hidden = true;
    cameraBtn.replaceChildren(icon('camera', { size: 18 }), t('desk.camera.start'));
  }

  // Kamera aç/kapa. İzin verilmezse veya kütüphane yüklenemezse mesaj gösterilir; elle giriş
  // çalışmaya devam eder.
  const cameraBtn = button(t('desk.camera.start'), { variant: 'ghost', iconName: 'camera', onClick: async () => {
    if (scanner) return stopScanner();
    scannerBox.hidden = false;
    try {
      // Her okunan metin doğrulamaya gönderilir.
      scanner = await startScanner(scannerBox, (text) => verify(text));
      cameraBtn.replaceChildren(icon('x', { size: 18 }), t('desk.camera.stop'));
    } catch (err) {
      scannerBox.hidden = true;
      result.replaceChildren(notice(err.message, 'error'));
    }
  } });

  // Bekleyenler ve son işlemler listesi.
  async function loadIncoming() {
    const rows = await api('/reservations/incoming');
    const pending = rows.filter((r) => r.status === 'PENDING');
    const recent = rows.filter((r) => r.status !== 'PENDING').slice(0, 8);
    setChildren(incoming,
      h('h2', {}, t('desk.waiting')),
      pending.length ? pending.map((r) => h('article', { class: 'card history-row' },
        h('div', { class: 'card-head' },
          h('div', {}, h('strong', {}, r.food_title), h('div', { class: 'muted small' }, `${r.beneficiary_label} - ${t('wallet.portions', { n: r.portions })}`)),
          h('span', { class: 'meta-item' }, icon('clock', { size: 15 }), mmss(r.expires_at))))) : emptyState(t('desk.noneWaiting'), 'qr'),
      recent.length ? [h('h2', {}, t('desk.recent')), recent.map((r) => h('article', { class: 'card history-row' },
        h('div', { class: 'card-head' },
          h('div', {}, h('strong', {}, r.food_title), h('div', { class: 'muted small' }, `${r.beneficiary_label} - ${formatDateTime(r.collected_at ?? r.created_at)}`)),
          badge(t(`reservation.status.${r.status}`), STATUS_TONE[r.status]))))] : null);
  }

  // Bekleyen listesi periyodik yenilenir.
  const timer = setInterval(() => loadIncoming().catch(() => {}), CONFIG.intervals.feed / 3);
  // Sayfadan çıkarken zamanlayıcı ve kamera kapatılır: kamera açık kalırsa gizlilik ve pil sorunu
  // olur.
  onCleanup(() => { clearInterval(timer); scanner?.stop(); });

  // İlk veri gelince sayfa gösterilir.
  return loadIncoming().then(() => h('section', {},
    h('h1', {}, t('desk.title')),
    h('p', { class: 'muted' }, t('desk.subtitle')),
    h('div', { class: 'desk-grid' },
      h('div', { class: 'stack' },
        h('form', { class: 'card form', onSubmit: (event) => { event.preventDefault(); withBusy(submit, () => verify(input.value)); } },
          field(t('desk.code'), input, t('desk.codeHint')), h('div', { class: 'row' }, submit, cameraBtn), scannerBox),
        result),
      incoming)));
}
