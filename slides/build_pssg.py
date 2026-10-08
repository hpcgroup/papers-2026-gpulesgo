"""Build the GPU-LESGO talk on the PSSG PowerPoint template (python-pptx).

Run via build.sh, which renders the paper's figures to PNG first:
    ./build.sh [template.pptx] [out.pptx]
Direct use: FIG_DIR=<dir of rendered PNGs> python build_pssg.py [template] [out]
Needs: python-pptx, Pillow, lxml.
"""
import copy
import os
import sys

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "PSSG-powerpoint-template-v3.pptx")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "gpulesgo_pssg.pptx")
FIG = os.environ.get("FIG_DIR", os.path.join(HERE, "build", "figs"))

# The template canvas is 26.667 x 15 in, twice a 13.333 x 7.5 design grid.
# All coordinates and point sizes below are on the design grid and scaled by K.
K = 2.0


def E(v):
    return Emu(int(round(v * K * 914400)))


def P(pt):
    return Pt(pt * K)


# ---------- template palette ----------
NAVY = "3F5A7E"
ORANGE = "E87053"
ORANGE_TXT = "C4512F"
TEAL = "35798B"
INK = "2A2F30"
MUTED = "5F6B76"
TINT = "EEF2F6"
TINT2 = "E3EDF2"
WHITE = "FFFFFF"
ONDARK = "D5DFEA"
PURPLE = "7A4FA0"
GREEN = "2F8F5B"
BODY = "Gill Sans"
HEAD = "Arial"
MONO = "Courier New"

TTXT = {"gate": PURPLE, "relocate": NAVY, "slice": GREEN, "overlap": ORANGE_TXT}

TOP, MID = MSO_ANCHOR.TOP, MSO_ANCHOR.MIDDLE
LEFT, CENTER, RIGHT = PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.RIGHT


def rgb(h):
    return RGBColor.from_string(h)


# ---------- text ----------
def _norm(content):
    """str | list[para]; para = str | list[(text, opts)] | dict(runs=..., bullet=...)."""
    if isinstance(content, str):
        content = [content]
    paras = []
    for para in content:
        if isinstance(para, str):
            paras.append({"runs": [(para, {})]})
        elif isinstance(para, dict):
            paras.append(para)
        else:
            paras.append({"runs": list(para)})
    return paras


def set_bullet(p, color=TEAL, indent=0.24):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(E(indent))))
    pPr.set("indent", str(-int(E(indent))))
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", color)
    etree.SubElement(pPr, qn("a:buSzPct")).set("val", "100000")
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", "•")


def add_text(slide, content, x, y, w, h, size=15, color=INK, bold=False, italic=False,
             font=BODY, align=LEFT, anchor=TOP, space_after=0, bullet=False):
    tb = slide.shapes.add_textbox(E(x), E(y), E(w), E(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, para in enumerate(_norm(content)):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if space_after:
            p.space_after = P(space_after)
        for t, o in para["runs"]:
            r = p.add_run()
            r.text = t
            f = r.font
            f.size = P(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", italic)
            f.name = o.get("font", font)
            f.color.rgb = rgb(o.get("color", color))
            if o.get("sup"):
                r._r.get_or_add_rPr().set("baseline", "30000")
        if para.get("bullet", bullet):
            set_bullet(p)
    return tb


# ---------- shapes ----------
def box(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12):
    sp = slide.shapes.add_shape(shape, E(x), E(y), E(w), E(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = rgb(fill)
    sp.line.fill.background()
    sp.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sp.adjustments[0] = min(0.5, radius / min(w, h))
    return sp


def img_w(slide, name, x, y, w):
    path = os.path.join(FIG, name)
    iw, ih = Image.open(path).size
    h = w * ih / iw
    slide.shapes.add_picture(path, E(x), E(y), E(w), E(h))
    return h


def img_h(slide, name, x, y, h):
    path = os.path.join(FIG, name)
    iw, ih = Image.open(path).size
    w = h * iw / ih
    slide.shapes.add_picture(path, E(x), E(y), E(w), E(h))
    return w


def stat(slide, x, y, w, h, big, label, color=TEAL, fill=TINT, big_size=26, pad=0.18):
    box(slide, x, y, w, h, fill)
    add_text(slide, big, x + pad, y + 0.06, w - 2 * pad, h * 0.55, size=big_size, bold=True,
             color=color, font=HEAD, anchor=MID)
    add_text(slide, label, x + pad, y + 0.06 + h * 0.55, w - 2 * pad, h * 0.45 - 0.12,
             size=12.5, color=MUTED)


# ---------- template plumbing ----------
prs = Presentation(TEMPLATE)
layout = {l.name: l for l in prs.slide_layouts}
sld_ids = prs.slides._sldIdLst
title_slide, example_slide, closing_slide = list(prs.slides)

# Keep the example slide's slide-number placeholder to clone onto new slides.
SLDNUM = next(copy.deepcopy(sp._element) for sp in example_slide.shapes
              if sp.is_placeholder and sp.placeholder_format.idx == 2)
# The example's number box is 0.29 in wide, so "10" wraps; widen and center it.
_xfrm = SLDNUM.find(qn("p:spPr")).find(qn("a:xfrm"))
_xfrm.find(qn("a:off")).set("x", str(int(E(6.4165))))
_xfrm.find(qn("a:ext")).set("cx", str(int(E(0.5))))
for _ext in SLDNUM.find(qn("p:spPr")).findall(qn("a:extLst")):
    SLDNUM.find(qn("p:spPr")).remove(_ext)
_p = SLDNUM.find(qn("p:txBody")).find(qn("a:p"))
_p.insert(0, etree.Element(qn("a:pPr"), algn="ctr"))

# Footer name on the master: the presenter.
for sp in prs.slide_master.shapes:
    if sp.name == "Abhinav Bhatele" and sp.has_text_frame:
        runs = sp.text_frame.paragraphs[0].runs
        runs[0].text = "Cunyang Wei"
        for r in runs[1:]:
            r.text = ""

n_slide = [1]


def content_slide(title, takeaway=None):
    s = prs.slides.add_slide(layout["Title & Bullets"])
    for ph in list(s.placeholders):
        if ph.placeholder_format.idx == 1:
            ph._element.getparent().remove(ph._element)
    s.shapes._spTree.append(copy.deepcopy(SLDNUM))
    s.shapes.title.text = title
    for r in s.shapes.title.text_frame.paragraphs[0].runs:
        r.font.size = Pt(72)
    if takeaway:
        add_text(s, takeaway, 0.6, 1.66, 12.1, 0.42, size=17, italic=True, color=TEAL, anchor=MID)
    n_slide[0] += 1
    return s


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


# ===== 1. Title (template slide) =====
ttl = title_slide.shapes.title.text_frame
p = ttl.paragraphs[0]
for r in list(p.runs):
    p._p.remove(r._r)
r = p.add_run()
r.text = "Accelerating Production-Scale Large Eddy"
r.font.size = Pt(72)
p.add_line_break()
r = p.add_run()
r.text = "Simulations of Wind Farms on GPUs"
r.font.size = Pt(72)
sub = next(sp for sp in title_slide.placeholders if sp.placeholder_format.idx == 1).text_frame
p = sub.paragraphs[0]
for r in list(p.runs):
    p._p.remove(r._r)
p.add_run().text = "Cunyang Wei, Wenyuan Chen, Abhinav Bhatele, Charles Meneveau, Zheng Li"
p2 = sub.add_paragraph()
r = p2.add_run()
r.text = "University of Maryland  ·  Morgan State University  ·  Johns Hopkins University"
r.font.size = Pt(32)
r.font.color.rgb = rgb(MUTED)
notes(title_slide, "Title. This talk presents the first GPU port of LESGO, a pseudo-spectral large-eddy simulation code for wind farms.")

# ===== 2. Motivation =====
s = content_slide("Why Accelerate Wind-Farm LES?",
                  "Fidelity needs fine grids and long physical times. The CPU code can't provide both.")
rows = [
    ("Wakes cost 10–20% of farm power",
     "Studying them means tens of turbines in kilometers of turbulent atmosphere, over hours of physical time."),
    ("LES resolves the turbulence directly",
     "LESGO is a widely used open-source pseudo-spectral LES code: little numerical dissipation, high accuracy per grid point."),
    ("Production runs take hours to days",
     "Converged statistics need hundreds of thousands of steps, at 6.48 s per step on 4 CPU nodes."),
]
for i, (head, body) in enumerate(rows):
    y = 2.3 + i * 1.45
    add_text(s, head, 0.6, y, 5.7, 0.4, size=18, bold=True)
    add_text(s, body, 0.6, y + 0.44, 5.7, 0.9, size=14, color=MUTED)
h = img_w(s, "wf60_raw.png", 6.7, 2.2, 6.0)
add_text(s, "Production benchmark wf60: instantaneous streamwise velocity, 4×4 turbine section",
         6.7, 2.25 + h, 6.0, 0.3, size=11, italic=True, color=MUTED)
tw = (6.0 - 0.4) / 3
for i, (big, lab) in enumerate([("60", "wind turbines"), ("604M", "grid cells"), ("28 km", "domain length")]):
    stat(s, 6.7 + i * (tw + 0.2), 5.45, tw, 1.15, big, lab)
notes(s, "Wake losses reduce farm output by 10 to 20 percent. LES is the standard tool, and LESGO is a widely used pseudo-spectral code for this regime. The problem: a production run of our 60-turbine case needs hundreds of thousands of steps, and the CPU code tops out at 6.48 seconds per step.")

# ===== 3. The time loop (Algorithm 1 of the paper) =====
s = content_slide("One LESGO Time Step")
LH, ELH, GAP = 0.19, 0.227, 0.06   # algorithm row, explanation row, gap before a stage
AX, AW = 0.6, 5.25                 # algorithm box
EX, EW = 6.25, 6.45                # explanation column
KW = {"bold": True}
DER, SGSC, CONV, TURB, PRES = "0072B2", "009E73", "646464", "800080", "D55E00"


def expl(name, color, text):
    return [(name, {"bold": True, "color": color}), ("  " + text, {})]


def elided(text):
    return [(text, {"italic": True, "color": MUTED, "size": 11.5})]


# (algorithm lines [(indent, runs, opt tag)], explanation runs, explanation rows, gap before)
groups = [
    ([(0, [("for", KW), (" n = 1, N ", {}), ("do", KW)], None)], None, 0, False),
    ([(1, [("…", {})], None)], elided("adaptive time-step control (elided)"), 1, False),
    ([(1, [("Derivatives()", {"color": DER})], None)],
     expl("Derivatives", DER, "Velocity gradients: 2D FFTs in x–y, centered differences in z."), 1, True),
    ([(1, [("SGS()", {"color": SGSC})], None),
      (2, [("if", KW), (" n mod c = 0 ", {}), ("then", KW)], None),
      (3, [("UpdateLASDCoefficient()", {"color": SGSC})], "Opt. 2"),
      (2, [("SGSStress()", {"color": SGSC})], None),
      (2, [("StressDivergence()", {"color": SGSC})], None)],
     expl("SGS", SGSC, "Subgrid stress from the LASD model. Every 5th step (c = 5) it filters 21 fields at two widths and interpolates along particle paths, the most irregular routine in the solver."), 3, True),
    ([(1, [("Convection()", {"color": CONV})], "Opt. 3")],
     expl("Convection", CONV, "Nonlinear term with 3/2-rule dealiasing: FFT to a 1.5× padded grid and back. The most FFT-heavy stage."), 2, True),
    ([(1, [("Turbines()", {"color": TURB})], None),
      (2, [("SampleBladeVelocities()", {"color": TURB})], "Opt. 2"),
      (2, [("ComputeBladeForces()", {"color": TURB})], "Opt. 3"),
      (2, [("SpreadBladeForces()", {"color": TURB})], "Opt. 2")],
     expl("Turbines", TURB, "Actuator line: interpolate velocity at thousands of blade points, look up lift and drag in airfoil tables, then spread the forces back with a Gaussian kernel."), 3, True),
    ([(1, [("…", {})], None)], elided("explicit time integration (elided)"), 1, False),
    ([(1, [("Pressure()", {"color": PRES})], None),
      (2, [("PoissonFFT()", {"color": PRES})], None),
      (2, [("PoissonTridiag()", {"color": PRES})], "Opt. 1"),
      (2, [("PoissonInvFFT()", {"color": PRES})], None),
      (1, [("ProjectVelocity()", {})], None)],
     expl("Pressure", PRES, "2D FFTs split the Poisson equation into ~590K tridiagonal systems along z, one per wavenumber pair, and Thomas solves them. ProjectVelocity() then removes the divergence."), 3, True),
    ([(0, [("end for", KW)], None)], None, 0, False),
]
PAD, y0 = 0.17, 1.8
total = sum((GAP if gap else 0) + max(len(lines) * LH, nrows * ELH) for lines, ex, nrows, gap in groups)
box(s, AX, y0, AW, total + 2 * PAD, TINT)
y = y0 + PAD
for lines, ex, nrows, gap in groups:
    if gap:
        y += GAP
    if ex:
        add_text(s, [ex], EX, y, EW, nrows * ELH + 0.05, size=12)
    for i, (indent, runs, tag) in enumerate(lines):
        ly = y + i * LH
        add_text(s, [runs], AX + 0.25 + indent * 0.3, ly, AW - 1.2, LH, size=11.5, font=MONO, anchor=MID)
        if tag:
            add_text(s, tag, AX + AW - 1.0, ly, 0.8, LH, size=10.5, italic=True, color=TEAL, align=RIGHT, anchor=MID)
    y += max(len(lines) * LH, nrows * ELH)
notes(s, "This is the main time loop from the paper's Algorithm 1, with minor routines elided. Five components take most of the step time. Derivatives and convection are FFT-heavy; the LASD subgrid model and the actuator-line turbines are irregular; the pressure solve couples all processes along z. The tags on the left mark which optimization later targets each routine. Every one of these routines sweeps dozens of persistent 3D arrays, so data placement matters a lot on the GPU.")

# ===== 4. Slab decomposition & ceiling =====
s = content_slide("1D Slab Decomposition Hits a CPU Ceiling",
                  "More cores barely help: the node saturates memory bandwidth, then runs out of memory.")
sx, sw, sh, sg, sy = 1.35, 3.8, 0.46, 0.07, 2.3
for i, lab in enumerate(["Process 3", "Process 2", "Process 1", "Process 0"]):
    y = sy + i * (sh + sg)
    box(s, sx, y, sw, sh, ["C8D3E2", "AFC0D6", "95ACCA", "7C98BE"][i], shape=MSO_SHAPE.RECTANGLE)
    add_text(s, lab + "  ·  full x–y planes", sx + 0.15, y, sw - 0.3, sh, size=13, anchor=MID)
stack_h = 4 * sh + 3 * sg
ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(0.95), E(sy + stack_h), E(0.95), E(sy))
ln.line.color.rgb = rgb(INK)
ln.line.width = P(1.5)
etree.SubElement(ln.line._get_or_add_ln(), qn("a:tailEnd")).set("type", "triangle")
add_text(s, "z", 0.6, sy + stack_h / 2 - 0.2, 0.3, 0.4, size=16, italic=True, bold=True, anchor=MID)
add_text(s, [
    {"runs": [("2D horizontal FFTs stay local: ", {"bold": True}), ("no all-to-all transposes", {})], "bullet": True},
    {"runs": [("Halo exchange: ", {"bold": True}), ("single planes between neighbors", {})], "bullet": True},
    {"runs": [("Poisson solve is global: ", {"bold": True}), ("every tridiagonal system spans all processes in z", {})], "bullet": True},
], 0.6, 4.6, 5.4, 2.0, size=15, space_after=8)
fw = 5.7
fh = img_w(s, "fig_ceiling.png", 7.0, 2.15, fw)
ty, tw = 2.15 + fh + 0.12, (fw - 0.4) / 3
for i, (big, lab) in enumerate([("1.08×", "16 → 64 cores"), ("OOM", "at 128 processes"), ("2.1×", "4 nodes vs. 1")]):
    stat(s, 7.0 + i * (tw + 0.2), ty, tw, 0.95, big, lab, color=ORANGE_TXT, big_size=22, pad=0.15)
notes(s, "LESGO splits the domain into horizontal slabs along z. This keeps 2D FFTs local but makes the pressure solve a serial chain across processes. On Perlmutter CPU nodes, 16 to 64 cores gives only 1.08x, 128 processes run out of memory, and four nodes plateau at 6.48 seconds per step.")

# ===== 5. Porting the kernels =====
s = content_slide("Porting the Kernels with OpenACC",
                  "Offloading the computation is the straightforward part.")
add_text(s, "Example: a field update loop", 0.6, 2.2, 6.0, 0.35, size=15, bold=True, anchor=MID)
box(s, 0.6, 2.62, 6.0, 3.1, "1E2A36", radius=0.1)
DIR, SRC = "F5B26B", "E6EDF3"
add_text(s, [
    [("!$acc parallel loop collapse(3) default(present)", {"color": DIR})],
    [("do k = 1, nz", {"color": SRC})],
    [("  do j = 1, ny", {"color": SRC})],
    [("    do i = 1, nx", {"color": SRC})],
    [("      u(i,j,k) = u(i,j,k) + dt * rhs(i,j,k)", {"color": SRC})],
    [("    end do", {"color": SRC})],
    [("  end do", {"color": SRC})],
    [("end do", {"color": SRC})],
], 0.85, 2.62, 5.6, 3.1, size=14, font=MONO, anchor=MID)
add_text(s, [
    [("One directive per loop nest. ", {"bold": True}),
     ("LESGO's kernels are loops over x, y, and z with independent iterations, so each one is offloaded as is.", {})],
    [("collapse(3)", {"bold": True, "font": MONO}), (" ", {}),
     ("merges the three loop levels, so every grid cell gets its own GPU thread.", {})],
    [("default(present)", {"bold": True, "font": MONO}), (" ", {}),
     ("stops with an error if an array is not already on the device, so no data moves behind our back.", {})],
    [("FFTs ", {"bold": True}),
     ("call batched cuFFT on the same CUDA stream as the OpenACC kernels, so transforms and loops run in order without host synchronization.", {})],
    [("One source tree. ", {"bold": True}),
     ("Without -acc the directives are plain comments, so the CPU build stays our correctness reference.", {})],
], 7.0, 2.2, 5.7, 4.45, size=14.5, space_after=11)
notes(s, "Porting the computation is the easy part. Every LESGO kernel is a loop nest over x, y, and z with independent iterations, so one OpenACC parallel loop with collapse(3) offloads it. default(present) guarantees that no data is copied implicitly. FFTW calls become batched cuFFT on the same CUDA stream as the loops, so there is no host synchronization between them. The loop shown is a representative update loop, not a verbatim excerpt.")

# ===== 6. Data strategies =====
s = content_slide("Computation Is Easy, Data Placement Is Not",
                  "Every solver array holds O(N³) values, so each needless transfer moves a whole field.")
add_text(s, "Directive-based ports commonly pick one of three data strategies:", 0.6, 2.25, 12.1, 0.4, size=17)
for i, (num, head, body) in enumerate([
    ("1", "Array mirroring", "Keep a device copy of every host array, and copy data back wherever host code reads it."),
    ("2", "CUDA managed memory", "Let the driver migrate pages between host and device on demand."),
    ("3", "Fine-grained explicit residency", "Decide, array by array and access by access, where each field lives and which part of it crosses PCIe."),
]):
    y = 2.95 + i * 1.0
    add_text(s, num, 0.6, y - 0.04, 0.5, 0.5, size=30, bold=True, color=TEAL, font=HEAD)
    add_text(s, head, 1.2, y, 11.5, 0.42, size=19, bold=True)
    add_text(s, body, 1.2, y + 0.42, 11.5, 0.5, size=16, color=MUTED)
add_text(s, "Strategies 1 and 2 need few code changes, so we try them first.", 0.6, 6.05, 12.1, 0.45,
         size=17, bold=True, color=NAVY)
notes(s, "Where the data lives is the hard part. Every solver array is O(N^3), so any unnecessary host-device transfer moves a whole field. Directive-based ports usually pick one of three strategies: mirroring every array, letting CUDA managed memory migrate pages, or fine-grained explicit residency. The first two need few code changes, so we tried them first.")

# ===== 7. Strategy 1: array mirroring =====
s = content_slide("Strategy 1: Array Mirroring",
                  "Only 13 ms of a 220 ms step runs on the GPU: it sits idle 94% of the time.")
fw = 9.0
fh = img_w(s, "fig_mirroring.png", (13.333 - fw) / 2, 2.15, fw)
add_text(s, "Time-step breakdown on a 256³ grid with two turbines, 4 A100 GPUs (Nsight Systems)",
         0.6, 2.2 + fh, 12.1, 0.3, size=12, italic=True, color=MUTED, align=CENTER)
py = 2.2 + fh + 0.5
add_text(s, [[("Host routines still need full fields. ", {"bold": True}),
              ("Several routines run slower on the GPU and stay on the host, so full fields cross PCIe wherever they read solver state. The largest source is twelve full-field syncs, 420 MB per step, while the host reads about 5 MB.", {})]],
         0.6, py, 5.85, 6.65 - py, size=14.5)
add_text(s, [[("Memory is wasted. ", {"bold": True}),
              ("LESGO keeps dozens of O(N³) fields plus 3/2-padded spectral scratch. Mirroring arrays that no kernel reads takes device memory, so a given grid needs more GPUs.", {})]],
         6.85, py, 5.85, 6.65 - py, size=14.5)
notes(s, "Mirroring works well when every kernel moves to the GPU and data only comes back for diagnostics and checkpoints. LESGO does not fit this mold. Some routines run slower on the GPU and stay on the host, so full fields cross PCIe wherever they read solver state. On the 256-cubed reference case, only 13 of 220 ms per step is GPU execution; the rest is transfers and host synchronization. The biggest item is twelve full-field syncs, 420 MB per step, although the host only reads about 5 MB. Mirroring every array also wastes device memory.")

# ===== 8. Strategy 2: CUDA managed memory =====
s = content_slide("Strategy 2: CUDA Managed Memory",
                  "The least porting effort, but page faults stall execution.")
box(s, 0.6, 2.25, 5.9, 0.6, "1E2A36", radius=0.1)
add_text(s, [[("nvfortran -acc ", {"color": SRC}), ("-gpu=mem:managed", {"color": DIR}), (" ...", {"color": SRC})]],
         0.85, 2.25, 5.5, 0.6, size=15, font=MONO, anchor=MID)
add_text(s, [
    [("One compiler flag, no data directives to write. We run the production benchmark (604M cells) on 16 A100 GPUs.", {})],
    [("nsys", {"bold": True}),
     (" shows page faults and on-demand migration, inherent to demand-paged unified memory, stalling execution, most of all in the pressure solve.", {})],
    [("The traffic is also invisible in the source code, so there is nothing to tune.", {})],
], 0.6, 3.1, 5.9, 2.4, size=15, space_after=10)
img_w(s, "fig_managed.png", 6.85, 2.3, 5.85)
box(s, 0.6, 5.65, 12.1, 0.95, TINT2)
add_text(s, [[("Same root cause for strategies 1 and 2: ", {"bold": True, "color": ORANGE_TXT}),
              ("after the kernels move to the GPU, routines left on the host still demand full-field transfers. Fixing that needs fine-grained control over residency and transfer footprints, which is strategy 3.", {})]],
         0.85, 5.65, 11.6, 0.95, size=15, anchor=MID)
notes(s, "Managed memory is the least effort: one compiler flag. On the production benchmark with 16 A100s, nsys shows page faults and on-demand migration stalling execution. The figure shows the pressure solve alone taking 0.97 s per step, dominated by page faults, so the step is far slower than with explicit residency. The traffic is also invisible in the source. Both strategies fail for the same reason: after the kernels move to the GPU, the routines that stay on the host still demand full-field transfers. That leads to strategy 3.")

# ===== 9. Strategy 3: consumer-driven explicit residency =====
s = content_slide("Consumer-Driven Explicit Residency",
                  "Strategy 3: keep every field on the device, and size each host transfer by what the host touches.")
add_text(s, [
    [("Residency by construction. ", {"bold": True}),
     ("Device memory holds the primary copy of every field. All persistent arrays get the ", {}), ("declare\u00a0create", {"font": MONO}),
     (" directive at module scope, and every kernel asserts ", {}), ("default(present)", {"font": MONO}),
     (". Host code touches solver state only at coupling points.", {})],
    [("Classify each coupling point ", {"bold": True}),
     ("by the footprint the host routine actually accesses (scalar, column, plane, or subvolume), how often it runs, and whether it reads, writes, or both. LESGO has nine classes (next slide).", {})],
    [("Four treatments, tried in order:", {"bold": True})],
    {"runs": [("Gate", {"bold": True, "color": TTXT["gate"]}),
              (" skips the transfer on steps where its consumer does not run, such as the SGS fallback gradients and output steps.", {})], "bullet": True},
    {"runs": [("Relocate", {"bold": True, "color": TTXT["relocate"]}),
              (" ports the consumer to the GPU so the transfer disappears: time integration and projection, diagnostics, the actuator line, and the Thomas chains.", {})], "bullet": True},
    {"runs": [("Slice", {"bold": True, "color": TTXT["slice"]}),
              (" keeps serial or I/O routines on the host but moves only the section they touch, such as wall planes and the pressure DC column.", {})], "bullet": True},
    {"runs": [("Overlap", {"bold": True, "color": TTXT["overlap"]}),
              (" hides irreducible host work, such as the airfoil polar lookups, behind GPU execution.", {})], "bullet": True},
], 0.6, 2.25, 12.1, 4.4, size=15, space_after=10)
notes(s, "Our port keeps device memory as the primary copy of every field. We declare arrays device-resident at module scope and assert presence in every kernel, which exposes every coupling point. We then classify each coupling point and apply four treatments in order: gate, relocate, slice, and overlap. We move to the next only if the previous one does not apply.")

# ===== 7. Taxonomy table =====
s = content_slide("Nine Coupling-Point Classes, Four Treatments",
                  "The classes recur across pseudo-spectral multiphysics codes: a reusable porting checklist.")


def tw_(k, rest):
    return [(k, {"bold": True, "color": TTXT[k]}), (rest, {})]


rows = [
    ("Boundary plane", "Wall-stress model reads u, v, w at the walls", "Full fields, 420 MB", tw_("slice", " to wall planes, later ") + tw_("relocate", "")),
    ("Conditional", "Velocity gradients read only by CPU SGS fallback", "9 fields, 315 MB", tw_("gate", " on the SGS model choice")),
    ("Spectral mode", "Pressure zero-wavenumber recurrence (serial in z)", "3 full-field round trips", tw_("slice", " to the DC column (~1 KB)")),
    ("Stale entry", "copyin of pressure at solver entry", "34 MB", tw_("slice", " to a seeded ghost plane")),
    ("Pipeline state", "Time integration and projection read u, v, w, RHS", "210 MB", tw_("relocate", "; keep pipeline on device")),
    ("Actuator", "Blade sampling and force projection", "2 full-field crossings", tw_("relocate", "; exchange O(blade points)")),
    ("Diagnostics", "Energy, divergence, checkpoint writes", "963 MB", tw_("relocate", " reductions, ") + tw_("gate", " output")),
    ("Serial chain", "Thomas chains spanning processes", "Host-staged relays", tw_("relocate", "; pipelined GPU exchange")),
    ("Host physics", "Tabulated airfoil polar lookups", "Serialized 28 ms", tw_("overlap", " with the GPU backlog")),
]
colw = [1.85, 4.55, 2.35, 3.35]
rh = 0.44
gf = s.shapes.add_table(len(rows) + 1, 4, E(0.6), E(2.2), E(sum(colw)), E(rh * (len(rows) + 1)))
tbl = gf.table
tblPr = gf._element.graphic.graphicData.tbl.tblPr
tblPr.set("firstRow", "0")
tblPr.set("bandRow", "0")
tblPr.find(qn("a:tableStyleId")).text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
for j, wv in enumerate(colw):
    tbl.columns[j].width = E(wv)


def style_cell(cell, fill, bottom):
    tcPr = cell._tc.get_or_add_tcPr()
    for chd in list(tcPr):
        tcPr.remove(chd)
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = etree.SubElement(tcPr, qn(tag))
        if tag == "a:lnB" and bottom:
            ln.set("w", str(int(P(0.75))))
            etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr")).set("val", bottom)
        else:
            ln.set("w", "0")
            etree.SubElement(ln, qn("a:noFill"))
    etree.SubElement(etree.SubElement(tcPr, qn("a:solidFill")), qn("a:srgbClr")).set("val", fill)
    cell.margin_left = cell.margin_right = E(0.12)
    cell.margin_top = cell.margin_bottom = E(0.03)
    cell.vertical_anchor = MID


def fill_cell(cell, runs, size=13, color=INK, bold=False):
    p = cell.text_frame.paragraphs[0]
    p.alignment = LEFT  # the master's otherStyle centers text by default
    for t, o in runs:
        r = p.add_run()
        r.text = t
        r.font.size = P(size)
        r.font.name = BODY
        r.font.bold = o.get("bold", bold)
        r.font.color.rgb = rgb(o.get("color", color))


for j, hdr in enumerate(["Class", "Instance in LESGO", "Naive cost per step", "Treatment"]):
    c = tbl.cell(0, j)
    style_cell(c, NAVY, None)
    fill_cell(c, [(hdr, {})], color=WHITE, bold=True)
for i, row in enumerate(rows):
    tbl.rows[i + 1].height = E(rh)
    for j in range(4):
        c = tbl.cell(i + 1, j)
        style_cell(c, WHITE if i % 2 == 0 else TINT, "D5DEE6")
        if j == 0:
            fill_cell(c, [(row[0], {})], bold=True)
        elif j == 1:
            fill_cell(c, [(row[1], {})])
        elif j == 2:
            fill_cell(c, [(row[2], {})], color=MUTED)
        else:
            fill_cell(c, row[3])
tbl.rows[0].height = E(rh)
notes(s, "This table lists all nine classes we found in LESGO, what a naive port pays per step, and the treatment we apply. Most full-field transfers are either relocated to the GPU or sliced to a tiny footprint. After all treatments, steady-state PCIe traffic is 1.6 MB up and 2.0 MB down per step.")

# ===== 8. Slice example =====
s = content_slide("Example: Slicing the Pressure DC Mode",
                  "Leave the serial recurrence on the CPU, but ship only the column it touches.")
add_text(s, [
    {"runs": [("Horizontal FFTs split the Poisson equation into N²−1 independent tridiagonal systems, solved as one batched GPU call", {})], "bullet": True},
    {"runs": [("The zero-wavenumber (DC) mode is singular and needs a serial first-order recurrence in z", {})], "bullet": True},
    {"runs": [("O(N) serial work runs faster on one CPU core than on the GPU, so it stays on the host", {})], "bullet": True},
], 0.6, 2.2, 4.7, 3.0, size=15, space_after=10)
stat(s, 0.6, 5.3, 4.7, 1.3, "34 MB → 1 KB", "per transfer, three round trips per step", color=TEAL, big_size=28)


def code(y, label, label_color, lines):
    add_text(s, label, 5.6, y, 7.1, 0.35, size=15, bold=True, color=label_color, anchor=MID)
    box(s, 5.6, y + 0.4, 7.1, 1.3, "1E2A36", radius=0.1)
    paras = [[(a, {"color": "E6EDF3"}), (b, {"color": "8DB6D9"})] for a, b in lines]
    add_text(s, paras, 5.85, y + 0.52, 6.7, 1.06, size=13, font=MONO, anchor=MID)


code(2.2, "Naive: three full-field round trips per step", ORANGE_TXT, [
    ("!$acc update self(p)        ", "! 34 MB"),
    ("call dc_recurrence(p)       ", "! DC column only"),
    ("!$acc update device(p)      ", "! 34 MB"),
])
box(s, 9.0, 3.98, 0.4, 0.32, "9AA8B5", shape=MSO_SHAPE.DOWN_ARROW)
code(4.38, "Sliced: O(1) traffic", GREEN, [
    ("!$acc update self(rH_z(1:2,1,:)) ", "! 1 KB in"),
    ("call dc_recurrence_column(p_col)", ""),
    ("!$acc update device(p(1:2,1,:))  ", "! 1 KB out"),
])
notes(s, "Here is one slice in practice. The batched tridiagonal solve for all non-zero modes runs on the GPU. The DC mode needs a tiny serial recurrence that is faster on the CPU. Our first port wrapped it in full 3D transfers, three 34 MB round trips per step. Slicing moves only the 1 KB column in and out, with the exact same arithmetic.")

# ===== 9. Chunk pipelining =====
s = content_slide("Opt. 1: Chunk Pipelining the Thomas Solve",
                  "Independent systems let each process start the next chunk instead of waiting.")
img_h(s, "fig4_lesgo_pipeline.png", 0.6, 2.2, 4.45)
x, w = 7.0, 5.7
add_text(s, "Problem", x, 2.2, w, 0.38, size=18, bold=True, color=ORANGE_TXT)
add_text(s, "~590K systems of 512 unknowns span all 16 processes. Thomas sweeps are serial in z, so process k idles until k−1 finishes.",
         x, 2.6, w, 1.0, size=15)
add_text(s, "Idea", x, 3.7, w, 0.38, size=18, bold=True, color=TEAL)
add_text(s, "Split the systems into chunks. Pass chunk m's boundary coefficients downstream and move straight to m+1. The last process starts back substitution right away.",
         x, 4.1, w, 1.15, size=15)
stat(s, x, 5.4, 2.75, 1.2, "1.9×", "faster time step", big_size=30)
stat(s, x + 2.95, 5.4, 2.75, 1.2, "Exact", "Thomas loops untouched", big_size=30)
notes(s, "The pressure solve gives about 590 thousand independent tridiagonal systems, each distributed across all processes. The Thomas algorithm is serial along z, so processes wait on each other. Because the systems are independent, we split them into chunks and pipeline them, and the last process turns around each chunk immediately. The inner loops are unchanged, so results match the sequential solve. This gives a 1.9x step speedup.")

# ===== 10. Batching =====
s = content_slide("Opt. 2: Batching Many Small Work Items",
                  "Per-turbine and per-plane work units are too small to fill a GPU, so we fuse them.")
for x, head, before, after in [
    (0.6, "Actuator-line turbines",
     "Per-turbine uploads, launches and syncs; over 1,000 MPI_Allreduce calls per process per step.",
     "Blade tables stay on the device. One sampling kernel and one projection kernel cover all points; one packed MPI_Allreduce."),
    (6.8, "LASD subgrid model",
     "Thousands of single-plane 2D FFTs per update: 21 fields × 2 filter widths × every z level.",
     "2D scratch planes promoted to 3D. One batched cuFFT call filters all z levels of a field: a few dozen launches."),
]:
    box(s, x, 2.2, 5.9, 3.25, TINT)
    add_text(s, head, x + 0.3, 2.35, 5.3, 0.55, size=19, bold=True, anchor=MID)
    add_text(s, "BEFORE", x + 0.3, 3.03, 1.5, 0.25, size=11, bold=True, color=ORANGE_TXT)
    add_text(s, before, x + 0.3, 3.3, 5.3, 0.8, size=15, color=MUTED)
    add_text(s, "AFTER", x + 0.3, 4.15, 1.5, 0.25, size=11, bold=True, color=GREEN)
    add_text(s, after, x + 0.3, 4.42, 5.3, 0.95, size=15)
tw = (12.1 - 0.4) / 3
for i, (big, lab) in enumerate([("1.6×", "step speedup from batching turbines"),
                                ("~10×", "fewer kernel launches and collectives"),
                                ("15–18%", "faster other stages (no in-loop allocations)")]):
    stat(s, 0.6 + i * (tw + 0.2), 5.65, tw, 0.95, big, lab, fill=TINT2, big_size=24)
notes(s, "Several components break into many small independent units. For the turbines, we batch the whole farm: one sampling kernel, one projection kernel, and a single packed reduction instead of over a thousand. Removing in-loop device allocations also sped up other stages by 15 to 18 percent. For the LASD model, promoting 2D scratch planes to 3D lets one batched cuFFT call filter every vertical level at once.")

# ===== 11. Heterogeneous overlap =====
s = content_slide("Opt. 3: Heterogeneous CPU–GPU Execution",
                  "Some physics runs better on the CPU. Hide it behind the GPU backlog.")
fh = img_w(s, "fig_overlap.png", 0.6, 2.2, 5.8)
stat(s, 0.6, 5.65, 2.8, 1.0, "30 ms", "saved per step", big_size=26)
stat(s, 3.6, 5.65, 2.8, 1.0, "93%", "GPU busy fraction", big_size=26)
x, w = 6.95, 5.75
for y, head, body, c, bh in [
    (2.2, "Why keep blade forces on the CPU?", "Only 10,800 actuator points, too few to fill a GPU, and data-dependent airfoil lookups diverge warps.", ORANGE_TXT, 0.8),
    (3.4, "The catch", "Host work costs ~28 ms per step. Run synchronously, the GPU sits idle.", ORANGE_TXT, 0.8),
    (4.6, "Two-phase split", "Sample on the GPU and copy a small packet out without flushing the queue. The CPU computes forces during convection, then forces go back for projection.", TEAL, 1.15),
]:
    add_text(s, head, x, y, w, 0.36, size=17, bold=True, color=c)
    add_text(s, body, x, y + 0.4, w, bh, size=14.5)
notes(s, "Blade-force evaluation actually ran slower on the GPU: only 10,800 points, and the airfoil lookups branch per point. So it stays on the CPU. Its inputs are fixed at the start of the step and its outputs are not needed until force projection. We split the turbine model into two phases around convection, so the CPU works while the GPU drains its backlog. This saves 30 ms per step and raises GPU utilization to 93 percent.")

# ===== 12. Setup & correctness =====
s = content_slide("Setup and Correctness", "GPU and CPU backends agree to floating-point roundoff.")
items = [
    ("Platform", "NERSC Perlmutter: 4× A100 per node, Slingshot-11"),
    ("Software", "NVHPC 25.5 OpenACC, CUDA 12.9, cuFFT, Cray MPICH"),
    ("CPU baseline", "2× 64-core AMD EPYC 7763 per node, fastest configuration"),
    ("wf60 case", "60 turbines, 604M cells; scaling series up to 1.36B cells"),
]
cw = (12.1 - 3 * 0.2) / 4
for i, (head, body) in enumerate(items):
    x = 0.6 + i * (cw + 0.2)
    box(s, x, 2.2, cw, 1.22, TINT)
    add_text(s, head, x + 0.18, 2.33, cw - 0.36, 0.4, size=15, bold=True, color=TEAL, anchor=MID)
    add_text(s, body, x + 0.18, 2.8, cw - 0.36, 0.58, size=12.5)
fw, fy = 7.95, 3.62
fh = img_w(s, "fig_cpu_gpu_lesgo_fields.png", 0.6, fy, fw)
add_text(s, "Single NREL 5-MW turbine, 480×384×240 grid, 1,000 steps from the same cold start. CPU: 48 MPI processes. GPU: 2 A100s.",
         0.6, fy + fh + 0.08, fw, 0.5, size=12, italic=True, color=MUTED)
tx, tw, th = 8.85, 3.85, 0.92
for i, (big, lab) in enumerate([
    ([("1.5×10", {}), ("−13", {"sup": True})], "relative L2 difference"),
    ([("9.0×10", {}), ("−14", {"sup": True})], "max normalized difference"),
    ("1.0", "wake-pattern correlation"),
]):
    stat(s, tx, fy + i * (th + 0.08), tw, th, [big] if isinstance(big, list) else big, lab, big_size=22)
notes(s, "All runs use Perlmutter A100 nodes; CPU baselines use its Milan CPU nodes, and we always compare against the fastest CPU configuration. Before measuring speed, we checked correctness with matched single-turbine runs: after 1,000 steps the GPU-minus-CPU difference is at roundoff, around 1e-13.")

# ===== 13. Cumulative speedup =====
s = content_slide("Each Optimization Stacks: 40× on 16 GPUs",
                  "604M cells, 60 turbines. 4 CPU nodes (512 processes) vs. 4 GPU nodes (16 A100s).")
cd = CategoryChartData()
cd.categories = ["CPU, fastest config", "Explicit residency", "+ Actuator line on GPU", "+ Chunk pipelining", "+ Batching", "+ CPU–GPU overlap"]
cd.add_series("Speedup vs. CPU", (1.0, 4.9, 11.3, 21.4, 33.8, 40.0))
chart = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, E(0.45), E(2.15), E(7.8), E(4.5), cd).chart
chart.has_legend = False
chart.font.name = BODY
chart.font.size = P(14)
chart.font.color.rgb = rgb(INK)
chart.has_title = True
chart.chart_title.text_frame.text = "Speedup over the fastest CPU run"
tr0 = chart.chart_title.text_frame.paragraphs[0].runs[0].font
tr0.size, tr0.bold, tr0.color.rgb, tr0.name = P(14), False, rgb(MUTED), BODY
plot = chart.plots[0]
plot.gap_width = 55
plot.vary_by_categories = False
ser = plot.series[0]
for i, c in enumerate(["9AA8B5", NAVY, NAVY, NAVY, NAVY, ORANGE]):
    pt = ser.points[i]
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = rgb(c)
plot.has_data_labels = True
dl = plot.data_labels
dl.number_format = '0.0"×"'
dl.number_format_is_linked = False
dl.position = XL_LABEL_POSITION.OUTSIDE_END
dl.font.size, dl.font.bold, dl.font.color.rgb, dl.font.name = P(15), True, rgb(INK), BODY
ca = chart.category_axis
ca.reverse_order = True
ca.major_tick_mark = XL_TICK_MARK.NONE
ca.format.line.fill.background()
ca.tick_labels.font.size = P(14)
ca.tick_labels.font.color.rgb = rgb(INK)
va = chart.value_axis
va.minimum_scale, va.maximum_scale = 0, 46
va.has_major_gridlines = False
va.visible = False
x, w = 8.65, 4.05
box(s, x, 2.2, w, 1.25, NAVY)
add_text(s, "6.48 s → 0.162 s", x + 0.25, 2.27, w - 0.5, 0.65, size=27, bold=True, color=WHITE, font=HEAD, anchor=MID)
add_text(s, "per time step (0.27 ms per million cells)", x + 0.25, 2.93, w - 0.5, 0.4, size=12, color=ONDARK)
tw = (w - 0.2) / 2
for i, (big, lab) in enumerate([("93%", "GPU busy"), ("73%", "of peak DRAM BW"), ("1.6 MB", "host→device / step"), ("2.0 MB", "device→host / step")]):
    stat(s, x + (i % 2) * (tw + 0.2), 3.62 + (i // 2) * 1.15, tw, 1.0, big, lab, big_size=24, pad=0.16)
add_text(s, "LASD every 5th step: 8.18 s → 0.206 s (39.7×)", x, 5.98, w, 0.6, size=12, italic=True, color=MUTED)
notes(s, "Each technique fixes a different bottleneck, and the gains multiply. Explicit residency alone gives 4.9x. Moving the actuator line to the GPU adds 2.3x, pipelining 1.9x, batching 1.6x, and overlap the final 1.2x, for 40x overall. The final profile shows the GPU busy 93 percent of the time and only a few MB of PCIe traffic per step: no O(N^3) transfers remain.")


# ===== 14 / 15. Scaling =====
def two_figs(title, take, left, right, tiles, note):
    s = content_slide(title, take)
    fw = 5.5
    fh = img_w(s, left, 0.6, 2.15, fw)
    img_w(s, right, 12.7 - fw, 2.15, fw)
    tw = (12.1 - 0.4) / 3
    for i, (big, lab, c) in enumerate(tiles):
        stat(s, 0.6 + i * (tw + 0.2), 2.15 + fh + 0.15, tw, 1.0, big, lab, color=c, big_size=24)
    notes(s, note)


two_figs("Strong Scaling to 128 GPUs",
         "90× over the best CPU run on 64 GPUs; 1.36B cells at 0.084 s per step on 128 GPUs.",
         "fig_scaling.png", "fig_stagescale.png",
         [("87–90%", "parallel efficiency when GPU count doubles", TEAL),
          ("16.2B", "cell updates per second on 128 GPUs", TEAL),
          ("33–36 ms", "flat Other stage: collectives + launches", ORANGE_TXT)],
         "Strong scaling at three grid sizes. On the production grid, 64 GPUs reach 0.072 s per step, 90x the best CPU run. Efficiency stays around 87 to 90 percent per doubling. The stage breakdown shows compute stages shrinking, pressure scaling superlinearly as the pipeline deepens, and a roughly constant 'Other' floor from latency-bound collectives and kernel launches.")
two_figs("Weak Scaling and Kernel Efficiency",
         "Kernels run near the memory-bandwidth roof, and efficiency holds when each GPU stays busy.",
         "fig_scaling_weak.png", "fig_roofline.png",
         [("90%", "weak-scaling efficiency, 4 → 64 GPUs", TEAL),
          ("67–88%", "of peak DRAM bandwidth, custom kernels", TEAL),
          ("48–82%", "of peak DRAM bandwidth, batched cuFFT", TEAL)],
         "At the production load of 29.5 million cells per GPU, weak scaling keeps 90 percent efficiency out to 64 GPUs. The roofline shows the main kernels sitting on the bandwidth roof: custom field kernels reach 67 to 88 percent of peak DRAM bandwidth. The remaining gap is inside cuFFT library kernels. The 1D slab layout is enough for this physics, since grid size is set by turbulence scales, not domain size.")

# ===== 16. Takeaways =====
s = content_slide("Takeaways")
pts = [
    ("First GPU port of LESGO", "~70K lines of Fortran, full physics pipeline, one OpenACC source tree."),
    ("Data movement governs performance", "Nine coupling-point classes, resolved by gate, relocate, slice, and overlap."),
    ("Three structural optimizations", "Chunk pipelining, batching, and CPU–GPU overlap: 93% GPU utilization."),
    ("Production-scale speed", "Strong scaling to 128 GPUs on a 1.36B-cell grid."),
]
for i, (head, body) in enumerate(pts):
    y = 1.95 + i * 1.18
    box(s, 0.6, y, 0.5, 0.5, NAVY, shape=MSO_SHAPE.OVAL)
    add_text(s, str(i + 1), 0.6, y, 0.5, 0.5, size=17, bold=True, color=WHITE, font=HEAD, align=CENTER, anchor=MID)
    add_text(s, head, 1.35, y - 0.02, 6.85, 0.42, size=19, bold=True)
    add_text(s, body, 1.35, y + 0.42, 6.85, 0.6, size=15, color=MUTED)
box(s, 8.45, 1.95, 4.25, 4.6, NAVY)
add_text(s, "40–90×", 8.75, 2.3, 3.75, 1.3, size=64, bold=True, color=WHITE, font=HEAD, anchor=MID)
add_text(s, "speedup over the fastest CPU run on the production wind farm (604M cells)", 8.75, 3.75, 3.75, 0.9, size=15, color=WHITE)
add_text(s, "Production campaigns: months → days.", 8.75, 4.95, 3.75, 0.8, size=15, italic=True, color=ONDARK)
notes(s, "To wrap up: this is the first GPU port of LESGO. The key lesson is that for this class of solver, data movement, not kernel speed, sets performance, and a small set of treatments covers every coupling point. With three further optimizations, we get 40 to 90x over the best CPU runs, which turns months-long production campaigns into days. The code will be open-sourced.")

# ===== Closing (template slide) =====
add_text(closing_slide, "Thank you!", 0.4, 1.3, 7.2, 1.1, size=54, bold=True, color=WHITE, font=HEAD, align=CENTER, anchor=MID)
add_text(closing_slide, "Questions?", 0.4, 2.45, 7.2, 0.7, size=30, color=WHITE, align=CENTER, anchor=MID)
add_text(closing_slide, "Accelerating Production-Scale Large Eddy Simulations of Wind Farms on GPUs",
         0.9, 3.45, 6.2, 0.9, size=16, italic=True, color=ONDARK, align=CENTER)

# Drop the template's example content slide (done last so new slide part
# names never collide with the template's), then move the closing slide last.
for sid in list(sld_ids):
    part = prs.part.related_part(sid.rId)
    if part is example_slide.part:
        prs.part.drop_rel(sid.rId)
        sld_ids.remove(sid)
    elif part is closing_slide.part:
        sld_ids.remove(sid)
        sld_ids.append(sid)

prs.save(OUT)
print("wrote", OUT, len(prs.slides), "slides")
