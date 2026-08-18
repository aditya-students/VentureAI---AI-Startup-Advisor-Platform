/* ==========================================================================
   VentureAI — mentorship-requests.js
   Handles the Founder-facing "My Mentorship Requests" page: list, detail,
   cancel flow.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  var currentView = 'list'; // 'list' or 'detail'
  var currentRequests = [];

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
     Fetch & render requests list
  --------------------------------------------------------- */
  async function fetchRequests() {
    var loading = document.getElementById('requests-loading');
    var container = document.getElementById('requests-container');
    var detail = document.getElementById('request-detail');

    loading.style.display = '';
    container.style.display = 'none';
    detail.style.display = 'none';

    try {
      var data = await apiRequest('/mentorship/requests/sent');
      currentRequests = data.requests || [];
      loading.style.display = 'none';
      container.style.display = '';
      renderRequestList(currentRequests);
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

  function renderRequestList(requests) {
    var container = document.getElementById('requests-container');
    currentView = 'list';

    if (requests.length === 0) {
      container.innerHTML =
        '<div class="mentorship-empty">' +
          '<div class="mentorship-empty__icon">' +
            '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" stroke="#5B3FE4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</div>' +
          '<h3>No mentorship requests yet</h3>' +
          '<p>Discover mentors and send a request to start your mentorship journey.</p>' +
          '<a href="mentor-discovery.html" class="btn btn--primary">Discover Mentors</a>' +
        '</div>';
      return;
    }

    var html = '<div class="mentorship-grid">';
    requests.forEach(function (req) {
      var m = req.mentor || {};
      var initials = getInitials(m.name || '?');
      var avatarContent = m.profile_image
        ? '<img src="' + escapeHTML(m.profile_image) + '" alt="' + escapeHTML(m.name) + '">'
        : escapeHTML(initials);

      html +=
        '<div class="mentorship-request-card" data-request-id="' + req.id + '">' +
          '<div class="mentorship-request-card__header">' +
            '<div class="mentorship-request-card__avatar">' + avatarContent + '</div>' +
            '<div class="mentorship-request-card__info">' +
              '<div class="mentorship-request-card__name">' + escapeHTML(m.name || 'Mentor') + '</div>' +
              '<div class="mentorship-request-card__headline">' + escapeHTML(m.headline || m.company || 'Mentor') + '</div>' +
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
            '<button type="button" class="mentorship-request-card__view-btn" data-view-id="' + req.id + '">View Details</button>' +
          '</div>' +
        '</div>';
    });
    html += '</div>';
    container.innerHTML = html;

    // Wire view detail buttons
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
    var container = document.getElementById('requests-container');
    var detail = document.getElementById('request-detail');

    container.style.display = 'none';
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
    var detail = document.getElementById('request-detail');
    currentView = 'detail';
    var m = req.mentor || {};
    var s = req.startup;
    var initials = getInitials(m.name || '?');
    var avatarContent = m.profile_image
      ? '<img src="' + escapeHTML(m.profile_image) + '" alt="' + escapeHTML(m.name) + '">'
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
            '<div class="mentor-context-bar__name">' + escapeHTML(m.name || 'Mentor') + '</div>' +
            '<div class="mentor-context-bar__headline">' + escapeHTML(m.headline || m.company || 'Mentor') + '</div>' +
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

    // Status-specific display
    var statusLower = (req.status || '').toLowerCase();
    if (statusLower === 'pending') {
      html +=
        '<div class="mentorship-detail__actions" id="detail-actions">' +
          '<button type="button" class="btn btn--reject" id="btn-cancel-request">Cancel Request</button>' +
        '</div>' +
        '<div id="cancel-confirm" style="display:none">' +
          '<div class="mentorship-confirm">' +
            '<h3 class="mentorship-confirm__title">Cancel this mentorship request?</h3>' +
            '<p class="mentorship-confirm__desc">This action cannot be undone. The mentor will no longer see your request.</p>' +
            '<div class="mentorship-confirm__actions">' +
              '<button type="button" class="btn btn--outline" id="btn-keep-request">Keep Request</button>' +
              '<button type="button" class="btn btn--reject" id="btn-confirm-cancel">Cancel Request</button>' +
            '</div>' +
          '</div>' +
        '</div>';
    } else if (statusLower === 'accepted') {
      html +=
        '<div class="mentorship-detail__status-display" style="background:#F0FDF4;border-color:#BBF7D0">' +
          '<h3 style="color:#15803D">Mentorship Active</h3>' +
          '<p style="margin-bottom:1rem;">Your mentor has accepted your request. You can now chat in real time!</p>' +
          '<a href="chat.html?mentor_id=' + (m.id || '') + '" class="btn btn--primary" style="display:inline-flex; align-items:center; gap:0.5rem;">' +
            '<span>Start Chat with Mentor</span>' +
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</a>' +
        '</div>';
    } else if (statusLower === 'rejected') {
      html +=
        '<div class="mentorship-detail__status-display" style="background:#FEF2F2;border-color:#FECACA">' +
          '<h3 style="color:#DC2626">Request Declined</h3>' +
          '<p>' + (req.rejection_reason ? escapeHTML(req.rejection_reason) : 'The mentor was unable to accept your request at this time.') + '</p>' +
        '</div>';
    } else if (statusLower === 'cancelled') {
      html +=
        '<div class="mentorship-detail__status-display">' +
          '<h3>Request Cancelled</h3>' +
          '<p>You cancelled this mentorship request.</p>' +
        '</div>';
    }

    html += '</div>';
    detail.innerHTML = html;

    // Wire back button
    document.getElementById('detail-back-btn').addEventListener('click', showListView);

    // Wire cancel flow
    if (statusLower === 'pending') {
      document.getElementById('btn-cancel-request').addEventListener('click', function () {
        document.getElementById('detail-actions').style.display = 'none';
        document.getElementById('cancel-confirm').style.display = '';
      });
      document.getElementById('btn-keep-request').addEventListener('click', function () {
        document.getElementById('cancel-confirm').style.display = 'none';
        document.getElementById('detail-actions').style.display = '';
      });
      document.getElementById('btn-confirm-cancel').addEventListener('click', function () {
        cancelRequest(req.id);
      });
    }
  }

  async function cancelRequest(requestId) {
    var confirmBtn = document.getElementById('btn-confirm-cancel');
    if (confirmBtn) {
      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Cancelling…';
    }
    try {
      var updated = await apiRequest('/mentorship/requests/' + requestId + '/cancel', { method: 'PATCH' });
      showToast('Mentorship request cancelled.', 'success');
      renderRequestDetail(updated);
    } catch (err) {
      showToast(err.message || 'Unable to cancel request.', 'error');
      if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Cancel Request';
      }
    }
  }

  function showListView() {
    var container = document.getElementById('requests-container');
    var detail = document.getElementById('request-detail');
    detail.style.display = 'none';
    container.style.display = '';
    currentView = 'list';
    fetchRequests();
  }

  /* ---------------------------------------------------------
     Init
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async function () {
    toastEl = document.getElementById('requests-toast');

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

    fetchRequests();
  });

})();
