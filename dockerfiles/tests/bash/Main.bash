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

heavy_seconds="${HEAVY_SECONDS:-2}"
if ! [[ "${heavy_seconds}" =~ ^[0-9]+$ ]] || [[ "${heavy_seconds}" -lt 1 ]]; then
  echo "invalid HEAVY_SECONDS: ${heavy_seconds}" >&2
  exit 1
fi

end=$((SECONDS + heavy_seconds))
acc=1
while ((SECONDS < end)); do
  for ((i = 1; i <= 50000; ++i)); do
    ((acc = (acc * 1103515245 + i + 12345) % 1000000007))
  done
done

echo "BASH_OK"
echo "BASH_HEAVY_OK ${acc}"
