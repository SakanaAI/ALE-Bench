use ac_library::Dsu;
use bitvec::prelude::*;
use counter::Counter;
use fixedbitset::FixedBitSet;
use itertools::Itertools;
use lazy_static::lazy_static;
use maplit::hashmap;
use nalgebra::Matrix2;
use ndarray::array;
use num::Integer;
use once_cell::sync::Lazy;
use ordered_float::OrderedFloat;
use pathfinding::prelude::bfs;
use permutohedron::Heap;
use petgraph::graph::UnGraph;
use proconio::source::once::OnceSource;
use rand::Rng;
use regex::Regex;
use rustc_hash::FxHashMap;
use smallvec::{smallvec, SmallVec};
use std::env;
use std::time::{Duration, Instant};
use superslice::Ext;

static GLOBAL_VAL: Lazy<i32> = Lazy::new(|| 42);

lazy_static! {
    static ref GLOBAL_STR: String = String::from("hello");
}

fn main() {
    // ac-library
    let mut dsu = Dsu::new(4);
    dsu.merge(0, 1);
    assert!(dsu.same(0, 1));

    // itertools
    let joined = [1, 2, 3].iter().join(",");
    assert_eq!(joined, "1,2,3");

    // ndarray
    let a = array![1_i64, 2, 3, 4];
    assert_eq!(a.sum(), 10);

    // num
    assert_eq!(48_i64.gcd(&18), 6);

    // regex
    let re = Regex::new(r"^a+b+$").expect("regex compile");
    assert!(re.is_match("aaab"));

    // smallvec
    let sv: SmallVec<[u32; 4]> = smallvec![1_u32, 2, 3, 4];
    assert_eq!(sv.len(), 4);

    // petgraph
    let mut graph = UnGraph::<&str, ()>::new_undirected();
    let a_node = graph.add_node("a");
    let b_node = graph.add_node("b");
    graph.add_edge(a_node, b_node, ());
    assert_eq!(graph.edge_count(), 1);

    // nalgebra
    let mat = Matrix2::new(1.0_f64, 2.0, 3.0, 4.0);
    assert!((mat.determinant() - (-2.0)).abs() < 1e-9);

    // rand
    let mut rng = rand::rng();
    let _val: u32 = rng.random();

    // ordered-float
    let mut floats = vec![OrderedFloat(3.0), OrderedFloat(1.0), OrderedFloat(2.0)];
    floats.sort();
    assert_eq!(floats[0], OrderedFloat(1.0));

    // pathfinding
    let result = bfs(&1, |&n| vec![n + 1, n + 2], |&n| n == 4);
    assert!(result.is_some());

    // once_cell
    assert_eq!(*GLOBAL_VAL, 42);

    // lazy_static
    assert_eq!(*GLOBAL_STR, "hello");

    // maplit
    let map = hashmap! { "a" => 1, "b" => 2 };
    assert_eq!(map["a"], 1);

    // proconio (test source parsing)
    let source = OnceSource::from("42\n");
    let mut source = source;
    let val: i32 = proconio::read_value!(from &mut source, i32);
    assert_eq!(val, 42);

    // bitvec
    let bv = bitvec![u8, Msb0; 1, 0, 1, 1];
    assert_eq!(bv.count_ones(), 3);

    // counter
    let counts: Counter<_> = "aabbc".chars().collect();
    assert_eq!(counts[&'a'], 2);

    // fixedbitset
    let mut fbs = FixedBitSet::with_capacity(4);
    fbs.insert(0);
    fbs.insert(2);
    assert_eq!(fbs.count_ones(..), 2);

    // permutohedron
    let mut data = vec![1, 2, 3];
    let heap = Heap::new(&mut data);
    assert_eq!(heap.count(), 6);

    // superslice
    let sorted = [1, 2, 3, 4, 5];
    assert_eq!(sorted.lower_bound(&3), 2);

    // rustc-hash
    let mut fxmap = FxHashMap::default();
    fxmap.insert(1, "one");
    assert_eq!(fxmap[&1], "one");

    let heavy_seconds: u64 = env::var("HEAVY_SECONDS")
        .ok()
        .and_then(|s| s.parse::<u64>().ok())
        .filter(|&n| n >= 1)
        .unwrap_or(2);
    let deadline = Instant::now() + Duration::from_secs(heavy_seconds);
    let mut acc: u64 = 1;
    while Instant::now() < deadline {
        for i in 1_u64..=100_000 {
            acc = (acc * 1103515245 + i + 12345) % 1_000_000_007;
        }
    }

    println!("RUST_OK");
    println!("RUST_HEAVY_OK {acc}");
}
