"""Analysis 3: copper balance per layer and per 5 mm cell (all nets, zones filled).

Coverage = copper area / board area, rasterised at 0.05 mm inside the Edge.Cuts outline.
Target (layout_principles check 6): L1 vs L4 and L2 vs L3 within 10 points, globally and per
region. Cells less than half inside the outline are ignored.

Run: python copper_balance.py TAG [TAG ...]
"""
import sys

import numpy as np

from pl_common import LAYERS, Grid, load, save_json, savefig, style

P = 0.05
CELL = 5.0
TOL = 10.0
PAIRS = [("F.Cu", "B.Cu"), ("In1.Cu", "In2.Cu")]
NAMES = {"F.Cu": "L1", "In1.Cu": "L2", "In2.Cu": "L3", "B.Cu": "L4"}


def analyse(tag):
    b = load(tag)
    g = Grid.from_bbox(b.bbox, P)
    om = b.outline_mask(g)
    cu = {L: b.raster(g, L, None, tracks_min_px=0) & om for L in LAYERS}
    k = int(round(CELL / P))
    ny, nx = (g.ny // k), (g.nx // k)

    def blocks(m):
        return m[:ny * k, :nx * k].reshape(ny, k, nx, k).sum(axis=(1, 3)).astype(float)
    area = blocks(om)
    valid = area >= 0.5 * k * k
    cells = {L: np.where(valid, 100 * blocks(cu[L]) / np.maximum(area, 1), np.nan) for L in LAYERS}
    glob = {NAMES[L]: float(100 * cu[L].sum() / om.sum()) for L in LAYERS}
    out = {"board": tag, "coverage_pct": glob, "cell_mm": CELL, "pairs": {}}
    for a, c in PAIRS:
        d = cells[a] - cells[c]
        dv = d[valid]
        out["pairs"][f"{NAMES[a]}-{NAMES[c]}"] = {
            "global_diff_pts": glob[NAMES[a]] - glob[NAMES[c]],
            "global_pass": abs(glob[NAMES[a]] - glob[NAMES[c]]) <= TOL,
            "cells": int(valid.sum()),
            "cells_out_of_tol": int((np.abs(dv) > TOL).sum()),
            "cells_out_pct": float(100 * (np.abs(dv) > TOL).mean()),
            "max_abs_cell_diff_pts": float(np.nanmax(np.abs(dv))),
        }
    save_json(out, f"copper_balance_{tag}.json")
    ext = [g.x0, g.x0 + nx * k * P, g.y0 + ny * k * P, g.y0]
    return out, cells, ext, b


def figure(results):
    plt = style()
    rows = ["F.Cu", "B.Cu", ("F.Cu", "B.Cu"), "In1.Cu", "In2.Cu", ("In1.Cu", "In2.Cu")]
    fig, axs = plt.subplots(len(rows), len(results), figsize=(3.3 * len(results), 6.6), squeeze=False)
    for ci, (tag, (out, cells, ext, b)) in enumerate(results.items()):
        for ri, r in enumerate(rows):
            ax = axs[ri, ci]
            if isinstance(r, tuple):
                d = cells[r[0]] - cells[r[1]]
                im_d = ax.imshow(d, extent=ext, cmap="RdBu_r", vmin=-50, vmax=50, interpolation="nearest")
                bad = np.abs(d) > TOL
                yy, xx = np.nonzero(bad)
                ax.plot(ext[0] + (xx + 0.5) * CELL, ext[3] + (yy + 0.5) * CELL, ".", color="k", ms=1.2)
                pr = out["pairs"][f"{NAMES[r[0]]}-{NAMES[r[1]]}"]
                lab = (f"{NAMES[r[0]]}$-${NAMES[r[1]]}: {pr['global_diff_pts']:+.1f} pts, "
                       f"{pr['cells_out_pct']:.0f}% cells >10")
            else:
                im_c = ax.imshow(cells[r], extent=ext, cmap="copper", vmin=0, vmax=100, interpolation="nearest")
                lab = f"{NAMES[r]}: {out['coverage_pct'][NAMES[r]]:.1f}%"
            ax.set_title(lab, fontsize=7.5, pad=2)
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            for s in ax.spines.values():
                s.set_visible(False)
        axs[0, ci].set_title(f"{tag}\n" + axs[0, ci].get_title(), fontsize=8)
    fig.subplots_adjust(hspace=0.35, wspace=0.05, right=0.86)
    c1 = fig.add_axes([0.88, 0.55, 0.015, 0.33]); fig.colorbar(im_c, cax=c1).set_label("copper %", fontsize=8)
    c2 = fig.add_axes([0.88, 0.12, 0.015, 0.33]); fig.colorbar(im_d, cax=c2).set_label("difference, pts", fontsize=8)
    for c in (c1, c2):
        c.tick_params(labelsize=7)
    savefig(fig, "copper_balance")


if __name__ == "__main__":
    tags = sys.argv[1:] or ["hybrid", "autoroute"]
    res = {t: analyse(t) for t in tags}
    for t, r in res.items():
        print(t, {k: round(v, 1) for k, v in r[0]["coverage_pct"].items()}, r[0]["pairs"])
    figure(res)
