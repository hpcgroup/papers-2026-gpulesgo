#!/usr/bin/env python3
"""make_roofline_data.py -- fold a full-step Nsight Compute capture of rank 0
into the Algorithm 1 stages and write roofline_stages.csv for make_roofline.py.

Input: raw.csv from
    ncu --import wf60_step_rank0.ncu-rep --csv --page raw
(case tree runs/ncu_step_gpu16_<jobid>/, produced by pm_ncu_fullstep.sbatch;
no kernel-name filter, so every launch of one step is present).

Step cut: every step starts with the two get_cfl_dt sentinel launches; the
window is cut from the first sentinel pair to the next one (365 launches on
the production case, verified against the nsys trace runs/nsys_57484319).

Stage attribution (Algorithm 1 / fig_stagescale timers in main.f90):
  hand-written kernels by source module; cuFFT kernels (template names) take
  the stage of the most recent stage-owning kernel. Actuator-line (ATM) and
  turbine-forcing kernels run on a second stream interleaved with convection,
  so they count as Turbines but never change the FFT context. Derivative-
  module kernels (ddx/ddy/ddz) called from divstress_* inside the SGS timer
  count as SGS. main.f90 loops: RHS bookkeeping / time advance / ghost fills
  = Other; RHS -= dp (inside clock_press) = Pressure; RHS += turbine force
  (inside clock_forcing) = Turbines.

FLOPs = dadd + dmul + 2 dfma (+ the FP32 terms when captured; thread-level
SASS instruction counts); bytes = dram__bytes.sum; AI = FLOPs / bytes;
rate = FLOPs / gpu__time_duration; DRAM % of peak = bytes / time / 2.039 TB/s.
"""
import csv
import os
import re
import sys
from collections import OrderedDict, defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
BW_PEAK = 2.039e12    # A100-80GB HBM2e, byte/s
STAGES = ["Derivatives", "SGS", "Convection", "Turbines", "Pressure",
          "Projection", "Other"]

M = {
    "t": "gpu__time_duration.sum",
    "b": "dram__bytes.sum",
    "br": "dram__bytes_read.sum",
    "bw": "dram__bytes_write.sum",
    "dadd": "smsp__sass_thread_inst_executed_op_dadd_pred_on.sum",
    "dmul": "smsp__sass_thread_inst_executed_op_dmul_pred_on.sum",
    "dfma": "smsp__sass_thread_inst_executed_op_dfma_pred_on.sum",
}
# optional columns (present only if the capture asked for them)
OPT = {
    "pct": "dram__throughput.avg.pct_of_peak_sustained_elapsed",
    "fadd": "smsp__sass_thread_inst_executed_op_fadd_pred_on.sum",
    "fmul": "smsp__sass_thread_inst_executed_op_fmul_pred_on.sum",
    "ffma": "smsp__sass_thread_inst_executed_op_ffma_pred_on.sum",
}
# ncu CSV units (decimal prefixes: 2.679668 Gbyte == 2,679,667,712 byte on the
# details page of the same report)
UNIT = {"": 1.0, "ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0,
        "nsecond": 1e-9, "usecond": 1e-6, "msecond": 1e-3, "second": 1.0,
        "byte": 1.0, "Kbyte": 1e3, "Mbyte": 1e6, "Gbyte": 1e9,
        "inst": 1.0, "%": 1.0}


def num(s):
    s = s.replace(",", "").strip()
    return float(s) if s not in ("", "n/a") else 0.0


def val(r, k, scale):
    """metric k of row r in base units; 0 if the capture lacks it."""
    return num(r[M[k]]) * scale[k] if k in M else 0.0


def flops(r, scale):
    return (val(r, "dadd", scale) + val(r, "dmul", scale) + 2 * val(r, "dfma", scale)
            + val(r, "fadd", scale) + val(r, "fmul", scale) + 2 * val(r, "ffma", scale))


def load(path):
    with open(path, newline="") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        units = next(rd)
        rows = []
        for r in rd:
            if len(r) != len(hdr):
                continue
            rows.append(dict(zip(hdr, r)))
    scale = {}
    for k, col in M.items():
        if col not in hdr:
            sys.exit(f"missing metric column {col}")
        u = units[hdr.index(col)]
        if u not in UNIT:
            sys.exit(f"unknown unit {u!r} for {col}")
        scale[k] = UNIT[u]
    for k, col in OPT.items():
        if col in hdr:
            M[k] = col
            scale[k] = UNIT[units[hdr.index(col)]]
    rows.sort(key=lambda r: int(r["ID"]))
    return rows, scale


def is_fft(name):
    return name.startswith("void ")


def family(name):
    if is_fft(name):
        return "cuFFT"
    if name.startswith("atm_"):
        return "ATM"
    return "hand-written"


def cut_step(rows):
    sent = [i for i, r in enumerate(rows)
            if r["Kernel Name"].startswith("cfl_util_get_cfl_dt")]
    if len(sent) < 3:
        sys.exit(f"need two sentinel pairs, found {len(sent)} sentinels")
    s0 = sent[0]
    nxt = [i for i in sent if i > s0 + 1]
    if not nxt:
        sys.exit("no second sentinel pair in the capture")
    s1 = nxt[0]
    return rows[s0:s1]


def attribute(rows):
    """Return list of stage names, one per row."""
    out = []
    ctx = "Other"      # FFT context
    in_sgs = False
    for r in rows:
        n = r["Kernel Name"]
        if is_fft(n):
            out.append(ctx)
            continue
        if n.startswith("cfl_util_") or n.startswith("wallstress_") \
                or n.startswith("test_filter"):
            st = "Other"
        elif n.startswith("derivatives_gpu_m_"):
            st = "SGS" if in_sgs else "Derivatives"
        elif n.startswith("sgs_gpu_m_"):
            st = "SGS"
            in_sgs = True
        elif n.startswith("convec_gpu_m_"):
            st = "Convection"
            in_sgs = False
        elif n.startswith("press_gpu_m_") or n.startswith("tridag_") \
                or n.startswith("main_908"):
            st = "Pressure"
        elif n.startswith("atm_") or n.startswith("forcing_forcing_applied") \
                or n.startswith("main_659"):
            out.append("Turbines")      # second stream: keep ctx
            continue
        elif n.startswith("forcing_project"):
            st = "Projection"
        elif n.startswith("main_"):
            st = "Other"
        else:
            print(f"WARN: unclassified kernel {n[:60]} -> Other", file=sys.stderr)
            st = "Other"
        out.append(st)
        ctx = st
    return out


def aggregate(rows, stages, scale):
    acc = OrderedDict()
    def add(key, r):
        a = acc.setdefault(key, defaultdict(float))
        a["n"] += 1
        t = val(r, "t", scale)
        a["t"] += t
        a["b"] += val(r, "b", scale)
        a["br"] += val(r, "br", scale)
        a["bw"] += val(r, "bw", scale)
        a["pct_t"] += val(r, "pct", scale) * t
        a["f"] += flops(r, scale)
        a["f32"] += val(r, "fadd", scale) + val(r, "fmul", scale) + 2 * val(r, "ffma", scale)
    for r, st in zip(rows, stages):
        add((st, "all"), r)
        add((st, family(r["Kernel Name"])), r)
        add(("step", "all"), r)
        add(("step", family(r["Kernel Name"])), r)
    T = acc[("step", "all")]["t"]
    recs = []
    for (st, fam), a in acc.items():
        recs.append(OrderedDict(
            stage=st, family=fam, n_kernels=int(a["n"]),
            time_ms=a["t"] * 1e3, time_share_pct=100 * a["t"] / T,
            flops=a["f"], fp32_flops=a["f32"], bytes=a["b"],
            bytes_read=a["br"], bytes_write=a["bw"],
            ai=a["f"] / a["b"] if a["b"] else 0.0,
            tflops=a["f"] / a["t"] / 1e12 if a["t"] else 0.0,
            dram_pct=100 * a["b"] / a["t"] / BW_PEAK if a["t"] else 0.0,
            dram_pct_kernel_mean=a["pct_t"] / a["t"] if a["t"] else 0.0))
    return recs


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: make_roofline_data.py raw.csv [out.csv]")
    rows, scale = load(sys.argv[1])
    step = cut_step(rows)
    print(f"capture: {len(rows)} launches; step window: {len(step)} launches")
    stages = attribute(step)
    recs = aggregate(step, stages, scale)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "roofline_stages.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
        w.writeheader()
        w.writerows(recs)
    print(f"{'stage':12s} {'family':12s} {'n':>4s} {'ms':>7s} {'share%':>7s} "
          f"{'AI':>7s} {'TF/s':>6s} {'DRAM%':>6s} {'DRAM%k':>6s}")
    for r in recs:
        print(f"{r['stage']:12s} {r['family']:12s} {r['n_kernels']:4d} "
              f"{r['time_ms']:7.2f} {r['time_share_pct']:7.2f} {r['ai']:7.3f} "
              f"{r['tflops']:6.2f} {r['dram_pct']:6.1f} {r['dram_pct_kernel_mean']:6.1f}")
    print("wrote", out)
    # per-kernel listing for inspection
    lst = os.path.splitext(out)[0] + "_kernels.csv"
    with open(lst, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "stage", "family", "time_us", "ai", "tflops", "dram_pct", "kernel"])
        for i, (r, st) in enumerate(zip(step, stages)):
            t = val(r, "t", scale)
            b = val(r, "b", scale)
            fl = flops(r, scale)
            w.writerow([i, st, family(r["Kernel Name"]), f"{t*1e6:.1f}",
                        f"{fl/b:.4f}" if b else "", f"{fl/t/1e12:.3f}" if t else "",
                        f"{100*b/t/BW_PEAK:.1f}" if t else "", r["Kernel Name"][:90]])
    print("wrote", lst)


if __name__ == "__main__":
    main()
