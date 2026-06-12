// @ts-check
const vscode = require('vscode');
const { KarlSidebarProvider, sendActiveStateToWebview } = require('./src/sidebarProvider');
const {
    WORKFLOW_REGISTRY,
    runWorkflow,
    sendActiveFileToKb,
    sendWorkspaceFolderToKb,
    revealKarlPanel
} = require('./src/commands');

function activate(context) {
    const sidebarProvider = new KarlSidebarProvider(context);
    const provider = sidebarProvider;
    Object.defineProperty(provider, '_view', {
        get() { return this.webviewView; }
    });
    context.subscriptions.push(sidebarProvider);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('karl.sidebarView', sidebarProvider)
    );

    const register = (command, handler) => {
        context.subscriptions.push(vscode.commands.registerCommand(command, handler));
    };

    register('karl.openSidebar', () => {
        vscode.commands.executeCommand('workbench.view.extension.karl-swarm');
    });

    register('karl.focus', () => {
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

    // ── Inline Editor Commands ─────────────────────────────────────────────────────
  
    function _getSelectionOrFile(editor) {
        if (!editor) return '';
        const sel = editor.selection;
        if (!sel.isEmpty) {
            return editor.document.getText(sel);
        }
        return editor.document.getText();
    }

    function _sendToKarlWebview(command, payload) {
        if (provider && provider._view) {
            provider._view.webview.postMessage({ command, ...payload });
        } else {
            vscode.window.showWarningMessage('Karl panel is not open. Open it first with Ctrl+Shift+K A.');
        }
    }

    context.subscriptions.push(
        vscode.commands.registerCommand('karl.explainSelection', async () => {
            const editor = vscode.window.activeTextEditor;
            const code = _getSelectionOrFile(editor);
            if (!code.trim()) {
                vscode.window.showWarningMessage('No code selected or file is empty.');
                return;
            }
            const lang = editor ? editor.document.languageId : 'code';
            const message = `Explain the following ${lang} code clearly. Identify any issues, anti-patterns, or improvements:\n\n\`\`\`${lang}\n${code.slice(0, 4000)}\n\`\`\``;
            _sendToKarlWebview('inject_chat', { text: message, autoSend: true });
            await vscode.commands.executeCommand('karl.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('karl.refactorSelection', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || editor.selection.isEmpty) {
                vscode.window.showWarningMessage('Select code to refactor first.');
                return;
            }
            const code = editor.document.getText(editor.selection);
            const lang = editor.document.languageId;
            const message = `Refactor the following ${lang} code to be cleaner, more efficient, and better documented. Return ONLY the refactored code in a code block, no explanation:\n\n\`\`\`${lang}\n${code.slice(0, 3000)}\n\`\`\``;
            _sendToKarlWebview('inject_chat', { text: message, autoSend: true });

            // Register a one-time listener for Karl's refactor response to show as diff
            const disposable = provider._view.webview.onDidReceiveMessage(async msg => {
                if (msg.command !== 'refactor_result') return;
                disposable.dispose();
                const refactored = msg.code;
                if (!refactored) return;

                // Write refactored content to a temp untitled document and open diff
                const originalUri = editor.document.uri;
                const refactoredDoc = await vscode.workspace.openTextDocument({
                    content: refactored,
                    language: lang,
                });
                await vscode.commands.executeCommand(
                    'vscode.diff',
                    originalUri,
                    refactoredDoc.uri,
                    'Karl Refactor Preview'
                );
            });
            context.subscriptions.push(disposable);
            await vscode.commands.executeCommand('karl.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('karl.askKarl', async () => {
            const question = await vscode.window.showInputBox({
                prompt: 'Ask Karl anything...',
                placeHolder: 'e.g. How do I implement a singleton in Python?'
            });
            if (!question) return;
            _sendToKarlWebview('inject_chat', { text: question, autoSend: true });
            await vscode.commands.executeCommand('karl.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('karl.sendToSwarm', async () => {
            const editor = vscode.window.activeTextEditor;
            const code = _getSelectionOrFile(editor);
            if (!code.trim()) return;
            const objective = `Improve and refactor the following code:\n\n${code.slice(0, 2000)}`;
            _sendToKarlWebview('inject_swarm', { objective });
            await vscode.commands.executeCommand('karl.focus');
        })
    );

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

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = { activate, deactivate };
