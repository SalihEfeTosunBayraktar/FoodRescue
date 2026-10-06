import { loginPage, registerPage } from './auth_pages.js';
import { accountsPanel } from './accounts_panel.js';
import { t } from '../../core/i18n.js';

// Public surface of the identity module (everything else in this folder is private).
// Modülün dışa açılan yüzeyi: yollar, menü öğeleri ve diğer modüllerin kullanabileceği bileşenler.
// Dosyaların geri kalanı modüle özeldir.
export default {
  name: 'identity',
  routes: [
    { path: '/login', render: loginPage },
    { path: '/register', render: registerPage },
  ],
  nav: () => [],
  // Başka modüller bu bileşene yalnızca burası üzerinden ulaşır.
  components: { accountsPanel },
  label: () => t('module.identity'),
};
