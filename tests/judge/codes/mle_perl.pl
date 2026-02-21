#!/usr/bin/env perl
use strict;
use warnings;

my @chunks;
for my $i (0 .. 69) {
  my $chunk = "a" x (16 * 1024 * 1024);
  substr($chunk, 0, 1) = chr($i % 256);
  push @chunks, $chunk;
}

if (scalar(@chunks) != 70) {
  die "allocation failed\n";
}
