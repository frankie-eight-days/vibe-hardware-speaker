"""Figure: the BEM hull (as meshed) and a check that it matches the FreeCAD concept model.

Panel 1-2: the bezel and waveguide hull meshes with the radiating pistons coloured.
Panel 3-4: cross-sections at the woofer (x = +33 mm) and tweeter (x = +83 mm) planes: the BEM hull
outline over the CAD shell/driver solids (mech/concept/build/*.stl), so any mismatch is visible.
Writes results/bem_geometry_check.json (max distance from hull section to CAD outer section).
"""
import os
import struct

import numpy as np

import common
import capsule_geometry as cg

BUILD = os.path.join(common.ROOT, "mech", "concept", "build")
CAD_EXTERIOR = ["shell_front", "shell_rear", "end_cap_L", "end_cap_R", "tweeter_L", "tweeter_R",
                "woofer_L_flange", "woofer_R_flange", "pr_L_flange", "pr_R_flange", "knob"]


def read_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        v = []
        for line in data.decode(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                v.append([float(t) for t in line.split()[1:4]])
        return np.array(v).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return arr["v"].reshape(-1, 3, 3).astype(float)


def slice_x(tri, x0):
    """Line segments where triangles (N,3,3) cross the plane x = x0 -> (M, 2, 2) in (y, z)."""
    d = tri[:, :, 0] - x0
    segs = []
    for t, dd in zip(tri, d):
        s = np.sign(dd)
        if np.all(s > 0) or np.all(s < 0):
            continue
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (dd[a] > 0) != (dd[b] > 0):
                w = dd[a] / (dd[a] - dd[b])
                p = t[a] + w * (t[b] - t[a])
                pts.append(p[1:])
        if len(pts) == 2:
            segs.append(pts)
    return np.array(segs)


def main():
    plt = common.setup_mpl()
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    meshes = {}
    for var in ("bezel", "waveguide"):
        meshes[var] = cg.build(var, h_max=6.0)
    fig = plt.figure(figsize=(7.0, 5.6))
    colors = {cg.TAG_RIGID: (0.80, 0.80, 0.78)}
    for n, t in cg.TAGS.items():
        colors[t] = {"w": (0.12, 0.31, 0.47), "p": (0.33, 0.51, 0.21), "t": (0.77, 0.35, 0.07)}[n[0]]
    light = np.array([-0.4, -0.8, 0.6])
    light /= np.linalg.norm(light)
    for i, var in enumerate(("bezel", "waveguide")):
        xyz, tris, dom, info = meshes[var]
        ax = fig.add_subplot(2, 2, i + 1, projection="3d")
        v = xyz[tris] * 1e3
        nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1)[:, None]
        shade = 0.45 + 0.55 * np.clip(nrm @ light, 0, 1)
        fc = np.array([colors[d] for d in dom]) * shade[:, None]
        pc = Poly3DCollection(v, facecolors=fc, edgecolors=(0, 0, 0, 0.12), linewidths=0.1)
        ax.add_collection3d(pc)
        lim = 112
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim / 2, lim / 2)
        ax.set_zlim(-lim / 2, lim / 2)
        ax.set_box_aspect((2, 1, 1))
        ax.view_init(elev=22, azim=-62)
        ax.set_axis_off()
        lab = "as designed: 3 mm bezel" if var == "bezel" else "what-if: 10 mm waveguide, 220 mm body"
        ax.set_title(f"({'ab'[i]}) {lab}\n{info['n_tri']} triangles at h = 6 mm", fontsize=8.5)
    # sections vs CAD
    cad = {n: read_stl(os.path.join(BUILD, n + ".stl")) for n in CAD_EXTERIOR if os.path.exists(os.path.join(BUILD, n + ".stl"))}
    check = {}
    xyz, tris, dom, info = meshes["bezel"]
    hull = xyz[tris] * 1e3
    for j, (x0, lab) in enumerate(((33.0, "woofer plane x = +33 mm"), (83.0, "tweeter plane x = +83 mm"))):
        ax = fig.add_subplot(2, 2, 3 + j)
        allc = []
        for n, tri in cad.items():
            s = slice_x(tri, x0 + 1e-3)
            if len(s):
                allc.append(s)
                for seg in s:
                    ax.plot(seg[:, 0], seg[:, 1], color="0.55", lw=0.6)
        hs = slice_x(hull, x0 + 1e-3)
        for seg in hs:
            ax.plot(seg[:, 0], seg[:, 1], color="#c55a11", lw=1.4)
        ax.plot([], [], color="0.55", lw=0.8, label="CAD solids")
        ax.plot([], [], color="#c55a11", lw=1.4, label="BEM hull")
        # distance hull -> nearest CAD section point (should be ~0 for the outer skin)
        cpts = np.vstack([c.reshape(-1, 2) for c in allc])
        hp = hs.reshape(-1, 2)
        dmin = np.sqrt(((hp[:, None, :] - cpts[None, :, :]) ** 2).sum(-1)).min(1)
        check[lab] = dict(max_mm=float(dmin.max()), p95_mm=float(np.percentile(dmin, 95)), median_mm=float(np.median(dmin)))
        ax.set_aspect("equal")
        ax.set_xlabel("y (mm, front = -y)")
        ax.set_ylabel("z (mm)")
        ax.set_title(f"({'cd'[j]}) section, {lab}", fontsize=8.5)
        ax.set_xlim(-62, 55)
        ax.set_ylim(-52, 68)
        if j == 0:
            ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    common.savefig(fig, "a2_a3_bem_hull_mesh_and_cad_check")
    common.save_json(check, "bem_geometry_check.json")
    print(check)


if __name__ == "__main__":
    main()
