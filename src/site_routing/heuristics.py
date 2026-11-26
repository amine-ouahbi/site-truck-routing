"""Two constructive heuristics: fast, simple, and with no guarantee of quality."""
from __future__ import annotations

from .instance import Instance


def nearest_neighbour(inst: Instance) -> list[list[int]]:
    """Greedy: always drive to the closest point that still fits in the truck.

    When nothing fits any more, the truck goes back to the storage hall and a new trip
    starts. This is the kind of rule a planner uses by hand, and the kind of heuristic
    used in the original project.
    """
    unvisited = set(range(1, inst.n + 1))
    routes = []
    while unvisited:
        route, load, here = [], 0, 0
        while True:
            fits = [p for p in unvisited if load + inst.demand[p] <= inst.capacity]
            if not fits:
                break
            nxt = min(fits, key=lambda p: (inst.dist[here][p], p))
            route.append(nxt)
            load += inst.demand[nxt]
            unvisited.remove(nxt)
            here = nxt
        routes.append(route)
    return routes


def clarke_wright(inst: Instance) -> list[list[int]]:
    """Clarke & Wright savings algorithm (1964), parallel version.

    Start with one trip per point. Joining the trips that end at i and start at j saves
    d(i, hall) + d(hall, j) - d(i, j) metres. Merge the pairs with the largest savings
    first, as long as the merged trip fits in the truck and i, j are at the ends of
    their trips.
    """
    d, q, cap = inst.dist, inst.demand, inst.capacity
    routes = {p: [p] for p in range(1, inst.n + 1)}  # trip id -> points
    trip_of = {p: p for p in routes}
    load = {p: q[p] for p in routes}
    savings = sorted(
        ((d[i][0] + d[0][j] - d[i][j], i, j) for i in routes for j in routes if i < j),
        reverse=True,
    )
    for saving, i, j in savings:
        if saving <= 0:
            break
        ti, tj = trip_of[i], trip_of[j]
        if ti == tj or load[ti] + load[tj] > cap:
            continue
        a, b = routes[ti], routes[tj]
        if a[-1] == i and b[0] == j:
            merged = a + b
        elif a[0] == i and b[-1] == j:
            merged = b + a
        elif a[-1] == i and b[-1] == j:
            merged = a + b[::-1]
        elif a[0] == i and b[0] == j:
            merged = a[::-1] + b
        else:
            continue  # i or j is in the middle of its trip: cannot join there
        routes[ti] = merged
        load[ti] += load.pop(tj)
        del routes[tj]
        for p in b:
            trip_of[p] = ti
    return list(routes.values())
