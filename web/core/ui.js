import { h } from './dom.js';
import { icon } from './icons.js';
import { t } from './i18n.js';

// Kısa süreli bildirim kutusu. aria-live: ekran okuyucu yeni mesajı okusun.
export function toast(message, tone = 'info') {
  // Kapsayıcı yoksa ilk çağrıda oluşturulur (tembel kurulum).
  let host = document.getElementById('toasts');
  if (!host) {
    host = h('div', { id: 'toasts', 'aria-live': 'polite' });
    document.body.append(host);
  }
  const node = h('div', { class: `toast toast-${tone}`, role: 'status' }, message);
  host.append(node);
  // 4,5 saniye sonra kendiliğinden kalkar.
  setTimeout(() => node.remove(), 4500);
}

// Küçük durum etiketi; renk tonu 'tone' ile seçilir.
export const badge = (text, tone = 'neutral') => h('span', { class: `badge badge-${tone}` }, text);

// Liste boşken kullanıcıya boş ekran yerine açıklayıcı mesaj.
export function emptyState(text, iconName = 'leaf') {
  return h('div', { class: 'empty' }, icon(iconName, { size: 32 }), h('p', {}, text));
}

// Yükleniyor göstergesi.
export function loading() {
  return h('div', { class: 'loading' }, t('common.loading'));
}

// Bilgi/hata kutusu. Hata ise role='alert': ekran okuyucu hemen okur.
export function notice(text, tone = 'info') {
  return h('div', { class: `notice notice-${tone}`, role: tone === 'error' ? 'alert' : 'status' }, text);
}

// <label> + control + optional hint. The label wraps the control, so clicking the text focuses it.
// Etiket + giriş kutusu. <label> kutuyu SARAR: etikete tıklamak kutuya odaklanır ve ekran okuyucu
// bağlantıyı bilir (erişilebilirlik).
export function field(label, control, hint) {
  return h('label', { class: 'field' }, h('span', { class: 'field-label' }, label), control, hint ? h('small', { class: 'field-hint' }, hint) : null);
}

// Tutarlı düğme üretici.
export function button(label, { variant = 'primary', iconName, onClick, type = 'button', disabled = false } = {}) {
  return h('button', { class: `btn btn-${variant}`, type, onClick, disabled }, iconName ? icon(iconName, { size: 18 }) : null, label);
}

// Runs an async action with the button disabled, so a double click cannot submit twice.
// Aynı düğmeye art arda tıklanıp isteğin ikiye katlanmasını önler: iş bitene kadar düğme kapalı
// kalır. finally: hata olsa da düğme tekrar açılır.
export async function withBusy(btn, action) {
  btn.disabled = true;
  try {
    return await action();
  } finally {
    btn.disabled = false;
  }
}

// Evet/Vazgeç penceresi. Promise döndürür: `if (await confirmDialog(...))` şeklinde sıralı okunur.
export function confirmDialog(message, { confirmLabel = t('common.confirm'), danger = false } = {}) {
  // Promise: sonucun (true/false) gelecekte hazır olacağını söyler; resolve çağrılınca await devam
  // eder.
  return new Promise((resolve) => {
    // <dialog>: tarayıcının yerleşik modal penceresi; odak yönetimi ve Esc tuşu bedavadır.
    const dialog = h('dialog', { class: 'dialog' });
    const close = (result) => { dialog.close(); dialog.remove(); resolve(result); };
    dialog.append(
      h('p', {}, message),
      h('div', { class: 'dialog-actions' },
        button(t('common.cancel'), { variant: 'ghost', onClick: () => close(false) }),
        button(confirmLabel, { variant: danger ? 'danger' : 'primary', onClick: () => close(true) })),
    );
    // Esc tuşuyla kapatma da 'vazgeç' sayılır.
    dialog.addEventListener('cancel', () => close(false));
    document.body.append(dialog);
    // Modal olarak aç: arkadaki sayfa tıklanamaz olur.
    dialog.showModal();
  });
}

// İçine form konabilen genel pencere.
export function formDialog(title, content) {
  const dialog = h('dialog', { class: 'dialog dialog-wide' });
  const close = () => { dialog.close(); dialog.remove(); };
  dialog.append(
    h('div', { class: 'dialog-head' }, h('h2', {}, title), h('button', { class: 'icon-btn', type: 'button', 'aria-label': t('common.close'), onClick: close }, icon('x'))),
    content,
  );
  // Esc ile kapatma burada da pencereyi kaldırır.
  dialog.addEventListener('cancel', close);
  document.body.append(dialog);
  dialog.showModal();
  return { close };
}

// Sekmeler gerçek bağlantılardır (<a href>): adres değişir, geri düğmesi ve yer imi çalışır.
export function tabs(items, activeKey) {
  return h('nav', { class: 'tabs', 'aria-label': 'tabs' },
    items.map((item) => h('a', { class: `tab ${item.key === activeKey ? 'is-active' : ''}`, href: item.href }, item.label)));
}
