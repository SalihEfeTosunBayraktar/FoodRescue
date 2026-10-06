import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime } from '../../core/format.js';
import { badge, button, emptyState, field, formDialog, tabs, toast, withBusy } from '../../core/ui.js';
import identity from '../identity/index.js';

const TABS = ['overview', 'accounts', 'complaints', 'audit'];
const COMPLAINT_TONE = { OPEN: 'warn', RESOLVED: 'ok', DISMISSED: 'neutral' };

function tile(label, value, iconName) {
  return h('div', { class: 'stat' }, icon(iconName, { size: 22 }), h('div', { class: 'stat-value' }, String(value)), h('div', { class: 'stat-label' }, label));
}

async function overviewTab() {
  const [overview, summary] = await Promise.all([api('/admin/overview'), api('/impact/summary')]);
  const breakdown = (title, data, labelKey) => h('div', { class: 'card' }, h('h3', {}, title),
    h('ul', { class: 'plain' }, Object.entries(data).map(([key, n]) => h('li', { class: 'row-between' }, h('span', {}, t(`${labelKey}.${key}`)), h('strong', {}, String(n))))));
  return h('div', { class: 'stack' },
    h('div', { class: 'stats' },
      tile(t('admin.overview.pending'), overview.pending_accounts, 'shield'),
      tile(t('admin.overview.complaints'), overview.open_complaints, 'flag'),
      tile(t('admin.overview.rescued'), summary.portions_rescued, 'heart'),
      tile(t('admin.overview.available'), summary.foods_available, 'utensils')),
    h('div', { class: 'cards-2' },
      breakdown(t('admin.overview.users'), overview.users_by_role, 'role'),
      breakdown(t('admin.overview.reservations'), overview.reservations_by_status, 'reservation.status')));
}

async function complaintsTab() {
  const root = h('div', { class: 'stack' });

  async function load() {
    const items = await api('/admin/complaints');
    root.replaceChildren(...(items.length ? items.map(card) : [emptyState(t('admin.complaints.empty'), 'flag')]));
  }

  function card(item) {
    return h('article', { class: 'card' },
      h('div', { class: 'card-head' },
        h('div', {}, h('strong', {}, item.donor_name), h('div', { class: 'muted small' }, formatDateTime(item.created_at))),
        badge(t(`complaint.status.${item.status}`), COMPLAINT_TONE[item.status])),
      h('p', {}, item.reason),
      item.resolution_note ? h('div', { class: 'muted small' }, `${t('admin.accounts.note')}: ${item.resolution_note}`) : null,
      item.status === 'OPEN' ? h('div', { class: 'row' },
        button(t('admin.complaints.resolve'), { iconName: 'check', onClick: () => resolve(item, 'RESOLVE') }),
        button(t('admin.complaints.dismiss'), { variant: 'ghost', iconName: 'x', onClick: () => resolve(item, 'DISMISS') })) : null);
  }

  function resolve(item, action) {
    const note = h('textarea', { rows: 3, maxlength: 500 });
    const submit = button(t('common.confirm'), { type: 'submit' });
    const dialog = formDialog(t(action === 'RESOLVE' ? 'admin.complaints.resolve' : 'admin.complaints.dismiss'),
      h('form', { class: 'form', onSubmit: async (event) => {
        event.preventDefault();
        await withBusy(submit, async () => {
          try {
            await api(`/admin/complaints/${item.id}/resolve`, { method: 'POST', body: { action, note: note.value.trim() || null } });
            dialog.close(); toast(t('common.saved'), 'success'); await load();
          } catch (err) { toast(err.message, 'error'); }
        });
      } }, field(t('admin.accounts.note'), note), submit));
  }

  await load();
  return root;
}

async function auditTab() {
  const rows = await api('/admin/audit', { query: { limit: 100 } });
  if (!rows.length) return emptyState(t('admin.audit.empty'), 'log');
  return h('div', { class: 'table-wrap' }, h('table', { class: 'table' },
    h('thead', {}, h('tr', {}, ['time', 'actor', 'action', 'entity', 'detail'].map((c) => h('th', {}, t(`admin.audit.col.${c}`))))),
    h('tbody', {}, rows.map((row) => h('tr', {},
      h('td', {}, formatDateTime(row.created_at)),
      h('td', {}, row.actor_id ?? t('admin.audit.system')),
      h('td', {}, h('code', {}, row.action)),
      h('td', {}, `${row.entity_type} #${row.entity_id}`),
      h('td', { class: 'muted small' }, row.detail ?? ''))))));
}

export async function adminPage({ params }) {
  const active = TABS.includes(params.tab) ? params.tab : 'overview';
  const renderers = { overview: overviewTab, accounts: async () => identity.components.accountsPanel(), complaints: complaintsTab, audit: auditTab };
  const content = await renderers[active]();
  return h('section', {},
    h('h1', {}, t('admin.title')),
    tabs(TABS.map((key) => ({ key, href: `#/admin/${key}`, label: t(`admin.tab.${key}`) })), active),
    content);
}
