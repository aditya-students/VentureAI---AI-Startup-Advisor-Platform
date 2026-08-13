/**
 * VentureAI — AI Business Model Canvas Controller (Vanilla JS)
 * Uses global apiRequest helper from auth.js for proper API base routing (port 8000).
 */

(function () {
  'use strict';

  // Dependency Matrix definition
  const DEPENDENCY_MATRIX = {
    customer_segments: ['value_propositions', 'channels', 'revenue_streams'],
    value_propositions: ['channels', 'customer_relationships', 'key_activities'],
    channels: ['customer_relationships', 'cost_structure'],
    key_activities: ['key_resources', 'key_partnerships', 'cost_structure'],
    key_resources: ['cost_structure'],
    key_partnerships: ['key_activities', 'cost_structure'],
    customer_relationships: [],
    revenue_streams: [],
    cost_structure: []
  };

  const BLOCK_TITLES = {
    key_partnerships: { title: 'Key Partnerships', icon: '🤝', gridClass: 'bmc-block--kp' },
    key_activities: { title: 'Key Activities', icon: '⚡', gridClass: 'bmc-block--ka' },
    key_resources: { title: 'Key Resources', icon: '🔑', gridClass: 'bmc-block--kr' },
    value_propositions: { title: 'Value Propositions', icon: '💎', gridClass: 'bmc-block--vp' },
    customer_relationships: { title: 'Customer Relationships', icon: '❤️', gridClass: 'bmc-block--cr' },
    channels: { title: 'Channels', icon: '📣', gridClass: 'bmc-block--ch' },
    customer_segments: { title: 'Customer Segments', icon: '🎯', gridClass: 'bmc-block--cs' },
    cost_structure: { title: 'Cost Structure', icon: '💸', gridClass: 'bmc-block--cost' },
    revenue_streams: { title: 'Revenue Streams', icon: '💰', gridClass: 'bmc-block--rev' }
  };

  let currentStartupId = null;
  let currentBMC = null;
  let currentVersions = [];

  window.BMCApp = {
    init: function (startupId) {
      currentStartupId = startupId;
      this.bindEvents();
      this.loadBMC();
    },

    bindEvents: function () {
      const btnGenerate = document.getElementById('btn-generate-bmc');
      if (btnGenerate) {
        btnGenerate.addEventListener('click', () => this.generateBMC());
      }

      const versionSelect = document.getElementById('bmc-version-select');
      if (versionSelect) {
        versionSelect.addEventListener('change', (e) => this.loadVersion(e.target.value));
      }
    },

    loadBMC: async function () {
      const emptyState = document.getElementById('bmc-empty-state');
      const mainState = document.getElementById('bmc-main-state');

      try {
        // 1. Check validation report status for context banner
        let valData = null;
        try {
          valData = await apiRequest(`/startups/${currentStartupId}/idea-validation/latest`);
        } catch (e) {
          // Silently ignore if no validation exists yet
        }

        this.renderContextBanner(valData);

        // 2. Fetch latest BMC
        try {
          currentBMC = await apiRequest(`/startups/${currentStartupId}/bmc/latest`);
        } catch (err) {
          if (err.message && (err.message.includes('No Business Model Canvas') || err.message.includes('404'))) {
            if (emptyState) emptyState.style.display = 'block';
            if (mainState) mainState.style.display = 'none';
            return;
          }
          throw err;
        }

        if (emptyState) emptyState.style.display = 'none';
        if (mainState) mainState.style.display = 'block';

        this.renderBMC(currentBMC);
        this.loadHistory();

        // Auto export PDF if requested via URL params
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('pdf') === 'true') {
          setTimeout(() => this.exportPDF(), 600);
        }
      } catch (err) {
        console.error('Error loading BMC:', err);
      }
    },

    renderContextBanner: function (valData) {
      const banner = document.getElementById('bmc-context-info');
      if (!banner) return;

      if (valData && valData.scores) {
        banner.innerHTML = `
          <span class="bmc-context-badge">
            ✓ Driven by AI Idea Validation Report (Moat: ${valData.scores.moat_score}/100, Score: ${valData.scores.overall_score}/100)
          </span>
        `;
      } else {
        banner.innerHTML = `
          <span class="bmc-context-badge bmc-context-badge--no-val">
            ⚠️ No Idea Validation report found. BMC generated using baseline startup profile data.
          </span>
        `;
      }
    },

    generateBMC: async function () {
      const loading = document.getElementById('bmc-loading');
      const emptyState = document.getElementById('bmc-empty-state');
      const mainState = document.getElementById('bmc-main-state');

      if (loading) loading.style.display = 'block';
      if (emptyState) emptyState.style.display = 'none';
      if (mainState) mainState.style.display = 'none';

      try {
        currentBMC = await apiRequest(`/startups/${currentStartupId}/bmc/generate`, {
          method: 'POST'
        });

        if (loading) loading.style.display = 'none';
        if (mainState) mainState.style.display = 'block';

        this.renderBMC(currentBMC);
        this.loadHistory();
      } catch (err) {
        if (loading) loading.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        alert('Failed to generate Business Model Canvas: ' + (err.message || err));
      }
    },

    loadHistory: async function () {
      const versionSelect = document.getElementById('bmc-version-select');
      if (!versionSelect) return;

      try {
        currentVersions = await apiRequest(`/startups/${currentStartupId}/bmc/history`);

        versionSelect.innerHTML = currentVersions.map(v => `
          <option value="${v.version_number || v.version}" ${currentBMC && (currentBMC.version_number === (v.version_number || v.version) || currentBMC.version === (v.version_number || v.version)) ? 'selected' : ''}>
            v${v.version_number || v.version} (${new Date(v.created_at).toLocaleDateString()})
          </option>
        `).join('');
      } catch (err) {
        console.error('Error loading BMC history:', err);
      }
    },

    loadVersion: async function (versionNumber) {
      try {
        const bmc = await apiRequest(`/startups/${currentStartupId}/bmc/versions/${versionNumber}`);
        currentBMC = bmc;
        this.renderBMC(currentBMC);
      } catch (err) {
        alert('Error loading version: ' + (err.message || err));
      }
    },

    renderBMC: function (bmc) {
      if (!bmc) return;

      // Populate startup name pill in header
      const namePill = document.getElementById('bmc-startup-name-pill');
      if (namePill) {
        namePill.textContent = `Startup #${bmc.startup_id} • v${bmc.version_number || bmc.version}`;
      }

      // Render Pivot Banner
      const pivotBanner = document.getElementById('bmc-pivot-banner');
      if (pivotBanner) {
        if (bmc.generation_mode === 'PIVOT_AWARE') {
          pivotBanner.style.display = 'flex';
          pivotBanner.innerHTML = `
            <div class="bmc-pivot-content">
              <span class="bmc-pivot-icon">⚠️</span>
              <div class="bmc-pivot-text">
                <h4>Pivot-Aware Mode Activated</h4>
                <p>Idea Validation overall score &lt; 50. Canvas generated with non-standard market assumption constraints.</p>
              </div>
            </div>
          `;
        } else {
          pivotBanner.style.display = 'none';
        }
      }

      // Render Red Pen Audit Report
      if (bmc.audit_data) {
        this.renderAudit(bmc.audit_data);
      }

      // Render Grid Cards
      const grid = document.getElementById('bmc-grid');
      if (!grid) return;

      const blockKeys = [
        'key_partnerships', 'key_activities', 'key_resources',
        'value_propositions', 'customer_relationships', 'channels',
        'customer_segments', 'cost_structure', 'revenue_streams'
      ];

      grid.innerHTML = blockKeys.map(key => {
        const meta = BLOCK_TITLES[key];
        const rawObj = (bmc.canvas_data && bmc.canvas_data[key]);
        let itemsList = [];
        let isAI = true;

        if (Array.isArray(rawObj)) {
          itemsList = rawObj;
        } else if (rawObj && typeof rawObj === 'object') {
          itemsList = rawObj.items || [];
          if (rawObj.generated_by_ai === false || rawObj.modified_by_founder === true) {
            isAI = false;
          }
        }

        return `
          <div class="bmc-card ${meta.gridClass}" data-block="${key}">
            <div class="bmc-card-header">
              <div class="bmc-card-title-group">
                <span class="bmc-card-icon">${meta.icon}</span>
                <h3 class="bmc-card-title">${meta.title}</h3>
              </div>
              <span class="bmc-card-badge ${isAI ? 'bmc-card-badge--ai' : 'bmc-card-badge--founder'}">
                ${isAI ? 'AI Generated' : 'Founder Edited'}
              </span>
            </div>

            <ul class="bmc-card-items">
              ${itemsList.map(item => `<li>${this.escapeHTML(item)}</li>`).join('')}
            </ul>

            <div class="bmc-card-actions">
              <button type="button" class="btn btn--outline bmc-btn-sm btn-edit-block" data-block="${key}">
                ✏️ Edit
              </button>
              <button type="button" class="btn btn--outline bmc-btn-sm btn-regen-block" data-block="${key}">
                🤖 AI Regenerate
              </button>
            </div>
          </div>
        `;
      }).join('');

      // Bind block edit buttons
      grid.querySelectorAll('.btn-edit-block').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          const key = e.currentTarget.dataset.block;
          const rawObj = currentBMC.canvas_data ? currentBMC.canvas_data[key] : null;
          let items = [];
          if (Array.isArray(rawObj)) {
            items = rawObj;
          } else if (rawObj && typeof rawObj === 'object') {
            items = rawObj.items || [];
          }
          this.openEditModal(key, items);
        });
      });

      // Bind block AI regenerate buttons
      grid.querySelectorAll('.btn-regen-block').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          const key = e.currentTarget.dataset.block;
          this.openRegenBlockModal(key);
        });
      });
    },

    renderAudit: function (audit) {
      const container = document.getElementById('bmc-audit-card');
      if (!container || !audit) return;

      const health = audit.health_score ?? 85;
      const conflicts = audit.conflicts || [];

      let healthClass = 'bmc-health-circle';
      if (health < 60) healthClass += ' bmc-health-circle--error';
      else if (health < 80) healthClass += ' bmc-health-circle--warning';

      container.innerHTML = `
        <div class="bmc-audit-header">
          <div class="bmc-audit-score-wrap">
            <div class="${healthClass}">${health}%</div>
            <div>
              <h3 class="bmc-audit-title">Red Pen Audit Health Score</h3>
              <p class="bmc-audit-subtitle">${conflicts.length === 0 ? '✓ No business model contradictions detected.' : `⚠️ ${conflicts.length} inter-block conflict(s) identified.`}</p>
            </div>
          </div>
        </div>

        ${conflicts.length > 0 ? `
          <div class="bmc-audit-conflicts-list">
            ${conflicts.map(c => `
              <div class="bmc-conflict-item ${c.severity === 'error' ? 'bmc-conflict-item--error' : ''}">
                <div class="bmc-conflict-title-row">
                  <span class="bmc-conflict-title">${this.escapeHTML(c.title)}</span>
                  <span class="bmc-conflict-blocks">${(c.blocks || []).join(', ')}</span>
                </div>
                <p class="bmc-conflict-desc">${this.escapeHTML(c.description)}</p>
                <p class="bmc-conflict-rec">💡 <strong>Recommendation:</strong> ${this.escapeHTML(c.recommendation)}</p>
              </div>
            `).join('')}
          </div>
        ` : ''}
      `;
    },

    exportPDF: function () {
      const element = document.getElementById('bmc-export-container') || document.getElementById('bmc-grid');
      if (!element) {
        alert('Canvas grid element not found for PDF export.');
        return;
      }

      if (window.html2pdf) {
        const opt = {
          margin:       [8, 8, 8, 8],
          filename:     `Business-Model-Canvas-v${currentBMC?.version_number || currentBMC?.version || 1}.pdf`,
          image:        { type: 'jpeg', quality: 0.98 },
          html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#131722' },
          jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' }
        };

        window.html2pdf().set(opt).from(element).save()
          .catch(err => {
            console.error('PDF export error:', err);
            window.print();
          });
      } else {
        window.print();
      }
    },

    openEditModal: function (blockKey, currentItems) {
      const meta = BLOCK_TITLES[blockKey];
      const itemsArray = Array.isArray(currentItems) ? currentItems : [];
      const text = itemsArray.join('\n');

      const existingModal = document.getElementById('modal-edit-block-backdrop');
      if (existingModal) existingModal.remove();

      const modalHtml = `
        <div class="bmc-dep-backdrop" id="modal-edit-block-backdrop">
          <div class="bmc-dep-modal" style="position:relative;z-index:100000;">
            <h3 class="bmc-dep-title">Edit ${meta ? meta.title : blockKey}</h3>
            <p class="bmc-dep-desc">Enter each bullet point on a new line:</p>
            <textarea id="edit-block-text" rows="8" class="workspace-form-group" style="width:100%;padding:12px;background:#131722;color:#FFF;border:1px solid rgba(99,102,241,0.3);border-radius:8px;font-family:inherit;font-size:0.9rem;line-height:1.5;box-sizing:border-box;resize:vertical;">${this.escapeHTML(text)}</textarea>
            <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px;">
              <button type="button" class="btn btn--outline" id="btn-cancel-edit-block">Cancel</button>
              <button type="button" class="btn btn--primary" id="btn-save-edit-block">Save Changes</button>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);

      const backdrop = document.getElementById('modal-edit-block-backdrop');
      const cancelBtn = document.getElementById('btn-cancel-edit-block');
      const saveBtn = document.getElementById('btn-save-edit-block');

      if (cancelBtn) {
        cancelBtn.addEventListener('click', () => backdrop.remove());
      }

      if (backdrop) {
        backdrop.addEventListener('click', (e) => {
          if (e.target === backdrop) backdrop.remove();
        });
      }

      if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
          const textarea = document.getElementById('edit-block-text');
          if (!textarea) return;
          const val = textarea.value;
          const newItems = val.split('\n').map(s => s.trim()).filter(s => s.length > 0);
          backdrop.remove();
          await this.saveBlockEdit(blockKey, newItems);
        });
      }
    },

    saveBlockEdit: async function (blockKey, items) {
      try {
        currentBMC = await apiRequest(`/startups/${currentStartupId}/bmc/blocks/${blockKey}`, {
          method: 'PUT',
          body: { items }
        });

        this.renderBMC(currentBMC);
        this.loadHistory();

        // Dependency Matrix Check
        const affected = DEPENDENCY_MATRIX[blockKey] || [];
        if (affected.length > 0) {
          this.promptDependencyCascade(blockKey, affected);
        }
      } catch (err) {
        alert('Error updating block: ' + (err.message || err));
      }
    },

    promptDependencyCascade: function (editedKey, affectedKeys) {
      const existing = document.getElementById('modal-dep-cascade');
      if (existing) existing.remove();

      const modalHtml = `
        <div class="bmc-dep-backdrop" id="modal-dep-cascade">
          <div class="bmc-dep-modal" style="position:relative;z-index:100000;">
            <h3 class="bmc-dep-title">⚡ Inter-Block Dependency Notice</h3>
            <p class="bmc-dep-desc">
              You edited <strong>${BLOCK_TITLES[editedKey]?.title}</strong>. According to business model logic, the following downstream blocks may be affected:
            </p>
            <div class="bmc-dep-list">
              ${affectedKeys.map(k => `
                <div class="bmc-dep-item">
                  <span>${BLOCK_TITLES[k]?.title}</span>
                  <button type="button" class="btn btn--outline bmc-btn-sm btn-cascade-edit" data-block="${k}">
                    ✏️ Edit ${BLOCK_TITLES[k]?.title}
                  </button>
                </div>
              `).join('')}
            </div>
            <div style="display:flex;justify-content:flex-end;">
              <button type="button" class="btn btn--primary" id="btn-close-dep-cascade">Keep Current Blocks</button>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);

      document.getElementById('btn-close-dep-cascade').addEventListener('click', () => {
        document.getElementById('modal-dep-cascade').remove();
      });

      document.querySelectorAll('.btn-cascade-edit').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const key = e.currentTarget.dataset.block;
          document.getElementById('modal-dep-cascade').remove();
          const rawObj = currentBMC.canvas_data ? currentBMC.canvas_data[key] : null;
          let items = [];
          if (Array.isArray(rawObj)) {
            items = rawObj;
          } else if (rawObj && typeof rawObj === 'object') {
            items = rawObj.items || [];
          }
          this.openEditModal(key, items);
        });
      });
    },

    openRegenBlockModal: function (blockKey) {
      const meta = BLOCK_TITLES[blockKey];
      const existingModal = document.getElementById('modal-regen-block-backdrop');
      if (existingModal) existingModal.remove();

      const modalHtml = `
        <div class="bmc-dep-backdrop" id="modal-regen-block-backdrop">
          <div class="bmc-dep-modal" style="position:relative;z-index:100000;">
            <h3 class="bmc-dep-title">🤖 AI Regenerate ${meta ? meta.title : blockKey}</h3>
            <p class="bmc-dep-desc">Optional custom instructions for AI (e.g. "Focus on B2B pricing model"):</p>
            <textarea id="regen-block-instructions" rows="4" class="workspace-form-group" style="width:100%;padding:12px;background:#131722;color:#FFF;border:1px solid rgba(99,102,241,0.3);border-radius:8px;font-family:inherit;font-size:0.9rem;line-height:1.5;box-sizing:border-box;resize:vertical;" placeholder="Leave empty for standard AI regeneration..."></textarea>
            <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px;">
              <button type="button" class="btn btn--outline" id="btn-cancel-regen-block">Cancel</button>
              <button type="button" class="btn btn--primary" id="btn-submit-regen-block">🔄 Regenerate Block</button>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);

      const backdrop = document.getElementById('modal-regen-block-backdrop');
      const cancelBtn = document.getElementById('btn-cancel-regen-block');
      const submitBtn = document.getElementById('btn-submit-regen-block');

      if (cancelBtn) cancelBtn.addEventListener('click', () => backdrop.remove());
      if (backdrop) backdrop.addEventListener('click', (e) => { if (e.target === backdrop) backdrop.remove(); });

      if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
          const textarea = document.getElementById('regen-block-instructions');
          const instructions = textarea ? textarea.value.trim() : '';
          backdrop.remove();
          await this.regenerateBlock(blockKey, instructions);
        });
      }
    },

    showToast: function (msg) {
      const old = document.querySelector('.vp-toast');
      if (old) old.remove();

      const toast = document.createElement('div');
      toast.className = 'vp-toast';
      toast.innerHTML = `<span>⚡</span> <span>${msg}</span>`;
      document.body.appendChild(toast);

      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s ease';
        setTimeout(() => toast.remove(), 500);
      }, 3500);
    },

    regenerateBlock: async function (blockKey, instructions) {
      const loading = document.getElementById('bmc-loading');
      const mainState = document.getElementById('bmc-main-state');

      if (loading) loading.style.display = 'block';
      if (mainState) mainState.style.display = 'none';

      try {
        currentBMC = await apiRequest(`/startups/${currentStartupId}/bmc/regenerate-block`, {
          method: 'POST',
          body: {
            block_name: blockKey,
            custom_instructions: instructions || null
          }
        });

        if (loading) loading.style.display = 'none';
        if (mainState) mainState.style.display = 'block';

        this.renderBMC(currentBMC);
        this.loadHistory();

        const card = document.querySelector(`.bmc-card[data-block="${blockKey}"]`);
        if (card) {
          card.scrollIntoView({ behavior: 'smooth', block: 'center' });
          card.classList.add('bmc-card--highlight');
          setTimeout(() => card.classList.remove('bmc-card--highlight'), 2600);
        }

        const title = BLOCK_TITLES[blockKey]?.title || blockKey;
        this.showToast(`${title} block regenerated successfully (v${currentBMC.version_number || currentBMC.version})!`);
      } catch (err) {
        if (loading) loading.style.display = 'none';
        if (mainState) mainState.style.display = 'block';
        alert('Block Regeneration Error: ' + (err.message || err));
      }
    },

    escapeHTML: function (str) {
      return (str || '').replace(/[&<>'"]/g, 
        tag => ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          "'": '&#39;',
          '"': '&quot;'
        }[tag] || tag)
      );
    }
  };

})();
