"""S4: PVDD_TRIM network (R908/C917/R909/C918 -> D901 -> R907 -> TPS61178 FB).

Questions
 1. PVDD vs trim voltage (DAC) and vs LEDC PWM duty, against the spec's hand table.
 2. Ripple at FB / PVDD for a 20 kHz LEDC PWM; slew of PVDD when the trim steps.
 3. Is "the trim can only lower PVDD" true?  (GPIO low, Hi-Z, diode reverse leakage vs temperature.)

Model: the boost is replaced by an ideal regulator that forces V(FB) = VREF = 1.198 V
(a gm-C integrator with ~250 Hz unity-gain crossover, matching S1's loop), so the DC
results are exact for the divider + injection network and the dynamics are representative.
D901 = 1N4148W SPICE model (Diodes Inc. style parameters). Leakage worst case from the
1N4148W datasheet limits (25 nA @ 20 V, 25 C; 50 uA @ 20 V, 150 C) is evaluated separately.
"""
from __future__ import annotations

import numpy as np

from common import RESULTS, run_ngspice, use_style, savefig, write_csv, write_json

VREF = 1.198
RUP, RDN = 300e3, 1 / (1 / 24e3 + 1 / 200e3)
R907, R908, R909, C917, C918 = 68e3, 10e3, 10e3, 1e-6, 1e-6
DMODEL = ".model D1N4148W D(IS=2.52n RS=0.568 N=1.752 CJO=4p M=0.4 TT=20n BV=75 IBV=5u XTI=3 EG=1.11)"
KFB = RDN / (RUP + RDN)
FC = 250.0
C_INT = 1e-6
GM_INT = 2 * np.pi * FC * C_INT / KFB   # unity-gain crossover of the integrator loop at FC


def reg_block(vsys=7.4):
    return f"""* ideal boost: gm-C integrator drives PVDD so that V(FB) = VREF; PVDD >= VSYS - 0.5 V
GINT vint 0 fb vref {GM_INT:.6g}
CINT vint 0 {C_INT}
RINT vint 0 1e12
VREF vref 0 {VREF}
BPV pvdd 0 V = max(v(vint), {vsys - 0.5})
RUP pvdd fb {RUP}
RDN fb 0 {RDN:.2f}
R907 trim_k fb {R907}
D901 trim_rc trim_k D1N4148W
R909 trim_a trim_rc {R909}
C918 trim_rc 0 {C918}
R908 pvdd_trim trim_a {R908}
C917 trim_a 0 {C917}
{DMODEL}
"""


def dc_sweep(temp):
    net = f"""* S4 DC: PVDD vs trim voltage at {temp} C
.temp {temp}
VT pvdd_trim 0 0
{reg_block()}
.ic v(vint)=17.97
.dc VT 0 3.3 0.01
.end
"""
    # the integrator has no DC solution by itself: use a large finite gain for the DC run
    net = net.replace(f"GINT vint 0 fb vref {GM_INT:.6g}", "GINT vint 0 fb vref 1").replace("RINT vint 0 1e12", "RINT vint 0 1e6")
    d = run_ngspice(net, f"s4_dc_{temp}C")
    return np.real(d["v(v-sweep)"] if "v(v-sweep)" in d else d[list(d)[0]]), np.real(d["v(pvdd)"]), np.real(d["v(trim_rc)"])


def hand(vt, vd=0.45):
    vt = np.asarray(vt)
    return np.where(vt - vd > VREF, 17.97 - RUP * (vt - vd - VREF) / (R907 + R908 + R909), 17.97)


def tran_pwm(duty, f_pwm=20e3, t_stop=300e-3, name="pwm"):
    per = 1 / f_pwm
    net = f"""* S4 transient: LEDC PWM {f_pwm/1e3:.0f} kHz, duty {duty}
VT pvdd_trim 0 PULSE(0 3.3 0 20n 20n {duty * per - 20e-9:.6g} {per:.6g})
{reg_block()}
.ic v(vint)=17.97 v(trim_a)=0 v(trim_rc)=0
.options reltol=1e-5 abstol=1e-13 vntol=1e-9
.tran 0.5u {t_stop} 0 0.5u uic
.end
"""
    return run_ngspice(net, f"s4_tran_{name}")


def main():
    plt = use_style()
    out = {}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 3.3))
    cols = {}
    for temp in (0, 25, 60):
        vt, pv, vrc = dc_sweep(temp)
        a1.plot(vt, pv, label=f"ngspice, {temp} °C")
        cols.setdefault("v_trim_V", vt); cols[f"pvdd_{temp}C"] = pv
        out[f"dc_{temp}C"] = {f"{v:.1f}V": float(np.interp(v, vt, pv)) for v in (0, 1.6, 2.0, 2.5, 3.0, 3.3)}
    spec = {1.6: 17.97, 2.0: 16.8, 2.5: 15.1, 3.0: 13.4, 3.3: 12.3}
    a1.plot(list(spec), list(spec.values()), "ko", mfc="none", label="spec hand table")
    a1.set_xlabel("PVDD_TRIM voltage (V)"); a1.set_ylabel("PVDD (V)"); a1.legend(fontsize=7)
    a1.set_title("PVDD vs trim (DC)", fontsize=10)
    out["spec_table"] = spec
    write_csv(RESULTS / "s4_trim_dc.csv", list(cols.keys()), list(cols.values()))

    # PWM: duty sweep (average) and ripple at 50 % duty
    res = {}
    for duty in (0.5, 0.75, 1.0):
        d = tran_pwm(duty, name=f"d{int(duty * 100)}")
        t = d["time"]; pv = d["v(pvdd)"]; fb = d["v(fb)"]; rc = d["v(trim_rc)"]
        sel = t > t[-1] - 1e-3          # last 1 ms = 20 PWM periods
        def pp(y):                       # peak-peak after removing the residual settling slope
            yy = y[sel]; tt_ = t[sel]
            return float(np.ptp(yy - np.polyval(np.polyfit(tt_, yy, 1), tt_)))
        vfin = float(pv[sel].mean())
        res[duty] = dict(pvdd_final=vfin, ripple_pvdd_pp_uV=pp(pv) * 1e6,
                         ripple_fb_pp_uV=pp(fb) * 1e6, ripple_trim_rc_pp_uV=pp(rc) * 1e6,
                         t_90pct_ms=float(t[np.argmax(pv <= pv[0] - 0.9 * (pv[0] - vfin))] * 1e3))
        a2.plot(t * 1e3, pv, label=f"duty {int(duty * 100)} % (avg {3.3 * duty:.2f} V)")
        tt = np.linspace(0, t[-1], 3000)
        write_csv(RESULTS / f"s4_trim_pwm_d{int(duty * 100)}.csv", ["t_s", "pvdd_V", "trim_rc_V", "fb_V"],
                  [tt, np.interp(tt, t, pv), np.interp(tt, t, rc), np.interp(tt, t, fb)])
    a2.set_xlabel("Time after PWM start (ms)"); a2.set_ylabel("PVDD (V)"); a2.legend(fontsize=7)
    a2.set_title("20 kHz LEDC PWM step (from 0 V)", fontsize=10)
    fig.tight_layout()
    savefig(fig, "s4_pvdd_trim")
    out["pwm_20kHz"] = res

    # "trim can only lower PVDD": diode reverse leakage pulls current out of FB -> PVDD rises
    # by I_R * RUP. 1N4148W limits: 25 nA @ 20 V/25 C, 50 uA @ 20 V/150 C (exponential between).
    temps = np.array([25, 40, 60, 85])
    ir20 = 25e-9 * (50e-6 / 25e-9) ** ((temps - 25) / 125)
    ir_low = ir20 * 0.3          # at ~1.2 V reverse bias, leakage is ~1/3 of the 20 V value (assumed)
    out["leakage_worst_case"] = [dict(T_C=int(T), IR_20V_max_nA=float(a * 1e9), IR_1V2_est_nA=float(b * 1e9),
                                      pvdd_rise_mV=float(b * RUP * 1e3)) for T, a, b in zip(temps, ir20, ir_low)]
    # GPIO driven high at boot or in a glitch: lowest possible PVDD with VT = 3.3 V (+ 3.6 V abs worst)
    out["gpio_high_pvdd_V"] = float(hand(3.3)); out["gpio_3v6_pvdd_V"] = float(hand(3.6))
    write_json(RESULTS / "s4_pvdd_trim.json", out)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1, default=float))
