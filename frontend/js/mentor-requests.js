/* ==========================================================================
   VentureAI — mentor-requests.js
   Handles the Mentor-facing "Mentorship Requests" page: list, filter,
   detail, accept/reject flows.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  var currentFilter = 'all';
  var currentView = 'list';

  /* ---------------------------------------------------------
     Escape HTML (XSS prevention)
  --------------------------------------------------------- */
  function escapeHTML(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------------------------------------------------------
     Toast
  --------------------------------------------------------- */
  var toastEl;
  var toastTimer = null;

  function showToast(message, type) {
    if (toastTimer) clearTimeout(toastTimer);
    toastEl.textContent = message;
    toastEl.className = 'profile-toast profile-toast--' + type + ' show';
    toastTimer = setTimeout(function () {
      toastEl.classList.remove('show');
    }, 4000);
  }

  /* ---------------------------------------------------------
     Date formatting
  --------------------------------------------------------- */
  function formatDate(dateStr) {
    if (!dateStr) return '—';
    var d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  /* ---------------------------------------------------------
     Status badge HTML
  --------------------------------------------------------- */
  function statusBadge(status) {
    var s = (status || '').toLowerCase();
    return '<span class="mentorship-status-badge mentorship-status-badge--' + escapeHTML(s) + '">' +
      escapeHTML(status) + '</span>';
  }

  /* ---------------------------------------------------------
     Fetch & render
  --------------------------------------------------------- */
  async function fetchRequests() {
    var loading = document.getElementById('mentor-requests-loading');
    var container = document.getElementById('mentor-requests-container');
    var detail = document.getElementById('mentor-request-detail');

    loading.style.display = '';
    container.style.display = 'none';
    detail.style.display = 'none';

    var url = '/mentorship/requests/received';
    if (currentFilter !== 'all') {
      url += '?status=' + encodeURIComponent(currentFilter);
    }

    try {
      var data = await apiRequest(url);
      var requests = data.requests || [];
      loading.style.display = 'none';
      container.style.display = '';
      renderRequestList(requests);
      updatePendingBadge(data);
    } catch (err) {
      loading.style.display = 'none';
      container.style.display = '';
      container.innerHTML =
        '<div class="discovery-error">' +
          '<div class="discovery-error__icon">' +
            '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 9v4M12 17h.01" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" stroke="#DC2626" stroke-width="2"/></svg>' +
          '</div>' +
          '<h3>Unable to load requests</h3>' +
          '<p>Something went wrong. Please try again.</p>' +
          '<button type="button" class="btn btn--primary" id="retry-btn">Retry</button>' +
        '</div>';
      document.getElementById('retry-btn').addEventListener('click', fetchRequests);
    }
  }

  function updatePendingBadge(data) {
    var badge = document.getElementById('pending-badge');
    // Count pending from full list
    if (currentFilter === 'all' && data.requests) {
      var pendingCount = data.requests.filter(function (r) {
        return (r.status || '').toLowerCase() === 'pending';
      }).length;
      if (pendingCount > 0) {
        badge.innerHTML = '<span class="mentorship-pending-count">' + pendingCount + '</span>';
      } else {
        badge.innerHTML = '';
      }
    }
  }

  function renderRequestList(requests) {
    var container = document.getElementById('mentor-requests-container');
    currentView = 'list';

    if (requests.length === 0) {
      var emptyMsg = currentFilter === 'all'
        ? 'No incoming mentorship requests yet.'
        : 'No ' + currentFilter + ' requests.';
      var emptyDesc = currentFilter === 'all'
        ? 'New founder requests will appear here once founders discover your profile.'
        : 'Try a different filter to see other requests.';

      container.innerHTML =
        '<div class="mentorship-empty">' +
          '<div class="mentorship-empty__icon">' +
            '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="#5B3FE4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9" cy="7" r="4" stroke="#5B3FE4" stroke-width="2"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="#5B3FE4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</div>' +
          '<h3>' + escapeHTML(emptyMsg) + '</h3>' +
          '<p>' + escapeHTML(emptyDesc) + '</p>' +
        '</div>';
      return;
    }

    var html = '<div class="mentorship-grid">';
    requests.forEach(function (req) {
      var f = req.founder || {};
      var s = req.startup;
      var initials = getInitials(f.name || '?');
      var avatarContent = f.profile_image
        ? '<img src="' + escapeHTML(f.profile_image) + '" alt="' + escapeHTML(f.name) + '">'
        : escapeHTML(initials);

      var startupLine = s ? escapeHTML(s.name) + ' • ' + escapeHTML(s.industry || 'Startup') : 'Startup not specified';

      html +=
        '<div class="mentorship-request-card" data-request-id="' + req.id + '">' +
          '<div class="mentorship-request-card__header">' +
            '<div class="mentorship-request-card__avatar">' + avatarContent + '</div>' +
            '<div class="mentorship-request-card__info">' +
              '<div class="mentorship-request-card__name">' + escapeHTML(f.name || 'Founder') + '</div>' +
              '<div class="mentorship-request-card__headline">' + startupLine + '</div>' +
            '</div>' +
          '</div>' +
          '<div class="mentorship-request-card__meta">' +
            '<span class="mentorship-request-card__tag">' + escapeHTML(req.mentorship_area) + '</span>' +
            '<span class="mentorship-request-card__tag mentorship-request-card__tag--stage">' + escapeHTML(req.startup_stage) + '</span>' +
          '</div>' +
          '<div class="mentorship-request-card__footer">' +
            '<div>' +
              statusBadge(req.status) +
              '<div class="mentorship-request-card__date">' + formatDate(req.created_at) + '</div>' +
            '</div>' +
            '<button type="button" class="mentorship-request-card__view-btn" data-view-id="' + req.id + '">View Request</button>' +
          '</div>' +
        '</div>';
    });
    html += '</div>';
    container.innerHTML = html;

    // Wire view buttons
    container.querySelectorAll('[data-view-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        loadRequestDetail(parseInt(btn.dataset.viewId, 10));
      });
    });
  }

  /* ---------------------------------------------------------
     Request detail view
  --------------------------------------------------------- */
  async function loadRequestDetail(requestId) {
    var container = document.getElementById('mentor-requests-container');
    var detail = document.getElementById('mentor-request-detail');
    var toolbar = document.getElementById('status-toolbar');

    container.style.display = 'none';
    toolbar.style.display = 'none';
    detail.style.display = '';
    detail.innerHTML =
      '<div class="mentor-detail-loading" style="padding:40px">' +
        '<div class="mentor-detail-loading__spinner"></div>' +
        '<p style="color:var(--muted)">Loading request…</p>' +
      '</div>';

    try {
      var req = await apiRequest('/mentorship/requests/' + requestId);
      renderRequestDetail(req);
    } catch (err) {
      detail.innerHTML =
        '<div class="discovery-error" style="padding:40px">' +
          '<h3>Unable to load request</h3>' +
          '<p>' + escapeHTML(err.message || 'Something went wrong.') + '</p>' +
          '<button type="button" class="btn btn--outline" id="detail-back-err">Back to Requests</button>' +
        '</div>';
      document.getElementById('detail-back-err').addEventListener('click', showListView);
    }
  }

  function renderRequestDetail(req) {
    var detail = document.getElementById('mentor-request-detail');
    currentView = 'detail';
    var f = req.founder || {};
    var s = req.startup;
    var initials = getInitials(f.name || '?');
    var avatarContent = f.profile_image
      ? '<img src="' + escapeHTML(f.profile_image) + '" alt="' + escapeHTML(f.name) + '">'
      : escapeHTML(initials);

    var html =
      '<div class="mentorship-detail">' +
        '<button type="button" class="mentorship-detail__back" id="detail-back-btn">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M19 12H5M12 19l-7-7 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          'Back to Requests' +
        '</button>' +

        '<div class="mentor-context-bar">' +
          '<div class="mentor-context-bar__avatar">' + avatarContent + '</div>' +
          '<div class="mentor-context-bar__info">' +
            '<div class="mentor-context-bar__name">' + escapeHTML(f.name || 'Founder') + '</div>' +
            '<div class="mentor-context-bar__headline">Founder</div>' +
          '</div>' +
        '</div>';

    // Startup context
    if (s) {
      html +=
        '<div class="startup-context">' +
          '<div class="startup-context__item"><span class="startup-context__label">Startup</span><span class="startup-context__value">' + escapeHTML(s.name) + '</span></div>' +
          '<div class="startup-context__item"><span class="startup-context__label">Stage</span><span class="startup-context__value">' + escapeHTML(s.stage) + '</span></div>' +
          '<div class="startup-context__item"><span class="startup-context__label">Industry</span><span class="startup-context__value">' + escapeHTML(s.industry || 'Not set') + '</span></div>' +
        '</div>';
    }

    html +=
      '<div class="mentorship-detail__section">' +
        '<div class="mentorship-detail__label">Status</div>' +
        statusBadge(req.status) +
      '</div>' +
      '<div class="mentorship-detail__section">' +
        '<div class="mentorship-detail__label">Mentorship Area</div>' +
        '<div class="mentorship-detail__value">' + escapeHTML(req.mentorship_area) + '</div>' +
      '</div>' +
      '<div class="mentorship-detail__section">' +
        '<div class="mentorship-detail__label">Startup Stage</div>' +
        '<div class="mentorship-detail__value">' + escapeHTML(req.startup_stage) + '</div>' +
      '</div>' +
      '<div class="mentorship-detail__section">' +
        '<div class="mentorship-detail__label">Challenge</div>' +
        '<div class="mentorship-detail__value">' + escapeHTML(req.challenge) + '</div>' +
      '</div>';

    if (req.message) {
      html +=
        '<div class="mentorship-detail__section">' +
          '<div class="mentorship-detail__label">Personal Message</div>' +
          '<div class="mentorship-detail__value">' + escapeHTML(req.message) + '</div>' +
        '</div>';
    }

    html +=
      '<div class="mentorship-detail__section">' +
        '<div class="mentorship-detail__label">Requested</div>' +
        '<div class="mentorship-detail__value">' + formatDate(req.created_at) + '</div>' +
      '</div>';

    if (req.responded_at) {
      html +=
        '<div class="mentorship-detail__section">' +
          '<div class="mentorship-detail__label">Response Date</div>' +
          '<div class="mentorship-detail__value">' + formatDate(req.responded_at) + '</div>' +
        '</div>';
    }

    // Status-specific actions
    var statusLower = (req.status || '').toLowerCase();
    if (statusLower === 'pending') {
      html +=
        '<div class="mentorship-detail__actions" id="detail-actions">' +
          '<button type="button" class="btn btn--reject" id="btn-reject-request">Reject Request</button>' +
          '<button type="button" class="btn btn--accept" id="btn-accept-request">Accept Request</button>' +
        '</div>' +
        '<div id="accept-confirm" style="display:none">' +
          '<div class="mentorship-confirm">' +
            '<h3 class="mentorship-confirm__title">Accept this mentorship request?</h3>' +
            '<p class="mentorship-confirm__desc">You will start an active mentorship relationship with this founder.</p>' +
            '<div class="mentorship-confirm__actions">' +
              '<button type="button" class="btn btn--outline" id="btn-cancel-accept">Go Back</button>' +
              '<button type="button" class="btn btn--accept" id="btn-confirm-accept">Accept Request</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div id="reject-confirm" style="display:none">' +
          '<div class="mentorship-confirm">' +
            '<h3 class="mentorship-confirm__title">Reject this mentorship request?</h3>' +
            '<p class="mentorship-confirm__desc">The founder will be notified that their request was declined.</p>' +
            '<div class="mentorship-form-group" style="text-align:left;margin:16px 0 0">' +
              '<label for="rejection-reason">Reason (optional)</label>' +
              '<textarea id="rejection-reason" placeholder="Provide a brief reason to help the founder understand..." maxlength="500" style="min-height:60px"></textarea>' +
            '</div>' +
            '<div class="mentorship-confirm__actions" style="margin-top:16px">' +
              '<button type="button" class="btn btn--outline" id="btn-cancel-reject">Go Back</button>' +
              '<button type="button" class="btn btn--reject" id="btn-confirm-reject">Reject Request</button>' +
            '</div>' +
          '</div>' +
        '</div>';
    } else if (statusLower === 'accepted') {
      html +=
        '<div class="mentorship-detail__status-display" style="background:#F0FDF4;border-color:#BBF7D0">' +
          '<h3 style="color:#15803D">Mentorship Active</h3>' +
          '<p style="margin-bottom:1rem;">You are actively mentoring this founder. Communication is enabled!</p>' +
          '<a href="chat.html?connection_id=' + req.id + '" class="btn btn--primary" style="display:inline-flex; align-items:center; gap:0.5rem;">' +
            '<span>Start Chat with Founder</span>' +
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</a>' +
        '</div>';
    } else if (statusLower === 'rejected') {
      html +=
        '<div class="mentorship-detail__status-display" style="background:#FEF2F2;border-color:#FECACA">' +
          '<h3 style="color:#DC2626">Request Rejected</h3>' +
          '<p>' + (req.rejection_reason ? escapeHTML(req.rejection_reason) : 'You declined this mentorship request.') + '</p>' +
        '</div>';
    } else if (statusLower === 'cancelled') {
      html +=
        '<div class="mentorship-detail__status-display">' +
          '<h3>Request Cancelled</h3>' +
          '<p>The founder cancelled this mentorship request.</p>' +
        '</div>';
    }

    html += '</div>';
    detail.innerHTML = html;

    // Wire back
    document.getElementById('detail-back-btn').addEventListener('click', showListView);

    // Wire accept/reject flows
    if (statusLower === 'pending') {
      // Accept flow
      document.getElementById('btn-accept-request').addEventListener('click', function () {
        document.getElementById('detail-actions').style.display = 'none';
        document.getElementById('accept-confirm').style.display = '';
      });
      document.getElementById('btn-cancel-accept').addEventListener('click', function () {
        document.getElementById('accept-confirm').style.display = 'none';
        document.getElementById('detail-actions').style.display = '';
      });
      document.getElementById('btn-confirm-accept').addEventListener('click', function () {
        acceptRequest(req.id);
      });

      // Reject flow
      document.getElementById('btn-reject-request').addEventListener('click', function () {
        document.getElementById('detail-actions').style.display = 'none';
        document.getElementById('reject-confirm').style.display = '';
      });
      document.getElementById('btn-cancel-reject').addEventListener('click', function () {
        document.getElementById('reject-confirm').style.display = 'none';
        document.getElementById('detail-actions').style.display = '';
      });
      document.getElementById('btn-confirm-reject').addEventListener('click', function () {
        rejectRequest(req.id);
      });
    }
  }

  async function acceptRequest(requestId) {
    var btn = document.getElementById('btn-confirm-accept');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Accepting…';
    }
    try {
      var updated = await apiRequest('/mentorship/requests/' + requestId + '/accept', { method: 'PATCH' });
      showToast('Mentorship request accepted!', 'success');
      renderRequestDetail(updated);
    } catch (err) {
      showToast(err.message || 'Unable to accept request.', 'error');
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Accept Request';
      }
    }
  }

  async function rejectRequest(requestId) {
    var btn = document.getElementById('btn-confirm-reject');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Rejecting…';
    }
    var reason = '';
    var reasonEl = document.getElementById('rejection-reason');
    if (reasonEl) reason = reasonEl.value.trim();

    try {
      var updated = await apiRequest('/mentorship/requests/' + requestId + '/reject', {
        method: 'PATCH',
        body: { rejection_reason: reason || null },
      });
      showToast('Mentorship request rejected.', 'success');
      renderRequestDetail(updated);
    } catch (err) {
      showToast(err.message || 'Unable to reject request.', 'error');
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Reject Request';
      }
    }
  }

  function showListView() {
    var container = document.getElementById('mentor-requests-container');
    var detail = document.getElementById('mentor-request-detail');
    var toolbar = document.getElementById('status-toolbar');
    detail.style.display = 'none';
    toolbar.style.display = '';
    container.style.display = '';
    currentView = 'list';
    fetchRequests();
  }

  /* ---------------------------------------------------------
     Filter tabs
  --------------------------------------------------------- */
  function initFilters() {
    var buttons = document.querySelectorAll('[data-status-filter]');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        buttons.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        currentFilter = btn.dataset.statusFilter;
        fetchRequests();
      });
    });
  }

  /* ---------------------------------------------------------
     Init
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async function () {
    toastEl = document.getElementById('mentor-requests-toast');

    // Wait for route guard
    await new Promise(function (resolve) {
      var attempts = 0;
      var check = function () {
        if (document.body.classList.contains('route-verified')) resolve();
        else if (attempts > 60) resolve();
        else { attempts++; setTimeout(check, 50); }
      };
      check();
    });

    initFilters();
    fetchRequests();
  });

})();
