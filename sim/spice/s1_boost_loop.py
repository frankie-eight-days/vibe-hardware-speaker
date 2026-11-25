"""S1 (small-signal part): TPS61178 peak-current-mode loop gain, averaged model.

Question: with Rc/Cc/Cp = 33 k / 47 nF / 10 pF, is the PVDD loop stable (PM, GM) over
VSYS 6.0-8.4 V, load 0.2-2.5 A and PVDD bulk ~0.07-1.5 mF, and how big is the PVDD dip
for a 0.2 -> 2 A load step?

Model (TPS61178 datasheet SLVSDA7E eq. 15-25, generalised to an arbitrary output network):
  T(s) = Gm (1-D) (1 - s/w_rhp) He(s) * Zo(s) * k_fb * G_EA * Z_comp(s)
  Gm = 1/R_sense = 12 A/V (EC table; 1/0.083 Ohm)
  Zo(s) = 1 / (g_o + Y_load + Y_caps(s)),  g_o = I_out/V_out (converter output conductance)
     Y_load = 1/R (resistive, the datasheet convention: pole 2/(R C)),
              0 (constant current), -1/R (constant power, a class-D amp at low frequency)
  w_rhp = R (1-D)^2 / L, R = V_out/I_out
  He(s) = 1 / (1 + s/(wn Qp) + s^2/wn^2), wn = pi f_sw, Qp = 1/(pi (mc (1-D) - 0.5)),
          mc = 1 + Se/Sn (Ridley sampled-data model, = datasheet eq. 19)
  Z_comp = R_EA || (Rc + 1/sCc) || 1/(s (Cp + C_int)); G_EA = 195 uS, R_EA = 20 MOhm (datasheet)
  C_int = 70 pF on COMP and Se are taken from TI's transient model (the datasheet eq. 21 for Se
  is typeset incorrectly), see s1_boost_switching.py.
Validated against: hand calculation of crossover, the TI switching model (FRA points and a
load step), see README.
"""
from __future__ import annotations

import json

import numpy as np

from common import RESULTS, use_style, savefig, write_csv, write_json, mlcc_cap_dc_bias

VOUT = 17.97
L, FSW = 2.2e-6, 599e3
GM, GEA, REA, C_INT = 12.0, 195e-6, 20e6, 70e-12
RUP, RDN = 300e3, 1 / (1 / 24e3 + 1 / 200e3)
KFB = RDN / (RUP + RDN)
RC, CC, CP = 33e3, 47e-9, 10e-12

# PVDD capacitor network (spec_power 4.1.1 + spec_signal 3.2)
C_CER_EACH = mlcc_cap_dc_bias(10e-6, 18.0, 50, "1206")   # ~4.5 uF
N_CER = 16                                                # 8 at the boost + 8 on the amp sheets
ESR_CER, ESL_CER = 5e-3, 1.0e-9
C_EL, ESL_EL = 470e-6, 5e-9
ESR_EL_NOM = 0.15        # assumption: KNSCHA RVT 10x10 general-purpose; tan(d)=0.12 @120 Hz -> 0.34 Ohm


def se_from_ti_model(vin):
    """Slope compensation (A/s) from the TI model extraction; scale as the model does (~1/(1-D))."""
    p = RESULTS / "s1_loadstep_switching.json"
    if p.exists():
        d = json.loads(p.read_text()).get("step74", {})
        if "slope_comp_Se_A_per_s" in d:
            se74 = d["slope_comp_Se_A_per_s"]
            d74 = 1 - 7.4 / VOUT
            d_ = 1 - vin / VOUT
            return se74 * (1 - d74) / (1 - d_)
    # value extracted from the TI model at 7.4 V (s1_boost_switching.analyse_step), used if the
    # switching run is not available
    return 2.755e6 * (1 - (1 - 7.4 / VOUT)) / (1 - (1 - vin / VOUT))


def y_caps(f, n_el, esr_el=ESR_EL_NOM, n_cer=N_CER):
    w = 2j * np.pi * f
    y = n_cer / (ESR_CER + w * ESL_CER + 1 / (w * C_CER_EACH))
    if n_el:
        y = y + n_el / (esr_el + w * ESL_EL + 1 / (w * C_EL))
    return y


def loop(f, vin, iout, n_el=3, esr_el=ESR_EL_NOM, load="resistive", rc=RC, cc=CC, cp=CP, se=None):
    s = 2j * np.pi * f
    D = 1 - vin / VOUT
    R = VOUT / iout
    sn = vin / L
    if se is None:
        se = se_from_ti_model(vin) or 0.5 * sn
    mc = 1 + se / sn
    qp = 1 / (np.pi * (mc * (1 - D) - 0.5))
    wn = np.pi * FSW
    he = 1 / (1 + s / (wn * qp) + (s / wn) ** 2)
    wrhp = R * (1 - D) ** 2 / L
    go = iout / VOUT
    yl = {"resistive": 1 / R, "current": 0.0, "power": -1 / R}[load]
    zo = 1 / (go + yl + y_caps(f, n_el, esr_el))
    zc = 1 / (1 / REA + 1 / (rc + 1 / (s * cc)) + s * (cp + C_INT))
    ctrl = GM * (1 - D) * (1 - s / wrhp) * he          # vc -> current into the output node
    T = ctrl * zo * KFB * GEA * zc
    return T, zo, dict(D=D, mc=mc, Qp=qp, f_rhp=wrhp / 2 / np.pi, Se=se, Sn=sn)


def margins(f, T):
    mag = 20 * np.log10(np.abs(T))
    ph = np.unwrap(np.angle(T))
    # crossover: last downward crossing of 0 dB
    idx = np.where((mag[:-1] > 0) & (mag[1:] <= 0))[0]
    if len(idx) == 0:
        return np.nan, np.nan, np.nan, np.nan
    i = idx[-1]
    fc = np.exp(np.interp(0, [mag[i + 1], mag[i]], [np.log(f[i + 1]), np.log(f[i])]))
    pm = 180 + np.degrees(np.interp(np.log(fc), np.log(f), ph))
    # gain margin: first frequency above fc where phase crosses -180 deg
    phd = np.degrees(ph)
    j = np.where((phd[:-1] > -180) & (phd[1:] <= -180) & (f[:-1] > fc))[0]
    if len(j):
        k = j[0]
        f180 = np.exp(np.interp(-180, [phd[k + 1], phd[k]], [np.log(f[k + 1]), np.log(f[k])]))
        gm = -np.interp(np.log(f180), np.log(f), mag)
    else:
        f180, gm = np.nan, np.inf
    return fc, pm, gm, f180


def step_response(vin, i0, i1, t_on, n_el=3, load="current", dt=0.5e-6, tw=80e-3, se=None, rc=RC, cc=CC):
    """PVDD deviation for a load pulse i0->i1 (duration t_on), linearised at i1.
    v(t) = IFFT{ -Zcl(jw) * I(jw) }, Zcl = Zo/(1+T)."""
    n = int(tw / dt)
    f = np.fft.rfftfreq(n, dt)
    f[0] = 1e-3
    T, zo, _ = loop(f, vin, i1, n_el=n_el, load=load, se=se, rc=rc, cc=cc)
    zcl = zo / (1 + T)
    t = np.arange(n) * dt
    t0 = 2e-3
    i = np.where((t >= t0) & (t < t0 + t_on), i1 - i0, 0.0)
    v = np.fft.irfft(-zcl * np.fft.rfft(i), n)
    return t - t0, v


def main():
    plt = use_style()
    f = np.logspace(0, np.log10(FSW / 2 * 0.98), 3000)
    vins = (6.0, 7.4, 8.4)
    iouts = (0.2, 0.5, 1.0, 2.5)
    banks = {0: "ceramics only (72 µF)", 1: "+1×470 µF", 2: "+2×470 µF", 3: "+3×470 µF (design, 1.48 mF)"}
    rows = []
    for vin in vins:
        for io in iouts:
            for nel in banks:
                for esr in ((0.05, ESR_EL_NOM, 0.34) if nel else (ESR_EL_NOM,)):
                    for load in ("resistive", "current", "power"):
                        T, _, p = loop(f, vin, io, nel, esr, load)
                        fc, pm, gm, f180 = margins(f, T)
                        rows.append(dict(vin=vin, iout=io, n_el=nel, esr_el=esr, load=load,
                                         fc_Hz=fc, pm_deg=pm, gm_dB=gm, f180_Hz=f180,
                                         f_rhp_Hz=p["f_rhp"], mc=p["mc"], ccm=bool(io * VOUT / vin / 0.93 > 0.5 * vin * p["D"] / (L * FSW))))
    write_json(RESULTS / "s1_loop_margins.json", rows)
    import csv
    with open(RESULTS / "s1_loop_margins.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # ---- Figure 1: Bode, design bank, Vin sweep at 2.5 A and 0.5 A (resistive, datasheet convention)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.5, 5.2), sharex=True)
    data = {"f_Hz": f}
    for vin in vins:
        for io, ls in ((2.5, "-"), (0.5, "--")):
            T, _, _ = loop(f, vin, io, 3)
            lab = f"VSYS {vin} V, {io} A"
            a1.semilogx(f, 20 * np.log10(abs(T)), ls, label=lab)
            a2.semilogx(f, np.degrees(np.unwrap(np.angle(T))), ls, color=a1.lines[-1].get_color())
            data[f"mag_dB_{vin}V_{io}A"] = 20 * np.log10(abs(T))
            data[f"phase_deg_{vin}V_{io}A"] = np.degrees(np.unwrap(np.angle(T)))
    # FRA points from the switching model
    fra_p = RESULTS / "s1_fra_switching.json"
    T74, _, _ = loop(f, 7.4, 2.0, 3)
    a1.semilogx(f, 20 * np.log10(abs(T74)), ":", color="k", lw=1.0, label="VSYS 7.4 V, 2.0 A (FRA case)")
    a2.semilogx(f, np.degrees(np.unwrap(np.angle(T74))), ":", color="k", lw=1.0)
    if fra_p.exists():
        fra = json.loads(fra_p.read_text())
        if fra:
            a1.plot([r["f_Hz"] for r in fra], [r["mag_dB"] for r in fra], "ko", ms=5, mfc="none",
                    label="TI switching model, injection (7.4 V, 2 A)")
            ph = np.array([r["phase_deg"] for r in fra])
            ref = np.degrees(np.unwrap(np.angle(T74)))
            # bring to the same 360-degree branch as the analytic curve
            ph = ph - 360 * np.round((ph - np.interp([r["f_Hz"] for r in fra], f, ref)) / 360)
            a2.plot([r["f_Hz"] for r in fra], ph, "ko", ms=5, mfc="none")
    a1.axhline(0, color="0.5", lw=0.8)
    a2.axhline(-180, color="0.5", lw=0.8)
    a1.set_ylabel("|T| (dB)"); a2.set_ylabel("∠T (deg)"); a2.set_xlabel("Frequency (Hz)")
    a1.set_ylim(-60, 80); a2.set_ylim(-270, 0)
    a1.legend(fontsize=7, ncol=2, loc="lower left")
    a1.set_title("TPS61178 loop gain, Rc/Cc/Cp = 33 k/47 nF/10 pF, 1.48 mF bank (averaged model)")
    savefig(fig, "s1_loop_bode")
    write_csv(RESULTS / "s1_loop_bode.csv", list(data.keys()), list(data.values()))

    # ---- Figure 2: margins vs bank and load (worst over Vin), by load model
    fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.2))
    for load, mk in (("resistive", "o"), ("current", "s"), ("power", "^")):
        for io, col in zip(iouts, ["C0", "C1", "C2", "C3"]):
            fcs, pms = [], []
            for nel in banks:
                sel = [r for r in rows if r["iout"] == io and r["n_el"] == nel and r["load"] == load
                       and r["esr_el"] == ESR_EL_NOM]
                pms.append(min(r["pm_deg"] for r in sel)); fcs.append(max(r["fc_Hz"] for r in sel))
            caps = [N_CER * C_CER_EACH + n * C_EL for n in banks]
            kw = dict(marker=mk, ms=4, lw=0.9, color=col, ls="-" if load == "resistive" else ":")
            axs[0].semilogx(np.array(caps) * 1e6, pms, label=f"{io} A, {load}" if load != "current" else None, **kw)
            axs[1].loglog(np.array(caps) * 1e6, fcs, **kw)
    axs[0].axhline(45, color="0.5", ls="--", lw=0.8)
    axs[0].set_xlabel("PVDD capacitance (µF, effective)"); axs[0].set_ylabel("Worst PM over VSYS (deg)")
    axs[1].set_xlabel("PVDD capacitance (µF, effective)"); axs[1].set_ylabel("Highest crossover (Hz)")
    axs[0].legend(fontsize=6, loc="lower left")
    fig.suptitle("Phase margin and crossover vs bank (solid: resistive, dotted: constant-current/-power loads)", fontsize=9)
    fig.tight_layout()
    savefig(fig, "s1_loop_margins")

    # ---- Figure 3: load step, averaged model vs TI switching model
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    sw = {}
    for name, vin in (("step60", 6.0), ("step74_rc100k", 7.4)):
        p = RESULTS / f"s1_{name}.csv"
        if p.exists():
            arr = np.loadtxt(p, delimiter=",", skiprows=1)
            sw[name] = arr
            from s1_boost_switching import T_STEP
            pre = arr[(arr[:, 0] > T_STEP - 0.5e-3) & (arr[:, 0] < T_STEP), 1].mean()
            lab = "Rc/Cc 100k/15n" if "rc100k" in name else "Rc/Cc 33k/47n (spec)"
            ax.plot((arr[:, 0] - T_STEP) * 1e3, arr[:, 1] - pre, lw=0.8, label=f"TI switching model, {vin} V, {lab}")
    avg = {}
    for vin, rc, cc, tag in ((6.0, RC, CC, "33k/47n"), (7.4, 100e3, 15e-9, "100k/15n")):
        t, v = step_response(vin, 0.2, 2.0, 2.5e-3, load="current", rc=rc, cc=cc)
        m = (t > -0.5e-3) & (t < 5e-3)
        ax.plot(t[m] * 1e3, v[m], "--", lw=1.4, label=f"averaged (linear) model, {vin} V, {tag}")
        avg[f"{vin}V_{tag}"] = dict(undershoot_mV=float(-v.min() * 1e3))
        write_csv(RESULTS / f"s1_loadstep_avg_{vin}V_{tag.replace('/', '_')}.csv", ["t_s", "dV_V"], [t[m], v[m]])
    ax.set_xlabel("Time after 0.2 → 2.0 A step (ms)"); ax.set_ylabel("ΔPVDD (V)")
    ax.set_title("PVDD load-step response: averaged loop model vs TI switching model")
    ax.legend(fontsize=7)
    savefig(fig, "s1_loadstep")
    write_json(RESULTS / "s1_loadstep_avg.json", avg)

    # ---- summary table (design bank, nominal ESR, resistive + power)
    summ = []
    for vin in vins:
        for io in iouts:
            for load in ("resistive", "power"):
                r = [x for x in rows if x["vin"] == vin and x["iout"] == io and x["n_el"] == 3
                     and x["esr_el"] == ESR_EL_NOM and x["load"] == load][0]
                summ.append(r)
    write_json(RESULTS / "s1_loop_summary_design_bank.json", summ)
    worst = {}
    for load in ("resistive", "current", "power"):
        sel = [r for r in rows if r["load"] == load and r["ccm"]]
        r = min(sel, key=lambda r: r["pm_deg"])
        g = min(sel, key=lambda r: r["gm_dB"])
        worst[load] = dict(min_pm=r, min_gm=g)
    write_json(RESULTS / "s1_loop_worst.json", worst)
    worst["compensation_options"] = compensation_options(plt)
    return worst


def compensation_options(plt):
    """What-if: faster loop. Rc up, Cc scaled to keep fz ~ 103 Hz. Worst PM/GM over the
    production states (1-3 electrolytics fitted, ESR 0.05-0.34 Ohm, VSYS 6-8.4 V, CCM loads,
    resistive and constant-power loads) and the closed-loop PVDD impedance peak."""
    f = np.logspace(0, np.log10(FSW / 2 * 0.98), 2500)
    res = []
    for rc in (33e3, 47e3, 68e3, 100e3, 150e3, 220e3):
        cc = CC * RC / rc
        pms, gms, fcs = [], [], []
        for vin in (6.0, 7.4, 8.4):
            for io in (1.0, 2.5):
                for nel in (1, 2, 3):
                    for esr in (0.05, ESR_EL_NOM, 0.34):
                        for load in ("resistive", "power"):
                            T, _, _ = loop(f, vin, io, nel, esr, load, rc=rc, cc=cc)
                            fc, pm, gm, _ = margins(f, T)
                            pms.append(pm); gms.append(gm); fcs.append(fc)
        Tc, _, _ = loop(f, 7.4, 2.5, 0, ESR_EL_NOM, "resistive", rc=rc, cc=cc)
        fc0, pm0, gm0, _ = margins(f, Tc)
        T, zo, p = loop(f, 7.4, 2.5, 3, ESR_EL_NOM, "power", rc=rc, cc=cc)
        zcl = zo / (1 + T)
        aud = f < 20e3
        res.append(dict(Rc=rc, Cc=cc, fc_min_Hz=min(fcs), fc_max_Hz=max(fcs), pm_min_deg=min(pms), gm_min_dB=min(gms),
                        fc_ceramic_only_Hz=fc0, pm_ceramic_only_deg=pm0,
                        zcl_peak_ohm=float(abs(zcl[aud]).max()), f_zpeak_Hz=float(f[aud][np.argmax(abs(zcl[aud]))]),
                        f_rhp_5_worst_Hz=float(2.5 ** -1 * 0 + (VOUT / 2.5) * (6.0 / VOUT) ** 2 / L / 2 / np.pi / 5)))
    write_json(RESULTS / "s1_compensation_options.json", res)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 3.0))
    rcs = [r["Rc"] / 1e3 for r in res]
    a1.plot(rcs, [r["pm_min_deg"] for r in res], "o-", label="worst PM, 1-3 electrolytics")
    a1.plot(rcs, [r["pm_ceramic_only_deg"] for r in res], "s--", label="ceramics only (no bulk)")
    a1.axhline(45, color="0.5", ls=":", lw=0.8)
    a1.set_xlabel("Rc (kΩ), Cc = 1.55 µs / Rc"); a1.set_ylabel("Phase margin (deg)"); a1.legend(fontsize=7)
    a2.plot(rcs, [r["zcl_peak_ohm"] for r in res], "o-", color="C2")
    a2.axhline(0.137, color="C3", ls="--", lw=0.9); a2.text(rcs[0], 0.145, "PVDD Z_target (S7)", color="C3", fontsize=7)
    a2.set_xlabel("Rc (kΩ)"); a2.set_ylabel("Peak |Z_PVDD| in audio band (Ω)")
    fig.suptitle("Faster boost loop: margin vs PVDD impedance (7.4 V, 2.5 A, 1.48 mF)", fontsize=9)
    fig.tight_layout()
    savefig(fig, "s1_compensation_options")
    return res


if __name__ == "__main__":
    w = main()
    for k, v in w.items():
        if k == "compensation_options":
            continue
        print(k, "PM", round(v["min_pm"]["pm_deg"], 1), v["min_pm"]["vin"], v["min_pm"]["iout"], v["min_pm"]["n_el"],
              "GM", round(v["min_gm"]["gm_dB"], 1))
