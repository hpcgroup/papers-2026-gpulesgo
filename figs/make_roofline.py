#!/usr/bin/env python3
"""fig_roofline -- per-kernel roofline of one production step.

Data: roofline_kernels.csv next to this script, written by
make_roofline_data.py from the full-step Nsight Compute capture
(runs/ncu_step_gpu16_59521430, rank 0, 604M case, 16 A100-80GB, 2026-10-07);
nothing else is needed to redraw the figure. Launches of the same kernel
within the step are summed (FLOPs, DRAM bytes, time), one point per kernel. Kernels below MIN_SHARE of the step's kernel
time are omitted (0.25% keeps 52 of 105 kernels and 99% of the time, and
both actuator-line force-projection kernels). Hand-written kernels are
colored by their Algorithm 1 stage; cuFFT kernels serve several stages and
are drawn hollow black. Only the actuator-line kernels and the
dealiased-grid FFT are labeled. Roofs: A100-80GB, 2.039 TB/s HBM2e and
9.7 TF/s FP64 (ridge 4.76 F/B). Stage-level aggregates quoted in the text
(77-81% of peak per stage, 78% for the step) are in roofline_stages.csv.
"""
import csv
import os

import matplotlib.pyplot as plt
import numpy as np

import pssg_style as ps
from pssg_style import VERM, BLUE, GREEN, PURPLE, ORANGE, ROSE, GRAY

ps.apply(env=True)
OUT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(OUT, "roofline_kernels.csv")
BW_TBS, PEAK_TF = 2.039, 9.7
MIN_SHARE = 0.25                      # % of the step's kernel time
CONV = "#646464"
COL = {"Derivatives": BLUE, "SGS": GREEN, "Convection": CONV, "Turbines": PURPLE,
       "Pressure": VERM, "Projection": ORANGE, "Other": ROSE}
MK = {"Derivatives": "o", "SGS": "^", "Convection": "s", "Turbines": "D",
      "Pressure": "X", "Projection": "p", "Other": "v"}

acc = {}
with open(DATA, newline="") as f:
    for r in csv.DictReader(f):
        acc[r["kernel"]] = dict(t=float(r["time_ms"]) * 1e-3, b=float(r["dram_bytes"]),
                                f=float(r["flops"]), st=set(r["stages"].split(";")),
                                fft=r["family"] == "cuFFT")
T = sum(a["t"] for a in acc.values())

fig, ax = plt.subplots(figsize=ps.FIGSIZE)
ax.set_xscale("log"); ax.set_yscale("log")
xs = np.logspace(-1.8, 2.5, 64)
ax.plot(xs, np.minimum(BW_TBS * xs, PEAK_TF), color=GRAY, zorder=2)
ax.annotate("2.04 TB/s HBM", xy=(0.07, 0.04 * BW_TBS * 2.6), color=GRAY,
            fontsize=12, rotation=37, ha="left", va="bottom")
ax.annotate("9.7 TF/s FP64", xy=(12, PEAK_TF * 1.18), color=GRAY,
            fontsize=12, ha="left", va="bottom")

MS0 = plt.rcParams["lines.markersize"] ** 2
shown = 0.0
for name, a in sorted(acc.items(), key=lambda kv: -kv[1]["t"]):
    if a["b"] <= 0 or a["t"] <= 0:
        continue
    ai, tf, share = a["f"] / a["b"], a["f"] / a["t"] / 1e12, 100 * a["t"] / T
    if share < MIN_SHARE:
        continue
    shown += share
    s = MS0 * 0.85
    if a["fft"]:
        ax.scatter([ai], [tf], s=s, facecolors="white", edgecolors="black",
                   marker="o", linewidths=0.9, zorder=3)
    else:
        st = next(iter(a["st"]))
        ax.scatter([ai], [tf], s=s, color=COL[st], marker=MK[st], zorder=4,
                   linewidths=0.5, edgecolors="white")
    if name.startswith("atm_lesgo_interface_atm_batch_convolute_force_gpu_6979"):
        ax.annotate("actuator-line force projection", xy=(ai, tf), xytext=(6, 10),
                    textcoords="offset points", ha="center", fontsize=12, color="#333333")
    # if name == "regular_fft<576>":
    #     ax.annotate("FFT on the 3/2 grid", xy=(ai, tf), xytext=(10, -10),
    #                 textcoords="offset points", ha="left", fontsize=10, color="#333333")

ms = 0.8 * MS0 ** 0.5
handles = [plt.Line2D([], [], ls="none", marker=MK[s], color=COL[s], ms=ms, label="Others" if s == "Other" else s)
           for s in ["Derivatives", "SGS", "Convection", "Turbines", "Pressure",
                     "Projection", "Other"]]
handles.append(plt.Line2D([], [], ls="none", marker="o", mfc="white", mec="black",
                          ms=ms, label="cuFFT"))
ax.legend(handles=handles, loc="lower right",
          handletextpad=0.3, borderaxespad=0.3, borderpad=0.3, labelspacing=0.2,
          handlelength=1.0, ncol=2, columnspacing=0.8)
ax.set_xlim(0.02, 300); ax.set_ylim(0.03, 30)
ax.set_xlabel("Arithmetic intensity (FLOP/byte)"); ax.set_ylabel("TFLOP/s")
ax.set_title("Roofline plot for LESGO kernels on A100 GPUs")
ax.grid(True, which="major", axis="both")
fig.tight_layout(pad=0.3)
fig.savefig(os.path.join(OUT, "fig_roofline.pdf"))
fig.savefig(os.path.join(OUT, "fig_roofline.png"), dpi=200)
n_shown = sum(1 for a in acc.values() if a["t"] > 0 and 100 * a["t"] / T >= MIN_SHARE)
print(f"wrote fig_roofline: {n_shown} of {len(acc)} kernels, {shown:.1f}% of kernel time")
