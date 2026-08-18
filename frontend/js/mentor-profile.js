/* ==========================================================================
   VentureAI — mentor-profile.js
   Handles loading, viewing, editing, and saving the mentor profile.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------------------------------------------------
     Constants — allowed values for multi-select fields
  --------------------------------------------------------- */
  const INDUSTRIES = [
    'SaaS', 'FinTech', 'HealthTech', 'EdTech', 'E-commerce',
    'AI/ML', 'Cybersecurity', 'Logistics', 'CleanTech', 'Consumer Tech', 'Other',
  ];

  const AREAS_OF_EXPERTISE = [
    'Product Strategy', 'Business Strategy', 'Go-To-Market', 'Marketing',
    'Sales', 'Fundraising', 'Finance', 'Operations', 'Technology', 'AI/ML',
    'Product-Market Fit', 'Customer Discovery', 'Business Model', 'Legal/Compliance',
  ];

  const STARTUP_STAGES = [
    'Idea Stage', 'Pre-MVP', 'MVP', 'Early Revenue', 'Growth Stage', 'Scaling',
  ];

  const MENTORSHIP_AREAS = [
    'Idea Validation', 'Product Development', 'Business Model', 'Go-To-Market',
    'Fundraising', 'Pitching', 'Operations', 'Technology', 'Scaling',
  ];

  const AVAILABILITY_MAP = {
    'Available': { label: 'Available', class: 'mentor-availability-badge--available' },
    'Limited Availability': { label: 'Limited Availability', class: 'mentor-availability-badge--limited' },
    'Currently Unavailable': { label: 'Currently Unavailable', class: 'mentor-availability-badge--unavailable' },
  };

  /* ---------------------------------------------------------
     Completion hints — shown when fields are missing
  --------------------------------------------------------- */
  const COMPLETION_HINTS = [
    { field: 'headline', msg: 'Add a professional headline to make a strong first impression.' },
    { field: 'bio', msg: 'Write a bio to tell mentees about your background.' },
    { field: 'current_role', msg: 'Add your current role to complete your professional info.' },
    { field: 'industries', msg: 'Select your industry expertise to improve future mentor matching.', isArray: true },
    { field: 'areas_of_expertise', msg: 'Add your areas of expertise so founders know where you can help.', isArray: true },
    { field: 'startup_stages', msg: 'Specify which startup stages you can advise on.', isArray: true },
    { field: 'mentorship_areas', msg: 'Select the types of mentoring you provide.', isArray: true },
    { field: 'experience', msg: 'Add your years of experience.', check: (p) => p.years_of_experience == null && p.startup_experience == null && p.mentoring_experience == null },
    { field: 'availability', msg: 'Set your availability status.', check: (p) => !p.availability },
  ];

  /* ---------------------------------------------------------
     State
  --------------------------------------------------------- */
  let currentProfile = null;

  // Working copies of selected tags during edit mode
  let editIndustries = [];
  let editExpertise = [];
  let editStages = [];
  let editMentorship = [];

  /* ---------------------------------------------------------
     DOM references (resolved after DOMContentLoaded)
  --------------------------------------------------------- */
  let viewEl, editEl, toastEl;

  /* ---------------------------------------------------------
     Profile API
  --------------------------------------------------------- */
  async function fetchProfile() {
    return apiRequest('/mentor/profile');
  }

  async function saveProfileData(data) {
    return apiRequest('/mentor/profile', { method: 'PUT', body: data });
  }

  /* ---------------------------------------------------------
     Escape helpers (prevent XSS)
  --------------------------------------------------------- */
  function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------------------------------------------------------
     Render helpers — VIEW mode
  --------------------------------------------------------- */
  function renderViewMode(profile) {
    currentProfile = profile;

    const initials = getInitials(profile.name);

    // Avatar + header
    document.getElementById('profile-avatar').textContent = initials;
    document.getElementById('profile-name').textContent = profile.name;

    // Headline
    const headlineEl = document.getElementById('profile-headline');
    if (profile.headline && profile.headline.trim()) {
      headlineEl.textContent = profile.headline;
      headlineEl.className = 'mentor-profile-headline';
    } else {
      headlineEl.textContent = 'No headline added yet';
      headlineEl.className = 'mentor-profile-headline profile-section__empty';
    }

    // Availability badge
    renderAvailabilityBadge(profile.availability);

    // Profile completion
    renderProfileCompletion(profile);

    // Bio
    const bioEl = document.getElementById('profile-bio');
    if (profile.bio && profile.bio.trim()) {
      bioEl.textContent = profile.bio;
      bioEl.className = 'profile-section__value';
    } else {
      bioEl.textContent = 'No bio added yet.';
      bioEl.className = 'profile-section__empty';
    }

    // Professional info
    renderInfoField('profile-current-role', profile.current_role, 'Not specified');
    renderInfoField('profile-company', profile.company, 'Not specified');
    renderInfoField('profile-location', profile.location, 'Not specified');

    // Tag sections
    renderTagSection('profile-industries', profile.industries);
    renderTagSection('profile-expertise', profile.areas_of_expertise);
    renderTagSection('profile-stages', profile.startup_stages);
    renderTagSection('profile-mentorship', profile.mentorship_areas);

    // Experience
    renderExperienceValue('profile-exp-professional', profile.years_of_experience, 'years');
    renderExperienceValue('profile-exp-startup', profile.startup_experience, 'years');
    renderExperienceValue('profile-exp-mentoring', profile.mentoring_experience, 'years');
  }

  function renderInfoField(elementId, value, placeholder) {
    const el = document.getElementById(elementId);
    if (value && value.trim()) {
      el.textContent = value;
      el.className = 'mentor-info-item__value';
    } else {
      el.textContent = placeholder;
      el.className = 'mentor-info-item__value profile-section__empty';
    }
  }

  function renderTagSection(elementId, tags) {
    const container = document.getElementById(elementId);
    const items = tags || [];
    if (items.length > 0) {
      container.innerHTML = items.map(tag =>
        `<span class="skill-tag">${escapeHTML(tag)}</span>`
      ).join('');
    } else {
      container.innerHTML = '<span class="profile-section__empty">None selected yet.</span>';
    }
  }

  function renderExperienceValue(elementId, value, unit) {
    const el = document.getElementById(elementId);
    if (value != null) {
      el.textContent = value + ' ' + unit;
    } else {
      el.textContent = '—';
    }
  }

  function renderAvailabilityBadge(availability) {
    const badgeEl = document.getElementById('profile-availability-badge');
    const config = AVAILABILITY_MAP[availability];
    if (config) {
      badgeEl.textContent = config.label;
      badgeEl.className = 'mentor-availability-badge ' + config.class;
      badgeEl.style.display = '';
    } else {
      badgeEl.style.display = 'none';
    }
  }

  function renderProfileCompletion(profile) {
    const pct = profile.profile_completion || 0;
    document.getElementById('profile-completion-pct').textContent = pct + '%';
    document.getElementById('profile-completion-fill').style.width = pct + '%';

    // Show a helpful hint for the first incomplete field
    const hintEl = document.getElementById('profile-completion-hint');
    if (pct >= 100) {
      hintEl.textContent = '🎉 Your profile is complete! You\'re ready for mentor matching.';
    } else {
      const hint = getFirstIncompleteHint(profile);
      hintEl.textContent = hint || '';
    }
  }

  function getFirstIncompleteHint(profile) {
    for (const item of COMPLETION_HINTS) {
      if (item.check) {
        if (item.check(profile)) return item.msg;
      } else if (item.isArray) {
        const arr = profile[item.field];
        if (!arr || arr.length === 0) return item.msg;
      } else {
        const val = profile[item.field];
        if (!val || (typeof val === 'string' && !val.trim())) return item.msg;
      }
    }
    return null;
  }

  /* ---------------------------------------------------------
     Multi-select tag rendering (EDIT mode)
  --------------------------------------------------------- */
  function renderEditTagGroup(containerId, allOptions, selectedArray) {
    const container = document.getElementById(containerId);
    container.innerHTML = allOptions.map(option => {
      const isSelected = selectedArray.includes(option);
      return `<button type="button" class="mentor-tag-option${isSelected ? ' selected' : ''}" data-value="${escapeHTML(option)}">${escapeHTML(option)}</button>`;
    }).join('');

    // Wire up toggle behavior
    container.querySelectorAll('.mentor-tag-option').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = btn.dataset.value;
        const arr = getEditArrayForContainer(containerId);
        const idx = arr.indexOf(val);
        if (idx >= 0) {
          arr.splice(idx, 1);
          btn.classList.remove('selected');
        } else {
          arr.push(val);
          btn.classList.add('selected');
        }
      });
    });
  }

  function getEditArrayForContainer(containerId) {
    switch (containerId) {
      case 'edit-industries': return editIndustries;
      case 'edit-expertise': return editExpertise;
      case 'edit-stages': return editStages;
      case 'edit-mentorship': return editMentorship;
      default: return [];
    }
  }

  /* ---------------------------------------------------------
     Mode switching
  --------------------------------------------------------- */
  function enterEditMode() {
    if (!currentProfile) return;

    // Populate header
    document.getElementById('edit-avatar').textContent = getInitials(currentProfile.name);
    document.getElementById('edit-name').textContent = currentProfile.name;
    document.getElementById('edit-email-display').textContent = currentProfile.email;

    // Text fields
    document.getElementById('edit-headline').value = currentProfile.headline || '';
    document.getElementById('edit-bio').value = currentProfile.bio || '';
    document.getElementById('edit-current-role').value = currentProfile.current_role || '';
    document.getElementById('edit-company').value = currentProfile.company || '';
    document.getElementById('edit-location').value = currentProfile.location || '';

    // Experience numbers
    document.getElementById('edit-exp-professional').value = currentProfile.years_of_experience != null ? currentProfile.years_of_experience : '';
    document.getElementById('edit-exp-startup').value = currentProfile.startup_experience != null ? currentProfile.startup_experience : '';
    document.getElementById('edit-exp-mentoring').value = currentProfile.mentoring_experience != null ? currentProfile.mentoring_experience : '';

    // Availability
    document.getElementById('edit-availability').value = currentProfile.availability || 'Available';

    // Discoverability
    document.getElementById('edit-discoverable').checked = currentProfile.is_discoverable !== false;

    // Multi-select tag groups — copy to working arrays and render
    editIndustries = [...(currentProfile.industries || [])];
    editExpertise = [...(currentProfile.areas_of_expertise || [])];
    editStages = [...(currentProfile.startup_stages || [])];
    editMentorship = [...(currentProfile.mentorship_areas || [])];

    renderEditTagGroup('edit-industries', INDUSTRIES, editIndustries);
    renderEditTagGroup('edit-expertise', AREAS_OF_EXPERTISE, editExpertise);
    renderEditTagGroup('edit-stages', STARTUP_STAGES, editStages);
    renderEditTagGroup('edit-mentorship', MENTORSHIP_AREAS, editMentorship);

    // Toggle visibility
    viewEl.classList.add('hidden');
    editEl.classList.add('active');

    editEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function exitEditMode() {
    editEl.classList.remove('active');
    viewEl.classList.remove('hidden');
    viewEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------------------------------------------------------
     Save profile
  --------------------------------------------------------- */
  async function handleSave(e) {
    e.preventDefault();

    const headline = document.getElementById('edit-headline').value.trim() || null;
    const bio = document.getElementById('edit-bio').value.trim() || null;
    const current_role = document.getElementById('edit-current-role').value.trim() || null;
    const company = document.getElementById('edit-company').value.trim() || null;
    const location = document.getElementById('edit-location').value.trim() || null;
    const availability = document.getElementById('edit-availability').value;

    // Parse experience values
    const expProRaw = document.getElementById('edit-exp-professional').value.trim();
    const expStartupRaw = document.getElementById('edit-exp-startup').value.trim();
    const expMentorRaw = document.getElementById('edit-exp-mentoring').value.trim();

    const years_of_experience = expProRaw !== '' ? parseInt(expProRaw, 10) : null;
    const startup_experience = expStartupRaw !== '' ? parseInt(expStartupRaw, 10) : null;
    const mentoring_experience = expMentorRaw !== '' ? parseInt(expMentorRaw, 10) : null;

    // Frontend validation
    if (headline && headline.length > 200) {
      showToast('Headline must be 200 characters or fewer.', 'error');
      return;
    }
    if (bio && bio.length > 2000) {
      showToast('Bio must be 2000 characters or fewer.', 'error');
      return;
    }
    if (current_role && current_role.length > 150) {
      showToast('Current role must be 150 characters or fewer.', 'error');
      return;
    }
    if (company && company.length > 200) {
      showToast('Company must be 200 characters or fewer.', 'error');
      return;
    }

    // Validate experience values
    const expFields = [
      { name: 'Professional experience', value: years_of_experience },
      { name: 'Startup experience', value: startup_experience },
      { name: 'Mentoring experience', value: mentoring_experience },
    ];
    for (const field of expFields) {
      if (field.value !== null) {
        if (isNaN(field.value) || field.value < 0) {
          showToast(`${field.name} must be 0 or greater.`, 'error');
          return;
        }
        if (field.value > 100) {
          showToast(`${field.name} value seems unreasonably high.`, 'error');
          return;
        }
      }
    }

    const saveBtn = document.getElementById('btn-save-profile');
    saveBtn.classList.add('is-loading');
    saveBtn.disabled = true;

    try {
      const is_discoverable = document.getElementById('edit-discoverable').checked;

      const updated = await saveProfileData({
        headline,
        bio,
        current_role,
        company,
        location,
        years_of_experience,
        startup_experience,
        mentoring_experience,
        industries: editIndustries,
        areas_of_expertise: editExpertise,
        startup_stages: editStages,
        mentorship_areas: editMentorship,
        availability,
        is_discoverable,
      });

      renderViewMode(updated);
      exitEditMode();
      showToast('Profile saved successfully!', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to save profile.', 'error');
    } finally {
      saveBtn.classList.remove('is-loading');
      saveBtn.disabled = false;
    }
  }

  /* ---------------------------------------------------------
     Toast notification
  --------------------------------------------------------- */
  let toastTimer = null;

  function showToast(message, type) {
    if (toastTimer) clearTimeout(toastTimer);

    toastEl.textContent = message;
    toastEl.className = `profile-toast profile-toast--${type} show`;

    toastTimer = setTimeout(() => {
      toastEl.classList.remove('show');
    }, 3500);
  }

  /* ---------------------------------------------------------
     Initialization
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async () => {
    viewEl = document.getElementById('profile-view');
    editEl = document.getElementById('profile-edit');
    toastEl = document.getElementById('profile-toast');

    // Wait for route-guard verification before loading data
    await new Promise(resolve => {
      let attempts = 0;
      const check = () => {
        if (document.body.classList.contains('route-verified')) {
          resolve();
        } else if (attempts > 60) {
          resolve();
        } else {
          attempts++;
          setTimeout(check, 50);
        }
      };
      check();
    });

    // Load profile
    try {
      const profile = await fetchProfile();
      renderViewMode(profile);
    } catch (err) {
      showToast(err.message || 'Failed to load profile.', 'error');
    }

    // Wire up buttons
    document.getElementById('btn-edit-profile').addEventListener('click', enterEditMode);
    document.getElementById('btn-cancel-edit').addEventListener('click', exitEditMode);
    document.getElementById('profile-form').addEventListener('submit', handleSave);
  });

})();
