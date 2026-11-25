"""Small-signal driver models shared by A2/A3/A5 (engineering convention e^{+jwt}).

* Woofer (ND65-8, 2 in one box with 2 PRs): cone and PR velocity per volt from A1
  (results/a1_bass_transfer.csv, final alignment 0.82 L, 3.5 g per PR, plain Le = 0.61 mH).
* Tweeter (OT19NC00-04): closed-back dome, own rear chamber, so the sealed printed pod does not load it.
  Datasheet (Vifa/Tymphany rev 1.0): Re 3.17 ohm, Le 0.01 mH, Bl 1.64 Tm, Mms 0.20 g, Fs 1029 Hz,
  Qms 7.03, Sd 4.5 cm^2 -> Qes recomputes to 1.52 (datasheet 1.56), so the set is consistent.
* Analytic rigid circular piston in an infinite baffle (reference case for A2/A3).
"""
import os

import numpy as np
from scipy.special import j1

import common

TW = dict(re=3.17, le=10e-6, bl=1.64, mms=0.20e-3, fs=1029.44, qms=7.03, sd=4.5e-4)


def tweeter_velocity(f, ts=TW):
    """Dome velocity (m/s) per volt."""
    w = 2 * np.pi * np.asarray(f, float)
    s = 1j * w
    cms = 1 / ((2 * np.pi * ts["fs"]) ** 2 * ts["mms"])
    rms = 2 * np.pi * ts["fs"] * ts["mms"] / ts["qms"]
    ze = ts["re"] + s * ts["le"]
    zm = rms + s * ts["mms"] + 1 / (s * cms)
    return ts["bl"] / (ze * zm + ts["bl"] ** 2)


def tweeter_zin(f, ts=TW):
    w = 2 * np.pi * np.asarray(f, float)
    s = 1j * w
    cms = 1 / ((2 * np.pi * ts["fs"]) ** 2 * ts["mms"])
    rms = 2 * np.pi * ts["fs"] * ts["mms"] / ts["qms"]
    return ts["re"] + s * ts["le"] + ts["bl"] ** 2 / (rms + s * ts["mms"] + 1 / (s * cms))


def woofer_transfer(f):
    """(v_d, v_p, zin, eq_gain_db) per volt of woofer drive, interpolated from A1's CSV."""
    d = np.genfromtxt(os.path.join(common.RESULTS, "a1_bass_transfer.csv"), delimiter=",", names=True)
    lf = np.log(np.asarray(f, float))
    li = np.log(d["f_hz"])

    def ci(re, im):
        return np.interp(lf, li, d[re]) + 1j * np.interp(lf, li, d[im])
    return ci("vd_re", "vd_im"), ci("vp_re", "vp_im"), ci("zin_re", "zin_im"), np.interp(lf, li, d["eq_gain_db"])


def baffle_piston_onaxis(f, a, r, v=1.0):
    """Exact on-axis pressure (e^{+jwt}) of a rigid piston of radius a in an infinite baffle at distance r."""
    k = 2 * np.pi * np.asarray(f, float) / common.C0
    return common.RHO * common.C0 * v * (np.exp(-1j * k * r) - np.exp(-1j * k * np.sqrt(r ** 2 + a ** 2)))


def baffle_piston_directivity(f, a, theta):
    """Far-field |D| of a baffled piston: 2 J1(ka sin th)/(ka sin th) in front, 0 behind (|th| > 90 deg)."""
    k = 2 * np.pi * np.asarray(f, float)[:, None] / common.C0
    x = k * a * np.sin(np.abs(theta))[None, :]
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.where(x < 1e-9, 1.0, 2 * j1(x) / x)
    d = np.where(np.abs(theta)[None, :] <= np.pi / 2 + 1e-9, d, 0.0)
    return d
