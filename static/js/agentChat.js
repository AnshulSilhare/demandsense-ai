/**
 * DemandSense AI — Autonomous Agent Chat Controller
 * ====================================================
 * Manages the floating AI assistant drawer, ReAct reasoning trace viewer,
 * Multi-Agent War Room, Scenario Copilot, and Live Sentinel monitoring.
 *
 * Author: Anshul Silhare
 */

(function () {
  'use strict';

  // ── DOM Elements ──
  // ── FMCG 20-Product Catalog ──
  const FMCG_CATALOG = [
    { id: 'SKU001', name: 'Premium Detergent 1kg', category: 'Home Care', icon: '🧼' },
    { id: 'SKU002', name: 'Instant Noodles 4-Pack', category: 'Packaged Food', icon: '🍜' },
    { id: 'SKU003', name: 'Fresh Butter 500g', category: 'Dairy', icon: '🧈' },
    { id: 'SKU004', name: 'Iodized Salt 1kg', category: 'Staples', icon: '🧂' },
    { id: 'SKU005', name: 'Glucose Biscuits 800g', category: 'Packaged Food', icon: '🍪' },
    { id: 'SKU006', name: 'Pure Honey 500g', category: 'Health Foods', icon: '🍯' },
    { id: 'SKU007', name: 'Traditional Namkeen 400g', category: 'Snacks', icon: '🥨' },
    { id: 'SKU008', name: 'Mango Juice 1L', category: 'Beverages', icon: '🧃' },
    { id: 'SKU009', name: 'Coconut Hair Oil 200ml', category: 'Personal Care', icon: '🧴' },
    { id: 'SKU010', name: 'Dishwash Liquid 500ml', category: 'Home Care', icon: '🍽️' },
    { id: 'SKU011', name: 'Basmati Rice 5kg', category: 'Staples', icon: '🍚' },
    { id: 'SKU012', name: 'Sunflower Oil 1L', category: 'Cooking Oils', icon: '🌻' },
    { id: 'SKU013', name: 'Green Tea 100 Bags', category: 'Beverages', icon: '🍵' },
    { id: 'SKU014', name: 'Face Wash 100ml', category: 'Personal Care', icon: '🫧' },
    { id: 'SKU015', name: 'Premium Chips 150g', category: 'Snacks', icon: '🥔' },
    { id: 'SKU016', name: 'Chyawanprash 500g', category: 'Health Foods', icon: '🌿' },
    { id: 'SKU017', name: 'Tomato Ketchup 500g', category: 'Packaged Food', icon: '🍅' },
    { id: 'SKU018', name: 'Floor Cleaner 1L', category: 'Home Care', icon: '🧹' },
    { id: 'SKU019', name: 'Chocolate Bar 50g', category: 'Confectionery', icon: '🍫' },
    { id: 'SKU020', name: 'Mosquito Repellent 45ml', category: 'Home Care', icon: '🦟' },
  ];

  let chatFab = null;
  let chatPanel = null;
  let chatOverlay = null;
  let chatCloseBtn = null;
  let chatExpandBtn = null;
  let chatResetBtn = null;
  let chatMessages = null;
  let chatInput = null;
  let chatSendBtn = null;
  let chatChipsContainer = null;
  let isSending = false;
  let tab6Messages = null;
  let tab6Input = null;
  let tab6SendBtn = null;
  let tab6ChipsContainer = null;

  // ── Initialize on DOMContentLoaded ──
  document.addEventListener('DOMContentLoaded', () => {
    initChatElements();
    initChatEventListeners();
    renderWelcomeMessage();
    setupAgentSubNav();
    startAutonomousMonitoring();
  });

  function initChatElements() {
    chatFab = document.getElementById('aiChatFab');
    chatPanel = document.getElementById('aiChatPanel');
    chatOverlay = document.getElementById('aiChatOverlay');
    chatCloseBtn = document.getElementById('aiChatClose');
    chatExpandBtn = document.getElementById('aiChatExpand');
    chatResetBtn = document.getElementById('aiChatReset');
    chatMessages = document.getElementById('aiChatMessages');
    chatInput = document.getElementById('aiChatInput');
    chatSendBtn = document.getElementById('aiChatSend');
    chatChipsContainer = document.getElementById('aiChatChips');

    // Tab 6 Dual-Surface Elements
    tab6Messages = document.getElementById('tab6Messages');
    tab6Input = document.getElementById('tab6Input');
    tab6SendBtn = document.getElementById('tab6Send');
    tab6ChipsContainer = document.getElementById('tab6Chips');
  }

  function initChatEventListeners() {
    if (chatFab) {
      chatFab.addEventListener('click', () => toggleChatPanel(true));
    }
    if (chatCloseBtn) {
      chatCloseBtn.addEventListener('click', () => toggleChatPanel(false));
    }
    if (chatExpandBtn) {
      chatExpandBtn.addEventListener('click', toggleExpandPanel);
    }
    if (chatOverlay) {
      chatOverlay.addEventListener('click', () => toggleChatPanel(false));
    }
    if (chatResetBtn) {
      chatResetBtn.addEventListener('click', handleResetMemory);
    }
    
    // Primary Input
    if (chatSendBtn) {
      chatSendBtn.addEventListener('click', handleSendMessage);
    }
    if (chatInput) {
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSendMessage();
        }
      });
      chatInput.addEventListener('input', (e) => {
        if (tab6Input) tab6Input.value = e.target.value;
      });
    }

    // Tab 6 Command Center Input
    if (tab6SendBtn) {
      tab6SendBtn.addEventListener('click', handleSendMessage);
    }
    if (tab6Input) {
      tab6Input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSendMessage();
        }
      });
      tab6Input.addEventListener('input', (e) => {
        if (chatInput) chatInput.value = e.target.value;
      });
    }

    // Escape closes drawer
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && chatPanel && chatPanel.classList.contains('open')) {
        toggleChatPanel(false);
      }
    });
  }

  // ── Open Briefing / Chat ──
  window.openAgentBriefing = function () {
    if (window.switchTab) {
      window.switchTab('tab6');
    } else {
      const tabBtn = document.querySelector('[data-tab="tab6"]');
      if (tabBtn) tabBtn.click();
    }
    const subNav = document.getElementById('agentSubNav');
    const briefBtn = subNav?.querySelector('[data-subtab="brief"]');
    if (briefBtn) {
      briefBtn.click();
    } else {
      loadAgentTabBrief();
    }
    setTimeout(() => {
      const target = document.getElementById('agentViewBrief') || document.getElementById('tab6');
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
  };

  window.openAgentChat = function (initialQuery = null) {
    if (window.switchTab) {
      window.switchTab('tab6');
    } else {
      const tabBtn = document.querySelector('[data-tab="tab6"]');
      if (tabBtn) tabBtn.click();
    }
    const subNav = document.getElementById('agentSubNav');
    const chatBtn = subNav?.querySelector('[data-subtab="chat"]');
    if (chatBtn) chatBtn.click();

    if (initialQuery && typeof initialQuery === 'string') {
      if (initialQuery === '__WARROOM__') {
        window.runWarRoom();
      } else if (initialQuery === '__SCENARIOS__') {
        window.runScenarioCopilot();
      } else {
        if (chatInput) chatInput.value = initialQuery;
        if (tab6Input) tab6Input.value = initialQuery;
        handleSendMessage();
      }
    }
  };

    function toggleExpandPanel() {
    if (!chatPanel) return;
    const isExpanded = chatPanel.classList.toggle('expanded');
    if (chatExpandBtn) {
      chatExpandBtn.textContent = isExpanded ? '🗗' : '⛶';
      chatExpandBtn.title = isExpanded ? 'Restore Standard View' : 'Toggle Wide Screen View';
    }
  }

  function toggleChatPanel(open) {
    if (!chatPanel) return;
    if (open) {
      chatPanel.classList.add('open');
      if (chatOverlay) chatOverlay.classList.add('open');
      if (chatFab) chatFab.classList.add('chat-open');
      setTimeout(() => {
        if (chatInput) chatInput.focus();
      }, 300);
    } else {
      chatPanel.classList.remove('open');
      if (chatOverlay) chatOverlay.classList.remove('open');
      if (chatFab) chatFab.classList.remove('chat-open');
    }
  }

  // ── Welcome Message & Starter Action Chips ──
  function renderWelcomeMessage() {
    const welcomeHtml = `
      <div class="ai-msg-bubble agent-msg">
        <div class="msg-avatar">🤖</div>
        <div class="msg-content">
          <div class="msg-sender">DemandSense Autonomous Agent</div>
          <p>Hello! I am your <strong>Supply Chain Intelligence Agent</strong>. I can autonomously run forecasts, check warehouse inventory, calculate stockout risks, and simulate what-if scenarios across all 20 FMCG SKUs.</p>
          <p>Select an action below or ask any question in plain English:</p>
        </div>
      </div>
    `;

    if (chatMessages) chatMessages.innerHTML = welcomeHtml;
    if (tab6Messages) tab6Messages.innerHTML = welcomeHtml;

    renderSuggestionChips();
  }

  function renderSuggestionChips() {
    const currentSku = window.state?.activeSku || window.state?.sku || 'SKU001';
    const chips = [
      { label: '✨ 2-Min Recruiter Tour', query: '__TOUR__' },
      { label: '🏛️ War Room Analysis', query: '__WARROOM__' },
      { label: '🔮 Scenario Copilot', query: '__SCENARIOS__' },
      { label: '📋 Morning Portfolio Brief', query: 'Generate an executive portfolio brief for all 20 SKUs.' },
      { label: `📦 Reorder Check: ${currentSku}`, query: `Should I place a purchase order for ${currentSku} based on current forecast?` },
      { label: '🎉 Festival Demand Spikes', query: 'What Indian festivals are coming up in the next 60 days and which SKUs will spike?' },
      { label: '⚡ Run What-If Simulation', query: `Simulate a 15% promotion and 3-day supplier delay for ${currentSku}.` },
    ];

    const chipsHtml = chips
      .map(
        (chip) => `
        <button class="chat-chip-btn" data-query="${escapeHtml(chip.query)}">
          ${chip.label}
        </button>
      `
      )
      .join('');

    [chatChipsContainer, tab6ChipsContainer].forEach((container) => {
      if (!container) return;
      container.innerHTML = chipsHtml;
      container.querySelectorAll('.chat-chip-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const q = btn.getAttribute('data-query');
          if (q === '__WARROOM__') {
            window.runWarRoom();
          } else if (q === '__SCENARIOS__') {
            window.runScenarioCopilot();
          } else {
            if (chatInput) chatInput.value = q;
            if (tab6Input) tab6Input.value = q;
            handleSendMessage();
          }
        });
      });
    });
  }

  // ── Send Message & Agent Execution ──
  async function handleSendMessage() {
    if (isSending) return;
    const query = (tab6Input && tab6Input.value.trim()) ? tab6Input.value.trim() : (chatInput ? chatInput.value.trim() : '');
    if (!query) return;

    if (chatInput) chatInput.value = '';
    if (tab6Input) tab6Input.value = '';

    // Route special keywords if typed directly
    const lower = query.toLowerCase();
        if (lower === '__tour__' || lower === 'tour' || lower === 'demo' || lower === 'recruiter tour') {
      window.runRecruiterTour();
      return;
    }
    if (lower === '__warroom__' || lower === 'war room' || lower === 'warroom') {
      window.runWarRoom();
      return;
    }
    if (lower === '__scenarios__' || lower === 'scenario copilot' || lower === 'scenarios') {
      window.runScenarioCopilot();
      return;
    }

    appendUserMessage(query);

    const typingId = appendTypingIndicator('Reasoning & executing tools...');
    isSending = true;
    if (chatSendBtn) chatSendBtn.disabled = true;

    const activeSku = document.getElementById('agentSkuSelect')?.value || window.state?.activeSku || window.state?.sku || 'SKU001';
    const activeStock = window.state?.currentStock || window.state?.stock || 25000;
    const sessionContext = {
      sku_id: activeSku,
      region: window.state?.activeRegion || window.state?.region || 'ALL',
      current_stock: activeStock,
      lead_time: window.state?.leadTime || 7,
    };

    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          session_context: sessionContext,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}. The agent may still be warming up — please retry in 30 seconds.`);
      }
      const data = await response.json();
      removeTypingIndicator(typingId);

      if (data.active_sku) {
        if (window.state) window.state.sku = data.active_sku;
        const agentSkuSelect = document.getElementById('agentSkuSelect');
        if (agentSkuSelect && agentSkuSelect.value !== data.active_sku) {
          agentSkuSelect.value = data.active_sku;
        }
        const mainSkuSelect = document.getElementById('skuSelect');
        if (mainSkuSelect && mainSkuSelect.value !== data.active_sku) {
          mainSkuSelect.value = data.active_sku;
        }
      }

      if (data.error && !data.answer) {
        appendAgentMessage(`⚠️ **Agent Error:** ${data.error}`, []);
      } else {
        appendAgentMessage(data.answer, data.steps || [], data.tools_called || []);
      }
    } catch (err) {
      removeTypingIndicator(typingId);
      appendAgentMessage(`⚠️ **Connection Error:** Could not reach the agent server. (${err.message})`, []);
    } finally {
      isSending = false;
      if (chatSendBtn) chatSendBtn.disabled = false;
      if (chatInput) chatInput.focus();
    }
  }

  // ── Mode: Recruiter Interactive Tour ──
  window.runRecruiterTour = function () {
    if (window.state?.activeTab !== 'tab6') {
      toggleChatPanel(true);
    }
    appendUserMessage('✨ Start 2-Minute Recruiter Interactive Tour');

    const tourHtml = `
      <div class="msg-avatar">🎯</div>
      <div class="msg-content">
        <div class="msg-sender">RECRUITER INTERACTIVE DEMO — 2-MIN TOUR</div>
        <p>Welcome to <strong>DemandSense AI</strong>! This tour walks through the 4 flagship autonomous agent capabilities built into this platform:</p>
        
        <div class="tour-container">
          <div class="tour-step-card">
            <div class="tour-step-header">
              <span>1. Multi-Agent War Room (Prophet + XGBoost + OR)</span>
              <span style="font-size:0.65rem;opacity:0.7;">3 Specialists</span>
            </div>
            <div class="tour-step-desc">Orchestrates Demand Planner, Inventory Controller, and Risk Analyst in parallel to produce consensus directives.</div>
            <button class="tour-step-action-btn" onclick="window.runWarRoomForSku('SKU001')">
              🚀 Launch War Room (SKU001)
            </button>
          </div>

          <div class="tour-step-card">
            <div class="tour-step-header">
              <span>2. Scenario Stress-Testing Copilot</span>
              <span style="font-size:0.65rem;opacity:0.7;">Monte Carlo & Elasticity</span>
            </div>
            <div class="tour-step-desc">Simulates promotional lift, supplier disruption delays, and pricing shifts with rupee revenue-at-risk scoring.</div>
            <button class="tour-step-action-btn" onclick="window.runScenarioCopilot('SKU001')">
              🔮 Benchmark 4 Scenarios
            </button>
          </div>

          <div class="tour-step-card">
            <div class="tour-step-header">
              <span>3. Executive Supply Chain Portfolio Brief</span>
              <span style="font-size:0.65rem;opacity:0.7;">All 20 SKUs</span>
            </div>
            <div class="tour-step-desc">Autonomous scan across all 20 FMCG SKUs detecting imminent stockouts, Diwali surges, and required PO values.</div>
            <button class="tour-step-action-btn" onclick="if(window.openAgentChat) window.openAgentChat('Generate an executive portfolio brief for all 20 SKUs.')">
              📋 Generate 20-SKU Brief
            </button>
          </div>

          <div class="tour-step-card">
            <div class="tour-step-header">
              <span>4. Indian Festival Demand Spike Forecast</span>
              <span style="font-size:0.65rem;opacity:0.7;">Diwali / Ganesh Chaturthi</span>
            </div>
            <div class="tour-step-desc">Predicts holiday surge multipliers and recommends pre-festival buffer stock additions.</div>
            <button class="tour-step-action-btn" onclick="if(window.openAgentChat) window.openAgentChat('What Indian festivals are coming up in the next 60 days and which SKUs will spike?')">
              🎉 Inspect Festival Spikes
            </button>
          </div>
        </div>
      </div>
    `;

    appendAgentHtmlNode(tourHtml);
  };

  // ── SKU Prompt Helpers ──
  window.promptWarRoomSku = function () {
    toggleChatPanel(true);
    const activeSku = window.state?.activeSku || window.state?.sku || 'SKU001';
    const ts = Date.now();

    const optionsHtml = FMCG_CATALOG.map(p => 
      `<option value="${p.id}" ${p.id === activeSku ? 'selected' : ''}>${p.id} — ${escapeHtml(p.name)} (${p.category})</option>`
    ).join('');

    const quickSkus = ['SKU001', 'SKU002', 'SKU003', 'SKU006', 'SKU007', 'SKU008', 'SKU011', 'SKU015', 'SKU019'];
    const quickButtons = quickSkus.map(sid => {
      const prod = FMCG_CATALOG.find(p => p.id === sid) || { id: sid, name: sid, icon: '📦' };
      return `<button class="sku-quick-btn" onclick="window.runWarRoomForSku('${sid}')">${prod.icon} ${sid} (${prod.name.split(' ')[0]})</button>`;
    }).join('');

    const promptHtml = `
      <div class="ai-msg-bubble agent-msg">
        <div class="msg-avatar">🏛️</div>
        <div class="msg-content">
          <div class="msg-sender">WAR ROOM — SELECT SKU</div>
          <p>Which product would you like the <strong>Demand Planner, Inventory Controller, and Risk Analyst</strong> to collaborate on?</p>
          
          <div class="sku-picker-container">
            <span class="sku-picker-label">⚡ Fast-Moving SKUs:</span>
            <div class="sku-picker-quick">
              ${quickButtons}
            </div>

            <span class="sku-picker-label" style="margin-top:0.3rem;">📋 Or Select Any of 20 SKUs:</span>
            <div class="sku-picker-select-row">
              <select class="sku-picker-select">
                ${optionsHtml}
              </select>
              <button class="sku-picker-launch-btn" onclick="window.runWarRoomFromSelect(this)">
                🚀 Launch War Room
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    if (window.state?.activeTab !== 'tab6') {
      toggleChatPanel(true);
    }
    appendAgentHtmlNode(promptHtml);
  };

  window.runWarRoomFromSelect = function (btnOrId) {
    let sku = 'SKU001';
    if (typeof btnOrId === 'string') {
      const el = document.getElementById(btnOrId);
      if (el) sku = el.value;
    } else if (btnOrId && btnOrId.parentElement) {
      const sel = btnOrId.parentElement.querySelector('select');
      if (sel) sku = sel.value;
    }
    window.runWarRoomForSku(sku);
  };

  window.promptScenarioSku = function () {
    const activeSku = window.state?.activeSku || window.state?.sku || 'SKU001';

    const optionsHtml = FMCG_CATALOG.map(p => 
      `<option value="${p.id}" ${p.id === activeSku ? 'selected' : ''}>${p.id} — ${escapeHtml(p.name)} (${p.category})</option>`
    ).join('');

    const quickSkus = ['SKU001', 'SKU002', 'SKU003', 'SKU006', 'SKU007', 'SKU008', 'SKU011', 'SKU015', 'SKU019'];
    const quickButtons = quickSkus.map(sid => {
      const prod = FMCG_CATALOG.find(p => p.id === sid) || { id: sid, name: sid, icon: '🔮' };
      return `<button class="sku-quick-btn" onclick="window.runScenarioCopilot('${sid}')">${prod.icon} ${sid} (${prod.name.split(' ')[0]})</button>`;
    }).join('');

    const promptHtml = `
      <div class="ai-msg-bubble agent-msg">
        <div class="msg-avatar">🔮</div>
        <div class="msg-content">
          <div class="msg-sender">SCENARIO COPILOT — SELECT SKU</div>
          <p>Which product would you like to benchmark across <strong>4 strategic scenarios</strong> (promotional lift, supplier delay, price elasticity)?</p>
          
          <div class="sku-picker-container">
            <span class="sku-picker-label">⚡ Fast-Moving SKUs:</span>
            <div class="sku-picker-quick">
              ${quickButtons}
            </div>

            <span class="sku-picker-label" style="margin-top:0.3rem;">📋 Or Select Any of 20 SKUs:</span>
            <div class="sku-picker-select-row">
              <select class="sku-picker-select">
                ${optionsHtml}
              </select>
              <button class="sku-picker-launch-btn" onclick="window.runScenarioFromSelect(this)">
                🚀 Run Scenarios
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    if (window.state?.activeTab !== 'tab6') {
      toggleChatPanel(true);
    }
    appendAgentHtmlNode(promptHtml);
  };

  window.runScenarioFromSelect = function (btnOrId) {
    let sku = 'SKU001';
    if (typeof btnOrId === 'string') {
      const el = document.getElementById(btnOrId);
      if (el) sku = el.value;
    } else if (btnOrId && btnOrId.parentElement) {
      const sel = btnOrId.parentElement.querySelector('select');
      if (sel) sku = sel.value;
    }
    window.runScenarioCopilot(sku);
  };

  // ── Mode C: Multi-Agent War Room ──
  window.runWarRoom = function (customQuery) {
    if (!customQuery || customQuery === '__WARROOM__' || customQuery === 'war room' || customQuery === 'warroom') {
      window.promptWarRoomSku();
      return;
    }
    const match = customQuery.match(/SKU\d{3}/i);
    const targetSku = match ? match[0].toUpperCase() : null;
    if (targetSku) {
      window.runWarRoomForSku(targetSku, customQuery);
    } else {
      window.promptWarRoomSku();
    }
  };

  window.runWarRoomForSku = async function (skuId, customQuery) {
    if (isSending) return;
    const sku = skuId || 'SKU001';
    const prod = FMCG_CATALOG.find(p => p.id === sku);
    const prodName = prod ? prod.name : sku;
    const query = customQuery || `Conduct a comprehensive War Room analysis for ${sku} (${prodName}) evaluating demand trajectory, inventory coverage, and rupee financial risk.`;

    if (window.state?.activeTab !== 'tab6') {
      toggleChatPanel(true);
    }
    appendUserMessage(`🏛️ War Room Request: ${sku} — ${prodName}`);

    const typingId = appendTypingIndicator(`War Room: Analyzing ${sku} across 3 specialists in parallel...`);
    isSending = true;
    if (chatSendBtn) chatSendBtn.disabled = true;

    const sessionContext = {
      sku_id: sku,
      current_stock: window.state?.currentStock || window.state?.stock || 1500,
    };

    try {
      const res = await fetch('/api/agent/warroom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, session_context: sessionContext }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}. The War Room may still be warming up — please retry in 30 seconds.`);
      }
      const data = await res.json();
      removeTypingIndicator(typingId);

      if (data.error) {
        appendAgentMessage(`⚠️ **War Room Error:** ${data.error}`);
        return;
      }

      const reportHtml = buildWarRoomReportHtml(data, sku);
      const htmlContent = `
        <div class="msg-avatar">🏛️</div>
        <div class="msg-content" style="background:transparent; border:none; box-shadow:none; padding:0;">
          <div class="msg-sender" style="margin-left: 0.5rem; margin-bottom: 0.8rem;">WAR ROOM — SPECIALIST COLLABORATION (${escapeHtml(sku)})</div>
          ${reportHtml}
        </div>
      `;
      appendAgentHtmlNode(htmlContent);

      const container = document.getElementById('agentWarroomContainer');
      if (container) {
        container.dataset.loadedSku = sku;
        container.innerHTML = reportHtml;
      }
    } catch (err) {
      removeTypingIndicator(typingId);
      appendAgentMessage(`⚠️ **Connection Error:** Could not reach War Room. (${err.message})`);
    } finally {
      isSending = false;
      if (chatSendBtn) chatSendBtn.disabled = false;
    }
  };

  function buildWarRoomReportHtml(data, sku) {
    let specialistCardsHtml = '';
    if (data.specialist_reports && data.specialist_reports.length > 0) {
      data.specialist_reports.forEach((r) => {
        const icon = r.icon || '🤖';
        const role = r.role || 'Specialist';
        const m = r.metrics;

        if (m && Object.keys(m).length > 0) {
          let themeClass = 'theme-demand';
          let innerHtml = '';

          if (r.specialist_id === 'demand_planner') {
            themeClass = 'theme-demand';
            const trend = String(m.forecast_trend || 'stable').toLowerCase();
            const trendIcon = trend === 'up' ? '↑' : (trend === 'down' ? '↓' : '→');
            const trendClass = trend === 'up' ? 'trend-up' : (trend === 'down' ? 'trend-down' : 'trend-stable');
            
            let festivalHtml = '';
            if (m.upcoming_festival && m.upcoming_festival.name) {
              festivalHtml = `<div class="festival-alert">🎉 ${escapeHtml(m.upcoming_festival.name)} in ${m.upcoming_festival.days_until} days → ${escapeHtml(m.upcoming_festival.demand_impact)}</div>`;
            }

            innerHtml = `
              <div class="specialist-hero-metric">
                <span class="hero-value">${Number(m.total_30d_forecast_units || 0).toLocaleString()}</span>
                <span class="hero-unit">units (30d)</span>
              </div>
              <div class="specialist-sub-metrics">
                <div class="metric-chip"><span class="chip-label">Model:</span> <span class="chip-value">${escapeHtml(m.winning_model || 'Auto-ML')}</span></div>
                <div class="metric-chip"><span class="chip-label">MAPE:</span> <span class="chip-value">${m.mape_pct ?? 0}%</span></div>
                <div class="trend-indicator ${trendClass}">${trendIcon} ${escapeHtml(trend.toUpperCase())}</div>
              </div>
              ${festivalHtml}
            `;
          } 
          else if (r.specialist_id === 'inventory_controller') {
            themeClass = 'theme-inventory';
            
            const poStatus = String(m.po_trigger_status || 'STABLE').toUpperCase();
            let statusClass = 'status-stable';
            let badgeText = 'STABLE';
            if (poStatus.includes('CRITICAL')) { statusClass = 'status-critical'; badgeText = 'CRITICAL'; }
            else if (poStatus.includes('WARNING') || poStatus.includes('REORDER') || poStatus.includes('ACTION')) { statusClass = 'status-warning'; badgeText = 'WARNING'; }
            
            const dosVal = Number(m.days_of_supply || 0);
            const dosPct = Math.min(100, Math.max(0, (dosVal / 60) * 100));
            const strokeOffset = 157 - (157 * dosPct) / 100;
            const ringColor = dosVal < 15 ? '#dc2626' : (dosVal < 30 ? '#f59e0b' : '#16a34a');

            let poHtml = '';
            const poQty = Number(m.recommended_po_qty_units || 0);
            const poVal = Number(m.recommended_po_value_inr || 0);
            if (poQty > 0) {
              poHtml = `<div class="po-callout po-required">📦 ACTION: Place PO for ${poQty.toLocaleString()} units (₹${poVal.toLocaleString()})</div>`;
            } else {
              poHtml = `<div class="po-callout po-healthy">📦 NO PO REQUIRED — Coverage Healthy</div>`;
            }

            innerHtml = `
              <div class="dos-ring-container">
                <svg class="dos-ring" viewBox="0 0 60 60">
                  <circle class="ring-bg" cx="30" cy="30" r="25"></circle>
                  <circle class="ring-fill" cx="30" cy="30" r="25" style="stroke: ${ringColor}; stroke-dasharray: 157; stroke-dashoffset: ${strokeOffset};" transform="rotate(-90 30 30)"></circle>
                </svg>
                <div class="dos-ring-label">
                  <span class="dos-value">${dosVal}</span>
                  <span class="dos-unit">Days of Supply</span>
                </div>
                <div style="margin-left:auto;"><span class="status-badge ${statusClass}">${badgeText}</span></div>
              </div>
              <div class="specialist-sub-metrics">
                <div class="metric-chip"><span class="chip-label">Stock:</span> <span class="chip-value">${Number(m.current_stock || 0).toLocaleString()}</span></div>
                <div class="metric-chip"><span class="chip-label">ROP:</span> <span class="chip-value">${Number(m.reorder_point_units || 0).toLocaleString()}</span></div>
              </div>
              ${poHtml}
            `;
          }
          else if (r.specialist_id === 'risk_analyst') {
            themeClass = 'theme-risk';
            
            const isRiskHigh = m.revenue_at_risk_inr > 0;
            const valClass = isRiskHigh ? 'risk-high' : 'risk-low';
            
            let roiHtml = '';
            if (isRiskHigh) {
              roiHtml = `<div class="roi-callout">Acting now preserves ₹${Number(m.revenue_at_risk_inr).toLocaleString()} margin vs ₹${Number(m.holding_cost_inr).toLocaleString()} holding cost.</div>`;
            }

            innerHtml = `
              <div class="risk-hero">
                <span class="risk-label">Projected Revenue at Risk</span>
                <span class="risk-value ${valClass}">₹${Number(m.revenue_at_risk_inr).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
              </div>
              <div class="specialist-sub-metrics">
                <div class="metric-chip"><span class="chip-label">Units at Risk:</span> <span class="chip-value">${Number(m.stockout_risk_units || 0).toLocaleString()}</span></div>
                <div class="metric-chip"><span class="chip-label">Cap. Outlay:</span> <span class="chip-value">₹${Number(m.required_capital_outlay_inr || 0).toLocaleString()}</span></div>
              </div>
              ${roiHtml}
            `;
          }

          specialistCardsHtml += `
            <div class="specialist-card-v2 ${themeClass}">
              <div class="specialist-accent-bar"></div>
              <div class="specialist-card-body">
                <div class="specialist-header-v2">
                  <div class="specialist-icon-v2">${icon}</div>
                  <div class="specialist-role-v2">${escapeHtml(role)}</div>
                </div>
                ${innerHtml}
              </div>
            </div>
          `;
        } else {
          const body = formatMarkdown(r.analysis || 'No analysis available.');
          specialistCardsHtml += `
            <div class="warroom-specialist-card">
              <div class="specialist-header">
                <span class="specialist-icon">${icon}</span>
                <span>${escapeHtml(role)}</span>
              </div>
              <div class="specialist-analysis">
                ${body}
              </div>
            </div>
          `;
        }
      });
    }

    let synthesisHtml = '';
    if (data.synthesis) {
      const parsedMarkdown = formatMarkdown(data.synthesis);
      if (parsedMarkdown.includes('<strong>1.</strong>')) {
        const actionItems = parsedMarkdown.match(/<li class="chat-li">.*?<\/li>/g);
        if (actionItems) {
          let actionsHtml = '';
          actionItems.forEach((li, idx) => {
            const cleanedText = li.replace(/<li class="chat-li"><strong>\d+\.<\/strong>\s*/, '').replace(/<\/li>/, '');
            actionsHtml += `
              <div class="directive-action">
                <div class="directive-num">${idx + 1}</div>
                <div class="directive-text">${cleanedText}</div>
              </div>
            `;
          });
          synthesisHtml = `
            <div class="executive-directive">
              <div class="directive-header">
                <span class="title-icon">🏛️</span>
                <span>War Room Unified Directive</span>
              </div>
              ${actionsHtml}
            </div>
          `;
        } else {
          synthesisHtml = `<div class="warroom-synthesis">${parsedMarkdown}</div>`;
        }
      } else {
        synthesisHtml = `<div class="warroom-synthesis">${parsedMarkdown}</div>`;
      }
    }

    return `
      <div class="warroom-grid">
        ${specialistCardsHtml}
      </div>
      ${synthesisHtml}
    `;
  }

  // ── Mode E: Scenario Planning Copilot ──
  window.runScenarioCopilot = async function (skuId) {
    if (!skuId || skuId === '__SCENARIOS__' || typeof skuId !== 'string' || !skuId.match(/SKU\d{3}/i)) {
      window.promptScenarioSku();
      return;
    }
    if (isSending) return;
    const match = skuId.match(/SKU\d{3}/i);
    const targetSku = match ? match[0].toUpperCase() : 'SKU001';
    const prod = FMCG_CATALOG.find(p => p.id === targetSku);
    const prodName = prod ? prod.name : targetSku;
    const stock = window.state?.currentStock || window.state?.stock || 1500;

    if (window.state?.activeTab !== 'tab6') {
      toggleChatPanel(true);
    }
    appendUserMessage(`🔮 Scenario Copilot: Benchmark 4 Strategies for ${targetSku} — ${prodName}`);

    const typingId = appendTypingIndicator(`Simulating 4 strategic scenarios for ${targetSku}...`);
    isSending = true;
    if (chatSendBtn) chatSendBtn.disabled = true;

    try {
      const res = await fetch('/api/agent/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: targetSku, current_stock: stock }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}. Scenarios may still be warming up — please retry in 30 seconds.`);
      }
      const data = await res.json();
      removeTypingIndicator(typingId);

      if (data.error) {
        appendAgentMessage(`⚠️ **Scenario Error:** ${data.error}`);
        return;
      }

      const reportHtml = buildScenariosReportHtml(data, targetSku, prodName, stock);
      const htmlContent = `
        <div class="msg-avatar">🔮</div>
        <div class="msg-content">
          <div class="msg-sender">SCENARIO PLANNING COPILOT (${escapeHtml(targetSku)})</div>
          ${reportHtml}
        </div>
      `;
      appendAgentHtmlNode(htmlContent);

      const container = document.getElementById('agentScenariosContainer');
      if (container) {
        container.dataset.loadedSku = targetSku;
        container.innerHTML = reportHtml;
      }
    } catch (err) {
      removeTypingIndicator(typingId);
      appendAgentMessage(`⚠️ **Connection Error:** Could not run scenario copilot. (${err.message})`);
    } finally {
      isSending = false;
      if (chatSendBtn) chatSendBtn.disabled = false;
    }
  };

  function buildScenariosReportHtml(data, targetSku, prodName, stock) {
    let tableRows = '';
    let maxDemand = 1;
    (data.scenarios || []).forEach(s => {
      if (s.total_30d_forecast > maxDemand) maxDemand = s.total_30d_forecast;
    });

    (data.scenarios || []).forEach((s) => {
      const isRec = s.scenario_name === data.recommended_scenario;
      const rowClass = isRec ? 'scenario-row recommended' : 'scenario-row';
      const star = isRec ? ' ⭐' : '';
      
      let statusClass = 'chip-stable';
      if (s.po_trigger_status && s.po_trigger_status.includes('CRITICAL')) statusClass = 'chip-critical';
      else if (s.po_trigger_status && (s.po_trigger_status.includes('WARNING') || s.po_trigger_status.includes('REORDER'))) statusClass = 'chip-warning';
      
      const demandPct = Math.max(5, (s.total_30d_forecast / maxDemand) * 100);

      tableRows += `
        <tr class="${rowClass}">
          <td>
            <strong>${escapeHtml(s.scenario_name)}${star}</strong><br/>
            <span class="scenario-status-chip ${statusClass}" style="margin-top:4px;">${escapeHtml(s.po_trigger_status || 'STABLE')}</span>
          </td>
          <td>
            <div class="demand-bar-cell">
              <span>${Number(s.total_30d_forecast || 0).toLocaleString()}</span>
              <div class="demand-mini-bar" style="width: ${demandPct}px;"></div>
            </div>
          </td>
          <td>${s.days_of_supply || 0}d</td>
          <td>₹${Number(s.revenue_at_risk_inr || 0).toLocaleString()}</td>
          <td>${Number(s.recommended_po_qty || 0).toLocaleString()}</td>
          <td>₹${Number(s.recommended_po_value_inr || 0).toLocaleString()}</td>
        </tr>
      `;
    });

    return `
      <p style="margin-bottom:1rem;color:var(--text2);font-size:0.85rem;">
        Benchmarked 4 strategic scenarios for <strong>${escapeHtml(targetSku)} — ${escapeHtml(prodName)}</strong> with ${(stock || 25000).toLocaleString()} units on hand:
      </p>
      <div class="scenario-table-wrap">
        <table class="scenario-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>30d Demand</th>
              <th>Coverage</th>
              <th>Rev. at Risk</th>
              <th>PO Qty</th>
              <th>PO Value</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows}
          </tbody>
        </table>
      </div>
      <div class="scenario-recommendation" style="margin-top:1rem;">
        <strong>🏆 Recommended Path:</strong> ${escapeHtml(data.recommended_scenario || 'N/A')}<br>
        <span style="font-size:0.78rem;color:var(--text2);margin-top:4px;display:block;">${escapeHtml(data.recommendation_rationale || '')}</span>
      </div>
    `;
  }

  function buildBriefReportHtml(data) {
    const critCount = data.critical_skus ? data.critical_skus.length : 0;
    const watchCount = data.watch_skus ? data.watch_skus.length : 0;
    const healthyCount = data.healthy_count || 0;
    const totalRisk = Number(data.total_risk_inr || 0);

    let criticalRows = '';
    if (data.critical_skus && data.critical_skus.length > 0) {
      criticalRows = data.critical_skus.map(s => `
        <tr class="scenario-row">
          <td><strong>${escapeHtml(s.sku_id)} — ${escapeHtml(s.name)}</strong></td>
          <td><span class="scenario-status-chip chip-critical">${s.days_of_supply} DOS</span></td>
          <td>₹${Number(s.revenue_at_risk_inr || 0).toLocaleString()}</td>
          <td>${Number(s.recommended_po_qty_units || 0).toLocaleString()} units</td>
          <td>
            <button class="agent-action-primary-btn" style="padding:0.25rem 0.65rem; font-size:0.72rem;" onclick="window.selectAgentSkuAndRunWarRoom('${s.sku_id}')">
              Launch War Room ➔
            </button>
          </td>
        </tr>
      `).join('');
    }

    const narrativeHtml = formatMarkdown(data.brief || 'Portfolio scan complete.');

    return `
      <div class="agent-brief-kpis">
        <div class="agent-brief-card" style="border-left: 3px solid var(--red);">
          <div style="font-size:0.72rem; color:var(--text3); font-weight:700; text-transform:uppercase;">Critical Stockouts</div>
          <div style="font-size:1.6rem; font-weight:800; color:var(--red); margin-top:4px;">${critCount}</div>
          <div style="font-size:0.7rem; color:var(--text3);">Immediate PO required</div>
        </div>
        <div class="agent-brief-card" style="border-left: 3px solid var(--amber);">
          <div style="font-size:0.72rem; color:var(--text3); font-weight:700; text-transform:uppercase;">Watchlist SKUs</div>
          <div style="font-size:1.6rem; font-weight:800; color:var(--amber); margin-top:4px;">${watchCount}</div>
          <div style="font-size:0.7rem; color:var(--text3);">Approaching ROP</div>
        </div>
        <div class="agent-brief-card" style="border-left: 3px solid var(--green);">
          <div style="font-size:0.72rem; color:var(--text3); font-weight:700; text-transform:uppercase;">Healthy Coverage</div>
          <div style="font-size:1.6rem; font-weight:800; color:var(--green); margin-top:4px;">${healthyCount}</div>
          <div style="font-size:0.7rem; color:var(--text3);">> 30 days buffer</div>
        </div>
        <div class="agent-brief-card" style="border-left: 3px solid var(--teal);">
          <div style="font-size:0.72rem; color:var(--text3); font-weight:700; text-transform:uppercase;">Total Rupee Risk</div>
          <div style="font-size:1.6rem; font-weight:800; color:var(--accent); margin-top:4px;">₹${totalRisk.toLocaleString()}</div>
          <div style="font-size:0.7rem; color:var(--text3);">Portfolio exposure</div>
        </div>
      </div>

      ${criticalRows ? `
        <div style="margin-bottom: 1.25rem;">
          <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:0.6rem;">⚠️ Priority SKUs Requiring Immediate Procurement Action</h4>
          <div class="scenario-table-wrap">
            <table class="scenario-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Coverage</th>
                  <th>Rupee Risk</th>
                  <th>PO Recommendation</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                ${criticalRows}
              </tbody>
            </table>
          </div>
        </div>
      ` : ''}

      <div class="warroom-synthesis">
        <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:0.6rem;">📋 Executive Narrative Summary</h4>
        ${narrativeHtml}
      </div>
    `;
  }

  // ── Tab 6 View Loaders & Sub-Nav Controllers ──
  async function loadAgentTabWarRoom(sku, force = false) {
    const container = document.getElementById('agentWarroomContainer');
    const title = document.getElementById('warroomTargetTitle');
    if (!container) return;

    if (!force && container.dataset.loadedSku === sku && container.children.length > 0) {
      return;
    }

    const prod = FMCG_CATALOG.find(p => p.id === sku);
    const prodName = prod ? prod.name : sku;
    if (title) title.textContent = `Multi-Agent Specialist Collaboration — ${sku} (${prodName})`;

    container.innerHTML = `
      <div style="padding: 3rem; text-align: center; color: var(--text2);">
        <div style="font-size: 2.2rem; margin-bottom: 0.75rem; animation: pulse-dot 1.5s infinite;">🏛️</div>
        <div style="font-weight: 700; font-size: 1.05rem; color: var(--text);">Convening Multi-Agent War Room for ${escapeHtml(sku)}...</div>
        <div style="font-size: 0.8rem; margin-top: 0.35rem; color: var(--text3);">Demand Planner, Inventory Controller, and Risk Analyst running in parallel...</div>
      </div>
    `;

    try {
      const res = await fetch('/api/agent/warroom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `Conduct comprehensive War Room analysis for ${sku}`,
          session_context: { sku_id: sku, current_stock: window.state?.stock || 25000 }
        })
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      container.dataset.loadedSku = sku;
      container.innerHTML = buildWarRoomReportHtml(data, sku);
    } catch (err) {
      container.innerHTML = `
        <div style="padding: 2.5rem; text-align: center; color: var(--red);">
          ⚠️ Could not load War Room for ${escapeHtml(sku)} (${err.message}).
          <div style="margin-top: 1rem;">
            <button class="agent-action-primary-btn" onclick="window.loadAgentTabWarRoom('${sku}', true)">Retry</button>
          </div>
        </div>
      `;
    }
  }

  async function loadAgentTabScenarios(sku, force = false) {
    const container = document.getElementById('agentScenariosContainer');
    const title = document.getElementById('scenariosTargetTitle');
    if (!container) return;

    if (!force && container.dataset.loadedSku === sku && container.children.length > 0) {
      return;
    }

    const prod = FMCG_CATALOG.find(p => p.id === sku);
    const prodName = prod ? prod.name : sku;
    if (title) title.textContent = `Scenario Stress-Testing Copilot (4 Strategies) — ${sku} (${prodName})`;

    container.innerHTML = `
      <div style="padding: 3rem; text-align: center; color: var(--text2);">
        <div style="font-size: 2.2rem; margin-bottom: 0.75rem; animation: pulse-dot 1.5s infinite;">🔮</div>
        <div style="font-weight: 700; font-size: 1.05rem; color: var(--text);">Simulating 4 Strategic Scenarios for ${escapeHtml(sku)}...</div>
        <div style="font-size: 0.8rem; margin-top: 0.35rem; color: var(--text3);">Benchmarking baseline, promotion, supplier delay, and price elasticity...</div>
      </div>
    `;

    try {
      const res = await fetch('/api/agent/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku_id: sku,
          current_stock: window.state?.stock || 25000
        })
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      container.dataset.loadedSku = sku;
      container.innerHTML = buildScenariosReportHtml(data, sku, prodName, window.state?.stock || 25000);
    } catch (err) {
      container.innerHTML = `
        <div style="padding: 2.5rem; text-align: center; color: var(--red);">
          ⚠️ Could not load scenarios for ${escapeHtml(sku)} (${err.message}).
          <div style="margin-top: 1rem;">
            <button class="agent-action-primary-btn" onclick="window.loadAgentTabScenarios('${sku}', true)">Retry</button>
          </div>
        </div>
      `;
    }
  }

  async function loadAgentTabBrief(force = false) {
    const container = document.getElementById('agentBriefContainer');
    if (!container) return;

    if (!force && container.dataset.loaded && container.children.length > 0) {
      return;
    }

    container.innerHTML = `
      <div style="padding: 3rem; text-align: center; color: var(--text2);">
        <div style="font-size: 2.2rem; margin-bottom: 0.75rem; animation: pulse-dot 1.5s infinite;">📋</div>
        <div style="font-weight: 700; font-size: 1.05rem; color: var(--text);">Scanning 20-SKU Portfolio...</div>
        <div style="font-size: 0.8rem; margin-top: 0.35rem; color: var(--text3);">Evaluating stockout risks, safety thresholds, and capital requirements...</div>
      </div>
    `;

    try {
      const res = await fetch('/api/agent/brief', { method: 'POST' });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      container.dataset.loaded = 'true';
      container.innerHTML = buildBriefReportHtml(data);
    } catch (err) {
      container.innerHTML = `
        <div style="padding: 2.5rem; text-align: center; color: var(--red);">
          ⚠️ Could not load portfolio brief (${err.message}).
          <div style="margin-top: 1rem;">
            <button class="agent-action-primary-btn" onclick="window.loadAgentTabBrief(true)">Retry</button>
          </div>
        </div>
      `;
    }
  }

  function setupAgentSubNav() {
    const skuSelect = document.getElementById('agentSkuSelect');
    const subNav = document.getElementById('agentSubNav');
    const runWarroomBtn = document.getElementById('agentRunWarroomBtn');
    const runScenariosBtn = document.getElementById('agentRunScenariosBtn');
    const runBriefBtn = document.getElementById('agentRunBriefBtn');

    if (skuSelect && skuSelect.options.length === 0) {
      const activeSku = window.state?.sku || 'SKU001';
      FMCG_CATALOG.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.id} — ${p.name} (${p.category})`;
        if (p.id === activeSku) opt.selected = true;
        skuSelect.appendChild(opt);
      });

      skuSelect.addEventListener('change', () => {
        const currentActive = subNav?.querySelector('.agent-subnav-btn.active')?.dataset.subtab || 'warroom';
        const newSku = skuSelect.value;
        if (window.state) {
          window.state.sku = newSku;
          const globalSku = document.getElementById('skuSelect');
          if (globalSku && globalSku.value !== newSku) {
            globalSku.value = newSku;
            globalSku.dispatchEvent(new Event('change'));
          }
        }
        if (currentActive === 'warroom') {
          loadAgentTabWarRoom(newSku, true);
        } else if (currentActive === 'scenarios') {
          loadAgentTabScenarios(newSku, true);
        }
      });
    }

    if (subNav && !subNav.dataset.bound) {
      subNav.dataset.bound = 'true';
      subNav.querySelectorAll('.agent-subnav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const target = btn.dataset.subtab;
          subNav.querySelectorAll('.agent-subnav-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          const panels = {
            'warroom': document.getElementById('agentViewWarroom'),
            'scenarios': document.getElementById('agentViewScenarios'),
            'brief': document.getElementById('agentViewBrief'),
            'chat': document.getElementById('agentViewChat'),
          };

          Object.keys(panels).forEach(k => {
            if (panels[k]) {
              panels[k].style.display = (k === target) ? 'block' : 'none';
              panels[k].classList.toggle('active', k === target);
            }
          });

          const currentSku = skuSelect ? skuSelect.value : (window.state?.sku || 'SKU001');
          if (target === 'warroom') {
            loadAgentTabWarRoom(currentSku);
          } else if (target === 'scenarios') {
            loadAgentTabScenarios(currentSku);
          } else if (target === 'brief') {
            loadAgentTabBrief();
          }
        });
      });
    }

    if (runWarroomBtn && !runWarroomBtn.dataset.bound) {
      runWarroomBtn.dataset.bound = 'true';
      runWarroomBtn.addEventListener('click', () => {
        const currentSku = skuSelect ? skuSelect.value : (window.state?.sku || 'SKU001');
        loadAgentTabWarRoom(currentSku, true);
      });
    }

    if (runScenariosBtn && !runScenariosBtn.dataset.bound) {
      runScenariosBtn.dataset.bound = 'true';
      runScenariosBtn.addEventListener('click', () => {
        const currentSku = skuSelect ? skuSelect.value : (window.state?.sku || 'SKU001');
        loadAgentTabScenarios(currentSku, true);
      });
    }

    if (runBriefBtn && !runBriefBtn.dataset.bound) {
      runBriefBtn.dataset.bound = 'true';
      runBriefBtn.addEventListener('click', () => {
        loadAgentTabBrief(true);
      });
    }
  }

  window.initAgentTab = function () {
    setupAgentSubNav();
    const skuSelect = document.getElementById('agentSkuSelect');
    const activeSku = window.state?.sku || 'SKU001';
    if (skuSelect) {
      skuSelect.value = activeSku;
    }
    const warroomContainer = document.getElementById('agentWarroomContainer');
    if (warroomContainer && (!warroomContainer.innerHTML.trim() || warroomContainer.dataset.loadedSku !== activeSku)) {
      loadAgentTabWarRoom(activeSku);
    }
  };

  window.selectAgentSkuAndRunWarRoom = function (sku) {
    const skuSelect = document.getElementById('agentSkuSelect');
    if (skuSelect) skuSelect.value = sku;
    if (window.state) {
      window.state.sku = sku;
      const globalSku = document.getElementById('skuSelect');
      if (globalSku && globalSku.value !== sku) {
        globalSku.value = sku;
        globalSku.dispatchEvent(new Event('change'));
      }
    }
    const warroomBtn = document.querySelector('.agent-subnav-btn[data-subtab="warroom"]');
    if (warroomBtn) warroomBtn.click();
    else loadAgentTabWarRoom(sku, true);
  };

  window.loadAgentTabWarRoom = loadAgentTabWarRoom;
  window.loadAgentTabScenarios = loadAgentTabScenarios;
  window.loadAgentTabBrief = loadAgentTabBrief;

  // ── Mode A: Live Autonomous Sentinel Monitoring ──
  function startAutonomousMonitoring() {
    const MONITOR_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

    async function runScan() {
      try {
        const res = await fetch('/api/agent/brief', { method: 'POST' });
        if (!res.ok) return;
        const data = await res.json();
        const critCount = (data.critical_skus || []).length;

        const badge = document.getElementById('aiFabBadge');
        if (badge) {
          if (critCount > 0) {
            badge.style.display = 'block';
            badge.textContent = critCount;
          } else {
            badge.style.display = 'none';
          }
        }
      } catch (e) {
        console.warn('[Agent Sentinel] Background scan paused:', e);
      }
    }

    // Run first scan after 2 seconds, then on interval
    setTimeout(runScan, 2000);
    setInterval(runScan, MONITOR_INTERVAL_MS);
  }

  // ── Message Renderers ──
  function appendUserMessage(text) {
    const htmlContent = `
      <div class="msg-content">
        <p>${escapeHtml(text)}</p>
      </div>
    `;

    if (chatMessages) {
      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble user-msg';
      msgEl.innerHTML = htmlContent;
      chatMessages.appendChild(msgEl);
    }
    
    if (tab6Messages) {
      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble user-msg';
      msgEl.innerHTML = htmlContent;
      tab6Messages.appendChild(msgEl);
    }
    scrollToBottom();
  }

  function appendAgentMessage(text, steps = [], toolsCalled = []) {
    let reasoningHtml = '';
    if (steps && steps.length > 0) {
      const toolSteps = steps.filter((s) => s.type === 'tool_call' || s.type === 'tool_result');
      if (toolSteps.length > 0) {
        const stepItems = steps
          .map((step) => {
            if (step.type === 'tool_call') {
              return `
                <div class="reasoning-step call">
                  <span class="step-badge">Tool Call</span>
                  <code>${escapeHtml(step.tool)}(${JSON.stringify(step.args || {})})</code>
                </div>
              `;
            } else if (step.type === 'tool_result') {
              return `
                <div class="reasoning-step result">
                  <span class="step-badge result">Result</span>
                  <pre><code>${escapeHtml(truncateStr(step.result, 400))}</code></pre>
                </div>
              `;
            }
            return '';
          })
          .join('');

        reasoningHtml = `
          <details class="agent-reasoning-trace">
            <summary>
              <span class="trace-icon">🔍</span>
              <span>Autonomous Reasoning Trace (${toolsCalled.length || toolSteps.length} step${toolSteps.length === 1 ? '' : 's'})</span>
            </summary>
            <div class="trace-body">
              ${stepItems}
            </div>
          </details>
        `;
      }
    }

    const formattedAnswer = formatMarkdown(text);
    const htmlContent = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">
        <div class="msg-sender">DemandSense Agent</div>
        ${reasoningHtml}
        <div class="msg-body">${formattedAnswer}</div>
      </div>
    `;

    if (chatMessages) {
      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble agent-msg';
      msgEl.innerHTML = htmlContent;
      chatMessages.appendChild(msgEl);
    }

    if (tab6Messages) {
      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble agent-msg';
      msgEl.innerHTML = htmlContent;
      tab6Messages.appendChild(msgEl);
    }

    scrollToBottom();
  }

  function appendAgentHtmlNode(htmlString) {
    if (chatMessages) {
      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble agent-msg';
      msgEl.innerHTML = htmlString;
      chatMessages.appendChild(msgEl);
    }
    
    if (tab6Messages) {
      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble agent-msg';
      msgEl.innerHTML = htmlString;
      tab6Messages.appendChild(msgEl);
    }
    scrollToBottom();
  }

  function appendTypingIndicator(label = 'Reasoning & executing tools...') {
    const id = 'typing_' + Date.now();
    const html = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
        <div class="typing-label">${escapeHtml(label)}</div>
      </div>
    `;

    if (chatMessages) {
      const el = document.createElement('div');
      el.id = id;
      el.className = 'ai-msg-bubble agent-msg typing';
      el.innerHTML = html;
      chatMessages.appendChild(el);
    }

    if (tab6Messages) {
      const elTab = document.createElement('div');
      elTab.id = id + '_tab';
      elTab.className = 'ai-msg-bubble agent-msg typing';
      elTab.innerHTML = html;
      tab6Messages.appendChild(elTab);
    }

    scrollToBottom();
    return id;
  }

  function removeTypingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
    const elTab = document.getElementById(id + '_tab');
    if (elTab) elTab.remove();
  }

  // ── Memory Reset ──
  async function handleResetMemory() {
    if (confirm('Reset agent conversation memory for a fresh session?')) {
      try {
        await fetch('/api/agent/reset', { method: 'POST' });
        if (chatMessages) chatMessages.innerHTML = '';
        if (tab6Messages) tab6Messages.innerHTML = '';
        renderWelcomeMessage();
      } catch (err) {
        console.error('Reset failed', err);
      }
    }
  }

  // ── Formatters & Utilities ──
  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    if (tab6Messages && tab6Messages.parentElement) {
      tab6Messages.parentElement.scrollTop = tab6Messages.parentElement.scrollHeight;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function truncateStr(str, maxLen = 300) {
    if (!str) return '';
    const s = String(str);
    return s.length > maxLen ? s.slice(0, maxLen) + '...' : s;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let out = escapeHtml(text);

    // Headers
    out = out.replace(/^#### (.*$)/gim, '<h5 class="chat-h5" style="margin:0.6rem 0 0.2rem 0;font-size:0.8rem;font-weight:700;">$1</h5>');
    out = out.replace(/^### (.*$)/gim, '<h4 class="chat-h4" style="margin:0.8rem 0 0.3rem 0;font-size:0.88rem;font-weight:700;">$1</h4>');
    out = out.replace(/^## (.*$)/gim, '<h3 class="chat-h3" style="margin:0.9rem 0 0.4rem 0;font-size:0.95rem;font-weight:700;">$1</h3>');
    out = out.replace(/^# (.*$)/gim, '<h2 class="chat-h2" style="margin:1rem 0 0.5rem 0;font-size:1.05rem;font-weight:700;">$1</h2>');

    // Bold / Italic
    out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code
    out = out.replace(/`([^`]+)`/g, '<code class="chat-code">$1</code>');

    // Numbered lists
    out = out.replace(/^(\d+)\.\s+(.*$)/gim, '<li class="chat-li"><strong>$1.</strong> $2</li>');

    // Bullet lists (Strip redundant markers like -, *, • so native disc bullet never doubles)
    out = out.replace(/^\s*[-*•]\s*(?:•\s*)?(.*$)/gim, '<li class="chat-li">$1</li>');

    // Wrap consecutive list items in ul/ol if needed
    out = out.replace(/(<li class="chat-li">.*?<\/li>\s*)+/g, '<ul class="chat-ul">$&</ul>');

    // Wrap in paragraphs
    out = out.replace(/\n\n/g, '</p><p>');
    out = '<p>' + out + '</p>';
    out = out.replace(/<p><\/p>/g, '');
    out = out.replace(/<p>\s*<ul/g, '<ul');
    out = out.replace(/<\/ul>\s*<\/p>/g, '</ul>');

    return out;
  }
})();
