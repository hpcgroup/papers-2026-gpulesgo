#!/usr/bin/env python3
"""Generate the measured-data figures for the LESGO GPU paper.

Outputs (vector PDF for LaTeX + PNG previews):
  fig_ceiling.pdf    -- Fig. 1: CPU strong scaling of the production case
  fig_breakdown.pdf  -- Fig. 4: component times before/after + GPU busy
  fig_scaling.pdf    -- Fig. 5: GPU strong (left) + weak (right) scaling

Data sources: cpu_scaling_summary.tsv / weak_scaling_summary.tsv (2026-07-03
sweeps) and measured campaign checkpoints from the optimization records.

Style: shared PSSG environment (pssg_style.py). Palette order VERM,
BLUE, GREEN...; CPU/before = vermillion, GPU/after = blue throughout.
"""
import os

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import pssg_style as ps
from pssg_style import VERM, BLUE, GREEN, GRAY, LGRAY

ps.apply()

OUT = os.path.dirname(os.path.abspath(__file__))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=200)
    plt.close(fig)
    print("wrote", name)


# ----------------------------------------------------------------------------
# Fig. 1 -- CPU strong scaling ceiling (production case)
# ----------------------------------------------------------------------------
# 2026-08 rerun on dedicated CPU nodes (2x EPYC 7763, 128 cores/node),
# 50 full steps, TRUE AVG; runs cpu24p*_563223xx in the case tree.
cores = [10, 20, 40, 100, 200, 400]
tstep = [17.424, 12.197, 9.676, 11.419, 7.294, 5.108]
nodes = [1, 1, 1, 1, 2, 4]
GPU_T = 0.157

fig, ax = plt.subplots(figsize=(3.45, 2.5))
ax.set_xscale("log")
ax.set_yscale("log")

# ideal scaling from the 10-core point
xs = [10, 400]
ax.plot(xs, [tstep[0] * 10 / x for x in xs], ls=ps.dashes(2), lw=0.8,
        color=LGRAY, zorder=1)
ax.annotate("ideal", xy=(120, tstep[0] * 10 / 120), color=GRAY, fontsize=7,
            rotation=-28, ha="center", va="bottom")

# CPU curve: one series, marker shape encodes node count
ax.plot(cores, tstep, lw=1.1, color=VERM, zorder=2)
marks = {1: ps.MARKERS[0], 2: ps.MARKERS[1], 4: ps.MARKERS[2]}
for n in (1, 2, 4):
    cx = [c for c, m in zip(cores, nodes) if m == n]
    cy = [t for t, m in zip(tstep, nodes) if m == n]
    ax.plot(cx, cy, marks[n], ms=4.5, color=VERM, mew=0, ls="none",
            zorder=3, label=f"CPU, {n} node" + ("s" if n > 1 else ""))

# GPU reference line
ax.axhline(GPU_T, color=BLUE, lw=1.2, zorder=2)
ax.annotate("16$\\times$A100 (4 nodes): 0.157 s", xy=(9.3, GPU_T * 1.22),
            color=BLUE, fontsize=7.5, va="bottom", ha="left")

# annotations: knee and best
# ax.annotate("knee: 8.51 s @ 40", xy=(40, 8.51), xytext=(52, 14.5),
#             fontsize=7, color="#333333",
#             arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.6))
ax.annotate("best: 5.11 s @ 400", xy=(400, 5.108), xytext=(110, 2.9),
            fontsize=7, color="#333333",
            arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.6))
ax.annotate("32$\\times$", xy=(478, 0.95), fontsize=8, color="#333333",
            ha="left")
ax.annotate("", xy=(460, 0.185), xytext=(460, 4.4),
            arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.7))

ax.set_xticks([10, 20, 40, 100, 200, 400])
ax.set_xticklabels(["10", "20", "40", "100", "200", "400"])
ax.set_yticks([0.2, 0.5, 1, 2, 5, 10, 20])
ax.set_yticklabels(["0.2", "0.5", "1", "2", "5", "10", "20"])
ax.set_xlim(9, 620)
ax.set_ylim(0.11, 20)
ax.set_xlabel("CPU cores")
ax.set_ylabel("time per step (s)")
ax.grid(True, which="major", axis="y")
ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.20),
          handletextpad=0.4, borderaxespad=0.2)
fig.tight_layout(pad=0.3)
save(fig, "fig_ceiling")

# ----------------------------------------------------------------------------
# Fig. 4 -- component before/after + GPU busy
# ----------------------------------------------------------------------------
comp = [
    ("Pressure solve",   152.0, 24.5),
    ("Diagnostics",      126.0, 5.0),
    ("Tip-loss corr.",    67.6, 5.0),
    ("Wall stress",       33.0, 0.1),
]

fig = plt.figure(figsize=(3.45, 2.1))
gs = fig.add_gridspec(1, 2, width_ratios=[2.6, 1.0], wspace=0.45)
ax = fig.add_subplot(gs[0])
axb = fig.add_subplot(gs[1])

ys = list(range(len(comp)))[::-1]
for y, (name, before, after) in zip(ys, comp):
    ax.plot([after, before], [y, y], lw=1.0, color=LGRAY, zorder=1)
    ax.plot(before, y, "o", ms=5, color=VERM, mew=0, zorder=2)
    ax.plot(after, y, "o", ms=5, color=BLUE, mew=0, zorder=3)
    ax.annotate(f"{before:g}", xy=(before, y), xytext=(0, 5),
                textcoords="offset points", ha="center", fontsize=6.5,
                color=VERM)
    ax.annotate(f"{after:g}", xy=(after, y), xytext=(0, 5),
                textcoords="offset points", ha="center", fontsize=6.5,
                color=BLUE)
ax.set_xscale("log")
ax.set_yticks(ys)
ax.set_yticklabels([c[0] for c in comp])
ax.set_xlim(0.05, 400)
ax.set_ylim(-0.5, len(comp) - 0.05)
ax.set_xticks([0.1, 1, 10, 100])
ax.set_xticklabels(["0.1", "1", "10", "100"])
ax.set_xlabel("ms per step (log)")
ax.grid(True, axis="x")
legend = [Line2D([], [], marker="o", ls="none", ms=5, color=VERM,
                 mew=0, label="before"),
          Line2D([], [], marker="o", ls="none", ms=5, color=BLUE,
                 mew=0, label="after")]
ax.legend(handles=legend, loc="upper left", ncol=2,
          handletextpad=0.3, borderaxespad=0.1, columnspacing=0.9)

# GPU busy panel
for x, v, c, h in ((0, 23, VERM, ps.HATCHES[0]), (1, 93, BLUE, ps.HATCHES[1])):
    axb.bar([x], [v], width=0.62, color=c, hatch=h, edgecolor="black",
            linewidth=0, zorder=3)
    axb.annotate(f"{v}%", xy=(x, v), xytext=(0, 2),
                 textcoords="offset points", ha="center", fontsize=7.5)
axb.set_xticks([0, 1])
axb.set_xticklabels(["before", "after"], fontsize=7.5)
axb.set_ylim(0, 105)
axb.set_yticks([0, 50, 100])
axb.set_ylabel("GPU busy (%)")
fig.subplots_adjust(left=0.26, right=0.985, bottom=0.24, top=0.96)
save(fig, "fig_breakdown")

# ----------------------------------------------------------------------------
# Fig. 5 -- GPU strong (left) + weak (right) scaling
# ----------------------------------------------------------------------------
# strong scaling at three problem sizes (clean production steps; the
# 472M series is the original 40-GB-node campaign, the 906M and 1.36B
# series run on the 80-GB node pool, chunk retuned at 64/128 GPUs)
strong = [
    ("472M",  [16, 32, 64],      [0.152, 0.080, 0.071],           VERM),
    ("906M",  [16, 32, 64, 128], [0.2377, 0.1313, 0.0831, 0.0783], BLUE),
    ("1.36B", [32, 64, 128],     [0.1875, 0.1081, 0.0839],         GREEN),
]
# weak scaling at three per-GPU loads (2026-08 campaign, case-tree
# paper-baseline binary with the pipelined tridiagonal solve, clean-step
# means, 40-GB pool homogeneous; chunk=16 at the 64-GPU points).
# ms/step: 29.5M: 149.4/156.7/158.5/162.9/165.7; 10.5M: 53.2/52.7/57.6/
# 60.0/63.6; 4.2M: 40.3/-/43.0/-/52.3.
weak = [
    ("29.5M/GPU (production load)", [4, 8, 16, 32, 64],
     [149.4, 156.7, 158.5, 162.9, 165.7], VERM),
    ("10.5M/GPU", [4, 8, 16, 32, 64],
     [53.2, 52.7, 57.6, 60.0, 63.6], BLUE),
    ("4.2M/GPU", [4, 16, 64],
     [40.3, 43.0, 52.3], GREEN),
]

# strong scaling, full single column
fig, a1 = plt.subplots(figsize=(3.45, 2.2))
a1.set_xscale("log", base=2)
for i, (name, gs, ts, col) in enumerate(strong):
    a1.plot(gs, ts, marker=ps.MARKERS[i], ls=ps.dashes(i), lw=1.1, ms=4.5,
            color=col, mew=0, zorder=3, label=name)
a1.set_xticks([16, 32, 64, 128])
a1.set_xticklabels(["16", "32", "64", "128"])
a1.set_ylim(0.05, 0.25)
a1.set_yticks([0.05, 0.10, 0.15, 0.20, 0.25])
a1.set_yticklabels(["0.05", "0.10", "0.15", "0.20", "0.25"])
a1.minorticks_off()
a1.set_xlabel("GPUs")
a1.set_ylabel("s per step")
a1.legend(loc="upper right")
a1.grid(True, axis="y")
fig.tight_layout(pad=0.3)
save(fig, "fig_scaling")

# weak scaling, full single column
fig, a2 = plt.subplots(figsize=(3.45, 2.0))
a2.set_xscale("log", base=2)
for i, (name, gs, ts, col) in enumerate(weak):
    a2.plot(gs, ts, marker=ps.MARKERS[i], ls=ps.dashes(i), lw=1.1, ms=4.5,
            color=col, mew=0, label=name)
a2.set_xticks([4, 8, 16, 32, 64])
a2.set_xticklabels(["4", "8", "16", "32", "64"])
a2.minorticks_off()
a2.set_ylim(0, 200)
a2.set_yticks([0, 50, 100, 150, 200])
a2.set_xlabel("GPUs")
a2.set_ylabel("ms per step")
a2.legend(loc="center left")
a2.grid(True, axis="y")
fig.tight_layout(pad=0.3)
save(fig, "fig_scaling_weak")