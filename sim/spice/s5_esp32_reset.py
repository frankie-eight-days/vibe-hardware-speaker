"""S5: ESP32 EN RC + 2-transistor DTR/RTS auto-reset (spec_signal 1.1, 2.3).

Question: when esptool runs its reset sequence through the CH340C, is GPIO0 low while EN
rises through the ESP32's input threshold (download mode), for realistic delays between the
host's separate DTR and RTS USB requests? Does EN come up late enough at power-up, and what
are the strapping-pin levels at reset?

Circuit: EN = R101 10k to +3V3, C103 1 uF to GND, Q201 (MMBT3904) C = EN, E = RTS#,
B = R201 10k from DTR#. IO0 = R102 10k to +3V3, ESP32 internal pull-up (45k), D101 + R103
1k from +3V3, Q202 C = IO0, E = DTR#, B = R202 10k from RTS#. CH340C DTR#/RTS# modelled as
3.3 V CMOS outputs with 150 Ohm output resistance (assumption: ~4 mA class drive).
Transistor: standard 2N3904 SPICE model (MMBT3904 is the SOT-23 die).

esptool sequences (esptool.py v4 reset.py; DTR=True means DTR# = 0 V):
  ClassicReset   : DTR=0,RTS=1 (EN low) | 100 ms | DTR=1 ... gap ... RTS=0 | 50 ms | DTR=0
  UnixTightReset : both lines changed in one TIOCMSET call (gap = 0)
Strap latch: ESP32 samples strapping pins when CHIP_PU (EN) rises; setup 0 ms, hold >= 1 ms
(ESP32 datasheet, strapping-pin timing). EN is a CMOS input with V_IL <= 0.25 VDD and
V_IH >= 0.75 VDD, so the release can happen anywhere between 0.825 V and 2.475 V; we require
IO0 to be low over that whole window + 1 ms.
"""
from __future__ import annotations

import numpy as np

from common import RESULTS, run_ngspice, use_style, savefig, write_csv, write_json

Q3904 = (".model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f "
         "IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p MJC=.3085 VJC=.75 FC=.5 "
         "CJE=4.493p MJE=.2593 VJE=.75 TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)")
LEDR = ".model LEDR D(IS=1e-20 N=1.9 RS=10 CJO=20p)"
VDD = 3.3
VIL, VIH = 0.25 * VDD, 0.75 * VDD


def pwl(points):
    return "PWL(" + " ".join(f"{t:.6g} {v:.3g}" for t, v in points) + ")"


def seq(gap, tight=False, t0=1e-3, edge=1e-6):
    """Return (DTR#, RTS#) PWL point lists for esptool's reset (pin levels in volts)."""
    H, L = VDD, 0.0
    dtr = [(0, H), (t0, H)]
    rts = [(0, H), (t0, H), (t0 + edge, L)]              # RTS=True -> EN low
    t1 = t0 + 0.1
    if tight:
        dtr += [(t1, H), (t1 + edge, L)]                 # DTR=True and RTS=False together
        rts += [(t1, L), (t1 + edge, H)]
        t2 = t1 + edge
    else:
        dtr += [(t1, H), (t1 + edge, L)]                 # setDTR(True)
        rts += [(t1 + gap, L), (t1 + gap + edge, H)]     # ...gap... setRTS(False)
        t2 = t1 + gap + edge
    t3 = t2 + 0.05                                       # reset_delay = 50 ms
    dtr += [(t3, L), (t3 + edge, H)]
    return dtr, rts, t1, t3


def netlist(name, dtr, rts, vdd_src=f"DC {VDD}", t_stop=0.2, c103="1u"):
    return f"""* S5 {name}: ESP32 EN/IO0 auto-reset
VDD vdd 0 {vdd_src}
VDTR dtr_src 0 {pwl(dtr)}
VRTS rts_src 0 {pwl(rts)}
RODTR dtr_src dtr_n 150
RORTS rts_src rts_n 150
* EN network
R101 vdd en 10k
C103 en 0 {c103}
CEN en 0 5p
R201 dtr_n q201b 10k
Q201 en q201b rts_n Q2N3904
* IO0 network
R102 vdd io0 10k
RPU_INT vdd io0 45k
D101 vdd led_k LEDR
R103 led_k io0 1k
CIO0 io0 0 10p
R202 rts_n q202b 10k
Q202 io0 q202b dtr_n Q2N3904
{Q3904}
{LEDR}
.options reltol=1e-4
.tran 10u {t_stop} 0 20u
.end
"""


def crossings(t, v, level):
    i = np.where((v[:-1] < level) & (v[1:] >= level))[0]
    return [float(np.interp(level, [v[k], v[k + 1]], [t[k], t[k + 1]])) for k in i]


def analyse(d, t_release_cmd):
    t = d["time"]; en = d["v(en)"]; io0 = d["v(io0)"]
    sel = t > t_release_cmd - 1e-4
    lo = crossings(t[sel], en[sel], VIL); hi = crossings(t[sel], en[sel], VIH)
    t_lo = lo[0] if lo else np.nan; t_hi = hi[0] if hi else np.nan
    # IO0 must be < V_IL from t_lo (earliest possible release) to t_hi + 1 ms (latest + hold)
    win = (t >= t_lo) & (t <= t_hi + 1e-3)
    io0_max = float(io0[win].max()) if np.any(win) else np.nan
    io0_low_until = crossings(t[t > t_lo], io0[t > t_lo], VIH)
    return dict(t_EN_cross_VIL_ms=(t_lo - t_release_cmd) * 1e3, t_EN_cross_VIH_ms=(t_hi - t_release_cmd) * 1e3,
                io0_max_in_window_V=io0_max, download_mode_ok=bool(io0_max < VIL),
                io0_released_at_ms=((io0_low_until[0] - t_release_cmd) * 1e3) if io0_low_until else None,
                en_min_during_reset_V=float(en[(t > t_release_cmd - 0.05) & (t < t_release_cmd)].min()),
                hold_margin_ms=((io0_low_until[0] - t_hi) * 1e3 - 1.0) if io0_low_until else None)


def main():
    plt = use_style()
    out = {"cases": {}}
    fig, axs = plt.subplots(3, 1, figsize=(6.5, 5.6), sharex=True)
    for name, gap, tight in (("tight", 0.0, True), ("gap1ms", 1e-3, False), ("gap2ms", 2e-3, False),
                             ("gap3ms", 3e-3, False), ("gap5ms", 5e-3, False)):
        dtr, rts, t1, t3 = seq(gap, tight)
        d = run_ngspice(netlist(name, dtr, rts), f"s5_{name}")
        r = analyse(d, t1)
        r["gap_ms"] = gap * 1e3
        out["cases"][name] = r
        t = d["time"]
        if name in ("tight", "gap2ms", "gap5ms"):
            tm = (t - t1) * 1e3
            axs[0].plot(tm, d["v(dtr_n)"], lw=1.0, label=f"DTR# ({name})")
            axs[0].plot(tm, d["v(rts_n)"], lw=1.0, ls="--", label=f"RTS# ({name})")
            axs[1].plot(tm, d["v(en)"], label=f"EN ({name})")
            axs[2].plot(tm, d["v(io0)"], label=f"IO0 ({name})")
        tt = np.linspace(0, t[-1], 4000)
        write_csv(RESULTS / f"s5_{name}.csv", ["t_s", "dtr_n", "rts_n", "en", "io0"],
                  [tt] + [np.interp(tt, t, d[k]) for k in ("v(dtr_n)", "v(rts_n)", "v(en)", "v(io0)")])
    for ax in axs[1:]:
        ax.axhspan(VIL, VIH, color="C3", alpha=0.08)
    axs[1].text(30, (VIL + VIH) / 2, "EN threshold band (0.25–0.75 VDD)", fontsize=7, color="C3", va="center")
    axs[0].set_ylabel("CH340C (V)"); axs[1].set_ylabel("EN (V)"); axs[2].set_ylabel("GPIO0 (V)")
    axs[2].set_xlabel("Time from esptool 'release reset' command (ms)")
    for ax in axs:
        ax.legend(fontsize=6, ncol=3, loc="center right")
    axs[0].set_xlim(-10, 70)
    axs[0].set_title("esptool reset into download mode: DTR/RTS → EN and GPIO0 (ngspice)")
    savefig(fig, "s5_autoreset")

    # analytic maximum gap: EN must stay below V_IL until IO0 is pulled low
    tau = 10e3 * 1e-6
    out["max_gap_ms_analytic"] = float(-tau * np.log(1 - VIL / VDD) * 1e3)

    # power-up: +3V3 ramps 0 -> 3.3 V over 4.8 ms (TPS62933 soft start), CH340C idle (lines high)
    d = run_ngspice(netlist("powerup", [(0, 0), (4.8e-3, VDD)], [(0, 0), (4.8e-3, VDD)],
                            vdd_src="PWL(0 0 4.8m 3.3)", t_stop=60e-3), "s5_powerup")
    t = d["time"]; en = d["v(en)"]; vdd = d["v(vdd)"]
    t_vdd_ok = crossings(t, vdd, 3.0)[0]
    t_en_lo = crossings(t, en, VIL)[0]
    out["powerup"] = dict(t_vdd_3V0_ms=t_vdd_ok * 1e3, t_en_cross_VIL_ms=t_en_lo * 1e3,
                          t_en_cross_VIH_ms=crossings(t, en, VIH)[0] * 1e3,
                          margin_after_vdd_ok_us=(t_en_lo - t_vdd_ok) * 1e6, required_us=50,
                          io0_at_en_rise_V=float(np.interp(t_en_lo, t, d["v(io0)"])))
    write_csv(RESULTS / "s5_powerup.csv", ["t_s", "vdd", "en", "io0"],
              [t, vdd, en, d["v(io0)"]])
    # what-if: C103 = 2.2 uF (power-up margin and esptool gap tolerance)
    d2 = run_ngspice(netlist("powerup_2u2", [(0, 0), (4.8e-3, VDD)], [(0, 0), (4.8e-3, VDD)],
                             vdd_src="PWL(0 0 4.8m 3.3)", t_stop=60e-3, c103="2.2u"), "s5_powerup_2u2")
    t2 = d2["time"]
    out["powerup_C103_2u2"] = dict(t_en_cross_VIL_ms=crossings(t2, d2["v(en)"], VIL)[0] * 1e3,
                                   margin_after_vdd_ok_us=(crossings(t2, d2["v(en)"], VIL)[0] - t_vdd_ok) * 1e6)
    gaps = {}
    for g in (2e-3, 4e-3, 5e-3, 6e-3):
        dtr, rts, t1, _ = seq(g)
        dd = run_ngspice(netlist(f"gap_2u2_{g}", dtr, rts, c103="2.2u"), f"s5_gap{int(g*1e3)}ms_2u2")
        gaps[f"{g*1e3:.0f}ms"] = analyse(dd, t1)["download_mode_ok"]
    out["C103_2u2_gap_ok"] = gaps
    # power-up figure
    fig2, ax = plt.subplots(figsize=(6.5, 3.0))
    ax.plot(t * 1e3, vdd, label="+3V3 (4.8 ms soft start)")
    ax.plot(t * 1e3, en, label="EN, C103 = 1 µF")
    ax.plot(t2 * 1e3, d2["v(en)"], "--", label="EN, C103 = 2.2 µF")
    ax.plot(t * 1e3, d["v(io0)"], ":", label="GPIO0")
    ax.axhspan(VIL, VIH, color="C3", alpha=0.08)
    ax.axvline(t_vdd_ok * 1e3, color="0.5", lw=0.8, ls="--")
    ax.text(t_vdd_ok * 1e3 + 0.3, 0.3, "VDD = 3.0 V", fontsize=7, color="0.4")
    ax.set_xlim(0, 25); ax.set_xlabel("Time (ms)"); ax.set_ylabel("V"); ax.legend(fontsize=7)
    ax.set_title("Power-up: EN delay vs +3V3 ramp (CH340C lines rise with +3V3)")
    savefig(fig2, "s5_powerup")

    # strapping levels at reset (DC divider estimates; ESP32 internal pulls 45 kOhm nominal,
    # taken as 20-80 kOhm worst case)
    straps = {}
    for nm, ext_pu, ext_pd, int_pull, need in (
            ("GPIO0 (boot)", 10e3, None, "up", 1), ("GPIO2 (BOOST_EN)", None, 1 / (1 / 100e3 + 1 / 800e3), "down", 0),
            ("GPIO12 MTDI (AMP_PDN)", None, 100e3, "down", 0), ("GPIO15 MTDO (LCD_DC)", None, None, "up", 1),
            ("GPIO5 (LCD_CS)", None, None, "up", 1)):
        worst = []
        for rint in (20e3, 80e3):
            pu = [r for r in (ext_pu, rint if int_pull == "up" else None) if r]
            pd = [r for r in (ext_pd, rint if int_pull == "down" else None) if r]
            gpu = sum(1 / r for r in pu); gpd = sum(1 / r for r in pd)
            # 1 uA input leakage either way (ESP32 I_IL/I_IH)
            v = (VDD * gpu + 0) / (gpu + gpd) if (gpu + gpd) else np.nan
            worst += [v + s * 1e-6 / (gpu + gpd) for s in (-1, 1)]
        straps[nm] = dict(v_min=min(worst), v_max=max(worst), required=need,
                          ok=bool((min(worst) > VIH) if need else (max(worst) < VIL)))
    out["straps"] = straps
    write_json(RESULTS / "s5_esp32_reset.json", out)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1, default=float))
