'use strict';

const _ = require('lodash');
const math = require('mathjs');
const Immutable = require('immutable');
const ac = require('ac-library-js');
const dstruct = require('data-structure-typed');
const std = require('tstl');

if (_.sum([1, 2, 3, 4]) !== 10) {
  throw new Error('lodash sum check failed');
}

if (math.sqrt(81) !== 9) {
  throw new Error('mathjs sqrt check failed');
}

const im = Immutable.Map({ a: 1 }).set('b', 2);
if (im.get('b') !== 2) {
  throw new Error('immutable check failed');
}

const dsu = new ac.DSU(4);
dsu.merge(0, 1);
if (!dsu.same(0, 1)) {
  throw new Error('ac-library-js DSU check failed');
}

if (Object.keys(dstruct).length === 0) {
  throw new Error('data-structure-typed export check failed');
}

const v = new std.Vector();
v.push_back(10);
v.push_back(20);
if (v.size() !== 2) {
  throw new Error('tstl Vector check failed');
}

const heavySecondsRaw = process.env.HEAVY_SECONDS ?? '2';
const heavySeconds = Number.parseInt(heavySecondsRaw, 10);
if (!Number.isInteger(heavySeconds) || heavySeconds < 1) {
  throw new Error(`invalid HEAVY_SECONDS: ${heavySecondsRaw}`);
}

const deadline = Date.now() + heavySeconds * 1000;
let acc = 1;
while (Date.now() < deadline) {
  for (let i = 1; i <= 100000; ++i) {
    acc = (acc * 1103515245 + i + 12345) % 1000000007;
  }
}

console.log('JAVASCRIPT_OK');
console.log(`JAVASCRIPT_HEAVY_OK ${acc}`);
