/**
 * VentureAI — Standalone AI Idea Validation Application
 */

const IdeaValidationApp = {
  startupId: null,
  currentStartup: null,
  currentReport: null,
  history: [],
  stageTimer: null,

  VALIDATION_STAGES: [
    { key: 'lofa', label: 'Extracting riskiest assumption' },
    { key: 'redteam', label: 'Running Red-Team analysis' },
    { key: 'vc', label: 'VC perspective', indent: true },
    { key: 'buyer', label: 'Buyer perspective', indent: true },
    { key: 'competitor', label: 'Competitor perspective', indent: true },
    { key: 'synthesis', label: 'Synthesizing results' },
    { key: 'scoring', label: 'Calculating validation score' },
    { key: 'blueprint', label: 'Generating validation blueprint' },
  ],

  init: async function (startupId) {
    this.startupId = startupId;

    try {
      this.currentStartup = await apiRequest('/startups/me');
      if (!this.startupId && this.currentStartup) {
        this.startupId = this.currentStartup.id;
      }
      const pill = document.getElementById('val-startup-name-pill');
      if (pill && this.currentStartup) pill.textContent = this.currentStartup.name;

      await this.loadLatestValidation();
      await this.loadHistory();
    } catch (err) {
      console.warn("Could not load startup profile details:", err);
      await this.loadLatestValidation();
      await this.loadHistory();
    }
  },

  showToast: function (msg, type = 'info') {
    const old = document.querySelector('.vp-toast');
    if (old) old.remove();

    const toast = document.createElement('div');
    toast.className = 'vp-toast';
    toast.innerHTML = `<span>${type === 'error' ? '⚠️' : '✨'}</span> <span>${msg}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.5s ease';
      setTimeout(() => toast.remove(), 500);
    }, 3500);
  },

  showLoading: function () {
    const loading = document.getElementById('validation-loading');
    const empty = document.getElementById('validation-empty-state');
    const main = document.getElementById('validation-main-state');

    if (loading) loading.style.display = 'block';
    if (empty) empty.style.display = 'none';
    if (main) main.style.display = 'none';

    const stages = document.getElementById('validation-stages');
    if (stages) {
      stages.innerHTML = this.VALIDATION_STAGES.map((s, i) => `
        <div class="validation-stage validation-stage--pending" id="val-stage-${s.key}" style="${s.indent ? 'padding-left:34px;' : ''}">
          <span class="validation-stage__icon">${i === 0 ? '●' : '○'}</span>
          <span>${s.label}</span>
        </div>
      `).join('');
    }

    this.animateStages();
  },

  animateStages: function () {
    const stageKeys = this.VALIDATION_STAGES.map(s => s.key);
    let current = 0;

    const advance = () => {
      if (current >= stageKeys.length) return;

      const el = document.getElementById(`val-stage-${stageKeys[current]}`);
      if (el) {
        el.className = 'validation-stage validation-stage--active';
        el.querySelector('.validation-stage__icon').textContent = '●';
      }

      if (current > 0) {
        const prev = document.getElementById(`val-stage-${stageKeys[current - 1]}`);
        if (prev) {
          prev.className = prev.className.replace('validation-stage--active', 'validation-stage--done');
          prev.querySelector('.validation-stage__icon').textContent = '✓';
        }
      }

      current++;
      const delays = { lofa: 1500, redteam: 1200, vc: 2000, buyer: 2000, competitor: 2000, synthesis: 1500, scoring: 800, blueprint: 1000 };
      const delay = delays[stageKeys[current - 1]] || 1500;

      if (current < stageKeys.length) {
        this.stageTimer = setTimeout(advance, delay);
      }
    };

    advance();
  },

  hideLoading: function () {
    if (this.stageTimer) clearTimeout(this.stageTimer);
    const loading = document.getElementById('validation-loading');
    if (loading) loading.style.display = 'none';
  },

  loadLatestValidation: async function () {
    try {
      const report = await apiRequest(`/startups/${this.startupId}/idea-validation/latest`);
      this.currentReport = report;
      this.renderReport(report);
    } catch (err) {
      console.warn("No latest validation report via /latest endpoint:", err);
      try {
        const history = await apiRequest(`/startups/${this.startupId}/idea-validation/history`);
        if (history && history.length > 0) {
          const latestId = history[0].validation_id;
          const report = await apiRequest(`/startups/${this.startupId}/idea-validation/${latestId}`);
          this.currentReport = report;
          this.renderReport(report);
          return;
        }
      } catch (hErr) {
        console.warn("No validation history found:", hErr);
      }

      const empty = document.getElementById('validation-empty-state');
      const main = document.getElementById('validation-main-state');
      if (empty) empty.style.display = 'block';
      if (main) main.style.display = 'none';
    }
  },

  loadHistory: async function () {
    try {
      this.history = await apiRequest(`/startups/${this.startupId}/idea-validation/history`);
      this.renderVersionDropdown();
      this.renderHistoryList();
    } catch (err) {
      console.error("Failed to load validation history:", err);
    }
  },

  loadValidationById: async function (id) {
    this.showLoading();
    try {
      const report = await apiRequest(`/startups/${this.startupId}/idea-validation/${id}`);
      this.currentReport = report;
      this.hideLoading();
      this.renderReport(report);
      this.renderVersionDropdown();
      this.renderHistoryList();
    } catch (err) {
      this.hideLoading();
      this.showToast("Failed to load selected validation version.", "error");
    }
  },

  runValidation: async function () {
    this.showLoading();

    try {
      const report = await apiRequest(`/startups/${this.startupId}/idea-validation`, {
        method: 'POST',
      });

      this.hideLoading();
      this.currentReport = report;
      this.renderReport(report);
      await this.loadHistory();
      this.showToast("Idea Validation analysis completed!", "success");
    } catch (err) {
      this.hideLoading();
      this.showToast(err.message || "Idea Validation failed.", "error");
      if (this.currentReport) {
        this.renderReport(this.currentReport);
      } else {
        document.getElementById('validation-empty-state').style.display = 'block';
      }
    }
  },

  getScoreStatus: function (score) {
    if (score >= 80) return 'Strong Foundation — validate assumptions and scale.';
    if (score >= 60) return 'Promising — but customer validation is required.';
    if (score >= 40) return 'Significant Concerns — pivot or validate core assumptions before investing further.';
    if (score >= 20) return 'High Risk — fundamental assumptions need validation.';
    return 'Critical Risk — reconsider the core business model.';
  },

  getBarClass: function (score) {
    if (score <= 20) return 'dimension-row__bar--low';
    if (score <= 50) return 'dimension-row__bar--mid';
    if (score <= 75) return 'dimension-row__bar--high';
    return 'dimension-row__bar--excellent';
  },

  formatDate: function (dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  },

  renderReport: function (report) {
    const empty = document.getElementById('validation-empty-state');
    const main = document.getElementById('validation-main-state');

    if (empty) empty.style.display = 'none';
    if (main) main.style.display = 'block';

    if (!report) return;

    try {
      const scores = report.scores || {};
      const score = Math.round(scores.final_validation_score || 0);
      const circumference = 2 * Math.PI * 56;
      const offset = circumference - (score / 100) * circumference;

      let deltaBadge = '';
      if (report.delta) {
        const change = report.delta.score_change;
        if (change > 0) deltaBadge = `<span class="score-delta score-delta--up">▲ +${change}</span>`;
        else if (change < 0) deltaBadge = `<span class="score-delta score-delta--down">▼ ${change}</span>`;
        else deltaBadge = `<span class="score-delta score-delta--neutral">— 0</span>`;
      }

      // Score hero
      const scoreHeroEl = document.getElementById('score-hero');
      if (scoreHeroEl) {
        scoreHeroEl.innerHTML = `
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
                <div class="score-hero__status-label">Overall Validation Score</div>
                <div class="score-hero__status">${this.getScoreStatus(score)} ${deltaBadge}</div>
                <div class="score-hero__version">Version ${report.version || 1} · ${this.formatDate(report.created_at)}</div>
              </div>
            </div>
          </div>
        `;
      }

      // Veto warnings
      const vetoEl = document.getElementById('veto-warnings');
      if (vetoEl) {
        if (report.triggered_vetoes && report.triggered_vetoes.length > 0) {
          vetoEl.innerHTML = `
            <div class="veto-warnings">
              ${report.triggered_vetoes.map(v => `
                <div class="veto-card">
                  <span class="veto-card__icon">⚠️</span>
                  <div class="veto-card__content">
                    <div class="veto-card__title">${v.label || v.key}</div>
                    <div class="veto-card__desc">Penalty applied: ×${v.penalty || 1} multiplier</div>
                  </div>
                </div>
              `).join('')}
            </div>
          `;
        } else {
          vetoEl.innerHTML = '';
        }
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
        report.delta.dimension_deltas.forEach(d => dimDeltas[d.dimension] = d.change);
      }
      const dimDeltaKeyMap = {
        'Problem Severity': 'problem_score',
        'Buyer Viability': 'buyer_score',
        'Market Potential': 'market_score',
        'Defensibility & Moat': 'moat_score',
        'Technical Feasibility': 'feasibility_score',
      };

      const dimScoresEl = document.getElementById('dimension-scores');
      const scoreTiers = report.score_tiers || {};
      if (dimScoresEl) {
        dimScoresEl.innerHTML = dims.map(d => {
          const s = scores[d.key] || 0;
          const tier = scoreTiers[tierMap[d.key]] || '';
          const barClass = this.getBarClass(s);

          let deltaHtml = '';
          const deltaDim = Object.keys(dimDeltas).find(k => dimDeltaKeyMap[k] === d.key);
          if (deltaDim !== undefined && dimDeltas[deltaDim] !== undefined) {
            const ch = dimDeltas[deltaDim];
            if (ch > 0) deltaHtml = `<span class="dimension-row__delta dimension-row__delta--up">+${ch}</span>`;
            else if (ch < 0) deltaHtml = `<span class="dimension-row__delta dimension-row__delta--down">${ch}</span>`;
          }

          return `
            <div style="margin-bottom:14px;">
              <div class="dimension-row">
                <span class="dimension-row__label">${d.label} <small style="color:var(--muted,#94A3B8);font-weight:400;">(${d.weight})</small></span>
                <div class="dimension-row__bar-wrap">
                  <div class="dimension-row__bar ${barClass}" style="width:${s}%;"></div>
                </div>
                <span class="dimension-row__score">${s} ${deltaHtml}</span>
              </div>
              <div class="dimension-row__tier" style="margin-top:2px;">${tier}</div>
            </div>
          `;
        }).join('');
      }

      // LOFA
      const lofaEl = document.getElementById('lofa-card');
      if (lofaEl) {
        lofaEl.innerHTML = `
          <div class="lofa-card">
            <div class="lofa-card__label">
              🎯 Leap-of-Faith Assumption (LOFA)
            </div>
            <div class="lofa-card__text">"${report.lofa || 'Key hypothesis under test.'}"</div>
          </div>
        `;
      }

      // Overall assessment
      const assessmentEl = document.getElementById('assessment-card');
      if (assessmentEl) {
        assessmentEl.innerHTML = `
          <div class="assessment-card">
            <div class="assessment-card__title">
              <span aria-hidden="true">📝</span> Overall Assessment & Strategic Guidance
            </div>
            <div class="assessment-card__text">${report.overall_assessment || 'N/A'}</div>
          </div>
        `;
      }

      // Red Team Analysis
      const agentAnalysis = report.agent_analysis || {};
      const agents = [
        {
          title: 'Skeptical VC Partner',
          icon: '💼',
          iconClass: 'redteam-card__icon--vc',
          data: agentAnalysis.vc || {},
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
          data: agentAnalysis.buyer || {},
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
          data: agentAnalysis.competitor || {},
          fields: [
            { key: 'primary_incumbent_threat', label: 'Primary Incumbent Threat' },
            { key: 'moat_vulnerability', label: 'Moat Vulnerability' },
            { key: 'competitor_verdict', label: 'Competitor Verdict' },
            { key: 'defensibility_assessment', label: 'Defensibility Assessment' },
          ],
        },
      ];

      const redteamEl = document.getElementById('redteam-grid');
      if (redteamEl) {
        redteamEl.innerHTML = agents.map(agent => {
          const critique = (agent.data && agent.data.critique) ? agent.data.critique : (agent.data || {});
          return `
            <div class="redteam-card">
              <div class="redteam-card__header">
                <div class="redteam-card__icon ${agent.iconClass}">${agent.icon}</div>
                <div class="redteam-card__title">${agent.title}</div>
              </div>
              <div class="redteam-card__body">
                ${agent.fields.map(f => {
                  const val = critique[f.key] || '';
                  if (!val) return '';
                  return `
                    <div style="margin-bottom:10px;">
                      <div class="redteam-field__label">${f.label}</div>
                      <div class="redteam-field__value">${val}</div>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          `;
        }).join('');
      }

      // Strengths & Risks
      const srEl = document.getElementById('sr-grid');
      if (srEl) {
        srEl.innerHTML = `
          <div class="sr-card">
            <div class="sr-card__title">
              <span aria-hidden="true">💪</span> Core Strengths
            </div>
            <div class="sr-list">
              ${(report.strengths || []).map(s => `
                <div class="sr-list__item">
                  <span class="sr-list__bullet sr-list__bullet--green"></span>
                  <span>${s}</span>
                </div>
              `).join('')}
            </div>
          </div>
          <div class="sr-card">
            <div class="sr-card__title">
              <span aria-hidden="true">⚠️</span> Key Business Risks
            </div>
            <div class="sr-list">
              ${(report.key_risks || []).map(r => `
                <div class="sr-list__item">
                  <span class="sr-list__bullet sr-list__bullet--red"></span>
                  <span>${r}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      // Falsification blueprint
      const bp = report.falsification_blueprint || {};
      const blueprintEl = document.getElementById('blueprint-card');
      if (blueprintEl) {
        blueprintEl.innerHTML = `
          <div class="blueprint-card">
            <div class="blueprint-card__title">
              <span aria-hidden="true">🔬</span> Falsification Blueprint
            </div>
            <div class="blueprint-section">
              <div class="blueprint-section__label">Mom Test Discovery Interview Questions</div>
              <div class="mom-test-list">
                ${(bp.mom_test_questions || []).map((q, i) => `
                  <div class="mom-test-item">
                    <span class="mom-test-item__num">${i + 1}</span>
                    <span class="mom-test-item__text">"${q}"</span>
                  </div>
                `).join('')}
              </div>
            </div>
            <div class="blueprint-section" style="margin-top:20px;">
              <div class="blueprint-section__label">Kill Threshold</div>
              <div class="kill-threshold">${bp.kill_threshold || ''}</div>
            </div>
          </div>
        `;
      }

      // Next steps
      const nextstepsEl = document.getElementById('val-nextsteps');
      if (nextstepsEl) {
        nextstepsEl.innerHTML = `
          <div class="val-nextsteps">
            <div class="val-nextsteps__title">
              <span aria-hidden="true">🚀</span> Recommended Next Steps
            </div>
            <div class="val-nextsteps__list">
              ${(report.recommended_next_steps || []).map((s, i) => `
                <div class="val-nextstep">
                  <span class="val-nextstep__num">${i + 1}</span>
                  <span class="val-nextstep__text">${s}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }
    } catch (err) {
      console.error("Error inside renderReport:", err);
    }
  },

  renderVersionDropdown: function () {
    const select = document.getElementById('val-version-select');
    if (!select || !this.history) return;

    select.innerHTML = this.history.map(v => `
      <option value="${v.validation_id}" ${this.currentReport && this.currentReport.validation_id === v.validation_id ? 'selected' : ''}>
        Version ${v.version} (${Math.round(v.final_validation_score)}/100)
      </option>
    `).join('');

    select.onchange = (e) => {
      const valId = parseInt(e.target.value, 10);
      if (valId) this.loadValidationById(valId);
    };
  },

  renderHistoryList: function () {
    const container = document.getElementById('version-history');
    if (!container || !this.history || this.history.length === 0) {
      if (container) container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    container.innerHTML = `
      <div class="version-history">
        <div class="version-history__title">
          <span aria-hidden="true">📋</span> Validation Run History
        </div>
        <div class="version-list">
          ${this.history.map(v => `
            <div class="version-item ${this.currentReport && this.currentReport.validation_id === v.validation_id ? 'version-item--active' : ''}"
                 onclick="IdeaValidationApp.loadValidationById(${v.validation_id})">
              <span class="version-item__version">Version ${v.version}</span>
              <span class="version-item__score">${Math.round(v.final_validation_score)} / 100</span>
              <span class="version-item__date">${this.formatDate(v.created_at)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  },

  exportPDF: function () {
    const element = document.getElementById('val-export-container');
    if (!element) return;

    if (window.html2pdf) {
      const startupName = (this.currentStartup?.name || 'Startup').replace(/[^a-zA-Z0-9]/g, '-');
      const opt = {
        margin: [0.3, 0.3, 0.3, 0.3],
        filename: `${startupName}-AI-Idea-Validation-Report-v${this.currentReport?.version || 1}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#0F172A' },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
      };
      html2pdf().set(opt).from(element).save();
    } else {
      window.print();
    }
  }
};

window.IdeaValidationApp = IdeaValidationApp;
