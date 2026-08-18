/* ==========================================================================
   VentureAI — pitch-deck.js
   Frontend application logic for AI Pitch Deck Generator:
   - Prerequisites checking & missing upstream data banner
   - Pitch deck generation & full regeneration
   - 13-slide presentation stage navigation (Prev, Next, Thumbnails, Keyboard)
   - Single slide editing (title, subtitle, content, key points)
   - Single slide AI regeneration with custom instructions
   - Red Pen Audit findings drawer
   - Low Validation Mode banner display
   - Version history modal & version switching
   - Document PDF Export via html2pdf.js
   ========================================================================== */

const PitchDeckApp = {
  startupId: null,
  currentStartup: null,
  currentDeck: null,
  currentSlideIndex: 0, // 0 to 12 (Slide 1 to 13)
  history: [],

  /* ---------------------------------------------------------
     1. Initialization
  --------------------------------------------------------- */
  init: async function () {
    // Wait for route-guard authentication check
    await new Promise(resolve => {
      let attempts = 0;
      const check = () => {
        if (document.body.classList.contains('route-verified')) resolve();
        else if (attempts > 60) resolve();
        else { attempts++; setTimeout(check, 50); }
      };
      check();
    });

    const urlParams = new URLSearchParams(window.location.search);
    this.startupId = urlParams.get('startup_id');

    if (!this.startupId) {
      try {
        const startup = await apiRequest('/startups/me');
        if (startup && startup.id) {
          this.startupId = startup.id;
          this.currentStartup = startup;
        }
      } catch (err) {
        this.renderEmptyState();
        return;
      }
    } else {
      try {
        this.currentStartup = await apiRequest(`/startups/${this.startupId}`);
      } catch (err) {
        console.warn('Could not load startup workspace details:', err);
      }
    }

    if (!this.startupId) return;

    // Check upstream prerequisites
    await this.checkPrerequisites();

    // Check if auto-generate requested via URL param
    if (urlParams.get('generate') === 'true') {
      await this.generateDeck();
    } else {
      await this.loadLatestDeck();
    }

    // Bind Keyboard navigation (Left / Right Arrow)
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        this.nextSlide();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        this.prevSlide();
      }
    });
  },

  /* ---------------------------------------------------------
     2. Prerequisites & Missing Data Banner
  --------------------------------------------------------- */
  checkPrerequisites: async function () {
    try {
      const status = await apiRequest(`/startups/${this.startupId}/pitch-deck/check-prerequisites`);
      const banner = document.getElementById('pd-prereq-banner');
      if (banner) {
        if (status.missing_message) {
          banner.style.display = 'flex';
          banner.innerHTML = `
            <span class="pd-alert-banner__icon">ℹ️</span>
            <div>${this.escapeHTML(status.missing_message)}</div>
          `;
        } else {
          banner.style.display = 'none';
        }
      }
    } catch (err) {
      console.warn('Could not verify pitch deck prerequisites:', err);
    }
  },

  /* ---------------------------------------------------------
     3. Load / Generate Deck
  --------------------------------------------------------- */
  loadLatestDeck: async function () {
    this.showLoading(true, 'Loading your pitch deck…');
    try {
      const deck = await apiRequest(`/startups/${this.startupId}/pitch-deck/latest`);
      this.currentDeck = deck;
      this.renderDeck();
      this.showLoading(false);
    } catch (err) {
      this.showLoading(false);
      // No deck generated yet — show empty generation CTA stage
      this.renderEmptyState();
    }
  },

  generateDeck: async function () {
    this.showLoading(true, 'Synthesizing your 13-slide investor pitch deck with AI…');
    try {
      const deck = await apiRequest(`/startups/${this.startupId}/pitch-deck/generate`, {
        method: 'POST',
      });
      this.currentDeck = deck;
      this.currentSlideIndex = 0;
      this.renderDeck();
      this.showLoading(false);
      this.showToast('13-slide pitch deck generated successfully!', 'success');
    } catch (err) {
      this.showLoading(false);
      this.showToast(err.message || 'Pitch deck generation failed.', 'error');
    }
  },

  regenerateFullDeck: async function () {
    if (!confirm('Regenerate entire 13-slide deck? This will save a new major version.')) return;
    this.showLoading(true, 'Regenerating full 13-slide pitch deck…');
    try {
      const deck = await apiRequest(`/pitch-deck/${this.currentDeck.id}/regenerate`, {
        method: 'POST',
      });
      this.currentDeck = deck;
      this.renderDeck();
      this.showLoading(false);
      this.showToast('Pitch deck regenerated as new version v' + deck.version_number + '.0!', 'success');
    } catch (err) {
      this.showLoading(false);
      this.showToast(err.message || 'Regeneration failed.', 'error');
    }
  },

  /* ---------------------------------------------------------
     4. Render Presentation Stage & Sidebar
  --------------------------------------------------------- */
  renderDeck: function () {
    if (!this.currentDeck || !this.currentDeck.slides_data) return;

    const slides = this.currentDeck.slides_data;
    const versionBadge = document.getElementById('pd-version-badge');
    if (versionBadge) {
      versionBadge.textContent = `v${this.currentDeck.version_number}.0`;
    }

    // Render Low Validation Mode Banner if validation_score < 50
    const valBanner = document.getElementById('pd-val-mode-banner');
    if (valBanner) {
      if (this.currentDeck.is_validation_mode) {
        const valScore = Math.round(this.currentDeck.validation_score || 42);
        valBanner.style.display = 'flex';
        valBanner.innerHTML = `
          <span class="pd-alert-banner__icon">⚠️</span>
          <div>
            <strong>Early-Stage Deck — Validation Score: ${valScore}/100</strong><br/>
            This deck is grounded in active validation risks and should not be treated as fully validated investment material.
          </div>
        `;
      } else {
        valBanner.style.display = 'none';
      }
    }

    // Render Sidebar Thumbnails
    const sidebarList = document.getElementById('pd-thumb-list');
    if (sidebarList) {
      sidebarList.innerHTML = slides.map((s, idx) => `
        <div class="pd-thumb-item ${idx === this.currentSlideIndex ? 'active' : ''}" onclick="PitchDeckApp.goToSlide(${idx})">
          <span class="pd-thumb-num">${s.slide_number < 10 ? '0' + s.slide_number : s.slide_number}</span>
          <div class="pd-thumb-info">
            <div class="pd-thumb-name">${this.escapeHTML(s.title)}</div>
            <div class="pd-thumb-type">${this.escapeHTML(s.slide_type || '')}</div>
          </div>
          ${s.warnings && s.warnings.length ? '<span class="pd-thumb-badge" title="Warning badge">⚠️</span>' : ''}
        </div>
      `).join('');
    }

    // Render Current Active Slide
    this.renderActiveSlide();

    // Render Red Pen Audit Drawer
    this.renderAuditReport();

    // Show workspace elements
    document.getElementById('pd-empty-state').style.display = 'none';
    document.getElementById('pd-workspace-grid').style.display = 'grid';
  },

  /* ---------------------------------------------------------
     Data Sanitizer & Component Layout Engine
  --------------------------------------------------------- */
  sanitizeText: function (input) {
    if (input === null || input === undefined) return '';

    if (typeof input === 'object') {
      if (Array.isArray(input)) {
        return input.map(item => this.sanitizeText(item)).filter(Boolean).join(' • ');
      }
      if (Array.isArray(input.items)) {
        return this.sanitizeText(input.items);
      }
      if (input.title || input.desc || input.label) {
        return [input.title, input.desc || input.label].filter(Boolean).join(': ');
      }
      const cleanVals = [];
      for (const [k, v] of Object.entries(input)) {
        if (['risk_notes', 'last_updated', 'generated_by_ai', 'modified_by_founder', 'id', 'created_at'].includes(k)) continue;
        if (v) cleanVals.push(this.sanitizeText(v));
      }
      return cleanVals.join(' • ');
    }

    if (typeof input === 'string') {
      let str = input.trim();

      if (str.includes('{') && str.includes('}')) {
        str = str.replace(/\{[^{}]*['"]items['"]\s*:\s*\[([^\]]+)\][^{}]*\}/gi, (match, itemsContent) => {
          const items = itemsContent.split(',').map(s => s.replace(/^['"\s]+|['"\s]+$/g, '')).filter(Boolean);
          return items.join(', ');
        });

        if (str.startsWith('{') && str.endsWith('}')) {
          try {
            let jsonStr = str.replace(/'/g, '"').replace(/\bNone\b/g, 'null').replace(/\bTrue\b/g, 'true').replace(/\bFalse\b/g, 'false');
            let parsed = JSON.parse(jsonStr);
            return this.sanitizeText(parsed);
          } catch (e) {
            str = str.replace(/'risk_notes':\s*None,?/gi, '')
                     .replace(/'last_updated':\s*'[^']+',?/gi, '')
                     .replace(/'generated_by_ai':\s*(True|False),?/gi, '')
                     .replace(/'modified_by_founder':\s*(True|False),?/gi, '')
                     .replace(/['"]items['"]:\s*/gi, '')
                     .replace(/[{}'"]/g, '');
          }
        }
      }

      str = str.replace(/'risk_notes':\s*None,?/gi, '')
               .replace(/'last_updated':\s*'[^']+',?/gi, '')
               .replace(/'generated_by_ai':\s*(True|False),?/gi, '')
               .replace(/'modified_by_founder':\s*(True|False),?/gi, '')
               .replace(/,\s*\./g, '.')
               .replace(/\s+/g, ' ');

      return str.trim();
    }

    return String(input);
  },

  parseHeroStat: function (text) {
    const clean = this.sanitizeText(text);
    if (!clean) return null;

    if (/^\d{4}-\d{2}-\d{2}/.test(clean) || /last_updated|created_at/i.test(clean)) {
      return null;
    }

    const match = clean.match(/(\$\d+(?:\.\d+)?[kMB]?|\d+(?:\.\d+)?%|\b\d+(?:\.\d+)?x\b|\b\d+s\b|\$\d+k?)/i);
    if (match && match[0] && match[0].length >= 2 && match[0].length <= 10) {
      const num = match[0];
      if (/^\d{4}$/.test(num)) {
        return null;
      }
      const label = clean.replace(num, '').replace(/^[:\-\s\•\(\)]+/, '').replace(/[\(\)]+$/, '').trim();
      if (label.length >= 3) {
        return { num, label };
      }
    }
    return null;
  },

  getLucideIconSVG: function (name, color = '#38BDF8', size = 20) {
    const n = (name || '').toLowerCase().replace(/[^a-z0-9-]/g, '');
    const svgOpen = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle;">`;
    const svgClose = `</svg>`;

    let inner = '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>';

    if (n.includes('shield') || n.includes('lock') || n.includes('moat') || n.includes('secu') || n.includes('defens')) {
      inner = '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>';
    } else if (n.includes('user') || n.includes('customer') || n.includes('people') || n.includes('team') || n.includes('ask')) {
      inner = '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>';
    } else if (n.includes('trend') || n.includes('growth') || n.includes('chart') || n.includes('up') || n.includes('unit') || n.includes('econ')) {
      inner = '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>';
    } else if (n.includes('data') || n.includes('server') || n.includes('layer') || n.includes('workflow') || n.includes('product')) {
      inner = '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>';
    } else if (n.includes('rocket') || n.includes('launch') || n.includes('speed') || n.includes('gtm') || n.includes('go-to')) {
      inner = '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-3.05 11a22.35 22.35 0 0 1-3.95 2z"/><path d="M9 20l-4 4"/><path d="M14.5 9.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>';
    } else if (n.includes('dollar') || n.includes('money') || n.includes('coin') || n.includes('rev') || n.includes('business') || n.includes('model') || n.includes('cost')) {
      inner = '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>';
    } else if (n.includes('award') || n.includes('star') || n.includes('trophy') || n.includes('crown') || n.includes('compet')) {
      inner = '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>';
    } else if (n.includes('check') || n.includes('valid') || n.includes('tract') || n.includes('done')) {
      inner = '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>';
    } else if (n.includes('target') || n.includes('aim') || n.includes('market') || n.includes('opp')) {
      inner = '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>';
    } else if (n.includes('zap') || n.includes('bolt') || n.includes('flash') || n.includes('speed')) {
      inner = '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>';
    } else if (n.includes('clock') || n.includes('time') || n.includes('why') || n.includes('now')) {
      inner = '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>';
    } else if (n.includes('light') || n.includes('bulb') || n.includes('solu') || n.includes('idea')) {
      inner = '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1.3.5 2.6 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>';
    } else if (n.includes('problem') || n.includes('alert') || n.includes('warn') || n.includes('issue')) {
      inner = '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>';
    } else if (n.includes('sparkle') || n.includes('gem') || n.includes('cover')) {
      inner = '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3z"/>';
    }

    return svgOpen + inner + svgClose;
  },

  renderCoverSlideHTML: function (slide, startupName, isPDFMode, title, subtitle, content, keyPoints) {
    const containerStyle = isPDFMode ? `
      width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden;
      background: radial-gradient(circle at 85% 15%, rgba(56, 189, 248, 0.15) 0%, transparent 55%),
                  radial-gradient(circle at 15% 85%, rgba(168, 85, 247, 0.12) 0%, transparent 55%), #151C2C;
      color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex; flex-direction: column;
      justify-content: space-between; page-break-after: always; break-after: page; page-break-inside: avoid; break-inside: avoid; margin: 0;
    ` : 'display:flex;flex-direction:column;justify-content:space-between;height:100%;box-sizing:border-box;overflow:hidden;';

    const kpCards = keyPoints.slice(0, 4).map(kp => {
      const stat = this.parseHeroStat(kp);
      const cleanKp = this.sanitizeText(kp);
      if (stat) {
        return `
          <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:6px;min-width:0;box-sizing:border-box;">
            <span style="font-size:1.8rem;font-weight:800;color:#38BDF8;letter-spacing:-0.02em;">${this.escapeHTML(stat.num)}</span>
            <span style="font-size:0.82rem;color:#94A3B8;line-height:1.35;word-break:break-word;">${this.escapeHTML(stat.label)}</span>
          </div>
        `;
      }
      return `
        <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;display:flex;align-items:flex-start;gap:10px;font-size:0.85rem;color:#E2E8F0;min-width:0;box-sizing:border-box;">
          <span style="margin-top:2px;">${this.getLucideIconSVG('sparkles', '#38BDF8', 16)}</span>
          <span style="word-break:break-word;overflow-wrap:break-word;">${this.escapeHTML(cleanKp)}</span>
        </div>
      `;
    }).join('');

    return `
      <div class="${isPDFMode ? 'pdf-slide-canvas pd-cover-canvas' : 'pd-stage-content pd-cover-canvas'}" style="${containerStyle}">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
              ${this.getLucideIconSVG('sparkles', '#38BDF8', 22)}
              <span>SLIDE 01 / 13</span>
            </span>
            <span style="background:rgba(56,189,248,0.12);color:#38BDF8;border:1px solid rgba(56,189,248,0.3);padding:4px 14px;border-radius:20px;font-size:0.75rem;font-weight:700;">
              INVESTOR PITCH DECK
            </span>
          </div>
          <div style="margin-bottom:20px;">
            <h1 style="font-size:2.2rem;font-weight:900;color:#FFF;line-height:1.15;margin:0 0 8px 0;letter-spacing:-0.02em;">${this.escapeHTML(title)}</h1>
            <div style="font-size:1.1rem;font-weight:600;color:#38BDF8;margin-bottom:14px;">${this.escapeHTML(subtitle)}</div>
            <div style="background:rgba(11,15,25,0.6);border:1px solid #232D42;border-radius:14px;padding:16px 20px;font-size:0.95rem;line-height:1.55;color:#CBD5E1;max-height:80px;overflow:hidden;word-break:break-word;">
              ${this.escapeHTML(content)}
            </div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(4, minmax(0, 1fr));gap:12px;width:100%;box-sizing:border-box;">
            ${kpCards}
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
          <span>VentureAI AI Pitch Deck Generator</span>
          <span>${this.escapeHTML(startupName)}</span>
        </div>
      </div>
    `;
  },

  renderWorkflowPipelineHTML: function (slide, startupName, isPDFMode, title, subtitle, content, keyPoints) {
    const containerStyle = isPDFMode ? `
      width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden;
      background: #151C2C; color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex;
      flex-direction: column; justify-content: space-between; page-break-after: always; break-after: page;
      page-break-inside: avoid; break-inside: avoid; margin: 0;
    ` : 'display:flex;flex-direction:column;justify-content:space-between;height:100%;box-sizing:border-box;overflow:hidden;';

    let steps = [
      { step: 1, title: 'Context Ingestion', desc: 'Securely ingests startup profile & validation data.' },
      { step: 2, title: 'AI Engine Execution', desc: 'Runs multi-agent Zero-Trust compliance & risk scoring.' },
      { step: 3, title: 'Audit & Output', desc: 'Generates investor-ready presentation decks in seconds.' }
    ];

    if (slide.visual_data && Array.isArray(slide.visual_data.steps) && slide.visual_data.steps.length) {
      steps = slide.visual_data.steps.slice(0, 3).map(st => ({
        step: st.step || st.step_number || 1,
        title: this.sanitizeText(st.title || st.step_title || 'Step'),
        desc: this.sanitizeText(st.desc || st.description || st.content || '')
      }));
    }

    const pipelineCardsHtml = steps.map((st, i) => `
      <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;text-align:center;position:relative;min-width:0;box-sizing:border-box;">
        <div style="width:30px;height:30px;border-radius:50%;background:#38BDF8;color:#0B0F19;font-weight:900;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:0.85rem;">${st.step}</div>
        <div style="font-weight:700;color:#FFF;margin-bottom:4px;font-size:0.9rem;word-break:break-word;">${this.escapeHTML(st.title)}</div>
        <div style="font-size:0.8rem;color:#94A3B8;line-height:1.35;word-break:break-word;">${this.escapeHTML(st.desc)}</div>
      </div>
      ${i < steps.length - 1 ? '<div style="color:#38BDF8;font-size:1.4rem;font-weight:800;text-align:center;align-self:center;">➔</div>' : ''}
    `).join('');

    return `
      <div class="${isPDFMode ? 'pdf-slide-canvas' : 'pd-stage-content'}" style="${containerStyle}">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
              ${this.getLucideIconSVG('database', '#38BDF8', 22)}
              <span>SLIDE 06 / 13</span>
            </span>
            <span style="background:rgba(255,255,255,0.06);color:#CBD5E1;padding:4px 12px;border-radius:12px;font-size:0.75rem;font-weight:600;">
              PRODUCT WORKFLOW
            </span>
          </div>
          <h2 style="font-size:1.8rem;font-weight:800;color:#FFF;line-height:1.2;margin:0 0 4px 0;">${this.escapeHTML(title)}</h2>
          <h3 style="font-size:1rem;font-weight:500;color:#94A3B8;margin:0 0 12px 0;line-height:1.35;">${this.escapeHTML(subtitle)}</h3>
          <p style="font-size:0.92rem;line-height:1.5;color:#E2E8F0;margin-bottom:16px;max-height:64px;overflow:hidden;word-break:break-word;">${this.escapeHTML(content)}</p>

          <div style="background:#151C2C;border:1px solid #232D42;border-radius:14px;padding:18px;margin-bottom:16px;width:100%;box-sizing:border-box;">
            <div style="display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:12px;width:100%;box-sizing:border-box;">
              ${pipelineCardsHtml}
            </div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
          <span>VentureAI AI Pitch Deck Generator</span>
          <span>${this.escapeHTML(startupName)}</span>
        </div>
      </div>
    `;
  },

  renderMetricStatSlideHTML: function (slide, startupName, isPDFMode, title, subtitle, content, keyPoints) {
    const sNum = slide.slide_number || 5;
    const sNumStr = sNum < 10 ? '0' + sNum : sNum;
    const sTypeUpper = (slide.slide_type || 'METRICS').toUpperCase();
    const iconSVG = this.getLucideIconSVG(slide.slide_type || 'trending-up', '#38BDF8', 22);

    const containerStyle = isPDFMode ? `
      width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden;
      background: #151C2C; color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex;
      flex-direction: column; justify-content: space-between; page-break-after: ${sNum === 13 ? 'avoid' : 'always'};
      break-after: ${sNum === 13 ? 'avoid' : 'page'}; page-break-inside: avoid; break-inside: avoid; margin: 0;
    ` : 'display:flex;flex-direction:column;justify-content:space-between;height:100%;box-sizing:border-box;overflow:hidden;';

    const statCardsHtml = keyPoints.slice(0, 4).map(kp => {
      const stat = this.parseHeroStat(kp);
      const cleanKp = this.sanitizeText(kp);
      if (stat) {
        return `
          <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:4px;min-width:0;box-sizing:border-box;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:1.9rem;font-weight:800;color:#38BDF8;letter-spacing:-0.02em;line-height:1;">${this.escapeHTML(stat.num)}</span>
              <span>${this.getLucideIconSVG(slide.slide_type || 'trending-up', '#38BDF8', 18)}</span>
            </div>
            <p style="font-size:0.82rem;color:#94A3B8;line-height:1.35;margin:0;font-weight:500;word-break:break-word;">${this.escapeHTML(stat.label)}</p>
          </div>
        `;
      }
      return `
        <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;display:flex;align-items:flex-start;gap:10px;font-size:0.86rem;color:#E2E8F0;min-width:0;box-sizing:border-box;">
          <span style="margin-top:2px;">${this.getLucideIconSVG('check-circle', '#38BDF8', 18)}</span>
          <span style="word-break:break-word;overflow-wrap:break-word;">${this.escapeHTML(cleanKp)}</span>
        </div>
      `;
    }).join('');

    return `
      <div class="${isPDFMode ? 'pdf-slide-canvas' : 'pd-stage-content'}" style="${containerStyle}">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
              ${iconSVG}
              <span>SLIDE ${sNumStr} / 13</span>
            </span>
            <span style="background:rgba(255,255,255,0.06);color:#CBD5E1;padding:4px 12px;border-radius:12px;font-size:0.75rem;font-weight:600;">
              ${this.escapeHTML(sTypeUpper)}
            </span>
          </div>
          <h2 style="font-size:1.8rem;font-weight:800;color:#FFF;line-height:1.2;margin:0 0 4px 0;">${this.escapeHTML(title)}</h2>
          <h3 style="font-size:1rem;font-weight:500;color:#94A3B8;margin:0 0 12px 0;line-height:1.35;">${this.escapeHTML(subtitle)}</h3>
          <p style="font-size:0.92rem;line-height:1.5;color:#94A3B8;margin-bottom:16px;max-height:72px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;word-break:break-word;">${this.escapeHTML(content)}</p>

          <div style="display:grid;grid-template-columns:repeat(4, minmax(0, 1fr));gap:12px;margin-bottom:16px;width:100%;box-sizing:border-box;">
            ${statCardsHtml}
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
          <span>VentureAI AI Pitch Deck Generator</span>
          <span>${this.escapeHTML(startupName)}</span>
        </div>
      </div>
    `;
  },

  renderStandardCardSlideHTML: function (slide, startupName, isPDFMode, title, subtitle, content, keyPoints) {
    const sNum = slide.slide_number || 2;
    const sNumStr = sNum < 10 ? '0' + sNum : sNum;
    const sTypeUpper = (slide.slide_type || 'SLIDE').toUpperCase();
    const iconSVG = this.getLucideIconSVG(slide.slide_type || slide.icon_name || 'sparkles', '#38BDF8', 22);

    let warningBadgeHtml = '';
    if (slide.warnings && slide.warnings.length) {
      warningBadgeHtml = `
        <div style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);color:#FCD34D;padding:6px 12px;border-radius:10px;font-size:0.82rem;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
          ${this.getLucideIconSVG('alert-triangle', '#FCD34D', 14)}
          <span style="word-break:break-word;">${this.escapeHTML(this.sanitizeText(slide.warnings[0]))}</span>
        </div>
      `;
    }

    const containerStyle = isPDFMode ? `
      width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden;
      background: #151C2C; color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex;
      flex-direction: column; justify-content: space-between; page-break-after: ${sNum === 13 ? 'avoid' : 'always'};
      break-after: ${sNum === 13 ? 'avoid' : 'page'}; page-break-inside: avoid; break-inside: avoid; margin: 0;
    ` : 'display:flex;flex-direction:column;justify-content:space-between;height:100%;box-sizing:border-box;overflow:hidden;';

    const cardGridHtml = keyPoints.slice(0, 4).map(kp => {
      const stat = this.parseHeroStat(kp);
      const cleanKp = this.sanitizeText(kp);
      if (stat) {
        return `
          <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:4px;min-width:0;box-sizing:border-box;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:1.9rem;font-weight:800;color:#38BDF8;letter-spacing:-0.02em;">${this.escapeHTML(stat.num)}</span>
              <span>${this.getLucideIconSVG(slide.slide_type || 'check-circle', '#38BDF8', 16)}</span>
            </div>
            <p style="font-size:0.82rem;color:#94A3B8;line-height:1.35;margin:0;word-break:break-word;">${this.escapeHTML(stat.label)}</p>
          </div>
        `;
      }
      return `
        <div style="background:#0E172A;border:1px solid #1E293B;border-radius:12px;padding:16px;display:flex;align-items:flex-start;gap:10px;font-size:0.86rem;color:#F1F5F9;line-height:1.4;min-width:0;box-sizing:border-box;">
          <span style="margin-top:2px;">${this.getLucideIconSVG(slide.slide_type || 'check-circle', '#38BDF8', 16)}</span>
          <span style="word-break:break-word;overflow-wrap:break-word;">${this.escapeHTML(cleanKp)}</span>
        </div>
      `;
    }).join('');

    return `
      <div class="${isPDFMode ? 'pdf-slide-canvas' : 'pd-stage-content'}" style="${containerStyle}">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
              ${iconSVG}
              <span>SLIDE ${sNumStr} / 13</span>
            </span>
            <span style="background:rgba(255,255,255,0.06);color:#CBD5E1;padding:4px 12px;border-radius:12px;font-size:0.75rem;font-weight:600;">
              ${this.escapeHTML(sTypeUpper)}
            </span>
          </div>
          <h2 style="font-size:1.8rem;font-weight:800;color:#FFF;line-height:1.2;margin:0 0 4px 0;">${this.escapeHTML(title)}</h2>
          <h3 style="font-size:1rem;font-weight:500;color:#94A3B8;margin:0 0 12px 0;line-height:1.35;">${this.escapeHTML(subtitle)}</h3>
          ${warningBadgeHtml}
          <div style="font-size:0.92rem;line-height:1.5;color:#94A3B8;margin-bottom:16px;max-height:72px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;word-break:break-word;">${this.escapeHTML(content)}</div>

          <div style="display:grid;grid-template-columns:repeat(4, minmax(0, 1fr));gap:12px;margin-bottom:16px;width:100%;box-sizing:border-box;">
            ${cardGridHtml}
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
          <span>VentureAI AI Pitch Deck Generator</span>
          <span>${this.escapeHTML(startupName)}</span>
        </div>
      </div>
    `;
  },

  renderSlideHTML: function (slide, startupName = 'Startup Workspace', isPDFMode = false) {
    const sNum = slide.slide_number || 1;
    const cleanTitle = this.sanitizeText(slide.title);
    const cleanSubtitle = this.sanitizeText(slide.subtitle);
    const cleanContent = this.sanitizeText(slide.content);
    const rawKeyPoints = slide.key_points || [];

    if (sNum === 1 || slide.slide_type === 'cover') {
      return this.renderCoverSlideHTML(slide, startupName, isPDFMode, cleanTitle, cleanSubtitle, cleanContent, rawKeyPoints);
    }
    if (sNum === 6 || slide.slide_type === 'product_workflow' || slide.visual_type === 'three_step_flow') {
      return this.renderWorkflowPipelineHTML(slide, startupName, isPDFMode, cleanTitle, cleanSubtitle, cleanContent, rawKeyPoints);
    }
    if ([5, 11, 12, 13].includes(sNum) || slide.visual_type === 'metrics_grid') {
      return this.renderMetricStatSlideHTML(slide, startupName, isPDFMode, cleanTitle, cleanSubtitle, cleanContent, rawKeyPoints);
    }
    return this.renderStandardCardSlideHTML(slide, startupName, isPDFMode, cleanTitle, cleanSubtitle, cleanContent, rawKeyPoints);
  },

  renderActiveSlide: function () {
    const slides = this.currentDeck.slides_data;
    if (this.currentSlideIndex < 0) this.currentSlideIndex = 0;
    if (this.currentSlideIndex >= slides.length) this.currentSlideIndex = slides.length - 1;

    const slide = slides[this.currentSlideIndex];
    const stage = document.getElementById('pd-stage');
    const counter = document.getElementById('pd-counter');

    if (counter) {
      counter.textContent = `${slide.slide_number} / ${slides.length}`;
    }

    const startupName = this.currentStartup ? this.currentStartup.name : 'Startup Workspace';
    stage.innerHTML = this.renderSlideHTML(slide, startupName, false);

    // Highlight active thumbnail item
    const items = document.querySelectorAll('.pd-thumb-item');
    items.forEach((it, i) => {
      it.classList.toggle('active', i === this.currentSlideIndex);
    });
  },

  renderEmptyState: function () {
    document.getElementById('pd-empty-state').style.display = 'block';
    document.getElementById('pd-workspace-grid').style.display = 'none';
  },

  /* ---------------------------------------------------------
     5. Slide Navigation
  --------------------------------------------------------- */
  goToSlide: function (index) {
    if (index >= 0 && index < this.currentDeck.slides_data.length) {
      this.currentSlideIndex = index;
      this.renderActiveSlide();
    }
  },

  nextSlide: function () {
    if (this.currentDeck && this.currentSlideIndex < this.currentDeck.slides_data.length - 1) {
      this.currentSlideIndex++;
      this.renderActiveSlide();
    }
  },

  prevSlide: function () {
    if (this.currentDeck && this.currentSlideIndex > 0) {
      this.currentSlideIndex--;
      this.renderActiveSlide();
    }
  },

  /* ---------------------------------------------------------
     6. Single Slide Editing
  --------------------------------------------------------- */
  openEditModal: function () {
    if (!this.currentDeck) return;
    const slide = this.currentDeck.slides_data[this.currentSlideIndex];
    document.getElementById('edit-slide-num').textContent = slide.slide_number;
    document.getElementById('edit-title').value = slide.title || '';
    document.getElementById('edit-subtitle').value = slide.subtitle || '';
    document.getElementById('edit-content').value = slide.content || '';
    document.getElementById('edit-keypoints').value = (slide.key_points || []).join('\n');

    document.getElementById('pd-edit-modal').classList.add('open');
  },

  closeEditModal: function () {
    document.getElementById('pd-edit-modal').classList.remove('open');
  },

  saveEditSlide: async function () {
    const slideNumber = this.currentDeck.slides_data[this.currentSlideIndex].slide_number;
    const title = document.getElementById('edit-title').value.trim();
    const subtitle = document.getElementById('edit-subtitle').value.trim();
    const content = document.getElementById('edit-content').value.trim();
    const kpsRaw = document.getElementById('edit-keypoints').value;
    const key_points = kpsRaw.split('\n').map(s => s.trim()).filter(s => s.length > 0);

    this.showLoading(true, 'Saving slide edits…');
    this.closeEditModal();

    try {
      const updatedDeck = await apiRequest(`/pitch-deck/${this.currentDeck.id}/slides/${slideNumber}`, {
        method: 'PATCH',
        body: { title, subtitle, content, key_points },
      });
      this.currentDeck = updatedDeck;
      this.renderDeck();
      this.showLoading(false);
      this.showToast(`Slide ${slideNumber} updated successfully!`, 'success');
    } catch (err) {
      this.showLoading(false);
      this.showToast(err.message || 'Failed to edit slide.', 'error');
    }
  },

  /* ---------------------------------------------------------
     7. Single Slide AI Regeneration
  --------------------------------------------------------- */
  openRegenModal: function () {
    if (!this.currentDeck) return;
    const slide = this.currentDeck.slides_data[this.currentSlideIndex];
    document.getElementById('regen-slide-num').textContent = slide.slide_number;
    document.getElementById('regen-instructions').value = '';
    document.getElementById('pd-regen-modal').classList.add('open');
  },

  closeRegenModal: function () {
    document.getElementById('pd-regen-modal').classList.remove('open');
  },

  confirmRegenSlide: async function () {
    const slideNumber = this.currentDeck.slides_data[this.currentSlideIndex].slide_number;
    const custom_instructions = document.getElementById('regen-instructions').value.trim();

    this.showLoading(true, `Regenerating Slide ${slideNumber} with AI…`);
    this.closeRegenModal();

    try {
      const updatedDeck = await apiRequest(`/pitch-deck/${this.currentDeck.id}/slides/${slideNumber}/regenerate`, {
        method: 'POST',
        body: { custom_instructions },
      });
      this.currentDeck = updatedDeck;
      this.renderDeck();
      this.showLoading(false);
      this.showToast(`Slide ${slideNumber} regenerated and audited!`, 'success');
    } catch (err) {
      this.showLoading(false);
      this.showToast(err.message || 'Slide regeneration failed.', 'error');
    }
  },

  /* ---------------------------------------------------------
     8. Red Pen Auditor Findings
  --------------------------------------------------------- */
  renderAuditReport: function () {
    const auditDrawer = document.getElementById('pd-audit-drawer');
    if (!auditDrawer || !this.currentDeck || !this.currentDeck.audit_report) return;

    const report = this.currentDeck.audit_report;
    const health = report.health_score ?? 100;
    const warnings = report.warnings || [];

    let healthClass = 'pd-health-score--high';
    if (health < 70) healthClass = 'pd-health-score--low';
    else if (health < 85) healthClass = 'pd-health-score--mid';

    const warningsHtml = warnings.map(w => `
      <div class="pd-audit-warning-item pd-audit-warning-item--${w.severity}">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="pd-warning-cat">${this.escapeHTML(w.category)} ${w.slide_number ? '(Slide ' + w.slide_number + ')' : ''}</span>
          <span style="font-size:0.75rem;font-weight:700;color:${w.severity === 'HIGH' ? '#EF4444' : '#F59E0B'};">${w.severity}</span>
        </div>
        <div class="pd-warning-issue">${this.escapeHTML(w.issue)}</div>
        ${w.recommended_fix ? `<div class="pd-warning-fix">💡 Recommendation: ${this.escapeHTML(w.recommended_fix)}</div>` : ''}
      </div>
    `).join('');

    auditDrawer.innerHTML = `
      <div class="pd-audit-header">
        <div class="pd-audit-title">
          <span>🔍</span>
          <span>Red Pen Auditor Consistency Report</span>
        </div>
        <span class="pd-health-score ${healthClass}">Audit Health: ${health}/100</span>
      </div>
      <div class="pd-audit-warning-list">
        ${warnings.length > 0 ? warningsHtml : '<div style="color:#4ADE80;font-size:0.9rem;">✅ Zero consistency warnings detected across all 13 slides.</div>'}
      </div>
    `;
  },

  /* ---------------------------------------------------------
     9. Version History Modal
  --------------------------------------------------------- */
  openHistoryModal: async function () {
    try {
      const versions = await apiRequest(`/startups/${this.startupId}/pitch-deck/versions`);
      this.history = versions;
      const listEl = document.getElementById('pd-history-list');
      if (listEl) {
        listEl.innerHTML = versions.map(v => `
          <div class="pd-thumb-item ${v.version_number === this.currentDeck.version_number ? 'active' : ''}"
               onclick="PitchDeckApp.loadDeckVersion(${v.id})">
            <span class="pd-thumb-num">v${v.version_number}</span>
            <div class="pd-thumb-info">
              <div class="pd-thumb-name">Version ${v.version_number}.0</div>
              <div class="pd-thumb-type">${new Date(v.created_at).toLocaleDateString()} ${v.is_validation_mode ? '• Low Validation Mode' : ''}</div>
            </div>
            <span>${v.version_number === this.currentDeck.version_number ? 'Active' : 'Load'}</span>
          </div>
        `).join('');
      }
      document.getElementById('pd-history-modal').classList.add('open');
    } catch (err) {
      this.showToast('Could not load version history.', 'error');
    }
  },

  closeHistoryModal: function () {
    document.getElementById('pd-history-modal').classList.remove('open');
  },

  loadDeckVersion: async function (deckId) {
    this.closeHistoryModal();
    this.showLoading(true, 'Loading pitch deck version…');
    try {
      const deck = await apiRequest(`/pitch-deck/${deckId}`);
      this.currentDeck = deck;
      this.currentSlideIndex = 0;
      this.renderDeck();
      this.showLoading(false);
      this.showToast(`Loaded Pitch Deck v${deck.version_number}.0`, 'success');
    } catch (err) {
      this.showLoading(false);
      this.showToast('Failed to load version.', 'error');
    }
  },

  /* ---------------------------------------------------------
     10. Export PDF
  --------------------------------------------------------- */
  /* ---------------------------------------------------------
     10. High-DPI 16:9 Full-Bleed PDF Export (jsPDF + html-to-image)
  --------------------------------------------------------- */
  exportPDF: async function () {
    if (!this.currentDeck || !this.currentDeck.slides_data) return;
    const startupName = this.currentStartup ? this.currentStartup.name : 'Startup Workspace';
    const sanitizedName = startupName.replace(/[^a-zA-Z0-9_-]/g, '_');

    this.showLoading(true, 'Rendering 100% full-bleed 16:9 PDF slides…');
    this.showToast('Generating high-DPI PDF document…', 'info');

    // 1. Off-screen container mounting all 13 slides at fixed 1920x1080 resolution
    const exportContainer = document.createElement('div');
    exportContainer.id = 'pdf-offscreen-export-container';
    exportContainer.style.position = 'fixed';
    exportContainer.style.top = '-99999px';
    exportContainer.style.left = '-99999px';
    exportContainer.style.width = '1920px';
    exportContainer.style.pointerEvents = 'none';
    exportContainer.style.zIndex = '-1';

    let slidesHtml = '';
    const slides = this.currentDeck.slides_data;

    slides.forEach((slide) => {
      slidesHtml += `
        <div class="pitch-slide-canvas">
          ${this.renderSlideHTML(slide, startupName, false)}
        </div>
      `;
    });

    exportContainer.innerHTML = slidesHtml;
    document.body.appendChild(exportContainer);

    try {
      const slideNodes = Array.from(exportContainer.querySelectorAll('.pitch-slide-canvas'));
      if (!slideNodes.length) throw new Error('No slide nodes found for PDF export.');

      // 2. Initialize jsPDF in Landscape mode with exact 1920x1080 dimensions
      const { jsPDF } = window.jspdf || {};
      if (!jsPDF) {
        throw new Error('jsPDF library not loaded');
      }

      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'px',
        format: [1920, 1080],
        hotfixes: ['px_scaling'],
      });

      const totalSlides = slideNodes.length;

      for (let index = 0; index < totalSlides; index++) {
        const slideEl = slideNodes[index];
        this.showLoading(true, `Capturing Slide ${index + 1} of ${totalSlides} for PDF…`);

        let imgDataUrl = '';
        if (window.htmlToImage) {
          imgDataUrl = await window.htmlToImage.toPng(slideEl, {
            pixelRatio: 2,
            quality: 0.95,
            cacheBust: true,
            canvasWidth: 1920,
            canvasHeight: 1080,
            style: {
              width: '1920px',
              height: '1080px',
              maxWidth: '1920px',
              maxHeight: '1080px',
              transform: 'none',
            },
          });
        } else if (window.html2canvas) {
          const canvas = await window.html2canvas(slideEl, {
            scale: 2,
            backgroundColor: '#151C2C',
            width: 1920,
            height: 1080,
          });
          imgDataUrl = canvas.toDataURL('image/png');
        } else {
          throw new Error('No DOM capture engine available');
        }

        if (index > 0) {
          pdf.addPage([1920, 1080], 'landscape');
        }

        pdf.addImage(imgDataUrl, 'PNG', 0, 0, 1920, 1080, undefined, 'FAST');
      }

      pdf.save(`${sanitizedName}_PitchDeck.pdf`);
      this.showToast('13-Slide Full-Bleed PDF Export complete!', 'success');
    } catch (err) {
      console.error('PDF Export Error:', err);
      this.showToast('PDF Export failed. Opening fallback printable view…', 'error');
      window.open(`${API_BASE_URL}/pitch-deck/${this.currentDeck.id}/export/pdf`, '_blank');
    } finally {
      if (document.body.contains(exportContainer)) {
        document.body.removeChild(exportContainer);
      }
      this.showLoading(false);
    }
  },

  /* ---------------------------------------------------------
     11. Export PowerPoint (.pptx)
  --------------------------------------------------------- */
  exportPPTX: async function () {
    if (!this.currentDeck || !this.currentDeck.slides_data) return;
    const startupName = this.currentStartup ? this.currentStartup.name : 'Startup Workspace';
    const cleanFilename = startupName.replace(/[^a-zA-Z0-9_-]/g, '_');

    if (!window.PptxGenJS) {
      window.open(`${API_BASE_URL}/pitch-deck/${this.currentDeck.id}/export/pptx`, '_blank');
      return;
    }

    this.showLoading(true, 'Rendering 100% visual-parity 16:9 PPTX slides…');
    this.showToast('Generating PowerPoint presentation (.pptx)…', 'info');

    // 1. Create hidden off-screen export container (1280px x 720px 16:9 standard slides)
    const exportContainer = document.createElement('div');
    exportContainer.id = 'pptx-export-deck-container';
    exportContainer.style.position = 'absolute';
    exportContainer.style.left = '-99999px';
    exportContainer.style.top = '0';
    exportContainer.style.width = '1280px';
    exportContainer.style.background = '#0F172A';
    exportContainer.style.color = '#F8FAFC';
    exportContainer.style.margin = '0';
    exportContainer.style.padding = '0';
    exportContainer.style.boxSizing = 'border-box';
    exportContainer.style.pointerEvents = 'none';

    let slidesHtml = '';
    const slides = this.currentDeck.slides_data;

    slides.forEach((slide) => {
      slidesHtml += `
        <div class="export-slide-node" style="width:1280px;height:720px;max-height:720px;box-sizing:border-box;overflow:hidden;background:#151C2C;color:#F8FAFC;padding:36px 48px;position:relative;display:flex;flex-direction:column;justify-content:space-between;margin-bottom:20px;">
          ${this.renderSlideHTML(slide, startupName, false)}
        </div>
      `;
    });

    exportContainer.innerHTML = slidesHtml;
    document.body.appendChild(exportContainer);

    try {
      const slideNodes = exportContainer.querySelectorAll('.export-slide-node');
      const pptx = new window.PptxGenJS();
      pptx.layout = 'LAYOUT_16x9';
      pptx.author = 'VentureAI AI Pitch Deck Generator';
      pptx.company = startupName;
      pptx.title = `${startupName} — Pitch Deck v${this.currentDeck.version_number}.0`;

      for (let i = 0; i < slideNodes.length; i++) {
        const node = slideNodes[i];
        this.showLoading(true, `Capturing Slide ${i + 1} of ${slideNodes.length} for PPTX…`);

        let imgDataUrl = '';
        if (window.htmlToImage) {
          imgDataUrl = await window.htmlToImage.toPng(node, {
            pixelRatio: 2,
            quality: 0.98,
            cacheBust: true,
            backgroundColor: '#151C2C',
            width: 1280,
            height: 720
          });
        } else if (window.html2canvas) {
          const canvas = await window.html2canvas(node, {
            scale: 2,
            backgroundColor: '#151C2C',
            width: 1280,
            height: 720
          });
          imgDataUrl = canvas.toDataURL('image/png');
        } else {
          throw new Error('No DOM capture library available');
        }

        const pptSlide = pptx.addSlide();
        pptSlide.addImage({
          data: imgDataUrl,
          x: 0,
          y: 0,
          w: '100%',
          h: '100%'
        });
      }

      await pptx.writeFile({ fileName: `${cleanFilename}_Pitch_Deck.pptx` });
      this.showToast('100% Visual-Parity PowerPoint (.pptx) Export complete!', 'success');
    } catch (err) {
      console.error('PPTX export error:', err);
      this.showToast('PPTX export error. Falling back to server export…', 'error');
      window.open(`${API_BASE_URL}/pitch-deck/${this.currentDeck.id}/export/pptx`, '_blank');
    } finally {
      if (document.body.contains(exportContainer)) {
        document.body.removeChild(exportContainer);
      }
      this.showLoading(false);
    }
  },

  /* ---------------------------------------------------------
     Helpers
  --------------------------------------------------------- */
  showLoading: function (show, text = 'Loading…') {
    const el = document.getElementById('pd-loading');
    const msg = document.getElementById('pd-loading-text');
    if (el) el.style.display = show ? 'flex' : 'none';
    if (msg) msg.textContent = text;
  },

  showToast: function (text, type = 'info') {
    const toast = document.getElementById('pd-toast');
    if (!toast) return;
    toast.textContent = text;
    toast.className = `pd-toast pd-toast--${type} show`;
    setTimeout(() => { toast.classList.remove('show'); }, 3000);
  },

  escapeHTML: function (str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  PitchDeckApp.init();
});
