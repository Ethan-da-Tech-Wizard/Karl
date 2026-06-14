// @ts-check
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
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

    context.subscriptions.push(
        vscode.commands.registerCommand('karl.autoTrain', async () => {
            const topic = await vscode.window.showInputBox({
                prompt: 'Enter the topic/behavior for Karl to learn (e.g., modular arithmetic):',
                placeHolder: 'e.g., binary search'
            });
            if (!topic) return;

            const adapterName = await vscode.window.showInputBox({
                prompt: 'Enter the save adapter name (e.g., math_specialist):',
                placeHolder: 'e.g., binary_search'
            });
            if (!adapterName) return;

            // Trigger training channel setup
            if (!sidebarProvider.autoTrainChannel) {
                sidebarProvider.autoTrainChannel = vscode.window.createOutputChannel("Karl Auto-Train Logs");
            }
            sidebarProvider.autoTrainChannel.show(true);
            sidebarProvider.autoTrainChannel.clear();
            sidebarProvider.autoTrainChannel.appendLine(`[SYSTEM] Starting auto-training for topic: "${topic}"...`);

            // Send RPC command
            const ok = sidebarProvider.sendRpc('start_auto_train', {
                topic,
                adapter_name: adapterName,
                count: 15,
                epochs: 3,
                lr: 2e-4
            });

            if (ok) {
                vscode.window.showInformationMessage(`Karl: Auto-training flywheel started for topic: "${topic}"! Output will stream to the Karl Auto-Train Logs channel.`);
            } else {
                vscode.window.showErrorMessage('Failed to start training. Is the Karl PyQt6 app running and connected?');
            }
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

    // Register Mini-GPT Inline Completion Provider
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const workspacePath = workspaceFolders && workspaceFolders.length > 0
        ? workspaceFolders[0].uri.fsPath
        : '/home/ethan/karl';

    const inlineProvider = new MiniGptInlineCompletionProvider(workspacePath);
    context.subscriptions.push(
        vscode.languages.registerInlineCompletionItemProvider(
            { pattern: '**' },
            inlineProvider
        )
    );
}

class MiniGptInlineCompletionProvider {
    /**
     * @param {string} workspacePath
     */
    constructor(workspacePath) {
        this.workspacePath = workspacePath;
    }

    /**
     * @param {vscode.TextDocument} document
     * @param {vscode.Position} position
     * @param {vscode.InlineCompletionContext} context
     * @param {vscode.CancellationToken} token
     */
    async provideInlineCompletionItems(document, position, context, token) {
        const weightsPath = path.join(this.workspacePath, "data", "mini_gpt", "weights.pt");
        if (!fs.existsSync(weightsPath)) {
            return undefined;
        }

        const lineText = document.lineAt(position.line).text.substring(0, position.character);
        if (!lineText.trim()) {
            return undefined;
        }

        try {
            const completion = await this.generateCompletion(lineText);
            if (completion && completion.trim().length > 0) {
                const item = new vscode.InlineCompletionItem(completion);
                item.range = new vscode.Range(position, position);
                return [item];
            }
        } catch (err) {
            console.error('[Mini-GPT Inline Completion Error]:', err);
        }

        return undefined;
    }

    /**
     * @param {string} prompt
     * @returns {Promise<string>}
     */
    generateCompletion(prompt) {
        return new Promise((resolve, reject) => {
            const pythonScript = `
import os
import sys
import json
import torch

workspace_root = sys.argv[1]
sys.path.insert(0, workspace_root)

from app.engine.mini_transformer import MiniGPT, CharTokenizer

save_dir = os.path.join(workspace_root, "data", "mini_gpt")
weights_path = os.path.join(save_dir, "weights.pt")
config_path = os.path.join(save_dir, "config.json")
tokenizer_path = os.path.join(save_dir, "tokenizer.json")

if not os.path.exists(weights_path) or not os.path.exists(config_path) or not os.path.exists(tokenizer_path):
    sys.exit(1)

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

with open(tokenizer_path, "r", encoding="utf-8") as f:
    tok_data = json.load(f)

tokenizer = CharTokenizer()
tokenizer.chars = tok_data["chars"]
tokenizer.stoi = tok_data["stoi"]
tokenizer.itos = {int(k): v for k, v in tok_data["itos"].items()}
tokenizer.vocab_size = len(tokenizer.chars)

model = MiniGPT(
    vocab_size=tokenizer.vocab_size,
    n_embd=config["n_embd"],
    n_heads=config["n_heads"],
    n_layers=config["n_layers"],
    block_size=config["block_size"]
)
model.load_state_dict(torch.load(weights_path, map_location="cpu"))
model.eval()

prompt = sys.argv[2]
encoded = tokenizer.encode(prompt)
encoded = encoded[-config["block_size"]:]

if not encoded:
    encoded = [0]

idx = torch.tensor([encoded], dtype=torch.long)
generated_ids = model.generate(idx, max_new_tokens=40, temperature=0.7, top_k=5)[0].tolist()

completion_ids = generated_ids[len(encoded):]
completion = tokenizer.decode(completion_ids)
print(completion, end="")
`;

            const proc = cp.spawn('python3', ['-c', pythonScript, this.workspacePath, prompt]);

            let stdout = '';
            let stderr = '';

            const timer = setTimeout(() => {
                proc.kill();
                reject(new Error('Mini-GPT generation timed out.'));
            }, 2000);

            proc.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            proc.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            proc.on('close', (code) => {
                clearTimeout(timer);
                if (code === 0) {
                    resolve(stdout);
                } else {
                    reject(new Error(stderr || `Python exited with code ${code}`));
                }
            });
        });
    }
}

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = { activate, deactivate };
