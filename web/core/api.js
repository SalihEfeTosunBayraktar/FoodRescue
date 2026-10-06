import { CONFIG } from '../config/app.js';
import { t } from './i18n.js';
import { session } from './session.js';

export class ApiError extends Error {
  constructor(status, message, code = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// FastAPI validation errors arrive as a list of {loc, msg}; business errors as {detail, code}.
function messageFrom(status, payload) {
  if (payload && typeof payload.detail === 'string') return payload.detail;
  if (payload && Array.isArray(payload.detail)) {
    return payload.detail.map((d) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`).join(' | ');
  }
  return t('error.generic', { status });
}

function buildUrl(path, query) {
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value);
  });
  const qs = params.toString();
  return `${CONFIG.apiBase}${path}${qs ? `?${qs}` : ''}`;
}

export async function api(path, { method = 'GET', body, query, form } = {}) {
  const headers = {};
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  let payload;
  if (form) {
    payload = form; // browser sets the multipart boundary itself
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(buildUrl(path, query), { method, headers, body: payload });
  } catch {
    throw new ApiError(0, t('error.network'));
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && session.isLoggedIn) {
      session.logout(); // token expired or revoked
    }
    throw new ApiError(response.status, messageFrom(response.status, data), data?.code ?? null);
  }
  return data;
}
