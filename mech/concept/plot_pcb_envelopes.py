# Plot main-board and UI-board envelopes (outline, holes, height zones, connector placements, keep-outs)
# from build/report.json written by speaker_concept.py.
# Run:  .venv/bin/python mech/concept/plot_pcb_envelopes.py
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(os.path.join(HERE, "build", "report.json")))
mb, ui, P = r["mainboard"], r["uiboard"], r["params"]

# ---------------- main board ----------------
fig, ax = plt.subplots(figsize=(15, 6.2))
(x0, x1), (y0, y1) = mb["outline_x"], mb["outline_y"]
tx0, tx1, ty1 = mb["usb_tab"]
poly = [(x0, y0), (x1, y0), (x1, y1), (tx1, y1), (tx1, ty1), (tx0, ty1), (tx0, y1), (x0, y1)]
ax.add_patch(Polygon(poly, closed=True, fc="#e8f5e9", ec="#1b5e20", lw=2.0, zorder=1))
zcol = {7.0: "#ffcdd2", 7.5: "#ffe0b2", 10.0: "#fff9c4", 21.0: "#c8e6c9", 24.0: "#b2dfdb"}
for name, z in r["mainboard_height_zones_mm_above_top"].items():
    if name.startswith("B_under_motor"):
        continue
    (zx0, zx1), (zy0, zy1), h = z["x"], z["y"], z["hmax"]
    c = zcol.get(h, "#eeeeee")
    ax.add_patch(Rectangle((zx0, zy0), zx1 - zx0, zy1 - zy0, fc=c, ec="#9e9e9e", lw=0.6, alpha=0.75, zorder=2))
    ax.text((zx0 + zx1) / 2, zy0 + 1.0, f"{name.split('_')[0]}: h<={h:g}", ha="center", va="bottom", fontsize=7, color="#424242", zorder=6)
ka = P.get("mb_antenna_keepout_x", -75.0)
ax.add_patch(Rectangle((x0 - 4, y0), ka - x0 + 4, y1 - y0, fc="none", ec="#c62828", hatch="///", lw=1.2, zorder=3))
ax.text(x0 + 1, y1 + 1.5, "ANTENNA KEEP-OUT\n(no copper, all layers)", color="#c62828", fontsize=8, va="bottom")
for n, (bx0, bx1, by0, by1, h) in mb["components"].items():
    ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fc="#90caf9", ec="#0d47a1", lw=1.0, alpha=0.9, zorder=4))
    ax.text((bx0 + bx1) / 2, (by0 + by1) / 2, f"{n}\n{h:g} mm", ha="center", va="center", fontsize=6.5, zorder=7)
for hx, hy in mb["holes"]:
    ax.add_patch(Circle((hx, hy), 3.25, fc="white", ec="black", lw=1, zorder=5))
    ax.add_patch(Circle((hx, hy), 1.6, fc="#616161", ec="black", lw=0.5, zorder=5))
    ax.text(hx, hy - 5.2, f"({hx:g},{hy:g})", ha="center", fontsize=6.5, zorder=7)
ax.annotate("FRONT (-Y, under woofers / grille)", (0, y0 - 4), ha="center", fontsize=9)
ax.annotate("REAR (+Y): USB-C exits rear shell here", (0, ty1 + 2), ha="center", fontsize=9)
ax.set_xlim(x0 - 8, x1 + 8); ax.set_ylim(y0 - 7, ty1 + 6); ax.set_aspect("equal")
ax.set_xlabel("X (mm, enclosure coords; board local = X+90)"); ax.set_ylabel("Y (mm; board local = Y+21)")
ax.set_title(f"Main board envelope {x1 - x0:g} x {y1 - y0:g} mm (+USB tab to Y={ty1:g}), 4L 1.6 mm, bottom face Z={mb['z_bottom']:g}. "
             "Shaded = max top-side component height (mm); bottom side: <=2 mm (standoffs 6.5 mm)", fontsize=9)
ax.grid(True, lw=0.3)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "mainboard_envelope.png"), dpi=130)

# ---------------- UI board ----------------
fig, ax = plt.subplots(figsize=(15, 4.6))
ax.add_patch(Polygon(ui["outline"], closed=True, fc="#e8f5e9", ec="#1b5e20", lw=2.0))
ax.add_patch(Circle((P["disp_x"], 0), P["disp_mod_d"] / 2, fc="#c5cae9", ec="#1a237e", alpha=0.7))
ax.add_patch(Rectangle((P["disp_x"] - 8, P["disp_mod_d"] / 2 - 2), 16, P["disp_mod_tab"] - P["disp_mod_d"] + 2, fc="#c5cae9", ec="#1a237e", alpha=0.7))
ax.add_patch(Rectangle((P["disp_x"] - 10.2, 12.0), 20.4, 2.6, fc="#3949ab", ec="k"))
ax.text(P["disp_x"], 0, "Waveshare 1.28\" module\nØ37.5 (40.4 w/ tab), glass up\n8-pin 2.54 header row at Y=13.3", ha="center", va="center", fontsize=7)
ax.add_patch(Rectangle((P["knob_x"] - 6.2, -6), 12.4, 12, fc="#bcaaa4", ec="#4e342e"))
ax.add_patch(Circle((P["knob_x"], 0), P["knob_d"] / 2, fc="none", ec="#bf360c", ls="--"))
ax.text(P["knob_x"], -10.5, "EC11 encoder (THT)\nknob Ø26 above", ha="center", fontsize=7)
for bx in P["btn_x"]:
    ax.add_patch(Rectangle((bx - 2.55, -2.55), 5.1, 5.1, fc="#bcaaa4", ec="#4e342e"))
ax.text(sum(P["btn_x"]) / 3, -7.5, "3x tact 5.1 mm (power / BT / play)", ha="center", fontsize=7)
ax.add_patch(Rectangle((P["mic_x"] - 1.75, -1.4), 3.5, 2.8, fc="#ef9a9a", ec="#b71c1c"))
ax.text(P["mic_x"], 3, "MEMS mic (bottom side,\nport via Ø1 hole + gasket)", ha="center", fontsize=6.5)
for hx, hy in ui["standoffs"]:
    ax.add_patch(Circle((hx, hy), 3.0, fc="white", ec="k")); ax.add_patch(Circle((hx, hy), 1.25, fc="#616161"))
ax.add_patch(Rectangle((58, 16.5), 26, 5.5, fc="#90caf9", ec="#0d47a1"))
ax.text(71, 19.2, "J1 FFC 20P (AFA07-S20FCA), cable exits +Y", ha="center", va="center", fontsize=6.5)
ax.set_xlim(-98, 98); ax.set_ylim(-26, 28); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
ax.set_title(f"UI board envelope (top view, +Y = rear). Top face Z={ui['z_top']:g}, 1.6 mm. Top-side parts <= 6.5 mm except display stack; "
             "bottom side <= 3 mm (tweeter pods 2.3 mm below at |X|>65)", fontsize=9)
ax.set_xlabel("X (mm, enclosure coords)"); ax.set_ylabel("Y (mm)")
fig.tight_layout(); fig.savefig(os.path.join(HERE, "uiboard_envelope.png"), dpi=130)
print("wrote mainboard_envelope.png, uiboard_envelope.png")
