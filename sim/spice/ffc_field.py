"""2-D electrostatic finite-difference solver for flat-cable / PCB cross-sections.

Solves div(eps grad phi) = 0 on a rectilinear (non-uniform) grid with zero-thickness strip
conductors (Dirichlet nodes) and a grounded outer box. Returns the Maxwell capacitance matrix
per unit length with and without dielectric; L = mu0 eps0 inv(C_air) (TEM / quasi-TEM).

Used by S6 for the 1.0 mm pitch FFC. Reusable: pass any list of strips and dielectric boxes.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

EPS0 = 8.8541878128e-12
MU0 = 4e-7 * np.pi
C0 = 299792458.0


def graded(fine_lo, fine_hi, h_fine, outer_lo, outer_hi, growth=1.12, h_max=0.5e-3):
    """Uniform fine grid in [fine_lo, fine_hi], geometric growth outwards to the box."""
    core = np.arange(fine_lo, fine_hi + h_fine / 2, h_fine)
    up, h, x = [], h_fine, fine_hi
    while x < outer_hi:
        h = min(h * growth, h_max); x = x + h; up.append(min(x, outer_hi))
    dn, h, x = [], h_fine, fine_lo
    while x > outer_lo:
        h = min(h * growth, h_max); x = x - h; dn.append(max(x, outer_lo))
    return np.unique(np.concatenate([dn[::-1], core, up]))


class Section:
    def __init__(self, x, y, strips, dielectrics, y_strip=0.0, box="neumann"):
        """x, y: node coordinates (m). strips: list of (x0, x1) at y = y_strip (zero thickness).
        dielectrics: list of (x0, x1, y0, y1, eps_r) boxes."""
        self.x, self.y = np.asarray(x), np.asarray(y)
        self.strips = strips
        self.diel = dielectrics
        self.box = box   # "neumann": far boundary carries no charge (all return on the strips)
        nx, ny = len(self.x), len(self.y)
        self.nx, self.ny = nx, ny
        jy = int(np.argmin(abs(self.y - y_strip)))
        self.jy = jy
        self.cond_nodes = []
        for st in strips:   # (x0, x1) at y_strip, or (x0, x1, y) for a strip/plane at another height
            a, b = st[0], st[1]
            jj = jy if len(st) == 2 else int(np.argmin(abs(self.y - st[2])))
            ii = np.where((self.x >= a - 1e-12) & (self.x <= b + 1e-12))[0]
            self.cond_nodes.append(ii * ny + jj)

    def _eps_cells(self, with_diel):
        xc = 0.5 * (self.x[1:] + self.x[:-1]); yc = 0.5 * (self.y[1:] + self.y[:-1])
        E = np.ones((len(xc), len(yc)))
        if with_diel:
            for (x0, x1, y0, y1, er) in self.diel:
                E[np.ix_((xc > x0) & (xc < x1), (yc > y0) & (yc < y1))] = er
        return E

    def _matrix(self, with_diel):
        x, y, nx, ny = self.x, self.y, self.nx, self.ny
        E = self._eps_cells(with_diel)
        hx = np.diff(x); hy = np.diff(y)
        idx = lambda i, j: i * ny + j
        rows, cols, vals = [], [], []
        # x-edges between (i,j) and (i+1,j): face length = half cells above/below
        for i in range(nx - 1):
            j = np.arange(ny)
            e_lo = np.where(j > 0, E[i, np.maximum(j - 1, 0)] * np.where(j > 0, hy[np.maximum(j - 1, 0)], 0), 0)
            e_hi = np.where(j < ny - 1, E[i, np.minimum(j, ny - 2)] * np.where(j < ny - 1, hy[np.minimum(j, ny - 2)], 0), 0)
            g = 0.5 * (e_lo + e_hi) / hx[i]
            a, b = idx(i, j), idx(i + 1, j)
            rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [g, g, -g, -g]
        for j in range(ny - 1):
            i = np.arange(nx)
            e_l = np.where(i > 0, E[np.maximum(i - 1, 0), j] * np.where(i > 0, hx[np.maximum(i - 1, 0)], 0), 0)
            e_r = np.where(i < nx - 1, E[np.minimum(i, nx - 2), j] * np.where(i < nx - 1, hx[np.minimum(i, nx - 2)], 0), 0)
            g = 0.5 * (e_l + e_r) / hy[j]
            a, b = idx(i, j), idx(i, j + 1)
            rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [g, g, -g, -g]
        rows = np.concatenate([np.atleast_1d(r) for r in rows])
        cols = np.concatenate([np.atleast_1d(c) for c in cols])
        vals = np.concatenate([np.atleast_1d(v) for v in vals])
        return sp.csr_matrix((vals * EPS0, (rows, cols)), shape=(nx * ny, nx * ny))

    def cap_matrix(self, active, with_diel=True):
        """Maxwell C (F/m) for the conductors listed in `active` (indices into strips).
        All other strips (and the outer box if box="dirichlet") are held at 0 V."""
        A = self._matrix(with_diel)
        N = self.nx * self.ny
        fixed = np.zeros(N, bool)
        for nodes in self.cond_nodes:
            fixed[nodes] = True
        bx = np.zeros((self.nx, self.ny), bool)
        bx[0, :] = bx[-1, :] = bx[:, 0] = bx[:, -1] = True
        if self.box == "dirichlet":
            fixed |= bx.ravel()
        free = ~fixed
        Aff = A[free][:, free].tocsc()
        Afx = A[free][:, fixed]
        lu = spla.splu(Aff)
        fixed_idx = np.where(fixed)[0]
        pos = {n: k for k, n in enumerate(fixed_idx)}
        C = np.zeros((len(active), len(active)))
        for a, ci in enumerate(active):
            vfix = np.zeros(len(fixed_idx))
            for n in self.cond_nodes[ci]:
                vfix[pos[n]] = 1.0
            phi = np.zeros(N)
            phi[fixed] = vfix
            phi[free] = lu.solve(-Afx @ vfix)
            q = A @ phi                     # net charge (per unit length) on each node
            for b, cj in enumerate(active):
                C[b, a] = q[self.cond_nodes[cj]].sum()
        return 0.5 * (C + C.T)

    def lc(self, active):
        C = self.cap_matrix(active, True)
        Ca = self.cap_matrix(active, False)
        L = MU0 * EPS0 * np.linalg.inv(Ca)
        return L, C, Ca


def cpw_finite_ground_z0(w, s, wg, eps_eff=1.0):
    """Analytic Z0 of a coplanar G-S-G line (no backing plane, zero thickness, finite ground
    width wg) by conformal mapping (Ghione & Naldi): k = (a/b) sqrt((1-b^2/c^2)/(1-a^2/c^2))."""
    from scipy.special import ellipk
    a, b, c = w / 2, w / 2 + s, w / 2 + s + wg
    k = (a / b) * np.sqrt((1 - b ** 2 / c ** 2) / (1 - a ** 2 / c ** 2))
    kp = np.sqrt(1 - k ** 2)
    return 30 * np.pi / np.sqrt(eps_eff) * ellipk(kp ** 2) / ellipk(k ** 2)
