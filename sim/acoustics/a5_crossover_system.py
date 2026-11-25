"""A5. Active crossover + system response per side, and the target DSP EQ.

Question: with an LR4 crossover near 2.5 kHz, what do the woofer+PR and tweeter of one side sum to,
on the front axis and at a seated listener on a desk, and what amp-DSP EQ flattens it?  Is 2.5 kHz the
right crossover frequency?

Chain per side (all at fs = 96 kHz, the TAS5805M DSP rate, TAS5805M-style biquads evaluated with scipy.signal.sosfreqz):
  woofer channel  = A1 bass EQ (subsonic HPF + shelf + peak) x LR4 low-pass(fx)            -> ND65-8 (+ box, PRs)
  tweeter channel = level trim g_t x LR4 high-pass(fx) x delay tau x polarity              -> OT19NC00-04
Acoustics: velocities per volt (A1 for woofer/PR, drivers_lumped for the tweeter) times the BEM transfer
functions of the as-designed capsule (bem_bezel.npz: Pa per m/s at each field point, includes the
tunnel, the bezel, the capsule diffraction and the desk image).
Per-side sum = left woofer + left PR + left tweeter, with the box in A1's state (both channels carry the
same bass, so both PRs move; the left PR is booked to the left side).  The stereo-pair curves add both
sides with identical (mono) signals.
"""
import json

import numpy as np
from scipy import signal
from scipy.optimize import least_squares

import common
import drivers_lumped as dl
from bem_results import BEM, frac_oct_smooth

FS = 96000.0          # TAS5805M DSP rate (process flow 1); biquad_export.py also writes 48 kHz versions
V_REF = 2.83
LV = None   # listener elevation in the tweeter frame (deg), set in main()


def lr4(fx, kind):
    sos = signal.butter(2, fx, btype="low" if kind == "lp" else "high", fs=FS, output="sos")
    return np.vstack([sos, sos])                    # LR4 = Butterworth-2 squared


def sos_resp(sos, f):
    _, h = signal.sosfreqz(sos, worN=f, fs=FS)
    return h


def peaking(fc, q, g):
    """RBJ peaking biquad (normalised sos row)."""
    A = 10 ** (g / 40)
    w0 = 2 * np.pi * fc / FS
    al = np.sin(w0) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w0), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w0), 1 - al / A]
    r = np.array(b + a) / a[0]
    r[3] = 1.0
    return r


def high_shelf(fc, q, g):
    A = 10 ** (g / 40)
    w0 = 2 * np.pi * fc / FS
    al = np.sin(w0) / (2 * q)
    cw = np.cos(w0)
    b = [A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * cw),
         A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * al]
    r = np.array(b + a) / a[0]
    r[3] = 1.0
    return r


class System:
    def __init__(self, bem, side="L"):
        self.b = bem
        self.f = bem.f
        f = self.f
        self.vd, self.vp, _, _ = dl.woofer_transfer(f)
        self.vt = dl.tweeter_velocity(f)
        import biquad_export
        self.h_bass = sos_resp(biquad_export.a1_sos(FS), f)       # A1's bass EQ re-realised at the DSP rate
        self.side = side

    def branches(self, key, idx=None, desk=False, fx=2500.0, gt=1.0, tau=0.0, pol=1, side=None):
        """Complex pressure (per V_REF input) of the woofer(+PR) and tweeter branches at field set `key`."""
        s = side or self.side
        b = self.b
        if key == "listener":
            get = lambda n: b.listener(n, desk=desk)
        else:
            get = lambda n: b.get(key, n)
        Hw = get(f"woofer_{s}") * self.vd[:, None] + get(f"pr_{s}") * self.vp[:, None]
        Ht = get(f"tweeter_{s}") * self.vt[:, None]
        if idx is not None:
            Hw, Ht = Hw[:, idx], Ht[:, idx]
        cw = self.h_bass * sos_resp(lr4(fx, "lp"), self.f) * V_REF
        ct = gt * pol * sos_resp(lr4(fx, "hp"), self.f) * np.exp(-2j * np.pi * self.f * tau) * V_REF
        if Hw.ndim == 2:
            cw, ct = cw[:, None], ct[:, None]
        return Hw * cw, Ht * ct


def align(sysm, fx):
    """Tweeter trim, delay and polarity for the free-field centre-seat listening axis."""
    ic = sysm.b.centre_seat()
    f = sysm.f
    # level trim from the 15-seat listening window on the desk (the use case): the desk lifts the low-mounted
    # woofers by ~5 dB over 0.2-3 kHz but the tweeter less, so a free-field trim would leave the treble low
    wg, tg = sysm.branches("listener", None, desk=True, fx=fx)
    pw = 10 * np.log10(np.mean(np.abs(wg) ** 2, axis=1))
    pt = 10 * np.log10(np.mean(np.abs(tg) ** 2, axis=1))
    wb = (f >= 400) & (f <= 1200)
    tb = (f >= 4000) & (f <= 10000)
    gt = 10 ** ((np.mean(pw[wb]) - np.mean(pt[tb])) / 20)
    xb = (f >= fx / 2) & (f <= fx * 2)
    best = None
    for pol in (1, -1):
        for tau in np.arange(-200e-6, 201e-6, 5e-6):
            w, t = sysm.branches("listener", ic, fx=fx, gt=gt, tau=tau, pol=pol)
            err = 20 * np.log10(np.abs(w + t)[xb]) - 20 * np.log10((np.abs(w) + np.abs(t))[xb])
            c = float(np.sqrt(np.mean(err ** 2)))
            if best is None or c < best[0]:
                best = (c, tau, pol)
    return dict(fx=fx, gt=float(gt), gt_db=float(20 * np.log10(gt)), tau_us=float(best[1] * 1e6), polarity=int(best[2]),
                phase_error_rms_db=best[0])


def window_metrics(sysm, al):
    """Listening-window and vertical-lobing metrics for an alignment."""
    f = sysm.f
    kw = dict(fx=al["fx"], gt=al["gt"], tau=al["tau_us"] * 1e-6, pol=al["polarity"])
    w, t = sysm.branches("listener", None, desk=False, **kw)
    S = common.spl(np.abs(w + t))                       # (nf, 15 seats)
    band = (f >= al["fx"] / 2) & (f <= al["fx"] * 2)
    spread = float(np.mean(np.std(S[band], axis=1)))    # seat-to-seat spread around the crossover
    # vertical lobing in the tweeter frame: level at -30..+30 deg re the listener direction
    ang = sysm.b.ang
    wv, tv = sysm.branches("tw_v", None, **kw)
    V = common.spl(np.abs(wv + tv))
    sel = (ang >= -50) & (ang <= 10)                     # from 50 deg below the tweeter axis to 10 deg above
    dip = float(np.min(V[band][:, sel] - V[band][:, [int(np.argmin(np.abs(ang - LV)))]]))
    return dict(seat_spread_db=spread, deepest_vertical_dip_db=dip)


def fit_eq(f, resp_db, n_peq=6, fmin=150.0, fmax=14000.0, boost_max=3.0, cut_max=-12.0):
    """Peaking-EQ fit to a flat target (level = mean of 300 Hz - 3 kHz) on the 1/3-octave smoothed response.
    The combined boost is held to about +3 dB (penalty term): dips from desk reflections and
    interference move with the listener and must not be filled; cuts may go to -12 dB."""
    sm = frac_oct_smooth(f, resp_db, 3)
    band = (f >= fmin) & (f <= fmax)
    target = np.mean(sm[(f >= 300) & (f <= 3000)])
    dev = sm - target
    params = []
    resid = dev.copy()
    for _ in range(n_peq):
        k = int(np.argmax(np.abs(resid * band)))
        g = float(np.clip(-resid[k], cut_max, boost_max))
        params += [np.log(f[k]), 1.4, g]
        resid = resid + 20 * np.log10(np.abs(sos_resp(peaking(f[k], 1.4, g)[None, :], f)))
    params += [np.log(8000.0), 0.7, 0.0]                 # high shelf

    def eqdb(p):
        sos = [peaking(np.exp(p[3 * i]), p[3 * i + 1], p[3 * i + 2]) for i in range(n_peq)]
        sos.append(high_shelf(np.exp(p[-3]), p[-2], p[-1]))
        return 20 * np.log10(np.abs(sos_resp(np.array(sos), f))), np.array(sos)

    def res(p):
        e = eqdb(p)[0]
        # keep the *combined* boost <= boost_max (stacked peaks must not fill a reflection dip)
        return np.concatenate([(dev + e)[band], 4.0 * np.maximum(0.0, e[band] - boost_max)])
    lo = [np.log(fmin), 0.4, cut_max] * n_peq + [np.log(3000), 0.5, -4]
    hi = [np.log(fmax), 6.0, boost_max] * n_peq + [np.log(14000), 1.0, 4]
    lo, hi = np.array(lo, float), np.array(hi, float)
    p0 = np.clip(params, lo + 1e-6, hi - 1e-6)
    sol = least_squares(res, p0, bounds=(lo, hi))
    g, sos = eqdb(sol.x)
    table = [dict(type="peaking", fc_hz=float(np.exp(sol.x[3 * i])), q=float(sol.x[3 * i + 1]), gain_db=float(sol.x[3 * i + 2]))
             for i in range(n_peq)] + [dict(type="high shelf", fc_hz=float(np.exp(sol.x[-3])), q=float(sol.x[-2]), gain_db=float(sol.x[-1]))]
    after = dev + g
    return dict(eq_db=g, sos=sos, table=table, target_db=float(target), resid_rms_db=float(np.sqrt(np.mean(after[band] ** 2))),
                resid_pp_db=float(np.ptp(after[band])), before_pp_db=float(np.ptp(dev[band])))


def main():
    plt = common.setup_mpl()
    global LV
    b = BEM("bezel")
    from a2_tweeter_bem import listener_geometry
    LV = listener_geometry(b)["vertical_deg"]
    f = b.f
    sysm = System(b, "L")
    ic = b.centre_seat()
    out = dict(f_hz=f.tolist())
    # ---------------- crossover frequency comparison
    cmp = []
    for fx in (2000.0, 2500.0, 3000.0):
        al = align(sysm, fx)
        al.update(window_metrics(sysm, al))
        # tweeter excursion at fx/2 for 2.83 V x trim (mm peak per 2.83 V rms... reported per 10 V peak drive)
        k = int(np.argmin(np.abs(f - fx / 2)))
        x = np.abs(sysm.vt[k] / (2j * np.pi * f[k]) * 10.0 * al["gt"] * np.abs(sos_resp(lr4(fx, "hp"), f[k:k + 1]))[0]) * 1e3
        al["tweeter_excursion_mm_at_fx_over_2_for_10Vpk_input"] = float(x)
        cmp.append(al)
        print(al)
    out["crossover_comparison"] = cmp
    al = [c for c in cmp if c["fx"] == 2500.0][0]
    kw = dict(fx=al["fx"], gt=al["gt"], tau=al["tau_us"] * 1e-6, pol=al["polarity"])

    # ---------------- branches & sum at the centre seat (free field) + front axis
    w, t = sysm.branches("listener", ic, desk=False, **kw)
    wa, ta = sysm.branches("wf_axis_1m_L", 0, **kw)
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    for ax, (ww, tt, ttl) in zip(axs, ((wa, ta, "front axis, 1 m from the left woofer, free field"),
                                         (w, t, "seated listener (centre), free field"))):
        ax.semilogx(f, common.spl(ww / np.sqrt(2)), label="woofer + PR branch")
        ax.semilogx(f, common.spl(tt / np.sqrt(2)), label="tweeter branch")
        ax.semilogx(f, common.spl((ww + tt) / np.sqrt(2)), color="k", lw=1.8, label="sum")
        ax.set_title(ttl, fontsize=8.5)
        common.freq_axis(ax, 100, 16000)
        ax.set_ylim(55, 95)
        ax.set_xlabel("frequency (Hz)")
    axs[0].set_ylabel("SPL, 2.83 V reference, before EQ (dB)")
    axs[0].legend(fontsize=7, loc="lower center")
    fig.tight_layout()
    common.savefig(fig, "a5_crossover_branches_lr4_2k5")

    # ---------------- target EQ from the 15-seat average on the desk (per side)
    wg, tg = sysm.branches("listener", None, desk=True, **kw)
    seat_avg = 10 * np.log10(np.mean(np.abs((wg + tg) / np.sqrt(2) / common.P_REF) ** 2, axis=1))
    eq = fit_eq(f, seat_avg)
    out["eq"] = {k: v for k, v in eq.items() if k not in ("sos", "eq_db")}
    out["eq"]["sos_fs96k"] = eq["sos"].tolist()
    out["eq"]["eq_db"] = eq["eq_db"].tolist()
    out["alignment"] = al
    curves = {
        "front axis 1 m, free field": common.spl((wa + ta) / np.sqrt(2)),
        "listener, free field": common.spl((w + t) / np.sqrt(2)),
        "listener, on desk": common.spl((wg + tg)[:, ic] / np.sqrt(2)),
        "15-seat average, on desk": seat_avg,
    }
    fig, axs = plt.subplots(2, 1, figsize=(6.5, 5.4), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.3]))
    for (lab, c), col in zip(curves.items(), ("#1f4e79", "#c55a11", "#548235", "#7030a0")):
        axs[0].semilogx(f, frac_oct_smooth(f, c + eq["eq_db"], 6), color=col, label=lab + " (EQ on)")
    axs[0].semilogx(f, frac_oct_smooth(f, seat_avg, 6), color="#7030a0", lw=0.9, ls=":", label="15-seat average, before EQ")
    axs[0].set_ylabel("SPL, 2.83 V ref. (dB, 1/6 oct)")
    axs[0].set_ylim(60, 95)
    axs[0].legend(fontsize=7, loc="lower center", ncol=2)
    axs[1].semilogx(f, eq["eq_db"], color="k")
    axs[1].set_ylabel("DSP EQ (dB)")
    axs[1].set_xlabel("frequency (Hz)")
    common.freq_axis(axs[1], 100, 16000)
    fig.tight_layout()
    common.savefig(fig, "a5_system_response_per_side_with_eq")

    # ---------------- stereo pair (mono signal) at the centre and off-centre seats, on the desk
    wR, tR = sysm.branches("listener", None, desk=True, side="R", **kw)
    pair = (wg + tg + wR + tR) / np.sqrt(2)
    xs = b.meta["listener_x"]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for j, x in enumerate(xs):
        idx = 5 + j                                         # ear 0.40 m above the desk
        ax.semilogx(f, frac_oct_smooth(f, common.spl(pair[:, idx]) + eq["eq_db"], 6), lw=1.8 if x == 0 else 1.0,
                    label=f"x = {x:+.2f} m")
    common.freq_axis(ax, 100, 16000)
    ax.set_ylim(55, 95)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("SPL, both sides, 2.83 V ref. (dB, 1/6 oct)")
    ax.legend(fontsize=7, title="listener offset (1 m away, 0.4 m above desk)", title_fontsize=7, ncol=3, loc="lower left")
    fig.tight_layout()
    common.savefig(fig, "a5_stereo_pair_mono_at_seats")

    # ---------------- combined vertical polar (tweeter frame) for 2.0 / 2.5 / 3.0 kHz
    ang = b.ang
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.8), sharey=True)
    for ax, c in zip(axs, cmp):
        kw2 = dict(fx=c["fx"], gt=c["gt"], tau=c["tau_us"] * 1e-6, pol=c["polarity"])
        wv, tv = sysm.branches("tw_v", None, **kw2)
        V = common.spl(np.abs(wv + tv))
        sel = (f >= 700) & (f <= 9000)
        ref = V[sel][:, [int(np.argmin(np.abs(ang - LV)))]]
        Z = np.clip(V[sel] - ref, -24, 6)
        from matplotlib.colors import TwoSlopeNorm
        cs = ax.contourf(f[sel], ang, Z.T, levels=np.arange(-24, 7, 3), cmap="RdBu_r", extend="both",
                         norm=TwoSlopeNorm(vmin=-24, vcenter=0, vmax=6))
        ax.axhline(LV, color="k", lw=0.6, ls="--")
        common.freq_axis(ax, 700, 9000)
        ax.set_ylim(-90, 90)
        ax.grid(False)
        ax.set_title(f"LR4 at {c['fx']/1e3:.1f} kHz", fontsize=9)
        ax.set_xlabel("frequency (Hz)")
    axs[0].set_ylabel("vertical angle, tweeter frame (deg)")
    cb = fig.colorbar(cs, ax=axs, shrink=0.9, pad=0.02)
    cb.set_label("level re listener direction (dB)")
    common.savefig(fig, "a5_vertical_lobing_vs_crossover_frequency")

    out["summary"] = dict(
        alignment=al,
        seat_avg_pp_before_eq_150_14k_db=eq["before_pp_db"], seat_avg_pp_after_eq_db=eq["resid_pp_db"], resid_rms_db=eq["resid_rms_db"],
        max_eq_boost_db=float(np.max(eq["eq_db"][(f >= 150) & (f <= 14000)])), max_eq_cut_db=float(np.min(eq["eq_db"][(f >= 150) & (f <= 14000)])),
        level_2v83_seat_avg_db=eq["target_db"],
    )
    print(json.dumps(out["summary"], indent=1))
    print(json.dumps(out["eq"]["table"], indent=1))
    common.save_json(out, "a5_crossover_system.json")
    hdr = ["f_hz"] + [k.replace(" ", "_").replace(",", "") + "_spl_db" for k in curves] + ["eq_db", "woofer_branch_listener_spl", "tweeter_branch_listener_spl"]
    common.save_csv("a5_system_responses.csv", hdr, [f] + list(curves.values()) + [eq["eq_db"], common.spl(w / np.sqrt(2)), common.spl(t / np.sqrt(2))])


if __name__ == "__main__":
    main()
