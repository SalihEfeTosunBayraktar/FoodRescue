import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { button, field, formDialog, notice, toast, withBusy } from '../../core/ui.js';

// Opened through the "complaint:open" bus event emitted by the wallet (reservation module).
export function openComplaintDialog(reservation) {
  const reason = h('textarea', { rows: 4, minlength: 10, maxlength: 1000, required: true, placeholder: t('complaint.placeholder') });
  const error = h('div');
  const submit = button(t('complaint.submit'), { type: 'submit', iconName: 'flag' });
  const dialog = formDialog(t('complaint.title', { title: reservation.food_title }),
    h('form', { class: 'form', onSubmit: async (event) => {
      event.preventDefault();
      error.replaceChildren();
      await withBusy(submit, async () => {
        try {
          await api('/complaints', { method: 'POST', body: { reservation_id: reservation.id, reason: reason.value.trim() } });
          dialog.close();
          toast(t('complaint.sent'), 'success');
        } catch (err) { error.replaceChildren(notice(err.message, 'error')); }
      });
    } }, h('p', { class: 'muted' }, t('complaint.intro')), field(t('complaint.reason'), reason), error, submit));
}
