"""Figures for the README (matplotlib, PNG)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .instance import Instance  # noqa: E402
from .solution import total_distance  # noqa: E402

# Validated categorical palette (fixed order, never cycled) and recessive inks.
SERIES = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647"]
INK, INK_2, GRID, SURFACE = "#1f1f1f", "#666666", "#e7e7e7", "#ffffff"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2,
    "ytick.color": INK_2, "text.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def routes_side_by_side(inst: Instance, panels: dict[str, list[list[int]]], path: str) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(6.4 * len(panels), 3.3))
    for ax, (title, routes) in zip(axes, panels.items()):
        if len(routes) > len(SERIES):
            raise ValueError("more trips than palette slots: plot with one colour instead")
        for k, route in enumerate(routes):
            path_pts = [inst.coords[p] for p in [0, *route, 0]]
            xs, ys = zip(*path_pts)
            load = sum(inst.demand[p] for p in route)
            ax.plot(xs, ys, color=SERIES[k], lw=2, solid_capstyle="round",
                    label=f"Trip {k + 1} · {load} t")
            px, py = zip(*[inst.coords[p] for p in route])
            ax.scatter(px, py, s=48, color=SERIES[k], edgecolor=SURFACE, linewidth=2, zorder=3)
        hx, hy = inst.coords[0]
        ax.scatter([hx], [hy], s=110, marker="s", color=INK, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.annotate("Storage hall", (hx, hy), xytext=(0, -16), textcoords="offset points",
                    ha="center", va="top", fontsize=9, color=INK)
        ax.set_title(f"{title}\n{total_distance(inst, routes) / 1000:.1f} km driven, {len(routes)} trips",
                     loc="left", fontsize=11, color=INK)
        ax.set_aspect("equal")
        xs_all, ys_all = zip(*inst.coords)
        ax.set_xlim(min(xs_all) - 0.4, max(xs_all) + 0.4)
        ax.set_ylim(min(ys_all) - 0.6, max(ys_all) + 0.3)
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_visible(False)
        ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=8.5,
                  labelcolor=INK_2, handlelength=1.4)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def gap_bars(sizes: list[int], gaps: dict[str, list[float]], path: str) -> None:
    """Grouped bars: % above the best proven lower bound, per method and site size."""
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    width = 0.26
    for k, (method, values) in enumerate(gaps.items()):
        xs = [i + (k - (len(gaps) - 1) / 2) * width for i in range(len(sizes))]
        bars = ax.bar(xs, values, width=width - 0.02, color=SERIES[k], label=method,
                      edgecolor=SURFACE, linewidth=2)
        for bar, v in zip(bars, values):
            ax.annotate(f"{v:.1f}%", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                        fontsize=8.5, color=INK)
    ax.set_xticks(range(len(sizes)), [f"{n} points" for n in sizes])
    ax.set_ylabel("% more driving than the proven lower bound")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="both", length=0)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.13), ncol=len(gaps), frameon=False, labelcolor=INK_2)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
