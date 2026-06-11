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
        input, textarea {
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
        input:focus, textarea:focus {
            outline: none;
            border-color: var(--vscode-focusBorder, #007fd4);
        }
        textarea {
            resize: vertical;
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
        #stopBtn {
            background: var(--vscode-errorForeground, #f48771);
            color: #ffffff;
        }
        #stopBtn:hover {
            background: #e06c55;
        }
        .status-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 14px;
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
            height: 280px;
            overflow-y: auto;
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            margin-top: 14px;
            white-space: pre-wrap;
            font-size: 10px;
            line-height: 1.4;
        }
        
        /* Custom scrollbar to look integration-native */
        #terminal::-webkit-scrollbar {
            width: 8px;
        }
        #terminal::-webkit-scrollbar-track {
            background: transparent;
        }
        #terminal::-webkit-scrollbar-thumb {
            background: var(--vscode-scrollbarSlider-background, rgba(121, 121, 121, 0.4));
            border-radius: 4px;
        }
        #terminal::-webkit-scrollbar-thumb:hover {
            background: var(--vscode-scrollbarSlider-hoverBackground, rgba(100, 100, 100, 0.7));
        }
    </style>
</head>
<body>
    <h3>Karl Agent Swarm</h3>
    <div class="form-group">
        <label for="objective">Objective</label>
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
        <button id="stopBtn" onclick="stopSwarm()">Stop</button>
    </div>

    <div class="status-container">
        <span class="status-label">Bridge Status:</span>
        <span id="status" class="status-badge status-disconnected">Offline</span>
    </div>

    <div id="terminal">--- Swarm Logs ---</div>

    <script>
        const vscode = acquireVsCodeApi();
        const port = ${port};
        const autoConnect = ${autoConnect};
        const defaultWorkspace = ${JSON.stringify(workspaceFolder)};

        let socket = null;
        let activeFile = '';
        let reconnectTimer = null;

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
                document.getElementById('objective').value = 
                    \`Target File: \${data.filepath}\\nObjective: \${data.objective}\\n\\nCode Selection:\\n\${data.code}\`;
                activeFile = data.filepath;
                connectAndRun();
            }
        });

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
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const method = data.method;
                const params = data.params;

                if (method === 'status_update') {
                    log(params.message);
                } else if (method === 'task_plan_created') {
                    log('[Plan] Swarm Architect created implementation plan.');
                } else if (method === 'file_edited') {
                    log('[Edit] Swarm Coder modified ' + params.filepath);
                    vscode.postMessage({
                        command: 'write_file',
                        filepath: activeFile || params.filepath,
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
            // Wait for connection to open before sending task
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
            
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 1,
                method: 'submit_task',
                params: {
                    objective: obj,
                    workspace_path: wspace,
                    test_command: cmd
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
    </script>
</body>
</html>
