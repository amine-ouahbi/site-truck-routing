"""Run every method on every site instance and write results/ and figures/.

    python run.py              # full run (about 10 minutes)
    python run.py --quick      # short time limits, for a quick check
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from site_routing import heuristics, instance, mip, ortools_solver, plot  # noqa: E402
from site_routing import solution as S  # noqa: E402

SIZES = [12, 20, 30, 40]  # collection points; the seed is the size, so instances are reproducible


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    t_ortools, t_textbook, t_exact = (3, 10, 15) if args.quick else (10, 60, 120)
    for folder in ("instances", "results", "figures"):
        (ROOT / folder).mkdir(exist_ok=True)

    rows, bounds, gaps, maps = [], [], {"Greedy (nearest point)": [], "Clarke-Wright savings": [], "OR-Tools (GLS)": []}, None
    for n in SIZES:
        inst = instance.generate_site(n, seed=n)
        inst.save(ROOT / "instances" / f"{inst.name}.json")
        print(f"\n{inst.name}: {sum(inst.demand)} t to collect, at least {inst.min_trips} trips")

        sols = {
            "Greedy (nearest point)": heuristics.nearest_neighbour(inst),
            "Clarke-Wright savings": heuristics.clarke_wright(inst),
            "OR-Tools (GLS)": ortools_solver.solve(inst, t_ortools),
        }
        best_heur = min(sols.values(), key=lambda r: S.total_distance(inst, r))

        textbook = mip.solve(inst, t_textbook, backend="SCIP", hint=best_heur) if n <= 30 else None
        lp_bound = mip.lp_cut_sets(inst)[1]
        exact = mip.solve_exact(inst, t_exact, hint=best_heur)
        if exact.routes:
            sols["Exact (CP-SAT)"] = exact.routes
        for routes in sols.values():
            S.validate(inst, routes)

        bound = max(b for b in (exact.bound, lp_bound, textbook and textbook.bound) if b is not None)
        for method, routes in sols.items():
            dist = S.total_distance(inst, routes)
            gap = 100 * (dist - bound) / bound
            rows.append({
                "instance": inst.name, "method": method, "km": round(dist / 1000, 2), "trips": len(routes),
                "avg_trip_min": round(sum(S.trip_minutes(inst, r) for r in routes) / len(routes), 1),
                "pct_above_lower_bound": round(gap, 2),
                "proven_optimal": method == "Exact (CP-SAT)" and exact.optimal,
            })
            if method in gaps:
                gaps[method].append(gap)
            print(f"  {method:24s} {dist / 1000:6.1f} km  {len(routes):2d} trips  +{gap:5.1f}% vs bound")
        bounds.append({
            "instance": inst.name,
            "textbook_mip_bound_km": round(textbook.bound / 1000, 2) if textbook else "",
            "lp_capacity_cuts_bound_km": round(lp_bound / 1000, 2),
            "cpsat_bound_km": round(exact.bound / 1000, 2),
            "cpsat_best_km": round(exact.objective / 1000, 2) if exact.objective else "",
            "cpsat_seconds": round(exact.seconds, 1),
            "proven_optimal": exact.optimal,
        })
        print(f"  lower bounds: textbook MIP {textbook.bound / 1000 if textbook else float('nan'):.2f} km, "
              f"LP+cuts {lp_bound / 1000:.2f} km, CP-SAT {exact.bound / 1000:.2f} km "
              f"({'optimal' if exact.optimal else 'time limit'}, {exact.seconds:.0f} s)")
        if n == 20:
            maps = (inst, {"Greedy (nearest point)": sols["Greedy (nearest point)"],
                           "Proven optimal (CP-SAT)": exact.routes})

    with open(ROOT / "results" / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(ROOT / "results" / "bounds.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(bounds[0]))
        w.writeheader()
        w.writerows(bounds)
    plot.gap_bars(SIZES, gaps, str(ROOT / "figures" / "gap_by_method.png"))
    if maps and maps[1]["Proven optimal (CP-SAT)"]:
        plot.routes_side_by_side(maps[0], maps[1], str(ROOT / "figures" / "routes_site-20.png"))
    print("\nwrote results/results.csv, results/bounds.csv and figures/")


if __name__ == "__main__":
    main()
