"""Analysis 1: switching hot-loop inductance with FastHenry on the real copper.

Method (per loop, per board):
  1. Rasterise the two loop nets (e.g. PVDD and GND) on all 4 layers at 0.1 mm, join layers
     at every via / plated pad of that net.
  2. Find the shortest copper path IC(+) -> HF cap -> IC(-). No path = loop open in copper.
  3. Keep the copper within R_HALO of that path (all layers) plus the IC/cap area. That keeps
     the plane spreading and the L2 image currents and drops far-away copper.
  4. Write a FastHenry PEEC mesh: one node per 0.1 mm cell, x/y segments between neighbours
     (w = pitch, h = copper thickness), vias as vertical bars with barrel-equivalent sigma.
     The IC pin lands are equipotential (.equiv, flip-chip bars / die), the HF cap is an ideal
     short across its pads (its body ESL is added separately), the port is IC(+) - IC(-).
  5. L = Im(Z)/w at 100 MHz (ringing band) and 1 MHz.
Also: switch-node copper area per layer, its capacitance to the nearest plane, the partial
inductance of each SW run to its inductor, and V_overshoot = L * I_sw / t_r.

Run:  python fh_loops.py [board_tag ...]     (default: hybrid autoroute)
"""
import os
import re
import subprocess
import sys
import time

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

from pl_common import (DIEL, EPS0, FASTHENRY, LAYERS, T_CU, VIA_PLATING, WORK, Z, Grid, load,
                       save_json, dilate)

PITCH = 0.1
R_HALO = 2.0          # mm kept around the current path
FREQS = (1e6, 1e8)

# Switch current at commutation (A) and its source.
LOOPS = [
    dict(name="boost", title="Boost U901 (SW-VOUT-C914-PGND)", pos=("U901", "8"), neg=("U901", "6"),
         cap="C914", sw=("U901", "7"), ind=("L901", "2"), I=8.0, v_rail=18.0, v_abs=23.0,
         src="I = ILIM_SW 8.0 A typ (SLVSDA7E p.5, 80.6 kOhm); SW abs max 23 V (p.4)"),
    dict(name="buck", title="Buck U951 (VIN-C953-GND)", pos=("U951", "3"), neg=("U951", "4"),
         cap="C953", sw=("U951", "5"), ind=("L951", "1"), I=1.23, v_rail=8.4, v_abs=33.0,
         src="I = 1.23 A peak at 0.8 A load (spec_power 4.2.3); SW abs max 32 V DC, 33 V <10 ns (SLUSEA4D p.5)"),
    dict(name="chg_pmid", title="Charger U701 buck leg (PMID-C707-GND)", pos=("U701", "29"),
         neg=("U701", "27"), cap="C707", sw=("U701", "28"), ind=("L701", "1"), I=6.1, v_rail=15.0,
         v_abs=30.0, src="I = 6.1 A peak, 15 V/2.5 A charge-while-play (spec_power 2.3); SW1 abs max 30 V (SLUSDV2C p.7)"),
    dict(name="chg_sys", title="Charger U701 boost leg (SYS-C716-GND)", pos=("U701", "25"),
         neg=("U701", "27"), cap="C716", sw=("U701", "26"), ind=("L701", "2"), I=6.1, v_rail=8.4,
         v_abs=23.0, src="I = 6.1 A (same inductor current); SW2 abs max 23 V (SLUSDV2C p.7)"),
]
T_RISE = (2e-9, 5e-9)   # no rise time in SLVSDA7E/SLUSEA4D/SLUSDV2C: bracket, see README
ESL_0603 = 0.5e-9       # typical 0603 MLCC body ESL (assumption, Murata/Samsung curves)


# ----------------------------------------------------------------------------------------
class NetMesh:
    """Rasterised copper of a set of nets with 3-D connectivity."""

    def __init__(self, b, nets, grid, others=False):
        self.b, self.g, self.nets = b, grid, list(nets)
        self.mask = {}            # (net, layer) -> bool
        for n in self.nets:
            for L in LAYERS:
                self.mask[(n, L)] = b.raster(grid, L, [n])
        # resolve overlaps from the >= 2 px track fattening: a contested cell goes to the net whose
        # true polygon covers it; if neither does, to the thinner (smaller) net so thin traces survive
        if len(self.nets) == 2:
            a, c = self.nets
            for L in LAYERS:
                ov = self.mask[(a, L)] & self.mask[(c, L)]
                if ov.any():
                    pa = b.raster(grid, L, [a], tracks_min_px=0)
                    pc = b.raster(grid, L, [c], tracks_min_px=0)
                    thin_a = self.mask[(a, L)].sum() <= self.mask[(c, L)].sum()
                    keep_a = ov & (pa | (~pc & thin_a))
                    self.mask[(a, L)] &= ~(ov & ~keep_a)
                    self.mask[(c, L)] &= ~keep_a
        if others:   # all other copper as floating conductors (eddy / image currents)
            for L in LAYERS:
                m = b.raster(grid, L, None, tracks_min_px=0)
                for n in self.nets:
                    m &= ~dilate(self.mask[(n, L)], 1)
                self.mask[("__other__", L)] = m
        self._index()

    def _index(self):
        g = self.g
        self.id = {}
        n0 = 0
        coords = []
        for key, m in self.mask.items():
            idx = -np.ones(m.shape, dtype=np.int64)
            jj, ii = np.nonzero(m)
            idx[jj, ii] = np.arange(n0, n0 + len(jj))
            self.id[key] = idx
            coords.append((key, jj, ii))
            n0 += len(jj)
        self.N = n0
        self.coords = coords

    def via_links(self):
        """(net, x, y, [layers], drill) for vias and plated holes of the mesh nets."""
        out = []
        for v in self.b.vias:
            if v["net"] in self.nets:
                out.append((v["net"], v["x"], v["y"], v["layers"], v["drill"]))
        for p in self.b.pads:
            if p["net"] in self.nets and p["drill"] > 0 and len(p["layers"]) > 1:
                out.append((p["net"], p["x"], p["y"], p["layers"], max(p["drill"], 0.3)))
        return out

    def graph(self, keep=None):
        """Sparse adjacency (in-plane 4-neighbour + vias). keep: 2-D bool mask restricting cells."""
        rows, cols, w = [], [], []
        g = self.g
        for (n, L), idx in self.id.items():
            a = idx if keep is None else np.where(keep, idx, -1)
            for sl1, sl2 in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                             ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
                u, v = a[sl1].ravel(), a[sl2].ravel()
                ok = (u >= 0) & (v >= 0)
                rows.append(u[ok]); cols.append(v[ok]); w.append(np.full(ok.sum(), g.p))
        vl = []
        for (n, x, y, lays, d) in self.via_links():
            i, j = g.ij(x, y)
            if keep is not None and not keep[j, i]:
                continue
            ids = [self.id[(n, L)][j, i] for L in LAYERS if L in lays]
            ids = [k for k in ids if k >= 0]
            for a_, b_ in zip(ids[:-1], ids[1:]):
                rows.append(np.array([a_])); cols.append(np.array([b_])); w.append(np.array([0.3]))
                vl.append((a_, b_, d))
        r, c, ww = np.concatenate(rows), np.concatenate(cols), np.concatenate(w)
        A = sparse.coo_matrix((ww, (r, c)), shape=(self.N, self.N)).tocsr()
        return A + A.T, vl

    def cells_in_box(self, net, layer, bb):
        idx = self.id[(net, layer)]
        m = self.g.box_mask(bb) & (idx >= 0)
        return idx[m]

    def node_xyz(self):
        g = self.g
        X = np.zeros(self.N); Y = np.zeros(self.N); Zc = np.zeros(self.N)
        L_of = np.empty(self.N, dtype=object)
        for (n, L), jj, ii in self.coords:
            ids = self.id[(n, L)][jj, ii]
            X[ids] = g.x0 + (ii + 0.5) * g.p
            Y[ids] = g.y0 + (jj + 0.5) * g.p
            Zc[ids] = Z[L]
            L_of[ids] = L
        return X, Y, Zc, L_of


def shortest(A, src_ids, dst_ids):
    if len(src_ids) == 0 or len(dst_ids) == 0:
        return None
    s = int(src_ids[len(src_ids) // 2])
    dist, pred = csgraph.dijkstra(A, indices=s, return_predecessors=True)
    d = dist[dst_ids]
    if not np.isfinite(d).any():
        return None
    t = int(dst_ids[np.argmin(d)])
    path = [t]
    while path[-1] != s:
        path.append(int(pred[path[-1]]))
    return path[::-1], float(d.min())


def pad_bb(p, shrink=0.0):
    x0, y0, x1, y1 = p["bbox"]
    return [x0 + shrink, y0 + shrink, x1 - shrink, y1 - shrink]


# ----------------------------------------------------------------------------------------
def write_fasthenry(path, M, keepcells, vlinks, equivs, port, title):
    X, Y, Zc, L_of = M.node_xyz()
    keep = np.zeros(M.N, bool)
    keep[keepcells] = True
    lines = [f"* {title}", ".units mm", ".default sigma=5.8e4 nwinc=1 nhinc=1"]
    node_lines_at = len(lines)
    e = 0
    segs = []
    for (n, L), idx in M.id.items():
        a = np.where(np.isin(idx, keepcells), idx, -1)
        for sl1, sl2 in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                         ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
            u, v = a[sl1].ravel(), a[sl2].ravel()
            ok = (u >= 0) & (v >= 0)
            for uu, vv in zip(u[ok], v[ok]):
                lines.append(f"E{e} N{uu} N{vv} w={M.g.p:.4f} h={T_CU[L]:.4f}")
                segs.append((uu, vv, L))
                e += 1
    for a_, b_, d in vlinks:
        if keep[a_] and keep[b_]:
            asq = 1.12 * d                      # square bar with the GMD of a thin tube of dia d
            sig = 5.8e4 * (np.pi * d * VIA_PLATING) / asq ** 2
            lines.append(f"E{e} N{a_} N{b_} w={asq:.4f} h={asq:.4f} sigma={sig:.4g}")
            segs.append((a_, b_, "via"))
            e += 1
    used = set()
    for uu, vv, _ in segs:
        used.add(uu); used.add(vv)
    used |= {port[0], port[1]}
    eqs = []
    for grp in equivs:
        g2 = [k for k in grp if k in used]
        eqs.append(g2)
    lines[node_lines_at:node_lines_at] = [f"N{k} x={X[k]:.4f} y={Y[k]:.4f} z={Zc[k]:.4f}" for k in sorted(used)]
    lines = [l for l in lines if not l.startswith(".equiv")]
    for grp in eqs:
        if len(grp) > 1:
            for c0 in range(1, len(grp), 40):
                lines.append(".equiv " + " ".join(f"N{k}" for k in [grp[0]] + grp[c0:c0 + 40]))
    lines.append(f".external N{port[0]} N{port[1]}")
    lines.append(f".freq fmin={FREQS[0]:g} fmax={FREQS[1]:g} ndec=0.5")
    lines.append(".end")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(used), e, segs


def run_fasthenry(inp, suffix, grids=False):
    d = os.path.dirname(inp)
    cmd = [FASTHENRY, "-S", suffix, "-p", "off"] + (["-d", "grids"] if grids else []) + [os.path.basename(inp)]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
    dt = time.time() - t0
    out = os.path.join(d, f"Zc{suffix}.mat")
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    txt = open(out).read()
    res = {}
    for blk in txt.split("Impedance matrix for frequency = ")[1:]:
        f = float(blk.split()[0])
        m = re.search(r"([-+]?[\d.eE+-]+)\s*([-+]\s*[\d.eE+-]+)j", blk.split("\n", 1)[1])
        R, X = float(m.group(1)), float(m.group(2).replace(" ", ""))
        res[f] = dict(R=R, L=X / (2 * np.pi * f))
    return res, dt


# ----------------------------------------------------------------------------------------
def sw_node_stats(b, net, grid):
    """Area per layer and capacitance to the nearest plane (any net) and to GND."""
    gnd = b.net("GND")
    out = {"area_mm2": {}, "C_gnd_pF": 0.0, "C_any_pF": 0.0}
    masks = {L: b.raster(grid, L, [net], tracks_min_px=0) for L in LAYERS}
    allcu = {L: b.raster(grid, L, None, tracks_min_px=0) for L in LAYERS}
    gm = {L: b.raster(grid, L, [gnd], tracks_min_px=0) for L in LAYERS}
    a_px = grid.p ** 2
    order = LAYERS
    for k, L in enumerate(order):
        m = masks[L]
        out["area_mm2"][L] = float(m.sum() * a_px)
        if not m.any():
            continue
        for dirn in (-1, +1):
            # walk to the nearest copper layer in this direction, cell by cell
            remaining = m.copy()
            h = 0.0
            kk = k
            while remaining.any():
                kk += dirn
                if kk < 0 or kk >= len(order):
                    break
                up, lo = (order[kk - 1], order[kk]) if dirn > 0 else (order[kk], order[kk + 1])
                hh, er = DIEL[(up, lo)]
                h += hh
                other = allcu[order[kk]] & ~masks[order[kk]]
                hit = remaining & other
                hit_g = remaining & gm[order[kk]]
                c_cell = EPS0 * er * (a_px * 1e-6) / (h * 1e-3)
                out["C_any_pF"] += hit.sum() * c_cell * 1e12
                out["C_gnd_pF"] += hit_g.sum() * c_cell * 1e12
                remaining &= ~(hit | (masks[order[kk]]))
    # perimeter fringing estimate on the outer-layer copper (edge extension h/2, L1 over L2)
    m1 = masks["F.Cu"]
    per = (np.abs(np.diff(m1.astype(int), axis=0)).sum() + np.abs(np.diff(m1.astype(int), axis=1)).sum()) * grid.p
    out["perimeter_F_mm"] = float(per)
    out["C_fringe_pF"] = float(EPS0 * 4.4 * (per * H_PP_HALF() * 1e-6) / (DIEL[("F.Cu", "In1.Cu")][0] * 1e-3) * 1e12)
    out["area_total_mm2"] = float(sum(out["area_mm2"].values()))
    return out


def H_PP_HALF():
    return DIEL[("F.Cu", "In1.Cu")][0] / 2


# ----------------------------------------------------------------------------------------
def analyse_loop(b, spec, outdir, grids=False):
    """spec: pos/neg = port pads at the IC; cap = HF cap shorted across its pads, or
    short = ((ref, pad), (ref, pad)) for an explicit far-end short (PDN paths)."""
    g = Grid.from_bbox(b.bbox, spec.get("pitch", PITCH))
    halo = spec.get("halo", R_HALO)
    pp, pn = b.pad(*spec["pos"]), b.pad(*spec["neg"])
    netp, netn = pp["net"], pn["net"]
    if "short" in spec:
        capp, capn = [b.pad(*spec["short"][0])], [b.pad(*spec["short"][1])]
        cap = capp + capn
    else:
        cap = b.pads_of(spec["cap"])
        capp = [p for p in cap if p["net"] == netp]
        capn = [p for p in cap if p["net"] == netn]
    M = NetMesh(b, [netp, netn], g, others=True)
    A, vl = M.graph()
    ids = lambda net, pad: M.cells_in_box(net, "F.Cu", pad_bb(pad))
    res = {"loop": spec["name"], "board": b.name, "nets": [netp, netn]}
    r1 = shortest(A, ids(netp, pp), ids(netp, capp[0]))
    r2 = shortest(A, ids(netn, capn[0]), ids(netn, pn))
    if r1 is None or r2 is None:
        res["status"] = "OPEN: no copper path " + ("IC+ -> cap" if r1 is None else "cap -> IC-")
        return res
    path = r1[0] + r2[0]
    res["path_len_mm"] = r1[1] + r2[1]
    X, Y, Zc, L_of = M.node_xyz()
    # 2-D region: path halo + component box
    reg = np.zeros((g.ny, g.nx), bool)
    for k in path:
        i, j = g.ij(X[k], Y[k])
        reg[j, i] = True
    reg = dilate(reg, int(round(halo / g.p)))
    bbs = [pad_bb(p) for p in [pp, pn] + cap]
    core = [min(q[0] for q in bbs), min(q[1] for q in bbs), max(q[2] for q in bbs), max(q[3] for q in bbs)]
    reg |= g.box_mask(core, grow=1.0)
    # restrict and keep the component that holds the port (both nets joined by the cap short)
    A2, vl2 = M.graph(keep=reg)
    eq_p, eq_n = list(ids(netp, pp)), list(ids(netn, pn))
    eq_c = list(ids(netp, capp[0])) + list(ids(netn, capn[0]))
    # join the equivalence groups in the graph for the component search
    extra = []
    for grp in (eq_p, eq_n, eq_c):
        extra += [(grp[0], k) for k in grp[1:]]
    if extra:
        e = np.array(extra)
        J = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=A2.shape).tocsr()
        A2 = A2 + J + J.T
    ncomp, lab = csgraph.connected_components(A2, directed=False)
    keepcells = np.nonzero(lab == lab[eq_p[0]])[0]
    # plus floating copper (other nets, loop-net copper not joined inside the region)
    floating = np.nonzero(lab != lab[eq_p[0]])[0]
    keepcells = np.union1d(keepcells, floating)
    # only cells inside the region
    inreg = np.array([reg[int((Y[k] - g.y0) / g.p), int((X[k] - g.x0) / g.p)] for k in keepcells])
    keepcells = keepcells[inreg]
    if lab[eq_n[0]] != lab[eq_p[0]]:
        res["status"] = "OPEN inside halo region"
        return res
    inp = os.path.join(outdir, f"{b.name}_{spec['name']}.inp")
    nn, ns, segs = write_fasthenry(inp, M, keepcells, vl2, [eq_p, eq_n, eq_c], (eq_p[0], eq_n[0]),
                                   f"{b.name} {spec['title']}")
    res.update(nodes=nn, segments=ns)
    print(f"  {b.name}/{spec['name']}: {nn} nodes, {ns} segments, path {res['path_len_mm']:.1f} mm", flush=True)
    z, dt = run_fasthenry(inp, f"_{b.name}_{spec['name']}", grids=grids)
    res["fasthenry_s"] = dt
    res["L_nH"] = {f"{f:g}": z[f]["L"] * 1e9 for f in z}
    res["R_mohm"] = {f"{f:g}": z[f]["R"] * 1e3 for f in z}
    Lhf = z[max(z)]["L"]
    res["status"] = "ok"
    # layer use along the path
    res["path_layers"] = {L: int(sum(1 for k in path if L_of[k] == L)) for L in LAYERS}
    res["path_vias"] = int(sum(1 for a_, b_ in zip(path[:-1], path[1:]) if L_of[a_] != L_of[b_]))
    I = spec.get("I", 0.0)
    res["V_overshoot"] = {f"{t * 1e9:g}ns": {"pcb": Lhf * I / t, "pcb+ESL": (Lhf + ESL_0603) * I / t}
                          for t in T_RISE}
    # store mesh for current-density plots
    np.savez_compressed(os.path.join(outdir, f"{b.name}_{spec['name']}_mesh.npz"),
                        X=X[keepcells], Y=Y[keepcells], Z=Zc[keepcells], ids=keepcells,
                        path_x=X[path], path_y=Y[path], path_z=Zc[path])
    return res


def analyse_sw_run(b, ic, ind, outdir, name):
    """Partial self-inductance of the SW copper from the IC pin to the inductor pad."""
    g = Grid.from_bbox(b.bbox, PITCH)
    pi, pl = b.pad(*ic), b.pad(*ind)
    net = pi["net"]
    M = NetMesh(b, [net], g)
    A, vl = M.graph()
    s = M.cells_in_box(net, "F.Cu", pad_bb(pi))
    t = M.cells_in_box(net, "F.Cu", pad_bb(pl))
    r = shortest(A, s, t)
    if r is None:
        return {"run": name, "status": "OPEN"}
    ncomp, lab = csgraph.connected_components(A, directed=False)
    keep = np.nonzero(lab == lab[s[0]])[0]
    inp = os.path.join(outdir, f"{b.name}_{name}.inp")
    nn, ns, _ = write_fasthenry(inp, M, keep, vl, [list(s), list(t)], (s[0], t[0]), f"{b.name} {name}")
    z, dt = run_fasthenry(inp, f"_{b.name}_{name}")
    return {"run": name, "status": "ok", "path_len_mm": r[1], "nodes": nn, "segments": ns,
            "L_partial_nH": z[max(z)]["L"] * 1e9, "R_mohm_1MHz": z[min(z)]["R"] * 1e3}


def main(tags):
    outdir = os.path.join(WORK, "fasthenry")
    os.makedirs(outdir, exist_ok=True)
    allres = {}
    for tag in tags:
        b = load(tag)
        allres[tag] = {"loops": [], "sw": []}
        for spec in LOOPS:
            r = analyse_loop(b, spec, outdir, grids=True)
            print(f"  -> {r.get('status')} L={r.get('L_nH')}", flush=True)
            allres[tag]["loops"].append(r)
            g = Grid.from_bbox(b.bbox, 0.05)
            st = sw_node_stats(b, b.pad(*spec["sw"])["net"], g)
            st["net"] = b.pad(*spec["sw"])["net"]
            st["loop"] = spec["name"]
            ib = b.pad(*spec["ind"])["bbox"]
            st["ind_pad_mm2"] = (ib[2] - ib[0]) * (ib[3] - ib[1])
            st["area_excl_ind_pad_mm2"] = st["area_total_mm2"] - st["ind_pad_mm2"]
            sw = analyse_sw_run(b, spec["sw"], spec["ind"], outdir, spec["name"] + "_swrun")
            st.update(sw)
            allres[tag]["sw"].append(st)
            print(f"  SW {st['net']}: {st['area_total_mm2']:.1f} mm2, C_gnd {st['C_gnd_pF']:.1f} pF, "
                  f"run L {st.get('L_partial_nH')}", flush=True)
        save_json(allres[tag], f"fh_loops_{tag}.json")
    return allres


if __name__ == "__main__":
    main(sys.argv[1:] or ["hybrid", "autoroute"])
