// Tiny DOM helper. Builds elements with createElement/textContent only, so user data can never
// be interpreted as HTML (no innerHTML anywhere in the app).
//
// Ders notu (güvenlik): XSS, kullanıcı girdisinin HTML olarak yorumlanmasıyla oluşur. Metni
// her zaman textContent/createTextNode ile eklemek bu saldırı sınıfını kökten kapatır.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  let deferredValue;
  for (const [key, value] of Object.entries(attrs ?? {})) {
    if (value == null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key === 'value') deferredValue = value; // must be set after <option> children exist
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'checked' || key === 'selected' || key === 'disabled') el[key] = true;
    else el.setAttribute(key, value === true ? '' : value);
  }
  append(el, children);
  if (deferredValue !== undefined) el.value = deferredValue;
  return el;
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

// Replaces all children. Unlike Element.replaceChildren, null/false are skipped and arrays are
// flattened (replaceChildren(null) would insert the text "null", and an array becomes one string).
export function setChildren(el, ...children) {
  el.replaceChildren();
  return append(el, children);
}

export function clear(el) {
  el.replaceChildren();
  return el;
}

// Only ever called with static, trusted markup (icon paths) - never with user data.
export function svgFromString(markup) {
  const doc = new DOMParser().parseFromString(markup, 'image/svg+xml');
  return document.importNode(doc.documentElement, true);
}

export function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
