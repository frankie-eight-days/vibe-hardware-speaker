"""Analysis 4b: fold the extracted copper into the pre-layout PDN (sim/pdn, S7) and re-check targets.

Series copper between regulator and load:
  R = DC solve (ir_drop.py, path resistance seen by that load: V_drop / I with only that load)
  L = FastHenry loop inductance at 1 MHz, port at the regulator (+ / GND pad), far end shorted
      at the load's supply/GND pins (U301 15/14, U401 27/24: the PVDD pin pair that is connected
      on rev A), path halo 1.0 mm, 0.2 mm mesh, floating copper included.
The S7 rails (pdn_rails.rail_3v3 / rail_pvdd) are rebuilt with parasitics=False and their
placeholder series elements replaced. Boost compensation = spec v1.3 (Rc 100 k / Cc 15 nF).
Note: the S7 PDN is a Python nodal model (pdn_lib), not an ngspice deck; it is reused as is.

Run: python pdn_fold.py TAG [TAG ...]
"""
import os
import sys

import numpy as np

from fh_loops import analyse_loop
from ir_drop import solve_case
from pl_common import ROOT, WORK, load, save_json, savefig, style

sys.path.insert(0, os.path.join(ROOT, "sim", "pdn"))
sys.path.insert(0, os.path.join(ROOT, "sim", "spice"))
import pdn_rails as PR  # noqa: E402
from pdn_lib import Element, target_impedance  # noqa: E402

F = np.logspace(1, 8, 700)
TAS = ["15", "16", "27", "28"]
PATHS = {
    # name: (FastHenry spec, DC case)
    "boost->AMP_L": (dict(name="pdn_pvdd_ampl", pos=("U901", "8"), neg=("U901", "6"),
                          short=(("U301", "15"), ("U301", "14")), pitch=0.2, halo=1.0),
                     ("PVDD_L", "PVDD", [("U901", ["8"])], [("U301", TAS, 2.7)], 0.1, "")),
    "boost->AMP_R": (dict(name="pdn_pvdd_ampr", pos=("U901", "8"), neg=("U901", "6"),
                          short=(("U401", "27"), ("U401", "24")), pitch=0.2, halo=1.0),
                     ("PVDD_R", "PVDD", [("U901", ["8"])], [("U401", TAS, 2.7)], 0.1, "")),
    "buck->ESP": (dict(name="pdn_3v3_esp", pos=("C957", "1"), neg=("C957", "2"),
                       short=(("U101", "2"), ("U101", "1")), pitch=0.2, halo=1.0),
                  ("3V3_ESP", "+3V3", [("L951", ["2"])], [("U101", ["2"], 0.5)], 0.1, "")),
}


def extract(tag):
    b = load(tag)
    out = {}
    d = os.path.join(WORK, "fasthenry")
    for name, (fh, dc) in PATHS.items():
        r = solve_case(b, dc)
        r = r[0] if isinstance(r, tuple) else r
        ld = r["loads"][0]
        R = ld["V_drop_mV"] * 1e-3 / ld["I_A"] if ld.get("status") == "ok" else None
        f = analyse_loop(b, dict(fh, title=name), d)
        L = f["L_nH"]["1e+06"] * 1e-9 if f.get("status") == "ok" else None
        out[name] = {"R_ohm": R, "L_H": L, "fh_status": f.get("status"), "dc_status": r["status"],
                     "fh_nodes": f.get("nodes")}
        print(tag, name, out[name], flush=True)
    return out


def rails(par):
    """par: {path: (R, L)} or None for the S7 placeholders."""
    rc, cc = 100e3, 15e-9
    rp = PR.rail_pvdd(7.4, 2.5, "power", par is None, rc=rc, cc=cc)
    r3 = PR.rail_3v3(par is None)
    if par is not None:
        def el(n, R, L):
            return Element(n, lambda f, R=R, L=L: R + 2j * np.pi * f * L, dict(R=R, L=L))
        rp.series_el = [(a, b, el(f"{a}-{b} extracted", *par[f"boost->{b}"])) for a, b, _ in rp.series_el]
        new = []
        for a, b, e in r3.series_el:
            if b == "ESP":
                new.append((a, b, el("buck->ESP extracted", *par["buck->ESP"])))
            else:
                new.append((a, b, e))     # other 3V3 branches keep the S7 placeholders
        r3.series_el = new
    return rp, r3


def main(tags):
    plt = style()
    zt_pv = target_impedance(0.5 * (17.97 - (15.5 + 2.2 * 0.5)), 5.0)
    zt_33 = target_impedance(0.03 * 3.3, 0.33)
    res = {"targets": {"PVDD_ohm": zt_pv, "3V3_ohm": zt_33}, "boards": {}}
    fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.0))
    curves = {"S7 placeholder": None}
    for t in tags:
        ex = extract(t)
        res["boards"][t] = {"extracted": ex}
        if all(v["R_ohm"] is not None and v["L_H"] is not None for v in ex.values()):
            curves[t] = {k: (v["R_ohm"], v["L_H"]) for k, v in ex.items()}
        else:
            res["boards"][t]["note"] = "a path is open; rail not evaluated"
    for k, (lab, par) in enumerate(curves.items()):
        rp, r3 = rails(par)
        zl, zr = abs(rp.z(F, "AMP_L")), abs(rp.z(F, "AMP_R"))
        ze = abs(r3.z(F, "ESP"))
        aud = F < 20e3
        key = lab if lab in res["boards"] else "placeholder"
        res["boards"].setdefault(key, {})["Z"] = {
            "PVDD_AMP_R_max_audio_ohm": float(zr[aud].max()), "PVDD_AMP_L_max_audio_ohm": float(zl[aud].max()),
            "PVDD_AMP_R_at_1MHz_ohm": float(np.interp(1e6, F, zr)), "PVDD_AMP_R_at_10MHz_ohm": float(np.interp(1e7, F, zr)),
            "3V3_ESP_max_below_20MHz_ohm": float(ze[F < 2e7].max()),
            "PVDD_pass": bool(zr[aud].max() <= zt_pv and zl[aud].max() <= zt_pv),
            "3V3_pass": bool(ze[F < 2e7].max() <= zt_33)}
        ls = ["--", "-", ":"][k % 3]
        axs[0].loglog(F, zr, ls, label=f"{lab}, amp R")
        axs[1].loglog(F, ze, ls, label=lab)
    for ax, zt, ttl in ((axs[0], zt_pv, "PVDD at amp R (Rc 100 k)"), (axs[1], zt_33, "+3V3 at ESP32")):
        ax.axhline(zt, color="C3", ls="--", lw=0.9)
        ax.set_xlabel("Frequency (Hz)"); ax.set_title(ttl, fontsize=9); ax.set_ylim(1e-3, 2)
    axs[0].set_ylabel("|Z| (Ω)")
    axs[1].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    savefig(fig, "pdn_postlayout")
    save_json(res, "pdn_fold.json")
    return res


if __name__ == "__main__":
    print(main(sys.argv[1:] or ["hybrid", "autoroute"]))
