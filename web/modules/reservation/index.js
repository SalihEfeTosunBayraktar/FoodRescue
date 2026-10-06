import { session } from '../../core/session.js';
import { t } from '../../core/i18n.js';
import { deskPage } from './desk.js';
import { walletPage } from './wallet.js';

// Rezervasyon yapabilen roller.
const RECEIVERS = ['BENEFICIARY', 'SHELTER'];

// Modülün dışa açılan yüzeyi.
export default {
  name: 'reservation',
  // Cüzdan yalnızca yararlanıcı/barınak, teslim masası yalnızca bağışçı içindir.
  routes: [
    { path: '/wallet', auth: true, roles: RECEIVERS, render: walletPage },
    { path: '/donor/desk', auth: true, roles: ['DONOR'], render: deskPage },
  ],
  // Menü öğeleri role göre eklenir.
  nav: () => [
    ...(session.hasRole(...RECEIVERS) ? [{ href: '#/wallet', label: t('nav.wallet'), icon: 'qr', order: 30 }] : []),
    ...(session.hasRole('DONOR') ? [{ href: '#/donor/desk', label: t('nav.desk'), icon: 'camera', order: 31 }] : []),
  ],
};
