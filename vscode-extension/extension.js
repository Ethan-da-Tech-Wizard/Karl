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

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = { activate, deactivate };
