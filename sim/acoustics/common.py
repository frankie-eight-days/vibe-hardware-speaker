"""Shared paths, constants and figure helpers for the acoustics simulations (A1-A5)."""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RESULTS = os.path.join(HERE, "results")
FIGS = os.path.join(ROOT, "docs", "figures", "acoustics")
STYLE = os.path.join(ROOT, "sim", "paper.mplstyle")
DRIVERS_JSON = os.path.join(ROOT, "research", "drivers.json")
CAD_SCRIPT = os.path.join(ROOT, "mech", "concept", "speaker_concept.py")
CAD_REPORT = os.path.join(ROOT, "mech", "concept", "build", "report.json")
FREECADCMD = "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
CCX = "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(FIGS, exist_ok=True)

RHO, C0, P_REF = 1.20, 343.0, 20e-6     # air at ~20 C


def load_parts():
    with open(DRIVERS_JSON) as fh:
        return {p["id"]: p for p in json.load(fh)["parts"]}


def cad_params():
    """Parse the P = dict(...) parameter block of the FreeCAD concept script without running FreeCAD."""
    import ast
    src = open(CAD_SCRIPT).read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "P":
            return {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
    raise RuntimeError("P dict not found in speaker_concept.py")


def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.style.use(STYLE)
    return plt


def savefig(fig, name):
    """Save a figure as vector PDF + 300 dpi PNG under docs/figures/acoustics/."""
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGS, f"{name}.{ext}"))
    print("figure:", name)


def save_json(obj, name):
    path = os.path.join(RESULTS, name)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o))
    print("results:", path)
    return path


def save_csv(path_name, header, cols):
    path = os.path.join(RESULTS, path_name)
    arr = np.column_stack(cols)
    np.savetxt(path, arr, delimiter=",", header=",".join(header), comments="", fmt="%.6g")
    print("results:", path)
    return path


def spl(p_rms):
    return 20 * np.log10(np.abs(p_rms) / P_REF + 1e-30)


def freq_axis(ax, lo, hi):
    """Log frequency axis with plain labels (100, 200, 500, 1k, 2k, ...)."""
    from matplotlib.ticker import FixedLocator, FixedFormatter, NullFormatter
    ticks = [t for t in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000) if lo <= t <= hi]
    ax.set_xscale("log")
    ax.set_xlim(lo, hi)
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FixedFormatter([f"{t // 1000}k" if t >= 1000 else str(t) for t in ticks]))
    ax.xaxis.set_minor_formatter(NullFormatter())
