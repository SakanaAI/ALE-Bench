from importlib.metadata import version

required_dists = [
    "numpy",
    "scipy",
    "networkx",
    "sympy",
    "sortedcontainers",
    "more-itertools",
    "shapely",
    "bitarray",
    "PuLP",
    "mpmath",
    "pandas",
    "z3-solver",
    "scikit-learn",
    "lightgbm",
    "ortools",
    "polars",
    "torch",
    "ac-library-python",
    "acl-cpp-python",
    "cppyy",
    "gmpy2",
    "rustworkx",
    "numba",
    "Cython",
]
for dist in required_dists:
    version(dist)

import numpy as np
import pandas as pd
import polars as pl
import scipy.linalg as la
import networkx as nx
import sympy as sp
from sortedcontainers import SortedList
import more_itertools as mit
from shapely.geometry import Point
from bitarray import bitarray
import pulp
import mpmath as mp
import z3
from sklearn.linear_model import LinearRegression
import lightgbm as lgb
from ortools.linear_solver import pywraplp
import torch
import cppyy
import gmpy2
import rustworkx as rx
from atcoder.dsu import DSU
import numba
import Cython

assert np.array_equal(np.sort(np.array([3, 1, 2])), np.array([1, 2, 3]))
assert int(np.round(la.norm(np.array([3.0, 4.0])))) == 5

g = nx.Graph()
g.add_edge(1, 2)
assert nx.has_path(g, 1, 2)

x = sp.Symbol("x")
assert sp.expand((x + 1) ** 2) == x**2 + 2 * x + 1

sl = SortedList([3, 1, 2])
assert list(sl) == [1, 2, 3]
assert list(mit.chunked([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]

assert Point(0, 0).distance(Point(3, 4)) == 5

ba = bitarray("1011")
assert ba.count() == 3

v = pulp.LpVariable("x", lowBound=0)
prob = pulp.LpProblem("p", pulp.LpMaximize)
prob += v
prob += v <= 2
prob.solve(pulp.PULP_CBC_CMD(msg=False))
assert float(v.value()) == 2.0

assert mp.sqrt(81) == 9

z = z3.Int("z")
solver = z3.Solver()
solver.add(z > 5)
assert solver.check() == z3.sat

model = LinearRegression().fit(np.array([[0], [1], [2]]), np.array([0, 1, 2]))
assert float(model.predict(np.array([[3]]))[0]) > 2.9

assert hasattr(lgb, "Dataset")

ort_solver = pywraplp.Solver.CreateSolver("GLOP")
assert ort_solver is not None
var = ort_solver.NumVar(0, 1, "x")
ort_solver.Maximize(var)
status = ort_solver.Solve()
assert status == pywraplp.Solver.OPTIMAL

assert int(torch.tensor([1, 2, 3]).sum()) == 6

cppyy.cppdef("int add_ints(int a, int b) { return a + b; }")
assert cppyy.gbl.add_ints(2, 3) == 5

assert int(gmpy2.mpz(7) + gmpy2.mpz(8)) == 15

rx_graph = rx.PyGraph()
rx_graph.add_nodes_from([0, 1])
rx_graph.add_edge(0, 1, None)
assert rx_graph.num_edges() == 1

dsu = DSU(4)
dsu.merge(0, 1)
assert dsu.same(0, 1)

assert pd.DataFrame({"x": [1, 2]}).shape == (2, 1)
assert pl.DataFrame({"x": [1, 2]}).shape == (2, 1)

@numba.njit
def numba_sum(n):
    s = 0
    for i in range(n):
        s += i
    return s

assert numba_sum(10) == 45

assert hasattr(Cython, "__version__")

print("PYTHON_OK")
