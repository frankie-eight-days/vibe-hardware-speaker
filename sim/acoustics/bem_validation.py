"""Validation of the BEM pipeline (bem_core.py) against an exact solution: a rigid sphere with a
vibrating spherical-cap piston (Morse & Ingard, Theoretical Acoustics, sec. 7.2).

Sphere radius a = 50 mm (between the capsule's 47.5 mm radius and its end-cap scale), cap half-angle
27 deg (cap radius 22.7 mm, close to the ND65-8 piston radius 22.9 mm).  Exact pressure (e^{-iwt}):
    p(r, th) = i rho c  sum_n V_n h_n(kr) / h_n'(ka) P_n(cos th),
    V_0 = v0 (1 - cos al)/2,   V_n = v0/2 [P_{n-1}(cos al) - P_{n+1}(cos al)]  (n >= 1).
Frequencies: 1 kHz, 3.43 kHz (= the first interior Dirichlet eigenfrequency, ka = pi, where the plain
direct formulation must fail) and 8 kHz.  Methods: plain direct, CHIEF (production), Burton-Miller.
The mesh uses the same gmsh settings rule as the capsule (h = lambda/6 at 8 kHz).
Output: results/bem_validation.json and figure a2_a3_bem_validation_sphere_piston.
"""
import json
import math
import time

import numpy as np
from scipy.special import eval_legendre, spherical_jn, spherical_yn

import common
from bem_core import Radiator, make_grid, interior_points
from capsule_geometry import _orient_outward, check_closed

A_SPH = 0.05
ALPHA = math.radians(27.0)
FREQS = [1000.0, 3430.0, 8000.0]
F_MESH = 8000.0


def sphere_mesh(h_mm):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    a = A_SPH * 1e3
    s = occ.addSphere(0, 0, 0, a)
    d = occ.addDisk(0, 0, a * math.cos(ALPHA), 2 * a, 2 * a)
    out, omap = occ.fragment([(3, s)], [(2, d)])
    occ.synchronize()
    vols = [v for v in out if v[0] == 3]
    bnd = [b[1] for b in gmsh.model.getBoundary(vols, combined=True, oriented=False)]
    for e in gmsh.model.getEntities(2):
        if e[1] not in bnd:
            up, _ = gmsh.model.getAdjacencies(2, e[1])
            if len(up) == 0:
                occ.remove([e], recursive=True)
    occ.synchronize()
    bnd = [b[1] for b in gmsh.model.getBoundary(gmsh.model.getEntities(3), combined=True, oriented=False)]
    cap = [b for b in bnd if occ.getCenterOfMass(2, b)[2] > a * math.cos(ALPHA)]
    rest = [b for b in bnd if b not in cap]
    gmsh.model.addPhysicalGroup(2, rest, 1)
    gmsh.model.addPhysicalGroup(2, cap, 11)
    gmsh.option.setNumber("Mesh.MeshSizeMax", h_mm)
    gmsh.option.setNumber("Mesh.MeshSizeMin", h_mm / 2.5)
    gmsh.model.mesh.generate(2)
    nt, cc, _ = gmsh.model.mesh.getNodes()
    xyz = cc.reshape(-1, 3) * 1e-3
    idx = {t: i for i, t in enumerate(nt)}
    tris, dom = [], []
    for dim, tag in gmsh.model.getPhysicalGroups(2):
        for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, tag):
            _, _, en = gmsh.model.mesh.getElements(2, ent)
            t = np.array([idx[n] for n in en[0]]).reshape(-1, 3)
            tris.append(t)
            dom.append(np.full(len(t), tag))
    gmsh.finalize()
    tris = _orient_outward(xyz, np.vstack(tris))
    return xyz, tris, np.concatenate(dom)


def exact(f, r, th, v0=1.0):
    k = 2 * np.pi * f / common.C0
    ca = math.cos(ALPHA)
    N = int(k * A_SPH + 40)
    p = np.zeros_like(th, dtype=complex)
    for n in range(N):
        Vn = v0 * (1 - ca) / 2 if n == 0 else v0 / 2 * (eval_legendre(n - 1, ca) - eval_legendre(n + 1, ca))
        hn = spherical_jn(n, k * r) + 1j * spherical_yn(n, k * r)
        hnp = spherical_jn(n, k * A_SPH, derivative=True) + 1j * spherical_yn(n, k * A_SPH, derivative=True)
        p += 1j * common.RHO * common.C0 * Vn * hn / hnp * eval_legendre(n, np.cos(th))
    return np.conj(p)                                   # -> e^{+jwt} convention like bem_core outputs


def main():
    plt = common.setup_mpl()
    h = common.C0 / F_MESH / 6 * 1e3
    xyz, tris, dom = sphere_mesh(h)
    assert check_closed(tris) == 0
    grid = make_grid(xyz, tris, dom)
    sd_cap = 2 * np.pi * A_SPH ** 2 * (1 - math.cos(ALPHA))
    pts_in = interior_points(30, 1, lambda q: np.linalg.norm(q, axis=1) < 0.7 * A_SPH,
                             np.array([-A_SPH, -A_SPH, -A_SPH, A_SPH, A_SPH, A_SPH]))
    rad = Radiator(grid, {"cap": 11}, interior_pts=pts_in, sd_true={"cap": sd_cap})
    th = np.radians(np.arange(0, 181, 2.0))
    r_eval = 1.0
    pts = np.vstack([r_eval * np.sin(th), np.zeros_like(th), r_eval * np.cos(th)])
    res = dict(mesh=dict(h_mm=h, n_tri=int(len(tris)), n_dof=rad.ndof, f_mesh=F_MESH), cases=[])
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.8), sharey=True)
    for ax, f in zip(axs, FREQS):
        pex = exact(f, r_eval, th)
        ax.plot(np.degrees(th), common.spl(np.abs(pex) / np.sqrt(2)), "k-", lw=2.4, label="exact (series)")
        for method, ls, lab in (("direct", ":", "direct BIE"), ("chief", "--", "direct + CHIEF"), ("bm", "-.", "Burton-Miller")):
            t0 = time.time()
            if method == "direct":
                saved, rad.interior = rad.interior, None
                sol, k = rad.solve(f, method="chief")
                rad.interior = saved
            else:
                sol, k = rad.solve(f, method=method)
            p = rad.field(sol, k, pts)["cap"]
            err_db = common.spl(np.abs(p)) - common.spl(np.abs(pex))
            rel = np.abs(p - pex) / np.abs(pex)
            res["cases"].append(dict(f_hz=f, ka=k * A_SPH, method=method, max_abs_err_db=float(np.max(np.abs(err_db))),
                                     rms_err_db=float(np.sqrt(np.mean(err_db ** 2))), max_rel_err=float(rel.max()),
                                     median_rel_err=float(np.median(rel)), time_s=time.time() - t0))
            print(res["cases"][-1])
            ax.plot(np.degrees(th), common.spl(np.abs(p) / np.sqrt(2)), ls, label=lab)
        ax.set_title(f"{f/1e3:.2f} kHz (ka = {k*A_SPH:.2f})", fontsize=9)
        ax.set_xlabel("angle from piston axis (deg)")
        ax.set_xlim(0, 180)
        ax.set_xticks([0, 45, 90, 135, 180])
    axs[0].set_ylabel("SPL at 1 m for 1 m/s (dB)")
    axs[1].legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    common.savefig(fig, "a2_a3_bem_validation_sphere_piston")

    # fine sweep through the first interior eigenfrequency: the plain direct BIE breaks down in a narrow band
    fs = np.arange(3300.0, 3601.0, 3.0)
    sweep = {"f_hz": fs.tolist(), "direct": [], "chief": []}
    for f in fs:
        pex = exact(f, r_eval, th)
        for method in ("direct", "chief"):
            if method == "direct":
                saved, rad.interior = rad.interior, None
                sol, k = rad.solve(f, method="chief")
                rad.interior = saved
            else:
                sol, k = rad.solve(f, method="chief")
            p = rad.field(sol, k, pts)["cap"]
            sweep[method].append(float(np.max(np.abs(common.spl(np.abs(p)) - common.spl(np.abs(pex))))))
    res["eigen_sweep"] = sweep
    i = int(np.argmax(sweep["direct"]))
    res["eigen_sweep_summary"] = dict(f_worst_direct=float(fs[i]), err_direct_db=sweep["direct"][i],
                                      err_chief_db_at_same_f=sweep["chief"][i], err_chief_max_db=max(sweep["chief"]))
    print(res["eigen_sweep_summary"])
    fig2, ax2 = plt.subplots(figsize=(4.5, 2.8))
    ax2.semilogy(fs, sweep["direct"], label="direct BIE")
    ax2.semilogy(fs, sweep["chief"], "--", label="direct + CHIEF (30 points)")
    ax2.axvline(common.C0 * np.pi / (2 * np.pi * A_SPH), color="0.5", lw=0.8)
    ax2.text(common.C0 / (2 * A_SPH) + 5, max(sweep["direct"]) * 0.6, "ka = pi\n(interior eigenfrequency)", fontsize=7)
    ax2.set_xlabel("frequency (Hz)")
    ax2.set_ylabel("max |error| over angle (dB)")
    ax2.legend(loc="upper left")
    fig2.tight_layout()
    common.savefig(fig2, "a2_a3_bem_validation_irregular_frequency")
    common.save_json(res, "bem_validation.json")
    # CSV of the exact curves and the CHIEF result
    rows = [np.degrees(th)]
    hdr = ["angle_deg"]
    for f in FREQS:
        rows.append(common.spl(np.abs(exact(f, r_eval, th)) / np.sqrt(2)))
        hdr.append(f"exact_spl_db_{int(f)}hz")
    common.save_csv("bem_validation_exact.csv", hdr, rows)


if __name__ == "__main__":
    main()
