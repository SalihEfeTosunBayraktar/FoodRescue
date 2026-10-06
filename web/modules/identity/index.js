import { loginPage, registerPage } from './auth_pages.js';
import { accountsPanel } from './accounts_panel.js';
import { t } from '../../core/i18n.js';

// Public surface of the identity module (everything else in this folder is private).
export default {
  name: 'identity',
  routes: [
    { path: '/login', render: loginPage },
    { path: '/register', render: registerPage },
  ],
  nav: () => [],
  components: { accountsPanel },
  label: () => t('module.identity'),
};
