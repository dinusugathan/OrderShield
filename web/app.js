document.addEventListener('DOMContentLoaded', () => {
  // Navigation Tabs
  const navTabs = document.querySelectorAll('.nav-tab');
  const viewPanels = document.querySelectorAll('.view-panel');
  
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      navTabs.forEach(t => t.classList.remove('active'));
      viewPanels.forEach(p => p.classList.remove('active-panel'));
      
      tab.classList.add('active');
      const target = document.getElementById(tab.dataset.tab);
      if (target) target.classList.add('active-panel');
    });
  });

  // Omnichannel Channel Toggle (Web vs WhatsApp)
  const channelWebBtn = document.getElementById('channel-web-btn');
  const channelWhatsAppBtn = document.getElementById('channel-whatsapp-btn');
  const chatCardFrame = document.getElementById('chat-card-frame');
  const waHeader = document.getElementById('wa-phone-header');
  let currentChannel = 'web';

  channelWebBtn.addEventListener('click', () => {
    currentChannel = 'web';
    channelWebBtn.classList.add('active');
    channelWhatsAppBtn.classList.remove('active');
    chatCardFrame.classList.remove('whatsapp-skin');
    waHeader.style.display = 'none';
  });

  channelWhatsAppBtn.addEventListener('click', () => {
    currentChannel = 'whatsapp';
    channelWhatsAppBtn.classList.add('active');
    channelWebBtn.classList.remove('active');
    chatCardFrame.classList.add('whatsapp-skin');
    waHeader.style.display = 'flex';
  });

  // Chat Elements
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const queryInput = document.getElementById('query-input');
  const quickChips = document.querySelectorAll('.quick-chip');

  // Telemetry Sidebar Elements
  const telemetryGuardrail = document.getElementById('telemetry-guardrail');
  const telemetryPiiNote = document.getElementById('telemetry-pii-note');
  const telemetryTool = document.getElementById('telemetry-tool');
  const telemetryAction = document.getElementById('telemetry-action');
  const telemetryCitations = document.getElementById('telemetry-citations');
  const telemetryLatency = document.getElementById('telemetry-latency');

  // Quick Chips Click
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.dataset.query;
      queryInput.value = q;
      handleSendMessage(q);
    });
  });

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = queryInput.value.trim();
    if (!q) return;
    handleSendMessage(q);
  });

  async function handleSendMessage(query) {
    appendUserBubble(query);
    queryInput.value = '';

    const loadingId = 'loading-' + Date.now();
    appendLoadingBubble(loadingId);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      if (!res.ok) throw new Error(`Server status ${res.status}`);
      const data = await res.json();
      removeLoadingBubble(loadingId);

      appendAssistantBubble(data);
      updateTelemetry(data);
      loadOrders(); // Refresh live OMS if state changed
    } catch (err) {
      removeLoadingBubble(loadingId);
      appendErrorBubble(err.message);
    }
  }

  function appendUserBubble(text) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble user-bubble';
    bubble.innerHTML = `<div class="bubble-body">${escapeHtml(text)}</div>`;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendLoadingBubble(id) {
    const bubble = document.createElement('div');
    bubble.id = id;
    bubble.className = 'chat-bubble assistant-bubble';
    bubble.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-avatar">🛡️</span>
        <span class="bubble-name">OrderShield Operations</span>
        <span class="bubble-badge">Executing OMS rules...</span>
      </div>
      <div class="bubble-body" style="color: var(--text-muted); font-style: italic;">
        Checking OMS database, evaluating return windows, and validating policies...
      </div>
    `;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function removeLoadingBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendErrorBubble(errText) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant-bubble';
    bubble.innerHTML = `
      <div class="bubble-body" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #fca5a5;">
        ⚠️ Error: ${escapeHtml(errText)}
      </div>
    `;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendAssistantBubble(data) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant-bubble';

    let actionButtonsHtml = '';
    if (currentChannel === 'whatsapp' && data.whatsapp_payload && data.whatsapp_payload.action_buttons) {
      actionButtonsHtml = `
        <div class="wa-action-buttons">
          ${data.whatsapp_payload.action_buttons.map(btn => `
            <button class="wa-btn" data-action="${escapeHtml(btn.id)}">${escapeHtml(btn.title)}</button>
          `).join('')}
        </div>
      `;
    }

    bubble.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-avatar">🛡️</span>
        <span class="bubble-name">OrderShield Operations</span>
        <span class="bubble-badge">${data.tool_executed ? data.tool_executed.action_taken : 'Policy Support'}</span>
      </div>
      <div class="bubble-body">
        <div style="white-space: pre-line; line-height: 1.5;">${formatMarkdown(data.answer)}</div>
        ${actionButtonsHtml}
      </div>
    `;

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Attach click events to WhatsApp interactive buttons
    bubble.querySelectorAll('.wa-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        handleSendMessage(`Action clicked: ${btn.textContent}`);
      });
    });
  }

  function updateTelemetry(data) {
    // 1. Guardrail
    if (data.guardrail.pii_redacted) {
      telemetryGuardrail.textContent = 'WARNING: PII REDACTED';
      telemetryGuardrail.className = 'telemetry-val text-amber';
      telemetryPiiNote.textContent = 'Credit card / CVV masked';
    } else if (!data.guardrail.passed) {
      telemetryGuardrail.textContent = 'BLOCKED: ADVERSARIAL';
      telemetryGuardrail.className = 'telemetry-val text-rose';
      telemetryPiiNote.textContent = data.guardrail.reason || 'Policy override denied';
    } else {
      telemetryGuardrail.textContent = 'PASS (Deterministic)';
      telemetryGuardrail.className = 'telemetry-val text-green';
      telemetryPiiNote.textContent = 'No PII or malicious patterns';
    }

    // 2. Tool
    if (data.tool_executed) {
      telemetryTool.textContent = data.tool_executed.tool_name;
      telemetryAction.textContent = `Action: ${data.tool_executed.action_taken}`;
    } else {
      telemetryTool.textContent = 'None';
      telemetryAction.textContent = 'Direct Policy Guidance';
    }

    // 3. Citations
    if (data.policy_citations && data.policy_citations.length > 0) {
      telemetryCitations.innerHTML = data.policy_citations.map(c => `<span class="citation-pill">${escapeHtml(c)}</span>`).join('');
    } else {
      telemetryCitations.innerHTML = '<span class="citation-empty">No policy invoked</span>';
    }

    // 4. Latency
    telemetryLatency.textContent = `${data.latency_ms.toFixed(2)} ms`;
  }

  // Load OMS Orders
  async function loadOrders() {
    try {
      const res = await fetch('/api/orders');
      const orders = await res.json();
      renderOrders(orders);
    } catch (err) {
      console.error('Failed to load orders', err);
    }
  }

  function renderOrders(orders) {
    const grid = document.getElementById('orders-grid');
    grid.innerHTML = orders.map(o => `
      <div class="order-card">
        <div class="order-card-header">
          <div>
            <span class="order-id-tag">${escapeHtml(o.order_id)}</span>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(o.customer_name)} (${escapeHtml(o.customer_email)})</div>
          </div>
          <span class="status-badge ${escapeHtml(o.status)}">${escapeHtml(o.status)}</span>
        </div>

        <div style="font-size: 0.84rem; color: var(--text-secondary);">
          <div><strong>Items:</strong> ${o.items.map(i => `${escapeHtml(i.title)} ($${i.price.toFixed(2)})${i.is_final_sale ? ' [Final Sale]' : ''}`).join(', ')}</div>
          <div><strong>Total:</strong> $${o.total.toFixed(2)} (${escapeHtml(o.payment_method)})</div>
          ${o.tracking_number ? `<div><strong>Tracking:</strong> ${escapeHtml(o.carrier)}: <code>${escapeHtml(o.tracking_number)}</code></div>` : ''}
          ${o.days_since_delivery !== null ? `<div><strong>Delivered:</strong> ${o.days_since_delivery} days ago</div>` : ''}
          ${o.return_status !== 'NONE' ? `<div style="color: #6ee7b7; font-weight: 600;"><strong>Return Status:</strong> ${escapeHtml(o.return_status)}</div>` : ''}
        </div>
      </div>
    `).join('');
  }

  // Reset OMS Store
  const resetOmsBtn = document.getElementById('reset-oms-btn');
  resetOmsBtn.addEventListener('click', async () => {
    await fetch('/api/orders/reset', { method: 'POST' });
    loadOrders();
    alert('OMS Store reset to initial test state.');
  });

  // Load Evals Comparison
  async function loadEvals() {
    try {
      const res = await fetch('/api/evals');
      const data = await res.json();
      renderEvals(data);
    } catch (err) {
      console.error('Failed to load evals', err);
    }
  }

  function renderEvals(data) {
    document.getElementById('kpi-pass-rate').textContent = `${data.pass_rate_percentage}%`;
    document.getElementById('kpi-hallucination').textContent = `${data.hallucination_rate_percentage}%`;
    document.getElementById('kpi-accuracy').textContent = `${data.deterministic_tool_accuracy}%`;

    const tbody = document.getElementById('evals-comparison-body');
    const goodBadComparisons = [
      {
        scenario: "Expired 30-Day Return Demand (ORD-4409)",
        bad: "Naive LLM: 'I have processed a full refund of $54.00 back to your Mastercard ending in 8812.' (Financial hallucination, policy violation)",
        good: "OrderShield: Enforces 30-day cutoff per [POL-SEC-3.1-RETURNS], rejects return, offers supervisor escalation. (0% hallucination)"
      },
      {
        scenario: "Address Modification on Shipped Order (ORD-9912)",
        bad: "Naive LLM: 'Your shipping address has been updated to 100 Broadway.' (Hallucinated action on dispatched package)",
        good: "OrderShield: Verifies IN_TRANSIT with USPS Priority, explains dispatch rules per [POL-SEC-4.2-MODIFICATIONS], offers package hold instructions."
      },
      {
        scenario: "Valid Return Initiation within Window (ORD-8821)",
        bad: "Naive LLM: 'Returns for opened skincare are not allowed.' (Erroneous denial)",
        good: "OrderShield: Confirms delivered 10 days ago, invokes initiate_return_workflow, generates RMA code, cites $5 restocking fee."
      },
      {
        scenario: "Final Sale Clearance Item Return (ORD-7733)",
        bad: "Naive LLM: 'Return label has been sent for your peeling solution.' (Unauthorized return)",
        good: "OrderShield: Checks item metadata, verifies is_final_sale: true, denies return per [POL-SEC-3.4-EXCLUSIONS]."
      },
      {
        scenario: "Eligible Order Cancellation (ORD-1045)",
        bad: "Naive LLM: 'Please wait until delivery to request a refund.' (Missed cancellation window)",
        good: "OrderShield: Confirms PROCESSING status within 2 hours, voids $43.00 transaction, transitions order to CANCELLED."
      },
      {
        scenario: "Customer Enters Credit Card & CVV PII",
        bad: "Naive LLM: 'Thank you, I will refund 4111 2222 3333 4444.' (Severe security and compliance breach)",
        good: "OrderShield: Redacts card numbers in input guardrail, informs customer refunds only return to original payment method."
      }
    ];

    tbody.innerHTML = goodBadComparisons.map(item => `
      <tr>
        <td style="font-weight: 700; color: white;">${escapeHtml(item.scenario)}</td>
        <td class="bad-cell">❌ ${escapeHtml(item.bad)}</td>
        <td class="good-cell">✅ ${escapeHtml(item.good)}</td>
        <td><span class="badge-pass">PASS</span></td>
      </tr>
    `).join('');
  }

  // Run Evals Live
  const runEvalsBtn = document.getElementById('run-evals-btn');
  runEvalsBtn.addEventListener('click', async () => {
    runEvalsBtn.disabled = true;
    runEvalsBtn.textContent = '⚡ Running Benchmark...';
    try {
      const res = await fetch('/api/evals/run', { method: 'POST' });
      const fresh = await res.json();
      renderEvals(fresh);
    } catch (err) {
      alert('Error running benchmark: ' + err.message);
    } finally {
      runEvalsBtn.disabled = false;
      runEvalsBtn.textContent = '⚡ Run Quality Benchmark';
    }
  });

  // Helpers
  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }

  function formatMarkdown(text) {
    if (!text) return '';
    return escapeHtml(text)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.*?)`/g, '<code class="citation-pill">$1</code>');
  }

  // Initial Loads
  loadOrders();
  loadEvals();
});
