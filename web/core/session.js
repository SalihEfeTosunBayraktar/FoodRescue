import { CONFIG } from '../config/app.js';

// Session = access token + user profile. Persisted in localStorage when available.
//
// Ders notu (güvenlik): localStorage'daki token, sayfaya enjekte edilen bir script (XSS) tarafından
// okunabilir. Bu yüzden uygulamada hiçbir yerde innerHTML kullanmıyoruz. Üretimde httpOnly çerez
// daha güçlü bir alternatiftir (docs/ogrenme/guvenlik.md).

const listeners = new Set();
let state = load();

function load() {
  try {
    const raw = localStorage.getItem(CONFIG.storageKey);
    return raw ? JSON.parse(raw) : { token: null, user: null };
  } catch {
    return { token: null, user: null };
  }
}

function persist() {
  try {
    if (state.token) localStorage.setItem(CONFIG.storageKey, JSON.stringify(state));
    else localStorage.removeItem(CONFIG.storageKey);
  } catch {
    /* storage unavailable (private mode): session lives in memory only */
  }
}

function emit() {
  listeners.forEach((fn) => fn(state));
}

export const session = {
  get token() { return state.token; },
  get user() { return state.user; },
  get isLoggedIn() { return Boolean(state.token); },
  hasRole(...roles) { return Boolean(state.user) && roles.includes(state.user.role); },
  login(token, user) { state = { token, user }; persist(); emit(); },
  update(user) { state = { ...state, user }; persist(); emit(); },
  logout() { state = { token: null, user: null }; persist(); emit(); },
  subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
};
