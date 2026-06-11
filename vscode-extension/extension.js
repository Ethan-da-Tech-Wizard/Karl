const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

function activate(context) {
    console.log('Karl extension is active!');

    // 1. Sidebar View Provider Registration
    const sidebarProvider = new KarlSidebarProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('karl.sidebarView', sidebarProvider)
    );

    // 2. Fix Selection Context Menu Command
    let fixSelectionCmd = vscode.commands.registerCommand('karl.fixSelection', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('No active editor found.');
            return;
        }

        const selection = editor.selection;
        const text = editor.document.getText(selection);
        const filepath = editor.document.uri.fsPath;
        const folder = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : path.dirname(filepath);

        if (!text) {
            vscode.window.showWarningMessage('Please highlight some code first.');
            return;
        }

        const objective = await vscode.window.showInputBox({
            prompt: 'What should Karl do with the selected code?',
            placeHolder: 'e.g. Add validation, optimize database query...'
        });

        if (!objective) return;

        // Open sidebar if not already visible
        await vscode.commands.executeCommand('workbench.view.extension.karl-swarm');

        // Post the selection task to the sidebar webview
        sidebarProvider.postMessageToWebview({
            command: 'start_selection_task',
            data: {
                code: text,
                filepath: filepath,
                workspace_path: folder,
                objective: objective
            }
        });
    });

    // 3. Open Sidebar Panel Command
    let openSidebarCmd = vscode.commands.registerCommand('karl.openSidebar', () => {
        vscode.commands.executeCommand('workbench.view.extension.karl-swarm');
    });

    context.subscriptions.push(fixSelectionCmd, openSidebarCmd);
}

class KarlSidebarProvider {
    constructor(extensionUri) {
        this.extensionUri = extensionUri;
        this.webviewView = null;
    }

    resolveWebviewView(webviewView, context, token) {
        this.webviewView = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri]
        };

        const config = vscode.workspace.getConfiguration('karl');
        const port = config.get('port', 8080);
        const autoConnect = config.get('autoConnect', true);
        const workspaceFolder = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : '';

        webviewView.webview.html = this.getHtmlForWebview(webviewView.webview, port, autoConnect, workspaceFolder);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'write_file': {
                    const fullPath = message.filepath;
                    try {
                        // Backup original file for diff comparison
                        const backupPath = fullPath + '.original';
                        if (fs.existsSync(fullPath) && !fs.existsSync(backupPath)) {
                            fs.copyFileSync(fullPath, backupPath);
                        }

                        // Write new content
                        fs.writeFileSync(fullPath, message.content, 'utf-8');

                        // Show side-by-side diff in editor
                        const originalUri = vscode.Uri.file(backupPath);
                        const modifiedUri = vscode.Uri.file(fullPath);
                        vscode.commands.executeCommand(
                            'vscode.diff',
                            originalUri,
                            modifiedUri,
                            `Karl Changes: ${path.basename(fullPath)}`
                        );
                    } catch (err) {
                        vscode.window.showErrorMessage(`Failed to write file: ${err.message}`);
                    }
                    break;
                }
                case 'rollback_file': {
                    const fullPath = message.filepath;
                    const backupPath = fullPath + '.original';
                    try {
                        if (fs.existsSync(backupPath)) {
                            fs.copyFileSync(backupPath, fullPath);
                            fs.unlinkSync(backupPath);
                            vscode.window.showInformationMessage(`Successfully reverted changes for ${path.basename(fullPath)}`);
                        } else {
                            vscode.window.showWarningMessage('No backup file found to rollback.');
                        }
                    } catch (err) {
                        vscode.window.showErrorMessage(`Rollback failed: ${err.message}`);
                    }
                    break;
                }
                case 'accept_file': {
                    const fullPath = message.filepath;
                    const backupPath = fullPath + '.original';
                    try {
                        if (fs.existsSync(backupPath)) {
                            fs.unlinkSync(backupPath);
                            vscode.window.showInformationMessage(`Changes accepted for ${path.basename(fullPath)}`);
                        }
                    } catch (err) {
                        console.error(err);
                    }
                    break;
                }
                case 'show_message':
                    vscode.window.showInformationMessage(message.text);
                    break;
                case 'show_error':
                    vscode.window.showErrorMessage(message.text);
                    break;
            }
        });
    }

    postMessageToWebview(message) {
        if (this.webviewView) {
            this.webviewView.webview.postMessage(message);
        }
    }

    getHtmlForWebview(webview, port, autoConnect, workspaceFolder) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Karl</title>
    <style>
        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
            padding: 12px;
            color: var(--vscode-foreground);
            background-color: var(--vscode-sideBar-background);
            font-size: 11px;
            line-height: 1.4;
        }
        h3 {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            margin-top: 0;
            margin-bottom: 12px;
            color: var(--vscode-sideBarTitle-foreground, #cccccc);
            border-bottom: 1px solid var(--vscode-widget-border, #3c3c3c);
            padding-bottom: 6px;
        }

        /* Workspace Dropdown Styles */
        .workspace-header {
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--vscode-widget-border, #3c3c3c);
        }
        .workspace-select {
            width: 100%;
            background: var(--vscode-dropdown-background, #252526);
            color: var(--vscode-dropdown-foreground, #cccccc);
            border: 1px solid var(--vscode-dropdown-border, #3c3c3c);
            padding: 6px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
        }
        .workspace-select:focus {
            outline: none;
            border-color: var(--vscode-focusBorder, #007fd4);
        }

        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }

        .form-group {
            margin-bottom: 12px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 600;
            color: var(--vscode-descriptionForeground, #989898);
            text-transform: uppercase;
            font-size: 9px;
            letter-spacing: 0.5px;
        }
        input, textarea, select {
            width: 100%;
            box-sizing: border-box;
            background: var(--vscode-input-background, #252526);
            color: var(--vscode-input-foreground, #cccccc);
            border: 1px solid var(--vscode-input-border, #3c3c3c);
            padding: 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: inherit;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: var(--vscode-focusBorder, #007fd4);
        }
        textarea {
            resize: vertical;
        }
        .checkbox-row {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
        }
        .checkbox-row input[type="checkbox"] {
            width: auto;
            margin: 0;
        }

        /* Collapsible Settings Drawer */
        .drawer-trigger {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--vscode-editor-background, #1e1e1e);
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            padding: 6px 8px;
            cursor: pointer;
            font-size: 9px;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 12px;
            color: var(--vscode-descriptionForeground, #989898);
        }
        .drawer-content {
            display: none;
            padding: 10px;
            background: var(--vscode-editor-background, #1e1e1e);
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            margin-bottom: 12px;
        }
        .drawer-content.open {
            display: block;
        }

        .actions-row {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        button {
            flex: 1;
            background: var(--vscode-button-background, #0e639c);
            color: var(--vscode-button-foreground, #ffffff);
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            font-size: 11px;
            transition: background 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        button:hover {
            background: var(--vscode-button-hoverBackground, #1177bb);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-danger {
            background: var(--vscode-errorForeground, #f48771);
            color: #ffffff;
        }
        .btn-danger:hover {
            background: #e06c55;
        }
        .btn-success {
            background: #1d5a36;
            color: #ffffff;
        }
        .btn-success:hover {
            background: #277c4a;
        }

        /* Transaction Banner */
        .transaction-banner {
            display: none;
            background: #2c2514;
            border: 1px solid #7a5e20;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 12px;
        }
        .transaction-banner.active {
            display: block;
        }
        .banner-title {
            font-weight: 700;
            color: #f1cf7b;
            margin-bottom: 6px;
            font-size: 10px;
            text-transform: uppercase;
        }

        /* Chat view styles */
        #chat-messages {
            height: 280px;
            overflow-y: auto;
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            padding: 8px;
            margin-bottom: 10px;
            font-size: 11px;
        }
        .message {
            margin-bottom: 10px;
            padding: 6px 8px;
            border-radius: 4px;
            max-width: 90%;
            word-wrap: break-word;
        }
        .message.user {
            background: #1a2f42;
            color: #c5e1f5;
            margin-left: auto;
            border-left: 2px solid #00C2FF;
        }
        .message.assistant {
            background: #252526;
            color: #cccccc;
            margin-right: auto;
            border-left: 2px solid #2DD4A0;
        }
        .message-role {
            font-weight: 700;
            font-size: 9px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        /* Live Introspection Box */
        .introspection-container {
            display: none;
            background: #0f1c24;
            border: 1px solid #144b6b;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 10px;
        }
        .introspection-container.active {
            display: block;
        }
        .introspection-title {
            font-weight: 700;
            color: #00C2FF;
            font-size: 9px;
            text-transform: uppercase;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
        }
        .introspection-stream {
            font-family: var(--vscode-editor-font-family, "Courier New", monospace);
            font-size: 10px;
            color: #98d8f5;
            white-space: pre-wrap;
            max-height: 120px;
            overflow-y: auto;
        }

        /* Prompt Lab Styling */
        .lab-output {
            font-family: var(--vscode-editor-font-family, "Courier New", monospace);
            font-size: 10px;
            background: var(--vscode-editor-background, #1e1e1e);
            color: var(--vscode-editor-foreground, #cccccc);
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            padding: 8px;
            height: 110px;
            overflow-y: auto;
            white-space: pre-wrap;
            margin-bottom: 8px;
        }
        .lab-diff-container {
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            padding: 8px;
            height: 140px;
            overflow-y: auto;
        }

        /* Codex Library Styling */
        .codex-list {
            max-height: 140px;
            overflow-y: auto;
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            margin-bottom: 10px;
        }
        .codex-item {
            padding: 6px 8px;
            cursor: pointer;
            border-bottom: 1px solid var(--vscode-widget-border, #3c3c3c);
            transition: background 0.15s ease;
        }
        .codex-item:hover {
            background: var(--vscode-list-hoverBackground, #2a2d2e);
        }
        .codex-item.active {
            background: var(--vscode-list-activeSelectionBackground, #094771);
            color: var(--vscode-list-activeSelectionForeground, #ffffff);
            font-weight: 600;
        }
        .codex-viewer {
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            padding: 8px;
            height: 280px;
            overflow-y: auto;
        }

        .status-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 12px;
            padding: 6px 8px;
            background: var(--vscode-editor-background, #1e1e1e);
            border-radius: 4px;
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
        }
        .status-label {
            color: var(--vscode-descriptionForeground, #989898);
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 9px;
            text-transform: uppercase;
        }
        .status-disconnected { background: #5a1d1d; color: #f17b7b; }
        .status-connected { background: #1d5a36; color: #7bf19f; }
        .status-running { background: #5a481d; color: #f1cf7b; }

        #terminal {
            background: var(--vscode-terminal-background, #1e1e1e);
            color: var(--vscode-terminal-foreground, #cccccc);
            font-family: var(--vscode-editor-font-family, "Courier New", monospace);
            padding: 10px;
            border-radius: 4px;
            height: 180px;
            overflow-y: auto;
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            margin-top: 12px;
            white-space: pre-wrap;
            font-size: 10px;
            line-height: 1.4;
        }

        /* Custom scrollbars */
        #chat-messages::-webkit-scrollbar, #terminal::-webkit-scrollbar, .introspection-stream::-webkit-scrollbar, .lab-output::-webkit-scrollbar, .lab-diff-container::-webkit-scrollbar, .codex-list::-webkit-scrollbar, .codex-viewer::-webkit-scrollbar {
            width: 6px;
        }
        #chat-messages::-webkit-scrollbar-track, #terminal::-webkit-scrollbar-track, .introspection-stream::-webkit-scrollbar-track, .lab-output::-webkit-scrollbar-track, .lab-diff-container::-webkit-scrollbar-track, .codex-list::-webkit-scrollbar-track, .codex-viewer::-webkit-scrollbar-track {
            background: transparent;
        }
        #chat-messages::-webkit-scrollbar-thumb, #terminal::-webkit-scrollbar-thumb, .introspection-stream::-webkit-scrollbar-thumb, .lab-output::-webkit-scrollbar-thumb, .lab-diff-container::-webkit-scrollbar-thumb, .codex-list::-webkit-scrollbar-thumb, .codex-viewer::-webkit-scrollbar-thumb {
            background: var(--vscode-scrollbarSlider-background, rgba(121, 121, 121, 0.4));
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h3>Karl Agent Swarm</h3>

    <!-- Workspace Selector Header -->
    <div class="workspace-header">
        <label for="workspace-select">Active Workspace</label>
        <select class="workspace-select" id="workspace-select" onchange="switchWorkspace(this.value)">
            <option value="swarm">🐝 Swarm Workspace</option>
            <option value="chat">💬 Chat Workspace</option>
            <option value="lab">🧪 Prompt Lab</option>
            <option value="codex">📚 Codex Library</option>
        </select>
    </div>

    <!-- Parameter Config Drawer Trigger -->
    <div class="drawer-trigger" onclick="toggleSettingsDrawer()">
        <span>⚙ Settings Overrides</span>
        <span id="drawer-arrow">▼</span>
    </div>
    <!-- Parameter Config Drawer Content -->
    <div class="drawer-content" id="settingsDrawer">
        <div class="form-group">
            <label for="karl-temp">Temperature (0.0 - 2.0)</label>
            <input id="karl-temp" type="number" step="0.05" min="0" max="2" value="0.7">
        </div>
        <div class="form-group">
            <label for="karl-topp">Top-P (0.0 - 1.0)</label>
            <input id="karl-topp" type="number" step="0.05" min="0" max="1" value="0.95">
        </div>
        <div class="form-group">
            <label for="karl-maxtok">Max Tokens</label>
            <input id="karl-maxtok" type="number" min="64" max="32768" value="2048">
        </div>
        <div class="checkbox-row">
            <input id="karl-rag" type="checkbox" checked>
            <label for="karl-rag" style="display:inline; text-transform:none; font-size:11px;">Enable RAG Context</label>
        </div>
        <div class="checkbox-row">
            <input id="karl-loop" type="checkbox">
            <label for="karl-loop" style="display:inline; text-transform:none; font-size:11px;">Enable Agentic loop</label>
        </div>
    </div>

    <!-- Workspace 1: Swarm Content -->
    <div class="tab-content active" id="contentSwarm">
        <!-- Transaction banner for edited files -->
        <div class="transaction-banner" id="diffBanner">
            <div class="banner-title" id="bannerFileTitle">Swarm Edited File</div>
            <div class="actions-row">
                <button class="btn-success" onclick="acceptSwarmChanges()">Accept</button>
                <button class="btn-danger" onclick="rollbackSwarmChanges()">Rollback</button>
            </div>
        </div>

        <div class="form-group">
            <label for="objective">Swarm Objective</label>
            <textarea id="objective" rows="4" placeholder="Describe the task for Karl's multi-agent swarm..."></textarea>
        </div>
        <div class="form-group">
            <label for="workspace">Workspace Path</label>
            <input id="workspace" type="text" placeholder="/path/to/project">
        </div>
        <div class="form-group">
            <label for="testCmd">Verification Test Command</label>
            <input id="testCmd" type="text" value="python run_tests.py">
        </div>

        <div class="actions-row">
            <button id="runBtn" onclick="runSwarm()">▶ Deploy Swarm</button>
            <button id="stopBtn" onclick="stopSwarm()" class="btn-danger">Stop</button>
        </div>

        <div id="terminal">--- Swarm Logs ---</div>
    </div>

    <!-- Workspace 2: Chat Content -->
    <div class="tab-content" id="contentChat">
        <!-- Live Introspection Thought Stream -->
        <div class="introspection-container" id="introspectionBox">
            <div class="introspection-title">Live Introspection thoughts</div>
            <div class="introspection-stream" id="introspectionThoughts"></div>
        </div>

        <div id="chat-messages">
            <div class="message assistant">
                <div class="message-role">Assistant</div>
                Hello, I am Karl. How can I assist you with your codebase today?
            </div>
        </div>

        <div class="form-group">
            <input id="chatInput" type="text" placeholder="Type a message to Karl..." onkeydown="if(event.key === 'Enter') sendChatMessage()">
        </div>
        <button id="chatSendBtn" onclick="sendChatMessage()">Send Message</button>
    </div>

    <!-- Workspace 3: Prompt Lab Content -->
    <div class="tab-content" id="contentLab">
        <div class="form-group">
            <label for="labSysA">System Prompt A</label>
            <textarea id="labSysA" rows="2" placeholder="e.g. You are a succinct helper."></textarea>
        </div>
        <div class="form-group">
            <label for="labSysB">System Prompt B</label>
            <textarea id="labSysB" rows="2" placeholder="e.g. You are a verbose helper."></textarea>
        </div>
        <div class="form-group">
            <label for="labUser">Common User Message</label>
            <textarea id="labUser" rows="2" placeholder="Prompt input for A and B..."></textarea>
        </div>
        <button id="labRunBtn" onclick="runLab()">▶ Run A/B Comparison</button>

        <div class="form-group" style="margin-top:12px;">
            <label>Output A</label>
            <div class="lab-output" id="labOutputA">Output A will stream here...</div>
        </div>
        <div class="form-group">
            <label>Output B</label>
            <div class="lab-output" id="labOutputB">Output B will stream here...</div>
        </div>
        <div class="form-group">
            <label>Difference View (A vs B)</label>
            <div class="lab-diff-container" id="labDiff">Diff comparisons will render here after runs complete...</div>
        </div>
    </div>

    <!-- Workspace 4: Codex Library Content -->
    <div class="tab-content" id="contentCodex">
        <div class="form-group">
            <input type="text" id="codexSearch" placeholder="Search references..." oninput="filterCodex()">
        </div>
        <label>Documentation Chapters</label>
        <div class="codex-list" id="codexList">
            <div style="padding:8px; color:var(--vscode-descriptionForeground)">Loading documentation library...</div>
        </div>
        <label>Viewer</label>
        <div class="codex-viewer" id="codexViewer">
            Select a chapter guide above to read reference specifications locally.
        </div>
    </div>

    <!-- Status indicator row -->
    <div class="status-container">
        <span class="status-label">Bridge Status:</span>
        <span id="status" class="status-badge status-disconnected">Offline</span>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const port = ${port};
        const autoConnect = ${autoConnect};
        const defaultWorkspace = ${JSON.stringify(workspaceFolder)};

        let socket = null;
        let activeFile = '';
        let reconnectTimer = null;
        let activeEditPath = '';
        let chatFinished = true;

        // Prompt Lab tracking variables
        let labOutputA = '';
        let labOutputB = '';
        let labRunning = false;
        let currentLabTarget = '';

        // Auto-populate default fields on load
        window.addEventListener('DOMContentLoaded', () => {
            if (defaultWorkspace) {
                document.getElementById('workspace').value = defaultWorkspace;
            }
            if (autoConnect) {
                connect();
            }
        });

        // Handle messages from host extension
        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'start_selection_task') {
                const data = message.data;
                document.getElementById('workspace').value = data.workspace_path;
                document.getElementById('workspace-select').value = 'swarm';
                switchWorkspace('swarm');
                document.getElementById('objective').value =
                    \`Target File: \${data.filepath}\\nObjective: \${data.objective}\\n\\nCode Selection:\\n\${data.code}\`;
                activeFile = data.filepath;
                connectAndRun();
            }
        });

        function switchWorkspace(wsId) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            if (wsId === 'swarm') {
                document.getElementById('contentSwarm').classList.add('active');
            } else if (wsId === 'chat') {
                document.getElementById('contentChat').classList.add('active');
            } else if (wsId === 'lab') {
                document.getElementById('contentLab').classList.add('active');
            } else if (wsId === 'codex') {
                document.getElementById('contentCodex').classList.add('active');
                loadCodexTopics();
            }
        }

        function toggleSettingsDrawer() {
            const drawer = document.getElementById('settingsDrawer');
            const arrow = document.getElementById('drawer-arrow');
            drawer.classList.toggle('open');
            arrow.innerText = drawer.classList.contains('open') ? '▲' : '▼';
        }

        function log(msg) {
            const term = document.getElementById('terminal');
            term.innerText += '\\n' + msg;
            term.scrollTop = term.scrollHeight;
        }

        function setStatus(state, text) {
            const el = document.getElementById('status');
            el.className = 'status-badge ' + state;
            el.innerText = text;
        }

        function connect() {
            if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
                return;
            }

            setStatus('status-running', 'Connecting...');
            socket = new WebSocket('ws://localhost:' + port);

            socket.onopen = () => {
                setStatus('status-connected', 'Connected');
                log('[WebSocket] Connection established on port ' + port + '.');
                if (reconnectTimer) {
                    clearInterval(reconnectTimer);
                    reconnectTimer = null;
                }

                // If Codex list is empty and currently in codex tab, load topics
                if (document.getElementById('workspace-select').value === 'codex') {
                    loadCodexTopics();
                }
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const method = data.method;
                const params = data.params;

                // Handle RPC response results
                if (data.result) {
                    if (data.id === 12) { // diff result
                        document.getElementById('labDiff').innerHTML = data.result.diff_html;
                        labRunning = false;
                        document.getElementById('labRunBtn').disabled = false;
                        log('[PromptLab] Diff rendering completed.');
                    } else if (data.id === 20) { // list topics
                        renderCodexTopics(data.result.topics);
                    } else if (data.id === 21) { // get topic content
                        document.getElementById('codexViewer').innerHTML = data.result.content;
                    }
                    return;
                }

                // Handle Swarm notifications
                if (method === 'status_update') {
                    log(params.message);
                } else if (method === 'task_plan_created') {
                    log('[Plan] Swarm Architect created implementation plan.');
                } else if (method === 'file_edited') {
                    log('[Edit] Swarm Coder modified ' + params.filepath);
                    activeEditPath = params.filepath;

                    const filename = params.filepath.split('/').pop().split('\\\\').pop();
                    document.getElementById('bannerFileTitle').innerText = 'Swarm Edited: ' + filename;
                    document.getElementById('diffBanner').classList.add('active');

                    vscode.postMessage({
                        command: 'write_file',
                        filepath: params.filepath,
                        content: params.content
                    });
                } else if (method === 'test_result') {
                    const status = params.passed ? 'PASSED' : 'FAILED';
                    log('[Test] Execution result: ' + status);
                    if (!params.passed) {
                        log('[Test] Output/Trace:\n' + params.error_trace);
                    }
                } else if (method === 'finished_swarm') {
                    setStatus('status-connected', 'Connected');
                    const outcome = params.success ? 'SUCCESS' : 'FAILURE';
                    log('[Swarm] Swarm finished: ' + outcome);
                    log('[Summary] ' + params.summary);
                }

                // Chat / Prompt Lab streaming notifications
                else if (method === 'chat_thought_token') {
                    if (!labRunning) {
                        const box = document.getElementById('introspectionBox');
                        const stream = document.getElementById('introspectionThoughts');
                        box.classList.add('active');
                        stream.innerText += params.token;
                        stream.scrollTop = stream.scrollHeight;
                    }
                } else if (method === 'chat_response_token') {
                    if (labRunning) {
                        if (currentLabTarget === 'A') {
                            labOutputA += params.token;
                            document.getElementById('labOutputA').innerText = labOutputA;
                            document.getElementById('labOutputA').scrollTop = document.getElementById('labOutputA').scrollHeight;
                        } else if (currentLabTarget === 'B') {
                            labOutputB += params.token;
                            document.getElementById('labOutputB').innerText = labOutputB;
                            document.getElementById('labOutputB').scrollTop = document.getElementById('labOutputB').scrollHeight;
                        }
                    } else {
                        appendChatToken(params.token);
                    }
                } else if (method === 'chat_finished') {
                    if (labRunning) {
                        if (currentLabTarget === 'A') {
                            // Column A complete, launch Column B
                            currentLabTarget = 'B';
                            document.getElementById('labOutputB').innerText = 'Generating output B...';

                            const sysB = document.getElementById('labSysB').value;
                            const userMsg = document.getElementById('labUser').value;
                            const temp = parseFloat(document.getElementById('karl-temp').value);
                            const topp = parseFloat(document.getElementById('karl-topp').value);
                            const maxtok = parseInt(document.getElementById('karl-maxtok').value);
                            const rag = document.getElementById('karl-rag').checked;
                            const loop = document.getElementById('karl-loop').checked;

                            sendLabMessage('B', sysB, userMsg, temp, topp, maxtok, rag, loop);
                        } else if (currentLabTarget === 'B') {
                            // Column B complete, request A/B diff
                            document.getElementById('labDiff').innerHTML = '<div style="color:var(--vscode-descriptionForeground)">Computing difference...</div>';
                            socket.send(JSON.stringify({
                                jsonrpc: '2.0',
                                id: 12,
                                method: 'compute_diff',
                                params: {
                                    text_a: labOutputA,
                                    text_b: labOutputB
                                }
                            }));
                        }
                    } else {
                        chatFinished = true;
                        document.getElementById('chatSendBtn').disabled = false;
                    }
                }
            };

            socket.onerror = (err) => {
                setStatus('status-disconnected', 'Error');
            };

            socket.onclose = () => {
                setStatus('status-disconnected', 'Offline');
                if (!reconnectTimer && autoConnect) {
                    log('[WebSocket] Connection lost. Retrying in 5 seconds...');
                    reconnectTimer = setInterval(connect, 5000);
                }
            };
        }

        function connectAndRun() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                runSwarm();
                return;
            }
            connect();
            const checkInterval = setInterval(() => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    clearInterval(checkInterval);
                    runSwarm();
                }
            }, 100);
        }

        function runSwarm() {
            const obj = document.getElementById('objective').value;
            const wspace = document.getElementById('workspace').value;
            const cmd = document.getElementById('testCmd').value;

            if (!obj || !wspace) {
                vscode.postMessage({ command: 'show_error', text: 'Objective and Workspace are required.' });
                return;
            }

            if (!socket || socket.readyState !== WebSocket.OPEN) {
                connectAndRun();
                return;
            }

            setStatus('status-running', 'Active');
            document.getElementById('terminal').innerText = '--- Swarm Logs ---';
            log('[Swarm] Deploying agents on codebase...');

            // Extract settings overrides
            const temp = parseFloat(document.getElementById('karl-temp').value);
            const topp = parseFloat(document.getElementById('karl-topp').value);
            const maxtok = parseInt(document.getElementById('karl-maxtok').value);
            const rag = document.getElementById('karl-rag').checked;
            const loop = document.getElementById('karl-loop').checked;

            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 1,
                method: 'submit_task',
                params: {
                    objective: obj,
                    workspace_path: wspace,
                    test_command: cmd,
                    hyperparams: {
                        temperature: temp,
                        top_p: topp,
                        max_tokens: maxtok,
                        rag_enabled: rag,
                        agentic_loop_enabled: loop
                    }
                }
            }));
        }

        function stopSwarm() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    jsonrpc: '2.0',
                    id: 2,
                    method: 'stop_task'
                }));
            }
        }

        function acceptSwarmChanges() {
            if (activeEditPath) {
                vscode.postMessage({
                    command: 'accept_file',
                    filepath: activeEditPath
                });
                document.getElementById('diffBanner').classList.remove('active');
                activeEditPath = '';
            }
        }

        function rollbackSwarmChanges() {
            if (activeEditPath) {
                vscode.postMessage({
                    command: 'rollback_file',
                    filepath: activeEditPath
                });
                document.getElementById('diffBanner').classList.remove('active');
                activeEditPath = '';
            }
        }

        // Chat View Implementation
        function sendChatMessage() {
            const inputEl = document.getElementById('chatInput');
            const text = inputEl.value.trim();
            if (!text || !chatFinished) return;

            if (!socket || socket.readyState !== WebSocket.OPEN) {
                vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected. Check bridge status.' });
                return;
            }

            // Append user bubble
            appendMessageBubble('user', text);
            inputEl.value = '';

            // Reset thoughts pane
            document.getElementById('introspectionThoughts').innerText = '';
            document.getElementById('introspectionBox').classList.remove('active');

            // Set state to generating
            chatFinished = false;
            document.getElementById('chatSendBtn').disabled = true;

            // Prepare placeholder assistant bubble
            appendMessageBubble('assistant', '');

            // Get settings overrides
            const temp = parseFloat(document.getElementById('karl-temp').value);
            const topp = parseFloat(document.getElementById('karl-topp').value);
            const maxtok = parseInt(document.getElementById('karl-maxtok').value);
            const rag = document.getElementById('karl-rag').checked;
            const loop = document.getElementById('karl-loop').checked;
            const wspace = document.getElementById('workspace').value;

            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 3,
                method: 'submit_chat',
                params: {
                    message: text,
                    workspace_path: wspace,
                    hyperparams: {
                        temperature: temp,
                        top_p: topp,
                        max_tokens: maxtok,
                        rag_enabled: rag,
                        agentic_loop_enabled: loop
                    }
                }
            }));
        }

        function appendMessageBubble(role, text) {
            const container = document.getElementById('chat-messages');
            const msgEl = document.createElement('div');
            msgEl.className = 'message ' + role;

            const roleEl = document.createElement('div');
            roleEl.className = 'message-role';
            roleEl.innerText = role === 'user' ? 'User' : 'Karl';

            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.innerText = text;

            msgEl.appendChild(roleEl);
            msgEl.appendChild(contentEl);
            container.appendChild(msgEl);
            container.scrollTop = container.scrollHeight;
        }

        function appendChatToken(token) {
            const container = document.getElementById('chat-messages');
            const lastMsg = container.querySelector('.message.assistant:last-child .message-content');
            if (lastMsg) {
                lastMsg.innerText += token;
                container.scrollTop = container.scrollHeight;
            }
        }

        // Prompt Lab Implementation
        function runLab() {
            if (labRunning) return;
            const sysA = document.getElementById('labSysA').value;
            const sysB = document.getElementById('labSysB').value;
            const userMsg = document.getElementById('labUser').value;

            if (!userMsg) {
                vscode.postMessage({ command: 'show_error', text: 'User message is required.' });
                return;
            }

            if (!socket || socket.readyState !== WebSocket.OPEN) {
                vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected.' });
                return;
            }

            labRunning = true;
            document.getElementById('labRunBtn').disabled = true;

            document.getElementById('labOutputA').innerText = 'Generating output A...';
            document.getElementById('labOutputB').innerText = 'Waiting...';
            document.getElementById('labDiff').innerText = 'Waiting for runs to complete...';

            labOutputA = '';
            labOutputB = '';

            const temp = parseFloat(document.getElementById('karl-temp').value);
            const topp = parseFloat(document.getElementById('karl-topp').value);
            const maxtok = parseInt(document.getElementById('karl-maxtok').value);
            const rag = document.getElementById('karl-rag').checked;
            const loop = document.getElementById('karl-loop').checked;

            // Start sequential execution with Column A
            sendLabMessage('A', sysA, userMsg, temp, topp, maxtok, rag, loop);
        }

        function sendLabMessage(target, systemPrompt, userMsg, temp, topp, maxtok, rag, loop) {
            currentLabTarget = target;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 10 + (target === 'A' ? 0 : 1),
                method: 'submit_chat',
                params: {
                    message: userMsg,
                    hyperparams: {
                        temperature: temp,
                        top_p: topp,
                        max_tokens: maxtok,
                        rag_enabled: rag,
                        agentic_loop_enabled: loop,
                        system_prompt: systemPrompt
                    }
                }
            }));
        }

        // Codex Library Implementation
        function loadCodexTopics() {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 20,
                method: 'list_codex_topics'
            }));
        }

        function renderCodexTopics(topics) {
            const container = document.getElementById('codexList');
            container.innerHTML = '';
            if (!topics || topics.length === 0) {
                container.innerHTML = '<div style="padding:8px; color:var(--vscode-descriptionForeground)">No chapters loaded.</div>';
                return;
            }
            topics.forEach(t => {
                const el = document.createElement('div');
                el.className = 'codex-item';
                el.innerText = t;
                el.onclick = () => selectCodexTopic(t, el);
                container.appendChild(el);
            });
        }

        function selectCodexTopic(topic, element) {
            document.querySelectorAll('.codex-item').forEach(item => item.classList.remove('active'));
            element.classList.add('active');

            document.getElementById('codexViewer').innerHTML = '<div style="color:var(--vscode-descriptionForeground); padding:8px;">Loading reference...</div>';

            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 21,
                method: 'get_codex_content',
                params: { topic: topic }
            }));
        }

        function filterCodex() {
            const q = document.getElementById('codexSearch').value.toLowerCase();
            const items = document.querySelectorAll('.codex-item');
            items.forEach(item => {
                const visible = item.innerText.toLowerCase().includes(q);
                item.style.display = visible ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>`;
    }
}

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = {
    activate,
    deactivate
};
