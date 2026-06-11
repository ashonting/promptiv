"""ROBUSTNESS (2/2): the Orlando-vs-Guatemala-City flip holds from all 12 origins.
Dumbbell chart on the shared DashAway frame, matched to the hero."""
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib import patheffects as pe

import dashaway_style as ds

HERE = Path(__file__).parent
rows = json.load(open(HERE / "robust.json"))
rows.sort(key=lambda r: r["orlando_week"])
OBSERVED = "2026-06-08"

gaps = [r["orlando_week"] - r["guatemala_week"] for r in rows]
gmin, gmax = min(gaps), max(gaps)

fig = plt.figure(figsize=(12, 9.2), dpi=170)
ax = fig.add_axes([0.135, 0.105, 0.83, 0.60])

ds.header(
    fig,
    eyebrow="DashAway · Trip economics",
    series="2 / 2",
    headline="And it isn't a fluke of one city.",
    dek="The same week, priced from every US origin we cover: Guatemala City vs. "
        "Orlando, the all-in cost of seven nights.",
    finding=f"Orlando is the cheaper flight every single time, yet the week costs "
            f"${gmin:,} to ${gmax:,} more, from all 12 origins.",
)

y = np.arange(len(rows))
for i, r in enumerate(rows):
    ax.plot([r["guatemala_week"], r["orlando_week"]], [i, i],
            color=ds.HAIR, lw=2.6, zorder=1, solid_capstyle="round")
    ax.text((r["guatemala_week"] + r["orlando_week"]) / 2, i - 0.34,
            f"+${r['orlando_week'] - r['guatemala_week']:,}", ha="center",
            va="bottom", family=ds.MONO, fontsize=8.6, color=ds.MUTED, zorder=2)

ax.scatter([r["guatemala_week"] for r in rows], y, s=165, color=ds.GREEN,
           zorder=3, edgecolors=ds.PANEL, linewidths=1.2)
ax.scatter([r["orlando_week"] for r in rows], y, s=165, color=ds.RED,
           zorder=3, edgecolors=ds.PANEL, linewidths=1.2)

ax.set_yticks(y)
ax.set_yticklabels([r["origin"] for r in rows], fontsize=12)
ax.invert_yaxis()
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_xlabel("All-in cost of one week   (round-trip airfare + 7 nights)",
              fontsize=12, labelpad=8)
ax.set_xlim(480, 1440)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(ds.HAIR)
ax.grid(axis="x", color=ds.GRID, lw=1, zorder=0)
ax.tick_params(axis="x", labelsize=11, length=0)
ax.tick_params(axis="y", length=0)

# in-plot legend, top row
def chip(x, color, label):
    ax.scatter([x], [-1.05], s=165, color=color, edgecolors=ds.PANEL,
               linewidths=1.2, clip_on=False, zorder=5)
    t = ax.text(x + 22, -1.05, label, va="center", family=ds.SANS,
                fontsize=10.5, color=ds.INK, clip_on=False, zorder=5)
    t.set_path_effects([pe.withStroke(linewidth=2.5, foreground=ds.BG)])
chip(560, ds.GREEN, "Guatemala City  (the pricier flight)")
chip(920, ds.RED, "Orlando  (the cheaper flight, every time)")

ds.footer(fig, OBSERVED)
out = HERE / "trap_holds_everywhere.png"
fig.savefig(out, dpi=170)
print("wrote", out)
