import { strings } from '../config/strings.js';

// t('key', { name: 'x' }) -> text from config/strings.js with {name} placeholders filled in.
export function t(key, params = {}) {
  const template = strings[key];
  if (template === undefined) {
    console.warn(`[i18n] missing string: ${key}`);
    return `[${key}]`;
  }
  return template.replace(/\{(\w+)\}/g, (_, name) => (params[name] ?? `{${name}}`));
}
