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
    "ac-library-python",
    "acl-cpp-python",
    "cppyy",
]
for dist in required_dists:
    version(dist)

import numpy as np
import scipy.linalg as la
import networkx as nx
import sympy as sp
from sortedcontainers import SortedList
import more_itertools as mit
from shapely.geometry import Point
from bitarray import bitarray
import pulp
import mpmath as mp
import pandas as pd
import z3
from sklearn.linear_model import LinearRegression
import cppyy
from atcoder.dsu import DSU

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

cppyy.cppdef("int add_ints_pypy(int a, int b) { return a + b; }")
assert cppyy.gbl.add_ints_pypy(2, 3) == 5

dsu = DSU(4)
dsu.merge(0, 1)
assert dsu.same(0, 1)

assert pd.DataFrame({"x": [1, 2]}).shape == (2, 1)

print("PYPY_OK")
