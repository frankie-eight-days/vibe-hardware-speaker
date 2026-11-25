"""FreeCAD STEP -> gmsh surface mesh -> bempp grid. Usage: python step_to_bempp.py capsule.step [f_max_Hz]"""
import sys, gmsh, bempp_cl.api as bempp
step = sys.argv[1]; fmax = float(sys.argv[2]) if len(sys.argv) > 2 else 4000.0
h = 343.0 / fmax / 6 * 1000  # mm, 6 elements per wavelength (STEP units are mm)
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.occ.importShapes(step); gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMax", h)
gmsh.option.setNumber("Mesh.MeshSizeFactor", 1.0)
gmsh.model.mesh.generate(2)
msh = step.rsplit(".", 1)[0] + ".msh"
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.write(msh); gmsh.finalize()
grid = bempp.import_grid(msh)
print(f"gmsh -> {msh}; bempp grid: {grid.number_of_elements} triangles, {grid.number_of_vertices} vertices")
