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
                case 'choose_kb_file': {
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
                        this.postMessageToWebview({
                            command: 'set_kb_path',
                            path: files[0].fsPath
                        });
                    }
                    break;
                }
                case 'choose_kb_folder': {
                    const folders = await vscode.window.showOpenDialog({
                        canSelectFiles: false,
                        canSelectFolders: true,
                        canSelectMany: false,
                        title: 'Select a folder to ingest into Karl Knowledge Base'
                    });
                    if (folders && folders[0]) {
                        this.postMessageToWebview({
                            command: 'set_kb_path',
                            path: folders[0].fsPath
                        });
                    }
                    break;
                }
                case 'use_active_file_for_kb': {
                    const editor = vscode.window.activeTextEditor;
                    if (!editor) {
                        vscode.window.showWarningMessage('No active editor found.');
                        return;
                    }
                    this.postMessageToWebview({
                        command: 'set_kb_path',
                        path: editor.document.uri.fsPath
                    });
                    break;
                }
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

        /* Runtime status panel */
        .runtime-panel {
            background: var(--vscode-editor-background, #1e1e1e);
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 12px;
        }
        .runtime-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }
        .runtime-cell {
            min-width: 0;
        }
        .runtime-label {
            display: block;
            color: var(--vscode-descriptionForeground, #989898);
            font-size: 8px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        .runtime-value {
            display: block;
            color: var(--vscode-foreground, #cccccc);
            font-size: 10px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .runtime-value.good {
            color: #7bf19f;
        }
        .runtime-value.warn {
            color: #f1cf7b;
        }

        /* Model registry */
        .model-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .model-card {
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            padding: 8px;
        }
        .model-card.active {
            border-color: #2DD4A0;
            background: #102018;
        }
        .model-title {
            color: var(--vscode-foreground, #cccccc);
            font-size: 10px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .model-meta {
            color: var(--vscode-descriptionForeground, #989898);
            font-size: 9px;
            line-height: 1.4;
            margin-bottom: 8px;
        }
        .model-actions {
            display: flex;
            gap: 8px;
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
        .prompt-pair-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 8px;
            margin-bottom: 8px;
        }
        .prompt-pair-actions {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
            margin-bottom: 10px;
        }
        .prompt-pair-actions button {
            padding: 6px 8px;
            font-size: 10px;
        }

        /* Knowledge Base Styling */
        .kb-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }
        .kb-stat-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
            margin-bottom: 10px;
        }
        .kb-stat {
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            padding: 8px;
            min-width: 0;
        }
        .kb-stat-value {
            display: block;
            font-size: 13px;
            font-weight: 700;
            color: #7bf19f;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .kb-stat-label {
            display: block;
            color: var(--vscode-descriptionForeground, #989898);
            font-size: 8px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-top: 2px;
        }
        .kb-source-list {
            max-height: 120px;
            overflow-y: auto;
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            margin-bottom: 10px;
        }
        .kb-source-item {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 8px;
            padding: 6px 8px;
            border-bottom: 1px solid var(--vscode-widget-border, #3c3c3c);
            cursor: pointer;
        }
        .kb-source-item:hover {
            background: var(--vscode-list-hoverBackground, #2a2d2e);
        }
        .kb-source-item.active {
            background: var(--vscode-list-activeSelectionBackground, #094771);
            color: var(--vscode-list-activeSelectionForeground, #ffffff);
            font-weight: 600;
        }
        .kb-source-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .kb-source-count {
            color: var(--vscode-descriptionForeground, #989898);
            font-size: 9px;
        }
        .kb-result-list {
            max-height: 360px;
            overflow-y: auto;
        }
        .kb-result-card {
            border: 1px solid var(--vscode-widget-border, #3c3c3c);
            border-radius: 4px;
            background: var(--vscode-editor-background, #1e1e1e);
            padding: 8px;
            margin-bottom: 8px;
        }
        .kb-result-meta {
            color: var(--vscode-descriptionForeground, #989898);
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .kb-result-text {
            font-family: var(--vscode-editor-font-family, "Courier New", monospace);
            white-space: pre-wrap;
            color: var(--vscode-editor-foreground, #cccccc);
            font-size: 10px;
            line-height: 1.45;
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
        #chat-messages::-webkit-scrollbar, #terminal::-webkit-scrollbar, .introspection-stream::-webkit-scrollbar, .lab-output::-webkit-scrollbar, .lab-diff-container::-webkit-scrollbar, .kb-source-list::-webkit-scrollbar, .kb-result-list::-webkit-scrollbar, .codex-list::-webkit-scrollbar, .codex-viewer::-webkit-scrollbar {
            width: 6px;
        }
        #chat-messages::-webkit-scrollbar-track, #terminal::-webkit-scrollbar-track, .introspection-stream::-webkit-scrollbar-track, .lab-output::-webkit-scrollbar-track, .lab-diff-container::-webkit-scrollbar-track, .kb-source-list::-webkit-scrollbar-track, .kb-result-list::-webkit-scrollbar-track, .codex-list::-webkit-scrollbar-track, .codex-viewer::-webkit-scrollbar-track {
            background: transparent;
        }
        #chat-messages::-webkit-scrollbar-thumb, #terminal::-webkit-scrollbar-thumb, .introspection-stream::-webkit-scrollbar-thumb, .lab-output::-webkit-scrollbar-thumb, .lab-diff-container::-webkit-scrollbar-thumb, .kb-source-list::-webkit-scrollbar-thumb, .kb-result-list::-webkit-scrollbar-thumb, .codex-list::-webkit-scrollbar-thumb, .codex-viewer::-webkit-scrollbar-thumb {
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
            <option value="models">🧠 Models</option>
            <option value="lab">🧪 Prompt Lab</option>
            <option value="kb">📎 Knowledge Base</option>
            <option value="codex">📚 Codex Library</option>
        </select>
    </div>

    <!-- Runtime Status -->
    <div class="runtime-panel">
        <div class="runtime-grid">
            <div class="runtime-cell">
                <span class="runtime-label">Model</span>
                <span class="runtime-value" id="runtimeModel">unknown</span>
            </div>
            <div class="runtime-cell">
                <span class="runtime-label">State</span>
                <span class="runtime-value" id="runtimeState">offline</span>
            </div>
            <div class="runtime-cell">
                <span class="runtime-label">Adapter</span>
                <span class="runtime-value" id="runtimeAdapter">none</span>
            </div>
            <div class="runtime-cell">
                <span class="runtime-label">RAM / Context</span>
                <span class="runtime-value" id="runtimeSystem">--</span>
            </div>
        </div>
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

    <!-- Workspace 3: Models Content -->
    <div class="tab-content" id="contentModels">
        <div class="actions-row" style="margin-top:0; margin-bottom:10px;">
            <button onclick="loadModels()">Refresh Models</button>
        </div>
        <div class="model-list" id="modelList">
            <div class="model-card">
                <div class="model-meta">Connect to Karl to inspect local model tiers.</div>
            </div>
        </div>
    </div>

    <!-- Workspace 4: Prompt Lab Content -->
    <div class="tab-content" id="contentLab">
        <div class="prompt-pair-row">
            <select id="promptPairSelect" onchange="loadSelectedPromptPair()">
                <option value="">Saved prompt pairs...</option>
            </select>
            <button onclick="loadPromptPairs()">Refresh</button>
        </div>
        <div class="form-group">
            <input id="promptPairName" type="text" placeholder="Pair name for save/load...">
        </div>
        <div class="prompt-pair-actions">
            <button onclick="savePromptPair()">Save</button>
            <button onclick="loadSelectedPromptPair()">Load</button>
            <button class="btn-danger" onclick="deletePromptPair()">Delete</button>
        </div>
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
            <div class="actions-row" style="margin-top:0; margin-bottom:8px;">
                <button onclick="computeLabDiff()">Recompute Diff</button>
            </div>
            <div class="lab-diff-container" id="labDiff">Diff comparisons will render here after runs complete...</div>
        </div>
    </div>

    <!-- Workspace 5: Codex Library Content -->
    <div class="tab-content" id="contentKb">
        <div class="kb-stat-row">
            <div class="kb-stat">
                <span class="kb-stat-value" id="kbSourceCount">0</span>
                <span class="kb-stat-label">Sources</span>
            </div>
            <div class="kb-stat">
                <span class="kb-stat-value" id="kbChunkCount">0</span>
                <span class="kb-stat-label">Chunks</span>
            </div>
            <div class="kb-stat">
                <span class="kb-stat-value" id="kbIngestState">Idle</span>
                <span class="kb-stat-label">Index</span>
            </div>
        </div>

        <label>Indexed Sources</label>
        <div class="kb-source-list" id="kbSourceList">
            <div style="padding:8px; color:var(--vscode-descriptionForeground)">Connect to Karl to inspect indexed sources.</div>
        </div>

        <div class="form-group">
            <label for="kbPath">File Or Folder To Ingest</label>
            <input id="kbPath" type="text" placeholder="/path/to/file-or-folder">
        </div>
        <div class="actions-row" style="margin-top:0;">
            <button onclick="useActiveFileForKb()">Active File</button>
            <button onclick="chooseKbFile()">Choose File</button>
            <button onclick="chooseKbFolder()">Choose Folder</button>
        </div>

        <div class="kb-grid" style="margin-top:12px;">
            <div class="form-group">
                <label for="kbChunkSize">Chunk Size</label>
                <input id="kbChunkSize" type="number" min="50" max="2000" step="50" value="200">
            </div>
            <div class="form-group">
                <label for="kbOverlap">Overlap</label>
                <input id="kbOverlap" type="number" min="0" max="1000" step="10" value="50">
            </div>
        </div>
        <div class="checkbox-row">
            <input id="kbRecursive" type="checkbox" checked>
            <label for="kbRecursive" style="display:inline; text-transform:none; font-size:11px;">Ingest folders recursively</label>
        </div>
        <div class="actions-row">
            <button id="kbIngestBtn" onclick="ingestKbPath()">Ingest Path</button>
            <button onclick="loadKbSources()">Refresh Index</button>
        </div>

        <div class="kb-grid" style="margin-top:12px;">
            <div class="form-group">
                <label for="kbTopK">Top-K</label>
                <input id="kbTopK" type="number" min="1" max="25" value="5">
            </div>
            <div class="form-group">
                <label for="kbThreshold">Distance Threshold</label>
                <input id="kbThreshold" type="number" min="0" max="100" step="0.05" value="0">
            </div>
        </div>
        <div class="form-group">
            <label for="kbSourceFilter">Source Filter</label>
            <select id="kbSourceFilter">
                <option value="">All sources</option>
            </select>
        </div>
        <div class="form-group">
            <label for="kbQuery">Retrieval Preview Query</label>
            <textarea id="kbQuery" rows="2" placeholder="Search indexed project knowledge before sending it into generation..."></textarea>
        </div>
        <button onclick="searchKb()">Search Knowledge Base</button>

        <div class="form-group" style="margin-top:12px;">
            <label>Retrieval Preview</label>
            <div class="kb-result-list" id="kbResults">
                <div style="padding:8px; color:var(--vscode-descriptionForeground)">Search results will appear here.</div>
            </div>
        </div>
    </div>

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
        let runtimeStatusTimer = null;
        let kbSelectedSource = '';

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
            } else if (message.command === 'set_kb_path') {
                document.getElementById('kbPath').value = message.path || '';
                document.getElementById('workspace-select').value = 'kb';
                switchWorkspace('kb');
            }
        });

        function switchWorkspace(wsId) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            if (wsId === 'swarm') {
                document.getElementById('contentSwarm').classList.add('active');
            } else if (wsId === 'chat') {
                document.getElementById('contentChat').classList.add('active');
            } else if (wsId === 'models') {
                document.getElementById('contentModels').classList.add('active');
                loadModels();
            } else if (wsId === 'lab') {
                document.getElementById('contentLab').classList.add('active');
                loadPromptPairs();
            } else if (wsId === 'kb') {
                document.getElementById('contentKb').classList.add('active');
                loadKbSources();
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
                requestRuntimeStatus();
                if (!runtimeStatusTimer) {
                    runtimeStatusTimer = setInterval(requestRuntimeStatus, 4000);
                }

                // If Codex list is empty and currently in codex tab, load topics
                if (document.getElementById('workspace-select').value === 'codex') {
                    loadCodexTopics();
                }
                if (document.getElementById('workspace-select').value === 'kb') {
                    loadKbSources();
                }
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const method = data.method;
                const params = data.params;

                if (data.error) {
                    const message = data.error.message || 'Unknown bridge error';
                    log('[Bridge Error] ' + message);
                    if (data.id === 51) {
                        document.getElementById('kbIngestBtn').disabled = false;
                        document.getElementById('kbIngestState').innerText = 'Error';
                    }
                    vscode.postMessage({ command: 'show_error', text: message });
                    return;
                }

                // Handle RPC response results
                if (data.result) {
                    if (data.id === 12) { // diff result
                        document.getElementById('labDiff').innerHTML = data.result.diff_html;
                        labRunning = false;
                        document.getElementById('labRunBtn').disabled = false;
                        log('[PromptLab] Diff rendering completed.');
                    } else if (data.id === 30) { // runtime status
                        renderRuntimeStatus(data.result);
                    } else if (data.id === 31) { // list models
                        renderModels(data.result.models || []);
                    } else if (data.id === 32) { // set active model
                        log('[Models] ' + data.result.message);
                        requestRuntimeStatus();
                        loadModels();
                    } else if (data.id === 40) { // list prompt pairs
                        renderPromptPairs(data.result.pairs || []);
                    } else if (data.id === 41) { // get prompt pair
                        applyPromptPair(data.result);
                    } else if (data.id === 42) { // save prompt pair
                        document.getElementById('promptPairName').value = data.result.name;
                        log('[PromptLab] Saved pair: ' + data.result.name);
                        loadPromptPairs();
                    } else if (data.id === 43) { // delete prompt pair
                        log('[PromptLab] Deleted pair: ' + data.result.name);
                        document.getElementById('promptPairName').value = '';
                        loadPromptPairs();
                    } else if (data.id === 50) { // list KB sources
                        renderKbSnapshot(data.result);
                    } else if (data.id === 51) { // ingest path
                        document.getElementById('kbIngestBtn').disabled = true;
                        document.getElementById('kbIngestState').innerText = 'Running';
                        log('[KB] Ingestion started for ' + data.result.file_count + ' file(s).');
                    } else if (data.id === 52) { // search KB
                        renderKbSearch(data.result);
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
                } else if (method === 'kb_ingest_progress') {
                    document.getElementById('kbIngestState').innerText = params.current + '/' + params.total;
                    log('[KB] Ingesting ' + params.current + '/' + params.total + ': ' + params.filename);
                } else if (method === 'kb_ingest_finished') {
                    document.getElementById('kbIngestBtn').disabled = false;
                    document.getElementById('kbIngestState').innerText = params.error_count ? 'Check Log' : 'Ready';
                    renderKbSnapshot(params.snapshot || {});
                    log('[KB] Ingestion finished. Added ' + params.chunks_added + ' chunk(s) from ' + params.file_count + ' file(s).');
                    if (params.error_count) {
                        (params.errors || []).forEach(err => log('[KB] Error: ' + err.filename + ' — ' + err.error));
                    }
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
                            computeLabDiff();
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
                renderRuntimeOffline();
                if (runtimeStatusTimer) {
                    clearInterval(runtimeStatusTimer);
                    runtimeStatusTimer = null;
                }
                if (!reconnectTimer && autoConnect) {
                    log('[WebSocket] Connection lost. Retrying in 5 seconds...');
                    reconnectTimer = setInterval(connect, 5000);
                }
            };
        }

        function requestRuntimeStatus() {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 30,
                method: 'get_runtime_status'
            }));
        }

        function renderRuntimeStatus(status) {
            const model = status.model || {};
            const adapter = status.adapter || {};
            const runtime = status.runtime || {};
            const system = status.system || {};
            const bridge = status.bridge || {};

            const modelText = (model.name || 'none') + (model.loaded ? ' loaded' : ' ready');
            const adapterText = adapter.name || 'none';
            const stateText = runtime.state || 'idle';
            const clients = Number.isInteger(bridge.clients) ? bridge.clients : 0;
            const ramText = system.ram_mb === null || system.ram_mb === undefined ? '-- MB' : system.ram_mb + ' MB';
            const ctxText = model.n_ctx ? model.n_ctx + ' ctx' : '-- ctx';

            const modelEl = document.getElementById('runtimeModel');
            const stateEl = document.getElementById('runtimeState');
            const adapterEl = document.getElementById('runtimeAdapter');
            const systemEl = document.getElementById('runtimeSystem');

            modelEl.innerText = modelText;
            stateEl.innerText = stateText + ' · ' + clients + ' client' + (clients === 1 ? '' : 's');
            adapterEl.innerText = adapterText;
            systemEl.innerText = ramText + ' · ' + ctxText;

            stateEl.className = 'runtime-value ' + (stateText === 'running' ? 'warn' : 'good');
            modelEl.className = 'runtime-value ' + (model.loaded ? 'good' : '');
            adapterEl.className = 'runtime-value ' + (adapter.name ? 'good' : '');
            systemEl.className = 'runtime-value';
        }

        function renderRuntimeOffline() {
            document.getElementById('runtimeModel').innerText = 'unknown';
            document.getElementById('runtimeState').innerText = 'offline';
            document.getElementById('runtimeAdapter').innerText = 'none';
            document.getElementById('runtimeSystem').innerText = '--';
            document.getElementById('runtimeState').className = 'runtime-value warn';
        }

        function getKbSettings() {
            const topKEl = document.getElementById('kbTopK');
            const thresholdEl = document.getElementById('kbThreshold');
            return {
                top_k: Math.max(1, Math.min(25, parseInt(topKEl ? topKEl.value : '3') || 3)),
                threshold: Math.max(0, parseFloat(thresholdEl ? thresholdEl.value : '0') || 0)
            };
        }

        function loadModels() {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                document.getElementById('modelList').innerHTML = '<div class="model-card"><div class="model-meta">Karl bridge is offline.</div></div>';
                return;
            }
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 31,
                method: 'list_models'
            }));
        }

        function activateModel(filename) {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 32,
                method: 'set_active_model',
                params: { filename: filename }
            }));
        }

        function renderModels(models) {
            const container = document.getElementById('modelList');
            if (!models || models.length === 0) {
                container.innerHTML = '<div class="model-card"><div class="model-meta">No model registry entries found.</div></div>';
                return;
            }

            container.innerHTML = models.map(model => {
                const title = escapeHtml(model.name || model.filename || 'Unknown model');
                const filename = escapeHtml(model.filename || '');
                const tier = model.tier ? 'Tier ' + model.tier + ' · ' : '';
                const ctx = model.n_ctx ? model.n_ctx + ' ctx · ' : '';
                const ram = model.min_ram_gb ? model.min_ram_gb + ' GB RAM · ' : '';
                const size = model.size_gb ? model.size_gb + ' GB · ' : '';
                const state = model.active ? 'Active' : (model.installed ? 'Installed' : 'Not installed');
                const cardClass = 'model-card' + (model.active ? ' active' : '');
                const action = model.active
                    ? '<button disabled>Active</button>'
                    : (model.installed
                        ? '<button data-filename="' + escapeHtml(model.filename || '') + '" onclick="activateModelFromButton(this)">Set Active</button>'
                        : '<button disabled>Download in Karl</button>');

                return '<div class="' + cardClass + '">' +
                    '<div class="model-title">' + title + '</div>' +
                    '<div class="model-meta">' + tier + ctx + ram + size + state + '<br><code>' + filename + '</code></div>' +
                    '<div class="model-actions">' + action + '</div>' +
                    '</div>';
            }).join('');
        }

        function escapeHtml(value) {
            return String(value)
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#39;');
        }

        function activateModelFromButton(button) {
            activateModel(button.dataset.filename);
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
            const kb = getKbSettings();

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
                        agentic_loop_enabled: loop,
                        rag_top_k: kb.top_k,
                        rag_threshold: kb.threshold
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
            const kb = getKbSettings();
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
                        agentic_loop_enabled: loop,
                        rag_top_k: kb.top_k,
                        rag_threshold: kb.threshold
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
                        rag_top_k: getKbSettings().top_k,
                        rag_threshold: getKbSettings().threshold,
                        system_prompt: systemPrompt
                    }
                }
            }));
        }

        function computeLabDiff() {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            if (!labOutputA || !labOutputB) {
                document.getElementById('labDiff').innerHTML = '<div style="color:var(--vscode-descriptionForeground)">Run both prompts before computing a diff.</div>';
                return;
            }
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

        function loadPromptPairs() {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 40,
                method: 'list_prompt_pairs'
            }));
        }

        function renderPromptPairs(pairs) {
            const select = document.getElementById('promptPairSelect');
            const current = select.value;
            select.innerHTML = '<option value="">Saved prompt pairs...</option>';
            pairs.forEach(pair => {
                const option = document.createElement('option');
                option.value = pair.name;
                option.innerText = pair.name;
                select.appendChild(option);
            });
            if (current) {
                select.value = current;
            }
        }

        function loadSelectedPromptPair() {
            const select = document.getElementById('promptPairSelect');
            const name = select.value || document.getElementById('promptPairName').value.trim();
            if (!name || !socket || socket.readyState !== WebSocket.OPEN) return;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 41,
                method: 'get_prompt_pair',
                params: { name: name }
            }));
        }

        function applyPromptPair(pair) {
            document.getElementById('promptPairName').value = pair.name || '';
            document.getElementById('promptPairSelect').value = pair.name || '';
            document.getElementById('labSysA').value = pair.system_a || '';
            document.getElementById('labSysB').value = pair.system_b || '';
            document.getElementById('labUser').value = pair.user_a || pair.user_b || '';
            labOutputA = pair.output_a_raw || '';
            labOutputB = pair.output_b_raw || '';
            document.getElementById('labOutputA').innerText = pair.output_a_display || labOutputA || 'Output A will stream here...';
            document.getElementById('labOutputB').innerText = pair.output_b_display || labOutputB || 'Output B will stream here...';
            if (labOutputA && labOutputB) {
                computeLabDiff();
            } else {
                document.getElementById('labDiff').innerText = 'Loaded pair. Run both prompts to render a fresh diff.';
            }
        }

        function savePromptPair() {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            const name = document.getElementById('promptPairName').value.trim();
            if (!name) {
                vscode.postMessage({ command: 'show_error', text: 'Prompt pair name is required.' });
                return;
            }
            const userMsg = document.getElementById('labUser').value;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 42,
                method: 'save_prompt_pair',
                params: {
                    name: name,
                    system_a: document.getElementById('labSysA').value,
                    user_a: userMsg,
                    system_b: document.getElementById('labSysB').value,
                    user_b: userMsg,
                    rag_a: document.getElementById('karl-rag').checked,
                    rag_b: document.getElementById('karl-rag').checked,
                    loop_a: document.getElementById('karl-loop').checked,
                    loop_b: document.getElementById('karl-loop').checked,
                    output_a_raw: labOutputA,
                    output_b_raw: labOutputB,
                    output_a_display: document.getElementById('labOutputA').innerText,
                    output_b_display: document.getElementById('labOutputB').innerText
                }
            }));
        }

        function deletePromptPair() {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;
            const name = document.getElementById('promptPairSelect').value || document.getElementById('promptPairName').value.trim();
            if (!name) return;
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 43,
                method: 'delete_prompt_pair',
                params: { name: name }
            }));
        }

        // Knowledge Base Implementation
        function loadKbSources() {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                document.getElementById('kbSourceList').innerHTML = '<div style="padding:8px; color:var(--vscode-descriptionForeground)">Karl bridge is offline.</div>';
                return;
            }
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 50,
                method: 'list_kb_sources'
            }));
        }

        function renderKbSnapshot(snapshot) {
            const sources = snapshot.sources || [];
            document.getElementById('kbSourceCount').innerText = snapshot.total_sources || sources.length || 0;
            document.getElementById('kbChunkCount').innerText = snapshot.total_chunks || 0;
            document.getElementById('kbIngestState').innerText = snapshot.ingesting ? 'Running' : 'Ready';

            const list = document.getElementById('kbSourceList');
            const filter = document.getElementById('kbSourceFilter');
            const previousFilter = filter.value || kbSelectedSource;

            if (!sources.length) {
                list.innerHTML = '<div style="padding:8px; color:var(--vscode-descriptionForeground)">No indexed sources yet.</div>';
            } else {
                list.innerHTML = sources.map(source => {
                    const active = source.name === kbSelectedSource ? ' active' : '';
                    return '<div class="kb-source-item' + active + '" data-source="' + escapeHtml(source.name) + '" onclick="selectKbSourceFromRow(this)">' +
                        '<span class="kb-source-name">' + escapeHtml(source.name) + '</span>' +
                        '<span class="kb-source-count">' + Number(source.chunks || 0) + ' chunks</span>' +
                        '</div>';
                }).join('');
            }

            filter.innerHTML = '<option value="">All sources</option>' + sources.map(source => {
                return '<option value="' + escapeHtml(source.name) + '">' + escapeHtml(source.name) + '</option>';
            }).join('');
            if (previousFilter && sources.some(source => source.name === previousFilter)) {
                filter.value = previousFilter;
                kbSelectedSource = previousFilter;
            } else {
                kbSelectedSource = '';
            }
        }

        function selectKbSourceFromRow(row) {
            kbSelectedSource = row.dataset.source || '';
            document.querySelectorAll('.kb-source-item').forEach(item => item.classList.remove('active'));
            row.classList.add('active');
            document.getElementById('kbSourceFilter').value = kbSelectedSource;
        }

        function chooseKbFile() {
            vscode.postMessage({ command: 'choose_kb_file' });
        }

        function chooseKbFolder() {
            vscode.postMessage({ command: 'choose_kb_folder' });
        }

        function useActiveFileForKb() {
            vscode.postMessage({ command: 'use_active_file_for_kb' });
        }

        function ingestKbPath() {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected. Start the desktop app bridge first.' });
                return;
            }
            const ingestPath = document.getElementById('kbPath').value.trim();
            if (!ingestPath) {
                vscode.postMessage({ command: 'show_error', text: 'Choose a file or folder to ingest first.' });
                return;
            }

            const chunkSize = parseInt(document.getElementById('kbChunkSize').value) || 200;
            const overlap = parseInt(document.getElementById('kbOverlap').value) || 0;
            if (overlap >= chunkSize) {
                vscode.postMessage({ command: 'show_error', text: 'Overlap must be lower than chunk size.' });
                return;
            }

            document.getElementById('kbIngestBtn').disabled = true;
            document.getElementById('kbIngestState').innerText = 'Starting';
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 51,
                method: 'ingest_path',
                params: {
                    path: ingestPath,
                    recursive: document.getElementById('kbRecursive').checked,
                    chunk_size: chunkSize,
                    overlap: overlap
                }
            }));
        }

        function searchKb() {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                vscode.postMessage({ command: 'show_error', text: 'Karl is disconnected.' });
                return;
            }
            const query = document.getElementById('kbQuery').value.trim();
            if (!query) {
                vscode.postMessage({ command: 'show_error', text: 'Enter a retrieval preview query.' });
                return;
            }
            const kb = getKbSettings();
            document.getElementById('kbResults').innerHTML = '<div style="padding:8px; color:var(--vscode-descriptionForeground)">Searching index...</div>';
            socket.send(JSON.stringify({
                jsonrpc: '2.0',
                id: 52,
                method: 'search_kb',
                params: {
                    query: query,
                    top_k: kb.top_k,
                    threshold: kb.threshold,
                    source_filter: document.getElementById('kbSourceFilter').value || null
                }
            }));
        }

        function renderKbSearch(payload) {
            renderKbSnapshot(payload.snapshot || {});
            const results = payload.results || [];
            const container = document.getElementById('kbResults');
            if (!results.length) {
                container.innerHTML = '<div style="padding:8px; color:var(--vscode-descriptionForeground)">No chunks matched the current query and threshold.</div>';
                return;
            }

            container.innerHTML = results.map((result, index) => {
                const text = escapeHtml(result.text || '').slice(0, 1800);
                const rank = result.rank === null || result.rank === undefined ? index : result.rank;
                const distance = Number(result.distance || 0).toFixed(4);
                return '<div class="kb-result-card">' +
                    '<div class="kb-result-meta">Rank ' + rank + ' · ' + escapeHtml(result.source_file || 'unknown') + ' · Chunk ' + escapeHtml(result.chunk_id) + ' · dist=' + distance + '</div>' +
                    '<div class="kb-result-text">' + text + '</div>' +
                    '</div>';
            }).join('');
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
