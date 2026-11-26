"""Problem instances: truck collection routes on an industrial site.

The setting mirrors internal transport on a large processing site: trucks leave a central
storage hall (the depot), collect product from points spread over several production areas,
and bring it back. Each truck trip can carry at most `capacity` tonnes.

The instances are synthetic (generated from a fixed random seed). They are NOT company data:
they only reproduce the shape of the real problem (site size, clustered areas, load sizes).
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path

# Site roads are not straight lines: road distance ~ straight-line distance x a detour factor.
# 1.3 is a common "circuity factor" for road networks. In the original project, travel
# times came from Google Maps; here they are approximated so the instances can be shared.
DETOUR_FACTOR = 1.3


@dataclass
class Instance:
    name: str
    coords: list[tuple[float, float]]  # km on the site plan; index 0 = depot (storage hall)
    demand: list[int]                  # tonnes to collect at each point; demand[0] = 0
    capacity: int                      # tonnes per truck trip
    dist: list[list[int]]              # road distance in metres (integer, symmetric)

    @property
    def n(self) -> int:
        """Number of collection points (the depot is not counted)."""
        return len(self.coords) - 1

    @property
    def min_trips(self) -> int:
        """No solution can use fewer trips than total tonnes / truck capacity, rounded up."""
        return math.ceil(sum(self.demand) / self.capacity)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self)), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Instance":
        d = json.loads(path.read_text(encoding="utf-8"))
        d["coords"] = [tuple(c) for c in d["coords"]]
        return cls(**d)


def road_distances(coords: list[tuple[float, float]]) -> list[list[int]]:
    return [[round(1000 * DETOUR_FACTOR * math.dist(a, b)) for b in coords] for a in coords]


def generate_site(n: int, seed: int, capacity: int = 30, areas: int = 4) -> Instance:
    """A site of about 8 km x 5 km with `areas` production areas.

    Collection points are clustered around the areas (as plants and stockpiles are on a real
    site), and each point has 3 to 12 tonnes to collect.
    """
    rng = random.Random(seed)
    depot = (1.0, 2.5)
    centres = [(rng.uniform(2.5, 7.5), rng.uniform(0.5, 4.5)) for _ in range(areas)]
    coords = [depot]
    while len(coords) < n + 1:
        cx, cy = rng.choice(centres)
        x, y = rng.gauss(cx, 0.45), rng.gauss(cy, 0.45)
        if 0 <= x <= 8 and 0 <= y <= 5:
            coords.append((round(x, 3), round(y, 3)))
    demand = [0] + [rng.randint(3, 12) for _ in range(n)]
    return Instance(f"site-{n}", coords, demand, capacity, road_distances(coords))
