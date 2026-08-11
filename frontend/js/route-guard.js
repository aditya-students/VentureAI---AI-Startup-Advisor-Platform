/* ==========================================================================
   VentureAI — route-guard.js
   Protects dashboard pages: unauthenticated users are sent to login.html,
   authenticated users with the wrong role are sent to unauthorized.html.

   Depends on auth.js being loaded first (uses getCurrentUser()).
   Include this ONLY on the dashboard pages — it's a no-op elsewhere.
   ========================================================================== */

const DASHBOARD_ROLES = {
  'founder-dashboard.html': 'Founder',
  'founder-dashboard': 'Founder',
  'founder-profile.html': 'Founder',
  'founder-profile': 'Founder',
  'startup-workspace.html': 'Founder',
  'startup-workspace': 'Founder',
  'mentor-dashboard.html': 'Mentor',
  'mentor-dashboard': 'Mentor',
  'admin-dashboard.html': 'Admin',
  'admin-dashboard': 'Admin',
};

async function protectRoute() {
  try {
    let rawPage = (window.location.pathname.split('/').pop() || 'index.html').split('?')[0].split('#')[0].toLowerCase();
    if (!rawPage || rawPage === '/') rawPage = 'index.html';

    let requiredRole = DASHBOARD_ROLES[rawPage];
    if (!requiredRole && !rawPage.endsWith('.html')) {
      requiredRole = DASHBOARD_ROLES[`${rawPage}.html`];
    }

    if (!requiredRole) {
      // If not a protected page or unknown route, reveal content to prevent hanging loader
      if (document.body.hasAttribute('data-protected')) {
        document.body.classList.add('route-verified');
      }
      return;
    }

    let user = await getCurrentUser();

    // If access token expired or failed, attempt silent refresh
    if (!user) {
      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });
        if (refreshRes.ok) {
          user = await getCurrentUser();
        }
      } catch (_) {
        // Refresh failed
      }
    }

    if (!user) {
      window.location.href = `login.html?next=${encodeURIComponent(rawPage)}`;
      return;
    }

    if (user.role !== requiredRole) {
      window.location.href = 'unauthorized.html';
      return;
    }

    // Populate placeholders
    document.querySelectorAll('[data-user-name]').forEach(el => { el.textContent = user.name; });
    document.querySelectorAll('[data-user-email]').forEach(el => { el.textContent = user.email; });
    document.querySelectorAll('[data-user-role]').forEach(el => { el.textContent = user.role; });

    // Reveal protected content
    document.body.classList.add('route-verified');
  } catch (err) {
    console.error('Route guard verification error:', err);
    // Ensure body doesn't stay hidden indefinitely on error
    document.body.classList.add('route-verified');
  }
}

document.addEventListener('DOMContentLoaded', protectRoute);
