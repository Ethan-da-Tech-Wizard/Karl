window.addEventListener('DOMContentLoaded', () => {
    initializeAppearance();
    hydrate();
    _initThoughtsPanel();
    _initChatInnerTabs();
    _initLogsSubtabs();
    _initWsStateObserver();
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

    vscode.postMessage({ command: 'ready' });

    if (boot.autoConnect) connect();
});

window.addEventListener('unload', () => {
    if (bridgeMetaTimer) { clearInterval(bridgeMetaTimer); bridgeMetaTimer = null; }
    if (reconnectTimer)  { clearInterval(reconnectTimer);  reconnectTimer = null; }
    // runtimeStatusTimer and socket are cleaned up by teardownSocket/disconnect
    if (window.KARL_USE_HOST_RELAY) {
        vscode.postMessage({ command: 'bridge_disconnect' });
    } else {
        teardownSocket(false);
    }
});

window.addEventListener('message', event => {
    const message = event.data || {};

    if (message.command === 'inject_chat') {
        const text = message.text || '';
        $('chatInput').value = text;
        switchWorkspace('chat');
        if (message.autoSend && text.trim()) {
            sendChatMessage();
        }
        return;
    }

    if (message.command === 'inject_swarm') {
        const objective = message.objective || '';
        if ($('objective')) $('objective').value = objective;
        switchWorkspace('swarm');
        return;
    }

    // ── Host-relay bridge events ──────────────────────────────────────────────
    // When KARL_USE_HOST_RELAY is active the extension host owns the WebSocket
    // and forwards frames/lifecycle events here via postMessage.
    if (message.command === 'bridge_message') {
        try {
            const data = typeof message.data === 'string'
                ? JSON.parse(message.data)
                : message.data;
            handleSocketMessage(data);
        } catch (err) {
            log(`[Relay] Malformed bridge frame: ${err.message}`);
        }
        return;
    }
    if (message.command === 'bridge_status') {
        const state = message.state || 'offline';
        if (state === 'connected') {
            lastConnectedAt = new Date();
            setConnectionState('connected', 'Connected');
            if (reconnectTimer) { clearInterval(reconnectTimer); reconnectTimer = null; }
            requestRuntimeStatus();
            runtimeStatusTimer = runtimeStatusTimer || setInterval(requestRuntimeStatus, 4000);
            persist();
        } else if (state === 'error') {
            lastBridgeError = message.message || 'Host relay error';
            handleDisconnect(true);
        } else {
            handleDisconnect(false);
        }
        return;
    }

    // ── Webview ↔ host commands ───────────────────────────────────────────────
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

// ── thoughts panel initialisation ─────────────────────────────────────────────
// Transforms the static HTML inside #introspectionBox into a collapsible
// reasoning panel matching Karl's Obsidian aesthetic. Called once on load.
function _initThoughtsPanel() {
    const box = $('introspectionBox');
    const thoughts = $('introspectionThoughts');
    if (!box || !thoughts) return;

    // Replace the static .eyebrow div with a full interactive header
    const oldEyebrow = box.querySelector('.eyebrow');
    const header = document.createElement('div');
    header.id = 'thoughtsHeader';
    header.className = 'thoughts-header';
    header.innerHTML = `
        <span class="thoughts-toggle" id="thoughtsToggle">▼</span>
        <span class="eyebrow" style="margin:0">Reasoning</span>
        <span id="thoughtsTokenCount" class="thoughts-token-count">0 tokens</span>
        <span id="thoughtsPulseDot" class="thoughts-pulse-dot"></span>
    `;
    if (oldEyebrow) {
        box.replaceChild(header, oldEyebrow);
    } else {
        box.insertBefore(header, thoughts);
    }

    // Mark the <pre> so CSS targets it as the scrollable body
    thoughts.classList.add('thoughts-body');

    // Wire the collapse/expand toggle
    let _collapsed = false;
    header.addEventListener('click', () => {
        _collapsed = !_collapsed;
        if (_collapsed) {
            thoughts.style.maxHeight = '0';
            thoughts.style.paddingTop = '0';
            thoughts.style.paddingBottom = '0';
        } else {
            thoughts.style.maxHeight = '';
            thoughts.style.paddingTop = '';
            thoughts.style.paddingBottom = '';
        }
        $('thoughtsToggle').textContent = _collapsed ? '▶' : '▼';
        header.classList.toggle('thoughts-header--collapsed', _collapsed);
    });
}

let _lastAssistantContent = '';

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
    _lastAssistantContent = '';
    $('chatInput').dataset.lastSent = $('chatInput').value;
    input.value = '';
    chatFinished = false;
    document.body.dataset.wsState = 'generating';
    $('chatSendBtn').disabled = true;
    // Reset the reasoning panel for this new generation
    resetThoughtsPanel();
    currentResponseText = '';
    rpc(3, 'submit_chat', {
        message: text,
        workspace_path: $('workspace').value.trim(),
        hyperparams: hyperparams()
    });
}

function handleResponseToken(token) {
    _lastAssistantContent += token;
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
    // Remove streaming cursor and stop the pulse dot before recording the turn
    removeStreamingCursor();
    finalizeThoughts();
    chatFinished = true;
    $('chatSendBtn').disabled = false;
    // Restore ws-state indicator (use statusDot class as source of truth)
    const _dot = $('statusDot');
    if (_dot) {
        const _st = [..._dot.classList].find(c => c !== 'status-dot') || 'connected';
        document.body.dataset.wsState = _st;
    }
    const lastAssistant = $('chatMessages').querySelector('.message.assistant:last-child .message-content');
    recordConversationTurn(currentConversationInput, lastAssistant ? lastAssistant.innerText : '');
    currentConversationInput = '';
    activeWorkflowId = '';

    // Check if this was a refactor request — extract code block and notify host
    const lastInput = $('chatInput').dataset.lastSent || '';
    if (lastInput.startsWith('Refactor the following')) {
        const fullResponse = _lastAssistantContent || '';
        const codeMatch = fullResponse.match(/```[\w]*\n([\s\S]*?)```/);
        if (codeMatch) {
            vscode.postMessage({ command: 'refactor_result', code: codeMatch[1] });
        }
    }
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

function loadSelectedPromptPair() {
    const name = $('promptPairSelect').value || $('promptPairName').value.trim();
    if (name) rpc(41, 'get_prompt_pair', { name });
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

function applyPromptPair(result) {
    if (!result || typeof result !== 'object') return;
    if (result.name) $('promptPairName').value = result.name;
    if (result.system_a !== undefined) $('labSysA').value = result.system_a;
    if (result.user_a  !== undefined) $('labUser').value  = result.user_a;
    if (result.system_b !== undefined) $('labSysB').value = result.system_b;
    if (result.rag_a   !== undefined) $('karlRag').checked  = !!result.rag_a;
    if (result.loop_a  !== undefined) $('karlLoop').checked = !!result.loop_a;
    labOutputA = result.output_a_raw || '';
    labOutputB = result.output_b_raw || '';
    if (labOutputA || labOutputB) {
        $('labOutputA').innerText = result.output_a_display || labOutputA;
        $('labOutputB').innerText = result.output_b_display || labOutputB;
        renderLabDiff(labOutputA, labOutputB);
    }
    log(`[Prompt Lab] Loaded pair: ${result.name || '(unnamed)'}`);
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

function markCurrentKbQueueDone(status) {
    const running = kbQueue.find(item => item.status === 'running');
    if (running) {
        running.status = status;
        renderKbQueue();
    }
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

function rememberKbQuery(query) {
    recentKbQueries = [query, ...recentKbQueries.filter(item => item !== query)].slice(0, 12);
    renderRecentKbQueries();
    persist();
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

// ── WS-state MutationObserver ─────────────────────────────────────────────────
// Watches #statusDot className changes and mirrors the state to
// body.dataset.wsState so CSS can drive the chat-border animation.
function _initWsStateObserver() {
    const dot = $('statusDot');
    if (!dot) return;
    function _sync() {
        const state = [...dot.classList].find(c => c !== 'status-dot') || 'offline';
        if (document.body.dataset.wsState !== 'generating') {
            document.body.dataset.wsState = state;
        }
    }
    _sync();
    new MutationObserver(_sync).observe(dot, { attributes: true, attributeFilter: ['class'] });
}

// ── Chat workspace inner tabs ─────────────────────────────────────────────────
// Injects a 3-tab sub-layout (Chat / Reasoning / Swarm) inside #workspace-chat.
// Runs after _initThoughtsPanel() so #introspectionBox already has its header.
function _initChatInnerTabs() {
    const chatSection = $('workspace-chat');
    if (!chatSection || chatSection.dataset.innerTabsReady) return;
    chatSection.dataset.innerTabsReady = '1';

    const thoughtsBox  = $('introspectionBox');
    const chatMessages = $('chatMessages');
    const composer     = chatSection.querySelector('.composer');
    const sectionHead  = chatSection.querySelector('.section-head');
    if (!thoughtsBox || !chatMessages || !composer) return;

    // ── Tab bar ────────────────────────────────────────────────────────────────
    const tabBar = document.createElement('div');
    tabBar.className = 'chat-inner-tabs';
    tabBar.innerHTML = `
        <button class="chat-inner-tab active" data-inner-tab="chatPanel">Chat</button>
        <button class="chat-inner-tab" data-inner-tab="reasoningPanel">Reasoning</button>
        <button class="chat-inner-tab" data-inner-tab="swarmPanel">Swarm</button>
        <button class="chat-toggle active" id="thoughtsVisToggle" title="Show / hide inline thought stream">◈ Thoughts</button>
    `;

    // ── Panel 1: chat messages + composer ─────────────────────────────────────
    const chatPanel = document.createElement('div');
    chatPanel.id = 'chatPanel';
    chatPanel.className = 'chat-tab-panel active';
    chatPanel.appendChild(thoughtsBox);
    chatPanel.appendChild(chatMessages);
    chatPanel.appendChild(composer);

    // ── Panel 2: full reasoning view ──────────────────────────────────────────
    const reasoningPanel = document.createElement('div');
    reasoningPanel.id = 'reasoningPanel';
    reasoningPanel.className = 'chat-tab-panel';
    reasoningPanel.innerHTML = `
        <div style="margin-bottom:8px;">
            <div class="eyebrow">Full Reasoning Stream</div>
            <div style="color:var(--karl-muted);font-size:10px;margin-top:3px;">Complete thought stream — updated live during generation</div>
        </div>
        <pre id="reasoningFullView" class="reasoning-full">No reasoning yet. Start a chat to see thoughts here.</pre>
    `;

    // ── Panel 3: swarm progress feed ──────────────────────────────────────────
    const swarmPanel = document.createElement('div');
    swarmPanel.id = 'swarmPanel';
    swarmPanel.className = 'chat-tab-panel';
    swarmPanel.innerHTML = `
        <div style="margin-bottom:8px;">
            <div class="eyebrow">Swarm Progress Feed</div>
            <div style="color:var(--karl-muted);font-size:10px;margin-top:3px;">Real-time agent execution timeline</div>
        </div>
        <div id="swarmFeed" class="swarm-feed">
            <div style="color:var(--karl-muted);padding:8px;font-size:11px;" data-swarm-empty>No swarm activity yet.</div>
        </div>
    `;

    // Insert all panels right after the section-head
    if (sectionHead) {
        sectionHead.after(tabBar, chatPanel, reasoningPanel, swarmPanel);
    } else {
        chatSection.prepend(swarmPanel, reasoningPanel, chatPanel, tabBar);
    }

    // ── Tab switching ──────────────────────────────────────────────────────────
    tabBar.querySelectorAll('.chat-inner-tab').forEach(btn => {
        btn.addEventListener('click', () => _switchChatInnerTab(btn.dataset.innerTab));
    });

    // ── Thoughts inline visibility toggle ─────────────────────────────────────
    const toggleBtn = $('thoughtsVisToggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const hidden = thoughtsBox.style.display === 'none';
            thoughtsBox.style.display = hidden ? '' : 'none';
            toggleBtn.classList.toggle('active', hidden);
        });
    }
}

function _switchChatInnerTab(panelId) {
    const panels = ['chatPanel', 'reasoningPanel', 'swarmPanel'];
    panels.forEach(id => {
        const el = $(id);
        if (el) el.classList.toggle('active', el.id === panelId);
    });
    const chatSection = $('workspace-chat');
    if (chatSection) {
        chatSection.querySelectorAll('.chat-inner-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.innerTab === panelId);
        });
    }
}

// ── Logs workspace subtabs ────────────────────────────────────────────────────
// Adds three subtabs (Swarm / Training / Eval) inside #workspace-logs,
// wrapping the existing #terminal, #trainingLog, #evalLog into panels.
function _initLogsSubtabs() {
    const logsSection = $('workspace-logs');
    if (!logsSection || logsSection.dataset.logsSubtabsReady) return;
    logsSection.dataset.logsSubtabsReady = '1';

    const terminal    = $('terminal');
    const trainingLog = $('trainingLog');
    const evalLog     = $('evalLog');
    const actionRow   = logsSection.querySelector('.action-row');
    const sectionHead = logsSection.querySelector('.section-head');
    if (!terminal || !trainingLog || !evalLog) return;

    // Remove orphaned eyebrow labels that belonged to trainingLog / evalLog
    logsSection.querySelectorAll(':scope > .eyebrow').forEach(el => el.remove());

    // ── Subtab bar ────────────────────────────────────────────────────────────
    const subtabBar = document.createElement('div');
    subtabBar.className = 'log-subtabs';
    subtabBar.innerHTML = `
        <button class="log-subtab active" data-log-panel="swarmLogPanel">Swarm</button>
        <button class="log-subtab"        data-log-panel="trainingLogPanel">Training</button>
        <button class="log-subtab"        data-log-panel="evalLogPanel">Eval</button>
    `;

    // ── Panels ────────────────────────────────────────────────────────────────
    const swarmLogPanel = document.createElement('div');
    swarmLogPanel.id = 'swarmLogPanel';
    swarmLogPanel.className = 'log-panel active';
    swarmLogPanel.appendChild(terminal);

    const trainingLogPanel = document.createElement('div');
    trainingLogPanel.id = 'trainingLogPanel';
    trainingLogPanel.className = 'log-panel';
    trainingLogPanel.appendChild(trainingLog);

    const evalLogPanel = document.createElement('div');
    evalLogPanel.id = 'evalLogPanel';
    evalLogPanel.className = 'log-panel';
    evalLogPanel.appendChild(evalLog);

    // Insert after action-row (or section-head as fallback)
    const insertRef = actionRow || sectionHead;
    if (insertRef) {
        insertRef.after(subtabBar, swarmLogPanel, trainingLogPanel, evalLogPanel);
    }

    // ── Tab switching ─────────────────────────────────────────────────────────
    subtabBar.querySelectorAll('.log-subtab').forEach(btn => {
        btn.addEventListener('click', () => {
            subtabBar.querySelectorAll('.log-subtab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            ['swarmLogPanel', 'trainingLogPanel', 'evalLogPanel'].forEach(id => {
                const el = $(id);
                if (el) el.classList.toggle('active', el.id === btn.dataset.logPanel);
            });
        });
    });
}

// ── Educational Sandbox Workspace ─────────────────────────────────────────────
let miniGptSimTimer = null;
let currentMiniStep = 0;

function fitTfidfVectorizer(documents) {
    const stopWords = new Set(["the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "of", "in", "on", "at", "for", "with", "by", "about", "as"]);
    
    function tokenize(text) {
        return text.toLowerCase()
            .split(/[^a-z0-9]+/)
            .filter(word => word.length >= 2 && !stopWords.has(word));
    }
    
    const tokenizedDocs = documents.map(doc => tokenize(doc));
    const termDocCounts = {};
    
    tokenizedDocs.forEach(tokens => {
        const uniqueTokens = new Set(tokens);
        uniqueTokens.forEach(word => {
            termDocCounts[word] = (termDocCounts[word] || 0) + 1;
        });
    });
    
    const N = documents.length;
    const vocabulary = [];
    
    for (const [word, df] of Object.entries(termDocCounts)) {
        const idf = Math.log((1 + N) / (1 + df)) + 1.0;
        vocabulary.push({ word, df, idf });
    }
    
    vocabulary.sort((a, b) => a.word.localeCompare(b.word));
    
    const vectors = tokenizedDocs.map((tokens, docIdx) => {
        const tf = {};
        tokens.forEach(word => {
            tf[word] = (tf[word] || 0) + 1;
        });
        
        const vector = {};
        let normSq = 0;
        vocabulary.forEach(v => {
            const word = v.word;
            const count = tf[word] || 0;
            const tfidf = count * v.idf;
            vector[word] = tfidf;
            normSq += tfidf * tfidf;
        });
        
        const norm = Math.sqrt(normSq);
        const normVector = {};
        vocabulary.forEach(v => {
            const word = v.word;
            normVector[word] = norm > 0 ? (vector[word] / norm) : 0;
        });
        
        return normVector;
    });
    
    return { vocabulary, vectors };
}

function renderVectorizerResults(vocabulary, vectors, docs) {
    const vocabBody = $('vocabTable').querySelector('tbody');
    vocabBody.innerHTML = '';
    
    vocabulary.forEach(v => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td style="text-align: left; padding: 4px; color: var(--karl-text);">${escapeHtml(v.word)}</td>
            <td style="text-align: right; padding: 4px; color: var(--karl-muted);">${v.df}</td>
            <td style="text-align: right; padding: 4px; color: var(--karl-accent-2);">${v.idf.toFixed(4)}</td>
        `;
        vocabBody.appendChild(row);
    });
    
    let vectorText = '';
    vectors.forEach((v, idx) => {
        vectorText += `Doc ${idx + 1}: "${escapeHtml(docs[idx])}"\n`;
        const nonZeroTerms = [];
        vocabulary.forEach(term => {
            const val = v[term.word];
            if (val > 0) {
                nonZeroTerms.push(`${term.word}: ${val.toFixed(4)}`);
            }
        });
        vectorText += `  Vector: [${nonZeroTerms.join(', ')}]\n\n`;
    });
    
    $('tfidfVectors').innerText = vectorText;
    $('vectorizerOutput').style.display = 'block';
}

function handleInterceptedTelemetry(msg) {
    if (typeof msg !== 'string') return;
    
    const statusPanel = $('miniGptTrainingStatus');
    if (!statusPanel) return;
    statusPanel.style.display = 'block';
    
    const stepLossRegex = /Step\s*(\d+)\s*\|\s*(?:Val\s+)?Loss:\s*([0-9.]+)/i;
    const match = msg.match(stepLossRegex);
    if (match) {
        const step = parseInt(match[1]);
        const loss = parseFloat(match[2]);
        updateMiniGptTelemetryUi(step, loss);
        return;
    }
    
    const jsonLossRegex = /['"]loss['"]\s*:\s*([0-9.]+)/i;
    const jsonMatch = msg.match(jsonLossRegex);
    if (jsonMatch) {
        const loss = parseFloat(jsonMatch[1]);
        currentMiniStep++;
        updateMiniGptTelemetryUi(currentMiniStep, loss);
        return;
    }
    
    if (msg.includes('Generation Output') || msg.includes('--- Generation')) {
        const cleanMsg = msg.replace(/<[^>]*>/g, '');
        $('miniTypewriterOutput').innerHTML = `<div style="color: var(--karl-accent);">${escapeHtml(cleanMsg)}</div>`;
        return;
    }
    
    if (msg.includes('training') || msg.includes('Trainer') || msg.includes('Loss') || msg.includes('Epoch')) {
        const cleanMsg = msg.replace(/<[^>]*>/g, '');
        const entry = document.createElement('div');
        entry.style.borderBottom = '1px solid rgba(0, 194, 255, 0.05)';
        entry.style.padding = '2px 0';
        entry.innerText = cleanMsg;
        const logContainer = $('miniLossHistory');
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

function startMiniGptSimulation(maxIters, lr) {
    if (miniGptSimTimer) {
        clearInterval(miniGptSimTimer);
    }
    
    $('miniGptTrainingStatus').style.display = 'block';
    $('miniLossHistory').innerHTML = '<div style="color: var(--karl-muted);">Local Simulation Active...</div>';
    $('miniTypewriterOutput').innerHTML = '';
    
    let step = 0;
    let currentLoss = 4.5 + Math.random();
    
    const sampleWords = [
        "karl", "agent", "local", "model", "training", "offline", "zero", "network", 
        "vector", "sandbox", "embeddings", "attention", "transformer", "weights", 
        "loss", "gradient", "optimization", "completion", "intelligence", "generation"
    ];
    
    function generateTypewriterTokens() {
        const wordCount = 10 + Math.floor(Math.random() * 15);
        const sentence = [];
        for (let i = 0; i < wordCount; i++) {
            sentence.push(sampleWords[Math.floor(Math.random() * sampleWords.length)]);
        }
        return sentence.join(' ') + '.';
    }
    
    miniGptSimTimer = setInterval(() => {
        step += 5;
        if (step > maxIters) {
            clearInterval(miniGptSimTimer);
            miniGptSimTimer = null;
            const finalEntry = document.createElement('div');
            finalEntry.style.color = 'var(--karl-good)';
            finalEntry.innerText = `[Simulation] Training complete. Saved to data/mini_gpt/weights.pt`;
            $('miniLossHistory').appendChild(finalEntry);
            return;
        }
        
        const decay = (step / maxIters) * 3.0;
        currentLoss = Math.max(0.12, (4.5 - decay) + (Math.random() * 0.4 - 0.2));
        
        updateMiniGptTelemetryUi(step, currentLoss);
        
        if (step % 20 === 0) {
            const text = generateTypewriterTokens();
            streamTypewriterTokens(step, maxIters, text);
        }
    }, 500);
}

function updateMiniGptTelemetryUi(step, loss) {
    const stepEl = $('miniCurrentStep');
    const lossEl = $('miniCurrentLoss');
    if (stepEl) stepEl.innerText = step;
    if (lossEl) lossEl.innerText = loss.toFixed(4);
    
    const entry = document.createElement('div');
    entry.style.color = loss < 1.0 ? 'var(--karl-good)' : 'var(--karl-text)';
    entry.innerText = `Step ${step} | Loss: ${loss.toFixed(4)}`;
    
    const logContainer = $('miniLossHistory');
    if (logContainer) {
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

function streamTypewriterTokens(step, maxIters, text) {
    const container = $('miniTypewriterOutput');
    if (!container) return;
    
    container.innerHTML = `<div style="color: var(--karl-accent); border-bottom: 1px solid rgba(0, 194, 255, 0.1); margin-bottom: 4px; padding-bottom: 2px;">--- Step ${step} / ${maxIters} ---</div>`;
    
    const textSpan = document.createElement('span');
    container.appendChild(textSpan);
    
    let charIdx = 0;
    const interval = setInterval(() => {
        if (charIdx >= text.length) {
            clearInterval(interval);
            return;
        }
        textSpan.innerText += text[charIdx];
        charIdx++;
        container.scrollTop = container.scrollHeight;
    }, 20);
}

function _initEducationalSandbox() {
    const fitBtn = $('fitVectorizerBtn');
    const trainBtn = $('startMiniGptBtn');
    
    if (fitBtn) {
        fitBtn.addEventListener('click', () => {
            const text = $('sandboxDocs').value.trim();
            if (!text) {
                vscode.postMessage({ command: 'show_error', text: 'Please enter at least one document.' });
                return;
            }
            const docs = text.split('\n').map(d => d.trim()).filter(d => d.length > 0);
            if (docs.length === 0) {
                vscode.postMessage({ command: 'show_error', text: 'Please enter valid non-empty documents.' });
                return;
            }
            
            rpc(60, 'fit_vectorizer', { documents: docs });
            
            try {
                const { vocabulary, vectors } = fitTfidfVectorizer(docs);
                renderVectorizerResults(vocabulary, vectors, docs);
            } catch (err) {
                log(`[Vectorizer Local Error] ${err.message}`);
            }
        });
    }

    if (trainBtn) {
        trainBtn.addEventListener('click', () => {
            const lr = parseFloat($('miniLr').value) || 0.001;
            const iters = parseInt($('miniIters').value) || 100;
            const batchSize = parseInt($('miniBatchSize').value) || 16;
            
            rpc(61, 'start_mini_train', {
                lr: lr,
                max_iters: iters,
                batch_size: batchSize
            });
            
            startMiniGptSimulation(iters, lr);
        });
    }

    if (typeof handleSocketMessage === 'function') {
        const originalHandleSocketMessage = handleSocketMessage;
        handleSocketMessage = function(data) {
            originalHandleSocketMessage(data);
            
            if (data && data.method === 'auto_train_log') {
                const msg = (data.params && data.params.message) || '';
                handleInterceptedTelemetry(msg);
            } else if (data && data.method === 'status_update') {
                const msg = (data.params && data.params.message) || '';
                handleInterceptedTelemetry(msg);
            }
        };
    }
}

window.addEventListener('DOMContentLoaded', () => {
    _initEducationalSandbox();
});
