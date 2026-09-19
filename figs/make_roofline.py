#!/usr/bin/env python3
"""fig_roofline -- classic roofline of the production-step kernel families.
"""
import os

import matplotlib.pyplot as plt

import pssg_style as ps
from pssg_style import VERM, BLUE, GREEN, GRAY, LGRAY

ps.apply(env=True)
# a notch above the PSSG defaults: this plot carries per-point labels
plt.rcParams.update({"font.size": 11.5, "lines.markersize": 10})

OUT = os.path.dirname(os.path.abspath(__file__))

# family, AI (F/B), TFLOP/s, % of profiled time, class (0 = hand-written
# OpenACC, 1 = cuFFT, 2 = ATM/scattered)
fams = [
    ("convection",        0.074, 0.13, 24.3, 0),
    ("SGS",               0.163, 0.26, 16.8, 0),
    ("pressure",          0.063, 0.11,  1.5, 0),
    ("regular\\_fft",     1.471, 1.73, 32.5, 1),
    ("vector\\_fft",      1.886, 3.13, 23.4, 1),
    ("ATM force proj.",  33.57,  2.70,  1.4, 2),
    ("ATM sampling",      4.805, 0.40,  0.05, 2),
]
BW_TBS = 2.039     # A100-80 HBM2e
PEAK_TF = 9.7      # FP64 (FMA)
RIDGE = PEAK_TF / BW_TBS

fig, ax = plt.subplots(figsize=ps.FIGSIZE)
ax.set_xscale("log")
ax.set_yscale("log")

# roofs
import numpy as np
xs = np.logspace(-1.5, 2.0, 64)
roof = np.minimum(BW_TBS * xs, PEAK_TF)
ax.plot(xs, roof, color=GRAY, zorder=2)
ax.annotate("2.04 TB/s HBM", xy=(0.115, 0.115 * BW_TBS * 1.35), color=GRAY,
            fontsize=10.5, rotation=35, ha="left", va="bottom")
ax.annotate("9.7 TF/s FP64", xy=(11, PEAK_TF * 1.18), color=GRAY,
            fontsize=10.5, ha="left", va="bottom")
ax.axvline(RIDGE, ls=ps.dashes(2), lw=1.0, color=LGRAY, zorder=1)

cols = {0: BLUE, 1: VERM, 2: GREEN}
mks = {0: ps.MARKERS[0], 1: ps.MARKERS[1], 2: ps.MARKERS[2]}
MS = plt.rcParams["lines.markersize"] ** 2   # fixed marker area; time share not encoded
for name, ai, tf, share, cls in fams:
    ax.scatter([ai], [tf], s=MS, color=cols[cls],
               marker=mks[cls], zorder=3, linewidths=0)
# name: (x, y, offset in points, horizontal alignment)
lab = {
    "convection":       (0.074, 0.13, (7, -16), "left"),
    "SGS":              (0.163, 0.26, (8, -5), "left"),
    "pressure":         (0.063, 0.11, (-12, 13), "left"),
    "regular\\_fft":    (1.471, 1.73, (-8, -16), "left"),
    "vector\\_fft":     (1.886, 3.13, (8, 5), "left"),
    "ATM force proj.":  (33.57, 2.70, (0, 12), "center"),
    "ATM sampling":     (4.805, 0.40, (0, 12), "center"),
}
for name, (x, y, off, ha) in lab.items():
    ax.annotate(name.replace("\\_", "_"), xy=(x, y), xytext=off, ha=ha,
                textcoords="offset points", fontsize=10.5, color="#333333")

handles = [plt.Line2D([], [], ls="none", marker=mks[c], color=cols[c], ms=MS**0.5,
                      label=t) for c, t in
           ((0, "hand-written"), (1, "cuFFT"), (2, "actuator line"))]
ax.legend(handles=handles, loc="lower right", handletextpad=0.3,
          borderaxespad=0.3)
ax.set_xlim(0.03, 110)
ax.set_ylim(0.05, 22)
ax.set_xlabel("arithmetic intensity (FLOP/byte)")
ax.set_ylabel("TFLOP/s")
ax.set_title("Roofline of the production step on A100")
ax.grid(True, which="major", axis="both")
fig.tight_layout(pad=0.3)
fig.savefig(os.path.join(OUT, "fig_roofline.pdf"))
fig.savefig(os.path.join(OUT, "fig_roofline.png"), dpi=200)
print("wrote fig_roofline")