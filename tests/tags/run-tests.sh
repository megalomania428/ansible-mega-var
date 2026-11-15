#!/usr/bin/env bash
set -ueo pipefail
umask 0022
MY_BIN="$(realpath "$0")"
MY_PATH="$(dirname "${MY_BIN}")"
cd "${MY_PATH}/../.."
# shellcheck disable=1091
source "${MY_PATH}/../../molecule/prepare.sh"
: "${MEVA_TAGS_JOBS:="$(nproc)"}"
[[ "${MEVA_TAGS_JOBS}" =~ ^[1-9][0-9]*$ ]] || {
  echo "MEVA_TAGS_JOBS must be a positive integer, got [${MEVA_TAGS_JOBS}]" >&2
  exit 2
}
MEVA_TAGS_OUT="$(mktemp -d)"
trap 'echo "outputs of the tags matrix are kept in [${MEVA_TAGS_OUT}]" >&2' EXIT
# shellcheck disable=2154
export MEVA_TAGS_BIN="${_appimage_bin}" MEVA_TAGS_OUT
export ANSIBLE_STDOUT_CALLBACK='ansible.posix.json' ANSIBLE_LOG_PATH='/dev/null'
export ANSIBLE_VERBOSITY='0'
meva_tags_run() {
  local -a sel
  local rc=0
  IFS=$'\t' read -r -a sel <<<"$1"
  "${MEVA_TAGS_BIN}" ansible-playbook -i tests/tags/inventory.yaml \
    tests/tags/play.yaml "${sel[@]:1}" >"${MEVA_TAGS_OUT}/${sel[0]}.json" \
    2>"${MEVA_TAGS_OUT}/${sel[0]}.err" || rc=$?
  echo "${rc}" >"${MEVA_TAGS_OUT}/${sel[0]}.rc"
}
export -f meva_tags_run
"${MEVA_TAGS_BIN}" python tests/tags/compare.py selectors "${MEVA_TAGS_OUT}/selectors"
SECONDS=0
# shellcheck disable=2016
xargs -P "${MEVA_TAGS_JOBS}" -d '\n' -n 1 bash -c 'meva_tags_run "$1"' _ \
  <"${MEVA_TAGS_OUT}/selectors"
echo "runs of the tags matrix took ${SECONDS} s"
echo 'warnings in stderr of the tags matrix runs, by count:'
grep -hF 'WARNING' "${MEVA_TAGS_OUT}"/*.err | sort | uniq -c || true
meva_tags_failed=0
while IFS= read -r line; do
  idx="${line%%$'\t'*}"
  args="${line:${#idx}}"
  args="${args//$'\t'/ }"
  rc='missing'
  [[ -f "${MEVA_TAGS_OUT}/${idx}.rc" ]] && rc="$(<"${MEVA_TAGS_OUT}/${idx}.rc")"
  [[ "${rc}" == '0' ]] && continue
  meva_tags_failed=1
  echo "selector [${args# }] failed with rc [${rc}], tail of its stderr:" >&2
  tail -n 33 "${MEVA_TAGS_OUT}/${idx}.err" >&2 || true
done <"${MEVA_TAGS_OUT}/selectors"
((meva_tags_failed == 0)) || exit 1
SECONDS=0
"${MEVA_TAGS_BIN}" python tests/tags/compare.py check "${MEVA_TAGS_OUT}"
echo "compare of the tags matrix took ${SECONDS} s"
trap - EXIT
rm -rf "${MEVA_TAGS_OUT}"
