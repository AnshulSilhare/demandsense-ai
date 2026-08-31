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
