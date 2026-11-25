"""Loader for the BEM sweeps written by bem_capsule_run.py (results/bem_<case>.npz)."""
import os
import sys

import numpy as np

import common

QUICK = "--quick" in sys.argv or os.environ.get("BEM_QUICK") == "1"


class BEM:
    def __init__(self, case):
        tag = case + ("_quick" if QUICK else "")
        z = np.load(os.path.join(os.environ.get("BEM_DIR", common.RESULTS), f"bem_{tag}.npz"))
        self.case = case
        self.f = z["freqs"]
        self.pistons = [str(p) for p in z["pistons"]]
        self.F = {k[2:]: z[k] for k in z.files if k.startswith("F_")}
        self.BM = {k[3:]: z[k] for k in z.files if k.startswith("BM_")}
        self.dirs = {k[4:]: z[k] for k in z.files if k.startswith("dir_")}
        self.pts = {k[3:]: z[k] for k in z.files if k.startswith("pt_")}
        self.meta = {k[5:]: z[k] for k in z.files if k.startswith("meta_")}
        self.ang = self.meta["angles_deg"]

    def get(self, key, piston, bm=False):
        """Complex array (n_freq, n_points), Pa per (m/s) [far-field keys: Pa*m per m/s]."""
        src = self.BM if bm else self.F
        return src[key][:, self.pistons.index(piston), :]

    def listener(self, piston, desk=True):
        """Pressure at the 15 listener positions (free field + desk image if desk=True)."""
        p = self.get("listener", piston)
        if desk:
            p = p + self.get("listener_image", piston)
        return p

    def centre_seat(self):
        xs, hs = self.meta["listener_x"], self.meta["listener_h"]
        grid = [(h, x) for h in hs for x in xs]
        return grid.index((0.40, 0.0))


def norm_polar(P, ang):
    """dB relative to the 0-degree direction at each frequency."""
    i0 = int(np.argmin(np.abs(ang)))
    return 20 * np.log10(np.abs(P) / np.abs(P[:, i0:i0 + 1]) + 1e-12)


def beamwidth(Pdb, ang, level=-6.0):
    """Full angle between the first crossings of `level` dB either side of 0 deg (per frequency)."""
    i0 = int(np.argmin(np.abs(ang)))
    out = []
    for row in np.nan_to_num(Pdb, nan=-300.0):
        r = np.where(row[i0:] < level)[0]
        l = np.where(row[:i0 + 1][::-1] < level)[0]
        a_r = ang[i0 + r[0]] if len(r) else 180.0
        a_l = -ang[i0 - l[0]] if len(l) else 180.0
        out.append(a_r + a_l)
    return np.array(out)


def frac_oct_smooth(f, mag_db, frac=6):
    """Power-average smoothing over 1/frac octave (on the log grid)."""
    p = 10 ** (mag_db / 10)
    out = np.empty_like(p)
    lf = np.log2(f)
    for i, x in enumerate(lf):
        m = np.abs(lf - x) <= 0.5 / frac
        out[i] = p[m].mean()
    return 10 * np.log10(out)
