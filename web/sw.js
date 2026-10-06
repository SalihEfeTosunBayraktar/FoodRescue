// Minimal service worker: network first, cached copy only when offline. API calls are never cached
// (stale reservation data would be worse than an error).
// Önbellek adı. Sürüm numarasını artırmak eski önbelleği geçersiz kılar.
const CACHE = 'foodrescue-shell-v1';

// Yeni sürüm yüklenince beklemeden etkinleşsin.
self.addEventListener('install', () => self.skipWaiting());
// Eski sürümlerin önbelleklerini temizler ve açık sayfaların denetimini devralır.
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()),
  );
});

// Her ağ isteğinde araya girebilir. Buradaki strateji 'önce ağ, çevrimdışıysa önbellek'.
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  // API ve yüklemeler ASLA önbelleğe alınmaz: eski rezervasyon verisi göstermek hata göstermekten
  // daha kötüdür.
  if (request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/uploads/')) return;
  // Yanıtı biz üretiriz.
  event.respondWith(
    // Önce gerçek ağdan dene; başarılıysa kopyasını önbelleğe yaz.
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
        return response;
      })
      // Ağ yoksa son kaydedilen kopyayı göster (çevrimdışı çalışma).
      .catch(() => caches.match(request)),
  );
});
