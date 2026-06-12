const cp = require('child_process');

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

module.exports = {
    execGit,
    getGitBranch
};
