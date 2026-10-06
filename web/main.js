import { api } from './core/api.js';
import { clear, h } from './core/dom.js';
import { icon } from './core/icons.js';
import { t } from './core/i18n.js';
import { createRouter, navigate } from './core/router.js';
import { session } from './core/session.js';
import identity from './modules/identity/index.js';
import impact from './modules/impact/index.js';
import inventory from './modules/inventory/index.js';
import notification from './modules/notification/index.js';
import reservation from './modules/reservation/index.js';

// Each module is a self-contained vertical slice: it declares routes, nav items and (optionally)
// an init hook and a header widget. The shell only composes them.
const modules = [identity, inventory, reservation, notification, impact];
modules.forEach((module) => module.init?.());

const header = document.getElementById('app-header');
const outlet = document.getElementById('view');
const footer = document.getElementById('app-footer');
let bell = null;

function renderHeader() {
  bell?.destroy();
  bell = null;
  const user = session.user;
  const links = modules.flatMap((m) => m.nav()).sort((a, b) => a.order - b.order);
  const nav = h('nav', { class: 'nav', id: 'main-nav', 'aria-label': t('nav.label') },
    links.map((link) => h('a', { href: link.href, class: 'nav-link' }, icon(link.icon, { size: 18 }), link.label)));

  const account = user
    ? h('div', { class: 'account' },
        h('span', { class: 'account-name' }, h('strong', {}, user.organization_name || user.full_name), h('small', {}, t(`role.${user.role}`))),
        h('button', { class: 'icon-btn', type: 'button', 'aria-label': t('nav.logout'), title: t('nav.logout'), onClick: () => { session.logout(); navigate('#/'); } }, icon('logout')))
    : h('div', { class: 'account' },
        h('a', { class: 'btn btn-ghost', href: '#/login' }, t('nav.login')),
        h('a', { class: 'btn btn-primary', href: '#/register' }, t('nav.register')));

  const widgetHost = h('div', { class: 'widgets' });
  if (user) {
    bell = notification.headerWidget();
    widgetHost.append(bell.el);
  }

  const toggle = h('button', { class: 'icon-btn menu-toggle', type: 'button', 'aria-label': t('nav.menu'), 'aria-expanded': 'false',
    onClick: () => { const open = nav.classList.toggle('is-open'); toggle.setAttribute('aria-expanded', String(open)); } }, icon('menu'));

  clear(header).append(h('div', { class: 'header-inner' },
    h('a', { class: 'brand', href: '#/' }, icon('leaf', { size: 26 }), h('span', {}, t('app.name'))),
    nav, widgetHost, account, toggle));
  markActive();
}

function markActive() {
  const current = location.hash || '#/';
  header.querySelectorAll('.nav-link').forEach((link) => {
    const href = link.getAttribute('href');
    const active = href === '#/' ? current === '#/' || current === '' : current.startsWith(href.split('/').slice(0, 2).join('/'));
    link.classList.toggle('is-active', active);
  });
  header.querySelector('#main-nav')?.classList.remove('is-open');
}

const router = createRouter({
  routes: modules.flatMap((m) => m.routes),
  outlet,
  notFound: () => h('div', { class: 'notice notice-error' }, t('error.notFound'), ' ', h('a', { href: '#/' }, t('nav.home'))),
});

footer.append(h('p', {}, t('footer.text')));
session.subscribe(() => { renderHeader(); router.refresh(); });
window.addEventListener('hashchange', markActive);

async function boot() {
  if (session.isLoggedIn) {
    // Refresh the profile: an admin may have approved or suspended the account since last visit.
    await api('/auth/me').then((user) => session.update(user)).catch(() => {});
  }
  renderHeader();
  router.start();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
}

boot();
