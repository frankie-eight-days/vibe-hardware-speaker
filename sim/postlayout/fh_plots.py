"""Figures for analysis 1: current density in each hot loop (FastHenry, 100 MHz) and the
hybrid-vs-autoroute loop-inductance bar chart."""
import json
import os

import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle

from fh_loops import LOOPS
from pl_common import RESULTS, WORK, Z, load, savefig, style

FH = os.path.join(WORK, "fasthenry")


def jmap(tag, loop):
    f = os.path.join(FH, f"Jmag_{tag}_{loop}.mat")
    zc = os.path.join(FH, f"Zc_{tag}_{loop}.mat")
    if not os.path.exists(f):
        return None
    a = np.loadtxt(f)
    txt = open(zc).read().split("Impedance matrix for frequency = ")[-1].splitlines()[1].split()
    zabs = abs(complex(float(txt[0]), float(txt[1].replace("j", "")) if len(txt) > 1 else 0))
    a[:, :3] *= 1e3            # FastHenry writes SI: m -> mm
    a[:, 3:] *= 1e-6 * zabs    # A/m2 at 1 V -> A/mm2 per 1 A of port current
    return a


def main(tags=("hybrid", "autoroute")):
    plt = style()
    res = {t: json.load(open(os.path.join(RESULTS, f"fh_loops_{t}.json"))) for t in tags
           if os.path.exists(os.path.join(RESULTS, f"fh_loops_{t}.json"))}
    panels = [(t, l["loop"]) for t in res for l in res[t]["loops"] if l.get("status") == "ok"]
    fig, axs = plt.subplots(2, len(panels), figsize=(1.45 * len(panels) + 0.6, 3.6), squeeze=False)
    norm = LogNorm(1e-2, 10)
    for k, (t, ln) in enumerate(panels):
        a = jmap(t, ln)
        b = load(t)
        spec = next(s for s in LOOPS if s["name"] == ln)
        refs = {spec["pos"][0], spec["cap"]}
        pads = [p for p in b.pads if p["ref"] in refs]
        x0 = min(p["bbox"][0] for p in pads) - 1.5; x1 = max(p["bbox"][2] for p in pads) + 1.5
        y0 = min(p["bbox"][1] for p in pads) - 1.5; y1 = max(p["bbox"][3] for p in pads) + 1.5
        L = next(l for l in res[t]["loops"] if l["loop"] == ln)
        for r, (lay, zz) in enumerate((("L1", Z["F.Cu"]), ("L2", Z["In1.Cu"]))):
            ax = axs[r, k]
            if a is not None:
                sel = np.abs(a[:, 2] - zz) < 0.01
                jm = np.hypot(a[sel, 3], a[sel, 4])
                # thin-sheet density in A/mm (J * t) is what matters for inductance; show A/mm^2
                ax.scatter(a[sel, 0], a[sel, 1], c=np.clip(jm, 1e-2, None), s=1.2, marker="s", lw=0,
                           cmap="inferno", norm=norm, rasterized=True)
            for p in pads:
                bb = p["bbox"]
                ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1], fill=False, lw=0.4,
                                       ec="#2e75b6"))
            ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            ax.set_facecolor("#f2f2f2")
            if r == 0:
                ax.set_title(f"{t}\n{ln}: {L['L_nH']['1e+08']:.2f} nH", fontsize=8)
            if k == 0:
                ax.set_ylabel(lay, fontsize=9)
    sm = plt.cm.ScalarMappable(norm=norm, cmap="inferno")
    cb = fig.colorbar(sm, ax=axs, shrink=0.8, pad=0.02)
    cb.set_label("|J| at 100 MHz, A/mm$^2$ per 1 A", fontsize=8)
    savefig(fig, "hotloop_current_density")

    # bar chart
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    names = [s["name"] for s in LOOPS]
    w = 0.8 / len(res)
    for k, t in enumerate(res):
        vals, opens = [], []
        for n in names:
            l = next(l for l in res[t]["loops"] if l["loop"] == n)
            vals.append(l["L_nH"]["1e+08"] if l.get("status") == "ok" else 0)
            opens.append(l.get("status") != "ok")
        xs = np.arange(len(names)) + (k - (len(res) - 1) / 2) * w
        ax.bar(xs, vals, w, label=t, color=["#1f4e79", "#c55a11", "#548235"][k % 3])
        for x, v, o in zip(xs, vals, opens):
            ax.text(x, v + 0.02, "open\n(unrouted)" if o else f"{v:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(np.arange(len(names)))
    ax.set_xticklabels(["boost\nSW-VOUT-C914", "buck\nVIN-C953", "charger buck\nPMID-C707", "charger boost\nSYS-C716"])
    ax.set_ylabel("PCB loop inductance (nH)")
    ax.set_ylim(0, max(0.9, ax.get_ylim()[1] * 1.15))
    ax.legend(loc="upper left")
    ax.set_title("Hot-loop inductance, FastHenry at 100 MHz (cap body ESL excluded)", fontsize=10)
    savefig(fig, "hotloop_L_bar")


if __name__ == "__main__":
    import sys
    main(tuple(sys.argv[1:]) or ("hybrid", "autoroute"))
