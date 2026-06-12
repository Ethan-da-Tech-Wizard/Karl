const vscode = acquireVsCodeApi();
const boot = window.KARL_BOOTSTRAP || {};

let socket = null;
let reconnectTimer = null;
let runtimeStatusTimer = null;
let bridgeMetaTimer = null;
let chatFinished = true;
let labRunning = false;
let currentLabTarget = '';
let labOutputA = '';
let labOutputB = '';
let kbSelectedSource = '';
let connectionState = 'offline';
let pendingEdits = new Map();
let manualDisconnect = false;
let persistTimer = null;
let recentTasks = [];
let recentKbQueries = [];
let taskQueue = [];
let activeTaskId = '';
let activeWorkflowId = '';
let lastHeartbeatAt = null;
let lastConnectedAt = null;
let lastBridgeError = '';
let kbQueue = [];
let kbQueueRunning = false;
let conversationBranches = [];
let activeBranchId = '';
let currentConversationInput = '';
let responseThinkActive = false;
let currentResponseText = '';
let nextReconnectSec = 5;
let lastKbSnapshot = {};
let lastKbResults = [];

const $ = (id) => document.getElementById(id);

function hydrate() {
    const persisted = boot.persisted || {};
    $('workspace').value = persisted.workspace || boot.workspaceFolder || '';
    $('bridgePort').value = persisted.port || boot.port || 8080;
    $('taskMode').value = persisted.taskMode || 'Custom Task';
    $('themeSelect').value = persisted.theme || 'obsidian-core';
    $('customAccent').value = persisted.customAccent || themeById($('themeSelect').value).vars['--karl-accent'];
    $('layoutSelect').value = persisted.layout || 'cockpit';
    
    // Aesthetic settings checkboxes
    $('syncVsCodeTheme').checked = persisted.syncVsCodeTheme !== false;
    $('highContrastMode').checked = !!persisted.highContrastMode;
    $('reducedMotion').checked = !!persisted.reducedMotion;
    $('animationIntensity').value = persisted.animationIntensity !== undefined ? persisted.animationIntensity : 100;

    const rawTasks = Array.isArray(persisted.recentTasks) ? persisted.recentTasks : [];
    recentTasks = rawTasks.filter(t => t && typeof t.workflowId === 'string' && typeof t.title === 'string' && typeof t.objective === 'string').slice(0, 15);

    const rawQueries = Array.isArray(persisted.recentKbQueries) ? persisted.recentKbQueries : [];
    recentKbQueries = rawQueries.filter(q => typeof q === 'string').slice(0, 12);

    const rawBranches = Array.isArray(persisted.conversationBranches) ? persisted.conversationBranches : [];
    conversationBranches = rawBranches.filter(b => b && typeof b.id === 'string' && typeof b.title === 'string' && Array.isArray(b.turns)).slice(0, 20);
    
    activeBranchId = persisted.activeBranchId || (conversationBranches[0] && conversationBranches[0].id) || '';
    
    applyAppearance();
    if (persisted.workspaceTab) {
        switchWorkspace(persisted.workspaceTab);
    } else {
        switchWorkspace('cockpit');
    }
}

function persist() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
        vscode.postMessage({
            command: 'persist_state',
            state: {
                workspace: $('workspace').value,
                port: Number($('bridgePort').value) || boot.port || 8080,
                taskMode: $('taskMode').value,
                workspaceTab: document.querySelector('.tab.active')?.dataset.workspace || 'cockpit',
                theme: $('themeSelect').value,
                customAccent: $('customAccent').value,
                layout: $('layoutSelect').value,
                syncVsCodeTheme: $('syncVsCodeTheme').checked,
                highContrastMode: $('highContrastMode').checked,
                reducedMotion: $('reducedMotion').checked,
                animationIntensity: Number($('animationIntensity').value),
                recentTasks: recentTasks.slice(0, 15),
                recentKbQueries: recentKbQueries.slice(0, 12),
                conversationBranches: conversationBranches.slice(0, 20),
                activeBranchId
            }
        });
    }, 250);
}

function initializeAppearance() {
    $('themeSelect').innerHTML = window.KARL_THEMES.map(theme => {
        return `<option value="${escapeHtml(theme.id)}">${escapeHtml(theme.name)}</option>`;
    }).join('');
    $('layoutSelect').innerHTML = window.KARL_LAYOUTS.map(layout => {
        return `<option value="${escapeHtml(layout.id)}">${escapeHtml(layout.name)}</option>`;
    }).join('');
    renderThemeCatalog();
}

function themeById(id) {
    const themes = Array.isArray(window.KARL_THEMES) ? window.KARL_THEMES : [];
    return themes.find(theme => theme && theme.id === id) || themes[0] || { id: 'obsidian-core', vars: { '--karl-accent': '#00c2ff' }, name: 'Obsidian Core', description: '' };
}

function layoutById(id) {
    const layouts = Array.isArray(window.KARL_LAYOUTS) ? window.KARL_LAYOUTS : [];
    return layouts.find(layout => layout && layout.id === id) || layouts[0] || { id: 'cockpit', name: 'Cockpit', description: '' };
}

function applyAppearance() {
    const theme = themeById($('themeSelect').value);
    const layout = layoutById($('layoutSelect').value);
    const vars = theme.vars || {};
    const customAccent = $('customAccent').value || vars['--karl-accent'] || '#00c2ff';
    
    Object.entries(vars).forEach(([key, value]) => {
        document.documentElement.style.setProperty(key, value);
    });
    
    document.documentElement.style.setProperty('--karl-accent', customAccent);
    document.body.dataset.layout = layout.id;
    $('themeDescription').innerText = theme.description || '';
    $('layoutDescription').innerText = layout.description || '';

    // Presets variables modifications
    if ($('syncVsCodeTheme').checked) {
        document.documentElement.style.setProperty('--karl-bg', 'color-mix(in srgb, var(--vscode-sideBar-background) 82%, #020817)');
        document.documentElement.style.setProperty('--karl-panel', 'color-mix(in srgb, var(--vscode-editor-background) 88%, #07162a)');
        document.documentElement.style.setProperty('--karl-border', 'color-mix(in srgb, var(--vscode-widget-border) 60%, #0ea5ff)');
        document.documentElement.style.setProperty('--karl-text', 'var(--vscode-foreground)');
    }

    if ($('highContrastMode').checked) {
        document.body.dataset.layoutContrast = 'high';
    } else {
        delete document.body.dataset.layoutContrast;
    }

    const intensity = Number($('animationIntensity').value);
    document.documentElement.style.setProperty('--animation-intensity', intensity / 100);

    if ($('reducedMotion').checked || intensity === 0) {
        document.body.dataset.motion = 'reduced';
    } else {
        delete document.body.dataset.motion;
    }

    renderThemeCatalog();
    persist();
}

function switchWorkspace(wsId) {
    document.querySelectorAll('.workspace').forEach(section => section.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.dataset.workspace === wsId));
    const section = $(`workspace-${wsId}`);
    if (section) {
        section.classList.add('active');
    }

    if (wsId === 'settings') {
        loadModels();
    }
    if (wsId === 'knowledge') {
        loadKbSources();
        loadCodexTopics();
    }
    if (wsId === 'lab') loadPromptPairs();
    
    // Request an update to sync cockpit variables
    vscode.postMessage({ command: 'get_cockpit_state' });
    persist();
}
