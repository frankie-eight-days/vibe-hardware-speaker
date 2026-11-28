#!/usr/bin/env python3
"""ID sensitivity of the A1 bass alignment to net box volume (read-only use of the committed A1 model).

Question (industrial design): if a new enclosure shape changes the net internal volume, what happens to
F3/F6 and the pink-noise maximum? Uses exactly the committed model (`sim/acoustics/bass_model.py`) and
the A1 settings (QL 10, QA 100, crest 3, 15.5 V limiter, BW4 63 Hz target, 18 dB boost cap). The committed
scripts are not modified; nothing in results/ or docs/figures/ is overwritten.

Three views per volume:
  A  PR mass kept at 3.5 g, bass EQ re-designed for the new volume (normal practice: re-fit the 4 biquads)
  B  PR mass re-optimised (0..16.75 g in 0.25 g steps) + EQ re-designed
  C  PR mass 3.5 g, EQ left as designed for 0.82 L (what happens if nobody re-tunes the DSP)

Run: .venv/bin/python sim/acoustics/id_sens/a1_volume_sensitivity.py   (~20 s)
Out: sim/acoustics/id_sens/a1_volume_sensitivity.json (+ console table)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np            # noqa: E402

import bass_model as bm       # noqa: E402
import common                 # noqa: E402

PARTS = common.load_parts()
W, P = PARTS["ND65-8"]["ts"], PARTS["DMA58-PR"]["ts"]
VB0 = 0.82e-3                 # A1 baseline (final) net volume
QL, QA, CREST, F3T, FX, MAXB = 10.0, 100.0, 3.0, 63.0, 2500.0, 18.0
M35 = 3.5e-3
F = np.logspace(1, np.log10(20000), 600)
BAND = (F >= 15) & (F <= 1000)
R_PB = (F > 300) & (F < 600)


def run(vb, m_add, g_fixed=None, href_fixed=None):
    s = bm.system(F, W, P, vb, m_add, ql=QL, qa=QA)
    if g_fixed is None:
        g, href = bm.ideal_eq(F, s, f3=F3T, max_boost_db=MAXB)
    else:
        g, href = g_fixed, href_fixed
    pink, lim, pw, cand = bm.pink_estimate(F, s, W, P, g, href, crest=CREST, fx=FX)
    rdb = 20 * np.log10(np.abs(s["p_hs"]) * g / href)
    rdb -= np.mean(rdb[R_PB])                      # re-reference to the passband
    ndb = bm.spl_pk(s["p_hs"])
    v_allow, which = bm.sine_limits(s, W, P)
    maxspl = bm.spl_pk(s["p_hs"] * v_allow)
    p_pb = v_allow[BAND] * href / g[BAND]
    return dict(vb_l=vb * 1e3, m_add_g=m_add * 1e3, fb_hz=s["fb"], pink_db=pink, pink_limit=lim,
                margins_db={k: v - pink for k, v in cand.items()},
                f3_eq_hz=bm.f_at_level(F, rdb, 0, 3), f6_eq_hz=bm.f_at_level(F, rdb, 0, 6),
                f3_nat_hz=bm.f_at_level(F, ndb, np.mean(ndb[R_PB]), 3),
                max_boost_db=float(20 * np.log10(g[BAND].max())),
                sine_max_50hz_db=float(np.interp(50, F, maxspl)), sine_max_63hz_db=float(np.interp(63, F, maxspl)),
                flat_ceiling_db=float(bm.spl_pk(p_pb.min())), g=g, href=href)


base = run(VB0, M35)
g0, h0 = base["g"], base["href"]
rows = []
for label, fac in (("-30 %", 0.70), ("-20 %", 0.80), ("-10 %", 0.90), ("baseline 0.82 L", 1.00),
                   ("+10 %", 1.10), ("+20 %", 1.20)):
    vb = VB0 * fac
    a = run(vb, M35)
    ms = np.arange(0, 2.5 * P["mms_kg"] + 1e-9, 0.25e-3)
    b = max((run(vb, m) for m in ms), key=lambda r: r["pink_db"])
    c = run(vb, M35, g0, h0)
    rows.append(dict(case=label, factor=fac, A=a, B=b, C=c))

strip = lambda r: {k: v for k, v in r.items() if k not in ("g", "href")}
out = dict(question="Net-volume sensitivity of the A1 bass alignment for industrial-design changes",
           model="sim/acoustics/bass_model.py (unchanged), settings as sim/acoustics/a1_bass_lumped.py",
           baseline=strip(base),
           rows=[dict(case=r["case"], factor=r["factor"], A_eq_redesigned=strip(r["A"]),
                      B_mass_reoptimised=strip(r["B"]), C_eq_not_retuned=strip(r["C"])) for r in rows])
with open(os.path.join(HERE, "a1_volume_sensitivity.json"), "w") as fh:
    json.dump(out, fh, indent=1, default=float)

print(f"{'case':16s} {'Vb L':>5s} | A: fb  F3/F6eq  boost pink(lim)        sine50 sine63 | B: m g pink | C: F3/F6 pink")
for r in rows:
    a, b, c = r["A"], r["B"], r["C"]
    print(f"{r['case']:16s} {a['vb_l']:5.3f} | {a['fb_hz']:5.1f} {a['f3_eq_hz']:5.1f}/{a['f6_eq_hz']:4.1f} "
          f"{a['max_boost_db']:5.1f} {a['pink_db']:6.2f}({a['pink_limit']:11s}) {a['sine_max_50hz_db']:5.1f} "
          f"{a['sine_max_63hz_db']:5.1f} | {b['m_add_g']:4.2f} {b['pink_db']:6.2f} | "
          f"{c['f3_eq_hz']:5.1f}/{c['f6_eq_hz']:4.1f} {c['pink_db']:6.2f}")

# ------------------------------------------------------------------ leaks: an unsealed hole through the 3 mm wall
# Hole of diameter d through a wall l: viscous R = 8 mu l / (pi a^4), inertance M = rho (l + 0.85 d) / S.
# Expressed as an equivalent leakage Q at fb (Q_hole = |Z_hole| w_b Cab), combined in parallel with the
# baseline QL 10, then run through the same A1 evaluation (3.5 g, EQ re-designed).
MU = 1.8e-5
leak_rows = []
s0 = bm.system(F, W, P, VB0, M35, ql=QL, qa=QA)
wb = 2 * np.pi * s0["fb"]
for dmm in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
    if dmm == 0:
        ql_eff, qh = QL, float("inf")
    else:
        a = dmm / 2e3
        S = np.pi * a * a
        Z = 8 * MU * 3e-3 / (np.pi * a ** 4) + 1j * wb * bm.RHO * (3e-3 + 0.85 * 2 * a) / S
        qh = abs(Z) * wb * s0["cab"]
        ql_eff = 1 / (1 / QL + 1 / qh)
    s = bm.system(F, W, P, VB0, M35, ql=ql_eff, qa=QA)
    g, href = bm.ideal_eq(F, s, f3=F3T, max_boost_db=MAXB)
    pink = bm.pink_estimate(F, s, W, P, g, href, crest=CREST, fx=FX)[0]
    leak_rows.append(dict(hole_d_mm=dmm, Q_hole=qh, QL_eff=ql_eff, pink_db=pink))
    print(f"open hole d {dmm:3.1f} mm: Q_hole {qh:8.2f}  QL_eff {ql_eff:5.2f}  pink {pink:6.2f} dB")
out["leaks_single_open_hole_3mm_wall"] = leak_rows
with open(os.path.join(HERE, "a1_volume_sensitivity.json"), "w") as fh:
    json.dump(out, fh, indent=1, default=float)
