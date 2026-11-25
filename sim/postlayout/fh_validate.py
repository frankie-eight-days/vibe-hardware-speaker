"""FastHenry mesh validation: L1 microstrip (w x len) over an L2 plane, shorted at the far end.
Compares the PEEC grid mesh (same conventions as fh_loops.py) with the quasi-static microstrip
inductance L' = Z0_air / c (Hammerstad-Jensen, air-filled, thickness-corrected)."""
import os
import numpy as np
from fh_loops import run_fasthenry
from pl_common import WORK, Z, T_CU, save_json

def build(p, w=0.5, length=10.0, pw=6.0, path=None):
    lines = ["* microstrip validation", ".units mm", ".default sigma=5.8e4 nwinc=1 nhinc=1"]
    nid = {}
    def node(key, x, y, z):
        if key not in nid:
            nid[key] = len(nid); lines.append(f"N{nid[key]} x={x:.4f} y={y:.4f} z={z:.4f}")
        return nid[key]
    e = 0
    def mesh(tag, nx, ny, x0, y0, z, t):
        nonlocal e
        for j in range(ny):
            for i in range(nx):
                node((tag, i, j), x0 + (i + .5) * p, y0 + (j + .5) * p, z)
        for j in range(ny):
            for i in range(nx):
                if i + 1 < nx: lines.append(f"E{e} N{nid[(tag,i,j)]} N{nid[(tag,i+1,j)]} w={p} h={t}"); e += 1
                if j + 1 < ny: lines.append(f"E{e} N{nid[(tag,i,j)]} N{nid[(tag,i,j+1)]} w={p} h={t}"); e += 1
    ntw, ntl = int(round(w / p)), int(round(length / p))
    mesh("t", ntw, ntl, -w / 2, 0, Z["F.Cu"], T_CU["F.Cu"])
    npw, npl = int(round(pw / p)), int(round((length + 2) / p))
    mesh("g", npw, npl, -pw / 2, -1.0, Z["In1.Cu"], T_CU["In1.Cu"])
    # shorting via at the far end (centre of trace), port at the near end
    ic = ntw // 2; gi = npw // 2
    a = nid[("t", ic, ntl - 1)]; b = nid[("g", gi, int(round((length - p / 2 + 1) / p)))]
    lines.append(f"E{e} N{a} N{b} w=0.336 h=0.336 sigma={5.8e4*np.pi*0.3*0.02/0.336**2:.4g}"); e += 1
    pa = nid[("t", ic, 0)]; pb = nid[("g", gi, int(round(1 / p)))]
    lines += [f".external N{pa} N{pb}", ".freq fmin=1e8 fmax=1e8 ndec=1", ".end"]
    open(path, "w").write("\n".join(lines) + "\n")
    return len(nid), e

def analytic(w, h, t, length):
    # Hammerstad-Jensen air microstrip with thickness correction (Wheeler)
    u = w / h
    dw = t / np.pi * np.log(1 + 4 * np.e / (t / h * (1 / np.tanh(np.sqrt(6.517 * u))) ** 2))
    u = (w + dw) / h
    f = 6 + (2 * np.pi - 6) * np.exp(-(30.666 / u) ** 0.7528)
    z0 = 60 * np.log(f / u + np.sqrt(1 + (2 / u) ** 2))
    return z0 / 2.998e8 * length * 1e-3

if __name__ == "__main__":
    d = os.path.join(WORK, "fasthenry"); os.makedirs(d, exist_ok=True)
    h = Z["F.Cu"] - Z["In1.Cu"] - (T_CU["F.Cu"] + T_CU["In1.Cu"]) / 2  # dielectric gap
    hcc = Z["F.Cu"] - Z["In1.Cu"]
    La = analytic(0.5, hcc, 1e-4, 10.0)   # same filament geometry as the mesh (centre-to-centre)
    out = {"analytic_cc_nH": La * 1e9, "analytic_physical_nH": analytic(0.5, h, 0.035, 10.0) * 1e9,
           "note": "mesh vs analytic with centre-to-centre spacing = discretisation error; "
                   "centre filaments put the current 25 um further apart than the 100 MHz surface "
                   "currents, so mesh results are ~5-9 % high (conservative)", "h_mm": h, "w_mm": 0.5, "len_mm": 10.0, "mesh": []}
    for p in (0.25, 0.1):
        inp = os.path.join(d, f"valid_p{p}.inp")
        nn, ns = build(p, path=inp)
        z, dt = run_fasthenry(inp, f"_valid_{p}")
        L = z[1e8]["L"] * 1e9
        out["mesh"].append({"pitch": p, "nodes": nn, "segments": ns, "L_nH": L, "s": dt,
                            "err_pct": 100 * (L - La * 1e9) / (La * 1e9)})
        print(out["mesh"][-1], "analytic", La * 1e9)
    save_json(out, "fh_validation.json")
