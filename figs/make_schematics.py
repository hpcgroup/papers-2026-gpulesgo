#!/usr/bin/env python3
"""Schematic figures for Sec. IV (optimization) of the LESGO GPU paper.

  fig_tridag.pdf   -- chunk-pipelined distributed Thomas solve (rank-time)
  fig_overlap.pdf  -- CPU/GPU heterogeneous overlap (two-lane timeline)

Style: shared PSSG environment (pssg_style.py). Blue #0072B2 = GPU
work, vermillion #D55E00 = CPU work, grays = idle/reference, matching
the measured-data figures.
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import pssg_style as ps
from pssg_style import VERM, BLUE, SKY, GRAY, ORANGE

ps.apply()

LGRAY = "#d8d8d8"   # idle-box edges (lighter than the shared LGRAY)

OUT = os.path.dirname(os.path.abspath(__file__))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=200)
    plt.close(fig)
    print("wrote", name)


def bar(ax, x0, x1, y, color, label=None, ec="none", h=0.62, fs=6.5,
        tcolor="white", hatch=None):
    ax.add_patch(Rectangle((x0, y - h / 2), x1 - x0, h, facecolor=color,
                           edgecolor=ec if ec != "none" else color,
                           linewidth=0.5, hatch=hatch, zorder=2))
    if label:
        ax.text((x0 + x1) / 2, y, label, ha="center", va="center",
                fontsize=fs, color=tcolor, zorder=3)


# ----------------------------------------------------------------------------
# Fig: chunk-pipelined distributed tridiagonal solve
# ----------------------------------------------------------------------------
P = 4          # ranks drawn (of 16)
C = 4          # chunks drawn (of 8)
fig, (a, b) = plt.subplots(2, 1, figsize=(3.45, 2.8), sharex=True,
                           gridspec_kw={"height_ratios": [1.0, 1.45]})

# (a) baseline: serialized forward sweep, rank k waits for k-1
for i in range(P):
    y = P - 1 - i
    bar(a, i, i + 1, y, BLUE, "forward" if i == 0 else None)
    if i > 0:
        bar(a, 0, i, y, "white", "blocked in MPI_Recv" if i == P - 1
            else None, ec=LGRAY, tcolor=GRAY, hatch="//")
a.annotate("", xy=(1.0, 2.0), xytext=(1.0, 3.0 - 0.31),
           arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.7))
a.text(P + 0.15, (P - 1) / 2, "serial:\n$P\\,T$", fontsize=7,
       va="center", color="#333333")
a.set_title("(a) baseline: each rank waits for the full sweep above it",
            fontsize=7.5, loc="left")

# (b) pipelined: chunk m on rank k starts when rank k-1 finishes chunk m.
# Two lanes per rank: forward sweep (blue/sky, upper) and back substitution
# (orange, lower). The last rank owns the closing boundary row, so it
# back-substitutes each chunk right after that chunk's forward pass and the
# return wave climbs the chain while later chunks still sweep forward.
tau = 1.0 / C
LANE, FDY, BDY = 0.30, 0.16, -0.16
LORANGE = "#f3c76d"
for i in range(P):
    y = P - 1 - i
    for m in range(C):
        t0 = (i + m) * tau
        bar(b, t0, t0 + tau, y + FDY, BLUE if m % 2 == 0 else SKY,
            None, ec="white", h=LANE)
        tb = (P + m + (P - 1 - i)) * tau
        bar(b, tb, tb + tau, y + BDY, ORANGE if m % 2 == 0 else LORANGE,
            None, ec="white", h=LANE)
# chunk labels above rank 0's forward lane
for m in range(C):
    b.text((m + 0.5) * tau, P - 1 + 0.44, f"c{m+1}", fontsize=5.5,
           ha="center", color="#333333")
# boundary-send arrows for chunk 1, forward (down) and backward (up)
for i in range(P - 1):
    t = (i + 1) * tau
    b.annotate("", xy=(t + 0.02, P - 2 - i + 0.31), xytext=(t - 0.02, P - 1 - i - 0.31),
               arrowprops=dict(arrowstyle="->", color=VERM, lw=0.8))
for i in range(P - 1, 0, -1):
    t = (P + (P - i)) * tau
    yl = P - 1 - i
    b.annotate("", xy=(t + 0.02, yl + 1 - 0.31), xytext=(t - 0.02, yl + 0.31),
               arrowprops=dict(arrowstyle="->", color=ORANGE, lw=0.8))
b.text(0.02, -0.05, "GPU-aware\nboundary send", fontsize=6, color=VERM,
       va="center")
b.annotate("last rank fuses back-sub,\nno turnaround wait",
           xy=(P * tau + tau / 2, BDY - 0.13), xytext=(1.9, -0.72),
           fontsize=6, color="#333333", va="center",
           arrowprops=dict(arrowstyle="->", color=ORANGE, lw=0.8))
b.text((2 * P - 2) * tau + 1.32, P - 1 + BDY, "back-sub wave", fontsize=6.5,
       color="#b07800", va="center")
b.text(P + 0.15, (P - 1) / 2, "pipelined:\n$(P{+}c{-}1)\\,T/c$",
       fontsize=7, va="center", color="#333333")
b.set_title("(b) chunked pipeline with fused back substitution (orange)",
            fontsize=7.5, loc="left")

for ax in (a, b):
    ax.set_xlim(-0.05, P + 1.45)
    ax.set_yticks([P - 1 - i for i in range(P)])
    ax.set_yticklabels([f"rank {i}" for i in range(P)], fontsize=6.5)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
a.set_ylim(-0.55, P - 0.35)
b.set_ylim(-1.0, P - 0.30)
b.set_xlabel(r"time $\rightarrow$", fontsize=7.5)
fig.tight_layout(pad=0.4, h_pad=1.0)
save(fig, "fig_tridag")

# ----------------------------------------------------------------------------
# Fig: CPU/GPU heterogeneous overlap (two-lane timeline)
# ----------------------------------------------------------------------------
fig, (a, b) = plt.subplots(2, 1, figsize=(3.45, 2.05), sharex=True)

# time units: sample 6, blade 28, convec 60, project 14
S, BL, CV, PR = 6, 28, 60, 14

# (a) serial: sample -> convection -> device idles while CPU blade -> project
t = 0
bar(a, t, t + S, 1, BLUE)
a.text(t + S / 2, 1.42, "sample", fontsize=6, ha="center", color="#333333")
t += S
bar(a, t, t + CV, 1, BLUE, "convection", fs=6)
t += CV
bar(a, t, t + BL, 1, "white", "idle", ec=LGRAY, tcolor=GRAY, hatch="//")
bar(a, t, t + BL, 0, VERM, "blade physics", fs=6)
t += BL
bar(a, t, t + PR, 1, SKY, "project", fs=6, tcolor="#333333")
end_a = t + PR
a.set_title("(a) serial: host physics stalls the device", fontsize=7.5,
            loc="left")

# (b) overlapped: two-phase ATM; blade physics under the convec backlog
t = 0
bar(b, t, t + S, 1, BLUE)
b.text(t + S / 2, 1.42, "sample", fontsize=6, ha="center", color="#333333")
t += S
bar(b, t, t + CV, 1, BLUE, "convection backlog", fs=6)
bar(b, t, t + BL, 0, VERM, "blade physics", fs=6)
merge_x = t + CV
bar(b, merge_x, merge_x + PR, 1, SKY, "project", fs=6, tcolor="#333333")
b.annotate("", xy=(merge_x + 1, 1 - 0.31), xytext=(t + BL - 1, 0 + 0.31),
           arrowprops=dict(arrowstyle="->", color=VERM, lw=0.8))
b.text(t + BL + 2, -0.5, "forces, $O$(blade pts)", fontsize=6, color=VERM)
end_b = merge_x + PR
# saved-time marker
b.annotate("", xy=(end_b, 1.42), xytext=(end_a, 1.42),
           arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.8))
b.text((end_a + end_b) / 2, 1.62, r"$-29$ ms/step", fontsize=7,
       ha="center", color="#333333")
b.set_title("(b) two-phase: host physics hidden by the backlog",
            fontsize=7.5, loc="left")

for ax in (a, b):
    ax.set_xlim(-2, end_a + 4)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["CPU", "GPU"], fontsize=7)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
a.set_ylim(-0.55, 1.75)
b.set_ylim(-0.85, 1.95)
b.set_xlabel(r"time $\rightarrow$", fontsize=7.5)
fig.tight_layout(pad=0.4, h_pad=0.8)
save(fig, "fig_overlap")

# ----------------------------------------------------------------------------
# Fig: where a step goes under the two baseline data strategies (Sec. IV)
# ----------------------------------------------------------------------------
from pssg_style import ORANGE

fig, (a, b) = plt.subplots(2, 1, figsize=(3.45, 2.35),
                           gridspec_kw={"height_ratios": [1.0, 1.35]})

# (a) mirroring, reference case [R]: 220 ms step, GPU compute only 13 ms
GPUC, H2D, D2H, HOST = 13, 26, 65, 116
segs = [(GPUC, BLUE, "GPU\n13", "seg"), (H2D, ORANGE, "H2D\n26", "seg"),
        (D2H, VERM, "D2H 65", "in"), (HOST, "white", "host code + sync 116", "gray")]
t = 0.0
for w, c, lab, mode in segs:
    if mode == "gray":
        bar(a, t, t + w, 0, "white", lab, ec=LGRAY, tcolor=GRAY, hatch="//", fs=6.5)
    else:
        bar(a, t, t + w, 0, c, lab if mode == "in" else None, ec="white", fs=6.5)
    if mode == "seg":  # small segment, label above with connector
        a.annotate(lab, xy=(t + w / 2, 0.33), xytext=(t + w / 2, 0.78),
                   fontsize=6, ha="center", va="bottom", color="#333333",
                   arrowprops=dict(arrowstyle="-", color=ps.LGRAY, lw=0.6))
    t += w
a.annotate("GPU busy 6% (13 ms)", xy=(GPUC / 2, -0.33),
           xytext=(2, -0.95), fontsize=6.5, color=BLUE, va="center",
           arrowprops=dict(arrowstyle="->", color=BLUE, lw=0.7,
                           connectionstyle="arc3,rad=-0.2"))
a.text(222, -0.95, "largest source: 12 full-field syncs\n420 MB/step, consumer reads ~5 MB",
       fontsize=6, color=GRAY, ha="right", va="center")
a.set_xlim(0, 224)
a.set_ylim(-1.35, 1.45)
a.set_yticks([])
a.tick_params(bottom=False, labelbottom=False)
for s in ("top", "right", "left", "bottom"):
    a.spines[s].set_visible(False)
a.set_title("(a) mirroring, reference case (256$^3$, 4 GPUs): 220 ms step",
            fontsize=7.5, loc="left")

# (b) managed vs explicit residency, production case [P]
PRESS, REST, RESID = 0.76, 0.48, 0.157
YM, YR = 1.15, -0.05
bar(b, 0, PRESS, YM, VERM, "pressure solve in page faults  0.76", fs=6.5)
bar(b, PRESS, PRESS + REST, YM, "white", "other stages 0.48", ec=LGRAY,
    tcolor=GRAY, hatch="//", fs=6.5)
bar(b, 0, RESID, YR, BLUE, None, ec="white")
b.text(RESID + 0.03, YR, "0.157 s,  zero $O(N^3)$ PCIe crossings\n(~260 KB packet + halo planes)",
       fontsize=6.5, color="#333333", va="center")
b.annotate("", xy=(RESID + 0.01, 0.55), xytext=(PRESS + REST, 0.55),
           arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.8))
b.text((RESID + PRESS + REST) / 2, 0.68, r"7.9$\times$", fontsize=8,
       color="#333333", ha="center", va="center")
b.set_xlim(0, 1.30)
b.set_ylim(-0.75, 1.95)
b.set_yticks([YM, YR])
b.set_yticklabels(["managed\nmemory", "explicit\nresidency"], fontsize=6.5)
b.tick_params(left=False, bottom=False, labelbottom=False)
for s in ("top", "right", "left", "bottom"):
    b.spines[s].set_visible(False)
b.set_title("(b) managed vs explicit residency, production case (472M, 16 GPUs)",
            fontsize=7.5, loc="left")

fig.tight_layout(pad=0.4, h_pad=1.2)
save(fig, "fig_datamove")
