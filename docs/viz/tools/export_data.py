#!/usr/bin/env python3
"""Export the simulation results the explainer page (docs/viz/index.html) draws, as compact JSON.

Reads sim/acoustics/results, sim/spice/results, sim/pdn/results and research/drivers.json (never writes there).
Two curve sets are re-evaluated from the project's own models because the result files hold magnitudes only:
  - A5 complex woofer/tweeter branches (a5_crossover_system.System.branches), so the page can toggle the 110 us delay;
  - S1 loop gain with the ECO-001 compensation (s1_boost_loop.loop), so the page can show before/after Bode.
Run from the repo root:  PATH=.venv/bin:$PATH .venv/bin/python docs/viz/tools/export_data.py
"""
import csv
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "viz" / "data"
IMG = ROOT / "docs" / "viz" / "img"
OUT.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)
AR = ROOT / "sim" / "acoustics" / "results"
SR = ROOT / "sim" / "spice" / "results"
PR = ROOT / "sim" / "pdn" / "results"


def rcsv(p):
    with open(p) as fh:
        rows = list(csv.reader(fh))
    hdr = rows[0]
    data = np.array([[float(x) if x not in ("", "nan", "None") else np.nan for x in r] for r in rows[1:]])
    return hdr, data


def r(a, n=2):
    a = np.asarray(a, float)
    return [None if not np.isfinite(x) else round(float(x), n) for x in a]


def sig(a, n=4):
    a = np.asarray(a, float)
    return [None if not np.isfinite(x) else float(f"{x:.{n}g}") for x in a]


def dump(name, obj):
    p = OUT / name
    p.write_text(json.dumps(obj, separators=(",", ":")))
    print(f"{name}: {p.stat().st_size / 1024:.0f} kB")


def thin(t, n):
    """Indices that keep about n points, always including the last."""
    k = max(1, len(t) // n)
    idx = np.arange(0, len(t), k)
    if idx[-1] != len(t) - 1:
        idx = np.append(idx, len(t) - 1)
    return idx


def minmax_thin(t, y, n):
    """Keep min and max of y in n buckets so peaks/overshoot survive decimation."""
    edges = np.linspace(0, len(t), n + 1).astype(int)
    ti, yi = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        seg = y[a:b]
        i0, i1 = a + int(np.argmin(seg)), a + int(np.argmax(seg))
        for i in sorted({i0, i1}):
            ti.append(t[i]); yi.append(y[i])
    return np.array(ti), np.array(yi)


# ------------------------------------------------------------------ A1 bass
parts = {p["id"]: p for p in json.loads((ROOT / "research" / "drivers.json").read_text())["parts"]}
a1 = json.loads((AR / "a1_bass_summary.json").read_text())
h, d = rcsv(AR / "a1_spl_halfspace_1m.csv")
_, ex = rcsv(AR / "a1_excursion_vs_xmax.csv")
_, zz = rcsv(AR / "a1_impedance.csv")
_, mx = rcsv(AR / "a1_max_spl_vs_frequency.csv")
_, eq = rcsv(AR / "a1_dsp_bass_eq.csv")
sel = d[:, 0] <= 1000.0
dump("a1.json", dict(
    woofer=parts["ND65-8"]["ts"], pr=parts["DMA58-PR"]["ts"],
    ref=dict(f=r(d[sel, 0], 3), spl_2v83=r(d[sel, 2], 3), spl_15v5=r(d[sel, 1], 3),
             xd_15v5=r(ex[sel, 1], 4), xp_15v5=r(ex[sel, 2], 4), zmag=r(zz[sel, 1], 4),
             maxsine=r(mx[sel, 1], 3), limit=[int(x) for x in mx[sel, 2]],
             eq_biquad_db=r(eq[sel, 4], 3), eq_ideal_db=r(eq[sel, 3], 3)),
    summary=a1["chosen"], assumptions=a1["assumptions"], validation=a1["validation"],
    biquads=a1["biquads_fs48k"], sos48k=a1["biquad_sos_fs48k"], whatif=a1["whatif"]))

# ------------------------------------------------------------------ A2 tweeter polar maps
pol = {}
for case in ("bezel", "waveguide", "baffle"):
    for pl in ("h", "v"):
        hh, dd = rcsv(AR / f"a2_polar_{case}_{pl}.csv")
        pol[f"{case}_{pl}"] = [r(row, 1) for row in dd[:, 1:]]
angles = [float(x) for x in hh[1:]]
dirj = json.loads((AR / "a2_tweeter_directivity.json").read_text())
_, tr = rcsv(AR / "a2_tweeter_responses.csv")
dump("a2.json", dict(f=r(dd[:, 0], 1), angles=angles, maps=pol,
                     listener=dirj["listener_geometry_bezel"], listener_wg=dirj["listener_geometry_waveguide"],
                     cases={k: {kk: r(vv, 2) for kk, vv in v.items()} for k, v in dirj["cases"].items()},
                     summary=dirj["summary"], checks=dirj["checks"],
                     resp=dict(f=r(tr[:, 0], 1), cols=open(AR / "a2_tweeter_responses.csv").readline().strip().split(",")[1:],
                               data=[r(tr[:, i], 2) for i in range(1, tr.shape[1])])))

# ------------------------------------------------------------------ A4 panel modes
a4 = json.loads((AR / "a4_modes.json").read_text())
keep = ["asm_infill40_free", "asm_infill40_drivers", "asm_infill40_drivers_batt", "asm_infill40_drivers_rib_top",
        "asm_infill40_drivers_rib_top_tray", "asm_infill40_drivers_spine", "asm_infill40_drivers_all_braces",
        "asm_infill40_drivers_batt_spine_top_tray"]
hh = open(AR / "a4_shell_vs_woofer_output.csv").readline().strip().split(",")
_, fr = rcsv(AR / "a4_shell_vs_woofer_output.csv")
frf = {c: r(fr[:, i], 2) for i, c in enumerate(hh) if c.endswith("_total_db")}
dump("a4.json", dict(cases={k: dict(label=a4["cases"][k]["label"], freqs=r(a4["cases"][k]["freqs_hz"], 1),
                                    below1k=a4["cases"][k]["modes_below_1khz"],
                                    frf_peak=a4["cases"][k].get("frf_peak_db_below_1khz"))
                            for k in keep if k in a4["cases"]},
                     frf_f=r(fr[:, 0], 1), frf=frf))

# ------------------------------------------------------------------ A5 crossover (complex branches)
sys.path.insert(0, str(ROOT / "sim" / "acoustics"))
os.chdir(ROOT / "sim" / "acoustics")
import a5_crossover_system as a5  # noqa: E402
from bem_results import BEM  # noqa: E402

b = BEM("bezel")
sysm = a5.System(b, "L")
a5j = json.loads((AR / "a5_crossover_system.json").read_text())
al = a5j["alignment"]
ic = b.centre_seat()
kw = dict(fx=al["fx"], gt=al["gt"], tau=0.0, pol=al["polarity"])          # delay applied in the page
w, t = sysm.branches("listener", ic, desk=False, **kw)
wa, ta = sysm.branches("wf_axis_1m_L", 0, **kw)
f5 = sysm.f
cx = lambda z: dict(re=sig(z.real / np.sqrt(2), 5), im=sig(z.imag / np.sqrt(2), 5))   # rms Pa
_, sr = rcsv(AR / "a5_system_responses.csv")
dump("a5.json", dict(f=r(f5, 1), alignment=al, comparison=a5j["crossover_comparison"], eq=a5j["eq"],
                     summary=a5j["summary"], seat=dict(w=cx(w), t=cx(t)), axis=dict(w=cx(wa), t=cx(ta)),
                     sys_cols=open(AR / "a5_system_responses.csv").readline().strip().split(",")[1:],
                     sys=[r(sr[:, i], 2) for i in range(1, sr.shape[1])]))

# ------------------------------------------------------------------ S1 boost loop (spec vs ECO-001)
sys.modules.pop("common", None)          # sim/acoustics and sim/spice both have a common.py
sys.path.insert(0, str(ROOT / "sim" / "spice"))
os.chdir(ROOT / "sim" / "spice")
import s1_boost_loop as s1  # noqa: E402

fb = np.logspace(0, np.log10(s1.FSW / 2 * 0.98), 400)
bode = []
for comp, (rc, cc) in (("spec", (33e3, 47e-9)), ("eco", (100e3, 15e-9))):
    for vin in (6.0, 7.4, 8.4):
        for nel in (0, 1, 2, 3):
            for io, load in ((2.5, "power"), (0.5, "resistive")):
                T, zo, p = s1.loop(fb, vin, io, nel, s1.ESR_EL_NOM, load, rc=rc, cc=cc)
                fc, pm, gm, f180 = s1.margins(fb, T)
                zcl = zo / (1 + T)
                bode.append(dict(comp=comp, vin=vin, nel=nel, iout=io, load=load,
                                 mag=r(20 * np.log10(np.abs(T)), 2), ph=r(np.degrees(np.unwrap(np.angle(T))), 1),
                                 zcl=sig(np.abs(zcl), 4), fc=sig([fc])[0], pm=sig([pm])[0], gm=sig([gm])[0]))
starts = {}
for k in ("s1_start_typ", "s1_start_min", "s1_start_min_rc100k"):
    _, st = rcsv(SR / f"{k}.csv")
    i = thin(st[:, 0], 700)
    starts[k] = dict(t=sig(st[i, 0] * 1e3, 5), v=r(st[i, 1], 3), il=r(st[i, 2], 2))
steps = {}
for k in ("s1_step60", "s1_step74_rc100k"):
    _, st = rcsv(SR / f"{k}.csv")
    i = thin(st[:, 0], 900)
    steps[k] = dict(t=sig(st[i, 0] * 1e3, 6), v=r(st[i, 1], 3), il=r(st[i, 2], 2))
dump("s1.json", dict(f=sig(fb, 4), bode=bode, comp_options=json.loads((SR / "s1_compensation_options.json").read_text()),
                     worst=json.loads((SR / "s1_loop_worst.json").read_text()),
                     startup=json.loads((SR / "s1_startup.json").read_text()), start=starts, step=steps))

# ------------------------------------------------------------------ S2 filter, S3 NTC, S6 FFC, S7 PDN
hh, fr2 = rcsv(SR / "s2_filter_response.csv")
i = thin(fr2[:, 0], 350)
_, zd = rcsv(SR / "s2_driver_impedance.csv")
j = thin(zd[:, 0], 300)
s2j = json.loads((SR / "s2_classd_filter.json").read_text())
hh_ntc, nt = rcsv(SR / "s3_ntc_ts_curve.csv")
s3j = json.loads((SR / "s3_ntc.json").read_text())
sclk = {}
for rs in (33, 47, 68, 82):
    _, sc = rcsv(SR / f"s6_sclk40_rs{rs}.csv")
    tt, vv = minmax_thin(sc[:, 0] * 1e9, sc[:, 1], 500)
    tp, vp = minmax_thin(sc[:, 0] * 1e9, sc[:, 2], 250)
    sclk[str(rs)] = dict(t=r(tt, 3), v=r(vv, 3), tp=r(tp, 3), vp=r(vp, 3))
xt = {}
for rs in (33, 68):
    _, x = rcsv(SR / f"s6_xtalk_mosi_rs{rs}.csv")
    cols = {}
    for ci, name in ((1, "sclk"), (2, "mosi"), (3, "cs"), (4, "dc")):
        tt, vv = minmax_thin(x[:, 0] * 1e9, x[:, ci], 400)
        cols[name] = dict(t=r(tt, 3), v=r(vv, 3))
    xt[str(rs)] = cols
s6j = json.loads((SR / "s6_ffc_si.json").read_text())
s6j.pop("ffc_lines_1mm_above_metal", None)
dump("s2s3s6.json", dict(
    filt=dict(f=sig(fr2[i, 0], 4), cols=hh[1:], data=[r(fr2[i, c], 3) for c in range(1, fr2.shape[1])]),
    zdrv=dict(f=sig(zd[j, 0], 4), woofer=r(zd[j, 1], 3), tweeter=r(zd[j, 2], 3)),
    s2=dict(validation=s2j["validation"], ac=s2j["ac"], peaks=s2j["peaks"]),
    ntc=dict(T=r(nt[:, 0], 2), b3435=r(nt[:, 1], 3), b3380=r(nt[:, 2], 3), j=s3j),
    sclk=sclk, xtalk=xt, s6=s6j))

hh, pd = rcsv(PR / "s7_pdn_impedance.csv")
i = thin(pd[:, 0], 400)
dump("s7.json", dict(f=sig(pd[i, 0], 4), cols=hh[1:], data=[sig(pd[i, c], 4) for c in range(1, pd.shape[1])],
                     j=json.loads((PR / "s7_pdn.json").read_text())))


# ------------------------------------------------------------------ A3, S4, S5 (compact sections)
a3j = json.loads((AR / "a3_woofer_diffraction.json").read_text())
hh = open(AR / "a3_woofer_responses.csv").readline().strip().split(",")
_, a3 = rcsv(AR / "a3_woofer_responses.csv")
dump("a3.json", dict(f=r(a3[:, 0], 1), cols=hh[1:], data=[r(a3[:, i], 2) for i in range(1, a3.shape[1])],
                     tunnel={k: (r(v, 2) if isinstance(v, list) else v) for k, v in a3j["tunnel"].items()},
                     summary=a3j["summary"], geom=a3j["tunnel_geometry"]))
hh = open(SR / "s4_trim_dc.csv").readline().strip().split(",")
_, s4 = rcsv(SR / "s4_trim_dc.csv")
s5w = {}
for k in ("tight", "gap2ms", "gap3ms", "gap5ms"):
    hh5 = open(SR / f"s5_{k}.csv").readline().strip().split(",")
    _, x = rcsv(SR / f"s5_{k}.csv")
    i = thin(x[:, 0], 600)
    s5w[k] = {c: r(x[i, n] * (1e3 if n == 0 else 1), 3) for n, c in enumerate(hh5)}
dump("s4s5.json", dict(trim=dict(v=r(s4[:, 0], 3), cols=hh[1:], data=[r(s4[:, i], 3) for i in range(1, s4.shape[1])]),
                       s4=json.loads((SR / "s4_pvdd_trim.json").read_text()), s5=json.loads((SR / "s5_esp32_reset.json").read_text()),
                       waves=s5w))

# ------------------------------------------------------------------ static figures used on the page
figs = {
    "docs/figures/acoustics/a4_mode_shapes_main_assembly.png": "a4_modes_main.png",
    "docs/figures/acoustics/a4_mode_shapes_all_braces.png": "a4_modes_braces.png",
    "docs/figures/acoustics/a2_a3_bem_hull_mesh_and_cad_check.png": "bem_mesh.png",
    "docs/figures/spice/s6_mosi_eye.png": "s6_mosi_eye.png",
    "mech/concept/view_iso_internals.png": "concept_internals.png",
}
for src, dst in figs.items():
    shutil.copy(ROOT / src, IMG / dst)
print("done")
