# How it works, in plain words

## The problem

A storage hall (the depot) sends trucks to collect product from points spread over a site.
Each point has some tonnes to collect, and a truck can carry at most 30 t per trip. Every
point must be visited exactly once. The goal is to drive as little as possible.

In operations research this is the **Capacitated Vehicle Routing Problem (CVRP)**. It is
"NP-hard": no known method finds the best answer quickly for every large case. The number of
possible plans grows faster than exponentially with the number of points.

## Two kinds of methods

**Heuristics** build a good plan fast but say nothing about how good it is.

- *Greedy (nearest point):* drive to the closest point that still fits in the truck. When
  nothing fits, go back to the hall. Simple and natural, but a bad early choice is never
  corrected.
- *Clarke-Wright savings (1964):* start with one trip per point, then merge trips. Merging the
  trip ending at *i* with the trip starting at *j* saves `d(i, hall) + d(hall, j) - d(i, j)`.
  The biggest savings are merged first.
- *OR-Tools Guided Local Search:* start from a plan, then keep making small changes (move a
  point, swap two points, reverse a piece of a trip). Changes that look like "traps" are
  penalised, so the search keeps exploring. Very good plans, still no proof.

**Exact methods** find the best plan *and prove it*. They do this by computing a **lower
bound**: a distance that no plan can beat.

- If the best plan found equals the lower bound, it is **proven optimal**.
- If time runs out first, the **gap** `(best plan - lower bound) / lower bound` is the
  most we could still be losing.

## Why the "textbook" model is weak

The classic integer program uses binary variables `x[i,j]` ("does a truck drive from i to j?")
and load variables `u[i]` (the Miller-Tucker-Zemlin, or MTZ, constraints) to forbid impossible
trips. Its lower bound comes from relaxing the binary variables to fractions, and for MTZ
that relaxation is very loose. On the 20-point site the textbook bound after 60 seconds is about 50 km, while
the optimum is 73.6 km. The solver cannot close such a gap within minutes.

## Cutting planes: the idea behind branch-and-cut

A **rounded capacity cut** says: for any group of points S,

> trucks must leave S at least `ceil(tonnes(S) / truck capacity)` times.

A group with 70 t of product needs at least 3 trips, so at least 3 departures from it. Every
real plan satisfies this, so adding the cut never removes a real plan, but it removes many
fractional "fake" plans and **raises the lower bound**. `lp_cut_sets()` finds violated cuts
on the relaxed problem, adds them, solves again, and repeats. On the 20-point site this lifts
the bound from about 50 km to 72.8 km in a fraction of a second, within about 1% of the optimum.

This is the starting point of the state of the art: **branch-and-cut-and-price** combines
these cuts with column generation (choosing among whole trips instead of single arcs) and
with branching.

## The exact solver used here

CP-SAT (Google OR-Tools) combines constraint programming, SAT solving and linear relaxations.
The model:

- `AddMultipleCircuit` makes every chosen arc belong to a trip through the hall.
- Loads are linked exactly with conditional constraints: *if* the truck drives i → j, *then*
  `load[j] >= load[i] + tonnes[j]`.

It proves the optimum in seconds up to about 20 points. At 30–40 points it stops at the time
limit with a gap of a few percent. Adding our capacity cuts to it did **not** help, because
CP-SAT already generates similar cuts internally. That result is reported as it is.

## What the numbers mean for a real site

- A natural "nearest point" rule can drive 8–47% more than necessary on these instances.
  That is fuel, truck hours and cycle time.
- Classic algorithms (Clarke-Wright) recover most of that loss. Modern metaheuristics recover
  nearly all of it, but without proof.
- Proving optimality stops scaling quickly. Real sites add time windows, shifts, several
  products and uncertain travel times, which makes the problem bigger still. Better
  decomposition methods and matheuristics are needed there.
