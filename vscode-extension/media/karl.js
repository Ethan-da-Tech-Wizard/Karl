const vscode = acquireVsCodeApi();
const boot = window.KARL_BOOTSTRAP || {};

let socket = null;
let reconnectTimer = null;
let runtimeStatusTimer = null;
let bridgeMetaTimer = null;
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
let recentTasks = [];
let recentKbQueries = [];
let taskQueue = [];
let activeTaskId = '';
let activeWorkflowId = '';
let lastHeartbeatAt = null;
let lastConnectedAt = null;
let lastBridgeError = '';
let kbQueue = [];
let kbQueueRunning = false;
let conversationBranches = [];
let activeBranchId = '';
let currentConversationInput = '';
let responseThinkActive = false;
let currentResponseText = '';
let nextReconnectSec = 5;
let lastKbSnapshot = {};
let lastKbResults = [];

const $ = (id) => document.getElementById(id);

window.addEventListener('DOMContentLoaded', () => {
    initializeAppearance();
    hydrate();
    bindEvents();
    renderQuickActions();
    renderRecentTasks();
    renderRecentKbQueries();
    renderTaskQueue();
    renderKbQueue();
    renderBranches();
    renderDownloadRegistry([]);
    bridgeMetaTimer = setInterval(() => updateBridgeMeta(), 1000);
    appendMessageBubble('assistant', 'Karl command cockpit ready. Connect to the local backend to execute agentic workflows.');
    
    // Post ready handshake
    vscode.postMessage({ command: 'ready' });

    if (boot.autoConnect) connect();
});

window.addEventListener('unload', () => {
    if (bridgeMetaTimer) {
        clearInterval(bridgeMetaTimer);
        bridgeMetaTimer = null;
    }
    if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
    }
    if (runtimeStatusTimer) {
        clearInterval(runtimeStatusTimer);
        runtimeStatusTimer = null;
    }
    if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        try {
            socket.close();
        } catch {}
        socket = null;
    }
});

window.addEventListener('message', event => {
    const message = event.data || {};
    if (message.command === 'start_workflow') {
        startWorkflow(message.workflowId, message.data || {});
    } else if (message.command === 'set_kb_path') {
        $('kbPath').value = message.path || '';
        switchWorkspace('knowledge');
    } else if (message.command === 'search_kb_text') {
        $('kbQuery').value = message.query || '';
        switchWorkspace('knowledge');
        searchKb();
    } else if (message.command === 'open_review_bay') {
        switchWorkspace('changes');
    } else if (message.command === 'pending_file_edit') {
        addPendingEdit(message.edit);
    } else if (message.command === 'file_edit_previewed') {
        markPendingEdit(message.editId, 'previewed');
    } else if (message.command === 'file_edit_applied') {
        markPendingEdit(message.editId, 'applied');
    } else if (message.command === 'file_edit_rejected') {
        removePendingEdit(message.editId, 'Rejected');
    } else if (message.command === 'file_edit_rolled_back') {
        markPendingEdit(message.editId, 'rolled_back');
    } else if (message.command === 'cockpit_state_update') {
        updateCockpitState(message.state || {});
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
    
    // Aesthetic settings checkboxes
    $('syncVsCodeTheme').checked = persisted.syncVsCodeTheme !== false;
    $('highContrastMode').checked = !!persisted.highContrastMode;
    $('reducedMotion').checked = !!persisted.reducedMotion;
    $('animationIntensity').value = persisted.animationIntensity !== undefined ? persisted.animationIntensity : 100;

    const rawTasks = Array.isArray(persisted.recentTasks) ? persisted.recentTasks : [];
    recentTasks = rawTasks.filter(t => t && typeof t.workflowId === 'string' && typeof t.title === 'string' && typeof t.objective === 'string').slice(0, 15);

    const rawQueries = Array.isArray(persisted.recentKbQueries) ? persisted.recentKbQueries : [];
    recentKbQueries = rawQueries.filter(q => typeof q === 'string').slice(0, 12);

    const rawBranches = Array.isArray(persisted.conversationBranches) ? persisted.conversationBranches : [];
    conversationBranches = rawBranches.filter(b => b && typeof b.id === 'string' && typeof b.title === 'string' && Array.isArray(b.turns)).slice(0, 20);
    
    activeBranchId = persisted.activeBranchId || (conversationBranches[0] && conversationBranches[0].id) || '';
    
    applyAppearance();
    if (persisted.workspaceTab) {
        switchWorkspace(persisted.workspaceTab);
    } else {
        switchWorkspace('cockpit');
    }
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
                workspaceTab: document.querySelector('.tab.active')?.dataset.workspace || 'cockpit',
                theme: $('themeSelect').value,
                customAccent: $('customAccent').value,
                layout: $('layoutSelect').value,
                syncVsCodeTheme: $('syncVsCodeTheme').checked,
                highContrastMode: $('highContrastMode').checked,
                reducedMotion: $('reducedMotion').checked,
                animationIntensity: Number($('animationIntensity').value),
                recentTasks: recentTasks.slice(0, 15),
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

    document.querySelectorAll('.subtab').forEach(btn => {
        btn.addEventListener('click', () => {
            const container = btn.closest('.workspace');
            container.querySelectorAll('.subtab').forEach(sb => sb.classList.remove('active'));
            btn.classList.add('active');
            container.querySelectorAll('.subworkspace').forEach(sw => {
                const matches = sw.id === `subworkspace-${btn.dataset.subworkspace}`;
                sw.style.display = matches ? 'block' : 'none';
                sw.classList.toggle('active', matches);
            });
        });
    });

    // Cockpit buttons
    $('cockpitConnectBtn').addEventListener('click', connect);
    $('cockpitDisconnectBtn').addEventListener('click', disconnect);
    $('clearRecentTasksBtn').addEventListener('click', () => {
        recentTasks = [];
        renderRecentTasks();
        persist();
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
    
    // Git Tab Actions
    $('gitReviewStagedBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'reviewStagedDiff' }));
    $('gitReviewUnstagedBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'reviewUnstagedDiff' }));
    $('gitReviewCombinedBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'reviewCombinedDiff' }));
    $('gitCommitMsgBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'generateCommitMessage' }));
    $('gitCopyCommitBtn').addEventListener('click', async () => {
        const text = $('gitCommitText').innerText;
        if (text && text !== 'Generating commit message...') {
            await navigator.clipboard.writeText(text);
            vscode.postMessage({ command: 'show_message', text: 'Commit message copied to clipboard.' });
        }
    });

    // Diagnostics Tab Actions
    $('diagExplainFileBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'explainCurrentFileDiagnostics' }));
    $('diagExplainWorkspaceBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'explainDiagnostics' }));

    // Vision Tab Actions
    $('visionSelectBtn').addEventListener('click', () => vscode.postMessage({ command: 'choose_kb_file' }));
    $('visionActiveBtn').addEventListener('click', () => vscode.postMessage({ command: 'runWorkflow', workflowId: 'analyzeImage' }));
    $('visionAskBtn').addEventListener('click', () => {
        const path = $('visionImagePath').value.trim();
        if (!path) {
            vscode.postMessage({ command: 'show_error', text: 'Please select an image file first.' });
            return;
        }
        vscode.postMessage({ command: 'runWorkflow', workflowId: 'analyzeImage', payload: { filepath: path } });
    });
    $('visionErrBtn').addEventListener('click', () => {
        const path = $('visionImagePath').value.trim();
        if (!path) {
            vscode.postMessage({ command: 'show_error', text: 'Please select an image file first.' });
            return;
        }
        vscode.postMessage({ command: 'runWorkflow', workflowId: 'reviewScreenshotError', payload: { filepath: path } });
    });

    // Logs Actions
    $('clearLogsBtn').addEventListener('click', () => {
        $('terminal').innerText = '--- Swarm Logs ---';
        $('trainingLog').innerText = 'No training logs recorded.';
        $('evalLog').innerText = 'No eval execution logs.';
    });
    $('copyLogsBtn').addEventListener('click', async () => {
        const logs = `--- SWARM LOGS ---\n${$('terminal').innerText}\n\n--- TRAINING LOGS ---\n${$('trainingLog').innerText}\n\n--- EVAL LOGS ---\n${$('evalLog').innerText}`;
        await navigator.clipboard.writeText(logs);
        vscode.postMessage({ command: 'show_message', text: 'All logs copied to clipboard.' });
    });

    $('codexSearch').addEventListener('input', filterCodex);
    $('workspace').addEventListener('change', persist);
    $('bridgePort').addEventListener('change', () => {
        $('cockpitPort').innerText = $('bridgePort').value;
        persist();
    });
    $('taskMode').addEventListener('change', persist);
    
    // Look workspace styling hooks
    $('themeSelect').addEventListener('change', applyAppearance);
    $('customAccent').addEventListener('input', applyAppearance);
    $('layoutSelect').addEventListener('change', applyAppearance);
    $('syncVsCodeTheme').addEventListener('change', applyAppearance);
    $('highContrastMode').addEventListener('change', applyAppearance);
    $('reducedMotion').addEventListener('change', applyAppearance);
    $('animationIntensity').addEventListener('input', applyAppearance);
    
    $('previewAllBtn').addEventListener('click', () => vscode.postMessage({ command: 'preview_all_files' }));
    $('rejectAllBtn').addEventListener('click', () => vscode.postMessage({ command: 'reject_all_files' }));
    $('copySummaryBtn').addEventListener('click', () => vscode.postMessage({ command: 'copy_patch_summary' }));
    $('changeFilter').addEventListener('change', renderPendingEdits);
    $('clearTasksBtn').addEventListener('click', () => {
        taskQueue = taskQueue.filter(task => task.status === 'running');
        renderTaskQueue();
    });
    
    $('resetAppearanceBtn').addEventListener('click', () => {
        $('themeSelect').value = 'obsidian-core';
        $('customAccent').value = '#00c2ff';
        $('layoutSelect').value = 'cockpit';
        $('syncVsCodeTheme').checked = true;
        $('highContrastMode').checked = false;
        $('reducedMotion').checked = false;
        $('animationIntensity').value = 100;
        applyAppearance();
    });

    // Delegated Event Listeners to prevent memory/event-listener leaks
    $('changeQueue').addEventListener('click', event => {
        const btn = event.target.closest('button');
        if (!btn) return;
        if (btn.dataset.preview) {
            vscode.postMessage({ command: 'preview_file', editId: btn.dataset.preview });
        } else if (btn.dataset.apply) {
            vscode.postMessage({ command: 'apply_file', editId: btn.dataset.apply });
        } else if (btn.dataset.reject) {
            vscode.postMessage({ command: 'reject_file', editId: btn.dataset.reject });
        } else if (btn.dataset.open) {
            vscode.postMessage({ command: 'open_file', editId: btn.dataset.open });
        } else if (btn.dataset.copyPath) {
            vscode.postMessage({ command: 'copy_file_path', editId: btn.dataset.copyPath });
        } else if (btn.dataset.rollback) {
            vscode.postMessage({ command: 'rollback_applied_file', editId: btn.dataset.rollback });
        }
    });

    $('diagnosticsList').addEventListener('click', event => {
        const el = event.target.closest('[data-diag-file]');
        if (!el) return;
        vscode.postMessage({
            command: 'open_diagnostic_line',
            filepath: el.dataset.diagFile,
            line: Number(el.dataset.diagLine),
            character: Number(el.dataset.diagChar)
        });
    });

    $('themeGrid').addEventListener('click', event => {
        const card = event.target.closest('[data-theme-id]');
        if (!card) return;
        $('themeSelect').value = card.dataset.themeId;
        applyAppearance();
    });

    $('kbSourceList').addEventListener('click', event => {
        const row = event.target.closest('[data-source]');
        if (!row) return;
        kbSelectedSource = row.dataset.source || '';
        $('kbSourceFilter').value = kbSelectedSource;
        renderKbSnapshot(lastKbSnapshot);
    });

    $('kbQueue').addEventListener('click', event => {
        const btn = event.target.closest('[data-remove-kb]');
        if (!btn) return;
        kbQueue.splice(Number(btn.dataset.removeKb), 1);
        renderKbQueue();
    });

    $('quickActions').addEventListener('click', event => {
        const btn = event.target.closest('[data-workflow]');
        if (!btn) return;
        vscode.postMessage({
            command: 'runWorkflow',
            workflowId: btn.dataset.workflow,
            payload: {}
        });
    });

    $('recentTasksHistory').addEventListener('click', event => {
        const btn = event.target.closest('[data-task-idx]');
        if (!btn) return;
        const task = recentTasks[Number(btn.dataset.taskIdx)];
        if (task) {
            vscode.postMessage({
                command: 'runWorkflow',
                workflowId: task.workflowId,
                payload: {
                    objective: task.objective,
                    filepath: task.filepath
                }
            });
        }
    });

    $('recentKbQueries').addEventListener('click', event => {
        const btn = event.target.closest('[data-kb-query]');
        if (!btn) return;
        $('kbQuery').value = recentKbQueries[Number(btn.dataset.kbQuery)] || '';
        searchKb();
    });

    $('kbResults').addEventListener('click', event => {
        const btn = event.target.closest('button');
        if (!btn) return;
        if (btn.dataset.sendChat !== undefined) {
            const res = lastKbResults[Number(btn.dataset.sendChat)];
            if (res) {
                $('chatInput').value = `Reference: ${res.source_file} (Chunk ${res.chunk_id})\n\n${res.text}\n\n`;
                switchWorkspace('chat');
            }
        } else if (btn.dataset.sendSwarm !== undefined) {
            const res = lastKbResults[Number(btn.dataset.sendSwarm)];
            if (res) {
                $('objective').value = `Reference: ${res.source_file} (Chunk ${res.chunk_id})\n\n${res.text}\n\n${$('objective').value}`;
                switchWorkspace('swarm');
            }
        }
    });

    $('modelList').addEventListener('click', event => {
        const btn = event.target.closest('[data-model]');
        if (!btn) return;
        rpc(32, 'set_active_model', { filename: btn.dataset.model });
    });

    $('codexList').addEventListener('click', event => {
        const row = event.target.closest('[data-topic]');
        if (!row) return;
        $('codexViewer').innerHTML = 'Loading reference...';
        rpc(21, 'get_codex_content', { topic: row.dataset.topic });
    });

    $('branchTree').addEventListener('click', event => {
        const btn = event.target.closest('[data-branch]');
        if (!btn) return;
        activeBranchId = btn.dataset.branch;
        renderBranches();
        persist();
    });

    $('codexViewer').addEventListener('click', event => {
        const btn = event.target.closest('button');
        if (!btn) return;
        if (btn.id === 'codexSendChatBtn') {
            const txt = $('codexViewer').querySelector('.codex-content').innerText;
            $('chatInput').value = `Codex Reference:\n\n${txt}\n\n`;
            switchWorkspace('chat');
        } else if (btn.id === 'codexSendSwarmBtn') {
            const txt = $('codexViewer').querySelector('.codex-content').innerText;
            $('objective').value = `Codex Reference:\n\n${txt}\n\n${$('objective').value}`;
            switchWorkspace('swarm');
        }
    });
}

function switchWorkspace(wsId) {
    document.querySelectorAll('.workspace').forEach(section => section.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.dataset.workspace === wsId));
    const section = $(`workspace-${wsId}`);
    if (section) {
        section.classList.add('active');
    }

    if (wsId === 'settings') {
        loadModels();
    }
    if (wsId === 'knowledge') {
        loadKbSources();
        loadCodexTopics();
    }
    if (wsId === 'lab') loadPromptPairs();
    
    // Request an update to sync cockpit variables
    vscode.postMessage({ command: 'get_cockpit_state' });
    persist();
}

function setConnectionState(state, label) {
    connectionState = state;
    $('statusDot').className = `status-dot ${state}`;
    $('statusText').innerText = label;
    $('cockpitConnection').innerText = label.toLowerCase();
    $('cockpitConnection').className = `state-chip ${state}`;
    $('offlinePanel').classList.toggle('active', state !== 'connected' && state !== 'running');
    updateBridgeMeta();
}

function teardownSocket(isError = false) {
    if (runtimeStatusTimer) {
        clearInterval(runtimeStatusTimer);
        runtimeStatusTimer = null;
    }
    if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        try {
            if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
                socket.close();
            }
        } catch {}
        socket = null;
    }
    setConnectionState('offline', isError ? 'Error' : 'Offline');
    renderRuntimeOffline();
}

function handleDisconnect(isError = false) {
    teardownSocket(isError);

    if (boot.autoConnect && !manualDisconnect && !reconnectTimer) {
        nextReconnectSec = 5;
        log(`[Bridge] Connection lost. Retrying in ${nextReconnectSec}s.`);
        updateBridgeMeta();
        reconnectTimer = setInterval(() => {
            nextReconnectSec--;
            updateBridgeMeta();
            if (nextReconnectSec <= 0) {
                clearInterval(reconnectTimer);
                reconnectTimer = null;
                connect();
            }
        }, 1000);
    }
}

function connect() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        teardownSocket(false);
    }
    manualDisconnect = false;
    const port = Number($('bridgePort').value) || boot.port || 8080;
    $('cockpitPort').innerText = port;
    setConnectionState('connecting', 'Connecting');
    log(`[Bridge] Connecting to ws://localhost:${port}`);
    try {
        socket = new WebSocket(`ws://localhost:${port}`);
    } catch (err) {
        lastBridgeError = err.message;
        handleDisconnect(true);
        return;
    }

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

    socket.onmessage = event => {
        try {
            const data = JSON.parse(event.data);
            handleSocketMessage(data);
        } catch (err) {
            lastBridgeError = 'Malformed frame: ' + err.message;
            log(`[Bridge Error] Malformed JSON: ${err.message}`);
            updateBridgeMeta();
        }
    };
    socket.onerror = () => {
        lastBridgeError = 'Connection failed';
        vscode.postMessage({ command: 'show_error', text: 'Karl bridge connection failed. Start Karl and verify the WebSocket port.' });
    };
    socket.onclose = () => {
        handleDisconnect(false);
    };
}

function disconnect() {
    manualDisconnect = true;
    if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
    }
    teardownSocket(false);
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
    } else if (method === 'vision_result') {
        $('visionResult').style.display = 'block';
        $('visionResultText').innerText = `Caption: ${params.caption || 'No caption'}\n\nOCR Text:\n${params.ocr || 'No OCR text detected.'}`;
    }
}

function handleRpcResult(id, result) {
    if (!result || typeof result !== 'object') result = {};
    if (id === 12) {
        renderLabDiff(labOutputA, labOutputB);
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
        log(`[KB] Ingestion started for ${result.file_count || 0} file(s).`);
    } else if (id === 52) {
        renderKbSearch(result);
    } else if (id === 20) {
        renderCodexTopics(result.topics || []);
    } else if (id === 21) {
        const cleanText = result.content || '';
        $('codexViewer').innerHTML = `
            <div class="action-row compact-actions" style="margin-bottom:8px;">
                <button id="codexSendChatBtn">Send to Chat</button>
                <button id="codexSendSwarmBtn">Send to Swarm</button>
            </div>
            <div class="codex-content">${escapeHtml(cleanText)}</div>
        `;
        
        $('codexSendChatBtn').addEventListener('click', () => {
            const txt = $('codexViewer').querySelector('.codex-content').innerText;
            $('chatInput').value = `Codex Reference:\n\n${txt}\n\n`;
            switchWorkspace('chat');
        });
        
        $('codexSendSwarmBtn').addEventListener('click', () => {
            const txt = $('codexViewer').querySelector('.codex-content').innerText;
            $('objective').value = `Codex Reference:\n\n${txt}\n\n${$('objective').value}`;
            switchWorkspace('swarm');
        });
    }
}

function requestRuntimeStatus() {
    rpc(30, 'get_runtime_status');
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

function renderRuntimeOffline() {
    $('runtimeModel').innerText = 'unknown';
    $('runtimeState').innerText = 'offline';
    $('runtimeAdapter').innerText = 'none';
    $('runtimeSystem').innerText = '--';
    
    $('cockpitModel').innerText = 'unknown';
    $('cockpitSystem').innerText = '--';
}

function startWorkflow(workflowId, data) {
    activeWorkflowId = workflowId;
    $('taskMode').value = workflowId;
    $('workspace').value = data.workspace_path || '';
    $('objective').value = data.objective || '';
    
    renderContextMeta(data.context_meta);
    rememberTask(workflowId, data.mode || 'Task', data.objective || '', data.filepath || '');
    
    const tab = data.targetTab || 'swarm';
    switchWorkspace(tab);

    if (tab === 'git') {
        $('gitDiffContainer').style.display = 'block';
        $('gitDiffText').innerText = data.code || 'No changes or diff found.';
        if (workflowId === 'generateCommitMessage') {
            $('gitCommitOutput').style.display = 'block';
            $('gitCommitText').innerText = 'Generating commit message...';
        }
    }

    if (tab === 'diagnostics') {
        $('diagExplanation').style.display = 'block';
        $('diagExplanationText').innerText = 'Karl is reviewing problem diagnostics...';
    }

    if (tab === 'vision') {
        $('visionImagePath').value = data.filepath || '';
        $('visionPreviewCard').style.display = 'block';
        $('visionImagePreview').innerHTML = `<span style="color:var(--karl-accent-2); font-weight:700;">Image: ${escapeHtml(data.filepath.split('/').pop())}</span>`;
        $('visionResult').style.display = 'block';
        $('visionResultText').innerText = 'Karl is inspecting image file...';
    }

    if (tab === 'swarm') {
        connectAndRun();
    }
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
    rememberTask($('taskMode').value, $('taskMode').selectedOptions?.[0]?.text || 'Task', objective, workspace);
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
    currentResponseText = '';
    rpc(3, 'submit_chat', {
        message: text,
        workspace_path: $('workspace').value.trim(),
        hyperparams: hyperparams()
    });
}

function handleResponseToken(token) {
    currentResponseText += token;
    
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

    if (activeWorkflowId === 'generateCommitMessage') {
        $('gitCommitText').innerText = currentResponseText;
    } else if (activeWorkflowId === 'explainDiagnostics' || activeWorkflowId === 'explainCurrentFileDiagnostics') {
        $('diagExplanationText').innerText = currentResponseText;
    } else if (activeWorkflowId === 'analyzeImage' || activeWorkflowId === 'reviewScreenshotError') {
        $('visionResultText').innerText = currentResponseText;
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
    activeWorkflowId = '';
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
    vscode.postMessage({ command: 'show_message', text: 'Karl conversation branch created in the Chat panel.' });
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
    renderLabDiff(labOutputA, labOutputB);
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
    if (!pair || typeof pair !== 'object') pair = {};
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
    renderThemeCatalog();
}

function themeById(id) {
    const themes = Array.isArray(window.KARL_THEMES) ? window.KARL_THEMES : [];
    return themes.find(theme => theme && theme.id === id) || themes[0] || { id: 'obsidian-core', vars: { '--karl-accent': '#00c2ff' }, name: 'Obsidian Core', description: '' };
}

function layoutById(id) {
    const layouts = Array.isArray(window.KARL_LAYOUTS) ? window.KARL_LAYOUTS : [];
    return layouts.find(layout => layout && layout.id === id) || layouts[0] || { id: 'cockpit', name: 'Cockpit', description: '' };
}

function applyAppearance() {
    const theme = themeById($('themeSelect').value);
    const layout = layoutById($('layoutSelect').value);
    const vars = theme.vars || {};
    const customAccent = $('customAccent').value || vars['--karl-accent'] || '#00c2ff';
    
    Object.entries(vars).forEach(([key, value]) => {
        document.documentElement.style.setProperty(key, value);
    });
    
    document.documentElement.style.setProperty('--karl-accent', customAccent);
    document.body.dataset.layout = layout.id;
    $('themeDescription').innerText = theme.description || '';
    $('layoutDescription').innerText = layout.description || '';

    // Presets variables modifications
    if ($('syncVsCodeTheme').checked) {
        document.documentElement.style.setProperty('--karl-bg', 'color-mix(in srgb, var(--vscode-sideBar-background) 82%, #020817)');
        document.documentElement.style.setProperty('--karl-panel', 'color-mix(in srgb, var(--vscode-editor-background) 88%, #07162a)');
        document.documentElement.style.setProperty('--karl-border', 'color-mix(in srgb, var(--vscode-widget-border) 60%, #0ea5ff)');
        document.documentElement.style.setProperty('--karl-text', 'var(--vscode-foreground)');
    }

    if ($('highContrastMode').checked) {
        document.body.dataset.layoutContrast = 'high';
    } else {
        delete document.body.dataset.layoutContrast;
    }

    const intensity = Number($('animationIntensity').value);
    document.documentElement.style.setProperty('--animation-intensity', intensity / 100);

    if ($('reducedMotion').checked || intensity === 0) {
        document.body.dataset.motion = 'reduced';
    } else {
        delete document.body.dataset.motion;
    }

    renderThemeCatalog();
    persist();
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
    vscode.postMessage({ command: 'show_error', text: 'Training validation requires bridge support.' });
}

function renderQuickActions() {
    const actions = [
        ['Explain Selection', 'explainSelection'],
        ['Refactor Selection', 'fixSelection'],
        ['Review File', 'reviewActiveFile'],
        ['Generate Tests', 'generateTests'],
        ['Staged Diff Review', 'reviewStagedDiff'],
        ['Unstaged Diff Review', 'reviewUnstagedDiff'],
        ['Combined Diff Review', 'reviewCombinedDiff'],
        ['Commit Message', 'generateCommitMessage'],
        ['Git Branch Summary', 'branchSummary'],
        ['Explain Current Diagnostics', 'explainCurrentFileDiagnostics'],
        ['Explain Workspace Diagnostics', 'explainDiagnostics'],
        ['Ask Workspace', 'askWorkspace'],
        ['Search KB Selection', 'searchKbSelection'],
        ['Ingest Active File', 'ingestActiveFile'],
        ['Review Bay', 'openReviewBay'],
        ['Analyze Image (Vision)', 'analyzeImage'],
        ['Review Screenshot Error', 'reviewScreenshotError']
    ];
    $('quickActions').innerHTML = actions.map(([label, workflowId]) => {
        return `<button class="quick-action" data-workflow="${escapeHtml(workflowId)}">${escapeHtml(label)}</button>`;
    }).join('');
}

function rememberTask(workflowId, title, objective, filepath) {
    const text = String(objective || '').trim();
    if (!text) return;
    recentTasks = [
        { workflowId, title, objective: text, filepath: filepath || '', at: new Date().toISOString() },
        ...recentTasks.filter(item => item.objective !== text || item.workflowId !== workflowId)
    ].slice(0, 15);
    renderRecentTasks();
    persist();
}

function renderRecentTasks() {
    const panel = $('recentTasksHistory');
    if (!panel) return;
    if (!recentTasks.length) {
        panel.className = 'recent-list empty';
        panel.innerText = 'No tasks run recently.';
        return;
    }
    panel.className = 'recent-list';
    panel.innerHTML = recentTasks.map((task, index) => `
        <button class="recent-item" data-task-idx="${index}">
            <strong>${escapeHtml(task.title)}</strong>
            <span>${escapeHtml(task.objective)}</span>
            <small style="font-size: 8px; color: var(--karl-muted); display: block; margin-top: 2px;">Target: ${escapeHtml(task.filepath || 'unknown')}</small>
        </button>
    `).join('');
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

function updateBridgeMeta(status) {
    if (!$('bridgeMeta')) return;
    const heartbeat = lastHeartbeatAt ? `${Math.max(0, Math.round((Date.now() - lastHeartbeatAt.getTime()) / 1000))}s ago` : 'never';
    const connected = lastConnectedAt ? lastConnectedAt.toLocaleTimeString() : 'never';
    const version = (status && status.bridge && status.bridge.version) || $('bridgeMeta').dataset.version || 'unknown';
    
    let reconnectStr = '';
    if (reconnectTimer && nextReconnectSec > 0) {
        reconnectStr = ` · Retrying in ${nextReconnectSec}s`;
        const label = `Reconnecting in ${nextReconnectSec}s`;
        $('statusText').innerText = label;
        $('cockpitConnection').innerText = label.toLowerCase();
    } else if (connectionState === 'offline' || connectionState === 'error') {
        const label = 'Karl app not running';
        $('statusText').innerText = label;
        $('cockpitConnection').innerText = label.toLowerCase();
    }
    const error = lastBridgeError ? ` · Last error: ${lastBridgeError}` : '';
    $('bridgeMeta').innerText = `Heartbeat: ${heartbeat} · Last connect: ${connected} · Version: ${version}${reconnectStr}${error}`;
    $('cockpitHeartbeat').innerText = heartbeat;
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

function loadModels() {
    if (!isConnected()) {
        $('modelList').innerHTML = '<div class="model-card"><div class="model-meta">Karl bridge is offline.</div></div>';
        return;
    }
    rpc(31, 'list_models');
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
        return `<div class="model-card">
            <div class="model-title">${escapeHtml(model.name || model.filename || 'Unknown model')}</div>
            <div class="model-meta">${escapeHtml(model.filename || '')}<br>${model.n_ctx || '--'} ctx · ${model.min_ram_gb || '--'} GB RAM · ${model.active ? 'Active' : model.installed ? 'Installed' : 'Missing'}</div>
            ${action}
        </div>`;
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
    if (!Array.isArray(topics)) topics = [];
    $('codexList').innerHTML = topics.length ? topics.map(topic => {
        return `<div class="source-item" data-topic="${escapeHtml(topic)}"><span>${escapeHtml(topic)}</span></div>`;
    }).join('') : '<div class="source-item">No chapters loaded.</div>';
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
