"""Shared PSSG style for the paper figures.

Mirrors the pssg-plots PlotEnvironment (/home/wcy/paper/pssg-plots):
Gill Sans, top/right spines removed, #606060 spines with inward ticks,
dotted y-grid, filled edge-free markers, hatched bars, and the PSSG
palette order (vermillion, blue, green, black, purple, rose, orange,
sky).

Two geometries:
  apply(env=True)  -- the PlotEnvironment defaults verbatim: 5 x 3 in
                      figure (FIGSIZE), matplotlib default font sizes
                      (10 pt base, 12 pt title), 2 pt lines, 8 pt markers.
                      LaTeX scales the figure to the column (x0.7).
                      Used by the measured-data plots.
  apply()          -- compact variant for the hand-drawn schematics:
                      sized for a 3.45 in column with 8 pt fonts.
"""
import os

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt

# pssgplot.PALETTE order
VERM = "#D55E00"
BLUE = "#0072B2"
GREEN = "#009E73"
BLACK = "#000000"
PURPLE = "#800080"
ROSE = "#CC79A7"
ORANGE = "#E69F00"
SKY = "#56B4E9"
PALETTE = [VERM, BLUE, GREEN, BLACK, PURPLE, ROSE, ORANGE, SKY]
PALETTE1 = [VERM, BLUE, GREEN, PURPLE, ROSE, ORANGE, SKY]  # no black

HATCHES = ["xxx", "//", "|||", "OO", "++", "**", "\\\\\\"]
MARKERS = ["o", "^", "s", "D", "X", "p"]
LINESTYLES = [(), (1, 2), (4, 2), (3, 1, 1, 1), (3, 1, 1, 1, 1, 1),
              (5, 1), (7, 2, 1, 2)]

AXGRAY = "#606060"   # spines, tick marks (pssgplot uses #606060)
GRAY = "#777777"     # reference annotations
LGRAY = "#aaaaaa"    # ideal lines, connectors

FONT_PATH = "/home/wcy/paper/pssg-plots/fonts/gillsans.ttf"
FIGSIZE = (5, 3)     # pssgplot LinePlot/BarPlot default figsize


def dashes(i):
    """Line style i as a matplotlib linestyle (pssgplot.LINESTYLES)."""
    d = LINESTYLES[i % len(LINESTYLES)]
    return "-" if not d else (0, d)


def apply(env=False):
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(f"Gill Sans font not found: {FONT_PATH}")
    font_manager.fontManager.addfont(FONT_PATH)
    name = font_manager.FontProperties(fname=FONT_PATH).get_name()
    if env:
        # Equivalent of `with PlotEnvironment(font_path=...)`: seaborn's
        # context only sets the eight keys below on top of matplotlib's
        # defaults, so font sizes are matplotlib's (10 pt, title 12 pt).
        plt.rcParams.update({
            "font.family": name,
            "mathtext.fontset": "stixsans",
            "font.size": 10,
            "axes.labelsize": "medium",
            "axes.titlesize": "large",
            "xtick.labelsize": "medium",
            "ytick.labelsize": "medium",
            "legend.fontsize": "medium",
            "legend.frameon": False,
            "lines.linewidth": 2,
            "lines.markersize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "axes.edgecolor": AXGRAY,
            "axes.axisbelow": True,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.color": AXGRAY,
            "ytick.color": AXGRAY,
            "xtick.labelcolor": "black",
            "ytick.labelcolor": "black",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "grid.linestyle": ":",
            "grid.color": "#b0b0b0",
            "grid.linewidth": 0.8,
            "hatch.linewidth": 0.5,
            "pdf.fonttype": 42,
        })
        return
    plt.rcParams.update({
        "font.family": name,
        "mathtext.fontset": "stixsans",
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "axes.edgecolor": AXGRAY,
        "axes.axisbelow": True,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.color": AXGRAY,
        "ytick.color": AXGRAY,
        "xtick.labelcolor": "black",
        "ytick.labelcolor": "black",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "grid.linestyle": ":",
        "grid.color": "#b0b0b0",
        "grid.linewidth": 0.6,
        "hatch.linewidth": 0.5,
        "pdf.fonttype": 42,
    })
