/**
 * VentureAI — Business Plan Application Module
 */

const BusinessPlanApp = {
  currentStartupId: null,
  currentPlan: null,
  planHistory: [],
  prereqStatus: null,

  /**
   * Initialize Business Plan workspace.
   */
  init: async function (startupId, autoGen = false) {
    this.currentStartupId = startupId;
    this.setupNavigation();

    // Check prerequisites first
    await this.loadPrerequisites(autoGen);
  },

  /**
   * Setup sidebar tab smooth scroll and active highlighting.
   */
  setupNavigation: function () {
    const navItems = document.querySelectorAll('.bp-nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', (e) => {
        navItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        const targetId = item.getAttribute('data-target');
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  },

  /**
   * Load prerequisite status from API.
   */
  loadPrerequisites: async function (autoGen = false) {
    try {
      const status = await apiRequest(`/startups/${this.currentStartupId}/business-plan/check-prerequisites`);
      this.prereqStatus = status;

      if (!status.can_generate) {
        this.showPrerequisiteState(status);
        return;
      }

      // Prerequisites met — load history and latest plan
      await this.loadHistory();
      await this.loadLatestPlan(autoGen);
    } catch (err) {
      console.error("Prerequisites check error:", err);
      this.showPrerequisiteState({
        has_workspace: true,
        has_validation: false,
        has_bmc: false,
        missing_prerequisite_message: "Complete AI Idea Validation and Business Model Canvas first."
      });
    }
  },

  /**
   * Display missing prerequisite state with checklist.
   */
  showPrerequisiteState: function (status) {
    document.getElementById('bp-loading').style.display = 'none';
    document.getElementById('bp-empty-state').style.display = 'none';
    document.getElementById('bp-main-state').style.display = 'none';
    document.getElementById('bp-prereq-state').style.display = 'block';

    const msgEl = document.getElementById('bp-prereq-message');
    if (msgEl) {
      msgEl.textContent = status.missing_prerequisite_message || "Complete prerequisites first.";
    }

    const listEl = document.getElementById('bp-prereq-checklist');
    if (listEl) {
      listEl.innerHTML = `
        <div class="bp-prereq-item ${status.has_workspace ? 'bp-prereq-item--checked' : 'bp-prereq-item--missing'}">
          <span class="bp-prereq-icon">${status.has_workspace ? '✓' : '✗'}</span> Startup Workspace
        </div>
        <div class="bp-prereq-item ${status.has_validation ? 'bp-prereq-item--checked' : 'bp-prereq-item--missing'}">
          <span class="bp-prereq-icon">${status.has_validation ? '✓' : '✗'}</span> AI Idea Validation Report
        </div>
        <div class="bp-prereq-item ${status.has_bmc ? 'bp-prereq-item--checked' : 'bp-prereq-item--missing'}">
          <span class="bp-prereq-icon">${status.has_bmc ? '✓' : '✗'}</span> AI Business Model Canvas (BMC)
        </div>
      `;
    }
  },

  /**
   * Navigate founder to the missing prerequisite page.
   */
  goToPrerequisite: function () {
    if (!this.prereqStatus) return;

    if (!this.prereqStatus.has_validation) {
      window.location.href = `startup-workspace.html?id=${this.currentStartupId}`;
    } else if (!this.prereqStatus.has_bmc) {
      window.location.href = `bmc.html?startup_id=${this.currentStartupId}&generate=true`;
    } else {
      window.location.href = `startup-workspace.html?id=${this.currentStartupId}`;
    }
  },

  /**
   * Fetch version history.
   */
  loadHistory: async function () {
    try {
      const history = await apiRequest(`/startups/${this.currentStartupId}/business-plan/versions`);
      this.planHistory = history || [];
    } catch (err) {
      console.warn("Failed to load plan history:", err);
      this.planHistory = [];
    }
  },

  /**
   * Fetch latest generated plan.
   */
  loadLatestPlan: async function (autoGen = false) {
    try {
      const plan = await apiRequest(`/startups/${this.currentStartupId}/business-plan/latest`);
      if (plan && plan.id) {
        this.renderPlan(plan);
      } else {
        if (autoGen) {
          this.generatePlan();
        } else {
          this.showEmptyState();
        }
      }
    } catch (err) {
      console.warn("Failed to load latest business plan:", err);
      if (autoGen) {
        this.generatePlan();
      } else {
        this.showEmptyState();
      }
    }
  },

  /**
   * Show empty state when prerequisites met but no plan exists yet.
   */
  showEmptyState: function () {
    document.getElementById('bp-loading').style.display = 'none';
    document.getElementById('bp-prereq-state').style.display = 'none';
    document.getElementById('bp-main-state').style.display = 'none';
    document.getElementById('bp-empty-state').style.display = 'block';
  },

  /**
   * Generate a complete new Business Plan version with AI pipeline.
   */
  generatePlan: async function () {
    document.getElementById('bp-empty-state').style.display = 'none';
    document.getElementById('bp-prereq-state').style.display = 'none';
    document.getElementById('bp-main-state').style.display = 'none';
    document.getElementById('bp-loading').style.display = 'block';

    try {
      const plan = await apiRequest(`/startups/${this.currentStartupId}/business-plan/generate`, {
        method: 'POST'
      });

      await this.loadHistory();
      this.renderPlan(plan);
    } catch (err) {
      console.error("Business Plan generation error:", err);
      alert(`Generation Error: ${err.message}`);
      this.loadPrerequisites(false);
    }
  },

  /**
   * Render complete Business Plan document.
   */
  renderPlan: function (plan) {
    this.currentPlan = plan;

    document.getElementById('bp-loading').style.display = 'none';
    document.getElementById('bp-empty-state').style.display = 'none';
    document.getElementById('bp-prereq-state').style.display = 'none';
    document.getElementById('bp-main-state').style.display = 'block';

    // 1. Version select dropdown
    this.populateVersionDropdown();

    // 2. Pivot-Aware Mode Banner
    const isPivot = plan.is_pivot_mode || (plan.validation_score !== null && plan.validation_score < 50);
    const pivotBanner = document.getElementById('bp-pivot-banner');
    const pivotBadge = document.getElementById('bp-pivot-badge');
    const scoreSpan = document.getElementById('bp-banner-val-score');

    if (isPivot) {
      if (pivotBanner) pivotBanner.style.display = 'flex';
      if (pivotBadge) pivotBadge.style.display = 'inline-flex';
      if (scoreSpan) scoreSpan.textContent = plan.validation_score ? plan.validation_score.toFixed(0) : '45';
    } else {
      if (pivotBanner) pivotBanner.style.display = 'none';
      if (pivotBadge) pivotBadge.style.display = 'none';
    }

    // 3. Document Cover Meta
    const startupName = window._currentStartup?.name || "Your Startup";
    const tagline = window._currentStartup?.tagline || window._currentStartup?.solution || "";

    document.getElementById('doc-startup-name').textContent = startupName;
    document.getElementById('doc-startup-tagline').textContent = tagline;
    document.getElementById('doc-meta-version').textContent = `Version ${plan.version}.0`;
    document.getElementById('doc-meta-date').textContent = new Date(plan.created_at).toLocaleDateString();
    document.getElementById('doc-meta-score').textContent = plan.validation_score ? `${plan.validation_score.toFixed(0)}/100` : 'N/A';

    const pill = document.getElementById('bp-startup-name-pill');
    if (pill) pill.textContent = startupName;

    // 4. Executive Summary
    this.renderExecutiveSummary(plan.executive_summary);

    // 5. Domains 1 to 5
    const d = plan.domains_data || {};
    this.renderDomain1(d.market_customer || {});
    this.renderDomain2(d.business_model_unit_economics || {});
    this.renderDomain3(d.gtm_operations || {});
    this.renderDomain4(d.financial_structure || {});
    this.renderDomain5(d.risk_validation_legal || {});

    // 6. Red Pen Audit
    this.renderAuditReport(plan.audit_report || {});
  },

  /**
   * Populate Version Select Dropdown.
   */
  populateVersionDropdown: function () {
    const select = document.getElementById('bp-version-select');
    if (!select) return;

    select.innerHTML = '';

    if (!this.planHistory || this.planHistory.length === 0) {
      select.innerHTML = `<option value="${this.currentPlan.id}">v${this.currentPlan.version}.0 (Latest)</option>`;
      return;
    }

    this.planHistory.forEach((item, idx) => {
      const opt = document.createElement('option');
      opt.value = item.id;
      const isLatest = idx === 0 ? ' (Latest)' : '';
      opt.textContent = `v${item.version}.0 - ${new Date(item.created_at).toLocaleDateString()}${isLatest}`;
      if (item.id === this.currentPlan.id) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  },

  /**
   * Handle dropdown version change.
   */
  onVersionChange: async function (planId) {
    try {
      const plan = await apiRequest(`/business-plan/${planId}`);
      if (plan) {
        this.renderPlan(plan);
      }
    } catch (err) {
      console.error("Failed to load version:", err);
    }
  },

  /**
   * Render Executive Summary.
   */
  renderExecutiveSummary: function (summary) {
    const container = document.getElementById('content-exec-summary');
    if (!container) return;

    container.innerHTML = `
      <div class="bp-subcard">
        <div class="bp-subcard__title">📌 Startup Overview</div>
        <p>${summary.startup_overview || 'N/A'}</p>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
        <div class="bp-subcard" style="margin:0;">
          <div class="bp-subcard__title">🚨 Problem Statement</div>
          <p>${summary.problem_statement || 'N/A'}</p>
        </div>
        <div class="bp-subcard" style="margin:0;">
          <div class="bp-subcard__title">💡 Core Solution</div>
          <p>${summary.solution_overview || 'N/A'}</p>
        </div>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">🎯 Target Customer & Business Model</div>
        <p><strong>Target Customer:</strong> ${summary.target_customer || 'N/A'}</p>
        <p><strong>Business Model:</strong> ${summary.business_model_summary || 'N/A'}</p>
        <p><strong>Go-To-Market Direction:</strong> ${summary.gtm_direction || 'N/A'}</p>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">🚀 Next Steps & Validation Readiness</div>
        <p><strong>Validation Readiness:</strong> ${summary.validation_readiness || 'N/A'}</p>
        <strong>Key Founder Next Steps:</strong>
        <ul>
          ${(summary.key_next_steps || []).map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>
    `;
  },

  /**
   * Render Domain 1: Market & Customer
   */
  renderDomain1: function (d) {
    const el = document.getElementById('content-market-customer');
    if (!el) return;

    el.innerHTML = `
      <div class="bp-subcard">
        <div class="bp-subcard__title">Problem Analysis & Severity</div>
        <p>${d.problem_analysis || 'N/A'}</p>
        <p style="color:#94A3B8;font-size:0.88rem;font-style:italic;">Note: ${d.problem_severity_note || 'Aligned with validation problem score.'}</p>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Ideal Customer Profile & Buyer Persona</div>
        <p><strong>ICP Definition:</strong> ${d.icp_definition || 'N/A'}</p>
        <p><strong>Buyer Persona:</strong> ${d.buyer_persona || 'N/A'}</p>
        <strong>Customer Pain Points:</strong>
        <ul>${(d.customer_pain_points || []).map(p => `<li>${p}</li>`).join('')}</ul>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Market Opportunity & Drivers</div>
        <p>${d.market_opportunity || 'N/A'}</p>
        <strong>TAM/SAM/SOM Qualitative Drivers:</strong>
        <ul>${(d.tam_sam_som_drivers || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <strong>Market Growth Drivers:</strong>
        <ul>${(d.market_growth_drivers || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <strong>Market Limitations / Stats Note:</strong>
        <ul>${(d.market_limitations || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Competitive Positioning & Defensibility Moat</div>
        <p><strong>Direct Competitors:</strong> ${(d.direct_competitors || []).join(', ') || 'N/A'}</p>
        <p><strong>Indirect Competitors:</strong> ${(d.indirect_competitors || []).join(', ') || 'N/A'}</p>
        <p><strong>Existing Alternatives:</strong> ${(d.existing_alternatives || []).join(', ') || 'N/A'}</p>
        <p><strong>Competitive Positioning:</strong> ${d.competitive_positioning || 'N/A'}</p>
        <p><strong>Defensibility Moat:</strong> ${d.defensibility_moat || 'N/A'}</p>
      </div>
    `;
  },

  /**
   * Render Domain 2: Business Model & Unit Economics
   */
  renderDomain2: function (d) {
    const el = document.getElementById('content-business-model');
    if (!el) return;

    el.innerHTML = `
      <div class="bp-subcard">
        <div class="bp-subcard__title">Revenue Model & Pricing Logic</div>
        <p><strong>Primary Revenue Model:</strong> ${d.revenue_model || 'N/A'}</p>
        <p><strong>Monetization Strategy:</strong> ${d.monetization_strategy || 'N/A'}</p>
        <p><strong>Pricing Logic:</strong> ${d.pricing_logic || 'N/A'}</p>
        <p><strong>Payment Mechanism:</strong> ${d.payment_mechanism || 'N/A'}</p>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">CAC & LTV Economics Framework</div>
        <p><strong>CAC Framework:</strong> ${d.cac_framework || 'N/A'}</p>
        <p><strong>LTV Framework:</strong> ${d.ltv_framework || 'N/A'}</p>
        <p><strong>CAC/LTV Relationship Target:</strong> ${d.cac_ltv_relationship || 'N/A'}</p>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Economics Assumptions & Key Metrics</div>
        <strong>Unit Economics Assumptions:</strong>
        <ul>${(d.unit_economics_assumptions || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <strong>Key Economics Metrics to Track:</strong>
        <ul>${(d.key_metrics_to_track || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </div>
    `;
  },

  /**
   * Render Domain 3: Go-To-Market & Operations
   */
  renderDomain3: function (d) {
    const el = document.getElementById('content-gtm-operations');
    if (!el) return;

    el.innerHTML = `
      <div class="bp-subcard">
        <div class="bp-subcard__title">Customer Acquisition & Sales Strategy</div>
        <p><strong>Acquisition Strategy:</strong> ${d.customer_acquisition_strategy || 'N/A'}</p>
        <p><strong>Sales Strategy:</strong> ${d.sales_strategy || 'N/A'}</p>
        <p><strong>Distribution Strategy:</strong> ${d.distribution_strategy || 'N/A'}</p>
        <strong>Marketing Channels:</strong>
        <ul>${(d.marketing_channels || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Customer Onboarding & Retention</div>
        <p><strong>Onboarding Flow:</strong> ${d.customer_onboarding || 'N/A'}</p>
        <p><strong>Retention Approach:</strong> ${d.customer_retention_approach || 'N/A'}</p>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Operational Workflow & Infrastructure Requirements</div>
        <strong>Operational Workflow:</strong>
        <ul>${(d.operational_workflow || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <strong>Technology & Infrastructure Requirements:</strong>
        <ul>${(d.technology_infrastructure_requirements || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <strong>Key Operational Dependencies:</strong>
        <ul>${(d.operational_dependencies || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </div>
    `;
  },

  /**
   * Render Domain 4: Financial Structure
   */
  renderDomain4: function (d) {
    const el = document.getElementById('content-financial-structure');
    if (!el) return;

    el.innerHTML = `
      <div class="bp-subcard">
        <div class="bp-subcard__title">Cost Categories & Drivers</div>
        <p><strong>Startup Setup Costs:</strong> ${(d.startup_cost_categories || []).join(', ') || 'N/A'}</p>
        <p><strong>Operating Cost Categories:</strong> ${(d.operating_cost_categories || []).join(', ') || 'N/A'}</p>
        <p><strong>Infrastructure Costs:</strong> ${(d.infrastructure_costs || []).join(', ') || 'N/A'}</p>
        <p><strong>Sales & Marketing Costs:</strong> ${(d.sales_marketing_costs || []).join(', ') || 'N/A'}</p>
        <strong>Major Cost Drivers:</strong>
        <ul>${(d.major_cost_drivers || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Burn-Rate & Break-Even Logic</div>
        <p><strong>Burn-Rate Management:</strong> ${d.burn_rate_explanation || 'N/A'}</p>
        <p><strong>Break-Even Logic & Formula:</strong> ${d.break_even_logic || 'N/A'}</p>
        <p><strong>Break-Even Operational Volume Required:</strong> ${d.break_even_volume_requirements || 'N/A'}</p>
      </div>
    `;
  },

  /**
   * Render Domain 5: Risk, Validation & Legal
   */
  renderDomain5: function (d) {
    const el = document.getElementById('content-risk-legal');
    if (!el) return;

    el.innerHTML = `
      <div class="bp-subcard">
        <div class="bp-subcard__title">Business Risks & Mitigation Strategies</div>
        <strong>Major Business & Market Risks:</strong>
        <ul>
          ${(d.major_business_risks || []).map(x => `<li>${x}</li>`).join('')}
          ${(d.buyer_adoption_risks || []).map(x => `<li>${x}</li>`).join('')}
        </ul>
        <strong>Risk Mitigation Strategies:</strong>
        <ul>${(d.risk_mitigation_strategies || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <p><strong>Plan B / Fallback Pivot Strategy:</strong> ${d.plan_b_fallback_strategy || 'N/A'}</p>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Falsification Blueprint & LOFA</div>
        <p><strong>Leap-of-Faith Assumption (LOFA):</strong> ${d.lofa || 'N/A'}</p>
        <p><strong>Kill Threshold / Falsification Criteria:</strong> ${d.kill_threshold || 'N/A'}</p>
        <strong>Mom Test Discovery Questions:</strong>
        <ul>${(d.mom_test_questions || []).map(q => `<li>"${q}"</li>`).join('')}</ul>
      </div>

      <div class="bp-subcard">
        <div class="bp-subcard__title">Legal, IP & Compliance Considerations</div>
        <p style="color:#94A3B8;font-size:0.84rem;font-style:italic;">Disclaimer: General informational considerations. Consult qualified legal counsel for binding legal guidance.</p>
        <strong>General Legal Considerations:</strong>
        <ul>${(d.general_legal_considerations || []).map(x => `<li>${x}</li>`).join('')}</ul>
        <strong>IP & Proprietary Protection:</strong>
        <ul>${(d.ip_considerations || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </div>
    `;
  },

  /**
   * Render Cross-Document Audit Report.
   */
  renderAuditReport: function (audit) {
    const el = document.getElementById('content-audit-warnings');
    const badgeCount = document.getElementById('bp-audit-badge-count');
    const cardWrap = document.getElementById('bp-audit-card-wrap');

    if (!el) return;

    const health = audit.health_score ?? 100;
    const warnings = audit.warnings || [];

    if (badgeCount) badgeCount.textContent = warnings.length;

    // Render banner card if warnings exist
    if (cardWrap) {
      if (warnings.length > 0) {
        cardWrap.innerHTML = `
          <div class="bp-audit-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <h4 style="margin:0;color:#FFF;font-size:1.05rem;">🔍 Cross-Document Consistency Audit</h4>
              <span class="bp-badge ${health >= 80 ? 'bp-badge--success' : health >= 60 ? 'bp-badge--warning' : 'bp-badge--error'}">Health Score: ${health}/100</span>
            </div>
            <p style="color:#94A3B8;font-size:0.88rem;margin:0 0 12px 0;">
              Detected ${warnings.length} potential contradiction(s) between Business Plan sections and upstream Workspace/Validation/BMC data:
            </p>
          </div>
        `;
      } else {
        cardWrap.innerHTML = `
          <div class="bp-audit-card">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:1.2rem;">✅</span>
              <div>
                <strong style="color:#34D399;">Cross-Document Consistency Audit Passed (100/100)</strong>
                <p style="margin:2px 0 0 0;color:#94A3B8;font-size:0.88rem;">No contradictions detected between Business Plan, Workspace, Validation, and Business Model Canvas.</p>
              </div>
            </div>
          </div>
        `;
      }
    }

    if (warnings.length === 0) {
      el.innerHTML = `<p style="color:#34D399;">No consistency conflicts found. All sections align with upstream data.</p>`;
      return;
    }

    el.innerHTML = warnings.map(w => `
      <div class="bp-audit-item bp-audit-item--${w.severity || 'MEDIUM'}">
        <div class="bp-audit-item__title">
          <span class="bp-badge ${w.severity === 'HIGH' ? 'bp-badge--error' : 'bp-badge--warning'}">${w.severity || 'WARNING'}</span>
          <span>${w.section}</span>
        </div>
        <div class="bp-audit-item__desc"><strong>Issue:</strong> ${w.issue}</div>
        <div style="font-size:0.84rem;color:#94A3B8;margin-bottom:4px;"><strong>Source Context:</strong> ${w.source_context}</div>
        <div class="bp-audit-item__rec"><strong>Recommended Correction:</strong> ${w.recommended_correction}</div>
      </div>
    `).join('');
  },

  /**
   * Open Single Section Regeneration Modal.
   */
  openRegenModal: function (sectionKey) {
    const modal = document.getElementById('bp-regen-modal');
    const inputKey = document.getElementById('bp-modal-section-key');
    const title = document.getElementById('bp-modal-title');
    const text = document.getElementById('bp-modal-instructions');

    if (inputKey) inputKey.value = sectionKey;
    if (text) text.value = '';

    const labels = {
      market_customer: 'Domain 1 — Market & Customer',
      business_model_unit_economics: 'Domain 2 — Business Model & Economics',
      gtm_operations: 'Domain 3 — Go-To-Market & Operations',
      financial_structure: 'Domain 4 — Financial Structure',
      risk_validation_legal: 'Domain 5 — Risk, Validation & Legal',
      executive_summary: 'Executive Summary',
    };

    if (title) title.textContent = `Regenerate ${labels[sectionKey] || sectionKey}`;
    if (modal) modal.style.display = 'flex';
  },

  /**
   * Close Section Regeneration Modal.
   */
  closeRegenModal: function () {
    const modal = document.getElementById('bp-regen-modal');
    if (modal) modal.style.display = 'none';
  },

  /**
   * Display toast message feedback.
   */
  showToast: function (msg) {
    const old = document.querySelector('.vp-toast');
    if (old) old.remove();

    const toast = document.createElement('div');
    toast.className = 'vp-toast';
    toast.innerHTML = `<span>✨</span> <span>${msg}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.5s ease';
      setTimeout(() => toast.remove(), 500);
    }, 3500);
  },

  /**
   * Submit Section Regeneration Request.
   */
  submitRegenSection: async function () {
    const sectionKey = document.getElementById('bp-modal-section-key').value;
    const instructions = document.getElementById('bp-modal-instructions').value;

    if (!sectionKey || !this.currentPlan) return;

    this.closeRegenModal();

    document.getElementById('bp-main-state').style.display = 'none';
    document.getElementById('bp-loading').style.display = 'block';

    try {
      const updatedPlan = await apiRequest(`/business-plan/${this.currentPlan.id}/regenerate-section`, {
        method: 'POST',
        body: {
          section_name: sectionKey,
          custom_instructions: instructions || null,
        },
      });

      await this.loadHistory();
      this.renderPlan(updatedPlan);

      const secMap = {
        executive_summary: 'sec-exec-summary',
        market_customer: 'sec-market-customer',
        business_model_unit_economics: 'sec-business-model',
        gtm_operations: 'sec-gtm-operations',
        financial_structure: 'sec-financial-structure',
        risk_validation_legal: 'sec-risk-legal',
      };

      const domId = secMap[sectionKey];
      if (domId) {
        const secEl = document.getElementById(domId);
        if (secEl) {
          secEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          secEl.classList.add('bp-section--highlight');
          setTimeout(() => secEl.classList.remove('bp-section--highlight'), 2600);
        }
      }

      const labels = {
        executive_summary: 'Executive Summary',
        market_customer: 'Domain 1 — Market & Customer',
        business_model_unit_economics: 'Domain 2 — Business Model & Economics',
        gtm_operations: 'Domain 3 — Go-To-Market & Operations',
        financial_structure: 'Domain 4 — Financial Structure',
        risk_validation_legal: 'Domain 5 — Risk, Validation & Legal',
      };
      this.showToast(`${labels[sectionKey] || sectionKey} regenerated successfully (v${updatedPlan.version}.0)!`);
    } catch (err) {
      console.error("Section regeneration error:", err);
      alert(`Regeneration Error: ${err.message}`);
      if (this.currentPlan) this.renderPlan(this.currentPlan);
    }
  },

  /**
   * Export Business Plan as PDF using html2pdf.js.
   */
  exportPDF: function () {
    const element = document.getElementById('bp-export-container');
    if (!element) {
      alert('Business Plan document container not found.');
      return;
    }

    if (window.html2pdf) {
      const startupName = (window._currentStartup?.name || 'Startup').replace(/[^a-zA-Z0-9]/g, '-');
      const opt = {
        margin:       [12, 12, 12, 12],
        filename:     `${startupName}-Business-Plan-v${this.currentPlan?.version || 1}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#0F172A' },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };

      window.html2pdf().set(opt).from(element).save();
    } else {
      window.print();
    }
  }
};

window.BusinessPlanApp = BusinessPlanApp;
