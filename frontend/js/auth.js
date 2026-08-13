/* ==========================================================================
   VentureAI — auth.js
   Handles registration, login, logout, session checking, and the
   dynamic (logged-in vs logged-out) navbar. Vanilla JS, no dependencies.

   IMPORTANT: the actual JWTs live in HttpOnly cookies set by the backend —
   this file never reads or stores the token itself. `sessionStorage` is
   only used to cache non-sensitive user info (id/name/role) so the navbar
   can paint instantly without waiting on a network round trip; the cache
   is always re-verified against /auth/me.
   ========================================================================== */

// Dynamically match the current hostname (localhost vs 127.0.0.1) so cross-origin cookie restrictions don't block auth cookies.
const API_BASE_URL = (typeof window !== 'undefined' && window.location.hostname)
  ? `http://${window.location.hostname}:8000`
  : 'http://127.0.0.1:8000';

const USER_CACHE_KEY = 'vp_user';

const ROLE_DASHBOARD = {
  Founder: 'founder-dashboard.html',
  Mentor: 'mentor-dashboard.html',
  Admin: 'admin-dashboard.html',
};

/* ---------------------------------------------------------
   Low-level API helper
--------------------------------------------------------- */
async function apiRequest(path, { method = 'GET', body } = {}, isRetry = false) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: 'include', // required so HttpOnly auth cookies are sent/received
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body, e.g. some 204s */ }

  if (res.status === 401 && !isRetry && path !== '/auth/login' && path !== '/auth/refresh') {
    try {
      const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshRes.ok) {
        return await apiRequest(path, { method, body }, true);
      }
    } catch (_) {
      /* fallback to standard error handling */
    }
  }

  if (!res.ok) {
    const detail = data && data.detail;
    // FastAPI validation errors return an array of {msg,...} objects; flatten to one line.
    const message = Array.isArray(detail)
      ? detail.map(d => d.msg).join(' ')
      : (detail || 'Something went wrong. Please try again.');
    throw new Error(message);
  }
  return data;
}

/* ---------------------------------------------------------
   User cache (UI convenience only — never the token)
--------------------------------------------------------- */
function cacheUser(user) {
  sessionStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
}
function getCachedUser() {
  try { return JSON.parse(sessionStorage.getItem(USER_CACHE_KEY)); } catch (_) { return null; }
}
function clearCachedUser() {
  sessionStorage.removeItem(USER_CACHE_KEY);
}

/* ---------------------------------------------------------
   Auth actions
--------------------------------------------------------- */
async function registerUser({ name, email, password, role }) {
  return apiRequest('/auth/register', { method: 'POST', body: { name, email, password, role } });
}

async function loginUser({ email, password }) {
  const data = await apiRequest('/auth/login', { method: 'POST', body: { email, password } });
  cacheUser(data.user);
  return data.user;
}

async function logoutUser() {
  try { await apiRequest('/auth/logout', { method: 'POST' }); } catch (_) { /* clear locally regardless */ }
  clearCachedUser();
}

async function getCurrentUser() {
  try {
    const user = await apiRequest('/auth/me');
    cacheUser(user);
    return user;
  } catch (_) {
    clearCachedUser();
    return null;
  }
}

function redirectToDashboard(role) {
  window.location.href = ROLE_DASHBOARD[role] || 'index.html';
}

/* ---------------------------------------------------------
   Dynamic navbar (logged-out vs logged-in state)
--------------------------------------------------------- */
function loggedOutActionsHTML() {
  return `
    <a href="login.html" class="btn btn--outline">Login</a>
    <a href="register.html" class="btn btn--primary" data-ripple>Get Started</a>
  `;
}

function getInitials(name) {
  if (!name || !name.trim()) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function loggedInActionsHTML(user) {
  const initials = getInitials(user.name);
  const dashboardHref = ROLE_DASHBOARD[user.role] || 'index.html';
  const profileLink = user.role === 'Founder'
    ? `<a href="founder-profile.html">Profile</a>`
    : '';
  return `
    <a href="${dashboardHref}" class="btn btn--outline">Dashboard</a>
    <div class="navbar__profile" data-profile-menu>
      <button type="button" class="navbar__profile-btn" data-profile-toggle aria-haspopup="true" aria-expanded="false">
        <span class="navbar__avatar" aria-hidden="true">${initials}</span>
        <span class="navbar__profile-name">${user.name}</span>
      </button>
      <div class="navbar__profile-dropdown" data-profile-dropdown>
        ${profileLink}
        <a href="${dashboardHref}">Dashboard</a>
        <button type="button" data-logout-btn>Log out</button>
      </div>
    </div>
  `;
}

function renderNavbarAuthState(user) {
  const targets = document.querySelectorAll('[data-navbar-actions]');
  if (!targets.length) return;
  const html = user ? loggedInActionsHTML(user) : loggedOutActionsHTML();
  targets.forEach(el => { el.innerHTML = html; });
  if (user) wireProfileMenu();
}

function wireProfileMenu() {
  document.querySelectorAll('[data-profile-toggle]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const dropdown = btn.closest('[data-profile-menu]').querySelector('[data-profile-dropdown]');
      const isOpen = dropdown.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(isOpen));
    });
  });

  document.querySelectorAll('[data-logout-btn]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await logoutUser();
      window.location.href = 'index.html';
    });
  });

  // Close any open dropdown when clicking outside it.
  document.addEventListener('click', (e) => {
    document.querySelectorAll('[data-profile-dropdown].open').forEach(dd => {
      if (!dd.closest('[data-profile-menu]').contains(e.target)) {
        dd.classList.remove('open');
      }
    });
  });
}

async function initNavbarAuthState() {
  // Paint instantly from cache to avoid a flash of the logged-out state,
  // then reconcile with the server (cache can be stale/tampered with).
  renderNavbarAuthState(getCachedUser());
  const user = await getCurrentUser();
  renderNavbarAuthState(user);
}

/* ---------------------------------------------------------
   Shared form helpers
--------------------------------------------------------- */
function showMsg(el, text, type) {
  if (!el) return;
  el.textContent = text;
  el.className = `form-msg ${type}`;
}

function setLoading(btn, isLoading) {
  if (!btn) return;
  btn.classList.toggle('is-loading', isLoading);
  btn.disabled = isLoading;
}

function initPasswordToggles() {
  document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.password-field').querySelector('input');
      const nowShowing = input.type === 'password';
      input.type = nowShowing ? 'text' : 'password';
      btn.setAttribute('aria-label', nowShowing ? 'Hide password' : 'Show password');
      btn.textContent = nowShowing ? '🙈' : '👁';
    });
  });
}

/* ---------------------------------------------------------
   Login form
--------------------------------------------------------- */
function initLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return;
  const msg = document.getElementById('login-msg');
  const submitBtn = form.querySelector('.auth-submit');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    showMsg(msg, '', '');
    msg.className = 'form-msg';

    const email = form.email.value.trim();
    const password = form.password.value;

    if (!email || !password) {
      showMsg(msg, 'Please enter your email and password.', 'error');
      return;
    }

    setLoading(submitBtn, true);
    try {
      const user = await loginUser({ email, password });
      showMsg(msg, `Welcome back, ${user.name.split(' ')[0]}! Redirecting…`, 'success');
      setTimeout(() => redirectToDashboard(user.role), 500);
    } catch (err) {
      showMsg(msg, err.message, 'error');
      setLoading(submitBtn, false);
    }
  });
}

/* ---------------------------------------------------------
   Register form
--------------------------------------------------------- */
function isPasswordStrong(pw) {
  return pw.length >= 8 && /[a-z]/.test(pw) && /[A-Z]/.test(pw) && /\d/.test(pw) && /[^\w\s]/.test(pw);
}

function updatePasswordChecklist(pw, checklist) {
  const rules = {
    length: pw.length >= 8,
    lower: /[a-z]/.test(pw),
    upper: /[A-Z]/.test(pw),
    number: /\d/.test(pw),
    special: /[^\w\s]/.test(pw),
  };
  Object.entries(rules).forEach(([key, met]) => {
    const li = checklist.querySelector(`[data-rule="${key}"]`);
    if (li) li.classList.toggle('met', met);
  });
}

function initRegisterForm() {
  const form = document.getElementById('register-form');
  if (!form) return;
  const msg = document.getElementById('register-msg');
  const submitBtn = form.querySelector('.auth-submit');
  const checklist = document.getElementById('pw-checklist');

  if (form.password && checklist) {
    form.password.addEventListener('input', () => updatePasswordChecklist(form.password.value, checklist));
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    showMsg(msg, '', '');
    msg.className = 'form-msg';

    const name = form.name.value.trim();
    const email = form.email.value.trim();
    const password = form.password.value;
    const confirmPassword = form.confirmPassword.value;
    const roleInput = form.querySelector('input[name="role"]:checked');
    const role = roleInput ? roleInput.value : '';

    if (!name || !email || !password || !confirmPassword || !role) {
      showMsg(msg, 'Please fill in all fields and select a role.', 'error');
      return;
    }
    if (password !== confirmPassword) {
      showMsg(msg, 'Passwords do not match.', 'error');
      return;
    }
    if (!isPasswordStrong(password)) {
      showMsg(msg, 'Password does not meet the requirements below.', 'error');
      return;
    }

    setLoading(submitBtn, true);
    try {
      await registerUser({ name, email, password, role });
      showMsg(msg, 'Account created! Redirecting to login…', 'success');
      form.reset();
      if (checklist) updatePasswordChecklist('', checklist);
      setTimeout(() => { window.location.href = 'login.html'; }, 800);
    } catch (err) {
      showMsg(msg, err.message, 'error');
      setLoading(submitBtn, false);
    }
  });
}

/* ---------------------------------------------------------
   Forgot password form (structure only — backend optional per spec)
--------------------------------------------------------- */
function initForgotPasswordForm() {
  const form = document.getElementById('forgot-password-form');
  if (!form) return;
  const msg = document.getElementById('forgot-password-msg');
  const submitBtn = form.querySelector('.auth-submit');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = form.email.value.trim();
    if (!email) {
      showMsg(msg, 'Please enter your email address.', 'error');
      return;
    }
    setLoading(submitBtn, true);
    // No backend endpoint yet — this simulates the request so the UI/UX is complete
    // and ready to wire up to POST /auth/forgot-password once implemented.
    setTimeout(() => {
      showMsg(msg, "If an account exists for that email, we've sent a reset link.", 'success');
      setLoading(submitBtn, false);
      form.reset();
    }, 600);
  });
}

/* ---------------------------------------------------------
   Init
--------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  initNavbarAuthState();
  initLoginForm();
  initRegisterForm();
  initForgotPasswordForm();
  initPasswordToggles();
});
