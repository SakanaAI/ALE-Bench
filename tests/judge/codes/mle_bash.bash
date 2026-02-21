#!/usr/bin/env bash
set -euo pipefail

# Allocate around 1.1 GiB in-process.
printf -v data '%*s' $((1120 * 1024 * 1024)) ''
if [[ ${#data} -lt $((1100 * 1024 * 1024)) ]]; then
  echo "allocation failed" >&2
  exit 1
fi
