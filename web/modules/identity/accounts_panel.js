import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { formatDateTime } from '../../core/format.js';
import { badge, button, confirmDialog, emptyState, field, formDialog, toast, withBusy } from '../../core/ui.js';

// Durum -> renk tonu eşlemesi (veriyle kural: if/else zinciri yerine tablo).
const STATUS_TONE = { ACTIVE: 'ok', PENDING_REVIEW: 'warn', REJECTED: 'bad', SUSPENDED: 'bad' };
// Yönetici sekmesindeki durum süzgeçleri.
const FILTERS = ['PENDING_REVIEW', 'ACTIVE', 'SUSPENDED', 'REJECTED'];

// Admin panel for account review. Exported through identity/index.js and mounted by the admin page.
// Yönetici hesap paneli. Bu bileşen identity modülünündür; impact modülünün yönetim sayfası
// index.js üzerinden kullanır.
export function accountsPanel() {
  const root = h('div');
  // Seçili süzgeç; varsayılan olarak onay bekleyenler (yöneticinin asıl işi).
  let filter = 'PENDING_REVIEW';

  // Listeyi sunucudan çeker ve ekranı baştan çizer. Süzgeç değişince tekrar çağrılır.
  async function load() {
    const accounts = await api('/admin/accounts', { query: { status: filter } });
    root.replaceChildren(
      h('div', { class: 'chips' }, FILTERS.map((key) => h('button', {
        class: `chip ${key === filter ? 'is-active' : ''}`, type: 'button', onClick: () => { filter = key; load(); },
      }, t(`account.status.${key}`)))),
      accounts.length ? h('div', { class: 'stack' }, accounts.map(accountCard)) : emptyState(t('admin.accounts.empty'), 'users'),
    );
  }

  // Bir hesabın kartı; duruma göre farklı düğmeler gösterilir (durum makinesi arayüze yansır).
  function accountCard(user) {
    const actions = [];
    if (user.status === 'PENDING_REVIEW') {
      actions.push(button(t('admin.accounts.approve'), { iconName: 'check', onClick: () => review(user, true) }));
      actions.push(button(t('admin.accounts.reject'), { variant: 'danger', iconName: 'x', onClick: () => review(user, false) }));
    }
    if (user.status === 'ACTIVE' && user.role !== 'ADMIN') {
      actions.push(button(t('admin.accounts.suspend'), { variant: 'danger', onClick: () => suspend(user) }));
    }
    if (user.status === 'SUSPENDED') {
      actions.push(button(t('admin.accounts.reinstate'), { onClick: () => reinstate(user) }));
    }
    return h('article', { class: 'card' },
      h('div', { class: 'card-head' },
        h('div', {},
          h('strong', {}, user.organization_name || user.full_name),
          h('div', { class: 'muted small' }, `${user.email} - ${t(`role.${user.role}`)}`)),
        badge(t(`account.status.${user.status}`), STATUS_TONE[user.status])),
      user.license_number ? h('div', { class: 'meta' }, `${t('auth.license')}: ${user.license_number}`) : null,
      user.address ? h('div', { class: 'meta' }, user.address) : null,
      h('div', { class: 'meta muted' }, formatDateTime(user.created_at)),
      user.review_note ? h('div', { class: 'meta' }, `${t('admin.accounts.note')}: ${user.review_note}`) : null,
      actions.length ? h('div', { class: 'row' }, actions) : null,
    );
  }

  // Not/gerekçe soran ortak pencere: onay, ret ve askıya alma aynı pencereyi paylaşır (DRY).
  function noteDialog(title, label, submitLabel, onSubmit, required = false) {
    const note = h('textarea', { rows: 3, maxlength: 500, required });
    const submit = button(submitLabel, { type: 'submit' });
    const form = h('form', { class: 'form', onSubmit: async (event) => {
      event.preventDefault();
      await withBusy(submit, async () => {
        try { await onSubmit(note.value.trim()); dialog.close(); await load(); }
        catch (err) { toast(err.message, 'error'); }
      });
    } }, field(label, note), submit);
    // Pencere, onSubmit içinde dialog.close() çağıracağı için form tanımından SONRA oluşturulur;
    // işlev yalnızca gönderimde çalıştığından erişim güvenlidir.
    const dialog = formDialog(title, form);
  }

  // Onay veya ret kararı: sunucuya APPROVE/REJECT gönderir.
  function review(user, approve) {
    noteDialog(
      t(approve ? 'admin.accounts.approve' : 'admin.accounts.reject'), t('admin.accounts.note'), t('common.confirm'),
      async (note) => { await api(`/admin/accounts/${user.id}/review`, { method: 'POST', body: { decision: approve ? 'APPROVE' : 'REJECT', note: note || null } }); toast(t('common.saved'), 'success'); },
    );
  }

  // Askıya alma gerekçe ister (required=true): sunucu da zorunlu tutar.
  function suspend(user) {
    noteDialog(
      t('admin.accounts.suspend'), t('admin.accounts.reason'), t('common.confirm'),
      async (reason) => { await api(`/admin/accounts/${user.id}/suspend`, { method: 'POST', body: { reason } }); toast(t('common.saved'), 'success'); },
      true,
    );
  }

  // Geri alınabilir işlem olsa da önce onay sorarız.
  async function reinstate(user) {
    if (!(await confirmDialog(t('admin.accounts.reinstateConfirm', { name: user.organization_name || user.full_name })))) return;
    try { await api(`/admin/accounts/${user.id}/reinstate`, { method: 'POST' }); toast(t('common.saved'), 'success'); await load(); }
    catch (err) { toast(err.message, 'error'); }
  }

  // İlk yükleme hata verirse kullanıcıya mesaj göster; sessizce boş ekran bırakma.
  load().catch((err) => root.replaceChildren(h('div', { class: 'notice notice-error' }, err.message)));
  return root;
}
