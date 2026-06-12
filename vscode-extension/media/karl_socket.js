// ── Bridge Relay Layer ─────────────────────────────────────────────────────────
// All outbound RPC passes through BridgeRelay. When window.KARL_USE_HOST_RELAY
// is true the extension host owns the WebSocket and we communicate via
// postMessage. When false (the default), we manage the WebSocket directly.
// The relay flag lets the host opt-in without any webview code changes.

const BridgeRelay = (() => {
    function _directSend(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
        }
    }

    return {
        send(payload) {
            if (window.KARL_USE_HOST_RELAY) {
                vscode.postMessage({ command: 'bridge_send', payload });
            } else {
                _directSend(payload);
            }
        },
        connected() {
            if (window.KARL_USE_HOST_RELAY) return connectionState === 'connected';
            return socket !== null && socket.readyState === WebSocket.OPEN;
        }
    };
})();

// ── connection state ──────────────────────────────────────────────────────────

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

// ── public connection API ──────────────────────────────────────────────────────

// connect() is the single entry point. It dispatches to the host relay or to
// the direct WebSocket implementation depending on KARL_USE_HOST_RELAY.
function connect() {
    if (window.KARL_USE_HOST_RELAY) {
        manualDisconnect = false;
        const port = Number($('bridgePort').value) || boot.port || 8080;
        $('cockpitPort').innerText = port;
        setConnectionState('connecting', 'Connecting');
        log(`[Bridge] Requesting host relay connection to ws://localhost:${port}`);
        vscode.postMessage({ command: 'bridge_connect', port });
        return;
    }
    _directConnect();
}

function disconnect() {
    manualDisconnect = true;
    if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
    }
    if (window.KARL_USE_HOST_RELAY) {
        vscode.postMessage({ command: 'bridge_disconnect' });
        setConnectionState('offline', 'Offline');
        return;
    }
    teardownSocket(false);
}

// ── direct WebSocket implementation ───────────────────────────────────────────

function _directConnect() {
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

// ── RPC ───────────────────────────────────────────────────────────────────────

function rpc(id, method, params) {
    if (!BridgeRelay.connected()) {
        if (![20, 31, 40, 50].includes(id)) {
            vscode.postMessage({ command: 'show_error', text: 'Karl bridge is offline.' });
        }
        return;
    }
    BridgeRelay.send({ jsonrpc: '2.0', id, method, params });
}

function isConnected() {
    return BridgeRelay.connected();
}

// ── incoming message dispatcher ───────────────────────────────────────────────

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
        // Route thought tokens to the collapsible reasoning panel
        if (!labRunning) {
            $('introspectionBox').classList.add('active');
            appendThoughtToken(params.token || '');
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

// ── polling ────────────────────────────────────────────────────────────────────

function requestRuntimeStatus() {
    rpc(30, 'get_runtime_status');
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

// ── data loaders ───────────────────────────────────────────────────────────────

function loadModels() {
    if (!isConnected()) {
        $('modelList').innerHTML = '<div class="model-card"><div class="model-meta">Karl bridge is offline.</div></div>';
        return;
    }
    rpc(31, 'list_models');
}

function loadPromptPairs() {
    rpc(40, 'list_prompt_pairs');
}

function loadKbSources() {
    if (!isConnected()) {
        $('kbSourceList').innerHTML = '<div class="source-item">Karl bridge is offline.</div>';
        return;
    }
    rpc(50, 'list_kb_sources');
}

function loadCodexTopics() {
    rpc(20, 'list_codex_topics');
}
