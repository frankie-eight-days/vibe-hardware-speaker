# Render PNG views of the packaging concept from build/*.stl (written by speaker_concept.py).
# Run:  .venv/bin/python mech/concept/render_views.py
import json, os
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build")
meta = json.load(open(os.path.join(B, "parts.json")))
meshes = {n: pv.read(os.path.join(B, n + ".stl")) for n in meta}
W, H = 1600, 1000


def plotter(title):
    p = pv.Plotter(off_screen=True, window_size=(W, H))
    p.set_background("white")
    p.add_text(title, font_size=12, color="black", position="upper_left")
    return p


def add_parts(p, skip=(), opacity=None, clip=None, show_keepouts=False):
    for n, m in meshes.items():
        g = meta[n]["group"]
        if n in skip or g in skip:
            continue
        if g == "keepout" and not show_keepouts:
            continue
        mm = m
        if clip is not None:
            normal, origin = clip
            try:
                mm = m.clip_closed_surface(normal=normal, origin=origin)
            except Exception:
                mm = m.clip(normal=normal, origin=origin, invert=False)
            if mm.n_points == 0:
                continue
        op = 1.0
        if opacity and n in opacity:
            op = opacity[n]
        elif g == "keepout":
            op = 0.35
        p.add_mesh(mm, color=meta[n]["color"], opacity=op, smooth_shading=False, show_edges=False)


def axes_note(p, txt):
    p.add_text(txt, font_size=9, color="#444444", position="lower_left")


def save(p, name, cam, parallel=False, zoom=1.0):
    p.camera_position = cam
    if parallel:
        p.enable_parallel_projection()
    p.camera.zoom(zoom)
    p.screenshot(os.path.join(HERE, name))
    p.close()
    print("wrote", name)


# coordinates: X long axis, -Y front, +Z up
iso_cam = [(-260, -330, 220), (0, 0, 0), (0, 0, 1)]
iso_rear = [(260, 330, 160), (0, 0, 0), (0, 0, 1)]

p = plotter("Iso (front-left-top). Grille shown translucent.")
add_parts(p, opacity={"grille_alu": 0.35})
axes_note(p, "X = length (210 body / 216 over PR flanges), -Y = front, Z = up.  D = 95 mm")
save(p, "view_iso.png", iso_cam, zoom=1.25)

p = plotter("Iso, front shell + grille hidden: internal packaging")
add_parts(p, skip=("shell_front", "grille_alu", "end_cap_L"), show_keepouts=True)
axes_note(p, "red = PR excursion keep-out, light blue = battery swell envelope, yellow = sealed tweeter pods")
save(p, "view_iso_internals.png", iso_cam, zoom=1.25)

p = plotter("Rear iso: rear shell (battery tray), USB-C pocket, knob/display on top")
add_parts(p)
save(p, "view_iso_rear.png", iso_rear, zoom=1.25)

p = plotter("Front (grille hidden)")
add_parts(p, skip=("grille_alu",))
save(p, "view_front.png", [(0, -600, 0), (0, 0, 0), (0, 0, 1)], parallel=True, zoom=1.45)

p = plotter("Top")
add_parts(p, opacity={"grille_alu": 0.5})
save(p, "view_top.png", [(0, 0, 600), (0, 0, 0), (0, 1, 0)], parallel=True, zoom=1.45)

for xs, tag in ((33.0, "woofer"), (83.0, "tweeter"), (0.0, "centre")):
    p = plotter(f"Cross-section at X = {xs:+.0f} mm ({tag} plane), looking -X")
    add_parts(p, clip=((-1, 0, 0), (xs, 0, 0)), show_keepouts=True, skip=("grille_alu",))
    axes_note(p, "front (-Y) is left; top is up")
    save(p, f"view_section_x{int(xs):+d}_{tag}.png".replace("+", "p").replace("-", "m"),
         [(xs + 600, 0, 0), (xs, 0, 0), (0, 0, 1)], parallel=True, zoom=2.0)

p = plotter("Mid-section: horizontal cut at Z = +2 mm, seen from above")
add_parts(p, clip=((0, 0, -1), (0, 0, 2.0)), show_keepouts=True, skip=("grille_alu",))
axes_note(p, "front (-Y) is down")
save(p, "view_section_z_mid.png", [(0, 0, 600), (0, 0, 0), (0, 1, 0)], parallel=True, zoom=1.45)

p = plotter("Mid-section: horizontal cut at Z = -30 mm (main board level), seen from above")
add_parts(p, clip=((0, 0, -1), (0, 0, -30.0)), skip=("grille_alu",))
save(p, "view_section_z_board.png", [(0, 0, 600), (0, 0, 0), (0, 1, 0)], parallel=True, zoom=1.45)
