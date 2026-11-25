"""A3. Woofer + capsule diffraction (BEM) and the 14 mm woofer tunnel.

Questions: how big are the baffle step and the diffraction ripple of the ND65-8s on the real front
face (100 Hz - 5 kHz)?  What does the stereo pair (+ PRs) deliver at a seated listener on a desk?
Does the Ø53 tunnel through the baffle land (piston ~10-14 mm below the skin) matter?

Data: bem_bezel.npz (as designed, woofers in their tunnels, PRs on the end caps),
      bem_flush.npz (same hull, woofer pistons flush on the skin: no tunnel).
Woofer and PR velocities per volt come from A1 (results/a1_bass_transfer.csv).
Tunnel lumped model: plane-wave tube of the bore area driven by the cone volume velocity and loaded at
the mouth by the radiation impedance of a flanged piston of the bore radius (Kinsler et al.):
    U_mouth / U_cone = 1 / (cos kL + j (Z_rad / Z_c) sin kL),  Z_c = rho c / S_bore.
"""
import json

import numpy as np
from scipy.special import j1, struve

import common
import capsule_geometry as cg
import drivers_lumped as dl
from bem_results import BEM, frac_oct_smooth, norm_polar, QUICK

A_W = np.sqrt(cg.SD_WOOFER / np.pi)
V_DRIVE = 2.83


def tunnel_geometry():
    lay = cg.layout("bezel")
    p = lay["p"]
    a_t = p["w_hole_d"] / 2
    # depth from the piston plane to the skin, averaged over the bore (skin curves away in z)
    z = np.linspace(-a_t, a_t, 401)
    x = np.linspace(-a_t, a_t, 401)
    Z, X = np.meshgrid(z, x)
    inside = Z ** 2 + X ** 2 <= a_t ** 2
    depth = np.sqrt(lay["R"] ** 2 - Z ** 2) - abs(lay["w_piston_y"])
    return dict(a_bore_mm=a_t, depth_centre_mm=float(lay["R"] - abs(lay["w_piston_y"])),
                depth_mean_mm=float(depth[inside].mean()), depth_edge_mm=float(depth[inside].min()))


def tunnel_lumped(f, L, a):
    k = 2 * np.pi * f / common.C0
    S = np.pi * a ** 2
    zc = common.RHO * common.C0 / S
    x = 2 * k * a
    zr = zc * ((1 - 2 * j1(x) / x) + 1j * 2 * struve(1, x) / x)      # flanged piston, e^{+jwt}
    return 1.0 / (np.cos(k * L) + 1j * (zr / zc) * np.sin(k * L))


def main():
    plt = common.setup_mpl()
    b = BEM("bezel")
    try:
        fl = BEM("flush")
    except FileNotFoundError:
        fl = None
    f = b.f
    vd, vp, zin, eq_db = dl.woofer_transfer(f)
    out = dict(f_hz=f.tolist())
    # ------------- diffraction re infinite baffle (same piston, same 1 m point, exact on-axis)
    ref = dl.baffle_piston_onaxis(f, A_W, 1.0)
    pL = b.get("wf_axis_1m_L", "woofer_L")[:, 0]
    pLR = pL + b.get("wf_axis_1m_L", "woofer_R")[:, 0]
    d_L = 20 * np.log10(np.abs(pL / ref))
    d_LR = 20 * np.log10(np.abs(pLR / (2 * ref)))
    out["diffraction_woofer_L_db"] = d_L.tolist()
    out["diffraction_both_woofers_db"] = d_LR.tolist()
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.semilogx(f, d_L, label="left woofer, as designed (in tunnel)")
    ax.semilogx(f, d_LR, label="both woofers, same signal (point 1 m in front of left woofer)")
    if fl is not None:
        pF = fl.get("wf_axis_1m_L", "woofer_L")[:, 0]
        refF = dl.baffle_piston_onaxis(fl.f, A_W, 1.0)
        ax.semilogx(fl.f, 20 * np.log10(np.abs(pF / refF)), "--", label="left woofer flush on the skin (no tunnel)")
    # simple baffle-step reference: Olson-type first-order shelf with f3 = 115 / W(m) for a 95 mm-wide baffle
    fbs = 115.0 / 0.095
    ax.semilogx(f, 20 * np.log10(np.abs((1j * f / fbs + 0.5) / (1j * f / fbs + 1))), ":", color="0.4",
                label=f"textbook baffle step (95 mm baffle, f3 ~ {fbs:.0f} Hz)")
    ax.axhline(0, color="0.6", lw=0.6)
    common.freq_axis(ax, 100, 6300)
    ax.set_ylim(-9, 6)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("on-axis level re infinite baffle (dB)")
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    common.savefig(fig, "a3_woofer_baffle_step_and_diffraction")

    # ------------- tunnel effect: BEM (tunnel / flush) vs lumped tube
    tg = tunnel_geometry()
    out["tunnel_geometry"] = tg
    if fl is not None:
        fi = fl.f
        m = (f >= fi.min() - 1) & (f <= fi.max() + 1)
        # radiated power (sphere average) and on-axis
        Pt = np.mean(np.abs(b.get("sphere", "woofer_L")[m]) ** 2, axis=1)
        Pf = np.mean(np.abs(fl.get("sphere", "woofer_L")) ** 2, axis=1)
        Pf = np.interp(f[m], fi, Pf)
        pf_ax = np.interp(f[m], fi, np.abs(fl.get("wf_axis_1m_L", "woofer_L")[:, 0]))
        r_pow = 10 * np.log10(Pt / Pf)
        r_ax = 20 * np.log10(np.abs(pL[m]) / pf_ax)
        L_mean = tg["depth_mean_mm"] * 1e-3
        a_t = tg["a_bore_mm"] * 1e-3
        H = tunnel_lumped(f[m], L_mean, a_t) * (np.pi * a_t ** 2 / (np.pi * a_t ** 2))
        Hc = tunnel_lumped(f[m], tg["depth_centre_mm"] * 1e-3, a_t)
        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        ax.semilogx(f[m], r_ax, label="BEM: tunnel / flush, on axis 1 m")
        ax.semilogx(f[m], r_pow, label="BEM: tunnel / flush, radiated power")
        ax.semilogx(f[m], 20 * np.log10(np.abs(H)), "--", label=f"lumped tube, L = {tg['depth_mean_mm']:.1f} mm (mean depth)")
        ax.semilogx(f[m], 20 * np.log10(np.abs(Hc)), ":", label=f"lumped tube, L = {tg['depth_centre_mm']:.1f} mm (centre depth)")
        ax.axhline(0, color="0.6", lw=0.6)
        common.freq_axis(ax, 200, 8000)
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("level change from the tunnel (dB)")
        ax.legend(fontsize=7)
        fig.tight_layout()
        common.savefig(fig, "a3_woofer_tunnel_effect")
        k1 = int(np.argmax(r_ax))
        kp = int(np.argmax(r_pow))
        out["tunnel"] = dict(f_hz=f[m].tolist(), bem_onaxis_db=r_ax.tolist(), bem_power_db=r_pow.tolist(),
                             lumped_mean_db=(20 * np.log10(np.abs(H))).tolist(),
                             peak_onaxis_db=float(r_ax[k1]), peak_onaxis_f=float(f[m][k1]),
                             peak_power_db=float(r_pow[kp]), peak_power_f=float(f[m][kp]),
                             lumped_peak_f=float(f[m][int(np.argmax(np.abs(H)))]), lumped_peak_db=float(20 * np.log10(np.abs(H).max())),
                             at_2k5_onaxis_db=float(np.interp(2500, f[m], r_ax)), at_2k5_power_db=float(np.interp(2500, f[m], r_pow)))

    # ------------- polar maps of the left woofer (100 Hz - 6.3 kHz)
    sel = f <= 6400
    ang = b.ang
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    for ax, pl, lab in zip(axs, ("h", "v"), ("horizontal (+ = toward +x)", "vertical (+ = up)")):
        Z = np.clip(norm_polar(b.get(f"wf_{pl}", "woofer_L")[sel], ang), -30, 3)
        cs = ax.contourf(f[sel], ang, Z.T, levels=np.arange(-30, 4, 3), cmap="magma", extend="both")
        ax.contour(f[sel], ang, Z.T, levels=[-6], colors="w", linewidths=0.7)
        common.freq_axis(ax, 100, 6300)
        ax.grid(False)
        ax.set_title(f"left woofer, {lab}", fontsize=9)
        ax.set_xlabel("frequency (Hz)")
        ax.set_yticks(np.arange(-180, 181, 60))
        np.savetxt(common.os.path.join(common.RESULTS, f"a3_polar_woofer_L_{pl}.csv"), np.column_stack([f[sel], Z]),
                   delimiter=",", fmt="%.4g", header="f_hz," + ",".join(f"{a:g}" for a in ang), comments="")
    axs[0].set_ylabel("angle from woofer axis (deg)")
    cb = fig.colorbar(cs, ax=axs, shrink=0.9, pad=0.02)
    cb.set_label("level re on-axis (dB)")
    common.savefig(fig, "a3_woofer_polar_maps")

    # ------------- full bass/mid system at the listener: both woofers + both PRs (A1 velocities, 2.83 V each)
    ic = b.centre_seat()
    comps = {"woofer_L": vd, "woofer_R": vd, "pr_L": vp, "pr_R": vp}
    p_free = sum(b.listener(n, desk=False)[:, ic] * v for n, v in comps.items()) * V_DRIVE
    p_desk = sum(b.listener(n, desk=True)[:, ic] * v for n, v in comps.items()) * V_DRIVE
    p_wo = sum(b.listener(n, desk=True)[:, ic] * comps[n] for n in ("woofer_L", "woofer_R")) * V_DRIVE
    # A1 monopole half-space model at the same distance (sum of volume velocities, 2 pi radiation)
    r_l = np.linalg.norm(b.pts["listener"][:, ic])
    U = 2 * cg.SD_WOOFER * vd + 2 * cg.SD_PR * vp
    p_a1 = common.RHO * 2 * np.pi * f * U * V_DRIVE / (2 * np.pi * r_l)
    # spatial average over the 15-seat grid (desk), power average
    p_grid = sum(b.listener(n, desk=True) * v[:, None] for n, v in comps.items()) * V_DRIVE
    grid_avg = 10 * np.log10(np.mean(np.abs(p_grid / np.sqrt(2) / common.P_REF) ** 2, axis=1))
    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.semilogx(f, common.spl(p_desk / np.sqrt(2)), label="BEM, centre seat, on the desk (image)")
    ax.semilogx(f, common.spl(p_free / np.sqrt(2)), label="BEM, centre seat, free field")
    ax.semilogx(f, grid_avg, lw=1.0, label="BEM, desk, average of 15 seats (±0.3 m, 0.3-0.5 m high)")
    ax.semilogx(f, common.spl(p_a1 / np.sqrt(2)), "--", color="0.35", label="A1 lumped model, half space (monopole)")
    ax.semilogx(f, common.spl(p_wo / np.sqrt(2)), ":", color="0.5", lw=1.0, label="BEM, desk, woofers only (no PRs)")
    common.freq_axis(ax, 100, 6300)
    ax.set_ylim(55, 95)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(f"SPL at listener, {V_DRIVE} V per woofer (dB)")
    ax.legend(fontsize=7, loc="lower center")
    fig.tight_layout()
    common.savefig(fig, "a3_woofers_and_prs_at_listener")
    lo = (f >= 100) & (f <= 200)
    out["listener"] = dict(distance_m=float(r_l), spl_desk=common.spl(p_desk / np.sqrt(2)).tolist(),
                           spl_free=common.spl(p_free / np.sqrt(2)).tolist(), spl_grid_avg=grid_avg.tolist(),
                           spl_a1_halfspace=common.spl(p_a1 / np.sqrt(2)).tolist(),
                           bem_desk_minus_a1_100_200hz_db=float(np.mean(common.spl(p_desk)[lo] - common.spl(p_a1)[lo])),
                           bem_desk_minus_a1_max_abs_100_200hz_db=float(np.max(np.abs(common.spl(p_desk)[lo] - common.spl(p_a1)[lo]))))
    band = (f >= 150) & (f <= 2500)
    sm = frac_oct_smooth(f, d_L, 3)
    out["summary"] = dict(
        baffle_step_low_db=float(np.mean(d_L[(f >= 100) & (f <= 130)])),
        diffraction_at_500_1k_2k_4k_db=[float(np.interp(x, f, d_L)) for x in (500, 1000, 2000, 4000)],
        ripple_pp_150_2500_db=float(np.ptp(d_L[band] - sm[band])),
    )
    if fl is not None:
        dF = 20 * np.log10(np.abs(fl.get("wf_axis_1m_L", "woofer_L")[:, 0] / dl.baffle_piston_onaxis(fl.f, A_W, 1.0)))
        out["summary"]["flush_step_minus3db_hz"] = float(np.interp(-3.0, dF[fl.f < 1500], fl.f[fl.f < 1500]))
        out["summary"]["flush_ripple_pp_1k_6k_db"] = float(np.ptp(dF[(fl.f >= 1000) & (fl.f <= 6000)]))
    out["summary"]["tunnel_step_minus3db_hz"] = float(np.interp(-3.0, d_L[f < 1500], f[f < 1500]))
    print(json.dumps({k: v for k, v in out.items() if k in ("summary", "tunnel_geometry")}, indent=1))
    if "tunnel" in out:
        print({k: v for k, v in out["tunnel"].items() if not isinstance(v, list)})
    print({k: v for k, v in out["listener"].items() if not isinstance(v, list)})
    common.save_json(out, "a3_woofer_diffraction.json")
    common.save_csv("a3_woofer_responses.csv", ["f_hz", "diffraction_L_db", "diffraction_LR_db", "listener_desk_spl", "listener_free_spl",
                                                "listener_grid_avg_spl", "a1_halfspace_spl"],
                    [f, d_L, d_LR, common.spl(p_desk / np.sqrt(2)), common.spl(p_free / np.sqrt(2)), grid_avg, common.spl(p_a1 / np.sqrt(2))])


if __name__ == "__main__":
    main()
