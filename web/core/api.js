import { CONFIG } from '../config/app.js';
import { t } from './i18n.js';
import { session } from './session.js';

// Sunucudan dönen hatayı durum kodu ve anlaşılır mesajla taşıyan hata sınıfı. Sayfalar try/catch
// ile yakalayıp kullanıcıya gösterir.
export class ApiError extends Error {
  constructor(status, message, code = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// FastAPI validation errors arrive as a list of {loc, msg}; business errors as {detail, code}.
// Sunucu iki biçimde hata döner: iş hatası {detail: 'metin', code} ve doğrulama hatası {detail:
// [{loc, msg}]}. İkisini de okunur tek metne çevirir.
function messageFrom(status, payload) {
  if (payload && typeof payload.detail === 'string') return payload.detail;
  if (payload && Array.isArray(payload.detail)) {
    return payload.detail.map((d) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`).join(' | ');
  }
  return t('error.generic', { status });
}

// Sorgu dizisini (?a=1&b=2) güvenle kurar: URLSearchParams özel karakterleri kodlar, boş değerleri
// atar.
function buildUrl(path, query) {
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value);
  });
  const qs = params.toString();
  return `${CONFIG.apiBase}${path}${qs ? `?${qs}` : ''}`;
}

// Tüm sunucu çağrılarının TEK kapısı. Bilet ekleme, JSON dönüşümü ve hata işleme tek yerde;
// sayfalar fetch ayrıntısını bilmez.
export async function api(path, { method = 'GET', body, query, form } = {}) {
  // İstek başlıkları: bilet varsa Authorization ile eklenir.
  const headers = {};
  // Bearer şeması: 'Authorization: Bearer <bilet>'.
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  let payload;
  // Dosya yüklemede FormData verilir; Content-Type'ı TARAYICI sınır (boundary) bilgisiyle kendisi
  // koyar, elle yazmayız.
  if (form) {
    payload = form; // browser sets the multipart boundary itself
  } else if (body !== undefined) {
    // JSON gövde: nesneyi metne çevirir ve başlığı ekler.
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let response;
  try {
    // fetch ağ düzeyinde başarısız olursa (sunucu kapalı, internet yok) istisna fırlatır; HTTP
    // hataları (404, 500) ise istisna DEĞİL, response.ok=false ile gelir.
    response = await fetch(buildUrl(path, query), { method, headers, body: payload });
  } catch {
    throw new ApiError(0, t('error.network'));
  }

  // 204 No Content'te gövde yoktur; json() çağrısı hata verirdi. Geçersiz JSON için de null döner
  // (catch).
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  // 4xx/5xx durumları.
  if (!response.ok) {
    // Bilet süresi dolmuş veya iptal edilmiş: oturumu kapatırız, router giriş sayfasına
    // yönlendirir.
    if (response.status === 401 && session.isLoggedIn) {
      session.logout(); // token expired or revoked
    }
    // Sayfa bunu try/catch ile yakalar.
    throw new ApiError(response.status, messageFrom(response.status, data), data?.code ?? null);
  }
  return data;
}
