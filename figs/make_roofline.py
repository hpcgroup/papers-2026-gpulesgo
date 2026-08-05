#!/usr/bin/env python3
"""fig_roofline -- classic roofline of the production-step kernel families.

Data: roofline ncu capture of rank 0 on the wf60 production case
(case tree runs/ncu_gpu16_55477553/wf60_roofline_rank0.ncu-rep, A100-80).
Per family: FLOPs = (dadd+dmul+2*dfma [+f-ops]) x elapsed cycles, bytes =
dram__bytes.sum.per_second x duration, aggregated over captured launches.
AI = FLOPs/DRAM bytes; rate = FLOPs/duration; size ~ share of profiled time.
Roofs: A100-80GB, 2.039 TB/s HBM2e and 9.7 TF/s FP64 (ridge 4.76 F/B).
"""
import os

import matplotlib.pyplot as plt

import pssg_style as ps
from pssg_style import VERM, BLUE, GREEN, GRAY, LGRAY

ps.apply()

OUT = os.path.dirname(os.path.abspath(__file__))

# family, AI (F/B), TFLOP/s, % of profiled time, class (0 = hand-written
# OpenACC, 1 = cuFFT, 2 = ATM/scattered)
fams = [
    ("convection",        0.074, 0.13, 24.1, 0),
    ("SGS",               0.163, 0.26, 16.7, 0),
    ("pressure",          0.063, 0.11,  1.5, 0),
    ("regular\\_fft",     1.476, 1.71, 32.7, 1),
    ("vector\\_fft",      1.899, 3.14, 23.4, 1),
    ("ATM force proj.",  34.63,  2.59,  1.5, 2),
    ("ATM sampling",      5.193, 0.41,  0.05, 2),
]
BW_TBS = 2.039     # A100-80 HBM2e
PEAK_TF = 9.7      # FP64 (FMA)
RIDGE = PEAK_TF / BW_TBS

fig, ax = plt.subplots(figsize=(3.45, 2.4))
ax.set_xscale("log")
ax.set_yscale("log")

# roofs
import numpy as np
xs = np.logspace(-1.5, 2.0, 64)
roof = np.minimum(BW_TBS * xs, PEAK_TF)
ax.plot(xs, roof, lw=1.1, color=GRAY, zorder=2)
ax.annotate("2.04 TB/s HBM", xy=(0.115, 0.115 * BW_TBS * 1.35), color=GRAY,
            fontsize=7, rotation=43, ha="left", va="bottom")
ax.annotate("9.7 TF/s FP64", xy=(11, PEAK_TF * 1.18), color=GRAY,
            fontsize=7, ha="left", va="bottom")
ax.axvline(RIDGE, ls=ps.dashes(2), lw=0.7, color=LGRAY, zorder=1)

cols = {0: BLUE, 1: VERM, 2: GREEN}
mks = {0: ps.MARKERS[0], 1: ps.MARKERS[1], 2: ps.MARKERS[2]}
for name, ai, tf, share, cls in fams:
    ax.scatter([ai], [tf], s=30 + 9 * share**0.9, color=cols[cls],
               marker=mks[cls], zorder=3, linewidths=0)
lab = {
    "convection":       (0.074, 0.13, (4, -11)),
    "SGS":              (0.163, 0.26, (5, -3)),
    "pressure":         (0.063, 0.11, (-4, 6)),
    "regular\\_fft":    (1.476, 1.71, (-6, -14)),
    "vector\\_fft":     (1.899, 3.14, (5, 3)),
    "ATM force proj.":  (34.63, 2.59, (-4, 6)),
    "ATM sampling":     (5.193, 0.41, (-8, 8)),
}
for name, (x, y, off) in lab.items():
    ax.annotate(name.replace("\\_", "_"), xy=(x, y), xytext=off,
                textcoords="offset points", fontsize=6.5, color="#333333")

handles = [plt.Line2D([], [], ls="none", marker=mks[c], color=cols[c], ms=5,
                      label=t) for c, t in
           ((0, "hand-written"), (1, "cuFFT"), (2, "actuator line"))]
ax.legend(handles=handles, loc="lower right", handletextpad=0.3,
          borderaxespad=0.3)
ax.set_xlim(0.03, 110)
ax.set_ylim(0.05, 22)
ax.set_xlabel("arithmetic intensity (FLOP/byte)")
ax.set_ylabel("TFLOP/s")
ax.grid(True, which="major", axis="both")
fig.tight_layout(pad=0.3)
fig.savefig(os.path.join(OUT, "fig_roofline.pdf"))
fig.savefig(os.path.join(OUT, "fig_roofline.png"), dpi=200)
print("wrote fig_roofline")