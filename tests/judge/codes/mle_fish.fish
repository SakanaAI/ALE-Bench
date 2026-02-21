#!/usr/bin/env fish

# Allocate around 1.1 GiB in-process.
set data (string repeat -n 1174405120 "a")
if test (string length -- "$data") -lt 1100000000
    echo "allocation failed" >&2
    exit 1
end
