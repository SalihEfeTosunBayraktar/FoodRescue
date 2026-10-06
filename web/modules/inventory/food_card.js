import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDistance, formatTime, timeLeft } from '../../core/format.js';
import { badge } from '../../core/ui.js';

export const categoryIcon = (category) => (category === 'ANIMAL' ? 'paw' : 'utensils');

export function foodThumb(food) {
  if (food.photo_url) return h('img', { class: 'thumb', src: food.photo_url, alt: '', loading: 'lazy' });
  return h('div', { class: `thumb thumb-${food.category.toLowerCase()}` }, icon(categoryIcon(food.category), { size: 28 }));
}

export function foodCard(food, { onHover } = {}) {
  const card = h('a', { class: 'card food-card', href: `#/foods/${food.id}`, dataset: { id: food.id }, onMouseenter: () => onHover?.(food) },
    foodThumb(food),
    h('div', { class: 'food-body' },
      h('div', { class: 'card-head' },
        h('strong', { class: 'food-title' }, food.title),
        badge(t(`category.${food.category}`), food.category === 'ANIMAL' ? 'warn' : 'ok')),
      h('div', { class: 'muted small' }, food.donor_name),
      h('div', { class: 'meta-row' },
        h('span', { class: 'meta-item' }, icon('utensils', { size: 15 }), t('food.portionsLeft', { n: food.portions_left })),
        h('span', { class: 'meta-item' }, icon('clock', { size: 15 }), t('food.until', { time: formatTime(food.pickup_until), left: timeLeft(food.pickup_until) })),
        food.distance_km != null ? h('span', { class: 'meta-item' }, icon('pin', { size: 15 }), formatDistance(food.distance_km)) : null),
      h('div', { class: 'muted small' }, food.address)),
  );
  return card;
}
