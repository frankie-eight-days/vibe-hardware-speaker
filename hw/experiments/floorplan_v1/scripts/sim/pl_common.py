"""Shared helpers for the post-layout analyses: stack-up, board loading, rasterisation, plotting.

Geometry comes from extract_kicad.py (KiCad pcbnew API on a scratch copy of the board).
Coordinates are KiCad mm (+y down). Grids index as [row j (y), column i (x)].
"""
import json
import os
import subprocess
import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
RESULTS = os.path.join(HERE, "results")
FIGDIR = os.path.join(HERE, "figs")
KICAD_PY = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
FASTHENRY = "/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/sim/postlayout/tools/fh2src/bin/fasthenry"

LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
# JLC04161H-7628 (LAYOUT_RULES §1). Thickness in mm, z = copper centre above the bottom face.
T_CU = {"F.Cu": 0.035, "In1.Cu": 0.0152, "In2.Cu": 0.0152, "B.Cu": 0.035}
H_PP, H_CORE = 0.2104, 1.065
ER_PP, ER_CORE = 4.4, 4.6
Z = {"B.Cu": 0.0175,
     "In2.Cu": 0.035 + H_PP + 0.0076,
     "In1.Cu": 0.035 + H_PP + 0.0152 + H_CORE + 0.0076,
     "F.Cu": 0.035 + H_PP + 0.0152 + H_CORE + 0.0152 + H_PP + 0.0175}
# dielectric between neighbouring copper layers: (upper, lower) -> (h, er)
DIEL = {("F.Cu", "In1.Cu"): (H_PP, ER_PP), ("In1.Cu", "In2.Cu"): (H_CORE, ER_CORE),
        ("In2.Cu", "B.Cu"): (H_PP, ER_PP)}
# The module constants above are the 4-layer (rev A) stack-up. Per-board values come from
# stackup(n), keyed by the board's copper layer count: top to bottom, (layer, t_Cu, role) and
# the dielectric (h, er) below each layer. Roles: sig = signal, gnd / pwr = plane.
_H7 = 0.2104 * 2 + 0.70             # 6L: 7628 + 0.70 core + 7628 as one dielectric
STACKS = {
    4: ("JLC04161H-7628",
        [("F.Cu", 0.035, "sig"), ("In1.Cu", 0.0152, "gnd"), ("In2.Cu", 0.0152, "pwr"), ("B.Cu", 0.035, "sig")],
        [(H_PP, ER_PP), (H_CORE, ER_CORE), (H_PP, ER_PP)]),
    6: ("JLC06161H-1080B",
        [("F.Cu", 0.035, "sig"), ("In1.Cu", 0.0152, "gnd"), ("In2.Cu", 0.0152, "sig"),
         ("In3.Cu", 0.0152, "pwr"), ("In4.Cu", 0.0152, "gnd"), ("B.Cu", 0.035, "sig")],
        [(0.0764, 3.91), (0.10, 4.36), (_H7, _H7 / (2 * 0.2104 / 4.4 + 0.70 / 4.53)), (0.10, 4.36), (0.0764, 3.91)]),
}


def stackup(n):
    """Stack-up of an n-layer board: layers (top first), t_cu, z (copper centre above the bottom
    face), diel {(upper, lower): (h, er)}, refs {layer: [(neighbour, h), ...] nearest first},
    t_fr4 (dielectric share per layer for in-plane heat flow), pairs (mirrored layers), names."""
    name, lay, die = STACKS[n]
    layers = [L for L, _, _ in lay]
    t_cu = {L: t for L, t, _ in lay}
    z, acc = {}, 0.0
    for k in range(n - 1, -1, -1):          # bottom up, summed in the same order as Z above
        L = layers[k]
        z[L] = acc + t_cu[L] / 2
        acc = acc + t_cu[L]
        if k > 0:
            acc = acc + die[k - 1][0]
    diel = {(layers[k], layers[k + 1]): die[k] for k in range(n - 1)}
    refs = {}
    for k, L in enumerate(layers):
        nb = [(layers[k - 1], die[k - 1][0])] if k > 0 else []
        nb += [(layers[k + 1], die[k][0])] if k < n - 1 else []
        refs[L] = sorted(nb, key=lambda q: q[1])
    t_fr4 = {L: (die[k - 1][0] / 2 if k > 0 else 0) + (die[k][0] / 2 if k < n - 1 else 0)
             for k, L in enumerate(layers)}
    if n == 4:
        t_fr4 = {"F.Cu": 0.105, "In1.Cu": 0.64, "In2.Cu": 0.64, "B.Cu": 0.105}   # rev A values (rounded)
    return {"n": n, "name": name, "layers": layers, "t_cu": t_cu, "z": z, "diel": diel, "refs": refs,
            "role": {L: r for L, _, r in lay}, "t_fr4": t_fr4,
            "pairs": [(layers[k], layers[n - 1 - k]) for k in range(n // 2)],
            "names": {L: f"L{k + 1}" for k, L in enumerate(layers)}}
SIGMA_CU = 5.8e7          # S/m
RHO_CU = 1 / SIGMA_CU     # ohm m
VIA_PLATING = 0.020       # mm barrel plating (JLC typ 18-25 um)
EPS0 = 8.854e-12


def mm2(x):
    return x * 1e-6


@dataclass
class Grid:
    x0: float
    y0: float
    nx: int
    ny: int
    p: float

    @classmethod
    def from_bbox(cls, bbox, p, margin=0.0):
        x0, y0 = bbox[0] - margin, bbox[1] - margin
        nx = int(np.ceil((bbox[2] - bbox[0] + 2 * margin) / p))
        ny = int(np.ceil((bbox[3] - bbox[1] + 2 * margin) / p))
        return cls(x0, y0, nx, ny, p)

    def xc(self):
        return self.x0 + (np.arange(self.nx) + 0.5) * self.p

    def yc(self):
        return self.y0 + (np.arange(self.ny) + 0.5) * self.p

    def ij(self, x, y):
        return (int(np.clip(np.floor((x - self.x0) / self.p), 0, self.nx - 1)),
                int(np.clip(np.floor((y - self.y0) / self.p), 0, self.ny - 1)))

    def extent(self):
        return [self.x0, self.x0 + self.nx * self.p, self.y0 + self.ny * self.p, self.y0]

    def box_mask(self, bb, grow=0.0):
        xc, yc = self.xc(), self.yc()
        mx = (xc >= bb[0] - grow) & (xc <= bb[2] + grow)
        my = (yc >= bb[1] - grow) & (yc <= bb[3] + grow)
        return my[:, None] & mx[None, :]


class Board:
    def __init__(self, path_json):
        with open(path_json) as f:
            d = json.load(f)
        self.d = d
        self.name = os.path.splitext(os.path.basename(path_json))[0]
        self.bbox = d["bbox"]
        self.copper = d["copper"]
        self.tracks = d["tracks"]
        self.vias = d["vias"]
        self.pads = d["pads"]
        self.fps = {f["ref"]: f for f in d["footprints"]}
        self.outline = d["outline"]
        self.nets = sorted({c["net"] for c in self.copper} | {t["net"] for t in self.tracks})
        # copper layer count: written by extract_kicad.py; older extracts are 4-layer
        n = d.get("n_cu") or (6 if any(c["layer"] in ("In3.Cu", "In4.Cu") for c in self.copper) else 4)
        self.st = stackup(n)
        self.layers, self.t_cu, self.z, self.diel = self.st["layers"], self.st["t_cu"], self.st["z"], self.st["diel"]

    def net(self, name):
        """Resolve a short net name ('PVDD', 'GND', '/charger/VSYS') to the board's full name."""
        if name in self.nets:
            return name
        hits = [n for n in self.nets if n.split("/")[-1] == name.split("/")[-1]]
        if len(hits) != 1:
            raise KeyError(f"net {name!r}: {hits}")
        return hits[0]

    def pad(self, ref, num):
        for p in self.pads:
            if p["ref"] == ref and str(p["pad"]) == str(num):
                return p
        raise KeyError(f"{ref}.{num}")

    def pads_of(self, ref):
        return [p for p in self.pads if p["ref"] == ref]

    # ---------- rasterisation ----------
    def raster(self, grid, layer, nets=None, tracks_min_px=2):
        """Copper of `nets` (None = all) on `layer` as a bool mask. Polygons use the cell-centre
        rule; tracks are also drawn as lines >= tracks_min_px wide so thin traces stay
        4-connected on the grid."""
        img = Image.new("1", (grid.nx, grid.ny), 0)
        dr = ImageDraw.Draw(img)
        netset = None if nets is None else set(nets)

        def tr(pts):
            return [((x - grid.x0) / grid.p - 0.5, (y - grid.y0) / grid.p - 0.5) for x, y in pts]

        for c in self.copper:
            if c["layer"] != layer or (netset is not None and c["net"] not in netset):
                continue
            for poly in c["polys"]:
                ol = poly["outline"]
                if len(ol) < 3:
                    continue
                xs = [q[0] for q in ol]
                ys = [q[1] for q in ol]
                if (max(xs) < grid.x0 or min(xs) > grid.x0 + grid.nx * grid.p or
                        max(ys) < grid.y0 or min(ys) > grid.y0 + grid.ny * grid.p):
                    continue
                if not poly["holes"]:
                    dr.polygon(tr(ol), fill=1)
                    continue
                # draw outline minus holes in a cropped temp image, then OR in
                i0, j0 = grid.ij(min(xs), min(ys))
                i1, j1 = grid.ij(max(xs), max(ys))
                i0, j0, i1, j1 = max(i0 - 1, 0), max(j0 - 1, 0), min(i1 + 2, grid.nx), min(j1 + 2, grid.ny)
                sub = Grid(grid.x0 + i0 * grid.p, grid.y0 + j0 * grid.p, i1 - i0, j1 - j0, grid.p)
                tmp = Image.new("1", (sub.nx, sub.ny), 0)
                td = ImageDraw.Draw(tmp)

                def trs(pts):
                    return [((x - sub.x0) / sub.p - 0.5, (y - sub.y0) / sub.p - 0.5) for x, y in pts]
                td.polygon(trs(ol), fill=1)
                for h in poly["holes"]:
                    if len(h) >= 3:
                        td.polygon(trs(h), fill=0)
                img.paste(1, (i0, j0), tmp)
        m = np.array(img, dtype=bool)
        if tracks_min_px:
            img2 = Image.new("1", (grid.nx, grid.ny), 0)
            d2 = ImageDraw.Draw(img2)
            for t in self.tracks:
                if t["layer"] != layer or (netset is not None and t["net"] not in netset):
                    continue
                wpx = max(tracks_min_px, int(round(t["w"] / grid.p)))
                pts = [(t["x1"], t["y1"])] + ([(t["xm"], t["ym"])] if "xm" in t else []) + [(t["x2"], t["y2"])]
                d2.line(tr(pts), fill=1, width=wpx)
            m |= np.array(img2, dtype=bool)
        return m

    def outline_mask(self, grid):
        img = Image.new("1", (grid.nx, grid.ny), 0)
        dr = ImageDraw.Draw(img)
        for poly in self.outline:
            dr.polygon([((x - grid.x0) / grid.p - 0.5, (y - grid.y0) / grid.p - 0.5) for x, y in poly["outline"]], fill=1)
            for h in poly["holes"]:
                dr.polygon([((x - grid.x0) / grid.p - 0.5, (y - grid.y0) / grid.p - 0.5) for x, y in h], fill=0)
        return np.array(img, dtype=bool)


def load(name_or_path):
    p = name_or_path if name_or_path.endswith(".json") else os.path.join(WORK, name_or_path + ".json")
    return Board(p)


def extract(board_pcb, tag):
    """Copy a .kicad_pcb into work/ and extract it with KiCad's Python (read-only)."""
    import shutil
    os.makedirs(WORK, exist_ok=True)
    dst = os.path.join(WORK, tag + ".kicad_pcb")
    shutil.copyfile(board_pcb, dst)
    out = os.path.join(WORK, tag + ".json")
    subprocess.run([KICAD_PY, os.path.join(HERE, "extract_kicad.py"), dst, out], check=True,
                   stderr=subprocess.DEVNULL)
    return out


def style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.style.use(os.path.join(ROOT, "sim", "paper.mplstyle"))
    return plt


def savefig(fig, name):
    """Saves PDF + PNG. POSTLAYOUT_FIGSUFFIX (set by run_all.sh) keeps re-runs from overwriting
    the rev A figures."""
    name += os.environ.get("POSTLAYOUT_FIGSUFFIX", "")
    os.makedirs(FIGDIR, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGDIR, f"{name}.{ext}"))


def save_json(obj, name):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, name), "w") as f:
        json.dump(obj, f, indent=1, default=float)


def dilate(mask, r_px):
    """Binary dilation by a disc of radius r_px (scipy)."""
    from scipy import ndimage
    if r_px <= 0:
        return mask
    yy, xx = np.mgrid[-r_px:r_px + 1, -r_px:r_px + 1]
    return ndimage.binary_dilation(mask, structure=(xx ** 2 + yy ** 2) <= r_px ** 2)


if __name__ == "__main__":
    b = load(sys.argv[1])
    print(b.name, len(b.nets), "nets")
