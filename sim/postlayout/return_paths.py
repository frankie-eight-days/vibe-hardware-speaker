"""Analysis 2: reference-plane (return-path) check for fast nets.

For every track segment of a fast net, sample every 0.1 mm and look at the nearest reference
layer in a strip of +/- max(3h, w/2 + h) across the trace (h = dielectric height to that layer;
a microstrip return current density ~ 1/(1+(x/h)^2) puts ~80 % inside +/-3h). Classes:
  gnd     >= 90 % of the strip is GND copper
  plane   >= 90 % copper, but partly a power plane (PVDD/VSYS/3V3...): return goes through caps
  partial 50-90 % plane copper (running along a split edge)
  far     inner layer: near plane missing, far plane (L2/L3, 1.07 mm away) present
  void    < 50 % plane copper (over a split, slot or no plane)
Void runs: extra loop area = (D_geo - D_straight)/2 * D_straight, with D_geo the shortest path
through the reference layer's GND copper between the run's end points. Without a GND path on
that layer: length * mean distance to the nearest GND copper on any layer.
Layer changes: distance from each signal via to the nearest GND via; > 2 mm fails; the extra
loop area is d * (spacing of the two reference layers).

Run: python return_paths.py TAG [TAG ...]
"""
import re
import sys

import numpy as np
from scipy import ndimage
from scipy.sparse import csgraph

from pl_common import DIEL, LAYERS, Z, Grid, load, save_json, savefig, style

P = 0.05
STEP = 0.1
FAST = [r"I2S_BCLK", r"I2S_LRCK", r"I2S_SDIN", r"I2S_DOUT", r"I2S_EXT_", r"LCD_SCLK", r"LCD_MOSI",
        r"PDM_CLK", r"PDM_DATA", r"USB_D[PN]", r"UD[PM]", r"A[LR]_OUT[AB]_[PN]"]
SERIES_R = ["R110", "R113", "R114", "R118"]   # source series R of BCLK, SCLK, MOSI, PDM_CLK
STITCH_MAX = 2.0
H_REF = {"F.Cu": [("In1.Cu", DIEL[("F.Cu", "In1.Cu")][0])],
         "B.Cu": [("In2.Cu", DIEL[("In2.Cu", "B.Cu")][0])],
         "In1.Cu": [("F.Cu", DIEL[("F.Cu", "In1.Cu")][0]), ("In2.Cu", DIEL[("In1.Cu", "In2.Cu")][0])],
         "In2.Cu": [("B.Cu", DIEL[("In2.Cu", "B.Cu")][0]), ("In1.Cu", DIEL[("In1.Cu", "In2.Cu")][0])]}
COLORS = {"gnd": "#548235", "plane": "#bf9000", "partial": "#c55a11", "far": "#7030a0", "void": "#c00000"}


def fast_nets(b):
    nets = set()
    for n in b.nets:
        if any(re.search(p, n) for p in FAST):
            nets.add(n)
    for r in SERIES_R:
        for p in b.pads_of(r):
            if p["net"]:
                nets.add(p["net"])
    return sorted(n for n in nets if not n.startswith("unconnected"))


def plane_nets(b, g, L, min_area=50.0):
    """Non-GND nets with > min_area mm2 of copper on layer L (planes / pours)."""
    out = []
    for c in b.copper:
        if c["layer"] != L or c["net"] in ("GND", ""):
            continue
        m = b.raster(g, L, [c["net"]], tracks_min_px=0)
        if m.sum() * g.p ** 2 > min_area:
            out.append(c["net"])
    return out


def analyse(tag):
    b = load(tag)
    g = Grid.from_bbox(b.bbox, P)
    gnd = {L: b.raster(g, L, ["GND"], tracks_min_px=0) for L in LAYERS}
    pl = {}
    for L in LAYERS:
        pn = plane_nets(b, g, L)
        pl[L] = b.raster(g, L, pn, tracks_min_px=0) if pn else np.zeros_like(gnd[L])
    gnd_any = np.zeros_like(gnd["F.Cu"])
    for L in LAYERS:
        gnd_any |= gnd[L]
    dist_any = ndimage.distance_transform_edt(~gnd_any) * P
    ny, nx = gnd["F.Cu"].shape

    def val(m, x, y):
        i = np.clip(((x - g.x0) / P).astype(int), 0, nx - 1)
        j = np.clip(((y - g.y0) / P).astype(int), 0, ny - 1)
        return m[j, i]

    nets = fast_nets(b)
    segs_out, runs, stats = [], [], {}
    for net in nets:
        st = {"len": 0.0, **{c: 0.0 for c in COLORS}, "extra_area_mm2": 0.0,
              "layers": {}}
        for t in [t for t in b.tracks if t["net"] == net]:
            L = t["layer"]
            x1, y1, x2, y2 = t["x1"], t["y1"], t["x2"], t["y2"]
            ln = float(np.hypot(x2 - x1, y2 - y1))
            if ln < 1e-6:
                continue
            n = max(2, int(np.ceil(ln / STEP)) + 1)
            s = np.linspace(0, 1, n)
            xs, ys = x1 + s * (x2 - x1), y1 + s * (y2 - y1)
            ux, uy = (x2 - x1) / ln, (y2 - y1) / ln
            refL, h = H_REF[L][0]
            wr = max(3 * h, t["w"] / 2 + h)
            offs = np.linspace(-wr, wr, max(5, int(2 * wr / P) + 1))
            X = xs[:, None] - uy * offs[None, :]
            Y = ys[:, None] + ux * offs[None, :]
            fg = val(gnd[refL], X, Y).mean(axis=1)
            fp = val(pl[refL], X, Y).mean(axis=1)
            fc = fg + fp
            cls = np.where(fg >= 0.9, "gnd", np.where(fc >= 0.9, "plane", np.where(fc >= 0.5, "partial", "void")))
            if len(H_REF[L]) > 1:   # inner layer: if the near plane is missing, is the far one there?
                ref2, h2 = H_REF[L][1]
                f2 = val(gnd[ref2], X, Y).mean(axis=1) + val(pl[ref2], X, Y).mean(axis=1)
                far = (cls == "void") & (f2 >= 0.9)
                cls = np.where(far, "far", cls)
                st["far_area_mm2"] = st.get("far_area_mm2", 0.0) + float(far.sum() * ln / (n - 1) * (h2 - h))
            ds = ln / (n - 1)
            w = np.full(n, ds); w[0] = w[-1] = ds / 2
            st["len"] += ln
            st["layers"][L] = st["layers"].get(L, 0.0) + ln
            for c in COLORS:
                st[c] += float(w[cls == c].sum())
            segs_out.append({"net": net, "layer": L, "x": xs.tolist(), "y": ys.tolist(), "cls": cls.tolist()})
            # void runs on this segment
            v = cls == "void"
            if v.any():
                lab, nrun = ndimage.label(v)
                for k in range(1, nrun + 1):
                    idx = np.nonzero(lab == k)[0]
                    a, c_ = idx[0], idx[-1]
                    dstr = float(np.hypot(xs[c_] - xs[a], ys[c_] - ys[a])) + ds
                    area, how = None, None
                    geo = geodesic(gnd[refL], g, (xs[a], ys[a]), (xs[c_], ys[c_]), dstr)
                    if geo is not None:
                        area, how = max(0.0, (geo - dstr) / 2 * dstr), "geodesic"
                    else:
                        area, how = dstr * float(np.mean(val(dist_any, xs[idx], ys[idx]))), "nearest GND"
                    st["extra_area_mm2"] += area
                    runs.append({"net": net, "layer": L, "ref": refL, "x": float(xs[a]), "y": float(ys[a]),
                                 "len_mm": dstr, "area_mm2": area, "method": how})
        stats[net] = st

    # layer transitions
    gvias = np.array([(v["x"], v["y"]) for v in b.vias if v["net"] == "GND"] or [(1e9, 1e9)])
    trans = []
    for v in b.vias:
        if v["net"] not in stats:
            continue
        lays = sorted({t["layer"] for t in b.tracks if t["net"] == v["net"] and
                       (np.hypot(t["x1"] - v["x"], t["y1"] - v["y"]) < v["dia"] / 2 + 0.05 or
                        np.hypot(t["x2"] - v["x"], t["y2"] - v["y"]) < v["dia"] / 2 + 0.05)},
                      key=LAYERS.index)
        if len(lays) < 2:
            continue
        d = float(np.min(np.hypot(gvias[:, 0] - v["x"], gvias[:, 1] - v["y"])))
        refs = sorted({H_REF[L][0][0] for L in lays}, key=LAYERS.index)
        hgap = abs(Z[refs[0]] - Z[refs[-1]]) if len(refs) > 1 else 0.0
        trans.append({"net": v["net"], "x": v["x"], "y": v["y"], "layers": lays, "refs": refs,
                      "d_gnd_via_mm": d, "ok": d <= STITCH_MAX,
                      "extra_area_mm2": (d * hgap) if hgap > 0 else 0.0})
    summary = {
        "nets": len(stats),
        "len_mm": sum(s["len"] for s in stats.values()),
        **{f"{c}_mm": sum(s[c] for s in stats.values()) for c in COLORS},
        "void_runs": len(runs),
        "extra_area_void_mm2": sum(r["area_mm2"] for r in runs),
        "extra_area_far_mm2": sum(s.get("far_area_mm2", 0.0) for s in stats.values()),
        "transitions": len(trans),
        "transitions_unstitched": sum(1 for t in trans if not t["ok"]),
        "extra_area_transitions_mm2": sum(t["extra_area_mm2"] for t in trans if not t["ok"]),
    }
    out = {"board": tag, "summary": summary, "per_net": stats, "void_runs": runs, "transitions": trans}
    save_json(out, f"return_paths_{tag}.json")
    return out, segs_out, b, g, gnd


def geodesic(mask, g, a, c, dstr, margin=10.0):
    """Shortest path length (mm) through `mask` between points a and c, searching a window."""
    x0, y0 = min(a[0], c[0]) - margin, min(a[1], c[1]) - margin
    x1, y1 = max(a[0], c[0]) + margin, max(a[1], c[1]) + margin
    i0, j0 = max(0, int((x0 - g.x0) / g.p)), max(0, int((y0 - g.y0) / g.p))
    i1, j1 = min(g.nx, int((x1 - g.x0) / g.p)), min(g.ny, int((y1 - g.y0) / g.p))
    sub = mask[j0:j1, i0:i1]
    if not sub.any():
        return None
    # snap end points to the nearest copper cell
    def snap(pt):
        i, j = int((pt[0] - g.x0) / g.p) - i0, int((pt[1] - g.y0) / g.p) - j0
        jj, ii = np.nonzero(sub)
        k = np.argmin((jj - j) ** 2 + (ii - i) ** 2)
        return jj[k], ii[k], np.hypot(jj[k] - j, ii[k] - i) * g.p
    ja, ia, da = snap(a)
    jc, ic, dc = snap(c)
    idx = -np.ones(sub.shape, int)
    jj, ii = np.nonzero(sub)
    idx[jj, ii] = np.arange(len(jj))
    from scipy import sparse
    r, cc = [], []
    for s1, s2 in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                   ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
        u, v = idx[s1].ravel(), idx[s2].ravel()
        ok = (u >= 0) & (v >= 0)
        r.append(u[ok]); cc.append(v[ok])
    r, cc = np.concatenate(r), np.concatenate(cc)
    A = sparse.coo_matrix((np.ones(len(r)), (r, cc)), shape=(len(jj), len(jj))).tocsr()
    d = csgraph.dijkstra(A, directed=False, indices=idx[ja, ia])[idx[jc, ic]]
    if not np.isfinite(d):
        return None
    return float(d * g.p * 0.85 + da + dc)   # 0.85: 4-neighbour Manhattan -> Euclidean (avg.)


def figure(results):
    plt = style()
    fig, axs = plt.subplots(len(results), 1, figsize=(6.5, 2.2 * len(results)))
    axs = np.atleast_1d(axs)
    for ax, (tag, (out, segs, b, g, gnd)) in zip(axs, results.items()):
        ax.imshow(gnd["In1.Cu"], extent=g.extent(), cmap="Greys", vmin=0, vmax=4, interpolation="nearest")
        for s in segs:
            x, y, c = np.array(s["x"]), np.array(s["y"]), s["cls"]
            for k in range(len(x) - 1):
                ax.plot(x[k:k + 2], y[k:k + 2], color=COLORS[c[k]], lw=0.9, solid_capstyle="butt")
        bad = [t for t in out["transitions"] if not t["ok"]]
        ax.plot([t["x"] for t in bad], [t["y"] for t in bad], "x", color="k", ms=3, mew=0.7)
        s = out["summary"]
        ax.set_title(f"{tag}: {s['void_mm']:.0f} mm over voids, {s['partial_mm']:.0f} mm on split edges, "
                     f"{s['transitions_unstitched']}/{s['transitions']} vias without GND via $\\leq$2 mm",
                     fontsize=9)
        ax.set_xlim(b.bbox[0], b.bbox[2]); ax.set_ylim(b.bbox[3], b.bbox[1])
        ax.set_aspect("equal"); ax.grid(False)
        ax.set_xlabel("x (mm)", fontsize=8); ax.set_ylabel("y (mm)", fontsize=8)
        ax.tick_params(labelsize=7)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=c, lw=2, label=k) for k, c in
         [("GND plane", COLORS["gnd"]), ("power plane", COLORS["plane"]), ("split edge", COLORS["partial"]),
          ("far plane only", COLORS["far"]), ("void", COLORS["void"])]] + [Line2D([], [], color="k", marker="x", ls="", label="via, no GND via $\\leq$2 mm")]
    fig.legend(handles=h, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    savefig(fig, "return_paths_map")


if __name__ == "__main__":
    tags = sys.argv[1:] or ["hybrid", "autoroute"]
    res = {}
    for t in tags:
        res[t] = analyse(t)
        print(t, res[t][0]["summary"])
    figure(res)
