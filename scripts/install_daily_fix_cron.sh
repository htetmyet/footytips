#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNNER_SCRIPT="${REPO_ROOT}/scripts/run_daily_fix_updates.sh"
LOG_DIR="${REPO_ROOT}/logs"
LOG_FILE="${LOG_DIR}/daily_fix_job.log"
CRON_TAG="footytips-daily-fix-job"

mkdir -p "${LOG_DIR}"

cron_line="0 15 * * * cd ${REPO_ROOT} && /usr/bin/env bash ${RUNNER_SCRIPT} >> ${LOG_FILE} 2>&1 # ${CRON_TAG}"
existing_cron="$(crontab -l 2>/dev/null || true)"

updated_cron="$(printf '%s\n' "${existing_cron}" | sed "/${CRON_TAG}/d")"
updated_cron="$(printf '%s\n%s\n' "${updated_cron}" "${cron_line}" | sed '/^[[:space:]]*$/N;/^\n$/D')"

printf '%s\n' "${updated_cron}" | crontab -
echo "Installed cron: ${cron_line}"
