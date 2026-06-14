// @ts-check
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const { writeTempFileAndDiff } = require('./fileOps');
const { getGitBranch } = require('./gitOps');
const {
    currentWorkspacePath,
    groupedDiagnostics,
    runWorkflowById,
    sendActiveFileToKb
} = require('./commands');

/**
 * @typedef {Object} PendingEdit
 * @property {string} filepath
 * @property {string} content
 * @property {string} summary
 * @property {string} filename
 * @property {number} oldLines
 * @property {number} newLines
 * @property {string} status
 * @property {string} [backupPath]
 */

function getDiagnosticsStats() {
    const severityName = ['error', 'warning', 'info', 'hint'];
    const counts = { error: 0, warning: 0, info: 0, hint: 0 };
    for (const [, items] of vscode.languages.getDiagnostics()) {
        items.forEach(item => {
            const severity = severityName[item.severity] || 'info';
            counts[severity] += 1;
        });
    }
    return counts;
}

let sendStateTimeout = null;

/**
 * Sends current active editor state, git branch, diagnostics, and edits count.
 * @param {KarlSidebarProvider} sidebarProvider
 */
function sendActiveStateToWebview(sidebarProvider) {
    if (sendStateTimeout) {
        clearTimeout(sendStateTimeout);
    }
    sendStateTimeout = setTimeout(async () => {
        sendStateTimeout = null;
        try {
            const workspacePath = currentWorkspacePath('');
            const activeFile = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.document.uri.fsPath : '';
            
            if (!sidebarProvider._cachedBranch && workspacePath) {
                sidebarProvider._cachedBranch = await getGitBranch(workspacePath);
            }
            const gitBranch = sidebarProvider._cachedBranch;
            
            const diagnostics = getDiagnosticsStats();
            const diagnosticsDetails = groupedDiagnostics(false);
            const pendingEditsCount = sidebarProvider.pendingEdits ? sidebarProvider.pendingEdits.size : 0;

            const state = {
                workspacePath,
                activeFile,
                gitBranch,
                diagnostics,
                diagnosticsDetails,
                pendingEditsCount
            };

            const stateJson = JSON.stringify(state);
            if (sidebarProvider.lastSentStateJson === stateJson) {
                return; // Skip sending unchanged state
            }
            sidebarProvider.lastSentStateJson = stateJson;

            sidebarProvider.postMessageToWebview({
                command: 'cockpit_state_update',
                state
            });
        } catch (err) {
            console.error('Failed to send active state:', err);
        }
    }, 150);
}

class KarlSidebarProvider {
    /**
     * @param {vscode.ExtensionContext} context
     */
    constructor(context) {
        /** @type {vscode.ExtensionContext} */
        this.context = context;
        /** @type {vscode.Uri} */
        this.extensionUri = context.extensionUri;
        /** @type {vscode.WebviewView | null} */
        this.webviewView = null;
        
        /** @type {Map<string, PendingEdit>} */
        const savedEdits = context.workspaceState.get('karl.pendingEdits', []);
        this.pendingEdits = new Map(savedEdits);
        
        /** @type {(() => void) | null} */
        this._resolveWebview = null;
        /** @type {boolean} */
        this.isReady = false;
        /** @type {any[]} */
        this.messageQueue = [];
        /** @type {vscode.OutputChannel | null} */
        this.autoTrainChannel = null;

        // WebSocket properties
        /** @type {WebSocket | null} */
        this.socket = null;
        /** @type {NodeJS.Timeout | null} */
        this.reconnectTimer = null;
        /** @type {NodeJS.Timeout | null} */
        this.heartbeatTimer = null;
        /** @type {boolean} */
        this.manualDisconnect = false;
        /** @type {string} */
        this.connectionState = 'offline';
        /** @type {Date | null} */
        this.lastHeartbeatAt = null;
        /** @type {Date | null} */
        this.lastConnectedAt = null;
        /** @type {string} */
        this.lastBridgeError = '';

        // Git branch caching properties
        /** @type {string} */
        this._cachedBranch = '';
        /** @type {vscode.FileSystemWatcher | null} */
        this._gitWatcher = null;

        this._initGitWatcher();
        vscode.workspace.onDidChangeWorkspaceFolders(() => {
            this._cachedBranch = '';
            this._initGitWatcher();
            sendActiveStateToWebview(this);
        });
    }

    /**
     * Sends an RPC command directly over the active bridge socket.
     * @param {string} method
     * @param {Object} params
     * @returns {boolean}
     */
    sendRpc(method, params) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const reqId = Math.floor(Math.random() * 10000);
            this.socket.send(JSON.stringify({
                jsonrpc: "2.0",
                id: reqId,
                method,
                params
            }));
            return true;
        }
        return false;
    }

    /**
     * Persists pending edits to workspaceState.
     * @private
     */
    _savePendingEdits() {
        this.context.workspaceState.update('karl.pendingEdits', Array.from(this.pendingEdits.entries()));
    }

    /**
     * Initializes the git branch watcher.
     * @private
     */
    _initGitWatcher() {
        if (this._gitWatcher) {
            this._gitWatcher.dispose();
        }
        const workspacePath = currentWorkspacePath('');
        if (!workspacePath) return;

        const pattern = new vscode.RelativePattern(workspacePath, '.git/HEAD');
        this._gitWatcher = vscode.workspace.createFileSystemWatcher(pattern);

        const clearCache = () => {
            this._cachedBranch = '';
            sendActiveStateToWebview(this);
        };

        this._gitWatcher.onDidChange(clearCache);
        this._gitWatcher.onDidCreate(clearCache);
        this._gitWatcher.onDidDelete(clearCache);
    }

    /**
     * Reads the bridge token from disk, retrying up to 3 times with a 100 ms delay
     * to tolerate file-lock races while the Python host is rotating the token file.
     * Returns an empty string if the file is absent or unparseable after all retries.
     * @returns {Promise<string>}
     * @private
     */
    async _readBridgeToken() {
        const wsRoot = currentWorkspacePath('') || process.cwd();
        const tokenFile = path.join(wsRoot, 'data', 'bridge_token.json');
        const MAX_RETRIES = 3;
        for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
            try {
                const raw = await fs.promises.readFile(tokenFile, 'utf8');
                return JSON.parse(raw).token || '';
            } catch (err) {
                if (attempt < MAX_RETRIES - 1) {
                    await new Promise(res => setTimeout(res, 100));
                } else {
                    // File absent or unreadable after all retries — connect tokenless;
                    // the server will reject with 4001 if a token is required.
                    console.warn('[Karl] Could not read bridge_token.json after 3 attempts:', err.message);
                }
            }
        }
        return '';
    }

    /**
     * Connects to the Karl WebSocket server.
     * @param {number} [port]
     */
    async connectToBridge(port) {
        if (this.socket) {
            this.teardownSocket();
        }

        const config = vscode.workspace.getConfiguration('karl');
        const activePort = port !== undefined ? port : config.get('port', 8080);

        this.lastBridgeError = '';
        this._setConnectionState('connecting', 'Connecting');

        // Re-read the token from disk on every connection attempt so token rotation
        // (single-use handshake policy) is picked up without an extension reload.
        const bridgeToken = await this._readBridgeToken();
        const wsUrl = `wss://127.0.0.1:${activePort}${bridgeToken ? `?token=${encodeURIComponent(bridgeToken)}` : ''}`;
        // rejectUnauthorized: false — the Python backend uses a self-signed localhost cert
        const wsOptions = { rejectUnauthorized: false };

        try {
            this.socket = new WebSocket(wsUrl, wsOptions);
        } catch (err) {
            this.lastBridgeError = err.message || 'Connection failed';
            this._handleDisconnect(true);
            return;
        }

        this.socket.on('open', () => {
            this.lastConnectedAt = new Date();
            this._setConnectionState('connected', 'Connected');
            if (this.reconnectTimer) {
                clearInterval(this.reconnectTimer);
                this.reconnectTimer = null;
            }
            this._startHeartbeat();
        });

        this.socket.on('message', (rawData) => {
            try {
                const data = JSON.parse(rawData.toString());
                
                // Intercept status update response (heartbeat result)
                if (data && data.id === 30 && data.result) {
                    this.lastHeartbeatAt = new Date();
                }

                // Intercept auto-train log notifications
                if (data && data.method === 'auto_train_log') {
                    const msg = data.params.message;
                    if (!this.autoTrainChannel) {
                        this.autoTrainChannel = vscode.window.createOutputChannel("Karl Auto-Train Logs");
                    }
                    this.autoTrainChannel.appendLine(msg);
                }
                if (data && data.method === 'auto_train_finished') {
                    const success = data.params.success;
                    const msg = data.params.message;
                    if (!this.autoTrainChannel) {
                        this.autoTrainChannel = vscode.window.createOutputChannel("Karl Auto-Train Logs");
                    }
                    this.autoTrainChannel.appendLine(`\n--- Auto-Training Finished. Success: ${success}. ${msg} ---`);
                    if (success) {
                        vscode.window.showInformationMessage(`Karl: Auto-training finished successfully for adapter "${data.params.adapter_name}"!`);
                    } else {
                        vscode.window.showErrorMessage(`Karl: Auto-training failed: ${msg}`);
                    }
                }

                // Forward message to webview
                this.postMessageToWebview({
                    command: 'socket_message',
                    data
                });
            } catch (err) {
                console.error('[Host Bridge Error] Malformed JSON:', err);
            }
        });

        this.socket.on('error', (err) => {
            this.lastBridgeError = err.message || 'Connection failed';
            this._handleDisconnect(true);
        });

        this.socket.on('close', (code) => {
            if (code === 4001) {
                console.error('[Karl] Unauthorized Karl extension bridge connection: invalid or expired token');
                this.lastBridgeError = 'Token invalid or expired (4001) — check data/bridge_token.json';
                this.manualDisconnect = true; // Don't auto-reconnect on auth rejection
                vscode.window.showWarningMessage(
                    'Karl: Bridge connection rejected (invalid or expired token). Check data/bridge_token.json.'
                );
                this._handleDisconnect(false);
                // Override the generic 'Offline' label with a dedicated auth-rejected indicator
                this.postMessageToWebview({
                    command: 'connection_state',
                    state: 'offline',
                    label: 'Auth Rejected',
                    lastConnected: this.lastConnectedAt ? this.lastConnectedAt.toLocaleTimeString() : 'never',
                    lastHeartbeat: this.lastHeartbeatAt ? this.lastHeartbeatAt.toLocaleTimeString() : 'never',
                    lastError: 'Token invalid or expired (4001) — check data/bridge_token.json'
                });
                return;
            }
            this._handleDisconnect(false);
        });
    }

    /**
     * Closes the active WebSocket socket.
     */
    teardownSocket() {
        this._stopHeartbeat();
        if (this.socket) {
            this.socket.removeAllListeners('open');
            this.socket.removeAllListeners('message');
            this.socket.removeAllListeners('error');
            this.socket.removeAllListeners('close');
            try {
                if (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN) {
                    this.socket.close();
                }
            } catch {}
            this.socket = null;
        }
        if (this.reconnectTimer) {
            clearInterval(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    /**
     * Handles connection disconnect and auto-reconnection.
     * @param {boolean} [isError]
     * @private
     */
    _handleDisconnect(isError = false) {
        this.teardownSocket();
        this._setConnectionState('offline', isError ? 'Error' : 'Offline');

        const config = vscode.workspace.getConfiguration('karl');
        const autoConnect = config.get('autoConnect', true);

        if (autoConnect && !this.manualDisconnect && !this.reconnectTimer) {
            let nextReconnectSec = 5;
            this._setConnectionState('offline', `Reconnecting in ${nextReconnectSec}s`);
            this.reconnectTimer = setInterval(() => {
                nextReconnectSec--;
                if (nextReconnectSec <= 0) {
                    clearInterval(this.reconnectTimer);
                    this.reconnectTimer = null;
                    const port = config.get('port', 8080);
                    this.connectToBridge(port);
                } else {
                    this._setConnectionState('offline', `Reconnecting in ${nextReconnectSec}s`);
                }
            }, 1000);
        }
    }

    /**
     * Starts the heartbeat loop.
     * @private
     */
    _startHeartbeat() {
        this._stopHeartbeat();
        this._sendHeartbeatRpc();
        this.heartbeatTimer = setInterval(() => {
            this._sendHeartbeatRpc();
        }, 4000);
    }

    /**
     * Stops the heartbeat loop.
     * @private
     */
    _stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Sends a status check RPC.
     * @private
     */
    _sendHeartbeatRpc() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 30,
                method: 'get_runtime_status'
            }));
        }
    }

    /**
     * Updates and propagates the current connection state.
     * @param {string} state
     * @param {string} label
     * @private
     */
    _setConnectionState(state, label) {
        this.connectionState = state;
        this.postMessageToWebview({
            command: 'connection_state',
            state,
            label,
            lastConnected: this.lastConnectedAt ? this.lastConnectedAt.toLocaleTimeString() : 'never',
            lastHeartbeat: this.lastHeartbeatAt ? this.lastHeartbeatAt.toLocaleTimeString() : 'never',
            lastError: this.lastBridgeError || ''
        });
        sendActiveStateToWebview(this);
    }

    dispose() {
        this.teardownSocket();
        if (this._gitWatcher) {
            this._gitWatcher.dispose();
            this._gitWatcher = null;
        }
        this.webviewView = null;
        this.pendingEdits.clear();
        this._resolveWebview = null;
        this.isReady = false;
        this.messageQueue = [];
    }

    waitForWebview() {
        if (this.isReady) return Promise.resolve();
        return new Promise(resolve => {
            this._resolveWebview = resolve;
        });
    }

    /**
     * Resolves the Webview panel instance.
     * @param {vscode.WebviewView} webviewView
     */
    resolveWebviewView(webviewView) {
        this.webviewView = webviewView;
        this.isReady = false;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri]
        };

        const config = vscode.workspace.getConfiguration('karl');
        const port = config.get('port', 8080);
        const autoConnect = config.get('autoConnect', true);
        const workspaceFolder = currentWorkspacePath('');
        const persisted = this.context.workspaceState.get('karl.sidebarState', {});

        webviewView.webview.html = this.getHtmlForWebview(
            webviewView.webview,
            port,
            autoConnect,
            workspaceFolder,
            persisted
        );

        webviewView.webview.onDidReceiveMessage(async message => {
            switch (message.command) {
                case 'ready':
                    this.isReady = true;
                    
                    // Sync current connection status
                    this._setConnectionState(this.connectionState, this.connectionState.toUpperCase());
                    
                    // Sync loaded pending edits to webview
                    for (const [editId, edit] of this.pendingEdits.entries()) {
                        this.postMessageToWebview({
                            command: 'pending_file_edit',
                            edit: {
                                id: editId,
                                filepath: edit.filepath,
                                filename: edit.filename,
                                summary: edit.summary,
                                bytes: Buffer.byteLength(edit.content, 'utf8'),
                                oldLines: edit.oldLines,
                                newLines: edit.newLines,
                                lineDelta: edit.newLines - edit.oldLines,
                                status: edit.status
                            }
                        });
                    }

                    while (this.messageQueue.length > 0) {
                        const msg = this.messageQueue.shift();
                        if (this.webviewView) {
                            this.webviewView.webview.postMessage(msg);
                        }
                    }
                    if (this._resolveWebview) {
                        this._resolveWebview();
                        this._resolveWebview = null;
                    }
                    break;
                case 'persist_state':
                    await this.context.workspaceState.update('karl.sidebarState', message.state || {});
                    break;
                case 'show_message':
                    vscode.window.showInformationMessage(message.text);
                    break;
                case 'show_error':
                    vscode.window.showErrorMessage(message.text);
                    break;
                case 'run_command':
                    await vscode.commands.executeCommand(message.commandId);
                    break;
                case 'choose_kb_file':
                    await this.chooseKbFile();
                    break;
                case 'choose_kb_folder':
                    await this.chooseKbFolder();
                    break;
                case 'use_active_file_for_kb':
                    await sendActiveFileToKb(this);
                    break;
                case 'queue_file_edit':
                    this.queueFileEdit(message.filepath, message.content, message.summary);
                    break;
                case 'preview_file':
                    await this.previewFile(message.editId);
                    break;
                case 'apply_file':
                    await this.applyFile(message.editId);
                    break;
                case 'reject_file':
                    this.rejectFile(message.editId);
                    break;
                case 'reject_all_files':
                    this.rejectAllFiles();
                    break;
                case 'open_file':
                    await this.openFile(message.editId);
                    break;
                case 'copy_file_path':
                    await this.copyFilePath(message.editId);
                    break;
                case 'rollback_applied_file':
                    await this.rollbackAppliedFile(message.editId);
                    break;
                case 'preview_all_files':
                    await this.previewAllFiles();
                    break;
                case 'copy_patch_summary':
                    await this.copyPatchSummary();
                    break;
                case 'accept_file':
                    await this.acceptLegacyFile(message.filepath);
                    break;
                case 'rollback_file':
                    await this.rollbackLegacyFile(message.filepath);
                    break;
                case 'runWorkflow':
                    await runWorkflowById(this, message.workflowId, message.payload);
                    break;
                case 'get_cockpit_state':
                    await sendActiveStateToWebview(this);
                    break;
                case 'open_diagnostic_line':
                    await this.openDiagnosticLine(message.filepath, message.line, message.character);
                    break;
                case 'connect':
                    this.manualDisconnect = false;
                    this.connectToBridge(message.port);
                    break;
                case 'disconnect':
                    this.manualDisconnect = true;
                    this.teardownSocket();
                    this._setConnectionState('offline', 'Offline');
                    break;
                case 'rpc':
                    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                        this.socket.send(JSON.stringify(message.payload));
                    }
                    break;
                default:
                    break;
            }
        });

        if (autoConnect && !this.socket) {
            this.connectToBridge(port);
        }

        // Trigger cockpit refresh immediately
        sendActiveStateToWebview(this);
    }

    postMessageToWebview(message) {
        if (this.isReady && this.webviewView) {
            this.webviewView.webview.postMessage(message);
        } else {
            this.messageQueue.push(message);
        }
    }

    async queueFileEdit(filepath, content, summary = '') {
        if (!filepath || typeof content !== 'string') {
            vscode.window.showErrorMessage('Karl sent an invalid file edit payload.');
            return;
        }
        const editId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const filename = path.basename(filepath);
        let previous = '';
        try {
            const fileExists = await fs.promises.access(filepath).then(() => true).catch(() => false);
            previous = fileExists ? await fs.promises.readFile(filepath, 'utf8') : '';
        } catch {
            previous = '';
        }
        const oldLines = previous ? previous.split(/\r?\n/).length : 0;
        const newLines = content ? content.split(/\r?\n/).length : 0;
        this.pendingEdits.set(editId, { filepath, content, summary, filename, oldLines, newLines, status: 'proposed' });
        this._savePendingEdits();

        this.postMessageToWebview({
            command: 'pending_file_edit',
            edit: {
                id: editId,
                filepath,
                filename,
                summary,
                bytes: Buffer.byteLength(content, 'utf8'),
                oldLines,
                newLines,
                lineDelta: newLines - oldLines,
                status: 'proposed'
            }
        });
        sendActiveStateToWebview(this);
    }

    async previewFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (!edit) {
            vscode.window.showWarningMessage('That Karl edit is no longer pending.');
            return;
        }
        try {
            await writeTempFileAndDiff(edit.filename, edit.filepath, edit.content, `Karl Preview: ${edit.filename}`);
            edit.status = 'previewed';
            this._savePendingEdits();
            this.postMessageToWebview({ command: 'file_edit_previewed', editId });
            sendActiveStateToWebview(this);
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to show preview: ${err.message}`);
        }
    }

    async previewAllFiles() {
        for (const editId of this.pendingEdits.keys()) {
            await this.previewFile(editId);
        }
    }

    async copyPatchSummary() {
        const rows = Array.from(this.pendingEdits.values()).map(edit => {
            const delta = edit.newLines - edit.oldLines;
            return `- ${edit.filepath} (${delta >= 0 ? '+' : ''}${delta} lines): ${edit.summary || 'Karl proposed an update.'}`;
        });
        const text = rows.length ? rows.join('\n') : 'No pending Karl edits.';
        await vscode.env.clipboard.writeText(text);
        vscode.window.showInformationMessage('Karl patch summary copied.');
    }

    async applyFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (!edit) {
            vscode.window.showWarningMessage('That Karl edit is no longer pending.');
            return;
        }

        try {
            const backupPath = edit.filepath + '.original';
            const fileExists = await fs.promises.access(edit.filepath).then(() => true).catch(() => false);
            const backupExists = await fs.promises.access(backupPath).then(() => true).catch(() => false);
            if (fileExists && !backupExists) {
                await fs.promises.copyFile(edit.filepath, backupPath);
            }
            await fs.promises.writeFile(edit.filepath, edit.content, 'utf8');
            edit.status = 'applied';
            edit.backupPath = backupPath;
            this.pendingEdits.set(editId, edit);
            this._savePendingEdits();
            const backupExistsAfter = await fs.promises.access(backupPath).then(() => true).catch(() => false);
            this.postMessageToWebview({ command: 'file_edit_applied', editId, backupExists: backupExistsAfter });
            vscode.window.showInformationMessage(`Karl applied changes to ${edit.filename}.`);
            await vscode.window.showTextDocument(vscode.Uri.file(edit.filepath), { preview: false });
            sendActiveStateToWebview(this);
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to apply Karl edit: ${err.message}`);
        }
    }

    rejectFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (edit && edit.status === 'applied') {
            vscode.window.showWarningMessage('Applied edits stay in Review Bay until rollback or manual cleanup.');
            return;
        }
        this.pendingEdits.delete(editId);
        this._savePendingEdits();
        this.postMessageToWebview({ command: 'file_edit_rejected', editId });
        if (edit) {
            vscode.window.showInformationMessage(`Rejected Karl edit for ${edit.filename}.`);
        }
        sendActiveStateToWebview(this);
    }

    rejectAllFiles() {
        for (const [editId, edit] of this.pendingEdits.entries()) {
            if (edit.status !== 'applied') {
                this.pendingEdits.delete(editId);
                this.postMessageToWebview({ command: 'file_edit_rejected', editId });
            }
        }
        this._savePendingEdits();
        sendActiveStateToWebview(this);
    }

    async openFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (edit) {
            const fileExists = await fs.promises.access(edit.filepath).then(() => true).catch(() => false);
            if (fileExists) {
                await vscode.window.showTextDocument(vscode.Uri.file(edit.filepath), { preview: false });
            }
        }
    }

    async copyFilePath(editId) {
        const edit = this.pendingEdits.get(editId);
        if (edit) {
            await vscode.env.clipboard.writeText(edit.filepath);
            vscode.window.showInformationMessage('Karl file path copied.');
        }
    }

    async rollbackAppliedFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (!edit) return;
        const backupPath = edit.backupPath || edit.filepath + '.original';
        const backupExists = await fs.promises.access(backupPath).then(() => true).catch(() => false);
        if (!backupExists) {
            vscode.window.showWarningMessage('No backup file found to rollback.');
            return;
        }
        await fs.promises.copyFile(backupPath, edit.filepath);
        await fs.promises.unlink(backupPath);
        edit.status = 'rolled_back';
        this.pendingEdits.set(editId, edit);
        this._savePendingEdits();
        this.postMessageToWebview({ command: 'file_edit_rolled_back', editId });
        vscode.window.showInformationMessage(`Rolled back ${edit.filename}.`);
        sendActiveStateToWebview(this);
    }

    async acceptLegacyFile(filepath) {
        if (!filepath) return;
        const backupPath = filepath + '.original';
        const backupExists = await fs.promises.access(backupPath).then(() => true).catch(() => false);
        if (backupExists) {
            await fs.promises.unlink(backupPath);
            vscode.window.showInformationMessage(`Accepted changes for ${path.basename(filepath)}.`);
        }
    }

    async rollbackLegacyFile(filepath) {
        if (!filepath) return;
        const backupPath = filepath + '.original';
        const backupExists = await fs.promises.access(backupPath).then(() => true).catch(() => false);
        if (!backupExists) {
            vscode.window.showWarningMessage('No backup file found to rollback.');
            return;
        }
        await fs.promises.copyFile(backupPath, filepath);
        await fs.promises.unlink(backupPath);
        vscode.window.showInformationMessage(`Rolled back changes for ${path.basename(filepath)}.`);
    }

    async chooseKbFile() {
        const files = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            filters: {
                'Knowledge files': ['pdf', 'docx', 'txt', 'md', 'py', 'csv'],
                'All files': ['*']
            },
            title: 'Select a file to ingest into Karl Knowledge Base'
        });
        if (files && files[0]) {
            this.postMessageToWebview({ command: 'set_kb_path', path: files[0].fsPath });
        }
    }

    async chooseKbFolder() {
        const folders = await vscode.window.showOpenDialog({
            canSelectFiles: false,
            canSelectFolders: true,
            canSelectMany: false,
            title: 'Select a folder to ingest into Karl Knowledge Base'
        });
        if (folders && folders[0]) {
            this.postMessageToWebview({ command: 'set_kb_path', path: folders[0].fsPath });
        }
    }

    async openDiagnosticLine(filepath, line, character) {
        try {
            const document = await vscode.workspace.openTextDocument(vscode.Uri.file(filepath));
            const editor = await vscode.window.showTextDocument(document);
            const pos = new vscode.Position(line - 1, character - 1);
            editor.selection = new vscode.Selection(pos, pos);
            editor.revealRange(new vscode.Range(pos, pos));
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to open diagnostic line: ${err.message}`);
        }
    }

    getHtmlForWebview(webview, port, autoConnect, workspaceFolder, persisted) {
        const cssUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'karl.css'));
        const themesUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'themes.js'));
        const stateUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'karl_state.js'));
        const renderUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'karl_render.js'));
        const socketUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'karl_socket.js'));
        const jsUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'karl.js'));
        const nonce = String(Date.now());
        const config = JSON.stringify({
            port,
            autoConnect,
            workspaceFolder,
            persisted: persisted || {}
        }).replace(/</g, '\\u003c');

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} https:; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src ws://localhost:* ws://127.0.0.1:* wss://localhost:* wss://127.0.0.1:* http://localhost:* http://127.0.0.1:*;">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karl</title>
    <link href="${cssUri}" rel="stylesheet">
</head>
<body>
    <script nonce="${nonce}">window.KARL_BOOTSTRAP = ${config};</script>
    <div class="shell">
        <header class="topbar glow-panel">
            <div>
                <div class="eyebrow">Karl IDE</div>
                <h1>Offline Control Deck</h1>
            </div>
            <div class="bridge">
                <span id="statusDot" class="status-dot offline"></span>
                <span id="statusText">Offline</span>
            </div>
        </header>

        <nav class="tabs" aria-label="Karl workspaces">
            <button class="tab active" data-workspace="cockpit">Cockpit</button>
            <button class="tab" data-workspace="chat">Chat</button>
            <button class="tab" data-workspace="swarm">Swarm</button>
            <button class="tab" data-workspace="changes">Changes</button>
            <button class="tab" data-workspace="git">Git</button>
            <button class="tab" data-workspace="diagnostics">Diag</button>
            <button class="tab" data-workspace="knowledge">Knowledge</button>
            <button class="tab" data-workspace="vision">Vision</button>
            <button class="tab" data-workspace="lab">Lab</button>
            <button class="tab" data-workspace="sandbox">Sandbox</button>
            <button class="tab" data-workspace="settings">Settings</button>
            <button class="tab" data-workspace="logs">Logs</button>
        </nav>

        <section id="offlinePanel" class="offline-panel glow-panel">
            <div class="scanner-line"></div>
            <div>
                <div class="eyebrow">Bridge Checklist</div>
                <p>Start Karl, verify the WebSocket bridge is listening, then connect. The panel will keep trying unless you disconnect manually.</p>
                <p id="bridgeMeta">Heartbeat: never · Last connect: never · Version: unknown</p>
            </div>
        </section>

        <main>
            <section id="workspace-cockpit" class="workspace active">
                <div class="section-head">
                    <div><div class="eyebrow">Cockpit</div><h2>Home Control & Status</h2></div>
                </div>
                <div class="cockpit-status-grid glow-panel">
                    <div class="metric"><span>Bridge Port</span><strong id="cockpitPort">--</strong></div>
                    <div class="metric"><span>Connection</span><strong id="cockpitConnection">offline</strong></div>
                    <div class="metric"><span>Active Model</span><strong id="cockpitModel">unknown</strong></div>
                    <div class="metric"><span>RAM / Context</span><strong id="cockpitSystem">--</strong></div>
                    <div class="metric"><span>Active Workspace</span><strong id="cockpitWorkspace">--</strong></div>
                    <div class="metric"><span>Active File</span><strong id="cockpitFile">none</strong></div>
                    <div class="metric"><span>Git Branch</span><strong id="cockpitBranch">--</strong></div>
                    <div class="metric"><span>Pending Changes</span><strong id="cockpitPendingChanges">0</strong></div>
                    <div class="metric"><span>Diagnostics</span><strong id="cockpitDiagnostics">0 errors</strong></div>
                    <div class="metric"><span>Last Heartbeat</span><strong id="cockpitHeartbeat">never</strong></div>
                </div>
                <div class="action-row">
                    <button id="cockpitConnectBtn" class="primary">Connect</button>
                    <button id="cockpitDisconnectBtn">Disconnect</button>
                </div>
                <div class="quick-actions-section">
                    <div class="eyebrow">Quick Actions</div>
                    <div class="quick-actions" id="quickActions"></div>
                </div>
                <div class="queue-panel">
                    <div class="section-head mini-head"><div><div class="eyebrow">Tasks</div><h2>Recent Run History</h2></div><button id="clearRecentTasksBtn">Clear</button></div>
                    <div id="recentTasksHistory" class="recent-list empty">No tasks run recently.</div>
                </div>
            </section>

            <section id="workspace-chat" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Chat</div><h2>Direct Assistant Chat</h2></div>
                    <button id="branchLatestBtn">Branch Latest</button>
                </div>
                <div id="introspectionBox" class="thoughts"><div class="eyebrow">Thought Stream</div><pre id="introspectionThoughts"></pre></div>
                <div id="chatMessages" class="chat"></div>
                <div class="composer">
                    <input id="chatInput" type="text" placeholder="Ask Karl about the codebase...">
                    <button id="chatSendBtn" class="primary">Send</button>
                </div>
                <div class="subpanel">
                    <div class="section-head mini-head"><div><div class="eyebrow">Branches</div><h2>Conversation Forks</h2></div><button id="newBranchBtn">New Branch</button></div>
                    <div id="branchTree" class="branch-tree empty">No conversation branches yet.</div>
                </div>
            </section>

            <section id="workspace-swarm" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Swarm</div><h2>Task Execution Surface</h2></div>
                    <button id="askWorkspaceBtn">Ask Workspace</button>
                </div>
                <div class="context-meter" id="contextMeter">Context package: none queued.</div>
                <label>Workflow
                    <select id="taskMode">
                        <option value="Custom Task">Custom Task</option>
                        <option value="fixSelection">Refactor Selection</option>
                        <option value="explainSelection">Explain Selection</option>
                        <option value="generateTests">Generate Tests</option>
                        <option value="reviewActiveFile">Review Active File</option>
                        <option value="sendCurrentFileToSwarm">Send File to Swarm</option>
                        <option value="createImplementationPlan">Create Implementation Plan</option>
                    </select>
                </label>
                <label>Objective <textarea id="objective" rows="5" placeholder="Describe what Karl should do..."></textarea></label>
                <label>Workspace Path <input id="workspace" type="text" placeholder="/path/to/project"></label>
                <label>Verification Command <input id="testCmd" type="text" value="python run_tests.py"></label>
                <div class="action-row">
                    <button id="runBtn" class="primary">Deploy Swarm</button>
                    <button id="stopBtn" class="danger">Stop</button>
                </div>
                <div class="timeline" id="timeline"></div>
                <div class="queue-panel">
                    <div class="section-head mini-head"><div><div class="eyebrow">Swarm Tasks</div><h2>Queue</h2></div><button id="clearTasksBtn">Clear Completed</button></div>
                    <div id="taskQueue" class="task-queue empty">No tasks queued.</div>
                </div>
            </section>

            <section id="workspace-changes" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Review</div><h2>Pending File Changes</h2></div>
                    <div class="action-row compact-actions">
                        <button id="previewAllBtn">Preview All</button>
                        <button id="rejectAllBtn" class="danger">Reject All</button>
                        <button id="copySummaryBtn">Copy Summary</button>
                    </div>
                </div>
                <label>Filter <select id="changeFilter"><option value="">All</option><option value="proposed">Proposed</option><option value="previewed">Previewed</option><option value="applied">Applied</option><option value="rolled_back">Rolled Back</option></select></label>
                <div id="changeQueue" class="queue empty">No pending Karl edits.</div>
            </section>

            <section id="workspace-git" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Git</div><h2>Diff & Commit Workspace</h2></div>
                </div>
                <div class="git-status-card glow-panel" style="padding: 10px;">
                    <div>Current Branch: <strong id="gitBranchDisplay">--</strong></div>
                </div>
                <div class="action-row">
                    <button id="gitReviewStagedBtn">Review Staged Diff</button>
                    <button id="gitReviewUnstagedBtn">Review Unstaged Diff</button>
                    <button id="gitReviewCombinedBtn">Review Combined Diff</button>
                </div>
                <div class="action-row">
                    <button id="gitCommitMsgBtn" class="primary">Generate Commit Msg</button>
                    <button id="gitCopyCommitBtn">Copy Commit Msg</button>
                </div>
                <div id="gitCommitOutput" class="result-card" style="display:none;">
                    <div class="eyebrow">Generated Commit Message</div>
                    <pre id="gitCommitText"></pre>
                </div>
                <div id="gitDiffContainer" class="result-card" style="display:none;">
                    <div class="eyebrow">Active Diff Review</div>
                    <pre id="gitDiffText"></pre>
                </div>
            </section>

            <section id="workspace-diagnostics" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Diagnostics</div><h2>Problems & Explanations</h2></div>
                </div>
                <div class="diagnostics-summary-grid glow-panel">
                    <div class="metric"><span>Errors</span><strong id="diagErrorsCount">0</strong></div>
                    <div class="metric"><span>Warnings</span><strong id="diagWarningsCount">0</strong></div>
                    <div class="metric"><span>Infos</span><strong id="diagInfosCount">0</strong></div>
                    <div class="metric"><span>Hints</span><strong id="diagHintsCount">0</strong></div>
                </div>
                <div class="action-row">
                    <button id="diagExplainFileBtn">Explain Active File Problems</button>
                    <button id="diagExplainWorkspaceBtn">Explain Workspace Problems</button>
                </div>
                <div id="diagnosticsList" class="source-list" style="margin-top: 8px;"></div>
                <div id="diagExplanation" class="result-card" style="display:none;">
                    <div class="eyebrow">Problem Explanations</div>
                    <pre id="diagExplanationText"></pre>
                </div>
            </section>

            <section id="workspace-knowledge" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Knowledge</div><h2>KB RAG & Codex Library</h2></div>
                </div>
                <nav class="subtabs" aria-label="Knowledge Mode">
                    <button class="subtab active" data-subworkspace="kb-rag">RAG Database</button>
                    <button class="subtab" data-subworkspace="kb-codex">Codex Library</button>
                </nav>
                <div id="subworkspace-kb-rag" class="subworkspace active" style="margin-top: 8px;">
                    <section class="runtime-grid">
                        <div class="metric"><span>Sources</span><strong id="kbSourceCount">0</strong></div>
                        <div class="metric"><span>Chunks</span><strong id="kbChunkCount">0</strong></div>
                        <div class="metric"><span>Index</span><strong id="kbIngestState">Idle</strong></div>
                    </section>
                    <div id="kbSourceList" class="source-list"></div>
                    <label>File Or Folder <input id="kbPath" type="text" placeholder="/path/to/file-or-folder"></label>
                    <div class="action-row">
                        <button id="activeFileKbBtn">Active File</button>
                        <button id="chooseKbFileBtn">Choose File</button>
                        <button id="chooseKbFolderBtn">Choose Folder</button>
                    </div>
                    <div class="action-row">
                        <button id="kbQueueAddBtn">Add To Queue</button>
                        <button id="kbQueueRunBtn" class="primary">Ingest Queue</button>
                        <button id="kbQueueClearBtn">Clear Queue</button>
                    </div>
                    <div id="kbQueue" class="queue-list empty">No files queued for batch ingest.</div>
                    <div class="settings-grid">
                        <label>Chunk Size <input id="kbChunkSize" type="number" min="50" max="2000" step="50" value="200"></label>
                        <label>Overlap <input id="kbOverlap" type="number" min="0" max="1000" step="10" value="50"></label>
                        <label class="check"><input id="kbRecursive" type="checkbox" checked> Recursive folders</label>
                    </div>
                    <button id="kbIngestBtn" class="primary">Ingest Path</button>
                    <label>Source Filter <select id="kbSourceFilter"><option value="">All sources</option></select></label>
                    <label>Retrieval Preview <textarea id="kbQuery" rows="3" placeholder="Search indexed project knowledge..."></textarea></label>
                    <div id="recentKbQueries" class="recent-list empty">No recent KB searches yet.</div>
                    <button id="kbSearchBtn">Search Knowledge Base</button>
                    <div id="kbResults" class="result-list"></div>
                </div>
                <div id="subworkspace-kb-codex" class="subworkspace" style="margin-top: 8px; display: none;">
                    <input id="codexSearch" type="text" placeholder="Search references...">
                    <div id="codexList" class="source-list" style="margin-top: 8px;"></div>
                    <article id="codexViewer" class="codex-viewer" style="margin-top: 8px;">Select a chapter to read local reference material.</article>
                </div>
            </section>

            <section id="workspace-vision" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Vision</div><h2>Karl Vision Desk</h2></div>
                </div>
                <div class="offline-panel active" id="visionBridgeWarning" style="margin-bottom: 8px;">
                    <div class="eyebrow">Bridge Required</div>
                    <p>Requires Karl Vision bridge support. Exposes local multimodal image understanding workflows.</p>
                </div>
                <label>Image File Path <input id="visionImagePath" type="text" placeholder="/path/to/image.png"></label>
                <div class="action-row">
                    <button id="visionSelectBtn">Select Image File</button>
                    <button id="visionActiveBtn">Use Active Editor File</button>
                </div>
                <div class="action-row">
                    <button id="visionAskBtn" class="primary">Ask About Image</button>
                    <button id="visionErrBtn">Review Screenshot Error</button>
                </div>
                <div id="visionPreviewCard" class="result-card" style="display:none; margin-top: 8px;">
                    <div class="eyebrow">Image Preview</div>
                    <div id="visionImagePreview" style="max-height: 180px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2); margin-top: 8px; border-radius: 6px;">
                        <span>No image loaded</span>
                    </div>
                </div>
                <div id="visionResult" class="result-card" style="display:none; margin-top: 8px;">
                    <div class="eyebrow">OCR & Caption Analysis</div>
                    <pre id="visionResultText"></pre>
                </div>
            </section>

            <section id="workspace-lab" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Experiment</div><h2>Prompt Lab</h2></div>
                    <button id="loadPairsBtn">Refresh Pairs</button>
                </div>
                <label>Saved Pair <select id="promptPairSelect"><option value="">Saved prompt pairs...</option></select></label>
                <label>Pair Name <input id="promptPairName" type="text" placeholder="name"></label>
                <div class="action-row">
                    <button id="savePairBtn">Save</button>
                    <button id="loadPairBtn">Load</button>
                    <button id="deletePairBtn" class="danger">Delete</button>
                </div>
                <label>System Prompt A <textarea id="labSysA" rows="3"></textarea></label>
                <label>System Prompt B <textarea id="labSysB" rows="3"></textarea></label>
                <label class="check"><input id="labLockSync" type="checkbox"> Lock system prompts while editing A</label>
                <label>Common User Message <textarea id="labUser" rows="3"></textarea></label>
                <div class="action-row">
                    <button id="tokenizeLabBtn">Preview BPE Tokens</button>
                </div>
                <div id="tokenPreview" class="token-preview">Tokenizer visualization requires Karl bridge tokenization support.</div>
                <button id="labRunBtn" class="primary">Run A/B Comparison</button>
                <div class="split" style="margin-top: 8px;">
                    <pre id="labOutputA" class="lab-output">Output A will stream here...</pre>
                    <pre id="labOutputB" class="lab-output">Output B will stream here...</pre>
                </div>
                <button id="diffBtn" style="margin-top: 8px;">Recompute Diff</button>
                <div id="labDiff" class="diff-view" style="margin-top: 8px;">Diff comparisons will render here.</div>
            </section>

            <section id="workspace-sandbox" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Educational Sandbox</div><h2>Vector Sandbox & Mini-GPT</h2></div>
                </div>
                
                <nav class="subtabs" aria-label="Sandbox Mode">
                    <button class="subtab active" data-subworkspace="vector-sandbox">Vector Sandbox</button>
                    <button class="subtab" data-subworkspace="minigpt-sandbox">Mini-GPT Telemetry</button>
                </nav>

                <div id="subworkspace-vector-sandbox" class="subworkspace active" style="margin-top: 8px;">
                    <div class="glow-panel" style="padding: 10px; margin-bottom: 10px;">
                        <div class="eyebrow">Corpus / Input Documents</div>
                        <p style="font-size: 8.5pt; color: var(--karl-muted); margin: 4px 0 8px 0;">
                            Enter one document per line. The vectorizer will construct a vocabulary, compute IDF scores, and generate TF-IDF representations.
                        </p>
                        <textarea id="sandboxDocs" rows="6" style="width: 100%; font-family: monospace; resize: vertical; border: 1px solid var(--karl-border); border-radius: 4px; padding: 6px; background: rgba(0,0,0,0.2); color: var(--karl-text);" placeholder="Document 1: Karl is a local multi-agent software engineering environment.&#10;Document 2: The system uses local models and runs entirely offline.&#10;Document 3: Multi-agent systems can perform complex autonomous workflows."></textarea>
                        
                        <div class="action-row" style="margin-top: 8px;">
                            <button id="fitVectorizerBtn" class="primary">Fit Vectorizer</button>
                        </div>
                    </div>

                    <div id="vectorizerOutput" class="result-card" style="display: none;">
                        <div class="eyebrow">Fitted Vocabulary & IDF Scores</div>
                        <div style="max-height: 150px; overflow-y: auto; border: 1px solid var(--karl-border); border-radius: 4px; padding: 6px; background: rgba(0,0,0,0.2); margin-top: 6px;">
                            <table id="vocabTable" style="width: 100%; border-collapse: collapse; font-family: monospace; font-size: 9pt;">
                                <thead>
                                    <tr style="border-bottom: 1px solid var(--karl-border); color: var(--karl-accent);">
                                        <th style="text-align: left; padding: 4px;">Word</th>
                                        <th style="text-align: right; padding: 4px;">DF</th>
                                        <th style="text-align: right; padding: 4px;">IDF</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                            </table>
                        </div>

                        <div class="eyebrow" style="margin-top: 12px;">Document TF-IDF Vectors</div>
                        <div id="tfidfVectors" style="max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 8.5pt; white-space: pre-wrap; padding: 6px; border: 1px solid var(--karl-border); border-radius: 4px; background: rgba(0,0,0,0.2); margin-top: 6px;"></div>
                    </div>
                </div>

                <div id="subworkspace-minigpt-sandbox" class="subworkspace" style="margin-top: 8px; display: none;">
                    <div class="settings-grid glow-panel" style="padding: 10px; margin-bottom: 10px;">
                        <label>Learning Rate <input id="miniLr" type="number" step="0.0001" min="0.0001" max="0.01" value="0.001" style="border: 1px solid var(--karl-border); border-radius: 4px; padding: 4px; background: rgba(0,0,0,0.2); color: var(--karl-text);"></label>
                        <label>Max Iterations <input id="miniIters" type="number" min="10" max="1000" step="10" value="100" style="border: 1px solid var(--karl-border); border-radius: 4px; padding: 4px; background: rgba(0,0,0,0.2); color: var(--karl-text);"></label>
                        <label>Batch Size <input id="miniBatchSize" type="number" min="2" max="64" step="2" value="16" style="border: 1px solid var(--karl-border); border-radius: 4px; padding: 4px; background: rgba(0,0,0,0.2); color: var(--karl-text);"></label>
                        
                        <div class="action-row" style="margin-top: 8px;">
                            <button id="startMiniGptBtn" class="primary">Start Mini-GPT Training</button>
                        </div>
                    </div>

                    <div id="miniGptTrainingStatus" class="result-card" style="display: none;">
                        <div class="eyebrow">Training Telemetry</div>
                        <div class="runtime-grid" style="grid-template-columns: repeat(2, 1fr); margin-top: 6px; display: grid; gap: 8px;">
                            <div class="metric" style="padding: 8px; border: 1px solid var(--karl-border); border-radius: 4px; background: rgba(0,0,0,0.1);">
                                <span style="font-size: 8pt; color: var(--karl-muted); display: block;">Current Iteration</span>
                                <strong id="miniCurrentStep" style="font-size: 14pt; color: var(--karl-accent);">--</strong>
                            </div>
                            <div class="metric" style="padding: 8px; border: 1px solid var(--karl-border); border-radius: 4px; background: rgba(0,0,0,0.1);">
                                <span style="font-size: 8pt; color: var(--karl-muted); display: block;">Current Loss</span>
                                <strong id="miniCurrentLoss" style="font-size: 14pt; color: var(--karl-accent);">--</strong>
                            </div>
                        </div>

                        <div class="eyebrow" style="margin-top: 12px;">Real-Time Loss Curve</div>
                        <div id="miniLossHistory" class="studio-log" style="height: 100px; overflow-y: auto; font-family: monospace; font-size: 8.5pt; margin-top: 6px; background: rgba(0,0,0,0.2); border: 1px solid var(--karl-border); border-radius: 4px; padding: 6px;"></div>

                        <div class="eyebrow" style="margin-top: 12px;">Real-Time Typewriter Generation</div>
                        <div id="miniTypewriterOutput" class="studio-log" style="height: 120px; overflow-y: auto; font-family: monospace; font-size: 9pt; white-space: pre-wrap; margin-top: 6px; background: rgba(0,0,0,0.2); border: 1px solid var(--karl-border); border-radius: 4px; padding: 6px;"></div>
                    </div>
                </div>
            </section>

            <section id="workspace-settings" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Settings</div><h2>Aesthetics & Configs</h2></div>
                </div>
                <nav class="subtabs" aria-label="Settings Mode">
                    <button class="subtab active" data-subworkspace="settings-look">Appearance</button>
                    <button class="subtab" data-subworkspace="settings-runtime">System Config</button>
                </nav>
                <div id="subworkspace-settings-look" class="subworkspace active" style="margin-top: 8px;">
                    <label>Theme Preset <select id="themeSelect"></select></label>
                    <div id="themeDescription" class="theme-description"></div>
                    <label>Custom Accent <input id="customAccent" type="color" value="#00c2ff"></label>
                    <label>Layout Mode <select id="layoutSelect"></select></label>
                    <div id="layoutDescription" class="theme-description"></div>
                    
                    <div class="look-options-grid glow-panel" style="padding: 10px; margin-top: 10px;">
                        <label class="check"><input id="syncVsCodeTheme" type="checkbox" checked> Sync with VS Code theme</label>
                        <label class="check"><input id="highContrastMode" type="checkbox"> High contrast layout</label>
                        <label class="check"><input id="reducedMotion" type="checkbox"> Reduced motion effects</label>
                        <label style="margin-top: 8px;">Animation Intensity
                            <input id="animationIntensity" type="range" min="0" max="100" value="100" style="margin-top: 4px;">
                        </label>
                    </div>

                    <div class="eyebrow" style="margin-top: 12px; margin-bottom: 6px;">Theme Catalog Previews</div>
                    <div id="themeGrid" class="theme-grid"></div>
                    
                    <button id="resetAppearanceBtn" style="margin-top:12px;">Reset Appearance</button>
                </div>
                <div id="subworkspace-settings-runtime" class="subworkspace" style="margin-top: 8px; display: none;">
                    <div class="section-head mini-head"><div><div class="eyebrow">Bridge</div><h2>Connection settings</h2></div></div>
                    <section class="connection-row glow-panel">
                        <label>Port <input id="bridgePort" type="number" min="1" max="65535" value="8080"></label>
                        <label class="check"><input id="autoConnect" type="checkbox" checked> Auto Connect</label>
                    </section>
                    <div class="action-row">
                        <button id="connectBtn" class="primary">Connect</button>
                        <button id="disconnectBtn">Disconnect</button>
                    </div>
                    
                    <div class="section-head mini-head" style="margin-top: 12px;"><div><div class="eyebrow">Hyperparams</div><h2>Generation Overrides</h2></div></div>
                    <div class="settings-grid glow-panel" style="padding: 10px;">
                        <label>Temperature <input id="karlTemp" type="number" step="0.05" min="0" max="2" value="0.7"></label>
                        <label>Top-P <input id="karlTopP" type="number" step="0.05" min="0" max="1" value="0.95"></label>
                        <label>Max Tokens <input id="karlMaxTok" type="number" min="64" max="32768" value="2048"></label>
                        <label>RAG Top-K <input id="kbTopK" type="number" min="1" max="25" value="5"></label>
                        <label>RAG Threshold <input id="kbThreshold" type="number" min="0" max="100" step="0.05" value="0"></label>
                        <label class="check"><input id="karlRag" type="checkbox" checked> Use RAG</label>
                        <label class="check"><input id="karlLoop" type="checkbox"> Agentic loop</label>
                    </div>

                    <div class="section-head mini-head" style="margin-top: 12px;"><div><div class="eyebrow">Models</div><h2>Available GGUFs</h2></div><button id="loadModelsBtn">Refresh</button></div>
                    <div id="modelList" class="model-list"></div>
                    <div class="section-head mini-head" style="margin-top: 12px;"><div><div class="eyebrow">Registry</div><h2>Download Tiers</h2></div></div>
                    <div id="downloadRegistry" class="model-list"></div>
                </div>
            </section>

            <section id="workspace-logs" class="workspace">
                <div class="section-head">
                    <div><div class="eyebrow">Logs</div><h2>Swarm Logs & Runtimes</h2></div>
                    <button id="clearLogsBtn">Clear logs</button>
                </div>
                <div class="action-row">
                    <button id="copyLogsBtn">Copy All logs</button>
                </div>
                <pre id="terminal">--- Swarm Logs ---</pre>
                <div class="eyebrow" style="margin-top:12px;">Fine-Tuning Loss/Logs</div>
                <pre id="trainingLog" class="studio-log">No training logs recorded.</pre>
                <div class="eyebrow" style="margin-top:12px;">Eval Harness Status</div>
                <pre id="evalLog" class="eval-log">No eval execution logs.</pre>
            </section>
        </main>
    </div>
    <script nonce="${nonce}" src="${themesUri}"></script>
    <script nonce="${nonce}" src="${stateUri}"></script>
    <script nonce="${nonce}" src="${renderUri}"></script>
    <script nonce="${nonce}" src="${socketUri}"></script>
    <script nonce="${nonce}" src="${jsUri}"></script>
</body>
</html>`;
    }
}

module.exports = {
    KarlSidebarProvider,
    sendActiveStateToWebview
};
