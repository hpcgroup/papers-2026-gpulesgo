#!/usr/bin/env bash
# Rebuild the GPU-LESGO talk on the PSSG template.
# Usage: ./build.sh [template.pptx] [out.pptx]
# Needs: pdftoppm (poppler) and python3 with python-pptx, Pillow, lxml
# (set PYTHON=/path/to/python to use a venv).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FIGSRC="$HERE/../figs"
FIG_DIR="$(mktemp -d)"
trap 'rm -rf "$FIG_DIR"' EXIT

# Render the paper's PDF figures to PNG (dpi chosen per figure size).
for f in fig_ceiling fig_scaling fig_scaling_weak fig_stagescale fig_roofline; do
  pdftoppm -png -r 400 -singlefile "$FIGSRC/$f.pdf" "$FIG_DIR/$f"
done
for f in fig4_lesgo_pipeline fig_overlap fig_mirroring fig_cpu_gpu_lesgo_fields; do
  pdftoppm -png -r 250 -singlefile "$FIGSRC/$f.pdf" "$FIG_DIR/$f" 2>/dev/null
done
pdftoppm -png -r 400 -singlefile "$FIGSRC/fig_wf60_velocity_fixed.pdf" "$FIG_DIR/wf60_raw" 2>/dev/null
pdftoppm -png -r 600 -singlefile "$FIGSRC/fig_managed.pdf" "$FIG_DIR/fig_managed"

FIG_DIR="$FIG_DIR" "${PYTHON:-python3}" "$HERE/build_pssg.py" "$@"
