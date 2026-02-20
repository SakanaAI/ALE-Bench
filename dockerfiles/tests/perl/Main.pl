#!/usr/bin/env perl
use strict;
use warnings;

my @vals = (1, 2, 3);
my $sum = 0;
$sum += $_ for @vals;

if ($sum != 6) {
  die "unexpected sum: $sum\n";
}

my %h = (x => 42);
if ($h{x} != 42) {
  die "hash check failed\n";
}

print "PERL_OK\n";
