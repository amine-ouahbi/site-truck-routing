"""Checking and measuring a solution.

A solution is a list of routes. Each route is one truck trip: depot -> points -> depot,
written as the list of points it visits, e.g. [4, 9, 2].
"""
from __future__ import annotations

from .instance import Instance

TRUCK_SPEED_KMH = 20      # average speed on site roads
LOAD_MIN_PER_STOP = 5     # loading time at each collection point
UNLOAD_MIN = 10           # unloading at the storage hall, once per trip


def route_distance(inst: Instance, route: list[int]) -> int:
    path = [0, *route, 0]
    return sum(inst.dist[a][b] for a, b in zip(path, path[1:]))


def total_distance(inst: Instance, routes: list[list[int]]) -> int:
    return sum(route_distance(inst, r) for r in routes)


def trip_minutes(inst: Instance, route: list[int]) -> float:
    """Cycle time of one trip: driving + loading at each stop + unloading at the hall."""
    drive = route_distance(inst, route) / 1000 / TRUCK_SPEED_KMH * 60
    return drive + LOAD_MIN_PER_STOP * len(route) + UNLOAD_MIN


def validate(inst: Instance, routes: list[list[int]]) -> None:
    """Raise if a point is missed or visited twice, or if a trip is overloaded."""
    visited = [p for r in routes for p in r]
    if sorted(visited) != list(range(1, inst.n + 1)):
        raise ValueError("every collection point must be visited exactly once")
    for r in routes:
        load = sum(inst.demand[p] for p in r)
        if load > inst.capacity:
            raise ValueError(f"trip {r} carries {load} t > capacity {inst.capacity} t")
