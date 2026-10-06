import { CONFIG } from '../../config/app.js';
import { api } from '../../core/api.js';
import { h } from '../../core/dom.js';
import { icon } from '../../core/icons.js';
import { t } from '../../core/i18n.js';
import { createLocationPicker, currentPosition, loadLeaflet, mapUnavailable } from '../../core/map.js';
import { navigate } from '../../core/router.js';
import { session } from '../../core/session.js';
import { button, field, notice, toast, withBusy } from '../../core/ui.js';

const REVIEWED_ROLES = ['DONOR', 'SHELTER'];

function goAfterLogin(next, role) {
  navigate(next || CONFIG.homeByRole[role] || '#/');
}

export function loginPage({ query }) {
  const error = h('div');
  const email = h('input', { type: 'email', name: 'email', required: true, autocomplete: 'username' });
  const password = h('input', { type: 'password', name: 'password', required: true, autocomplete: 'current-password' });
  const submit = button(t('auth.login.submit'), { type: 'submit', iconName: 'lock' });

  const form = h('form', { class: 'card form', onSubmit: async (event) => {
    event.preventDefault();
    error.replaceChildren();
    await withBusy(submit, async () => {
      try {
        const data = await api('/auth/login', { method: 'POST', body: { email: email.value, password: password.value } });
        session.login(data.access_token, data.user);
        goAfterLogin(query.next, data.user.role);
      } catch (err) {
        error.replaceChildren(notice(err.message, 'error'));
      }
    });
  } },
    h('h1', {}, t('auth.login.title')),
    field(t('auth.email'), email),
    field(t('auth.password'), password),
    error,
    submit,
    h('p', { class: 'muted center' }, t('auth.login.noAccount'), ' ', h('a', { href: '#/register' }, t('auth.login.register'))),
  );
  return h('section', { class: 'narrow' }, form);
}

const ROLE_CARDS = [
  { role: 'BENEFICIARY', iconName: 'heart' },
  { role: 'DONOR', iconName: 'building' },
  { role: 'SHELTER', iconName: 'paw' },
];

export function registerPage({ onCleanup }) {
  const root = h('section', { class: 'narrow' });
  let picker = null;
  onCleanup(() => picker?.destroy());

  function chooseRole() {
    root.replaceChildren(
      h('h1', {}, t('auth.register.title')),
      h('p', { class: 'muted' }, t('auth.register.chooseRole')),
      h('div', { class: 'role-grid' },
        ROLE_CARDS.map(({ role, iconName }) => h('button', { class: 'role-card', type: 'button', onClick: () => showForm(role) },
          icon(iconName, { size: 28 }),
          h('strong', {}, t(`role.${role}`)),
          h('span', {}, t(`auth.register.roleHint.${role}`))))),
      h('p', { class: 'muted center' }, t('auth.register.haveAccount'), ' ', h('a', { href: '#/login' }, t('auth.login.submit'))),
    );
  }

  function showForm(role) {
    const needsOrg = REVIEWED_ROLES.includes(role);
    const needsMap = role === 'DONOR';
    const location = { lat: null, lon: null };
    const error = h('div');
    const inputs = {
      full_name: h('input', { name: 'full_name', required: true, minlength: 2, autocomplete: 'name' }),
      email: h('input', { type: 'email', name: 'email', required: true, autocomplete: 'username' }),
      password: h('input', { type: 'password', name: 'password', required: true, minlength: 8, autocomplete: 'new-password' }),
      phone: h('input', { type: 'tel', name: 'phone', autocomplete: 'tel' }),
      organization_name: h('input', { name: 'organization_name', required: needsOrg }),
      license_number: h('input', { name: 'license_number', required: needsOrg }),
      address: h('input', { name: 'address', required: needsOrg }),
    };
    const coords = h('small', { class: 'field-hint' }, t('auth.register.pickLocation'));
    const mapBox = h('div', { class: 'picker-map' });
    const submit = button(t('auth.register.submit'), { type: 'submit' });

    const setLocation = ({ lat, lon }) => {
      location.lat = lat; location.lon = lon;
      coords.textContent = t('auth.register.locationSet', { lat: lat.toFixed(5), lon: lon.toFixed(5) });
    };

    const locationBlock = needsMap ? h('div', { class: 'field' },
      h('span', { class: 'field-label' }, t('auth.register.location')),
      mapBox, coords,
      button(t('auth.register.useMyLocation'), { variant: 'ghost', iconName: 'locate', onClick: async () => {
        try {
          const pos = await currentPosition();
          picker?.set(pos.lat, pos.lon);
        } catch (err) { toast(err.message, 'error'); }
      } })) : null;

    const form = h('form', { class: 'card form', onSubmit: async (event) => {
      event.preventDefault();
      error.replaceChildren();
      if (needsMap && location.lat === null) { error.replaceChildren(notice(t('auth.register.locationRequired'), 'error')); return; }
      const body = { role };
      Object.entries(inputs).forEach(([key, input]) => { if (input.value.trim()) body[key] = input.value.trim(); });
      if (needsMap) { body.latitude = location.lat; body.longitude = location.lon; }
      await withBusy(submit, async () => {
        try {
          const user = await api('/auth/register', { method: 'POST', body });
          if (user.status === 'PENDING_REVIEW') {
            toast(t('auth.register.pending'), 'success');
            navigate('#/login');
          } else {
            const data = await api('/auth/login', { method: 'POST', body: { email: body.email, password: body.password } });
            session.login(data.access_token, data.user);
            toast(t('auth.register.welcome'), 'success');
            goAfterLogin(null, data.user.role);
          }
        } catch (err) { error.replaceChildren(notice(err.message, 'error')); }
      });
    } },
      h('h1', {}, t(`role.${role}`)),
      field(t('auth.fullName'), inputs.full_name),
      field(t('auth.email'), inputs.email),
      field(t('auth.password'), inputs.password, t('auth.passwordHint')),
      field(t('auth.phone'), inputs.phone),
      needsOrg ? [
        field(t('auth.organization'), inputs.organization_name),
        field(t('auth.license'), inputs.license_number, t('auth.licenseHint')),
        field(t('auth.address'), inputs.address),
      ] : null,
      locationBlock,
      needsOrg ? notice(t('auth.register.reviewNotice'), 'info') : null,
      error,
      h('div', { class: 'row' }, button(t('common.back'), { variant: 'ghost', onClick: chooseRole }), submit),
    );
    root.replaceChildren(form);

    if (needsMap) {
      loadLeaflet().then(async () => {
        picker = await createLocationPicker(mapBox, { onChange: setLocation });
      }).catch(() => mapBox.replaceWith(mapUnavailable()));
    }
  }

  chooseRole();
  return root;
}
