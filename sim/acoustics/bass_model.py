"""Lumped-element (Thiele/Small) model of the bass system: 2 woofers + 2 passive radiators in one box.

Reusable by A1 (alignment), A3 (BEM source strengths) and A5 (system response).

Circuit, per woofer, in the mechanical/acoustic impedance analogy (all small-signal, linear):

    e --[Re + jwLe]--(Bl)--> woofer: Zmd = Rms + jwMms + 1/(jwCms)  --Sd--> box node p_box
    box node:   Cab = Vb_eff/(rho c^2) with absorption Rab in series (Q_A),
                leakage Ral to outside (Q_L),
                Np passive radiators: Zmp = Rmp + jw(Mmp + m_add) + 1/(jwCmp), area Sp.
    radiation:  default none (published Mms includes the air load; see `radiation` below).

Conventions: phasors e^{+jwt}; v_d and v_p are cone velocities, POSITIVE OUTWARD (out of the box).
Pressure at r in half space (2*pi, speaker on a table): |p| = rho*w*|U|/(2*pi*r), U = Nd*Sd*v_d + Np*Sp*v_p.
All quantities are per 1 V PEAK of drive on each woofer (both woofers driven identically).
"""
import numpy as np
from scipy.special import j1, struve

RHO, C0, P_REF = 1.20, 343.0, 20e-6

# Amplifier (TAS5805M, BTL, PVDD = 18.0 V). The woofer channel limiter caps the output at 15.5 V peak
# (headroom below the ~17.1 V BTL clipping point at 95 % swell). The 5 A OCP less 10 % gives 4.5 A peak.
PVDD = 18.0
V_PK_MAX = 15.5
I_PK_MAX = 4.5


def ts_from_part(part):
    """T/S dict (SI) from a drivers.json part entry."""
    return dict(part["ts"])


def baffled_piston_zrad(f, S, rho=RHO, c=C0):
    """Mechanical radiation impedance of a rigid circular piston in an infinite baffle (one side), N*s/m."""
    a = np.sqrt(S / np.pi)
    k = 2 * np.pi * f / c
    x = 2 * k * a
    R1 = 1 - 2 * j1(x) / x
    X1 = 2 * struve(1, x) / x
    return rho * c * S * (R1 + 1j * X1)


def system(f, w, p, vb, m_add=0.0, ql=10.0, qa=np.inf, nd=2, np_=2, vb_factor=1.0, radiation="none",
           rho=RHO, c=C0, leak_ref="fb", r=1.0):
    """Solve the lumped bass circuit per 1 V peak on each woofer.

    w, p : woofer / PR T/S dicts (drivers.json 'ts'); p=None or np_=0 gives a sealed box.
    vb : net box volume [m^3]; vb_factor scales the acoustic compliance (polyfill/zeolite what-ifs).
    m_add : mass added to EACH PR [kg]. ql, qa : leakage and absorption Q at the reference frequency
    (fb for a PR box, the sealed resonance fc otherwise; leak_ref='fc' uses fc always, as electroacPy does).
    radiation : 'none' (default) or 'baffled_piston' (adds the one-sided radiation impedance of each
    diaphragm as an extra mechanical load; used for the electroacPy cross-check).
    Returns a dict of complex arrays (per volt peak) and scalars.
    """
    f = np.asarray(f, float)
    om = 2 * np.pi * f
    s = 1j * om
    re_, le = w["re_ohm"], (w.get("le_h") or 0.0)
    bl, mms, cms, sd, rms = w["bl_tm"], w["mms_kg"], w["cms_m_per_n"], w["sd_m2"], w["rms_kg_per_s"]
    ze = re_ + s * le
    zmd = rms + s * mms + 1.0 / (s * cms)
    if radiation == "baffled_piston":
        zmd = zmd + baffled_piston_zrad(f, sd, rho, c)

    cab = vb * vb_factor / (rho * c ** 2)
    fc = w["fs_hz"] * np.sqrt(1 + nd * rho * c ** 2 * sd ** 2 * cms / (rho * c ** 2) / cab)  # sealed resonance
    if p is not None and np_ > 0:
        sp, cmp_, rmp = p["sd_m2"], p["cms_m_per_n"], p["rms_kg_per_s"]
        mmp = p["mms_kg"] + m_add
        zmp = rmp + s * mmp + 1.0 / (s * cmp_)
        if radiation == "baffled_piston":
            zmp = zmp + baffled_piston_zrad(f, sp, rho, c)
        cap = cmp_ * sp ** 2 * np_            # acoustic compliance of all PR suspensions
        map_ = mmp / sp ** 2 / np_            # acoustic mass of all PRs
        fb = np.sqrt((1.0 / cap + 1.0 / cab) / map_) / (2 * np.pi)   # box tuning (Helmholtz-like)
        fp = 1.0 / (2 * np.pi * np.sqrt(mmp * cmp_))                 # PR notch (PR free resonance)
        ypr = np_ * sp ** 2 / zmp             # acoustic admittance of the PRs (box -> outside)
    else:
        sp, zmp, ypr, fb, fp = 0.0, None, 0.0, float("nan"), float("nan")
    w_ref = 2 * np.pi * (fb if (np_ > 0 and leak_ref == "fb") else fc)
    ral = ql / (w_ref * cab)
    rab = 0.0 if not np.isfinite(qa) else 1.0 / (w_ref * cab * qa)
    yb = 1.0 / (rab + 1.0 / (s * cab)) + 1.0 / ral   # box: (Rab + Cab) branch || leakage

    e = 1.0
    # woofer velocity: electrical force / (mech impedance + motional + box load seen by all woofers)
    v_d = (bl * e / ze) / (zmd + bl ** 2 / ze + nd * sd ** 2 / (yb + ypr))
    p_box = -nd * sd * v_d / (yb + ypr)          # outward cone motion lowers the box pressure
    v_p = sp * p_box / zmp if zmp is not None else np.zeros_like(v_d)
    u = nd * sd * v_d + np_ * sp * v_p
    p_hs = rho * s * u / (2 * np.pi * r)         # half-space pressure (peak) at r
    i_coil = (e - bl * v_d) / ze
    return dict(f=f, v_d=v_d, v_p=v_p, x_d=v_d / s, x_p=v_p / s, u=u, p_hs=p_hs, p_box=p_box,
                zin=e / i_coil, i=i_coil, fb=float(fb), fp=float(fp), fc=float(fc), cab=cab)


def spl_pk(p_peak):
    """dB SPL of a peak-amplitude phasor (sine rms = peak/sqrt 2)."""
    return 20 * np.log10(np.abs(p_peak) / np.sqrt(2) / P_REF + 1e-30)


def f_at_level(f, level_db, ref_db, drop, fmax=300.0):
    """Highest frequency below fmax where the response falls `drop` dB under ref (log-f interpolation)."""
    rel = np.asarray(level_db) - ref_db
    idx = np.where(rel < -drop)[0]
    idx = idx[f[idx] < fmax]
    if len(idx) == 0:
        return float(f[0])
    k = idx[-1]
    x0, x1 = np.log(f[k]), np.log(f[k + 1])
    y0, y1 = rel[k] + drop, rel[k + 1] + drop
    return float(np.exp(x0 + (x1 - x0) * (-y0) / (y1 - y0))) if y1 != y0 else float(f[k])


# ------------------------------------------------------------------ amplifier / excursion limits
def amp_vlimit(sysd, v_max=V_PK_MAX, i_max=I_PK_MAX):
    return np.minimum(v_max, i_max * np.abs(sysd["zin"]))


def sine_limits(sysd, w, p, v_max=V_PK_MAX, i_max=I_PK_MAX):
    """Per-frequency allowed peak voltage (min of amp V, amp I, woofer Xmax, PR limit) and the limiter name."""
    v_amp = amp_vlimit(sysd, v_max, i_max)
    v_x = w["xmax_m"] / np.abs(sysd["x_d"])
    v_p = (p["xlim_model_m"] / np.maximum(np.abs(sysd["x_p"]), 1e-30)) if p is not None else np.full_like(v_x, np.inf)
    stack = np.vstack([np.full_like(v_x, v_max), i_max * np.abs(sysd["zin"]), v_x, v_p])
    names = np.array(["amp V", "amp I", "woofer Xmax", "PR Xmax"])
    k = np.argmin(stack, axis=0)
    v_allowed = stack[k, np.arange(stack.shape[1])]
    return v_allowed, names[k]


# ------------------------------------------------------------------ DSP target and EQ
def bw_hp_mag(f, fc, order):
    return 1.0 / np.sqrt(1.0 + (fc / f) ** (2 * order))


def dsp_target(f, f3=63.0, subsonic_ratio=0.45):
    """Target acoustic high-pass: Butterworth 4th order at f3 times a 2nd-order Butterworth subsonic."""
    return bw_hp_mag(f, f3, 4) * bw_hp_mag(f, subsonic_ratio * f3, 2)


def ideal_eq(f, sysd, f3=63.0, max_boost_db=18.0, floor_ratio=0.75, band=(300, 600)):
    """Ideal (magnitude-only) EQ: target / natural response, boost capped, 24 dB/oct roll-off below
    floor_ratio*f3 so the EQ never chases the PR notch, faded to 0 dB over the reference band.
    Returns (g, href) with g linear, 0 dB = passband."""
    h = np.abs(sysd["p_hs"])
    sel = (f > band[0]) & (f < band[1])
    href = np.mean(h[sel])
    g = dsp_target(f, f3) * href / h
    g = np.minimum(g, 10 ** (max_boost_db / 20.0))
    f_floor = floor_ratio * f3
    g_floor = np.interp(f_floor, f, g)
    lo = f < f_floor
    g[lo] = np.minimum(g[lo], g_floor * (f[lo] / f_floor) ** 4)
    # the bass EQ fades to 0 dB across the 300-600 Hz reference band and is flat above it; anything the
    # woofer does higher up (Le roll-off, baffle step, crossover) is the job of the system EQ in A5
    wfade = np.clip(np.log(band[1] / f) / np.log(band[1] / band[0]), 0.0, 1.0)
    g = 10 ** (wfade * np.log10(g))
    return g, href


# RBJ audio-EQ-cookbook biquads (b, a normalised) ---------------------------------------------
def rbj(kind, f0, fs, q=0.7071, gain_db=0.0):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    if kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        sa = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sa), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sa)]
        a = [(A + 1) + (A - 1) * cw + sa, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sa]
    elif kind == "highshelf":
        sa = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
        a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    else:
        raise ValueError(kind)
    b, a = np.array(b) / a[0], np.array(a) / a[0]
    return np.concatenate([b, a])


def sos_response(sos, f, fs):
    from scipy.signal import sosfreqz
    _, h = sosfreqz(np.atleast_2d(sos), worN=np.asarray(f, float), fs=fs)
    return h


# ------------------------------------------------------------------ pink-noise estimate
def third_octave_centres():
    return 1000.0 * 2.0 ** (np.arange(-17, 14) / 3.0)      # 20 Hz .. 20 kHz, 31 bands


def pink_estimate(f, sysd, w, p, g, href, crest=3.0, fx=2500.0, v_max=V_PK_MAX, i_max=I_PK_MAX):
    """Long-term pink-noise SPL (half space, 1 m) the bass system can sustain through EQ g and an LR4 low-pass.

    Pink = equal power per 1/3 octave 20 Hz-20 kHz, shaped by the realised acoustic response (bands above 1 kHz
    are assumed flat after the tweeter/crossover EQ). The woofer drive per band must satisfy
    crest*V_rms <= v_max, crest*I_rms <= i_max, I_rms^2*Re <= rated RMS power, crest*x_rms <= Xmax and
    crest*x_pr,rms <= PR limit. Returns (SPL dB, limiting mechanism, average electrical power per woofer W).
    """
    fc = third_octave_centres()
    lp = 1.0 / (1.0 + (fc / fx) ** 4)                       # LR4 low-pass magnitude
    lf = np.log(f)
    r = np.abs(sysd["p_hs"]) * g / href                      # realised response rel. passband
    rb = np.where(fc < 1000, np.interp(np.log(fc), lf, r), 1.0)
    tot_rel = 10 * np.log10(np.sum(rb ** 2))
    gb = np.interp(np.log(fc), lf, g) * lp
    ip = lambda a: np.interp(np.log(fc), lf, a)
    xd, xpr = ip(np.abs(sysd["x_d"])), ip(np.abs(sysd["x_p"]))
    zb = ip(sysd["zin"].real) + 1j * ip(sysd["zin"].imag)
    # rms volts per band that give 0 dB SPL in that band: band rms pressure = P_REF -> V = P_REF*sqrt2 / (href/sqrt2)?
    # href is peak Pa per peak V, i.e. also rms Pa per rms V, so V_rms = P_REF * gb / href.
    v_b = P_REF * gb / href
    v_rms = np.sqrt(np.sum(v_b ** 2))
    x_rms = np.sqrt(np.sum((xd * v_b) ** 2))
    xp_rms = np.sqrt(np.sum((xpr * v_b) ** 2))
    i_b = v_b / np.abs(zb)
    i_rms = np.sqrt(np.sum(i_b ** 2))
    cand = {"amp V": v_max / (crest * v_rms), "amp I": i_max / (crest * i_rms),
            "woofer thermal": np.sqrt(w["power_rms_w"] / (np.sum(i_b ** 2) * w["re_ohm"])),
            "woofer Xmax": w["xmax_m"] / (crest * x_rms)}
    if p is not None:
        cand["PR Xmax"] = p["xlim_model_m"] / (crest * xp_rms)
    lim = min(cand, key=cand.get)
    gl = cand[lim]
    p_elec = float(np.sum(i_b ** 2 * zb.real) * gl ** 2)
    return float(20 * np.log10(gl) + tot_rel), lim, p_elec, {k: float(20 * np.log10(v) + tot_rel) for k, v in cand.items()}
