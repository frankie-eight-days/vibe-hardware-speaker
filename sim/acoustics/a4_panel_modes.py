#!/usr/bin/env python
"""A4 - Structural (panel) modes of the printed PETG enclosure, solved with CalculiX.

Question
    Which vibration modes of the printed shell fall inside the woofer band (below ~1 kHz in
    particular), how strongly can the woofers excite them, and what ribs/braces would move them?

Pipeline (all scripted, no GUI)
    concept STEP (FreeCAD, mech/concept/speaker_concept.step, units mm)
      -> gmsh OCC: pick the printed solids, fragment them into one conformal body
      -> 2nd-order tetrahedra (C3D10), mesh size H_ASM
      -> our own CalculiX .inp writer (units mm, N, tonne, s, MPa -> frequencies in Hz)
      -> ccx 2.23 (bundled with FreeCAD) *FREQUENCY step (Lanczos/ARPACK, mass-normalised modes)
      -> parse .dat (eigenfrequencies, effective modal mass) and .frd (mode shapes)
      -> excitation indices, figures, JSON/CSV.

Validation
    Fully clamped 100 x 100 x 3 mm PETG plate meshed with the same element type and mesh
    sizes as the enclosure, against Leissa's thin-plate eigenvalues (lambda = 35.985, 73.394,
    108.22, 131.58).

Run:  .venv/bin/python sim/acoustics/a4_panel_modes.py            (all stages, ~35 min on an M4)
      .venv/bin/python sim/acoustics/a4_panel_modes.py validate   (validation only)
      .venv/bin/python sim/acoustics/a4_panel_modes.py post       (figures from cached results)
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

WORK = os.path.join(common.RESULTS, "a4_work")
os.makedirs(WORK, exist_ok=True)
STEP = os.path.join(common.ROOT, "mech", "concept", "speaker_concept.step")

# ----------------------------------------------------------------------------- material
# PETG, isotropic. Units: mm, N, tonne, s -> stress MPa, density t/mm^3.
E_SOLID = 2100.0          # MPa (task value; datasheets 1.9-2.1 GPa for printed PETG in-plane)
NU = 0.38
RHO_SOLID = 1.27e-9       # t/mm^3 (1270 kg/m^3)
INFILL = 0.40             # gyroid infill fraction for thick regions
GA_EXP = 2.0              # Gibson-Ashby, bending-dominated open cell: E*/Es = (rho*/rhos)^2
E_CORE = E_SOLID * INFILL ** GA_EXP      # 336 MPa
RHO_CORE = RHO_SOLID * INFILL            # 508 kg/m^3
SKIN = 4 * 0.45           # 4 perimeters x 0.45 mm line width = solid skin on every surface (mm)
ETA = 0.03                # structural loss factor of printed PETG (assumed 0.02-0.05) -> zeta = eta/2

# ----------------------------------------------------------------------------- acoustics
RHO_AIR, C_AIR = common.RHO, common.C0
VB = 0.85e-3              # m^3 net box volume (mech_envelope.md)
MMS_W, SD_W = 2.6e-3, 16.5e-4             # ND65-8 moving mass (kg), Sd (m^2)
M_WOOFER = 0.181          # kg, ND65-8 (Dayton product page: 0.4 lb)
M_PR = 0.068 + 0.0035     # kg, DMA58-PR (Dayton: 0.15 lb) + ~3.5 g add-mass
M_BATT = 0.189            # kg, Gens ace 2S 5000 mAh

H_ASM = 3.5               # mm, enclosure mesh size (C3D10); convergence checked against H_FINE
H_FINE = 2.8
N_MODES = 30
F_WOOFER_BAND = (60.0, 2500.0)   # woofer passband up to the LR4 crossover
F_FLAG = 1000.0

KEEP_SHAPES = ("asm_solid_free", "asm_infill40_drivers", "asm_infill40_drivers_all_braces")


# ============================================================================ gmsh helpers
def _gmsh_init():
    import gmsh
    if gmsh.isInitialized():
        gmsh.finalize()
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 1)   # deterministic meshes
    return gmsh


def _import_parts(gmsh, names):
    gmsh.model.occ.importShapes(STEP)
    gmsh.model.occ.synchronize()
    keep, rm = {}, []
    for d, t in gmsh.model.getEntities(3):
        n = gmsh.model.getEntityName(d, t).split("/")[-1]
        if n in names:
            keep[n] = t
        else:
            rm.append((d, t))
    gmsh.model.occ.remove(rm, recursive=True)
    gmsh.model.occ.synchronize()
    missing = set(names) - set(keep)
    assert not missing, f"missing solids in STEP: {missing}"
    return keep


def _mesh_and_extract(gmsh, h, hmin=None):
    gmsh.option.setNumber("Mesh.MeshSizeMax", h)
    gmsh.option.setNumber("Mesh.MeshSizeMin", hmin if hmin else 0.3 * h)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)   # straight-sided C3D10: avoids negative Jacobians in thin curved walls
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.model.mesh.generate(3)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    tags, xyz = tags[order], coords.reshape(-1, 3)[order]
    tets, etag = [], []
    for d, t in gmsh.model.getEntities(3):
        types, _, ntags = gmsh.model.mesh.getElements(d, t)
        for ty, nt in zip(types, ntags):
            assert ty == 11, f"unexpected element type {ty}"
            conn = np.asarray(nt, dtype=np.int64).reshape(-1, 10)
            tets.append(conn)
            etag.append(np.full(len(conn), t))
    conn = np.vstack(tets)
    # gmsh tet10 edge-node order (01,12,20,30,32,31) -> Abaqus/ccx C3D10 (01,12,20,03,13,23)
    conn = conn[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    idx = np.searchsorted(tags, conn)
    return dict(xyz=xyz, tets=idx, vol_tag=np.concatenate(etag))


# ============================================================================ geometry builders
def build_plate(h, a=100.0, t=3.0):
    gmsh = _gmsh_init()
    gmsh.model.occ.addBox(0, 0, 0, a, a, t)
    gmsh.model.occ.synchronize()
    m = _mesh_and_extract(gmsh, h)
    gmsh.finalize()
    return m


ASM_PARTS = ("shell_front", "shell_rear", "battery_tray", "end_cap_L", "end_cap_R")


def build_parts(names, h, rib=None):
    """Fragment the named solids into one conformal body (tied joints) and mesh.

    rib: optional list of extra gmsh OCC solids (recommendation what-ifs), each a callable(occ) -> (3, tag).
    """
    gmsh = _gmsh_init()
    keep = _import_parts(gmsh, names)
    objs = [(3, t) for t in keep.values()]
    if rib:
        for make in rib:
            objs.append(make(gmsh.model.occ))
    if len(objs) > 1:
        gmsh.model.occ.fragment(objs[:1], objs[1:])
    gmsh.model.occ.synchronize()
    m = _mesh_and_extract(gmsh, h)
    gmsh.finalize()
    return m


# ---- recommendation what-if geometry (NOT in the CAD; only added to this FE model)
def rib_top_arc(x0, depth=5.0, thick=3.0):
    """Partial ring rib under the top of the front shell at axial position x0: 3 mm thick, 5 mm deep
    (r 39.5-44.5), limited to z >= 28 mm (phi ~40 deg) and y <= 20 mm (stays in front of the UI-board
    rear edge and the seam). At |x| = 40 it clears the display pad (|x| < 23), the knob pad (x > 54),
    the button pad (x < -53), the UI bosses (|x| = 16, 60) and the board itself (z < 35)."""
    def make(occ):
        outer = occ.addCylinder(x0 - thick / 2, 0, 0, thick, 0, 0, 44.5 + 0.05)
        inner = occ.addCylinder(x0 - thick / 2, 0, 0, thick, 0, 0, 44.5 - depth)
        ring, _ = occ.cut([(3, outer)], [(3, inner)])
        win = occ.addBox(x0 - thick, -60.0, 28.0, 2 * thick, 80.0, 30.0)     # y -60..20, z 28..58
        out, _ = occ.intersect(ring, [(3, win)])
        return out[0]
    return make


def tray_gusset(x0, top=True, thick=2.5):
    """Gusset plate (y-z plane) tying the battery-tray top (or bottom) wall to the rear shell:
    x0 +- 1.25 mm, y from the seam region to the shell, |z| from the tray wall (25) to the shell.
    The bottom gussets start at y = 27 to clear the main board (y <= 25)."""
    def make(occ):
        y0 = 24.0 if top else 27.0
        z0, z1 = (24.5, 45.0) if top else (-45.0, -24.5)
        b = occ.addBox(x0 - thick / 2, y0, z0, thick, 44.5 - y0, z1 - z0)
        cyl = occ.addCylinder(x0 - 5, 0, 0, 10, 0, 0, 44.5 + 0.05)
        out, _ = occ.intersect([(3, b)], [(3, cyl)])
        return out[0]
    return make


def spine_plate(occ, thick=1.6):
    """Centre spine plate at x = 0 in the 2 mm gap between the two woofer flanges: from the inner face
    of the baffle land (y = -30.4) back to the battery-tray front wall (y = 15.6), z -20..+24
    (clears the 10.5 mm bulk cap on the main board below and the UI paddle above; baskets are >= 7 mm
    and motors >= 14 mm away in x). Ties the woofer land to the tray/rear shell (front-back brace)."""
    b = occ.addBox(-thick / 2, -30.45, -20.0, thick, 15.6 + 0.05 + 30.45, 44.0)
    return (3, b)


def cap_gusset(side, phi_deg, thick=3.0, depth=5.0):
    """Radial gusset on the inside of an end cap (x = +-101 inward by 5 mm), r 26-44.5 mm, at polar
    angle phi; ties cap and tube end together. The angles in RIBS_CAP (120, 180, 240, 315, -15 deg)
    avoid the tweeter pods (phi 18-62), the five cap-screw bosses (phi 0/90/150/210/270) and the PR
    basket (r < 25)."""
    import math

    def make(occ):
        x0 = 101.0 - depth if side > 0 else -101.0
        b = occ.addBox(x0, -thick / 2, 26.0, depth, thick, 19.0)
        occ.rotate([(3, b)], 0, 0, 0, 1, 0, 0, math.radians(90.0 - phi_deg))
        cyl = occ.addCylinder(x0 - 1, 0, 0, depth + 2, 0, 0, 44.5 + 0.05)
        out, _ = occ.intersect([(3, b)], [(3, cyl)])
        return out[0]
    return make


RIBS_CAP = [cap_gusset(sd, ph) for sd in (-1, 1) for ph in (120.0, 180.0, 240.0, 315.0, -15.0)]


RIBS_TOP = [rib_top_arc(-40.0), rib_top_arc(40.0)]
RIBS_TRAY = [tray_gusset(sx * 30.0, top) for sx in (-1, 1) for top in (True, False)]


# ============================================================================ FE model utilities
FACES = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])
OPP = np.array([3, 2, 1, 0])


def boundary_faces(tets, xyz):
    """Corner triangles of faces that belong to exactly one tet, normals oriented out of the solid."""
    f = tets[:, :4][:, FACES].reshape(-1, 3)
    opp = tets[:, :4][:, OPP].reshape(-1)
    key = np.sort(f, axis=1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    once = cnt[inv.ravel()] == 1
    f, opp = f[once], opp[once]
    p0, p1, p2 = xyz[f[:, 0]], xyz[f[:, 1]], xyz[f[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    cen = (p0 + p1 + p2) / 3.0
    flip = np.einsum("ij,ij->i", n, xyz[opp] - cen) > 0
    f[flip] = f[flip][:, [0, 2, 1]]
    n[flip] *= -1
    area = 0.5 * np.linalg.norm(n, axis=1)
    n = n / (2 * area[:, None])
    return f, n, area, cen


def core_elements(m):
    """Elements whose centroid is deeper than SKIN below every surface -> infill core."""
    from scipy.spatial import cKDTree
    f, n, area, cen = boundary_faces(m["tets"], m["xyz"])
    surf_nodes = np.unique(f)
    # sample surface densely: corner nodes + face centroids
    pts = np.vstack([m["xyz"][surf_nodes], cen])
    tree = cKDTree(pts)
    ecen = m["xyz"][m["tets"][:, :4]].mean(axis=1)
    d, _ = tree.query(ecen)
    return d > SKIN, d


def outer_skin_mask(cen, n):
    """Boundary faces on the outside of the capsule (cylinder skin, flat bottom, end-cap faces)."""
    r = np.hypot(cen[:, 1], cen[:, 2])
    rhat = np.zeros_like(cen)
    rhat[:, 1:] = cen[:, 1:] / np.maximum(r, 1e-9)[:, None]
    skin = (r > 45.6) & (np.einsum("ij,ij->i", n, rhat) > 0.3)
    bottom = (cen[:, 2] < -43.5) & (n[:, 2] < -0.7)
    caps = (np.abs(cen[:, 0]) > 104.0) & (n[:, 0] * np.sign(cen[:, 0]) > 0.7)
    return skin | bottom | caps


def node_patch(xyz, cond):
    return np.where(cond(xyz))[0]


def woofer_mount_nodes(xyz, side):
    """Nodes on the inner flat of the woofer land (y = -30.4) inside the flange footprint."""
    xw = side * 33.0
    rr = np.hypot(xyz[:, 0] - xw, xyz[:, 2])
    return np.where((np.abs(xyz[:, 1] + 30.4) < 0.05) & (rr > 26.4) & (rr < 33.5))[0]


def pr_mount_nodes(xyz, side):
    rr = np.hypot(xyz[:, 1], xyz[:, 2])
    return np.where((np.abs(xyz[:, 0] - side * 105.0) < 0.05) & (rr > 25.0) & (rr < 34.0))[0]


def battery_nodes(xyz):
    """Inside faces of the tray floor/top walls and front wall that touch the pack (foam-coupled)."""
    x, y, z = xyz.T
    inx = np.abs(x) < 59.6
    front = (np.abs(y - 17.6) < 0.05) & (np.abs(z) < 23.0)
    return np.where(inx & front)[0]


# ============================================================================ ccx deck
def write_inp(path, m, fixed=None, masses=None, core=None, n_modes=N_MODES, fmin=1.0, out_nodes=None):
    xyz, tets = m["xyz"], m["tets"]
    L = ["*HEADING", "A4 PETG enclosure modal analysis (units mm N t s MPa)", "*NODE, NSET=NALL"]
    L += [f"{i + 1},{x:.6f},{y:.6f},{z:.6f}" for i, (x, y, z) in enumerate(xyz)]
    groups = {"ESOLID": np.arange(len(tets))}
    if core is not None and core.any():
        groups = {"ESOLID": np.where(~core)[0], "ECORE": np.where(core)[0]}
    for name, ids in groups.items():
        if len(ids) == 0:
            continue
        L.append(f"*ELEMENT, TYPE=C3D10, ELSET={name}")
        L += [f"{e + 1}," + ",".join(str(v + 1) for v in tets[e]) for e in ids]
    mat = {"ESOLID": ("PETG_SOLID", E_SOLID, RHO_SOLID), "ECORE": ("PETG_CORE", E_CORE, RHO_CORE)}
    eid = len(tets)
    mass_sets = []
    if masses:
        for k, (nodes, mtot) in enumerate(masses):
            nodes = np.asarray(nodes)
            if len(nodes) == 0:
                raise RuntimeError(f"mass group {k} has no nodes")
            name = f"EMASS{k}"
            L.append(f"*ELEMENT, TYPE=MASS, ELSET={name}")
            for nd in nodes:
                eid += 1
                L.append(f"{eid},{nd + 1}")
            mass_sets.append((name, mtot / 1000.0 / len(nodes)))   # kg -> tonne, per node
    for name in groups:
        if len(groups[name]) == 0:
            continue
        mn, E, rho = mat[name]
        L += [f"*MATERIAL, NAME={mn}", "*ELASTIC", f"{E},{NU}", "*DENSITY", f"{rho:.6e}",
              f"*SOLID SECTION, ELSET={name}, MATERIAL={mn}"]
    for name, mper in mass_sets:
        L += [f"*MASS, ELSET={name}", f"{mper:.6e}"]
    if fixed is not None and len(fixed):
        L.append("*NSET, NSET=NFIX")
        L += _chunk(fixed + 1)
        L += ["*BOUNDARY", "NFIX,1,3,0."]
    if out_nodes is not None:
        L.append("*NSET, NSET=NOUT")
        L += _chunk(np.asarray(out_nodes) + 1)
    L += ["*STEP", "*FREQUENCY, SOLVER=SPOOLES", f"{n_modes},{fmin},20000."]
    L += [f"*NODE FILE, NSET={'NOUT' if out_nodes is not None else 'NALL'}", "U", "*END STEP"]
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def _chunk(ids, k=12):
    ids = list(map(int, ids))
    return [",".join(map(str, ids[i:i + k])) for i in range(0, len(ids), k)]


def run_ccx(job):
    env = dict(os.environ, OMP_NUM_THREADS="4", CCX_NPROC_EQUATION_SOLVER="4")
    t0 = time.time()
    r = subprocess.run([common.CCX, "-i", job], cwd=WORK, env=env, capture_output=True, text=True)
    dt = time.time() - t0
    if r.returncode != 0 or "ERROR" in r.stdout:
        tail = "\n".join(r.stdout.splitlines()[-30:])
        raise RuntimeError(f"ccx failed for {job}:\n{tail}")
    return dt


def parse_dat(job):
    lines = open(os.path.join(WORK, job + ".dat")).read().splitlines()
    freqs, emass = [], {}
    sec = None
    for ln in lines:
        s = ln.strip()
        if "E I G E N V A L U E   O U T P U T" in s:
            sec = "eig"; continue
        if "E F F E C T I V E   M O D A L   M A S S" in s:
            sec = "em"; continue
        if "P A R T I C I P A T I O N" in s or "T O T A L" in s:
            sec = None if "P A R T" in s else sec
            continue
        parts = s.split()
        if not parts or not parts[0].isdigit():
            if s.startswith("TOTAL"):
                sec = None
            continue
        if sec == "eig" and len(parts) >= 4:
            freqs.append(float(parts[3]))
        elif sec == "em" and len(parts) >= 7:
            emass[int(parts[0])] = [float(v) for v in parts[1:7]]
    return np.array(freqs), emass


def parse_frd(job, n_nodes):
    """Displacement blocks of a CalculiX .frd -> array (n_modes, n_nodes, 3) (NaN where not output)."""
    modes, cur = [], None
    with open(os.path.join(WORK, job + ".frd")) as fh:
        for ln in fh:
            if ln.startswith(" -4  DISP"):
                cur = np.full((n_nodes, 3), np.nan, dtype=np.float32)
                modes.append(cur)
                continue
            if cur is not None:
                if ln.startswith(" -1"):
                    nd = int(ln[3:13])
                    cur[nd - 1] = (float(ln[13:25]), float(ln[25:37]), float(ln[37:49]))
                elif ln.startswith(" -3"):
                    cur = None
    return np.array(modes)


def solve(job, m, **kw):
    write_inp(os.path.join(WORK, job + ".inp"), m, **kw)
    dt = run_ccx(job)
    f, em = parse_dat(job)
    out_nodes = kw.get("out_nodes")
    U = parse_frd(job, len(m["xyz"]))
    for ext in (".frd", ".sta", ".cvg", ".12d", ".inp"):      # keep disk use small (.inp is regenerated)
        p = os.path.join(WORK, job + ext)
        if os.path.exists(p):
            os.remove(p)
    return dict(f=f, emass=em, U=U, t=dt, out_nodes=out_nodes)


# ============================================================================ validation
LEISSA_CCCC = [35.985, 73.394, 73.394, 108.22, 131.58, 132.20]   # lambda = w a^2 sqrt(rho h / D)


def validate():
    a, t = 100.0, 3.0
    D = E_SOLID * t ** 3 / (12 * (1 - NU ** 2))
    f_ex = np.array(LEISSA_CCCC) / (2 * np.pi * a ** 2) * np.sqrt(D / (RHO_SOLID * t))
    rows = []
    for h in (H_ASM, 2.5, 1.5):
        m = build_plate(h, a, t)
        x, y = m["xyz"][:, 0], m["xyz"][:, 1]
        fixed = np.where((x < 1e-6) | (x > a - 1e-6) | (y < 1e-6) | (y > a - 1e-6))[0]
        r = solve(f"val_plate_h{h:g}", m, fixed=fixed, n_modes=6, fmin=1.0)
        err = (r["f"][:6] - f_ex) / f_ex * 100
        rows.append(dict(h_mm=h, n_nodes=len(m["xyz"]), n_tets=len(m["tets"]), elems_through_t=t / h,
                         f_fe=r["f"][:6].tolist(), err_pct=err.tolist(), ccx_s=r["t"]))
        print(f"plate h={h}: nodes {len(m['xyz'])}, f1 {r['f'][0]:.1f} vs {f_ex[0]:.1f} Hz "
              f"({err[0]:+.2f} %), max |err| modes 1-6 {np.abs(err).max():.2f} %, ccx {r['t']:.1f} s")
    res = dict(case="fully clamped square plate 100 x 100 x 3 mm, PETG, C3D10",
               reference="Leissa (1969) NASA SP-160, CCCC square plate, thin-plate theory",
               lambda_ref=LEISSA_CCCC, f_exact_hz=f_ex.tolist(), runs=rows)
    common.save_json(res, "a4_validation.json")
    return res


# ============================================================================ excitation indices
def indices(m, f, U, woofer_nodes):
    """Per-mode excitation / radiation indices (see README A4 'Method').

    U: mode shapes mass-normalised in model units (t, mm); converted to SI normalisation.
    R_p: panel net volume displacement / woofer volume displacement at modal resonance, driven by
         box pressure (lumped box, valid below ~800 Hz).
    R_f: same, driven by the woofer motor reaction force on the land (woofers in phase).
    D_f: peak skin displacement / cone displacement at resonance, force path.
    """
    zeta = ETA / 2
    fcs, n, area, cen = boundary_faces(m["tets"], m["xyz"])
    sk = outer_skin_mask(cen, n)
    fcs, n, area = fcs[sk], n[sk], area[sk] * 1e-6        # m^2
    out = []
    # ccx normalises phi^T M phi = 1 in model units (t mm^2 = 1e-3 kg m^2); SI normalisation (1 kg m^2)
    # therefore needs phi_SI[m] = phi_mm * 1e-3 * sqrt(1000)
    scale = 1e-3 * np.sqrt(1000.0)
    for k, (fk, Uk) in enumerate(zip(f, U)):
        Us = np.nan_to_num(Uk.astype(float)) * scale
        un = np.einsum("ij,ij->i", Us[fcs].mean(axis=1), n)
        Vm = float(np.sum(un * area))                      # m^3 per unit modal coordinate
        w = 2 * np.pi * fk
        R_p = RHO_AIR * C_AIR ** 2 / VB * Vm ** 2 / (2 * zeta * w ** 2)
        wy = [np.nanmean(Us[nodes, 1]) for nodes in woofer_nodes]
        phi_w_sym = abs(wy[0] + wy[1]) if len(wy) == 2 else abs(wy[0])
        phi_w_anti = abs(wy[0] - wy[1]) if len(wy) == 2 else 0.0
        R_f = abs(Vm) * MMS_W * phi_w_sym / (2 * zeta * 2 * SD_W)
        umax = float(np.nanmax(np.abs(un)))
        D_f = umax * MMS_W * max(phi_w_sym, phi_w_anti) / (2 * zeta)
        D_p = umax * RHO_AIR * C_AIR ** 2 / VB * 2 * SD_W * abs(Vm) / (2 * zeta * w ** 2)
        out.append(dict(mode=k + 1, f_hz=float(fk), Vm_m3_per_q=Vm,
                        R_p_db=float(20 * np.log10(R_p + 1e-30)), R_f_db=float(20 * np.log10(R_f + 1e-30)),
                        D_p_db=float(20 * np.log10(D_p + 1e-30)), D_f_db=float(20 * np.log10(D_f + 1e-30)),
                        woofer_land_phi_y_sym=float(phi_w_sym), woofer_land_phi_y_anti=float(phi_w_anti)))
    return out


F_FRF = np.logspace(np.log10(50.0), np.log10(2500.0), 500)


def frf(m, f, U, woofer_nodes, eta=ETA):
    """Modal-superposition estimate of the shell's net outward volume velocity relative to the
    woofers' cone volume velocity (both woofers in phase, same excursion X).

    Two drives, added with their phases:
      pressure path: lumped box pressure p = -(rho c^2 / Vb) * 2 Sd X acting on the inner skin
                     (generalised force p * Vm_k; valid while the box is acoustically small, < ~800 Hz);
      force path   : inertial reaction of each cone on its frame, F_y = -w^2 Mms X (outward = -y),
                     applied to the woofer mounting land (generalised force F_y * mean(phi_y)).
    Returns |H| (panel / woofers) for each drive separately and combined, on F_FRF.
    Upper-bound flavour: no fluid loading, no joint/gasket damping beyond eta, rigid driver frames.
    """
    scale = 1e-3 * np.sqrt(1000.0)
    fcs, n, area, cen = boundary_faces(m["tets"], m["xyz"])
    sk = outer_skin_mask(cen, n)
    fcs, n, area = fcs[sk], n[sk], area[sk] * 1e-6
    w = 2 * np.pi * F_FRF
    X = 1.0
    vol_ref = 2 * SD_W * X
    Hp = np.zeros_like(w, dtype=complex)
    Hf = np.zeros_like(w, dtype=complex)
    for fk, Uk in zip(f, U):
        Us = np.nan_to_num(Uk.astype(float)) * scale
        Vk = np.sum(np.einsum("ij,ij->i", Us[fcs].mean(axis=1), n) * area)
        wk = 2 * np.pi * fk
        den = wk ** 2 - w ** 2 + 1j * eta * wk ** 2
        Fp = -(RHO_AIR * C_AIR ** 2 / VB) * vol_ref * Vk
        Ff = sum(-(w ** 2) * MMS_W * X * np.mean(Us[nodes, 1]) for nodes in woofer_nodes)
        Hp += Vk * Fp / den
        Hf += Vk * Ff / den
    return dict(f=F_FRF, Hp=np.abs(Hp) / vol_ref, Hf=np.abs(Hf) / vol_ref, H=np.abs(Hp + Hf) / vol_ref)


def static_wall_compliance(res_rows):
    """Sum over modes of Vm^2/w^2 (m^5/N) vs air compliance Vb/(rho c^2): fraction of box compliance."""
    c_wall = sum(r["Vm_m3_per_q"] ** 2 / (2 * np.pi * r["f_hz"]) ** 2 for r in res_rows)
    return c_wall / (VB / (RHO_AIR * C_AIR ** 2))


def where_moves(m, Uk):
    """Label the region with the largest displacement (for the table)."""
    mag = np.linalg.norm(np.nan_to_num(Uk), axis=1)
    i = int(np.nanargmax(mag))
    x, y, z = m["xyz"][i]
    phi = np.degrees(np.arctan2(z, -y))
    part = "end cap" if abs(x) > 101 else ("rear shell" if y > 24 else ("battery tray" if (abs(x) < 62 and 15 < y < 45 and abs(z) < 26) else "front shell"))
    return f"{part} (x={x:.0f}, phi={phi:.0f} deg)"


# ============================================================================ cases
def run_case(name, parts, h, fixed_fn=None, masses_fn=None, infill=False, rib=None, n_modes=N_MODES):
    t0 = time.time()
    m = build_parts(parts, h, rib=rib)
    tmesh = time.time() - t0
    core = None
    if infill:
        core, _ = core_elements(m)
    fixed = fixed_fn(m["xyz"]) if fixed_fn else None
    masses = masses_fn(m["xyz"]) if masses_fn else None
    wn = [woofer_mount_nodes(m["xyz"], s) for s in (-1, 1)]
    wn = [w for w in wn if len(w)]
    nfree = 0 if fixed is not None and len(fixed) else 6
    r = solve(name, m, fixed=fixed, masses=masses, core=core, n_modes=n_modes + nfree, fmin=1.0)
    f, U = r["f"], r["U"]
    if len(U) == len(f) + 6:   # ccx printed only the modes above fmin; .frd may still hold rigid modes
        U = U[6:]
    assert len(U) == len(f), (len(U), len(f))
    flex = f > 5.0             # free-free: drop rigid-body modes (ccx normally omits them below fmin)
    f, U = f[flex], U[flex]
    idx = indices(m, f, U, wn) if wn else []
    for row, Uk in zip(idx, U):
        row["max_motion_at"] = where_moves(m, Uk)
    info = dict(case=name, parts=list(parts), h_mm=h, n_nodes=int(len(m["xyz"])), n_tets=int(len(m["tets"])),
                dof=int(3 * len(m["xyz"])), infill_core_elements=int(core.sum()) if core is not None else 0,
                fixed_nodes=int(len(fixed)) if fixed is not None else 0,
                lumped_masses_kg=[float(mm) for _, mm in masses] if masses else [],
                mesh_s=round(tmesh, 1), ccx_s=round(r["t"], 1), freqs_hz=f.tolist(), modes=idx,
                wall_compliance_fraction=static_wall_compliance(idx) if idx else None)
    if wn:
        H = frf(m, f, U, wn)
        info["frf_db"] = dict(f_hz=H["f"].tolist(), pressure=(20 * np.log10(H["Hp"] + 1e-30)).tolist(),
                              force=(20 * np.log10(H["Hf"] + 1e-30)).tolist(),
                              total=(20 * np.log10(H["H"] + 1e-30)).tolist())
    print(f"[{name}] nodes {len(m['xyz'])}, mesh {tmesh:.0f} s, ccx {r['t']:.0f} s; first modes: "
          + ", ".join(f"{x:.0f}" for x in f[:8]) + " Hz")
    if name in KEEP_SHAPES:      # mode shapes kept only for the rendered / visualised cases (disk)
        np.savez_compressed(os.path.join(WORK, name + "_modes.npz"), xyz=m["xyz"].astype(np.float32),
                            tets=m["tets"][:, :4].astype(np.int32), f=f, U=U[:10].astype(np.float32),
                            core=core if core is not None else np.zeros(len(m["tets"]), bool))
    return info


def masses_drivers(with_battery):
    def fn(xyz):
        g = [(woofer_mount_nodes(xyz, -1), M_WOOFER), (woofer_mount_nodes(xyz, 1), M_WOOFER),
             (pr_mount_nodes(xyz, -1), M_PR), (pr_mount_nodes(xyz, 1), M_PR)]
        if with_battery:
            g.append((battery_nodes(xyz), M_BATT))
        return g
    return fn


def fix_seam_and_ends(xyz):
    return np.where((np.abs(xyz[:, 1] - 24.0) < 0.05) | (np.abs(xyz[:, 0]) > 100.95))[0]


def fix_rear_screws(xyz):
    """Rear shell held only at its screw points: 4 seam screws (x = +-50, top/bottom seam lips) and
    the two cap-screw bosses per end (phi = 150, 210 deg at r = 42)."""
    x, y, z = xyz.T
    sel = np.zeros(len(xyz), bool)
    for sx in (-1, 1):
        for sz in (-1, 1):
            sel |= (np.abs(y - 24.0) < 0.05) & (np.hypot(x - sx * 50, z - sz * 41.0) < 5.0)
        for phi in (150.0, 210.0):
            py, pz = -np.cos(np.radians(phi)) * 42.0, np.sin(np.radians(phi)) * 42.0
            sel |= (np.abs(np.abs(x) - 101.0) < 0.05) & (np.sign(x) == sx) & (np.hypot(y - py, z - pz) < 4.0)
    return np.where(sel)[0]


def fix_cap_rim(xyz):
    """End cap clamped where it bears on the tube end and the 5 axial screws (r > 41 mm on the inner face)."""
    r = np.hypot(xyz[:, 1], xyz[:, 2])
    return np.where((np.abs(np.abs(xyz[:, 0]) - 101.0) < 0.05) & (r > 41.0))[0]


def masses_pr_cap(xyz):
    return [(pr_mount_nodes(xyz, 1), M_PR)]


def run_all():
    res = {}
    full = ASM_PARTS
    res["asm_solid_free"] = run_case("asm_solid_free", full, H_ASM)
    res["asm_solid_free_fine"] = run_case("asm_solid_free_fine", full, H_FINE, n_modes=12)
    res["asm_infill40_free"] = run_case("asm_infill40_free", full, H_ASM, infill=True)
    res["asm_infill40_drivers"] = run_case("asm_infill40_drivers", full, H_ASM, infill=True,
                                           masses_fn=masses_drivers(False))
    res["asm_infill40_drivers_batt"] = run_case("asm_infill40_drivers_batt", full, H_ASM, infill=True,
                                                masses_fn=masses_drivers(True))
    # bounding cases: individual parts
    res["rear_edges_clamped"] = run_case("rear_edges_clamped", ("shell_rear", "battery_tray"), H_ASM,
                                         fixed_fn=fix_seam_and_ends, n_modes=12)
    res["rear_screws_only"] = run_case("rear_screws_only", ("shell_rear", "battery_tray"), H_ASM,
                                       fixed_fn=fix_rear_screws, n_modes=12)
    res["front_edges_clamped"] = run_case("front_edges_clamped", ("shell_front",), H_ASM, infill=True,
                                          fixed_fn=fix_seam_and_ends, masses_fn=lambda xyz: [
                                              (woofer_mount_nodes(xyz, -1), M_WOOFER),
                                              (woofer_mount_nodes(xyz, 1), M_WOOFER)], n_modes=12)
    res["endcap_rim_clamped_PR"] = run_case("endcap_rim_clamped_PR", ("end_cap_R",), H_FINE,
                                            fixed_fn=fix_cap_rim, masses_fn=masses_pr_cap, n_modes=8)
    common.save_json(res, "a4_modes_raw.json")
    return res


def run_ribs(res):
    """Recommendation what-ifs: ribs/gussets added in our FE model only (CAD untouched)."""
    res["asm_infill40_drivers_rib_top"] = run_case(
        "asm_infill40_drivers_rib_top", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(False), rib=RIBS_TOP)
    res["asm_infill40_drivers_rib_top_tray"] = run_case(
        "asm_infill40_drivers_rib_top_tray", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(False),
        rib=RIBS_TOP + RIBS_TRAY)
    res["asm_infill40_drivers_batt_rib_top_tray"] = run_case(
        "asm_infill40_drivers_batt_rib_top_tray", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(True),
        rib=RIBS_TOP + RIBS_TRAY)
    res["asm_infill40_drivers_spine"] = run_case(
        "asm_infill40_drivers_spine", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(False),
        rib=[spine_plate])
    res["asm_infill40_drivers_spine_top_tray"] = run_case(
        "asm_infill40_drivers_spine_top_tray", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(False),
        rib=[spine_plate] + RIBS_TOP + RIBS_TRAY)
    res["asm_infill40_drivers_batt_spine_top_tray"] = run_case(
        "asm_infill40_drivers_batt_spine_top_tray", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(True),
        rib=[spine_plate] + RIBS_TOP + RIBS_TRAY)
    res["asm_infill40_drivers_all_braces"] = run_case(
        "asm_infill40_drivers_all_braces", ASM_PARTS, H_ASM, infill=True, masses_fn=masses_drivers(False),
        rib=[spine_plate] + RIBS_TOP + RIBS_TRAY + RIBS_CAP)
    common.save_json(res, "a4_modes_raw.json")
    return res


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("validate", "all"):
        validate()
    if stage in ("solve", "all"):
        r = run_all()
        run_ribs(r)
    if stage in ("ribs",):
        r = json.load(open(os.path.join(common.RESULTS, "a4_modes_raw.json")))
        run_ribs(r)
    if stage in ("post", "all", "ribs"):
        import a4_post
        a4_post.main()
