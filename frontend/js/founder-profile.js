/* ==========================================================================
   VentureAI — founder-profile.js
   Handles loading, viewing, editing, and saving the founder profile.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------------------------------------------------
     State
  --------------------------------------------------------- */
  let currentProfile = null;   // latest profile data from the API
  let editSkills = [];         // working copy of skills during edit mode

  /* ---------------------------------------------------------
     DOM references (resolved after DOMContentLoaded)
  --------------------------------------------------------- */
  let viewEl, editEl, toastEl;

  /* ---------------------------------------------------------
     Profile API
  --------------------------------------------------------- */
  async function fetchProfile() {
    return apiRequest('/founder/profile');
  }

  async function saveProfileData(data) {
    return apiRequest('/founder/profile', { method: 'PUT', body: data });
  }

  /* ---------------------------------------------------------
     Render helpers
  --------------------------------------------------------- */
  function renderViewMode(profile) {
    currentProfile = profile;

    const initials = getInitials(profile.name);

    // Avatar + header
    document.getElementById('profile-avatar').textContent = initials;
    document.getElementById('profile-name').textContent = profile.name;
    document.getElementById('profile-email').textContent = profile.email;

    // Bio
    const bioEl = document.getElementById('profile-bio');
    if (profile.bio && profile.bio.trim()) {
      bioEl.textContent = profile.bio;
      bioEl.className = 'profile-section__value';
    } else {
      bioEl.textContent = 'No bio added yet.';
      bioEl.className = 'profile-section__empty';
    }

    // Skills
    const skillsEl = document.getElementById('profile-skills');
    const skills = profile.skills || [];
    if (skills.length > 0) {
      skillsEl.innerHTML = skills.map(s =>
        `<span class="skill-tag">${escapeHTML(s)}</span>`
      ).join('');
    } else {
      skillsEl.innerHTML = '<span class="profile-section__empty">No skills added yet.</span>';
    }

    // Education
    const eduEl = document.getElementById('profile-education');
    if (profile.education && profile.education.trim()) {
      eduEl.textContent = profile.education;
      eduEl.className = 'profile-section__value';
    } else {
      eduEl.textContent = 'No education added yet.';
      eduEl.className = 'profile-section__empty';
    }

    // Experience
    const expEl = document.getElementById('profile-experience');
    if (profile.experience && profile.experience.trim()) {
      expEl.textContent = profile.experience;
      expEl.className = 'profile-section__value';
    } else {
      expEl.textContent = 'No experience added yet.';
      expEl.className = 'profile-section__empty';
    }

    // LinkedIn
    const linkedinEl = document.getElementById('profile-linkedin');
    if (profile.linkedin_url && profile.linkedin_url.trim()) {
      linkedinEl.innerHTML = `<a href="${escapeAttr(profile.linkedin_url)}" target="_blank" rel="noopener noreferrer" class="profile-section__link">${escapeHTML(profile.linkedin_url)}</a>`;
    } else {
      linkedinEl.innerHTML = '<span class="profile-section__empty">No LinkedIn URL added yet.</span>';
    }
  }

  function renderEditSkills() {
    const container = document.getElementById('edit-skills-tags');
    container.innerHTML = editSkills.map((s, i) =>
      `<span class="skill-tag skill-tag--editable">${escapeHTML(s)}<button type="button" class="skill-tag__remove" data-skill-index="${i}" aria-label="Remove ${escapeAttr(s)}">×</button></span>`
    ).join('');

    // Wire up remove buttons
    container.querySelectorAll('.skill-tag__remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.skillIndex, 10);
        editSkills.splice(idx, 1);
        renderEditSkills();
      });
    });
  }

  /* ---------------------------------------------------------
     Mode switching
  --------------------------------------------------------- */
  function enterEditMode() {
    if (!currentProfile) return;

    // Populate edit fields from current profile
    document.getElementById('edit-avatar').textContent = getInitials(currentProfile.name);
    document.getElementById('edit-name').textContent = currentProfile.name;
    document.getElementById('edit-email').textContent = currentProfile.email;

    document.getElementById('edit-bio').value = currentProfile.bio || '';
    document.getElementById('edit-education').value = currentProfile.education || '';
    document.getElementById('edit-experience').value = currentProfile.experience || '';
    document.getElementById('edit-linkedin').value = currentProfile.linkedin_url || '';

    editSkills = [...(currentProfile.skills || [])];
    renderEditSkills();

    // Toggle visibility
    viewEl.classList.add('hidden');
    editEl.classList.add('active');

    // Scroll to top of card
    editEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function exitEditMode() {
    editEl.classList.remove('active');
    viewEl.classList.remove('hidden');
    viewEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------------------------------------------------------
     Skills input handling
  --------------------------------------------------------- */
  function addSkill() {
    const input = document.getElementById('edit-skill-input');
    const value = input.value.trim();
    if (!value) return;

    if (value.length > 50) {
      showToast('Skill is too long (max 50 characters).', 'error');
      return;
    }
    if (editSkills.length >= 20) {
      showToast('You can add up to 20 skills.', 'error');
      return;
    }
    if (editSkills.some(s => s.toLowerCase() === value.toLowerCase())) {
      showToast('This skill has already been added.', 'error');
      return;
    }

    editSkills.push(value);
    renderEditSkills();
    input.value = '';
    input.focus();
  }

  /* ---------------------------------------------------------
     Save profile
  --------------------------------------------------------- */
  async function handleSave(e) {
    e.preventDefault();

    const bio = document.getElementById('edit-bio').value.trim() || null;
    const education = document.getElementById('edit-education').value.trim() || null;
    const experience = document.getElementById('edit-experience').value.trim() || null;
    const linkedin_url = document.getElementById('edit-linkedin').value.trim() || null;

    // Frontend validation
    if (bio && bio.length > 1000) {
      showToast('Bio must be 1000 characters or fewer.', 'error');
      return;
    }
    if (education && education.length > 500) {
      showToast('Education must be 500 characters or fewer.', 'error');
      return;
    }
    if (experience && experience.length > 500) {
      showToast('Experience must be 500 characters or fewer.', 'error');
      return;
    }
    if (linkedin_url && !/^https?:\/\/(www\.)?linkedin\.com\/.+$/i.test(linkedin_url)) {
      showToast('Please enter a valid LinkedIn URL.', 'error');
      return;
    }

    const saveBtn = document.getElementById('btn-save-profile');
    saveBtn.classList.add('is-loading');
    saveBtn.disabled = true;

    try {
      const updated = await saveProfileData({
        bio,
        skills: editSkills,
        education,
        experience,
        linkedin_url,
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
     Escape helpers (prevent XSS)
  --------------------------------------------------------- */
  function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ---------------------------------------------------------
     Initialization
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async () => {
    viewEl = document.getElementById('profile-view');
    editEl = document.getElementById('profile-edit');
    toastEl = document.getElementById('profile-toast');

    // Don't load profile data until route-guard has verified the session.
    // We wait a short tick so route-guard's DOMContentLoaded fires first.
    // If the body gets .route-verified, the user is authenticated & authorized.
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

    // Skills: add on click or Enter
    document.getElementById('btn-add-skill').addEventListener('click', addSkill);
    document.getElementById('edit-skill-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addSkill();
      }
    });
  });

})();
