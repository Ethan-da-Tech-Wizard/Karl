// @ts-check
const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
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

/**
 * Read the Karl service-discovery descriptor written by the Python backend.
 * Returns the parsed JSON or null if the file is absent / unreadable.
 * @returns {{ active_port: number, token: string, bound_at: string } | null}
 */
function readServiceDiscovery() {
    const discoveryPath = path.join(os.homedir(), '.karl', 'service_discovery.json');
    try {
        const raw = fs.readFileSync(discoveryPath, 'utf8');
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function activate(context) {
    const sidebarProvider = new KarlSidebarProvider(context);

    // Pre-populate the provider with the discovered endpoint so that
    // connectToBridge() can use the correct port without manual config.
    const discovery = readServiceDiscovery();
    if (discovery && discovery.active_port) {
        sidebarProvider.discoveredPort = discovery.active_port;
        sidebarProvider.discoveredToken = discovery.token || '';
    }
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

    const inlineProvider = new MiniGptInlineCompletionProvider(workspacePath, sidebarProvider);
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
     * @param {import('./src/sidebarProvider').KarlSidebarProvider} [sidebarProvider]
     */
    constructor(workspacePath, sidebarProvider) {
        this.workspacePath = workspacePath;
        this.sidebarProvider = sidebarProvider || null;
        /** @type {ReturnType<typeof setTimeout> | null} */
        this.debounceTimeout = null;
        /** @type {import('child_process').ChildProcess | null} */
        this._pendingProc = null;
    }

    /**
     * @param {vscode.TextDocument} document
     * @param {vscode.Position} position
     * @param {vscode.InlineCompletionContext} context
     * @param {vscode.CancellationToken} token
     * @returns {Promise<vscode.InlineCompletionItem[] | undefined>}
     */
    provideInlineCompletionItems(document, position, context, token) {
        const weightsPath = path.join(this.workspacePath, "data", "mini_gpt", "weights.pt");
        if (!fs.existsSync(weightsPath)) {
            return Promise.resolve(undefined);
        }

        const lineText = document.lineAt(position.line).text.substring(0, position.character);
        if (!lineText.trim()) {
            return Promise.resolve(undefined);
        }

        // Clear any pending debounce from the previous keypress
        if (this.debounceTimeout !== null) {
            clearTimeout(this.debounceTimeout);
            this.debounceTimeout = null;
        }

        return new Promise((resolve) => {
            // Abort immediately if VS Code has already cancelled this request
            if (token.isCancellationRequested) {
                resolve(undefined);
                return;
            }

            // Resolve early if VS Code cancels while we are waiting (user kept typing).
            // Also kills any already-spawned subprocess so it cannot hold VRAM.
            const cancelListener = token.onCancellationRequested(() => {
                if (this.debounceTimeout !== null) {
                    clearTimeout(this.debounceTimeout);
                    this.debounceTimeout = null;
                }
                if (this._pendingProc) {
                    this._pendingProc.kill('SIGTERM');
                    this._pendingProc = null;
                }
                resolve(undefined);
            });

            this.debounceTimeout = setTimeout(async () => {
                this.debounceTimeout = null;
                cancelListener.dispose();

                if (token.isCancellationRequested) {
                    resolve(undefined);
                    return;
                }

                try {
                    const completion = await this.generateCompletion(lineText, token);
                    if (!token.isCancellationRequested && completion && completion.trim().length > 0) {
                        const item = new vscode.InlineCompletionItem(completion);
                        item.range = new vscode.Range(position, position);
                        resolve([item]);
                    } else {
                        resolve(undefined);
                    }
                } catch (err) {
                    console.error('[Mini-GPT Inline Completion Error]:', err);
                    resolve(undefined);
                }
            }, 500);
        });
    }

    /**
     * @param {string} prompt
     * @param {vscode.CancellationToken} [token]
     * @returns {Promise<string>}
     */
    generateCompletion(prompt, token) {
        const sidebarProvider = this.sidebarProvider;
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
            this._pendingProc = proc;

            // Settled flag — prevents double-resolve/reject when both the hard
            // timeout and the close event fire (e.g. kill → close with code -2).
            let settled = false;

            /** @type {ReturnType<typeof setTimeout> | null} */
            let hardTimer = null;
            /** @type {ReturnType<typeof setTimeout> | null} */
            let sigkillTimer = null;
            /** @type {vscode.Disposable | null} */
            let cancelListener = null;

            // Escalating kill: SIGTERM first, SIGKILL after 500 ms if process hangs.
            const killProc = () => {
                proc.kill('SIGTERM');
                sigkillTimer = setTimeout(() => { proc.kill('SIGKILL'); }, 500);
            };

            // Single-call settle — clears all timers and listeners then calls fn.
            const settle = (fn, value) => {
                if (settled) return;
                settled = true;
                this._pendingProc = null;
                if (hardTimer)    { clearTimeout(hardTimer);    hardTimer    = null; }
                if (sigkillTimer) { clearTimeout(sigkillTimer); sigkillTimer = null; }
                if (cancelListener) { cancelListener.dispose(); cancelListener = null; }
                proc.stdout.removeAllListeners();
                proc.stderr.removeAllListeners();
                proc.removeAllListeners();
                fn(value);
            };

            // VS Code cancellation: kill the subprocess and resolve empty.
            if (token) {
                cancelListener = token.onCancellationRequested(() => {
                    killProc();
                    settle(resolve, '');
                });
            }

            let stdout = '';
            let stderr = '';

            // Hard 2-second execution guard.
            hardTimer = setTimeout(() => {
                killProc();
                settle(reject, new Error('Mini-GPT generation timed out.'));
            }, 2000);

            proc.stdout.on('data', (/** @type {Buffer} */ data) => { stdout += data.toString(); });
            proc.stderr.on('data', (/** @type {Buffer} */ data) => { stderr += data.toString(); });

            // Spawn errors (e.g. python3 not on PATH) — logged silently, no popup.
            proc.on('error', (/** @type {Error} */ err) => {
                console.error('[Mini-GPT] Spawn error:', err.message);
                settle(reject, err);
            });

            proc.on('close', (/** @type {number | null} */ code, /** @type {string | null} */ signal) => {
                // SIGSEGV: exit code 139 or SIGSEGV signal — likely AVX incompatibility in llama-cpp-python
                if ((code === 139 || signal === 'SIGSEGV') && sidebarProvider) {
                    console.error('[Mini-GPT] Segmentation fault — likely AVX incompatibility. code:', code, 'signal:', signal);
                    sidebarProvider.postMessageToWebview({
                        command: 'completion_diagnostic_failed',
                        exitCode: code,
                        exitSignal: signal,
                        reason: 'sigsegv',
                        message: 'llama-cpp-python SIGSEGV — rebuild without AVX: CMAKE_ARGS="-DGGML_AVX=OFF -DGGML_AVX2=OFF" pip install --force-reinstall --no-cache-dir llama-cpp-python'
                    });
                // OOM SIGKILL: exit code 137 — system killed the process due to memory pressure
                } else if ((code === 137 || signal === 'SIGKILL') && sidebarProvider) {
                    console.error('[Mini-GPT] OOM SIGKILL detected. code:', code, 'signal:', signal);
                    sidebarProvider.postMessageToWebview({
                        command: 'completion_diagnostic_failed',
                        exitCode: code,
                        exitSignal: signal,
                        reason: 'oom',
                        message: 'llama-cpp-python was killed by the OS (OOM). Load a smaller model or reduce context size.'
                    });
                }
                settle(
                    code === 0 ? resolve : reject,
                    code === 0 ? stdout  : new Error(stderr || `Python exited with code ${code}`)
                );
            });
        });
    }
}

function deactivate() {
    console.log('Karl extension deactivated.');
}

module.exports = { activate, deactivate };
