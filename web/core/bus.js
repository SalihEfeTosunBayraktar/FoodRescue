// Front-end event bus. Mirrors the backend's event bus: modules announce what happened instead of
// importing each other. Example: the wallet (reservation module) emits "complaint:open" and the
// impact module, which owns complaints, reacts to it.
// olay adı -> dinleyici kümesi.
const handlers = new Map();

// Ön yüzdeki olay yolu, sunucudakinin küçük kopyasıdır: cüzdan (reservation) şikâyet penceresini
// (impact) doğrudan çağırmaz, 'complaint:open' olayını duyurur.
export const bus = {
  // Dinleyici ekler; geri dönen fonksiyon aboneliği iptal eder.
  on(event, handler) {
    if (!handlers.has(event)) handlers.set(event, new Set());
    handlers.get(event).add(handler);
    return () => handlers.get(event).delete(handler);
  },
  // Olayı tüm dinleyicilere iletir. `?.` seçenekli zincir: dinleyici yoksa hata vermez.
  emit(event, payload) {
    handlers.get(event)?.forEach((handler) => handler(payload));
  },
};
