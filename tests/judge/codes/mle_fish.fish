#!/usr/bin/env fish

# Keep large chunks alive in-process so RSS exceeds 64 MiB.
set -l chunks
for i in (seq 1 24)
    set -a chunks (string repeat -n 4194304 "a")
end
