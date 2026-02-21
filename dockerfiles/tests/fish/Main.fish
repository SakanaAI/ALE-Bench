#!/usr/bin/env fish

set vals 1 2 3
set sum 0
for v in $vals
    set sum (math "$sum + $v")
end

if test "$sum" -ne 6
    echo "unexpected sum: $sum" >&2
    exit 1
end

# Require fish 4.x
set fish_ver (fish --version | string replace -r '.*version ' '')
if not string match -q "4.*" $fish_ver
    echo "fish version check failed: $fish_ver (need 4.x)" >&2
    exit 1
end

set heavy_seconds 2
if set -q HEAVY_SECONDS
    set heavy_seconds $HEAVY_SECONDS
end
if not string match -rq '^[0-9]+$' -- $heavy_seconds
    echo "invalid HEAVY_SECONDS: $heavy_seconds" >&2
    exit 1
end
if test "$heavy_seconds" -lt 1
    echo "invalid HEAVY_SECONDS: $heavy_seconds" >&2
    exit 1
end

set start_ts (date +%s)
set end_ts (math "$start_ts + $heavy_seconds")
set acc 1
while test (date +%s) -lt $end_ts
    for i in (seq 1 800)
        set acc (math "($acc * 1103515245 + $i + 12345) % 1000000007")
    end
end

echo "FISH_OK"
echo "FISH_HEAVY_OK $acc"
