const _: any = require('lodash');
const math: any = require('mathjs');
const Immutable: any = require('immutable');
const ac: any = require('ac-library-js');
const dstruct: any = require('data-structure-typed');
const std: any = require('tstl');

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

console.log('TYPESCRIPT_OK');
