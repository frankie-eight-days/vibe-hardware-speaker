"""Heavy BEM sweep on the real capsule hull (feeds A2 tweeter directivity, A3 woofer diffraction, A5).

Usage:  python bem_capsule_run.py <case> [--quick]
  case = bezel      : as-designed hull, all six radiators (woofers, PRs, tweeters), 100 Hz - 16 kHz
         waveguide  : 10 mm-deep OS waveguide hull (capsule 220 mm), tweeters only, 1 - 16 kHz
         flush      : woofer pistons flush on the skin (no 14 mm tunnel), woofers only, 200 Hz - 8 kHz
         bmcheck    : Burton-Miller vs CHIEF spot check on the bezel hull at a few frequencies
For every frequency (1/12 octave) and radiator (1 m/s normal velocity) it stores the complex pressure
(e^{+jwt} convention, Pa per m/s) at: far-field directions in the tweeter and woofer polar planes, a
coarse full sphere (for power/DI), 1 m on-axis points, and listener / desk-image points.
Mesh levels: element size h <= lambda/6 at the top frequency of each band; the 95th-percentile
edge is reported (gmsh's size field is a target, a few edges exceed it).
Output: results/bem_<case>.npz + results/bem_<case>_log.json.
"""
import json
import os
import sys
import time

import numpy as np

import common
import capsule_geometry as cg
from bem_core import Radiator, make_grid, interior_points, directions

F_12 = 1000.0 * 2.0 ** (np.arange(-40, 49) / 12.0)            # 100 Hz ... 16 kHz, 1/12 octave
Z_DESK = common.cad_params()["flat_bottom_z"] * 1e-3          # desk plane (speaker stands on its flat)
EAR_ABOVE_DESK = 0.40                                          # seated ear height above the desk top (m)
LISTEN_DIST = 1.0                                              # horizontal distance capsule centre -> head (m)

# local element size around the tweeters: resolves the Ø24 dome, the 3 mm bezel lip and the waveguide
# flare.  Without it the tweeter polars at 5 kHz moved by up to 1.3 dB between meshes; with it, <= 0.3 dB.
H_TWEETER = 2.8
CASES = {
    "bezel": dict(variant="bezel", tunnel=True, fmin=100.0, fmax=16200.0, h_tweeter=H_TWEETER,
                  pistons=["woofer_L", "woofer_R", "pr_L", "pr_R", "tweeter_L", "tweeter_R"]),
    "waveguide": dict(variant="waveguide", tunnel=True, fmin=990.0, fmax=16200.0, h_tweeter=H_TWEETER, pistons=["tweeter_L", "tweeter_R"]),
    "flush": dict(variant="bezel", tunnel=False, fmin=198.0, fmax=8100.0, pistons=["woofer_L", "woofer_R"]),
}
# (band top frequency, mesh size mm): h = lambda/6 at the band top, but not coarser than 9 mm
LEVELS = [(6350.0, 9.0), (10100.0, 5.6), (16200.0, 3.5)]


def field_points(variant):
    lay = cg.layout(variant)
    a = lay["t_axis"]
    ev = np.array([0.0, np.sin(np.radians(lay["p"]["t_elev"])), np.cos(np.radians(lay["p"]["t_elev"]))])  # "up" in the tweeter frame
    ang = np.arange(-180.0, 180.0, 2.5)
    F = {}
    F["tw_h"] = directions(a, [1, 0, 0], ang)          # tweeter horizontal plane (contains capsule axis)
    F["tw_v"] = directions(a, ev, ang)                 # tweeter vertical plane (+ = up/back over the top)
    F["wf_h"] = directions([0, -1, 0], [1, 0, 0], ang)  # woofer horizontal plane z = 0
    F["wf_v"] = directions([0, -1, 0], [0, 0, 1], ang)  # woofer vertical plane x = const
    # coarse sphere for sound power / DI (equal-area-ish Fibonacci lattice, 400 directions)
    n = 400
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    F["sphere"] = np.vstack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)])
    P = {}
    tf = {s: lay["t_face"][s] * 1e-3 for s in "LR"}
    P["tw_axis_1m_L"] = (tf["L"] + a * 1.0)[:, None]
    P["tw_axis_1m_R"] = (tf["R"] + a * 1.0)[:, None]
    yb = lay["w_piston_y"] * 1e-3
    P["wf_axis_1m_L"] = np.array([[-lay["w_x"] * 1e-3], [yb - 1.0], [0.0]])
    P["wf_axis_1m_R"] = np.array([[lay["w_x"] * 1e-3], [yb - 1.0], [0.0]])
    # listener grid: centre seat and +-0.15/0.30 m lateral, ear 0.30/0.40/0.50 m above the desk
    xs = np.array([-0.30, -0.15, 0.0, 0.15, 0.30])
    hs = np.array([0.30, 0.40, 0.50])
    L = np.array([[x, -LISTEN_DIST, Z_DESK + h] for h in hs for x in xs]).T
    P["listener"] = L
    P["listener_image"] = np.vstack([L[0], L[1], 2 * Z_DESK - L[2]])
    meta = dict(angles_deg=ang, listener_x=xs, listener_h=hs, z_desk=Z_DESK, t_axis=a, t_up=ev)
    return F, P, meta


def _concat(d):
    sl, arrs, n0 = {}, [], 0
    for k, v in d.items():
        sl[k] = slice(n0, n0 + v.shape[1])
        n0 += v.shape[1]
        arrs.append(v)
    return np.hstack(arrs), sl


def _store(rad, sol, k, i, out, Fall, Fsl, Pall, Psl, pistons):
    rf = rad.field(sol, k, Fall, far=True)
    rp = rad.field(sol, k, Pall, far=False)
    for j, n in enumerate(pistons):
        for key, s in Fsl.items():
            out[key][i, j] = rf[n][s]
        for key, s in Psl.items():
            out[key][i, j] = rp[n][s]


def inside_capsule(q):
    return (np.abs(q[:, 0]) < 0.088) & (np.hypot(q[:, 1], q[:, 2]) < 0.030)


def run(case, quick=False, bm_freqs=None):
    cfg = CASES["bezel" if case == "bmcheck" else case]
    freqs = F_12[(F_12 >= cfg["fmin"]) & (F_12 <= cfg["fmax"])]
    if bm_freqs is not None:
        freqs = np.array(bm_freqs)
    if quick:
        freqs = freqs[::20]
    Fd, Pd, meta = field_points(cfg["variant"])
    pts_in = interior_points(40, 7, inside_capsule, np.array([-0.09, -0.03, -0.03, 0.09, 0.03, 0.03]))
    log = dict(case=case, cfg=cfg, levels=[], freqs=freqs.tolist(), timing_s=[])
    out = {k: np.zeros((len(freqs), len(cfg["pistons"]), v.shape[1]), complex) for k, v in {**Fd, **Pd}.items()}
    if case == "bmcheck":
        out_bm = {k: np.zeros_like(v) for k, v in out.items()}
    sd = {n: (cg.SD_WOOFER if n.startswith("woofer") else cg.SD_PR if n.startswith("pr") else cg.SD_TWEETER)
          for n in cfg["pistons"]}
    # evaluate all far-field directions / all points in one operator each (bempp call overhead dominates)
    Fall, Fsl = _concat(Fd)
    Pall, Psl = _concat(Pd)
    # restartable: each finished frequency is checkpointed to results/bem_ckpt_<tag>/ and skipped on restart
    tag = case + ("_quick" if quick else "")
    ck = os.path.join(common.RESULTS, f"bem_ckpt_{tag}")
    os.makedirs(ck, exist_ok=True)
    ckf = lambda i: os.path.join(ck, f"f{i:03d}_{freqs[i]:.1f}.npz")
    t_all = time.time()
    lo = 0.0
    for ftop, h in LEVELS:
        sel = np.where((freqs > lo) & (freqs <= ftop))[0]
        lo = ftop
        if len(sel) == 0:
            continue
        xyz, tris, dom, info = cg.build(cfg["variant"], tunnel=cfg["tunnel"], h_max=h, h_tweeter=cfg.get("h_tweeter"))
        assert cg.check_closed(tris) == 0, "mesh not closed"
        v = xyz[tris]
        edges = np.concatenate([np.linalg.norm(v[:, a] - v[:, b], axis=1) for a, b in ((0, 1), (1, 2), (2, 0))])
        info["edge_p95_mm"] = float(np.percentile(edges, 95) * 1e3)
        info["lambda_over_6_at_top_mm"] = common.C0 / min(ftop, freqs[sel].max()) / 6 * 1e3
        info["band_hz"] = [float(freqs[sel].min()), float(freqs[sel].max())]
        todo = [i for i in sel if not os.path.exists(ckf(i))]
        rad = None
        if todo:
            grid = make_grid(xyz, tris, dom)
            rad = Radiator(grid, {n: cg.TAGS[n] for n in cfg["pistons"]}, interior_pts=pts_in, sd_true=sd)
            info["ndof"] = rad.ndof
        else:
            info["ndof"] = int(len(xyz))                  # P1 dofs = mesh nodes
        log["levels"].append(info)
        print(f"[{case}] level h={h} mm: {info['n_tri']} triangles, {info['ndof']} dofs, band {info['band_hz']}, "
              f"{len(todo)} of {len(sel)} frequencies to do", flush=True)
        for i in todo:
            f = freqs[i]
            one = {k: np.zeros((1,) + v.shape[1:], complex) for k, v in out.items()}
            sol, k = rad.solve(f, method="chief")
            _store(rad, sol, k, 0, one, Fall, Fsl, Pall, Psl, cfg["pistons"])
            t_solve = rad.last_time
            if case == "bmcheck":
                one_bm = {k: np.zeros_like(v) for k, v in one.items()}
                sol, k = rad.solve(f, method="bm")
                _store(rad, sol, k, 0, one_bm, Fall, Fsl, Pall, Psl, cfg["pistons"])
                one.update({"BM_" + k: v for k, v in one_bm.items()})
            np.savez(ckf(i) + ".tmp.npz", t_solve=t_solve, **one)
            os.replace(ckf(i) + ".tmp.npz", ckf(i))
            print(f"  f = {f:8.1f} Hz  solve {t_solve:6.1f} s  (elapsed {time.time() - t_all:7.0f} s)", flush=True)
    # assemble
    for i in range(len(freqs)):
        z = np.load(ckf(i))
        for k in out:
            out[k][i] = z[k][0]
            if case == "bmcheck":
                out_bm[k][i] = z["BM_" + k][0]
        log["timing_s"].append(float(z["t_solve"]))
    log["total_s"] = time.time() - t_all
    np.savez_compressed(os.path.join(common.RESULTS, f"bem_{tag}.npz"), freqs=freqs, pistons=np.array(cfg["pistons"]),
                        **{f"F_{k}": v for k, v in out.items()},
                        **({f"BM_{k}": v for k, v in out_bm.items()} if case == "bmcheck" else {}),
                        **{f"dir_{k}": v for k, v in Fd.items()}, **{f"pt_{k}": v for k, v in Pd.items()},
                        **{f"meta_{k}": np.asarray(v) for k, v in meta.items()})
    with open(os.path.join(common.RESULTS, f"bem_{tag}_log.json"), "w") as fh:
        json.dump(log, fh, indent=1, default=float)
    import shutil
    shutil.rmtree(ck)                                      # checkpoints no longer needed
    print("done", tag, f"{log['total_s']:.0f} s")


if __name__ == "__main__":
    case = sys.argv[1]
    quick = "--quick" in sys.argv
    if case == "bmcheck":
        run(case, bm_freqs=[2900.0, 5000.0, 9000.0])
    else:
        run(case, quick=quick)
