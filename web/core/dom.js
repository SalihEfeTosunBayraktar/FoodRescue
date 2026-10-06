// Tiny DOM helper. Builds elements with createElement/textContent only, so user data can never
// be interpreted as HTML (no innerHTML anywhere in the app).
//
// Ders notu (güvenlik): XSS, kullanıcı girdisinin HTML olarak yorumlanmasıyla oluşur. Metni
// her zaman textContent/createTextNode ile eklemek bu saldırı sınıfını kökten kapatır.

// h(): 'hyperscript' yardımcısı. h('div', {class: 'kart'}, 'metin') gibi bir çağrı <div
// class="kart">metin</div> elemanını KURAR. innerHTML ile metin birleştirmek yerine bu yolu seçtik,
// çünkü kullanıcıdan gelen metin hiçbir zaman HTML olarak yorumlanmaz.
export function h(tag, attrs = {}, ...children) {
  // createElement: bellekte yeni bir DOM elemanı üretir (henüz sayfada değildir).
  const el = document.createElement(tag);
  // `value` özelliği <select> için seçenekler (option) eklendikten SONRA atanmalıdır; o yüzden
  // ertelenir.
  let deferredValue;
  // Nesnenin her (anahtar, değer) çiftini gezer. `?? {}`: attrs null/undefined ise boş nesne
  // kullan.
  for (const [key, value] of Object.entries(attrs ?? {})) {
    // null, undefined ve false değerli özellikleri atla: `disabled: false` gibi koşullu özellikler
    // böyle yazılabilir.
    if (value == null || value === false) continue;
    // `class` JS'te ayrılmış kelime olduğundan DOM'da className özelliğidir.
    if (key === 'class') el.className = value;
    // data-* özellikleri (data-id gibi) nesne olarak verilir.
    else if (key === 'dataset') Object.assign(el.dataset, value);
    // Değer atamasını çocuklar eklendikten sonraya bırakır (aşağıya bakın).
    else if (key === 'value') deferredValue = value; // must be set after <option> children exist
    // onClick, onSubmit gibi anahtarlar olay dinleyicisidir: 'onClick' -> 'click'.
    // addEventListener, var olan dinleyicileri ezmez.
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    // Bu üç özellik HTML özniteliği değil DOM özelliği olarak atanmalıdır (kullanıcı etkileşimiyle
    // değişirler).
    else if (key === 'checked' || key === 'selected' || key === 'disabled') el[key] = true;
    // Geri kalan her şey HTML özniteliğidir (href, type, aria-label...).
    else el.setAttribute(key, value === true ? '' : value);
  }
  // Çocukları ekle (metin, eleman ya da bunların iç içe dizileri).
  append(el, children);
  if (deferredValue !== undefined) el.value = deferredValue;
  return el;
}

// Çocukları elemana ekler. Her türlü girdiyi kabul eder: eleman, metin, sayı, dizi, null.
export function append(el, children) {
  // .flat(Infinity): iç içe dizileri tamamen düzleştirir; böylece h('ul', {}, liste.map(...))
  // çalışır.
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    // Eleman ise olduğu gibi, değilse güvenli METİN düğümü olarak ekler (createTextNode HTML
    // yorumlamaz, XSS'e karşı korur).
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
// Yalnızca sabit ve güvenilir SVG metinleri için (ikonlar). Kullanıcı verisiyle ASLA çağrılmaz.
export function svgFromString(markup) {
  const doc = new DOMParser().parseFromString(markup, 'image/svg+xml');
  return document.importNode(doc.documentElement, true);
}

// debounce: art arda gelen çağrıları bekletip yalnızca SON çağrıyı çalıştırır. Arama kutusunda her
// tuş vuruşunda değil, kullanıcı yazmayı bırakınca istek atmak için.
export function debounce(fn, delay) {
  let timer;
  // Closure: `timer` değişkeni her çağrıda korunur.
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
