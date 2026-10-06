import { bus } from '../../core/bus.js';
import { session } from '../../core/session.js';
import { t } from '../../core/i18n.js';
import { adminPage } from './admin.js';
import { openComplaintDialog } from './complaint_dialog.js';
import { homePage } from './home.js';

export default {
  name: 'impact',
  init() {
    bus.on('complaint:open', openComplaintDialog);
  },
  routes: [
    { path: '/', render: homePage },
    { path: '/admin', auth: true, roles: ['ADMIN'], render: () => adminPage({ params: {} }) },
    { path: '/admin/:tab', auth: true, roles: ['ADMIN'], render: adminPage },
  ],
  nav: () => [
    { href: '#/', label: t('nav.home'), icon: 'home', order: 10 },
    ...(session.hasRole('ADMIN') ? [{ href: '#/admin/overview', label: t('nav.admin'), icon: 'chart', order: 40 }] : []),
  ],
};
