# Run with: /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd sim/smoke/freecad_make_capsule.py
import os, FreeCAD as App, Part
L, R = 210.0, 45.0  # mm
cyl = Part.makeCylinder(R, L - 2 * R, App.Vector(-(L / 2 - R), 0, 0), App.Vector(1, 0, 0))
s1 = Part.makeSphere(R, App.Vector(-(L / 2 - R), 0, 0)); s2 = Part.makeSphere(R, App.Vector(L / 2 - R, 0, 0))
shape = cyl.fuse([s1, s2]).removeSplitter()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd(), "out", "capsule.step")
out = os.environ.get("CAPSULE_STEP", out)
shape.exportStep(out)
print("FreeCAD", App.Version()[:3], "wrote", out, "volume L =", round(shape.Volume / 1e6, 3))
