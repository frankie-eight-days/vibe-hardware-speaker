import json, os, FreeCAD as App, Part
H = "/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/mech/concept_fp1"
doc = App.openDocument(os.path.join(H, "speaker_fp1.FCStd"))
meta = json.load(open(os.path.join(H, "build", "parts.json")))
board = []
for o in doc.Objects:
    if o.Name in meta or o.TypeId == "App::DocumentObjectGroup": continue
    if o.Name.startswith("mb_") or (o.TypeId == "App::Part" and not o.InList):
        s = Part.getShape(o)
        if not s.isNull(): board.append((o.Label, s))
bb = None
for _, s in board:
    bb = s.BoundBox if bb is None else bb.united(s.BoundBox)
obst = [o for o in doc.Objects if o.Name in meta and meta[o.Name]["group"] in ("drivers", "structure", "shell", "battery", "keepout")]
hits = {}
for ob in obst:
    for lab, s in board:
        if not s.BoundBox.intersect(ob.Shape.BoundBox): continue
        sub = s.Solids if s.Solids else [s]
        for so in sub:
            if not so.BoundBox.intersect(ob.Shape.BoundBox): continue
            try: v = so.common(ob.Shape).Volume
            except Exception: v = 0
            if v > 0.01: hits.setdefault(ob.Name, []).append(round(v, 2))
print("BBOX", [round(x, 2) for x in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)])
print("TOPLEVEL", [l for l, _ in board if not l.startswith(("J", "U", "SW"))][:5], len(board))
print("HITS", {k: (len(v), round(sum(v), 2)) for k, v in hits.items()})
