function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

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

function renderLabDiff(textA, textB) {
    const diffContainer = $('labDiff');
    if (!textA || !textB) {
        diffContainer.innerText = 'Run both prompts before computing a diff.';
        return;
    }
    
    // Character-level simple diffing
    let i = 0, j = 0;
    let html = '';
    while (i < textA.length || j < textB.length) {
        if (i < textA.length && j < textB.length && textA[i] === textB[j]) {
            html += escapeHtml(textA[i]);
            i++;
            j++;
        } else {
            let del = '';
            let add = '';
            while (i < textA.length && (j >= textB.length || textA[i] !== textB[j])) {
                del += textA[i];
                i++;
            }
            while (j < textB.length && (i >= textA.length || textA[i] !== textB[j])) {
                add += textB[j];
                j++;
            }
            if (del) html += `<span class="diff-del" style="background: rgba(255, 107, 122, 0.25); border-bottom: 1px solid var(--karl-danger);">${escapeHtml(del)}</span>`;
            if (add) html += `<span class="diff-add" style="background: rgba(114, 245, 164, 0.25); border-bottom: 1px solid var(--karl-good);">${escapeHtml(add)}</span>`;
        }
    }
    diffContainer.innerHTML = html;
}

function renderPromptPairs(pairs) {
    $('promptPairSelect').innerHTML = '<option value="">Saved prompt pairs...</option>' + pairs.map(pair => {
        return `<option value="${escapeHtml(pair.name)}">${escapeHtml(pair.name)}</option>`;
    }).join('');
}

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

function renderCodexTopics(topics) {
    if (!Array.isArray(topics)) topics = [];
    $('codexList').innerHTML = topics.length ? topics.map(topic => {
        return `<div class="source-item" data-topic="${escapeHtml(topic)}"><span>${escapeHtml(topic)}</span></div>`;
    }).join('') : '<div class="source-item">No chapters loaded.</div>';
}

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

function renderContextMeta(meta) {
    if (!meta) {
        $('contextMeter').innerText = 'Context package: none queued.';
        $('contextMeter').className = 'context-meter';
        return;
    }
    $('contextMeter').innerText = `Context package: ${meta.sentChars}/${meta.originalChars} chars sent from ${meta.label}${meta.truncated ? ' · safely truncated' : ''}.`;
    $('contextMeter').className = `context-meter ${meta.truncated ? 'warn' : 'ok'}`;
}

function addTimeline(title, detail) {
    const item = document.createElement('div');
    item.className = 'timeline-item';
    item.innerHTML = `<strong>${escapeHtml(title)}</strong><br>${escapeHtml(detail)}`;
    $('timeline').prepend(item);
}

function log(message) {
    const terminal = $('terminal');
    terminal.innerText += `\n${message}`;
    terminal.scrollTop = terminal.scrollHeight;
}

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
            ? 'base mismatch'
            : 'none';
    }
    if (status.bridge && status.bridge.version) {
        $('bridgeMeta').dataset.version = status.bridge.version;
    }
    
    // Hide Vision warning if bridge version reports Vision capability
    if (status.bridge && status.bridge.capabilities && status.bridge.capabilities.includes('vision')) {
        $('visionBridgeWarning').style.display = 'none';
    } else {
        $('visionBridgeWarning').style.display = 'block';
    }
}

function appendMessageBubble(role, text) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    msg.innerHTML = `<div class="message-role">${role === 'user' ? 'User' : 'Karl'}</div><div class="message-content"></div>`;
    msg.querySelector('.message-content').innerText = text;
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

function routeThinkMarkup(token, chatTarget) {
    const text = String(token || '');
    if (!responseThinkActive && !text.includes('<think') && !text.includes('</think>')) {
        chatTarget.innerText += text;
        return;
    }
    let remaining = text;
    while (remaining.length) {
        if (responseThinkActive) {
            const close = remaining.indexOf('</think>');
            $('introspectionBox').classList.add('active');
            if (close === -1) {
                $('introspectionThoughts').innerText += remaining;
                remaining = '';
            } else {
                $('introspectionThoughts').innerText += remaining.slice(0, close);
                remaining = remaining.slice(close + '</think>'.length);
                responseThinkActive = false;
            }
            continue;
        }

        const open = remaining.indexOf('<think>');
        if (open === -1) {
            chatTarget.innerText += remaining;
            break;
        }
        chatTarget.innerText += remaining.slice(0, open);
        remaining = remaining.slice(open + '<think>'.length);
        responseThinkActive = true;
    }
    $('introspectionThoughts').scrollTop = $('introspectionThoughts').scrollHeight;
}
