#!/usr/bin/env python3
"""2D checks of the FACET section against the hard points of sim/acoustics/id_sens/section_check.py.

Run: .venv/bin/python mech/id/facet/facet_section_check.py  -> build/section_check_facet.json + figure
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facet_section as fs  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SC = json.load(open(os.path.join(ROOT, "sim/acoustics/id_sens/section_check.json")))
RECTS = SC["package_rects"]
OUTER_PTS = {"display lens top": [(0.0, 47.5)], "woofer cone + grille clearance (Y<=-41 over |Z|<=23)":
             [(-41.0, z) for z in (-23, -15, -5, 0, 5, 15, 23)]}
BASE_INNER_AREA = SC["results"][0]["inner_area_cm2"]   # 61.56 cm2, R 44.5 circle with the flat floor
L_IN = 202.0

po = fs.polyline(0.0, 48)
pi = fs.polyline(fs.WALL, 48)
res = dict(facets=[dict(name=n, phi_deg=p, h_outer_mm=round(h, 3), outer_corner_radius_mm=r)
                   for (n, p, h), r in zip(fs.FACETS, fs.RADII)])
res["outer_area_cm2"] = round(fs.area(po) / 100, 2)
res["inner_area_cm2"] = round(fs.area(pi) / 100, 2)
res["baseline_inner_area_cm2"] = BASE_INNER_AREA
res["delta_volume_cm3_uniform_202mm"] = round((res["inner_area_cm2"] - BASE_INNER_AREA) * L_IN / 10, 1)
ys = [p[0] for p in po]
zs = [p[1] for p in po]
res["outer_depth_y_mm"] = round(max(ys) - min(ys), 1)
res["outer_height_z_mm"] = round(max(zs) - min(zs), 1)
res["outer_y_range"] = [round(min(ys), 2), round(max(ys), 2)]
res["outer_z_range"] = [round(min(zs), 2), round(max(zs), 2)]
res["flats_outer"] = fs.facet_flats(0.0)

# hard points: inner skin must enclose package rectangles
hp = {}
for k, (y0, y1, z0, z1) in RECTS.items():
    d = min(fs.inside(pi, c) for c in ((y0, z0), (y0, z1), (y1, z0), (y1, z1)))
    hp[k] = round(d, 2)
res["inner_clearance_to_package_mm"] = hp
op = {}
for k, pts in OUTER_PTS.items():
    op[k] = round(min(fs.inside(po, c) for c in pts), 2)
res["outer_margin_mm"] = op

# tweeter: face centre on the shoulder facet, the pod rectangle in the section at X = +-83
n40 = fs.normal(40.0)
t40 = (math.sin(math.radians(40)), math.cos(math.radians(40)))    # along the facet, up-rear
C_TW = (-0.766044 * 47.5 * 1.0, 0.642788 * 47.5)                  # (-36.39, 30.53): today's face centre
POD_R, POD_DEPTH = 17.5, 21.5
pod = [(C_TW[0] + s * POD_R * t40[0] - d * n40[0], C_TW[1] + s * POD_R * t40[1] - d * n40[1])
       for s, d in ((-1, 0), (1, 0), (1, POD_DEPTH), (-1, POD_DEPTH))]
on_facet = fs.inside(po, C_TW)
res["tweeter"] = dict(face_centre_yz=[round(v, 2) for v in C_TW], axis_elevation_deg=40.0,
                      face_on_shoulder_facet_residual_mm=round(on_facet, 3),
                      face_height_above_desk_mm=round(C_TW[1] + 44.5, 1))
sh = res["flats_outer"]["shoulder"]
a, b = sh["from_"], sh["to"]
s_face = (C_TW[0] - a[0]) * t40[0] + (C_TW[1] - a[1]) * t40[1]
L_flat = math.dist(a, b)
res["tweeter"]["boss_r_mm"] = 18.5
res["tweeter"]["shoulder_flat_len_mm"] = round(L_flat, 2)
res["tweeter"]["boss_edge_to_lower_tangent_mm"] = round(s_face - 18.5, 2)
res["tweeter"]["boss_edge_to_upper_tangent_mm"] = round(L_flat - s_face - 18.5, 2)


# how far the facet plane stands above the rounded skin under the boss edges (relief seen by the dome)
def skin_drop(dist_into_fillet, r):
    return 0.0 if dist_into_fillet <= 0 else r - math.sqrt(max(r * r - dist_into_fillet ** 2, 0.0))


res["tweeter"]["boss_overhang_drop_lower_mm"] = round(skin_drop(-(s_face - 18.5), fs.RADII[0]), 2)
res["tweeter"]["boss_overhang_drop_upper_mm"] = round(skin_drop(-(L_flat - s_face - 18.5), fs.RADII[1]), 2)
ui = (-9.0, 22.0, 31.4, 39.0)
pod_dense = []
for k in range(4):
    p0, p1 = pod[k], pod[(k + 1) % 4]
    pod_dense += [(p0[0] + (p1[0] - p0[0]) * j / 40, p0[1] + (p1[1] - p0[1]) * j / 40) for j in range(41)]
res["tweeter"]["pod_to_PR_basket_r25_mm"] = round(min(math.hypot(*p) for p in pod_dense) - 25.0, 2)
res["tweeter"]["pod_to_UI_envelope_mm"] = round(min(math.hypot(max(ui[0] - p[0], 0, p[0] - ui[1]), max(ui[2] - p[1], 0, p[1] - ui[3]))
                                                    for p in pod_dense), 2)
res["tweeter"]["pod_inside_inner_skin_mm"] = round(min(fs.inside(po, p) for p in pod_dense), 2)

# woofer tunnel depth over the d53 bore (piston plane Y -33.9, as capsule_geometry / a3)
Y_PISTON = -33.9
a_t = 26.5
dep = []
N = 81
for i in range(N):
    for j in range(N):
        x = -a_t + 2 * a_t * i / (N - 1)
        z = -a_t + 2 * a_t * j / (N - 1)
        if x * x + z * z > a_t * a_t:
            continue
        # outer skin Y at height z (front side): min Y of the polygon at that z
        ymin = None
        for k in range(len(po)):
            (y0, z0), (y1, z1) = po[k], po[(k + 1) % len(po)]
            if (z0 - z) * (z1 - z) <= 0 and abs(z1 - z0) > 1e-12:
                yy = y0 + (y1 - y0) * (z - z0) / (z1 - z0)
                ymin = yy if ymin is None else min(ymin, yy)
        dep.append(-ymin + Y_PISTON)
res["woofer_tunnel"] = dict(depth_centre_mm=round(47.5 + Y_PISTON, 2), depth_mean_mm=round(sum(dep) / len(dep), 2),
                            depth_edge_min_mm=round(min(dep), 2), baseline_a3=dict(centre=13.6, mean=11.68, edge=5.52))

# desk flat, feet, tip angle are in the scorecard (need the CG)
json.dump(res, open(os.path.join(HERE, "build", "section_check_facet.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("flats_outer",)}, indent=1))
print(json.dumps(res["flats_outer"], indent=1))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

fig, ax = plt.subplots(figsize=(7, 7))
ax.fill([p[0] for p in po], [p[1] for p in po], color="0.82", label="FACET wall (3 mm)")
ax.fill([p[0] for p in pi], [p[1] for p in pi], color="white")
th = [2 * math.pi * k / 200 for k in range(201)]
ax.plot([47.5 * math.cos(t) for t in th], [max(47.5 * math.sin(t), -44.5) for t in th], "k--", lw=0.8, label="today R 47.5 + flat")
for k, (y0, y1, z0, z1) in RECTS.items():
    ax.add_patch(plt.Rectangle((y0, z0), y1 - y0, z1 - z0, fc="tab:blue", alpha=0.3, lw=0))
ax.add_patch(plt.Polygon(pod, fc="tab:orange", alpha=0.5, label="tweeter pod (X +-83)"))
ax.add_patch(plt.Circle((0, 0), 25, fill=False, ls=":", color="tab:green", label="PR basket r 25 (ends)"))
ax.plot([C_TW[0], C_TW[0] + 25 * n40[0]], [C_TW[1], C_TW[1] + 25 * n40[1]], color="tab:red", lw=1.5, label="tweeter axis 40 deg")
ax.plot([-41, -41], [-23, 23], "r", lw=2, label="Y <= -41 rule")
ax.set_aspect("equal")
ax.set_xlim(-60, 55)
ax.set_ylim(-55, 60)
ax.set_xlabel("Y (mm, front <-)")
ax.set_ylabel("Z (mm)")
ax.set_title(f"FACET section: inner {res['inner_area_cm2']} cm2 vs {BASE_INNER_AREA} today "
             f"({res['delta_volume_cm3_uniform_202mm']:+.0f} cm3)", fontsize=9)
ax.legend(fontsize=7, loc="lower right")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "build", "section_facet_2d.png"), dpi=140)
