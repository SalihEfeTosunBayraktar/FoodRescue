import { CONFIG } from '../config/app.js';

// Session = access token + user profile. Persisted in localStorage when available.
//
// Ders notu (güvenlik): localStorage'daki token, sayfaya enjekte edilen bir script (XSS) tarafından
// okunabilir. Bu yüzden uygulamada hiçbir yerde innerHTML kullanmıyoruz. Üretimde httpOnly çerez
// daha güçlü bir alternatiftir (docs/ogrenme/guvenlik.md).

// Oturum değişince haberdar edilecek fonksiyonlar (gözlemci / observer deseni). Header, giriş-
// çıkışta kendini yeniler.
const listeners = new Set();
// Sayfa yenilense de giriş korunsun diye başlangıç durumu saklı veriden okunur.
let state = load();

// try/catch: tarayıcı depolamayı engelleyebilir (gizli pencere); bu durumda uygulama yine çalışır,
// yalnızca oturum bellekte kalır.
function load() {
  try {
    const raw = localStorage.getItem(CONFIG.storageKey);
    return raw ? JSON.parse(raw) : { token: null, user: null };
  } catch {
    return { token: null, user: null };
  }
}

// Giriş varsa saklar, yoksa siler.
function persist() {
  try {
    if (state.token) localStorage.setItem(CONFIG.storageKey, JSON.stringify(state));
    else localStorage.removeItem(CONFIG.storageKey);
  } catch {
    /* storage unavailable (private mode): session lives in memory only */
  }
}

// Tüm dinleyicilere yeni durumu bildirir.
function emit() {
  listeners.forEach((fn) => fn(state));
}

// Tek bir oturum nesnesi dışa açılır; iç durum (state) dışarıdan doğrudan değiştirilemez, yalnızca
// bu yöntemlerle.
export const session = {
  get token() { return state.token; },
  get user() { return state.user; },
  // getter: `session.isLoggedIn` parantezsiz okunur.
  get isLoggedIn() { return Boolean(state.token); },
  // Rest parametresi (...roles): birden fazla rol verilebilir, kullanıcı bunlardan birine sahipse
  // true.
  hasRole(...roles) { return Boolean(state.user) && roles.includes(state.user.role); },
  // Girişte durumu değiştir, sakla, dinleyicileri uyar.
  login(token, user) { state = { token, user }; persist(); emit(); },
  update(user) { state = { ...state, user }; persist(); emit(); },
  logout() { state = { token: null, user: null }; persist(); emit(); },
  // Dinleyici ekler ve geri dönen fonksiyonla kaldırılabilmesini sağlar.
  subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
};
