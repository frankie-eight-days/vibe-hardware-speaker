# Portable stereo BT speaker -- mechanical PACKAGING CONCEPT (not print-ready).
# Run headless:
#   /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd mech/concept/speaker_concept.py
# Writes (next to this file): speaker_concept.FCStd, speaker_concept.step, build/*.stl,
#   build/report.json (net volume, interference matrix, PCB envelopes), mainboard_outline.dxf/.svg,
#   uiboard_outline.dxf/.svg.  Render PNGs afterwards with render_views.py (.venv python).
#
# Coordinates (mm): X = capsule long axis (+X = right when facing the speaker),
#                   Y = depth (-Y = FRONT / grille side, +Y = rear),  Z = up.
# Polar angle phi on the cross-section is measured from the front (-Y) toward the top (+Z):
#   dir(phi) = (0, -cos phi, sin phi).   phi=0 front, 90 top, 180 rear, -90 bottom.
import os, json, math
import FreeCAD as App
import Part

V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)

# ============================ PARAMETERS ============================
P = dict(
    # --- capsule ---
    L_total=210.0,        # overall length incl. end caps
    D_out=95.0,           # outer diameter (req. 80-95; 95 needed for battery beside 48 mm-deep woofers)
    wall=3.0,             # shell wall (>=3 mm PETG/ASA, 4+ perimeters)
    cap_t=4.0,            # end cap plate thickness (+ radial ribs); PR flange sits proud on its face
    cap_spigot=5.0,       # cap spigot length into the tube (gasket land)
    edge_fillet=3.0,      # fillet on cap outer edge
    flat_bottom_z=-44.5,  # outer flat for stability (chord ~33 mm wide)
    seam_y=24.0,          # front shell / rear shell split plane (Y = const)

    # --- woofer: Dayton ND65-8 (spec sheet: 64 sq frame, 66 BC, 4x4.2 holes, 52 basket, 48 overall, 43 below flange)
    w_flange=64.0, w_flange_r=8.0, w_flange_t=1.5, w_surround_h=3.5,
    w_basket_d=52.0, w_basket_d2=44.0, w_basket_len=23.0,
    w_motor_d=38.0,       # ESTIMATE scaled from drawing (not dimensioned on sheet)
    w_below_flange=43.0,
    w_x=33.0,             # woofer centre |x|; limited by PR rear-excursion keep-out (see check) and 4 mm frame gap
    w_clear=0.5,          # flange-to-inner-wall clearance
    w_hole_d=53.0, w_chamfer=3.0,

    # --- tweeter: Peerless OT19NC00-04 (face Ø33.4, cutout Ø31, depth 17)
    t_face_d=33.4, t_face_t=3.0, t_body_d=31.0, t_depth=17.0,
    t_x=83.0,             # tweeter centre |x| (outboard of woofers, over the PR baskets)
    t_phi=40.0,           # position on shell (deg above front)
    t_elev=40.0,          # tweeter axis elevation above horizontal (req. 35-45); = t_phi -> radial pod
    t_face_r=47.5,        # radial position of faceplate front centre (flush with skin; annulus is only 22.5 deep)
    t_pod_wall=1.5, t_pod_gap=0.0, t_chamber_r=16.0,
    t_wg_boss_r=18.0, t_wg_d=36.0, t_wg_len=3.0,   # short printed conical waveguide in a raised boss

    # --- passive radiator: Dayton DMA58-PR (56 sq flange 3 t, Ø50 basket, 35 below flange, 4xØ3.3 on 64.3 BC)
    pr_flange=56.0, pr_flange_r=3.2, pr_flange_t=3.0, pr_basket_d=50.0, pr_basket_d2=42.0,
    pr_basket_len=27.0, pr_below_flange=35.0, pr_post_d=8.0, pr_mass_d=20.0, pr_mass_len=2.0,
    pr_xmech=7.0, pr_clear_factor=1.5, pr_hole_d=50.5,
    pr_proud=3.0,         # PR flange surface-mounted on the cap face (adds 3 mm per end over the flange)

    # --- battery (chosen pack, see docs/mech_envelope.md) ---
    bat_L=109.0, bat_W=42.0, bat_T=19.5,
    bat_tol_L=5.0, bat_tol_W=2.0,   # vendor tolerance (+/-)
    bat_swell=0.10,                  # >=10 % thickness swell allowance
    tray_wall=2.0, tray_gap_front=1.5,

    # --- main PCB (bottom, horizontal) ---
    mb_z_bot=-35.0, mb_t=1.6, mb_x=(-90.0, 90.0), mb_y=(-21.0, 25.0),
    mb_usb_tab=(-7.0, 7.0, 26.5),    # tab x-range and y-extent for the USB-C receptacle
    mb_holes=[(-70.0, -17.0), (-70.0, 21.0), (86.0, -17.0), (86.0, 12.0), (0.0, -17.0), (18.0, 21.0)],
    mb_antenna_keepout_x=-75.0,   # no copper (all layers) for x < this; WROVER antenna overhangs the -X edge

    # --- UI (top) ---
    ui_z_top=35.0, ui_t=1.6,
    ui_rects=[(-91.0, 91.0, -9.0, 22.0), (-22.0, 22.0, -20.0, 22.0)],
    disp_x=0.0, disp_mod_d=37.5, disp_mod_tab=40.4, disp_mod_t=4.0, disp_view_d=33.5,
    disp_pad_d=46.0, lens_d=40.0, lens_t=1.5,
    knob_x=70.0, knob_d=26.0, knob_h=13.0, knob_pad_d=32.0,
    btn_x=[-60.0, -72.0, -84.0], btn_pad=(-91.0, -53.0, 14.0),
    mic_x=-30.0,
)
p = P
R = p["D_out"] / 2.0
Ri = R - p["wall"]
X_END = p["L_total"] / 2.0          # 105
X_TUBE = X_END - p["cap_t"]         # 99 : tube end / cap inner face
ZF_IN = p["flat_bottom_z"] + p["wall"]


def d(phi_deg):
    a = math.radians(phi_deg)
    return V(0, -math.cos(a), math.sin(a))


def cyl(r, h, base, axis):
    return Part.makeCylinder(r, h, base, axis)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rounded_square_slab(size, r, t, axis):
    """Square plate (size x size x t) with rounded corners, centred at origin, thickness along +axis."""
    if axis == "y":
        b = box(-size / 2, size / 2, 0, t, -size / 2, size / 2)
        edges = [e for e in b.Edges if abs(e.Vertexes[0].Point.y - e.Vertexes[1].Point.y) > 1e-6]
    else:  # x
        b = box(0, t, -size / 2, size / 2, -size / 2, size / 2)
        edges = [e for e in b.Edges if abs(e.Vertexes[0].Point.x - e.Vertexes[1].Point.x) > 1e-6]
    return b.makeFillet(r, edges)


# ============================ ENVELOPES ============================
outer = cyl(R, 2 * X_END, V(-X_END, 0, 0), V(1, 0, 0))
outer = outer.makeFillet(p["edge_fillet"], [e for e in outer.Edges if e.Curve.__class__.__name__ == "Circle"])
outer = outer.cut(box(-200, 200, -200, 200, -200, p["flat_bottom_z"]))
inner = cyl(Ri, 2 * X_TUBE, V(-X_TUBE, 0, 0), V(1, 0, 0)).cut(box(-200, 200, -200, 200, -200, ZF_IN))
GROSS = inner.Volume

parts = {}       # name -> dict(shape, color, kind, fill)
# kind: 'shell' (structure, displacement inside cavity counted geometrically)
#       'disp'  (component, displacement = fill * volume)
#       'keepout' (must stay empty; not counted)
#       'sealed' (sealed sub-volume, excluded from box volume)


def add(name, shape, color, kind, fill=1.0, group="assembly"):
    parts[name] = dict(shape=shape, color=color, kind=kind, fill=fill, group=group)


# ============================ WOOFERS ============================
w_land_y = -math.sqrt(Ri ** 2 - (p["w_flange"] / 2 + p["w_clear"]) ** 2)   # flange front plane
w_back_y = w_land_y + p["w_flange_t"] + p["w_below_flange"]
woofer_meta = {}
for side, sx in (("L", -1), ("R", 1)):
    xw = sx * p["w_x"]
    y0 = w_land_y
    flange = rounded_square_slab(p["w_flange"], p["w_flange_r"], p["w_flange_t"], "y").translate(V(xw, y0, 0))
    surround = cyl(p["w_basket_d"] / 2 - 1, p["w_surround_h"], V(xw, y0, 0), V(0, -1, 0))
    yb = y0 + p["w_flange_t"]
    basket = Part.makeCone(p["w_basket_d"] / 2, p["w_basket_d2"] / 2, p["w_basket_len"], V(xw, yb, 0), V(0, 1, 0))
    ym = yb + p["w_basket_len"]
    motor = cyl(p["w_motor_d"] / 2, w_back_y - ym, V(xw, ym, 0), V(0, 1, 0))
    add(f"woofer_{side}_flange", flange.fuse(surround), (0.15, 0.15, 0.15), "disp", 1.0, "drivers")
    add(f"woofer_{side}_basket", basket, (0.35, 0.35, 0.38), "disp", 0.25, "drivers")
    add(f"woofer_{side}_motor", motor, (0.55, 0.55, 0.6), "disp", 1.0, "drivers")
    woofer_meta[side] = dict(x=xw, land_y=y0, back_y=w_back_y)

# ============================ PASSIVE RADIATORS ============================
pr_mount_x = X_END + p["pr_proud"] - p["pr_flange_t"]   # mounting surface (back face of flange)
X_OVERALL = 2 * (X_END + p["pr_proud"])
pr_keep = {}
for side, sx in (("L", -1), ("R", 1)):
    s = sx
    fl = rounded_square_slab(p["pr_flange"], p["pr_flange_r"], p["pr_flange_t"], "x")
    fl = fl.translate(V(pr_mount_x if s > 0 else -pr_mount_x - p["pr_flange_t"], 0, 0))
    xb0 = s * pr_mount_x
    bas1 = cyl(p["pr_basket_d"] / 2, p["pr_basket_len"], V(xb0, 0, 0), V(-s, 0, 0))   # drawing: straight Ø50
    bas2 = bas1
    xpost0 = xb0 - s * p["pr_basket_len"]
    post = cyl(p["pr_post_d"] / 2, p["pr_below_flange"] - p["pr_basket_len"], V(xpost0, 0, 0), V(-s, 0, 0))
    xm0 = xb0 - s * p["pr_below_flange"]
    mass = cyl(p["pr_mass_d"] / 2, p["pr_mass_len"], V(xm0, 0, 0), V(-s, 0, 0))   # wing nut + add-mass
    xk0 = xm0 - s * p["pr_mass_len"]
    klen = p["pr_xmech"] * p["pr_clear_factor"]           # 1.5 x Xmech(7) = 10.5 mm behind the add-mass
    keep = cyl(p["pr_mass_d"] / 2 + 1.0, klen, V(xk0, 0, 0), V(-s, 0, 0))   # +1 mm radial (rocking)
    add(f"pr_{side}_flange", fl, (0.12, 0.12, 0.12), "disp", 1.0, "drivers")
    add(f"pr_{side}_basket", bas1.fuse(bas2), (0.3, 0.3, 0.32), "disp", 0.2, "drivers")
    add(f"pr_{side}_post_mass", post.fuse(mass), (0.7, 0.6, 0.2), "disp", 1.0, "drivers")
    add(f"pr_{side}_excursion_keepout", keep, (1.0, 0.2, 0.2), "keepout", 0.0, "keepout")
    pr_keep[side] = (min(xk0, xk0 - s * klen), max(xk0, xk0 - s * klen))

# ============================ TWEETER PODS ============================
ea = math.radians(p["t_elev"])
t_axis = V(0, -math.cos(ea), math.sin(ea))          # acoustic axis (out of the box)
tweeter_meta = {}
pod_outer_all, pod_cut_all, boss_all = [], [], []
for side, sx in (("L", -1), ("R", 1)):
    c = d(p["t_phi"]) * p["t_face_r"] + V(sx * p["t_x"], 0, 0)    # faceplate front-face centre
    back = t_axis * -1
    face = cyl(p["t_face_d"] / 2, p["t_face_t"], c, back)   # faceplate front flush at c
    body = cyl(p["t_body_d"] / 2 - 2.0, p["t_depth"], c + back * p["t_face_t"], back)
    add(f"tweeter_{side}", face.fuse(body), (0.1, 0.1, 0.1), "sealed", 1.0, "drivers")
    depth_tot = p["t_face_t"] + p["t_depth"] + p["t_pod_gap"] + p["t_pod_wall"]
    r_out = p["t_chamber_r"] + p["t_pod_wall"]
    pod_out = cyl(r_out, depth_tot, c, back)
    boss = cyl(p["t_wg_boss_r"], p["t_wg_len"] + 8.0, c - t_axis * 8.0, t_axis)          # raised waveguide boss
    pod_in = cyl(p["t_chamber_r"], depth_tot - p["t_pod_wall"] - p["t_face_t"], c + back * p["t_face_t"], back)
    cbore = cyl(p["t_face_d"] / 2 + 0.3, p["t_face_t"], c + back * p["t_face_t"], t_axis)   # faceplate seat
    wg = Part.makeCone(p["t_face_d"] / 2 + 0.3, p["t_wg_d"] / 2, p["t_wg_len"], c, t_axis)
    wg = wg.fuse(cyl(p["t_wg_d"] / 2, 30, c + t_axis * p["t_wg_len"], t_axis))
    pod_outer_all.append(pod_out)
    boss_all.append(boss)
    pod_cut_all += [pod_in, cbore, wg]
    tweeter_meta[side] = dict(face_centre=[round(c.x, 1), round(c.y, 1), round(c.z, 1)])
    # sealed pod (interior + walls) is excluded from the box volume
    add(f"tweeter_pod_{side}_sealed", pod_out.common(inner), (0.85, 0.75, 0.3), "sealed", 1.0, "keepout")

# ============================ BATTERY + TRAY ============================
bat_T_sw = p["bat_T"] * (1 + p["bat_swell"])
bay_L = p["bat_L"] + 2 * p["bat_tol_L"]
bay_W = p["bat_W"] + 2 * p["bat_tol_W"]
y_tray_front = w_back_y + p["tray_gap_front"]
y_bat0 = y_tray_front + p["tray_wall"]
y_bat1 = y_bat0 + bat_T_sw
bat_mid_y = y_bat0 + bat_T_sw / 2
battery = box(-p["bat_L"] / 2, p["bat_L"] / 2, bat_mid_y - p["bat_T"] / 2, bat_mid_y + p["bat_T"] / 2,
              -p["bat_W"] / 2, p["bat_W"] / 2)
swell_env = box(-bay_L / 2, bay_L / 2, y_bat0, y_bat1, -bay_W / 2, bay_W / 2).common(inner)
add("battery", battery, (0.2, 0.35, 0.8), "disp", 1.0, "battery")
tw = p["tray_wall"]
tray_outer = box(-bay_L / 2 - tw, bay_L / 2 + tw, y_tray_front, Ri + 1, -bay_W / 2 - tw, bay_W / 2 + tw)
tray = tray_outer.cut(box(-bay_L / 2, bay_L / 2, y_bat0, Ri + 2, -bay_W / 2, bay_W / 2)).common(inner)
# lighten the tray front wall (puncture plate stays solid; side walls get windows would be done in detail design)
add("battery_tray", tray, (0.95, 0.55, 0.15), "shell", 1.0, "structure")
add("battery_swell_envelope", swell_env, (0.4, 0.6, 1.0), "keepout", 0.0, "keepout")

# ============================ MAIN PCB ============================
mz0, mz1 = p["mb_z_bot"], p["mb_z_bot"] + p["mb_t"]
(mx0, mx1), (my0, my1) = p["mb_x"], p["mb_y"]
tx0, tx1, ty1 = p["mb_usb_tab"]
mb = box(mx0, mx1, my0, my1, mz0, mz1).fuse(box(tx0, tx1, my1 - 1, ty1, mz0, mz1))
for hx, hy in p["mb_holes"]:
    mb = mb.cut(cyl(1.6, 10, V(hx, hy, mz0 - 1), V(0, 0, 1)))
mb = mb.removeSplitter()
add("mainboard_pcb", mb, (0.05, 0.45, 0.15), "disp", 1.0, "pcb")

# Height-zone envelope for top-side components (keep-out map given to layout)
xw = p["w_x"]
zones = []   # (name, x0, x1, y0, y1, hmax)
zones.append(("A_under_woofer_baskets_L", -xw - 27, -xw + 27, my0, -6.5, None))
zones.append(("A_under_woofer_baskets_R", xw - 27, xw + 27, my0, -6.5, None))
zones.append(("B_under_woofer_motors_L", -xw - 19.5, -xw + 19.5, -6.5, y_tray_front - 0.5, None))
zones.append(("B_under_woofer_motors_R", xw - 19.5, xw + 19.5, -6.5, y_tray_front - 0.5, None))
zones.append(("C_under_battery_tray", -bay_L / 2 - tw, bay_L / 2 + tw, y_tray_front, my1, None))
mb_comp_env = []


def clear_height(x0, x1, y0, y1):
    """max component height above board top in a rectangle, found by probing obstacles."""
    obst = [parts[n]["shape"] for n in parts if n.startswith(("woofer_", "pr_", "battery_tray"))]
    h = 0.0
    step = 0.5
    while h < 25:
        b = box(x0, x1, y0, y1, mz1, mz1 + h + step)
        if any(b.common(o).Volume > 1e-3 for o in obst) or b.common(inner).Volume < b.Volume - 1e-3:
            break
        h += step
    return max(h - 1.0, 0.0)   # 1 mm air gap


zone_rects = [
    ("A_front_under_woofer_baskets", mx0, mx1, my0, -6.5),
    ("B_mid_under_woofer_motors", -xw - 19.5, xw + 19.5, -6.5, y_tray_front - 0.5),
    ("C_rear_under_battery_tray", -bay_L / 2 - tw, bay_L / 2 + tw, y_tray_front - 0.5, my1),
    ("D_centre_between_woofers", -6.0, 6.0, my0, y_tray_front - 0.5),
    ("E_end_L_under_PR_(x<-77)", mx0, -77.0, my0, my1),
    ("E_end_R_under_PR_(x>77)", 77.0, mx1, my0, my1),
    ("G_L_between_motor_and_PR", -77.0, -53.5, -6.5, 15.1),
    ("G_R_between_motor_and_PR", 53.5, 77.0, -6.5, 15.1),
    ("H_R_rear_end_(battery/UI connectors)", 62.0, 77.0, 15.1, my1),
]
zone_heights = {}
for name, x0, x1, y0, y1 in zone_rects:
    zone_heights[name] = dict(x=[round(x0, 1), round(x1, 1)], y=[round(y0, 1), round(y1, 1)],
                              hmax=round(clear_height(x0, x1, y0, y1), 1))
# also the motor rectangles individually (more height than the whole 'B' strip)
for side, sx in (("L", -1), ("R", 1)):
    x0, x1 = sx * xw - 19.5, sx * xw + 19.5
    zone_heights[f"B_under_motor_{side}"] = dict(x=[round(min(x0, x1), 1), round(max(x0, x1), 1)],
                                                 y=[-6.5, round(y_tray_front - 0.5, 1)],
                                                 hmax=round(clear_height(min(x0, x1), max(x0, x1), -6.5, y_tray_front - 0.5), 1))

# representative component block (for render + displacement): connectors, caps, inductors
comp_blocks = [   # proposed placements of edge connectors / tall parts (X0, X1, Y0, Y1 in enclosure coords)
    ("J601_usb_c", box(-4.5, 4.5, 20.0, 27.5, mz1, mz1 + 3.3)),             # HRO TYPE-C-31-M-12, ~1 mm past tab edge
    ("J801_xt30", box(64.0, 74.5, 3.0, 11.5, mz1, mz1 + 8.5)),              # XT30PW-M right-angle
    ("J802_xh3_bal", box(64.0, 74.0, -6.0, 0.0, mz1, mz1 + 10.0)),          # B3B-XH-A vertical
    ("J803_ph2_ntc", box(76.0, 82.0, 4.0, 10.0, mz1, mz1 + 6.5)),           # B2B-PH-K external NTC
    ("J501_ffc20_ui", box(63.0, 89.0, 19.5, 24.5, mz1, mz1 + 2.5)),         # AFA07-S20FCA, FFC exits +Y (rear)
    ("J301_vh_woofer_L", box(-62.0, -54.0, -6.0, 1.0, mz1, mz1 + 11.5)),    # B2P-VH vertical
    ("J302_vh_tweeter_L", box(-62.0, -54.0, 3.0, 10.0, mz1, mz1 + 11.5)),
    ("J401_vh_woofer_R", box(54.0, 62.0, -6.0, 1.0, mz1, mz1 + 11.5)),
    ("J402_vh_tweeter_R", box(54.0, 62.0, 3.0, 10.0, mz1, mz1 + 11.5)),
    ("bulk_cap_470u", box(-5.0, 5.0, -5.0, 5.0, mz1, mz1 + 10.5)),         # 10x10.5 electrolytic in the tall centre zone
    ("boost_inductor", box(-24.0, -12.0, -2.0, 9.0, mz1, mz1 + 4.2)),      # FXL1040 11.5x10x4
    ("amp_L_LC_filter", box(-42.0, -16.0, -19.0, -9.0, mz1, mz1 + 3.0)),   # 4x FXL0630 7x6.6x3
    ("amp_R_LC_filter", box(16.0, 42.0, -19.0, -9.0, mz1, mz1 + 3.0)),
    ("U101_esp32_wrover", box(-90.0 - 4.0, -90.0 + 27.4, -3.0, 15.0, mz1, mz1 + 3.2)),  # antenna end overhangs -X edge by 4 mm
]
cb = comp_blocks[0][1]
for _, s in comp_blocks[1:]:
    cb = cb.fuse(s)
add("mainboard_components", cb, (0.8, 0.8, 0.75), "disp", 1.0, "pcb")

# ============================ UI BOARD + DISPLAY + ENCODER ============================
uz1 = p["ui_z_top"]
uz0 = uz1 - p["ui_t"]
ui_rects = p["ui_rects"]
ui = None
for x0, x1, y0, y1 in ui_rects:
    b = box(x0, x1, y0, y1, uz0, uz1)
    ui = b if ui is None else ui.fuse(b)
ui = ui.removeSplitter()
add("ui_board_pcb", ui, (0.05, 0.45, 0.15), "disp", 1.0, "pcb")
# display module (Waveshare 1.28" round: Ø37.5 x 40.4 incl. tab), glass top under a 1 mm web + 1.5 mm lens
z_mod_top = R - p["lens_t"] - 1.0
mod = cyl(p["disp_mod_d"] / 2, p["disp_mod_t"], V(p["disp_x"], 0, z_mod_top - p["disp_mod_t"]), V(0, 0, 1))
mod = mod.fuse(box(p["disp_x"] - 8, p["disp_x"] + 8, p["disp_mod_d"] / 2 - 2, p["disp_mod_tab"] - p["disp_mod_d"] / 2,
                   z_mod_top - p["disp_mod_t"], z_mod_top - p["disp_mod_t"] + 1.6))
hdr = box(p["disp_x"] - 10.2, p["disp_x"] + 10.2, 12.0, 14.6, uz1, z_mod_top - p["disp_mod_t"])  # 8-pin 2.54 header
add("display_module", mod.fuse(hdr), (0.1, 0.1, 0.25), "disp", 1.0, "ui")
lens = cyl(p["lens_d"] / 2, p["lens_t"], V(p["disp_x"], 0, R - p["lens_t"]), V(0, 0, 1))
add("display_lens", lens, (0.6, 0.8, 0.95), "disp", 0.0, "ui")
enc = box(p["knob_x"] - 6.2, p["knob_x"] + 6.2, -6.0, 6.0, uz1, uz1 + 6.5)
enc = enc.fuse(cyl(3.5, R - (uz1 + 6.5) + 0.5, V(p["knob_x"], 0, uz1 + 6.5), V(0, 0, 1)))
enc = enc.fuse(cyl(3.0, 15.0, V(p["knob_x"], 0, R), V(0, 0, 1)))
add("encoder_EC11", enc, (0.75, 0.75, 0.75), "disp", 1.0, "ui")
knob = cyl(p["knob_d"] / 2, p["knob_h"], V(p["knob_x"], 0, R + 1.0), V(0, 0, 1))
add("knob", knob, (0.85, 0.3, 0.1), "disp", 0.0, "ui")
btns = None
for bx in p["btn_x"]:
    b = box(bx - 2.55, bx + 2.55, -2.55, 2.55, uz1, uz1 + 1.5).fuse(cyl(2.6, R + 1.0 - (uz1 + 1.5), V(bx, 0, uz1 + 1.5), V(0, 0, 1)))
    btns = b if btns is None else btns.fuse(b)
add("buttons", btns, (0.85, 0.3, 0.1), "disp", 1.0, "ui")

# ============================ SHELL STRUCTURE ============================
shell = outer.cut(inner)
# end caps: spigot ring for gasket + PR recess + PR hole + 5 axial screw bosses
cap_bosses_phi = [0, 90, 150, 210, 270]
# woofer lands: solid baffle from the flange plane to the outer skin, both woofers
land = box(-p["w_x"] - 35, p["w_x"] + 35, -R - 5, w_land_y, -p["w_flange"] / 2 - 2, p["w_flange"] / 2 + 2).common(inner)
shell = shell.fuse(land)
# tweeter pods
for po in pod_outer_all:
    shell = shell.fuse(po.common(outer))
for bo in boss_all:
    shell = shell.fuse(bo.cut(inner).common(box(-X_TUBE + 0.5, X_TUBE - 0.5, -200, 200, -200, 200)))
# UI pads (flat raised bezels on top)
pads = [cyl(p["disp_pad_d"] / 2, 9.0, V(p["disp_x"], 0, R - 9.0), V(0, 0, 1)),
        cyl(p["knob_pad_d"] / 2, 8.0, V(p["knob_x"], 0, R - 8.0), V(0, 0, 1))]
bx0, bx1, bw = p["btn_pad"]
pads.append(box(bx0, bx1, -bw / 2, bw / 2, R - 8.0, R))
for pd in pads:
    shell = shell.fuse(pd.cut(inner))
# ring ribs (rear/top/bottom arcs) at |x| = 64, 3 mm thick, 6 mm deep -- stiffen the rear shell
for sx in (-1, 1):
    ring = cyl(Ri, 3.0, V(sx * 64 - 1.5, 0, 0), V(1, 0, 0)).cut(cyl(Ri - 5.0, 3.0, V(sx * 64 - 1.5, 0, 0), V(1, 0, 0)))
    a0, a1 = math.radians(130), math.radians(230)                    # rear arc only, clear of both PCBs
    wedge_r = Part.Face(Part.makePolygon([V(0, 0, 0)] + [V(0, -80 * math.cos(a0 + (a1 - a0) * k / 8), 80 * math.sin(a0 + (a1 - a0) * k / 8)) for k in range(9)] + [V(0, 0, 0)])).extrude(V(400, 0, 0)).translate(V(-200, 0, 0))
    ring = ring.common(wedge_r)
    shell = shell.fuse(ring.common(inner))
# seam lips (front shell side) + cap screw bosses + mainboard standoffs + UI standoffs
for phi in cap_bosses_phi:
    pt = d(phi) * (Ri - 2.5)
    for sx in (-1, 1):
        bss = cyl(4.0, 12.0, V(sx * (X_TUBE - 12.0) if sx > 0 else -X_TUBE, pt.y, pt.z), V(1, 0, 0))
        shell = shell.fuse(bss.common(inner))
for hx, hy in p["mb_holes"]:
    shell = shell.fuse(cyl(3.5, mz0 - (ZF_IN - 6), V(hx, hy, ZF_IN - 6), V(0, 0, 1)).common(inner).cut(
        cyl(2.0, 20, V(hx, hy, ZF_IN - 6), V(0, 0, 1))))
for hx, hy in [(-80.0, 18.5), (87.0, 6.0), (-16.0, -15.0), (16.0, -15.0), (60.0, -12.0), (-60.0, -12.0)]:
    shell = shell.fuse(cyl(3.0, R - uz1 + 2, V(hx, hy, uz1), V(0, 0, 1)).common(inner).cut(cyl(1.0, 20, V(hx, hy, uz1), V(0, 0, 1))))
# battery tray belongs to the rear shell
# --- holes ---
front_air = []
for side, sx in (("L", -1), ("R", 1)):
    xw_ = sx * p["w_x"]
    shell = shell.cut(cyl(p["w_hole_d"] / 2, 30, V(xw_, w_land_y + 0.01, 0), V(0, -1, 0)))
    front_air.append(cyl(p["w_hole_d"] / 2, 30, V(xw_, w_land_y, 0), V(0, -1, 0)).common(inner)
                     .cut(parts[f"woofer_{side}_flange"]["shape"]))
    ch = Part.makeCone(p["w_hole_d"] / 2, p["w_hole_d"] / 2 + 30, 30, V(xw_, -R + p["w_chamfer"], 0), V(0, -1, 0))
    shell = shell.cut(ch)
for c_ in pod_cut_all:
    shell = shell.cut(c_)
for sx in (-1, 1):
    shell = shell.cut(cyl(p["pr_hole_d"] / 2, 20, V(sx * (X_END + 5), 0, 0), V(-sx, 0, 0)))
    rec_d = p["pr_flange_t"] - p["pr_proud"]
    if rec_d > 0:
        rec = rounded_square_slab(p["pr_flange"] + 0.6, p["pr_flange_r"], rec_d + 1, "x")
        rec = rec.translate(V(pr_mount_x if sx > 0 else -X_END - 1, 0, 0))
        shell = shell.cut(rec)
# display: view hole, lens counterbore, module pocket
shell = shell.cut(cyl(p["disp_view_d"] / 2, 20, V(p["disp_x"], 0, R - 10), V(0, 0, 1)))
shell = shell.cut(cyl(p["lens_d"] / 2 + 0.2, p["lens_t"] + 5, V(p["disp_x"], 0, R - p["lens_t"]), V(0, 0, 1)))
shell = shell.cut(cyl(p["disp_mod_d"] / 2 + 0.3, 20, V(p["disp_x"], 0, z_mod_top - 20), V(0, 0, 1)))
shell = shell.cut(box(p["disp_x"] - 8.5, p["disp_x"] + 8.5, 0, p["disp_mod_tab"] - p["disp_mod_d"] / 2 + 0.5, z_mod_top - 20, z_mod_top))
shell = shell.cut(cyl(3.6, 20, V(p["knob_x"], 0, R - 15), V(0, 0, 1)))          # encoder bushing
for bx in p["btn_x"]:
    shell = shell.cut(cyl(3.0, 20, V(bx, 0, R - 15), V(0, 0, 1)))              # button plungers
shell = shell.cut(cyl(0.5, 20, V(p["mic_x"], 0, R - 10), V(0, 0, 1)))           # mic port Ø1
# USB-C: 1 mm wall at the receptacle, outer pocket for the plug overmold
usb_z = mz1 + 1.6
shell = shell.cut(box(-4.6, 4.6, 26.0, 29.0 + 0.5, usb_z - 1.8, usb_z + 1.8))   # receptacle opening (8.94 x 3.26)
shell = shell.cut(box(-7.0, 7.0, 29.0, 60.0, usb_z - 4.0, usb_z + 4.0))         # overmold pocket 14 x 8
assert shell.isValid(), "shell boolean became invalid"

# --- split into printable parts ---
big = 400
cap_L = shell.common(box(-big, -X_TUBE, -big, big, -big, big))
cap_R = shell.common(box(X_TUBE, big, -big, big, -big, big))
tube = shell.common(box(-X_TUBE, X_TUBE, -big, big, -big, big))
front_shell = tube.common(box(-big, big, -big, p["seam_y"], -big, big))
rear_shell = tube.common(box(-big, big, p["seam_y"], big, -big, big))
add("shell_front", front_shell, (0.82, 0.82, 0.80), "shell", 1.0, "shell")
add("shell_rear", rear_shell, (0.70, 0.72, 0.75), "shell", 1.0, "shell")
add("end_cap_L", cap_L, (0.55, 0.57, 0.6), "shell", 1.0, "shell")
add("end_cap_R", cap_R, (0.55, 0.57, 0.6), "shell", 1.0, "shell")
# grille: 0.8 mm perforated aluminium, rolled, phi -48..+48, |x| <= 72, sits in a 0.8 mm recess
g_out = cyl(R + 0.05, 2 * 96, V(-96, 0, 0), V(1, 0, 0)).cut(cyl(R - 0.75, 2 * 96, V(-96, 0, 0), V(1, 0, 0)))
g0, g1 = math.radians(-45), math.radians(58)
wedge = Part.Face(Part.makePolygon([V(0, 0, 0)] + [V(0, -100 * math.cos(g0 + (g1 - g0) * k / 10), 100 * math.sin(g0 + (g1 - g0) * k / 10)) for k in range(11)] + [V(0, 0, 0)])).extrude(V(300, 0, 0)).translate(V(-150, 0, 0))
grille = g_out.common(wedge)
for bo in boss_all:
    grille = grille.cut(cyl(p["t_wg_boss_r"] + 1.0, 40, bo.BoundBox.Center - t_axis * 20, t_axis))
add("grille_alu", grille, (0.25, 0.25, 0.27), "disp", 0.0, "grille")

# ============================ CHECKS ============================
report = {"params": {k: v for k, v in P.items()}}
report["derived"] = dict(
    R_out=R, R_in=Ri, overall_length_incl_PR_flanges=X_OVERALL, body_length=2 * X_END, tube_inner_x=[-X_TUBE, X_TUBE], woofer_flange_plane_y=round(w_land_y, 2),
    woofer_back_y=round(w_back_y, 2), woofer_cc_mm=2 * p["w_x"], tweeter_cc_mm=2 * p["t_x"],
    tweeters=tweeter_meta, pr_keepout_x=pr_keep, battery_bay=dict(L=bay_L, W=bay_W, T_swell=round(bat_T_sw, 2),
    y=[round(y_bat0, 2), round(y_bat1, 2)], tray_front_y=round(y_tray_front, 2)),
)
# interference: every pair of non-shell solids, and each solid vs shell structure
names = [n for n in parts if parts[n]["group"] not in ("shell", "grille")]
inter = []
struct = parts["shell_front"]["shape"].fuse([parts["shell_rear"]["shape"], parts["end_cap_L"]["shape"], parts["end_cap_R"]["shape"]])
ignore = {("display_lens", "*"), ("knob", "*")}
same_assy = lambda a, b: a.split("_")[0:2] == b.split("_")[0:2]
for i, a in enumerate(names):
    sa = parts[a]["shape"]
    for b in names[i + 1:]:
        if same_assy(a, b) or {a, b} <= {"tweeter_L", "tweeter_pod_L_sealed"} or {a, b} <= {"tweeter_R", "tweeter_pod_R_sealed"}:
            continue
        if {a, b} & {"battery", "battery_swell_envelope", "battery_tray"} == {a, b} or {a, b} == {"battery", "battery_swell_envelope"}:
            continue
        if {a, b} == {"display_module", "ui_board_pcb"} or {a, b} == {"encoder_EC11", "ui_board_pcb"} or {a, b} == {"buttons", "ui_board_pcb"}:
            continue
        if {a, b} == {"mainboard_pcb", "mainboard_components"} or {a, b} == {"encoder_EC11", "knob"}:
            continue
        v = sa.common(parts[b]["shape"]).Volume
        if v > 0.5:
            inter.append((a, b, round(v, 1)))
    if a.startswith(("tweeter_pod", "tweeter_", "pr_", "display_lens", "knob", "encoder", "buttons", "display_module", "battery_tray")):
        continue
    v = sa.common(struct).Volume
    if v > 0.5:
        inter.append((a, "SHELL", round(v, 1)))
report["interference"] = inter

# ============================ NET VOLUME ============================
vol = {}
vol["gross_tube_interior"] = GROSS
shell_in = struct.common(inner).Volume
pods = sum(parts[n]["shape"].Volume for n in parts if n.startswith("tweeter_pod"))
# shell intrusion includes pod walls; pod interiors are sealed -> subtract pod envelopes (minus overlap with shell)
pod_union = parts["tweeter_pod_L_sealed"]["shape"].fuse(parts["tweeter_pod_R_sealed"]["shape"])
pod_extra = pod_union.cut(struct).Volume
vol["shell_lands_ribs_bosses_tray_in_cavity"] = shell_in + parts["battery_tray"]["shape"].cut(struct).Volume
vol["tweeter_pods_sealed"] = pod_extra
vol["woofer_front_openings_(outside_air)"] = sum(fa.Volume for fa in front_air)
for grp_name, prefix in (("woofers", "woofer_"), ("passive_radiators", "pr_"), ("battery", "battery"),
                         ("mainboard", "mainboard_"), ("ui", ("ui_", "display_module", "encoder", "buttons"))):
    s = 0.0
    for n, q in parts.items():
        if q["kind"] != "disp" or not n.startswith(prefix) or n == "battery_tray":
            continue
        s += q["fill"] * q["shape"].common(inner).Volume
    vol[grp_name] = s
vol["wiring_foam_gaskets_allowance"] = 15000.0   # 15 cm3 allowance for cables, cable ties, gasket intrusion
net = vol["gross_tube_interior"] - sum(v for k, v in vol.items() if k != "gross_tube_interior")
report["volume_cm3"] = {k: round(v / 1000, 1) for k, v in vol.items()}
report["volume_cm3"]["NET_box"] = round(net / 1000, 1)
report["mainboard_height_zones_mm_above_top"] = zone_heights
report["mainboard"] = dict(outline_x=list(p["mb_x"]), outline_y=list(p["mb_y"]), usb_tab=list(p["mb_usb_tab"]),
                           z_bottom=mz0, thickness=p["mb_t"], holes=p["mb_holes"],
                           components={n: [round(s.BoundBox.XMin, 1), round(s.BoundBox.XMax, 1), round(s.BoundBox.YMin, 1),
                                           round(s.BoundBox.YMax, 1), round(s.BoundBox.ZMax - mz1, 1)] for n, s in comp_blocks})
report["uiboard"] = dict(rects=ui_rects, z_top=uz1, thickness=p["ui_t"],
                         standoffs=[(-80.0, 18.5), (87.0, 6.0), (-16.0, -15.0), (16.0, -15.0), (60.0, -12.0), (-60.0, -12.0)])
# UI clearances to the tweeter pods / battery
report["ui_clear_to_pods_mm"] = round(min(parts["ui_board_pcb"]["shape"].distToShape(parts[f"tweeter_pod_{s}_sealed"]["shape"])[0] for s in "LR"), 2)
report["ui_clear_to_battery_tray_mm"] = round(parts["ui_board_pcb"]["shape"].distToShape(parts["battery_tray"]["shape"])[0], 2)
report["woofer_motor_to_pr_keepout_mm"] = round(parts["woofer_R_motor"]["shape"].distToShape(parts["pr_R_excursion_keepout"]["shape"])[0], 2)
report["pod_to_pr_basket_mm"] = round(min(parts[f"tweeter_pod_{s}_sealed"]["shape"].distToShape(parts[f"pr_{s}_basket"]["shape"])[0] for s in "LR"), 2)
report["pod_to_woofer_flange_mm"] = round(min(parts[f"tweeter_pod_{s}_sealed"]["shape"].distToShape(parts[f"woofer_{s}_flange"]["shape"])[0] for s in "LR"), 2)
report["woofer_basket_to_pr_keepout_mm"] = round(parts["woofer_R_basket"]["shape"].distToShape(parts["pr_R_excursion_keepout"]["shape"])[0], 2)
report["woofer_frame_gap_mm"] = round(parts["woofer_L_flange"]["shape"].distToShape(parts["woofer_R_flange"]["shape"])[0], 2)
_sw_box = box(-bay_L / 2, bay_L / 2, y_bat0, y_bat1, -bay_W / 2, bay_W / 2)
report["swell_envelope_clipped_by_shell_mm3"] = round(_sw_box.Volume - _sw_box.common(inner).Volume, 1)
_sw_nom = box(-p["bat_L"] / 2, p["bat_L"] / 2, y_bat0, y_bat1, -p["bat_W"] / 2, p["bat_W"] / 2)
report["swell_envelope_nominal_LW_clipped_mm3"] = round(_sw_nom.Volume - _sw_nom.common(inner).Volume, 1)
report["battery_to_shell_mm"] = round(parts["battery"]["shape"].distToShape(struct)[0], 2)
_ob = outer.optimalBoundingBox()
report["bbox_mm"] = [round(X_OVERALL, 1), round(_ob.YLength, 1), round(_ob.ZLength, 1)]
report["print_bboxes_mm"] = {n: [round(v, 1) for v in (parts[n]["shape"].optimalBoundingBox().XLength, parts[n]["shape"].optimalBoundingBox().YLength,
                                 parts[n]["shape"].optimalBoundingBox().ZLength)] for n in ("shell_front", "shell_rear", "end_cap_L")}
report["part_volumes_cm3"] = {n: round(q["shape"].Volume / 1000, 2) for n, q in parts.items()}
report["shell_mass_g_PETG"] = round(sum(parts[n]["shape"].Volume for n in ("shell_front", "shell_rear", "end_cap_L", "end_cap_R")) / 1000 * 1.27, 0)

# ============================ OUTPUTS ============================
doc = App.newDocument("speaker_concept")
for n, q in parts.items():
    o = doc.addObject("Part::Feature", n)
    o.Shape = q["shape"]
doc.recompute()
_fc = os.path.join(HERE, "speaker_concept.FCStd")
if os.path.exists(_fc):
    os.remove(_fc)          # avoid FreeCAD .FCBak clutter
doc.saveAs(_fc)
try:
    import Import
    Import.export([o for o in doc.Objects], os.path.join(HERE, "speaker_concept.step"))
except Exception as e:  # fallback: unnamed compound
    Part.makeCompound([q["shape"] for q in parts.values()]).exportStep(os.path.join(HERE, "speaker_concept.step"))
    report["step_note"] = f"Import.export failed ({e}); wrote plain compound"
import MeshPart
meta = {}
for n, q in parts.items():
    m = MeshPart.meshFromShape(Shape=q["shape"], LinearDeflection=0.25, AngularDeflection=0.3)
    f = os.path.join(BUILD, n + ".stl")
    m.write(f)
    meta[n] = dict(color=q["color"], group=q["group"], kind=q["kind"])
json.dump(meta, open(os.path.join(BUILD, "parts.json"), "w"), indent=1)


# --- PCB outlines (DXF R12 + SVG), board-local coordinates = global X/Y (mm) ---
def outline_polys_main():
    x0, x1 = p["mb_x"]; y0, y1 = p["mb_y"]; ax0, ax1, ay1 = p["mb_usb_tab"]
    return [(x0, y0), (x1, y0), (x1, y1), (ax1, y1), (ax1, ay1), (ax0, ay1), (ax0, y1), (x0, y1)]


def outline_polys_ui():
    sh = ui
    # take the outer wire of the top face
    top = [f for f in sh.Faces if abs(f.Surface.Axis.z) > 0.99 and abs(f.CenterOfMass.z - uz1) < 1e-3][0]
    pts = [(round(v.Point.x, 3), round(v.Point.y, 3)) for v in top.OuterWire.OrderedVertexes]
    return pts


def write_dxf(path, poly, holes, texts):
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
         "0", "SECTION", "2", "ENTITIES"]
    n = len(poly)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        L += ["0", "LINE", "8", "Edge.Cuts", "10", f"{xa:.3f}", "20", f"{ya:.3f}", "11", f"{xb:.3f}", "21", f"{yb:.3f}"]
    for hx, hy, r in holes:
        L += ["0", "CIRCLE", "8", "Edge.Cuts", "10", f"{hx:.3f}", "20", f"{hy:.3f}", "40", f"{r:.3f}"]
    for tx, ty, s in texts:
        L += ["0", "TEXT", "8", "Notes", "10", f"{tx:.3f}", "20", f"{ty:.3f}", "40", "2.0", "1", s]
    L += ["0", "ENDSEC", "0", "EOF"]
    open(path, "w").write("\n".join(L) + "\n")


def write_svg(path, poly, holes, rects, title):
    xs = [q[0] for q in poly]; ys = [q[1] for q in poly]
    pad = 8; sc = 4.0
    W = (max(xs) - min(xs) + 2 * pad) * sc; H = (max(ys) - min(ys) + 2 * pad) * sc
    tx = lambda x: (x - min(xs) + pad) * sc
    ty = lambda y: (max(ys) - y + pad) * sc    # +Y (rear) up in the drawing
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H + 30:.0f}" viewBox="0 0 {W:.0f} {H + 30:.0f}">',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="10" y="{H + 20:.0f}" font-family="monospace" font-size="13">{title}</text>',
         '<polygon points="' + " ".join(f"{tx(x):.1f},{ty(y):.1f}" for x, y in poly) + '" fill="#2e7d32" fill-opacity="0.15" stroke="#1b5e20" stroke-width="2"/>']
    for (x0, x1, y0, y1, lab, col) in rects:
        s.append(f'<rect x="{tx(x0):.1f}" y="{ty(y1):.1f}" width="{(x1 - x0) * sc:.1f}" height="{(y1 - y0) * sc:.1f}" fill="{col}" fill-opacity="0.35" stroke="{col}"/>')
        s.append(f'<text x="{tx(x0) + 2:.1f}" y="{ty(y1) + 12:.1f}" font-family="monospace" font-size="10">{lab}</text>')
    for hx, hy, r in holes:
        s.append(f'<circle cx="{tx(hx):.1f}" cy="{ty(hy):.1f}" r="{r * sc:.1f}" fill="white" stroke="black"/>')
    s.append("</svg>")
    open(path, "w").write("\n".join(s))


mpoly = outline_polys_main()
mholes = [(hx, hy, 1.6) for hx, hy in p["mb_holes"]]
mrects = [(s.BoundBox.XMin, s.BoundBox.XMax, s.BoundBox.YMin, s.BoundBox.YMax, n, "#1565c0") for n, s in comp_blocks]
mrects.append((-90.0, p["mb_antenna_keepout_x"], my0, my1, "ANTENNA KEEP-OUT (all layers)", "#c62828"))
write_dxf(os.path.join(HERE, "mainboard_outline.dxf"), mpoly, mholes,
          [(-88, -24, "MAIN BOARD  X/Y = enclosure coords (mm), -Y = front"), (-88, 27, "USB-C tab at X=0, rear edge")])
write_svg(os.path.join(HERE, "mainboard_outline.svg"), mpoly, mholes, mrects,
          "Main board outline (top view, +Y = rear/up in drawing). Blue = connector/tall-part placements; red = antenna keep-out")
upoly = outline_polys_ui()
uholes = [(hx, hy, 1.6) for hx, hy in report["uiboard"]["standoffs"]]
urects = [(p["disp_x"] - 18.75, p["disp_x"] + 18.75, -18.75, 18.75, "display Ø37.5", "#283593"),
          (p["knob_x"] - 6.2, p["knob_x"] + 6.2, -6, 6, "EC11", "#6d4c41")] + \
         [(bx - 2.55, bx + 2.55, -2.55, 2.55, "SW", "#6d4c41") for bx in p["btn_x"]] + \
         [(p["mic_x"] - 1.75, p["mic_x"] + 1.75, -1.4, 1.4, "MIC", "#c62828")]
write_dxf(os.path.join(HERE, "uiboard_outline.dxf"), upoly, uholes, [(-88, 26, "UI BOARD  X/Y = enclosure coords (mm)")])
write_svg(os.path.join(HERE, "uiboard_outline.svg"), upoly, uholes, urects, "UI board outline (top view, +Y = rear/up in drawing)")
report["uiboard"]["outline"] = upoly
json.dump(report, open(os.path.join(BUILD, "report.json"), "w"), indent=1, default=str)
print("NET VOLUME (L):", round(net / 1e6, 3))
print("INTERFERENCES:", inter)
print(json.dumps(report["volume_cm3"], indent=1))
