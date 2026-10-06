import { session } from '../../core/session.js';
import { t } from '../../core/i18n.js';
import { donorDashboard, foodFormPage } from './donor_pages.js';
import { foodDetailPage } from './food_detail.js';
import { feedPage, foodFeed } from './feed.js';

// Modülün dışa açılan yüzeyi.
export default {
  name: 'inventory',
  // Yol tanımları: auth ve roles alanları router'a erişim kuralını söyler. Bu yalnızca arayüz
  // yönlendirmesidir; sunucu her istekte yetkiyi yeniden denetler.
  routes: [
    { path: '/foods', render: feedPage },
    { path: '/foods/:id', render: foodDetailPage },
    { path: '/donor', auth: true, roles: ['DONOR'], render: donorDashboard },
    { path: '/donor/new', auth: true, roles: ['DONOR'], render: foodFormPage },
  ],
  // Menü öğeleri oturuma göre değişir: bağışçıya 'İlanlarım' eklenir.
  nav: () => [
    { href: '#/foods', label: t('nav.foods'), icon: 'utensils', order: 20 },
    ...(session.hasRole('DONOR') ? [{ href: '#/donor', label: t('nav.myFoods'), icon: 'list', order: 30 }] : []),
  ],
  // Ana sayfa (impact modülü) canlı bağış akışını buradan kullanır.
  components: { foodFeed },
};
