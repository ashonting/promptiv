"""HERO (1/2): The cheap flight is a trap.
Airfare vs all-in cost of one week, 96 destinations from Atlanta,
colored by the hidden variable (daily on-ground cost)."""
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import FancyBboxPatch
from matplotlib import patheffects as pe

import dashaway_style as ds

HERE = Path(__file__).parent
rows = json.load(open(HERE / "ATL.json"))["rows"]
OBSERVED = "2026-06-08"

fare = np.array([r["fare"] for r in rows], float)
allin = np.array([r["allin"] for r in rows], float)
daily = np.array([r["daily"] for r in rows], float)
r2 = np.corrcoef(fare, allin)[0, 1] ** 2

fig = plt.figure(figsize=(12, 9.2), dpi=170)
ax = fig.add_axes([0.066, 0.092, 0.84, 0.66])

ds.header(
    fig,
    eyebrow="DashAway · Trip economics",
    series="1 / 2",
    headline="The cheap flight is a trap.",
    dek="Round-trip airfare vs. what a full week actually costs. 96 destinations, "
        "all priced from Atlanta on one day.",
    finding=f"Airfare explains barely a third of the trip (R² = {r2:.2f}). "
            f"The flight price tells you almost nothing.",
)

xmax = fare.max() * 1.07
ymax = allin.max() * 1.06
ax.set_xlim(0, xmax)
ax.set_ylim(540, ymax)

# weak trend
z = np.polyfit(fare, allin, 1)
xs = np.linspace(fare.min(), fare.max(), 50)
ax.plot(xs, np.polyval(z, xs), color=ds.MUTED, lw=1.3, ls=(0, (1, 3)),
        alpha=0.8, zorder=2)

sc = ax.scatter(fare, allin, c=daily, cmap=ds.COST, s=135,
                edgecolors=ds.PANEL, linewidths=0.9, alpha=0.97,
                vmin=30, vmax=210, zorder=3)

ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_xlabel("Round-trip airfare", fontsize=12, labelpad=8)
ax.set_ylabel("All-in cost of one week   (airfare + 7 nights on the ground)",
              fontsize=12, labelpad=8)
ds.style_axes(ax, xgrid=True, ygrid=True)

by = {r["city"]: r for r in rows}
def lbl(city, dx, dy, ha="left", note=None, name=None):
    r = by[city]
    ax.annotate("", xy=(r["fare"], r["allin"]),
                xytext=(r["fare"] + dx, r["allin"] + dy),
                arrowprops=dict(arrowstyle="-", color=ds.INK, lw=0.8,
                                alpha=0.45, shrinkA=2, shrinkB=6), zorder=4)
    tx, ty = r["fare"] + dx, r["allin"] + dy
    t1 = ax.text(tx, ty, name or city, family=ds.SANS, fontsize=11,
                 weight="semibold", color=ds.INK, ha=ha, va="bottom", zorder=5)
    t2 = ax.text(tx, ty - 36, f"${r['fare']:,} flight  ·  ${r['allin']:,} week",
                 family=ds.MONO, fontsize=8.8, color=ds.SUB, ha=ha, va="top",
                 zorder=5)
    line = ax.text(tx, ty - 96, note or "", family=ds.SANS, fontsize=9.3,
                   style="italic", color=ds.MUTED, ha=ha, va="top", zorder=5)
    for t in (t1, t2, line):
        t.set_path_effects([pe.withStroke(linewidth=3, foreground=ds.BG)])

lbl("Orlando", 55, 285, note="cheapest flight of all 96")
lbl("Honolulu", -95, 150, ha="right", note="cheap flight, brutal week")
lbl("Guatemala City", 135, 250, note="cheapest week of all 96")
lbl("Sofia", 80, 250, note="pricey flight buys a cheap week")
lbl("Malé", -120, 35, ha="right", name="Malé, Maldives")

cb = fig.colorbar(sc, ax=ax, pad=0.015, fraction=0.043, aspect=26)
cb.set_label("Daily on-ground cost  ($ / day)", family=ds.MONO, fontsize=9.5,
             color=ds.SUB, labelpad=10)
cb.ax.tick_params(labelsize=9, length=0)
cb.outline.set_edgecolor(ds.HAIR)

ds.footer(fig, OBSERVED)
out = HERE / "cheap_flight_trap.png"
fig.savefig(out, dpi=170)
print("wrote", out, "| r2=%.3f" % r2)
