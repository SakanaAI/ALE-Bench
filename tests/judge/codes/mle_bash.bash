#!/usr/bin/env bash
set -euo pipefail

# Allocate around 128 MiB in-process.
printf -v data '%*s' $((128 * 1024 * 1024)) ''
if [[ ${#data} -lt $((120 * 1024 * 1024)) ]]; then
  echo "allocation failed" >&2
  exit 1
fi
