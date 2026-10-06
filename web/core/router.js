import { clear, h } from './dom.js';
import { session } from './session.js';
import { t } from './i18n.js';

// Hash router: "#/foods/12?x=1" -> route "/foods/:id" with params {id: "12"}.
//
// Ders notu: hash (#) kısmı sunucuya gönderilmez; bu yüzden tek sayfalık uygulamalarda ek sunucu
// ayarı gerektirmeden "sayfa" geçişi yapabiliriz.

function compile(path) {
  const names = [];
  const pattern = path.replace(/:([A-Za-z]+)/g, (_, name) => {
    names.push(name);
    return '([^/]+)';
  });
  return { regex: new RegExp(`^${pattern}$`), names };
}

function parseHash() {
  const raw = location.hash.replace(/^#/, '') || '/';
  const [path, queryString = ''] = raw.split('?');
  return { path: path || '/', query: Object.fromEntries(new URLSearchParams(queryString)) };
}

export function navigate(hash) {
  if (location.hash === hash) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = hash;
}

export function createRouter({ routes, outlet, notFound }) {
  const compiled = routes.map((route) => ({ ...route, ...compile(route.path) }));
  let cleanups = [];
  let generation = 0;

  function runCleanups() {
    cleanups.forEach((fn) => { try { fn(); } catch { /* ignore */ } });
    cleanups = [];
  }

  async function render() {
    const mine = ++generation;
    runCleanups();
    const { path, query } = parseHash();
    const match = compiled.map((r) => ({ r, m: r.regex.exec(path) })).find((x) => x.m);
    if (!match) return show(notFound());

    const { r, m } = match;
    const params = Object.fromEntries(r.names.map((name, i) => [name, decodeURIComponent(m[i + 1])]));
    if (r.auth && !session.isLoggedIn) return navigate(`#/login?next=${encodeURIComponent(location.hash)}`);
    if (r.roles && !session.hasRole(...r.roles)) return show(forbidden());

    const ctx = { params, query, onCleanup: (fn) => cleanups.push(fn) };
    clear(outlet).append(h('div', { class: 'loading' }, t('common.loading')));
    try {
      const view = await r.render(ctx);
      if (mine !== generation) return; // user navigated away while this page was loading
      show(view);
    } catch (error) {
      if (mine !== generation) return;
      show(h('div', { class: 'notice notice-error' }, error.message));
    }
    window.scrollTo(0, 0);
  }

  function show(view) {
    clear(outlet).append(view);
    outlet.focus({ preventScroll: true });
  }

  function forbidden() {
    return h('div', { class: 'notice notice-error' }, t('error.forbidden'));
  }

  window.addEventListener('hashchange', render);
  return { start: render, refresh: render };
}
