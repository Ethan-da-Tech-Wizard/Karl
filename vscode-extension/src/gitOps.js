// @ts-check
const cp = require('child_process');

/**
 * Executes a git command.
 * @param {string[]} args
 * @param {string} cwd
 * @returns {Promise<string>}
 */
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

/**
 * Gets the current git branch name.
 * @param {string} workspacePath
 * @returns {Promise<string>}
 */
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
