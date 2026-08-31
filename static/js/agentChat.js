/**
 * DemandSense AI — Autonomous Agent Chat Controller
 * ====================================================
 * Manages the floating AI assistant drawer, ReAct reasoning trace viewer,
 * proactive portfolio briefs, and multi-turn conversational queries.
 *
 * Author: Anshul Silhare
 */

(function () {
  'use strict';

  // ── DOM Elements ──
  let chatFab = null;
  let chatPanel = null;
  let chatOverlay = null;
  let chatCloseBtn = null;
  let chatResetBtn = null;
  let chatMessages = null;
  let chatInput = null;
  let chatSendBtn = null;
  let chatChipsContainer = null;
  let isSending = false;

  // ── Initialize on DOMContentLoaded ──
  document.addEventListener('DOMContentLoaded', () => {
    initChatElements();
    initChatEventListeners();
    renderWelcomeMessage();
  });

  function initChatElements() {
    chatFab = document.getElementById('aiChatFab');
    chatPanel = document.getElementById('aiChatPanel');
    chatOverlay = document.getElementById('aiChatOverlay');
    chatCloseBtn = document.getElementById('aiChatClose');
    chatResetBtn = document.getElementById('aiChatReset');
    chatMessages = document.getElementById('aiChatMessages');
    chatInput = document.getElementById('aiChatInput');
    chatSendBtn = document.getElementById('aiChatSend');
    chatChipsContainer = document.getElementById('aiChatChips');
  }

  function initChatEventListeners() {
    if (chatFab) {
      chatFab.addEventListener('click', () => toggleChatPanel(true));
    }
    if (chatCloseBtn) {
      chatCloseBtn.addEventListener('click', () => toggleChatPanel(false));
    }
    if (chatOverlay) {
      chatOverlay.addEventListener('click', () => toggleChatPanel(false));
    }
    if (chatResetBtn) {
      chatResetBtn.addEventListener('click', handleResetMemory);
    }
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
    }

    // Keyboard shortcut: Escape closes chat
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && chatPanel && chatPanel.classList.contains('open')) {
        toggleChatPanel(false);
      }
    });
  }

  // ── Open / Close Panel ──
  window.openAgentChat = function (initialQuery = null) {
    toggleChatPanel(true);
    if (initialQuery && typeof initialQuery === 'string') {
      if (chatInput) chatInput.value = initialQuery;
      handleSendMessage();
    }
  };

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

  // ── Welcome Message & Starter Chips ──
  function renderWelcomeMessage() {
    if (!chatMessages) return;
    chatMessages.innerHTML = `
      <div class="ai-msg-bubble agent-msg">
        <div class="msg-avatar">🤖</div>
        <div class="msg-content">
          <div class="msg-sender">DemandSense Autonomous Agent</div>
          <p>Hello! I am your <strong>Supply Chain Intelligence Agent</strong>. I can autonomously run forecasts, check warehouse inventory, calculate stockout risks, and simulate what-if scenarios across all 20 FMCG SKUs.</p>
          <p>What would you like to analyze?</p>
        </div>
      </div>
    `;

    renderSuggestionChips();
  }

  function renderSuggestionChips() {
    if (!chatChipsContainer) return;
    const currentSku = window.state?.activeSku || 'SKU001';
    const chips = [
      { label: '\U0001f3db\ufe0f War Room Analysis', query: '__WARROOM__' },
      { label: '\U0001f52e Scenario Copilot', query: '__SCENARIOS__' },
      { label: '\U0001f4cb Morning Portfolio Brief', query: 'Generate an executive portfolio brief for all 20 SKUs.' },
      { label: '\U0001f4e6 Reorder Check: ' + currentSku, query: 'Should I place a purchase order for ' + currentSku + ' based on current forecast?' },
      { label: '\U0001f389 Festival Demand Spikes', query: 'What Indian festivals are coming up in the next 60 days and which SKUs will spike?' },
      { label: '\u26a1 Run What-If Simulation', query: 'Simulate a 15% promotion and 3-day supplier delay for ' + currentSku + '.' },
    ];
    // ALREADY_DEFINED

    chatChipsContainer.innerHTML = chips
      .map(
        (chip) => `
        <button class="chat-chip-btn" data-query="${escapeHtml(chip.query)}">
          ${chip.label}
        </button>
      `
      )
      .join('');

    chatChipsContainer.querySelectorAll('.chat-chip-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const q = btn.getAttribute('data-query');
        if (chatInput) chatInput.value = q;
        handleSendMessage();
      });
    });
  }

  // ── Send User Message & Execute Agent Query ──
  async function handleSendMessage() {
    if (isSending) return;
    const query = chatInput ? chatInput.value.trim() : '';
    if (!query) return;

    if (chatInput) chatInput.value = '';

    appendUserMessage(query);

    const typingId = appendTypingIndicator();
    isSending = true;
    if (chatSendBtn) chatSendBtn.disabled = true;

    const sessionContext = {
      sku_id: window.state?.activeSku || 'SKU001',
      region: window.state?.activeRegion || 'ALL',
      current_stock: window.state?.currentStock || 1500,
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

      const data = await response.json();
      removeTypingIndicator(typingId);

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

  // ── Render Message Elements ──
  function appendUserMessage(text) {
    if (!chatMessages) return;
    const msgEl = document.createElement('div');
    msgEl.className = 'ai-msg-bubble user-msg';
    msgEl.innerHTML = `
      <div class="msg-content">
        <p>${escapeHtml(text)}</p>
      </div>
      <div class="msg-avatar user-av">👤</div>
    `;
    chatMessages.appendChild(msgEl);
    scrollToBottom();
  }

  function appendAgentMessage(text, steps = [], toolsCalled = []) {
    if (!chatMessages) return;
    const msgEl = document.createElement('div');
    msgEl.className = 'ai-msg-bubble agent-msg';

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
              <span>Autonomous Reasoning Trace (${toolsCalled.length} tool${toolsCalled.length === 1 ? '' : 's'} executed)</span>
            </summary>
            <div class="trace-body">
              ${stepItems}
            </div>
          </details>
        `;
      }
    }

    const formattedAnswer = formatMarkdown(text);

    msgEl.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">
        <div class="msg-sender">DemandSense Agent</div>
        ${reasoningHtml}
        <div class="msg-body">${formattedAnswer}</div>
      </div>
    `;
    chatMessages.appendChild(msgEl);
    scrollToBottom();
  }

  function appendTypingIndicator() {
    if (!chatMessages) return null;
    const id = 'typing_' + Date.now();
    const el = document.createElement('div');
    el.id = id;
    el.className = 'ai-msg-bubble agent-msg typing';
    el.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
        <div class="typing-label">Reasoning & calling tools...</div>
      </div>
    `;
    chatMessages.appendChild(el);
    scrollToBottom();
    return id;
  }

  function removeTypingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // ── Reset Conversation Memory ──
  async function handleResetMemory() {
    if (confirm('Reset agent conversation memory for a fresh session?')) {
      try {
        await fetch('/api/agent/reset', { method: 'POST' });
        if (chatMessages) {
          chatMessages.innerHTML = '';
          renderWelcomeMessage();
        }
      } catch (err) {
        console.error('Reset failed', err);
      }
    }
  }

  // ── Helpers ──
  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function truncateStr(str, maxLen = 300) {
    if (!str) return '';
    return str.length > maxLen ? str.slice(0, maxLen) + '...' : str;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let out = escapeHtml(text);

    // Headers
    out = out.replace(/^### (.*$)/gim, '<h4 class="chat-h4">$1</h4>');
    out = out.replace(/^## (.*$)/gim, '<h3 class="chat-h3">$1</h3>');
    out = out.replace(/^# (.*$)/gim, '<h2 class="chat-h2">$1</h2>');

    // Bold / Italic
    out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code
    out = out.replace(/`([^`]+)`/g, '<code class="chat-code">$1</code>');

    // Lists (bullets)
    out = out.replace(/^\s*[-*]\s+(.*$)/gim, '<li class="chat-li">$1</li>');

    // Paragraphs
    out = out.replace(/\n\n/g, '</p><p>');
    out = '<p>' + out + '</p>';
    out = out.replace(/<p><\/p>/g, '');

    return out;
  }
})();


// ═══ OPTION A: AUTONOMOUS MONITORING (Periodic Background Scan) ═══
(function() {
  const MONITOR_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
  let monitorTimer = null;
  let lastRiskCount = 0;

  function startAutonomousMonitoring() {
    if (monitorTimer) return;
    console.log('[Agent Monitor] Autonomous monitoring started (5-min interval)');

    monitorTimer = setInterval(async () => {
      try {
        const res = await fetch('/api/agent/brief', { method: 'POST' });
        if (!res.ok) return;
        const data = await res.json();
        const critCount = (data.critical_skus || []).length;

        // Update FAB badge
        const badge = document.getElementById('aiFabBadge');
        if (badge && critCount > 0) {
          badge.style.display = 'block';
          badge.textContent = critCount;
        }

        // If new risks detected since last scan, update banner
        if (critCount > lastRiskCount && critCount > 0) {
          const banner = document.getElementById('agentAlertBanner');
          const alertText = document.getElementById('agentAlertText');
          if (banner && alertText) {
            const topSku = data.critical_skus[0];
            alertText.innerHTML = '<strong>\u26a0\ufe0f Live Monitor Alert:</strong> ' + critCount +
              ' SKU(s) at risk. Top: <strong>' + topSku.name + '</strong> (' + topSku.days_of_supply +
              ' DOS). Portfolio Risk: <strong>\u20b9' + Number(data.total_risk_inr || 0).toLocaleString() + '</strong>';
            banner.style.display = 'flex';
          }
        }
        lastRiskCount = critCount;
      } catch (e) {
        console.warn('[Agent Monitor] Scan failed:', e);
      }
    }, MONITOR_INTERVAL_MS);
  }

  // Start monitoring after page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startAutonomousMonitoring);
  } else {
    startAutonomousMonitoring();
  }
})();


// ═══ OPTION C: WAR ROOM MODE ═══
window.runWarRoom = async function(query) {
  const chatMessages = document.getElementById('aiChatMessages');
  const chatPanel = document.getElementById('aiChatPanel');
  if (chatPanel && !chatPanel.classList.contains('open')) {
    if (window.openAgentChat) window.openAgentChat();
  }

  // Show user message
  const userEl = document.createElement('div');
  userEl.className = 'ai-msg-bubble user-msg';
  userEl.innerHTML = '<div class="msg-content"><p>' + query + '</p></div><div class="msg-avatar user-av">\ud83d\udc64</div>';
  if (chatMessages) chatMessages.appendChild(userEl);

  // Show typing
  const typingEl = document.createElement('div');
  typingEl.className = 'ai-msg-bubble agent-msg typing';
  typingEl.id = 'warroom_typing';
  typingEl.innerHTML = '<div class="msg-avatar">\U0001f3db\ufe0f</div><div class="msg-content"><div class="typing-indicator"><span></span><span></span><span></span></div><div class="typing-label">War Room: 3 specialists analyzing...</div></div>';
  if (chatMessages) chatMessages.appendChild(typingEl);
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const sessionContext = {
      sku_id: window.state?.activeSku || window.state?.sku || 'SKU001',
      current_stock: window.state?.currentStock || window.state?.stock || 1500,
    };

    const res = await fetch('/api/agent/warroom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, session_context: sessionContext }),
    });
    const data = await res.json();

    // Remove typing
    const t = document.getElementById('warroom_typing');
    if (t) t.remove();

    // Render specialist reports
    const msgEl = document.createElement('div');
    msgEl.className = 'ai-msg-bubble agent-msg';

    let specialistHtml = '';
    if (data.specialist_reports) {
      data.specialist_reports.forEach(function(r) {
        specialistHtml += '<div class="warroom-specialist-card">' +
          '<div class="specialist-header"><span class="specialist-icon">' + (r.icon || '\U0001f916') + '</span>' +
          '<strong>' + (r.role || 'Specialist') + '</strong></div>' +
          '<div class="specialist-analysis"><p>' + (r.analysis || 'No analysis.').replace(/\n/g, '<br>') + '</p></div></div>';
      });
    }

    const synthesis = (data.synthesis || '').replace(/\n/g, '<br>');

    msgEl.innerHTML = '<div class="msg-avatar">\U0001f3db\ufe0f</div><div class="msg-content">' +
      '<div class="msg-sender">WAR ROOM — MULTI-AGENT ANALYSIS</div>' +
      '<div class="warroom-grid">' + specialistHtml + '</div>' +
      '<div class="warroom-synthesis">' + synthesis + '</div></div>';

    if (chatMessages) chatMessages.appendChild(msgEl);
    if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
  } catch (err) {
    const t = document.getElementById('warroom_typing');
    if (t) t.remove();
    console.error('[WarRoom] Error:', err);
  }
};


// ═══ OPTION E: SCENARIO COPILOT ═══
window.runScenarioCopilot = async function(skuId) {
  const chatMessages = document.getElementById('aiChatMessages');
  const chatPanel = document.getElementById('aiChatPanel');
  if (chatPanel && !chatPanel.classList.contains('open')) {
    if (window.openAgentChat) window.openAgentChat();
  }

  skuId = skuId || window.state?.activeSku || window.state?.sku || 'SKU001';
  const stock = window.state?.currentStock || window.state?.stock || 1500;

  // User message
  const userEl = document.createElement('div');
  userEl.className = 'ai-msg-bubble user-msg';
  userEl.innerHTML = '<div class="msg-content"><p>Run scenario comparison for ' + skuId + '</p></div><div class="msg-avatar user-av">\ud83d\udc64</div>';
  if (chatMessages) chatMessages.appendChild(userEl);

  // Typing
  const typingEl = document.createElement('div');
  typingEl.className = 'ai-msg-bubble agent-msg typing';
  typingEl.id = 'scenario_typing';
  typingEl.innerHTML = '<div class="msg-avatar">\U0001f52e</div><div class="msg-content"><div class="typing-indicator"><span></span><span></span><span></span></div><div class="typing-label">Generating 4 scenarios & comparing...</div></div>';
  if (chatMessages) chatMessages.appendChild(typingEl);
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const res = await fetch('/api/agent/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sku_id: skuId, current_stock: stock }),
    });
    const data = await res.json();

    const t = document.getElementById('scenario_typing');
    if (t) t.remove();

    // Build comparison table
    let tableRows = '';
    (data.scenarios || []).forEach(function(s) {
      const isRec = s.scenario_name === data.recommended_scenario;
      const rowClass = isRec ? 'scenario-row recommended' : 'scenario-row';
      tableRows += '<tr class="' + rowClass + '">' +
        '<td>' + s.scenario_name + (isRec ? ' \u2b50' : '') + '</td>' +
        '<td>' + (s.total_30d_forecast || 0).toLocaleString() + '</td>' +
        '<td>' + (s.days_of_supply || 0) + '</td>' +
        '<td>\u20b9' + (s.revenue_at_risk_inr || 0).toLocaleString() + '</td>' +
        '<td>' + (s.recommended_po_qty || 0).toLocaleString() + '</td>' +
        '<td>\u20b9' + (s.recommended_po_value_inr || 0).toLocaleString() + '</td></tr>';
    });

    const msgEl = document.createElement('div');
    msgEl.className = 'ai-msg-bubble agent-msg';
    msgEl.innerHTML = '<div class="msg-avatar">\U0001f52e</div><div class="msg-content">' +
      '<div class="msg-sender">SCENARIO PLANNING COPILOT</div>' +
      '<div class="scenario-table-wrap"><table class="scenario-table">' +
      '<thead><tr><th>Scenario</th><th>30d Forecast</th><th>DOS</th><th>Rev. at Risk</th><th>PO Qty</th><th>PO Value</th></tr></thead>' +
      '<tbody>' + tableRows + '</tbody></table></div>' +
      '<div class="scenario-recommendation"><strong>\U0001f3c6 Recommended:</strong> ' +
      (data.recommended_scenario || 'N/A') + '<br><em>' +
      (data.recommendation_rationale || '') + '</em></div></div>';

    if (chatMessages) chatMessages.appendChild(msgEl);
    if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
  } catch (err) {
    const t = document.getElementById('scenario_typing');
    if (t) t.remove();
    console.error('[Scenario Copilot] Error:', err);
  }
};
