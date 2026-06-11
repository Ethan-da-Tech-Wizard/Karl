const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

function activate(context) {
    console.log('Karl SWE Agent extension is active!');

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

        webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

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

    getHtmlForWebview(webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Karl Swarm</title>
    <style>
        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
            padding: 10px;
            color: var(--vscode-foreground);
            background-color: var(--vscode-sideBar-background);
            font-size: 11px;
        }
        h3 {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            border-bottom: 1px solid var(--vscode-widget-border, #3c3c3c);
            padding-bottom: 4px;
        }
        .form-group {
            margin-bottom: 10px;
        }
        label {
            display: block;
            margin-bottom: 4px;
            font-weight: bold;
            color: var(--vscode-descriptionForeground);
        }
        input, textarea, button {
            width: 100%;
            box-sizing: border-box;
            background: var(--vscode-input-background, #252526);
            color: var(--vscode-input-foreground, #cccccc);
            border: 1px solid var(--vscode-input-border, #3c3c3c);
            padding: 6px;
            border-radius: 3px;
            font-size: 11px;
            font-family: inherit;
        }
        button {
            background: var(--vscode-button-background, #0e639c);
            color: var(--vscode-button-foreground, #ffffff);
            border: none;
            cursor: pointer;
            font-weight: bold;
            margin-top: 6px;
        }
        button:hover {
            background: var(--vscode-button-hoverBackground, #1177bb);
        }
        #terminal {
            background: #1e1e1e;
            color: #d4d4d4;
            font-family: var(--vscode-editor-font-family, "Courier New", monospace);
            padding: 8px;
            border-radius: 4px;
            height: 250px;
            overflow-y: auto;
            border: 1px solid #3c3c3c;
            margin-top: 10px;
            white-space: pre-wrap;
            font-size: 10px;
        }
        .status-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
            font-size: 9px;
            margin-top: 4px;
        }
        .status-disconnected { background: #5a1d1d; color: #f17b7b; }
        .status-connected { background: #1d5a36; color: #7bf19f; }
        .status-running { background: #5a481d; color: #f1cf7b; }
    </style>
</head>
<body>
    <h3>Karl Agent Swarm</h3>
    <div class="form-group">
        <label>Objective</label>
        <textarea id="objective" rows="3" placeholder="Enter task for the swarm..."></textarea>
    </div>
    <div class="form-group">
        <label>Workspace Path</label>
        <input id="workspace" type="text" placeholder="/path/to/project">
    </div>
    <div class="form-group">
        <label>Test Command</label>
        <input id="testCmd" type="text" value="python run_tests.py">
    </div>
    <div style="display:flex; gap:6px;">
        <button id="runBtn" onclick="runSwarm()">▶ Deploy Swarm</button>
        <button id="stopBtn" onclick="stopSwarm()" style="background:#5a1d1d;">Stop</button>
    </div>

    <div style="margin-top:10px;">
        <span>Status:</span>
        <span id="status" class="status-badge status-disconnected">Disconnected</span>
    </div>

    <div id="terminal">--- Swarm Logs ---</div>

    <script>
        const vscode = acquireVsCodeApi();
        let socket = null;
        let activeFile = '';

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

        function connectAndRun() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                runSwarm();
                return;
            }

            setStatus('status-running', 'Connecting...');
            socket = new WebSocket('ws://localhost:8080');

            socket.onopen = () => {
                setStatus('status-connected', 'Connected');
                log('[WebSocket] Connection established.');
                runSwarm();
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const method = data.method;
                const params = data.params;

                if (method === 'status_update') {
                    log(params.message);
                } else if (method === 'task_plan_created') {
                    log('[Plan] Architect created plan: ' + JSON.stringify(params.plan, null, 2));
                } else if (method === 'file_edited') {
                    log('[Edit] Coder modified ' + params.filepath);
                    // Ask host extension to save modified code and show diff
                    vscode.postMessage({
                        command: 'write_file',
                        filepath: activeFile || params.filepath,
                        content: params.content
                    });
                } else if (method === 'test_result') {
                    const status = params.passed ? 'PASSED' : 'FAILED';
                    log('[Test] Runs result: ' + status);
                    if (!params.passed) {
                        log('[Test] Error: ' + params.error_trace);
                    }
                } else if (method === 'finished_swarm') {
                    setStatus('status-connected', 'Connected');
                    const outcome = params.success ? 'SUCCESS' : 'FAILURE';
                    log('[Swarm] Run finished with: ' + outcome);
                    log('[Summary] ' + params.summary);
                }
            };

            socket.onerror = (err) => {
                setStatus('status-disconnected', 'Error');
                log('[WebSocket] Connection error.');
            };

            socket.onclose = () => {
                setStatus('status-disconnected', 'Disconnected');
                log('[WebSocket] Connection closed.');
            };
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

            setStatus('status-running', 'Swarm Active');
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
</html>`;
    }
}

function deactivate() {
    console.log('Karl SWE Agent extension deactivated.');
}

module.exports = {
    activate,
    deactivate
};
