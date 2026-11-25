"""A2. Tweeter directivity on the real capsule (BEM, bempp-cl).

Question: does the as-designed 3 mm bezel on the 40-degree-up shoulder give acceptable tweeter
directivity, or is a ~10 mm waveguide worth a 10 mm longer capsule?  How does either compare with a
flat infinite baffle, and what does a seated listener 1 m away (speaker on a desk) actually get?

Cases (all: rigid piston of the OT19NC00-04's Sd = 4.5 cm^2, Ø24 mm, 1 m/s):
  (a) bezel     - as designed (bem_bezel.npz, left tweeter at x = -83 mm)
  (b) waveguide - 10 mm-deep OS flare, faceplate 10 mm deeper, capsule 220 mm (bem_waveguide.npz)
  (c) baffle    - analytic piston in an infinite flat baffle (2 J1(x)/x), radiating into half space
Planes (tweeter frame): "horizontal" contains the tweeter axis and the capsule's long axis (+ angle =
toward +x, i.e. toward the capsule centre for the left tweeter); "vertical" contains the tweeter axis
and the capsule cross-section (+ angle = up/back over the top, - = down toward the desk/listener).
Run after bem_capsule_run.py bezel / waveguide.  Outputs figures a2_*, results/a2_*.json/csv.
"""
import numpy as np

import common
import drivers_lumped as dl
from bem_results import BEM, beamwidth, norm_polar

A_TW = np.sqrt(dl.TW["sd"] / np.pi)
V_DRIVE = 2.83


def listener_geometry(bem, side="L"):
    """Angles of the centre seat in the tweeter frame and the distance."""
    import capsule_geometry as cg
    lay = cg.layout(bem.case if bem.case in ("bezel", "waveguide") else "bezel")
    c = lay["t_face"][side] * 1e-3
    a, ev = bem.meta["t_axis"], bem.meta["t_up"]
    eh = np.array([1.0, 0, 0])
    L = bem.pts["listener"][:, bem.centre_seat()]
    d = L - c
    r = np.linalg.norm(d)
    d /= r
    off = np.degrees(np.arccos(np.clip(d @ a, -1, 1)))
    vert = np.degrees(np.arctan2(d @ ev, d @ a))
    hor = np.degrees(np.arctan2(d @ eh, d @ a))
    return dict(distance_m=float(r), off_axis_deg=float(off), vertical_deg=float(vert), horizontal_deg=float(hor))


def main():
    plt = common.setup_mpl()
    cases = {}
    for name in ("bezel", "waveguide"):
        try:
            cases[name] = BEM(name)
        except FileNotFoundError:
            print("missing", name)
    ang = cases["bezel"].ang
    th = np.radians(ang)
    fb = cases["bezel"].f
    sel = fb >= 990
    f = fb[sel]
    out = dict(f_hz=f.tolist(), angles_deg=ang.tolist(), cases={})
    maps = {}
    for name, b in cases.items():
        m = b.f >= 990
        maps[name] = {pl: norm_polar(b.get(f"tw_{pl}", "tweeter_L")[m], ang) for pl in ("h", "v")}
        fr = b.f[m]
        if len(fr) != len(f) or not np.allclose(fr, f):
            maps[name] = {pl: np.array([np.interp(f, fr, col) for col in maps[name][pl].T]).T for pl in ("h", "v")}
    D = dl.baffle_piston_directivity(f, A_TW, th)
    bdb = 20 * np.log10(np.abs(D) + 1e-6)
    bdb[:, np.abs(ang) > 90] = np.nan                    # nothing radiates behind an infinite baffle
    maps["baffle"] = {"h": bdb, "v": bdb}

    # ---------------- polar maps
    names = [n for n in ("bezel", "waveguide", "baffle") if n in maps]
    titles = {"bezel": "(a) 3 mm bezel (as built)", "waveguide": "(b) 10 mm waveguide", "baffle": "(c) infinite flat baffle"}
    lv = np.arange(-30, 4, 3)
    fig, axs = plt.subplots(2, len(names), figsize=(7.0, 5.0), sharex=True, sharey=True)
    for j, n in enumerate(names):
        for i, pl in enumerate(("h", "v")):
            ax = axs[i, j]
            Z = np.clip(maps[n][pl], -30, 3)
            ax.set_facecolor("0.85")
            cs = ax.contourf(f, ang, Z.T, levels=lv, cmap="magma", extend="both")
            ax.contour(f, ang, Z.T, levels=[-6], colors="w", linewidths=0.7)
            ax.set_xscale("log")
            ax.set_ylim(-180, 180)
            ax.set_yticks(np.arange(-180, 181, 60))
            ax.grid(False)
            if i == 0:
                ax.set_title(titles[n], fontsize=8.5)
            if j == 0:
                ax.set_ylabel(("horizontal" if pl == "h" else "vertical") + " angle (deg)")
            if i == 1:
                ax.set_xlabel("frequency (Hz)")
            ax.set_xticks([1000, 2000, 5000, 10000])
            ax.set_xticklabels(["1k", "2k", "5k", "10k"])
    lg = listener_geometry(cases["bezel"])
    for j in range(len(names)):
        axs[1, j].axhline(lg["vertical_deg"], color="#2e75b6", lw=1.0, ls="--")
    axs[1, 0].text(1050, lg["vertical_deg"] - 22, "seated listener", color="#9dc3e6", fontsize=7)
    axs[0, len(names) - 1].text(1100, 135, "no sound behind\nan infinite baffle", fontsize=6.5, color="0.3")
    cb = fig.colorbar(cs, ax=axs, shrink=0.9, pad=0.02)
    cb.set_label("level re on-axis (dB)")
    common.savefig(fig, "a2_tweeter_polar_maps_bezel_waveguide_baffle")

    # ---------------- on-axis and listening-axis SPL for 2.83 V
    vt = dl.tweeter_velocity(f) * V_DRIVE
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    resp = {}
    for n, b in cases.items():
        m = b.f >= 990
        pa = b.get("tw_axis_1m_L", "tweeter_L")[m, 0]
        pa = np.interp(f, b.f[m], pa.real) + 1j * np.interp(f, b.f[m], pa.imag)
        pl_free = b.listener("tweeter_L", desk=False)[m, b.centre_seat()]
        pl_desk = b.listener("tweeter_L", desk=True)[m, b.centre_seat()]
        pl_free = np.interp(f, b.f[m], np.abs(pl_free))
        pl_desk = np.interp(f, b.f[m], np.abs(pl_desk))
        resp[n] = dict(onaxis=common.spl(np.abs(pa * vt) / np.sqrt(2)), listen_free=common.spl(pl_free * np.abs(vt) / np.sqrt(2)),
                       listen_desk=common.spl(pl_desk * np.abs(vt) / np.sqrt(2)))
    pb = dl.baffle_piston_onaxis(f, A_TW, 1.0) * vt
    resp["baffle"] = dict(onaxis=common.spl(np.abs(pb) / np.sqrt(2)))
    sty = {"bezel": dict(color="#1f4e79"), "waveguide": dict(color="#c55a11"), "baffle": dict(color="0.4", ls="--")}
    for n in resp:
        axs[0].semilogx(f, resp[n]["onaxis"], label=titles[n][4:], **sty[n])
    for n in cases:
        axs[1].semilogx(f, resp[n]["listen_free"], label=titles[n][4:] + ", free field", **sty[n])
        axs[1].semilogx(f, resp[n]["listen_desk"], lw=0.9, alpha=0.75, label=titles[n][4:] + ", with desk", color=sty[n]["color"], ls=":")
    axs[0].set_title("on tweeter axis, 1 m, free field", fontsize=9)
    axs[1].set_title(f"seated listener ({lg['distance_m']:.2f} m, {abs(lg['vertical_deg']):.0f} deg below axis)", fontsize=9)
    axs[0].set_ylabel("SPL for 2.83 V (dB)")
    for ax in axs:
        ax.set_xlabel("frequency (Hz)")
        common.freq_axis(ax, 1000, 16000)
        ax.set_ylim(70, 100)
        ax.legend(fontsize=6.5, loc="lower center")
    fig.tight_layout()
    common.savefig(fig, "a2_tweeter_onaxis_and_listening_axis")

    # ---------------- beamwidth and directivity index
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for n in names:
        for pl, ls in (("h", "-"), ("v", "--")):
            bw = beamwidth(maps[n][pl], ang)
            axs[0].semilogx(f, bw, ls=ls, color=sty[n]["color"], label=f"{titles[n][4:]} ({'hor.' if pl == 'h' else 'vert.'})" if n != "baffle" or pl == "h" else None)
            out["cases"].setdefault(n, {})[f"beamwidth_{pl}_deg"] = bw.tolist()
    axs[0].set_ylabel("-6 dB beamwidth (deg)")
    axs[0].set_ylim(0, 360)
    for n, b in cases.items():
        m = b.f >= 990
        S = np.abs(b.get("sphere", "tweeter_L")[m]) ** 2
        ax0 = np.abs(b.get("tw_h", "tweeter_L")[m, int(np.argmin(np.abs(ang)))]) ** 2
        di = 10 * np.log10(ax0 / S.mean(axis=1))
        di = np.interp(f, b.f[m], di)
        out["cases"][n]["DI_dB"] = di.tolist()
        axs[1].semilogx(f, di, label=titles[n][4:], **sty[n])
    # baffle: DI of a baffled piston (power into half space only)
    dirs = cases["bezel"].dirs["sphere"]
    cz = dirs[2]                                        # use z as the piston axis for the reference
    thb = np.arccos(np.clip(cz, -1, 1))
    Db = dl.baffle_piston_directivity(f, A_TW, thb)
    dib = 10 * np.log10(1.0 / np.mean(np.abs(Db) ** 2, axis=1))
    out["cases"]["baffle"]["DI_dB"] = dib.tolist()
    axs[1].semilogx(f, dib, label=titles["baffle"][4:], **sty["baffle"])
    axs[1].set_ylabel("directivity index (dB)")
    for ax in axs:
        ax.set_xlabel("frequency (Hz)")
        common.freq_axis(ax, 1000, 16000)
        ax.legend(fontsize=6.5)
    fig.tight_layout()
    common.savefig(fig, "a2_tweeter_beamwidth_and_DI")

    # ---------------- consistency checks: L/R mirror symmetry and Burton-Miller vs CHIEF
    b = cases["bezel"]
    m = b.f >= 990
    hL = np.abs(b.get("tw_h", "tweeter_L")[m])
    hR = np.abs(b.get("tw_h", "tweeter_R")[m])[:, ::-1]
    # mirror: angle -> -angle; ang grid is -180..177.5, so reverse and roll by one to align
    hR = np.roll(hR, 1, axis=1)
    sym = 20 * np.log10(hR / hL)
    front = np.abs(ang) <= 90
    out["checks"] = dict(mirror_LR_max_db_front=float(np.max(np.abs(sym[:, front]))),
                         mirror_LR_p95_db_front=float(np.percentile(np.abs(sym[:, front]), 95)))
    try:
        bm = BEM("bmcheck")
        dd = []
        for key in ("tw_h", "tw_v"):
            a1 = 20 * np.log10(np.abs(bm.get(key, "tweeter_L")))
            a2 = 20 * np.log10(np.abs(bm.get(key, "tweeter_L", bm=True)))
            dd.append(np.abs(a1 - a2)[:, front])
        out["checks"]["chief_vs_burton_miller_max_db_front"] = float(np.max(dd))
        out["checks"]["chief_vs_burton_miller_freqs"] = bm.f.tolist()
    except FileNotFoundError:
        pass
    # ---------------- summary numbers
    lg_w = listener_geometry(cases["waveguide"]) if "waveguide" in cases else None
    out["listener_geometry_bezel"] = lg
    out["listener_geometry_waveguide"] = lg_w
    summ = {}
    for n in names:
        i10 = np.argmin(np.abs(f - 10000))
        i5 = np.argmin(np.abs(f - 5000))
        i2 = np.argmin(np.abs(f - 2500))
        vi = int(np.argmin(np.abs(ang - lg["vertical_deg"])))
        summ[n] = dict(bw_h_2k5=out["cases"][n]["beamwidth_h_deg"][i2], bw_h_5k=out["cases"][n]["beamwidth_h_deg"][i5],
                       bw_h_10k=out["cases"][n]["beamwidth_h_deg"][i10], bw_v_10k=out["cases"][n]["beamwidth_v_deg"][i10],
                       DI_2k5=out["cases"][n]["DI_dB"][i2], DI_10k=out["cases"][n]["DI_dB"][i10],
                       listener_dir_re_axis_db_5k=float(maps[n]["v"][i5, vi]), listener_dir_re_axis_db_10k=float(maps[n]["v"][i10, vi]))
        if n in resp:
            band = (f >= 2000) & (f <= 12000)
            summ[n]["onaxis_ripple_2k_12k_db"] = float(np.ptp(resp[n]["onaxis"][band] - np.polyval(np.polyfit(np.log(f[band]), resp[n]["onaxis"][band], 1), np.log(f[band]))))
            if "listen_free" in resp[n]:
                summ[n]["listen_free_ripple_2k_12k_db"] = float(np.ptp(resp[n]["listen_free"][band] - np.polyval(np.polyfit(np.log(f[band]), resp[n]["listen_free"][band], 1), np.log(f[band]))))
                summ[n]["listen_free_spl_5k_2v83"] = float(resp[n]["listen_free"][i5])
                summ[n]["onaxis_spl_5k_2v83"] = float(resp[n]["onaxis"][i5])
    # desk reflection: dip depth (desk minus free field) at the centre seat and in the 15-seat average
    for n, b in cases.items():
        m = b.f >= 990
        vt_b = dl.tweeter_velocity(b.f[m])
        free = np.abs(b.listener("tweeter_L", desk=False)[m] * vt_b[:, None]) ** 2
        desk = np.abs(b.listener("tweeter_L", desk=True)[m] * vt_b[:, None]) ** 2
        rel_c = 10 * np.log10(desk[:, b.centre_seat()] / free[:, b.centre_seat()])
        rel_avg = 10 * np.log10(desk.mean(1) / free.mean(1))
        band = (b.f[m] >= 1500) & (b.f[m] <= 6000)
        summ[n]["desk_dip_centre_seat_db"] = float(rel_c[band].min())
        summ[n]["desk_dip_centre_seat_hz"] = float(b.f[m][band][np.argmin(rel_c[band])])
        summ[n]["desk_dip_15seat_avg_db"] = float(rel_avg[band].min())
        summ[n]["desk_dip_15seat_avg_hz"] = float(b.f[m][band][np.argmin(rel_avg[band])])
    out["summary"] = summ
    out["mesh"] = {n: __import__("json").load(open(common.os.path.join(common.RESULTS, f"bem_{n}_log.json")))["levels"]
                   for n in cases} if not __import__("bem_results").QUICK else None
    print(__import__("json").dumps(dict(summary=summ, checks=out["checks"], listener=lg), indent=1, default=float))
    common.save_json(out, "a2_tweeter_directivity.json")
    hdr, cols = ["f_hz"], [f]
    for n in resp:
        for k, v in resp[n].items():
            hdr.append(f"{n}_{k}_spl_db_2v83")
            cols.append(v)
    common.save_csv("a2_tweeter_responses.csv", hdr, cols)
    for n in names:
        for pl in ("h", "v"):
            arr = np.column_stack([f, maps[n][pl]])
            np.savetxt(common.os.path.join(common.RESULTS, f"a2_polar_{n}_{pl}.csv"), arr, delimiter=",", fmt="%.4g",
                       header="f_hz," + ",".join(f"{a:g}" for a in ang), comments="")


if __name__ == "__main__":
    main()
