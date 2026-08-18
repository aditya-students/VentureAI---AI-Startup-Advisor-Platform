/* ==========================================================================
   VentureAI — mentor-detail.js
   Handles the Founder-facing Mentor Detail (public profile) page.
   Loads a single mentor's profile by ID from URL params and renders it.
   Includes the Request Mentorship modal workflow.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  var currentMentor = null;
  var founderStartup = null;

  var AVAILABILITY_MAP = {
    'Available': { label: 'Available', class: 'mentor-availability-badge--available' },
    'Limited Availability': { label: 'Limited Availability', class: 'mentor-availability-badge--limited' },
    'Currently Unavailable': { label: 'Currently Unavailable', class: 'mentor-availability-badge--unavailable' },
  };

  /* ---------------------------------------------------------
     Escape helpers (prevent XSS)
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
     Render profile data
  --------------------------------------------------------- */
  function renderProfile(mentor) {
    currentMentor = mentor;
    var card = document.getElementById('mentor-detail-card');
    var loading = document.getElementById('mentor-detail-loading');

    // Avatar
    var avatarEl = document.getElementById('detail-avatar');
    if (mentor.profile_image) {
      avatarEl.innerHTML = '<img src="' + escapeHTML(mentor.profile_image) + '" alt="' + escapeHTML(mentor.name) + '">';
    } else {
      avatarEl.textContent = getInitials(mentor.name);
    }

    // Name + headline
    document.getElementById('detail-name').textContent = mentor.name;
    var headlineEl = document.getElementById('detail-headline');
    if (mentor.headline && mentor.headline.trim()) {
      headlineEl.textContent = mentor.headline;
      headlineEl.className = 'mentor-detail__headline';
    } else {
      headlineEl.textContent = 'Mentor';
      headlineEl.className = 'mentor-detail__headline profile-section__empty';
    }

    // Availability badge
    var badgeEl = document.getElementById('detail-availability-badge');
    var config = AVAILABILITY_MAP[mentor.availability];
    if (config) {
      badgeEl.textContent = config.label;
      badgeEl.className = 'mentor-availability-badge ' + config.class;
      badgeEl.style.display = '';
    } else {
      badgeEl.style.display = 'none';
    }

    // Experience stats
    renderExpValue('detail-exp-professional', mentor.years_of_experience);
    renderExpValue('detail-exp-startup', mentor.startup_experience);
    renderExpValue('detail-exp-mentoring', mentor.mentoring_experience);

    // Bio
    var bioEl = document.getElementById('detail-bio');
    if (mentor.bio && mentor.bio.trim()) {
      bioEl.textContent = mentor.bio;
      bioEl.className = 'profile-section__value';
    } else {
      bioEl.textContent = 'No bio provided.';
      bioEl.className = 'profile-section__empty';
    }

    // Professional info
    renderInfoField('detail-current-role', mentor.current_role);
    renderInfoField('detail-company', mentor.company);
    renderInfoField('detail-location', mentor.location);

    // Tag sections
    renderTags('detail-industries', mentor.industries);
    renderTags('detail-expertise', mentor.areas_of_expertise);
    renderTags('detail-stages', mentor.startup_stages);
    renderTags('detail-mentorship', mentor.mentorship_areas);

    // Update page title
    document.title = mentor.name + ' — Mentor Profile — VentureAI';

    // Preserve back link query params
    var backLink = document.getElementById('back-link');
    var referrerUrl = document.referrer;
    if (referrerUrl && referrerUrl.includes('mentor-discovery')) {
      try {
        var refUrl = new URL(referrerUrl);
        backLink.href = 'mentor-discovery.html' + refUrl.search;
      } catch (_) { /* keep default */ }
    }

    // Show card, hide loading
    loading.style.display = 'none';
    card.style.display = '';
  }

  function renderExpValue(elementId, value) {
    var el = document.getElementById(elementId);
    if (value != null) {
      el.textContent = value + ' years';
    } else {
      el.textContent = '—';
    }
  }

  function renderInfoField(elementId, value) {
    var el = document.getElementById(elementId);
    if (value && value.trim()) {
      el.textContent = value;
      el.className = 'mentor-info-item__value';
    } else {
      el.textContent = 'Not specified';
      el.className = 'mentor-info-item__value profile-section__empty';
    }
  }

  function renderTags(elementId, tags) {
    var container = document.getElementById(elementId);
    var items = tags || [];
    if (items.length > 0) {
      container.innerHTML = items.map(function (tag) {
        return '<span class="skill-tag">' + escapeHTML(tag) + '</span>';
      }).join('');
    } else {
      container.innerHTML = '<span class="profile-section__empty">None specified.</span>';
    }
  }

  /* ---------------------------------------------------------
     Error state
  --------------------------------------------------------- */
  function showError(message) {
    var loading = document.getElementById('mentor-detail-loading');
    var errorEl = document.getElementById('mentor-detail-error');

    loading.style.display = 'none';
    errorEl.style.display = '';
    errorEl.innerHTML =
      '<div class="discovery-error">' +
        '<div class="discovery-error__icon">' +
          '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 9v4M12 17h.01" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" stroke="#DC2626" stroke-width="2"/></svg>' +
        '</div>' +
        '<h3>Mentor not found</h3>' +
        '<p>' + escapeHTML(message) + '</p>' +
        '<a href="mentor-discovery.html" class="btn btn--primary">Back to Mentors</a>' +
      '</div>';
  }

  /* ---------------------------------------------------------
     Request Mentorship — Button State
  --------------------------------------------------------- */
  function updateRequestButton(checkData) {
    var btn = document.getElementById('btn-request-mentorship');
    if (!btn) return;

    // Reset classes
    btn.classList.remove('btn--pending', 'btn--active-mentorship');
    btn.disabled = false;

    if (checkData && checkData.has_active_mentorship) {
      btn.innerHTML =
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/></svg>' +
        'Active Mentorship';
      btn.classList.add('btn--active-mentorship');
      btn.disabled = true;
    } else if (checkData && checkData.has_pending_request) {
      btn.innerHTML =
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' +
        'Request Pending';
      btn.classList.add('btn--pending');
      btn.disabled = true;
    } else {
      btn.innerHTML =
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        'Request Mentorship';
    }
  }

  async function checkMentorStatus(mentorId) {
    try {
      var data = await apiRequest('/mentorship/requests/check/' + encodeURIComponent(mentorId));
      updateRequestButton(data);
      return data;
    } catch (_) {
      // If check fails, keep button as default
      updateRequestButton(null);
      return null;
    }
  }

  /* ---------------------------------------------------------
     Request Mentorship — Modal
  --------------------------------------------------------- */
  var modalOverlay, requestForm, sendBtn;
  var isSubmitting = false;

  function openModal() {
    if (!currentMentor) return;

    // Populate mentor context
    var avatarEl = document.getElementById('modal-mentor-avatar');
    if (currentMentor.profile_image) {
      avatarEl.innerHTML = '<img src="' + escapeHTML(currentMentor.profile_image) + '" alt="' + escapeHTML(currentMentor.name) + '">';
    } else {
      avatarEl.textContent = getInitials(currentMentor.name);
    }
    document.getElementById('modal-mentor-name').textContent = currentMentor.name;
    document.getElementById('modal-mentor-headline').textContent = currentMentor.headline || currentMentor.current_role || 'Mentor';

    // Populate startup context
    if (founderStartup) {
      document.getElementById('modal-startup-context').style.display = '';
      document.getElementById('modal-startup-name').textContent = founderStartup.name;
      document.getElementById('modal-startup-stage').textContent = founderStartup.stage || 'Idea';
      document.getElementById('modal-startup-industry').textContent = founderStartup.industry || 'Not set';
    } else {
      document.getElementById('modal-startup-context').style.display = 'none';
    }

    // Reset form
    requestForm.reset();
    clearFieldErrors();
    hideModalError();
    updateCharCount('req-challenge', 'challenge-count');
    updateCharCount('req-message', 'message-count');

    // Open
    modalOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modalOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  function showModalError(msg) {
    var el = document.getElementById('modal-error');
    el.textContent = msg;
    el.classList.add('visible');
  }

  function hideModalError() {
    var el = document.getElementById('modal-error');
    el.textContent = '';
    el.classList.remove('visible');
  }

  function clearFieldErrors() {
    var errors = requestForm.querySelectorAll('.field-error');
    for (var i = 0; i < errors.length; i++) {
      errors[i].textContent = '';
    }
  }

  function showFieldError(id, msg) {
    var el = document.getElementById(id);
    if (el) el.textContent = msg;
  }

  function updateCharCount(textareaId, countId) {
    var textarea = document.getElementById(textareaId);
    var counter = document.getElementById(countId);
    if (!textarea || !counter) return;
    var len = textarea.value.length;
    counter.textContent = len + ' / 1000';
    counter.classList.toggle('over', len > 1000);
  }

  function validateForm() {
    clearFieldErrors();
    hideModalError();
    var valid = true;

    var area = document.getElementById('req-mentorship-area').value;
    if (!area) {
      showFieldError('err-mentorship-area', 'Please select a mentorship area.');
      valid = false;
    }

    var stage = document.getElementById('req-startup-stage').value;
    if (!stage) {
      showFieldError('err-startup-stage', 'Please select your startup stage.');
      valid = false;
    }

    var challenge = document.getElementById('req-challenge').value.trim();
    if (!challenge) {
      showFieldError('err-challenge', 'Please describe the challenge you are facing.');
      valid = false;
    } else if (challenge.length < 20) {
      showFieldError('err-challenge', 'Challenge must be at least 20 characters.');
      valid = false;
    } else if (challenge.length > 1000) {
      showFieldError('err-challenge', 'Challenge must be 1000 characters or fewer.');
      valid = false;
    }

    var message = document.getElementById('req-message').value.trim();
    if (message.length > 1000) {
      showFieldError('err-message', 'Message must be 1000 characters or fewer.');
      valid = false;
    }

    return valid;
  }

  async function submitRequest(e) {
    e.preventDefault();
    if (isSubmitting) return;
    if (!validateForm()) return;

    isSubmitting = true;
    sendBtn.disabled = true;
    var origHTML = sendBtn.innerHTML;
    sendBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" stroke-dasharray="28" stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite"/></circle></svg> Sending…';

    var payload = {
      mentor_id: currentMentor.id,
      mentorship_area: document.getElementById('req-mentorship-area').value,
      startup_stage: document.getElementById('req-startup-stage').value,
      challenge: document.getElementById('req-challenge').value.trim(),
      message: document.getElementById('req-message').value.trim() || null,
    };

    try {
      await apiRequest('/mentorship/requests', { method: 'POST', body: payload });
      closeModal();
      showToast('Mentorship request sent successfully!', 'success');
      // Update button to pending state
      updateRequestButton({ has_pending_request: true, has_active_mentorship: false });
    } catch (err) {
      showModalError(err.message || 'Something went wrong. Please try again.');
    } finally {
      isSubmitting = false;
      sendBtn.disabled = false;
      sendBtn.innerHTML = origHTML;
    }
  }

  /* ---------------------------------------------------------
     Fetch founder's startup
  --------------------------------------------------------- */
  async function fetchStartup() {
    try {
      founderStartup = await apiRequest('/startups/me');
    } catch (_) {
      founderStartup = null;
    }
  }

  /* ---------------------------------------------------------
     Init
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async function () {
    toastEl = document.getElementById('detail-toast');
    modalOverlay = document.getElementById('request-modal-overlay');
    requestForm = document.getElementById('request-form');
    sendBtn = document.getElementById('btn-send-request');

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

    // Get mentor ID from URL
    var params = new URLSearchParams(window.location.search);
    var mentorId = params.get('id');

    if (!mentorId) {
      showError('No mentor ID provided.');
      return;
    }

    // Fetch mentor profile and startup in parallel
    try {
      var mentorPromise = apiRequest('/mentor/discover/' + encodeURIComponent(mentorId));
      var startupPromise = fetchStartup();
      var mentor = await mentorPromise;
      await startupPromise;
      renderProfile(mentor);
    } catch (err) {
      showError(err.message || 'Unable to load this mentor\'s profile.');
      return;
    }

    // Check request status
    await checkMentorStatus(mentorId);

    // Request Mentorship button
    document.getElementById('btn-request-mentorship').addEventListener('click', function () {
      var btn = document.getElementById('btn-request-mentorship');
      if (btn.disabled) return;
      openModal();
    });

    // Modal close
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modalOverlay.classList.contains('open')) closeModal();
    });

    // Char counters
    document.getElementById('req-challenge').addEventListener('input', function () {
      updateCharCount('req-challenge', 'challenge-count');
    });
    document.getElementById('req-message').addEventListener('input', function () {
      updateCharCount('req-message', 'message-count');
    });

    // Form submit
    requestForm.addEventListener('submit', submitRequest);
  });

})();
