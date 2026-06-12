window.addEventListener('DOMContentLoaded', () => {
    initializeAppearance();
    hydrate();
    _initThoughtsPanel();
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
