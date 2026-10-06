// Front-end event bus. Mirrors the backend's event bus: modules announce what happened instead of
// importing each other. Example: the wallet (reservation module) emits "complaint:open" and the
// impact module, which owns complaints, reacts to it.
const handlers = new Map();

export const bus = {
  on(event, handler) {
    if (!handlers.has(event)) handlers.set(event, new Set());
    handlers.get(event).add(handler);
    return () => handlers.get(event).delete(handler);
  },
  emit(event, payload) {
    handlers.get(event)?.forEach((handler) => handler(payload));
  },
};
