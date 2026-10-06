import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { session } from '../../core/session.js';
import inventory from '../inventory/index.js';

const GOALS = [
  { key: 'waste', iconName: 'leaf' },
  { key: 'dignity', iconName: 'heart' },
  { key: 'animals', iconName: 'paw' },
  { key: 'pickup', iconName: 'walk' },
];
const STEPS = ['donor', 'receiver', 'pickup'];

function statCell(label, value) {
  return h('div', { class: 'stat' }, h('div', { class: 'stat-value' }, String(value)), h('div', { class: 'stat-label' }, label));
}

export async function homePage({ onCleanup }) {
  const summary = await api('/impact/summary').catch(() => null);
  const user = session.user;

  const actions = user
    ? [h('a', { class: 'btn btn-primary', href: CONFIG.homeByRole[user.role] }, t('home.cta.panel')),
       h('a', { class: 'btn btn-ghost-light', href: '#/foods' }, t('home.cta.browse'))]
    : [h('a', { class: 'btn btn-primary', href: '#/foods' }, t('home.cta.browse')),
       h('a', { class: 'btn btn-ghost-light', href: '#/register' }, t('home.cta.join'))];

  return h('div', { class: 'home' },
    h('section', { class: 'hero' },
      h('div', { class: 'hero-inner' },
        h('h1', {}, t('home.hero.title')),
        h('p', {}, t('home.hero.subtitle')),
        h('div', { class: 'row' }, actions))),
    summary ? h('section', { class: 'stats stats-strip' },
      statCell(t('home.stats.rescued'), summary.portions_rescued),
      statCell(t('home.stats.pickups'), summary.pickups_completed),
      statCell(t('home.stats.donors'), summary.active_donors),
      statCell(t('home.stats.available'), summary.foods_available)) : null,
    h('section', {}, h('h2', {}, t('home.goals.title')),
      h('div', { class: 'cards-4' }, GOALS.map(({ key, iconName }) => h('div', { class: 'card goal' },
        icon(iconName, { size: 30 }), h('h3', {}, t(`home.goals.${key}.title`)), h('p', {}, t(`home.goals.${key}.text`)))))),
    h('section', {}, h('h2', {}, t('home.how.title')),
      h('ol', { class: 'cards-3 steps-cards' }, STEPS.map((key, index) => h('li', { class: 'card' },
        h('span', { class: 'step-no' }, String(index + 1)), h('h3', {}, t(`home.how.${key}.title`)), h('p', {}, t(`home.how.${key}.text`)))))),
    h('section', {},
      h('div', { class: 'page-head' }, h('h2', {}, t('home.live.title')), h('a', { href: '#/foods' }, t('home.live.all'))),
      inventory.components.foodFeed({ onCleanup, limit: 6, compact: true })),
  );
}
