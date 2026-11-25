"""Diff the power-stage copper of two extracted boards (e.g. hybrid_final vs pcb_critical_routed).

For each stage window (loop parts + 3 mm), per layer and per net: copper area in A, in B and the
XOR area (0.05 mm raster); plus vias of the stage nets inside the window.
Run: python diff_power.py TAG_A TAG_B
"""
import sys

import numpy as np

from pl_common import Grid, load, save_json

STAGES = {
    "boost": (["U901", "C914", "C906", "C903", "L901"], ["PVDD", "GND", "BST_SW", "VSYS"]),
    "buck": (["U951", "C953", "L951"], ["VSYS", "GND", "BUCK_SW"]),
    "charger": (["U701", "C707", "C716", "L701"], ["CHG_PMID", "VSYS", "GND", "CHG_SW1", "CHG_SW2"]),
}


def window(b, refs, m=3.0):
    bb = np.array([p["bbox"] for r in refs for p in b.pads_of(r)])
    return [bb[:, 0].min() - m, bb[:, 1].min() - m, bb[:, 2].max() + m, bb[:, 3].max() + m]


def main(ta, tb):
    A, B = load(ta), load(tb)
    LAYERS = A.layers + [L for L in B.layers if L not in A.layers]   # 4L vs 6L: union
    out = {}
    for st, (refs, nets) in STAGES.items():
        win = window(A, refs)
        g = Grid.from_bbox(win, 0.05)
        rows = []
        for n in nets:
            na, nb = A.net(n), B.net(n)
            for L in LAYERS:
                ma = A.raster(g, L, [na], tracks_min_px=0)
                mb = B.raster(g, L, [nb], tracks_min_px=0)
                a2 = g.p ** 2
                x = (ma ^ mb).sum() * a2
                if ma.any() or mb.any():
                    rows.append({"net": n, "layer": L, "A_mm2": float(ma.sum() * a2), "B_mm2": float(mb.sum() * a2),
                                 "xor_mm2": float(x)})
        inwin = lambda v: win[0] <= v["x"] <= win[2] and win[1] <= v["y"] <= win[3]
        nn = {A.net(n) for n in nets}
        va = sorted((round(v["x"], 2), round(v["y"], 2), v["net"]) for v in A.vias if v["net"] in nn and inwin(v))
        vb = sorted((round(v["x"], 2), round(v["y"], 2), v["net"]) for v in B.vias if v["net"] in nn and inwin(v))
        out[st] = {"window": win, "copper": rows, "vias_A": len(va), "vias_B": len(vb),
                   "vias_only_A": [v for v in va if v not in vb], "vias_only_B": [v for v in vb if v not in va],
                   "xor_total_mm2": sum(r["xor_mm2"] for r in rows)}
        print(f"{st}: XOR {out[st]['xor_total_mm2']:.2f} mm2, vias {len(va)}/{len(vb)}, "
              f"only {ta} {len(out[st]['vias_only_A'])}, only {tb} {len(out[st]['vias_only_B'])}")
        for r in rows:
            if r["xor_mm2"] > 0.05:
                print(f"   {r['net']:>9} {r['layer']:7} {ta} {r['A_mm2']:7.2f}  {tb} {r['B_mm2']:7.2f}  xor {r['xor_mm2']:.2f}")
    save_json(out, f"diff_power_{ta}_vs_{tb}.json")


if __name__ == "__main__":
    main(*(sys.argv[1:3] if len(sys.argv) > 2 else ("hybrid", "designed")))
