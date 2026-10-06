import { clear, h } from './dom.js';
import { session } from './session.js';
import { t } from './i18n.js';

// Hash router: "#/foods/12?x=1" -> route "/foods/:id" with params {id: "12"}.
//
// Ders notu: hash (#) kısmı sunucuya gönderilmez; bu yüzden tek sayfalık uygulamalarda ek sunucu
// ayarı gerektirmeden "sayfa" geçişi yapabiliriz.

// '/foods/:id' gibi bir yolu düzenli ifadeye çevirir ve parametre adlarını (id) ayrı tutar.
function compile(path) {
  const names = [];
  const pattern = path.replace(/:([A-Za-z]+)/g, (_, name) => {
    names.push(name);
    return '([^/]+)';
  });
  return { regex: new RegExp(`^${pattern}$`), names };
}

// Adres çubuğundaki '#/foods?x=1' kısmını yol ve sorgu parametrelerine ayırır.
function parseHash() {
  const raw = location.hash.replace(/^#/, '') || '/';
  const [path, queryString = ''] = raw.split('?');
  return { path: path || '/', query: Object.fromEntries(new URLSearchParams(queryString)) };
}

// Programla sayfa değiştirir. Aynı adrese gidiliyorsa tarayıcı olay üretmez; bu yüzden olayı elle
// tetikleriz (sayfayı yenilemek için).
export function navigate(hash) {
  if (location.hash === hash) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = hash;
}

// Hash tabanlı yönlendirici. Her modül kendi yollarını bildirir; router hepsini birleştirir.
export function createRouter({ routes, outlet, notFound }) {
  // Yolları bir kez derleriz; her gezinmede yeniden derlemeyiz.
  const compiled = routes.map((route) => ({ ...route, ...compile(route.path) }));
  // Sayfadan çıkarken temizlenmesi gerekenler (zamanlayıcılar, haritalar). Sayfalar
  // `ctx.onCleanup(fn)` ile kaydeder; unutulursa bellek sızar.
  let cleanups = [];
  // Her gezinmeye bir numara verilir. Yavaş bir sayfa yüklenirken kullanıcı başka sayfaya geçerse
  // eski sonucu atmak için kullanılır (yarış durumu koruması).
  let generation = 0;

  // Kayıtlı temizlik fonksiyonlarını çalıştırır; biri hata verse diğerleri yine çalışır.
  function runCleanups() {
    cleanups.forEach((fn) => { try { fn(); } catch { /* ignore */ } });
    cleanups = [];
  }

  // Her gezinmede çalışan ana fonksiyon: yolu bul -> yetkiyi denetle -> sayfayı üret -> göster.
  async function render() {
    // Bu gezinmenin numarası.
    const mine = ++generation;
    runCleanups();
    const { path, query } = parseHash();
    // İlk eşleşen yolu bul (find).
    const match = compiled.map((r) => ({ r, m: r.regex.exec(path) })).find((x) => x.m);
    if (!match) return show(notFound());

    const { r, m } = match;
    const params = Object.fromEntries(r.names.map((name, i) => [name, decodeURIComponent(m[i + 1])]));
    // Giriş gerektiren sayfa: girişsizse giriş sayfasına yönlendir ve dönüş adresini (next) sakla.
    if (r.auth && !session.isLoggedIn) return navigate(`#/login?next=${encodeURIComponent(location.hash)}`);
    // Rol uyuşmuyorsa 'yetkiniz yok' göster. NOT: bu yalnızca arayüz kolaylığıdır; GERÇEK yetki
    // denetimi sunucudadır.
    if (r.roles && !session.hasRole(...r.roles)) return show(forbidden());

    // Sayfaya verilen bağlam: yol parametreleri, sorgu, temizlik kaydı.
    const ctx = { params, query, onCleanup: (fn) => cleanups.push(fn) };
    // Veri gelene kadar 'Yükleniyor...' göster.
    clear(outlet).append(h('div', { class: 'loading' }, t('common.loading')));
    try {
      // Sayfa fonksiyonu eleman döndürür veya eleman döndüren bir söz (Promise): await ikisini de
      // bekler.
      const view = await r.render(ctx);
      // Kullanıcı bu sırada başka sayfaya geçtiyse bu sonucu göstermeyiz.
      if (mine !== generation) return; // user navigated away while this page was loading
      show(view);
    } catch (error) {
      if (mine !== generation) return;
      show(h('div', { class: 'notice notice-error' }, error.message));
    }
    // Yeni sayfa en üstten başlasın.
    window.scrollTo(0, 0);
  }

  // Çıktı alanındaki içeriği değiştirir.
  function show(view) {
    clear(outlet).append(view);
    // Odağı içeriğe taşı: ekran okuyucu kullanıcıları sayfa değişimini fark eder (erişilebilirlik).
    outlet.focus({ preventScroll: true });
  }

  function forbidden() {
    return h('div', { class: 'notice notice-error' }, t('error.forbidden'));
  }

  // Adres çubuğundaki # kısmı değişince render çalışır. Geri/ileri düğmeleri de böyle çalışır.
  window.addEventListener('hashchange', render);
  return { start: render, refresh: render };
}
