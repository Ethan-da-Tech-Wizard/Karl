// Mock the 'vscode' module before requiring any file that depends on it
const Module = require('module');
const originalRequire = Module.prototype.require;
Module.prototype.require = function(id) {
    if (id === 'vscode') {
        return {
            Uri: {
                file: (path) => ({ fsPath: path })
            },
            commands: {
                executeCommand: async () => {}
            }
        };
    }
    return originalRequire.apply(this, arguments);
};

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const { packageContext } = require('../fileOps');

console.log('--- Starting Karl Extension Unit Tests ---');

// 1. Test packageContext
console.log('Testing packageContext...');
const smallText = 'Hello World';
const packagedSmall = packageContext(smallText, 'TestLabel', false);
assert.strictEqual(packagedSmall.code, smallText);
assert.strictEqual(packagedSmall.meta.truncated, false);
assert.strictEqual(packagedSmall.meta.summaryOnly, false);

const largeText = 'A'.repeat(80000);
const packagedLarge = packageContext(largeText, 'TestLabel', false);
assert.strictEqual(packagedLarge.meta.truncated, true);
assert.strictEqual(packagedLarge.meta.summaryOnly, true);
assert.ok(packagedLarge.code.includes('middle omitted'));

// 2. Test escapeHtml
console.log('Testing escapeHtml...');
const renderCode = fs.readFileSync(path.join(__dirname, '../../media/karl_render.js'), 'utf8');
const sandbox = {
    $: () => {},
    document: {},
    window: {},
    lastKbSnapshot: {},
    kbSelectedSource: '',
    lastKbResults: [],
    pendingEdits: new Map(),
    conversationBranches: [],
    activeBranchId: '',
    responseThinkActive: false
};
vm.createContext(sandbox);
vm.runInContext(renderCode, sandbox);
const escapeHtml = sandbox.escapeHtml;

assert.strictEqual(escapeHtml('<div>&"\'</div>'), '&lt;div&gt;&amp;&quot;&#39;&lt;/div&gt;');
assert.strictEqual(escapeHtml(''), '');
assert.strictEqual(escapeHtml(null), '');

console.log('Testing buildModelCard...');
const buildModelCard = sandbox.buildModelCard;
const cardHtml = buildModelCard('MyModel', 'meta info', '<button>Btn</button>');
assert.ok(cardHtml.includes('MyModel'));
assert.ok(cardHtml.includes('meta info'));
assert.ok(cardHtml.includes('<button>Btn</button>'));

console.log('--- All Tests Passed! ---');
