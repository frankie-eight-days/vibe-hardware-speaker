"""S7: pre-layout PDN impedance of +3V3 and PVDD vs target impedance.

+3V3: TPS62933 (current mode, internal compensation; fc/fz assumed 35 kHz / 7 kHz on 34 uF)
      with the spec's capacitors at their DC-bias values. Loads: ESP32-WROVER-E (Wi-Fi TX
      burst), 2x TAS5805M DVDD, CH340C, UI board via the FFC.
PVDD: TPS61178 closed-loop output admittance taken from the S1 averaged loop model (so the
      boost loop and its compensation are included exactly), plus the PVDD capacitor set.
      Load: the two TAS5805M at bass transients.
Placeholder layout parasitics (series R-L between regulator node and load nodes) are set to
typical pre-layout values and listed in the JSON; after layout replace them with extracted
values (see pdn_lib.Rail.series) and re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "spice"))
sys.path.insert(0, str(HERE))
from common import use_style, savefig, write_csv, write_json, ROOT  # noqa: E402
from pdn_lib import Rail, mlcc, electrolytic, regulator_cpm, regulator_from_admittance, target_impedance  # noqa: E402
import s1_boost_loop as s1  # noqa: E402

RES = HERE / "results"
FIG = ROOT / "docs" / "figures" / "pdn"
F = np.logspace(1, 8, 1400)


def rail_3v3(parasitics=True, fc=35e3):
    r = Rail("+3V3")
    c_design = 2 * 17e-6
    r.shunt("BUCK", regulator_cpm("TPS62933 loop", fc=fc, fz=fc / 5, c_design=c_design))
    r.shunt("BUCK", mlcc("C957,C958 22u/25V 1206", 22e-6, 25, "1206", 3.3, qty=2))
    r.shunt("BUCK", mlcc("C959 100n 0603", 1e-7, 50, "0603", 3.3))
    # ESP32 module pin 2
    r.shunt("ESP", mlcc("C101 22u/25V 0805", 22e-6, 25, "0805", 3.3))
    r.shunt("ESP", mlcc("C102 100n 0402", 1e-7, 16, "0402", 3.3))
    # amps DVDD (both), CH340C, USBLC6 VBUS pin, UI connector
    r.shunt("AMPS", mlcc("C308/C408 4.7u 0603", 4.7e-6, 16, "0603", 3.3, qty=2))
    r.shunt("AMPS", mlcc("C309/C409 100n 0402", 1e-7, 16, "0402", 3.3, qty=2))
    r.shunt("MISC", mlcc("C201, C603 100n", 1e-7, 16, "0402", 3.3, qty=2))
    r.shunt("UI", mlcc("C501 10u/10V 0603", 1e-5, 10, "0603", 3.3))
    r.shunt("UI", mlcc("C502 100n 0402", 1e-7, 16, "0402", 3.3))
    if parasitics:   # placeholder copper: inner-plane/pour segments, 2 vias each end
        r.series("BUCK", "ESP", R=4e-3, L=2.0e-9, name="buck->ESP32 (30 mm pour + vias)")
        r.series("BUCK", "AMPS", R=6e-3, L=3.0e-9, name="buck->amps (45 mm)")
        r.series("BUCK", "MISC", R=5e-3, L=2.5e-9, name="buck->CH340C")
        r.series("ESP", "UI", R=8e-3, L=4.0e-9, name="ESP area->J501 (40 mm)")
    else:
        for n in ("ESP", "AMPS", "MISC", "UI"):
            r.series("BUCK", n, R=1e-6, L=1e-15)
    return r


def boost_admittance(vin, iout, load="power", rc=s1.RC, cc=s1.CC):
    """Regulator-only admittance from S1: Y_reg = 1/Zcl - Y_caps(S1)."""
    def y(f):
        T, zo, _ = s1.loop(f, vin, iout, 3, s1.ESR_EL_NOM, load, rc=rc, cc=cc)
        zcl = zo / (1 + T)
        return 1 / zcl - s1.y_caps(f, 3, s1.ESR_EL_NOM)
    return y


def rail_pvdd(vin=7.4, iout=2.5, load="power", parasitics=True, rc=s1.RC, cc=s1.CC):
    r = Rail("PVDD")
    r.shunt("BOOST", regulator_from_admittance("TPS61178 loop (S1)", boost_admittance(vin, iout, load, rc, cc)))
    r.shunt("BOOST", mlcc("C906-C913 10u/50V 1206", 1e-5, 50, "1206", 18.0, qty=8))
    r.shunt("BOOST", mlcc("C914 100n 0603", 1e-7, 50, "0603", 18.0))
    r.shunt("BOOST", electrolytic("C920 470u/35V", 470e-6, s1.ESR_EL_NOM))
    for amp in ("AMP_L", "AMP_R"):
        r.shunt(amp, electrolytic(f"C301 470u/35V ({amp})", 470e-6, s1.ESR_EL_NOM))
        r.shunt(amp, mlcc(f"C302,C303,C305,C306 10u/50V ({amp})", 1e-5, 50, "1206", 18.0, qty=4))
        r.shunt(amp, mlcc(f"C304,C307 100n 0402 ({amp})", 1e-7, 50, "0402", 18.0, qty=2))
    if parasitics:
        r.series("BOOST", "AMP_L", R=5e-3, L=6e-9, name="boost->amp L (50 mm, 2 mm pour)")
        r.series("BOOST", "AMP_R", R=7e-3, L=8e-9, name="boost->amp R (70 mm, 2 mm pour)")
    else:
        r.series("BOOST", "AMP_L", R=1e-6, L=1e-15); r.series("BOOST", "AMP_R", R=1e-6, L=1e-15)
    return r


def main():
    plt = use_style()
    out = {}
    # ---------------------------------------------------------------- targets
    di_3v3, dv_3v3 = 0.33, 0.03 * 3.3        # ESP32 TX burst 20 -> 350 mA (WROVER-E Table 16), 3 %
    zt_3v3 = target_impedance(dv_3v3, di_3v3)
    # PVDD: 2 woofers at the 15.5 V-pk limiter ceiling (2.2 A each, S2) + tweeter share -> 5 A peak;
    # allowed sag = half the headroom between PVDD (17.97 V) and what the woofer ceiling needs
    # (15.5 V + 2.2 A x 0.5 Ohm = 16.6 V) -> 0.68 V
    di_pv = 5.0; dv_pv = 0.5 * (17.97 - (15.5 + 2.2 * 0.5))
    zt_pv = target_impedance(dv_pv, di_pv)
    out["targets"] = {"3V3": dict(dI_A=di_3v3, dV_V=dv_3v3, Z_ohm=zt_3v3, band="DC-20 MHz"),
                      "PVDD": dict(dI_A=di_pv, dV_V=dv_pv, Z_ohm=zt_pv, band="10 Hz-20 kHz audio-rate current; above that local decoupling")}

    # ---------------------------------------------------------------- 3V3
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    cols = {"f_Hz": F}
    r3 = rail_3v3(True)
    for node, ls in (("ESP", "-"), ("UI", "--"), ("AMPS", ":")):
        z = r3.z(F, node)
        ax.loglog(F, abs(z), ls, label=f"at {node} (placeholder copper)")
        cols[f"absZ_3v3_{node}"] = abs(z)
        out[f"3V3_{node}"] = dict(z_max_ohm=float(abs(z).max()), f_at_max_Hz=float(F[np.argmax(abs(z))]),
                                  z_max_below_1MHz=float(abs(z[F < 1e6]).max()),
                                  f_exceeds_target=[float(x) for x in F[abs(z) > zt_3v3][[0, -1]]] if np.any(abs(z) > zt_3v3) else None)
    z0 = rail_3v3(False).z(F, "ESP"); cols["absZ_3v3_lumped"] = abs(z0)
    ax.loglog(F, abs(z0), color="0.5", lw=0.9, label="lumped (no copper)")
    for fc in (20e3, 60e3):
        zz = rail_3v3(True, fc=fc).z(F, "ESP"); cols[f"absZ_3v3_ESP_fc{int(fc/1e3)}k"] = abs(zz)
        ax.loglog(F, abs(zz), lw=0.6, alpha=0.6, label=f"at ESP, buck fc = {fc/1e3:.0f} kHz")
        out[f"3V3_ESP_fc{int(fc/1e3)}k_zmax"] = float(abs(zz).max())
    ax.axhline(zt_3v3, color="C3", ls="--", lw=1.0)
    ax.text(15, zt_3v3 * 1.12, f"Z_target = {zt_3v3 * 1e3:.0f} mΩ (3 % / {di_3v3:.2f} A)", color="C3", fontsize=7)
    ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("|Z| (Ω)"); ax.set_ylim(1e-3, 3)
    ax.set_title("+3V3 PDN impedance (TPS62933 + spec capacitors, DC-bias derated)")
    ax.legend(fontsize=6.5, loc="upper left", ncol=2)
    savefig(fig, "s7_pdn_3v3", FIG)
    out["3V3_bom"] = r3.bom()

    # ---------------------------------------------------------------- PVDD
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    for (vin, io, load), ls in (((7.4, 2.5, "power"), "-"), ((6.0, 2.5, "power"), "--"),
                                ((8.4, 0.5, "resistive"), ":")):
        rp = rail_pvdd(vin, io, load, True)
        z = rp.z(F, "AMP_R")
        lab = f"at amp R, VSYS {vin} V, {io} A, {load} load"
        ax.loglog(F, abs(z), ls, label=lab)
        cols[f"absZ_pvdd_{vin}V_{io}A_{load}"] = abs(z)
        aud = F < 20e3
        out[f"PVDD_{vin}V_{io}A_{load}"] = dict(z_max_audio_ohm=float(abs(z[aud]).max()),
                                                f_at_max_Hz=float(F[aud][np.argmax(abs(z[aud]))]),
                                                sag_at_5A_V=float(abs(z[aud]).max() * di_pv),
                                                z_at_768k_ohm=float(abs(np.interp(768e3, F, abs(z)))))
    # what-if: faster boost loop (Rc 100k / Cc 15n)
    rp2 = rail_pvdd(7.4, 2.5, "power", True, rc=100e3, cc=15e-9)
    z2 = rp2.z(F, "AMP_R"); cols["absZ_pvdd_7.4V_2.5A_Rc100k"] = abs(z2)
    ax.loglog(F, abs(z2), color="C4", lw=1.2, label="what-if Rc/Cc = 100 k/15 nF (7.4 V, 2.5 A)")
    out["PVDD_7.4V_Rc100k"] = dict(z_max_audio_ohm=float(abs(z2[F < 20e3]).max()),
                                   f_at_max_Hz=float(F[F < 20e3][np.argmax(abs(z2[F < 20e3]))]))
    ax.axhline(zt_pv, color="C3", ls="--", lw=1.0)
    ax.axvspan(20e3, 1e8, color="0.93", zorder=-5)
    ax.text(15, zt_pv * 1.12, f"Z_target = {zt_pv * 1e3:.0f} mΩ (0.68 V / 5 A)", color="C3", fontsize=7)
    ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("|Z| (Ω)"); ax.set_ylim(1e-3, 3)
    ax.set_title("PVDD PDN impedance (TPS61178 loop from S1 + 1.5 mF bank)")
    ax.legend(fontsize=6.5, loc="upper right")
    savefig(fig, "s7_pdn_pvdd", FIG)
    out["PVDD_bom"] = rail_pvdd().bom()

    # validation: lumped 3V3 at 1 kHz must be ~ the regulator branch; at high f, the 0402s' SRF
    r = rail_3v3(False)
    srf = 1 / (2 * np.pi * np.sqrt(0.6e-9 * 1e-7))
    out["validation"] = dict(srf_100n_0402_hand_MHz=srf / 1e6,
                             z_reg_plateau_hand_ohm=1 / (2 * np.pi * 35e3 * 34e-6),
                             z_3v3_lumped_at_35kHz=float(abs(r.z(np.array([35e3]), "ESP"))[0]),
                             pvdd_peak_hand_ohm=1 / (2 * np.pi * 247 * 1.48e-3))
    write_csv(RES / "s7_pdn_impedance.csv", list(cols.keys()), list(cols.values()))
    write_json(RES / "s7_pdn.json", out)
    return out


if __name__ == "__main__":
    import json
    o = main()
    print(json.dumps({k: v for k, v in o.items() if not k.endswith("bom")}, indent=1, default=float))
