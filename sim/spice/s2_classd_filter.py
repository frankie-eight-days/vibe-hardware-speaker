"""S2: TAS5805M BTL output filter (10 uH + 1 uF per leg, 768 kHz) into real driver impedances.

Questions
 1. Frequency response of the LC filter into the ND65-8 woofer and OT19NC00-04 tweeter
    electrical models vs resistive 8 / 4 Ohm loads (does the tweeter EQ need correcting, does
    the woofer channel peak?).
 2. Ripple current at the switching frequency for BD and Hybrid/1SPW modulation (behavioural
    PWM), and how much of it reaches the drivers.
 3. Peak inductor current vs Isat (5.5 A) and the TAS5805M OCP (5 A) at the spec's limiter
    ceilings (woofer 15.5 V pk, tweeter 8 V pk) and if the tweeter limiter fails (hard clip).

Method: ngspice AC + transient. Each BTL leg = ideal PWM switch (B-source) + 180 mOhm RDS(on)
-> 10 uH (68 mOhm DCR, 2 pF parasitic) -> 1 uF X7R to GND (0.75 uF effective at 9 V bias,
5 mOhm ESR, 0.6 nH ESL). The driver is a T/S electrical model across SPK_P/SPK_N:
Re + Le in series with the motional parallel R-L-C (Res = Re Qms/Qes, Lces = Res/(2 pi fs Qms),
Cmes = Qms/(2 pi fs Res)).
"""
from __future__ import annotations

import json

import numpy as np

from common import ROOT, RESULTS, NETLISTS, run_ngspice, use_style, savefig, write_csv, write_json

PVDD = 18.0
FSW = 768e3
L0, DCR, CPAR = 10e-6, 68e-3, 2e-12
C_NOM, C_EFF, C_ESR, C_ESL = 1.0e-6, 0.75e-6, 5e-3, 0.6e-9
RDS = 0.18
ISAT, IOCP = 5.5, 5.0

drv = {d["id"]: d for d in json.loads((ROOT / "research" / "drivers.json").read_text())["parts"]}


def ts_subckt(name, pid):
    ts = drv[pid]["ts"]
    re, le, fs, qms, qes = ts["re_ohm"], ts["le_h"], ts["fs_hz"], ts["qms"], ts["qes"]
    res = re * qms / qes
    lces = res / (2 * np.pi * fs * qms)
    cmes = qms / (2 * np.pi * fs * res)
    return (f".subckt {name} a b\n* {pid}: Re={re} Le={le} fs={fs} Qms={qms} Qes={qes}\n"
            f"RE a n1 {re}\nLE n1 n2 {le}\nRES n2 b {res:.4g}\nLCES n2 b {lces:.4g}\n"
            f"CMES n2 b {cmes:.4g}\n.ends {name}\n"), dict(Re=re, Le=le, fs=fs, Res=res, Lces=lces, Cmes=cmes)


SUBS = {}
for nm, pid in (("WOOFER", "ND65-8"), ("TWEETER", "OT19NC00-04")):
    SUBS[nm] = ts_subckt(nm, pid)

LOADS = {
    "ND65-8 woofer model": "XLD spk_pl spk_n WOOFER",
    "OT19NC00-04 tweeter model": "XLD spk_pl spk_n TWEETER",
    "8 Ω resistor": "RLD spk_pl spk_n 8",
    "4 Ω resistor": "RLD spk_pl spk_n 4",
    "open (no load)": "RLD spk_pl spk_n 1Meg",
}


def filt(c):
    return f"""RDSP sw_p o_p {RDS}
VILP o_p o_pi 0
LP o_pi lp {L0}
RLP lp spk_p {DCR}
CPP o_pi spk_p {CPAR}
CFP spk_p cfp {c}
RCP cfp cfp2 {C_ESR}
LCP cfp2 0 {C_ESL}
RDSN sw_n o_n {RDS}
VILN o_n o_ni 0
LN o_ni ln {L0}
RLN ln spk_n {DCR}
CPN o_ni spk_n {CPAR}
VSPK spk_p spk_pl 0
CFN spk_n cfn {c}
RCN cfn cfn2 {C_ESR}
LCN cfn2 0 {C_ESL}
"""


def ac_run(load_key, c):
    subs = SUBS["WOOFER"][0] + SUBS["TWEETER"][0]
    net = f"""* S2 AC: BTL LC filter, load = {load_key}, C = {c}
{subs}
VP sw_p 0 DC 9 AC 0.5
VN sw_n 0 DC 9 AC -0.5
{filt(c)}{LOADS[load_key]}
.ac dec 200 10 2Meg
.end
"""
    tag = load_key.split()[0].replace("-", "").replace("Ω", "R").replace("(", "")
    d = run_ngspice(net, f"s2_ac_{tag}_{int(c * 1e9)}n")
    f = d["frequency"].real
    h = d["v(spk_p)"] - d["v(spk_n)"]
    return f, h, None


def zload_analytic(f, key):
    w = 2j * np.pi * f
    if "resistor" in key:
        return np.full_like(f, float(key.split()[0]), dtype=complex)
    if key.startswith("open"):
        return np.full_like(f, 1e6, dtype=complex)
    p = SUBS["WOOFER" if "woofer" in key else "TWEETER"][1]
    zm = 1 / (1 / p["Res"] + 1 / (w * p["Lces"]) + w * p["Cmes"])
    return p["Re"] + w * p["Le"] + zm


def pwm_run(name, mod, m_amp, f_sig, load_key, t_stop, d0=0.14):
    """Behavioural PWM. tri: 0..1 triangle at FSW. BD: dP = 0.5 + m/2, dN = 0.5 - m/2.
    1SPW (the low-power state of TI 'Hybrid'): the idle duty d0 on both legs, and only one leg
    modulates (dP = d0 + m for m>0, dN = d0 - m for m<0)."""
    subs = SUBS["WOOFER"][0] + SUBS["TWEETER"][0]
    if mod == "BD":
        dp = f"(0.5+0.5*{m_amp}*sin(2*pi*{f_sig}*time))"
        dn = f"(0.5-0.5*{m_amp}*sin(2*pi*{f_sig}*time))"
    else:
        m = f"({m_amp}*sin(2*pi*{f_sig}*time))"
        dp = f"({d0}+max({m},0))"
        dn = f"({d0}+max(-{m},0))"
    vcm = PVDD * (0.5 if mod == "BD" else d0)
    k = 400  # edge sharpness: transition over ~1/400 of the carrier ramp ~ 1.6 ns
    net = f"""* S2 PWM: {name}  modulation={mod} m={m_amp} f={f_sig} load={load_key}
{subs}
VTRI tri 0 PULSE(0 1 0 {0.5 / FSW:.6g} {0.5 / FSW:.6g} 1e-12 {1 / FSW:.6g})
BSWP sw_p 0 V = {PVDD}*(0.5+0.5*tanh({k}*({dp}-v(tri))))
BSWN sw_n 0 V = {PVDD}*(0.5+0.5*tanh({k}*({dn}-v(tri))))
{filt(C_EFF)}{LOADS[load_key]}
.options method=gear reltol=1e-4 abstol=1e-10
* start from the idle operating point: every node at the idle common-mode level, no current
.ic v(spk_p)={vcm} v(spk_n)={vcm} v(spk_pl)={vcm} v(cfp)=0 v(cfn)=0
+ v(o_p)={vcm} v(o_pi)={vcm} v(lp)={vcm} v(o_n)={vcm} v(o_ni)={vcm} v(ln)={vcm}
{'+ v(xld.n1)=' + str(vcm) + ' v(xld.n2)=' + str(vcm) if load_key.startswith(('ND', 'OT')) else ''}
.save v(spk_p) v(spk_n) i(vilp) i(viln) i(vspk)
.tran 5n {t_stop} 0 5n uic
.end
"""
    return run_ngspice(net, f"s2_pwm_{name}")


def cur(d, src):
    for k in (f"i({src})", f"{src}#branch"):
        if k in d:
            return d[k]
    raise KeyError(f"{src}: {list(d)}")


def main():
    plt = use_style()
    out = {"validation": {}, "ac": {}, "ripple": {}, "peaks": {}}
    # ---------------------------------------------------------------- AC
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.5, 5.4), sharex=True,
                                 gridspec_kw=dict(height_ratios=[2, 1.2]))
    csvcols = {}
    for key in LOADS:
        for c, ls in ((C_EFF, "-"), (C_NOM, ":")):
            f, h, _ = ac_run(key, c)
            mag = 20 * np.log10(abs(h))
            csvcols.setdefault("f_Hz", f)
            csvcols[f"H_dB[{key}|C={c * 1e6:.2f}uF]"] = mag
            i20 = np.argmin(abs(f - 20e3)); i10 = np.argmin(abs(f - 10e3))
            ipk = np.argmax(mag)
            out["ac"][f"{key} | C={c * 1e6:.2f} uF"] = dict(H_20k_dB=mag[i20], H_10k_dB=mag[i10],
                                                           peak_dB=mag[ipk], f_peak_Hz=f[ipk],
                                                           H_2k5_dB=mag[np.argmin(abs(f - 2.5e3))])
            if c == C_EFF:
                a1.semilogx(f, mag, ls, label=key)
            elif key.startswith(("4", "8")):
                a1.semilogx(f, mag, ls, color=a1.lines[-1].get_color(), lw=1.0)
    a1.axvspan(20, 20e3, color="0.92", zorder=-5)
    a1.set_ylim(-40, 25); a1.set_ylabel("|V_spk / V_PWM,diff| (dB)")
    a1.set_title("BTL output filter 2×(10 µH + 0.75 µF eff.) into driver models and resistors")
    a1.legend(fontsize=7, loc="lower left"); a1.text(25, 18, "dotted: resistors with 1.0 µF nominal", fontsize=7)
    # driver impedance curves
    fz = np.logspace(1, np.log10(2e6), 800)
    for key in ("ND65-8 woofer model", "OT19NC00-04 tweeter model"):
        z = zload_analytic(fz, key)
        a2.loglog(fz, abs(z), label=key.replace(" model", ""))
        csvcols_z = csvcols.setdefault("_z", {}); csvcols_z[key] = abs(z)
    a2.axhline(8, color="0.5", ls="--", lw=0.8); a2.axhline(4, color="0.5", ls=":", lw=0.8)
    a2.set_ylabel("|Z_driver| (Ω)"); a2.set_xlabel("Frequency (Hz)"); a2.legend(fontsize=7)
    savefig(fig, "s2_filter_response")
    z = csvcols.pop("_z")
    write_csv(RESULTS / "s2_filter_response.csv", list(csvcols.keys()), list(csvcols.values()))
    write_csv(RESULTS / "s2_driver_impedance.csv", ["f_Hz"] + [f"absZ_ohm[{k}]" for k in z],
              [fz] + list(z.values()))

    # validation vs hand calculation (spec_signal 3.1): f0 = 50.3 kHz, Q = 0.63 @ 4 Ohm, -0.44 dB @ 20 kHz
    Ld, Cd = 2 * L0, C_NOM / 2
    f0 = 1 / (2 * np.pi * np.sqrt(Ld * Cd))
    def h_ideal(f, R):
        s = 2j * np.pi * f
        return 1 / (1 + s * Ld / R + s * s * Ld * Cd)
    out["validation"] = dict(f0_hand_kHz=f0 / 1e3, Q4_hand=4 * np.sqrt(Cd / Ld), Q8_hand=8 * np.sqrt(Cd / Ld),
                             H20k_4ohm_ideal_dB=20 * np.log10(abs(h_ideal(20e3, 4))),
                             H20k_4ohm_spice_dB=out["ac"]["4 Ω resistor | C=1.00 uF"]["H_20k_dB"],
                             H20k_8ohm_ideal_dB=20 * np.log10(abs(h_ideal(20e3, 8))),
                             H20k_8ohm_spice_dB=out["ac"]["8 Ω resistor | C=1.00 uF"]["H_20k_dB"],
                             note="SPICE includes DCR 68 mOhm + RDS(on) 180 mOhm per leg (a -0.5 dB "
                                  "broadband loss into 4 Ohm), which the ideal formula omits")

    # ---------------------------------------------------------------- PWM idle ripple
    cases = [("idle_BD_tw", "BD", 0.0, 1e3, "OT19NC00-04 tweeter model"),
             ("idle_1SPW_tw", "1SPW", 0.0, 1e3, "OT19NC00-04 tweeter model"),
             ("idle_BD_wf", "BD", 0.0, 1e3, "ND65-8 woofer model"),
             ("idle_1SPW_wf", "1SPW", 0.0, 1e3, "ND65-8 woofer model"),
             ("sig_BD_tw", "BD", 4.0 / PVDD, 5e3, "OT19NC00-04 tweeter model"),
             ("sig_1SPW_tw", "1SPW", 4.0 / PVDD, 5e3, "OT19NC00-04 tweeter model")]
    fig, axs = plt.subplots(2, 1, figsize=(6.5, 4.6), sharex=True)
    for name, mod, m, fs_, key in cases:
        t_stop = 200e-6 if m == 0 else 1.2e-3
        d = pwm_run(name, mod, m, fs_, key, t_stop)
        t = d["time"]
        sel = t > t_stop - (20e-6 if m == 0 else 200e-6)
        ilp = cur(d, "vilp")[sel]
        ild = cur(d, "vspk")[sel]
        vd = (d["v(spk_p)"] - d["v(spk_n)"])[sel]
        tt = t[sel]
        # ultrasonic (> 100 kHz) part of the speaker current/voltage: FFT band power over the
        # window (an integer number of signal and carrier periods), uniform resampling first
        def band_rms(y):
            tu = np.linspace(tt[0], tt[-1], 2 ** 15, endpoint=False)
            yu = np.interp(tu, tt, y)
            w = np.hanning(len(yu))
            Y = np.fft.rfft((yu - yu.mean()) * w) / w.sum()
            fr = np.fft.rfftfreq(len(yu), tu[1] - tu[0])
            b = fr > 100e3
            return np.sqrt(2 * np.sum(abs(Y[b]) ** 2) / 1.5)  # Hann ENBW = 1.5 bins
        irms_us = band_rms(ild)
        vres_rms = band_rms(vd)
        re = drv["OT19NC00-04" if "tw" in name else "ND65-8"]["ts"]["re_ohm"]
        out["ripple"][name] = dict(modulation=mod, load=key, m=m, f_sig=fs_,
                                   IL_pp_A=float(np.ptp(ilp)) if m == 0 else None,
                                   IL_peak_A=float(np.max(abs(ilp))),
                                   spk_ultrasonic_rms_mA=irms_us * 1e3,
                                   spk_ultrasonic_vrms_mV=vres_rms * 1e3,
                                   P_ultrasonic_in_Re_mW=irms_us ** 2 * re * 1e3)
        if m == 0 and "tw" in name:
            tt0 = (tt - tt[0]) * 1e6
            axs[0].plot(tt0, ilp, label=f"{mod}: leg inductor current")
            axs[1].plot(tt0, ild * 1e3, label=f"{mod}: tweeter current")
            write_csv(RESULTS / f"s2_{name}.csv", ["t_s", "iL_leg_A", "i_spk_A", "v_spk_diff_V"],
                      [tt, ilp, ild, vd])
    axs[0].set_ylabel("i_L (A)"); axs[1].set_ylabel("i_tweeter (mA)")
    axs[1].set_xlabel("Time (µs)"); axs[0].legend(fontsize=7); axs[1].legend(fontsize=7)
    axs[0].set_title("Idle switching ripple, 18 V, 768 kHz, tweeter channel (behavioural PWM)")
    savefig(fig, "s2_idle_ripple")

    # ---------------------------------------------------------------- peaks at limiter ceilings
    peak_cases = [("wf_15V5_150Hz", 15.5, 150, "ND65-8 woofer model"),
                  ("wf_15V5_400Hz", 15.5, 400, "ND65-8 woofer model"),
                  ("wf_15V5_2k5Hz", 15.5, 2.5e3, "ND65-8 woofer model"),
                  ("tw_8V_3kHz", 8.0, 3e3, "OT19NC00-04 tweeter model"),
                  ("tw_8V_10kHz", 8.0, 10e3, "OT19NC00-04 tweeter model"),
                  ("tw_8V_20kHz", 8.0, 20e3, "OT19NC00-04 tweeter model"),
                  ("tw_clip_3kHz", 1.25 * PVDD, 3e3, "OT19NC00-04 tweeter model")]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for name, vpk, fsig, key in peak_cases:
        # modulation index: compensate RDS+DCR drop roughly; clip handled by limiting duty to [0,1]
        zl = abs(zload_analytic(np.array([fsig]), key))[0]
        m = vpk / PVDD * (zl + 2 * (RDS + DCR)) / zl
        clip = m > 1
        mm = min(m, 1.0) if not clip else m
        t_stop = 2.0 / fsig + 0.2e-3
        net_m = mm
        d = pwm_run(name, "BD", net_m, fsig, key, t_stop)
        t = d["time"]; sel = t > t_stop - 1.0 / fsig
        ilp = cur(d, "vilp")[sel]; vd = (d["v(spk_p)"] - d["v(spk_n)"])[sel]
        ld = cur(d, "vspk")[sel]
        ipk = float(np.max(abs(ilp)))
        lrat = 1 - 0.3 * (ipk / ISAT) ** 2   # soft-saturation estimate: -30 % at Isat
        out["peaks"][name] = dict(target_vpk=vpk, f_Hz=fsig, m=m, clipped=bool(clip),
                                  v_spk_pk=float(np.max(abs(vd))), i_spk_pk=float(np.max(abs(ld))),
                                  iL_pk=ipk, Isat=ISAT, OCP=IOCP, margin_to_OCP_A=IOCP - ipk,
                                  L_at_peak_est_uH=L0 * lrat * 1e6, passes_80pct_rule=bool(lrat >= 0.75))
        if fsig in (400, 3e3) or "clip" in name:
            ph = (t[sel] - t[sel][0]) * fsig
            ax.plot(ph, ilp, lw=0.7, label=f"{name}: i_L pk {ipk:.2f} A")
            write_csv(RESULTS / f"s2_peak_{name}.csv", ["t_s", "iL_A", "v_spk_V", "i_spk_A"], [t[sel], ilp, vd, ld])
    ax.axhline(IOCP, color="C3", ls="--", lw=0.9); ax.axhline(-IOCP, color="C3", ls="--", lw=0.9)
    ax.axhline(ISAT, color="k", ls=":", lw=0.9); ax.axhline(-ISAT, color="k", ls=":", lw=0.9)
    ax.text(0.01, IOCP + 0.1, "TAS5805M OCP 5 A", fontsize=7, color="C3")
    ax.text(0.01, ISAT + 0.1, "FXL0630-100-M Isat 5.5 A", fontsize=7)
    ax.set_xlabel("Signal phase (cycles)"); ax.set_ylabel("Leg inductor current (A)")
    ax.set_ylim(-6.5, 6.5); ax.legend(fontsize=6.5, loc="lower right", ncol=1)
    ax.set_title("Inductor current at the limiter ceilings (BD, 768 kHz, 18 V)")
    savefig(fig, "s2_inductor_peaks")
    write_json(RESULTS / "s2_classd_filter.json", out)
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps(o, indent=1, default=float)[:6000])
