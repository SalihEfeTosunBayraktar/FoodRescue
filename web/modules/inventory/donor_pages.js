import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { formatDateTime, timeLeft } from '../../core/format.js';
import { navigate } from '../../core/router.js';
import { session } from '../../core/session.js';
import { badge, button, confirmDialog, emptyState, field, notice, toast, withBusy } from '../../core/ui.js';
import { foodThumb } from './food_card.js';

// İlan durumu -> etiket rengi.
const STATUS_TONE = { AVAILABLE: 'ok', EXPIRED: 'neutral', CANCELLED: 'bad' };

// Panodaki sayı kartı.
function statTile(label, value, iconName) {
  return h('div', { class: 'stat' }, icon(iconName, { size: 22 }), h('div', { class: 'stat-value' }, String(value)), h('div', { class: 'stat-label' }, label));
}

// Bağışçı paneli: etki sayıları + kendi ilanları.
export async function donorDashboard() {
  const user = session.user;
  // Promise.all: iki isteği AYNI ANDA başlatır; toplam süre ikisinin toplamı değil uzun olanın
  // süresidir. Onaysız bağışçı için istek hiç atılmaz.
  const [foods, impact] = await Promise.all([
    user.status === 'ACTIVE' ? api('/foods/mine') : Promise.resolve([]),
    user.status === 'ACTIVE' ? api('/impact/mine') : Promise.resolve(null),
  ]);
  const list = h('div', { class: 'stack' });

  // Liste boşsa açıklayıcı boş durum gösterir.
  function renderList(items) {
    list.replaceChildren(...(items.length ? items.map(foodRow) : [emptyState(t('donor.foods.empty'), 'utensils')]));
  }

  // Bir ilan satırı: durum, stok, kalan süre ve işlemler.
  function foodRow(food) {
    // Gizli dosya kutusu: 'Fotoğraf' düğmesi bunu tetikler (özel düğme görünümü için yaygın
    // yöntem). accept: dosya seçicide yalnızca görseller görünür (sunucu yine de içeriği doğrular).
    const fileInput = h('input', { type: 'file', accept: 'image/jpeg,image/png,image/webp', hidden: true, onChange: async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      // FormData: dosya yüklemek için multipart gövde.
      const form = new FormData();
      // Alan adı 'file', sunucudaki UploadFile parametresiyle aynı olmalı.
      form.append('file', file);
      try { await api(`/foods/${food.id}/photo`, { method: 'POST', form }); toast(t('common.saved'), 'success'); navigate('#/donor'); }
      catch (err) { toast(err.message, 'error'); }
    } });
    // İşlemler yalnızca yayındaki ilanda görünür.
    const actions = food.status === 'AVAILABLE' ? h('div', { class: 'row' },
      button(t('donor.foods.photo'), { variant: 'ghost', iconName: 'image', onClick: () => fileInput.click() }),
      button(t('donor.foods.cancel'), { variant: 'danger', iconName: 'trash', onClick: async () => {
        // Geri alınamaz işlemden önce onay: bekleyen rezervasyonlar iptal olacak.
        if (!(await confirmDialog(t('donor.foods.cancelConfirm', { title: food.title }), { danger: true }))) return;
        try { await api(`/foods/${food.id}`, { method: 'DELETE' }); toast(t('common.saved'), 'success'); navigate('#/donor'); }
        catch (err) { toast(err.message, 'error'); }
      } })) : null;
    return h('article', { class: 'card food-card' }, foodThumb(food),
      h('div', { class: 'food-body' },
        h('div', { class: 'card-head' }, h('a', { href: `#/foods/${food.id}` }, h('strong', {}, food.title)), badge(t(`food.status.${food.status}`), STATUS_TONE[food.status])),
        h('div', { class: 'meta-row' },
          h('span', { class: 'meta-item' }, icon('utensils', { size: 15 }), t('donor.foods.stock', { left: food.portions_left, total: food.portions_total })),
          h('span', { class: 'meta-item' }, icon('clock', { size: 15 }), food.status === 'AVAILABLE' ? `${formatDateTime(food.pickup_until)} (${timeLeft(food.pickup_until)})` : formatDateTime(food.pickup_until))),
        actions, fileInput));
  }

  // İlk çizim.
  renderList(foods);
  return h('section', {},
    h('div', { class: 'page-head' }, h('h1', {}, t('donor.title', { name: user.organization_name || user.full_name })),
      user.status === 'ACTIVE' ? h('a', { class: 'btn btn-primary', href: '#/donor/new' }, icon('plus', { size: 18 }), t('donor.new')) : null),
    user.status !== 'ACTIVE' ? notice(t('donor.pending'), 'info') : null,
    impact ? h('div', { class: 'stats' },
      statTile(t('donor.stats.rescued'), impact.portions_rescued, 'heart'),
      statTile(t('donor.stats.pickups'), impact.pickups_completed, 'check'),
      statTile(t('donor.stats.waiting'), impact.portions_waiting, 'clock'),
      statTile(t('donor.stats.published'), impact.foods_published, 'list')) : null,
    h('h2', {}, t('donor.foods.title')),
    list);
}

// <input type='datetime-local'> yerel saat ister; UTC'den yerel saate çevirmek için saat dilimi
// farkı (getTimezoneOffset) çıkarılır.
function defaultPickupValue() {
  const d = new Date(Date.now() + 2 * 3600 * 1000);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16); // value format of <input type="datetime-local">
}

// İlan formu. Alanlar tek nesnede toplanır.
export function foodFormPage() {
  const user = session.user;
  const error = h('div');
  // Giriş kutuları.
  const inputs = {
    title: h('input', { name: 'title', required: true, minlength: 3, maxlength: 200 }),
    description: h('textarea', { name: 'description', rows: 3, maxlength: 1000 }),
    category: h('select', { name: 'category' }, ['HUMAN', 'ANIMAL'].map((c) => h('option', { value: c }, t(`category.${c}`)))),
    storage: h('select', { name: 'storage' }, ['HOT', 'COLD', 'ROOM'].map((s) => h('option', { value: s }, t(`storage.${s}`)))),
    portions: h('input', { type: 'number', name: 'portions', min: 1, max: 500, value: 10, required: true }),
    maxPer: h('input', { type: 'number', name: 'max_per_person', min: 1, max: 10, value: 2, required: true }),
    until: h('input', { type: 'datetime-local', name: 'pickup_until', value: defaultPickupValue(), required: true }),
    hygiene: h('input', { type: 'checkbox', name: 'hygiene', required: true }),
    photo: h('input', { type: 'file', accept: 'image/jpeg,image/png,image/webp' }),
  };
  const submit = button(t('donor.form.submit'), { type: 'submit', iconName: 'check' });

  return h('section', { class: 'narrow' },
    h('a', { class: 'back', href: '#/donor' }, t('common.back')),
    h('form', { class: 'card form', onSubmit: async (event) => {
      event.preventDefault();
      error.replaceChildren();
      await withBusy(submit, async () => {
        try {
          const food = await api('/foods', { method: 'POST', body: {
            title: inputs.title.value.trim(),
            description: inputs.description.value.trim() || null,
            category: inputs.category.value,
            storage: inputs.storage.value,
            portions_total: Number(inputs.portions.value),
            max_per_person: Number(inputs.maxPer.value),
            // Yerel saati UTC ISO metnine çevirir; sunucu UTC bekler.
            pickup_until: new Date(inputs.until.value).toISOString(),
            hygiene_confirmed: inputs.hygiene.checked,
          } });
          // Fotoğraf İKİNCİ bir istekle yüklenir (önce ilan oluşur, sonra görsel eklenir). Yükleme
          // başarısız olsa ilan yine yayında kalır.
          if (inputs.photo.files[0]) {
            const form = new FormData();
            form.append('file', inputs.photo.files[0]);
            await api(`/foods/${food.id}/photo`, { method: 'POST', form });
          }
          toast(t('donor.form.published'), 'success');
          navigate('#/donor');
        } catch (err) { error.replaceChildren(notice(err.message, 'error')); }
      });
    } },
      h('h1', {}, t('donor.form.title')),
      field(t('donor.form.name'), inputs.title),
      field(t('donor.form.description'), inputs.description),
      h('div', { class: 'grid-2' }, field(t('donor.form.category'), inputs.category), field(t('donor.form.storage'), inputs.storage)),
      h('div', { class: 'grid-2' }, field(t('donor.form.portions'), inputs.portions), field(t('donor.form.maxPerPerson'), inputs.maxPer, t('donor.form.maxPerPersonHint'))),
      field(t('donor.form.until'), inputs.until, t('donor.form.untilHint')),
      field(t('donor.form.photo'), inputs.photo),
      h('p', { class: 'muted small' }, icon('pin', { size: 14 }), ' ', t('donor.form.location', { address: user.address })),
      h('label', { class: 'check' }, inputs.hygiene, h('span', {}, t('donor.form.hygiene'))),
      error, submit));
}
