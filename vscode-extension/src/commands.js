const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const { packageContext } = require('./fileOps');
const { execGit } = require('./gitOps');

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

function currentWorkspacePath(fallbackFile) {
    if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
        return vscode.workspace.workspaceFolders[0].uri.fsPath;
    }
    return fallbackFile ? path.dirname(fallbackFile) : '';
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

async function revealKarlPanel(sidebarProvider) {
    await vscode.commands.executeCommand('workbench.view.extension.karl-swarm');
    await sidebarProvider.waitForWebview();
}

async function runWorkflow(sidebarProvider, workflow, customUri = null) {
    const context = await buildWorkflowContext(workflow, sidebarProvider, customUri);
    if (!context) return;

    let finalCode = context.code;
    let isTruncated = false;
    let isSummary = false;
    const originalChars = finalCode.length;

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

module.exports = {
    WORKFLOW_REGISTRY,
    currentWorkspacePath,
    groupedDiagnostics,
    revealKarlPanel,
    runWorkflow,
    runWorkflowById,
    buildWorkflowContext,
    sendActiveFileToKb,
    sendWorkspaceFolderToKb
};
