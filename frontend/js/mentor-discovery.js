/* ==========================================================================
   VentureAI — mentor-discovery.js
   Handles the Founder-facing Mentor Discovery page: search, filter, sort,
   pagination, and mentor card rendering.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------------------------------------------------
     Constants — filter option values (mirrors backend schemas)
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

  const AVAILABILITY_OPTIONS = [
    'Available', 'Limited Availability', 'Currently Unavailable',
  ];

  const MAX_TAGS_SHOWN = 3;
  const DEFAULT_LIMIT = 4;

  /* ---------------------------------------------------------
     State
  --------------------------------------------------------- */
  let state = {
    search: '',
    industry: [],
    expertise: [],
    startup_stage: [],
    availability: [],
    sort: 'relevance',
    page: 1,
    limit: DEFAULT_LIMIT,
  };

  let isLoading = false;
  let lastResponse = null;

  /* ---------------------------------------------------------
     DOM references
  --------------------------------------------------------- */
  let searchInput, searchClear, sortSelect, mentorGrid, gridContainer;
  let paginationContainer, resultCount, clearFiltersBtn, toastEl;

  /* ---------------------------------------------------------
     Escape HTML (XSS prevention)
  --------------------------------------------------------- */
  function escapeHTML(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------------------------------------------------------
     URL State Management
  --------------------------------------------------------- */
  function readStateFromURL() {
    var params = new URLSearchParams(window.location.search);
    state.search = params.get('search') || '';
    state.industry = params.getAll('industry');
    state.expertise = params.getAll('expertise');
    state.startup_stage = params.getAll('startup_stage');
    state.availability = params.getAll('availability');
    state.sort = params.get('sort') || 'relevance';
    state.page = parseInt(params.get('page'), 10) || 1;
  }

  function writeStateToURL() {
    var params = new URLSearchParams();
    if (state.search) params.set('search', state.search);
    state.industry.forEach(function(v) { params.append('industry', v); });
    state.expertise.forEach(function(v) { params.append('expertise', v); });
    state.startup_stage.forEach(function(v) { params.append('startup_stage', v); });
    state.availability.forEach(function(v) { params.append('availability', v); });
    if (state.sort !== 'relevance') params.set('sort', state.sort);
    if (state.page > 1) params.set('page', state.page);

    var qs = params.toString();
    var url = window.location.pathname + (qs ? '?' + qs : '');
    window.history.replaceState(null, '', url);
  }

  /* ---------------------------------------------------------
     Build API Query String
  --------------------------------------------------------- */
  function buildApiURL() {
    var params = new URLSearchParams();
    if (state.search) params.set('search', state.search);
    state.industry.forEach(function(v) { params.append('industry', v); });
    state.expertise.forEach(function(v) { params.append('expertise', v); });
    state.startup_stage.forEach(function(v) { params.append('startup_stage', v); });
    state.availability.forEach(function(v) { params.append('availability', v); });
    params.set('sort', state.sort);
    params.set('page', state.page);
    params.set('limit', state.limit);
    return '/mentor/discover?' + params.toString();
  }

  /* ---------------------------------------------------------
     Fetch mentors from API
  --------------------------------------------------------- */
  async function fetchMentors() {
    if (isLoading) return;
    isLoading = true;
    showSkeletons();
    writeStateToURL();

    try {
      var data = await apiRequest(buildApiURL());
      lastResponse = data;
      renderMentorGrid(data);
      renderPagination(data);
      renderResultCount(data);
    } catch (err) {
      renderError(err.message || 'Unable to load mentors.');
    } finally {
      isLoading = false;
    }
  }

  /* ---------------------------------------------------------
     DOM Container Safeguard
  --------------------------------------------------------- */
  function ensureMentorGrid() {
    var el = document.getElementById('mentor-grid');
    if (!el || !gridContainer.contains(el)) {
      gridContainer.innerHTML = '<div class="discovery-grid" id="mentor-grid"></div>';
      mentorGrid = document.getElementById('mentor-grid');
    }
    return mentorGrid;
  }

  /* ---------------------------------------------------------
     Render: Skeleton Loading Cards
  --------------------------------------------------------- */
  function showSkeletons() {
    ensureMentorGrid();
    var html = '';
    for (var i = 0; i < 4; i++) {
      html += '<div class="mentor-card mentor-card--skeleton">' +
        '<div class="mentor-card__header">' +
          '<div class="skeleton-avatar"></div>' +
          '<div class="mentor-card__info" style="flex:1">' +
            '<div class="skeleton-line" style="height:14px;width:70%;margin-bottom:8px"></div>' +
            '<div class="skeleton-line" style="height:11px;width:50%"></div>' +
          '</div>' +
        '</div>' +
        '<div class="skeleton-line" style="height:12px;width:40%;margin-bottom:14px"></div>' +
        '<div style="display:flex;gap:6px;margin-bottom:10px">' +
          '<div class="skeleton-line" style="height:24px;width:60px;border-radius:999px"></div>' +
          '<div class="skeleton-line" style="height:24px;width:50px;border-radius:999px"></div>' +
          '<div class="skeleton-line" style="height:24px;width:70px;border-radius:999px"></div>' +
        '</div>' +
        '<div style="display:flex;gap:6px;margin-bottom:10px">' +
          '<div class="skeleton-line" style="height:24px;width:80px;border-radius:999px"></div>' +
          '<div class="skeleton-line" style="height:24px;width:65px;border-radius:999px"></div>' +
        '</div>' +
        '<div style="display:flex;justify-content:space-between;margin-top:auto;padding-top:16px;border-top:1px solid #F3F4F6">' +
          '<div class="skeleton-line" style="height:12px;width:70px"></div>' +
          '<div class="skeleton-line" style="height:30px;width:90px;border-radius:8px"></div>' +
        '</div>' +
      '</div>';
    }
    mentorGrid.innerHTML = html;
    mentorGrid.className = 'discovery-grid';
    paginationContainer.style.display = 'none';
  }

  /* ---------------------------------------------------------
     Render: Mentor Card Grid
  --------------------------------------------------------- */
  function renderMentorGrid(data) {
    var mentors = data.mentors || [];

    if (mentors.length === 0) {
      renderEmpty();
      return;
    }

    ensureMentorGrid();

    var html = '';
    mentors.forEach(function(mentor) {
      html += buildMentorCard(mentor);
    });

    mentorGrid.innerHTML = html;
    mentorGrid.className = 'discovery-grid';
  }

  function buildMentorCard(m) {
    var initials = getInitials(m.name);
    var avatarContent = m.profile_image
      ? '<img src="' + escapeHTML(m.profile_image) + '" alt="' + escapeHTML(m.name) + '">'
      : escapeHTML(initials);

    // Experience line
    var expText = '';
    if (m.years_of_experience != null) {
      expText = m.years_of_experience + '+ Years Experience';
    }

    // Industry tags (limited)
    var industryTags = renderLimitedTags(m.industries || [], 'mentor-card__tag--industry', MAX_TAGS_SHOWN);

    // Expertise tags (limited)
    var expertiseTags = renderLimitedTags(m.areas_of_expertise || [], '', MAX_TAGS_SHOWN);

    // Stage tags (limited)
    var stageTags = renderLimitedTags(m.startup_stages || [], 'mentor-card__tag--stage', MAX_TAGS_SHOWN);

    // Availability
    var availClass = getAvailabilityClass(m.availability);
    var availLabel = m.availability || 'Not set';

    return '<div class="mentor-card">' +
      '<div class="mentor-card__header">' +
        '<div class="mentor-card__avatar">' + avatarContent + '</div>' +
        '<div class="mentor-card__info">' +
          '<div class="mentor-card__name">' + escapeHTML(m.name) + '</div>' +
          '<div class="mentor-card__headline">' + escapeHTML(m.headline || m.current_role || 'Mentor') + '</div>' +
        '</div>' +
      '</div>' +
      (expText ? '<div class="mentor-card__experience"><svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2Z" stroke="currentColor" stroke-width="1.6"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" stroke="currentColor" stroke-width="1.6"/></svg>' + escapeHTML(expText) + '</div>' : '') +
      (industryTags ? '<div class="mentor-card__tags">' + industryTags + '</div>' : '') +
      (expertiseTags ? '<div class="mentor-card__tags">' + expertiseTags + '</div>' : '') +
      (stageTags ? '<div class="mentor-card__section-label">Supports</div><div class="mentor-card__tags">' + stageTags + '</div>' : '') +
      '<div class="mentor-card__footer">' +
        '<span class="mentor-card__availability ' + availClass + '">' +
          '<span class="mentor-card__availability-dot"></span>' +
          escapeHTML(availLabel) +
        '</span>' +
        '<a href="mentor-detail.html?id=' + m.id + '" class="mentor-card__view-btn">View Profile</a>' +
      '</div>' +
    '</div>';
  }

  function renderLimitedTags(items, extraClass, max) {
    if (!items || items.length === 0) return '';
    var html = '';
    var shown = items.slice(0, max);
    var remaining = items.length - max;
    shown.forEach(function(tag) {
      html += '<span class="mentor-card__tag ' + extraClass + '">' + escapeHTML(tag) + '</span>';
    });
    if (remaining > 0) {
      html += '<span class="mentor-card__tag mentor-card__tag--more">+' + remaining + ' more</span>';
    }
    return html;
  }

  function getAvailabilityClass(availability) {
    switch (availability) {
      case 'Available': return 'mentor-card__availability--available';
      case 'Limited Availability': return 'mentor-card__availability--limited';
      case 'Currently Unavailable': return 'mentor-card__availability--unavailable';
      default: return '';
    }
  }

  /* ---------------------------------------------------------
     Render: Empty State
  --------------------------------------------------------- */
  function renderEmpty() {
    var hasFilters = state.search || state.industry.length || state.expertise.length ||
                     state.startup_stage.length || state.availability.length;

    var html = '<div class="discovery-empty">' +
      '<div class="discovery-empty__icon">' +
        '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="8" stroke="#5B3FE4" stroke-width="2"/><path d="M21 21l-4.35-4.35" stroke="#5B3FE4" stroke-width="2" stroke-linecap="round"/></svg>' +
      '</div>' +
      '<h3>' + (hasFilters ? 'No mentors match your search' : 'No mentors available yet') + '</h3>' +
      '<p>' + (hasFilters
        ? 'Try adjusting your filters or search terms to find mentors.'
        : 'Mentors are being onboarded. Check back soon!') + '</p>' +
      (hasFilters ? '<button type="button" class="btn btn--outline" id="empty-clear-filters">Clear Filters</button>' : '') +
    '</div>';

    gridContainer.innerHTML = html;
    paginationContainer.style.display = 'none';

    var emptyBtn = document.getElementById('empty-clear-filters');
    if (emptyBtn) {
      emptyBtn.addEventListener('click', clearAllFilters);
    }
  }

  /* ---------------------------------------------------------
     Render: Error State
  --------------------------------------------------------- */
  function renderError(message) {
    var html = '<div class="discovery-error">' +
      '<div class="discovery-error__icon">' +
        '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 9v4M12 17h.01" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" stroke="#DC2626" stroke-width="2"/></svg>' +
      '</div>' +
      '<h3>Unable to load mentors</h3>' +
      '<p>Something went wrong. Please try again.</p>' +
      '<button type="button" class="btn btn--primary" id="error-retry-btn">Retry</button>' +
    '</div>';

    gridContainer.innerHTML = html;
    paginationContainer.style.display = 'none';

    document.getElementById('error-retry-btn').addEventListener('click', function() {
      ensureMentorGrid();
      fetchMentors();
    });
  }

  /* ---------------------------------------------------------
     Render: Result Count
  --------------------------------------------------------- */
  function renderResultCount(data) {
    if (!data || data.total === 0) {
      resultCount.textContent = '';
      return;
    }
    var start = (data.page - 1) * data.limit + 1;
    var end = Math.min(data.page * data.limit, data.total);
    resultCount.innerHTML = 'Showing <strong>' + start + '–' + end + '</strong> of <strong>' + data.total + '</strong> mentors';
  }

  /* ---------------------------------------------------------
     Render: Pagination
  --------------------------------------------------------- */
  function renderPagination(data) {
    if (!data || data.total_pages <= 1) {
      paginationContainer.style.display = 'none';
      return;
    }

    paginationContainer.style.display = 'flex';
    var html = '';

    // Previous button
    html += '<button class="discovery-pagination__btn" data-page="' + (data.page - 1) + '"' +
      (data.page <= 1 ? ' disabled' : '') + '>← Prev</button>';

    // Page numbers with ellipsis
    var pages = buildPageNumbers(data.page, data.total_pages);
    pages.forEach(function(p) {
      if (p === '...') {
        html += '<span class="discovery-pagination__ellipsis">…</span>';
      } else {
        html += '<button class="discovery-pagination__btn' + (p === data.page ? ' active' : '') +
          '" data-page="' + p + '">' + p + '</button>';
      }
    });

    // Next button
    html += '<button class="discovery-pagination__btn" data-page="' + (data.page + 1) + '"' +
      (data.page >= data.total_pages ? ' disabled' : '') + '>Next →</button>';

    paginationContainer.innerHTML = html;

    // Wire up clicks
    paginationContainer.querySelectorAll('[data-page]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        if (btn.disabled) return;
        state.page = parseInt(btn.dataset.page, 10);
        fetchMentors();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
  }

  function buildPageNumbers(current, total) {
    var pages = [];
    if (total <= 7) {
      for (var i = 1; i <= total; i++) pages.push(i);
      return pages;
    }
    pages.push(1);
    if (current > 3) pages.push('...');
    var start = Math.max(2, current - 1);
    var end = Math.min(total - 1, current + 1);
    for (var j = start; j <= end; j++) pages.push(j);
    if (current < total - 2) pages.push('...');
    pages.push(total);
    return pages;
  }

  /* ---------------------------------------------------------
     Filter Dropdowns
  --------------------------------------------------------- */
  function initFilterDropdowns() {
    populateFilterPanel('panel-filter-industry', INDUSTRIES, 'industry');
    populateFilterPanel('panel-filter-expertise', AREAS_OF_EXPERTISE, 'expertise');
    populateFilterPanel('panel-filter-stage', STARTUP_STAGES, 'startup_stage');
    populateFilterPanel('panel-filter-availability', AVAILABILITY_OPTIONS, 'availability');

    // Toggle dropdown open/close
    document.querySelectorAll('.filter-dropdown__btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var dropdown = btn.closest('.filter-dropdown');
        var isOpen = dropdown.classList.contains('open');
        closeAllDropdowns();
        if (!isOpen) dropdown.classList.add('open');
      });
    });

    // Close dropdowns on outside click
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.filter-dropdown')) {
        closeAllDropdowns();
      }
    });
  }

  function populateFilterPanel(panelId, options, filterKey) {
    var panel = document.getElementById(panelId);
    var html = '';
    options.forEach(function(option) {
      var checked = state[filterKey].includes(option) ? ' checked' : '';
      html += '<label class="filter-dropdown__option">' +
        '<input type="checkbox" value="' + escapeHTML(option) + '"' + checked +
        ' data-filter-key="' + filterKey + '">' +
        escapeHTML(option) +
      '</label>';
    });
    panel.innerHTML = html;

    // Wire up checkbox changes
    panel.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
      cb.addEventListener('change', function() {
        var key = cb.dataset.filterKey;
        var val = cb.value;
        if (cb.checked) {
          if (!state[key].includes(val)) state[key].push(val);
        } else {
          state[key] = state[key].filter(function(v) { return v !== val; });
        }
        state.page = 1;
        updateFilterButtonStates();
        fetchMentors();
      });
    });
  }

  function closeAllDropdowns() {
    document.querySelectorAll('.filter-dropdown.open').forEach(function(dd) {
      dd.classList.remove('open');
    });
  }

  function updateFilterButtonStates() {
    updateFilterBtn('btn-filter-industry', state.industry.length);
    updateFilterBtn('btn-filter-expertise', state.expertise.length);
    updateFilterBtn('btn-filter-stage', state.startup_stage.length);
    updateFilterBtn('btn-filter-availability', state.availability.length);

    var hasFilters = state.search || state.industry.length || state.expertise.length ||
                     state.startup_stage.length || state.availability.length;
    clearFiltersBtn.style.display = hasFilters ? '' : 'none';
  }

  function updateFilterBtn(btnId, count) {
    var btn = document.getElementById(btnId);
    var existingCount = btn.querySelector('.filter-count');
    if (existingCount) existingCount.remove();

    if (count > 0) {
      btn.classList.add('active');
      var badge = document.createElement('span');
      badge.className = 'filter-count';
      badge.textContent = count;
      btn.insertBefore(badge, btn.querySelector('.filter-dropdown__chevron'));
    } else {
      btn.classList.remove('active');
    }
  }

  /* ---------------------------------------------------------
     Clear All Filters
  --------------------------------------------------------- */
  function clearAllFilters() {
    state.search = '';
    state.industry = [];
    state.expertise = [];
    state.startup_stage = [];
    state.availability = [];
    state.sort = 'relevance';
    state.page = 1;

    searchInput.value = '';
    searchClear.classList.remove('visible');
    sortSelect.value = 'relevance';

    // Reset all checkboxes
    document.querySelectorAll('.filter-dropdown__panel input[type="checkbox"]').forEach(function(cb) {
      cb.checked = false;
    });

    updateFilterButtonStates();
    fetchMentors();
  }

  /* ---------------------------------------------------------
     Search
  --------------------------------------------------------- */
  var searchTimer = null;

  function initSearch() {
    searchInput.value = state.search;
    searchClear.classList.toggle('visible', !!state.search);

    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimer);
      var val = searchInput.value.trim();
      searchClear.classList.toggle('visible', !!val);
      searchTimer = setTimeout(function() {
        state.search = val;
        state.page = 1;
        updateFilterButtonStates();
        fetchMentors();
      }, 300);
    });

    searchClear.addEventListener('click', function() {
      searchInput.value = '';
      searchClear.classList.remove('visible');
      state.search = '';
      state.page = 1;
      updateFilterButtonStates();
      fetchMentors();
      searchInput.focus();
    });
  }

  /* ---------------------------------------------------------
     Sort
  --------------------------------------------------------- */
  function initSort() {
    sortSelect.value = state.sort;
    sortSelect.addEventListener('change', function() {
      state.sort = sortSelect.value;
      state.page = 1;
      fetchMentors();
    });
  }

  /* ---------------------------------------------------------
     Toast
  --------------------------------------------------------- */
  var toastTimer = null;
  function showToast(message, type) {
    if (toastTimer) clearTimeout(toastTimer);
    toastEl.textContent = message;
    toastEl.className = 'profile-toast profile-toast--' + type + ' show';
    toastTimer = setTimeout(function() {
      toastEl.classList.remove('show');
    }, 3500);
  }

  /* ---------------------------------------------------------
     Initialization
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async function() {
    // Resolve DOM references
    searchInput = document.getElementById('search-input');
    searchClear = document.getElementById('search-clear');
    sortSelect = document.getElementById('sort-select');
    mentorGrid = document.getElementById('mentor-grid');
    gridContainer = document.getElementById('mentor-grid-container');
    paginationContainer = document.getElementById('pagination-container');
    resultCount = document.getElementById('result-count');
    clearFiltersBtn = document.getElementById('btn-clear-filters');
    toastEl = document.getElementById('discovery-toast');

    // Wait for route guard
    await new Promise(function(resolve) {
      var attempts = 0;
      var check = function() {
        if (document.body.classList.contains('route-verified')) resolve();
        else if (attempts > 60) resolve();
        else { attempts++; setTimeout(check, 50); }
      };
      check();
    });

    // Read state from URL
    readStateFromURL();

    // Initialize UI components
    initFilterDropdowns();
    initSearch();
    initSort();
    updateFilterButtonStates();

    // Wire up clear filters button
    clearFiltersBtn.addEventListener('click', clearAllFilters);

    // Load mentors
    fetchMentors();
  });

})();
