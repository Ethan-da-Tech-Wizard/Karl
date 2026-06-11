const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

function activate(context) {
    const sidebarProvider = new KarlSidebarProvider(context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('karl.sidebarView', sidebarProvider)
    );

    const register = (command, handler) => {
        context.subscriptions.push(vscode.commands.registerCommand(command, handler));
    };

    register('karl.openSidebar', () => {
        vscode.commands.executeCommand('workbench.view.extension.karl-swarm');
    });

    register('karl.fixSelection', () => runSelectionWorkflow(sidebarProvider, 'Refactor Selection'));
    register('karl.explainSelection', () => runSelectionWorkflow(sidebarProvider, 'Explain Selection'));
    register('karl.generateTests', () => runEditorWorkflow(sidebarProvider, 'Generate Tests'));
    register('karl.reviewActiveFile', () => runEditorWorkflow(sidebarProvider, 'Review Active File'));
    register('karl.askWorkspace', () => runWorkspaceWorkflow(sidebarProvider));
    register('karl.ingestActiveFile', (uri) => sendActiveFileToKb(sidebarProvider, uri));
    register('karl.ingestWorkspaceFolder', (uri) => sendWorkspaceFolderToKb(sidebarProvider, uri));
    register('karl.reviewStagedDiff', () => runGitDiffWorkflow(sidebarProvider, 'Review Staged Diff', ['diff', '--staged']));
    register('karl.generateCommitMessage', () => runGitDiffWorkflow(sidebarProvider, 'Generate Commit Message', ['diff', '--staged']));
    register('karl.explainDiagnostics', () => runDiagnosticsWorkflow(sidebarProvider));
    register('karl.createImplementationPlan', (...args) => runImplementationPlanWorkflow(sidebarProvider, args));
    register('karl.searchKbSelection', () => searchKbFromSelection(sidebarProvider));
    register('karl.sendCurrentFileToSwarm', () => runEditorWorkflow(sidebarProvider, 'Current File Swarm Task'));
    register('karl.openReviewBay', async () => {
        await revealKarlPanel(sidebarProvider);
        sidebarProvider.postMessageToWebview({ command: 'open_review_bay' });
    });
}

async function revealKarlPanel(sidebarProvider) {
    await vscode.commands.executeCommand('workbench.view.extension.karl-swarm');
    await sidebarProvider.waitForWebview();
}

function currentWorkspacePath(fallbackFile) {
    if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
        return vscode.workspace.workspaceFolders[0].uri.fsPath;
    }
    return fallbackFile ? path.dirname(fallbackFile) : '';
}

async function runSelectionWorkflow(sidebarProvider, mode) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showInformationMessage('No active editor found.');
        return;
    }

    const selection = editor.selection;
    const code = editor.document.getText(selection);
    if (!code.trim()) {
        vscode.window.showWarningMessage('Highlight code before sending a selection task to Karl.');
        return;
    }

    const filepath = editor.document.uri.fsPath;
    const objective = await vscode.window.showInputBox({
        prompt: `${mode}: what should Karl do?`,
        placeHolder: mode === 'Explain Selection'
            ? 'Explain control flow, risks, and intent.'
            : 'Refactor for clarity, safety, and maintainability.'
    });
    if (!objective) return;

    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'start_code_task',
        data: {
            mode,
            objective,
            code,
            filepath,
            workspace_path: currentWorkspacePath(filepath)
        }
    });
}

async function runEditorWorkflow(sidebarProvider, mode) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showInformationMessage('No active editor found.');
        return;
    }

    const filepath = editor.document.uri.fsPath;
    const code = editor.document.getText();
    let defaultObjective = 'Review the active file for bugs, regressions, missing tests, and concrete improvements.';
    if (mode === 'Generate Tests') {
        defaultObjective = 'Generate focused tests for the active file. Preserve existing behavior and name likely test commands.';
    } else if (mode === 'Current File Swarm Task') {
        defaultObjective = 'Implement the requested change in this file and verify behavior.';
    }

    const objective = await vscode.window.showInputBox({
        prompt: `${mode}: adjust the objective if needed.`,
        value: defaultObjective
    });
    if (!objective) return;

    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'start_code_task',
        data: {
            mode,
            objective,
            code,
            filepath,
            workspace_path: currentWorkspacePath(filepath)
        }
    });
}

function execGit(args, cwd) {
    return new Promise((resolve, reject) => {
        cp.execFile('git', args, { cwd, maxBuffer: 1024 * 1024 * 8 }, (err, stdout, stderr) => {
            if (err) {
                reject(new Error(stderr || err.message));
            } else {
                resolve(stdout);
            }
        });
    });
}

async function runGitDiffWorkflow(sidebarProvider, mode, args) {
    const workspacePath = currentWorkspacePath('');
    if (!workspacePath) {
        vscode.window.showWarningMessage('Open a workspace before using git workflows.');
        return;
    }
    let diff = '';
    try {
        diff = await execGit(args, workspacePath);
    } catch (err) {
        vscode.window.showErrorMessage(`Git workflow failed: ${err.message}`);
        return;
    }
    if (!diff.trim()) {
        vscode.window.showInformationMessage('No staged git diff found.');
        return;
    }

    const objective = mode === 'Generate Commit Message'
        ? 'Generate a concise conventional commit message and a short body from this staged diff.'
        : 'Review this staged diff for bugs, regressions, missing tests, and risky changes.';

    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'start_code_task',
        data: {
            mode,
            objective,
            code: diff,
            filepath: 'git diff --staged',
            workspace_path: workspacePath
        }
    });
}

async function runDiagnosticsWorkflow(sidebarProvider) {
    const workspacePath = currentWorkspacePath('');
    const diagnostics = vscode.languages.getDiagnostics()
        .flatMap(([uri, items]) => items.map(item => ({
            file: uri.fsPath,
            severity: item.severity,
            message: item.message,
            source: item.source || '',
            line: item.range.start.line + 1,
            character: item.range.start.character + 1
        })))
        .slice(0, 80);

    if (!diagnostics.length) {
        vscode.window.showInformationMessage('No current diagnostics found.');
        return;
    }

    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'start_code_task',
        data: {
            mode: 'Explain Diagnostics',
            objective: 'Explain these editor diagnostics, group likely root causes, and propose a fix order.',
            code: JSON.stringify(diagnostics, null, 2),
            filepath: 'VS Code diagnostics',
            workspace_path: workspacePath
        }
    });
}

async function runImplementationPlanWorkflow(sidebarProvider, args) {
    const workspacePath = currentWorkspacePath('');
    const uris = args.flat().filter(item => item && item.fsPath);
    const files = uris.length ? uris : (vscode.window.activeTextEditor ? [vscode.window.activeTextEditor.document.uri] : []);
    if (!files.length) {
        vscode.window.showWarningMessage('Select files or open an active file before asking for an implementation plan.');
        return;
    }

    const chunks = [];
    for (const uri of files.slice(0, 12)) {
        try {
            const stat = await fs.promises.stat(uri.fsPath);
            if (!stat.isFile() || stat.size > 500000) continue;
            const content = await fs.promises.readFile(uri.fsPath, 'utf8');
            chunks.push(`File: ${uri.fsPath}\n\n${content.slice(0, 30000)}`);
        } catch {
            // Ignore unreadable selected files.
        }
    }
    if (!chunks.length) {
        vscode.window.showWarningMessage('No readable selected files found for planning.');
        return;
    }

    const objective = await vscode.window.showInputBox({
        prompt: 'What should Karl plan across the selected files?',
        placeHolder: 'Describe the implementation goal.'
    });
    if (!objective) return;

    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'start_code_task',
        data: {
            mode: 'Implementation Plan',
            objective,
            code: chunks.join('\n\n---\n\n'),
            filepath: `${chunks.length} selected file(s)`,
            workspace_path: workspacePath
        }
    });
}

async function searchKbFromSelection(sidebarProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showInformationMessage('No active editor found.');
        return;
    }
    const query = editor.document.getText(editor.selection).trim();
    if (!query) {
        vscode.window.showWarningMessage('Select text to search in Karl Knowledge Base.');
        return;
    }
    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'search_kb_text',
        query
    });
}

async function runWorkspaceWorkflow(sidebarProvider) {
    const workspacePath = currentWorkspacePath('');
    if (!workspacePath) {
        vscode.window.showWarningMessage('Open a workspace before asking Karl about it.');
        return;
    }

    const objective = await vscode.window.showInputBox({
        prompt: 'Ask Karl about this workspace.',
        placeHolder: 'Find risky areas, explain architecture, or plan a change.'
    });
    if (!objective) return;

    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'start_workspace_question',
        data: { objective, workspace_path: workspacePath }
    });
}

async function sendActiveFileToKb(sidebarProvider, uri) {
    const selectedPath = uri && uri.fsPath ? uri.fsPath : null;
    const editor = vscode.window.activeTextEditor;
    const filePath = selectedPath || (editor ? editor.document.uri.fsPath : '');
    if (!filePath) {
        vscode.window.showWarningMessage('No active editor found.');
        return;
    }
    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'set_kb_path',
        path: filePath
    });
}

async function sendWorkspaceFolderToKb(sidebarProvider, uri) {
    const workspacePath = uri && uri.fsPath ? uri.fsPath : currentWorkspacePath('');
    if (!workspacePath) {
        vscode.window.showWarningMessage('Open a workspace before ingesting a folder.');
        return;
    }
    await revealKarlPanel(sidebarProvider);
    sidebarProvider.postMessageToWebview({
        command: 'set_kb_path',
        path: workspacePath
    });
}

class KarlSidebarProvider {
    constructor(context) {
        this.context = context;
        this.extensionUri = context.extensionUri;
        this.webviewView = null;
        this.pendingEdits = new Map();
        this._resolveWebview = null;
    }

    waitForWebview() {
        if (this.webviewView) return Promise.resolve();
        return new Promise(resolve => {
            this._resolveWebview = resolve;
            setTimeout(resolve, 1200);
        });
    }

    resolveWebviewView(webviewView) {
        this.webviewView = webviewView;
        if (this._resolveWebview) {
            this._resolveWebview();
            this._resolveWebview = null;
        }

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
                case 'persist_state':
                    await this.context.workspaceState.update('karl.sidebarState', message.state || {});
                    break;
                case 'show_message':
                    vscode.window.showInformationMessage(message.text);
                    break;
                case 'show_error':
                    vscode.window.showErrorMessage(message.text);
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
                default:
                    break;
            }
        });
    }

    postMessageToWebview(message) {
        if (this.webviewView) {
            this.webviewView.webview.postMessage(message);
        }
    }

    queueFileEdit(filepath, content, summary = '') {
        if (!filepath || typeof content !== 'string') {
            vscode.window.showErrorMessage('Karl sent an invalid file edit payload.');
            return;
        }
        const editId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const filename = path.basename(filepath);
        let previous = '';
        try {
            previous = fs.existsSync(filepath) ? fs.readFileSync(filepath, 'utf8') : '';
        } catch {
            previous = '';
        }
        const oldLines = previous ? previous.split(/\r?\n/).length : 0;
        const newLines = content ? content.split(/\r?\n/).length : 0;
        this.pendingEdits.set(editId, { filepath, content, summary, filename, oldLines, newLines, status: 'proposed' });
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
    }

    async previewFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (!edit) {
            vscode.window.showWarningMessage('That Karl edit is no longer pending.');
            return;
        }
        const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'karl-proposed-'));
        const proposedPath = path.join(tempDir, edit.filename);
        await fs.promises.writeFile(proposedPath, edit.content, 'utf8');
        await vscode.commands.executeCommand(
            'vscode.diff',
            vscode.Uri.file(edit.filepath),
            vscode.Uri.file(proposedPath),
            `Karl Preview: ${edit.filename}`
        );
        edit.status = 'previewed';
        this.postMessageToWebview({ command: 'file_edit_previewed', editId });
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
            if (fs.existsSync(edit.filepath) && !fs.existsSync(backupPath)) {
                await fs.promises.copyFile(edit.filepath, backupPath);
            }
            await fs.promises.writeFile(edit.filepath, edit.content, 'utf8');
            this.pendingEdits.delete(editId);
            this.postMessageToWebview({ command: 'file_edit_applied', editId });
            vscode.window.showInformationMessage(`Karl applied changes to ${edit.filename}.`);
            await vscode.window.showTextDocument(vscode.Uri.file(edit.filepath), { preview: false });
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to apply Karl edit: ${err.message}`);
        }
    }

    rejectFile(editId) {
        const edit = this.pendingEdits.get(editId);
        this.pendingEdits.delete(editId);
        this.postMessageToWebview({ command: 'file_edit_rejected', editId });
        if (edit) {
            vscode.window.showInformationMessage(`Rejected Karl edit for ${edit.filename}.`);
        }
    }

    async acceptLegacyFile(filepath) {
        if (!filepath) return;
        const backupPath = filepath + '.original';
        if (fs.existsSync(backupPath)) {
            await fs.promises.unlink(backupPath);
            vscode.window.showInformationMessage(`Accepted changes for ${path.basename(filepath)}.`);
        }
    }

    async rollbackLegacyFile(filepath) {
        if (!filepath) return;
        const backupPath = filepath + '.original';
        if (!fs.existsSync(backupPath)) {
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

    getHtmlForWebview(webview, port, autoConnect, workspaceFolder, persisted) {
        const cssUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'karl.css'));
        const themesUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'themes.js'));
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
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} https:; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karl</title>
    <link href="${cssUri}" rel="stylesheet">
</head>
<body>
    <script nonce="${nonce}">window.KARL_BOOTSTRAP = ${config};</script>
    <div class="shell">
        <header class="topbar glow-panel">
            <div>
                <div class="eyebrow">Karl Cockpit</div>
                <h1>Agent Swarm</h1>
            </div>
            <div class="bridge">
                <span id="statusDot" class="status-dot offline"></span>
                <span id="statusText">Offline</span>
            </div>
        </header>

        <section class="runtime-grid">
            <div class="metric"><span>Model</span><strong id="runtimeModel">unknown</strong></div>
            <div class="metric"><span>State</span><strong id="runtimeState">offline</strong></div>
            <div class="metric"><span>Adapter</span><strong id="runtimeAdapter">none</strong></div>
            <div class="metric"><span>RAM / Context</span><strong id="runtimeSystem">--</strong></div>
        </section>

        <nav class="tabs" aria-label="Karl workspaces">
            <button class="tab active" data-workspace="swarm">Swarm</button>
            <button class="tab" data-workspace="chat">Chat</button>
            <button class="tab" data-workspace="changes">Changes</button>
            <button class="tab" data-workspace="kb">Knowledge</button>
            <button class="tab" data-workspace="lab">Lab</button>
            <button class="tab" data-workspace="models">Models</button>
            <button class="tab" data-workspace="codex">Codex</button>
            <button class="tab" data-workspace="appearance">Look</button>
        </nav>

        <section id="offlinePanel" class="offline-panel glow-panel">
            <div class="scanner-line"></div>
            <div>
                <div class="eyebrow">Bridge Checklist</div>
                <p>Start Karl, verify the WebSocket bridge is listening, then connect. The panel will keep trying unless you disconnect manually.</p>
            </div>
        </section>

        <section class="connection-row glow-panel">
            <label>Bridge Port <input id="bridgePort" type="number" min="1" max="65535" value="${port}"></label>
            <button id="connectBtn" class="primary">Connect</button>
            <button id="disconnectBtn">Disconnect</button>
        </section>

        <details class="settings glow-panel">
            <summary>Generation Overrides</summary>
            <div class="settings-grid">
                <label>Temperature <input id="karlTemp" type="number" step="0.05" min="0" max="2" value="0.7"></label>
                <label>Top-P <input id="karlTopP" type="number" step="0.05" min="0" max="1" value="0.95"></label>
                <label>Max Tokens <input id="karlMaxTok" type="number" min="64" max="32768" value="2048"></label>
                <label>RAG Top-K <input id="kbTopK" type="number" min="1" max="25" value="5"></label>
                <label>RAG Threshold <input id="kbThreshold" type="number" min="0" max="100" step="0.05" value="0"></label>
                <label class="check"><input id="karlRag" type="checkbox" checked> Use RAG</label>
                <label class="check"><input id="karlLoop" type="checkbox"> Agentic loop</label>
            </div>
        </details>

        <main>
            <section id="workspace-swarm" class="workspace active">
                <div class="section-head">
                    <div><div class="eyebrow">Deploy</div><h2>Task Composer</h2></div>
                    <button id="askWorkspaceBtn">Ask Workspace</button>
                </div>
                <label>Workflow
                    <select id="taskMode">
                        <option>Custom Task</option>
                        <option>Refactor Selection</option>
                        <option>Explain Selection</option>
                        <option>Generate Tests</option>
                        <option>Review Active File</option>
                    </select>
                </label>
                <label>Objective <textarea id="objective" rows="6" placeholder="Describe what Karl should do across the workspace..."></textarea></label>
                <label>Workspace Path <input id="workspace" type="text" placeholder="/path/to/project"></label>
                <label>Verification Command <input id="testCmd" type="text" value="python run_tests.py"></label>
                <div class="action-row">
                    <button id="runBtn" class="primary">Deploy Swarm</button>
                    <button id="stopBtn" class="danger">Stop</button>
                </div>
                <div class="timeline" id="timeline"></div>
                <pre id="terminal">--- Swarm Logs ---</pre>
            </section>

            <section id="workspace-chat" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Direct</div><h2>Chat + Introspection</h2></div></div>
                <div id="introspectionBox" class="thoughts"><div class="eyebrow">Thought Stream</div><pre id="introspectionThoughts"></pre></div>
                <div id="chatMessages" class="chat"></div>
                <div class="composer">
                    <input id="chatInput" type="text" placeholder="Ask Karl about the current codebase...">
                    <button id="chatSendBtn" class="primary">Send</button>
                </div>
            </section>

            <section id="workspace-changes" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Review</div><h2>Pending File Changes</h2></div><div class="action-row compact-actions"><button id="previewAllBtn">Preview All</button><button id="copySummaryBtn">Copy Summary</button></div></div>
                <div id="changeQueue" class="queue empty">No pending Karl edits.</div>
            </section>

            <section id="workspace-kb" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Context</div><h2>Knowledge Base</h2></div><button id="refreshKbBtn">Refresh</button></div>
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
                <div class="settings-grid">
                    <label>Chunk Size <input id="kbChunkSize" type="number" min="50" max="2000" step="50" value="200"></label>
                    <label>Overlap <input id="kbOverlap" type="number" min="0" max="1000" step="10" value="50"></label>
                    <label class="check"><input id="kbRecursive" type="checkbox" checked> Recursive folders</label>
                </div>
                <button id="kbIngestBtn" class="primary">Ingest Path</button>
                <label>Source Filter <select id="kbSourceFilter"><option value="">All sources</option></select></label>
                <label>Retrieval Preview <textarea id="kbQuery" rows="3" placeholder="Search indexed project knowledge..."></textarea></label>
                <button id="kbSearchBtn">Search Knowledge Base</button>
                <div id="kbResults" class="result-list"></div>
            </section>

            <section id="workspace-lab" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Experiment</div><h2>Prompt Lab</h2></div><button id="loadPairsBtn">Refresh Pairs</button></div>
                <label>Saved Pair <select id="promptPairSelect"><option value="">Saved prompt pairs...</option></select></label>
                <label>Pair Name <input id="promptPairName" type="text" placeholder="name"></label>
                <div class="action-row">
                    <button id="savePairBtn">Save</button>
                    <button id="loadPairBtn">Load</button>
                    <button id="deletePairBtn" class="danger">Delete</button>
                </div>
                <label>System Prompt A <textarea id="labSysA" rows="3"></textarea></label>
                <label>System Prompt B <textarea id="labSysB" rows="3"></textarea></label>
                <label>Common User Message <textarea id="labUser" rows="3"></textarea></label>
                <button id="labRunBtn" class="primary">Run A/B Comparison</button>
                <div class="split">
                    <pre id="labOutputA" class="lab-output">Output A will stream here...</pre>
                    <pre id="labOutputB" class="lab-output">Output B will stream here...</pre>
                </div>
                <button id="diffBtn">Recompute Diff</button>
                <div id="labDiff" class="diff-view">Diff comparisons will render here.</div>
            </section>

            <section id="workspace-models" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Runtime</div><h2>Models</h2></div><button id="loadModelsBtn">Refresh</button></div>
                <div id="modelList" class="model-list"></div>
            </section>

            <section id="workspace-codex" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Reference</div><h2>Codex Library</h2></div></div>
                <input id="codexSearch" type="text" placeholder="Search references...">
                <div id="codexList" class="source-list"></div>
                <article id="codexViewer" class="codex-viewer">Select a chapter to read local reference material.</article>
            </section>

            <section id="workspace-appearance" class="workspace">
                <div class="section-head"><div><div class="eyebrow">Personalize</div><h2>Appearance System</h2></div></div>
                <label>Theme Preset <select id="themeSelect"></select></label>
                <div id="themeDescription" class="theme-description"></div>
                <label>Custom Accent <input id="customAccent" type="color" value="#00c2ff"></label>
                <label>Layout Mode <select id="layoutSelect"></select></label>
                <div id="layoutDescription" class="theme-description"></div>
                <div class="swatch-grid" id="themeSwatches"></div>
                <button id="resetAppearanceBtn">Reset Appearance</button>
            </section>
        </main>
    </div>
    <script nonce="${nonce}" src="${themesUri}"></script>
    <script nonce="${nonce}" src="${jsUri}"></script>
</body>
</html>`;
    }
}

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = { activate, deactivate };
