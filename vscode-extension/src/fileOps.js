const fs = require('fs');
const path = require('path');
const os = require('os');
const vscode = require('vscode');

const MAX_CONTEXT_CHARS = 70000;
const SUMMARY_CONTEXT_CHARS = 18000;

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

async function checkFileExists(filepath) {
    return fs.promises.access(filepath).then(() => true).catch(() => false);
}

async function writeTempFileAndDiff(filename, targetPath, content, title) {
    const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'karl-proposed-'));
    const proposedPath = path.join(tempDir, filename);
    await fs.promises.writeFile(proposedPath, content, 'utf8');
    await vscode.commands.executeCommand(
        'vscode.diff',
        vscode.Uri.file(targetPath),
        vscode.Uri.file(proposedPath),
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
