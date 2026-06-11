"""HERO (rebuilt): airfare vs. ground cost — the two INDEPENDENT components.
Answers the methodological critique: the all-in chart put airfare inside the
y-axis. Plotted as independent axes, the two barely relate (r ~ -0.2), and the
'cheap flight / expensive week' trap becomes a real, populated quadrant."""
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib import patheffects as pe

import dashaway_style as ds

HERE = Path(__file__).parent
rows = json.load(open(HERE / "ATL.json"))["rows"]
OBSERVED = "2026-06-08"

A = np.array([r["fare"] for r in rows], float)       # airfare
B = np.array([r["daily"] * 7 for r in rows], float)  # 7-night ground cost
r = np.corrcoef(A, B)[0, 1]
mA, mB = np.median(A), np.median(B)

# quadrant colors (cheap flight = left, expensive ground = top)
TRAP, BARGAIN, WORTH, SPLURGE = ds.RED, ds.GREEN, "#3f72a4", "#cf7d3f"
def quad(a, b):
    if a < mA and b >= mB: return TRAP
    if a < mA and b < mB:  return BARGAIN
    if a >= mA and b < mB: return WORTH
    return SPLURGE
colors = [quad(a, b) for a, b in zip(A, B)]
counts = {c: colors.count(c) for c in (TRAP, BARGAIN, WORTH, SPLURGE)}

fig = plt.figure(figsize=(12, 9.2), dpi=170)
ax = fig.add_axes([0.092, 0.092, 0.86, 0.66])

ds.header(
    fig,
    eyebrow="DashAway · Trip economics",
    series="1 / 2",
    headline="The cheap flight is a trap.",
    dek="What you pay to fly there vs. what you pay to be there for a week, as "
        "independent costs. 96 destinations from Atlanta.",
    finding=f"The two barely relate (r = {r:.2f}). The cheapest flights tend to "
            f"have the priciest weeks on the ground, not the other way around.",
)

xmax, ymax = A.max() * 1.07, B.max() * 1.08
ax.set_xlim(0, xmax)
ax.set_ylim(0, ymax)

# quadrant tints + median split
ax.axvspan(0, mA, ymin=mB / ymax, ymax=1, color=TRAP, alpha=0.045, zorder=0)
ax.axhline(mB, color=ds.HAIR, lw=1.1, zorder=1)
ax.axvline(mA, color=ds.HAIR, lw=1.1, zorder=1)
ax.text(mA + 8, ax.get_ylim()[1] * 0.012, f"median airfare ${mA:,.0f}",
        family=ds.MONO, fontsize=8.3, color=ds.MUTED, va="bottom")
ax.text(xmax * 0.992, mB + 12, f"median ground ${mB:,.0f}", family=ds.MONO,
        fontsize=8.3, color=ds.MUTED, ha="right", va="bottom")

# corner quadrant labels
def corner(xf, yf, ha, va, title, sub, color, n):
    t = ax.text(xf, yf, f"{title}\n{sub}\n{n} of 96", transform=ax.transAxes,
                ha=ha, va=va, family=ds.SANS, fontsize=10.5, color=color,
                weight="semibold", linespacing=1.45, zorder=2)
    t.set_path_effects([pe.withStroke(linewidth=3, foreground=ds.BG)])
corner(0.015, 0.975, "left", "top", "THE TRAP", "cheap flight · pricey week",
       TRAP, counts[TRAP])
corner(0.015, 0.03, "left", "bottom", "BARGAINS", "cheap both ways",
       BARGAIN, counts[BARGAIN])
corner(0.985, 0.03, "right", "bottom", "WORTH THE FLIGHT",
       "pay to get there, cheap once you land", WORTH, counts[WORTH])
corner(0.985, 0.975, "right", "top", "SPLURGE", "expensive both ways",
       SPLURGE, counts[SPLURGE])

ax.scatter(A, B, c=colors, s=130, edgecolors=ds.PANEL, linewidths=0.9,
           alpha=0.95, zorder=3)

ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_xlabel("Round-trip airfare", fontsize=12, labelpad=8)
ax.set_ylabel("Ground cost for the week   (7 nights)", fontsize=12, labelpad=8)
ds.style_axes(ax, xgrid=True, ygrid=True)

by = {r0["city"]: r0 for r0 in rows}
def lbl(city, dx, dy, ha="left"):
    r0 = by[city]
    x0, y0 = r0["fare"], r0["daily"] * 7
    ax.annotate("", xy=(x0, y0), xytext=(x0 + dx, y0 + dy),
                arrowprops=dict(arrowstyle="-", color=ds.INK, lw=0.8,
                                alpha=0.45, shrinkA=2, shrinkB=6), zorder=4)
    t1 = ax.text(x0 + dx, y0 + dy, city, family=ds.SANS, fontsize=10.5,
                 weight="semibold", color=ds.INK, ha=ha, va="bottom", zorder=5)
    t2 = ax.text(x0 + dx, y0 + dy - 30,
                 f"${r0['fare']:,} flight  ·  ${r0['daily']*7:,} ground",
                 family=ds.MONO, fontsize=8.3, color=ds.SUB, ha=ha, va="top",
                 zorder=5)
    for t in (t1, t2):
        t.set_path_effects([pe.withStroke(linewidth=3, foreground=ds.BG)])

lbl("Orlando", 40, 150)
lbl("Honolulu", -45, 120, ha="right")
lbl("Guatemala City", 45, -120)
lbl("Cairo", -40, 150, ha="right")
lbl("Malé", -60, -40, ha="right")

ds.footer(fig, OBSERVED)
out = HERE / "cheap_flight_trap.png"
fig.savefig(out, dpi=170)
print("wrote", out, "| r=%.3f" % r, "| trap quadrant:", counts[TRAP])
