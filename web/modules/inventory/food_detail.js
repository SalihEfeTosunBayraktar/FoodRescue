import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime, mapsLink, timeLeft } from '../../core/format.js';
import { createFoodMap, mapUnavailable } from '../../core/map.js';
import { navigate } from '../../core/router.js';
import { session } from '../../core/session.js';
import { badge, button, field, notice, toast, withBusy } from '../../core/ui.js';
import { foodThumb } from './food_card.js';

const RECEIVER_CATEGORY = { BENEFICIARY: 'HUMAN', SHELTER: 'ANIMAL' };

function reservePanel(food) {
  const user = session.user;
  if (!food.is_available) return notice(t('food.detail.unavailable'), 'info');
  if (!user) {
    return h('div', { class: 'stack' }, notice(t('food.detail.loginRequired'), 'info'),
      h('a', { class: 'btn btn-primary', href: `#/login?next=${encodeURIComponent(location.hash)}` }, t('auth.login.submit')));
  }
  if (!RECEIVER_CATEGORY[user.role]) return notice(t('food.detail.notReceiver'), 'info');
  if (user.status !== 'ACTIVE') return notice(t('account.notActive'), 'info');
  if (RECEIVER_CATEGORY[user.role] !== food.category) return notice(t(`food.detail.wrongCategory.${user.role}`), 'info');

  const maxPortions = Math.min(food.max_per_person, food.portions_left);
  const select = h('select', { name: 'portions' }, Array.from({ length: maxPortions }, (_, i) => h('option', { value: i + 1 }, String(i + 1))));
  const submit = button(t('food.detail.reserve'), { iconName: 'qr', type: 'submit' });
  const error = h('div');
  return h('form', { class: 'form', onSubmit: async (event) => {
    event.preventDefault();
    error.replaceChildren();
    await withBusy(submit, async () => {
      try {
        await api('/reservations', { method: 'POST', body: { food_id: food.id, portions: Number(select.value) } });
        toast(t('food.detail.reserved'), 'success');
        navigate('#/wallet');
      } catch (err) { error.replaceChildren(notice(err.message, 'error')); }
    });
  } }, field(t('food.detail.portions'), select, t('food.detail.maxPerPerson', { n: food.max_per_person })), error, submit);
}

export async function foodDetailPage({ params, onCleanup }) {
  const food = await api(`/foods/${params.id}`);
  const mapBox = h('div', { class: 'detail-map' });
  const mapHost = h('div', {}, mapBox);

  let foodMap = null;
  let disposed = false;
  onCleanup(() => { disposed = true; foodMap?.destroy(); });
  createFoodMap(mapBox, { center: [food.latitude, food.longitude] })
    .then((map) => {
      if (disposed) return map.destroy();
      foodMap = map;
      map.update([food]);
    })
    .catch(() => mapHost.replaceChildren(mapUnavailable()));

  return h('section', { class: 'detail' },
    h('a', { class: 'back', href: '#/foods' }, t('common.back')),
    h('div', { class: 'detail-grid' },
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('div', { class: 'detail-hero' }, foodThumb(food)),
          h('div', { class: 'card-head' }, h('h1', {}, food.title), badge(t(`category.${food.category}`), food.category === 'ANIMAL' ? 'warn' : 'ok')),
          food.description ? h('p', {}, food.description) : null,
          h('dl', { class: 'facts' },
            h('dt', {}, icon('building', { size: 16 }), t('food.detail.donor')), h('dd', {}, food.donor_name),
            h('dt', {}, icon('utensils', { size: 16 }), t('food.detail.stock')), h('dd', {}, t('food.detail.stockValue', { left: food.portions_left, total: food.portions_total })),
            h('dt', {}, icon('clock', { size: 16 }), t('food.detail.until')), h('dd', {}, `${formatDateTime(food.pickup_until)} (${timeLeft(food.pickup_until)})`),
            h('dt', {}, icon('shield', { size: 16 }), t('food.detail.storage')), h('dd', {}, t(`storage.${food.storage}`)),
            h('dt', {}, icon('pin', { size: 16 }), t('food.detail.address')), h('dd', {}, food.address))),
        h('div', { class: 'card' }, h('h2', {}, t('food.detail.howItWorks')), h('ol', { class: 'steps' },
          ['step1', 'step2', 'step3'].map((key) => h('li', {}, t(`food.detail.${key}`)))))),
      h('div', { class: 'stack' },
        h('div', { class: 'card' }, h('h2', {}, t('food.detail.reserveTitle')), reservePanel(food)),
        h('div', { class: 'card' }, mapHost,
          h('a', { class: 'btn btn-ghost', href: mapsLink(food.latitude, food.longitude), target: '_blank', rel: 'noopener' }, icon('navigate', { size: 18 }), t('food.detail.directions'))))),
  );
}
