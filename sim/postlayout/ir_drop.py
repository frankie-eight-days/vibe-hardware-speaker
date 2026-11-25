"""Analysis 4a: DC IR drop on the real copper (2-D finite differences per layer + via barrels).

Each net is rasterised on every copper layer of the board (4 or 6, pl_common.stackup), so a rail
may live on any layer. Neighbouring cells are joined by the sheet conductance sigma*t (1 oz outer
35 um, 0.5 oz inner 15.2 um, JLC04161H-7628 / JLC06161H-1080B), layers by via barrels
(sigma*pi*d*t_plating/dz, 20 um plating) and plated pads. The source pad is held at 0 V; each
load pad draws its current spread over its land. Copper at 25 C (+0.39 %/K).
Outputs per case: drop at each load, I^2R, hot-spot current density (A/mm2) and max via current,
hot-spot J excludes the terminal pads and via lands (singular there on a grid). Via barrels
connect to every cell of their annular ring.

Run: python ir_drop.py TAG [TAG ...]
"""
import sys

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph
from scipy.sparse.linalg import spsolve

from pl_common import SIGMA_CU, VIA_PLATING, Grid, load, save_json, savefig, style

MU0 = 4e-7 * np.pi
TAS_PVDD = ["15", "16", "27", "28"]          # TAS5805M PVDD pins (SLASEH5D Table 5-1)
# (name, net, source [(ref, pads)], loads [(ref, pads, A)], pitch mm, note)
CASES = [
    ("PVDD", "PVDD", [("U901", ["8"])], [("U301", TAS_PVDD, 2.7), ("U401", TAS_PVDD, 2.7)], 0.1,
     "boost VOUT bar -> both amps at 2.7 A peak each"),
    ("VSYS", "VSYS", [("U701", ["25"])], [("L901", ["1"], 7.0), ("U951", ["3"], 0.35)], 0.1,
     "charger SYS pin -> boost inductor 7.0 A (40 W out at 6 V, spec_power 4.1.4) + buck 0.35 A"),
    ("+3V3", "+3V3", [("L951", ["2"])], [("U101", ["2"], 0.5)], 0.1,
     "buck inductor -> ESP32 pin 2 at 500 mA peak"),
    ("PACK_P", "PACK_P", [("J801", ["2"])], [("F801", ["1"], 7.0)], 0.1, "XT30 + -> fuse, 7 A"),
    ("VBAT_PACK", "VBAT_PACK", [("F801", ["2"])], [("Q701", ["5"], 7.0)], 0.1, "fuse -> ship FET drain, 7 A"),
    ("CHG_BAT", "CHG_BAT", [("Q701", ["1", "2", "3"])], [("U701", ["22", "23"], 7.0)], 0.1,
     "ship FET source -> BQ25792 BAT pins, 7 A"),
    ("BATT_N", "BATT_N", [("J801", ["1"])], [("Q801", ["1", "2", "3"], 7.0)], 0.1, "XT30 - -> Q801 source, 7 A"),
    ("PROT_D", "PROT_D", [("Q801", ["5"])], [("Q802", ["5"], 7.0)], 0.1, "common drain Q801 -> Q802, 7 A"),
    ("GND_batt", "GND", [("Q802", ["1", "2", "3"])], [("U901", ["6"], 7.0)], 0.2,
     "battery return: boost PGND -> Q802 source, 7 A"),
]


def solve_case(b, case):
    name, net_s, src, loads, p, note = case
    LAYERS, T_CU, Z = b.layers, b.t_cu, b.z
    net = b.net(net_s)
    pads_all = [b.pad(r, n) for r, ns in src for n in ns] + [b.pad(r, n) for r, ns, _ in loads for n in ns]
    if net_s == "GND":
        xs = [q["x"] for q in pads_all]; ys = [q["y"] for q in pads_all]
        bb = [min(xs) - 15, b.bbox[1], max(xs) + 15, b.bbox[3]]
    else:
        bb = b.bbox
    g = Grid.from_bbox(bb, p)
    mask = {L: b.raster(g, L, [net]) for L in LAYERS}
    idx, n0 = {}, 0
    for L in LAYERS:
        a = -np.ones(mask[L].shape, np.int64)
        jj, ii = np.nonzero(mask[L])
        a[jj, ii] = np.arange(n0, n0 + len(jj)); n0 += len(jj)
        idx[L] = a
    N = n0
    rows, cols, gv, kind = [], [], [], []
    for L in LAYERS:
        a = idx[L]
        gs = SIGMA_CU * T_CU[L] * 1e-3
        for s1, s2, d in (((slice(None), slice(0, -1)), (slice(None), slice(1, None)), "x"),
                          ((slice(0, -1), slice(None)), (slice(1, None), slice(None)), "y")):
            u, v = a[s1].ravel(), a[s2].ravel()
            ok = (u >= 0) & (v >= 0)
            rows.append(u[ok]); cols.append(v[ok]); gv.append(np.full(ok.sum(), gs))
            kind.append(np.full(ok.sum(), f"{L}{d}", dtype=object))
    vias = [(v["x"], v["y"], v["layers"], v["drill"]) for v in b.vias if v["net"] == net]
    vias += [(q["x"], q["y"], q["layers"], max(q["drill"], 0.3)) for q in b.pads
             if q["net"] == net and q["drill"] > 0 and len(q["layers"]) > 1]
    via_id = []            # per via link: via index (for per-via current)
    excl = {L: np.zeros(mask[L].shape, bool) for L in LAYERS}
    xc, yc = g.xc(), g.yc()
    for vi, (x, y, lays, d) in enumerate(vias):
        rad = max(d / 2 + 0.15, g.p)          # barrel lands on its annular ring (dia ~ drill + 0.3)
        i0, j0 = g.ij(x - rad, y - rad); i1, j1 = g.ij(x + rad, y + rad)
        sub = (xc[None, i0:i1 + 1] - x) ** 2 + (yc[j0:j1 + 1, None] - y) ** 2 <= rad ** 2
        jj, ii = np.nonzero(sub); jj += j0; ii += i0
        if len(jj) == 0:
            jj, ii = np.array([g.ij(x, y)[1]]), np.array([g.ij(x, y)[0]])
        Ls = [L for L in LAYERS if L in lays and (idx[L][jj, ii] >= 0).any()]
        for L in Ls:
            excl[L][jj, ii] = True
        for La, Lb in zip(Ls[:-1], Ls[1:]):
            a_, b_ = idx[La][jj, ii], idx[Lb][jj, ii]
            ok = (a_ >= 0) & (b_ >= 0)
            if not ok.any():
                continue
            gvia = SIGMA_CU * np.pi * d * 1e-3 * VIA_PLATING * 1e-3 / (abs(Z[La] - Z[Lb]) * 1e-3)
            rows.append(a_[ok]); cols.append(b_[ok]); gv.append(np.full(ok.sum(), gvia / ok.sum()))
            kind.append(np.full(ok.sum(), "via", dtype=object))
            via_id.append(np.full(ok.sum(), vi * len(LAYERS) + LAYERS.index(La)))
    r, c, w = np.concatenate(rows), np.concatenate(cols), np.concatenate(gv)
    kd = np.concatenate(kind)
    A = sparse.coo_matrix((w, (r, c)), shape=(N, N)).tocsr()
    A = A + A.T
    Gm = sparse.diags(np.asarray(A.sum(axis=1)).ravel()) - A

    def pad_cells(q):
        out = []
        for L in q["layers"]:
            m = g.box_mask(q["bbox"]) & (idx[L] >= 0)
            out += list(idx[L][m])
        return np.array(out, np.int64)
    srcc = np.unique(np.concatenate([pad_cells(b.pad(rf, n)) for rf, ns in src for n in ns]))
    res = {"case": name, "net": net, "note": note, "pitch_mm": p, "nodes": int(N)}
    if len(srcc) == 0:
        res["status"] = "source pad has no copper"; return res
    ncomp, lab = csgraph.connected_components(A, directed=False)
    live = np.isin(lab, np.unique(lab[srcc]))
    I = np.zeros(N)
    res["loads"] = []
    open_loads = []
    for rf, ns, amp in loads:
        cc = np.unique(np.concatenate([pad_cells(b.pad(rf, n)) for n in ns]))
        dead = [n for n in ns if not live[pad_cells(b.pad(rf, n))].any()]
        if dead and len(dead) < len(ns):
            open_loads.append(f"{rf} pins {','.join(dead)} not connected (current carried by the others)")
        if len(cc) == 0 or not live[cc].any():
            open_loads.append(rf); res["loads"].append({"ref": rf, "I_A": amp, "status": "OPEN"}); continue
        cc = cc[live[cc]]
        I[cc] -= amp / len(cc)
        res["loads"].append({"ref": rf, "I_A": amp, "cells": cc})
    free = np.nonzero(live & ~np.isin(np.arange(N), srcc))[0]
    V = np.zeros(N)
    if len(free):
        V[free] = spsolve(Gm[free][:, free].tocsc(), I[free])
    for ld in res["loads"]:
        if "cells" in ld:
            ld["V_drop_mV"] = float(-1e3 * V[ld.pop("cells")].mean())
            ld["status"] = "ok"
    # edge currents
    ie = w * (V[r] - V[c])
    res["P_loss_mW"] = float(1e3 * np.sum(w * (V[r] - V[c]) ** 2))
    res["status"] = "ok" if not open_loads else "OPEN: " + ", ".join(open_loads)
    # per-layer current density (A/mm2) and sheet current K (A/mm)
    Kmap = np.zeros((g.ny, g.nx))
    res["J_max_A_mm2"] = {}
    for L in LAYERS:
        a = idx[L]
        jx = np.zeros(a.shape); jy = np.zeros(a.shape)
        for d, arr in (("x", jx), ("y", jy)):
            sel = kd == f"{L}{d}"
            if not sel.any():
                continue
            rr, ie_ = r[sel], ie[sel]
            # map node -> (j, i)
            jj, ii = np.nonzero(a >= 0)
            pos = np.empty(N, np.int64); pos[:] = -1
            lin = jj * g.nx + ii
            pos[a[jj, ii]] = lin
            np.add.at(arr.ravel(), pos[rr], np.abs(ie_))
        K = np.hypot(jx, jy) / g.p            # A per mm of width (sheet current)
        J = K / T_CU[L]                       # A/mm2
        ex = excl[L].copy()
        for q in pads_all:
            if L in q["layers"]:
                ex |= g.box_mask(q["bbox"], grow=0.2)
        Jh = np.where(ex, 0.0, J)
        if (a >= 0).any():
            jm = float(Jh.max()); jj_, ii_ = np.unravel_index(np.argmax(Jh), J.shape)
            res["J_max_A_mm2"][L] = {"J": jm, "x": float(g.x0 + (ii_ + .5) * g.p), "y": float(g.y0 + (jj_ + .5) * g.p)}
        Kmap += K
    Itot = sum(amp for _, _, amp in loads)
    vsel = kd == "via"
    if vsel.any():
        vid = np.concatenate(via_id)
        tot = np.zeros(vid.max() + 1)
        np.add.at(tot, vid, ie[vsel])
        res["via_I_max_A"] = float(np.abs(tot).max())
        res["vias"] = len(vias)
    else:
        res["via_I_max_A"] = 0.0; res["vias"] = 0
    res["R_eff_mohm"] = float(1e3 * res["P_loss_mW"] * 1e-3 / Itot ** 2)
    return res, Kmap, g


def figure(allres):
    plt = style()
    tags = list(allres)
    names = [c[0] for c in CASES]
    fig, axs = plt.subplots(len(names), len(tags), figsize=(6.5, 1.25 * len(names)), squeeze=False)
    from matplotlib.colors import LogNorm
    norm = LogNorm(1e-3, 5)
    for ci, t in enumerate(tags):
        b = allres[t]["board"]
        for ri, n in enumerate(names):
            ax = axs[ri, ci]
            res, K, g = allres[t]["maps"][n]
            ax.imshow(np.where(K > 0, K, np.nan), extent=g.extent(), cmap="inferno", norm=norm,
                      interpolation="nearest")
            ax.set_xlim(b.bbox[0], b.bbox[2]); ax.set_ylim(b.bbox[3], b.bbox[1])
            ax.set_facecolor("#eeeeee"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            drops = [l.get("V_drop_mV") for l in res.get("loads", [])]
            dtxt = "/".join("open" if d is None else f"{d:.0f}" for d in drops)
            ax.set_title(f"{t} {n}: {dtxt} mV, {res.get('P_loss_mW', 0):.0f} mW", fontsize=7, pad=1.5)
    sm = plt.cm.ScalarMappable(norm=norm, cmap="inferno")
    fig.subplots_adjust(hspace=0.45, wspace=0.04, right=0.88)
    cax = fig.add_axes([0.9, 0.3, 0.015, 0.4])
    fig.colorbar(sm, cax=cax).set_label("sheet current, A/mm (all layers)", fontsize=8)
    cax.tick_params(labelsize=7)
    savefig(fig, "ir_drop_maps")


def main(tags):
    allres = {}
    for t in tags:
        b = load(t)
        out, maps = [], {}
        for case in CASES:
            r = solve_case(b, case)
            if isinstance(r, tuple):
                r, K, g = r
                maps[case[0]] = (r, K, g)
            else:
                maps[case[0]] = (r, np.zeros((2, 2)), Grid(0, 0, 2, 2, 1))
            out.append(r)
            print(t, r["case"], r["status"], [(l["ref"], round(l.get("V_drop_mV", -1), 1)) for l in r.get("loads", [])],
                  f"P={r.get('P_loss_mW', 0):.0f} mW", {k: round(v["J"], 1) for k, v in r.get("J_max_A_mm2", {}).items()},
                  "via", round(r.get("via_I_max_A", 0), 2), flush=True)
        save_json(out, f"ir_drop_{t}.json")
        allres[t] = {"board": b, "maps": maps, "res": out}
    figure(allres)
    return allres


if __name__ == "__main__":
    main(sys.argv[1:] or ["hybrid", "autoroute"])
