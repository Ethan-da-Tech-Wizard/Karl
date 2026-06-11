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
let persistTimer = null;
let recentObjectives = [];
let recentKbQueries = [];
let taskQueue = [];
let activeTaskId = '';
let lastHeartbeatAt = null;
let lastConnectedAt = null;
let lastBridgeError = '';
let kbQueue = [];
let kbQueueRunning = false;
let conversationBranches = [];
let activeBranchId = '';
let currentConversationInput = '';
let responseThinkActive = false;

const $ = (id) => document.getElementById(id);

window.addEventListener('DOMContentLoaded', () => {
    initializeAppearance();
    hydrate();
    bindEvents();
    renderQuickActions();
    renderRecentObjectives();
    renderRecentKbQueries();
    renderTaskQueue();
    renderKbQueue();
    renderBranches();
    renderDownloadRegistry([]);
    setInterval(() => updateBridgeMeta(), 1000);
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
    } else if (message.command === 'search_kb_text') {
        $('kbQuery').value = message.query || '';
        switchWorkspace('kb');
        searchKb();
    } else if (message.command === 'open_review_bay') {
        switchWorkspace('changes');
    } else if (message.command === 'pending_file_edit') {
        addPendingEdit(message.edit);
    } else if (message.command === 'file_edit_previewed') {
        markPendingEdit(message.editId, 'previewed');
    } else if (message.command === 'file_edit_applied') {
        markPendingEdit(message.editId, message.backupExists ? 'applied' : 'applied');
    } else if (message.command === 'file_edit_rejected') {
        removePendingEdit(message.editId, 'Rejected');
    } else if (message.command === 'file_edit_rolled_back') {
        markPendingEdit(message.editId, 'rolled_back');
    }
});

function hydrate() {
    const persisted = boot.persisted || {};
    $('workspace').value = persisted.workspace || boot.workspaceFolder || '';
    $('bridgePort').value = persisted.port || boot.port || 8080;
    $('taskMode').value = persisted.taskMode || 'Custom Task';
    $('themeSelect').value = persisted.theme || 'obsidian-core';
    $('customAccent').value = persisted.customAccent || themeById($('themeSelect').value).vars['--karl-accent'];
    $('layoutSelect').value = persisted.layout || 'cockpit';
    recentObjectives = Array.isArray(persisted.recentObjectives) ? persisted.recentObjectives.slice(0, 12) : [];
    recentKbQueries = Array.isArray(persisted.recentKbQueries) ? persisted.recentKbQueries.slice(0, 12) : [];
    conversationBranches = Array.isArray(persisted.conversationBranches) ? persisted.conversationBranches.slice(0, 20) : [];
    activeBranchId = persisted.activeBranchId || (conversationBranches[0] && conversationBranches[0].id) || '';
    applyAppearance();
    if (persisted.workspaceTab) switchWorkspace(persisted.workspaceTab);
}

function persist() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
        vscode.postMessage({
            command: 'persist_state',
            state: {
                workspace: $('workspace').value,
                port: Number($('bridgePort').value) || boot.port || 8080,
                taskMode: $('taskMode').value,
                workspaceTab: document.querySelector('.tab.active')?.dataset.workspace || 'swarm',
                theme: $('themeSelect').value,
                customAccent: $('customAccent').value,
                layout: $('layoutSelect').value,
                recentObjectives: recentObjectives.slice(0, 12),
                recentKbQueries: recentKbQueries.slice(0, 12),
                conversationBranches: conversationBranches.slice(0, 20),
                activeBranchId
            }
        });
    }, 250);
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
    $('kbQueueAddBtn').addEventListener('click', addKbQueuePath);
    $('kbQueueRunBtn').addEventListener('click', ingestKbQueue);
    $('kbQueueClearBtn').addEventListener('click', () => {
        kbQueue = [];
        renderKbQueue();
    });
    $('kbIngestBtn').addEventListener('click', ingestKbPath);
    $('kbSearchBtn').addEventListener('click', searchKb);
    $('loadPairsBtn').addEventListener('click', loadPromptPairs);
    $('promptPairSelect').addEventListener('change', loadSelectedPromptPair);
    $('savePairBtn').addEventListener('click', savePromptPair);
    $('loadPairBtn').addEventListener('click', loadSelectedPromptPair);
    $('deletePairBtn').addEventListener('click', deletePromptPair);
    $('labRunBtn').addEventListener('click', runLab);
    $('diffBtn').addEventListener('click', computeLabDiff);
    $('labSysA').addEventListener('input', () => {
        if ($('labLockSync').checked) $('labSysB').value = $('labSysA').value;
    });
    $('tokenizeLabBtn').addEventListener('click', () => requiresBridgeSupport('Prompt Lab tokenizer visualization', 'tokenize_text'));
    $('loadModelsBtn').addEventListener('click', loadModels);
    $('branchLatestBtn').addEventListener('click', branchFromLatest);
    $('newBranchBtn').addEventListener('click', createConversationBranch);
    $('trainingCheckBtn').addEventListener('click', () => requiresBridgeSupport('Training dependency checks', 'training_status'));
    $('trainingValidateBtn').addEventListener('click', validateTrainingForm);
    $('trainingRunBtn').addEventListener('click', () => requiresBridgeSupport('Training run orchestration', 'start_training'));
    $('trainingExportBtn').addEventListener('click', () => requiresBridgeSupport('Training export from VS Code', 'export_training_dataset'));
    $('evalRefreshBtn').addEventListener('click', () => requiresBridgeSupport('Eval harness status', 'eval_status'));
    $('evalRunBtn').addEventListener('click', () => requiresBridgeSupport('Eval harness execution', 'run_eval'));
    $('evalStopBtn').addEventListener('click', () => requiresBridgeSupport('Eval cancellation', 'stop_eval'));
    $('evalExportBtn').addEventListener('click', () => requiresBridgeSupport('Eval summary export', 'export_eval_summary'));
    $('codexSearch').addEventListener('input', filterCodex);
    $('workspace').addEventListener('change', persist);
    $('bridgePort').addEventListener('change', persist);
    $('taskMode').addEventListener('change', persist);
    $('previewAllBtn').addEventListener('click', () => vscode.postMessage({ command: 'preview_all_files' }));
    $('rejectAllBtn').addEventListener('click', () => vscode.postMessage({ command: 'reject_all_files' }));
    $('copySummaryBtn').addEventListener('click', () => vscode.postMessage({ command: 'copy_patch_summary' }));
    $('changeFilter').addEventListener('change', renderPendingEdits);
    $('clearTasksBtn').addEventListener('click', () => {
        taskQueue = taskQueue.filter(task => task.status === 'running');
        renderTaskQueue();
    });
    $('clearHistoryBtn').addEventListener('click', () => {
        recentObjectives = [];
        renderRecentObjectives();
        persist();
    });
    $('themeSelect').addEventListener('change', applyAppearance);
    $('customAccent').addEventListener('input', applyAppearance);
    $('layoutSelect').addEventListener('change', applyAppearance);
    $('resetAppearanceBtn').addEventListener('click', () => {
        $('themeSelect').value = 'obsidian-core';
        $('customAccent').value = '#00c2ff';
        $('layoutSelect').value = 'cockpit';
        applyAppearance();
    });
}

function switchWorkspace(wsId) {
    document.querySelectorAll('.workspace').forEach(section => section.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.dataset.workspace === wsId));
    const section = $(`workspace-${wsId}`);
    if (section) section.classList.add('active');

    if (wsId === 'system') loadModels();
    if (wsId === 'kb') loadKbSources();
    if (wsId === 'lab') loadPromptPairs();
    if (wsId === 'codex') loadCodexTopics();
    persist();
}

function setConnectionState(state, label) {
    connectionState = state;
    $('statusDot').className = `status-dot ${state}`;
    $('statusText').innerText = label;
    $('offlinePanel').classList.toggle('active', state !== 'connected' && state !== 'running');
    updateBridgeMeta();
}

function connect() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
    manualDisconnect = false;
    const port = Number($('bridgePort').value) || boot.port || 8080;
    setConnectionState('connecting', 'Connecting');
    log(`[Bridge] Connecting to ws://localhost:${port}`);
    socket = new WebSocket(`ws://localhost:${port}`);

    socket.onopen = () => {
        lastConnectedAt = new Date();
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
        lastBridgeError = 'Connection failed';
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
        lastBridgeError = message;
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
        finishActiveTask(params.success ? 'completed' : 'failed');
        addTimeline('Finished', params.success ? 'Swarm finished successfully.' : 'Swarm finished with issues.');
        log(`[Swarm] ${params.success ? 'SUCCESS' : 'FAILURE'}: ${params.summary || ''}`);
    } else if (method === 'kb_ingest_progress') {
        $('kbIngestState').innerText = `${params.current}/${params.total}`;
        log(`[KB] ${params.current}/${params.total}: ${params.filename}`);
    } else if (method === 'kb_ingest_finished') {
        $('kbIngestBtn').disabled = false;
        $('kbIngestState').innerText = params.error_count ? 'Check Log' : 'Ready';
        markCurrentKbQueueDone(params.error_count ? 'error' : 'done');
        renderKbSnapshot(params.snapshot || {});
        log(`[KB] Added ${params.chunks_added} chunk(s) from ${params.file_count} file(s).`);
        (params.errors || []).forEach(err => log(`[KB] ${err.filename}: ${err.error}`));
        if (kbQueueRunning) ingestNextQueuedPath();
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
        lastHeartbeatAt = new Date();
        renderRuntimeStatus(result);
        updateBridgeMeta(result);
    } else if (id === 31) {
        renderModels(result.models || []);
        renderDownloadRegistry(result.models || []);
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
    renderContextMeta(data.context_meta);
    rememberObjective(data.objective || '', data.filepath || '', data.mode || 'Code Task');
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
    activeTaskId = addTask($('taskMode').value, objective);
    rememberObjective(objective, workspace, $('taskMode').value);
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
    currentConversationInput = text;
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
    const lastAssistant = $('chatMessages').querySelector('.message.assistant:last-child .message-content');
    recordConversationTurn(currentConversationInput, lastAssistant ? lastAssistant.innerText : '');
    currentConversationInput = '';
}

function activeBranch() {
    if (!activeBranchId) createConversationBranch();
    return conversationBranches.find(branch => branch.id === activeBranchId) || conversationBranches[0];
}

function createConversationBranch(seedTitle = '') {
    const id = `branch-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const branch = {
        id,
        title: seedTitle || `Branch ${conversationBranches.length + 1}`,
        turns: [],
        createdAt: new Date().toISOString()
    };
    conversationBranches.unshift(branch);
    activeBranchId = id;
    renderBranches();
    persist();
}

function branchFromLatest() {
    const current = activeBranch();
    const id = `branch-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const branch = {
        id,
        title: `Fork of ${current.title || 'Workbench'}`,
        turns: current.turns.slice(0, -1),
        createdAt: new Date().toISOString()
    };
    conversationBranches.unshift(branch);
    activeBranchId = id;
    renderBranches();
    vscode.postMessage({ command: 'show_message', text: 'Karl conversation branch created in the Workbench panel.' });
    persist();
}

function recordConversationTurn(user, assistant) {
    const prompt = String(user || '').trim();
    const response = String(assistant || '').trim();
    if (!prompt && !response) return;
    const branch = activeBranch();
    branch.turns.push({ user: prompt, assistant: response, at: new Date().toISOString() });
    branch.title = prompt.slice(0, 48) || branch.title;
    conversationBranches = [branch, ...conversationBranches.filter(item => item.id !== branch.id)].slice(0, 20);
    activeBranchId = branch.id;
    renderBranches();
    persist();
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
    panel.querySelectorAll('[data-branch]').forEach(btn => {
        btn.addEventListener('click', () => {
            activeBranchId = btn.dataset.branch;
            renderBranches();
            persist();
        });
    });
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

function addPendingEdit(edit) {
    if (!edit || !edit.id) return;
    pendingEdits.set(edit.id, edit);
    renderPendingEdits();
}

function markPendingEdit(editId, status) {
    const edit = pendingEdits.get(editId);
    if (edit) {
        edit.status = status;
        pendingEdits.set(editId, edit);
        renderPendingEdits();
    }
}

function removePendingEdit(editId, state) {
    pendingEdits.delete(editId);
    renderPendingEdits();
    log(`[Changes] ${state} pending edit ${editId}.`);
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
        <div class="change-card">
            <div class="change-title">${escapeHtml(edit.filename || 'unknown')}</div>
            <div class="change-meta">${escapeHtml(edit.filepath || '')}<br>${Number(edit.bytes || 0)} bytes · ${formatLineDelta(edit)} · ${riskLabel(edit)} · <span class="state-chip ${escapeHtml(edit.status || 'proposed')}">${escapeHtml(edit.status || 'proposed')}</span><br>${escapeHtml(edit.summary || 'Proposed Karl edit')}</div>
            <div class="change-actions">
                <button data-preview="${escapeHtml(edit.id)}">Preview</button>
                <button class="primary" data-apply="${escapeHtml(edit.id)}">Apply</button>
                <button class="danger" data-reject="${escapeHtml(edit.id)}">Reject</button>
                <button data-open="${escapeHtml(edit.id)}">Open</button>
                <button data-copy-path="${escapeHtml(edit.id)}">Copy Path</button>
                <button data-rollback="${escapeHtml(edit.id)}">Rollback</button>
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
    queue.querySelectorAll('[data-open]').forEach(btn => btn.addEventListener('click', () => {
        vscode.postMessage({ command: 'open_file', editId: btn.dataset.open });
    }));
    queue.querySelectorAll('[data-copy-path]').forEach(btn => btn.addEventListener('click', () => {
        vscode.postMessage({ command: 'copy_file_path', editId: btn.dataset.copyPath });
    }));
    queue.querySelectorAll('[data-rollback]').forEach(btn => btn.addEventListener('click', () => {
        vscode.postMessage({ command: 'rollback_applied_file', editId: btn.dataset.rollback });
    }));
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

function initializeAppearance() {
    $('themeSelect').innerHTML = window.KARL_THEMES.map(theme => {
        return `<option value="${escapeHtml(theme.id)}">${escapeHtml(theme.name)}</option>`;
    }).join('');
    $('layoutSelect').innerHTML = window.KARL_LAYOUTS.map(layout => {
        return `<option value="${escapeHtml(layout.id)}">${escapeHtml(layout.name)}</option>`;
    }).join('');
}

function themeById(id) {
    return window.KARL_THEMES.find(theme => theme.id === id) || window.KARL_THEMES[0];
}

function layoutById(id) {
    return window.KARL_LAYOUTS.find(layout => layout.id === id) || window.KARL_LAYOUTS[0];
}

function applyAppearance() {
    const theme = themeById($('themeSelect').value);
    const layout = layoutById($('layoutSelect').value);
    const customAccent = $('customAccent').value || theme.vars['--karl-accent'];
    Object.entries(theme.vars).forEach(([key, value]) => document.documentElement.style.setProperty(key, value));
    document.documentElement.style.setProperty('--karl-accent', customAccent);
    document.body.dataset.layout = layout.id;
    $('themeDescription').innerText = theme.description;
    $('layoutDescription').innerText = layout.description;
    $('themeSwatches').innerHTML = Object.entries(theme.vars).slice(0, 9).map(([name, value]) => {
        const color = name === '--karl-accent' ? customAccent : value;
        return `<div class="swatch"><span style="background:${escapeHtml(color)}"></span><small>${escapeHtml(name.replace('--karl-', ''))}</small></div>`;
    }).join('');
    persist();
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

function addKbQueuePath() {
    const ingestPath = $('kbPath').value.trim();
    if (!ingestPath) {
        vscode.postMessage({ command: 'show_error', text: 'Choose a file or folder before adding it to the queue.' });
        return;
    }
    kbQueue = [{ path: ingestPath, status: 'queued' }, ...kbQueue.filter(item => item.path !== ingestPath)].slice(0, 50);
    renderKbQueue();
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
    panel.querySelectorAll('[data-remove-kb]').forEach(btn => {
        btn.addEventListener('click', () => {
            kbQueue.splice(Number(btn.dataset.removeKb), 1);
            renderKbQueue();
        });
    });
}

function markCurrentKbQueueDone(status) {
    const running = kbQueue.find(item => item.status === 'running');
    if (running) {
        running.status = status;
        renderKbQueue();
    }
}

function ingestKbQueue() {
    if (!kbQueue.length) {
        addKbQueuePath();
    }
    if (!kbQueue.length || kbQueueRunning) return;
    ingestNextQueuedPath();
}

function ingestNextQueuedPath() {
    const next = kbQueue.find(item => item.status === 'queued');
    if (!next) {
        kbQueueRunning = false;
        renderKbQueue();
        loadKbSources();
        return;
    }
    kbQueueRunning = true;
    next.status = 'running';
    $('kbPath').value = next.path;
    renderKbQueue();
    ingestKbPath();
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
    rememberKbQuery(query);
    rpc(52, 'search_kb', {
        query,
        top_k: Number($('kbTopK').value) || 5,
        threshold: Number($('kbThreshold').value) || 0,
        source_filter: $('kbSourceFilter').value || null
    });
}

function requiresBridgeSupport(feature, method) {
    const text = `${feature} requires Karl bridge method "${method}". The VS Code workspace is ready, but this backend endpoint is not exposed by the current desktop bridge.`;
    vscode.postMessage({ command: 'show_error', text });
    if ($('trainingLog') && feature.toLowerCase().includes('training')) {
        $('trainingLog').innerText += `\n[Bridge Required] ${text}`;
    }
    if ($('evalLog') && feature.toLowerCase().includes('eval')) {
        $('evalLog').innerText = `[Bridge Required] ${text}`;
    }
    if ($('tokenPreview') && feature.toLowerCase().includes('tokenizer')) {
        $('tokenPreview').innerText = text;
    }
}

function validateTrainingForm() {
    const dataset = $('trainingDatasetPath').value.trim();
    const adapter = $('trainingAdapterName').value.trim();
    if (!dataset || !adapter) {
        vscode.postMessage({ command: 'show_error', text: 'Training validation needs a dataset path and adapter name.' });
        return;
    }
    $('trainingDatasetState').innerText = dataset;
    $('trainingAdapterPath').innerText = `data/adapters/${adapter}`;
    $('trainingStatus').innerText = 'local form valid';
    $('trainingLog').innerText = [
        'Local form validation passed.',
        `Dataset: ${dataset}`,
        `Adapter: data/adapters/${adapter}`,
        'Runtime validation still requires bridge support for dataset inspection and dependency checks.'
    ].join('\n');
}

function renderQuickActions() {
    const actions = [
        ['Refactor Selection', 'karl.fixSelection'],
        ['Explain Selection', 'karl.explainSelection'],
        ['Review File', 'karl.reviewActiveFile'],
        ['Review Staged Diff', 'karl.reviewStagedDiff'],
        ['Review Unstaged Diff', 'karl.reviewUnstagedDiff'],
        ['Generate Tests', 'karl.generateTests'],
        ['Explain Diagnostics', 'karl.explainDiagnostics'],
        ['Commit Message', 'karl.generateCommitMessage'],
        ['Search KB Selection', 'karl.searchKbSelection'],
        ['Ingest Active File', 'karl.ingestActiveFile'],
        ['Review Bay', 'karl.openReviewBay']
    ];
    $('quickActions').innerHTML = actions.map(([label, commandId]) => {
        return `<button class="quick-action" data-command="${escapeHtml(commandId)}">${escapeHtml(label)}</button>`;
    }).join('');
    $('quickActions').querySelectorAll('[data-command]').forEach(btn => {
        btn.addEventListener('click', () => vscode.postMessage({ command: 'run_command', commandId: btn.dataset.command }));
    });
}

function rememberObjective(objective, file, mode) {
    const text = String(objective || '').trim();
    if (!text) return;
    recentObjectives = [
        { objective: text, file: file || '', mode: mode || 'Task', at: new Date().toISOString() },
        ...recentObjectives.filter(item => item.objective !== text)
    ].slice(0, 12);
    renderRecentObjectives();
    persist();
}

function renderRecentObjectives() {
    const panel = $('recentObjectives');
    if (!recentObjectives.length) {
        panel.className = 'recent-list empty';
        panel.innerText = 'No recent objectives yet.';
        return;
    }
    panel.className = 'recent-list';
    panel.innerHTML = recentObjectives.map((item, index) => `
        <button class="recent-item" data-recent="${index}">
            <strong>${escapeHtml(item.mode)}</strong>
            <span>${escapeHtml(item.objective)}</span>
        </button>
    `).join('');
    panel.querySelectorAll('[data-recent]').forEach(btn => {
        btn.addEventListener('click', () => {
            const item = recentObjectives[Number(btn.dataset.recent)];
            $('taskMode').value = item.mode || 'Custom Task';
            $('objective').value = item.objective || '';
            if (item.file && item.file.startsWith('/')) $('workspace').value = item.file;
        });
    });
}

function rememberKbQuery(query) {
    recentKbQueries = [query, ...recentKbQueries.filter(item => item !== query)].slice(0, 12);
    renderRecentKbQueries();
    persist();
}

function renderRecentKbQueries() {
    const panel = $('recentKbQueries');
    if (!panel) return;
    if (!recentKbQueries.length) {
        panel.className = 'recent-list empty';
        panel.innerText = 'No recent KB searches yet.';
        return;
    }
    panel.className = 'recent-list';
    panel.innerHTML = recentKbQueries.slice(0, 6).map((query, index) => `
        <button class="recent-item" data-kb-query="${index}">
            <strong>KB Search</strong>
            <span>${escapeHtml(query)}</span>
        </button>
    `).join('');
    panel.querySelectorAll('[data-kb-query]').forEach(btn => {
        btn.addEventListener('click', () => {
            $('kbQuery').value = recentKbQueries[Number(btn.dataset.kbQuery)] || '';
            searchKb();
        });
    });
}

function addTask(mode, objective) {
    const id = `task-${Date.now()}`;
    taskQueue.unshift({ id, mode, objective, status: 'running', at: new Date().toISOString() });
    renderTaskQueue();
    return id;
}

function finishActiveTask(status) {
    if (!activeTaskId) return;
    taskQueue = taskQueue.map(task => task.id === activeTaskId ? { ...task, status } : task);
    activeTaskId = '';
    renderTaskQueue();
}

function renderTaskQueue() {
    const panel = $('taskQueue');
    if (!taskQueue.length) {
        panel.className = 'task-queue empty';
        panel.innerText = 'No Karl tasks queued.';
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

function updateBridgeMeta(status) {
    if (!$('bridgeMeta')) return;
    const heartbeat = lastHeartbeatAt ? `${Math.max(0, Math.round((Date.now() - lastHeartbeatAt.getTime()) / 1000))}s ago` : 'never';
    const connected = lastConnectedAt ? lastConnectedAt.toLocaleTimeString() : 'never';
    const version = (status && status.bridge && status.bridge.version) || $('bridgeMeta').dataset.version || 'unknown';
    const error = lastBridgeError ? ` · Last error: ${lastBridgeError}` : '';
    $('bridgeMeta').innerText = `Heartbeat: ${heartbeat} · Last connect: ${connected} · Version: ${version}${error}`;
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
        return `<div class="model-card">
            <div class="model-title">${escapeHtml(name)}</div>
            <div class="model-meta">${escapeHtml(description)}<br>Recommended RAM: ${escapeHtml(ram)} · ${isInstalled ? 'Installed candidate detected' : 'Download requires desktop bridge support'}</div>
            <button disabled>${isInstalled ? 'Available' : 'Bridge Download Required'}</button>
        </div>`;
    }).join('');
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
