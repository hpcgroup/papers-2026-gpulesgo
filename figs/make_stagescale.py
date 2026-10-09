#!/usr/bin/env python3
"""fig_stagescale -- per-stage device kernel time per step vs GPU count
(strong scaling of the 604M-cell production case); "Others" is the rest of
the measured step time (kernels of the routines elided in Algorithm 1 plus
the time the GPU is idle).

Data: stagescale_kernel.csv from make_stagescale_data.py (nsys traces of all
ranks: runs/nsys_57484319 for 16 GPUs and the pm_nsys_gpu{32,64}nz512.sbatch
runs for 32/64 GPUs; kernel time per stage averaged over steady steps and
over ranks, stages attributed as in make_roofline_data.py). The bar total is
the unprofiled step time of fig_scaling's 604M series
(runs/z512_gpu{16,32,64}nz512_57483793/57484316/57484317, clean-step means),
so Others = step time - kernel time of the named stages: the Other kernels
(6.5 / 3.5 / 2.0 ms on 16 / 32 / 64 GPUs) plus the time the device waits on
host work, communication and synchronization. Stage colors follow Algorithm 1.
"""
import csv
import os

import matplotlib.pyplot as plt

import pssg_style as ps
from pssg_style import VERM, BLUE, GREEN, PURPLE, ROSE, ORANGE

ps.apply(env=True)
OUT = os.path.dirname(os.path.abspath(__file__))
CONV = "#646464"                      # stgconv in paper.tex
STEP_MS = {16: 161.9, 32: 93.4, 64: 72.2}   # fig_scaling 604M series
GPUS = [16, 32, 64]

# bottom -> top; (stage, color, text color, hatch) as the previous wall-clock
# version of this figure, with Convection added
STAGES = [
    ("Pressure",    VERM,   "white", "xxx"),
    ("Derivatives", BLUE,   "white", "//"),
    ("SGS",         GREEN,  "white", "|||"),
    ("Convection",  CONV,   "white", "\\\\"),
    ("Turbines",    PURPLE, "white", "OO"),
    ("Projection",  ORANGE, "black", "**"),
]
OTHERS = ("Others", ROSE, "black", "++")

data = {}
with open(os.path.join(OUT, "stagescale_kernel.csv"), newline="") as f:
    for r in csv.DictReader(f):
        if r["agg"] == "mean":
            data.setdefault(int(r["gpus"]), {})[r["stage"]] = float(r["ms"])
have = [g for g in GPUS if g in data]
print("GPU counts with kernel data:", have)

fig, ax = plt.subplots(figsize=ps.FIGSIZE)
x = {g: i for i, g in enumerate(GPUS)}
for g in have:
    bottom = 0.0
    segs = [(n, data[g][n], c, tc, h) for n, c, tc, h in STAGES]
    ksum = sum(v for _, v, _, _, _ in segs)
    segs.append((OTHERS[0], STEP_MS[g] - ksum, OTHERS[1], OTHERS[2], OTHERS[3]))
    for name, v, col, tcol, hatch in segs:
        ax.bar(x[g], v, 0.55, bottom=bottom, color=col, hatch=hatch,
               edgecolor="black", linewidth=0,
               label=name if g == have[0] else None, zorder=3)
        if v > 7.5:
            ax.annotate(f"{v:.0f}", xy=(x[g], bottom + v / 2), ha="center",
                        va="center", fontsize=11, color=tcol, zorder=4)
        bottom += v
    ax.annotate(f"{bottom:.0f} ms", xy=(x[g], bottom), xytext=(0, 4),
                textcoords="offset points", ha="center", fontsize=12)

ax.set_xticks(list(x.values()))
ax.set_xticklabels([str(g) for g in GPUS])
ax.set_xlim(-0.55, 2.6)
ax.set_ylim(0, 180)
ax.set_yticks([0, 30, 60, 90, 120, 150, 180])
ax.set_xlabel("Number of GPUs")
ax.set_ylabel("Time (ms)")
ax.set_title("Device time by stage on the 604M-cell grid")
ax.grid(True, axis="y")
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles[::-1], labels[::-1], loc="upper right", ncol=2,
          columnspacing=0.8, handletextpad=0.4, borderaxespad=0.2,
          handlelength=1.2, labelspacing=0.35)
fig.tight_layout(pad=0.3)
fig.savefig(os.path.join(OUT, "fig_stagescale.pdf"))
fig.savefig(os.path.join(OUT, "fig_stagescale.png"), dpi=200)
print("wrote fig_stagescale")
