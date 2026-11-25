#!/usr/bin/env python3
"""First-pass passive-radiator (PR) alignment for the portable stereo BT speaker.

Runs on the system Python 3.9 with numpy only (matplotlib optional, for PNGs).

Model (lumped-element, small-signal, linear):
  * Nd identical woofers share ONE sealed box of net volume Vb with Np identical PRs.
    All woofers get the same voltage (bass is mono below the crossover).
  * Woofer: Re + jwLe (plain inductor), Bl, Mms, Cms, Rms (Rms from Qms when not published).
  * Box: acoustic compliance Cab = Vb/(rho c^2) plus a leakage resistance Ral set by QL at fb.
    No absorption loss (QA = inf), no stuffing gain. Box is assumed rigid.
  * PR: Mmp = Mms_pr + m_add, Cmp, Rmp (= 2*pi*Fs*Mms/Qms of the bare PR).
  * Radiation: total far-field volume velocity U = Nd*Sd*v_d + Np*Sp*v_p (monopole; valid
    well below ~300 Hz where the end-cap PRs and the front woofers are acoustically close).
    Pressure at 1 m in HALF space (2*pi, speaker standing on a table): |p| = rho*w*|U|/(2*pi*r).
    Subtract 6 dB for free-field (4*pi). Radiation mass/resistance are neglected (published Mms
    already includes the free-air load).
  * Amplifier (TAS5805M, BTL, 19 V boost rail): peak output voltage V_PK_MAX = 18 V
    (~20 W into 8 ohm, ~27 W into 6 ohm) AND peak current I_PK_MAX = 4.5 A (5 A OCP less 10%
    margin), applied per frequency as V <= min(V_PK_MAX, I_PK_MAX*|Zin(f)|). A 4 ohm woofer is
    therefore current-limited near its impedance minimum.
  * Woofer one-way Xmax as published, PR usable limit xlim_model_m from drivers.json
    (5 mm for the DMA PRs, ~0.7 x their 7 mm Xmech).

Outputs per driver set (printed + PNG):
  * natural (no-EQ) F3/F6, fb (box tuning), fp (PR notch),
  * sine max SPL vs frequency (min of power / woofer Xmax / PR Xmax limits) -- EQ-independent,
  * "DSP ceiling": the highest flat-passband sine level reachable when the DSP EQs the system to a
    target high-pass (Butterworth 4th order at F3_target times a 2nd-order subsonic at 0.45*F3),
    with EQ boost capped at MAX_BOOST_DB and the EQ gain rolled off at 24 dB/oct below
    EQ_FLOOR_RATIO*F3 (DSP subsonic filter, so the EQ never boosts into the PR notch),
  * pink-noise estimate (1/3-octave bands, crest factor 3 on voltage and excursion, woofer thermal
    limited to its rated RMS power) through the same DSP target plus an LR4 crossover at FX_HZ,
  * the PR added mass that maximises the pink-noise estimate, and the minimum net box volume that
    meets the requirement (F3 <= 63 Hz with DSP and >= 90 dB pink noise, half space).
"""
import json
import os
import sys

import numpy as np

RHO, C = 1.18, 343.0
P0 = 20e-6
HERE = os.path.dirname(os.path.abspath(__file__))
DRIVERS_JSON = os.path.join(HERE, "..", "..", "research", "drivers.json")

V_RAIL = 19.0              # boost rail feeding the TAS5805M (electronics research, 2026-11-24)
V_PK_MAX = 0.95 * V_RAIL   # BTL peak output swing (~18 V)
I_PK_MAX = 4.5             # peak output current: 5 A OCP minus 10 % margin
BATTERY_AVG_MAX_W = 40.0   # total average battery draw budget (all amps + system)
AMP_CHAIN_EFF = 0.75       # boost (~0.9) x class-D (~0.85) efficiency for the battery estimate
QL = 10.0                  # box leakage Q (printed box with gaskets; 7 = leaky, 15+ = tight)
CREST = 3.0                # peak/rms for pink noise after DRC/limiter (~9.5 dB)
F3_TARGET = 63.0           # DSP target F3 (gives F6 ~ 55 Hz with the target below)
SUBSONIC_RATIO = 0.45      # 2nd-order Butterworth subsonic HPF at 0.45 * F3_TARGET
FX_HZ = 2500.0             # woofer/tweeter LR4 crossover used for the pink-noise estimate
PINK_REQ_DB = 90.0         # requirement (half space, 1 m)
MAX_ADD_MASS_X = 2.5       # cap added PR mass at 2.5x the bare PR Mms (rocking / sag)
EQ_FLOOR_RATIO = 0.75      # EQ gain rolls off at 24 dB/oct below 0.75*F3_TARGET (subsonic protection)
MAX_BOOST_DB = 18.0        # max DSP EQ boost relative to the 300-600 Hz passband (cannot fill the PR notch)

F = np.logspace(np.log10(10.0), np.log10(2000.0), 1200)

# Candidate driver sets: (label, woofer id, PR id, tweeter id)
SETS = [
    # 8-ohm woofers (electronics decision 2026-11-24: 6-8 ohm woofers on a 19 V rail)
    ("A8 budget : PLS-65F25AL02-08 + DMA58-PR", "PLS-65F25AL02-08", "DMA58-PR", "OT19NC00-04"),
    ("A8' Dayton: DMA70-8 + DMA70-PR", "DMA70-8", "DMA70-PR", "OT19NC00-04"),
    ("B8 rec.   : ND65-8 + DMA58-PR", "ND65-8", "DMA58-PR", "OT19NC00-04"),
    ("B8' bigPR : ND65-8 + DMA70-PR", "ND65-8", "DMA70-PR", "OT19NC00-04"),
    ("C8 premium: ND91-8 + DMA70-PR", "ND91-8", "DMA70-PR", "OT19NC00-04"),
    ("ref       : ND91-8 + DMA80-PR", "ND91-8", "DMA80-PR", "OT19NC00-04"),
    ("ref       : DMA70-8 + DMA58-PR", "DMA70-8", "DMA58-PR", "OT19NC00-04"),
    ("ref       : PC83-8 + DMA70-PR", "PC83-8", "DMA70-PR", "OT19NC00-04"),
    ("ref       : PLS-P830986 + DMA70-PR", "PLS-P830986", "DMA70-PR", "OT19NC00-04"),
    ("ref (OOS) : DMA80-8 + DMA80-PR", "DMA80-8", "DMA80-PR", "OT19NC00-04"),
    ("ref (wide): M3N + DMA70-PR", "M3N", "DMA70-PR", "OT19NC00-04"),
    # previous 4-ohm picks, now under the 4.5 A current limit (for comparison only)
    ("old B 4ohm: SLS-65S25PR03-04 + DMA58-PR", "SLS-65S25PR03-04", "DMA58-PR", "OT19NC00-04"),
    ("old A 4ohm: DMA70-4 + DMA70-PR", "DMA70-4", "DMA70-PR", "OT19NC00-04"),
]
VB_NOMINAL_L = 0.75        # estimated net internal volume (see research/drivers.md)


def load_parts(path=DRIVERS_JSON):
    with open(path) as fh:
        data = json.load(fh)
    return {p["id"]: p for p in data["parts"]}


def system(f, w_ts, p_ts, nd, np_, vb, m_add, ql=None):
    """Per volt (peak) of woofer drive: returns dict of complex arrays.

    v_d, v_p: cone velocities (outward +), x_d, x_p: displacements, p_ff: 1 m half-space pressure,
    fb, fp: closed-form tuning and PR notch frequencies.
    """
    w = 2 * np.pi * f
    s = 1j * w
    re_, le = w_ts["re_ohm"], (w_ts.get("le_h") or 0.0)
    bl, mms, cms, sd = w_ts["bl_tm"], w_ts["mms_kg"], w_ts["cms_m_per_n"], w_ts["sd_m2"]
    rms = w_ts["rms_kg_per_s"]
    ze = re_ + s * le
    zmd = rms + s * mms + 1.0 / (s * cms)

    cab = vb / (RHO * C ** 2)
    if np_ > 0:
        sp, cmp_ = p_ts["sd_m2"], p_ts["cms_m_per_n"]
        mmp = p_ts["mms_kg"] + m_add
        rmp = p_ts["rms_kg_per_s"]
        zmp = rmp + s * mmp + 1.0 / (s * cmp_)
        cap = cmp_ * sp ** 2 * np_
        map_ = mmp / sp ** 2 / np_
        fb = np.sqrt((1.0 / cap + 1.0 / cab) / map_) / (2 * np.pi)
        fp = 1.0 / (2 * np.pi * np.sqrt(mmp * cmp_))
        ypr = np_ * sp ** 2 / zmp
    else:
        sp, zmp, ypr = 0.0, None, 0.0
        fb = fp = float("nan")
    ql = QL if ql is None else ql
    wl = 2 * np.pi * (fb if np_ > 0 else w_ts["fs_hz"])
    ral = ql / (wl * cab)
    yb = s * cab + 1.0 / ral

    e = 1.0
    v_d = (bl * e / ze) / (zmd + bl ** 2 / ze + nd * sd ** 2 / (yb + ypr))
    p_box = -nd * sd * v_d / (yb + ypr)
    v_p = sp * p_box / zmp if np_ > 0 else np.zeros_like(v_d)
    u = nd * sd * v_d + np_ * sp * v_p
    p_ff = RHO * s * u / (2 * np.pi * 1.0)
    i_coil = (e - bl * v_d) / ze
    return dict(v_d=v_d, v_p=v_p, x_d=v_d / s, x_p=v_p / s, p_ff=p_ff, zin=e / i_coil,
                p_box=p_box, fb=fb, fp=fp)


def spl(p_peak):
    return 20 * np.log10(np.abs(p_peak) / np.sqrt(2) / P0 + 1e-30)


def f_at_level(f, level_db, ref_db, drop):
    """Lowest frequency above which the response stays within `drop` dB of ref (searching downward)."""
    rel = level_db - ref_db
    idx = np.where(rel < -drop)[0]
    idx = idx[f[idx] < 300]
    if len(idx) == 0:
        return f[0]
    k = idx[-1]
    # linear interpolation in log f
    x0, x1 = np.log(f[k]), np.log(f[k + 1])
    y0, y1 = rel[k] + drop, rel[k + 1] + drop
    return float(np.exp(x0 + (x1 - x0) * (-y0) / (y1 - y0))) if y1 != y0 else f[k]


def bw_hp_mag(f, fc, order):
    return 1.0 / np.sqrt(1.0 + (fc / f) ** (2 * order))


def dsp_target(f, f3=F3_TARGET):
    """Magnitude of the DSP target high-pass (BW4 at f3 * BW2 subsonic)."""
    return bw_hp_mag(f, f3, 4) * bw_hp_mag(f, SUBSONIC_RATIO * f3, 2)


def lr4_lp(f, fx=FX_HZ):
    return 1.0 / (1.0 + (f / fx) ** 4)


def limits(f, sysd, w_part, p_part):
    """Peak-voltage limits per frequency (arrays) and the sine max SPL."""
    v_amp = amp_vlimit(sysd)
    xw = w_part["ts"]["xmax_m"]
    xp = p_part["ts"]["xlim_model_m"] if p_part else np.inf
    v_x = xw / np.abs(sysd["x_d"])
    v_p = xp / np.maximum(np.abs(sysd["x_p"]), 1e-30)
    v_allowed = np.minimum(np.minimum(v_amp, v_x), v_p)
    amp_kind = np.where(v_amp >= V_PK_MAX - 1e-12, "amp V", "amp I")
    which = np.where(v_allowed == v_amp, amp_kind, np.where(v_allowed == v_x, "woofer Xmax", "PR Xmax"))
    return v_allowed, spl(sysd["p_ff"] * v_allowed), which, v_amp


def amp_vlimit(sysd):
    """Per-frequency peak voltage the amp can deliver: rail swing or OCP current limit."""
    return np.minimum(V_PK_MAX, I_PK_MAX * np.abs(sysd["zin"]))


def eq_design(sysd):
    """DSP EQ that drives the system toward the target, with boost capped at MAX_BOOST_DB.

    Returns (g, r, href): g = EQ gain (linear, relative to passband), r = realised acoustic response
    relative to the passband, href = passband pressure per volt (peak/peak).
    """
    h = np.abs(sysd["p_ff"])
    href = np.mean(h[(F > 300) & (F < 600)])
    g = dsp_target(F) * href / h
    g = np.minimum(g, 10 ** (MAX_BOOST_DB / 20.0))
    # below EQ_FLOOR_RATIO*F3 the EQ stops tracking the target and rolls off at 24 dB/oct
    # (a real DSP subsonic HPF): never boost into the PR notch / below-fb unloading region
    f_floor = EQ_FLOOR_RATIO * F3_TARGET
    g_floor = np.interp(f_floor, F, g)
    lo = F < f_floor
    g[lo] = np.minimum(g[lo], g_floor * (F[lo] / f_floor) ** 4)
    r = h * g / href
    return g, r, href


def dsp_ceiling(sysd, v_allowed):
    """Highest flat-passband sine SPL with the capped-boost DSP EQ (all f in 15-1000 Hz)."""
    g, r, href = eq_design(sysd)
    band = (F >= 15) & (F <= 1000)
    p_pb_pk = v_allowed[band] * href / g[band]               # passband peak Pa allowed by each f
    k = np.argmin(p_pb_pk)
    return float(spl(p_pb_pk[k])), float(F[band][k])


def realised_f3(sysd):
    _, r, _ = eq_design(sysd)
    rdb = 20 * np.log10(r)
    return f_at_level(F, rdb, 0.0, 3.0), f_at_level(F, rdb, 0.0, 6.0)


def pink_estimate(sysd, w_part, p_part, nd, with_power=False):
    """Long-term pink-noise SPL (half space, 1 m) through the capped-boost DSP EQ + LR4 crossover.

    Pink noise = equal power per 1/3 octave, 20 Hz - 20 kHz, then shaped by the realised response.
    Woofer bands must satisfy: CREST*V_rms <= V_PK_MAX, CREST*I_rms <= I_PK_MAX,
    voice-coil power I_rms^2*Re <= rated RMS power, CREST*x_rms <= Xmax (woofer) and <= xlim (PR).
    Tweeter bands are assumed to have headroom. Also returns the average electrical power per
    woofer at that level (W) for the battery budget.
    """
    g, r, href = eq_design(sysd)
    fc = 1000.0 * 2.0 ** (np.arange(-17, 14) / 3.0)          # 31 bands
    lp = 1.0 / (1.0 + (fc / FX_HZ) ** 4)
    rb = np.where(fc < 1000, np.interp(np.log(fc), np.log(F), r), 1.0)
    tot_rel = 10 * np.log10(np.sum(rb ** 2))
    gb = np.interp(np.log(fc), np.log(F), g) * lp
    xd = np.interp(np.log(fc), np.log(F), np.abs(sysd["x_d"]))
    xpr = np.interp(np.log(fc), np.log(F), np.abs(sysd["x_p"]))
    zr = np.interp(np.log(fc), np.log(F), sysd["zin"].real)
    zi = np.interp(np.log(fc), np.log(F), sysd["zin"].imag)
    zb = zr + 1j * zi
    v_b = P0 * gb / href                                      # rms V per band for 0 dB band level
    v_rms = np.sqrt(np.sum(v_b ** 2))
    x_rms = np.sqrt(np.sum((xd * v_b) ** 2))
    xp_rms = np.sqrt(np.sum((xpr * v_b) ** 2))
    i_b = v_b / np.abs(zb)
    i_rms = np.sqrt(np.sum(i_b ** 2))
    p_coil = np.sum(i_b ** 2) * w_part["ts"]["re_ohm"]
    p_elec = np.sum(i_b ** 2 * zb.real)
    ts = w_part["ts"]
    cand = {
        "amp V": V_PK_MAX / (CREST * v_rms),
        "amp I": I_PK_MAX / (CREST * i_rms),
        "woofer thermal": np.sqrt(ts["power_rms_w"] / p_coil),
        "woofer Xmax": ts["xmax_m"] / (CREST * x_rms),
    }
    if p_part is not None:
        cand["PR Xmax"] = p_part["ts"]["xlim_model_m"] / (CREST * xp_rms)
    lim = min(cand, key=cand.get)
    g_lim = cand[lim]
    if with_power:
        return float(20 * np.log10(g_lim) + tot_rel), lim, float(p_elec * g_lim ** 2)
    return float(20 * np.log10(g_lim) + tot_rel), lim


def optimise(w_part, p_part, nd, np_, vb):
    """Sweep PR added mass; return best (by pink-noise estimate) result dict."""
    if p_part is None:
        masses = [0.0]
    else:
        masses = np.arange(0.0, MAX_ADD_MASS_X * p_part["ts"]["mms_kg"] + 1e-9, 0.25e-3)
    best = None
    for m in masses:
        sysd = system(F, w_part["ts"], p_part["ts"] if p_part else None, nd, np_, vb, m)
        _, max_spl, which, _ = limits(F, sysd, w_part, p_part)
        pink, lim, p_w = pink_estimate(sysd, w_part, p_part, nd, with_power=True)
        v_allowed, _, _, _ = limits(F, sysd, w_part, p_part)
        ceil, fceil = dsp_ceiling(sysd, v_allowed)
        r = dict(m_add=m, sys=sysd, max_spl=max_spl, which=which, pink=pink, pink_lim=lim, p_woofer_avg=p_w,
                 ceil=ceil, fceil=fceil)
        if best is None or pink > best["pink"] + 1e-9:
            best = r
    return best


def summarise(label, w_part, p_part, nd, np_, vb, r):
    sysd = r["sys"]
    lvl = spl(sysd["p_ff"])                                   # 1 V peak
    ref = np.mean(lvl[(F > 300) & (F < 600)])
    f3 = f_at_level(F, lvl, ref, 3.0)
    f6 = f_at_level(F, lvl, ref, 6.0)
    out = dict(label=label, vb_l=vb * 1e3, m_add_g=r["m_add"] * 1e3, fb=sysd["fb"], fp=sysd["fp"],
               f3_natural=f3, f6_natural=f6, pink_db=r["pink"], pink_limit=r["pink_lim"],
               dsp_ceiling_db=r["ceil"], dsp_ceiling_f=r["fceil"])
    out["f3_dsp"], out["f6_dsp"] = realised_f3(sysd)
    for fq in (50, 63, 80, 100, 150, 300):
        k = np.argmin(np.abs(F - fq))
        out["maxspl_%d" % fq] = float(r["max_spl"][k])
        out["limit_%d" % fq] = str(r["which"][k])
    v_amp = amp_vlimit(sysd)
    k = np.argmin(np.abs(F - 400))
    out["passband_spl_max"] = float(spl(sysd["p_ff"][k] * v_amp[k]))
    out["amp_w_into_woofer_at_400hz"] = float((v_amp[k] / np.sqrt(2)) ** 2 * np.real(1 / sysd["zin"][k]))
    out["zmin_ohm"] = float(np.min(np.abs(sysd["zin"][F < 1000])))
    out["woofer_avg_w_at_pink"] = r["p_woofer_avg"]
    # battery: 2 woofers + tweeters (~10 % of woofer power) through the amp chain, plus ~2 W system
    out["battery_avg_w_at_pink"] = 2 * r["p_woofer_avg"] * 1.1 / AMP_CHAIN_EFF + 2.0
    return out


def required_volume(w_part, p_part, nd, np_, vbs):
    for vb in vbs:
        r = optimise(w_part, p_part, nd, np_, vb)
        f3, f6 = realised_f3(r["sys"])
        if r["pink"] >= PINK_REQ_DB and f3 <= 65.0 and f6 <= 55.0 + 1.0:
            return vb, r
    return None, None


def self_test(parts):
    """Sanity checks against closed-form results."""
    w = parts["DMA70-4"]["ts"]
    vb = 0.5e-3
    sysd = system(F, w, None, 1, 0, vb, 0.0, ql=1e9)
    zin = np.abs(sysd["zin"])
    band = F < 1000
    fc_lem = F[band][np.argmax(zin[band])]
    fc_th = w["fs_hz"] * np.sqrt(1 + w["vas_m3"] / vb)
    assert abs(fc_lem - fc_th) / fc_th < 0.02, (fc_lem, fc_th)
    # two drivers in 2*vb must behave like one in vb (per-driver excursion identical)
    s2 = system(F, w, None, 2, 0, 2 * vb, 0.0, ql=1e9)
    assert np.allclose(np.abs(s2["x_d"]), np.abs(sysd["x_d"]), rtol=1e-9)
    # PR notch: at fp the woofer-plus-PR output must have a deep minimum
    p = parts["DMA70-PR"]["ts"]
    s3 = system(F, w, p, 2, 2, 0.75e-3, 10e-3)
    k = np.argmin(np.abs(F - s3["fp"]))
    lvl = spl(s3["p_ff"])
    assert lvl[k] < np.max(lvl) - 15, "no PR notch at fp"
    return fc_lem, fc_th


def plot(results, path_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                  # pragma: no cover
        print("matplotlib unavailable (%s); skipping plots" % exc)
        return
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    for lab, w_part, p_part, r in results:
        sysd = r["sys"]
        ax[0, 0].semilogx(F, spl(sysd["p_ff"] * amp_vlimit(sysd)), label=lab)
        ax[0, 1].semilogx(F, r["max_spl"], label=lab)
        _, rr, _ = eq_design(sysd)
        ax[0, 1].semilogx(F, r["ceil"] + 20 * np.log10(rr), "--", lw=0.8, color=ax[0, 1].lines[-1].get_color())
        v_allowed, _, _, _ = limits(F, sysd, w_part, p_part)
        ax[1, 0].semilogx(F, np.abs(sysd["x_d"]) * v_allowed * 1e3, label=lab + " woofer")
        ax[1, 1].semilogx(F, np.abs(sysd["x_p"]) * v_allowed * 1e3, label=lab + " PR")
    ax[0, 0].set_title("No-EQ SPL at full amp output (18 V pk / 4.5 A pk), 1 m, half space")
    ax[0, 1].set_title("Sine max SPL (solid) and DSP-target ceiling (dashed)")
    ax[1, 0].set_title("Woofer excursion at the max-SPL voltage [mm]")
    ax[1, 1].set_title("PR excursion at the max-SPL voltage [mm]")
    for a in ax.flat:
        a.set_xlim(20, 1000)
        a.grid(True, which="both", alpha=0.3)
        a.set_xlabel("Hz")
    ax[0, 0].set_ylim(60, 110)
    ax[0, 1].set_ylim(60, 110)
    ax[0, 0].set_ylabel("dB SPL")
    ax[0, 0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path_png, dpi=110)
    print("wrote", path_png)


def main(argv):
    parts = load_parts()
    fc_lem, fc_th = self_test(parts)
    print("self-test OK: sealed fc LEM %.1f Hz vs closed form %.1f Hz" % (fc_lem, fc_th))
    print("Assumptions: 2 woofers + 2 PRs in one shared box, amp %.1f V pk / %.1f A pk per woofer (19 V rail BTL),"
          " QL=%.0f, half-space 1 m, pink crest %.1f, DSP target F3=%.0f Hz (BW4 + BW2 subsonic @ %.0f Hz), LR4 @ %.0f Hz"
          % (V_PK_MAX, I_PK_MAX, QL, CREST, F3_TARGET, SUBSONIC_RATIO * F3_TARGET, FX_HZ))
    t = dsp_target(F)
    tdb = 20 * np.log10(t)
    print("DSP target: F3 = %.1f Hz, F6 = %.1f Hz" % (F[np.argmin(np.abs(tdb + 3))], F[np.argmin(np.abs(tdb + 6))]))
    vbs = np.round(np.arange(0.30, 2.01, 0.05), 3) * 1e-3
    results, rows = [], []
    for lab, wid, pid, tid in SETS:
        w_part, p_part = parts[wid], parts[pid]
        r = optimise(w_part, p_part, 2, 2, VB_NOMINAL_L * 1e-3)
        row = summarise(lab, w_part, p_part, 2, 2, VB_NOMINAL_L * 1e-3, r)
        vreq, rreq = required_volume(w_part, p_part, 2, 2, vbs)
        row["vb_required_l"] = vreq * 1e3 if vreq else None
        row["m_add_at_required_g"] = rreq["m_add"] * 1e3 if rreq else None
        row["fb_at_required"] = rreq["sys"]["fb"] if rreq else None
        # sealed comparison (same volume, no PR)
        rs = optimise(w_part, None, 2, 0, VB_NOMINAL_L * 1e-3)
        row["sealed_pink_db"] = rs["pink"]
        row["sealed_limit"] = rs["pink_lim"]
        row["sealed_f3_dsp"] = realised_f3(rs["sys"])[0]
        rows.append(row)
        results.append((lab.split(":")[0].strip() + " " + wid + "/" + pid, w_part, p_part, r))

    print("\n=== Net box %.2f L (2 woofers + 2 PRs shared), PR mass optimised for pink-noise SPL ===" % VB_NOMINAL_L)
    hdr = ("set", "m_add g/PR", "fb", "fp", "F3 nat", "F6 nat", "pass@max", "max50", "max63", "max80", "max100",
           "DSPceil", "@Hz", "F3/F6 dsp", "pink", "pink lim", "sealed pink", "Vb req L")
    print(" | ".join(hdr))
    for r in rows:
        print("%s | %.1f | %.0f | %.0f | %.0f | %.0f | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %.0f | %.0f/%.0f | %.1f | %s | %.1f (%s, F3 %.0f) | %s" % (
            r["label"], r["m_add_g"], r["fb"], r["fp"], r["f3_natural"], r["f6_natural"], r["passband_spl_max"],
            r["maxspl_50"], r["maxspl_63"], r["maxspl_80"], r["maxspl_100"], r["dsp_ceiling_db"], r["dsp_ceiling_f"], r["f3_dsp"], r["f6_dsp"],
            r["pink_db"], r["pink_limit"], r["sealed_pink_db"], r["sealed_limit"], r["sealed_f3_dsp"],
            ("%.2f (m_add %.1f g, fb %.0f Hz)" % (r["vb_required_l"], r["m_add_at_required_g"], r["fb_at_required"]))
            if r["vb_required_l"] else "> 2.0"))
    print("\namp power into woofer at 400 Hz / |Z|min / avg W per woofer at pink limit / est. battery W:")
    for r in rows:
        print("  %s: %.1f W / %.1f ohm / %.2f W / %.1f W" % (r["label"], r["amp_w_into_woofer_at_400hz"], r["zmin_ohm"],
                                                         r["woofer_avg_w_at_pink"], r["battery_avg_w_at_pink"]))
    print("\nlimiting mechanism at 50/63/80/100 Hz:")
    for r in rows:
        print("  %s: %s / %s / %s / %s" % (r["label"], r["limit_50"], r["limit_63"], r["limit_80"], r["limit_100"]))

    # volume sweep for the three main sets
    print("\n=== Volume sweep (pink-noise estimate dB, half space; PR mass re-optimised each point) ===")
    sweep_vbs = [0.5, 0.6, 0.75, 0.9, 1.0, 1.2]
    print("Vb [L]: " + "  ".join("%5.2f" % v for v in sweep_vbs))
    for lab, wid, pid, tid in SETS[:5] + SETS[-2:-1]:
        vals = [optimise(parts[wid], parts[pid], 2, 2, v * 1e-3)["pink"] for v in sweep_vbs]
        print("%-42s " % lab + "  ".join("%5.1f" % v for v in vals))

    out_json = os.path.join(HERE, "pr_alignment_firstpass_results.json")
    with open(out_json, "w") as fh:
        json.dump({"assumptions": dict(V_RAIL=V_RAIL, V_PK_MAX=V_PK_MAX, I_PK_MAX=I_PK_MAX, QL=QL, CREST=CREST, F3_TARGET=F3_TARGET,
                                       SUBSONIC_RATIO=SUBSONIC_RATIO, FX_HZ=FX_HZ, VB_NOMINAL_L=VB_NOMINAL_L,
                                       space="half (2pi), 1 m"),
                   "rows": rows}, fh, indent=1, default=float)
    print("wrote", out_json)
    plot([results[i] for i in (0, 2, 4, len(results) - 2)], os.path.join(HERE, "pr_alignment_firstpass.png"))


if __name__ == "__main__":
    main(sys.argv[1:])
