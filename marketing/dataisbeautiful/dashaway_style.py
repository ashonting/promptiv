"""Shared editorial design system for the DashAway data-story charts.
One source of truth so the two charts read as a designed series, not two plots."""
import glob
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
from matplotlib import patheffects as pe

HERE = Path(__file__).parent
for _f in glob.glob(str(HERE / "fonts" / "*.ttf")):
    fm.fontManager.addfont(_f)

SERIF = "Instrument Serif"
SANS = "Inter"
MONO = "IBM Plex Mono"

# Tinted neutrals (never pure black/white) + brand purple.
BG = "#faf9fc"
PANEL = "#ffffff"
INK = "#1b1a23"
SUB = "#52505e"
MUTED = "#8a8895"
GRID = "#eceaf2"
HAIR = "#dcd9e6"
ACCENT = "#7c5cff"   # brand purple

# Editorial cost ramp (cheap -> expensive), muted, no stock RdYlGn garishness.
COST = LinearSegmentedColormap.from_list("cost", [
    (0.00, "#0f7d64"),  # deep teal-green  = cheap day
    (0.28, "#5fa96a"),  # sage
    (0.52, "#cbab4a"),  # muted gold
    (0.76, "#cf7d3f"),  # warm amber
    (1.00, "#bd463c"),  # terracotta red   = expensive day
])
GREEN = "#0f7d64"
RED = "#bd463c"

plt.rcParams.update({
    "font.family": SANS,
    "text.parse_math": False,   # render literal '$' — we print dollar figures, not math
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "text.color": INK,
    "axes.edgecolor": HAIR,
    "axes.labelcolor": SUB,
    "xtick.color": MUTED,
    "ytick.color": INK,
})


def header(fig, eyebrow, series, headline, dek, finding,
           x=0.066, top=0.96, head_size=33):
    """Draw the shared header block. Identical geometry across both charts."""
    # brand kicker: a small accent tick + plain uppercase mono (no fragile tracking)
    fig.add_artist(Rectangle((x, top - 0.016), 0.014, 0.007, color=ACCENT,
                             transform=fig.transFigure, zorder=5))
    fig.text(x + 0.024, top, eyebrow.upper(), family=MONO, fontsize=10,
             color=ACCENT, weight="medium", va="top")
    fig.text(1 - x, top, series, family=MONO, fontsize=10,
             color=MUTED, ha="right", va="top")
    fig.text(x, top - 0.052, headline, family=SERIF, fontsize=head_size,
             color=INK, va="top")
    fig.text(x, top - 0.115, dek, family=SANS, fontsize=12.5, color=SUB,
             va="top")
    ft = fig.text(x, top - 0.152, finding, family=SANS, fontsize=12.5,
                  color=ACCENT, weight="semibold", va="top")
    ft.set_path_effects([pe.withStroke(linewidth=2.5, foreground=BG)])
    fig.add_artist(Line2D([x, 1 - x], [top - 0.178, top - 0.178],
                          color=HAIR, lw=1.1, transform=fig.transFigure))


def footer(fig, observed, x=0.066, y=0.034):
    fig.add_artist(Circle(
        (x + 0.004, y + 0.004), 0.006, color=ACCENT,
        transform=fig.transFigure, zorder=5))
    fig.text(x + 0.022, y, "dashaway.io", family=SERIF, fontsize=13,
             color=INK, va="center")
    fig.text(1 - x, y,
             f"Live Google Flights fares (7-night round trip)  +  per-destination "
             f"daily-cost estimates   ·   {observed}",
             family=MONO, fontsize=8.6, color=MUTED, ha="right", va="center")


def style_axes(ax, xgrid=True, ygrid=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(HAIR)
    ax.grid(axis="x" if xgrid and not ygrid else "both" if xgrid and ygrid
            else "y", color=GRID, lw=1, zorder=0)
    ax.tick_params(labelsize=11, length=0)
