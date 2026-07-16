// @ts-check
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const vscode = require('vscode');

const MAX_CONTEXT_CHARS = 70000;
const SUMMARY_CONTEXT_CHARS = 18000;

/**
 * Packages file or git context into a bounded payload.
 * @param {any} raw
 * @param {string} label
 * @param {boolean} [summaryOnly]
 * @returns {{code: string, meta: {label: string, originalChars: number, sentChars: number, truncated: boolean, summaryOnly: boolean}}}
 */
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

/**
 * Checks if a file exists.
 * @param {string} filepath
 * @returns {Promise<boolean>}
 */
async function checkFileExists(filepath) {
    try {
        await vscode.workspace.fs.stat(vscode.Uri.file(filepath));
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Writes content to a temp file and opens a vscode diff.
 * @param {string} filename
 * @param {string} targetPath
 * @param {string} content
 * @param {string} title
 * @returns {Promise<string>}
 */
async function writeTempFileAndDiff(filename, targetPath, content, title) {
    const randomHex = crypto.randomBytes(8).toString('hex');
    const tempProposedDir = path.join(os.tmpdir(), `karl-proposed-${randomHex}`);
    const proposedPath = path.join(tempProposedDir, filename);
    const proposedUri = vscode.Uri.file(proposedPath);

    await vscode.workspace.fs.createDirectory(vscode.Uri.file(tempProposedDir));
    const encoder = new TextEncoder();
    await vscode.workspace.fs.writeFile(proposedUri, encoder.encode(content));

    await vscode.commands.executeCommand(
        'vscode.diff',
        vscode.Uri.file(targetPath),
        proposedUri,
        title
    );
    return proposedPath;
}

module.exports = {
    MAX_CONTEXT_CHARS,
    SUMMARY_CONTEXT_CHARS,
    packageContext,
    checkFileExists,
    writeTempFileAndDiff
};
