const input = document.querySelector('#changeInput');
const charCount = document.querySelector('#charCount');
const analyzeBtn = document.querySelector('#analyzeBtn');
const results = document.querySelector('#results');
const modelSelect = document.querySelector('#modelSelect');
const embeddingSelect = document.querySelector('#embeddingSelect');
const connectionMessage = document.querySelector('#connectionMessage');
const toast = document.querySelector('#toast');
const STORAGE_KEY = 'codeimpact.run-history.v1';
const REPO_KEY = 'codeimpact.github-selection.v1';
let currentStatus = { ollama: 'offline', models: [], embeddingModels: [] };
let currentReport = null;
let githubBranchesCache = null;
let toastTimer;

const settingsPage = document.querySelector('#settingsPage');
settingsPage.querySelector('.guardrail-card').insertAdjacentHTML('beforebegin', `<div class="card settings-card" id="groqSettings"><div class="section-title">Connect Groq API <span class="step-badge" id="groqBadge">NOT CONNECTED</span></div><p class="setting-help">Paste your Groq API key to add hosted models to comparisons. The key is sent only to this local server and kept in memory for this run; it is not saved. When you explicitly opt in on the comparison page, your change and retrieved repository excerpts go to Groq.</p><label for="groqApiKey">Groq API key</label><div class="input-row"><input id="groqApiKey" type="password" autocomplete="off" placeholder="Paste key to connect"><button class="secondary-button" id="connectGroqBtn">Connect</button><button class="secondary-button" id="disconnectGroqBtn">Disconnect</button></div><div class="pull-progress" id="groqStatus" role="status">Not connected.</div><div class="installed-models"><strong>Available hosted models</strong><div id="groqModelList">Not connected.</div></div></div>`);
settingsPage.querySelector('#groqSettings').insertAdjacentHTML('beforebegin', `<div class="card settings-card" id="githubSettings"><div class="section-title">Connect private GitHub repositories <span class="step-badge" id="githubBadge">NOT CONNECTED</span></div><p class="setting-help">Public repositories need no token. To fetch a private repository, create a fine-grained GitHub token with read access to repository contents and metadata. It is sent only to GitHub, held in this local server's memory, and never added to the LLM prompt or saved to disk.</p><label for="githubToken">GitHub read token</label><div class="input-row"><input id="githubToken" type="password" autocomplete="off" placeholder="github_pat_…"><button class="secondary-button" id="connectGithubBtn">Connect</button><button class="secondary-button" id="disconnectGithubBtn">Disconnect</button></div><div class="pull-progress" id="githubStatus" role="status">Not connected.</div></div>`);

function notify(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
}
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
function metric(value, suffix = '') { return value === null || value === undefined ? 'Unavailable' : `${value}${suffix}`; }
function getRepoConfig() { try { return JSON.parse(localStorage.getItem(REPO_KEY) || 'null'); } catch { return null; } }
function setRepoConfig(value) { localStorage.setItem(REPO_KEY, JSON.stringify(value)); }
function readHistory() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; } }
function saveHistory(run) {
  const history = readHistory();
  history.unshift(run);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, 30)));
}
function getPayload() {
  const payload = { change: input.value.trim(), model: modelSelect.value, embeddingModel: embeddingSelect.value };
  const github = getRepoConfig();
  if (github?.repository && github?.base && github?.head) payload.github = github;
  return payload;
}

function route(view) {
  document.querySelectorAll('.dashboard-only').forEach((element) => element.classList.toggle('hidden', view !== 'analysis'));
  document.querySelectorAll('.route-page').forEach((element) => element.classList.add('hidden'));
  document.querySelector(`#${view}Page`)?.classList.remove('hidden');
  document.querySelectorAll('[data-view]').forEach((element) => element.classList.toggle('active', element.dataset.view === view));
  if (view === 'repository') syncRepositoryPage();
  if (view === 'evaluation') populateCompareModels();
  if (view === 'history') renderHistory();
  if (view === 'settings') renderInstalledModels();
}

function renderEmpty(message, title = 'No live analysis yet') {
  results.innerHTML = `<div class="result-heading"><div><div class="section-title">Impact report <span class="live-label live-off"><span></span> LIVE DATA</span></div><div class="section-subtitle">Results appear after a real branch comparison, repository search, and Ollama response.</div></div></div><div class="empty-report card"><div class="empty-mark">✳</div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(message)}</p></div>`;
}

function setSelectOptions(select, items, current, placeholder) {
  select.innerHTML = items.length ? items.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join('') : `<option value="">${escapeHtml(placeholder)}</option>`;
  if (items.includes(current)) select.value = current;
}

function updateCompareReady() {
  const ids = ['#compareModel1', '#compareModel2', '#compareModel3'].map((selector) => document.querySelector(selector).value);
  const needsGroq = ids.some((model) => model.startsWith('groq:'));
  const ready = ids.every(Boolean) && new Set(ids).size === 3 && (!needsGroq || document.querySelector('#groqConsent').checked);
  document.querySelector('#compareBtn').disabled = !ready;
  document.querySelector('#compareStatus').textContent = ready ? 'Ready · same prompt and retrieved context for all three.'
    : needsGroq && !document.querySelector('#groqConsent').checked ? 'Opt in before sending repository context to Groq.'
      : ids.some((model) => !model) ? 'Install Ollama models or connect Groq to add model choices.' : 'Choose three different models.';
}

function compareOptions() {
  const options = [
    ...(currentStatus.models || []).map((model) => ({ value: model, label: `Ollama · ${model}` })),
    ...(currentStatus.groqModels || []).map((model) => ({ value: `groq:${model}`, label: `Groq API · ${model}` })),
  ];
  return options;
}

function renderStatus(state) {
  currentStatus = state;
  const previousModel = modelSelect.value;
  const previousEmbedding = embeddingSelect.value;
  const dot = document.querySelector('#ollamaDot');
  dot.classList.toggle('offline', state.ollama !== 'connected');
  document.querySelector('#ollamaLabel').textContent = state.ollama === 'connected' ? 'Ollama connected' : 'Ollama offline';
  setSelectOptions(modelSelect, state.models || [], previousModel, state.ollama === 'connected' ? 'No local models found' : 'Ollama offline');
  setSelectOptions(embeddingSelect, state.embeddingModels || [], previousEmbedding || state.embeddingModel, 'No embedding model found');
  document.querySelector('#repoName').textContent = getRepoConfig()?.repository || state.repository || 'This local repository';
  document.querySelector('#footerStatus').textContent = state.ollama === 'connected' ? 'OLLAMA ONLINE' : 'OLLAMA OFFLINE';
  document.querySelector('#footerStatusDot').style.background = state.ollama === 'connected' ? '#48ad7c' : '#cc795f';
  document.querySelector('#indexStatus').textContent = state.ollama === 'connected' ? 'Index builds on analysis' : 'Waiting for Ollama';
  document.querySelector('#indexCheck').textContent = state.ollama === 'connected' ? '·' : '!';
  document.querySelector('#indexPulse').classList.toggle('offline', state.ollama !== 'connected');
  document.querySelector('#groqBadge').textContent = state.groqConnected ? 'CONNECTED · SESSION ONLY' : 'NOT CONNECTED';
  document.querySelector('#groqStatus').textContent = state.groqConnected ? 'Connected. The key remains in the server process memory and clears when the server stops.' : 'Not connected.';
  document.querySelector('#githubBadge').textContent = state.githubTokenConfigured ? `CONNECTED · ${state.githubLogin || 'SERVER TOKEN'}` : 'NOT CONNECTED';
  document.querySelector('#githubStatus').textContent = state.githubTokenConfigured ? 'Connected. Private repository reads use this token; it clears when the server stops.' : 'Not connected. Public repositories can still be fetched.';
  document.querySelector('#groqModelList').innerHTML = (state.groqModels || []).map((model) => `<span class="installed-model">${escapeHtml(model)}</span>`).join('') || '<span class="quiet">No hosted models loaded.</span>';
  if (state.ollama !== 'connected') {
    connectionMessage.innerHTML = 'Ollama is not responding at <code>localhost:11434</code>. Start Ollama to run live analysis. <a href="https://ollama.com/download" target="_blank" rel="noreferrer">Install Ollama ↗</a>';
    analyzeBtn.disabled = true;
  } else if (!(state.models || []).length) {
    connectionMessage.textContent = 'Ollama is running, but no chat model is installed. Open Settings to pull a chat model.';
    analyzeBtn.disabled = true;
  } else if (!(state.embeddingModels || []).length) {
    connectionMessage.textContent = 'A language model is available, but semantic retrieval needs an embedding model. Open Settings to pull one.';
    analyzeBtn.disabled = true;
  } else {
    connectionMessage.textContent = `Ready · ${state.baseUrl} · embedding model ${embeddingSelect.value}`;
    analyzeBtn.disabled = false;
  }
  populateCompareModels();
  if (document.querySelector('#settingsPage').classList.contains('hidden') === false) renderInstalledModels();
}

async function refreshStatus() {
  try {
    const response = await fetch('/api/status', { cache: 'no-store' });
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    renderStatus(await response.json());
  } catch (error) {
    renderStatus({ ollama: 'offline', models: [], embeddingModels: [], embeddingModel: null, repository: 'Local repository' });
    connectionMessage.textContent = `CodeImpact API is unavailable: ${error.message}. Start the app with python server.py.`;
  }
}

function toHtmlMarkdown(text) {
  return escapeHtml(text).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/^### (.+)$/gm, '<h3>$1</h3>').replace(/^## (.+)$/gm, '<h2>$1</h2>').replace(/^# (.+)$/gm, '<h2>$1</h2>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function renderReport(data) {
  currentReport = data;
  const stats = data.stats;
  const latency = stats.latency;
  const tokens = stats.tokens;
  const resource = stats.resources;
  const sources = data.sources || [];
  const citedSources = sources.filter((source) => data.report?.includes(source.path));
  const sourceRows = sources.map((source, index) => {
    const score = source.score == null ? '—' : source.score.toFixed(4);
    const excerpt = (source.text || '').replace(/\s+/g, ' ').slice(0, 240);
    return `<article class="source-row"><div class="source-number">${String(index + 1).padStart(2, '0')}</div><div class="source-content"><div class="source-path">${escapeHtml(source.path)} <span>lines ${source.startLine}–${source.endLine}</span></div><p>${escapeHtml(excerpt)}${source.text?.length > 240 ? '…' : ''}</p></div><span class="similarity">${score}</span></article>`;
  }).join('');
  const memory = resource.systemMemoryAfter?.usedMb != null ? `${resource.systemMemoryAfter.usedMb.toLocaleString()} / ${resource.systemMemoryAfter.totalMb.toLocaleString()} MB` : 'Unavailable';
  const gpu = resource.gpu?.available ? resource.gpu.devices.map((device, index) => `GPU ${index + 1}: ${device.utilizationPercent}% · ${device.usedMb}/${device.totalMb} MB`).join(' | ') : 'Unavailable';
  const cpu = resource.cpuAfterPercent == null ? 'Unavailable' : `${resource.cpuAfterPercent}% system CPU`;
  const branch = data.github ? `${escapeHtml(data.github.base)} → ${escapeHtml(data.github.head)} · ${data.github.files.length} changed files` : 'Local working tree';
  results.innerHTML = `<div class="result-heading"><div><div class="section-title">Impact report <span class="live-label"><span></span> LIVE OLLAMA RESPONSE</span></div><div class="section-subtitle">${escapeHtml(data.repository)} · ${branch} · ${escapeHtml(data.model)} · ${new Date(data.generatedAt).toLocaleString()}</div></div><button class="export-button" id="copyBtn">↗ <span>Copy report</span></button></div>
    <div class="summary-card card"><div class="summary-main"><div class="live-ring">⌁</div><div><div class="risk-label live-tone">RETRIEVAL COMPLETE</div><h2>${sources.length} unique source files retrieved</h2><p>Similarity ranks retrieved context; it is not a probability of impact. Review the model report and cited evidence.</p></div></div><div class="summary-meta"><div><span>END-TO-END</span><strong>${metric(latency.endToEndMs, ' ms')}</strong></div><div><span>MODEL TOKENS</span><strong>${metric(tokens.total)}</strong></div><div><span>INDEXED CHUNKS</span><strong>${stats.retrieval.chunksIndexed.toLocaleString()}</strong></div></div></div>
    ${data.github ? `<div class="card diff-summary"><strong>GitHub branch comparison</strong><span>${branch}</span><div>${data.github.files.map((file) => `<span class="diff-file"><b>${escapeHtml(file.status)}</b> ${escapeHtml(file.filename)} <i>+${file.additions} / −${file.deletions}</i></span>`).join('')}</div></div>` : ''}
    <div class="evidence-check ${citedSources.length ? 'evidence-check-found' : 'evidence-check-missing'}" role="status"><strong>${citedSources.length ? `Evidence check · ${citedSources.length}/${sources.length} retrieved paths cited` : 'Evidence check · no retrieved paths cited'}</strong><span>${citedSources.length ? 'Cited paths match retrieved files; verify that each claim is supported by its excerpt.' : 'The answer contains no citations to retrieved files. Treat its claims as unverified and review the source excerpts below.'}</span></div>
    <div class="results-grid"><div class="files-panel card"><div class="panel-heading"><div><span class="panel-icon">⌘</span><strong>Retrieved repository context</strong></div><span class="count-badge">${sources.length}</span></div><div class="source-list">${sourceRows || '<div class="empty-source">No source context was returned.</div>'}</div><div class="source-legend">Cosine similarity · a retrieval rank, not a correctness score</div></div>
    <div class="context-panel card"><div class="panel-heading"><div><span class="panel-icon context-icon">✳</span><strong>Measured for this run</strong></div><span class="evidence-label"><span></span> API DATA</span></div><div class="metric-list"><div><span>End-to-end (index + model)</span><strong>${metric(latency.endToEndMs, ' ms')}</strong></div><div><span>Retrieval/index preparation</span><strong>${metric(latency.retrievalMs, ' ms')}</strong></div><div><span>Model/API response</span><strong>${metric(latency.latencyMs, ' ms')}</strong></div><div><span>Provider model time</span><strong>${metric(latency.ollamaTotalMs, ' ms')}</strong></div><div><span>Model load time</span><strong>${metric(latency.modelLoadMs, ' ms')}</strong></div><div><span>Prompt / generated tokens</span><strong>${metric(tokens.prompt)} / ${metric(tokens.generated)}</strong></div><div><span>Prompt / generation time</span><strong>${metric(latency.promptEvalMs, ' ms')} / ${metric(latency.generationMs, ' ms')}</strong></div><div><span>System CPU sample</span><strong>${cpu}</strong></div><div><span>System memory after</span><strong>${memory}</strong></div><div><span>GPU utilization / memory</span><strong>${escapeHtml(gpu)}</strong></div></div><div class="context-footer"><span class="shield">◈</span> Resource readings are machine-wide snapshots, not per-process attribution.</div></div></div>
    <article class="model-response card"><div class="panel-heading"><div><span class="panel-icon context-icon">✳</span><strong>${escapeHtml(data.model)} analysis</strong></div><span class="count-badge">${escapeHtml(data.model)}</span></div><div class="response-text">${toHtmlMarkdown(data.report || '')}</div></article>
    <div class="bottom-note"><span>✳</span> ${data.embeddingModel ? `Embeddings: ${escapeHtml(data.embeddingModel)} <span class="note-divider">·</span> ` : ''}${stats.retrieval.chunksIndexed.toLocaleString()} chunks indexed</div>`;
  document.querySelector('#copyBtn').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText([`CodeImpact AI — live report`, `Repository: ${data.repository}`, `Model: ${data.model}`, `Embedding model: ${data.embeddingModel}`, `End-to-end latency: ${latency.endToEndMs} ms`, `Model/API latency: ${latency.latencyMs} ms`, `Prompt/generated tokens: ${tokens.prompt} / ${tokens.generated}`, '', data.report, '', 'Retrieved sources:', ...sources.map((source) => `${source.path}:${source.startLine}-${source.endLine} (similarity ${source.score})`)].join('\n')); notify('Live report copied.'); }
    catch { notify('Clipboard access is unavailable in this browser.'); }
  });
}

function historyRecord(data, kind = 'analysis') {
  saveHistory({ kind, repository: data.repository, model: data.model, generatedAt: data.generatedAt, report: data.report,
    github: data.github, stats: data.stats, sources: data.sources, embeddingModel: data.embeddingModel, provider: data.provider, modelResults: data.results });
}

function renderHistory() {
  const runs = readHistory();
  const host = document.querySelector('#historyList');
  if (!runs.length) { host.innerHTML = '<div class="card empty-report"><h2>No saved runs</h2><p>Completed local analyses and model comparisons will appear here.</p></div>'; return; }
  host.innerHTML = runs.map((run, index) => `<article class="card history-card"><div class="history-top"><div><span class="live-label"><span></span> ${run.kind === 'comparison' ? '3-MODEL COMPARISON' : 'ANALYSIS'}</span><h2>${escapeHtml(run.repository || 'Local repository')}</h2><p>${new Date(run.generatedAt).toLocaleString()} · ${escapeHtml(run.model || `${run.modelResults?.length || 3} models`)}</p></div><button class="secondary-button" data-history-open="${index}">Open report</button></div><div class="history-preview">${escapeHtml((run.report || run.modelResults?.map((result) => `${result.model}: ${result.report}`).join(' | ') || '').slice(0, 350))}</div></article>`).join('');
  host.querySelectorAll('[data-history-open]').forEach((button) => button.addEventListener('click', () => {
    const run = runs[Number(button.dataset.historyOpen)];
    if (run.kind === 'comparison') { renderBenchmark({ results: run.modelResults || [], repository: run.repository, github: run.github, generatedAt: run.generatedAt }, false); route('evaluation'); }
    else { renderReport(run); route('analysis'); }
  }));
}

function renderInstalledModels() {
  const list = document.querySelector('#installedModels');
  if (!list) return;
  list.innerHTML = currentStatus.ollama !== 'connected' ? '<span class="quiet">Ollama offline</span>' : (currentStatus.installedModels || currentStatus.models || []).map((name) => `<span class="installed-model">${escapeHtml(name)}${(currentStatus.embeddingModels || []).includes(name) ? ' · embedding' : ' · chat available'}</span>`).join('') || '<span class="quiet">No models installed.</span>';
}

function populateCompareModels() {
  const installed = compareOptions();
  ['#compareModel1', '#compareModel2', '#compareModel3'].forEach((selector, index) => {
    const select = document.querySelector(selector);
    if (!select) return;
    const previous = select.value;
    select.innerHTML = installed.length ? installed.map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`).join('') : '<option value="">No models connected</option>';
    if (installed.some((option) => option.value === previous)) select.value = previous;
    else if (installed[index]) select.value = installed[index].value;
    select.disabled = installed.length < 3;
  });
  updateCompareReady();
}

function renderBenchmark(data, addHistory = true) {
  const good = (data.results || []).filter((item) => item.stats?.latency?.latencyMs != null);
  const latencyMax = Math.max(1, ...good.map((item) => item.stats.latency.latencyMs));
  const tokenMax = Math.max(1, ...good.map((item) => item.stats.tokens.total || 0));
  const rows = good.map((item) => `<div class="chart-row"><div class="chart-label">${escapeHtml(item.model)}</div><div class="chart-track"><i style="width:${Math.max(2, item.stats.latency.latencyMs / latencyMax * 100)}%"></i></div><strong>${item.stats.latency.latencyMs.toLocaleString()} ms</strong></div>`).join('');
  const tokenRows = good.map((item) => `<div class="chart-row"><div class="chart-label">${escapeHtml(item.model)}</div><div class="chart-track token-track"><i style="width:${Math.max(2, (item.stats.tokens.total || 0) / tokenMax * 100)}%"></i></div><strong>${metric(item.stats.tokens.total)} tokens</strong></div>`).join('');
  document.querySelector('#benchmarkResults').innerHTML = `<div class="benchmark-grid"><article class="card chart-card"><div class="panel-heading"><strong>Measured response latency</strong><span class="count-badge">LOWER IS FASTER</span></div><div class="chart-rows">${rows || '<p class="quiet">No completed responses to chart.</p>'}</div></article><article class="card chart-card"><div class="panel-heading"><strong>Ollama-reported tokens</strong><span class="count-badge">PROMPT + GENERATED</span></div><div class="chart-rows">${tokenRows || '<p class="quiet">No token measurements to chart.</p>'}</div></article></div>
  <div class="benchmark-cards">${(data.results || []).map((item) => item.error ? `<article class="card model-result"><h2>${escapeHtml(item.model)}</h2><p class="error-text">${escapeHtml(item.error)}</p></article>` : `<details class="card model-result"><summary><div><strong>${escapeHtml(item.model)}</strong><span>${metric(item.stats.latency.latencyMs, ' ms')} · ${metric(item.stats.tokens.total)} tokens</span></div><b>＋</b></summary><pre>${escapeHtml(item.report)}</pre></details>`).join('')}</div>`;
  if (addHistory && data.results?.length) { historyRecord(data, 'comparison'); notify('Three live model runs completed; measured charts updated.'); }
}

async function analyze() {
  const payload = getPayload();
  if (!payload.change) { input.focus(); notify('Describe a proposed code change first.'); return; }
  if (!payload.model || !payload.embeddingModel) { notify('Choose an installed language model and embedding model.'); return; }
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span class="button-spark">✳</span> Comparing branches & analyzing…';
  connectionMessage.textContent = 'Fetching selected repository branches, embedding the base branch, and generating a live response.';
  renderEmpty('Fetching branches and building the repository index…', 'Analysis in progress');
  try {
    const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    renderReport(data); historyRecord(data); currentReport = data;
    connectionMessage.textContent = `Completed with ${data.model}; measurements came from the Ollama response and this machine.`;
    document.querySelector('#indexStatus').textContent = 'Repository indexed';
    document.querySelector('#indexCheck').textContent = '✓';
    document.querySelector('#indexStats').textContent = `${data.stats.retrieval.chunksIndexed.toLocaleString()} embedded code chunks`;
    if (data.github) {
      document.querySelector('#branchStatus').textContent = `${data.github.base} compared with ${data.github.head}`;
      document.querySelector('#branchSummary').classList.remove('hidden');
      document.querySelector('#branchSummary').innerHTML = `<strong>${escapeHtml(data.github.repository)} · ${escapeHtml(data.github.base)} → ${escapeHtml(data.github.head)}</strong><p>${data.github.totalCommits} commits · ${data.github.files.length} changed files · +${data.github.files.reduce((sum, file) => sum + (file.additions || 0), 0)} / −${data.github.files.reduce((sum, file) => sum + (file.deletions || 0), 0)} lines</p>`;
    }
  } catch (error) { renderEmpty(error.message, 'Live analysis could not complete'); connectionMessage.textContent = error.message; }
  finally { analyzeBtn.innerHTML = '<span class="button-spark">✳</span> Analyze change <span class="button-arrow">→</span>'; await refreshStatus(); }
}

async function compareThree() {
  const payload = getPayload();
  payload.models = ['#compareModel1', '#compareModel2', '#compareModel3'].map((selector) => document.querySelector(selector).value);
  payload.allowExternal = document.querySelector('#groqConsent').checked;
  if (!payload.change) { route('analysis'); input.focus(); notify('Enter a proposed change on the Impact analysis page first.'); return; }
  if (!payload.embeddingModel) { notify('Choose an installed embedding model on the Impact analysis page.'); return; }
  if (new Set(payload.models).size !== 3 || payload.models.some((model) => !model)) { notify('Select three different installed models.'); return; }
  const button = document.querySelector('#compareBtn');
  button.disabled = true; button.textContent = 'Running three models…';
  document.querySelector('#compareStatus').textContent = 'Same branch diff and retrieved context are being sent to each model.';
  document.querySelector('#benchmarkResults').innerHTML = '<div class="card empty-report"><h2>Comparison running</h2><p>Repository retrieval runs once; model calls run sequentially for comparable conditions.</p></div>';
  try {
    const response = await fetch('/api/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    renderBenchmark(data);
    document.querySelector('#compareStatus').textContent = `Completed · ${data.repository} · ${data.generatedAt}`;
  } catch (error) { document.querySelector('#benchmarkResults').innerHTML = `<div class="card empty-report"><h2>Comparison failed</h2><p>${escapeHtml(error.message)}</p></div>`; document.querySelector('#compareStatus').textContent = error.message; }
  finally { updateCompareReady(); button.textContent = 'Run 3-model comparison →'; }
}

async function fetchBranches() {
  const repository = document.querySelector('#githubRepo').value.trim();
  const status = document.querySelector('#branchStatus');
  if (!repository) { status.textContent = 'Enter a GitHub repository URL first.'; return; }
  status.textContent = 'Fetching repository and branch list from GitHub…';
  try {
    const response = await fetch(`/api/github/branches?repository=${encodeURIComponent(repository)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `GitHub request failed (${response.status})`);
    githubBranchesCache = data;
    const names = data.branches.map((branch) => branch.name);
    const fill = (selector, preferred) => {
      const select = document.querySelector(selector);
      select.innerHTML = names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
      if (names.includes(preferred)) select.value = preferred;
      else if (names.includes(data.defaultBranch)) select.value = data.defaultBranch;
    };
    fill('#baseBranch', getRepoConfig()?.base || data.defaultBranch);
    fill('#headBranch', getRepoConfig()?.head || names.find((name) => name !== data.defaultBranch) || data.defaultBranch);
    status.textContent = `${data.repository} · ${names.length} branches${data.private ? ' · private' : ' · public'}`;
  } catch (error) { status.textContent = error.message; }
}

function syncRepositoryPage() {
  const config = getRepoConfig();
  if (config) document.querySelector('#githubRepo').value = config.repository;
  if (config && !githubBranchesCache) fetchBranches();
}

function setRepo() {
  const repository = document.querySelector('#githubRepo').value.trim();
  const base = document.querySelector('#baseBranch').value;
  const head = document.querySelector('#headBranch').value;
  if (!repository || !base || !head || base === head) { notify('Select a repository and two different branches.'); return; }
  const config = { repository, base, head };
  setRepoConfig(config);
  document.querySelector('#repoName').textContent = repository;
  document.querySelector('#branchStatus').textContent = `Active comparison: ${base} → ${head}`;
  route('analysis');
  notify('GitHub repository and branch comparison selected.');
}

async function pullModel() {
  const model = document.querySelector('#newModelName').value.trim();
  const output = document.querySelector('#pullProgress');
  if (!model) { output.textContent = 'Enter a model name first.'; return; }
  const button = document.querySelector('#pullModelBtn');
  button.disabled = true; button.textContent = 'Downloading…';
  output.textContent = `Requesting ${model} from Ollama. Download progress depends on Ollama's local API.`;
  try {
    const response = await fetch('/api/models/pull', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Pull failed (${response.status})`);
    output.textContent = `${model} pull completed.`;
    document.querySelector('#newModelName').value = '';
    await refreshStatus(); renderInstalledModels();
  } catch (error) { output.textContent = error.message; }
  finally { button.disabled = false; button.textContent = 'Pull model'; }
}

async function connectGroq(disconnect = false) {
  const input = document.querySelector('#groqApiKey');
  const status = document.querySelector('#groqStatus');
  const button = document.querySelector('#connectGroqBtn');
  if (!disconnect && !input.value.trim()) { status.textContent = 'Paste your Groq API key first.'; return; }
  button.disabled = true;
  status.textContent = disconnect ? 'Disconnecting…' : 'Verifying the key and fetching available models…';
  try {
    const response = await fetch('/api/groq/connect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ apiKey: disconnect ? '' : input.value.trim() }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Groq connection failed (${response.status})`);
    input.value = '';
    status.textContent = data.connected ? `Connected for this server session · ${data.models.length} models available.` : 'Disconnected. The key was removed from server memory.';
    await refreshStatus();
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}

async function connectGithub(disconnect = false) {
  const input = document.querySelector('#githubToken');
  const status = document.querySelector('#githubStatus');
  const button = document.querySelector('#connectGithubBtn');
  if (!disconnect && !input.value.trim()) { status.textContent = 'Paste a read-only GitHub token first.'; return; }
  button.disabled = true;
  status.textContent = disconnect ? 'Disconnecting…' : 'Verifying token with GitHub…';
  try {
    const response = await fetch('/api/github/connect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: disconnect ? '' : input.value.trim() }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `GitHub connection failed (${response.status})`);
    input.value = '';
    status.textContent = data.connected ? `Connected as ${data.login || 'server token'} for this session.` : 'Disconnected. The token was removed from server memory.';
    await refreshStatus();
    if (getRepoConfig()) fetchBranches();
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}

input.addEventListener('input', () => {
  if (input.value.length > 2000) input.value = input.value.slice(0, 2000);
  charCount.textContent = `${input.value.length.toLocaleString()} / 2,000`;
});
document.querySelector('#clearBtn').addEventListener('click', () => { input.value = ''; charCount.textContent = '0 / 2,000'; input.focus(); });
analyzeBtn.addEventListener('click', analyze);
input.addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') analyze(); });
document.querySelectorAll('[data-view]').forEach((element) => element.addEventListener('click', (event) => { event.preventDefault(); route(element.dataset.view); }));
document.querySelectorAll('[data-go]').forEach((element) => element.addEventListener('click', () => route(element.dataset.go)));
document.querySelector('#fetchBranches').addEventListener('click', fetchBranches);
document.querySelector('#saveRepository').addEventListener('click', setRepo);
document.querySelector('#compareBtn').addEventListener('click', compareThree);
['#compareModel1', '#compareModel2', '#compareModel3'].forEach((selector) => document.querySelector(selector).addEventListener('change', updateCompareReady));
document.querySelector('#pullModelBtn').addEventListener('click', pullModel);
document.querySelector('#connectGroqBtn').addEventListener('click', () => connectGroq(false));
document.querySelector('#disconnectGroqBtn').addEventListener('click', () => connectGroq(true));
document.querySelector('#connectGithubBtn').addEventListener('click', () => connectGithub(false));
document.querySelector('#disconnectGithubBtn').addEventListener('click', () => connectGithub(true));
document.querySelector('#groqConsent').addEventListener('change', updateCompareReady);
document.querySelector('#clearHistory').addEventListener('click', () => { localStorage.removeItem(STORAGE_KEY); renderHistory(); notify('Local run history cleared.'); });

renderEmpty('Connect Ollama and choose a model to analyze a repository with live retrieval.', 'Waiting for Ollama');
refreshStatus();
setInterval(refreshStatus, 20000);

