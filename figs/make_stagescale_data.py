#!/usr/bin/env python3
"""make_stagescale_data.py -- per-stage device kernel time per step from nsys
traces, for fig_stagescale (runtime breakdown by stage vs GPU count).

usage: make_stagescale_data.py <label>=<run_dir> [...]   e.g.
       make_stagescale_data.py 16=runs/nsys_57484319 32=runs/nsys32_... 64=...

For every rank report nsys_rank<r>.nsys-rep in a run dir (sqlite exported on
demand with `nsys export`), the kernel stream is cut into steps at the
get_cfl_dt sentinel pair (two launches at the top of every step), steady-state
steps are kept (first STEADY_FROM steps dropped, the last step dropped because
its diagnostics at wbase land in it), every kernel is attributed to its
Algorithm 1 stage with the rules of make_roofline_data.attribute(), and the
per-step kernel time of each stage is averaged over steps. Across ranks the
script reports the mean (device-time view: average GPU busy time) and the
max. The step wall time is the sentinel-to-sentinel period, averaged the same
way (rank 0). Output: stagescale_kernel.csv with one row per (gpus, rank
aggregate, stage).
"""
import csv
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_roofline_data import attribute, STAGES  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
STEADY_FROM = 3      # steps 1-2 are startup (step 2 carries the field upload)


def sqlite_for(rep):
    db = os.path.splitext(rep)[0] + ".sqlite"
    if not os.path.exists(db):
        subprocess.run(["nsys", "export", "--type", "sqlite", "--force-overwrite",
                        "true", "-o", db, rep], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return db


def kernels(db):
    con = sqlite3.connect(db)
    q = ("SELECT k.start, k.end, s.value FROM CUPTI_ACTIVITY_KIND_KERNEL k "
         "JOIN StringIds s ON k.demangledName = s.id ORDER BY k.start")
    return con.execute(q).fetchall()


def steps_of(rows):
    """Split into steps at the first launch of each sentinel pair."""
    starts = []
    prev = -10
    for i, r in enumerate(rows):
        if r[2].startswith("cfl_util_get_cfl_dt"):
            if i != prev + 1:
                starts.append(i)
            prev = i
    return [(a, b) for a, b in zip(starts, starts[1:])]


def per_rank(db):
    rows = kernels(db)
    stp = steps_of(rows)
    use = stp[STEADY_FROM - 1:-1]          # drop startup and the last step
    acc = defaultdict(float)
    wall = 0.0
    for a, b in use:
        seg = [{"Kernel Name": r[2]} for r in rows[a:b]]
        st = attribute(seg)
        for r, s in zip(rows[a:b], st):
            acc[s] += (r[1] - r[0]) * 1e-9
        wall += (rows[b][0] - rows[a][0]) * 1e-9
    n = len(use)
    return {k: v / n for k, v in acc.items()}, wall / n, n


def main():
    specs = [a.split("=", 1) for a in sys.argv[1:]]
    if not specs:
        sys.exit(__doc__)
    recs = []
    for label, run in specs:
        reps = sorted((f for f in os.listdir(run)
                       if re.fullmatch(r"nsys_rank\d+\.nsys-rep", f)),
                      key=lambda f: int(re.search(r"\d+", f).group()))
        per = {}
        for f in reps:
            r = int(re.search(r"\d+", f).group())
            per[r], wall, n = per_rank(sqlite_for(os.path.join(run, f)))
            if r == 0:
                wall0, n0 = wall, n
        ranks = sorted(per)
        print(f"{label} GPUs: {len(ranks)} ranks, {n0} steady steps, "
              f"rank-0 step {wall0*1e3:.1f} ms")
        for agg in ("mean", "max", "rank0"):
            for s in STAGES:
                vals = [per[r].get(s, 0.0) for r in ranks]
                v = {"mean": sum(vals) / len(vals), "max": max(vals),
                     "rank0": per[0].get(s, 0.0)}[agg]
                recs.append(dict(gpus=label, agg=agg, stage=s, ms=v * 1e3))
            tot = sum(r["ms"] for r in recs if r["gpus"] == label and r["agg"] == agg)
            recs.append(dict(gpus=label, agg=agg, stage="Step", ms=wall0 * 1e3))
            print(f"  {agg:5s} kernel {tot:6.1f} ms  " + "  ".join(
                f"{s[:5]} {next(r['ms'] for r in recs if r['gpus']==label and r['agg']==agg and r['stage']==s):5.1f}"
                for s in STAGES))
        # per-rank spread of total kernel time and of Turbines
        tots = [sum(per[r].values()) * 1e3 for r in ranks]
        turb = [per[r].get("Turbines", 0.0) * 1e3 for r in ranks]
        print(f"  per-rank kernel total: min {min(tots):.1f} max {max(tots):.1f} ms; "
              f"Turbines nonzero on {sum(1 for t in turb if t > 0.01)}/{len(ranks)} ranks")
    out = os.path.join(OUT, "stagescale_kernel.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["gpus", "agg", "stage", "ms"])
        w.writeheader()
        w.writerows(recs)
    print("wrote", out)


if __name__ == "__main__":
    main()
