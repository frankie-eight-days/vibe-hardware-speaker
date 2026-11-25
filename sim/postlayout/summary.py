"""Print the hybrid-vs-other comparison table (markdown) from results/*.json."""
import json
import os
import sys

from pl_common import RESULTS


def j(name):
    p = os.path.join(RESULTS, name)
    return json.load(open(p)) if os.path.exists(p) else None


def row(label, vals):
    print(f"| {label} | " + " | ".join(vals) + " |")


def main(tags):
    print("| Metric | " + " | ".join(tags) + " |")
    print("|---|" + "---|" * len(tags))
    fh = {t: j(f"fh_loops_{t}.json") for t in tags}
    for loop in ("boost", "buck", "chg_pmid", "chg_sys"):
        v = []
        for t in tags:
            d = fh[t]
            l = next((x for x in d["loops"] if x["loop"] == loop), None) if d else None
            v.append("-" if l is None else (f"{l['L_nH']['1e+08']:.2f}" if l.get("status") == "ok" else "open"))
        row(f"Hot loop {loop}, nH @100 MHz", v)
    for i, nm in enumerate(("boost SW", "buck SW", "chg SW1", "chg SW2")):
        v = []
        for t in tags:
            d = fh[t]
            s = d["sw"][i] if d else None
            v.append("-" if s is None else f"{s['area_total_mm2']:.0f} / {s['C_gnd_pF'] + s['C_fringe_pF']:.1f}")
        row(f"{nm} area mm² / C to GND pF", v)
    rp = {t: j(f"return_paths_{t}.json") for t in tags}
    for k, lab in (("void_mm", "Fast nets over void, mm"), ("partial_mm", "Fast nets on split edge, mm"),
                   ("extra_area_void_mm2", "Extra return-loop area (voids), mm²")):
        row(lab, [f"{rp[t]['summary'][k]:.0f}" if rp[t] else "-" for t in tags])
    row("Fast-net vias without GND via ≤ 2 mm", [f"{rp[t]['summary']['transitions_unstitched']}/{rp[t]['summary']['transitions']}" if rp[t] else "-" for t in tags])
    cb = {t: j(f"copper_balance_{t}.json") for t in tags}
    nmax = max((len(cb[t]["coverage_pct"]) for t in tags if cb[t]), default=4)   # 4 or 6 layers
    row("Copper " + "/".join(f"L{k + 1}" for k in range(nmax)) + " %", ["/".join(f"{v:.0f}" for v in cb[t]["coverage_pct"].values()) if cb[t] else "-" for t in tags])
    prs = list(dict.fromkeys(pr for t in tags if cb[t] for pr in cb[t]["pairs"]))   # mirrored pairs, all boards
    for pr in prs:
        row(f"{pr} diff, pts (cells > 10 pts)", [f"{cb[t]['pairs'][pr]['global_diff_pts']:+.1f} ({cb[t]['pairs'][pr]['cells_out_pct']:.0f} %)" if cb[t] and pr in cb[t]["pairs"] else "-" for t in tags])
    ir = {t: j(f"ir_drop_{t}.json") for t in tags}
    for case in ("PVDD", "VSYS", "+3V3", "VBAT_PACK", "CHG_BAT", "GND_batt"):
        v = []
        for t in tags:
            c = next((x for x in ir[t] if x["case"] == case), None) if ir[t] else None
            if c is None:
                v.append("-"); continue
            ds = [("open" if l.get("V_drop_mV") is None else f"{l['V_drop_mV']:.0f}") for l in c.get("loads", [])]
            jm = max((x["J"] for x in c.get("J_max_A_mm2", {}).values()), default=0)
            v.append(f"{'/'.join(ds)} mV, {c.get('P_loss_mW', 0):.0f} mW, {jm:.0f} A/mm²" + (" (pins open)" if "not connected" in c["status"] else ""))
        row(f"DC {case}", v)
    th = {t: j(f"thermal_{t}.json") for t in tags}
    row("Max sustained out, W (Tj ≤ 125 °C, h 5/10)", [f"{th[t]['max_sustained_W']['h5']:.0f} / {th[t]['max_sustained_W']['h10']:.0f}" if th[t] else "-" for t in tags])
    for cn, ref in (("moderate 2.9 W", "U301"), ("charge 2 A + moderate", "U701"), ("Q801 recovery 1.5 W", "Q801")):
        row(f"Tj {ref}, {cn}, °C (h 5/10)", [f"{th[t]['cases'][cn]['h5']['parts'][ref]['T_j_C']:.0f} / {th[t]['cases'][cn]['h10']['parts'][ref]['T_j_C']:.0f}" if th[t] and ref in th[t]['cases'][cn]['h5']['parts'] else "-" for t in tags])


if __name__ == "__main__":
    main(sys.argv[1:] or ["hybrid", "autoroute"])
