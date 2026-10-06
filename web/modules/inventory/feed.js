import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { debounce, h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { createFoodMap, currentPosition, mapUnavailable } from '../../core/map.js';
import { emptyState, notice, toast } from '../../core/ui.js';
import { foodCard } from './food_card.js';

// Live donation feed: filters + list + map. Used by the donations page and by the home page.
// Canlı bağış akışı: arama + süzgeçler + liste + harita. Hem Bağışlar sayfasında hem ana sayfada
// kullanılır (`limit`, `compact` seçenekleriyle).
export function foodFeed({ onCleanup, limit = null, compact = false } = {}) {
  // Süzgeç durumu. Değişince load() yeniden çağrılır.
  const state = { category: '', q: '', position: null, radius: CONFIG.defaultRadiusKm };
  // Kart listesinin kapsayıcısı.
  const list = h('div', { class: 'stack' });
  // Harita elemanı: Leaflet bunun içine çizer.
  const mapBox = h('div', { class: 'feed-map' });
  const mapHost = h('div', { class: 'feed-map-host' }, mapBox);
  const count = h('span', { class: 'muted small' });
  // Harita hazır olana kadar null; sonra nesne atanır.
  let foodMap = null;
  let foods = [];
  // Sayfadan çıkıldığını belirtir: geç hazırlanan harita yok edilsin diye.
  let disposed = false;

  // Sunucudan ilanları çeker (süzgeç parametreleriyle) ve listeyi + haritayı günceller.
  async function load() {
    // Boş süzgeçler api() tarafından otomatik atlanır.
    const query = { category: state.category, q: state.q };
    // Konum seçiliyse sunucu mesafeye göre sıralar ve yarıçapla süzer.
    if (state.position) Object.assign(query, { lat: state.position.lat, lon: state.position.lon, radius_km: state.radius });
    try {
      // Hata olursa listeye hata kutusu koyarız ve çıkarız.
      foods = await api('/foods', { query });
    } catch (err) {
      list.replaceChildren(notice(err.message, 'error'));
      return;
    }
    // Ana sayfada yalnızca ilk birkaç ilan gösterilir (limit).
    const shown = limit ? foods.slice(0, limit) : foods;
    count.textContent = t('feed.count', { n: foods.length });
    list.replaceChildren(...(shown.length
      ? shown.map((food) => foodCard(food, { onHover: (f) => foodMap?.focus(f.id) }))
      : [emptyState(t('feed.empty'))]));
    // Harita henüz yoksa `?.` hata vermez.
    foodMap?.update(shown, { fit: !state.userMovedMap });
  }

  // debounce: kullanıcı yazmayı bırakınca (300 ms) istek atılır; her tuşta değil.
  const search = h('input', { type: 'search', placeholder: t('feed.search'), 'aria-label': t('feed.search'),
    onInput: debounce((event) => { state.q = event.target.value.trim(); load(); }, 300) });

  // Kategori düğmesi üretici: tıklanınca etkin görünümü değiştirir ve listeyi yeniler.
  const chip = (key, label, iconName) => {
    const el = h('button', { class: `chip ${state.category === key ? 'is-active' : ''}`, type: 'button', onClick: () => {
      state.category = key;
      chips.querySelectorAll('.chip[data-cat]').forEach((c) => c.classList.toggle('is-active', c.dataset.cat === key));
      load();
    }, dataset: { cat: key } }, iconName ? icon(iconName, { size: 16 }) : null, label);
    return el;
  };

  // Mesafe seçimi yalnızca konum açıkken görünür (hidden).
  const radius = h('select', { 'aria-label': t('feed.radius'), hidden: true, onChange: (event) => { state.radius = Number(event.target.value); load(); } },
    CONFIG.radiusOptionsKm.map((km) => h('option', { value: km, selected: km === state.radius }, t('feed.radiusOption', { n: km }))));

  // 'Yakınımda': tarayıcıdan konum izni ister. Tekrar tıklanırsa konum süzgeci kapanır (aç/kapa).
  const nearBtn = h('button', { class: 'chip', type: 'button', onClick: async () => {
    if (state.position) {
      state.position = null;
      nearBtn.classList.remove('is-active');
      radius.hidden = true;
      return load();
    }
    try {
      // Kullanıcı izin vermezse istisna fırlar ve toast ile gösterilir.
      state.position = await currentPosition();
      nearBtn.classList.add('is-active');
      radius.hidden = false;
      load();
    } catch (err) { toast(err.message, 'error'); }
  } }, icon('locate', { size: 16 }), t('feed.nearMe'));

  // Süzgeç düğmeleri.
  const chips = h('div', { class: 'chips' }, chip('', t('feed.all')), chip('HUMAN', t('category.HUMAN'), 'utensils'), chip('ANIMAL', t('category.ANIMAL'), 'paw'), nearBtn, radius);

  // Sayfa iskeleti: üstte araç çubuğu, altta liste ve harita yan yana.
  const root = h('div', { class: `feed ${compact ? 'feed-compact' : ''}` },
    h('div', { class: 'feed-toolbar' }, h('div', { class: 'search' }, icon('search', { size: 18 }), search), chips, count),
    h('div', { class: 'feed-grid' }, list, mapHost));

  // Harita ASENKRON hazırlanır; hazır olana kadar liste zaten çalışır. Hata olursa harita kutusu
  // mesajla değişir.
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

  // Liste periyodik yenilenir: başkası rezerve edince stok güncel görünür.
  const timer = setInterval(load, CONFIG.intervals.feed);
  // Sayfadan çıkarken zamanlayıcı ve harita temizlenir (aksi halde arka planda çalışmaya devam
  // ederdi).
  onCleanup?.(() => { disposed = true; clearInterval(timer); foodMap?.destroy(); });
  load();
  return root;
}

// Bağışlar sayfası: başlık + akış bileşeni.
export function feedPage({ onCleanup }) {
  return h('section', {}, h('h1', {}, t('feed.title')), h('p', { class: 'muted' }, t('feed.subtitle')), foodFeed({ onCleanup }));
}
