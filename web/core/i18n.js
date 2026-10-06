import { strings } from '../config/strings.js';

// t('key', { name: 'x' }) -> text from config/strings.js with {name} placeholders filled in.
// t('anahtar', {ad: 'x'}): web/config/strings.js içindeki metni döndürür. Arayüzde gömülü metin
// olmaz; başka dile çeviri tek dosyada yapılır.
export function t(key, params = {}) {
  // Anahtara karşılık gelen şablon metin.
  const template = strings[key];
  // Eksik anahtar geliştirmede gözden kaçmasın diye konsola uyarı yazılır ve ekranda [anahtar]
  // görünür.
  if (template === undefined) {
    console.warn(`[i18n] missing string: ${key}`);
    return `[${key}]`;
  }
  // Düzenli ifade (regex) ile {ad} yer tutucularını bulup params'taki değerle değiştirir.
  return template.replace(/\{(\w+)\}/g, (_, name) => (params[name] ?? `{${name}}`));
}
