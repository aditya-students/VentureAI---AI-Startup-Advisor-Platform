/* ==========================================================================
   VentureAI — startup-workspace.js
   Handles loading, creating, editing, archiving, and displaying the
   founder's startup workspace.
   Depends on auth.js being loaded first (uses apiRequest, getInitials).
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------------------------------------------------
     State
  --------------------------------------------------------- */
  let currentStartup = null;   // latest startup data from the API
  let validationHistory = [];  // validation runs for activity log & history UI
  let isEditMode = false;      // true when the modal is in edit mode

  /* ---------------------------------------------------------
     DOM references (resolved after DOMContentLoaded)
  --------------------------------------------------------- */
  let emptyEl, mainEl, toastEl;
  let modalBackdrop, archiveBackdrop;

  /* ---------------------------------------------------------
     Startup API
  --------------------------------------------------------- */
  async function fetchStartup() {
    return apiRequest('/startups/me');
  }

  async function createStartupAPI(data) {
    return apiRequest('/startups', { method: 'POST', body: data });
  }

  async function updateStartupAPI(data) {
    return apiRequest('/startups/me', { method: 'PUT', body: data });
  }

  async function updateStatusAPI(status) {
    return apiRequest('/startups/me/status', { method: 'PATCH', body: { status } });
  }

  async function fetchValidationHistory() {
    if (!currentStartup) return [];
    try {
      const history = await apiRequest(`/startups/${currentStartup.id}/idea-validation/history`);
      validationHistory = history || [];
      return validationHistory;
    } catch (err) {
      validationHistory = [];
      return [];
    }
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
     Date formatting
  --------------------------------------------------------- */
  function formatDate(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();

    const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

    if (isToday) return `Today, ${time}`;

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return `Yesterday, ${time}`;

    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) + `, ${time}`;
  }

  /* ---------------------------------------------------------
     Toast notification
  --------------------------------------------------------- */
  let toastTimer = null;

  function showToast(message, type) {
    if (toastTimer) clearTimeout(toastTimer);
    toastEl.textContent = message;
    toastEl.className = `workspace-toast workspace-toast--${type} show`;
    toastTimer = setTimeout(() => {
      toastEl.classList.remove('show');
    }, 3500);
  }

  /* ---------------------------------------------------------
     Render: Empty state
  --------------------------------------------------------- */
  function showEmptyState() {
    emptyEl.style.display = 'block';
    mainEl.style.display = 'none';
  }

  /* ---------------------------------------------------------
     Render: Workspace
  --------------------------------------------------------- */
  function renderWorkspace(startup) {
    currentStartup = startup;
    emptyEl.style.display = 'none';
    mainEl.style.display = 'block';

    // Overview card
    document.getElementById('overview-name').textContent = startup.name;

    const taglineEl = document.getElementById('overview-tagline');
    if (startup.tagline && startup.tagline.trim()) {
      taglineEl.textContent = startup.tagline;
      taglineEl.style.display = 'block';
    } else {
      taglineEl.style.display = 'none';
    }

    // Stage badge
    const stageEl = document.getElementById('overview-stage');
    stageEl.textContent = `Stage: ${startup.stage}`;

    // Status badge
    const statusEl = document.getElementById('overview-status');
    statusEl.textContent = startup.status;
    statusEl.className = startup.status === 'Active'
      ? 'badge-status badge-status--active'
      : 'badge-status badge-status--archived';

    // Archived banner + buttons
    const archivedBanner = document.getElementById('archived-banner');
    const archiveBtn = document.getElementById('btn-archive-startup');
    const editBtn = document.getElementById('btn-edit-startup');

    if (startup.status === 'Archived') {
      archivedBanner.style.display = 'flex';
      archiveBtn.style.display = 'none';
      editBtn.style.display = 'none';
    } else {
      archivedBanner.style.display = 'none';
      archiveBtn.style.display = '';
      editBtn.style.display = '';
    }

    // Startup information
    renderInfoField('info-problem', startup.problem);
    renderInfoField('info-solution', startup.solution);
    renderInfoField('info-industry', startup.industry, 'No industry specified.');
    renderInfoField('info-target-market', startup.target_market, 'No target market specified.');

    // Progress
    renderProgress(startup);

    // Activity
    renderActivity(startup);
  }

  function renderInfoField(id, value, emptyText) {
    const el = document.getElementById(id);
    if (value && value.trim()) {
      el.textContent = value;
      el.className = 'info-item__value';
    } else {
      el.textContent = emptyText || 'Not specified.';
      el.className = 'info-item__empty';
    }
  }

  /* ---------------------------------------------------------
     Render: Progress
  --------------------------------------------------------- */
  function renderProgress(startup) {
    const list = document.getElementById('progress-list');

    // Check if validation has been done (we'll update this after loading)
    const validationDone = !!window._latestValidation;

    const steps = [
      { label: 'Startup Created', done: true },
      { label: 'Idea Validation', done: validationDone },
      { label: 'Business Model Canvas', done: false },
      { label: 'Business Plan', done: false },
      { label: 'Pitch Deck', done: false },
      { label: 'Tasks', done: false },
    ];

    list.innerHTML = steps.map(step => `
      <div class="progress-item">
        <span class="progress-item__icon ${step.done ? 'progress-item__icon--done' : 'progress-item__icon--pending'}">
          ${step.done ? '✓' : '○'}
        </span>
        <span class="progress-item__label">${escapeHTML(step.label)}</span>
        <span class="progress-item__status ${step.done ? 'progress-item__status--done' : 'progress-item__status--pending'}">
          ${step.done ? 'Done' : 'Not Started'}
        </span>
      </div>
    `).join('');
  }

  /* ---------------------------------------------------------
     Render: Activity
  --------------------------------------------------------- */
  function renderActivity(startup) {
    const list = document.getElementById('activity-list');
    if (!list) return;

    const activities = [];

    // Validation runs
    if (validationHistory && validationHistory.length > 0) {
      validationHistory.forEach(v => {
        const score = Math.round(v.final_validation_score || 0);
        activities.push({
          text: `AI Idea Validation completed (v${v.version} · Score: ${score}/100)`,
          time: v.created_at,
        });
      });
    }

    // If updated_at differs from created_at by more than 2 seconds, show update
    const created = new Date(startup.created_at).getTime();
    const updated = new Date(startup.updated_at).getTime();

    if (Math.abs(updated - created) > 2000) {
      activities.push({
        text: 'Startup information updated',
        time: startup.updated_at,
      });
    }

    if (startup.status === 'Archived') {
      activities.push({
        text: 'Startup archived',
        time: startup.updated_at,
      });
    }

    activities.push({
      text: 'Startup created',
      time: startup.created_at,
    });

    // Sort descending by timestamp (newest activity first)
    activities.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

    if (activities.length === 0) {
      list.innerHTML = '<p class="activity-empty">No activity yet.</p>';
      return;
    }

    list.innerHTML = activities.map(a => `
      <div class="activity-item">
        <span class="activity-item__dot"></span>
        <div class="activity-item__content">
          <div class="activity-item__text">${escapeHTML(a.text)}</div>
          <div class="activity-item__time">${formatDate(a.time)}</div>
        </div>
      </div>
    `).join('');
  }

  /* ---------------------------------------------------------
     Modal management
  --------------------------------------------------------- */
  function openModal(editMode) {
    isEditMode = editMode;
    const title = document.getElementById('modal-title');
    const submitBtn = document.getElementById('form-submit');
    const form = document.getElementById('startup-form');

    if (editMode && currentStartup) {
      title.textContent = 'Edit Startup';
      submitBtn.querySelector('.btn-text').textContent = 'Save Changes';
      // Populate form with current values
      form.name.value = currentStartup.name || '';
      document.getElementById('form-tagline').value = currentStartup.tagline || '';
      document.getElementById('form-problem').value = currentStartup.problem || '';
      document.getElementById('form-solution').value = currentStartup.solution || '';
      document.getElementById('form-industry').value = currentStartup.industry || '';
      document.getElementById('form-target-market').value = currentStartup.target_market || '';
      document.getElementById('form-stage').value = currentStartup.stage || 'Idea';
    } else {
      title.textContent = 'Create Your Startup';
      submitBtn.querySelector('.btn-text').textContent = 'Create Startup';
      form.reset();
    }

    modalBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modalBackdrop.classList.remove('open');
    document.body.style.overflow = '';
  }

  function openArchiveDialog() {
    archiveBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeArchiveDialog() {
    archiveBackdrop.classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ---------------------------------------------------------
     Form submission (create / edit)
  --------------------------------------------------------- */
  async function handleFormSubmit(e) {
    e.preventDefault();

    const form = document.getElementById('startup-form');
    const submitBtn = document.getElementById('form-submit');

    const name = form.name.value.trim();
    const tagline = document.getElementById('form-tagline').value.trim() || null;
    const problem = document.getElementById('form-problem').value.trim();
    const solution = document.getElementById('form-solution').value.trim();
    const industry = document.getElementById('form-industry').value.trim() || null;
    const target_market = document.getElementById('form-target-market').value.trim() || null;
    const stage = document.getElementById('form-stage').value;

    // Frontend validation
    if (!name) {
      showToast('Startup name is required.', 'error');
      return;
    }
    if (!problem) {
      showToast('Problem is required.', 'error');
      return;
    }
    if (!solution) {
      showToast('Solution is required.', 'error');
      return;
    }

    submitBtn.classList.add('is-loading');
    submitBtn.disabled = true;

    try {
      const data = { name, tagline, problem, solution, industry, target_market, stage };
      let startup;

      if (isEditMode) {
        startup = await updateStartupAPI(data);
        showToast('Startup updated successfully!', 'success');
      } else {
        startup = await createStartupAPI(data);
        showToast('Startup created successfully!', 'success');
      }

      closeModal();
      renderWorkspace(startup);
    } catch (err) {
      showToast(err.message || 'Something went wrong.', 'error');
    } finally {
      submitBtn.classList.remove('is-loading');
      submitBtn.disabled = false;
    }
  }

  /* ---------------------------------------------------------
     Archive / Restore
  --------------------------------------------------------- */
  async function handleArchive() {
    const btn = document.getElementById('archive-confirm');
    btn.classList.add('is-loading');
    btn.disabled = true;

    try {
      const startup = await updateStatusAPI('Archived');
      closeArchiveDialog();
      renderWorkspace(startup);
      showToast('Startup archived.', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to archive startup.', 'error');
    } finally {
      btn.classList.remove('is-loading');
      btn.disabled = false;
    }
  }

  async function handleRestore() {
    const btn = document.getElementById('btn-restore-startup');
    btn.classList.add('is-loading');
    btn.disabled = true;

    try {
      const startup = await updateStatusAPI('Active');
      renderWorkspace(startup);
      showToast('Startup restored!', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to restore startup.', 'error');
    } finally {
      btn.classList.remove('is-loading');
      btn.disabled = false;
    }
  }

  /* ---------------------------------------------------------
     Close modals on backdrop click
  --------------------------------------------------------- */
  function onBackdropClick(backdrop, e) {
    if (e.target === backdrop) {
      backdrop.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  /* =========================================================
     IDEA VALIDATION
  ========================================================= */

  const VALIDATION_STAGES = [
    { key: 'lofa', label: 'Extracting riskiest assumption' },
    { key: 'redteam', label: 'Running Red-Team analysis' },
    { key: 'vc', label: 'VC perspective', indent: true },
    { key: 'buyer', label: 'Buyer perspective', indent: true },
    { key: 'competitor', label: 'Competitor perspective', indent: true },
    { key: 'synthesis', label: 'Synthesizing results' },
    { key: 'scoring', label: 'Calculating validation score' },
    { key: 'blueprint', label: 'Generating validation blueprint' },
  ];

  function showValidationLoading() {
    const section = document.getElementById('validation-section');
    const loading = document.getElementById('validation-loading');
    const report = document.getElementById('validation-report');

    section.style.display = 'block';
    loading.style.display = 'block';
    report.style.display = 'none';

    const stages = document.getElementById('validation-stages');
    stages.innerHTML = VALIDATION_STAGES.map((s, i) => `
      <div class="validation-stage validation-stage--pending" id="stage-${s.key}" style="${s.indent ? 'padding-left:34px;' : ''}">
        <span class="validation-stage__icon">${i === 0 ? '●' : '○'}</span>
        <span>${escapeHTML(s.label)}</span>
      </div>
    `).join('');

    // Animate stages
    animateStages();

    // Scroll to loading
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function animateStages() {
    const stageKeys = VALIDATION_STAGES.map(s => s.key);
    let current = 0;

    function advance() {
      if (current >= stageKeys.length) return;

      // Mark current as active
      const el = document.getElementById(`stage-${stageKeys[current]}`);
      if (el) {
        el.className = 'validation-stage validation-stage--active';
        el.querySelector('.validation-stage__icon').textContent = '●';
      }

      // Mark previous as done
      if (current > 0) {
        const prev = document.getElementById(`stage-${stageKeys[current - 1]}`);
        if (prev) {
          prev.className = prev.className.replace('validation-stage--active', 'validation-stage--done');
          prev.querySelector('.validation-stage__icon').textContent = '✓';
        }
      }

      current++;

      // Stagger times: LOFA fast, redteam slower (parallel), synthesis medium
      const delays = { lofa: 2000, redteam: 1500, vc: 3000, buyer: 3000, competitor: 3000, synthesis: 2500, scoring: 1000, blueprint: 1500 };
      const key = stageKeys[current - 1];
      const delay = delays[key] || 2000;

      if (current < stageKeys.length) {
        window._stageTimer = setTimeout(advance, delay);
      } else {
        // Mark last as done after delay
        window._stageTimer = setTimeout(() => {
          const last = document.getElementById(`stage-${stageKeys[stageKeys.length - 1]}`);
          if (last) {
            last.className = last.className.replace('validation-stage--active', 'validation-stage--done');
            last.querySelector('.validation-stage__icon').textContent = '✓';
          }
        }, delay);
      }
    }

    advance();
  }

  function hideValidationLoading(success = true) {
    if (window._stageTimer) {
      clearTimeout(window._stageTimer);
      window._stageTimer = null;
    }

    if (success) {
      // Mark all stages as done
      VALIDATION_STAGES.forEach(s => {
        const el = document.getElementById(`stage-${s.key}`);
        if (el) {
          el.className = 'validation-stage validation-stage--done';
          el.querySelector('.validation-stage__icon').textContent = '✓';
        }
      });
      setTimeout(() => {
        document.getElementById('validation-loading').style.display = 'none';
      }, 400);
    } else {
      document.getElementById('validation-loading').style.display = 'none';
    }
  }

  /* ----- Run validation ----- */
  async function runIdeaValidation() {
    if (!currentStartup) return;

    showValidationLoading();

    try {
      const report = await apiRequest(`/startups/${currentStartup.id}/idea-validation`, {
        method: 'POST',
      });

      hideValidationLoading(true);

      setTimeout(() => {
        window._latestValidation = report;

        if (report && report.version) {
          const idx = validationHistory.findIndex(v => v.version === report.version);
          const historyItem = {
            validation_id: report.validation_id,
            version: report.version,
            final_validation_score: report.scores ? report.scores.final_validation_score : 0,
            created_at: report.created_at,
          };
          if (idx >= 0) {
            validationHistory[idx] = historyItem;
          } else {
            validationHistory.unshift(historyItem);
          }
        }

        renderValidationReport(report);
        renderProgress(currentStartup);
        renderActivity(currentStartup);
        showToast('Idea validation completed!', 'success');
      }, 500);

    } catch (err) {
      hideValidationLoading(false);
      showToast(err.message || 'Validation failed. Please try again.', 'error');
    }
  }

  /* ----- Load latest validation ----- */
  async function loadLatestValidation() {
    if (!currentStartup) return;

    try {
      const report = await apiRequest(`/startups/${currentStartup.id}/idea-validation/latest`);
      window._latestValidation = report;
      renderValidationReport(report);
      renderProgress(currentStartup);
    } catch (err) {
      // 404 = no validation yet, silently ignore
      if (!err.message || !err.message.includes('No validation report found')) {
        console.error('Failed to load validation:', err);
      }
    }
  }

  /* ----- Load history ----- */
  async function loadValidationHistory() {
    if (!currentStartup) return;

    try {
      const history = await fetchValidationHistory();
      renderVersionHistory(history);
      renderActivity(currentStartup);
    } catch (err) {
      showToast('Failed to load version history.', 'error');
    }
  }

  /* ----- Load specific version ----- */
  async function loadValidationById(validationId) {
    if (!currentStartup) return;

    try {
      const report = await apiRequest(`/startups/${currentStartup.id}/idea-validation/${validationId}`);
      window._latestValidation = report;
      renderValidationReport(report);
    } catch (err) {
      showToast('Failed to load validation report.', 'error');
    }
  }

  /* ----- Get score status text ----- */
  function getScoreStatus(score) {
    if (score >= 80) return 'Strong Foundation — validate assumptions and scale.';
    if (score >= 60) return 'Promising — but customer validation is required.';
    if (score >= 40) return 'Significant Concerns — pivot or validate core assumptions before investing further.';
    if (score >= 20) return 'High Risk — fundamental assumptions need validation.';
    return 'Critical Risk — reconsider the core business model.';
  }

  /* ----- Get bar color class ----- */
  function getBarClass(score) {
    if (score <= 20) return 'dimension-row__bar--low';
    if (score <= 50) return 'dimension-row__bar--mid';
    if (score <= 75) return 'dimension-row__bar--high';
    return 'dimension-row__bar--excellent';
  }

  /* ----- Render full report ----- */
  function renderValidationReport(report) {
    const section = document.getElementById('validation-section');
    const reportEl = document.getElementById('validation-report');

    section.style.display = 'block';
    reportEl.style.display = 'block';

    const score = Math.round(report.scores.final_validation_score);
    const circumference = 2 * Math.PI * 56;
    const offset = circumference - (score / 100) * circumference;

    // Delta badge
    let deltaBadge = '';
    if (report.delta) {
      const change = report.delta.score_change;
      if (change > 0) deltaBadge = `<span class="score-delta score-delta--up">▲ +${change}</span>`;
      else if (change < 0) deltaBadge = `<span class="score-delta score-delta--down">▼ ${change}</span>`;
      else deltaBadge = `<span class="score-delta score-delta--neutral">— 0</span>`;
    }

    // Score hero
    document.getElementById('score-hero').innerHTML = `
      <div class="score-hero">
        <div class="score-hero__inner">
          <div class="score-hero__gauge">
            <svg width="140" height="140" viewBox="0 0 140 140">
              <circle class="score-hero__gauge-bg" cx="70" cy="70" r="56"></circle>
              <circle class="score-hero__gauge-fill" cx="70" cy="70" r="56"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${offset}"></circle>
            </svg>
            <div class="score-hero__gauge-text">
              <span class="score-hero__number">${score}</span>
              <span class="score-hero__label">/ 100</span>
            </div>
          </div>
          <div class="score-hero__details">
            <div class="score-hero__status-label">Validation Status</div>
            <div class="score-hero__status">${escapeHTML(getScoreStatus(score))} ${deltaBadge}</div>
            <div class="score-hero__version">Version ${report.version} · ${formatDate(report.created_at)}</div>
          </div>
        </div>
      </div>
    `;

    // Veto warnings
    const vetoEl = document.getElementById('veto-warnings');
    if (report.triggered_vetoes && report.triggered_vetoes.length > 0) {
      vetoEl.innerHTML = `
        <div class="veto-warnings">
          ${report.triggered_vetoes.map(v => `
            <div class="veto-card">
              <span class="veto-card__icon">⚠️</span>
              <div class="veto-card__content">
                <div class="veto-card__title">${escapeHTML(v.label)}</div>
                <div class="veto-card__desc">Penalty applied: ×${v.penalty} multiplier</div>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } else {
      vetoEl.innerHTML = '';
    }

    // Dimension scores
    const dims = [
      { key: 'problem_score', label: 'Problem Severity', weight: '30%' },
      { key: 'buyer_score', label: 'Buyer Viability', weight: '25%' },
      { key: 'market_score', label: 'Market Potential', weight: '20%' },
      { key: 'moat_score', label: 'Defensibility & Moat', weight: '15%' },
      { key: 'feasibility_score', label: 'Technical Feasibility', weight: '10%' },
    ];
    const tierMap = {
      problem_score: 'problem',
      buyer_score: 'buyer',
      market_score: 'market',
      moat_score: 'moat',
      feasibility_score: 'feasibility',
    };

    const dimDeltas = {};
    if (report.delta && report.delta.dimension_deltas) {
      report.delta.dimension_deltas.forEach(d => {
        dimDeltas[d.dimension] = d.change;
      });
    }
    const dimDeltaKeyMap = {
      'Problem Severity': 'problem_score',
      'Buyer Viability': 'buyer_score',
      'Market Potential': 'market_score',
      'Defensibility & Moat': 'moat_score',
      'Technical Feasibility': 'feasibility_score',
    };

    document.getElementById('dimension-scores').innerHTML = dims.map(d => {
      const s = report.scores[d.key];
      const tier = report.score_tiers[tierMap[d.key]] || '';
      const barClass = getBarClass(s);

      let deltaHtml = '';
      const deltaDim = Object.keys(dimDeltas).find(k => dimDeltaKeyMap[k] === d.key);
      if (deltaDim !== undefined && dimDeltas[deltaDim] !== undefined) {
        const ch = dimDeltas[deltaDim];
        if (ch > 0) deltaHtml = `<span class="dimension-row__delta dimension-row__delta--up">+${ch}</span>`;
        else if (ch < 0) deltaHtml = `<span class="dimension-row__delta dimension-row__delta--down">${ch}</span>`;
      }

      return `
        <div>
          <div class="dimension-row">
            <span class="dimension-row__label">${escapeHTML(d.label)} <small style="color:var(--muted);font-weight:400;">(${d.weight})</small></span>
            <div class="dimension-row__bar-wrap">
              <div class="dimension-row__bar ${barClass}" style="width:${s}%;"></div>
            </div>
            <span class="dimension-row__score">${s} ${deltaHtml}</span>
          </div>
          <div class="dimension-row__tier">${escapeHTML(tier)}</div>
        </div>
      `;
    }).join('');

    // LOFA
    document.getElementById('lofa-card').innerHTML = `
      <div class="lofa-card">
        <div class="lofa-card__label">
          🎯 Leap-of-Faith Assumption (LOFA)
        </div>
        <div class="lofa-card__text">"${escapeHTML(report.lofa)}"</div>
      </div>
    `;

    // Overall assessment
    document.getElementById('assessment-card').innerHTML = `
      <div class="assessment-card">
        <div class="assessment-card__title">
          <span aria-hidden="true">📝</span> Overall Assessment
        </div>
        <div class="assessment-card__text">${escapeHTML(report.overall_assessment)}</div>
      </div>
    `;

    // Red Team Analysis
    const agents = [
      {
        title: 'Skeptical VC Partner',
        icon: '💼',
        iconClass: 'redteam-card__icon--vc',
        data: report.agent_analysis.vc,
        fields: [
          { key: 'tam_assessment', label: 'TAM Assessment' },
          { key: 'platform_risk', label: 'Platform Risk' },
          { key: 'venture_verdict', label: 'Venture Verdict' },
          { key: 'market_assessment', label: 'Market Assessment' },
          { key: 'feasibility_assessment', label: 'Feasibility Assessment' },
        ],
      },
      {
        title: 'Cynical Buyer / ICP',
        icon: '🛒',
        iconClass: 'redteam-card__icon--buyer',
        data: report.agent_analysis.buyer,
        fields: [
          { key: 'buying_objection', label: 'Buying Objection' },
          { key: 'status_quo_trap', label: 'Status-Quo Trap' },
          { key: 'buyer_verdict', label: 'Buyer Verdict' },
          { key: 'problem_assessment', label: 'Problem Assessment' },
          { key: 'buyer_assessment', label: 'Buyer Assessment' },
        ],
      },
      {
        title: 'Competitor & Moat Strategist',
        icon: '🛡️',
        iconClass: 'redteam-card__icon--competitor',
        data: report.agent_analysis.competitor,
        fields: [
          { key: 'primary_incumbent_threat', label: 'Primary Incumbent Threat' },
          { key: 'moat_vulnerability', label: 'Moat Vulnerability' },
          { key: 'competitor_verdict', label: 'Competitor Verdict' },
          { key: 'defensibility_assessment', label: 'Defensibility Assessment' },
        ],
      },
    ];

    document.getElementById('redteam-grid').innerHTML = agents.map(agent => {
      // The critique might be nested inside a "critique" key
      const critique = agent.data.critique || agent.data;
      return `
        <div class="redteam-card">
          <div class="redteam-card__header">
            <div class="redteam-card__icon ${agent.iconClass}">${agent.icon}</div>
            <div class="redteam-card__title">${escapeHTML(agent.title)}</div>
          </div>
          <div class="redteam-card__body">
            ${agent.fields.map(f => {
              const val = critique[f.key] || '';
              if (!val) return '';
              return `
                <div>
                  <div class="redteam-field__label">${escapeHTML(f.label)}</div>
                  <div class="redteam-field__value">${escapeHTML(val)}</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');

    // Strengths & Risks
    document.getElementById('sr-grid').innerHTML = `
      <div class="sr-card">
        <div class="sr-card__title">
          <span aria-hidden="true">💪</span> Strengths
        </div>
        <div class="sr-list">
          ${(report.strengths || []).map(s => `
            <div class="sr-list__item">
              <span class="sr-list__bullet sr-list__bullet--green"></span>
              <span>${escapeHTML(s)}</span>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="sr-card">
        <div class="sr-card__title">
          <span aria-hidden="true">⚠️</span> Key Risks
        </div>
        <div class="sr-list">
          ${(report.key_risks || []).map(r => `
            <div class="sr-list__item">
              <span class="sr-list__bullet sr-list__bullet--red"></span>
              <span>${escapeHTML(r)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    // Falsification blueprint
    const bp = report.falsification_blueprint || {};
    document.getElementById('blueprint-card').innerHTML = `
      <div class="blueprint-card">
        <div class="blueprint-card__title">
          <span aria-hidden="true">🔬</span> Falsification Blueprint
        </div>
        <div class="blueprint-section">
          <div class="blueprint-section__label">Mom Test Interview Questions</div>
          <div class="mom-test-list">
            ${(bp.mom_test_questions || []).map((q, i) => `
              <div class="mom-test-item">
                <span class="mom-test-item__num">${i + 1}</span>
                <span class="mom-test-item__text">"${escapeHTML(q)}"</span>
              </div>
            `).join('')}
          </div>
        </div>
        <div class="blueprint-section">
          <div class="blueprint-section__label">Kill Threshold</div>
          <div class="kill-threshold">${escapeHTML(bp.kill_threshold || '')}</div>
        </div>
      </div>
    `;

    // Next steps
    document.getElementById('val-nextsteps').innerHTML = `
      <div class="val-nextsteps">
        <div class="val-nextsteps__title">
          <span aria-hidden="true">🚀</span> Recommended Next Steps
        </div>
        <div class="val-nextsteps__list">
          ${(report.recommended_next_steps || []).map((s, i) => `
            <div class="val-nextstep">
              <span class="val-nextstep__num">${i + 1}</span>
              <span class="val-nextstep__text">${escapeHTML(s)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    // Scroll to report
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ----- Render version history ----- */
  function renderVersionHistory(history) {
    const container = document.getElementById('version-history');
    if (!history || history.length === 0) {
      container.style.display = 'none';
      return;
    }

    const currentVersion = window._latestValidation ? window._latestValidation.version : 0;

    container.style.display = 'block';
    container.innerHTML = `
      <div class="version-history">
        <div class="version-history__title">
          <span aria-hidden="true">📋</span> Version History
        </div>
        <div class="version-list">
          ${history.map(v => `
            <div class="version-item ${v.version === currentVersion ? 'version-item--active' : ''}"
                 data-validation-id="${v.validation_id}">
              <span class="version-item__version">Version ${v.version}</span>
              <span class="version-item__score">${Math.round(v.final_validation_score)} / 100</span>
              <span class="version-item__date">${formatDate(v.created_at)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    // Wire version clicks
    container.querySelectorAll('.version-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = parseInt(item.dataset.validationId, 10);
        loadValidationById(id);
      });
    });
  }

  /* ---------------------------------------------------------
     Initialization
  --------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', async () => {
    emptyEl = document.getElementById('workspace-empty');
    mainEl = document.getElementById('workspace-main');
    toastEl = document.getElementById('workspace-toast');
    modalBackdrop = document.getElementById('modal-startup');
    archiveBackdrop = document.getElementById('modal-archive');

    // Wait for route-guard to verify session (same pattern as founder-profile.js)
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

    // Load startup
    try {
      const startup = await fetchStartup();
      currentStartup = startup;

      // Fetch existing validation history before rendering
      await fetchValidationHistory();

      renderWorkspace(startup);

      // Load latest validation (if any)
      await loadLatestValidation();
    } catch (err) {
      // 404 means no startup yet — show empty state
      if (err.message && (err.message.includes('haven\'t created') || err.message.includes('404'))) {
        showEmptyState();
      } else {
        showEmptyState();
        showToast(err.message || 'Failed to load startup.', 'error');
      }
    }

    // Wire up buttons
    document.getElementById('btn-create-startup').addEventListener('click', () => openModal(false));
    document.getElementById('btn-edit-startup').addEventListener('click', () => openModal(true));
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('form-cancel').addEventListener('click', closeModal);
    document.getElementById('startup-form').addEventListener('submit', handleFormSubmit);

    // Archive
    document.getElementById('btn-archive-startup').addEventListener('click', openArchiveDialog);
    document.getElementById('archive-cancel').addEventListener('click', closeArchiveDialog);
    document.getElementById('archive-confirm').addEventListener('click', handleArchive);

    // Restore
    document.getElementById('btn-restore-startup').addEventListener('click', handleRestore);

    // Close modals on backdrop click
    modalBackdrop.addEventListener('click', (e) => onBackdropClick(modalBackdrop, e));
    archiveBackdrop.addEventListener('click', (e) => onBackdropClick(archiveBackdrop, e));

    // Close modals on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (modalBackdrop.classList.contains('open')) closeModal();
        if (archiveBackdrop.classList.contains('open')) closeArchiveDialog();
      }
    });

    // ----- Idea Validation buttons -----
    document.getElementById('tool-idea-validation').addEventListener('click', runIdeaValidation);
    document.getElementById('btn-validate-nextstep').addEventListener('click', runIdeaValidation);
    document.getElementById('btn-reanalyze').addEventListener('click', runIdeaValidation);
    document.getElementById('btn-show-history').addEventListener('click', loadValidationHistory);
  });

})();

