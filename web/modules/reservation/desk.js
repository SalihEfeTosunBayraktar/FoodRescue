import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { h, setChildren } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime, mmss } from '../../core/format.js';
import { badge, button, emptyState, field, notice, withBusy } from '../../core/ui.js';
import { startScanner } from './scanner.js';

const STATUS_TONE = { PENDING: 'warn', COLLECTED: 'ok', CANCELLED: 'neutral', EXPIRED: 'bad' };

// Pickup desk for donors: scan a QR with the camera or type the 6-digit PIN.
export function deskPage({ onCleanup }) {
  const result = h('div', { 'aria-live': 'polite' });
  const incoming = h('div', { class: 'stack' });
  const scannerBox = h('div', { class: 'scanner-box', hidden: true });
  const input = h('input', { name: 'code', inputmode: 'text', autocomplete: 'off', required: true, placeholder: t('desk.placeholder'), maxlength: 80 });
  const submit = button(t('desk.verify'), { type: 'submit', iconName: 'check' });
  let scanner = null;
  let busy = false;

  async function verify(code) {
    if (busy) return;
    busy = true;
    try {
      const done = await api('/reservations/verify', { method: 'POST', body: { code } });
      result.replaceChildren(h('div', { class: 'notice notice-success verified' },
        icon('check', { size: 28 }),
        h('div', {}, h('strong', {}, t('desk.success')), h('div', {}, t('desk.successDetail', { title: done.food_title, n: done.portions, name: done.beneficiary_label })))));
      input.value = '';
      await stopScanner();
      await loadIncoming();
    } catch (err) {
      result.replaceChildren(notice(err.message, 'error'));
    } finally {
      busy = false;
    }
  }

  async function stopScanner() {
    if (scanner) { await scanner.stop(); scanner = null; }
    scannerBox.hidden = true;
    cameraBtn.replaceChildren(icon('camera', { size: 18 }), t('desk.camera.start'));
  }

  const cameraBtn = button(t('desk.camera.start'), { variant: 'ghost', iconName: 'camera', onClick: async () => {
    if (scanner) return stopScanner();
    scannerBox.hidden = false;
    try {
      scanner = await startScanner(scannerBox, (text) => verify(text));
      cameraBtn.replaceChildren(icon('x', { size: 18 }), t('desk.camera.stop'));
    } catch (err) {
      scannerBox.hidden = true;
      result.replaceChildren(notice(err.message, 'error'));
    }
  } });

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

  const timer = setInterval(() => loadIncoming().catch(() => {}), CONFIG.intervals.feed / 3);
  onCleanup(() => { clearInterval(timer); scanner?.stop(); });

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
