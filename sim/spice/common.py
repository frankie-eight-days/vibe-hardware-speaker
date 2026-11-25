"""Shared helpers for the SPICE simulations (S1-S7).

- run_ngspice(): write a netlist, run `ngspice -b`, return parsed vectors from a raw file.
- read_raw(): minimal parser for ngspice binary/ASCII raw files (real and complex).
- savefig(): write PDF + PNG with the project style.
- write_csv()/write_json(): machine-readable results for every figure.
- Capacitor/inductor helper models shared with sim/pdn.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SPICE = ROOT / "sim" / "spice"
NETLISTS = SPICE / "netlists"
TI_RUNS = SPICE / "ti_runs"
RESULTS = SPICE / "results"
FIGS = ROOT / "docs" / "figures" / "spice"
STYLE = ROOT / "sim" / "paper.mplstyle"
NGSPICE = shutil.which("ngspice") or "/opt/homebrew/bin/ngspice"

for d in (NETLISTS, RESULTS, FIGS):
    d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- raw files
def read_raw(path: str | Path) -> dict[str, np.ndarray]:
    """Parse an ngspice raw file (binary or ascii, real or complex). Returns {name: array}."""
    data = Path(path).read_bytes()
    out: dict[str, np.ndarray] = {}
    pos = 0
    while pos < len(data):
        # header lines until "Binary:" or "Values:"
        header = {}
        names = []
        nvars = npts = 0
        complex_ = False
        while True:
            nl = data.index(b"\n", pos)
            line = data[pos:nl].decode("latin-1")
            pos = nl + 1
            if ":" in line and not line.startswith("\t"):
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                header[key] = val
                if key == "flags":
                    complex_ = "complex" in val.lower()
                elif key == "no. variables":
                    nvars = int(val)
                elif key == "no. points":
                    npts = int(val)
                elif key == "variables":
                    for _ in range(nvars):
                        nl = data.index(b"\n", pos)
                        parts = data[pos:nl].decode("latin-1").split()
                        pos = nl + 1
                        names.append(parts[1])
                elif key == "binary":
                    width = 16 if complex_ else 8
                    # ngspice may write more/fewer rows than the header announces (interp,
                    # aborted runs): use the real block length up to the next plot or EOF.
                    nxt = data.find(b"Title:", pos + nvars * npts * width - 64) if npts else -1
                    end = nxt if nxt > 0 else len(data)
                    npts = (end - pos) // (nvars * width)
                    n = nvars * npts
                    arr = np.frombuffer(data, dtype="<f8", count=n * (width // 8), offset=pos)
                    pos += n * width
                    if complex_:
                        arr = arr.reshape(npts, nvars, 2)
                        arr = arr[..., 0] + 1j * arr[..., 1]
                    else:
                        arr = arr.reshape(npts, nvars)
                    for i, nm in enumerate(names):
                        out[nm.lower()] = arr[:, i].copy()
                    if nxt <= 0:
                        pos = len(data)   # ignore a trailing partial row
                    else:
                        pos = nxt
                    break
                elif key == "values":
                    vals = []
                    txt = data[pos:].decode("latin-1").split()
                    # ascii: index, then nvars values per point
                    k = 0
                    rows = []
                    for _ in range(npts):
                        k += 1  # index
                        row = []
                        for _ in range(nvars):
                            t = txt[k]
                            k += 1
                            if "," in t:
                                re, im = t.split(",")
                                row.append(float(re) + 1j * float(im))
                            else:
                                row.append(float(t))
                        rows.append(row)
                    arr = np.array(rows)
                    for i, nm in enumerate(names):
                        out[nm.lower()] = arr[:, i]
                    pos = len(data)
                    break
        if pos >= len(data) or not data[pos:].strip():
            break
    return out


def run_ngspice(netlist: str, name: str, cwd: Path | None = None, timeout: int = 7200,
                quiet: bool = True, control: bool = False) -> dict[str, np.ndarray]:
    """Write <name>.cir (into cwd or NETLISTS), run ngspice -b -r <name>.raw, parse the raw file.
    control=True: the netlist has its own .control block that writes <name>.raw (no -r).
    Note: ngspice-47 writes a corrupt binary raw file with `.options interp` + `uic`; use a
    .control block with `linearize` instead (see s1_boost_switching.py)."""
    cwd = Path(cwd) if cwd else NETLISTS
    cir = cwd / f"{name}.cir"
    raw = cwd / f"{name}.raw"
    log = cwd / f"{name}.log"
    cir.write_text(netlist)
    if raw.exists():
        raw.unlink()
    with open(log, "w") as fh:
        args = [NGSPICE, "-b", cir.name] if control else [NGSPICE, "-b", "-r", raw.name, cir.name]
        subprocess.run(args, cwd=cwd, stdout=fh,
                       stderr=subprocess.STDOUT, timeout=timeout, check=False)
    if not raw.exists():
        raise RuntimeError(f"ngspice produced no raw file for {name}; see {log}")
    return read_raw(raw)


# --------------------------------------------------------------------------- output helpers
def use_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.style.use(str(STYLE))
    return plt


def savefig(fig, stem: str, figdir: Path = FIGS):
    figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / f"{stem}.pdf")
    fig.savefig(figdir / f"{stem}.png")


def write_csv(path: Path, header: list[str], cols: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [np.asarray(c) for c in cols]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for row in zip(*cols):
            w.writerow([f"{v:.6g}" if isinstance(v, (float, np.floating)) else v for v in row])


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, complex):
        return {"re": o.real, "im": o.imag}
    return o


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(obj), indent=1))


def decimate(t, *ys, n=4000):
    """Uniformly resample for CSV export (keeps files small)."""
    t = np.asarray(t)
    tt = np.linspace(t[0], t[-1], n)
    return [tt] + [np.interp(tt, t, np.asarray(y)) for y in ys]


# --------------------------------------------------------------------------- component models
def mlcc_cap_dc_bias(c0: float, v: float, v_rated: float, size: str = "1206",
                     dielectric: str = "X5R") -> float:
    """Effective MLCC capacitance under DC bias (empirical).

    C(V) = C0 / (1 + (V / V50)^n). V50 (the bias at which C halves) is set per case size /
    rating from published curves (Murata SimSurfing / Samsung MLCC tool / TI SLUSEA4D quotes):
      * 10 uF 50 V X5R 1206 : ~4.5 uF @ 18 V, ~3.5 uF @ 24 V  -> V50 ~ 15 V, n ~ 1.2
      * 22 uF 25 V X5R 1206 : ~11 uF @ 7.4 V                    -> V50 ~ 7.5 V
      * 22 uF 25 V X5R 0805/1206 at 3.3 V: ~17 uF (spec)        -> V50 ~ 9 V
      * 10 uF 25 V X5R 0805 : ~6 uF @ 7.4 V                     -> V50 ~ 10 V
      * 1 uF 50 V X7R 0805  : ~0.75 uF @ 9 V                    -> V50 ~ 25 V
    These anchors are estimates (curve reads), not vendor SPICE models. Replace the table with
    exported vendor curves when the exact LCSC part numbers are fixed.
    """
    table = {
        ("1206", 50, 10e-6): (15.0, 1.2),
        ("1206", 25, 22e-6): (7.5, 1.2),
        ("1206", 25, 22e-6, 3.3): (9.0, 1.2),
        ("0805", 25, 10e-6): (10.0, 1.2),
        ("0805", 25, 22e-6): (6.0, 1.2),
        ("0805", 50, 1e-6): (25.0, 1.2),
        ("0603", 50, 1e-6): (12.0, 1.2),
        ("0603", 16, 4.7e-6): (6.0, 1.2),
        ("0603", 10, 10e-6): (4.0, 1.2),
    }
    key = (size, int(v_rated), c0)
    v50, n = table.get(key, (0.45 * v_rated, 1.2))
    if dielectric.upper().startswith("C0G"):
        return c0
    return c0 / (1.0 + (abs(v) / v50) ** n)


def z_rlc(f, C=None, esr=0.0, esl=0.0):
    """Impedance of a series R-L-C branch (C=None -> R-L only)."""
    w = 2 * np.pi * np.asarray(f, dtype=float)
    z = esr + 1j * w * esl
    if C:
        z = z + 1 / (1j * w * C)
    return z


def par(*zs):
    y = 0
    for z in zs:
        y = y + 1 / z
    return 1 / y
