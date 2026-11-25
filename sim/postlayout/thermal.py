"""Analysis 5: steady-state 2.5-D finite-difference thermal model of the board.

Grid 0.5 mm, one node per copper layer per column (L1..L4 or L1..L6, pl_common.stackup). In-plane sheet conductance per layer =
k_Cu * t_Cu * (copper fraction of the cell, from a 0.05 mm raster) + k_FR4,xy * (share of the
dielectric). Vertical: FR4 through-plane (0.3 W/mK) + every plated barrel in the cell
(k_Cu * pi * d * 20 um / dz, all nets). Convection + radiation lumped as h on both faces to
the 45 C enclosure air (h = 5 and 10 W/m2K). Component losses go into L1 under their pads;
T_j = T_board,max(under pads) + P * psi_JB (datasheet). Component bodies are not modelled as fins
(conservative).
Validation: energy balance, and a uniformly heated board vs T = Ta + P/(2 h A).

Run: python thermal.py TAG [TAG ...]
"""
import sys

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from pl_common import VIA_PLATING, Grid, load, save_json, savefig, style

DX = 0.5
K_CU, K_FR4_XY, K_FR4_Z = 385.0, 0.8, 0.3
T_AMB = 45.0
H_VALUES = (5.0, 10.0)
THICK = 1.6
# psi_JB (degC/W): TAS5805M 8.1 (SLASEH5D p.7), TPS61178 14.5 (SLVSDA7E p.4), TPS62933 19.2
# (SLUSEA4D p.6), BQ25792 9.7 (SLUSDV2C p.8), NCEP3065QU R_thJC 2.3 (V6.0 p.1). Inductors: body
# self-heating not modelled (board temperature under the pads is reported).
PSI = {"U301": 8.1, "U401": 8.1, "U901": 14.5, "U951": 19.2, "U701": 9.7, "Q801": 2.3, "Q802": 2.3,
       "Q701": 2.3}
TJ_LIMIT = {"U301": 150, "U401": 150, "U901": 150, "U951": 150, "U701": 120, "Q801": 150}  # U701: TREG 120 C

# Losses (W). Amp: idle PVDD*Icc (32.5 mA at 13.5 V, 10 uH filter, SLASEH5D p.8, scaled to 18 V
# -> 0.6 W) + DVDD 0.06 W + Pout*(1/eta - 1), eta = 0.90 (Fig. 6-32, p.17, read off the plot).
AMP_IDLE = 18 * 0.0325 + 3.3 * 0.018


def amp_loss(pout):
    return AMP_IDLE + pout * (1 / 0.90 - 1)


CASES = {
    # 2.9 W "moderate" system average (mech_envelope / electronics 12): ~0.5 W out per amp
    "moderate 2.9 W": {"U301": amp_loss(0.5), "U401": amp_loss(0.5), "U901": 0.2, "L901": 0.1,
                       "U951": 0.1, "U101": 0.4},
    # boost-limited 40 W out (spec_power 4.1.4), 20 W per amp; boost 2.0 W IC + 0.5 W L901
    # (spec_power 6 worst case); battery path at ~6.5 A: Q801/Q802 0.1 W, Q701 0.12 W, F801 0.24 W
    "max sustained 40 W": {"U301": amp_loss(20), "U401": amp_loss(20), "U901": 2.0, "L901": 0.5,
                           "U951": 0.15, "U101": 0.4, "Q801": 0.1, "Q802": 0.1, "Q701": 0.12, "F801": 0.24},
    # charging 2 A while playing (moderate): U701 1.5 W (spec_power 6), L701 15 mOhm at ~5 A -> 0.4 W
    "charge 2 A + moderate": {"U301": amp_loss(0.5), "U401": amp_loss(0.5), "U901": 0.2, "L901": 0.1,
                              "U951": 0.1, "U101": 0.4, "U701": 1.5, "L701": 0.4},
    # over-discharge recovery: 2 A through Q801's body diode (spec_power 2.3, S3)
    "Q801 recovery 1.5 W": {"Q801": 1.5, "U701": 0.8, "L701": 0.2, "U951": 0.1, "U101": 0.2},
}
REPORT = ["U301", "U401", "U901", "L901", "U701", "Q801"]
TJ_DESIGN = 125.0   # design ceiling: 35 K below TAS5805M OTE 160 C (SLASEH5D p.9), 25 K below TPS61178 TSD 150 C (p.6)


def playback_case(p_total):
    """Losses for a sustained total output p_total (W), both amps equal. Boost loss scaled from
    spec_power 6 (2.5 W at 40 W out): 5.5 % of its output, 80 % in U901, 20 % in L901."""
    amp_in = p_total / 2 / 0.90 + AMP_IDLE
    pb = 0.055 * 2 * amp_in
    return {"U301": amp_loss(p_total / 2), "U401": amp_loss(p_total / 2), "U901": 0.8 * pb,
            "L901": 0.2 * pb, "U951": 0.15, "U101": 0.4}


def max_sustained(b, g, M, idx):
    """Highest sustained total output with U301/U401/U901 T_j <= TJ_DESIGN (bisection)."""
    def worst(p):
        case = playback_case(p)
        q, cells = heat_vector(b, g, idx, case)
        T = spsolve(M, q)
        return max(T_AMB + max(T[idx(0)[j, i]] for j, i in cells[r]) + case[r] * PSI[r] - TJ_DESIGN
                   for r in ("U301", "U401", "U901"))
    lo, hi = 0.0, 40.0
    if worst(lo) > 0:
        return 0.0
    if worst(hi) < 0:
        return hi
    for _ in range(14):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if worst(mid) < 0 else (lo, mid)
    return lo


def build(b, h):
    LAYERS, T_CU, Z = b.layers, b.t_cu, b.z
    nl = len(LAYERS)
    g = Grid.from_bbox(b.bbox, DX)
    fine = Grid(g.x0, g.y0, g.nx * 10, g.ny * 10, DX / 10)
    om_f = b.outline_mask(fine)
    k = 10
    inside = om_f.reshape(g.ny, k, g.nx, k).mean(axis=(1, 3))
    frac = {}
    for L in LAYERS:
        m = b.raster(fine, L, None, tracks_min_px=0) & om_f
        frac[L] = m.reshape(g.ny, k, g.nx, k).mean(axis=(1, 3))
    on = inside > 0.3
    nc = g.nx * g.ny
    idx = lambda li: li * nc + np.arange(nc).reshape(g.ny, g.nx)
    rows, cols, vals = [], [], []
    t_d = b.st["t_fr4"]   # FR4 share per layer, mm
    for li, L in enumerate(LAYERS):
        kt = (K_CU * T_CU[L] * frac[L] + K_FR4_XY * t_d[L]) * 1e-3     # W/K per square
        a = idx(li)
        for s1, s2 in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                       ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
            ok = on[s1] & on[s2]
            gk = 2 / (1 / kt[s1] + 1 / kt[s2])
            rows.append(a[s1][ok]); cols.append(a[s2][ok]); vals.append(gk[ok])
    # vias per cell
    nvia = np.zeros((g.ny, g.nx))
    for v in b.vias + [p for p in b.pads if p["drill"] > 0 and len(p["layers"]) > 1]:
        i, j = g.ij(v["x"], v["y"])
        nvia[j, i] += np.pi * max(v["drill"], 0.2) * VIA_PLATING      # mm2 of barrel
    A = (DX * 1e-3) ** 2
    for li in range(nl - 1):
        L1, L2 = LAYERS[li], LAYERS[li + 1]
        dz = abs(Z[L1] - Z[L2]) * 1e-3
        gz = K_FR4_Z * A / dz + K_CU * nvia * 1e-6 / dz
        rows.append(idx(li)[on]); cols.append(idx(li + 1)[on]); vals.append(gz[on])
    r, c, v = map(np.concatenate, (rows, cols, vals))
    N = nl * nc
    G = sparse.coo_matrix((v, (r, c)), shape=(N, N)).tocsr()
    G = G + G.T
    diag = np.asarray(G.sum(axis=1)).ravel()
    conv = np.zeros(N)
    conv[idx(0)[on]] = h * A * inside[on]
    conv[idx(nl - 1)[on]] = h * A * inside[on]
    off = np.ones(N, bool)
    for li in range(nl):
        off[idx(li)[on]] = False
    M = sparse.diags(diag + conv + off * 1.0) - G
    return g, M.tocsc(), conv, on, idx, frac, inside


def heat_vector(b, g, idx, case):
    q = np.zeros(len(b.layers) * g.nx * g.ny)
    cells = {}
    for ref, P in case.items():
        pads = [p for p in b.pads_of(ref) if "F.Cu" in p["layers"]] or b.pads_of(ref)
        cs = set()
        for p in pads:
            x0, y0, x1, y1 = p["bbox"]
            for x in np.arange(x0, x1 + 1e-6, DX / 2):
                for y in np.arange(y0, y1 + 1e-6, DX / 2):
                    i, j = g.ij(x, y); cs.add((j, i))
        cs = list(cs)
        cells[ref] = cs
        for (j, i) in cs:
            q[idx(0)[j, i]] += P / len(cs)
    return q, cells


def analyse(tag):
    b = load(tag)
    out = {"board": tag, "cases": {}}
    maps = {}
    for h in H_VALUES:
        g, M, conv, on, idx, frac, inside = build(b, h)
        # validation: uniform heating
        q = np.zeros(M.shape[0]); area = inside[on].sum() * (DX * 1e-3) ** 2
        q[idx(0)[on]] = 1.0 * inside[on] / inside[on].sum()
        T = spsolve(M, q)
        out.setdefault("validation", {})[f"h{h:g}"] = {
            "uniform_1W_dT_model": float(np.average(T[idx(0)[on]], weights=inside[on])),
            "uniform_1W_dT_analytic": float(1.0 / (2 * h * area))}
        out.setdefault("max_sustained_W", {})[f"h{h:g}"] = max_sustained(b, g, M, idx)
        for cname, case in CASES.items():
            q, cells = heat_vector(b, g, idx, case)
            T = spsolve(M, q)
            bal = float((conv * T).sum() / q.sum())
            rep = {}
            for ref in REPORT + [r for r in case if r not in REPORT]:
                if ref not in b.fps:
                    continue
                if ref not in cells:
                    _, c2 = heat_vector(b, g, idx, {ref: 0.0}); cs = c2[ref]
                else:
                    cs = cells[ref]
                tb = T_AMB + max(T[idx(0)[j, i]] for j, i in cs)
                P = case.get(ref, 0.0)
                tj = tb + P * PSI.get(ref, 0.0)
                rep[ref] = {"P_W": P, "T_board_C": float(tb), "T_j_C": float(tj),
                            "limit_C": TJ_LIMIT.get(ref)}
            out["cases"].setdefault(cname, {})[f"h{h:g}"] = {
                "parts": rep, "T_max_board_C": float(T_AMB + T[idx(0)[on]].max()),
                "P_total_W": float(q.sum()), "energy_balance": bal}
            maps[(cname, h)] = T_AMB + T[idx(0)].reshape(g.ny, g.nx), g, on
    save_json(out, f"thermal_{tag}.json")
    return out, maps, b


def figure(results):
    plt = style()
    cnames = list(CASES)
    fig, axs = plt.subplots(len(cnames), len(results), figsize=(6.5, 1.6 * len(cnames)), squeeze=False)
    vmin, vmax = T_AMB, 150
    for ci, (tag, (out, maps, b)) in enumerate(results.items()):
        for ri, cn in enumerate(cnames):
            T, g, on = maps[(cn, 5.0)]
            ax = axs[ri, ci]
            im = ax.imshow(np.where(on, T, np.nan), extent=g.extent(), cmap="inferno", vmin=vmin, vmax=vmax,
                           interpolation="bilinear")
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            for s in ax.spines.values():
                s.set_visible(False)
            parts = out["cases"][cn]["h5"]["parts"]
            hot = max(parts.items(), key=lambda kv: kv[1]["T_j_C"])
            ax.set_title(f"{tag}, {cn}\nboard max {out['cases'][cn]['h5']['T_max_board_C']:.0f} C, "
                         f"{hot[0]} Tj {hot[1]['T_j_C']:.0f} C", fontsize=6.5, pad=1.5)
            for ref in REPORT:
                if ref in b.fps and parts.get(ref, {}).get("P_W", 0) > 0:
                    f = b.fps[ref]
                    ax.text(f["x"], f["y"], ref, color="w", fontsize=5, ha="center", va="center")
    fig.subplots_adjust(hspace=0.55, wspace=0.03, right=0.88)
    cax = fig.add_axes([0.9, 0.3, 0.015, 0.4])
    fig.colorbar(im, cax=cax).set_label("L1 temperature, C (h = 5 W/m$^2$K, 45 C air)", fontsize=7)
    cax.tick_params(labelsize=7)
    savefig(fig, "thermal_maps")


if __name__ == "__main__":
    tags = sys.argv[1:] or ["hybrid", "autoroute"]
    res = {}
    for t in tags:
        res[t] = analyse(t)
        o = res[t][0]
        print(t, o["validation"], "max sustained W:", o["max_sustained_W"])
        for cn, d in o["cases"].items():
            print(" ", cn, {h: {r: round(v["T_j_C"], 1) for r, v in dd["parts"].items()} for h, dd in d.items()},
                  "bal", round(d["h5"]["energy_balance"], 4))
    figure(res)
