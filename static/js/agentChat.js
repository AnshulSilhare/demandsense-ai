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

  // ── Initialize on DOMContentLoaded ──
  document.addEventListener('DOMContentLoaded', () => {
    initChatElements();
    initChatEventListeners();
    renderWelcomeMessage();
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

    // Escape closes drawer
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
      if (initialQuery === '__WARROOM__') {
        window.runWarRoom();
      } else if (initialQuery === '__SCENARIOS__') {
        window.runScenarioCopilot();
      } else {
        if (chatInput) chatInput.value = initialQuery;
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
    if (!chatMessages) return;
    chatMessages.innerHTML = `
      <div class="ai-msg-bubble agent-msg">
        <div class="msg-avatar">🤖</div>
        <div class="msg-content">
          <div class="msg-sender">DemandSense Autonomous Agent</div>
          <p>Hello! I am your <strong>Supply Chain Intelligence Agent</strong>. I can autonomously run forecasts, check warehouse inventory, calculate stockout risks, and simulate what-if scenarios across all 20 FMCG SKUs.</p>
          <p>Select an action below or ask any question in plain English:</p>
        </div>
      </div>
    `;

    renderSuggestionChips();
  }

  function renderSuggestionChips() {
    if (!chatChipsContainer) return;
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
        if (q === '__WARROOM__') {
          window.runWarRoom();
        } else if (q === '__SCENARIOS__') {
          window.runScenarioCopilot();
        } else {
          if (chatInput) chatInput.value = q;
          handleSendMessage();
        }
      });
    });
  }

  // ── Send Message & Agent Execution ──
  async function handleSendMessage() {
    if (isSending) return;
    const query = chatInput ? chatInput.value.trim() : '';
    if (!query) return;

    if (chatInput) chatInput.value = '';

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

    const sessionContext = {
      sku_id: window.state?.activeSku || window.state?.sku || 'SKU001',
      region: window.state?.activeRegion || window.state?.region || 'ALL',
      current_stock: window.state?.currentStock || window.state?.stock || 1500,
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

  // ── Mode C: Multi-Agent War Room ──
  window.runWarRoom = async function (customQuery) {
    if (isSending) return;
    const sku = window.state?.activeSku || window.state?.sku || 'SKU001';
    const query = customQuery || `Conduct a comprehensive War Room analysis for ${sku} evaluating demand trajectory, inventory coverage, and rupee financial risk.`;

    toggleChatPanel(true);
    appendUserMessage(`🏛️ War Room Request: ${sku}`);

    const typingId = appendTypingIndicator('War Room: 3 specialists analyzing in parallel...');
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

      // Render specialist reports
      let specialistCardsHtml = '';
      if (data.specialist_reports && data.specialist_reports.length > 0) {
        data.specialist_reports.forEach((r) => {
          const icon = r.icon || '🤖';
          const role = r.role || 'Specialist';
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
        });
      }

      const synthesisHtml = formatMarkdown(data.synthesis || '');

      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble agent-msg';
      msgEl.innerHTML = `
        <div class="msg-avatar">🏛️</div>
        <div class="msg-content">
          <div class="msg-sender">WAR ROOM — SPECIALIST COLLABORATION</div>
          <div class="warroom-grid">
            ${specialistCardsHtml}
          </div>
          <div class="warroom-synthesis">
            ${synthesisHtml}
          </div>
        </div>
      `;
      if (chatMessages) chatMessages.appendChild(msgEl);
      scrollToBottom();
    } catch (err) {
      removeTypingIndicator(typingId);
      appendAgentMessage(`⚠️ **Connection Error:** Could not reach War Room. (${err.message})`);
    } finally {
      isSending = false;
      if (chatSendBtn) chatSendBtn.disabled = false;
    }
  };

  // ── Mode E: Scenario Planning Copilot ──
  window.runScenarioCopilot = async function (skuId) {
    if (isSending) return;
    const targetSku = skuId || window.state?.activeSku || window.state?.sku || 'SKU001';
    const stock = window.state?.currentStock || window.state?.stock || 1500;

    toggleChatPanel(true);
    appendUserMessage(`🔮 Scenario Copilot: Benchmark 4 Strategies for ${targetSku}`);

    const typingId = appendTypingIndicator('Simulating 4 strategic scenarios & comparing...');
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

      let tableRows = '';
      (data.scenarios || []).forEach((s) => {
        const isRec = s.scenario_name === data.recommended_scenario;
        const rowClass = isRec ? 'scenario-row recommended' : 'scenario-row';
        const star = isRec ? ' ⭐' : '';
        tableRows += `
          <tr class="${rowClass}">
            <td><strong>${escapeHtml(s.scenario_name)}${star}</strong></td>
            <td>${Number(s.total_30d_forecast || 0).toLocaleString()}</td>
            <td>${s.days_of_supply || 0}d</td>
            <td>₹${Number(s.revenue_at_risk_inr || 0).toLocaleString()}</td>
            <td>${Number(s.recommended_po_qty || 0).toLocaleString()}</td>
            <td>₹${Number(s.recommended_po_value_inr || 0).toLocaleString()}</td>
          </tr>
        `;
      });

      const msgEl = document.createElement('div');
      msgEl.className = 'ai-msg-bubble agent-msg';
      msgEl.innerHTML = `
        <div class="msg-avatar">🔮</div>
        <div class="msg-content">
          <div class="msg-sender">SCENARIO PLANNING COPILOT</div>
          <p>Benchmarked 4 strategic scenarios for <strong>${escapeHtml(data.sku_id)}</strong> with ${stock.toLocaleString()} units on hand:</p>
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
          <div class="scenario-recommendation">
            <strong>🏆 Recommended Path:</strong> ${escapeHtml(data.recommended_scenario || 'N/A')}<br>
            <span style="font-size:0.76rem;color:var(--text2);margin-top:4px;display:block;">${escapeHtml(data.recommendation_rationale || '')}</span>
          </div>
        </div>
      `;
      if (chatMessages) chatMessages.appendChild(msgEl);
      scrollToBottom();
    } catch (err) {
      removeTypingIndicator(typingId);
      appendAgentMessage(`⚠️ **Connection Error:** Could not run scenario copilot. (${err.message})`);
    } finally {
      isSending = false;
      if (chatSendBtn) chatSendBtn.disabled = false;
    }
  };

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

  function appendTypingIndicator(label = 'Reasoning & executing tools...') {
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
        <div class="typing-label">${escapeHtml(label)}</div>
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

  // ── Memory Reset ──
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

  // ── Formatters & Utilities ──
  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
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

    // Bullet lists
    out = out.replace(/^\s*[-*]\s+(.*$)/gim, '<li class="chat-li">• $1</li>');

    // Wrap in paragraphs
    out = out.replace(/\n\n/g, '</p><p>');
    out = '<p>' + out + '</p>';
    out = out.replace(/<p><\/p>/g, '');

    return out;
  }
})();
