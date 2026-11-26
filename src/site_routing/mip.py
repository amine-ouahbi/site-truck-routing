"""Exact method: a mixed-integer program (MIP) for the capacitated vehicle routing problem.

Unlike a heuristic, the solver also computes a LOWER BOUND: a distance that no solution can
beat. When the best solution found equals the bound, the solution is proven optimal. When
time runs out first, the gap between them says how far from optimal we might still be.

Formulation (two-index, with Miller-Tucker-Zemlin load variables):
  x[i,j] = 1 if a truck drives directly from i to j          (binary)
  u[i]   = tonnes on board when the truck leaves point i      (continuous, q[i] <= u[i] <= Q)

  minimise   sum d[i,j] * x[i,j]
  subject to each point is entered once and left once
             trips leaving the hall = trips returning, and >= total tonnes / Q
             u[j] >= u[i] + q[j] - Q * (1 - x[i,j])  for points i, j   (load grows along a
                                    trip, which also forbids trips that skip the hall)
The load constraints are written in the stronger "lifted" form of Desrochers & Laporte (1991).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ortools.linear_solver import pywraplp

from .instance import Instance


@dataclass
class MipResult:
    routes: list[list[int]] | None
    objective: float | None     # best distance found (metres)
    bound: float                # proven lower bound (metres)
    optimal: bool
    seconds: float


def solve(inst: Instance, time_limit_s: int = 120, backend: str = "CP_SAT",
          hint: list[list[int]] | None = None) -> MipResult:
    n, q, cap, d = inst.n, inst.demand, inst.capacity, inst.dist
    nodes, points = range(n + 1), range(1, n + 1)
    s = pywraplp.Solver.CreateSolver(backend)
    if s is None:
        raise RuntimeError(f"solver backend {backend} not available")

    # Arcs between two points whose loads cannot share a truck are left out.
    x = {(i, j): s.BoolVar(f"x_{i}_{j}") for i in nodes for j in nodes
         if i != j and not (i and j and q[i] + q[j] > cap)}
    u = {i: s.NumVar(q[i], cap, f"u_{i}") for i in points}

    for i in points:
        s.Add(sum(x[i, j] for j in nodes if (i, j) in x) == 1)
        s.Add(sum(x[j, i] for j in nodes if (j, i) in x) == 1)
    out_of_hall = sum(x[0, j] for j in points)
    s.Add(out_of_hall == sum(x[j, 0] for j in points))
    s.Add(out_of_hall >= math.ceil(sum(q) / cap))

    for (i, j) in x:
        if i and j:
            if (j, i) in x:  # lifted MTZ (Desrochers & Laporte)
                s.Add(u[i] - u[j] + cap * x[i, j] + (cap - q[i] - q[j]) * x[j, i] <= cap - q[j])
            else:
                s.Add(u[i] - u[j] + cap * x[i, j] <= cap - q[j])

    s.Minimize(sum(d[i][j] * var for (i, j), var in x.items()))

    if hint:  # start from a known solution: the solver only has to improve it / prove it
        used = {(a, b) for r in hint for a, b in zip([0, *r], [*r, 0])}
        s.SetHint(list(x.values()), [1.0 if k in used else 0.0 for k in x])

    s.SetTimeLimit(time_limit_s * 1000)
    status = s.Solve()
    seconds = s.wall_time() / 1000
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return MipResult(None, None, s.Objective().BestBound(), False, seconds)

    succ = {i: j for (i, j), var in x.items() if var.solution_value() > 0.5}
    starts = [j for (i, j), var in x.items() if i == 0 and var.solution_value() > 0.5]
    routes = []
    for p in starts:
        route = []
        while p != 0:
            route.append(p)
            p = succ[p]
        routes.append(route)
    return MipResult(routes, s.Objective().Value(), s.Objective().BestBound(),
                     status == pywraplp.Solver.OPTIMAL, seconds)


def _components(arcs: list[tuple[int, int]]) -> list[set[int]]:
    """Groups of points linked by the chosen arcs (ignoring the hall)."""
    parent: dict[int, int] = {}

    def find(a: int) -> int:
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in arcs:
        if i and j:
            parent[find(i)] = find(j)
        for k in (i, j):
            if k:
                find(k)
    groups: dict[int, set[int]] = {}
    for k in parent:
        groups.setdefault(find(k), set()).add(k)
    return list(groups.values())


def lp_cut_sets(inst: Instance, max_rounds: int = 300) -> tuple[list[set[int]], float]:
    """Find good cuts cheaply on the LINEAR relaxation (x between 0 and 1).

    The relaxed solution is fractional, so groups of points are found by keeping only the
    arcs above a threshold. A group S needs a cut when the flow leaving it is smaller than
    ceil(tonnes(S) / Q). Linear programs solve in milliseconds, so hundreds of rounds are
    cheap, and the integer phase then starts with most of the cuts it needs.
    Returns the groups found and the final linear-relaxation bound.
    """
    n, q, cap, d = inst.n, inst.demand, inst.capacity, inst.dist
    nodes, points = range(n + 1), range(1, n + 1)
    lp = pywraplp.Solver.CreateSolver("GLOP")
    x = {(i, j): lp.NumVar(0, 1, f"x_{i}_{j}") for i in nodes for j in nodes
         if i != j and not (i and j and q[i] + q[j] > cap)}
    for i in points:
        lp.Add(sum(x[i, j] for j in nodes if (i, j) in x) == 1)
        lp.Add(sum(x[j, i] for j in nodes if (j, i) in x) == 1)
    out_of_hall = sum(x[0, j] for j in points)
    lp.Add(out_of_hall == sum(x[j, 0] for j in points))
    lp.Add(out_of_hall >= math.ceil(sum(q) / cap))
    lp.Minimize(sum(d[i][j] * var for (i, j), var in x.items()))

    found: dict[frozenset[int], None] = {}
    bound = 0.0
    for _ in range(max_rounds):
        lp.Solve()
        bound = lp.Objective().Value()
        val = {k: var.solution_value() for k, var in x.items()}
        new = 0
        for threshold in (1e-6, 0.25, 0.5, 0.75):
            for group in _components([k for k, v in val.items() if v > threshold]):
                key = frozenset(group)
                if len(group) == n or key in found:
                    continue
                leaving = sum(v for (i, j), v in val.items() if i in group and j not in group)
                need = math.ceil(sum(q[k] for k in group) / cap)
                if leaving < need - 1e-6:
                    found[key] = None
                    lp.Add(sum(var for (i, j), var in x.items() if i in group and j not in group) >= need)
                    new += 1
        if not new:
            break
    return [set(k) for k in found], bound


def solve_exact(inst: Instance, time_limit_s: int = 120, hint: list[list[int]] | None = None,
                use_cuts: bool = True, workers: int = 8) -> MipResult:
    """Exact method used for the results: CP-SAT (Google's constraint/integer solver).

    - AddMultipleCircuit: the chosen arcs must form trips that all start and end at the hall,
      and every point is visited once. This replaces the weak MTZ subtour constraints.
    - Loads are enforced exactly with conditional constraints: if a truck drives i -> j,
      its load at j is its load at i plus the tonnes collected at j (never above Q).
    - With use_cuts=True, the rounded capacity cuts found on the linear relaxation
      (lp_cut_sets) are added. They do not remove any real solution, but they raise the
      lower bound, which lets the solver prove optimality much sooner.
    """
    from ortools.sat.python import cp_model

    n, q, cap, d = inst.n, inst.demand, inst.capacity, inst.dist
    nodes, points = range(n + 1), range(1, n + 1)
    m = cp_model.CpModel()
    x = {(i, j): m.NewBoolVar(f"x_{i}_{j}") for i in nodes for j in nodes
         if i != j and not (i and j and q[i] + q[j] > cap)}
    m.AddMultipleCircuit([(i, j, var) for (i, j), var in x.items()])
    load = {i: m.NewIntVar(q[i], cap, f"load_{i}") for i in points}
    for (i, j), var in x.items():
        if i and j:
            m.Add(load[j] >= load[i] + q[j]).OnlyEnforceIf(var)
    m.Add(sum(x[0, j] for j in points) >= math.ceil(sum(q) / cap))
    cuts = lp_cut_sets(inst)[0] if use_cuts else []
    for group in cuts:
        m.Add(sum(var for (i, j), var in x.items() if i in group and j not in group)
              >= math.ceil(sum(q[k] for k in group) / cap))
    m.Minimize(sum(d[i][j] * var for (i, j), var in x.items()))
    if hint:
        used = {(a, b) for r in hint for a, b in zip([0, *r], [*r, 0])}
        for k, var in x.items():
            m.AddHint(var, k in used)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = workers
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return MipResult(None, None, solver.BestObjectiveBound(), False, solver.WallTime())
    succ = {i: j for (i, j), var in x.items() if solver.Value(var)}
    routes = []
    for (i, j), var in x.items():
        if i == 0 and solver.Value(var):
            route, p = [], j
            while p != 0:
                route.append(p)
                p = succ[p]
            routes.append(route)
    return MipResult(routes, solver.ObjectiveValue(), solver.BestObjectiveBound(),
                     status == cp_model.OPTIMAL, solver.WallTime())
