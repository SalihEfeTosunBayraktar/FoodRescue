import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { debounce, h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { createFoodMap, currentPosition, mapUnavailable } from '../../core/map.js';
import { emptyState, notice, toast } from '../../core/ui.js';
import { foodCard } from './food_card.js';

// Live donation feed: filters + list + map. Used by the donations page and by the home page.
export function foodFeed({ onCleanup, limit = null, compact = false } = {}) {
  const state = { category: '', q: '', position: null, radius: CONFIG.defaultRadiusKm };
  const list = h('div', { class: 'stack' });
  const mapBox = h('div', { class: 'feed-map' });
  const mapHost = h('div', { class: 'feed-map-host' }, mapBox);
  const count = h('span', { class: 'muted small' });
  let foodMap = null;
  let foods = [];
  let disposed = false;

  async function load() {
    const query = { category: state.category, q: state.q };
    if (state.position) Object.assign(query, { lat: state.position.lat, lon: state.position.lon, radius_km: state.radius });
    try {
      foods = await api('/foods', { query });
    } catch (err) {
      list.replaceChildren(notice(err.message, 'error'));
      return;
    }
    const shown = limit ? foods.slice(0, limit) : foods;
    count.textContent = t('feed.count', { n: foods.length });
    list.replaceChildren(...(shown.length
      ? shown.map((food) => foodCard(food, { onHover: (f) => foodMap?.focus(f.id) }))
      : [emptyState(t('feed.empty'))]));
    foodMap?.update(shown, { fit: !state.userMovedMap });
  }

  const search = h('input', { type: 'search', placeholder: t('feed.search'), 'aria-label': t('feed.search'),
    onInput: debounce((event) => { state.q = event.target.value.trim(); load(); }, 300) });

  const chip = (key, label, iconName) => {
    const el = h('button', { class: `chip ${state.category === key ? 'is-active' : ''}`, type: 'button', onClick: () => {
      state.category = key;
      chips.querySelectorAll('.chip[data-cat]').forEach((c) => c.classList.toggle('is-active', c.dataset.cat === key));
      load();
    }, dataset: { cat: key } }, iconName ? icon(iconName, { size: 16 }) : null, label);
    return el;
  };

  const radius = h('select', { 'aria-label': t('feed.radius'), hidden: true, onChange: (event) => { state.radius = Number(event.target.value); load(); } },
    CONFIG.radiusOptionsKm.map((km) => h('option', { value: km, selected: km === state.radius }, t('feed.radiusOption', { n: km }))));

  const nearBtn = h('button', { class: 'chip', type: 'button', onClick: async () => {
    if (state.position) {
      state.position = null;
      nearBtn.classList.remove('is-active');
      radius.hidden = true;
      return load();
    }
    try {
      state.position = await currentPosition();
      nearBtn.classList.add('is-active');
      radius.hidden = false;
      load();
    } catch (err) { toast(err.message, 'error'); }
  } }, icon('locate', { size: 16 }), t('feed.nearMe'));

  const chips = h('div', { class: 'chips' }, chip('', t('feed.all')), chip('HUMAN', t('category.HUMAN'), 'utensils'), chip('ANIMAL', t('category.ANIMAL'), 'paw'), nearBtn, radius);

  const root = h('div', { class: `feed ${compact ? 'feed-compact' : ''}` },
    h('div', { class: 'feed-toolbar' }, h('div', { class: 'search' }, icon('search', { size: 18 }), search), chips, count),
    h('div', { class: 'feed-grid' }, list, mapHost));

  createFoodMap(mapBox, { onSelect: (food) => {
    const card = list.querySelector(`[data-id="${food.id}"]`);
    card?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card?.classList.add('is-highlight');
    setTimeout(() => card?.classList.remove('is-highlight'), 1500);
  } }).then((map) => {
    if (disposed) return map.destroy(); // the user left the page before the map was ready
    foodMap = map;
    map.update(limit ? foods.slice(0, limit) : foods);
  })
    .catch(() => mapHost.replaceChildren(mapUnavailable()));

  const timer = setInterval(load, CONFIG.intervals.feed);
  onCleanup?.(() => { disposed = true; clearInterval(timer); foodMap?.destroy(); });
  load();
  return root;
}

export function feedPage({ onCleanup }) {
  return h('section', {}, h('h1', {}, t('feed.title')), h('p', { class: 'muted' }, t('feed.subtitle')), foodFeed({ onCleanup }));
}
