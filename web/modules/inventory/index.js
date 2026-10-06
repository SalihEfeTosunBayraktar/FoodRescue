import { session } from '../../core/session.js';
import { t } from '../../core/i18n.js';
import { donorDashboard, foodFormPage } from './donor_pages.js';
import { foodDetailPage } from './food_detail.js';
import { feedPage, foodFeed } from './feed.js';

export default {
  name: 'inventory',
  routes: [
    { path: '/foods', render: feedPage },
    { path: '/foods/:id', render: foodDetailPage },
    { path: '/donor', auth: true, roles: ['DONOR'], render: donorDashboard },
    { path: '/donor/new', auth: true, roles: ['DONOR'], render: foodFormPage },
  ],
  nav: () => [
    { href: '#/foods', label: t('nav.foods'), icon: 'utensils', order: 20 },
    ...(session.hasRole('DONOR') ? [{ href: '#/donor', label: t('nav.myFoods'), icon: 'list', order: 30 }] : []),
  ],
  components: { foodFeed },
};
