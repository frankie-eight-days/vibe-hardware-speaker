"""A4 post-processing: figures, clean JSON/CSV from results/a4_modes_raw.json + a4_work/*_modes.npz.

Run: .venv/bin/python sim/acoustics/a4_post.py   (also called by a4_panel_modes.py)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402
import a4_panel_modes as A  # noqa: E402

MAIN = "asm_infill40_drivers"
LABELS = {
    "asm_solid_free": "Shell only, 100 % solid, free-free",
    "asm_solid_free_fine": "  same, finer mesh (2.8 mm)",
    "asm_infill40_free": "Shell only, 40 % infill core",
    "asm_infill40_drivers": "MAIN: 40 % infill + woofer/PR masses",
    "asm_infill40_drivers_batt": "  main + battery rigidly coupled",
    "rear_edges_clamped": "Rear shell alone, seam + ends clamped",
    "rear_screws_only": "Rear shell alone, held at screws only",
    "front_edges_clamped": "Front shell alone, seam + ends clamped",
    "endcap_rim_clamped_PR": "End cap + PR, rim clamped",
    "asm_infill40_drivers_rib_top": "What-if: main + top-arc ribs",
    "asm_infill40_drivers_rib_top_tray": "What-if: + tray gussets",
    "asm_infill40_drivers_spine": "What-if: main + centre spine plate",
    "asm_infill40_drivers_spine_top_tray": "What-if: spine + top ribs + tray gussets",
    "asm_infill40_drivers_all_braces": "What-if: all braces (+ cap gussets)",
    "asm_infill40_drivers_batt_rib_top_tray": "What-if: battery + top ribs + gussets",
    "asm_infill40_drivers_batt_spine_top_tray": "What-if: battery + spine + top + gussets",
}


def load():
    return json.load(open(os.path.join(common.RESULTS, "a4_modes_raw.json")))


def mode_strength(row):
    """Single excitation number per mode: the larger of the force and pressure paths (dB re woofer
    volume velocity at the modal resonance); the pressure path counts only below 800 Hz."""
    rp = row["R_p_db"] if row["f_hz"] < 800 else -200
    return max(row["R_f_db"], rp)


def fig_validation(plt):
    v = json.load(open(os.path.join(common.RESULTS, "a4_validation.json")))
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    modes = np.arange(1, 7)
    for k, run in enumerate(v["runs"]):
        ax.plot(modes + (k - 1) * 0.08, run["err_pct"], "o-", ms=4,
                label=f"h = {run['h_mm']:g} mm ({run['n_nodes'] / 1e3:.0f}k nodes)")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Mode number (clamped square plate)")
    ax.set_ylabel("FE − thin-plate theory (%)")
    ax.set_xticks(modes)
    ax.set_ylim(-4, 3)
    ax.legend(loc="lower left")
    ax.text(0.99, 0.96, f"Leissa f$_1$ = {v['f_exact_hz'][0]:.1f} Hz", transform=ax.transAxes, ha="right", va="top")
    common.savefig(fig, "a4_validation_clamped_plate")
    plt.close(fig)


def fig_modal_map(plt, res):
    order = [k for k in LABELS if k in res]
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.axvspan(A.F_WOOFER_BAND[0], A.F_WOOFER_BAND[1], color="#c55a11", alpha=0.07, lw=0)
    ax.axvline(A.F_FLAG, color="#c55a11", lw=1.0, ls="--")
    ax.text(A.F_FLAG * 1.03, len(order) - 0.35, "1 kHz flag", color="#c55a11", fontsize=8)
    ax.text(70, len(order) - 0.35, "woofer band (to 2.5 kHz LR4)", color="#c55a11", fontsize=8)
    cmap = plt.get_cmap("viridis_r")
    sc = None
    for i, k in enumerate(order):
        y = len(order) - 1 - i
        r = res[k]
        f = np.array(r["freqs_hz"])
        f = f[f < 3000]
        if r["modes"]:
            s = np.array([mode_strength(m) for m in r["modes"]])[: len(f)]
            sc = ax.scatter(f, np.full(len(f), y), c=np.clip(s, -60, 0), cmap=cmap, vmin=-60, vmax=0,
                            s=28, edgecolors="k", linewidths=0.3, zorder=3)
        else:
            ax.scatter(f, np.full(len(f), y), c="#a5a5a5", s=28, edgecolors="k", linewidths=0.3, zorder=3)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([LABELS[k] for k in order][::-1], fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(60, 3000)
    ax.set_ylim(-0.6, len(order) - 0.1)
    ax.set_xlabel("Natural frequency (Hz)")
    ax.grid(True, axis="x", which="both", alpha=0.3)
    ax.grid(False, axis="y")
    if sc is not None:
        cb = fig.colorbar(sc, ax=ax, pad=0.01)
        cb.set_label("Excitation index (dB re woofer\nvolume velocity, at resonance)", fontsize=8)
    common.savefig(fig, "a4_modal_frequency_map")
    plt.close(fig)


def fig_frf(plt, res):
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for k, ls in (("asm_infill40_free", ":"), (MAIN, "-"), ("asm_infill40_drivers_spine", "-."),
                  ("asm_infill40_drivers_all_braces", "--")):
        if k not in res or "frf_db" not in res[k]:
            continue
        d = res[k]["frf_db"]
        ax.semilogx(d["f_hz"], d["total"], ls, label=LABELS[k].strip())
    if MAIN in res:
        d = res[MAIN]["frf_db"]
        ax.semilogx(d["f_hz"], d["pressure"], color="#a5a5a5", lw=0.9, label="main: box-pressure path only")
        ax.semilogx(d["f_hz"], d["force"], color="#bf9000", lw=0.9, label="main: cone-reaction path only")
    ax.axhline(-20, color="k", lw=0.7, ls="--")
    ax.text(55, -18.5, "−20 dB (shell adds ±1 dB ripple)", fontsize=8)
    ax.set_xlim(50, 2500)
    ax.set_ylim(-80, 10)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Shell / woofer volume velocity (dB)")
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    common.savefig(fig, "a4_shell_vs_woofer_output")
    plt.close(fig)


def render_modes(plt, case, n_show=6, fname=None, title_prefix=""):
    import pyvista as pv
    pv.OFF_SCREEN = True
    d = np.load(os.path.join(A.WORK, case + "_modes.npz"))
    xyz, tets, f, U = d["xyz"].astype(float), d["tets"].astype(np.int64), d["f"], d["U"]
    faces, n, area, cen = A.boundary_faces(tets, xyz)
    used = np.unique(faces)
    remap = -np.ones(len(xyz), np.int64)
    remap[used] = np.arange(len(used))
    tri = remap[faces]
    pts = xyz[used]
    cells = np.hstack([np.full((len(tri), 1), 3), tri]).ravel()
    imgs, caps = [], []
    for k in range(min(n_show, len(U))):
        u = np.nan_to_num(U[k][used].astype(float))
        mag = np.linalg.norm(u, axis=1)
        u = u / mag.max()
        mesh = pv.PolyData(pts + 6.0 * u, cells)
        mesh["|u|"] = mag / mag.max()
        i_max = int(np.argmax(mag))
        rear = pts[i_max, 1] > 5
        p = pv.Plotter(off_screen=True, window_size=(900, 640))
        p.set_background("white")
        p.add_mesh(mesh, scalars="|u|", cmap="viridis", clim=(0, 1), show_scalar_bar=False, smooth_shading=True)
        cam = [(-260, 330, 190), (0, 0, 0), (0, 0, 1)] if rear else [(-260, -330, 190), (0, 0, 0), (0, 0, 1)]
        p.camera_position = cam
        p.camera.zoom(1.25)
        img = p.screenshot(return_img=True)
        p.close()
        imgs.append(img)
        caps.append(f"{title_prefix}mode {k + 1}: {f[k]:.0f} Hz\n({'rear-top' if rear else 'front-top'} view)")
    ncol = 3
    nrow = int(np.ceil(len(imgs) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(6.5, 1.75 * nrow + 0.3), gridspec_kw=dict(wspace=0.02, hspace=0.25))
    for ax in np.atleast_1d(axs).ravel():
        ax.axis("off")
    for ax, img, c in zip(np.atleast_1d(axs).ravel(), imgs, caps):
        ax.imshow(img[40:-40, 40:-40])
        ax.set_title(c, fontsize=8)
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=np.atleast_1d(axs).ravel().tolist(), shrink=0.6, pad=0.01)
    cb.set_label("|displacement| (normalised)", fontsize=8)
    common.savefig(fig, fname or f"a4_mode_shapes_{case}")
    plt.close(fig)


def write_tables(res):
    rows = []
    for k, r in res.items():
        for i, fq in enumerate(r["freqs_hz"]):
            m = r["modes"][i] if i < len(r["modes"]) else {}
            rows.append(dict(case=k, label=LABELS.get(k, k), mode=i + 1, f_hz=fq,
                             R_force_db=m.get("R_f_db"), R_pressure_db=m.get("R_p_db"),
                             D_force_db=m.get("D_f_db"), D_pressure_db=m.get("D_p_db"),
                             excitation_index_db=mode_strength(m) if m else None,
                             max_motion_at=m.get("max_motion_at"),
                             below_1khz=fq < A.F_FLAG))
    hdr = list(rows[0].keys())
    with open(os.path.join(common.RESULTS, "a4_modes.csv"), "w") as fh:
        fh.write(",".join(hdr) + "\n")
        for r in rows:
            fh.write(",".join("" if r[h] is None else (f"{r[h]:.4g}" if isinstance(r[h], float) else
                                                        f'"{r[h]}"' if isinstance(r[h], str) else str(r[h]))
                              for h in hdr) + "\n")
    summary = dict(
        description="A4 structural modes of the PETG enclosure (CalculiX C3D10). Indices: dB re the two "
                    "woofers' cone volume velocity at the modal resonance, loss factor eta=%.2f." % A.ETA,
        material=dict(E_solid_MPa=A.E_SOLID, nu=A.NU, rho_solid=1270, infill=A.INFILL, E_core_MPa=A.E_CORE,
                      rho_core=A.RHO_CORE * 1e12, skin_mm=A.SKIN, loss_factor=A.ETA),
        lumped_masses_kg=dict(woofer=A.M_WOOFER, pr_with_add_mass=A.M_PR, battery=A.M_BATT),
        cases={k: dict(label=LABELS.get(k, k), n_nodes=r["n_nodes"], dof=r["dof"], h_mm=r["h_mm"],
                       ccx_s=r["ccx_s"], freqs_hz=r["freqs_hz"][:20],
                       modes_below_1khz=([dict(mode=m["mode"], f_hz=round(m["f_hz"], 1),
                                               excitation_index_db=round(mode_strength(m), 1),
                                               where=m["max_motion_at"]) for m in r["modes"] if m["f_hz"] < A.F_FLAG]
                                         if r["modes"] else [dict(mode=i + 1, f_hz=round(fq, 1)) for i, fq in
                                                             enumerate(r["freqs_hz"]) if fq < A.F_FLAG]),
                       wall_compliance_fraction=r.get("wall_compliance_fraction"),
                       frf_peak_db_below_1khz=(max(v for fq, v in zip(r["frf_db"]["f_hz"], r["frf_db"]["total"])
                                                   if fq < 1000) if "frf_db" in r else None))
               for k, r in res.items()},
    )
    common.save_json(summary, "a4_modes.json")
    # FRF CSV for the main + rib cases
    cols, hdr = [], ["f_hz"]
    for k in (MAIN, "asm_infill40_drivers_spine", "asm_infill40_drivers_all_braces", "asm_infill40_free",
              "asm_infill40_drivers_batt", "asm_infill40_drivers_batt_spine_top_tray"):
        if k in res and "frf_db" in res[k]:
            if not cols:
                cols.append(res[k]["frf_db"]["f_hz"])
            for part in ("total", "pressure", "force"):
                cols.append(res[k]["frf_db"][part])
                hdr.append(f"{k}_{part}_db")
    common.save_csv("a4_shell_vs_woofer_output.csv", hdr, cols)
    return summary


def main():
    plt = common.setup_mpl()
    res = load()
    fig_validation(plt)
    fig_modal_map(plt, res)
    fig_frf(plt, res)
    render_modes(plt, MAIN, 6, "a4_mode_shapes_main_assembly")
    if "asm_infill40_drivers_all_braces" in res:
        render_modes(plt, "asm_infill40_drivers_all_braces", 3, "a4_mode_shapes_all_braces")
    s = write_tables(res)
    for k, c in s["cases"].items():
        print(f"{k:40s} f1..f4 = {[round(x) for x in c['freqs_hz'][:4]]}  <1kHz: "
              f"{[(m['f_hz'], m.get('excitation_index_db')) for m in c['modes_below_1khz']]}  FRFpk {c['frf_peak_db_below_1khz']}")


if __name__ == "__main__":
    main()
