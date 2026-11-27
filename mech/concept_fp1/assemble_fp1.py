# Floor-plan v1 mock-up: concept enclosure (variant run with the fp1 outline) + the real KiCad board STEP.
# Run in the FreeCAD GUI (colors need it):
#   /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/concept_fp1/assemble_fp1.py
# Inputs (this folder): speaker_concept.FCStd (SPEAKER_PARAMS=params_fp1.json run of ../concept/speaker_concept.py),
#   mainboard_fp1.step (kicad-cli pcb export step --user-origin 150x100mm, enclosure X/Y),
#   missing_boxes.json (courtyard x height for the 14 parts that have no KiCad 3D model).
# Writes speaker_fp1.FCStd and interference_fp1.json.
import os, json
import FreeCAD as App
import FreeCADGui as Gui
import Part
import ImportGui

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
if not os.path.exists(os.path.join(HERE, "params_fp1.json")):
    HERE = "/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/mech/concept_fp1"
V = App.Vector
MZ0, MT = -35.0, 1.6

doc = App.openDocument(os.path.join(HERE, "speaker_concept.FCStd"))
meta = json.load(open(os.path.join(HERE, "build", "parts.json")))
for n in ("mainboard_pcb", "mainboard_components"):
    if doc.getObject(n):
        doc.removeObject(n)

# concept parts: colors, transparency, visibility
for o in list(doc.Objects):
    m = meta.get(o.Name)
    if not m:
        continue
    vo = o.ViewObject
    vo.ShapeColor = tuple(m["color"])
    if m["kind"] == "keepout" or o.Name in ("grille_alu", "tweeter_pod_L_sealed", "tweeter_pod_R_sealed"):
        vo.Visibility = False
    elif o.Name == "shell_front":
        vo.Transparency = 85
    elif m["kind"] == "shell":
        vo.Transparency = 55

# real board
before = set(o.Name for o in doc.Objects)
ImportGui.insert(os.path.join(HERE, "mainboard_fp1.step"), doc.Name)
new = [o for o in doc.Objects if o.Name not in before]
top = [o for o in new if not any(p in new for p in o.InList)]
for o in top:
    o.Placement = App.Placement(V(0, 0, MZ0), App.Rotation()).multiply(o.Placement)
doc.recompute()

# placeholder blocks for parts with no 3D model (top side sits on z = MZ0 + MT, bottom hangs below MZ0)
cols = {"J": (0.92, 0.92, 0.88), "U": (0.12, 0.12, 0.12), "SW": (0.75, 0.75, 0.75)}
grp = doc.addObject("App::DocumentObjectGroup", "board_parts_no_3D_model")
for r, b in json.load(open(os.path.join(HERE, "missing_boxes.json"))).items():
    (x0, x1), (y0, y1), h = b["x"], b["y"], max(b["h"], 0.5)
    z0 = MZ0 + MT if b["side"] == "F" else MZ0 - h
    o = doc.addObject("Part::Feature", "mb_" + r)
    o.Shape = Part.makeBox(x1 - x0, y1 - y0, h, V(x0, y0, z0))
    o.Label = f"{r} {b['value']} (courtyard x {h} mm)"
    o.ViewObject.ShapeColor = cols["SW" if r.startswith("SW") else r[0]]
    grp.addObject(o)
doc.recompute()

# interference: board + parts vs drivers / battery tray / shells
board_shapes = [o.Shape for o in new if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Volume > 1e-6]
board_shapes += [o.Shape for o in grp.Group]
bb_all = None
for s in board_shapes:
    bb_all = s.BoundBox if bb_all is None else bb_all.united(s.BoundBox)
obst = [o for o in doc.Objects if o.Name in meta and meta[o.Name]["group"] in ("drivers", "structure", "shell", "battery", "keepout")]
hits = {}
for ob in obst:
    vol = 0.0
    for s in board_shapes:
        if s.BoundBox.intersect(ob.Shape.BoundBox):
            try:
                vol += s.common(ob.Shape).Volume
            except Exception:
                pass
    if vol > 0.01:
        hits[ob.Name] = round(vol, 2)
rep = dict(board_bbox=[round(v, 2) for v in (bb_all.XMin, bb_all.XMax, bb_all.YMin, bb_all.YMax, bb_all.ZMin, bb_all.ZMax)],
           interference_mm3=hits, imported_objects=len(new), placeholder_parts=len(grp.Group))
json.dump(rep, open(os.path.join(HERE, "interference_fp1.json"), "w"), indent=1)
App.Console.PrintMessage(f"fp1 mock-up: {rep}\n")

out = os.path.join(HERE, "speaker_fp1.FCStd")
if os.path.exists(out):
    os.remove(out)
doc.saveAs(out)
Gui.activeDocument().activeView().viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
