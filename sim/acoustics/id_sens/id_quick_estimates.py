#!/usr/bin/env python3
"""Closed-form / lumped estimates that back docs/id/constraints.md (industrial-design constraints).

Not a committed-sim replacement: each block is a first-order estimate, calibrated where possible to the
committed results it cites. Sections:
  1. RF: distances from the ESP32 antenna (floor plan v1) to metal in the concept CAD
  2. Grille: insertion loss of perforated sheet vs hole size / open area / thickness
  3. Flat panels: clamped / simply-supported strip modes and box-pressure compliance (A4 plate check)
  4. Stability, carry and drop loads
  5. Thermal: gap pads -> metal spreader (hidden behind PETG, or exposed) -> room air; lumped network
     calibrated to hw/experiments/floorplan_v1/FLOORPLAN.md section 4 (thermal_fp.py results)
Run: .venv/bin/python sim/acoustics/id_sens/id_quick_estimates.py   -> id_quick_estimates.json
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {}
RHO, C0 = 1.20, 343.0

# ----------------------------------------------------------------------------------------- 1. RF
# Antenna area (floor plan v1): U101 rot 270 at the +X end, footprint X 62.6..95.1, Y -20.9..-0.9
# (hw/experiments/floorplan_v1/mech/mech_inputs_fp1.json); antenna = last 6.3 mm, overhanging X = 88.2.
# Module top face ~ Z -33.4 + 0.8 (board top Z -33.4, mech_envelope 6).
ANT = dict(x=(88.2, 94.5), y=(-20.0, -1.8), z=(-33.4, -32.6))


def d_box(p):
    q = [min(max(p[i], ANT[k][0]), ANT[k][1]) for i, k in enumerate("xyz")]
    return math.dist(p, q)


def cyl_pts(r, phis, xs):
    return [(x, -r * math.cos(math.radians(f)), r * math.sin(math.radians(f))) for f in phis for x in xs]


phis_g = np.linspace(-45, 58, 207)
xs_g = np.linspace(-96, 96, 385)
grille = cyl_pts(46.75, phis_g, xs_g)                         # inner face of the grille (R 46.75..47.55)
dg = min(d_box(p) for p in grille)
# how far must the grille be cut back so that nothing is within 15 mm?
cut = {}
for phi_min in (-45, -30, -20, -10, 0, 10):
    pts = cyl_pts(46.75, np.linspace(phi_min, 58, 150), xs_g)
    cut[f"phi_min {phi_min}"] = round(min(d_box(p) for p in pts), 1)
xcut = {}
for xmax in (96, 85, 80, 75, 72, 70):
    pts = cyl_pts(46.75, phis_g, np.linspace(-xmax, xmax, 300))
    xcut[f"|x| <= {xmax}"] = round(min(d_box(p) for p in pts), 1)
items = {
    "right cap screw boss phi 270 (insert at R 42, X 87..99)": min(d_box((x, 0.0, -42.0 + 2.0)) for x in np.linspace(87, 99, 25)),
    "right cap screw boss phi 0": min(d_box((x, -40.0, 0.0)) for x in np.linspace(87, 99, 25)),
    "mainboard hole H3 (84.45, 3.04) screw/insert": d_box((84.45, 3.04 - 1.6, -34.0)),
    "PR-R diaphragm (aluminium, r<=21 at X~102)": min(d_box((102.0, -21 * math.cos(a), 21 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 73)),
    "PR-R basket (r 25, X 74..101)": min(d_box((x, -25 * math.cos(a), 25 * math.sin(a))) for x in np.linspace(74, 101, 28) for a in np.linspace(0, 2 * math.pi, 73)),
    "PR-R add-mass washers (r<=10, X~64-68)": min(d_box((x, 0, -10.0)) for x in np.linspace(64, 68, 5)),
    "tweeter R (X 83, phi 40, r 30..47)": min(d_box((x, -r * math.cos(math.radians(40)), r * math.sin(math.radians(40)))) for x in np.linspace(67, 99, 33) for r in np.linspace(30, 47.5, 10)),
    "woofer R frame edge (X 65, |Z|<=32, Y -30)": min(d_box((65.0, y, z)) for y in np.linspace(-30.4, 14, 20) for z in np.linspace(-32, 32, 33)),
    "flat bottom outer skin Z -44.5 (a metal base plate here)": d_box((91.0, -10.0, -44.5)),
    "right end-cap inner face X 101 (a metal cap)": d_box((101.0, -10.0, -33.0)),
}
OUT["rf"] = dict(antenna_box=ANT, rule_mm=15.0, grille_as_drawn_min_mm=round(dg, 1),
                 grille_phi_cut=cut, grille_x_cut=xcut, items_mm={k: round(v, 1) for k, v in items.items()})


# ----------------------------------------------------------------------------------------- 2. grille
def perforate_il(f, d, sigma, t):
    """Insertion loss (dB) of a perforated sheet in a normally incident plane wave, mass-reactance model:
    Z = j w rho t_eff / sigma, t_eff = t + 0.85 d (1 - 1.47 sqrt(sigma) + 0.47 sigma^1.5) (Ingard end
    correction with hole interaction). IL = 20 log10 |1 + Z / (2 rho c)|. Viscous loss neglected (d >= 1 mm)."""
    te = t + 0.85 * d * (1 - 1.47 * math.sqrt(sigma) + 0.47 * sigma ** 1.5)
    x = 2 * math.pi * f * te / (2 * C0 * sigma)
    return 10 * math.log10(1 + x * x)


gr = []
for d, s, t in ((1.0, 0.20, 0.8e-3), (1.5, 0.23, 0.8e-3), (2.0, 0.33, 0.8e-3), (2.0, 0.40, 0.8e-3),
                (3.0, 0.40, 0.8e-3), (3.0, 0.51, 1.0e-3), (1.5, 0.30, 0.5e-3), (2.0, 0.40, 3.0e-3)):
    gr.append(dict(hole_mm=d, open_area=s, t_mm=t * 1e3,
                   **{f"IL_{int(f/1000) if f >= 1000 else f}k_dB": round(perforate_il(f, d * 1e-3, s, t), 2)
                      for f in (2500, 5000, 10000, 16000)}))
OUT["grille_insertion_loss"] = gr

# ----------------------------------------------------------------------------------------- 3. flat panels
E, NU, RHOP = 2.1e9, 0.38, 1270.0       # PETG as in a4_panel_modes.py
VB = 0.82e-3
CAB = VB / (RHO * C0 ** 2)
ETA = 0.03                              # A4 loss factor


def strip(b, t, L=0.20):
    D = E * t ** 3 / (12 * (1 - NU ** 2))
    s = math.sqrt(D / (RHOP * t))
    f_cc = 22.373 / (2 * math.pi * b ** 2) * s             # clamped-clamped strip, 1st mode
    f_ss = math.pi ** 2 / (2 * math.pi * b ** 2) * s       # simply supported strip
    c_cc = b ** 5 * L / (720 * D)                          # volume compliance under uniform p, clamped
    ratio = c_cc / CAB
    return dict(b_mm=b * 1e3, t_mm=t * 1e3, f1_clamped_hz=round(f_cc), f1_simply_hz=round(f_ss),
                compliance_pct_of_box=round(100 * ratio, 2),
                peak_index_db_at_resonance=round(20 * math.log10(ratio / ETA), 1))


D3 = E * 0.003 ** 3 / (12 * (1 - NU ** 2))
plate_check = 35.985 / (2 * math.pi * 0.1 ** 2) * math.sqrt(D3 / (RHOP * 0.003))   # A4 validation: 689.5 Hz
OUT["flat_panels"] = dict(check_clamped_square_100mm_3mm_hz=round(plate_check, 1),
                          strips=[strip(b, t) for t in (0.003, 0.004) for b in (0.04, 0.05, 0.06, 0.08, 0.10)])

# ----------------------------------------------------------------------------------------- 4. stability/carry/drop
masses = {  # g, (y, z) mm   (sources: a4_panel_modes inputs, mech_envelope 1/3, estimates marked ~)
    "shell PETG 310 g (front-biased by the land)": (310, -8.0, 0.0),
    "woofers 2x181 g (motor-heavy)": (362, 4.0, 0.0),
    "battery 189 g": (189, 27.3, 0.0),
    "PRs 2x71.5 g": (143, 0.0, 0.0),
    "~grille 36 g": (36, -45.0, 5.0),
    "~tweeters 2x20 g": (40, -30.0, 25.0),
    "~main board 50 g": (50, 2.0, -34.0),
    "~UI board+display+knob 40 g": (40, 0.0, 40.0),
    "~hardware, foam, wire 40 g": (40, 0.0, 0.0),
}
m_tot = sum(v[0] for v in masses.values())
ycg = sum(v[0] * v[1] for v in masses.values()) / m_tot
zcg = sum(v[0] * v[2] for v in masses.values()) / m_tot
h_cg = zcg + 44.5                                   # above the desk (flat at Z -44.5)
g = 9.81
stab = []
for wflat in (33.0, 45.0, 55.0, 65.0):
    a = math.degrees(math.atan((wflat / 2 - abs(ycg)) / h_cg))
    f_knob = m_tot / 1000 * g * (wflat / 2 - abs(ycg)) / (61.5 + 44.5)          # sideways push at knob top
    stab.append(dict(flat_width_mm=wflat, tip_angle_deg=round(a, 1), sideways_push_at_knob_top_N=round(f_knob, 2)))
drop = []
for stop_mm in (1.0, 2.0, 5.0, 8.0):
    a_g = 1000.0 / stop_mm                                   # 1 m drop, constant deceleration over the crush
    drop.append(dict(stopping_mm=stop_mm, decel_g=round(a_g), battery_189g_N=round(0.189 * g * a_g),
                     woofer_181g_N=round(0.181 * g * a_g)))
OUT["mechanics"] = dict(mass_g=m_tot, cg_y_mm=round(ycg, 1), cg_z_mm=round(zcg, 1), cg_above_desk_mm=round(h_cg, 1),
                        stability=stab, strap_static_4x_weight_N=round(4 * m_tot / 1000 * g, 1), drop_1m=drop)

# ----------------------------------------------------------------------------------------- 5. thermal
# Losses as sim/postlayout/thermal.py playback_case (amp eta 0.90, idle 0.65 W/amp, boost 5.5 %).
AMP_IDLE = 18 * 0.0325 + 3.3 * 0.018


def losses(p):
    amp = AMP_IDLE + p / 2 * (1 / 0.9 - 1)
    pb = 0.055 * 2 * (p / 2 / 0.9 + AMP_IDLE)
    return dict(amp=amp, u901=0.8 * pb, total=2 * amp + pb + 0.15 + 0.4)


# Calibration against FLOORPLAN.md 4 (v1 + 3 gap pads to an ideal 45 C sink):
#  moderate case U301 Tj 56.6 C with 0.709 W -> junction-to-sink per amp = 56.6-45 = 11.6 K -> R_js_amp ~ 16.4 K/W
#  (incl. psi_JB 8.1); sustained limit 28.2 W (h5) set by U901 (no pad): U901 1.44 W reaches 125 C
#  -> R_js_U901 ~ 80/1.44 = 55.6 K/W (incl. psi 14.5). A 4th pad under U901 is taken as R_js = R_js_amp.
R_JS_AMP = (56.6 - 45.0) / losses(1.0)["amp"]
R_JS_901 = (125 - 45.0) / losses(28.2)["u901"]
A_BOARD = 6590e-6
A_SHELL = math.pi * 0.095 * 0.210 + 2 * math.pi * 0.0475 ** 2        # ~0.077 m2 outer skin
H_IN, H_OUT_PL, H_OUT_BARE_AL = 5.0, 10.0, 5.0                         # W/m2K (int.; ext. emissive; bare Al)
R_WALL = 0.003 / 0.20                                                  # m2K/W, 3 mm PETG
R_BOND = 0.0005 / 0.6                                                  # 0.5 mm thermal adhesive/pad
T_TOUCH = {"metal": 48.0, "plastic": 60.0}   # ~IEC 62368-1 TS1 for 1-10 min contact is ~51 metal / 60 plastic


def network(p_out, a_sp, mode, t0, h_b=5.0, pad901=False):
    """Steady state, nodes: board B, spreader S, internal air I; ambient t0.
    mode: 'none' (no pads), 'internal' (spreader free in the box air), 'hidden' (bonded to the inside of the
    PETG wall), 'exposed' (forms part of the outer skin; emissive finish), 'exposed_bare' (bright Al)."""
    L = losses(p_out)
    Q = L["total"]
    g_bi = 2 * h_b * A_BOARD
    g_bs = 0.0 if mode == "none" else 3 / (R_JS_AMP - 8.1)            # 3 landings, board-side part only
    a_sp = 0.0 if mode == "none" else a_sp
    g_so = {"none": 0.0, "internal": 0.0, "hidden": a_sp / (R_BOND + R_WALL + 1 / H_OUT_PL),
            "exposed": a_sp * H_OUT_PL, "exposed_bare": a_sp * H_OUT_BARE_AL}[mode]
    g_si = H_IN * a_sp * (2 if mode == "internal" else 1)
    g_io = (A_SHELL - (a_sp if mode in ("hidden", "exposed", "exposed_bare") else 0)) / (1 / H_IN + R_WALL + 1 / H_OUT_PL)
    # conductance matrix for [B, S, I]
    G = np.array([[g_bi + g_bs, -g_bs, -g_bi],
                  [-g_bs, g_bs + g_so + g_si + 1e-12, -g_si],
                  [-g_bi, -g_si, g_bi + g_si + g_io]])
    q = np.array([Q, g_so * t0, g_io * t0])
    q[1] += 0.0
    T = np.linalg.solve(G, q + np.array([0, 0, 0]) * t0)
    tb, ts, ti = T
    if mode == "none":
        # no pads: calibrate local rise so the v1 no-pad limit matches (10.5 W at h5 with 45 C air)
        tj_amp = ti + (tb - ti) + L["amp"] * (8.1 + 10.8)
        tj_901 = ti + (tb - ti) + L["u901"] * 14.5 + 13.4
    else:
        tj_amp = ts + L["amp"] * R_JS_AMP
        tj_901 = ts + L["u901"] * (R_JS_AMP if pad901 else R_JS_901)
    return dict(Q=Q, T_board=tb, T_spreader=ts, T_air=ti, Tj_amp=tj_amp, Tj_u901=tj_901)


def max_out(a_sp, mode, t0, touch=None, **kw):
    lo, hi = 0.0, 40.0
    def ok(p):
        r = network(p, a_sp, mode, t0, **kw)
        good = max(r["Tj_amp"], r["Tj_u901"]) <= 125.0
        if touch is not None and mode in ("exposed", "exposed_bare"):
            good &= r["T_spreader"] <= touch
        if touch is not None and mode == "hidden":
            # outer PETG skin over the spreader ~ T_s - Q_out*(R_bond+R_wall)/A
            q_out = (r["T_spreader"] - t0) * a_sp / (R_BOND + R_WALL + 1 / H_OUT_PL)
            good &= (r["T_spreader"] - q_out * (R_BOND + R_WALL) / a_sp) <= T_TOUCH["plastic"]
        return good
    if not ok(0.0):
        return 0.0
    if ok(hi):
        return hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return round(lo, 1)


th = dict(calibration=dict(R_js_amp_K_per_W=round(R_JS_AMP, 1), R_js_u901_K_per_W=round(R_JS_901, 1),
                           A_shell_m2=round(A_SHELL, 4),
                           shell_conductance_W_per_K=round(A_SHELL / (1 / H_IN + R_WALL + 1 / H_OUT_PL), 3),
                           board_to_air_W_per_K_h5_h10=[round(2 * 5 * A_BOARD, 3), round(2 * 10 * A_BOARD, 3)]),
          losses_W={str(p): round(losses(p)["total"], 2) for p in (2.9, 12, 20, 28, 40)})
rows = []
for t0 in (25.0, 35.0):
    rows.append(dict(case="no pads (as v1 without ECO-003 #2)", t0=t0, a_cm2=0, P_max_W=max_out(0, "none", t0)))
    for mode in ("internal", "hidden", "exposed", "exposed_bare"):
        for a in (50, 100, 200, 300):
            r = dict(case=mode, t0=t0, a_cm2=a, P_max_W=max_out(a * 1e-4, mode, t0),
                     P_max_touch_W=max_out(a * 1e-4, mode, t0, touch=T_TOUCH["metal"]),
                     P_max_4th_pad_W=max_out(a * 1e-4, mode, t0, pad901=True))
            n = network(12.0, a * 1e-4, mode, t0)
            r["at_12W_T_spreader_C"] = round(n["T_spreader"], 1)
            r["at_12W_T_air_C"] = round(n["T_air"], 1)
            rows.append(r)
th["rows"] = rows
OUT["thermal"] = th

with open(os.path.join(HERE, "id_quick_estimates.json"), "w") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print(json.dumps({k: v for k, v in OUT.items() if k != "thermal"}, indent=1))
print(json.dumps(th["calibration"]), th["losses_W"])
for r in rows:
    print(r)
