"""S3: BQ25792 TS-pin network -> charge temperature window.

Circuit (spec_power 2.1/3.2): REGN -- RT1 5.1k -- TS -- RT2 30k -- GND, NTC (10k, B=3435 or 3380)
from TS to GND (TH801 on board, or pack NTC via J803). TS is ratiometric to REGN, so REGN's
value cancels; the charger compares V(TS)/V(REGN) with fixed VT1/VT5 and programmable VT2/VT3.

Method: ngspice .dc sweep of the circuit temperature with a behavioural NTC
(R = R25 exp(B (1/T - 1/298.15)), the standard beta model), cross-checked against the same
formula in Python. Thresholds: BQ25798 SLUSDV2C EC table (identical comparator block in BQ25792).
Validation: the datasheet's own reference point (RT1 = 5.24k, RT2 = 30.31k, 103AT -> 0 C at
73.3 %, 60 C at 34.2 %) is recomputed with the same model.
Tolerance: worst case over RT1/RT2 1 %, NTC R25 1 %, B 1 %, and the comparator min/max.
"""
from __future__ import annotations

import itertools

import numpy as np

from common import RESULTS, run_ngspice, use_style, savefig, write_csv, write_json

RT1, RT2 = 5.1e3, 30e3
R25 = 10e3
TH = {  # % of REGN: (min, typ, max); temperatures are the TI labels for the 5.24k/30.31k network
    "VT1_rise (cold stop, 0 C)": (72.4, 73.3, 74.2),
    "VT1_fall (cold resume, 3 C)": (71.5, 72.0, 72.5),
    "VT2_rise TS_COOL=1h (10 C)": (67.9, 68.4, 68.9),
    "VT3_fall TS_WARM=1h (45 C)": (44.3, 44.8, 45.3),
    "VT5_rise (hot resume, 58 C)": (35.0, 35.5, 36.0),
    "VT5_fall (hot stop, 60 C)": (33.7, 34.2, 34.7),
}


def ts_ratio(T_c, rt1=RT1, rt2=RT2, r25=R25, B=3435.0):
    rn = r25 * np.exp(B * (1 / (np.asarray(T_c) + 273.15) - 1 / 298.15))
    rb = 1 / (1 / rt2 + 1 / rn)
    return rb / (rt1 + rb)


def temp_at(ratio, **kw):
    T = np.linspace(-40, 120, 16001)
    r = ts_ratio(T, **kw)            # monotonically decreasing with T
    return float(np.interp(-ratio, -r, T))


def spice(B):
    net = f"""* S3: BQ25792 TS network, NTC beta model B={B}
VREGN regn 0 5.0
RT1 regn ts {RT1}
RT2 ts 0 {RT2}
* behavioural NTC: R = R25 exp(B (1/T - 1/298.15)), T from the simulator temperature
RNTC ts 0 R = {{{R25}*exp({B}*(1/(temper+273.15)-1/298.15))}}
.dc temp -30 90 0.5
.end
"""
    d = run_ngspice(net, f"s3_ntc_B{int(B)}")
    T = d.get("temp-sweep", d.get("temp", None))
    if T is None:
        T = d[list(d)[0]]
    return np.real(T), np.real(d["v(ts)"]) / 5.0


def main():
    plt = use_style()
    out = {"thresholds_pct": TH, "windows": {}}
    # validation against TI's reference network
    out["validation"] = {
        "TI_network_0C_pct_model": 100 * float(ts_ratio(0.0, 5.24e3, 30.31e3, 10e3, 3435)),
        "TI_network_0C_pct_datasheet": 73.3,
        "TI_network_60C_pct_model": 100 * float(ts_ratio(60.0, 5.24e3, 30.31e3, 10e3, 3435)),
        "TI_network_60C_pct_datasheet": 34.2,
        "TI_network_10C_pct_model": 100 * float(ts_ratio(10.0, 5.24e3, 30.31e3, 10e3, 3435)),
        "TI_network_10C_pct_datasheet": 68.4,
        "TI_network_45C_pct_model": 100 * float(ts_ratio(45.0, 5.24e3, 30.31e3, 10e3, 3435)),
        "TI_network_45C_pct_datasheet": 44.8,
    }
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    cols = {}
    for B in (3435.0, 3380.0):
        T, r = spice(B)
        rp = ts_ratio(T, B=B)
        out[f"spice_vs_python_max_err_pct_B{int(B)}"] = float(np.max(abs(r - rp)) * 100)
        ax.plot(T, 100 * r, label=f"V(TS)/V(REGN), NTC B = {int(B)} (ngspice)")
        cols.setdefault("T_C", T); cols[f"ts_pct_B{int(B)}"] = 100 * r
        w = {k: temp_at(v[1] / 100, B=B) for k, v in TH.items()}
        # worst-case window (tolerances)
        cold_hi, hot_lo = -99, 99
        cold_lo, hot_hi = 99, -99
        for s1, s2, s3, s4 in itertools.product((-1, 1), repeat=4):
            kw = dict(rt1=RT1 * (1 + 0.01 * s1), rt2=RT2 * (1 + 0.01 * s2), r25=R25 * (1 + 0.01 * s3),
                      B=B * (1 + 0.01 * s4))
            for th in (TH["VT1_rise (cold stop, 0 C)"][0], TH["VT1_rise (cold stop, 0 C)"][2]):
                t = temp_at(th / 100, **kw); cold_lo = min(cold_lo, t); cold_hi = max(cold_hi, t)
            for th in (TH["VT5_fall (hot stop, 60 C)"][0], TH["VT5_fall (hot stop, 60 C)"][2]):
                t = temp_at(th / 100, **kw); hot_lo = min(hot_lo, t); hot_hi = max(hot_hi, t)
        out["windows"][f"B{int(B)}"] = dict(typ=w, cold_stop_range_C=[cold_lo, cold_hi],
                                            hot_stop_range_C=[hot_lo, hot_hi],
                                            open_ntc_pct=100 * RT2 / (RT1 + RT2),
                                            shorted_ntc_pct=0.0)
    styles = {"VT1": ("C3", "--"), "VT2": ("C2", ":"), "VT3": ("C2", ":"), "VT5": ("C3", "--")}
    for k, (lo, typ, hi) in TH.items():
        c, ls = styles[k[:3]]
        ax.axhline(typ, color=c, ls=ls, lw=0.8)
        ax.axhspan(lo, hi, color=c, alpha=0.08)
        ax.text(-29, typ + 0.6, k, fontsize=6.5, color=c)
    w = out["windows"]["B3435"]["typ"]
    ax.axvspan(w["VT1_rise (cold stop, 0 C)"], w["VT5_fall (hot stop, 60 C)"], color="C2", alpha=0.07, zorder=-5)
    ax.annotate(f"charging allowed\n{w['VT1_rise (cold stop, 0 C)']:.1f} … {w['VT5_fall (hot stop, 60 C)']:.1f} °C",
                xy=(28, 58), ha="center", fontsize=8)
    ax.axhline(100 * RT2 / (RT1 + RT2), color="0.4", lw=0.8)
    ax.text(60, 100 * RT2 / (RT1 + RT2) + 0.7, "open NTC → 85.5 % (reads 'cold', charge suspended)", fontsize=6.5, color="0.3", ha="center")
    ax.set_xlabel("NTC temperature (°C)"); ax.set_ylabel("TS / REGN (%)")
    ax.set_xlim(-30, 90); ax.set_ylim(20, 90)
    ax.set_title("BQ25792 TS network RT1 = 5.1 k, RT2 = 30 k, 10 k NTC")
    ax.legend(fontsize=7, loc="lower left")
    savefig(fig, "s3_ntc_window")
    write_csv(RESULTS / "s3_ntc_ts_curve.csv", list(cols.keys()), list(cols.values()))
    write_json(RESULTS / "s3_ntc.json", out)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1, default=float))
