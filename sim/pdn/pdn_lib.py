"""Reusable pre-layout PDN impedance library (S7).

A rail is a small linear network: nodes, shunt elements to GND (capacitors, regulator,
load) and series elements between nodes (traces/planes/vias). Z(f) at any node is computed
by nodal analysis (1 A injection). After layout, replace the placeholder series elements with
extracted plane/trace/via R-L values (e.g. from KiCad + a field solver or simple formulas) and
re-run; nothing else changes.

    net = Rail("3V3")
    net.series("REG", "ESP", R=5e-3, L=3e-9)            # trace/plane between two nodes
    net.shunt("REG", mlcc("C957", 22e-6, 25, "1206", vbias=3.3))
    net.shunt("REG", regulator_cpm(fc=35e3, fz=7e3, c_design=34e-6))
    z = net.z(f, "ESP")
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spice"))
from common import mlcc_cap_dc_bias  # noqa: E402

# Typical mounted ESL (body + pads + 2 vias to an inner plane, pre-layout estimates)
ESL_MOUNTED = {"0402": 0.6e-9, "0603": 0.8e-9, "0805": 1.0e-9, "1206": 1.2e-9}
# Typical ESR at self-resonance for X5R/X7R (vendor curves; small effect on |Z| minima)
ESR_TYP = {(1e-7, "0402"): 0.04, (1e-7, "0603"): 0.03, (1e-6, "0603"): 0.015, (4.7e-6, "0603"): 0.008,
           (1e-5, "0603"): 0.006, (1e-5, "0805"): 0.005, (1e-5, "1206"): 0.004, (2.2e-5, "0805"): 0.004,
           (2.2e-5, "1206"): 0.003}


@dataclass
class Element:
    name: str
    zfun: Callable[[np.ndarray], np.ndarray]
    info: dict = field(default_factory=dict)

    def z(self, f):
        return self.zfun(np.asarray(f, dtype=float))


def mlcc(name, c0, v_rated, size, vbias, qty=1, esr=None, esl=None, dielectric="X5R"):
    ceff = mlcc_cap_dc_bias(c0, vbias, v_rated, size, dielectric)
    esr = ESR_TYP.get((c0, size), 0.01) if esr is None else esr
    esl = ESL_MOUNTED[size] if esl is None else esl
    def zf(f):
        w = 2 * np.pi * f
        return (esr + 1j * w * esl + 1 / (1j * w * ceff)) / qty
    return Element(name, zf, dict(kind="MLCC", C0=c0, Ceff=ceff, Vbias=vbias, size=size, ESR=esr, ESL=esl, qty=qty))


def electrolytic(name, c, esr, esl=5e-9, qty=1):
    def zf(f):
        w = 2 * np.pi * f
        return (esr + 1j * w * esl + 1 / (1j * w * c)) / qty
    return Element(name, zf, dict(kind="Al", C=c, ESR=esr, ESL=esl, qty=qty))


def regulator_cpm(name, fc, fz, c_design, r_dc=1e-3):
    """Closed-loop output admittance of a current-mode regulator whose loop is
    T(s) ~ (wc/s)(1 + wz/s) when loaded by its design output capacitance c_design.
    Zcl = Zc/(1+T) reduces to the regulator branch R_reg || L_reg in parallel with C:
      R_reg = 1/(wc C), L_reg = 1/(wc wz C)   (standard 'VRM' R-L model), plus r_dc in series."""
    wc, wz = 2 * np.pi * fc, 2 * np.pi * fz
    rr = 1 / (wc * c_design); lr = 1 / (wc * wz * c_design)
    def zf(f):
        s = 2j * np.pi * f
        return r_dc + 1 / (1 / rr + 1 / (s * lr))
    return Element(name, zf, dict(kind="regulator", fc=fc, fz=fz, R_reg=rr, L_reg=lr, r_dc=r_dc))


def regulator_from_admittance(name, yfun):
    return Element(name, lambda f: 1 / yfun(f), dict(kind="regulator (from S1 loop model)"))


class Rail:
    def __init__(self, name):
        self.name = name
        self.nodes: list[str] = []
        self.shunts: list[tuple[str, Element]] = []
        self.series_el: list[tuple[str, str, Element]] = []

    def _node(self, n):
        if n not in self.nodes:
            self.nodes.append(n)
        return self.nodes.index(n)

    def shunt(self, node, el: Element):
        self._node(node); self.shunts.append((node, el)); return self

    def series(self, a, b, R=0.0, L=0.0, name=None, el: Element | None = None):
        self._node(a); self._node(b)
        if el is None:
            el = Element(name or f"{a}-{b}", lambda f, R=R, L=L: R + 2j * np.pi * f * L, dict(R=R, L=L))
        self.series_el.append((a, b, el)); return self

    def z(self, f, at):
        f = np.asarray(f, dtype=float)
        n = len(self.nodes)
        Y = np.zeros((len(f), n, n), complex)
        for node, el in self.shunts:
            k = self.nodes.index(node); Y[:, k, k] += 1 / el.z(f)
        for a, b, el in self.series_el:
            i, j = self.nodes.index(a), self.nodes.index(b); y = 1 / el.z(f)
            Y[:, i, i] += y; Y[:, j, j] += y; Y[:, i, j] -= y; Y[:, j, i] -= y
        I = np.zeros((len(f), n), complex); I[:, self.nodes.index(at)] = 1.0
        V = np.linalg.solve(Y, I[..., None])[..., 0]
        return V[:, self.nodes.index(at)]

    def bom(self):
        return [dict(node=n, name=e.name, **e.info) for n, e in self.shunts] + \
               [dict(between=f"{a}-{b}", name=e.name, **e.info) for a, b, e in self.series_el]


def target_impedance(dv, di):
    return dv / di


def droop_from_z(f, z, di, t_rise=1e-6):
    """Rough worst-case droop for a current step of di: max |Z| over the band the step excites
    (up to 0.35/t_rise). Used only for the talking point; the figure shows Z(f) vs target."""
    band = f <= 0.35 / t_rise
    return float(np.max(np.abs(z[band])) * di)
