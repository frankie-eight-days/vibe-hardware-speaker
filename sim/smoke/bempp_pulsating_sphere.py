"""Smoke test: bempp-cl exterior Helmholtz (pulsating sphere) vs analytic monopole.
Sphere radius a, normal velocity derivative du/dn = g = 1 on surface.
Analytic: u(r) = A exp(ikr)/r, A = g a^2 exp(-ika)/(ika - 1).
Direct BIE (exterior, outward normal): (1/2 I - K) u = -V g on Gamma, then
u(x) = D[u](x) - S[g](x).
"""
import time
import numpy as np
import bempp_cl.api as bempp

a, k = 0.05, 2 * np.pi * 1000 / 343.0   # 5 cm sphere, 1 kHz
t0 = time.time()
grid = bempp.shapes.sphere(r=a, h=a / 8)
space = bempp.function_space(grid, "P", 1)
I = bempp.operators.boundary.sparse.identity(space, space, space)
K = bempp.operators.boundary.helmholtz.double_layer(space, space, space, k)
V = bempp.operators.boundary.helmholtz.single_layer(space, space, space, k)
g = bempp.GridFunction(space, coefficients=np.ones(space.global_dof_count, dtype=complex))
rhs = -(V * g)
u, info = bempp.linalg.gmres(0.5 * I - K, rhs, tol=1e-6)

pts = np.array([[0.2, 0, 0], [0, 0.5, 0], [0, 0, 1.0]]).T
Dp = bempp.operators.potential.helmholtz.double_layer(space, pts, k)
Sp = bempp.operators.potential.helmholtz.single_layer(space, pts, k)
u_num = (Dp * u - Sp * g).ravel()
r = np.linalg.norm(pts, axis=0)
A = a**2 * np.exp(-1j * k * a) / (1j * k * a - 1)
u_ex = A * np.exp(1j * k * r) / r
err = np.abs(u_num - u_ex) / np.abs(u_ex)
print(f"elements={grid.number_of_elements} dofs={space.global_dof_count} gmres_info={info}")
for ri, n, e, er in zip(r, u_num, u_ex, err):
    print(f"r={ri:.2f} num={n:.4e} exact={e:.4e} relerr={er:.2e}")
print(f"elapsed {time.time() - t0:.1f}s; device={bempp.DEFAULT_DEVICE_INTERFACE}")
assert err.max() < 2e-2, "bempp smoke test FAILED"
print("PASS")
