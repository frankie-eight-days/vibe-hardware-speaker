"""S6: board-to-board signal integrity over the 200 mm, 1.0 mm-pitch, 20-way FFC.

Questions
 1. What are Z0 and the delay of the FFC conductors with the spec's GND interleaving?
 2. How do SPI SCLK (40 MHz) and PDM_CLK (3.072 MHz) look at the far end with the 33 Ohm
    source resistors (edges, overshoot, ringing, eye)?
 3. What is the maximum safe SPI clock, and which series resistor is best?
 4. How much do SCLK/MOSI couple into neighbouring lines (MOSI, CS, DC)?

Method
 * Cross-section -> per-unit-length L and C matrices with a 2-D finite-difference field
   solver (ffc_field.py), validated against the conformal-mapping CPW formula.
 * ngspice transient: ESP32 pad (ramp source + R_out) -> 33 Ohm -> 40 mm main-board trace ->
   connector -> FFC (lossless T line + 0.4 Ohm conductor/skin loss) -> connector -> 25 mm UI
   trace -> 30 mm display-module wiring -> GC9A01 input (6 pF).
 * Crosstalk: 4-conductor coupled ladder (40 RLGC sections, K-coupled inductors + mutual C).
Assumptions are listed in ASSUME and in the README.
"""
from __future__ import annotations

import numpy as np

from common import RESULTS, run_ngspice, use_style, savefig, write_csv, write_json
from ffc_field import Section, graded, cpw_finite_ground_z0, C0

mm = 1e-3
ASSUME = dict(pitch_mm=1.0, conductor_width_mm=0.6, insulation_total_mm=0.12, eps_r_insulation=3.2,
              length_mm=200, esp32_rout_ohm=(20, 30, 45), esp32_edge_10_90_ns=(0.6, 1.0, 2.0),
              mainboard_trace="40 mm, 50 Ohm, 6.0 ps/mm", ui_trace="25 mm, 55 Ohm, 6.0 ps/mm",
              display_wiring="30 mm, 70 Ohm, 5.0 ps/mm (module header + module traces)",
              receiver_c_pF=6.0, connector_L_nH=2.0, connector_C_pF=0.3,
              gc9a01_vil_vih=(0.3 * 3.3, 0.7 * 3.3), sclk_min_high_low_ns=7.0,
              ffc_loss_ohm=0.4)
PINS = {1: "GND", 2: "+3V3", 3: "+3V3", 4: "GND", 5: "LCD_SCLK", 6: "GND", 7: "LCD_MOSI", 8: "LCD_CS",
        9: "LCD_DC", 10: "LCD_BL", 11: "GND", 12: "PDM_CLK", 13: "GND", 14: "PDM_DATA", 15: "UI_ENC_A",
        16: "UI_ENC_B", 17: "UI_ENC_SW", 18: "UI_BTN_ADC", 19: "GND", 20: "GND"}
SIG = [p for p, n in PINS.items() if n not in ("GND", "+3V3")]    # +3V3 is AC ground (decoupled)


def ffc_section(h, w=0.6, t_ins=0.12, er=3.2, plane_gap=None):
    strips = [((p - 1) * mm - w / 2 * mm, (p - 1) * mm + w / 2 * mm) for p in range(1, 21)]
    if plane_gap is not None:
        strips.append((-30 * mm, 49 * mm, -plane_gap * mm))
    x = graded(-1.0 * mm, 20.0 * mm, h * mm, -40 * mm, 59 * mm, 1.12, 1.5 * mm)
    ylo = -(plane_gap + 0.2) * mm if plane_gap else -0.1 * mm
    y = graded(min(-0.1 * mm, ylo), 0.1 * mm, h * mm / 2, -40 * mm, 40 * mm, 1.12, 1.5 * mm)
    diel = [(-0.5 * mm - 0.3 * mm, 19.5 * mm + 0.3 * mm, -t_ins / 2 * mm, t_ins / 2 * mm, er)]
    return Section(x, y, strips, diel)


def solve_lc(h=0.0125, **kw):
    S = ffc_section(h, **kw)
    act = [p - 1 for p in SIG]
    L, C, Ca = S.lc(act)
    return L, C


def lc_extrapolated(**kw):
    """Richardson extrapolation from h and h/2 (first-order convergence, see validation)."""
    L1, C1 = solve_lc(0.025, **kw)
    L2, C2 = solve_lc(0.0125, **kw)
    return 2 * L2 - L1, 2 * C2 - C1


def validate():
    out = []
    for h in (0.05, 0.025, 0.0125):
        x = graded(-1.4 * mm, 1.4 * mm, h * mm, -25 * mm, 25 * mm, 1.1, 1 * mm)
        y = graded(-0.1 * mm, 0.1 * mm, h * mm / 2, -25 * mm, 25 * mm, 1.1, 1 * mm)
        S = Section(x, y, [(-1.3 * mm, -0.7 * mm), (-0.3 * mm, 0.3 * mm), (0.7 * mm, 1.3 * mm)], [])
        L, C, _ = S.lc([1])
        out.append(dict(h_mm=h, z0_solver=float(np.sqrt(L[0, 0] / C[0, 0]))))
    z_ex = 2 * out[-1]["z0_solver"] - out[-2]["z0_solver"]
    return dict(grid=out, z0_extrapolated=z_ex, z0_analytic=float(cpw_finite_ground_z0(0.6 * mm, 0.4 * mm, 0.6 * mm)))


def line_params(L, C):
    res = {}
    for k, p in enumerate(SIG):
        z0 = np.sqrt(L[k, k] / C[k, k]); v = 1 / np.sqrt(L[k, k] * C[k, k])
        res[PINS[p]] = dict(pin=p, z0_ohm=float(z0), eps_eff=float((C0 / v) ** 2),
                            delay_ps_per_mm=float(1e9 / v), td_200mm_ns=float(0.2 / v * 1e9),
                            L_nH_per_mm=float(L[k, k] * 1e6), C_pF_per_mm=float(C[k, k] * 1e9))
    return res


def ladder(tag, a, b, z0, td, n, r_total=0.0):
    """Lumped LC ladder equivalent of a transmission line (n sections, section delay td/n).
    Used instead of ngspice's ideal T element, which hit time-step failures at sharp edges."""
    Ls, Cs, Rs = z0 * td / n, td / z0 / n, r_total / n
    out, prev = [], a
    for i in range(n):
        nxt = b if i == n - 1 else f"{tag}{i}"
        mid = f"{tag}{i}m"
        out.append(f"L{tag}{i} {prev} {mid} {Ls:.5g}")
        out.append(f"R{tag}{i} {mid} {nxt} {max(Rs, 1e-6):.4g}")
        out.append(f"C{tag}{i} {nxt} 0 {Cs:.5g}")
        prev = nxt
    return "\n".join(out) + "\n"


def chain(z0, td, rs, rout, tr, src, rx_c=6e-12, name="x"):
    """Single-ended chain from the ESP32 pad to the receiver pin."""
    return (f"""* S6 {name}
VSRC src 0 {src}
ROUT src pad {rout}
CPAD pad 0 3p
RS pad a {rs}
""" + ladder("mb", "a", "b", 50, 40 * 6.0e-12, 8)
        + f"LC1 b c {ASSUME['connector_L_nH']}n\nCC1 c 0 {ASSUME['connector_C_pF']}p\n"
        + ladder("ffc", "c", "d", z0, td, 40, ASSUME['ffc_loss_ohm'])
        + f"LC2 d e {ASSUME['connector_L_nH']}n\nCC2 e 0 {ASSUME['connector_C_pF']}p\n"
        + ladder("ui", "e", "f", 55, 25 * 6.0e-12, 6)
        + ladder("dm", "f", "rx", 70, 30 * 5.0e-12, 6)
        + f"CRX rx 0 {rx_c}\n")


def clock_src(f, tr):
    per = 1 / f
    return f"PULSE(0 3.3 2n {tr / 0.8:.4g} {tr / 0.8:.4g} {per / 2 - tr / 0.8:.4g} {per:.4g})"


def edge_metrics(t, v, f, vil, vih, t_start):
    sel = t > t_start
    t, v = t[sel], v[sel]
    per = 1 / f
    hi_times, lo_times, recross = [], [], 0
    above = v > vih; below = v < vil
    # pulse widths above V_IH and below V_IL
    def runs(mask):
        d = np.diff(mask.astype(int)); st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
        if len(en) and len(st) and en[0] < st[0]:
            en = en[1:]
        n = min(len(st), len(en))
        return t[en[:n]] - t[st[:n]]
    hi = runs(above); lo = runs(below)
    n_expected = int((t[-1] - t[0]) / per)
    recross = max(0, len(hi) - n_expected - 1) + max(0, len(lo) - n_expected - 1)
    return dict(overshoot_V=float(v.max() - 3.3), undershoot_V=float(-v.min()),
                min_high_ns=float(hi.min() * 1e9) if len(hi) else 0.0,
                min_low_ns=float(lo.min() * 1e9) if len(lo) else 0.0,
                extra_threshold_crossings=int(recross))


def main():
    plt = use_style()
    out = {"assumptions": ASSUME, "validation": validate()}
    L, C = lc_extrapolated()
    lp = line_params(L, C)
    out["ffc_lines_free_air"] = lp
    Lp, Cp = lc_extrapolated(plane_gap=1.0)
    out["ffc_lines_1mm_above_metal"] = line_params(Lp, Cp)
    write_json(RESULTS / "s6_ffc_LC.json", dict(signals=[PINS[p] for p in SIG], L_H_per_m=L, C_F_per_m=C,
                                               L_plane=Lp, C_plane=Cp))
    z0 = lp["LCD_SCLK"]["z0_ohm"]; td = lp["LCD_SCLK"]["td_200mm_ns"] * 1e-9
    vil, vih = ASSUME["gc9a01_vil_vih"]

    # ------------------------------------------------ SCLK at 40 MHz, series-R sweep, nominal driver
    fig, axs = plt.subplots(2, 1, figsize=(6.5, 5.0), sharex=True)
    res = {}
    for rs in (33, 47, 68, 82):
        net = chain(z0, td, rs, 30, 1.0e-9, clock_src(40e6, 1.0e-9), name=f"sclk_rs{rs}") + \
            ".tran 5p 160n 0 5p\n.end\n"
        d = run_ngspice(net, f"s6_sclk40_rs{rs}")
        t = d["time"]; v = d["v(rx)"]
        res[rs] = edge_metrics(t, v, 40e6, vil, vih, 40e-9)
        m = (t > 100e-9) & (t < 160e-9)
        axs[0 if rs in (33, 82) else 1].plot((t[m] - 100e-9) * 1e9, v[m], label=f"Rs = {rs} Ω")
        write_csv(RESULTS / f"s6_sclk40_rs{rs}.csv", ["t_s", "v_rx_V", "v_pad_V"], [t, v, d["v(pad)"]])
    for ax in axs:
        ax.axhspan(vil, vih, color="C3", alpha=0.08); ax.set_ylabel("V at GC9A01 (V)"); ax.legend(fontsize=7)
    axs[1].set_xlabel("Time (ns)")
    axs[0].set_title(f"LCD_SCLK 40 MHz at the display (FFC Z0 ≈ {z0:.0f} Ω, td ≈ {td * 1e9:.2f} ns)")
    savefig(fig, "s6_sclk_40MHz")
    out["sclk40_series_R"] = res

    # ------------------------------------------------ max clock: corners x frequency x Rs
    corners = {"fast": (20, 0.6e-9), "nom": (30, 1.0e-9), "slow": (45, 2.0e-9)}
    fmax = {}
    for rs in (33, 68):
        fmax[rs] = {}
        for cn, (ro, tr) in corners.items():
            ok_f = []
            for f in (20e6, 26.67e6, 40e6, 53.3e6, 80e6):
                net = chain(z0, td, rs, ro, tr, clock_src(f, tr), name=f"fmax") + \
                    f".tran 5p {12 / f:.4g} 0 5p\n.end\n"
                d = run_ngspice(net, "s6_fmax_tmp")
                m = edge_metrics(d["time"], d["v(rx)"], f, vil, vih, 4 / f)
                good = (m["extra_threshold_crossings"] == 0 and m["min_high_ns"] >= ASSUME["sclk_min_high_low_ns"]
                        and m["min_low_ns"] >= ASSUME["sclk_min_high_low_ns"] and m["overshoot_V"] < 0.9
                        and m["undershoot_V"] < 0.9)
                fmax[rs][f"{cn}_{f / 1e6:.1f}MHz"] = dict(m, ok=bool(good))
                if good:
                    ok_f.append(f)
            fmax[rs][f"{cn}_fmax_MHz"] = max(ok_f) / 1e6 if ok_f else 0
    out["fmax"] = fmax

    # ------------------------------------------------ MOSI eye at 40 Mb/s (PRBS7)
    rng = np.random.default_rng(1)
    bits = []
    reg = 0x7F
    for _ in range(127 * 2):
        b = ((reg >> 6) ^ (reg >> 5)) & 1; reg = ((reg << 1) | b) & 0x7F; bits.append(b)
    ui = 25e-9; tr = 1.0e-9
    pts = ["0 0"]
    for k, b in enumerate(bits):
        t0 = 2e-9 + k * ui
        pts += [f"{t0:.6g} {3.3 * bits[k - 1] if k else 0}", f"{t0 + tr / 0.8:.6g} {3.3 * b}"]
    src = "PWL(" + " ".join(pts) + ")"
    fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.0), sharey=True)
    eyes = {}
    for ax, rs in zip(axs, (33, 68)):
        net = chain(lp["LCD_MOSI"]["z0_ohm"], lp["LCD_MOSI"]["td_200mm_ns"] * 1e-9, rs, 30, tr, src,
                    name=f"mosi_eye_{rs}") + f".tran 10p {2e-9 + len(bits) * ui:.6g} 0 10p\n.end\n"
        d = run_ngspice(net, f"s6_mosi_eye_rs{rs}")
        t = d["time"]; v = d["v(rx)"]
        tu = np.arange(10 * ui, t[-1] - ui, 20e-12)
        vu = np.interp(tu, t, v)
        ph = ((tu - 2e-9) % ui)
        ax.plot(ph * 1e9, vu, ",", alpha=0.25, color="C0")
        ax.axhspan(vil, vih, color="C3", alpha=0.08)
        ax.set_title(f"MOSI eye 40 Mb/s, Rs = {rs} Ω", fontsize=9); ax.set_xlabel("Time in UI (ns)")
        # eye opening at the bit centre (sample at half-UI after the far-end edge delay)
        delay = 0.0
        best = None
        for cphase in np.linspace(0, ui, 101):
            s = np.abs(ph - cphase) < 0.1e-9
            hi_ = vu[s & (vu > 1.65)]; lo_ = vu[s & (vu <= 1.65)]
            if len(hi_) and len(lo_):
                hgt = hi_.min() - lo_.max()
                if best is None or hgt > best[1]:
                    best = (cphase, hgt)
        eyes[rs] = dict(eye_height_V=float(best[1]), at_ns=float(best[0] * 1e9),
                        overshoot_V=float(vu.max() - 3.3), undershoot_V=float(-vu.min()))
        write_csv(RESULTS / f"s6_mosi_eye_rs{rs}.csv", ["t_s", "v_rx_V"], [tu, vu])
    axs[0].set_ylabel("V at GC9A01 (V)")
    savefig(fig, "s6_mosi_eye")
    out["mosi_eye"] = eyes

    # ------------------------------------------------ PDM clock and data round trip
    zc = lp["PDM_CLK"]["z0_ohm"]; tdc = lp["PDM_CLK"]["td_200mm_ns"] * 1e-9
    net = chain(zc, tdc, 33, 30, 1.0e-9, clock_src(3.072e6, 1.0e-9), rx_c=3e-12, name="pdm_clk") + \
        ".tran 20p 700n 0 20p\n.end\n"
    d = run_ngspice(net, "s6_pdm_clk")
    t = d["time"]; v = d["v(rx)"]; vp = d["v(pad)"]
    tp = t[np.argmax(vp > 1.65)]; tr_ = t[np.argmax(v > 1.65)]
    out["pdm_clk"] = dict(edge_metrics(t, v, 3.072e6, vil, vih, 330e-9), pad_to_mic_delay_ns=float((tr_ - tp) * 1e9))
    # data back: mic driver (assume 50 Ohm, 2 ns edge) + R10 33 Ohm at the mic, ESP32 input 5 pF
    zd = lp["PDM_DATA"]["z0_ohm"]; tdd = lp["PDM_DATA"]["td_200mm_ns"] * 1e-9
    net = chain(zd, tdd, 33, 50, 2.0e-9, clock_src(3.072e6, 2.0e-9), rx_c=5e-12, name="pdm_data") + \
        ".tran 20p 700n 0 20p\n.end\n"
    d2 = run_ngspice(net, "s6_pdm_data")
    t2 = d2["time"]; v2 = d2["v(rx)"]
    out["pdm_data"] = dict(edge_metrics(t2, v2, 3.072e6, vil, vih, 330e-9),
                           mic_to_esp_delay_ns=float((t2[np.argmax(v2 > 1.65)] - t2[np.argmax(d2['v(pad)'] > 1.65)]) * 1e9))
    out["pdm_round_trip_ns"] = out["pdm_clk"]["pad_to_mic_delay_ns"] + out["pdm_data"]["mic_to_esp_delay_ns"]
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    m = (t > 320e-9) & (t < 520e-9)
    ax.plot(t[m] * 1e9, vp[m], label="PDM_CLK at ESP32 pad")
    ax.plot(t[m] * 1e9, v[m], label="PDM_CLK at mic")
    m2 = (t2 > 320e-9) & (t2 < 520e-9)
    ax.plot(t2[m2] * 1e9, v2[m2], "--", label="PDM_DATA at ESP32 (mic-driven edge)")
    ax.set_xlabel("Time (ns)"); ax.set_ylabel("V"); ax.legend(fontsize=7)
    ax.set_title("PDM clock (3.072 MHz) over the FFC, R118 = 33 Ω")
    savefig(fig, "s6_pdm")
    write_csv(RESULTS / "s6_pdm_clk.csv", ["t_s", "v_pad", "v_mic"], [t, vp, v])

    # ------------------------------------------------ crosstalk: coupled ladder, conductors 5,7,8,9
    idx = [SIG.index(p) for p in (5, 7, 8, 9)]
    Ls = L[np.ix_(idx, idx)]; Cs = C[np.ix_(idx, idx)]
    N = 40; dz = 0.2 / N
    names = ["sclk", "mosi", "cs", "dc"]
    lines = ["* S6 crosstalk ladder: conductors 5 (SCLK), 7 (MOSI), 8 (CS), 9 (DC)"]
    for k, nm in enumerate(names):
        for i in range(N):
            lines.append(f"L{nm}{i} {nm}{i} {nm}{i}m {Ls[k, k] * dz:.5g}")
            lines.append(f"R{nm}{i} {nm}{i}m {nm}{i + 1} {ASSUME['ffc_loss_ohm'] / N:.4g}")
            cg = Cs[k].sum() * dz
            lines.append(f"CG{nm}{i} {nm}{i + 1} 0 {cg:.5g}")
    for a in range(4):
        for b in range(a + 1, 4):
            kab = Ls[a, b] / np.sqrt(Ls[a, a] * Ls[b, b])
            for i in range(N):
                lines.append(f"K{names[a]}{names[b]}{i} L{names[a]}{i} L{names[b]}{i} {kab:.5f}")
                lines.append(f"CM{names[a]}{names[b]}{i} {names[a]}{i + 1} {names[b]}{i + 1} {-Cs[a, b] * dz:.5g}")
    xt = {}
    for rs in (33, 68):
        for agg in ("sclk", "mosi"):
            net = "\n".join(lines) + "\n"
            for nm in names:   # fast driver corner: 20 Ohm, 0.6 ns edges; victims held low
                if nm == agg:
                    net += f"V{nm} {nm}_s 0 {clock_src(40e6, 0.6e-9)}\nRS{nm} {nm}_s {nm}0 {20 + rs}\n"
                else:
                    net += f"RS{nm} {nm}0 0 {20 + rs}\n"
                net += f"CRX{nm} {nm}{N} 0 6p\n"
            net += ".tran 5p 120n 0 5p\n.end\n"
            d = run_ngspice(net, f"s6_xtalk_{agg}_rs{rs}")
            t = d["time"]
            key = f"{agg}_aggressor_Rs{rs}"
            xt[key] = {f"{nm}_far_peak_mV": float(np.max(np.abs(d[f"v({nm}{N})"][t > 20e-9])) * 1e3)
                       for nm in names if nm != agg}
            xt[key].update({f"{nm}_near_peak_mV": float(np.max(np.abs(d[f"v({nm}0)"][t > 20e-9])) * 1e3)
                            for nm in names if nm != agg})
            if agg == "mosi":
                write_csv(RESULTS / f"s6_xtalk_mosi_rs{rs}.csv", ["t_s"] + [f"v_{nm}_far" for nm in names],
                          [t] + [d[f"v({nm}{N})"] for nm in names])
                if rs == 33:
                    fig, ax = plt.subplots(figsize=(6.5, 2.8))
                    m = (t > 40e-9) & (t < 120e-9)
                    for nm in names:
                        ax.plot((t[m] - 40e-9) * 1e9, d[f"v({nm}{N})"][m], lw=1.0 if nm != "mosi" else 0.6,
                                label=f"{nm.upper()} at display" + (" (aggressor)" if nm == "mosi" else ""))
                    ax.axhline(vil, color="C3", ls="--", lw=0.8); ax.text(1, vil + 0.05, "V_IL", color="C3", fontsize=7)
                    ax.set_ylim(-1, 1.5); ax.set_xlabel("Time (ns)"); ax.set_ylabel("V")
                    ax.set_title("Far-end crosstalk from MOSI (40 MHz toggling, fast corner, Rs = 33 Ω)")
                    ax.legend(fontsize=7, ncol=2)
                    savefig(fig, "s6_crosstalk")
    out["crosstalk_40MHz_fast_corner"] = xt
    out["coupling_coeffs"] = {f"k_L_{names[a]}_{names[b]}": float(Ls[a, b] / np.sqrt(Ls[a, a] * Ls[b, b]))
                              for a in range(4) for b in range(a + 1, 4)}
    out["coupling_coeffs"].update({f"k_C_{names[a]}_{names[b]}": float(-Cs[a, b] / np.sqrt(Cs[a, a] * Cs[b, b]))
                                   for a in range(4) for b in range(a + 1, 4)})
    write_json(RESULTS / "s6_ffc_si.json", out)
    return out


if __name__ == "__main__":
    import json
    o = main()
    print(json.dumps({k: v for k, v in o.items() if k not in ("fmax",)}, indent=1, default=float)[:7000])
    for rs, d in o["fmax"].items():
        print(rs, {k: v for k, v in d.items() if k.endswith("fmax_MHz")})
