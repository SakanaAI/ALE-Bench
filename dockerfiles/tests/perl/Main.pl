#!/usr/bin/env perl
use strict;
use warnings;
use Time::HiRes qw(time);

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

my $heavy_seconds = $ENV{HEAVY_SECONDS} // 2;
if ($heavy_seconds !~ /^\d+$/ || $heavy_seconds < 1) {
  die "invalid HEAVY_SECONDS: $heavy_seconds\n";
}

my $end = time + $heavy_seconds;
my $acc = 1;
while (time < $end) {
  for my $i (1 .. 50000) {
    $acc = ($acc * 1103515245 + $i + 12345) % 1000000007;
  }
}

print "PERL_OK\n";
print "PERL_HEAVY_OK $acc\n";
