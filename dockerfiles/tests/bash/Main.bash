#!/usr/bin/env bash
set -euo pipefail

# Require bash 5.3+
if [[ ${BASH_VERSINFO[0]} -lt 5 ]] || { [[ ${BASH_VERSINFO[0]} -eq 5 ]] && [[ ${BASH_VERSINFO[1]} -lt 3 ]]; }; then
  echo "bash version is too old: ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]} (need 5.3+)" >&2
  exit 1
fi

arr=(1 2 3)
sum=0
for v in "${arr[@]}"; do
  ((sum += v))
done

if [[ ${sum} -ne 6 ]]; then
  echo "unexpected sum: ${sum}" >&2
  exit 1
fi

declare -A m=([x]=42)
if [[ ${m[x]} -ne 42 ]]; then
  echo "associative array check failed" >&2
  exit 1
fi

echo "BASH_OK"
