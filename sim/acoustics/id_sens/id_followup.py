#!/usr/bin/env python3
"""Follow-up estimates for docs/id/constraints.md §7 (questions from docs/id/benchmark.md).

  1. Perforated grille (23 / 40 / 51 % open) and grille cloth: insertion loss, the grille-over-cavity
     resonance (grille mass on the air gap in front of the cone/dome), and the plate mode of the sheet
     over a woofer bore.
  2. Tweeter behind a continuous grille: the same cavity resonance for dome-to-grille gaps of 2-4 mm.
  3. TPU halo around each PR: air-mass loading, choking when resting on the halo, notch/vent area.
  4. Rounded regular octagon section (R 6 outer corners): net volume, woofer tunnel, PR annulus, pod fit,
     and the tweeter at 45 deg vs 40 deg from the committed A2 vertical polar (results/a2_polar_bezel_v.csv).
  5. N52 1/4" x 1/4" disc magnet: axial field vs distance, force on the PR's steel add-mass washers.
Run: .venv/bin/python sim/acoustics/id_sens/id_followup.py  -> id_followup.json
"""
import csv
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "results")
RHO, C0, MU0 = 1.20, 343.0, 4e-7 * math.pi
OUT = {}


# ------------------------------------------------------------------------------- 1/2 grille
def t_eff(d, s, t):
    return t + 0.85 * d * (1 - 1.47 * math.sqrt(s) + 0.47 * s ** 1.5)


def il_mass(f, d, s, t):
    x = 2 * math.pi * f * t_eff(d, s, t) / (2 * C0 * s)
    return 10 * math.log10(1 + x * x)


def f_cav(d, s, t, gap):
    """Grille mass (rho t_eff / sigma per unit area) on the air gap compliance (gap / rho c^2 per area)."""
    return C0 / (2 * math.pi) * math.sqrt(s / (t_eff(d, s, t) * gap))


def plate_bore(s, t=0.81e-3, a=0.0265):
    """First mode of the Al sheet clamped round a dia-53 bore; perforation: stiffness x(1-s)^2, mass x(1-s)."""
    E, nu, rho = 70e9, 0.33, 2700.0
    D = E * t ** 3 / (12 * (1 - nu ** 2)) * (1 - s) ** 2
    return 10.22 / (2 * math.pi * a * a) * math.sqrt(D / (rho * t * (1 - s)))


PERF = {"fine 23 % (dia 1.6 / 0.81 mm)": (1.6e-3, 0.23, 0.81e-3),
        "mid 40 % (dia 3.2 / 0.81 mm)": (3.2e-3, 0.40, 0.81e-3),
        "open 51 % (dia 4.8 / 0.81 mm)": (4.76e-3, 0.51, 0.81e-3)}
gr = {}
for k, (d, s, t) in PERF.items():
    gr[k] = dict(IL_dB={f"{f/1000:g}k": round(il_mass(f, d, s, t), 2) for f in (2500, 5000, 10000, 16000)},
                 f_cavity_kHz={f"gap {g*1e3:g} mm": round(f_cav(d, s, t, g) / 1000, 1) for g in (2e-3, 3e-3, 4e-3, 12e-3)},
                 plate_mode_over_woofer_bore_kHz=round(plate_bore(s) / 1000, 2))
cloth = {f"{r} Pa s/m": round(20 * math.log10(1 + r / (2 * RHO * C0)), 2) for r in (20, 40, 80, 150)}
OUT["grille"] = dict(perforated=gr, cloth_IL_dB_flat=cloth,
                     note="cavity f0: below ~f0/2 the response rises <= ~2.5 dB (undamped lumped bound), above f0 it "
                          "falls ~12 dB/oct; f0 must be >= ~1.5 x 16 kHz to keep the tweeter band clean")

# ------------------------------------------------------------------------------- 3 halo
SP, MP = 14.5e-4, (6.7 + 3.5) * 1e-3          # PR Sd, moving mass incl. 3.5 g add-mass (A1)
CMP = 0.0024
halo = []
for idd, h in ((52e-3, 6e-3), (60e-3, 10e-3), (78e-3, 10e-3), (78e-3, 16e-3)):
    A = math.pi * idd ** 2 / 4
    m_air = RHO * h * SP ** 2 / A                  # air plug in the ring, referred to the PR (kg)
    v_closed = A * h                               # ring closed by a wall/desk
    k_ratio = (RHO * C0 ** 2 * SP ** 2 / v_closed) / (1 / CMP)
    halo.append(dict(ring_id_mm=idd * 1e3, depth_ahead_of_diaphragm_mm=h * 1e3, air_mass_g=round(m_air * 1e3, 4),
                     mass_pct_of_PR=round(100 * m_air / MP, 3),
                     if_closed_by_surface_cavity_cm3=round(v_closed * 1e6, 1),
                     if_closed_stiffness_x_PR_suspension=round(k_ratio, 1)))
U = 2 * math.pi * 48 * 0.005 * SP                  # PR peak volume velocity at its 5 mm limit, 48 Hz (A1)
vents = [dict(vent_area_cm2=a, peak_air_speed_m_s=round(U / (a * 1e-4), 1)) for a in (0.5, 1, 2, 3, 5)]
OUT["halo"] = dict(rows=halo, vent_speed_at_PR_limit=vents, pr_peak_volume_velocity_m3_s=U)

# ------------------------------------------------------------------------------- 4 octagon
t8 = math.tan(math.pi / 8)


def rounded_oct_area(a, rc):
    s = a - rc
    return 8 * t8 * s * s + 16 * t8 * s * rc + math.pi * rc * rc


A_base_in = 6156.0                                   # mm2, section_check baseline inner area
A_oct_in = rounded_oct_area(44.5, 3.0)
A_oct_out = rounded_oct_area(47.5, 6.0)
# woofer tunnel depth over the piston (r <= 22.9): outer skin |y| = min(47.5 front facet, 67.18-|z| (45 deg facet))
zz = np.linspace(-22.9, 22.9, 461)
w = np.sqrt(np.maximum(22.9 ** 2 - zz ** 2, 0))     # chord weight (piston strip width)
oct_front = np.minimum(47.5, 47.5 * math.sqrt(2) - np.abs(zz))
circ_front = np.sqrt(47.5 ** 2 - zz ** 2)
piston = 33.9
tun_oct = float(np.sum((oct_front - piston) * w) / np.sum(w))
tun_circ = float(np.sum((circ_front - piston) * w) / np.sum(w))
# tweeter pod on the 45 deg facet vs the UI board (Y -9..22, Z 31.4..39)
ax = np.array([-math.cos(math.radians(45)), math.sin(math.radians(45))])
perp = np.array([ax[1], -ax[0]])
face = 47.5 * np.array([-math.cos(math.radians(45)), math.sin(math.radians(45))])
pod = [face + 17.5 * perp, face - 17.5 * perp, face - 21.5 * ax - 17.5 * perp, face - 21.5 * ax + 17.5 * perp]
dense = np.concatenate([pod[k] + np.linspace(0, 1, 50)[:, None] * (pod[(k + 1) % 4] - pod[k]) for k in range(4)])
dy = np.maximum(np.maximum(-9 - dense[:, 0], dense[:, 0] - 22), 0)
dz = np.maximum(np.maximum(31.4 - dense[:, 1], dense[:, 1] - 39), 0)
ui_clear_45 = float(np.min(np.hypot(dy, dz)))
pr_clear_45 = float(np.min(np.linalg.norm(dense, axis=1)) - 25.0)
# A2 vertical polar: listener at -21 deg re the 40 deg axis; with a 45 deg axis it is at -26 deg
rows = list(csv.reader(open(os.path.join(RES, "a2_polar_bezel_v.csv"))))
angs = np.array([float(x) for x in rows[0][1:]])
pol = {}
for r in rows[1:]:
    f = float(r[0])
    for tgt in (2500, 5000, 8000, 10000, 12500, 16000):
        if abs(f - tgt) / tgt < 0.03:
            v = np.array([float(x) for x in r[1:]])
            pol[f"{tgt/1000:g}k"] = dict(at_40deg=round(float(np.interp(-21, angs, v)), 2),
                                        at_45deg=round(float(np.interp(-26, angs, v)), 2),
                                        delta=round(float(np.interp(-26, angs, v) - np.interp(-21, angs, v)), 2))
OUT["octagon"] = dict(
    inner_area_cm2=round(A_oct_in / 100, 2), baseline_inner_area_cm2=A_base_in / 100,
    outer_area_cm2=round(A_oct_out / 100, 2), baseline_outer_area_cm2=70.21,
    net_volume_change_cm3=round((A_oct_in - A_base_in) * 202 / 1000), net_volume_change_pct=round(100 * (A_oct_in - A_base_in) * 202 / 1000 / 820, 1),
    across_flats_mm=95.0, across_corners_mm=round(2 * ((47.5 - 6) / math.cos(math.pi / 8) + 6), 1),
    facet_flat_width_mm=round(2 * (47.5 - 6) * t8, 1),
    min_inradius_inner_mm=round((30.4 + 32.5) / math.sqrt(2), 2),
    woofer_tunnel_mean_depth_mm=dict(octagon=round(tun_oct, 1), circle=round(tun_circ, 1)),
    tweeter_45=dict(pr_basket_clear_mm=round(pr_clear_45, 1), ui_board_clear_mm=round(ui_clear_45, 1),
                    face_height_above_desk_mm=round(face[1] + 47.5, 1)),
    tweeter_listener_level_re_axis_dB=pol)

# ------------------------------------------------------------------------------- 5 magnets
BR, RM, LM = 1.45, 3.175e-3, 6.35e-3              # N52 Br ~1.43-1.48 T; 1/4" x 1/4" disc


def b_axis(z):
    return BR / 2 * ((LM + z) / math.hypot(RM, LM + z) - z / math.hypot(RM, z))


def f_washer(z, v=1.3e-7):
    """Pull on a small soft-steel washer (~1 g) on axis: induced moment ~3 V H (unsaturated, sphere-like),
    F = m dB/dz (numerical gradient)."""
    b = b_axis(z)
    m = 3 * v * b / MU0
    db = (b_axis(z + 1e-4) - b_axis(z - 1e-4)) / 2e-4
    return abs(m * db)


mag = []
for zmm in (3, 5, 10, 15, 20, 30, 50):
    z = zmm * 1e-3
    F = f_washer(z)
    mag.append(dict(distance_mm=zmm, B_axis_mT=round(b_axis(z) * 1e3, 2), pull_on_PR_washers_N=round(F, 4),
                    PR_offset_mm=round(F * CMP * 1e3, 3)))
OUT["magnet_n52_quarter_inch"] = mag

with open(os.path.join(HERE, "id_followup.json"), "w") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print(json.dumps(OUT, indent=1, default=float))
