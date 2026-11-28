#!/usr/bin/env python3
"""2D cross-section check for industrial design: which outer section shapes enclose the fixed internal package?

The package (enclosure Y/Z, mm; -Y front, +Z up) is the union of the fixed internals in the woofer/display
mid-section (X 1..65), from mech/concept/speaker_concept.py parameters and docs/mech_envelope.md:
  woofer flange plane + clearance, basket, motor (ND65-8 rear-mounted on a land at Y -30.4),
  battery tray front wall, pack + vendor tolerance, swell + foam (Gens ace 2S 5000, 109x42x19.5),
  main board + top parts under the baskets + bottom parts, standoff / gap-pad / spreader zone,
  UI board + parts.
Requirements on the OUTER skin (3 mm wall): display lens flush at Z 47.5 over |Y| <= 20, and the woofer
cone at 1.5 x Xmax + 1 mm + 0.8 mm grille => front skin at Y <= -41.0 over |Z| <= 23 (cone Sd dia 45.8).
Desk flat: outer Z = -44.5 (as concept; inner floor -41.5 keeps the 6.5 mm standoff + gap-pad stack).

All shapes are convex, so containment of the rectangle corners is containment of the rectangles.
Per family, scipy differential_evolution minimises the OUTER section area subject to containment.
Then the end (tweeter) section is checked: a pod (dia 35 x 21.5 deep incl. faceplate, from mech_envelope 2)
placed where the outer normal is 40 deg above horizontal must clear the PR basket (r 25 + 1 mm) and the
UI board (Y -9..22, Z 31.4..39 incl. parts) and stay inside the outer skin.

Net volume change ~ (A_inner - A_inner,baseline) x 202 mm (inner tube length), uniform along X.
Run: .venv/bin/python sim/acoustics/id_sens/section_check.py   (~1-2 min) -> section_check.json/.png
"""
import json
import math
import os

import numpy as np
from matplotlib.path import Path
from scipy.optimize import differential_evolution

HERE = os.path.dirname(os.path.abspath(__file__))
WALL = 3.0
Z_FLAT_IN = -41.5
L_IN = 202.0

RECTS = {  # (y0, y1, z0, z1)
    "woofer flange + 0.5 clr": (-30.4, -28.9, -32.5, 32.5),
    "woofer basket d52": (-28.9, -5.9, -26.0, 26.0),
    "woofer motor d38": (-5.9, 14.1, -19.0, 19.0),
    "tray front wall (puncture shield)": (15.6, 17.6, -25.0, 25.0),
    "battery + tolerance": (17.6, 37.1, -23.0, 23.0),
    "battery swell 10% + foam": (37.1, 39.05, -21.0, 21.0),
    "main board + top parts": (-21.0, 25.0, -35.0, -26.0),
    "board bottom parts": (-19.0, 23.0, -37.0, -35.0),
    "standoff / gap pad / spreader zone": (-16.0, 16.0, -41.5, -37.0),
    "UI board": (-20.0, 22.0, 31.4, 35.0),
    "UI top parts (<=4 mm)": (-9.0, 20.0, 35.0, 39.0),
}
OUTER_PTS = {"display lens flush": [(-20.0, 47.5), (20.0, 47.5)],
             "woofer cone + grille clearance": [(-41.0, -23.0), (-41.0, 23.0)]}
UI_END = (-9.0, 22.0, 31.4, 39.0)
PR_R = 26.0
POD_D, POD_DEPTH = 35.0, 21.5


def corners(r):
    y0, y1, z0, z1 = r
    return [(y0, z0), (y0, z1), (y1, z0), (y1, z1)]


PIN = np.array([c for r in RECTS.values() for c in corners(r)])
POUT = np.array([p for v in OUTER_PTS.values() for p in v])
TH = np.linspace(0, 2 * np.pi, 721)[:-1]


def clip_below(poly, zc):
    """Keep the part of polygon (N,2) with z >= zc (Sutherland-Hodgman, one plane)."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia, ib = a[1] >= zc, b[1] >= zc
        if ia:
            out.append(a)
        if ia != ib:
            t = (zc - a[1]) / (b[1] - a[1])
            out.append(a + t * (b - a))
    return np.array(out)


def area(poly):
    y, z = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.dot(y, np.roll(z, -1)) - np.dot(z, np.roll(y, -1)))


def offset(poly, d):
    """Outward offset of a convex CCW polygon by d (vertex normals from neighbours)."""
    if area_signed(poly) < 0:
        poly = poly[::-1]
    t = np.roll(poly, -1, 0) - np.roll(poly, 1, 0)
    nrm = np.stack([t[:, 1], -t[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    return poly + d * nrm


def area_signed(poly):
    y, z = poly[:, 0], poly[:, 1]
    return 0.5 * (np.dot(y, np.roll(z, -1)) - np.dot(z, np.roll(y, -1)))


def outside_dist(poly, pts):
    """>0: distance of each point outside the polygon; 0 inside."""
    path = Path(poly)
    inside = path.contains_points(pts, radius=1e-6)
    seg_a, seg_b = poly, np.roll(poly, -1, 0)
    ab = seg_b - seg_a
    d = []
    for p in pts:
        t = np.clip(np.einsum("ij,ij->i", p - seg_a, ab) / (np.einsum("ij,ij->i", ab, ab) + 1e-12), 0, 1)
        d.append(np.min(np.linalg.norm(seg_a + t[:, None] * ab - p, axis=1)))
    return np.where(inside, 0.0, np.array(d))


# ---------------------------------------------------------------- shape families (inner boundary)
def superellipse(yc, a_f, a_r, b, n_f, n_r, zc=0.0):
    c, s = np.cos(TH), np.sin(TH)
    a = np.where(c < 0, a_f, a_r)
    n = np.where(c < 0, n_f, n_r)
    y = yc + a * np.sign(c) * np.abs(c) ** (2 / n)
    z = zc + b * np.sign(s) * np.abs(s) ** (2 / n)
    return np.stack([y, z], 1)


def rounded_triangle(yf, yr, yt, zt, rc, zb):
    """conv(triangle (yf,zb),(yr,zb),(yt,zt)) (+) disc(rc): support-function boundary."""
    V = np.array([[yf, zb], [yr, zb], [yt, zt]])
    u = np.stack([np.cos(TH), np.sin(TH)], 1)
    k = np.argmax(u @ V.T, axis=1)
    return V[k] + rc * u


FAMILIES = {
    # name: (builder(x) -> inner polygon, bounds)
    "circle (baseline family)": (lambda x: superellipse(x[0], x[1], x[1], x[1], 2, 2), [(-5, 5), (40, 52)]),
    "ellipse / oval": (lambda x: superellipse(x[0], x[1], x[1], x[2], 2, 2), [(-5, 8), (34, 55), (34, 55)]),
    "superellipse (pill / squircle)": (lambda x: superellipse(x[0], x[1], x[1], x[2], x[3], x[3]),
                                       [(-5, 8), (34, 55), (34, 55), (2.0, 5.0)]),
    "D / egg (flat-ish front, round rear)": (lambda x: superellipse(x[0], x[1], x[2], x[3], x[4], 2.0),
                                             [(-5, 10), (28, 50), (28, 55), (34, 55), (2.0, 6.0)]),
    "softened triangle (flat base, apex up-rear)": (lambda x: rounded_triangle(x[0], x[1], x[2], x[3], x[4], Z_FLAT_IN + x[4]),
                                                    [(-40, 0), (0, 45), (-20, 30), (0, 40), (8, 30)]),
}


def evaluate(poly_in):
    pin = clip_below(poly_in, Z_FLAT_IN)
    pout = clip_below(offset(poly_in, WALL), Z_FLAT_IN - WALL)
    return pin, pout


def penalty(poly_in):
    pin, pout = evaluate(poly_in)
    e1 = outside_dist(pin, PIN)
    e2 = outside_dist(pout, POUT)
    return area(pout) + 1e4 * (np.sum(e1 ** 2) + np.sum(e2 ** 2)) + 1e3 * (np.sum(e1 > 0.05) + np.sum(e2 > 0.05))


def tweeter_fit(pout, pin):
    """Find outer-skin points (front-top quadrant) whose outward normal is 40 deg above horizontal (front);
    return the best pod clearance to the PR basket and UI board."""
    P = pout
    t = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    if area_signed(P) < 0:
        t = -t
    nrm = np.stack([t[:, 1], -t[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    elev = np.degrees(np.arctan2(nrm[:, 1], -nrm[:, 0]))         # 0 = front, 90 = up
    cand = np.where((np.abs(elev - 40) < 2.5) & (P[:, 0] < 0) & (P[:, 1] > 0))[0]
    best = None
    ax = np.array([-math.cos(math.radians(40)), math.sin(math.radians(40))])
    perp = np.array([ax[1], -ax[0]])
    for i in cand:
        face = P[i]
        back = face - POD_DEPTH * ax
        pod = np.array([face + POD_D / 2 * perp, face - POD_D / 2 * perp, back - POD_D / 2 * perp, back + POD_D / 2 * perp])
        dense = np.concatenate([pod[k] + np.linspace(0, 1, 30)[:, None] * (pod[(k + 1) % 4] - pod[k]) for k in range(4)])
        pr_clear = float(np.min(np.linalg.norm(dense, axis=1)) - PR_R)
        y0, y1, z0, z1 = UI_END
        dy = np.maximum(np.maximum(y0 - dense[:, 0], dense[:, 0] - y1), 0)
        dz = np.maximum(np.maximum(z0 - dense[:, 1], dense[:, 1] - z1), 0)
        inside_ui = (dy == 0) & (dz == 0)
        ui_clear = float(-1.0 if inside_ui.any() else np.min(np.hypot(dy, dz)))
        out_skin = float(np.max(outside_dist(pout, dense)))
        score = min(pr_clear, ui_clear) - 10 * out_skin
        if best is None or score > best["score"]:
            best = dict(score=score, face_yz=[round(float(face[0]), 1), round(float(face[1]), 1)],
                        face_height_above_desk_mm=round(float(face[1]) - (Z_FLAT_IN - WALL), 1),
                        pr_basket_clear_mm=round(pr_clear, 1), ui_board_clear_mm=round(ui_clear, 1),
                        pod_outside_skin_mm=round(out_skin, 1))
    return best


def describe(name, poly_in, x=None):
    pin, pout = evaluate(poly_in)
    flat = pout[np.abs(pout[:, 1] - (Z_FLAT_IN - WALL)) < 1e-6]
    e1, e2 = outside_dist(pin, PIN), outside_dist(pout, POUT)
    tight = [k for k, r in RECTS.items() if np.any(outside_dist(offset(pin, -0.75), np.array(corners(r))) > 0)]
    tight += [k for k, v in OUTER_PTS.items() if np.any(outside_dist(offset(pout, -0.75), np.array(v)) > 0)]
    return dict(family=name, params=None if x is None else [round(float(v), 2) for v in x],
                outer_area_cm2=round(area(pout) / 100, 2), inner_area_cm2=round(area(pin) / 100, 2),
                outer_depth_y_mm=round(float(np.ptp(pout[:, 0])), 1), outer_height_z_mm=round(float(np.ptp(pout[:, 1])), 1),
                desk_flat_width_mm=round(float(np.ptp(flat[:, 0])), 1) if len(flat) else 0.0,
                max_violation_mm=round(float(max(e1.max(), e2.max())), 2), binding=tight,
                tweeter=tweeter_fit(pout, pin)), pin, pout


results = []
polys = {}
base_poly = superellipse(0.0, 44.5, 44.5, 44.5, 2, 2)
b, bpin, bpout = describe("BASELINE concept: circle R 44.5 in / 47.5 out, flat at Z -44.5", base_poly)
results.append(b)
polys[b["family"]] = (bpin, bpout)
for name, (fn, bounds) in FAMILIES.items():
    r = differential_evolution(lambda x: penalty(fn(x)), bounds, seed=3, tol=1e-7, maxiter=400, popsize=25, polish=False)
    d, pin, pout = describe(name, fn(r.x), r.x)
    results.append(d)
    polys[name] = (pin, pout)

A0 = results[0]["inner_area_cm2"]
for d in results:
    d["net_volume_change_cm3"] = round((d["inner_area_cm2"] - A0) * L_IN / 10, 0)
    d["net_volume_change_pct_of_820"] = round(100 * (d["inner_area_cm2"] - A0) * L_IN / 10 / 820, 1)

with open(os.path.join(HERE, "section_check.json"), "w") as fh:
    json.dump(dict(package_rects=RECTS, outer_points=OUTER_PTS, wall_mm=WALL, results=results), fh, indent=1)

import matplotlib                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt         # noqa: E402
fig, axs = plt.subplots(1, len(results), figsize=(3.2 * len(results), 3.6))
for ax, d in zip(axs, results):
    pin, pout = polys[d["family"]]
    ax.fill(pout[:, 0], pout[:, 1], color="0.85")
    ax.fill(pin[:, 0], pin[:, 1], color="white")
    for r in RECTS.values():
        ax.add_patch(plt.Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc="tab:blue", alpha=0.35, lw=0))
    ax.plot(POUT[:, 0], POUT[:, 1], "r+")
    ax.add_patch(plt.Circle((0, 0), PR_R, fill=False, ls=":", color="tab:green"))
    if d["tweeter"]:
        fy, fz = d["tweeter"]["face_yz"]
        axv = np.array([-math.cos(math.radians(40)), math.sin(math.radians(40))])
        ax.plot([fy, fy - POD_DEPTH * axv[0]], [fz, fz - POD_DEPTH * axv[1]], color="tab:orange", lw=4, alpha=0.7)
    ax.set_aspect("equal"); ax.set_xlim(-55, 55); ax.set_ylim(-50, 55)
    ax.set_title(f"{d['family'][:28]}\nA_out {d['outer_area_cm2']} cm2, dV {d['net_volume_change_cm3']:+.0f} cm3", fontsize=7)
    ax.tick_params(labelsize=6); ax.set_xlabel("Y (front <-)", fontsize=6)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "section_check.png"), dpi=160)
for d in results:
    print(json.dumps(d))
