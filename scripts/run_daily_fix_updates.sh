#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

sync_with_origin_main() {
    git fetch origin main
    git rebase origin/main
}

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Syncing branch with origin/main"
sync_with_origin_main

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running results-fix.py"
"${PYTHON_BIN}" results-fix.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running upcoming-fix.py"
"${PYTHON_BIN}" upcoming-fix.py

free_changed=0
pre_changed=0

if [[ -n "$(git status --porcelain -- free_fix.csv)" ]]; then
    free_changed=1
fi

if [[ -n "$(git status --porcelain -- pre_fix.csv)" ]]; then
    pre_changed=1
fi

if [[ "${free_changed}" -eq 1 || "${pre_changed}" -eq 1 ]]; then
    commit_message="$(date '+%Y-%m-%d')-new-fixs-updates"
    git add free_fix.csv pre_fix.csv

    if git diff --cached --quiet -- free_fix.csv pre_fix.csv; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] No staged changes found after git add."
        exit 0
    fi

    git commit -m "${commit_message}"

    # Re-sync before push in case remote moved while scripts were running.
    sync_with_origin_main

    if ! git push origin main; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Push failed on first attempt. Retrying after sync."
        sync_with_origin_main
        git push origin main
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Committed and pushed: ${commit_message}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skip commit: no CSV changes found."
fi
