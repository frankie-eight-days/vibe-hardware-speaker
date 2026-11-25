"""Thin bempp-cl wrapper for exterior radiation problems (rigid body with vibrating pistons).

Physics (time convention of bempp: e^{-i w t}, outgoing waves e^{ikr}):
  Helmholtz equation outside the closed surface Gamma, rigid everywhere except on pistons where the
  outward normal velocity is v_n (1 m/s per piston for the unit solutions).  Neumann data
      g = dp/dn = i w rho v_n                           (linearised Euler equation)
  Direct boundary-integral formulation (exterior, normals pointing into the air):
      (1/2 I - K) p = -V g    on Gamma
      p(x) = D[p](x) - S[g](x)   for x in the air
  (the same convention as sim/smoke/bempp_pulsating_sphere.py, which passed at 0.22 % error).

The direct formulation is not unique at the interior Dirichlet eigenfrequencies of the body (for the
capsule the first is ~2.9 kHz).  Two remedies are implemented:
  * CHIEF (Schenck 1968): add the interior-point conditions D[p](x_i) - S[g](x_i) = 0 at M random points
    inside the body and solve the over-determined system by least squares (cheap: no hypersingular).
  * Burton-Miller: (1/2 I - K + eta W) p = -(V + eta (1/2 I + K')) g with eta = i/k (robust, ~5x the
    assembly cost because of the hypersingular operator W).  Used as a cross-check.

P1 (continuous piecewise-linear) for the surface pressure; DP0 (piecewise-constant) on the piston
segments only for the Neumann data, so a piston's velocity drops sharply to zero at its rim.
All complex outputs are converted to the engineering convention e^{+j w t} (complex conjugate) at the
end, so they can be multiplied with the lumped-element transfer functions of A1/A5.
"""
import time

import numpy as np
import scipy.linalg as sla

import bempp_cl.api as bempp
from bempp_cl.api.grid.grid import Grid

from common import RHO, C0


def make_grid(xyz_m, tris, dom):
    return Grid(np.ascontiguousarray(xyz_m.T), np.ascontiguousarray(tris.T.astype("uint32")),
                domain_indices=np.asarray(dom, dtype="uint32"))


class Radiator:
    """Surface-pressure solver for unit normal velocity on each tagged piston."""

    def __init__(self, grid, piston_tags, interior_pts=None, sd_true=None):
        self.grid = grid
        self.p1 = bempp.function_space(grid, "P", 1)
        self.tags = dict(piston_tags)                          # name -> domain index
        self.dp0 = {n: bempp.function_space(grid, "DP", 0, segments=[t]) for n, t in self.tags.items()}
        self.interior = interior_pts                           # (3, M) in m, or None
        # piston area on the mesh (polygonal rim loses ~1-2 %); velocity is scaled so Q = v * Sd_true
        self.scale = {}
        for n, sp in self.dp0.items():
            a_mesh = float(np.sum(sp.grid.volumes[sp.support]))
            self.scale[n] = (sd_true[n] / a_mesh) if sd_true else 1.0
        self.ndof = self.p1.global_dof_count

    def solve(self, f, method="chief"):
        """Return dict name -> (p_surface coefficients [P1], g coefficients [DP0]) for 1 m/s on that piston."""
        k = 2 * np.pi * f / C0
        t0 = time.time()
        bnd = bempp.operators.boundary
        Isp = bnd.sparse.identity(self.p1, self.p1, self.p1).weak_form().A.tocoo()
        A = bnd.helmholtz.double_layer(self.p1, self.p1, self.p1, k).weak_form().A   # K, modified in place
        A *= -1.0
        np.add.at(A, (Isp.row, Isp.col), 0.5 * Isp.data)                             # A = 1/2 M - K
        rhs, gco = [], {}
        eta = 1j / k
        if method == "bm":
            W = bnd.helmholtz.hypersingular(self.p1, self.p1, self.p1, k).weak_form().A
            W *= eta
            A += W
            del W
        for n, sp in self.dp0.items():
            g = np.full(sp.global_dof_count, 1j * 2 * np.pi * f * RHO * self.scale[n], dtype=complex)
            gco[n] = g
            Vg = bnd.helmholtz.single_layer(sp, self.p1, self.p1, k).weak_form().A @ g
            b = -Vg
            if method == "bm":
                Kp = bnd.helmholtz.adjoint_double_layer(sp, self.p1, self.p1, k).weak_form().A @ g
                Mg = bnd.sparse.identity(sp, self.p1, self.p1).weak_form().A @ g
                b = b - eta * (0.5 * Mg + Kp)
            rhs.append(b)
        B = np.column_stack(rhs)
        use_chief = method == "chief" and self.interior is not None
        if use_chief:
            Dm, Cr = chief_rows(self.grid, self.p1, self.dp0, gco, self.interior, k)
            s = np.linalg.norm(A, axis=1).mean() / np.linalg.norm(Dm, axis=1).mean()
        lu = sla.lu_factor(A, overwrite_a=True, check_finite=False)                   # in place: low memory
        del A
        if use_chief:
            # Exact least-squares solution of [A; sC] x = [B; sD] without forming A^H A:
            # with y = A x and E = C A^-1, minimise |y - B|^2 + s^2 |E y - D|^2 (Woodbury, M << N rows).
            E = sla.lu_solve(lu, Dm.conj().T, trans=2, check_finite=False).conj().T  # (M, N)
            s2 = s ** 2
            r = B + s2 * (E.conj().T @ Cr)
            Msm = np.eye(E.shape[0]) + s2 * (E @ E.conj().T)
            Y = r - s2 * (E.conj().T @ np.linalg.solve(Msm, E @ r))
            X = sla.lu_solve(lu, Y, check_finite=False)
        else:
            X = sla.lu_solve(lu, B, check_finite=False)
        self.last_time = time.time() - t0
        return {n: (X[:, i], gco[n]) for i, n in enumerate(self.dp0)}, k

    # ------------------------------------------------------------------ field evaluation
    def field(self, sol, k, pts, far=False):
        """Pressure at points (3, N) [m] (or far-field pattern for unit directions if far=True).

        Returned in the e^{+jwt} convention (complex conjugate of bempp's), Pa per (m/s) of piston velocity.
        far=True returns F(d) with p ~ F(d) e^{-jkr}/r (so |F| in Pa*m per m/s).
        """
        mod = bempp.operators.far_field.helmholtz if far else bempp.operators.potential.helmholtz
        D = mod.double_layer(self.p1, pts, k)
        out = {}
        for n, (pc, gc) in sol.items():
            S = mod.single_layer(self.dp0[n], pts, k)
            u = bempp.GridFunction(self.p1, coefficients=pc)
            g = bempp.GridFunction(self.dp0[n], coefficients=gc)
            val = (D.evaluate(u) - S.evaluate(g)).ravel()
            out[n] = np.conj(val)
        return out


# 6-point, degree-4 Dunavant rule on the reference triangle (barycentric coordinates, weights sum to 1)
_QA, _QB = 0.445948490915965, 0.091576213509771
_QW1, _QW2 = 0.223381589678011, 0.109951743655322
_QBARY = np.array([[_QA, _QA, 1 - 2 * _QA], [_QA, 1 - 2 * _QA, _QA], [1 - 2 * _QA, _QA, _QA],
                   [_QB, _QB, 1 - 2 * _QB], [_QB, 1 - 2 * _QB, _QB], [1 - 2 * _QB, _QB, _QB]])
_QW = np.array([_QW1] * 3 + [_QW2] * 3)


def chief_rows(grid, p1, dp0, gco, pts, k):
    """CHIEF interior-point rows.  For x_i strictly inside the body (>= ~1 cm from the surface, so the
    kernel is smooth and a 6-point rule per triangle is accurate):
        Dm[i, :] u  = D[u](x_i)  (P1 basis),      Cr[i, n] = S[g_n](x_i)  (DP0 piston data)
    and CHIEF requires D[u](x_i) - S[g](x_i) = 0."""
    V = grid.vertices.T                                    # (Nv, 3)
    E = grid.elements.T                                    # (Ne, 3)
    v0, v1, v2 = V[E[:, 0]], V[E[:, 1]], V[E[:, 2]]
    cr = np.cross(v1 - v0, v2 - v0)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    nrm = cr / (2 * area[:, None])                         # same orientation bempp uses
    Q = (_QBARY[None, :, 0, None] * v0[:, None] + _QBARY[None, :, 1, None] * v1[:, None]
         + _QBARY[None, :, 2, None] * v2[:, None])        # (Ne, 6, 3)
    W = area[:, None] * _QW[None, :]                       # (Ne, 6)
    l2g = p1.local2global                                  # (Ne, 3) P1 dof per local vertex
    mult = p1.local_multipliers
    M = pts.shape[1]
    Dm = np.zeros((M, p1.global_dof_count), complex)
    for i in range(M):
        x = pts[:, i]
        d = Q - x                                          # y - x
        r = np.linalg.norm(d, axis=2)
        G = np.exp(1j * k * r) / (4 * np.pi * r)
        dG = G * (1j * k - 1 / r) * np.einsum("eqc,ec->eq", d, nrm) / r
        wq = dG * W                                        # (Ne, 6)
        for loc in range(3):
            # P1 local basis = barycentric coordinate of vertex 'loc' (bempp local vertex order)
            contrib = np.sum(wq * _QBARY[None, :, loc], axis=1) * mult[:, loc]
            np.add.at(Dm[i], l2g[:, loc], contrib)
    Cr = np.zeros((M, len(dp0)), complex)
    for j, (n, sp) in enumerate(dp0.items()):
        els = np.where(sp.support)[0]
        dofs = sp.local2global[els, 0]
        for i in range(M):
            d = Q[els] - pts[:, i]
            r = np.linalg.norm(d, axis=2)
            G = np.exp(1j * k * r) / (4 * np.pi * r)
            Cr[i, j] = np.sum(np.sum(G * W[els], axis=1) * gco[n][dofs])
    return Dm, Cr


def interior_points(m, rng_seed, inside_fn, bbox):
    """M random points satisfying inside_fn (vectorised), sampled in the bbox (6-tuple, metres)."""
    rng = np.random.default_rng(rng_seed)
    pts = []
    while len(pts) < m:
        q = rng.uniform(bbox[:3], bbox[3:], size=(4 * m, 3))
        q = q[inside_fn(q)]
        pts.extend(q.tolist())
    return np.array(pts[:m]).T


def directions(axis, side_vec, angles_deg):
    """Unit vectors in the plane (axis, side_vec): cos(t) axis + sin(t) side_vec."""
    a = np.radians(angles_deg)
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    side_vec = np.asarray(side_vec, float) / np.linalg.norm(side_vec)
    return (np.outer(np.cos(a), axis) + np.outer(np.sin(a), side_vec)).T
