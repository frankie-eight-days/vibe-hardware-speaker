"""Acoustic hull of the speaker capsule for BEM (A2, A3), built with gmsh/OpenCASCADE.

The hull is the *outside* surface the sound sees. It is rebuilt from the parameter block of the
FreeCAD concept model (mech/concept/speaker_concept.py, parsed with common.cad_params()), using the
same construction formulas, so a CAD parameter change flows through to the BEM. Only exterior
features are modelled:

  * Ø95 body, 210 mm long, 3 mm fillets on the end edges, flat bottom at z = -44.5 mm;
  * end caps with the DMA58-PR flanges standing 3 mm proud (56 mm rounded square); the PR
    diaphragm is a flat piston of the PR Sd, flush with the flange face;
  * woofer tunnels: Ø53 bore through the baffle land from the skin down to the front of the
    woofer surround (flange plane - 3.5 mm), with the 3 mm 45° mouth chamfer; the woofer cone is a
    flat piston of the ND65-8 Sd at the bottom of the tunnel;
  * tweeter mounts: variant "bezel" = the CAD's Ø36 raised boss with the 3 mm conical bezel, faceplate
    flush at R = 47.5 mm, axis 40° up; variant "waveguide" = faceplate sunk 10 mm along its axis at the
    throat of an oblate-spheroid (OS) flare cut into the skin, in a capsule 10 mm longer (220 mm) so the
    deeper pod would fit; the dome is a flat piston of the OT19NC00-04 Sd (4.5 cm², Ø24 mm);
  * the volume knob (Ø26 × 13 mm on top at x = +70 mm), seated on the skin.

Left out (acoustically small or flush): the perforated grille (0.8 mm, flush in its recess), display lens,
buttons, mic hole, USB pocket, screw heads, the 0.3 mm faceplate seat gap and the cone/dome curvature.

Coordinates as in docs/mech_envelope.md: x along the capsule (+x right when facing the speaker), -y = front,
+z = up, origin at the capsule centre. Built in mm; mesh nodes are returned in metres.
"""
import math

import numpy as np

import common

# Driver radiating areas (m^2) -> piston radii (mm)
SD_WOOFER = 16.5e-4     # ND65-8 (drivers.json)
SD_PR = 14.5e-4         # DMA58-PR (drivers.json)
SD_TWEETER = 4.5e-4     # OT19NC00-04 datasheet (Vifa/Tymphany rev 1.0: Sd 4.5 cm², eff. diameter 2.4 cm)
R_WOOFER = math.sqrt(SD_WOOFER / math.pi) * 1e3
R_PR = math.sqrt(SD_PR / math.pi) * 1e3
R_TWEETER = math.sqrt(SD_TWEETER / math.pi) * 1e3

# physical-group ids (become bempp domain indices)
TAG_RIGID = 1
TAGS = {"woofer_L": 11, "woofer_R": 12, "pr_L": 21, "pr_R": 22, "tweeter_L": 31, "tweeter_R": 32}

WG_DEPTH = 10.0         # waveguide variant: throat depth below the skin (mm)
WG_THETA = 60.0         # OS waveguide asymptotic half-angle (deg)
WG_EXTRA_LEN = 10.0     # capsule made 10 mm longer for the waveguide variant


def layout(variant="bezel", tunnel=True):
    """Key positions/axes in mm (used by geometry, field points and README)."""
    p = common.cad_params()
    R = p["D_out"] / 2
    Ri = R - p["wall"]
    x_end = p["L_total"] / 2 + (WG_EXTRA_LEN / 2 if variant == "waveguide" else 0.0)
    w_land_y = -math.sqrt(Ri ** 2 - (p["w_flange"] / 2 + p["w_clear"]) ** 2)
    ea = math.radians(p["t_elev"])
    ph = math.radians(p["t_phi"])
    t_axis = np.array([0.0, -math.cos(ea), math.sin(ea)])
    face = {}
    for side, sx in (("L", -1), ("R", 1)):
        c = np.array([sx * p["t_x"], -math.cos(ph) * p["t_face_r"], math.sin(ph) * p["t_face_r"]])
        if variant == "waveguide":
            c = c - t_axis * WG_DEPTH
        face[side] = c
    return dict(p=p, R=R, Ri=Ri, x_end=x_end, x_pr_face=x_end + p["pr_proud"], w_land_y=w_land_y,
                w_piston_y=w_land_y - p["w_surround_h"], w_x=p["w_x"], t_axis=t_axis, t_face=face,
                z_bottom=p["flat_bottom_z"], variant=variant, tunnel=tunnel)


def build(variant="bezel", tunnel=True, h_max=6.0, h_min=None, msh_path=None, verbose=False, h_tweeter=None):
    """Build the hull, mesh its surface and return (vertices [m], triangles, domain_index, info).

    variant: "bezel" (as designed) or "waveguide" (10 mm-deep OS flare, 220 mm capsule).
    tunnel:  False replaces the woofer tunnels by pistons flush with the skin (diagnostic for A3).
    h_tweeter: if set, local element size (mm) within 25 mm of each tweeter centre, graded to h_max at 50 mm
             (resolves the Ø24 dome piston, the 3 mm bezel lip and the waveguide flare; see the README).
    h_max:   maximum element edge length in mm (set to <= lambda/6 at the top frequency).
    """
    import gmsh
    L = layout(variant, tunnel)
    p, R = L["p"], L["R"]
    x_end = L["x_end"]
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1 if verbose else 0)
    gmsh.model.add("hull")
    occ = gmsh.model.occ

    # ---- body: filleted cylinder with a flat bottom
    body = occ.addCylinder(-x_end, 0, 0, 2 * x_end, 0, 0, R)
    occ.synchronize()
    circ = [e[1] for e in gmsh.model.getBoundary([(3, body)], combined=False, oriented=False, recursive=False)]
    edges = []
    for s in circ:
        for e in gmsh.model.getBoundary([(2, s)], combined=False, oriented=False):
            if e[1] not in edges:
                edges.append(e[1])
    body = occ.fillet([body], edges, [p["edge_fillet"]])[0][1]
    cutter = occ.addBox(-300, -300, -300, 600, 600, 300 + p["flat_bottom_z"])
    body = occ.cut([(3, body)], [(3, cutter)])[0][0][1]

    # ---- PR flanges, 3 mm proud on the end faces (rounded square)
    adds = []
    for sx in (-1, 1):
        x0 = x_end if sx > 0 else -x_end - p["pr_proud"]
        b = occ.addBox(x0, -p["pr_flange"] / 2, -p["pr_flange"] / 2, p["pr_proud"], p["pr_flange"], p["pr_flange"])
        occ.synchronize()
        ed = []
        # x-parallel edges of the box -> fillet the 4 corners of the square
        for e in gmsh.model.getEntities(1):
            bb = gmsh.model.getBoundingBox(1, e[1])
            if abs(bb[3] - bb[0] - p["pr_proud"]) < 1e-6 and abs(bb[4] - bb[1]) < 1e-6 and abs(bb[5] - bb[2]) < 1e-6:
                if x0 - 1e-6 <= bb[0] <= x0 + 1e-6:
                    ed.append(e[1])
        b = occ.fillet([b], ed, [p["pr_flange_r"]])[0][1]
        adds.append((3, b))

    # ---- tweeter boss (bezel variant)
    lay_t = L["t_axis"]
    if variant == "bezel":
        for side in ("L", "R"):
            c = L["t_face"][side]
            base = c - lay_t * 8.0
            hgt = lay_t * (p["t_wg_len"] + 8.0)
            adds.append((3, occ.addCylinder(*base, *hgt, p["t_wg_boss_r"])))
    # ---- knob (seated on the skin)
    adds.append((3, occ.addCylinder(p["knob_x"], 0, R - 6.0, 0, 0, p["knob_h"] + 7.0, p["knob_d"] / 2)))
    body = occ.fuse([(3, body)], adds)[0][0][1]

    # ---- cuts: woofer tunnels + chamfers, tweeter bezel cup / waveguide
    cuts = []
    yb = L["w_piston_y"]
    for sx in (-1, 1):
        xw = sx * L["w_x"]
        if tunnel:
            cuts.append((3, occ.addCylinder(xw, yb, 0, 0, -(80 + yb), 0, p["w_hole_d"] / 2)))
            # 45° chamfer: cone r=26.5 at y=-R+3 growing outward
            y0 = -R + p["w_chamfer"]
            cuts.append((3, occ.addCone(xw, y0, 0, 0, -30, 0, p["w_hole_d"] / 2, p["w_hole_d"] / 2 + 30)))
    for side in ("L", "R"):
        c = L["t_face"][side]
        if variant == "bezel":
            r0 = p["t_face_d"] / 2 + 0.3
            cuts.append((3, occ.addCone(*c, *(lay_t * p["t_wg_len"]), r0, p["t_wg_d"] / 2)))
            cuts.append((3, occ.addCylinder(*(c + lay_t * p["t_wg_len"]), *(lay_t * 30), p["t_wg_d"] / 2)))
        else:
            # OS profile r(z) = sqrt(r0^2 + (z tan th)^2), revolved about the tweeter axis
            r0 = p["t_face_d"] / 2 + 0.3
            tt = math.tan(math.radians(WG_THETA))
            zs = np.linspace(0, WG_DEPTH + 12.0, 23)
            rs = np.sqrt(r0 ** 2 + (zs * tt) ** 2)
            cuts.append((3, _revolve_profile(occ, c, lay_t, zs, rs)))
    body = occ.cut([(3, body)], cuts)[0][0][1]
    occ.synchronize()

    # ---- imprint piston discs on their faces (flush-woofer diagnostic: split the skin with a cylinder)
    tool = []
    for sx, side in ((-1, "L"), (1, "R")):
        xw = sx * L["w_x"]
        if tunnel:
            tool.append((2, occ.addDisk(xw, yb, 0, R_WOOFER, R_WOOFER, zAxis=[0, -1, 0], xAxis=[1, 0, 0])))
        else:
            tool.append((3, occ.addCylinder(xw, -R - 5, 0, 0, 25, 0, R_WOOFER)))
        tool.append((2, occ.addDisk(sx * L["x_pr_face"], 0, 0, R_PR, R_PR, zAxis=[sx, 0, 0], xAxis=[0, 1, 0])))
        c = L["t_face"][side]
        tool.append((2, occ.addDisk(*c, R_TWEETER, R_TWEETER, zAxis=list(lay_t), xAxis=[1, 0, 0])))
    out, omap = occ.fragment([(3, body)], tool)
    occ.synchronize()
    # keep only volumes inside the original body (drop tool-cylinder pieces outside it)
    vols = [e for e in out if e[0] == 3]
    keep = [v for v in omap[0] if v[0] == 3]
    for v in vols:
        if v not in keep:
            occ.remove([v], recursive=True)
    occ.synchronize()
    bnd = [s[1] for s in gmsh.model.getBoundary(keep, combined=True, oriented=False)]
    for e in gmsh.model.getEntities(2):
        if e[1] not in bnd:
            up, _ = gmsh.model.getAdjacencies(2, e[1])
            if len(up) == 0:
                occ.remove([e], recursive=True)
    occ.synchronize()

    vol = gmsh.model.getEntities(3)
    bnd = [s[1] for s in gmsh.model.getBoundary(vol, combined=True, oriented=False)]
    # identify piston faces by centroid / area
    groups = {k: [] for k in TAGS}
    rigid = []
    targets = {}
    for sx, side in ((-1, "L"), (1, "R")):
        xw = sx * L["w_x"]
        targets["woofer_" + side] = (np.array([xw, yb if tunnel else -R + R_WOOFER ** 2 / (8 * R), 0.0]), SD_WOOFER * 1e6)
        targets["pr_" + side] = (np.array([sx * L["x_pr_face"], 0, 0]), SD_PR * 1e6)
        targets["tweeter_" + side] = (L["t_face"][side], SD_TWEETER * 1e6)
    for s in bnd:
        com = np.array(occ.getCenterOfMass(2, s))
        area = occ.getMass(2, s)
        bb = np.array(gmsh.model.getBoundingBox(2, s))
        ext = np.max(bb[3:] - bb[:3])
        hit = None
        for k, (ctr, a) in targets.items():
            tol = 1.5 if (tunnel or not k.startswith("woofer")) else 3.0
            if np.linalg.norm(com - ctr) < tol and abs(area - a) / a < (0.03 if (tunnel or not k.startswith('woofer')) else 0.06) and ext < 1.05 * 2 * math.sqrt(a / math.pi):
                hit = k
        if hit:
            groups[hit].append(s)
        else:
            rigid.append(s)
    for k, ss in groups.items():
        assert len(ss) == 1, f"piston {k}: found faces {ss}"
        gmsh.model.addPhysicalGroup(2, ss, TAGS[k], name=k)
    gmsh.model.addPhysicalGroup(2, rigid, TAG_RIGID, name="rigid")

    # ---- mesh
    if h_tweeter and h_tweeter < h_max:
        pts = [occ.addPoint(*L["t_face"][sd]) for sd in ("L", "R")]
        occ.synchronize()
        fd = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(fd, "PointsList", pts)
        ft = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(ft, "InField", fd)
        gmsh.model.mesh.field.setNumber(ft, "SizeMin", h_tweeter)
        gmsh.model.mesh.field.setNumber(ft, "SizeMax", h_max)
        gmsh.model.mesh.field.setNumber(ft, "DistMin", 25.0)
        gmsh.model.mesh.field.setNumber(ft, "DistMax", 50.0)
        gmsh.model.mesh.field.setAsBackgroundMesh(ft)
    gmsh.option.setNumber("Mesh.MeshSizeMax", h_max)
    gmsh.option.setNumber("Mesh.MeshSizeMin", h_min if h_min else min(2.0, h_max / 2.5))
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 6)    # >= 6 elements per 2*pi of curvature
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.optimize("Laplace2D")
    if msh_path:
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.write(msh_path)
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    xyz = coords.reshape(-1, 3)
    idx = {t: i for i, t in enumerate(node_tags)}
    tris, dom = [], []
    for dim, ptag in gmsh.model.getPhysicalGroups(2):
        for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, ptag):
            types, _, enodes = gmsh.model.mesh.getElements(2, ent)
            for t, en in zip(types, enodes):
                assert t == 2, "only linear triangles expected"
                tri = np.array([idx[n] for n in en]).reshape(-1, 3)
                tris.append(tri)
                dom.append(np.full(len(tri), ptag))
    tris = np.vstack(tris)
    dom = np.concatenate(dom)
    # surface area check & mesh stats
    v = xyz[tris]
    edge = np.concatenate([np.linalg.norm(v[:, a] - v[:, b], axis=1) for a, b in ((0, 1), (1, 2), (2, 0))])
    areas = 0.5 * np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1)
    info = dict(variant=variant, tunnel=tunnel, h_max_mm=h_max, n_tri=int(len(tris)), n_nodes=int(len(xyz)),
                edge_max_mm=float(edge.max()), edge_mean_mm=float(edge.mean()), area_m2=float(areas.sum() * 1e-6),
                piston_areas_cm2={k: float(areas[dom == t].sum() * 1e-2) for k, t in TAGS.items()},
                x_end_mm=x_end)
    gmsh.finalize()
    # orient all triangles outward (bempp needs consistent outward normals)
    xyz_m = xyz * 1e-3
    tris = _orient_outward(xyz_m, tris)
    return xyz_m, tris, dom, info


def _revolve_profile(occ, c, axis, zs, rs):
    """Solid of revolution of profile r(z) about `axis` through point c (z measured along axis)."""
    axis = np.asarray(axis, float)
    u = np.cross(axis, [1.0, 0.0, 0.0])
    u /= np.linalg.norm(u)
    pts = [occ.addPoint(*(c + axis * zs[0]))]
    prof = []
    for z, r in zip(zs, rs):
        prof.append(occ.addPoint(*(c + axis * z + u * r)))
    top = occ.addPoint(*(c + axis * zs[-1]))
    l1 = occ.addLine(pts[0], prof[0])
    sp = occ.addSpline(prof)
    l2 = occ.addLine(prof[-1], top)
    l3 = occ.addLine(top, pts[0])
    loop = occ.addCurveLoop([l1, sp, l2, l3])
    surf = occ.addPlaneSurface([loop])
    out = occ.revolve([(2, surf)], *c, *axis, 2 * math.pi)
    return [e for e in out if e[0] == 3][0][1]


def _orient_outward(xyz, tris):
    """Make triangle orientation consistent and outward (divergence-theorem volume > 0)."""
    from collections import defaultdict, deque
    n = len(tris)
    edge_map = defaultdict(list)
    for i, t in enumerate(tris):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_map[tuple(sorted((t[a], t[b])))].append(i)
    tris = tris.copy()
    seen = np.zeros(n, bool)
    for seed in range(n):
        if seen[seed]:
            continue
        seen[seed] = True
        q = deque([seed])
        while q:
            i = q.popleft()
            t = tris[i]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                for j in edge_map[tuple(sorted((t[a], t[b])))]:
                    if j == i or seen[j]:
                        continue
                    tj = tris[j]
                    # consistent orientation: neighbour traverses the shared edge in the opposite direction
                    same = any((tj[c] == t[a] and tj[(c + 1) % 3] == t[b]) for c in range(3))
                    if same:
                        tris[j] = tj[[0, 2, 1]]
                    seen[j] = True
                    q.append(j)
    v = xyz[tris]
    vol = np.sum(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2]))) / 6.0
    if vol < 0:
        tris = tris[:, [0, 2, 1]]
    return tris


def check_closed(tris):
    """Every edge must be shared by exactly two triangles (closed, manifold surface)."""
    from collections import Counter
    cnt = Counter()
    for t in tris:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt[tuple(sorted((t[a], t[b])))] += 1
    bad = [e for e, k in cnt.items() if k != 2]
    return len(bad)


if __name__ == "__main__":
    import sys
    var = sys.argv[1] if len(sys.argv) > 1 else "bezel"
    h = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    xyz, tris, dom, info = build(var, h_max=h, msh_path=f"/tmp/hull_{var}.msh", verbose=False)
    print(info)
    print("open edges:", check_closed(tris))
