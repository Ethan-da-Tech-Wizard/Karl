const vscode = acquireVsCodeApi();
const boot = window.KARL_BOOTSTRAP || {};

let socket = null;
let reconnectTimer = null;
let runtimeStatusTimer = null;
let chatFinished = true;
let labRunning = false;
let currentLabTarget = '';
let labOutputA = '';
let labOutputB = '';
let kbSelectedSource = '';
let connectionState = 'offline';
let pendingEdits = new Map();
let manualDisconnect = false;

const $ = (id) => document.getElementById(id);

window.addEventListener('DOMContentLoaded', () => {
    hydrate();
    bindEvents();
    appendMessageBubble('assistant', 'Karl bridge ready. Connect to the desktop app to start.');
    if (boot.autoConnect) connect();
});

window.addEventListener('message', event => {
    const message = event.data || {};
    if (message.command === 'start_code_task') {
        startCodeTask(message.data || {});
    } else if (message.command === 'start_workspace_question') {
        startWorkspaceQuestion(message.data || {});
    } else if (message.command === 'set_kb_path') {
        $('kbPath').value = message.path || '';
        switchWorkspace('kb');
    } else if (message.command === 'pending_file_edit') {
        addPendingEdit(message.edit);
    } else if (message.command === 'file_edit_applied') {
        removePendingEdit(message.editId, 'Applied');
    } else if (message.command === 'file_edit_rejected') {
        removePendingEdit(message.editId, 'Rejected');
    }
});

function hydrate() {
    const persisted = boot.persisted || {};
    $('workspace').value = persisted.workspace || boot.workspaceFolder || '';
    $('bridgePort').value = persisted.port || boot.port || 8080;
    $('taskMode').value = persisted.taskMode || 'Custom Task';
    if (persisted.workspaceTab) switchWorkspace(persisted.workspaceTab);
}

function persist() {
    vscode.postMessage({
        command: 'persist_state',
        state: {
            workspace: $('workspace').value,
            port: Number($('bridgePort').value) || boot.port || 8080,
            taskMode: $('taskMode').value,
            workspaceTab: document.querySelector('.tab.active')?.dataset.workspace || 'swarm'
        }
    });
}

function bindEvents() {
    document.querySelectorAll('.tab').forEach(btn => {
        btn.addEventListener('click', () => switchWorkspace(btn.dataset.workspace));
    });

    $('connectBtn').addEventListener('click', connect);
    $('disconnectBtn').addEventListener('click', disconnect);
    $('runBtn').addEventListener('click', runSwarm);
    $('stopBtn').addEventListener('click', stopSwarm);
    $('askWorkspaceBtn').addEventListener('click', askWorkspace);
    $('chatSendBtn').addEventListener('click', sendChatMessage);
    $('chatInput').addEventListener('keydown', event => {
        if (event.key === 'Enter') sendChatMessage();
    });
    $('refreshKbBtn').addEventListener('click', loadKbSources);
    $('activeFileKbBtn').addEventListener('click', () => vscode.postMessage({ command: 'use_active_file_for_kb' }));
    $('chooseKbFileBtn').addEventListener('click', () => vscode.postMessage({ command: 'choose_kb_file' }));
    $('chooseKbFolderBtn').addEventListener('click', () => vscode.postMessage({ command: 'choose_kb_folder' }));
    $('kbIngestBtn').addEventListener('click', ingestKbPath);
    $('kbSearchBtn').addEventListener('click', searchKb);
    $('loadPairsBtn').addEventListener('click', loadPromptPairs);
    $('promptPairSelect').addEventListener('change', loadSelectedPromptPair);
    $('savePairBtn').addEventListener('click', savePromptPair);
    $('loadPairBtn').addEventListener('click', loadSelectedPromptPair);
    $('deletePairBtn').addEventListener('click', deletePromptPair);
    $('labRunBtn').addEventListener('click', runLab);
    $('diffBtn').addEventListener('click', computeLabDiff);
    $('loadModelsBtn').addEventListener('click', loadModels);
    $('codexSearch').addEventListener('input', filterCodex);
    $('workspace').addEventListener('change', persist);
    $('bridgePort').addEventListener('change', persist);
    $('taskMode').addEventListener('change', persist);
}

function switchWorkspace(wsId) {
    document.querySelectorAll('.workspace').forEach(section => section.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.dataset.workspace === wsId));
    const section = $(`workspace-${wsId}`);
    if (section) section.classList.add('active');

    if (wsId === 'models') loadModels();
    if (wsId === 'kb') loadKbSources();
    if (wsId === 'lab') loadPromptPairs();
    if (wsId === 'codex') loadCodexTopics();
    persist();
}

function setConnectionState(state, label) {
    connectionState = state;
    $('statusDot').className = `status-dot ${state}`;
    $('statusText').innerText = label;
}

function connect() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
    manualDisconnect = false;
    const port = Number($('bridgePort').value) || boot.port || 8080;
    setConnectionState('connecting', 'Connecting');
    log(`[Bridge] Connecting to ws://localhost:${port}`);
    socket = new WebSocket(`ws://localhost:${port}`);

    socket.onopen = () => {
        setConnectionState('connected', 'Connected');
        log('[Bridge] Connected.');
        if (reconnectTimer) {
            clearInterval(reconnectTimer);
            reconnectTimer = null;
        }
        requestRuntimeStatus();
        runtimeStatusTimer = runtimeStatusTimer || setInterval(requestRuntimeStatus, 4000);
        persist();
    };

    socket.onmessage = event => handleSocketMessage(JSON.parse(event.data));
    socket.onerror = () => {
        setConnectionState('offline', 'Error');
        vscode.postMessage({ command: 'show_error', text: 'Karl bridge connection failed. Start Karl and verify the WebSocket port.' });
    };
    socket.onclose = () => {
        setConnectionState('offline', 'Offline');
        renderRuntimeOffline();
        if (runtimeStatusTimer) {
            clearInterval(runtimeStatusTimer);
            runtimeStatusTimer = null;
        }
        if (boot.autoConnect && !manualDisconnect && !reconnectTimer) {
            log('[Bridge] Connection lost. Retrying every 5 seconds.');
            reconnectTimer = setInterval(connect, 5000);
        }
    };
}

function disconnect() {
    manualDisconnect = true;
    if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
    }
    if (runtimeStatusTimer) {
        clearInterval(runtimeStatusTimer);
        runtimeStatusTimer = null;
    }
    if (socket) socket.close();
    socket = null;
    setConnectionState('offline', 'Offline');
}

function handleSocketMessage(data) {
    if (data.error) {
        const message = data.error.message || 'Unknown Karl bridge error.';
        log(`[Bridge Error] ${message}`);
        vscode.postMessage({ command: 'show_error', text: message });
        if (data.id === 51) {
            $('kbIngestBtn').disabled = false;
            $('kbIngestState').innerText = 'Error';
        }
        return;
    }

    if (data.result) {
        handleRpcResult(data.id, data.result);
        return;
    }

    const method = data.method;
    const params = data.params || {};
    if (method === 'status_update') {
        log(params.message || '');
        addTimeline('Status', params.message || '');
    } else if (method === 'task_plan_created') {
        addTimeline('Plan', 'Swarm architect created an implementation plan.');
    } else if (method === 'file_edited') {
        log(`[Edit] Proposed change for ${params.filepath}`);
        vscode.postMessage({
            command: 'queue_file_edit',
            filepath: params.filepath,
            content: params.content,
            summary: params.summary || 'Swarm proposed a file update.'
        });
        switchWorkspace('changes');
    } else if (method === 'test_result') {
        const status = params.passed ? 'passed' : 'failed';
        addTimeline('Test', `Verification ${status}.`);
        log(`[Test] ${status.toUpperCase()}`);
        if (!params.passed && params.error_trace) log(params.error_trace);
    } else if (method === 'finished_swarm') {
        setConnectionState('connected', 'Connected');
        addTimeline('Finished', params.success ? 'Swarm finished successfully.' : 'Swarm finished with issues.');
        log(`[Swarm] ${params.success ? 'SUCCESS' : 'FAILURE'}: ${params.summary || ''}`);
    } else if (method === 'kb_ingest_progress') {
        $('kbIngestState').innerText = `${params.current}/${params.total}`;
        log(`[KB] ${params.current}/${params.total}: ${params.filename}`);
    } else if (method === 'kb_ingest_finished') {
        $('kbIngestBtn').disabled = false;
        $('kbIngestState').innerText = params.error_count ? 'Check Log' : 'Ready';
        renderKbSnapshot(params.snapshot || {});
        log(`[KB] Added ${params.chunks_added} chunk(s) from ${params.file_count} file(s).`);
        (params.errors || []).forEach(err => log(`[KB] ${err.filename}: ${err.error}`));
    } else if (method === 'chat_thought_token') {
        if (!labRunning) {
            $('introspectionBox').classList.add('active');
            $('introspectionThoughts').innerText += params.token || '';
            $('introspectionThoughts').scrollTop = $('introspectionThoughts').scrollHeight;
        }
    } else if (method === 'chat_response_token') {
        handleResponseToken(params.token || '');
    } else if (method === 'chat_finished') {
        handleChatFinished();
    }
}

function handleRpcResult(id, result) {
    if (id === 12) {
        $('labDiff').innerHTML = result.diff_html || '';
        labRunning = false;
        $('labRunBtn').disabled = false;
        log('[Prompt Lab] Diff complete.');
    } else if (id === 30) {
        renderRuntimeStatus(result);
    } else if (id === 31) {
        renderModels(result.models || []);
    } else if (id === 32) {
        log(`[Models] ${result.message || 'Model updated.'}`);
        requestRuntimeStatus();
        loadModels();
    } else if (id === 40) {
        renderPromptPairs(result.pairs || []);
    } else if (id === 41) {
        applyPromptPair(result);
    } else if (id === 42) {
        $('promptPairName').value = result.name || '';
        log(`[Prompt Lab] Saved pair ${result.name || ''}`);
        loadPromptPairs();
    } else if (id === 43) {
        log(`[Prompt Lab] Deleted pair ${result.name || ''}`);
        $('promptPairName').value = '';
        loadPromptPairs();
    } else if (id === 50) {
        renderKbSnapshot(result);
    } else if (id === 51) {
        $('kbIngestBtn').disabled = true;
        $('kbIngestState').innerText = 'Running';
        log(`[KB] Ingestion started for ${result.file_count} file(s).`);
    } else if (id === 52) {
        renderKbSearch(result);
    } else if (id === 20) {
        renderCodexTopics(result.topics || []);
    } else if (id === 21) {
        $('codexViewer').innerHTML = result.content || '';
    }
}

function requestRuntimeStatus() {
    rpc(30, 'get_runtime_status');
}

function renderRuntimeStatus(status) {
    const model = status.model || {};
    const adapter = status.adapter || {};
    const runtime = status.runtime || {};
    const system = status.system || {};
    const bridge = status.bridge || {};
    const clients = Number.isInteger(bridge.clients) ? bridge.clients : 0;

    $('runtimeModel').innerText = `${model.name || 'none'}${model.loaded ? ' loaded' : ''}`;
    $('runtimeState').innerText = `${runtime.state || 'idle'} · ${clients} client${clients === 1 ? '' : 's'}`;
    $('runtimeAdapter').innerText = adapter.name || 'none';
    $('runtimeSystem').innerText = `${system.ram_mb ?? '--'} MB · ${model.n_ctx || '--'} ctx`;
}

function renderRuntimeOffline() {
    $('runtimeModel').innerText = 'unknown';
    $('runtimeState').innerText = 'offline';
    $('runtimeAdapter').innerText = 'none';
    $('runtimeSystem').innerText = '--';
}

function startCodeTask(data) {
    $('taskMode').value = data.mode || 'Custom Task';
    $('workspace').value = data.workspace_path || '';
    $('objective').value = [
        `Mode: ${data.mode || 'Code Task'}`,
        `Target File: ${data.filepath || 'unknown'}`,
        `Objective: ${data.objective || ''}`,
        '',
        'Code Context:',
        data.code || ''
    ].join('\n');
    switchWorkspace('swarm');
    connectAndRun();
}

function startWorkspaceQuestion(data) {
    $('taskMode').value = 'Custom Task';
    $('workspace').value = data.workspace_path || '';
    $('objective').value = data.objective || '';
    switchWorkspace('swarm');
}

function askWorkspace() {
    const objective = $('objective').value.trim() || 'Review this workspace and identify the highest value next improvements.';
    $('objective').value = objective;
    runSwarm();
}

function connectAndRun() {
    if (isConnected()) {
        runSwarm();
        return;
    }
    connect();
    const started = Date.now();
    const timer = setInterval(() => {
        if (isConnected()) {
            clearInterval(timer);
            runSwarm();
        } else if (Date.now() - started > 8000) {
            clearInterval(timer);
            vscode.postMessage({ command: 'show_error', text: 'Karl bridge did not connect within 8 seconds.' });
        }
    }, 150);
}

function runSwarm() {
    const objective = $('objective').value.trim();
    const workspace = $('workspace').value.trim();
    const testCommand = $('testCmd').value.trim();
    if (!objective || !workspace) {
        vscode.postMessage({ command: 'show_error', text: 'Objective and workspace path are required.' });
        return;
    }
    if (!isConnected()) {
        connectAndRun();
        return;
    }
    setConnectionState('running', 'Running');
    $('terminal').innerText = '--- Swarm Logs ---';
    $('timeline').innerHTML = '';
    addTimeline('Launch', $('taskMode').value);
    log('[Swarm] Deploying Karl agents.');
    rpc(1, 'submit_task', {
        objective,
        workspace_path: workspace,
        test_command: testCommand,
        hyperparams: hyperparams()
    });
}

function stopSwarm() {
    rpc(2, 'stop_task');
}

function sendChatMessage() {
    const input = $('chatInput');
    const text = input.value.trim();
    if (!text || !chatFinished) return;
    if (!isConnected()) {
        vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected.' });
        return;
    }
    appendMessageBubble('user', text);
    appendMessageBubble('assistant', '');
    input.value = '';
    chatFinished = false;
    $('chatSendBtn').disabled = true;
    $('introspectionThoughts').innerText = '';
    $('introspectionBox').classList.remove('active');
    rpc(3, 'submit_chat', {
        message: text,
        workspace_path: $('workspace').value.trim(),
        hyperparams: hyperparams()
    });
}

function handleResponseToken(token) {
    if (labRunning) {
        if (currentLabTarget === 'A') {
            labOutputA += token;
            $('labOutputA').innerText = labOutputA;
        } else {
            labOutputB += token;
            $('labOutputB').innerText = labOutputB;
        }
        return;
    }
    appendChatToken(token);
}

function handleChatFinished() {
    if (labRunning) {
        if (currentLabTarget === 'A') {
            currentLabTarget = 'B';
            $('labOutputB').innerText = 'Generating output B...';
            sendLabMessage('B', $('labSysB').value, $('labUser').value);
        } else {
            computeLabDiff();
        }
        return;
    }
    chatFinished = true;
    $('chatSendBtn').disabled = false;
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
        target.innerText += token;
        $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
}

function addPendingEdit(edit) {
    if (!edit || !edit.id) return;
    pendingEdits.set(edit.id, edit);
    renderPendingEdits();
}

function removePendingEdit(editId, state) {
    pendingEdits.delete(editId);
    renderPendingEdits();
    log(`[Changes] ${state} pending edit ${editId}.`);
}

function renderPendingEdits() {
    const queue = $('changeQueue');
    if (!pendingEdits.size) {
        queue.className = 'queue empty';
        queue.innerText = 'No pending Karl edits.';
        return;
    }
    queue.className = 'queue';
    queue.innerHTML = Array.from(pendingEdits.values()).map(edit => `
        <div class="change-card">
            <div class="change-title">${escapeHtml(edit.filename || 'unknown')}</div>
            <div class="change-meta">${escapeHtml(edit.filepath || '')}<br>${Number(edit.bytes || 0)} bytes · ${escapeHtml(edit.summary || 'Proposed Karl edit')}</div>
            <div class="change-actions">
                <button data-preview="${escapeHtml(edit.id)}">Preview</button>
                <button class="primary" data-apply="${escapeHtml(edit.id)}">Apply</button>
                <button class="danger" data-reject="${escapeHtml(edit.id)}">Reject</button>
            </div>
        </div>
    `).join('');

    queue.querySelectorAll('[data-preview]').forEach(btn => btn.addEventListener('click', () => {
        vscode.postMessage({ command: 'preview_file', editId: btn.dataset.preview });
    }));
    queue.querySelectorAll('[data-apply]').forEach(btn => btn.addEventListener('click', () => {
        vscode.postMessage({ command: 'apply_file', editId: btn.dataset.apply });
    }));
    queue.querySelectorAll('[data-reject]').forEach(btn => btn.addEventListener('click', () => {
        vscode.postMessage({ command: 'reject_file', editId: btn.dataset.reject });
    }));
}

function runLab() {
    if (labRunning) return;
    if (!$('labUser').value.trim()) {
        vscode.postMessage({ command: 'show_error', text: 'Prompt Lab needs a user message.' });
        return;
    }
    if (!isConnected()) {
        vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected.' });
        return;
    }
    labRunning = true;
    currentLabTarget = 'A';
    labOutputA = '';
    labOutputB = '';
    $('labRunBtn').disabled = true;
    $('labOutputA').innerText = 'Generating output A...';
    $('labOutputB').innerText = 'Waiting...';
    $('labDiff').innerText = 'Waiting for both runs...';
    sendLabMessage('A', $('labSysA').value, $('labUser').value);
}

function sendLabMessage(target, systemPrompt, userMsg) {
    currentLabTarget = target;
    const params = hyperparams();
    params.system_prompt = systemPrompt;
    rpc(10 + (target === 'A' ? 0 : 1), 'submit_chat', {
        message: userMsg,
        hyperparams: params
    });
}

function computeLabDiff() {
    if (!labOutputA || !labOutputB) {
        $('labDiff').innerText = 'Run both prompts before computing a diff.';
        return;
    }
    rpc(12, 'compute_diff', { text_a: labOutputA, text_b: labOutputB });
}

function loadPromptPairs() {
    rpc(40, 'list_prompt_pairs');
}

function renderPromptPairs(pairs) {
    $('promptPairSelect').innerHTML = '<option value="">Saved prompt pairs...</option>' + pairs.map(pair => {
        return `<option value="${escapeHtml(pair.name)}">${escapeHtml(pair.name)}</option>`;
    }).join('');
}

function loadSelectedPromptPair() {
    const name = $('promptPairSelect').value || $('promptPairName').value.trim();
    if (name) rpc(41, 'get_prompt_pair', { name });
}

function applyPromptPair(pair) {
    $('promptPairName').value = pair.name || '';
    $('promptPairSelect').value = pair.name || '';
    $('labSysA').value = pair.system_a || '';
    $('labSysB').value = pair.system_b || '';
    $('labUser').value = pair.user_a || pair.user_b || '';
    labOutputA = pair.output_a_raw || '';
    labOutputB = pair.output_b_raw || '';
    $('labOutputA').innerText = pair.output_a_display || labOutputA || 'Output A will stream here...';
    $('labOutputB').innerText = pair.output_b_display || labOutputB || 'Output B will stream here...';
}

function savePromptPair() {
    const name = $('promptPairName').value.trim();
    if (!name) {
        vscode.postMessage({ command: 'show_error', text: 'Prompt pair name is required.' });
        return;
    }
    const userMsg = $('labUser').value;
    rpc(42, 'save_prompt_pair', {
        name,
        system_a: $('labSysA').value,
        user_a: userMsg,
        system_b: $('labSysB').value,
        user_b: userMsg,
        rag_a: $('karlRag').checked,
        rag_b: $('karlRag').checked,
        loop_a: $('karlLoop').checked,
        loop_b: $('karlLoop').checked,
        output_a_raw: labOutputA,
        output_b_raw: labOutputB,
        output_a_display: $('labOutputA').innerText,
        output_b_display: $('labOutputB').innerText
    });
}

function deletePromptPair() {
    const name = $('promptPairSelect').value || $('promptPairName').value.trim();
    if (name) rpc(43, 'delete_prompt_pair', { name });
}

function loadKbSources() {
    if (!isConnected()) {
        $('kbSourceList').innerHTML = '<div class="source-item">Karl bridge is offline.</div>';
        return;
    }
    rpc(50, 'list_kb_sources');
}

function renderKbSnapshot(snapshot) {
    const sources = snapshot.sources || [];
    $('kbSourceCount').innerText = snapshot.total_sources || sources.length || 0;
    $('kbChunkCount').innerText = snapshot.total_chunks || 0;
    $('kbIngestState').innerText = snapshot.ingesting ? 'Running' : 'Ready';
    $('kbSourceList').innerHTML = sources.length ? sources.map(source => `
        <div class="source-item ${source.name === kbSelectedSource ? 'active' : ''}" data-source="${escapeHtml(source.name)}">
            <span class="source-name">${escapeHtml(source.name)}</span>
            <span>${Number(source.chunks || 0)} chunks</span>
        </div>
    `).join('') : '<div class="source-item">No indexed sources yet.</div>';

    $('kbSourceList').querySelectorAll('[data-source]').forEach(row => {
        row.addEventListener('click', () => {
            kbSelectedSource = row.dataset.source || '';
            $('kbSourceFilter').value = kbSelectedSource;
            renderKbSnapshot(snapshot);
        });
    });

    $('kbSourceFilter').innerHTML = '<option value="">All sources</option>' + sources.map(source => {
        return `<option value="${escapeHtml(source.name)}">${escapeHtml(source.name)}</option>`;
    }).join('');
    if (kbSelectedSource) $('kbSourceFilter').value = kbSelectedSource;
}

function ingestKbPath() {
    if (!isConnected()) {
        vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected.' });
        return;
    }
    const ingestPath = $('kbPath').value.trim();
    const chunkSize = Number($('kbChunkSize').value) || 200;
    const overlap = Number($('kbOverlap').value) || 0;
    if (!ingestPath) {
        vscode.postMessage({ command: 'show_error', text: 'Choose a file or folder to ingest.' });
        return;
    }
    if (overlap >= chunkSize) {
        vscode.postMessage({ command: 'show_error', text: 'Overlap must be lower than chunk size.' });
        return;
    }
    $('kbIngestBtn').disabled = true;
    $('kbIngestState').innerText = 'Starting';
    rpc(51, 'ingest_path', {
        path: ingestPath,
        recursive: $('kbRecursive').checked,
        chunk_size: chunkSize,
        overlap
    });
}

function searchKb() {
    const query = $('kbQuery').value.trim();
    if (!query) {
        vscode.postMessage({ command: 'show_error', text: 'Enter a retrieval preview query.' });
        return;
    }
    $('kbResults').innerHTML = '<div class="result-card">Searching index...</div>';
    rpc(52, 'search_kb', {
        query,
        top_k: Number($('kbTopK').value) || 5,
        threshold: Number($('kbThreshold').value) || 0,
        source_filter: $('kbSourceFilter').value || null
    });
}

function renderKbSearch(payload) {
    renderKbSnapshot(payload.snapshot || {});
    const results = payload.results || [];
    $('kbResults').innerHTML = results.length ? results.map((result, index) => `
        <div class="result-card">
            <div class="result-meta">Rank ${escapeHtml(result.rank ?? index)} · ${escapeHtml(result.source_file || 'unknown')} · Chunk ${escapeHtml(result.chunk_id)} · dist=${Number(result.distance || 0).toFixed(4)}</div>
            <pre>${escapeHtml(result.text || '').slice(0, 1800)}</pre>
        </div>
    `).join('') : '<div class="result-card">No chunks matched the current query and threshold.</div>';
}

function loadModels() {
    if (!isConnected()) {
        $('modelList').innerHTML = '<div class="model-card"><div class="model-meta">Karl bridge is offline.</div></div>';
        return;
    }
    rpc(31, 'list_models');
}

function renderModels(models) {
    $('modelList').innerHTML = models.length ? models.map(model => {
        const action = model.active
            ? '<button disabled>Active</button>'
            : model.installed
                ? `<button data-model="${escapeHtml(model.filename || '')}">Set Active</button>`
                : '<button disabled>Download in Karl</button>';
        return `<div class="model-card">
            <div class="model-title">${escapeHtml(model.name || model.filename || 'Unknown model')}</div>
            <div class="model-meta">${escapeHtml(model.filename || '')}<br>${model.n_ctx || '--'} ctx · ${model.min_ram_gb || '--'} GB RAM · ${model.active ? 'Active' : model.installed ? 'Installed' : 'Missing'}</div>
            ${action}
        </div>`;
    }).join('') : '<div class="model-card"><div class="model-meta">No model registry entries found.</div></div>';

    $('modelList').querySelectorAll('[data-model]').forEach(btn => {
        btn.addEventListener('click', () => rpc(32, 'set_active_model', { filename: btn.dataset.model }));
    });
}

function loadCodexTopics() {
    rpc(20, 'list_codex_topics');
}

function renderCodexTopics(topics) {
    $('codexList').innerHTML = topics.length ? topics.map(topic => {
        return `<div class="source-item" data-topic="${escapeHtml(topic)}"><span>${escapeHtml(topic)}</span></div>`;
    }).join('') : '<div class="source-item">No chapters loaded.</div>';
    $('codexList').querySelectorAll('[data-topic]').forEach(row => {
        row.addEventListener('click', () => {
            $('codexViewer').innerHTML = 'Loading reference...';
            rpc(21, 'get_codex_content', { topic: row.dataset.topic });
        });
    });
}

function filterCodex() {
    const q = $('codexSearch').value.toLowerCase();
    $('codexList').querySelectorAll('.source-item').forEach(item => {
        item.style.display = item.innerText.toLowerCase().includes(q) ? 'grid' : 'none';
    });
}

function hyperparams() {
    return {
        temperature: Number($('karlTemp').value) || 0.7,
        top_p: Number($('karlTopP').value) || 0.95,
        max_tokens: Number($('karlMaxTok').value) || 2048,
        rag_enabled: $('karlRag').checked,
        agentic_loop_enabled: $('karlLoop').checked,
        rag_top_k: Number($('kbTopK').value) || 5,
        rag_threshold: Number($('kbThreshold').value) || 0
    };
}

function rpc(id, method, params) {
    if (!isConnected()) {
        if (![20, 31, 40, 50].includes(id)) {
            vscode.postMessage({ command: 'show_error', text: 'Karl bridge is offline.' });
        }
        return;
    }
    socket.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }));
}

function isConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
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

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}
