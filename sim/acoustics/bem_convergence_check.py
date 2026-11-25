"""Mesh-convergence and formulation check of the capsule BEM at 5 kHz (why the tweeter needs local refinement).

Solves the left tweeter and left woofer of the as-designed hull at 5 kHz on five meshes / methods and
compares the far-field patterns in the tweeter's horizontal and vertical planes with the finest
Burton-Miller solution (global h = 5.6 mm, h = 2.0 mm around the tweeters).  Reported: max and median
|dB difference| over directions within 20 dB of the pattern maximum.
Output: results/bem_convergence_check.json.  Runtime ~10 min.
"""
import numpy as np

import common
import capsule_geometry as cg
from bem_core import Radiator, make_grid, interior_points
from bem_capsule_run import field_points, inside_capsule

F = 5000.0
CASES = [  # (global h, tweeter h, label, CHIEF points, method)
    (9.0, None, "h9 CHIEF (no local refinement)", 40, "chief"),
    (9.0, None, "h9 CHIEF, 80 points", 80, "chief"),
    (9.0, None, "h9 Burton-Miller (no local refinement)", 40, "bm"),
    (9.0, 2.8, "h9 + 2.8 mm at tweeters, CHIEF (production)", 40, "chief"),
    (5.6, 2.8, "h5.6 + 2.8 mm at tweeters, CHIEF (production)", 40, "chief"),
    (5.6, 2.0, "h5.6 + 2.0 mm at tweeters, CHIEF", 40, "chief"),
    (5.6, 2.0, "reference: h5.6 + 2.0 mm, Burton-Miller", 40, "bm"),
]


def main():
    Fd, _, _ = field_points("bezel")
    dirs = np.hstack([Fd["tw_h"], Fd["tw_v"]])
    sd = {"tweeter_L": cg.SD_TWEETER, "woofer_L": cg.SD_WOOFER}
    res, meta = {}, {}
    for h, ht, lab, npt, meth in CASES:
        xyz, tris, dom, info = cg.build("bezel", h_max=h, h_tweeter=ht)
        pin = interior_points(npt, 7 if npt == 40 else 3, inside_capsule, np.array([-0.09, -0.03, -0.03, 0.09, 0.03, 0.03]))
        rad = Radiator(make_grid(xyz, tris, dom), {n: cg.TAGS[n] for n in sd}, interior_pts=pin, sd_true=sd)
        sol, k = rad.solve(F, method=meth)
        res[lab] = rad.field(sol, k, dirs, far=True)
        meta[lab] = dict(ndof=rad.ndof, solve_s=rad.last_time)
        print(lab, meta[lab], flush=True)
    ref = res[CASES[-1][2]]
    out = dict(f_hz=F, cases={})
    for lab, r in res.items():
        row = dict(meta[lab])
        for n in sd:
            d = np.abs(20 * np.log10(np.abs(r[n]) / np.abs(ref[n])))
            lev = 20 * np.log10(np.abs(ref[n]) / np.abs(ref[n]).max())
            row[n] = dict(max_db=float(d[lev > -20].max()), median_db=float(np.median(d[lev > -20])))
        out["cases"][lab] = row
        print(lab, {n: row[n] for n in sd})
    common.save_json(out, "bem_convergence_check.json")


if __name__ == "__main__":
    main()
