"""Smoke test numpy/scipy/matplotlib/gmsh: sealed-box 2nd-order HP response + gmsh OCC capsule surface mesh."""
import numpy as np, scipy.signal as ss, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, gmsh, os
fc, Q = 65.0, 0.707
w0 = 2 * np.pi * fc
b, a = [1, 0, 0], [1, w0 / Q, w0**2]
f = np.logspace(1, 4, 400)
_, h = ss.freqs(b, a, 2 * np.pi * f)
f3 = f[np.argmin(np.abs(20 * np.log10(abs(h)) + 3))]
print(f"scipy: Butterworth HP F3 = {f3:.1f} Hz (expect 65)")
# biquad via scipy for DSP sanity: 48k peaking EQ bilinear
bz, az = ss.bilinear(b, a, 48000)
print("scipy bilinear biquad:", np.round(bz, 6), np.round(az, 6))
out = os.path.join(os.path.dirname(__file__), "smoke_response.png")
plt.semilogx(f, 20 * np.log10(abs(h))); plt.grid(True, which="both"); plt.savefig(out, dpi=80)
print("matplotlib wrote", out)
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("capsule")
L, R = 0.21, 0.045
c = gmsh.model.occ.addCylinder(-L / 2 + R, 0, 0, L - 2 * R, 0, 0, R)
s1 = gmsh.model.occ.addSphere(-L / 2 + R, 0, 0, R); s2 = gmsh.model.occ.addSphere(L / 2 - R, 0, 0, R)
gmsh.model.occ.fuse([(3, c)], [(3, s1), (3, s2)]); gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMax", 343 / 4000 / 6)  # 6 elems/wavelength @ 4 kHz
gmsh.model.mesh.generate(2)
tags, _, _ = gmsh.model.mesh.getElements(2)
n = sum(len(t) for t in gmsh.model.mesh.getElements(2)[1])
print(f"gmsh {gmsh.__version__}: capsule surface triangles = {n}")
gmsh.finalize()
print("PASS")
