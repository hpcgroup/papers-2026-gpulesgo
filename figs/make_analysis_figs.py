#!/usr/bin/env python3
"""Generate the analysis figures for the LESGO GPU paper.

Outputs (vector PDF for LaTeX + PNG previews):
  fig_sol.pdf        -- per-kernel Nsight Compute speed-of-light scatter
                        (compute SOL vs memory SOL, sized by time share)
  fig_stagescale.pdf -- per-stage step-time breakdown vs GPU count
                        (strong scaling, 384-level production series)

Data sources:
  fig_sol:        runs/ncu_gpu16_55477553/ncu_details.csv (rank-0 ncu full
                  section set, production case, 16xA100, one steady step).
                  When the case tree is not mounted, falls back to the
                  embedded per-kernel table below (same job, aggregated
                  by the CSV branch of this script).
  fig_stagescale: runs/scal_gpu{16,32,64}nz384_*/run.log stage timers
                  (last wbase snapshot; extract_timing.sh semantics)

Style: shared PSSG environment (pssg_style.py).
"""
import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import pssg_style as ps
from pssg_style import VERM, BLUE, GREEN, PURPLE, ROSE, ORANGE, GRAY, LGRAY

ps.apply()

OUT = os.path.dirname(os.path.abspath(__file__))
NCU_CSV = ("/pscratch/sd/c/cunyang/msu/case/lesgo/test-cases/"
           "large_windfarm_3072x384x400_60turbines/runs/"
           "ncu_gpu16_55477553/ncu_details.csv")

# Embedded fallback for fig_sol: (compute SOL %, memory SOL %, marker
# area in pt^2 with the max(9, 900*dur/tot) floor already applied),
# aggregated from ncu_gpu16_55477553/ncu_details.csv.
ACC = [
    (22.46, 74.59, 9.0), (24.28, 80.28, 48.1), (76.00, 38.88, 9.0),
    (36.57, 67.33, 23.8), (27.79, 67.22, 9.0), (23.91, 80.28, 41.5),
    (31.28, 60.84, 9.0), (46.02, 56.92, 9.0), (25.26, 67.11, 9.0),
    (34.20, 87.68, 17.6), (3.95, 8.27, 9.0), (51.91, 49.72, 9.0),
    (58.17, 51.46, 9.0), (35.74, 58.45, 9.0), (51.12, 34.09, 9.0),
    (48.35, 56.71, 9.0), (49.46, 69.63, 9.0), (48.16, 83.54, 9.0),
    (3.53, 4.56, 9.0), (40.88, 81.55, 15.2), (62.92, 90.78, 15.3),
    (38.74, 80.85, 9.0), (40.01, 80.85, 9.0), (35.24, 83.77, 21.5),
    (28.57, 75.70, 9.0), (64.25, 90.13, 14.9), (39.78, 80.78, 9.0),
    (40.19, 80.93, 9.0), (33.31, 88.41, 33.0), (40.56, 84.03, 9.0),
    (67.06, 67.17, 9.0), (1.58, 10.36, 9.0), (12.71, 5.60, 9.0),
    (72.12, 64.83, 9.0), (33.72, 88.46, 33.0), (40.61, 84.82, 9.0),
    (35.40, 87.90, 33.2), (63.17, 41.25, 9.0), (45.41, 53.26, 9.0),
    (57.72, 47.83, 9.0), (57.50, 29.45, 9.0), (6.21, 3.85, 9.0),
    (60.07, 37.31, 9.0), (63.08, 35.95, 9.0), (41.77, 85.38, 13.4),
]
FFT = [
    (53.28, 81.27, 111.6), (35.57, 69.32, 125.9), (25.10, 47.79, 168.5),
    (55.60, 80.84, 99.4),
]


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=200)
    plt.close(fig)
    print("wrote", name)


# ----------------------------------------------------------------------------
# fig_sol -- Nsight Compute speed-of-light scatter, one point per kernel
# ----------------------------------------------------------------------------
WANT = {"Compute (SM) Throughput": "sm",
        "Memory Throughput": "mem",
        "DRAM Throughput": "dram",
        "Duration": "dur"}


def family(name):
    return "cufft" if ("fft<" in name or "Placeholder" in name) else "acc"


def load_ncu(path):
    inst = defaultdict(dict)   # (ID) -> {kernel, sm, mem, dram, dur}
    with open(path) as f:
        for row in csv.reader(f):
            if len(row) < 15 or row[0] == "ID":
                continue
            iid, k, metric, unit, val = row[0], row[4], row[12], row[13], row[14]
            if metric in WANT:
                key = WANT[metric]
                v = float(val.replace(",", ""))
                if key == "dur" and unit == "ms":
                    v *= 1000.0            # normalize to us
                inst[iid][key] = v
                inst[iid]["kernel"] = k

    # aggregate instances -> unique kernels (duration-weighted metric means)
    kern = defaultdict(lambda: {"dur": 0.0, "sm": 0.0, "mem": 0.0, "dram": 0.0})
    for rec in inst.values():
        k = rec["kernel"]
        d = rec["dur"]
        kern[k]["dur"] += d
        for m in ("sm", "mem", "dram"):
            kern[k][m] += rec[m] * d
    for k, r in kern.items():
        for m in ("sm", "mem", "dram"):
            r[m] /= r["dur"]

    tot = sum(r["dur"] for r in kern.values())
    print(f"{len(inst)} instances, {len(kern)} unique kernels, "
          f"{tot/1e3:.2f} ms profiled")

    # cross-check the prose claims on the dominant kernels (>=2% of time each)
    for fam, label in (("acc", "hand-written"), ("cufft", "cuFFT")):
        big = [(r["dur"], r["dram"], k) for k, r in kern.items()
               if family(k) == fam and r["dur"] / tot >= 0.02]
        big.sort(reverse=True)
        if big:
            drams = [d for _, d, _ in big]
            share = sum(d for d, _, _ in big) / tot
            print(f"  {label}: {len(big)} kernels >=2% of time "
                  f"({share*100:.0f}% together), DRAM {min(drams):.0f}"
                  f"-{max(drams):.0f}% of peak")
            for d, dr, k in big[:6]:
                print(f"      {d/1e3:6.2f} ms  DRAM {dr:4.1f}%  {k[:60]}")

    pts = {"acc": [], "cufft": []}
    for k, r in kern.items():
        s = max(9.0, 900.0 * r["dur"] / tot)
        pts[family(k)].append((r["sm"], r["mem"], s))
    return pts["acc"], pts["cufft"]


if os.path.exists(NCU_CSV):
    acc_pts, fft_pts = load_ncu(NCU_CSV)
else:
    print("ncu_details.csv not mounted; using embedded job-55477553 table")
    acc_pts, fft_pts = ACC, FFT

fig, ax = plt.subplots(figsize=(3.45, 2.55))
ax.fill_between([0, 100], [0, 100], [100, 100], color="#f0f0f0", zorder=0)
ax.plot([0, 100], [0, 100], ls=ps.dashes(2), lw=0.8, color=LGRAY, zorder=1)
ax.annotate("memory-bound", xy=(6, 91), fontsize=7, color=GRAY, ha="left")
ax.annotate("compute-bound", xy=(97, 30), fontsize=7, color=GRAY, ha="right")

for pts, color, z in ((acc_pts, VERM, 3), (fft_pts, BLUE, 4)):
    ax.scatter([p[0] for p in pts], [p[1] for p in pts],
               s=[p[2] for p in pts], facecolor=color, edgecolor="white",
               linewidth=0.6, alpha=0.85, zorder=z)

legend = [Line2D([], [], marker="o", ls="none", ms=6, mfc=VERM, mec="white",
                 label="hand-written (OpenACC)"),
          Line2D([], [], marker="o", ls="none", ms=6, mfc=BLUE, mec="white",
                 label="cuFFT (library)")]
ax.legend(handles=legend, loc="lower right",
          handletextpad=0.3, borderaxespad=0.2)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_xlabel("compute throughput (% of SM peak)")
ax.set_ylabel("memory throughput (% of peak)")
ax.grid(True)
fig.tight_layout(pad=0.3)
save(fig, "fig_sol")

# ----------------------------------------------------------------------------
# fig_stagescale -- per-stage step time vs GPU count (strong, 384-level)
# ----------------------------------------------------------------------------
# Stage timers (s) at the last wbase snapshot of runs/scal_gpu{16,32,64}nz384_*
# (sampled step 0.155 s vs 0.152 s true average at 16 GPUs, within 2%).
# Convection reads < 0.3 ms at every scale (its kernels drain inside the
# pressure stage's first synchronization) and is folded into the caption.
gpus = [16, 32, 64]
# Colors and hatches follow the PSSG lists in order, series i taking
# PALETTE1[i] (the palette with black removed) and HATCHES[i].
stages = [
    ("Pressure",           [0.0570, 0.0235, 0.0172], VERM,   "white", "xxx"),
    ("Derivatives + SGS",  [0.0607, 0.0330, 0.0191], BLUE,   "white", "//"),
    ("Turbines",           [0.0082, 0.0041, 0.0020], GREEN,  "white", "|||"),
    ("Projection",         [0.0053, 0.0036, 0.0028], PURPLE, "white", "OO"),
    ("Other",              [0.0304, 0.0290, 0.0309], ROSE,   "black", "++"),
]

fig, ax = plt.subplots(figsize=(3.45, 2.35))
x = range(len(gpus))
bottom = [0.0] * len(gpus)
for name, vals, color, tcol, hatch in stages:
    ms = [v * 1e3 for v in vals]
    ax.bar(x, ms, 0.55, bottom=bottom, color=color, hatch=hatch,
           edgecolor="black", linewidth=0, label=name, zorder=3)
    for i, (b, v) in enumerate(zip(bottom, ms)):
        if v > 7.5:   # direct-label the large segments
            ax.annotate(f"{v:.0f}", xy=(i, b + v / 2), ha="center",
                        va="center", fontsize=6.5, color=tcol, zorder=4)
    bottom = [b + v for b, v in zip(bottom, ms)]

for i, b in enumerate(bottom):
    ax.annotate(f"{b:.0f} ms", xy=(i, b), xytext=(0, 3),
                textcoords="offset points", ha="center", fontsize=7.5)

ax.set_xticks(list(x))
ax.set_xticklabels([str(g) for g in gpus])
ax.set_xlim(-0.55, 2.6)
ax.set_ylim(0, 180)
ax.set_yticks([0, 30, 60, 90, 120, 150, 180])
ax.set_xlabel("GPUs")
ax.set_ylabel("stage time per step (ms)")
ax.grid(True, axis="y")
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles[::-1], labels[::-1], loc="upper right",
          handletextpad=0.4, borderaxespad=0.2, handlelength=1.2,
          labelspacing=0.35)
fig.tight_layout(pad=0.3)
save(fig, "fig_stagescale")
