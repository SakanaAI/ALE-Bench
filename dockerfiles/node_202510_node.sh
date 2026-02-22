#!/bin/sh

if [ "$1" -gt 1048576 ]; then
  stack_size=1048576
else
  stack_size="$1"
fi

filename="$2"

node \
--stack-size="$stack_size" \
"$filename" \
ONLINE_JUDGE \
ATCODER
