#!/usr/bin/env python3
"""fig_cpu_gpu_lesgo_centerline -- hub-height centerline of the matched CPU
and GPU runs (Fig. 6/7), in the PSSG style.

Data: fig_cpu_gpu_lesgo_centerline.csv, recovered from the vector paths of the
original matplotlib figure (see the CSV header).
"""
import csv
import os

import matplotlib.pyplot as plt

import pssg_style as ps
from pssg_style import VERM, BLUE, LGRAY

ps.apply(env=True)

OUT = os.path.dirname(os.path.abspath(__file__))

x, u_cpu, u_gpu = [], [], []
with open(os.path.join(OUT, "fig_cpu_gpu_lesgo_centerline.csv")) as f:
    rows = csv.DictReader(line for line in f if not line.startswith("#"))
    for r in rows:
        x.append(float(r["x_over_D"]))
        u_cpu.append(float(r["u_over_Uinf_cpu"]))
        u_gpu.append(float(r["u_over_Uinf_gpu"]))

ROTOR_X = 3.0   # rotor plane of the single turbine (Fig. 6)

fig, ax = plt.subplots(figsize=ps.FIGSIZE)
# Series 0 (CPU) solid, series 1 (GPU) in PSSG dash 1 drawn on top, so the
# coinciding curves both stay visible.
ax.plot(x, u_cpu, color=VERM, ls=ps.dashes(0), zorder=3, label="CPU")
ax.plot(x, u_gpu, color=BLUE, ls=ps.dashes(1), zorder=4, label="GPU")
ax.axvline(ROTOR_X, color=LGRAY, ls=ps.dashes(2), lw=1.0, zorder=1)

ax.set_xlim(2.35, 4.8)
ax.set_ylim(0.75, 1.0)
ax.set_xticks([2.5, 3.0, 3.5, 4.0, 4.5])
ax.set_yticks([0.75, 0.80, 0.85, 0.90, 0.95, 1.00])
ax.set_yticklabels(["0.75", "0.80", "0.85", "0.90", "0.95", "1.00"])
ax.set_xlabel("$x/D$")
ax.set_ylabel("$u/U_\\infty$ at hub height")
ax.set_title("CPU\u2013GPU LESGO hub-height centerline")
ax.grid(True, axis="y")
ax.legend(loc="lower left")
fig.tight_layout(pad=0.3)
fig.savefig(os.path.join(OUT, "fig_cpu_gpu_lesgo_centerline.pdf"))
fig.savefig(os.path.join(OUT, "fig_cpu_gpu_lesgo_centerline.png"), dpi=200)
print("wrote fig_cpu_gpu_lesgo_centerline")
