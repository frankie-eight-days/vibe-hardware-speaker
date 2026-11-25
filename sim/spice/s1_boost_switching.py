"""S1 (switching part): TPS61178 boost with TI's own unencrypted PSpice transient model.

Model: TI SLVMC02A "TPS61178 Unencrypted PSpice Transient Model" (TPS61178_TRANS.LIB, WEBENCH,
Final 1.00), run in ngspice with `set ngbehavior=psa` (ti_runs/.spiceinit). It models the
switching stage, peak-current-mode loop with adaptive slope compensation, pre-charge + soft
start, cycle-by-cycle and short-circuit (hiccup) current limits, OVP, pre-bias and PFM.

Runs (each is an independent ngspice job, launched in parallel):
  start_typ : EN step, PVDD pre-biased at VSYS-0.5 V, VSYS 7.4 V, RLIM 82k (ILIM typ 9.1 A)
  start_min : same at VSYS 6.0 V and RLIM 118k, which reproduces ILIM(min) = 6.3 A
              (the model's limit is 745 kOhm*A / RLIM, so ILIM scales with 1/R)
  step74    : 0.2 -> 2.0 -> 0.2 A load step, VSYS 7.4 V, full 1.48 mF bank
  step60    : same at VSYS 6.0 V
  fra_*     : small-signal injection (Middlebrook, series source in the FB sense line) at
              VSYS 7.4 V / 2.0 A to cross-check the averaged loop model at a few frequencies

Usage: python s1_boost_switching.py run [names...]   (skips runs whose raw file exists)
       python s1_boost_switching.py plot
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from common import (TI_RUNS, RESULTS, read_raw, run_ngspice, use_style, savefig, write_csv,
                    write_json, decimate)

# ---------------------------------------------------------------- component values (spec_power §4.1)
L_H, L_DCR = 2.2e-6, 7e-3            # FXL1040-2R2-M
C_IN_EFF = 2 * 12e-6                  # 2x 22 uF/25 V at ~7 V
C_OUT1 = 8 * 4.5e-6                   # C906-C913 10 uF/50 V 1206 at 18 V (DC-bias derated)
C_AMP = 8 * 4.5e-6                    # amp sheets 2x (4x 10 uF/50 V)
C_EL, ESR_EL, ESL_EL = 470e-6, 0.15, 5e-9   # C920, C301, C401 (KNSCHA RVT 470 uF/35 V), ESR assumed
N_EL = 3
RUP, RDN = 300e3, 1 / (1 / 24e3 + 1 / 200e3)
RC, CC, CP = 33e3, 47e-9, 10e-12
RFREQ = 300e3
T_STEP = 12e-3        # load step time (the loop needs ~8 ms after soft start to settle)


def netlist(name, vin, rlim=82e3, t_stop=25e-3, iload="0", ss=0, vpre=None, inject=None,
            extra_save="", tstep=50e-9, vcomp0=0.0, rc=RC, cc=CC):
    vpre = vin - 0.5 if vpre is None else vpre
    ic = f"IC={vpre:.3f}"
    ss_txt = f"PARAMS: SS={ss}"
    # Middlebrook injection: series source between PVDD sense point and RUP
    if inject:
        f_inj, amp, t_inj = inject
        fb_top = "pvdd_inj"
        inj = f"VINJ pvdd_inj pvdd SIN(0 {amp} {f_inj} {t_inj} 0 0)\n"
    else:
        fb_top = "pvdd"
        inj = ""
    return f"""* {name}: TPS61178 (TI SLVMC02A transient model) - spec_power.md section 4.1
.include ../models/TPS61178_TRANS.LIB
* --- input: VSYS from the BQ25792 (30 mOhm source) + C901/C902 (derated) + C903
VSRC vsrc 0 {vin}
RSRC vsrc vsys 30m
CIN vsys 0 {C_IN_EFF} IC={vin}
* --- power stage
VIL vsys l_in 0
L1 l_in l_x {L_H} IC=0
RL l_x sw {L_DCR}
XU 0 bst comp disdrv en fb freq ilim 0 sw vcc vsys pvdd TPS61178_TRANS {ss_txt}
VEN en 0 PWL(0 0 100u 0 101u 3.3)
RFREQ freq 0 {RFREQ}
RILIM ilim 0 {rlim}
RC comp cz {rc}
CC cz 0 {cc} IC={vcomp0}
CP comp 0 {CP} IC={vcomp0}
CBST bst sw 100n
CVCC vcc 0 4.7u
* --- feedback divider R904 / (R905 || R906)
{inj}RUP {fb_top} fb {RUP}
RDN fb 0 {RDN:.2f}
* --- PVDD bank: COUT1 at the IC, 3x 470 uF electrolytics, amp-sheet ceramics
COUT1 pvdd 0 {C_OUT1} {ic}
CHF pvdd 0 100n {ic}
CEL1 pvdd e1 {C_EL} {ic}
REL1 e1 e1l {ESR_EL}
LEL1 e1l 0 {ESL_EL}
CEL2 pvdd e2 {C_EL} {ic}
REL2 e2 e2l {ESR_EL}
LEL2 e2l 0 {ESL_EL}
CEL3 pvdd e3 {C_EL} {ic}
REL3 e3 e3l {ESR_EL}
LEL3 e3l 0 {ESL_EL}
CAMP pvdd 0 {C_AMP} {ic}
* --- load (amps in PDN for start-up: ~uA; current source for load steps)
RBLEED pvdd 0 1Meg
ILOAD pvdd 0 {iload}
.options method=trap reltol=2e-3 abstol=1e-8 vntol=1e-4 itl4=200
.save v(pvdd) i(vil) v(comp) v(fb) v(vsys) {extra_save}
.tran {tstep} {t_stop} 0 50n uic
.control
run
linearize v(pvdd) i(vil) v(comp) v(fb) v(vsys) {extra_save}
write {name}.raw v(pvdd) i(vil) v(comp) v(fb) v(vsys) {extra_save}
.endc
.end
"""


def runs():
    step = f"PWL(0 0.2 {T_STEP} 0.2 {T_STEP + 1e-6} 2.0 {T_STEP + 2.5e-3} 2.0 {T_STEP + 2.501e-3} 0.2)"
    r = {
        "start_typ": dict(vin=7.4, rlim=82e3, t_stop=22e-3),
        "start_min": dict(vin=6.0, rlim=118e3, t_stop=26e-3),
        "start_min_rc100k": dict(vin=6.0, rlim=118e3, t_stop=26e-3, rc=100e3, cc=15e-9),
        "step74": dict(vin=7.4, t_stop=T_STEP + 5e-3, iload=step, vpre=18.0, vcomp0=1.43,
                       extra_save="v(xu.vslope) v(xu.pcend)"),
        "step60": dict(vin=6.0, t_stop=T_STEP + 5e-3, iload=step, vpre=18.0, vcomp0=1.43),
        # what-if from s1_boost_loop.compensation_options(): Rc 100k / Cc 15 nF
        "step74_rc100k": dict(vin=7.4, t_stop=T_STEP + 5e-3, iload=step, vpre=18.0, vcomp0=1.43,
                              rc=100e3, cc=15e-9),
    }
    for f in (300, 1000, 3000):
        # the 2 A load is ramped in after soft start (3-6 ms) so the loop never current-limits
        # or winds up; injection starts at 10 ms; the last 4 of 6 cycles are evaluated
        cycles = 6
        t_inj = 10e-3
        r[f"fra_{f}"] = dict(vin=7.4, t_stop=t_inj + cycles / f, iload="PWL(0 0 3m 0 6m 2.0)", vpre=18.0,
                             inject=(f, 0.05, t_inj), extra_save="v(pvdd_inj)")
    return r


def run(names=None, force=False):
    # step74 (spec compensation at 7.4 V) and the fra_* injection runs stalled ("time step too
    # small" loops) in ngspice-47 with this model; they run only when named explicitly.
    flaky = ("step74", "fra_300", "fra_1000", "fra_3000")
    todo = {k: v for k, v in runs().items() if (k in names if names else k not in flaky)}
    def job(item):
        k, kw = item
        if (TI_RUNS / f"{k}.raw").exists() and not force:
            return k, "cached"
        run_ngspice(netlist(k, **kw), k, cwd=TI_RUNS, timeout=6 * 3600, control=True)
        return k, "done"
    with ThreadPoolExecutor(max_workers=1) as ex:
        for k, s in ex.map(job, todo.items()):
            print(k, s, flush=True)


# ---------------------------------------------------------------- analysis
def _load(name):
    p = TI_RUNS / f"{name}.raw"
    return read_raw(p) if p.exists() else None


def analyse_startup():
    plt = use_style()
    out = {}
    fig, axs = plt.subplots(2, 1, figsize=(6.5, 5.0), sharex=True)
    for name, lab, ilim in (("start_typ", "VSYS 7.4 V, ILIM typ (9.1 A)", 9.1),
                            ("start_min", "VSYS 6.0 V, ILIM min (6.3 A)", 6.3),
                            ("start_min_rc100k", "6.0 V, ILIM min, what-if Rc/Cc 100k/15n", 6.3)):
        d = _load(name)
        if d is None:
            continue
        t = d["time"]; v = d["v(pvdd)"]; il = d["i(vil)"]
        en_t = 100e-6
        ok = np.where(v >= 0.98 * 17.97)[0]
        t98 = t[ok[0]] - en_t if len(ok) else np.nan
        vmin_after = v[t > en_t].min()
        # average inductor current in 50 us windows
        win = 50e-6
        tb = np.arange(0, t[-1], win)
        ilavg = np.array([il[(t >= a) & (t < a + win)].mean() if np.any((t >= a) & (t < a + win)) else np.nan for a in tb])
        out[name] = dict(label=lab, t_to_98pct_ms=t98 * 1e3, il_peak_A=float(il.max()),
                         il_avg_max_A=float(np.nanmax(ilavg)), v_min_after_en=float(vmin_after),
                         v_final=float(v[-1]), hiccup_threshold_V=0.3 * 17.97,
                         hiccup=bool(vmin_after < 0.3 * 17.97 or il.max() > 20.0),
                         overshoot_V=float(v.max() - 17.97))
        tt, vv, ii = decimate(t, v, il, n=6000)
        write_csv(RESULTS / f"s1_{name}.csv", ["t_s", "pvdd_V", "il_A"], [tt, vv, ii])
        axs[0].plot((t - en_t) * 1e3, v, label=lab)
        axs[1].plot((t - en_t) * 1e3, il, lw=0.4, alpha=0.6)
        axs[1].plot((tb + win / 2 - en_t) * 1e3, ilavg, lw=1.6, label=f"{lab}: 50 µs avg")
        axs[1].axhline(ilim, ls=":", lw=0.8, color=axs[1].lines[-1].get_color())
    axs[0].axhline(0.3 * 17.97, color="0.4", ls="--", lw=0.8)
    axs[0].text(0.2, 0.3 * 17.97 + 0.3, "hiccup threshold (30 % of VOUT)", fontsize=8, color="0.3")
    axs[0].set_ylabel("PVDD (V)"); axs[0].legend(loc="lower right")
    axs[1].set_ylabel("Inductor current (A)"); axs[1].set_xlabel("Time after BOOST_EN (ms)")
    axs[1].legend(loc="upper right", fontsize=7)
    axs[0].set_title("TPS61178 start-up into 1.48 mF, PVDD pre-biased at VSYS − 0.5 V (TI model)")
    savefig(fig, "s1_startup")
    write_json(RESULTS / "s1_startup.json", out)
    return out


def analyse_step():
    plt = use_style()
    out = {}
    fig, axs = plt.subplots(2, 1, figsize=(6.5, 5.0), sharex=True)
    for name, lab in (("step74", "VSYS 7.4 V"), ("step60", "VSYS 6.0 V"),
                      ("step74_rc100k", "VSYS 7.4 V, what-if Rc/Cc 100k/15n")):
        d = _load(name)
        if d is None:
            continue
        t = d["time"]; v = d["v(pvdd)"]; il = d["i(vil)"]
        m = (t > T_STEP - 1e-3)
        pre = v[(t > T_STEP - 0.5e-3) & (t < T_STEP)].mean()
        dip = v[(t > T_STEP) & (t < T_STEP + 2.5e-3)].min()
        post = v[(t > T_STEP + 2.2e-3) & (t < T_STEP + 2.5e-3)].mean()
        peak_up = v[(t > T_STEP + 2.5e-3)].max()
        out[name] = dict(v_pre=pre, v_min=dip, undershoot_mV=(pre - dip) * 1e3,
                         v_settled_2A=post, overshoot_on_release_mV=(peak_up - post) * 1e3,
                         ripple_pp_2A_mV=float(np.ptp(v[(t > T_STEP + 2.3e-3) & (t < T_STEP + 2.5e-3)]) * 1e3))
        if name == "step74" and "v(xu.vslope)" in d:
            vs = d["v(xu.vslope)"]
            sel = (t > T_STEP + 2.2e-3) & (t < T_STEP + 2.5e-3)
            dv = np.diff(vs[sel]) / np.diff(t[sel])
            se = 62.5 * np.percentile(dv[dv > 0], 90)
            out[name]["slope_comp_Se_A_per_s"] = float(se)
            out[name]["Sn_A_per_s"] = 7.4 / L_H
        tt, vv, ii = decimate(t[m], v[m], il[m], n=6000)
        write_csv(RESULTS / f"s1_{name}.csv", ["t_s", "pvdd_V", "il_A"], [tt, vv, ii])
        axs[0].plot((t[m] - T_STEP) * 1e3, v[m], label=lab, lw=0.9)
        axs[1].plot((t[m] - T_STEP) * 1e3, il[m], lw=0.4, label=lab)
    axs[0].set_ylabel("PVDD (V)"); axs[0].legend()
    axs[1].set_ylabel("Inductor current (A)"); axs[1].set_xlabel("Time after load step (ms)")
    axs[0].set_title("Load step 0.2 → 2.0 → 0.2 A on PVDD (TI switching model)")
    savefig(fig, "s1_loadstep_switching")
    write_json(RESULTS / "s1_loadstep_switching.json", out)
    return out


def analyse_fra():
    """Loop gain T = -v(fb_side)/v(inj side): with VINJ between pvdd (x) and pvdd_inj (y),
    T(f) = -Y/X evaluated by single-bin DFT over the last integer number of cycles."""
    res = []
    for f in (300, 1000, 3000):
        d = _load(f"fra_{f}")
        if d is None:
            continue
        t = d["time"]; x = d["v(pvdd)"]; y = d["v(pvdd_inj)"]
        n_cyc = 4
        sel = t >= t[-1] - n_cyc / f
        tt = t[sel]
        ph = np.exp(-2j * np.pi * f * tt)
        # trapezoid DFT on (possibly) non-uniform grid
        detr = lambda u: u - np.polyval(np.polyfit(tt, u, 1), tt)   # remove settling drift
        X = np.trapezoid(detr(x[sel]) * ph, tt)
        Y = np.trapezoid(detr(y[sel]) * ph, tt)
        T = -X / Y   # y = x + v_inj feeds the divider; the loop returns x = -T*y
        res.append(dict(f_Hz=f, mag_dB=20 * np.log10(abs(T)), phase_deg=np.degrees(np.angle(T))))
    write_json(RESULTS / "s1_fra_switching.json", res)
    return res


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2:] or None)
    elif len(sys.argv) > 1 and sys.argv[1] == "plot":
        print(analyse_startup()); print(analyse_step()); print(analyse_fra())
