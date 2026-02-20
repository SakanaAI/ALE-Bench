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

echo "FISH_OK"
