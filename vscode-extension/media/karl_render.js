// ── module-level streaming state ───────────────────────────────────────────────
let _thoughtTokenCount = 0;
let _streamingTarget = null;   // the .message-content el that owns the cursor

// ── helpers ────────────────────────────────────────────────────────────────────

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

// ── streaming cursor ───────────────────────────────────────────────────────────

function _getOrCreateCursor() {
    let cursor = document.getElementById('streaming-cursor');
    if (!cursor) {
        cursor = document.createElement('span');
        cursor.id = 'streaming-cursor';
        cursor.className = 'streaming-cursor';
        cursor.setAttribute('aria-hidden', 'true');
    }
    return cursor;
}

function attachStreamingCursor(contentEl) {
    removeStreamingCursor();
    _streamingTarget = contentEl;
    contentEl.appendChild(_getOrCreateCursor());
}

function removeStreamingCursor() {
    const cursor = document.getElementById('streaming-cursor');
    if (cursor) cursor.remove();
    _streamingTarget = null;
}

// Append plain text to a chat bubble's content element, keeping the cursor at
// the very end of the text at all times so it appears to advance with output.
// Each batch is wrapped in .token-appear for the CSS entrance animation.
function _appendChatText(el, text) {
    if (!text) return;
    const cursor = document.getElementById('streaming-cursor');
    const cursorOwned = cursor && cursor.parentElement === el;
    if (cursorOwned) cursor.remove();
    const span = document.createElement('span');
    span.className = 'token-appear';
    span.textContent = text;
    el.appendChild(span);
    if (cursorOwned || _streamingTarget === el) {
        _streamingTarget = el;
        el.appendChild(_getOrCreateCursor());
    }
}

// ── thought-panel helpers ──────────────────────────────────────────────────────

function appendThoughtToken(token) {
    const str = String(token || '');
    if (!str) return;
    _thoughtTokenCount += Math.ceil(str.length / 4);
    const thoughtsEl = $('introspectionThoughts');
    if (thoughtsEl) {
        thoughtsEl.textContent += str;
        thoughtsEl.scrollTop = thoughtsEl.scrollHeight;
    }
    const countEl = $('thoughtsTokenCount');
    if (countEl) countEl.textContent = `~${_thoughtTokenCount.toLocaleString()} tokens`;
    const dot = $('thoughtsPulseDot');
    if (dot && !dot.classList.contains('active')) dot.classList.add('active');
    // Mirror content to the full-view reasoning panel (Reasoning tab)
    const fullView = $('reasoningFullView');
    if (fullView) {
        fullView.textContent += str;
        fullView.scrollTop = fullView.scrollHeight;
    }
}

function resetThoughtsPanel() {
    _thoughtTokenCount = 0;
    const thoughtsEl = $('introspectionThoughts');
    if (thoughtsEl) thoughtsEl.textContent = '';
    const countEl = $('thoughtsTokenCount');
    if (countEl) countEl.textContent = '0 tokens';
    const dot = $('thoughtsPulseDot');
    if (dot) dot.classList.remove('active');
    const box = $('introspectionBox');
    if (box) box.classList.remove('active');
    const fullView = $('reasoningFullView');
    if (fullView) fullView.textContent = '';
}

function finalizeThoughts() {
    const dot = $('thoughtsPulseDot');
    if (dot) dot.classList.remove('active');
}

// ── model / download lists ─────────────────────────────────────────────────────

function buildModelCard(title, metaHtml, buttonHtml) {
    return `<div class="model-card">
        <div class="model-title">${escapeHtml(title)}</div>
        <div class="model-meta">${metaHtml}</div>
        ${buttonHtml}
    </div>`;
}

function renderModels(models) {
    if (!Array.isArray(models)) models = [];
    $('modelList').innerHTML = models.length ? models.map(model => {
        if (!model) return '';
        const action = model.active
            ? '<button disabled>Active</button>'
            : model.installed
                ? `<button data-model="${escapeHtml(model.filename || '')}">Set Active</button>`
                : '<button disabled>Download in Karl</button>';
        const meta = `${escapeHtml(model.filename || '')}<br>${model.n_ctx || '--'} ctx · ${model.min_ram_gb || '--'} GB RAM · ${model.active ? 'Active' : model.installed ? 'Installed' : 'Missing'}`;
        return buildModelCard(model.name || model.filename || 'Unknown model', meta, action);
    }).join('') : '<div class="model-card"><div class="model-meta">No model registry entries found.</div></div>';
}

function renderDownloadRegistry(models) {
    const panel = $('downloadRegistry');
    if (!panel) return;
    const installed = new Set((models || []).filter(model => model.installed).map(model => model.name || model.filename));
    const tiers = [
        ['1.5B Qwen', 'Fast local scout tier for low-RAM systems and short context tests.', '4 GB'],
        ['7B/8B Qwen/LLaMA', 'Balanced daily-driver tier for coding, review, and RAG workflows.', '12-16 GB'],
        ['14B', 'Higher reasoning headroom for deep planning and longer workbench sessions.', '24 GB'],
        ['70B', 'Maximum local quality tier for workstation-class systems.', '64+ GB']
    ];
    panel.innerHTML = tiers.map(([name, description, ram]) => {
        const isInstalled = Array.from(installed).some(item => String(item).toLowerCase().includes(name.split(' ')[0].toLowerCase()));
        const action = `<button disabled>${isInstalled ? 'Available' : 'Bridge Download Required'}</button>`;
        const meta = `${escapeHtml(description)}<br>Recommended RAM: ${escapeHtml(ram)} · ${isInstalled ? 'Installed candidate detected' : 'Download requires desktop bridge support'}`;
        return buildModelCard(name, meta, action);
    }).join('');
}

// ── theme catalog ──────────────────────────────────────────────────────────────

function renderThemeCatalog() {
    const grid = $('themeGrid');
    if (!grid) return;
    const themes = Array.isArray(window.KARL_THEMES) ? window.KARL_THEMES : [];
    grid.innerHTML = themes.map(theme => {
        if (!theme) return '';
        const vars = theme.vars || {};
        const active = $('themeSelect').value === theme.id;
        const bg = vars['--karl-bg'] || '';
        const panel = vars['--karl-panel'] || '';
        const border = vars['--karl-border'] || '';
        const accent = vars['--karl-accent'] || '';
        return `
            <div class="theme-card ${active ? 'active' : ''}" data-theme-id="${escapeHtml(theme.id)}">
                <div class="theme-card-title">${escapeHtml(theme.name)}</div>
                <div class="theme-card-colors">
                    <span style="background:${escapeHtml(bg)}" title="BG"></span>
                    <span style="background:${escapeHtml(panel)}" title="Panel"></span>
                    <span style="background:${escapeHtml(border)}" title="Border"></span>
                    <span style="background:${escapeHtml(accent)}" title="Accent"></span>
                </div>
                <div class="theme-card-desc">${escapeHtml(theme.description)}</div>
            </div>
        `;
    }).join('');
}

// ── pending-edit cards ─────────────────────────────────────────────────────────

function formatLineDelta(edit) {
    if (!Number.isFinite(edit.lineDelta)) return 'line delta unknown';
    return `${edit.lineDelta >= 0 ? '+' : ''}${edit.lineDelta} lines`;
}

function riskLabel(edit) {
    const delta = Math.abs(Number(edit.lineDelta || 0));
    if (delta > 400 || Number(edit.bytes || 0) > 120000) return '<span class="risk high">high risk</span>';
    if (delta > 80 || Number(edit.bytes || 0) > 30000) return '<span class="risk medium">medium risk</span>';
    return '<span class="risk low">low risk</span>';
}

function renderPendingEdits() {
    const queue = $('changeQueue');
    const filter = $('changeFilter') ? $('changeFilter').value : '';
    const edits = Array.from(pendingEdits.values()).filter(edit => !filter || edit.status === filter);
    if (!edits.length) {
        queue.className = 'queue empty';
        queue.innerText = pendingEdits.size ? 'No edits match the current filter.' : 'No pending Karl edits.';
        return;
    }
    queue.className = 'queue';
    queue.innerHTML = edits.map(edit => `
        <div class="change-card" style="margin-bottom: 8px;">
            <div class="change-title" style="font-size: 13px;">${escapeHtml(edit.filename || 'unknown')}</div>
            <div class="change-meta" style="margin-top: 4px; line-height: 1.4;">
                Path: <strong style="font-family:monospace; font-size:10px;">${escapeHtml(edit.filepath || '')}</strong><br>
                Size: <strong>${Number(edit.bytes || 0)} bytes</strong> · Delta: <strong>${formatLineDelta(edit)}</strong> · Risk: ${riskLabel(edit)} · Status: <span class="state-chip ${escapeHtml(edit.status || 'proposed')}">${escapeHtml(edit.status || 'proposed')}</span><br>
                Summary: <em>${escapeHtml(edit.summary || 'Proposed Karl edit')}</em>
            </div>
            <div class="change-actions" style="margin-top:8px;">
                <button data-preview="${escapeHtml(edit.id)}">Preview Diff</button>
                <button class="primary" data-apply="${escapeHtml(edit.id)}">Apply File</button>
                <button class="danger" data-reject="${escapeHtml(edit.id)}">Reject File</button>
                <button data-open="${escapeHtml(edit.id)}">Open File</button>
                <button data-copy-path="${escapeHtml(edit.id)}">Copy Path</button>
                <button data-rollback="${escapeHtml(edit.id)}">Rollback</button>
            </div>
        </div>
    `).join('');
}

// ── lab diff ───────────────────────────────────────────────────────────────────

function renderLabDiff(textA, textB) {
    const diffContainer = $('labDiff');
    if (!textA || !textB) {
        diffContainer.innerText = 'Run both prompts before computing a diff.';
        return;
    }
    let i = 0, j = 0;
    let html = '';
    while (i < textA.length || j < textB.length) {
        if (i < textA.length && j < textB.length && textA[i] === textB[j]) {
            html += escapeHtml(textA[i]);
            i++; j++;
        } else {
            let del = '', add = '';
            while (i < textA.length && (j >= textB.length || textA[i] !== textB[j])) { del += textA[i]; i++; }
            while (j < textB.length && (i >= textA.length || textA[i] !== textB[j])) { add += textB[j]; j++; }
            if (del) html += `<span class="diff-del">${escapeHtml(del)}</span>`;
            if (add) html += `<span class="diff-add">${escapeHtml(add)}</span>`;
        }
    }
    diffContainer.innerHTML = html;
}

// ── prompt pairs ───────────────────────────────────────────────────────────────

function renderPromptPairs(pairs) {
    $('promptPairSelect').innerHTML = '<option value="">Saved prompt pairs...</option>' + pairs.map(pair => {
        return `<option value="${escapeHtml(pair.name)}">${escapeHtml(pair.name)}</option>`;
    }).join('');
}

// ── knowledge base ─────────────────────────────────────────────────────────────

function renderKbSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') snapshot = {};
    lastKbSnapshot = snapshot;
    const sources = Array.isArray(snapshot.sources) ? snapshot.sources : [];
    $('kbSourceCount').innerText = snapshot.total_sources ?? sources.length ?? 0;
    $('kbChunkCount').innerText = snapshot.total_chunks ?? 0;
    $('kbIngestState').innerText = snapshot.ingesting ? 'Running' : 'Ready';
    $('kbSourceList').innerHTML = sources.length ? sources.map(source => `
        <div class="source-item ${source && source.name === kbSelectedSource ? 'active' : ''}" data-source="${escapeHtml(source ? source.name : '')}">
            <span class="source-name">${escapeHtml(source ? source.name : 'unknown')}</span>
            <span>${Number(source ? source.chunks : 0)} chunks</span>
        </div>
    `).join('') : '<div class="source-item">No indexed sources yet.</div>';

    $('kbSourceFilter').innerHTML = '<option value="">All sources</option>' + sources.map(source => {
        return `<option value="${escapeHtml(source ? source.name : '')}">${escapeHtml(source ? source.name : 'unknown')}</option>`;
    }).join('');
    if (kbSelectedSource) $('kbSourceFilter').value = kbSelectedSource;
}

function renderKbQueue() {
    const panel = $('kbQueue');
    if (!kbQueue.length) {
        panel.className = 'queue-list empty';
        panel.innerText = 'No files queued for batch ingest.';
        return;
    }
    panel.className = 'queue-list';
    panel.innerHTML = kbQueue.map((item, index) => `
        <div class="queue-row ${escapeHtml(item.status || 'queued')}">
            <span>${escapeHtml(item.path)}</span>
            <strong>${escapeHtml(item.status || 'queued')}</strong>
            <button data-remove-kb="${index}">Remove</button>
        </div>
    `).join('');
}

function renderKbSearch(payload) {
    if (!payload || typeof payload !== 'object') payload = {};
    renderKbSnapshot(payload.snapshot || {});
    const results = Array.isArray(payload.results) ? payload.results : [];
    lastKbResults = results;
    $('kbResults').innerHTML = results.length ? results.map((result, index) => {
        if (!result) result = {};
        return `
        <div class="result-card">
            <div class="result-meta">Rank ${escapeHtml(result.rank ?? index)} · ${escapeHtml(result.source_file || 'unknown')} · Chunk ${escapeHtml(result.chunk_id || '0')} · dist=${Number(result.distance || 0).toFixed(4)}</div>
            <pre>${escapeHtml(result.text || '').slice(0, 1800)}</pre>
            <div class="action-row compact-actions" style="margin-top:6px;">
                <button data-send-chat="${index}">Send to Chat</button>
                <button data-send-swarm="${index}">Send to Swarm</button>
            </div>
        </div>
    `; }).join('') : '<div class="result-card">No chunks matched the current query and threshold.</div>';
}

// ── codex ──────────────────────────────────────────────────────────────────────

function renderCodexTopics(topics) {
    if (!Array.isArray(topics)) topics = [];
    $('codexList').innerHTML = topics.length ? topics.map(topic => {
        return `<div class="source-item" data-topic="${escapeHtml(topic)}"><span>${escapeHtml(topic)}</span></div>`;
    }).join('') : '<div class="source-item">No chapters loaded.</div>';
}

// ── branches ───────────────────────────────────────────────────────────────────

function renderBranches() {
    const panel = $('branchTree');
    if (!panel) return;
    if (!conversationBranches.length) {
        panel.className = 'branch-tree empty';
        panel.innerText = 'No conversation branches yet.';
        return;
    }
    panel.className = 'branch-tree';
    panel.innerHTML = conversationBranches.map(branch => `
        <button class="branch-node ${branch.id === activeBranchId ? 'active' : ''}" data-branch="${escapeHtml(branch.id)}">
            <span>${escapeHtml(branch.title || 'Untitled branch')}</span>
            <strong>${branch.turns.length} turn${branch.turns.length === 1 ? '' : 's'}</strong>
        </button>
    `).join('');
}

// ── task queue ─────────────────────────────────────────────────────────────────

function renderTaskQueue() {
    const panel = $('taskQueue');
    if (!taskQueue.length) {
        panel.className = 'task-queue empty';
        panel.innerText = 'No tasks queued.';
        return;
    }
    panel.className = 'task-queue';
    panel.innerHTML = taskQueue.slice(0, 12).map(task => `
        <div class="task-item ${escapeHtml(task.status)}">
            <strong>${escapeHtml(task.mode)}</strong>
            <span>${escapeHtml(task.status)} · ${escapeHtml(task.objective)}</span>
        </div>
    `).join('');
}

// ── context meter ──────────────────────────────────────────────────────────────

function renderContextMeta(meta) {
    if (!meta) {
        $('contextMeter').innerText = 'Context package: none queued.';
        $('contextMeter').className = 'context-meter';
        return;
    }
    $('contextMeter').innerText = `Context package: ${meta.sentChars}/${meta.originalChars} chars sent from ${meta.label}${meta.truncated ? ' · safely truncated' : ''}.`;
    $('contextMeter').className = `context-meter ${meta.truncated ? 'warn' : 'ok'}`;
}

// ── swarm timeline / log ───────────────────────────────────────────────────────

function addTimeline(title, detail) {
    const item = document.createElement('div');
    item.className = 'timeline-item';
    item.innerHTML = `<strong>${escapeHtml(title)}</strong><br>${escapeHtml(detail)}`;
    $('timeline').prepend(item);
    // Mirror to the Swarm Progress tab feed
    const feed = $('swarmFeed');
    if (feed) {
        const placeholder = feed.querySelector('[data-swarm-empty]');
        if (placeholder) placeholder.remove();
        const now = new Date();
        const t = now.toLocaleTimeString('en', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const entry = document.createElement('div');
        entry.className = 'swarm-entry';
        entry.innerHTML = `
            <span class="swarm-entry-time">${escapeHtml(t)}</span>
            <div class="swarm-entry-text">
                <strong>${escapeHtml(title)}</strong>
                <span>${escapeHtml(detail)}</span>
            </div>`;
        feed.appendChild(entry);
        feed.scrollTop = feed.scrollHeight;
    }
}

function log(message) {
    const terminal = $('terminal');
    terminal.innerText += `\n${message}`;
    terminal.scrollTop = terminal.scrollHeight;
}

// ── diagnostics ────────────────────────────────────────────────────────────────

function renderDiagnosticsList(diagDetails) {
    const listPanel = $('diagnosticsList');
    if (!listPanel) return;
    if (!diagDetails || !diagDetails.files || !Object.keys(diagDetails.files).length) {
        listPanel.innerHTML = '<div class="source-item">No current diagnostics found.</div>';
        return;
    }
    let html = '';
    Object.entries(diagDetails.files).forEach(([filepath, items]) => {
        const basename = filepath.split(/[/\\]/).pop();
        html += `<div class="diagnostics-file-header" style="font-weight:750; margin: 8px 0 4px; color: var(--karl-accent-2);">${escapeHtml(basename)}</div>`;
        items.forEach(item => {
            const severityClass = item.severity === 'error' ? 'risk high' : item.severity === 'warning' ? 'risk medium' : 'risk low';
            html += `
                <div class="source-item" data-diag-file="${escapeHtml(filepath)}" data-diag-line="${item.line}" data-diag-char="${item.character}" style="grid-template-columns: auto minmax(0, 1fr) auto; gap: 6px; padding: 4px 6px;">
                    <span class="${severityClass}" style="padding: 1px 4px; font-size: 8px;">${escapeHtml(item.severity)}</span>
                    <span style="font-size: 10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(item.message)}">${escapeHtml(item.message)}</span>
                    <strong style="font-size: 9px; color: var(--karl-muted);">L${item.line}</strong>
                </div>
            `;
        });
    });
    listPanel.innerHTML = html;
}

// ── cockpit state ──────────────────────────────────────────────────────────────

function updateCockpitState(state) {
    $('cockpitWorkspace').innerText = state.workspacePath || '--';
    $('cockpitFile').innerText = state.activeFile ? state.activeFile.split(/[/\\]/).pop() : 'none';
    $('cockpitFile').title = state.activeFile || '';
    $('cockpitBranch').innerText = state.gitBranch || '--';
    $('gitBranchDisplay').innerText = state.gitBranch || '--';
    $('cockpitPendingChanges').innerText = state.pendingEditsCount || 0;

    const diag = state.diagnostics || { error: 0, warning: 0, info: 0, hint: 0 };
    const totalDiag = diag.error + diag.warning + diag.info + diag.hint;
    $('cockpitDiagnostics').innerText = `${totalDiag} problem${totalDiag === 1 ? '' : 's'} (${diag.error} errs)`;

    $('diagErrorsCount').innerText = diag.error || 0;
    $('diagWarningsCount').innerText = diag.warning || 0;
    $('diagInfosCount').innerText = diag.info || 0;
    $('diagHintsCount').innerText = diag.hint || 0;

    renderDiagnosticsList(state.diagnosticsDetails);
}

// ── runtime status ─────────────────────────────────────────────────────────────

function renderRuntimeOffline() {
    $('runtimeModel').innerText = 'unknown';
    $('runtimeState').innerText = 'offline';
    $('runtimeAdapter').innerText = 'none';
    $('runtimeSystem').innerText = '--';
    $('cockpitModel').innerText = 'unknown';
    $('cockpitSystem').innerText = '--';
}

function renderRuntimeStatus(status) {
    if (!status || typeof status !== 'object') status = {};
    const model = status.model || {};
    const adapter = status.adapter || {};
    const runtime = status.runtime || {};
    const system = status.system || {};
    const bridge = status.bridge || {};
    const clients = Number.isInteger(bridge.clients) ? bridge.clients : 0;

    const desc = `${model.name || 'none'}${model.loaded ? ' loaded' : ''}`;
    $('runtimeModel').innerText = desc;
    $('cockpitModel').innerText = desc;

    const stateStr = `${runtime.state || 'idle'} · ${clients} client${clients === 1 ? '' : 's'}`;
    $('runtimeState').innerText = stateStr;
    $('runtimeAdapter').innerText = adapter.name || 'none';

    const sysStr = `${system.ram_mb ?? '--'} MB · ${model.n_ctx || '--'} ctx`;
    $('runtimeSystem').innerText = sysStr;
    $('cockpitSystem').innerText = sysStr;

    if ($('systemActiveModel')) $('systemActiveModel').innerText = model.name || 'none';
    if ($('systemContext')) $('systemContext').innerText = `${model.n_ctx || '--'} ctx`;
    if ($('systemRamCheck')) {
        const ramGb = Number(system.ram_mb || 0) / 1024;
        const needGb = Number(model.min_ram_gb || 0);
        $('systemRamCheck').innerText = needGb && ramGb ? (ramGb >= needGb ? 'ok' : 'low ram') : 'unknown';
    }
    if ($('systemAdapterWarning')) {
        $('systemAdapterWarning').innerText = adapter.name && adapter.base_model && model.name && adapter.base_model !== model.name
            ? 'base mismatch' : 'none';
    }
    if (status.bridge && status.bridge.version) {
        $('bridgeMeta').dataset.version = status.bridge.version;
    }
    if (status.bridge && status.bridge.capabilities && status.bridge.capabilities.includes('vision')) {
        $('visionBridgeWarning').style.display = 'none';
    } else {
        $('visionBridgeWarning').style.display = 'block';
    }
}

// ── chat bubbles ───────────────────────────────────────────────────────────────

function appendMessageBubble(role, text) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    msg.innerHTML = `<div class="message-role">${role === 'user' ? 'User' : 'Karl'}</div><div class="message-content"></div>`;
    const contentEl = msg.querySelector('.message-content');
    if (text) {
        contentEl.innerText = text;
    } else if (role === 'assistant') {
        // Blank assistant bubble signals start of a streaming response.
        // Attach the animated cursor so the user sees immediate activity.
        attachStreamingCursor(contentEl);
    }
    $('chatMessages').appendChild(msg);
    $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
}

function appendChatToken(token) {
    const target = $('chatMessages').querySelector('.message.assistant:last-child .message-content');
    if (target) {
        routeThinkMarkup(token, target);
        $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
}

// Routes incoming response-stream tokens: text content goes to the chat
// bubble; <think>…</think> sections are routed to the reasoning panel.
// The streaming cursor is kept at the very end of chat content at all times.
function routeThinkMarkup(token, chatTarget) {
    const text = String(token || '');
    if (!responseThinkActive && !text.includes('<think') && !text.includes('</think>')) {
        _appendChatText(chatTarget, text);
        return;
    }
    let remaining = text;
    while (remaining.length) {
        if (responseThinkActive) {
            const close = remaining.indexOf('</think>');
            $('introspectionBox').classList.add('active');
            if (close === -1) {
                appendThoughtToken(remaining);
                remaining = '';
            } else {
                appendThoughtToken(remaining.slice(0, close));
                remaining = remaining.slice(close + '</think>'.length);
                responseThinkActive = false;
            }
            continue;
        }
        const open = remaining.indexOf('<think>');
        if (open === -1) {
            _appendChatText(chatTarget, remaining);
            break;
        }
        _appendChatText(chatTarget, remaining.slice(0, open));
        remaining = remaining.slice(open + '<think>'.length);
        responseThinkActive = true;
    }
}

// ── quick actions / recent tasks ───────────────────────────────────────────────

function renderQuickActions() {
    const panel = $('quickActions');
    if (!panel) return;
    const actions = [
        { label: '⚡ Fix Selection', workflow: 'fixSelection' },
        { label: '🔍 Explain Selection', workflow: 'explainSelection' },
        { label: '🧪 Generate Tests', workflow: 'generateTests' },
        { label: '📋 Review File', workflow: 'reviewActiveFile' },
        { label: '📤 Send to Swarm', workflow: 'sendCurrentFileToSwarm' },
        { label: '💬 Ask Workspace', workflow: 'askWorkspace' },
    ];
    panel.innerHTML = actions.map(action => `
        <button class="quick-action" data-workflow="${escapeHtml(action.workflow)}">${escapeHtml(action.label)}</button>
    `).join('');
}

function renderRecentTasks() {
    const panel = $('recentTasksHistory');
    if (!panel) return;
    if (!recentTasks.length) {
        panel.className = 'recent-list empty';
        panel.innerText = 'No recent tasks.';
        return;
    }
    panel.className = 'recent-list';
    panel.innerHTML = recentTasks.slice(0, 8).map((task, index) => `
        <button class="recent-item" data-task-idx="${index}">
            <strong>${escapeHtml(task.title || task.workflowId)}</strong>
            <span>${escapeHtml((task.objective || '').slice(0, 60))}</span>
        </button>
    `).join('');
}

function renderRecentKbQueries() {
    const panel = $('recentKbQueries');
    if (!panel) return;
    if (!recentKbQueries.length) {
        panel.className = 'recent-list empty';
        panel.innerText = 'No recent queries.';
        return;
    }
    panel.className = 'recent-list';
    panel.innerHTML = recentKbQueries.slice(0, 6).map((q, index) => `
        <button class="recent-item" data-kb-query="${index}">
            <span>${escapeHtml(q)}</span>
        </button>
    `).join('');
}
