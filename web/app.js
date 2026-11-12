// Hatua on the web. One page, three roles: the signed-in account decides which pages
// exist. All text from the server is put on the page with textContent (never as HTML),
// so nothing a person typed can run as code. The look follows the phone app: the same
// colours and fonts, plum page headers with a wavy edge, round pastel icons.
'use strict';

const API = location.origin; // the backend serves this site at /web
let token = sessionStorage.getItem('hatua.token');
let me = null;

// ---------- language: English or Swahili ----------
//
// The Swahili words come from i18n/sw.json, the file the app and the backend read too,
// served as /i18n/sw.js just before this file, so they are ready before any text is made.
// The choice is kept in this browser and on the account (so the server's questions and
// results match). Changing it reloads the page, so every word, even in fixed lists made
// when the page loads, is in one language.

const SW = window.HATUA_SW || {};
let chosenLang = null;
try { chosenLang = localStorage.getItem('hatua.lang'); } catch (_) { /* not kept: fine */ }
const LANG = chosenLang === 'sw' ? 'sw' : 'en';
const LOCALE = LANG === 'sw' ? 'sw-KE' : 'en-GB';
document.documentElement.lang = LANG;

/** text in the chosen language, with {name}-style gaps filled from params. English when
 * there is no Swahili yet. */
function t(text, params) {
  let out = LANG === 'sw' && SW[text] ? SW[text] : text;
  if (params) out = out.replace(/\{(\w+)\}/g, (gap, k) => (k in params ? String(params[k]) : gap));
  return out;
}

function setLanguage(lang) {
  try { localStorage.setItem('hatua.lang', lang); } catch (_) { /* not kept: fine */ }
  const save = token ? api('/auth/me', { method: 'PATCH', body: { language: lang } }).catch(() => {}) : Promise.resolve();
  save.finally(() => location.reload());
}

/** Switches to the other language. Its label is in that language, so a person who reads
 * only that language can find it. */
function languageButton() {
  const other = LANG === 'sw' ? 'en' : 'sw';
  return h('button', { type: 'button', class: 'lang-toggle', lang: other, onclick: () => setLanguage(other),
    title: other === 'sw' ? 'Tumia Kiswahili' : 'Use English' }, icon('translate'), other === 'sw' ? 'Kiswahili' : 'English');
}

// ---------- small helpers ----------

/** Build an element: h('p', {class: 'muted'}, 'text', childElement, ...). */
function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'class') el.className = v;
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

/** A rounded line icon (Material Symbols, the family the app's icons come from). */
const icon = (name) => h('span', { class: 'material-symbols-rounded', 'aria-hidden': 'true' }, name);

/** SVG from a fixed string written in this file (never from the server). */
function svg(markup) {
  const tpl = document.createElement('template');
  tpl.innerHTML = markup.trim();
  return tpl.content.firstChild;
}

// Sprout, the app's mascot: a yellow seedling with two leaves.
const SPROUT = `<svg viewBox="0 0 120 130" class="sprout" aria-hidden="true">
  <path d="M60 40 C58 30 60 22 64 16" stroke="#3a1f36" stroke-width="4" fill="none" stroke-linecap="round"/>
  <path d="M63 20 C50 6 30 8 26 20 C38 30 54 28 63 20Z" fill="#6cc3a4" stroke="#3a1f36" stroke-width="4" stroke-linejoin="round"/>
  <path d="M64 18 C76 2 98 6 100 18 C88 30 72 28 64 18Z" fill="#6cc3a4" stroke="#3a1f36" stroke-width="4" stroke-linejoin="round"/>
  <ellipse cx="60" cy="80" rx="36" ry="40" fill="#f9be3d" stroke="#3a1f36" stroke-width="4"/>
  <circle cx="47" cy="76" r="4.5" fill="#3a1f36"/><circle cx="73" cy="76" r="4.5" fill="#3a1f36"/>
  <path d="M50 90 Q60 99 70 90" stroke="#3a1f36" stroke-width="4" fill="none" stroke-linecap="round"/>
  <circle cx="40" cy="88" r="5" fill="#f8afa8" opacity=".8"/><circle cx="80" cy="88" r="5" fill="#f8afa8" opacity=".8"/>
  <path d="M46 118 L44 126 M74 118 L76 126" stroke="#3a1f36" stroke-width="4" stroke-linecap="round"/>
</svg>`;
const MARK = `<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="23" r="13" fill="#f9be3d" stroke="#3a1f36" stroke-width="3"/>
  <path d="M20 10 C14 2 6 4 5 9 C11 14 17 13 20 10Z M20 10 C26 2 34 4 35 9 C29 14 23 13 20 10Z" fill="#6cc3a4" stroke="#3a1f36" stroke-width="2.5" stroke-linejoin="round"/></svg>`;
const WAVE = `<svg class="wave" viewBox="0 0 1200 36" preserveAspectRatio="none" aria-hidden="true">
  <path d="M0 18 Q25 0 50 18 T100 18 T150 18 T200 18 T250 18 T300 18 T350 18 T400 18 T450 18 T500 18 T550 18 T600 18 T650 18 T700 18 T750 18 T800 18 T850 18 T900 18 T950 18 T1000 18 T1050 18 T1100 18 T1150 18 T1200 18 V36 H0Z" fill="currentColor"/></svg>`;

// ---------- light and dark mode ----------
//
// Like the app: follows the device until the person picks a mode, then remembers it in
// this browser. index.html applies the saved mode before the page draws, so it never
// flashes the wrong colours. Storage can be blocked; the page still works without it.

function isDark() {
  const set = document.documentElement.dataset.theme;
  return set ? set === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
}

function themeButton() {
  const b = h('button', { type: 'button', class: 'theme-toggle',
    'aria-label': isDark() ? t('Use light mode') : t('Use dark mode'),
    title: isDark() ? t('Use light mode') : t('Use dark mode') }, icon(isDark() ? 'light_mode' : 'dark_mode'));
  b.addEventListener('click', () => {
    const next = isDark() ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('hatua.theme', next); } catch (_) { /* not kept: fine */ }
    // Swap in a button with the right icon, and redraw Google's button in matching colours.
    b.replaceWith(themeButton());
    const google = document.querySelector('.google');
    if (google && !google.hidden && window.google) googleButton(google).catch(() => {});
  });
  return b;
}
const setToggle = () => document.getElementById('theme').replaceChildren(languageButton(), themeButton());

const main = () => document.getElementById('main');
const heroBox = () => document.getElementById('hero');

/**
 * Show a page: a plum header (title, one line under it, optional back link and chips)
 * and the content below. Pages are nested lists of elements, so flatten all the way.
 */
function page(head, ...nodes) {
  heroBox().replaceChildren(h('section', { class: 'hero' },
    h('div', { class: 'inner' },
      h('div', { class: 'text' },
        head.back ? h('a', { class: 'back', href: head.back[0] }, icon('arrow_back'), head.back[1]) : null,
        h('h1', {}, head.title),
        head.sub ? h('p', {}, head.sub) : null,
        head.chips ? h('div', { class: 'chips' }, head.chips) : null),
      svg(SPROUT)),
    svg(WAVE)));
  main().className = '';
  main().replaceChildren(...nodes.flat(Infinity).filter(Boolean));
}

let toastTimer;
function toast(text) {
  const box = document.getElementById('toast');
  box.textContent = text;
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.hidden = true; }, 4000);
}

class ApiError extends Error {
  constructor(status, message, detail) { super(message); this.status = status; this.detail = detail; }
}

async function api(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (_) {
    throw new ApiError(0, t('No connection. Check your internet and try again.'));
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = text; }
  if (res.ok) return data;
  if (res.status === 401 && token) { signOut(); }
  const detail = data && data.detail;
  let message = t('Something went wrong. Please try again.');
  if (typeof detail === 'string') message = detail;
  else if (Array.isArray(detail) && detail[0] && detail[0].msg) message = detail[0].msg.replace('Value error, ', '');
  message = message.charAt(0).toUpperCase() + message.slice(1);
  throw new ApiError(res.status, message, detail);
}

/** Run an action from a button: disables it meanwhile and shows any error. */
async function run(button, action) {
  if (button) button.disabled = true;
  try { await action(); } catch (e) { toast(e.message || t('Something went wrong.')); } finally {
    if (button) button.disabled = false;
  }
}

const fmtDate = (s) => s ? new Date(s).toLocaleDateString(LOCALE, { day: 'numeric', month: 'short', year: 'numeric' }) : '';
const fmtTime = (s) => s ? new Date(s).toLocaleString(LOCALE, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
function ageLabel(m) {
  if (m < 24) return t(m === 1 ? '1 month' : '{n} months', { n: m });
  const y = Math.floor(m / 12), r = m % 12;
  if (r === 0) return t('{n} years', { n: y });
  return t(r === 1 ? '{y} years 1 month' : '{y} years {m} months', { y, m: r });
}
const RISK = { low: t('On track'), medium: t('Keep an eye'), high: t('Needs a check') };
const riskChip = (level) => h('span', { class: 'chip ' + level }, RISK[level] || level);
const OUTCOMES = { refer_to_facility: t('Refer to facility'), reviewed_not_concerning: t('Reviewed, not concerning'), unreachable: t('Could not reach caregiver') };
const CARE = { low_birth_weight: t('Weighed less than 2.5 kg at birth'), multiple_birth: t('Born as a twin or triplet'), short_birth_spacing: t('Born less than 2 years after the child before') };
const ROLE = { caregiver: t('Caregiver'), chw: t('Community health worker'), admin: t('Administrator') };
// The four areas, with the app's colours and icons.
const DOMAIN_ICON = { motor: 'directions_walk', language: 'chat_bubble', cognitive: 'lightbulb', social_emotional: 'group' };

// The child's animal, as in the app: the chosen one, or a fixed default for the child.
const AVATARS = ['lion', 'elephant', 'giraffe', 'zebra', 'hippo', 'monkey', 'cheetah', 'rhino'];
function avatar(childId, avatarId) {
  const id = AVATARS.includes(avatarId) ? avatarId
    : AVATARS[[...childId].reduce((a, c) => a + c.charCodeAt(0), 0) % AVATARS.length];
  return h('img', { class: 'avatar', src: 'avatars/' + id + '.svg', alt: '' });
}
const initial = (name) => h('span', { class: 'initial', 'aria-hidden': 'true' }, (name || '?').trim().charAt(0).toUpperCase());
const person = (pic, name, sub) => h('div', { class: 'person' }, pic,
  h('div', {}, name, sub ? h('div', { class: 'muted', style: 'font-weight:400' }, sub) : null));

function field(label, input) { return h('div', {}, h('label', {}, label), input); }
function table(headers, rows) {
  return h('div', { class: 'table-wrap' },
    h('table', {}, h('thead', {}, h('tr', {}, headers.map((x) => h('th', {}, x)))), h('tbody', {}, rows)));
}
function empty(text, ico = 'eco') { return h('div', { class: 'empty' }, icon(ico), text); }
const note = (...content) => h('div', { class: 'note' }, icon('info'), h('div', {}, content));
const tile = (ico, color, n, label, opts = {}) => h(opts.href ? 'a' : 'div',
  { class: 'tile' + (opts.warn && n > 0 ? ' warn' : ''), href: opts.href },
  h('span', { class: 'ico ' + color }, icon(ico)), h('div', {}, h('b', {}, n), h('span', { class: 'lbl' }, label)));
/** A table row that opens a page, by mouse or by keyboard. */
const linkRow = (hash, ...cells) => h('tr', {
  class: 'click', tabindex: 0, onclick: () => { location.hash = hash; },
  onkeydown: (ev) => { if (ev.key === 'Enter') location.hash = hash; } }, cells);

// ---------- sign in ----------

function signOut() {
  token = null; me = null;
  sessionStorage.removeItem('hatua.token');
  document.getElementById('top').hidden = true;
  location.hash = '';
  loginPage();
}

/** The sign-in screen: the plum side with Sprout, and the form. */
function signinScreen(form) {
  document.getElementById('top').hidden = true;
  heroBox().replaceChildren();
  main().className = 'bare';
  main().replaceChildren(h('div', { class: 'signin' },
    h('div', { class: 'corner' }, languageButton(), themeButton()),
    h('div', { class: 'side' },
      svg(SPROUT),
      h('h1', {}, t('Every step counts')),
      h('p', {}, t('Hatua helps families notice how their child is growing, and makes sure a health worker follows up when a child needs support.')),
      h('ul', { class: 'points' },
        h('li', {}, h('span', { class: 'ico bg-sky' }, icon('child_care')), t('A 5-minute check for children under five')),
        h('li', {}, h('span', { class: 'ico bg-sun' }, icon('health_and_safety')), t('Health workers follow up on flagged results')),
        h('li', {}, h('span', { class: 'ico bg-blush' }, icon('chat_bubble')), t('Questions answered by your own health worker')))),
    h('div', { class: 'form-side' }, form)));
}

function loginPage(message) {
  const email = h('input', { type: 'email', autocomplete: 'username', required: true, placeholder: 'amina@example.com' });
  const password = h('input', { type: 'password', autocomplete: 'current-password', required: true });
  const button = h('button', { type: 'submit', class: 'full' }, t('Sign in'));
  const google = h('div', { class: 'google', hidden: true },
    h('p', { class: 'or' }, 'or'), h('div', { id: 'google-button' }));
  const form = h('form', { onsubmit: (ev) => {
    ev.preventDefault();
    run(button, async () => {
      try {
        await signedIn(await api('/auth/login', { method: 'POST', body: { email: email.value, password: password.value } }));
      } catch (e) {
        if (e.status === 403 && e.detail && e.detail.needs_verification) { checkEmailPage(e.detail.email, true); return; }
        throw e;
      }
    });
  } },
    h('a', { class: 'brand', href: '#' }, svg(MARK), 'Hatua'),
    h('h2', {}, t('Welcome back')),
    message ? note(message) : null,
    field(t('Email'), email), field(t('Password'), password), showPassword(password),
    h('p', { style: 'text-align:right;margin:.5rem 0 0' },
      h('button', { type: 'button', class: 'link', onclick: () => forgotPage(email.value) }, t('Forgot password?'))),
    button, google,
    h('p', { class: 'switch' }, t('New to Hatua? '),
      h('button', { type: 'button', class: 'link', onclick: () => registerPage() }, t('Create an account'))));
  signinScreen(form);
  email.focus();
  googleButton(google).catch(() => { /* no Google: email sign-in still works */ });
}

/** A "Show the password" tick box under one or more password boxes, as in the app. */
function showPassword(...inputs) {
  const box = h('input', { type: 'checkbox' });
  box.addEventListener('change', () => inputs.forEach((i) => { i.type = box.checked ? 'text' : 'password'; }));
  return h('label', { class: 'show-pw' }, box, inputs.length > 1 ? t('Show the passwords') : t('Show the password'));
}

/**
 * Create an account. Like the app, this always makes a caregiver account (health workers
 * and administrators are added by an administrator). There is no session until the
 * person opens the link emailed to them, then they sign in.
 */
function registerPage() {
  const name = h('input', { required: true, maxlength: 100, autocomplete: 'name', placeholder: 'Amina Wanjiru' });
  const email = h('input', { type: 'email', required: true, autocomplete: 'email', placeholder: 'amina@example.com' });
  const phone = h('input', { required: true, autocomplete: 'tel', placeholder: '0712 345 678' });
  const password = h('input', { type: 'password', required: true, minlength: 6, autocomplete: 'new-password' });
  const again = h('input', { type: 'password', required: true, minlength: 6, autocomplete: 'new-password' });
  const button = h('button', { type: 'submit', class: 'full' }, t('Create my account'));
  const form = h('form', { onsubmit: (ev) => {
    ev.preventDefault();
    run(button, async () => {
      if (password.value !== again.value) throw new Error(t('The two passwords are not the same.'));
      const r = await api('/auth/register', { method: 'POST', body: {
        full_name: name.value.trim(), email: email.value.trim(), phone_number: phone.value, password: password.value } });
      checkEmailPage(r.email, false);
    });
  } },
    h('a', { class: 'brand', href: '#' }, svg(MARK), 'Hatua'),
    h('h2', {}, t('Create your account')),
    h('p', { class: 'muted' }, t('For parents and caregivers. You can use the same account in the Hatua app.')),
    field(t('Your name'), name), field(t('Email'), email), field(t('Phone number'), phone),
    h('p', { class: 'muted', style: 'margin:.3rem 0 0' }, t('Your community health worker uses it to find you.')),
    field(t('Password'), password), field(t('Password again'), again), showPassword(password, again),
    h('p', { class: 'muted', style: 'margin:.3rem 0 .9rem' }, t('At least 6 characters.')),
    button,
    h('p', { class: 'switch' }, t('Already have an account? '),
      h('button', { type: 'button', class: 'link', onclick: () => loginPage() }, t('Sign in'))));
  signinScreen(form);
  name.focus();
}

/** After signing up, or signing in before confirming: open the emailed link, or get it again. */
function checkEmailPage(address, fromSignIn) {
  const again = h('button', { type: 'button', class: 'link' }, t('Send the email again'));
  again.addEventListener('click', () => run(again, async () => {
    await api('/auth/verify/resend', { method: 'POST', body: { email: address } });
    toast(t('Sent again to {email}. Look in your spam folder too.', { email: address }));
  }));
  signinScreen(h('form', { onsubmit: (e) => e.preventDefault() },
    h('a', { class: 'brand', href: '#' }, svg(MARK), 'Hatua'),
    h('h2', {}, fromSignIn ? t('Confirm your email first') : t('Check your email')),
    note(t('We sent a link to {email}. Open it to confirm your email, then come back here and sign in.', { email: address })),
    h('p', { class: 'muted' }, t('The link works for a limited time. If you cannot find the email, look in your spam folder.')),
    h('button', { type: 'button', class: 'full', onclick: () => loginPage() }, t('Back to sign in')),
    h('p', { class: 'switch' }, again)));
}

/**
 * Forgot password: emails a link to a page where the person chooses a new password
 * (served by the backend at /auth/password/reset). The answer is the same whether or
 * not the email has an account, so this cannot be used to find out who has one.
 */
function forgotPage(prefill) {
  const email = h('input', { type: 'email', autocomplete: 'username', required: true, placeholder: 'amina@example.com', value: prefill || null });
  const button = h('button', { type: 'submit', class: 'full' }, t('Send the link'));
  const back = h('p', { style: 'text-align:center' }, h('button', { type: 'button', class: 'link', onclick: () => loginPage() }, t('Back to sign in')));
  const form = h('form', { onsubmit: (ev) => {
    ev.preventDefault();
    run(button, async () => {
      const address = email.value.trim().toLowerCase();
      await api('/auth/password/forgot', { method: 'POST', body: { email: address } });
      signinScreen(h('form', { onsubmit: (e) => e.preventDefault() },
        h('a', { class: 'brand', href: '#' }, svg(MARK), 'Hatua'),
        h('h2', {}, t('Check your email')),
        note(t('If {email} has a Hatua account, we sent it a link to choose a new password. The link works for one hour and only once.', { email: address })),
        h('p', { class: 'muted' }, t("If you cannot find it, look in your spam folder. Then come back here and sign in with your new password.")),
        h('button', { type: 'button', class: 'full', onclick: () => loginPage() }, t('Back to sign in')),
        h('p', { style: 'text-align:center' }, h('button', { type: 'button', class: 'link', onclick: () => forgotPage(address) }, t('Send the link again')))));
    });
  } },
    h('a', { class: 'brand', href: '#' }, svg(MARK), 'Hatua'),
    h('h2', {}, t('Forgot your password?')),
    h('p', { class: 'muted' }, t('Enter the email you sign in with. We will email you a link to choose a new one.')),
    field(t('Email'), email), button, back);
  signinScreen(form);
  email.focus();
}

/** Keeps the session from /auth/login or /auth/google and opens the right pages. */
async function signedIn(session) {
  token = session.access_token;
  sessionStorage.setItem('hatua.token', token);
  // A language picked on the sign-in page goes onto the account; otherwise start()
  // takes the account's language.
  if (chosenLang) await api('/auth/me', { method: 'PATCH', body: { language: LANG } }).catch(() => {});
  await start();
}

// ---------- Google sign-in (Google Identity Services) ----------
//
// Google's button gives an ID token for the same web client the phone app uses, and
// /auth/google checks it exactly as for the app. A Google account Hatua has not seen
// before needs a phone number once (the backend answers 428), so CHWs can find them.

let gsiLoaded = null;
function loadGsi() {
  gsiLoaded = gsiLoaded || new Promise((ok, fail) => {
    const s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.onload = ok;
    s.onerror = () => { gsiLoaded = null; fail(new Error(t('Google sign-in could not load'))); };
    document.head.append(s);
  });
  return gsiLoaded;
}

async function googleButton(box) {
  const { google_client_id: clientId } = await api('/auth/config');
  if (!clientId) return;
  await loadGsi();
  window.google.accounts.id.initialize({ client_id: clientId, callback: (r) => withGoogle(r.credential) });
  window.google.accounts.id.renderButton(document.getElementById('google-button'),
    { theme: isDark() ? 'filled_black' : 'outline', size: 'large', shape: 'pill', text: 'signin_with', width: 320 });
  box.hidden = false;
}

async function withGoogle(idToken) {
  try {
    await signedIn(await api('/auth/google', { method: 'POST', body: { id_token: idToken } }));
  } catch (e) {
    if (e.status === 428 && e.detail && e.detail.needs_phone) { addPhonePage(idToken, e.detail); return; }
    toast(e.message || t('Google sign-in did not work. Please try again.'));
  }
}

/** First Google sign-in: the one-time phone number step, then the account is made. */
function addPhonePage(idToken, who) {
  const phone = h('input', { required: true, placeholder: '0712 345 678', autocomplete: 'tel' });
  const button = h('button', { type: 'submit', class: 'full' }, t('Create my account'));
  const form = h('form', { onsubmit: (ev) => {
    ev.preventDefault();
    run(button, async () => {
      try {
        await signedIn(await api('/auth/google', { method: 'POST', body: { id_token: idToken, phone_number: phone.value } }));
      } catch (e) {
        // Google's token is short-lived: if it ran out, start again.
        if (e.status === 401) { loginPage(t('That took a while. Please sign in with Google again.')); return; }
        throw e;
      }
    });
  } },
    h('a', { class: 'brand', href: '#' }, svg(MARK), 'Hatua'),
    h('h2', {}, t('One more step')),
    h('p', { class: 'muted' }, t('Welcome, {name}. Add your phone number to create your Hatua account for {email}.', { name: who.full_name, email: who.email })),
    field(t('Your phone number'), phone),
    h('p', { class: 'muted' }, t('Your community health worker uses it to find you and link to your account.')),
    button,
    h('p', { style: 'text-align:center' }, h('button', { type: 'button', class: 'link', onclick: () => loginPage() }, t('Back to sign in'))));
  signinScreen(form);
  phone.focus();
}

// ---------- administrator ----------

async function adminOverview() {
  const s = await api('/admin/summary');
  const n = (value, label) => h('div', {}, h('b', {}, value), h('span', {}, label));
  page({ title: t('Overview'), sub: t('How Hatua is being used, in totals. Individual children are only seen by their caregiver and health worker.') },
    h('div', { class: 'tiles' },
      tile('family_restroom', 'bg-sun', s.users.caregiver, t('Caregivers'), { href: '#users' }),
      tile('medical_services', 'bg-sky', s.users.chw, t('Health workers'), { href: '#users' }),
      tile('child_care', 'bg-blush', s.children, t('Children')),
      tile('pending_actions', 'bg-plum', s.awaiting_review, t('Waiting for a health worker'), { warn: true })),
    h('h2', {}, t('Checks')),
    h('div', { class: 'numbers' },
      n(s.assessments, t('Checks completed')), n(s.by_risk_level.low, t('On track')),
      n(s.by_risk_level.medium, t('Keep an eye')), n(s.by_risk_level.high, t('Needs a check')),
      n(s.flagged_for_chw, t('Sent to a health worker'))),
    h('div', { class: 'split' },
      h('div', { class: 'card' }, h('h3', {}, t('Outcomes recorded by health workers')),
        table([t('Outcome'), t('Count')], Object.entries(OUTCOMES).map(([k, label]) => h('tr', {}, h('td', {}, label), h('td', {}, s.outcomes[k]))))),
      h('div', { class: 'card' }, h('h3', {}, t('Flags')),
        table([t('Flag'), t('Count')], [
          h('tr', {}, h('td', {}, t('Hearing, eyes or growth need a look')), h('td', {}, s.red_flags || 0)),
          h('tr', {}, h('td', {}, t('Answers that do not fit together')), h('td', {}, s.anomaly_flags))]))));
}

async function adminUsers() {
  const users = await api('/admin/users');
  const chws = new Map(users.filter((u) => u.role === 'chw').map((u) => [u.user_id, u.full_name + (u.email ? ' (' + u.email + ')' : '')]));
  const search = h('input', { type: 'search', placeholder: t('Search by name, email or phone'), 'aria-label': t('Search users') });
  const body = h('tbody');
  const draw = () => {
    const q = search.value.trim().toLowerCase();
    body.replaceChildren(...users
      .filter((u) => !q || [u.full_name, u.email, u.phone_number].some((x) => (x || '').toLowerCase().includes(q)))
      .map((u) => h('tr', {},
        h('td', {}, person(initial(u.full_name), u.full_name, u.email || '')),
        h('td', {}, ROLE[u.role]), h('td', {}, u.phone_number),
        h('td', {}, u.role === 'caregiver' ? (chws.get(u.linked_chw_id) || t('No health worker yet')) : ''),
        h('td', {}, h('span', { class: 'chip ' + (u.is_active ? 'low' : 'flag') }, u.is_active ? t('Active') : t('Deactivated'))),
        h('td', {}, u.user_id === me.user_id ? '' : h('button', { class: 'small second', onclick: (ev) => run(ev.target, async () => {
          await api('/admin/users/' + u.user_id, { method: 'PATCH', body: { is_active: !u.is_active } });
          toast(t(u.is_active ? '{name} was deactivated.' : '{name} was reactivated.', { name: u.full_name }));
          await adminUsers();
        }) }, u.is_active ? t('Deactivate') : t('Reactivate'))))));
  };
  search.addEventListener('input', draw);

  const name = h('input', { required: true }), email = h('input', { type: 'email', required: true });
  const phone = h('input', { required: true, placeholder: '0712 345 678' });
  const password = h('input', { required: true, minlength: 6, placeholder: t('At least 6 characters') });
  const role = h('select', {}, h('option', { value: 'chw' }, t('Community health worker')),
    h('option', { value: 'admin' }, t('Administrator')), h('option', { value: 'caregiver' }, t('Caregiver')));
  const add = h('button', { type: 'submit' }, icon('person_add'), t('Add user'));
  const form = h('form', { class: 'card', onsubmit: (ev) => {
    ev.preventDefault();
    run(add, async () => {
      await api('/admin/users', { method: 'POST', body: { full_name: name.value, email: email.value, phone_number: phone.value, password: password.value, role: role.value } });
      toast(t('{name} was added.', { name: name.value }));
      await adminUsers();
    });
  } }, h('h3', {}, t('Add a user')),
    h('div', { class: 'row' }, field(t('Full name'), name), field(t('Email (used to sign in)'), email), field(t('Phone number'), phone)),
    h('div', { class: 'row' }, field(t('Temporary password'), password), field(t('Role'), role), add),
    h('p', { class: 'muted' }, t('Caregivers usually sign up themselves in the app. Give the person their temporary password; they can change it in their profile.')));

  page({ title: t('Users'), sub: t('Everyone with a Hatua account. Deactivated accounts cannot sign in; their records stay.') },
    h('div', { class: 'card' }, search,
      h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {},
        [t('Name'), t('Role'), t('Phone'), t('Health worker'), t('Status'), ''].map((x) => h('th', {}, x)))), body))),
    form);
  draw();
}

async function adminLinking() {
  const users = await api('/admin/users');
  const chws = users.filter((u) => u.role === 'chw' && u.is_active);
  const caregivers = users.filter((u) => u.role === 'caregiver' && u.is_active)
    .sort((a, b) => (a.linked_chw_id ? 1 : 0) - (b.linked_chw_id ? 1 : 0) || a.full_name.localeCompare(b.full_name));
  const unlinked = caregivers.filter((c) => !c.linked_chw_id).length;
  const rows = caregivers.map((c) => {
    const pick = h('select', { 'aria-label': t('Health worker for {name}', { name: c.full_name }) }, h('option', { value: '' }, t('No health worker')),
      // Name and email: two health workers can share a name.
      chws.map((w) => h('option', { value: w.user_id, selected: w.user_id === c.linked_chw_id }, w.full_name + (w.email ? ' (' + w.email + ')' : ''))));
    pick.addEventListener('change', () => run(pick, async () => {
      await api('/admin/users/' + c.user_id + '/chw', { method: 'PUT', body: { chw_id: pick.value || null } });
      toast(t(pick.value ? '{name} is now linked.' : '{name} is no longer linked.', { name: c.full_name }));
      await adminLinking();
    }));
    return h('tr', {}, h('td', {}, person(initial(c.full_name), c.full_name, c.email || '')), h('td', {}, c.phone_number), h('td', {}, pick));
  });
  page({ title: t('Linking'), sub: t('Each caregiver needs a health worker, or their flagged results and questions reach nobody.') },
    unlinked ? note(t(unlinked === 1 ? '1 caregiver has no health worker yet. They are listed first.' : '{n} caregivers have no health worker yet. They are listed first.', { n: unlinked })) : null,
    h('div', { class: 'card' }, caregivers.length
      ? table([t('Caregiver'), t('Phone'), t('Health worker')], rows) : empty(t('No caregivers yet.'), 'family_restroom')));
}

async function adminReports() {
  const start = h('input', { type: 'date' }), end = h('input', { type: 'date' });
  const out = h('div');
  const go = h('button', {}, t('Show report'));
  const draw = () => run(go, async () => {
    const q = new URLSearchParams();
    if (start.value) q.set('start', start.value);
    if (end.value) q.set('end', end.value);
    const s = await api('/admin/summary' + (q.toString() ? '?' + q : ''));
    const line = (label, n) => h('tr', {}, h('td', {}, label), h('td', {}, h('b', {}, n)));
    out.replaceChildren(h('div', { class: 'card' },
      h('h3', {}, (start.value || end.value)
        ? t('From {from} to {to}', { from: start.value ? fmtDate(start.value) : t('the start'), to: end.value ? fmtDate(end.value) : t('today') })
        : t('All time')),
      table([t('Measure'), t('Count')], [
        line(t('Checks completed'), s.assessments),
        line(t('On track'), s.by_risk_level.low), line(t('Keep an eye'), s.by_risk_level.medium),
        line(t('Needs a check'), s.by_risk_level.high),
        line(t('Sent to a health worker'), s.flagged_for_chw),
        line(t('Hearing, eyes or growth need a look'), s.red_flags || 0),
        line(t('Answers that do not fit together'), s.anomaly_flags),
        ...Object.entries(OUTCOMES).map(([k, label]) => line(t('Outcome: {outcome}', { outcome: label }), s.outcomes[k])),
        line(t('Waiting for a health worker now'), s.awaiting_review),
      ]),
      h('p', {}, h('button', { class: 'second', onclick: () => window.print() }, icon('print'), t('Print this report')))));
  });
  go.addEventListener('click', draw);
  page({ title: t('Reports'), sub: t('Usage over a period. Leave the dates empty for all time.') },
    h('div', { class: 'card' }, h('div', { class: 'row' }, field(t('From'), start), field(t('To'), end), go)), out);
  draw();
}

// ---------- shared: one result, one message thread ----------

/** A stored answer value as words: "dont_know" -> "don't know", "few_times_year" -> "few times year". */
const answerText = (v) => v === 'dont_know' ? t("don't know") : v.replace(/_/g, ' ');

/** The parts of a check result both a health worker and a caregiver see. */
function resultCards(a, forChw) {
  const checked = a.domains.filter((d) => d.status !== 'not_assessed');
  const skipped = a.domains.filter((d) => d.status === 'not_assessed').map((d) => d.label);
  return [
    // Hearing and eye answers, and the growth check (weight and height against the WHO
    // standard): rules apart from the result, each sending the check to the health worker.
    a.red_flags && a.red_flags.length ? h('div', { class: 'alert' }, icon('visibility'),
      h('div', {}, h('b', {}, t('Worth a check by a health worker. ')),
        forChw ? h('ul', { class: 'plain' }, a.red_flags.map((f) => h('li', {}, f.kind_label + ': ' + f.label)))
          : [a.red_flags.some((f) => f.kind !== 'growth') ? t('From the answers, hearing or eyes should be checked. ') : null,
             a.red_flags.some((f) => f.kind === 'growth') ? t('From the weight and height you entered, growth should be checked. ') : null,
             t('This is separate from the result and is not a diagnosis.')])) : null,
    h('div', { class: 'card' }, table([t('Area'), t('Result'), forChw ? t('Main reasons') : t('Things to try')], checked.map((d) => {
      const reasons = a.top_reasons.filter((r) => r.domain === d.domain);
      return h('tr', {},
        h('td', {}, h('div', { class: 'domain' }, h('span', { class: 'badge d-' + d.domain }, icon(DOMAIN_ICON[d.domain])), d.label)),
        h('td', {}, h('span', { class: 'chip ' + (d.status === 'needs_support' ? 'medium' : 'low') },
          d.status === 'needs_support' ? t('Needs support') : t('On track'))),
        h('td', {}, reasons.length ? h('ul', { class: 'plain' }, reasons.map((r) => h('li', {},
          forChw ? r.question + (a.answers && a.answers[r.item] ? ' (answered: ' + answerText(a.answers[r.item]) + ')' : '')
            : t('Practise {skill} together in everyday play.', { skill: r.question }))))
          : (d.status === 'needs_support' ? '' : h('span', { class: 'muted' }, t('Keep playing and talking together every day.')))));
    })),
    skipped.length ? h('p', { class: 'muted' }, t('Not checked at this age: {areas}. These are checked from 24 months.', { areas: skipped.join(', ') })) : null),
  ];
}

const DANGER = [
  t('cannot drink or breastfeed, or is feeding very poorly'),
  t('has fast or difficult breathing'),
  t('has a fever, or feels unusually hot or unusually cold'),
  t('has fits (convulsions)'),
  t('has blood in the stool'),
  t('is getting sicker, very sleepy or hard to wake'),
  t('is a young baby whose palms, soles or eyes look yellow'),
];

/** A message thread. path is /messages (caregiver) or /messages/threads/<id> (health worker). */
async function threadView(path, head, opts = {}) {
  const th = await api(path);
  const text = h('textarea', { rows: 3, maxlength: 1000, 'aria-label': opts.asChw ? t('Your reply') : t('Your question'),
    placeholder: opts.asChw ? t('Write your reply') : t('Write your question') });
  // Caregivers see the danger signs next to the send button, so an emergency goes to a
  // health facility instead of waiting in this thread.
  const send = h('button', {}, icon('send'), opts.asChw ? t('Send reply') : t('None of these apply. Send my question'));
  send.addEventListener('click', () => run(send, async () => {
    if (!text.value.trim()) throw new Error(opts.asChw ? t('Write your reply first.') : t('Write your question first.'));
    await api(path, { method: 'POST', body: { body: text.value, prediction_id: opts.predictionId || undefined } });
    await threadView(path, head, opts);
  }));
  const conversation = h('div', { class: 'card' },
    th.messages.length
      ? h('div', { class: 'thread' }, th.messages.map((m) => h('div', { class: 'bubble' + (m.from_me ? ' me' : '') },
          m.about ? h('b', {}, t("About {name}'s check. ", { name: m.about.child_name })) : null, m.body,
          h('small', {}, (m.from_me ? t('You') : m.sender_name) + ', ' + fmtTime(m.created_at)))))
      : empty(t('No messages yet.'), 'chat_bubble'),
    th.messages.length ? h('p', { class: 'status' }, th.waiting_for_chw
      ? (opts.asChw ? t('Waiting for your reply') : t('Sent. Waiting for a reply.')) : (opts.asChw ? t('You replied') : t('Answered'))) : null,
    text, h('p', {}, send));
  const side = opts.asChw ? null : h('div', {},
    h('div', { class: 'note' }, icon('schedule'), h('div', {}, th.chw
      ? t('{name} is your community health worker. They reply when they can, often within a day or two.', { name: th.chw.full_name })
      : t('You are not linked to a community health worker yet. You can still write; your question reaches them once you are linked.'))),
    h('div', { class: 'alert' }, icon('emergency'), h('div', {},
      h('b', {}, t('Go to a health facility now, and do not wait for a reply, if your child:')),
      h('ul', { class: 'plain' }, DANGER.map((d) => h('li', {}, d))))));
  page(head, opts.asChw ? conversation : h('div', { class: 'split' }, conversation, side));
}

// ---------- community health worker ----------

let caseCache = new Map();
const flagChips = (a) => [riskChip(a.risk_level),
  a.red_flags && a.red_flags.length ? h('span', { class: 'chip flag' }, [...new Set(a.red_flags.map((f) => f.kind_label))].join(', ')) : null,
  a.anomaly_flag ? h('span', { class: 'chip flag' }, t('Check answers')) : null];

function caseTable(cases) {
  const order = { high: 0, medium: 1, low: 2 };
  cases.sort((a, b) => order[a.risk_level] - order[b.risk_level] || new Date(b.submitted_at) - new Date(a.submitted_at));
  cases.forEach((a) => caseCache.set(a.prediction_id, a));
  return table([t('Child'), t('Flags'), t('Caregiver'), t('Checked'), t('Outcome')], cases.map((a) => linkRow('case/' + a.prediction_id,
    h('td', {}, person(avatar(a.child_id, a.child_avatar_id), a.child_name, ageLabel(a.age_months))),
    h('td', {}, flagChips(a)),
    h('td', {}, a.caregiver.full_name), h('td', {}, fmtDate(a.submitted_at)),
    h('td', {}, a.chw_outcome ? OUTCOMES[a.chw_outcome] : h('span', { class: 'muted' }, t('Waiting for review'))))));
}

async function chwHome() {
  const [open, families, threads] = await Promise.all([api('/chw/cases'), api('/chw/caregivers'), api('/messages/threads')]);
  const waiting = threads.filter((th) => th.waiting_for_chw).length;
  page({ title: t('Hello, {name}', { name: me.full_name.split(' ')[0] }), sub: t('Children who need a follow-up are listed below, the highest risk first.') },
    h('div', { class: 'tiles' },
      tile('flag', 'bg-blush', open.length, t('Cases waiting for review'), { warn: true }),
      tile('chat_bubble', 'bg-sun', waiting, t('Questions waiting for a reply'), { warn: true, href: '#questions' }),
      tile('family_restroom', 'bg-sky', families.length, t('Families linked to you'), { href: '#families' })),
    h('div', { class: 'card' }, h('h3', {}, t('Flagged cases')),
      open.length ? caseTable(open) : empty(t('All caught up. No children need a follow-up right now.'), 'task_alt')));
}

async function chwReviewed() {
  const all = (await api('/chw/cases?include_reviewed=true')).filter((a) => a.chw_outcome);
  page({ title: t('Reviewed'), sub: t('Cases you have already logged an outcome for. Open one to change it.') },
    h('div', { class: 'card' }, all.length ? caseTable(all) : empty(t('No outcomes recorded yet.'), 'fact_check')));
}

async function chwCase(id) {
  let a = caseCache.get(id);
  if (!a) {
    (await api('/chw/cases?include_reviewed=true')).forEach((c) => caseCache.set(c.prediction_id, c));
    a = caseCache.get(id);
  }
  if (!a) { page({ title: t('Case not found'), back: ['#home', t('Back to cases')] }); return; }
  const history = (await api('/children/' + a.child_id + '/assessments')).filter((x) => x.prediction_id !== id);
  const g = a.latest_growth;
  const pick = h('select', { 'aria-label': t('Outcome') }, h('option', { value: '' }, t('Choose an outcome')),
    Object.entries(OUTCOMES).map(([k, label]) => h('option', { value: k, selected: k === a.chw_outcome }, label)));
  const save = h('button', {}, t('Save outcome'));
  save.addEventListener('click', () => run(save, async () => {
    if (!pick.value) throw new Error(t('Choose an outcome first.'));
    await api('/chw/cases/' + id + '/outcome', { method: 'POST', body: { outcome: pick.value } });
    caseCache.clear();
    toast(t('Outcome saved for {name}.', { name: a.child_name }));
    location.hash = 'home';
  }));
  page({ title: a.child_name + ', ' + ageLabel(a.age_months), back: ['#home', t('Back to cases')],
    sub: t('Checked {when} by {name}', { when: fmtTime(a.submitted_at), name: a.caregiver.full_name }), chips: flagChips(a) },
    a.anomaly_flag ? note(t('Some answers do not fit together the way they usually do. Go through the questions with the caregiver before deciding.')) : null,
    h('div', { class: 'split' },
      h('div', {}, resultCards(a, true),
        h('div', { class: 'card' }, h('h3', {}, t('Earlier checks')),
          history.length ? table([t('Date'), t('Age'), t('Result'), t('Outcome')], history.map((x) => h('tr', {},
            h('td', {}, fmtDate(x.submitted_at)), h('td', {}, ageLabel(x.age_months)), h('td', {}, riskChip(x.risk_level)),
            h('td', {}, x.chw_outcome ? OUTCOMES[x.chw_outcome] : '')))) : h('p', { class: 'muted' }, t('This is the first check.')))),
      h('div', {},
        h('div', { class: 'card' }, h('h3', {}, t('Log outcome')),
          h('p', { class: 'muted' }, t('The caregiver sees a short fixed message for the first two.')),
          pick, h('p', {}, save)),
        h('div', { class: 'card' }, h('h3', {}, t('Family')),
          person(initial(a.caregiver.full_name), a.caregiver.full_name, a.caregiver.phone_number + (a.location ? ', ' + a.location : '')),
          h('p', {}, h('a', { href: '#thread/' + a.caregiver.user_id }, t('Messages with {name}', { name: a.caregiver.full_name.split(' ')[0] })))),
        h('div', { class: 'card' }, h('h3', {}, t('About {name}', { name: a.child_name })),
          a.care_factors && a.care_factors.length
            ? h('ul', { class: 'plain' }, a.care_factors.map((f) => h('li', {}, CARE[f] || f)))
            : h('p', { class: 'muted' }, t('No reasons for special care ticked.')),
          h('p', {}, g ? t('Latest measurement ({date}): {value}', { date: fmtDate(g.measured_on),
              value: [g.weight_kg ? g.weight_kg + ' kg' : null, g.height_cm ? g.height_cm + ' cm' : null].filter(Boolean).join(', ') })
            : h('span', { class: 'muted' }, t('No weight or height entered yet.')))))));
}

async function chwFamilies() {
  const families = await api('/chw/caregivers');
  const phone = h('input', { placeholder: '0712 345 678', required: true });
  const link = h('button', { type: 'submit' }, icon('link'), t('Link'));
  const linkForm = h('form', { class: 'card', onsubmit: (ev) => {
    ev.preventDefault();
    run(link, async () => {
      const u = await api('/chw/caregivers/link', { method: 'POST', body: { phone_number: phone.value } });
      toast(t('{name} is now linked to you.', { name: u.full_name }));
      await chwFamilies();
    });
  } }, h('h3', {}, t('Link a caregiver')),
    h('p', { class: 'muted' }, t('For a caregiver who already has a Hatua account.')),
    h('div', { class: 'row' }, field(t('Their phone number'), phone), link));
  page({ title: t('My families'), sub: t('Caregivers linked to you. Their flagged checks and questions come to you.') },
    h('div', { class: 'split' },
      h('div', { class: 'card' }, families.length ? table([t('Caregiver'), t('Children'), t('Open cases'), ''], families.map((f) => h('tr', {},
        h('td', {}, person(initial(f.full_name), f.full_name, f.phone_number)), h('td', {}, f.children),
        h('td', {}, f.open_cases ? h('span', { class: 'chip medium' }, f.open_cases) : 0),
        h('td', {}, h('a', { href: '#thread/' + f.user_id }, t('Messages')))))) : empty(t('No caregivers are linked to you yet.'), 'family_restroom')),
      linkForm));
}

async function chwQuestions() {
  const threads = await api('/messages/threads');
  page({ title: t('Questions'), sub: t('Questions from caregivers linked to you. Unanswered ones are first.') },
    h('div', { class: 'card' }, threads.length ? table([t('Caregiver'), t('Latest message'), t('When'), ''], threads.map((th) => linkRow('thread/' + th.caregiver.user_id,
      h('td', {}, person(initial(th.caregiver.full_name), th.caregiver.full_name)),
      h('td', {}, th.last_message.body.slice(0, 90)),
      h('td', {}, fmtTime(th.last_message.created_at)),
      h('td', {}, th.waiting_for_chw ? h('span', { class: 'chip medium' }, t('Waiting for your reply')) : h('span', { class: 'chip low' }, t('Replied'))))))
      : empty(t('When a caregiver linked to you asks a question, it shows here.'), 'chat_bubble')));
}

// ---------- caregiver ----------

async function cgChildren() {
  const children = await api('/children');
  const latest = await Promise.all(children.map((c) => api('/children/' + c.child_id + '/assessments').then((l) => l[0] || null)));
  const addBtn = h('button', { class: 'sun', onclick: () => { location.hash = 'add-child'; } }, icon('add'), t('Add a child'));
  page({ title: t('Hi, {name}', { name: me.full_name.split(' ')[0] }), sub: t("Let's see how your children are growing."), chips: addBtn },
    h('div', { class: 'card' }, h('h3', {}, t('My children')),
      children.length ? table([t('Child'), t('Latest check'), ''], children.map((c, i) => linkRow('child/' + c.child_id,
        h('td', {}, person(avatar(c.child_id, c.avatar_id), c.first_name, ageLabel(c.age_months))),
        h('td', {}, latest[i] ? [riskChip(latest[i].risk_level), h('div', { class: 'muted' }, fmtDate(latest[i].submitted_at))] : h('span', { class: 'muted' }, t('No checks yet'))),
        h('td', {}, h('a', { href: '#check/' + c.child_id, onclick: (ev) => ev.stopPropagation() }, t('Start a check'))))))
        : h('div', {}, empty(t('Add your child to start checking how they are growing.'), 'child_care'),
            h('p', { style: 'text-align:center' }, h('button', { onclick: () => { location.hash = 'add-child'; } }, icon('add'), t('Add a child'))))));
}

/** Add a child: its own page, as in the app, with the reasons for special care. */
async function cgAddChild() {
  const name = h('input', { required: true, maxlength: 50 }), dob = h('input', { type: 'date', required: true, max: new Date().toISOString().slice(0, 10) });
  const sex = h('select', {}, h('option', { value: 'female' }, t('Girl')), h('option', { value: 'male' }, t('Boy')));
  const place = h('input', { required: true, maxlength: 100, placeholder: t('Town or estate') });
  const care = Object.entries(CARE).map(([value, label]) =>
    h('label', { class: 'check' }, h('input', { type: 'checkbox', value }), label));
  const add = h('button', { type: 'submit', class: 'sun' }, icon('add'), t('Add child'));
  const form = h('form', { class: 'card', onsubmit: (ev) => {
    ev.preventDefault();
    run(add, async () => {
      const factors = care.map((l) => l.querySelector('input')).filter((i) => i.checked).map((i) => i.value);
      const c = await api('/children', { method: 'POST', body: { first_name: name.value, date_of_birth: dob.value,
        sex: sex.value, location: place.value, care_factors: factors } });
      toast(t('{name} was added.', { name: c.first_name }));
      location.hash = 'child/' + c.child_id;
    });
  } },
    h('div', { class: 'row' }, field(t('First name'), name), field(t('Date of birth'), dob)),
    h('div', { class: 'row' }, field(t('Sex'), sex), field(t('Where you live'), place)),
    h('h3', { style: 'margin-top:1.5rem' }, t('Does any of this apply?')),
    h('p', { class: 'muted' }, t('Tick any that do. It helps your health worker. You can change this later.')),
    h('div', { class: 'checks' }, care),
    h('p', { style: 'margin-top:1.25rem' }, add));
  page({ title: t('Add a child'), back: ['#children', t('My children')], sub: t('For a child under five. The questions at each check will match their age.') }, form);
  name.focus();
}

function cgResult(a, fresh) {
  const head = { high: t("Let's get {name} checked by a health worker", { name: a.child_name }), medium: t("Let's keep an eye on {name}", { name: a.child_name }), low: t('{name} is on track', { name: a.child_name }) };
  return [
    h('div', { class: 'card' },
      h('div', { class: 'person' }, avatar(a.child_id, a.child_avatar_id),
        h('div', {}, h('h3', {}, head[a.risk_level]), h('div', { class: 'muted', style: 'font-weight:400' }, ageLabel(a.age_months) + ', ' + fmtDate(a.submitted_at)))),
      h('p', {}, riskChip(a.risk_level)),
      a.caregiver_message ? note(a.caregiver_message)
        : a.sent_to_chw ? note(t('Your community health worker will look at this result and may get in touch with you.')) : null),
    resultCards(a, false),
    h('p', { class: 'muted' }, t('This check gives a signal, not a diagnosis. If you are worried about your child, visit a health facility.')),
    h('p', {}, h('button', { class: 'second', onclick: () => { askAbout = { id: a.prediction_id, name: a.child_name }; location.hash = 'ask'; } },
      icon('chat_bubble'), t('Ask your health worker about this')),
      fresh ? [' ', h('button', { class: 'sun', onclick: () => { location.hash = 'children'; } }, t('Back to my children'))] : null)];
}

let askAbout = null;

// ---------- clinic schedule (ported from the app's care_schedule.dart) ----------
//
// The routine schedule printed in the MOH Mother and Child Health Handbook (2020): a
// clinic visit every month, vitamin A every six months from 6 months, deworming every six
// months from 1 year, and the childhood vaccines. Hatua does not know what the child has
// already had, so these are reminders of when each is due. The clinic booklet is the record.

/** A date string "2024-03-15" as a local date (no time-zone shift). */
const localDate = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
function addMonths(d, months) {
  const total = d.getFullYear() * 12 + d.getMonth() + months;
  const y = Math.floor(total / 12), m = total % 12;
  return new Date(y, m, Math.min(d.getDate(), new Date(y, m + 1, 0).getDate()));
}
const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
const atAge = (m) => m < 12 ? t('at {n} months', { n: m })
  : m === 12 ? t('at 1 year') : m % 12 === 0 ? t('at {n} years', { n: m / 12 })
  : t('at {n}½ years', { n: Math.floor(m / 12) });

/** The next vitamin A, deworming, vaccine and clinic visit, soonest first. Due in the last two weeks counts as due now. */
function nextCare(dobText) {
  const now = new Date(), day = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dob = localDate(dobText);
  if (day >= addMonths(dob, 60)) return [];
  const from = addDays(day, -14), items = [];
  const first = (list, make) => { for (const x of list) { const it = make(x); if (it.due >= from) { items.push(it); return; } } };
  first([6, 12, 18, 24, 30, 36, 42, 48, 54, 59], (m) => ({ title: t('Vitamin A'), detail: t('Given at the clinic {age}', { age: atAge(m) }), due: addMonths(dob, m), ico: 'medication' }));
  first([12, 18, 24, 30, 36, 42, 48, 54, 59], (m) => ({ title: t('Deworming'), detail: t('Given at the clinic {age}', { age: atAge(m) }), due: addMonths(dob, m), ico: 'medication' }));
  first([[addDays(dob, 42), t('Vaccines at 6 weeks')], [addDays(dob, 70), t('Vaccines at 10 weeks')], [addDays(dob, 98), t('Vaccines at 14 weeks')],
    [addMonths(dob, 9), t('Measles-rubella vaccine, first dose')], [addMonths(dob, 18), t('Measles-rubella vaccine, second dose')]],
    ([due, title]) => ({ title, detail: t('Take the clinic booklet with you'), due, ico: 'vaccines' }));
  for (let m = 1; m < 60; m++) {
    const due = addMonths(dob, m);
    if (due >= day) { items.push({ title: t('Clinic visit'), detail: t('Monthly weighing and growth check'), due, ico: 'monitor_weight' }); break; }
  }
  return items.sort((a, b) => a.due - b.due).map((x) => ({ ...x, now: x.due <= day }));
}

function careCard(child) {
  const items = nextCare(child.date_of_birth);
  return h('div', { class: 'card' }, h('h3', {}, t('Coming up at the clinic')),
    items.length ? h('ul', { class: 'care' }, items.map((x) => h('li', {},
      h('span', { class: 'ico ' + (x.now ? 'bg-sun' : 'bg-sky') }, icon(x.ico)),
      h('div', {}, h('b', {}, x.title), h('div', { class: 'muted' }, x.detail)),
      x.now ? h('span', { class: 'chip medium' }, t('Due now')) : h('span', { class: 'when' }, fmtDate(x.due)))))
      : h('p', { class: 'muted' }, t('The routine clinic schedule ends at five years.')),
    h('p', { class: 'muted' }, t('From the routine schedule in the Mother and Child Health Handbook. Your clinic booklet is the record of what {name} has had.', { name: child.first_name })));
}

// ---------- growth (ported from the app's growth_chart.dart) ----------

// WHO Child Growth Standards, weight-for-age: [months, 3rd, median, 97th percentile] in kg.
const WHO_WEIGHT = {
  male: [[0, 2.5, 3.3, 4.3], [3, 5.1, 6.4, 7.9], [6, 6.4, 7.9, 9.7], [9, 7.2, 8.9, 10.9], [12, 7.8, 9.6, 11.8],
    [15, 8.4, 10.3, 12.7], [18, 8.9, 10.9, 13.5], [21, 9.3, 11.5, 14.3], [24, 9.8, 12.2, 15.1], [27, 10.2, 12.7, 15.9],
    [36, 11.4, 14.3, 18.0], [42, 12.2, 15.3, 19.4], [48, 12.9, 16.3, 20.9], [54, 13.6, 17.3, 22.3], [60, 14.3, 18.3, 23.8]],
  female: [[0, 2.4, 3.2, 4.2], [3, 4.6, 5.8, 7.4], [6, 5.8, 7.3, 9.2], [9, 6.6, 8.2, 10.4], [12, 7.1, 8.9, 11.3],
    [15, 7.7, 9.6, 12.2], [18, 8.2, 10.2, 13.0], [21, 8.7, 10.9, 13.8], [24, 9.2, 11.5, 14.6], [27, 9.6, 12.1, 15.4],
    [36, 11.0, 13.9, 17.8], [42, 11.8, 15.0, 19.5], [48, 12.5, 16.1, 21.1], [54, 13.2, 17.2, 22.8], [60, 14.0, 18.2, 24.4]],
};
function weightReference(sex, months) {
  const rows = WHO_WEIGHT[sex] || WHO_WEIGHT.male, m = Math.min(60, Math.max(0, months));
  for (let i = 1; i < rows.length; i++) {
    const a = rows[i - 1], b = rows[i];
    if (m <= b[0]) { const f = (m - a[0]) / (b[0] - a[0]); return [1, 2, 3].map((k) => a[k] + (b[k] - a[k]) * f); }
  }
  return rows[rows.length - 1].slice(1);
}

/** An SVG element with numeric or fixed attributes (nothing typed by a person). */
function s(tag, attrs, ...children) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  el.append(...children);
  return el;
}

/** Weight-for-age: the child's weights over the band where most healthy children fall. */
function weightChart(child) {
  const W = 600, H = 340, L = 34, B = 26, T = 8, R = 8, MAX = 26;
  const x = (m) => L + (m / 60) * (W - L - R), y = (kg) => T + (1 - kg / MAX) * (H - T - B);
  const dob = localDate(child.date_of_birth);
  const pts = child.growth.filter((g) => g.weight_kg)
    .map((g) => [Math.min(60, Math.max(0, (localDate(g.measured_on) - dob) / 864e5 / 30.4375)), g.weight_kg])
    .sort((a, b) => a[0] - b[0]);
  const grid = [];
  for (let yr = 0; yr <= 5; yr++) {
    grid.push(s('line', { x1: x(yr * 12), x2: x(yr * 12), y1: T, y2: H - B, class: 'grid' }),
      s('text', { x: x(yr * 12), y: H - 6, 'text-anchor': yr === 0 ? 'start' : yr === 5 ? 'end' : 'middle' }, yr === 0 ? t('Birth') : yr + ' y'));
  }
  for (let kg = 5; kg <= 25; kg += 5) {
    grid.push(s('line', { x1: L, x2: W - R, y1: y(kg), y2: y(kg), class: 'grid' }),
      s('text', { x: L - 6, y: y(kg) + 4, 'text-anchor': 'end' }, kg));
  }
  const low = [], high = [], mid = [];
  for (let m = 0; m <= 60; m++) {
    const [p3, p50, p97] = weightReference(child.sex, m);
    low.push(x(m) + ',' + y(p3)); mid.push(x(m) + ',' + y(p50)); high.unshift(x(m) + ',' + y(p97));
  }
  const svgEl = s('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'growth', role: 'img',
    'aria-label': t(pts.length === 1 ? 'Weight for age chart with 1 measurement' : 'Weight for age chart with {n} measurements', { n: pts.length }) },
    ...grid,
    s('polygon', { points: low.concat(high).join(' '), class: 'band' }),
    s('polyline', { points: mid.join(' '), class: 'median' }),
    pts.length > 1 ? s('polyline', { points: pts.map(([m, kg]) => x(m) + ',' + y(Math.min(kg, MAX))).join(' '), class: 'path' }) : '',
    ...pts.map(([m, kg]) => s('circle', { cx: x(m), cy: y(Math.min(kg, MAX)), r: 6, class: 'dot' })),
    s('text', { x: 0, y: T + 10 }, 'kg'));
  return h('div', {}, svgEl,
    h('p', { class: 'muted' }, t("Dots: {name}'s weights. Shaded area: where most healthy children of this age fall (WHO growth standards). Line: the middle.", { name: child.first_name })));
}

function growthCard(child, reload) {
  const d = new Date(), today = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  const on = h('input', { type: 'date', required: true, value: today, max: today, min: child.date_of_birth });
  const kg = h('input', { type: 'number', step: '0.1', min: 1, max: 35, inputmode: 'decimal', placeholder: '9.5' });
  const cm = h('input', { type: 'number', step: '0.1', min: 40, max: 130, inputmode: 'decimal', placeholder: '75' });
  const save = h('button', { type: 'submit' }, icon('add'), t('Add'));
  const latest = child.growth[child.growth.length - 1];
  const form = h('form', { onsubmit: (ev) => {
    ev.preventDefault();
    run(save, async () => {
      if (!kg.value && !cm.value) throw new Error(t('Enter a weight, a height or both.'));
      await api('/children/' + child.child_id + '/growth', { method: 'POST', body: { measured_on: on.value,
        weight_kg: kg.value ? Number(kg.value) : null, height_cm: cm.value ? Number(cm.value) : null } });
      toast(t('Measurement added for {name}.', { name: child.first_name }));
      await reload();
    });
  } },
    h('h3', { style: 'margin-top:1.25rem' }, t('Add a measurement')),
    h('p', { class: 'muted' }, t('Copy it from the clinic booklet. A weight, a height or both.')),
    field(t('Date measured'), on),
    h('div', { class: 'row' }, field(t('Weight (kg)'), kg), field(t('Height (cm)'), cm)),
    h('p', {}, save));
  return h('div', { class: 'card' }, h('h3', {}, t('Growth')),
    child.growth.some((g) => g.weight_kg) ? weightChart(child) : h('p', { class: 'muted' }, t('No weights entered yet. Add one to see the growth chart.')),
    latest ? h('p', {}, t('Latest ({date}): {value}', { date: fmtDate(latest.measured_on),
      value: [latest.weight_kg ? latest.weight_kg + ' kg' : null, latest.height_cm ? latest.height_cm + ' cm' : null].filter(Boolean).join(', ') })) : null,
    form);
}

async function cgChild(id) {
  const [child, checks] = await Promise.all([api('/children/' + id), api('/children/' + id + '/assessments')]);
  const startBtn = h('button', { class: 'sun', onclick: () => { location.hash = 'check/' + id; } }, icon('play_arrow'), t('Start a check'));
  const editBtn = h('button', { class: 'second', onclick: () => { location.hash = 'edit/' + id; } }, icon('edit'), t('Edit details'));
  page({ title: child.first_name + ', ' + ageLabel(child.age_months), back: ['#children', t('My children')],
    sub: checks.length ? t(checks.length === 1 ? '1 check so far.' : '{n} checks so far.', { n: checks.length }) : t('No checks yet.'), chips: [startBtn, ' ', editBtn] },
    h('div', { class: 'split' },
      h('div', {}, checks.length
        ? checks.map((a, i) => [h('h2', { style: i === 0 ? 'margin-top:0' : null }, i === 0 ? t('Latest check') : t('Check from {date}', { date: fmtDate(a.submitted_at) })), cgResult(a, false)])
        : h('div', { class: 'card' }, empty(t('Start the first check to see how {name} is growing.', { name: child.first_name }), 'child_care'))),
      h('div', {}, careCard(child), growthCard(child, () => cgChild(id)))));
}

/** Change the child's animal and the reasons for special care (what the app lets you change). */
async function cgEditChild(id) {
  const child = await api('/children/' + id);
  const current = AVATARS.includes(child.avatar_id) ? child.avatar_id : null;
  // No animal names, as in the app: the pictures speak for themselves.
  const animals = AVATARS.map((a, i) => h('label', { class: 'pick' },
    h('input', { type: 'radio', name: 'avatar', value: a, checked: a === current, 'aria-label': t('Picture {n}', { n: i + 1 }) }),
    h('img', { src: 'avatars/' + a + '.svg', alt: '' })));
  const care = Object.entries(CARE).map(([value, label]) =>
    h('label', { class: 'check' }, h('input', { type: 'checkbox', value, checked: child.care_factors.includes(value) }), label));
  const save = h('button', { type: 'submit', class: 'sun' }, t('Save changes'));
  const form = h('form', { class: 'card', onsubmit: (ev) => {
    ev.preventDefault();
    run(save, async () => {
      const picked = form.querySelector('input[name="avatar"]:checked');
      await api('/children/' + id, { method: 'PATCH', body: {
        avatar_id: picked ? picked.value : undefined,
        care_factors: care.map((l) => l.querySelector('input')).filter((i) => i.checked).map((i) => i.value) } });
      toast(t('Changes saved for {name}.', { name: child.first_name }));
      location.hash = 'child/' + id;
    });
  } },
    h('h3', {}, t('Picture')),
    h('p', { class: 'muted' }, t('Pick a picture for {name}.', { name: child.first_name })),
    h('div', { class: 'picks' }, animals),
    h('h3', { style: 'margin-top:1.5rem' }, t('Does any of this apply?')),
    h('p', { class: 'muted' }, t('Tick any that do. It helps your health worker.')),
    h('div', { class: 'checks' }, care),
    h('p', { style: 'margin-top:1.25rem' }, save));
  page({ title: t('Edit {name}', { name: child.first_name }), back: ['#child/' + id, child.first_name],
    sub: t('Name, date of birth and sex cannot be changed here. Ask your health worker if one is wrong.') }, form);
}

async function cgCheck(id) {
  const [q, child] = await Promise.all([api('/assessments/questions?child_id=' + id), api('/children/' + id)]);
  const send = h('button', { type: 'submit', class: 'sun' }, t('See results'));
  const form = h('form', { class: 'card', onsubmit: (ev) => {
    ev.preventDefault();
    run(send, async () => {
      const responses = {};
      for (const x of q.questions) {
        const picked = form.querySelector('input[name="' + x.item + '"]:checked');
        if (!picked) throw new Error(t('Please answer every question. One is still empty.'));
        responses[x.item] = picked.value;
      }
      const a = await api('/assessments', { method: 'POST', body: { child_id: id, responses } });
      page({ title: t('Results'), sub: t('Check complete for {name}.', { name: a.child_name }) }, cgResult(a, true));
      window.scrollTo(0, 0);
    });
  } }, q.questions.map((x, i) => h('fieldset', { class: 'q', style: 'border:0;margin:0' },
    h('legend', { class: 'text' }, h('span', { class: 'num' }, i + 1), h('span', {}, x.text,
      x.screening ? [' ', h('span', { class: 'chip flag' }, x.screening === 'hearing' ? t('Hearing') : t('Eyes and seeing'))] : null,
      x.hint ? h('span', { class: 'hint' }, x.hint) : null)),
    h('div', { class: 'opts' }, x.options.map((o) => h('label', {}, h('input', { type: 'radio', name: x.item, value: o.value }), o.label))))),
    h('p', {}, send));
  page({ title: t("{name}'s check", { name: child.first_name }), back: ['#child/' + id, child.first_name],
    sub: t('{n} questions for {age}. Think about what {name} does on most days.', { n: q.questions.length, age: ageLabel(q.age_months), name: child.first_name }) }, form);
}

async function cgAsk() {
  const about = askAbout; askAbout = null;
  await threadView('/messages', {
    title: about ? t("Ask about {name}'s check", { name: about.name }) : t('Ask your health worker'),
    sub: t('Write your question. Your health worker replies here.') },
    { predictionId: about ? about.id : null });
}

// ---------- pages by role, and the router ----------

const PAGES = {
  admin: [['overview', t('Overview'), 'dashboard', adminOverview], ['users', t('Users'), 'group', adminUsers],
    ['linking', t('Linking'), 'link', adminLinking], ['reports', t('Reports'), 'description', adminReports]],
  chw: [['home', t('Home'), 'home', chwHome], ['families', t('My families'), 'family_restroom', chwFamilies],
    ['questions', t('Questions'), 'chat_bubble', chwQuestions], ['reviewed', t('Reviewed'), 'fact_check', chwReviewed]],
  caregiver: [['children', t('My children'), 'child_care', cgChildren], ['ask', t('Ask your health worker'), 'chat_bubble', cgAsk]],
};
const DETAIL = {
  chw: { case: chwCase, thread: async (id) => {
    const th = await api('/messages/threads/' + id);
    await threadView('/messages/threads/' + id, { title: th.caregiver.full_name, back: ['#questions', t('Questions')],
      sub: th.caregiver.phone_number }, { asChw: true });
  } },
  caregiver: { child: cgChild, check: cgCheck, edit: cgEditChild },
};
// Pages with no menu entry and no id in the address.
const HIDDEN = { caregiver: { 'add-child': cgAddChild } };

async function route() {
  if (!me) return;
  const pages = PAGES[me.role];
  const [name, id] = location.hash.replace(/^#/, '').split('/');
  const pg = pages.find((p) => p[0] === name);
  const hidden = !id && HIDDEN[me.role] && HIDDEN[me.role][name];
  const detail = id ? DETAIL[me.role] && DETAIL[me.role][name] : hidden && (() => hidden());
  if (!pg && !detail) { location.hash = pages[0][0]; return; }
  document.getElementById('nav').replaceChildren(...pages.map((p) =>
    h('a', { href: '#' + p[0], class: p[0] === name ? 'on' : '', 'aria-current': p[0] === name ? 'page' : null }, icon(p[2]), p[1])));
  main().replaceChildren(h('p', { class: 'muted' }, t('Loading...')));
  try { await (detail ? detail(id) : pg[3]()); } catch (e) {
    if (me) page({ title: t('This page did not load') },
      h('div', { class: 'alert' }, icon('error'), h('div', {}, e.message || t('Something went wrong.'))),
      h('button', { onclick: route }, t('Try again')));
  }
}

async function start() {
  if (!token) { loginPage(); return; }
  try { me = await api('/auth/me'); } catch (_) { if (token) signOut(); return; }
  if (me.language && me.language !== LANG) {
    // Signed in somewhere else in the other language: follow the account.
    // (If this browser cannot keep the choice, stay in this language rather than reload forever.)
    let kept = false;
    try { localStorage.setItem('hatua.lang', me.language); kept = true; } catch (_) { /* stay */ }
    if (kept) { location.reload(); return; }
  }
  const brand = document.getElementById('brand');
  brand.replaceChildren(svg(MARK), 'Hatua');
  document.getElementById('who').replaceChildren(h('b', {}, me.full_name));
  document.getElementById('signout').textContent = t('Sign out');
  setToggle();
  document.getElementById('top').hidden = false;
  await route();
}

window.addEventListener('hashchange', route);
document.getElementById('signout').addEventListener('click', signOut);
start();
