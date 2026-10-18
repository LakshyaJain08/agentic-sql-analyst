/**
 * Agentic AI Data Analyst - Modern ES6 Client Application
 * Unified Professional Single-Color Theme (Corporate Slate & Cobalt Blue)
 */

// Application State
const state = {
  activeMode: 'nl', // 'nl' or 'sql'
  provider: localStorage.getItem('analyst_provider') || 'mock',
  apiKey: localStorage.getItem('analyst_api_key') || '',
  currentResult: null,
  tableData: [],
  tableColumns: [],
  sortCol: null,
  sortAsc: true,
  followUpHistory: []
};

// DOM Element Selectors
const elements = {
  nlTabBtn: document.getElementById('tab-btn-nl'),
  sqlTabBtn: document.getElementById('tab-btn-sql'),
  nlSection: document.getElementById('section-nl'),
  sqlSection: document.getElementById('section-sql'),
  nlInput: document.getElementById('nl-query-input'),
  btnRunNl: document.getElementById('btn-run-nl'),
  btnClearNl: document.getElementById('btn-clear-nl'),
  sqlInput: document.getElementById('custom-sql-input'),
  sqlQuestionInput: document.getElementById('custom-sql-question'),
  btnRunSql: document.getElementById('btn-run-sql'),
  btnClearSql: document.getElementById('btn-clear-sql'),
  stepper: document.getElementById('stepper-box'),
  stepperHeader: document.getElementById('stepper-header-text'),
  resultsWrapper: document.getElementById('results-wrapper'),
  executiveCard: document.getElementById('executive-card'),
  executiveAnswer: document.getElementById('executive-answer-body'),
  alertCard: document.getElementById('alert-card'),
  alertMessage: document.getElementById('alert-message'),
  chartBox: document.getElementById('chart-container'),
  tableRowsCount: document.getElementById('table-rows-count'),
  tableSearch: document.getElementById('table-search-input'),
  tableThead: document.getElementById('results-thead'),
  tableTbody: document.getElementById('results-tbody'),
  btnDownloadCsv: document.getElementById('btn-download-csv'),
  sqlCodeBlock: document.getElementById('sql-code-block'),
  btnCopySql: document.getElementById('btn-copy-sql'),
  sqlExecTime: document.getElementById('sql-exec-time'),
  telemetryJson: document.getElementById('telemetry-json'),
  followupInput: document.getElementById('followup-input'),
  btnAskFollowup: document.getElementById('btn-ask-followup'),
  followupList: document.getElementById('followup-list'),
  schemaModal: document.getElementById('schema-modal'),
  btnOpenSchema: document.getElementById('btn-open-schema'),
  btnCloseSchema: document.getElementById('btn-close-schema'),
  schemaContent: document.getElementById('schema-modal-content'),
  settingsModal: document.getElementById('settings-modal'),
  btnOpenSettings: document.getElementById('btn-open-settings'),
  btnCloseSettings: document.getElementById('btn-close-settings'),
  providerSelect: document.getElementById('setting-provider-select'),
  apiKeyInput: document.getElementById('setting-api-key-input'),
  btnSaveSettings: document.getElementById('btn-save-settings')
};

// Monochromatic Single-Theme Enterprise Palette
const BRAND_PRIMARY = '#2563eb';
const BRAND_LIGHT = '#3b82f6';
const BRAND_HOVER = '#1d4ed8';
const BRAND_SUBTLE = 'rgba(37, 99, 235, 0.12)';
const BRAND_BORDER = 'rgba(37, 99, 235, 0.35)';

// --------------------------------------------------------------------------
// Initialization
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  checkBackendHealth();
  if (elements.providerSelect) elements.providerSelect.value = state.provider;
  if (elements.apiKeyInput) elements.apiKeyInput.value = state.apiKey;
});

function setupEventListeners() {
  // Mode Tabs
  elements.nlTabBtn.addEventListener('click', () => switchMode('nl'));
  elements.sqlTabBtn.addEventListener('click', () => switchMode('sql'));

  // Suggested Chips
  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt');
      if (prompt) {
        elements.nlInput.value = prompt;
        runNLAnalysis();
      }
    });
  });

  // Run NL Query
  elements.btnRunNl.addEventListener('click', runNLAnalysis);
  elements.nlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runNLAnalysis();
  });
  elements.btnClearNl.addEventListener('click', () => {
    elements.nlInput.value = '';
    hideResults();
  });

  // Run Custom SQL
  elements.btnRunSql.addEventListener('click', runCustomSQLAnalysis);
  elements.btnClearSql.addEventListener('click', () => {
    elements.sqlInput.value = '';
    elements.sqlQuestionInput.value = '';
    hideResults();
  });

  // Result Tabs
  document.querySelectorAll('.rtab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.rtab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.rtab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add('active');
    });
  });

  // Table Search & CSV Download
  elements.tableSearch.addEventListener('input', filterTable);
  elements.btnDownloadCsv.addEventListener('click', downloadTableCsv);

  // Copy SQL
  elements.btnCopySql.addEventListener('click', copySqlToClipboard);

  // Follow-Up Q&A
  elements.btnAskFollowup.addEventListener('click', runFollowUp);
  elements.followupInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runFollowUp();
  });

  document.querySelectorAll('.fu-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      elements.followupInput.value = btn.getAttribute('data-fu');
      runFollowUp();
    });
  });

  // Modals
  elements.btnOpenSchema.addEventListener('click', openSchemaModal);
  elements.btnCloseSchema.addEventListener('click', () => elements.schemaModal.classList.remove('open'));
  elements.btnOpenSettings.addEventListener('click', () => elements.settingsModal.classList.add('open'));
  elements.btnCloseSettings.addEventListener('click', () => elements.settingsModal.classList.remove('open'));

  elements.btnSaveSettings.addEventListener('click', () => {
    state.provider = elements.providerSelect.value;
    state.apiKey = elements.apiKeyInput.value.trim();
    localStorage.setItem('analyst_provider', state.provider);
    localStorage.setItem('analyst_api_key', state.apiKey);
    elements.settingsModal.classList.remove('open');
    showNotification('Configuration saved successfully');
  });
}

function switchMode(mode) {
  state.activeMode = mode;
  if (mode === 'nl') {
    elements.nlTabBtn.classList.add('active');
    elements.sqlTabBtn.classList.remove('active');
    elements.nlSection.style.display = 'block';
    elements.sqlSection.style.display = 'none';
  } else {
    elements.sqlTabBtn.classList.add('active');
    elements.nlTabBtn.classList.remove('active');
    elements.nlSection.style.display = 'none';
    elements.sqlSection.style.display = 'block';
  }
}

// --------------------------------------------------------------------------
// API Calls & Execution
// --------------------------------------------------------------------------
async function checkBackendHealth() {
  try {
    const res = await fetch('/health');
    if (res.ok) {
      const data = await res.json();
      document.getElementById('status-pill').innerHTML = `<span class="pulse-dot"></span> ${data.database.dialect.toUpperCase()} Connected`;
    }
  } catch (err) {
    document.getElementById('status-pill').innerHTML = `<span class="pulse-dot" style="background: #ef4444;"></span> Offline`;
  }
}

async function runNLAnalysis() {
  const query = elements.nlInput.value.trim();
  if (!query) return;

  hideResults();
  showStepper('Executing Analytical Pipeline...');

  animateStep(1); // Interpreting
  await sleep(220);
  animateStep(2); // Retrieving Schema
  await sleep(180);
  animateStep(3); // Generating SQL

  try {
    const response = await fetch('/api/v1/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: query,
        provider: state.provider,
        api_key: state.apiKey || null
      })
    });

    animateStep(4); // Validating AST
    await sleep(180);
    animateStep(5); // Executing

    const data = await response.json();
    animateStep(6); // Grounded Answer
    await sleep(200);

    hideStepper();
    renderResults(data);
  } catch (error) {
    hideStepper();
    showErrorAlert(`Connection error: ${error.message}`);
  }
}

async function runCustomSQLAnalysis() {
  const sql = elements.sqlInput.value.trim();
  const question = elements.sqlQuestionInput.value.trim();
  if (!sql) return;

  hideResults();
  showStepper('Validating & Executing SQL...');

  animateStep(4); // Validating
  await sleep(200);
  animateStep(5); // Executing

  try {
    const response = await fetch('/api/v1/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sql: sql,
        question: question || 'Summarize key analytical findings from this query.',
        provider: state.provider,
        api_key: state.apiKey || null
      })
    });

    const data = await response.json();
    animateStep(6);
    await sleep(200);

    hideStepper();
    renderResults(data);
  } catch (error) {
    hideStepper();
    showErrorAlert(`Execution error: ${error.message}`);
  }
}

async function runFollowUp() {
  const question = elements.followupInput.value.trim();
  if (!question || !state.currentResult || !state.currentResult.rows) return;

  elements.btnAskFollowup.disabled = true;
  elements.btnAskFollowup.innerText = 'Analyzing...';

  try {
    const response = await fetch('/api/v1/follow-up', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        sql: state.currentResult.sql,
        columns: state.currentResult.columns,
        rows: state.currentResult.rows,
        provider: state.provider,
        api_key: state.apiKey || null
      })
    });

    const data = await response.json();
    elements.followupInput.value = '';

    // Append Chat Bubble
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.innerHTML = `
      <div class="chat-q">Q: ${escapeHtml(question)}</div>
      <div class="chat-a">${formatMarkdown(data.answer)}</div>
    `;
    elements.followupList.prepend(bubble);
  } catch (err) {
    showNotification(`Follow-up inquiry failed: ${err.message}`);
  } finally {
    elements.btnAskFollowup.disabled = false;
    elements.btnAskFollowup.innerText = 'Analyze';
  }
}

// --------------------------------------------------------------------------
// Result Rendering
// --------------------------------------------------------------------------
function renderResults(data) {
  state.currentResult = data;
  state.tableData = data.rows || [];
  state.tableColumns = data.columns || [];
  elements.resultsWrapper.style.display = 'block';

  // Handle Ambiguity & Unsupported Status
  if (data.status === 'clarification_required') {
    showWarningAlert(`<strong>Clarification Required</strong>: ${data.clarification_question || data.answer}`);
    elements.executiveCard.style.display = 'none';
    document.querySelector('.result-tabs').style.display = 'none';
    document.querySelectorAll('.rtab-panel').forEach(p => p.style.display = 'none');
    return;
  }

  if (data.status === 'unsupported') {
    showErrorAlert(`<strong>Inquiry Notice</strong>: ${data.unsupported_reason || data.answer}`);
    elements.executiveCard.style.display = 'none';
    document.querySelector('.result-tabs').style.display = 'none';
    document.querySelectorAll('.rtab-panel').forEach(p => p.style.display = 'none');
    return;
  }

  if (data.status === 'validation_failed' || data.status === 'execution_error') {
    showErrorAlert(data.answer);
    elements.executiveCard.style.display = 'none';
    return;
  }

  // Success Mode
  elements.alertCard.style.display = 'none';
  elements.executiveCard.style.display = 'block';
  document.querySelector('.result-tabs').style.display = 'flex';
  document.querySelectorAll('.rtab-panel').forEach(p => p.style.display = '');

  // Render Executive Answer
  elements.executiveAnswer.innerHTML = formatMarkdown(data.answer);

  // Render Chart
  renderChart(data);

  // Render Data Table
  renderTable(state.tableData, state.tableColumns);

  // Render SQL & Telemetry
  elements.sqlCodeBlock.innerText = data.sql || '-- No SQL query generated';
  elements.sqlExecTime.innerText = `Execution: ${data.execution_ms || 0} ms`;
  elements.telemetryJson.innerText = JSON.stringify(data.audit_trail || [], null, 2);

  // Reset Follow-Up Section
  elements.followupList.innerHTML = '';
}

// --------------------------------------------------------------------------
// Monochromatic SVG Chart Engine
// --------------------------------------------------------------------------
function renderChart(data) {
  const chartInfo = data.chart;
  elements.chartBox.innerHTML = '';

  if (!chartInfo || chartInfo.type === 'empty' || !data.rows || data.rows.length === 0) {
    elements.chartBox.innerHTML = `<div class="chart-empty-state">No chart available for this result set.</div>`;
    return;
  }

  // 1. KPI Metric Card
  if (chartInfo.type === 'metric') {
    elements.chartBox.innerHTML = `
      <div class="metric-card-display">
        <div class="metric-card-lbl">${escapeHtml(chartInfo.title || 'Aggregate Value')}</div>
        <div class="metric-card-val">${escapeHtml(chartInfo.value || '0')}</div>
        <div class="metric-card-badge">Verified Relational Metric</div>
      </div>
    `;
    return;
  }

  const rows = data.rows;
  const xKey = chartInfo.x || data.columns[0];
  const yKey = chartInfo.y || data.columns[1] || data.columns[0];
  const chartType = chartInfo.type || 'bar';

  // SVG dimensions
  const width = elements.chartBox.clientWidth || 900;
  const height = 340;
  const padding = { top: 30, right: 30, bottom: 50, left: 70 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  // Extract Numeric Values
  const yValues = rows.map(r => Number(r[yKey]) || 0);
  const minY = Math.min(0, Math.min(...yValues));
  const maxY = Math.max(...yValues) * 1.15 || 100;

  const yScale = val => plotHeight - ((val - minY) / (maxY - minY)) * plotHeight;
  const xScale = idx => (idx / Math.max(1, rows.length - (chartType === 'line' ? 1 : 0))) * plotWidth;

  let svgContent = '';

  // Background Grid Lines & Y Axis Labels
  for (let i = 0; i <= 4; i++) {
    const yVal = minY + (i / 4) * (maxY - minY);
    const yPos = padding.top + yScale(yVal);
    svgContent += `
      <line x1="${padding.left}" y1="${yPos}" x2="${width - padding.right}" y2="${yPos}" stroke="#1f293d" stroke-dasharray="3,3" />
      <text x="${padding.left - 12}" y="${yPos + 4}" fill="#64748b" font-size="11" text-anchor="end" font-family="'JetBrains Mono', monospace">${formatNumber(yVal)}</text>
    `;
  }

  if (chartType === 'line') {
    // Generate SVG Line & Gradient Area
    let pathD = '';
    let areaD = `M ${padding.left} ${padding.top + yScale(minY)} `;

    rows.forEach((r, idx) => {
      const xPos = padding.left + xScale(idx);
      const yPos = padding.top + yScale(r[yKey] || 0);
      pathD += `${idx === 0 ? 'M' : 'L'} ${xPos} ${yPos} `;
      areaD += `L ${xPos} ${yPos} `;
    });

    areaD += `L ${padding.left + xScale(rows.length - 1)} ${padding.top + yScale(minY)} Z`;

    svgContent += `
      <defs>
        <linearGradient id="chartBlueGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${BRAND_PRIMARY}" stop-opacity="0.30"/>
          <stop offset="100%" stop-color="${BRAND_PRIMARY}" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      <path d="${areaD}" fill="url(#chartBlueGrad)" />
      <path d="${pathD}" fill="none" stroke="${BRAND_PRIMARY}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
    `;

    // Data Points
    rows.forEach((r, idx) => {
      const xPos = padding.left + xScale(idx);
      const yPos = padding.top + yScale(r[yKey] || 0);
      svgContent += `
        <circle cx="${xPos}" cy="${yPos}" r="4.5" fill="#0b0f17" stroke="${BRAND_LIGHT}" stroke-width="2" />
        <text x="${xPos}" y="${height - padding.bottom + 22}" fill="#94a3b8" font-size="11" text-anchor="middle">${escapeHtml(String(r[xKey]))}</text>
      `;
    });
  } else {
    // Monochromatic Bar Chart
    const barWidth = Math.min(44, Math.max(16, (plotWidth / rows.length) * 0.65));
    const stepX = plotWidth / rows.length;

    rows.forEach((r, idx) => {
      const val = r[yKey] || 0;
      const barH = Math.max(2, plotHeight - yScale(val));
      const xPos = padding.left + idx * stepX + (stepX - barWidth) / 2;
      const yPos = padding.top + yScale(val);

      svgContent += `
        <rect x="${xPos}" y="${yPos}" width="${barWidth}" height="${barH}" rx="4" fill="${BRAND_PRIMARY}" opacity="0.92" />
        <text x="${xPos + barWidth / 2}" y="${yPos - 6}" fill="#cbd5e1" font-size="11" text-anchor="middle" font-family="'JetBrains Mono', monospace">${formatNumber(val)}</text>
        <text x="${xPos + barWidth / 2}" y="${height - padding.bottom + 22}" fill="#94a3b8" font-size="11" text-anchor="middle">${truncate(String(r[xKey]), 12)}</text>
      `;
    });
  }

  elements.chartBox.innerHTML = `
    <div class="chart-header">
      <div class="chart-title">${escapeHtml(chartInfo.title || `${yKey} by ${xKey}`)}</div>
      <span class="badge">Visual Breakdown</span>
    </div>
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow: visible;">
      ${svgContent}
    </svg>
  `;
}

// --------------------------------------------------------------------------
// Table Engine (Sort, Search, CSV Export)
// --------------------------------------------------------------------------
function renderTable(rows, columns) {
  elements.tableRowsCount.innerText = `${rows.length} rows returned`;

  // Render Thead
  elements.tableThead.innerHTML = `
    <tr>
      ${columns.map(col => `
        <th onclick="sortTable('${col}')">
          ${escapeHtml(col)} ${state.sortCol === col ? (state.sortAsc ? '▲' : '▼') : ''}
        </th>
      `).join('')}
    </tr>
  `;

  // Render Tbody
  elements.tableTbody.innerHTML = rows.map(r => `
    <tr>
      ${columns.map(col => `<td>${escapeHtml(String(r[col] !== null ? r[col] : ''))}</td>`).join('')}
    </tr>
  `).join('');
}

function filterTable() {
  const q = elements.tableSearch.value.toLowerCase();
  const filtered = state.tableData.filter(r => {
    return Object.values(r).some(val => String(val).toLowerCase().includes(q));
  });
  renderTable(filtered, state.tableColumns);
}

window.sortTable = function(col) {
  if (state.sortCol === col) {
    state.sortAsc = !state.sortAsc;
  } else {
    state.sortCol = col;
    state.sortAsc = true;
  }

  state.tableData.sort((a, b) => {
    let v1 = a[col];
    let v2 = b[col];
    if (typeof v1 === 'number' && typeof v2 === 'number') {
      return state.sortAsc ? v1 - v2 : v2 - v1;
    }
    return state.sortAsc ? String(v1).localeCompare(String(v2)) : String(v2).localeCompare(String(v1));
  });

  renderTable(state.tableData, state.tableColumns);
};

function downloadTableCsv() {
  if (!state.tableData || state.tableData.length === 0) return;
  const cols = state.tableColumns;
  let csv = cols.join(',') + '\n';
  state.tableData.forEach(r => {
    const row = cols.map(c => `"${String(r[c] || '').replace(/"/g, '""')}"`).join(',');
    csv += row + '\n';
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'query_results.csv';
  a.click();
}

function copySqlToClipboard() {
  const sql = elements.sqlCodeBlock.innerText;
  navigator.clipboard.writeText(sql).then(() => {
    elements.btnCopySql.innerText = 'Copied';
    setTimeout(() => {
      elements.btnCopySql.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        Copy SQL
      `;
    }, 2000);
  });
}

// --------------------------------------------------------------------------
// Schema Explorer Modal
// --------------------------------------------------------------------------
async function openSchemaModal() {
  elements.schemaModal.classList.add('open');
  elements.schemaContent.innerHTML = '<div style="color: var(--text-muted); padding: 1.5rem;">Loading schema definition...</div>';
  try {
    const res = await fetch('/api/v1/schema');
    const data = await res.json();
    let html = '';

    // Tables
    html += '<h3 class="schema-section-title">Relational Tables</h3>';
    for (const [tName, tInfo] of Object.entries(data.tables)) {
      html += `
        <div class="schema-table-card">
          <div class="schema-table-name">${tName}</div>
          <div class="schema-table-desc">${tInfo.description}</div>
          <div class="schema-columns-list">
            ${Object.entries(tInfo.columns).map(([cName, cInfo]) => `
              <span class="badge">
                ${cName} (${cInfo.type})
              </span>
            `).join('')}
          </div>
        </div>
      `;
    }

    // Formulas
    html += '<h3 class="schema-section-title" style="margin-top: 1.5rem;">Business Metrics Dictionary</h3>';
    for (const [mName, mInfo] of Object.entries(data.metrics)) {
      html += `
        <div class="schema-metric-row">
          <div class="schema-metric-header">
            <span class="schema-metric-name">${mName}</span>
            <code class="schema-metric-code">${mInfo.formula}</code>
          </div>
          <div class="schema-metric-desc">${mInfo.description}</div>
        </div>
      `;
    }

    elements.schemaContent.innerHTML = html;
  } catch (err) {
    elements.schemaContent.innerHTML = `<div style="color: var(--status-error); padding: 1.5rem;">Failed to load schema: ${err.message}</div>`;
  }
}

// --------------------------------------------------------------------------
// UI Helpers & Formatting
// --------------------------------------------------------------------------
function showStepper(msg) {
  elements.stepper.style.display = 'block';
  elements.stepperHeader.innerText = msg;
  document.querySelectorAll('.step-item').forEach(s => {
    s.classList.remove('active', 'completed');
  });
}

function animateStep(stepNum) {
  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById(`step-${i}`);
    if (!el) continue;
    if (i < stepNum) {
      el.classList.add('completed');
      el.classList.remove('active');
    } else if (i === stepNum) {
      el.classList.add('active');
      el.classList.remove('completed');
    } else {
      el.classList.remove('active', 'completed');
    }
  }
}

function hideStepper() {
  elements.stepper.style.display = 'none';
}

function hideResults() {
  elements.resultsWrapper.style.display = 'none';
  elements.alertCard.style.display = 'none';
}

function showWarningAlert(html) {
  elements.alertCard.style.display = 'flex';
  elements.alertCard.className = 'alert-card alert-warning';
  elements.alertMessage.innerHTML = html;
}

function showErrorAlert(html) {
  elements.alertCard.style.display = 'flex';
  elements.alertCard.className = 'alert-card alert-error';
  elements.alertMessage.innerHTML = html;
}

function showNotification(msg) {
  const toast = document.createElement('div');
  toast.innerText = msg;
  toast.style.cssText = `
    position: fixed; bottom: 24px; right: 24px; background: #161f30; color: #f8fafc;
    border: 1px solid #2563eb; padding: 10px 18px; border-radius: 6px; font-size: 0.85rem;
    font-weight: 500; box-shadow: 0 8px 24px rgba(0,0,0,0.4); z-index: 9999;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

function formatMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n- (.*)/g, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n/g, '<br>');
}

function formatNumber(num) {
  if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1) + 'k';
  return Math.round(num * 100) / 100;
}

function truncate(str, max) {
  return str.length > max ? str.substring(0, max) + '…' : str;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
