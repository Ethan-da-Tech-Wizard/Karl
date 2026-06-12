const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const MAX_CONTEXT_CHARS = 70000;
const SUMMARY_CONTEXT_CHARS = 18000;

const WORKFLOW_REGISTRY = {
    fixSelection: {
        id: 'fixSelection',
        title: 'Refactor Selection',
        description: 'Refactor code selection for clarity, safety, and maintainability.',
        requiresSelection: true,
        requiresFile: true,
        targetTab: 'chat',
        promptBuilder: (context) => `Refactor this code from ${context.filepath}:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    explainSelection: {
        id: 'explainSelection',
        title: 'Explain Selection',
        description: 'Explain selection control flow, risks, and intent.',
        requiresSelection: true,
        requiresFile: true,
        targetTab: 'chat',
        promptBuilder: (context) => `Explain this code from ${context.filepath}:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    generateTests: {
        id: 'generateTests',
        title: 'Generate Tests',
        description: 'Generate unit tests for the active file.',
        requiresFile: true,
        targetTab: 'swarm',
        promptBuilder: (context) => `Generate unit tests for the active file: ${context.filepath}\n\nCode:\n${context.code}\n\nObjective: ${context.objective}`
    },
    reviewActiveFile: {
        id: 'reviewActiveFile',
        title: 'Review Active File',
        description: 'Review the active file for bugs, regressions, and improvements.',
        requiresFile: true,
        targetTab: 'swarm',
        promptBuilder: (context) => `Review this file: ${context.filepath}\n\nCode:\n${context.code}\n\nObjective: ${context.objective}`
    },
    sendCurrentFileToSwarm: {
        id: 'sendCurrentFileToSwarm',
        title: 'Send File to Swarm',
        description: 'Send current file and objective to Karl Swarm.',
        requiresFile: true,
        targetTab: 'swarm',
        promptBuilder: (context) => `Implement the changes in: ${context.filepath}\n\nCode:\n${context.code}\n\nObjective: ${context.objective}`
    },
    reviewStagedDiff: {
        id: 'reviewStagedDiff',
        title: 'Review Staged Diff',
        description: 'Review the staged git diff.',
        requiresGit: true,
        targetTab: 'git',
        promptBuilder: (context) => `Review this staged git diff:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    reviewUnstagedDiff: {
        id: 'reviewUnstagedDiff',
        title: 'Review Unstaged Diff',
        description: 'Review the unstaged git diff.',
        requiresGit: true,
        targetTab: 'git',
        promptBuilder: (context) => `Review this unstaged git diff:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    reviewCombinedDiff: {
        id: 'reviewCombinedDiff',
        title: 'Review Combined Diff',
        description: 'Review all staged and unstaged changes.',
        requiresGit: true,
        targetTab: 'git',
        promptBuilder: (context) => `Review the combined git diff (all modified files):\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    generateCommitMessage: {
        id: 'generateCommitMessage',
        title: 'Generate Commit Message',
        description: 'Generate a conventional commit message from staged changes.',
        requiresGit: true,
        targetTab: 'git',
        promptBuilder: (context) => `Generate a conventional commit message from this staged diff:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    branchSummary: {
        id: 'branchSummary',
        title: 'Summarize Git Branch',
        description: 'Summarize the current branch status and commits.',
        requiresGit: true,
        targetTab: 'git',
        promptBuilder: (context) => `Summarize current git branch state:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    explainDiagnostics: {
        id: 'explainDiagnostics',
        title: 'Explain Diagnostics',
        description: 'Explain all workspace diagnostics.',
        targetTab: 'diagnostics',
        promptBuilder: (context) => `Explain these workspace diagnostics:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    explainCurrentFileDiagnostics: {
        id: 'explainCurrentFileDiagnostics',
        title: 'Explain File Diagnostics',
        description: 'Explain active file diagnostics.',
        requiresFile: true,
        targetTab: 'diagnostics',
        promptBuilder: (context) => `Explain these diagnostics in active file:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    askWorkspace: {
        id: 'askWorkspace',
        title: 'Ask About Workspace',
        description: 'Ask Karl about the workspace architecture.',
        targetTab: 'chat',
        promptBuilder: (context) => `Question about the workspace:\n\nObjective: ${context.objective}`
    },
    createImplementationPlan: {
        id: 'createImplementationPlan',
        title: 'Create Implementation Plan',
        description: 'Create an implementation plan from selected files.',
        targetTab: 'swarm',
        promptBuilder: (context) => `Create an implementation plan across the selected files:\n\n${context.code}\n\nObjective: ${context.objective}`
    },
    searchKbSelection: {
        id: 'searchKbSelection',
        title: 'Search KB',
        description: 'Search the Knowledge Base for selected text.',
        requiresSelection: true,
        requiresFile: true,
        targetTab: 'knowledge',
        promptBuilder: (context) => `${context.code}`
    },
    analyzeImage: {
        id: 'analyzeImage',
        title: 'Analyze Image',
        description: 'Analyze an image using Karl Vision.',
        targetTab: 'vision',
        promptBuilder: (context) => `Analyze this image at ${context.filepath}\n\nObjective: ${context.objective}`
    },
    reviewScreenshotError: {
        id: 'reviewScreenshotError',
        title: 'Review Screenshot Error',
        description: 'Review screenshot of an error.',
        targetTab: 'vision',
        promptBuilder: (context) => `Review this error screenshot at ${context.filepath}\n\nObjective: ${context.objective}`
    }
};

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

    // Register all workflows
    Object.keys(WORKFLOW_REGISTRY).forEach(id => {
        register(`karl.${id}`, (uri) => runWorkflow(sidebarProvider, WORKFLOW_REGISTRY[id], uri));
    });

    register('karl.ingestActiveFile', (uri) => sendActiveFileToKb(sidebarProvider, uri));
    register('karl.ingestWorkspaceFolder', (uri) => sendWorkspaceFolderToKb(sidebarProvider, uri));
    register('karl.openReviewBay', async () => {
        await revealKarlPanel(sidebarProvider);
        sidebarProvider.postMessageToWebview({ command: 'open_review_bay' });
    });

    // Synchronize cockpit state on events
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(() => {
            sendActiveStateToWebview(sidebarProvider);
        })
    );

    context.subscriptions.push(
        vscode.languages.onDidChangeDiagnostics(() => {
            sendActiveStateToWebview(sidebarProvider);
        })
    );
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

function packageContext(raw, label, summaryOnly = false) {
    const text = String(raw || '');
    const originalChars = text.length;
    if (originalChars <= MAX_CONTEXT_CHARS && !summaryOnly) {
        return {
            code: text,
            meta: { label, originalChars, sentChars: originalChars, truncated: false, summaryOnly: false }
        };
    }
    const head = text.slice(0, Math.floor(SUMMARY_CONTEXT_CHARS * 0.65));
    const tail = text.slice(-Math.floor(SUMMARY_CONTEXT_CHARS * 0.35));
    const notice = [
        `[Karl context notice: ${label} was ${originalChars} characters and exceeded the safe extension payload threshold of ${MAX_CONTEXT_CHARS}.`,
        `The extension sent a bounded head/tail summary of ${head.length + tail.length} characters. Ask for a narrower file, selection, or diff if full precision is needed.]`,
        ''
    ].join('\n');
    return {
        code: `${notice}${head}\n\n[Karl context notice: middle omitted]\n\n${tail}`,
        meta: { label, originalChars, sentChars: notice.length + head.length + tail.length, truncated: true, summaryOnly: true }
    };
}

async function runWorkflow(sidebarProvider, workflow, customUri = null) {
    const context = await buildWorkflowContext(workflow, sidebarProvider, customUri);
    if (!context) return;

    let finalCode = context.code;
    let isTruncated = false;
    let isSummary = false;
    const originalChars = finalCode.length;

    // Check size limit warning threshold (30,000 characters)
    if (originalChars > 30000) {
        const selection = await vscode.window.showWarningMessage(
            `The packaged context is large (${originalChars} characters). How would you like to proceed?`,
            'Send Full Context',
            'Send Bounded Summary (Head/Tail)',
            'Cancel'
        );

        if (selection === 'Cancel' || !selection) {
            return;
        }

        if (selection === 'Send Bounded Summary (Head/Tail)') {
            isSummary = true;
        }
    }

    const packaged = packageContext(finalCode, workflow.title, isSummary);
    finalCode = packaged.code;
    isTruncated = packaged.meta.truncated;
    isSummary = packaged.meta.summaryOnly;

    // Now reveal sidebar provider and send task/question
    await revealKarlPanel(sidebarProvider);

    if (workflow.id === 'searchKbSelection') {
        sidebarProvider.postMessageToWebview({
            command: 'search_kb_text',
            query: finalCode
        });
        return;
    }

    sidebarProvider.postMessageToWebview({
        command: 'start_workflow',
        workflowId: workflow.id,
        data: {
            mode: workflow.title,
            objective: context.objective || workflow.description,
            code: finalCode,
            filepath: context.filepath || workflow.title,
            workspace_path: currentWorkspacePath(context.filepath),
            targetTab: workflow.targetTab,
            context_meta: {
                label: workflow.title,
                originalChars,
                sentChars: finalCode.length,
                truncated: isTruncated,
                summaryOnly: isSummary
            }
        }
    });
}

async function runWorkflowById(sidebarProvider, workflowId, payload = {}) {
    const workflow = WORKFLOW_REGISTRY[workflowId];
    if (workflow) {
        await runWorkflow(sidebarProvider, workflow);
    }
}

async function buildWorkflowContext(workflow, sidebarProvider, customUri = null) {
    let code = '';
    let filepath = '';
    let objective = '';

    const editor = vscode.window.activeTextEditor;

    if (workflow.requiresSelection) {
        if (!editor) {
            vscode.window.showErrorMessage('No active text editor found.');
            return null;
        }
        const selection = editor.selection;
        code = editor.document.getText(selection);
        if (!code.trim()) {
            vscode.window.showWarningMessage('Please highlight some code first.');
            return null;
        }
        filepath = editor.document.uri.fsPath;
    } else if (workflow.requiresFile) {
        const pathFromUri = customUri && customUri.fsPath;
        if (pathFromUri) {
            filepath = pathFromUri;
            try {
                const stat = await fs.promises.stat(filepath);
                if (stat.isFile()) {
                    code = await fs.promises.readFile(filepath, 'utf8');
                }
            } catch (err) {
                vscode.window.showErrorMessage(`Failed to read file: ${err.message}`);
                return null;
            }
        } else {
            if (!editor) {
                vscode.window.showErrorMessage('No active text editor found.');
                return null;
            }
            filepath = editor.document.uri.fsPath;
            code = editor.document.getText();
        }
    }

    if (workflow.requiresGit) {
        const workspacePath = currentWorkspacePath('');
        if (!workspacePath) {
            vscode.window.showWarningMessage('Open a workspace before using git workflows.');
            return null;
        }
        try {
            if (workflow.id === 'reviewStagedDiff' || workflow.id === 'generateCommitMessage') {
                code = await execGit(['diff', '--staged'], workspacePath);
            } else if (workflow.id === 'reviewUnstagedDiff') {
                code = await execGit(['diff'], workspacePath);
            } else if (workflow.id === 'reviewCombinedDiff') {
                code = await execGit(['diff', 'HEAD'], workspacePath);
            } else if (workflow.id === 'branchSummary') {
                const [branch, status, recent] = await Promise.all([
                    execGit(['branch', '--show-current'], workspacePath),
                    execGit(['status', '--short', '--branch'], workspacePath),
                    execGit(['log', '--oneline', '--decorate', '-12'], workspacePath)
                ]);
                code = `Current branch: ${branch.trim() || '(detached)'}\n\nStatus:\n${status}\n\nRecent commits:\n${recent}`;
            }
        } catch (err) {
            vscode.window.showErrorMessage(`Git execution failed: ${err.message}`);
            return null;
        }

        if (workflow.id !== 'branchSummary' && !code.trim()) {
            vscode.window.showInformationMessage('No git changes found.');
            return null;
        }
    }

    if (workflow.id === 'explainDiagnostics' || workflow.id === 'explainCurrentFileDiagnostics') {
        const currentFileOnly = (workflow.id === 'explainCurrentFileDiagnostics');
        const diagnostics = groupedDiagnostics(currentFileOnly);
        if (!Object.keys(diagnostics.files).length) {
            vscode.window.showInformationMessage(currentFileOnly ? 'No diagnostics found for the active file.' : 'No current diagnostics found.');
            return null;
        }
        code = JSON.stringify(diagnostics, null, 2);
    }

    if (workflow.id === 'analyzeImage' || workflow.id === 'reviewScreenshotError') {
        let pathFromUri = customUri && customUri.fsPath;
        if (!pathFromUri && editor) {
            pathFromUri = editor.document.uri.fsPath;
        }
        if (!pathFromUri) {
            const uris = await vscode.window.showOpenDialog({
                canSelectFiles: true,
                canSelectFolders: false,
                canSelectMany: false,
                filters: {
                    'Images': ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']
                },
                title: 'Select an image for Karl Vision'
            });
            if (uris && uris[0]) {
                pathFromUri = uris[0].fsPath;
            }
        }
        if (!pathFromUri) return null;
        filepath = pathFromUri;
        code = `Image File: ${filepath}`;
    }

    // Prompt user for objective if required
    const needsPrompt = [
        'fixSelection', 'explainSelection', 'generateTests', 'reviewActiveFile',
        'sendCurrentFileToSwarm', 'createImplementationPlan', 'askWorkspace',
        'analyzeImage', 'reviewScreenshotError'
    ].includes(workflow.id);

    if (needsPrompt) {
        let defaultValue = workflow.description;
        if (workflow.id === 'generateTests') defaultValue = 'Generate focused tests for the active file. Preserve existing behavior.';
        if (workflow.id === 'reviewActiveFile') defaultValue = 'Review the active file for bugs, regressions, missing tests, and concrete improvements.';
        if (workflow.id === 'sendCurrentFileToSwarm') defaultValue = 'Implement the requested change in this file and verify behavior.';
        if (workflow.id === 'analyzeImage') defaultValue = 'Describe this image, extract text (OCR), and identify any UI or visual issues.';
        if (workflow.id === 'reviewScreenshotError') defaultValue = 'Review this screenshot for error messages, stack traces, and propose fixes.';

        const userObjective = await vscode.window.showInputBox({
            prompt: `${workflow.title}: What should Karl do?`,
            value: defaultValue
        });
        if (userObjective === undefined) return null;
        objective = userObjective.trim() || defaultValue;
    }

    return { code, filepath, objective };
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

async function getGitBranch(workspacePath) {
    if (!workspacePath) return '';
    try {
        const branch = await execGit(['branch', '--show-current'], workspacePath);
        return branch.trim();
    } catch {
        return '';
    }
}

function getDiagnosticsStats() {
    const severityName = ['error', 'warning', 'info', 'hint'];
    const counts = { error: 0, warning: 0, info: 0, hint: 0 };
    for (const [uri, items] of vscode.languages.getDiagnostics()) {
        items.forEach(item => {
            const severity = severityName[item.severity] || 'info';
            counts[severity] += 1;
        });
    }
    return counts;
}

async function sendActiveStateToWebview(sidebarProvider) {
    const workspacePath = currentWorkspacePath('');
    const activeFile = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.document.uri.fsPath : '';
    const gitBranch = await getGitBranch(workspacePath);
    const diagnostics = getDiagnosticsStats();
    const diagnosticsDetails = groupedDiagnostics(false);

    sidebarProvider.postMessageToWebview({
        command: 'cockpit_state_update',
        state: {
            workspacePath,
            activeFile,
            gitBranch,
            diagnostics,
            diagnosticsDetails,
            pendingEditsCount: sidebarProvider.pendingEdits.size
        }
    });
}

function groupedDiagnostics(currentFileOnly = false) {
    const activeFile = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.document.uri.fsPath : '';
    const groups = new Map();
    const counts = { error: 0, warning: 0, info: 0, hint: 0 };
    const severityName = ['error', 'warning', 'info', 'hint'];
    for (const [uri, items] of vscode.languages.getDiagnostics()) {
        if (currentFileOnly && uri.fsPath !== activeFile) continue;
        const fileItems = items.slice(0, 25).map(item => {
            const severity = severityName[item.severity] || 'info';
            counts[severity] += 1;
            return {
                severity,
                message: item.message,
                source: item.source || '',
                line: item.range.start.line + 1,
                character: item.range.start.character + 1
            };
        });
        if (fileItems.length) groups.set(uri.fsPath, fileItems);
    }
    return { counts, files: Object.fromEntries(groups) };
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
                default:
                    break;
            }
        });

        // Trigger cockpit refresh immediately
        sendActiveStateToWebview(this);
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
        sendActiveStateToWebview(this);
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
        sendActiveStateToWebview(this);
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
            edit.status = 'applied';
            edit.backupPath = backupPath;
            this.pendingEdits.set(editId, edit);
            this.postMessageToWebview({ command: 'file_edit_applied', editId, backupExists: fs.existsSync(backupPath) });
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
        sendActiveStateToWebview(this);
    }

    async openFile(editId) {
        const edit = this.pendingEdits.get(editId);
        if (edit && fs.existsSync(edit.filepath)) {
            await vscode.window.showTextDocument(vscode.Uri.file(edit.filepath), { preview: false });
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
        if (!fs.existsSync(backupPath)) {
            vscode.window.showWarningMessage('No backup file found to rollback.');
            return;
        }
        await fs.promises.copyFile(backupPath, edit.filepath);
        await fs.promises.unlink(backupPath);
        edit.status = 'rolled_back';
        this.pendingEdits.set(editId, edit);
        this.postMessageToWebview({ command: 'file_edit_rolled_back', editId });
        vscode.window.showInformationMessage(`Rolled back ${edit.filename}.`);
        sendActiveStateToWebview(this);
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
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} https:; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src ws://localhost:* ws://127.0.0.1:* http://localhost:* http://127.0.0.1:*;">
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
                        <label>Port <input id="bridgePort" type="number" min="1" max="65535" value="${port}"></label>
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
    <script nonce="${nonce}" src="${jsUri}"></script>
</body>
</html>`;
    }
}

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = { activate, deactivate };
