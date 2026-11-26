"""Google OR-Tools routing solver: a strong metaheuristic (Guided Local Search).

It usually finds very good solutions quickly, but it cannot prove how good they are.
"""
from __future__ import annotations

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .instance import Instance


def solve(inst: Instance, time_limit_s: int = 10) -> list[list[int]]:
    trucks = inst.n  # an upper bound on the number of trips; unused trips cost nothing
    manager = pywrapcp.RoutingIndexManager(inst.n + 1, trucks, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance(i: int, j: int) -> int:
        return inst.dist[manager.IndexToNode(i)][manager.IndexToNode(j)]

    routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(distance))

    def tonnes(i: int) -> int:
        return inst.demand[manager.IndexToNode(i)]

    routing.AddDimensionWithVehicleCapacity(
        routing.RegisterUnaryTransitCallback(tonnes), 0, [inst.capacity] * trucks, True, "Load")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(time_limit_s)
    sol = routing.SolveWithParameters(params)
    if sol is None:
        raise RuntimeError("OR-Tools found no solution")

    routes = []
    for v in range(trucks):
        idx = sol.Value(routing.NextVar(routing.Start(v)))
        route = []
        while not routing.IsEnd(idx):
            route.append(manager.IndexToNode(idx))
            idx = sol.Value(routing.NextVar(idx))
        if route:
            routes.append(route)
    return routes
