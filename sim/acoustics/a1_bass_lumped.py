#!/usr/bin/env python3
"""A1 - Bass system (lumped): 2x Dayton ND65-8 + 2x Dayton DMA58-PR in the real 0.82-0.85 L capsule.

Question: with the real net volume and the real amplifier limits (TAS5805M BTL on an 18.0 V PVDD, woofer
limiter at 15.5 V peak), what PR added mass should we use, how loud can the bass play before the amp, the
woofer or the PRs run out, and what DSP bass EQ gives F3 ~ 64 Hz? What do polyfill or zeolite buy?

Run:  .venv/bin/python sim/acoustics/a1_bass_lumped.py      (about 1 min; MPLBACKEND forced to Agg)
Model: sim/acoustics/bass_model.py.  Cross-check: electroacPy 2025.7.1 lumped solver.
Outputs: docs/figures/acoustics/a1_*.pdf/.png, sim/acoustics/results/a1_*.csv/.json
"""
import os
import sys
import time

os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib.ticker               # noqa: E402
import numpy as np                      # noqa: E402
from scipy.optimize import least_squares  # noqa: E402

import bass_model as bm                 # noqa: E402
import common                           # noqa: E402

T0 = time.time()
plt = common.setup_mpl()
PARTS = common.load_parts()
W = PARTS["ND65-8"]["ts"]
P = PARTS["DMA58-PR"]["ts"]

# ----------------------------------------------------------------------------- assumptions
VB_NOM = 0.85e-3          # net volume from the CAD (mech/concept/build/report.json)
VB_FINAL = 0.82e-3        # after unmodelled parts (docs/mech_envelope.md section 5)
QL = 10.0                 # leakage Q (gasketed printed box)
QA = 100.0                # absorption Q of an unstuffed box (Small 1973: ~100+ when empty)
CREST = 3.0               # pink-noise crest factor after the DRC/limiter (9.5 dB)
F3_TARGET = 63.0          # BW4 target corner; the realised -3 dB point lands at ~64 Hz with the subsonic
FX = 2500.0               # woofer/tweeter LR4 crossover
FS_DSP = 48000.0          # TAS5805M processing rate
MAX_BOOST_DB = 18.0
PINK_REQ = 90.0
M_STEP = 0.25e-3
M_ADD_MAX = 2.5 * P["mms_kg"]   # 16.75 g: more risks rocking / suspension sag on a horizontal axis
F = np.logspace(np.log10(10.0), np.log10(20000.0), 600)
BAND = (F >= 15) & (F <= 1000)
R_PB = (F > 300) & (F < 600)


def evaluate(vb, m_add, ql=QL, qa=QA, vb_factor=1.0, v_max=bm.V_PK_MAX):
    s = bm.system(F, W, P, vb, m_add, ql=ql, qa=qa, vb_factor=vb_factor)
    g, href = bm.ideal_eq(F, s, f3=F3_TARGET, max_boost_db=MAX_BOOST_DB)
    pink, lim, p_w, cand = bm.pink_estimate(F, s, W, P, g, href, crest=CREST, fx=FX, v_max=v_max)
    rdb = 20 * np.log10(np.abs(s["p_hs"]) * g / href)
    ndb = bm.spl_pk(s["p_hs"])
    nref = np.mean(ndb[R_PB])
    v_allow, which = bm.sine_limits(s, W, P, v_max=v_max)
    return dict(sys=s, g=g, href=href, pink=pink, pink_lim=lim, p_woofer=p_w, cand=cand,
                f3_eq=bm.f_at_level(F, rdb, 0, 3), f6_eq=bm.f_at_level(F, rdb, 0, 6),
                f3_nat=bm.f_at_level(F, ndb, nref, 3), f6_nat=bm.f_at_level(F, ndb, nref, 6),
                max_boost_db=float(20 * np.log10(g[BAND].max())), v_allow=v_allow, which=which,
                maxspl=bm.spl_pk(s["p_hs"] * v_allow), m_add=m_add, vb=vb, vb_factor=vb_factor, ql=ql, qa=qa)


def optimise_mass(vb, **kw):
    ms = np.arange(0.0, M_ADD_MAX + 1e-9, M_STEP)
    res = [evaluate(vb, m, **kw) for m in ms]
    k = int(np.argmax([r["pink"] for r in res]))
    return res[k], res


def dsp_ceiling(r):
    """Highest flat-passband SINE level (with the bass EQ) that no frequency 15 Hz-1 kHz violates."""
    p_pb = r["v_allow"][BAND] * r["href"] / r["g"][BAND]
    k = int(np.argmin(p_pb))
    return float(bm.spl_pk(p_pb[k])), float(F[BAND][k])


# ============================================================================ 1. validation
print("=== Validation ===")
val = {}
s = bm.system(F, W, None, VB_FINAL, nd=2, np_=0, ql=1e9)
fine = np.logspace(np.log10(50), np.log10(400), 20000)
sf = bm.system(fine, W, None, VB_FINAL, nd=2, np_=0, ql=1e9)
fc_lem = float(fine[np.argmax(np.abs(sf["zin"]))])
# closed form with the model's own constants: fs from Mms/Cms, Vas = rho c^2 Sd^2 Cms (2 woofers share Vb)
fs_mc = 1 / (2 * np.pi * np.sqrt(W["mms_kg"] * W["cms_m_per_n"]))
vas_mc = bm.RHO * bm.C0 ** 2 * W["sd_m2"] ** 2 * W["cms_m_per_n"]
fc_th = fs_mc * np.sqrt(1 + 2 * vas_mc / VB_FINAL)
# impedance peak of a driver with Le sits slightly off the mechanical resonance; compare with Le = 0
w0 = dict(W, le_h=0.0)
sf0 = bm.system(fine, w0, None, VB_FINAL, nd=2, np_=0, ql=1e9)
fc_lem0 = float(fine[np.argmax(np.abs(sf0["zin"]))])
val["sealed_fc_closed_form_hz"] = fc_th
val["sealed_fc_model_Le0_hz"] = fc_lem0
val["sealed_fc_model_with_Le_hz"] = fc_lem
print(f"sealed 2xND65-8 in {VB_FINAL*1e3:.2f} L: closed form fc {fc_th:.2f} Hz, model |Z| peak {fc_lem0:.2f} Hz "
      f"(Le=0), {fc_lem:.2f} Hz (with Le)")
assert abs(fc_lem0 - fc_th) / fc_th < 0.001
# 2 woofers + 2 PRs in Vb must equal 1 woofer + 1 PR in Vb/2 (symmetry), to machine precision
a = bm.system(F, W, P, VB_FINAL, 3.5e-3)
b = bm.system(F, W, P, VB_FINAL / 2, 3.5e-3, nd=1, np_=1)
assert np.allclose(a["x_d"], b["x_d"], rtol=1e-10) and np.allclose(a["x_p"], b["x_p"], rtol=1e-10)
# Lossless PR: at fp the PR's mechanical impedance is zero, the box pressure collapses and the PRs pass exactly
# the woofers' rear volume velocity, so the total output has a zero at fp. Check the notch depth with Rmp -> 0.
p_lossless = dict(P, rms_kg_per_s=1e-9)
fn = np.logspace(np.log10(15), np.log10(400), 40001)
c = bm.system(fn, W, p_lossless, VB_FINAL, 3.5e-3, ql=1e9)
k = np.argmin(np.abs(fn - c["fp"]))
val["lossless_notch_depth_db"] = float(bm.spl_pk(c["p_hs"][k]) - np.max(bm.spl_pk(c["p_hs"])))
print(f"lossless PR notch at fp={c['fp']:.1f} Hz: {val['lossless_notch_depth_db']:.0f} dB below peak")
assert val["lossless_notch_depth_db"] < -40


# ---- electroacPy cross-check ---------------------------------------------------------------
def electroacpy_crosscheck(m_add=3.5e-3, vb=VB_FINAL):
    """Same physics in electroacPy: one woofer + one PR in vb/2, which is identical to 2+2 in vb by symmetry
    (checked above), so pressures are doubled for the full system. electroacPy references its loss Qs to the
    sealed-box resonance (leak_ref='fc' here). Its `radiator` element uses rho*c*(R1 + jX1) as the ACOUSTIC
    impedance, without the 1/S factor, so its radiation load is ~1/S (~600x) too small, i.e. negligible; our
    default model (no added radiation impedance) is therefore the like-for-like comparison. The variant with a
    correct baffled-piston load is also reported to show how much the air load matters."""
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        from electroacPy.speakerSim.electroAcousticDriver import electroAcousticDriver
        from electroacPy.speakerSim.enclosureDesign import speakerBox
    rho, c0 = 1.22, 343.0
    fq = np.logspace(np.log10(15), np.log10(2000), 400)
    drv = electroAcousticDriver(1, W["le_h"], W["re_ohm"], W["cms_m_per_n"], W["mms_kg"], W["rms_kg_per_s"],
                                W["bl_tm"], W["sd_m2"], fq, c=c0, rho=rho)
    qab, qal = 120.0, 10.0
    box = speakerBox(vb / 2, frequencyRange=fq, Qab=qab, Qal=qal, c=c0, rho=rho,
                     Mmd=P["mms_kg"] + m_add, Cmd=P["cms_m_per_n"], Rmd=P["rms_kg_per_s"], Sd=P["sd_m2"])
    box.getDriverResponse(drv)
    s_ea = 1j * 2 * np.pi * fq
    u_ea = 2 * (box.Q + box.Qpr)                    # two identical halves
    out = dict(f=fq, zin_ea=box.Ze, xd_ea=box.v / s_ea, xp_ea=box.vpr / s_ea, p_ea=rho * s_ea * u_ea / (2 * np.pi))
    ours = bm.system(fq, W, P, vb, m_add, ql=qal, qa=qab, radiation="none", rho=rho, c=c0, leak_ref="fc")
    ours_rad = bm.system(fq, W, P, vb, m_add, ql=qal, qa=qab, radiation="baffled_piston", rho=rho, c=c0, leak_ref="fc")
    out.update(zin=ours["zin"], xd=ours["x_d"], xp=ours["x_p"], p=ours["p_hs"], p_rad=ours_rad["p_hs"])
    db = lambda x: 20 * np.log10(np.abs(x))
    dev = dict(spl_db=float(np.max(np.abs(db(out["p"]) - db(out["p_ea"])))),
               zin_pct=float(100 * np.max(np.abs(np.abs(out["zin"]) - np.abs(out["zin_ea"])) / np.abs(out["zin_ea"]))),
               xd_db=float(np.max(np.abs(db(out["xd"]) - db(out["xd_ea"])))),
               xp_db=float(np.max(np.abs(db(out["xp"]) - db(out["xp_ea"])))),
               air_load_effect_spl_db_max=float(np.max(np.abs(db(out["p_rad"]) - db(out["p"])))))
    return out, dev


ea, ea_dev = electroacpy_crosscheck()
val["electroacpy_max_deviation"] = ea_dev
print("electroacPy cross-check (same physics):", {k: round(v, 4) for k, v in ea_dev.items()})
assert ea_dev["spl_db"] < 0.1 and ea_dev["zin_pct"] < 0.5

# ============================================================================ 2. PR mass sweep
print("\n=== PR added-mass sweep ===")
sweep = {}
for vb in (VB_NOM, VB_FINAL):
    best, allr = optimise_mass(vb)
    sweep[vb] = (best, allr)
    print(f"Vb {vb*1e3:.2f} L: best m_add {best['m_add']*1e3:.2f} g/PR -> pink {best['pink']:.2f} dB ({best['pink_lim']})")
best82, all82 = sweep[VB_FINAL]
# Choice: the pink optimum is flat (+-0.05 dB from 2.5 to 4 g). Take 3.5 g: the PR and woofer excursion
# limits then sit >= 1.2 dB above the amp-voltage limit, so tolerance in Cms/Mms or the real QL does not
# make the PR the bottleneck, and it is reachable with M3/M4 washers on the DMA58-PR rod.
M_CHOSEN = 3.5e-3
fin = evaluate(VB_FINAL, M_CHOSEN)
nom = evaluate(VB_NOM, M_CHOSEN)
for r in (fin, nom):
    r["ceiling_db"], r["ceiling_f"] = dsp_ceiling(r)
s = fin["sys"]
print(f"chosen {M_CHOSEN*1e3:.1f} g/PR at {VB_FINAL*1e3:.2f} L: fb {s['fb']:.1f} Hz, fp {s['fp']:.1f} Hz, "
      f"pink {fin['pink']:.2f} dB ({fin['pink_lim']}), margins {', '.join(f'{k} {v-fin['pink']:+.1f}' for k, v in fin['cand'].items())}")
print(f"  natural F3/F6 {fin['f3_nat']:.0f}/{fin['f6_nat']:.0f} Hz; with EQ {fin['f3_eq']:.1f}/{fin['f6_eq']:.1f} Hz; "
      f"max boost {fin['max_boost_db']:.1f} dB; DSP sine ceiling {fin['ceiling_db']:.1f} dB (set by {fin['ceiling_f']:.0f} Hz)")

# ============================================================================ 3. biquad realisation of the bass EQ
print("\n=== Biquad realisation of the bass EQ (fs = 48 kHz) ===")
g_ideal_db = 20 * np.log10(fin["g"])
fit_band = (F >= 25) & (F <= 1500)


def eq_sos(x):
    f_hp, f_ls, g_ls, q_ls, f_pk, g_pk, q_pk = x
    return np.vstack([bm.rbj("hp", f_hp, FS_DSP, q=0.5412), bm.rbj("hp", f_hp, FS_DSP, q=1.3066),
                      bm.rbj("lowshelf", f_ls, FS_DSP, q=q_ls, gain_db=g_ls),
                      bm.rbj("peak", f_pk, FS_DSP, q=q_pk, gain_db=g_pk)])


def resid(x):
    h = 20 * np.log10(np.abs(bm.sos_response(eq_sos(x), F[fit_band], FS_DSP)))
    wgt = np.where(F[fit_band] > 40, 1.0, 0.3)
    return (h - g_ideal_db[fit_band]) * wgt


x0 = [45.0, 110.0, 8.0, 0.7, 70.0, 2.0, 1.5]
lb = [25.0, 50.0, 0.0, 0.3, 40.0, -6.0, 0.3]
ub = [70.0, 300.0, 18.0, 2.0, 200.0, 12.0, 5.0]
fit = least_squares(resid, x0, bounds=(lb, ub))
x = fit.x
SOS = eq_sos(x)
g_bq = np.abs(bm.sos_response(SOS, F, FS_DSP))
err = 20 * np.log10(g_bq) - g_ideal_db
chk = (F >= 40) & (F <= 1000)
bq_err_max = float(np.max(np.abs(err[chk])))
biquads = [dict(type="highpass (BW4 stage 1)", fc_hz=x[0], q=0.5412, gain_db=0.0),
           dict(type="highpass (BW4 stage 2)", fc_hz=x[0], q=1.3066, gain_db=0.0),
           dict(type="low shelf", fc_hz=x[1], q=x[3], gain_db=x[2]),
           dict(type="peaking", fc_hz=x[4], q=x[6], gain_db=x[5])]
for b_ in biquads:
    print("  {type:24s} fc {fc_hz:6.1f} Hz  Q {q:.3f}  gain {gain_db:+.2f} dB".format(**b_))
print(f"  max |biquad - ideal| 40 Hz-1 kHz: {bq_err_max:.2f} dB")
# realised response and limits with the implementable (biquad) EQ
r_bq = np.abs(s["p_hs"]) * g_bq / fin["href"]
rbq_db = 20 * np.log10(r_bq)
f3_bq, f6_bq = bm.f_at_level(F, rbq_db, 0, 3), bm.f_at_level(F, rbq_db, 0, 6)
pink_bq, lim_bq, pw_bq, cand_bq = bm.pink_estimate(F, s, W, P, g_bq, fin["href"], crest=CREST, fx=FX)
boost_bq = float(20 * np.log10(g_bq[BAND].max()))
print(f"  realised with biquads: F3 {f3_bq:.1f} Hz, F6 {f6_bq:.1f} Hz, max boost {boost_bq:.1f} dB, "
      f"pink {pink_bq:.2f} dB ({lim_bq}), woofer avg {pw_bq:.2f} W")
battery_w = 2 * pw_bq * 1.1 / 0.75 + 2.0
# sine ceiling with biquad EQ
p_pb = fin["v_allow"][BAND] * fin["href"] / g_bq[BAND]
kc = int(np.argmin(p_pb))
ceiling_bq, ceiling_f_bq = float(bm.spl_pk(p_pb[kc])), float(F[BAND][kc])
v_ceiling = p_pb[kc] / fin["href"] * g_bq            # peak volts per frequency at the ceiling level (sine)

# ============================================================================ 4. what-ifs
print("\n=== What-ifs (PR mass re-optimised for each) ===")
WHATIF = [
    ("baseline (0.82 L, QL 10, empty)", dict()),
    ("0.85 L (CAD nominal)", dict(vb=VB_NOM)),
    ("leaky box QL 5", dict(ql=5.0)),
    ("tight box QL 20", dict(ql=20.0)),
    ("polyfill light: Vb x1.10, QA 30", dict(vb_factor=1.10, qa=30.0)),
    ("polyfill heavy: Vb x1.20, QA 10", dict(vb_factor=1.20, qa=10.0)),
    ("zeolite x1.3 (QA 30)", dict(vb_factor=1.3, qa=30.0)),
    ("zeolite x1.5 (QA 30)", dict(vb_factor=1.5, qa=30.0)),
    ("zeolite x2.0 (QA 30)", dict(vb_factor=2.0, qa=30.0)),
    ("limiter 17.1 V (BTL clip, 18 V PVDD)", dict(v_max=17.1)),
]
whatif_rows = []
for lab, kw in WHATIF:
    vb = kw.pop("vb", VB_FINAL)
    bst, _ = optimise_mass(vb, **kw)
    at_chosen = evaluate(vb, M_CHOSEN, **kw)
    row = dict(case=lab, vb_l=vb * 1e3, vb_factor=kw.get("vb_factor", 1.0), ql=kw.get("ql", QL), qa=kw.get("qa", QA),
               v_max=kw.get("v_max", bm.V_PK_MAX),
               best_m_add_g=bst["m_add"] * 1e3, best_pink_db=bst["pink"], best_pink_limit=bst["pink_lim"],
               best_fb_hz=bst["sys"]["fb"], best_max_boost_db=bst["max_boost_db"], best_f3_nat=bst["f3_nat"],
               pink_at_3p5g_db=at_chosen["pink"], fb_at_3p5g_hz=at_chosen["sys"]["fb"],
               maxspl50_at_3p5g=float(np.interp(50, F, at_chosen["maxspl"])),
               maxspl63_at_3p5g=float(np.interp(63, F, at_chosen["maxspl"])),
               f3_nat_at_3p5g=at_chosen["f3_nat"], boost_at_3p5g=at_chosen["max_boost_db"])
    row["_curve"] = at_chosen
    whatif_rows.append(row)
    print(f"  {lab:38s} best m {row['best_m_add_g']:5.2f} g pink {row['best_pink_db']:.2f} ({row['best_pink_limit']}); "
          f"@3.5 g pink {row['pink_at_3p5g_db']:.2f} fb {row['fb_at_3p5g_hz']:.1f} max63 {row['maxspl63_at_3p5g']:.1f}")

# ============================================================================ 5. figures + data
FMT = dict(xlim=(15, 2000))


def logx(ax, lo=15, hi=2000):
    ax.set_xscale("log")
    t = [v for v in (10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000) if lo <= v <= hi]
    ax.set_xticks(t)
    ax.set_xticklabels([f"{v // 1000}k" if v >= 1000 else str(v) for v in t])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Frequency (Hz)")


fb, fp = s["fb"], s["fp"]
V283 = 2.83 * np.sqrt(2)          # 2.83 V rms -> peak
cols = plt.rcParams["axes.prop_cycle"].by_key()["color"]

# --- Fig 1: SPL (half space, 1 m), contributions
spl283 = bm.spl_pk(s["p_hs"] * V283)
spl_w = bm.spl_pk(1.20 * 1j * 2 * np.pi * F * 2 * W["sd_m2"] * s["v_d"] * V283 / (2 * np.pi))
spl_p = bm.spl_pk(1.20 * 1j * 2 * np.pi * F * 2 * P["sd_m2"] * s["v_p"] * V283 / (2 * np.pi))
spl_full = bm.spl_pk(s["p_hs"] * bm.amp_vlimit(s))
spl_eq_full = bm.spl_pk(s["p_hs"] * v_ceiling)
fig, ax = plt.subplots()
ax.plot(F, spl_full, color=cols[0], label="15.5 V peak on each woofer, no EQ")
ax.plot(F, spl283, color=cols[1], label="2.83 V rms on each woofer, no EQ")
ax.plot(F, spl_w, ":", color=cols[1], lw=1.1, label="  woofers only (2.83 V)")
ax.plot(F, spl_p, "--", color=cols[1], lw=1.1, label="  passive radiators only (2.83 V)")
ax.plot(F, spl_eq_full, color=cols[2], label="with bass EQ, max. clean sine level")
for fx_, lab, yt in ((fb, "$f_b$", 56), (fp, "$f_p$", 52)):
    ax.axvline(fx_, color="0.5", lw=0.8, ls="-.")
    ax.text(fx_ * 1.03, yt, f"{lab} = {fx_:.0f} Hz", fontsize=8, color="0.3")
logx(ax)
ax.set_ylim(50, 105)
ax.set_ylabel("SPL at 1 m, half space (dB re 20 µPa)")
ax.legend(loc="lower right", fontsize=8)
common.savefig(fig, "a1_spl_halfspace_1m")
plt.close(fig)
common.save_csv("a1_spl_halfspace_1m.csv",
                ["f_hz", "spl_15v5pk_noeq_db", "spl_2v83rms_db", "spl_woofers_only_2v83_db", "spl_prs_only_2v83_db",
                 "spl_eq_max_sine_db"], [F, spl_full, spl283, spl_w, spl_p, spl_eq_full])

# --- Fig 2: excursion vs Xmax
xd_full = np.abs(s["x_d"]) * bm.amp_vlimit(s) * 1e3
xp_full = np.abs(s["x_p"]) * bm.amp_vlimit(s) * 1e3
xd_eq = np.abs(s["x_d"]) * v_ceiling * 1e3
xp_eq = np.abs(s["x_p"]) * v_ceiling * 1e3
fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.2), sharey=True)
for ax, xd_, xp_, title in ((axs[0], xd_full, xp_full, "(a) 15.5 V peak sine, no EQ"),
                            (axs[1], xd_eq, xp_eq, f"(b) bass EQ at max. clean level ({ceiling_bq:.0f} dB)")):
    ax.plot(F, xd_, color=cols[0], label="woofer")
    ax.plot(F, xp_, color=cols[1], label="passive radiator")
    ax.axhline(W["xmax_m"] * 1e3, color=cols[0], ls="--", lw=1)
    ax.axhline(P["xlim_model_m"] * 1e3, color=cols[1], ls="--", lw=1)
    ax.text(16, W["xmax_m"] * 1e3 + 0.15, "woofer Xmax 3.5 mm", fontsize=7.5, color=cols[0])
    ax.text(16, P["xlim_model_m"] * 1e3 + 0.15, "PR usable limit 5 mm", fontsize=7.5, color=cols[1])
    logx(ax, 15, 1000)
    ax.set_title(title, fontsize=9)
axs[0].set_ylim(0, 12)
axs[0].set_ylabel("Peak excursion (mm)")
axs[0].legend(loc="upper right", fontsize=8)
common.savefig(fig, "a1_excursion_vs_xmax")
plt.close(fig)
common.save_csv("a1_excursion_vs_xmax.csv",
                ["f_hz", "xd_15v5_noeq_mm", "xp_15v5_noeq_mm", "xd_eq_ceiling_mm", "xp_eq_ceiling_mm", "v_ceiling_pk"],
                [F, xd_full, xp_full, xd_eq, xp_eq, v_ceiling])

# --- Fig 3: impedance
zin = s["zin"]
fig, ax = plt.subplots()
ax.plot(F, np.abs(zin), color=cols[0], label="|Z| (one woofer, in box)")
ax.set_ylabel("|Z| (Ω)")
ax2 = ax.twinx()
ax2.plot(F, np.degrees(np.angle(zin)), color=cols[1], lw=1.1, label="phase")
ax2.set_ylabel("Phase (degrees)")
ax2.set_ylim(-90, 90)
ax2.grid(False)
ax2.spines["right"].set_visible(True)
for fx_, lab, yt in ((fb, "$f_b$", 24), (fp, "$f_p$", 20)):
    ax.axvline(fx_, color="0.5", lw=0.8, ls="-.")
    ax.text(fx_ * 1.03, yt, f"{lab} {fx_:.0f} Hz", fontsize=8, color="0.3")
logx(ax, 10, 20000)
ax.set_ylim(0, 1.05 * float(np.max(np.abs(zin[F < 1000]))))
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left")
common.savefig(fig, "a1_impedance")
plt.close(fig)
common.save_csv("a1_impedance.csv", ["f_hz", "z_mag_ohm", "z_phase_deg", "z_re", "z_im"],
                [F, np.abs(zin), np.degrees(np.angle(zin)), zin.real, zin.imag])

# --- Fig 4: max SPL vs frequency with limiting mechanism
fig, ax = plt.subplots()
mech_cols = {"amp V": cols[0], "amp I": cols[4], "woofer Xmax": cols[1], "PR Xmax": cols[3]}
sel = F <= 2000
ms = fin["maxspl"]
for name, colr in mech_cols.items():
    m = (fin["which"] == name) & sel
    if m.any():
        y = np.where(m, ms, np.nan)
        ax.plot(F, y, color=colr, lw=2.4, label=f"sine max, limited by {name}")
ax.plot(F[sel], ms[sel], color="0.6", lw=0.6, zorder=0)
ax.plot(F, ceiling_bq + 20 * np.log10(r_bq), "--", color=cols[2], lw=1.2,
        label=f"with bass EQ: max. clean sine {ceiling_bq:.1f} dB")
ax.axhline(pink_bq, color="k", lw=1.0, ls=":")
ax.text(210, pink_bq - 2.2, f"pink-noise estimate {pink_bq:.1f} dB\n(limited by {lim_bq}; requirement 90 dB)", fontsize=8)
logx(ax)
ax.set_ylim(60, 110)
ax.set_ylabel("Max SPL at 1 m, half space (dB)")
ax.legend(loc="lower right", fontsize=8)
common.savefig(fig, "a1_max_spl_vs_frequency")
plt.close(fig)
mech_code = np.array([list(mech_cols).index(wh) for wh in fin["which"]])
common.save_csv("a1_max_spl_vs_frequency.csv", ["f_hz", "max_sine_spl_db", "limit_code_0ampV_1ampI_2wooferX_3PRX",
                                                "eq_ceiling_curve_db"],
                [F, ms, mech_code, ceiling_bq + 20 * np.log10(r_bq)])

# --- Fig 5: DSP bass EQ
nat_rel = bm.spl_pk(s["p_hs"]) - bm.spl_pk(fin["href"])
tgt_db = 20 * np.log10(bm.dsp_target(F, F3_TARGET))
fig, axs = plt.subplots(2, 1, figsize=(6.5, 5.2), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.2]))
ax = axs[0]
ax.plot(F, nat_rel, color=cols[6], label=f"natural response (F3 {fin['f3_nat']:.0f} Hz)")
ax.plot(F, tgt_db, ":", color="k", lw=1.2, label="target: BW4 63 Hz × BW2 subsonic 28 Hz")
ax.plot(F, g_ideal_db, color=cols[1], lw=1.2, label="ideal EQ gain")
ax.plot(F, 20 * np.log10(g_bq), "--", color=cols[3], lw=1.4, label="biquad EQ (4 biquads, 48 kHz)")
ax.plot(F, rbq_db, color=cols[0], lw=2.0, label=f"realised: F3 {f3_bq:.0f} Hz, F6 {f6_bq:.0f} Hz")
ax.axhline(-3, color="0.6", lw=0.6)
ax.set_ylim(-30, 15)
ax.set_ylabel("Level re passband (dB)")
ax.legend(loc="lower right", fontsize=8)
txt = "\n".join(f"{b_['type'].split(' (')[0]}: {b_['fc_hz']:.0f} Hz, Q {b_['q']:.2f}"
                + (f", {b_['gain_db']:+.1f} dB" if b_['gain_db'] else "") for b_ in biquads[1:])
txt = f"highpass ×2 (BW4): {x[0]:.0f} Hz\n" + "\n".join(txt.split("\n")[1:])
ax.text(0.02, 0.97, txt, transform=ax.transAxes, va="top", fontsize=7.5, family="monospace")
axs[1].plot(F, err, color=cols[3])
axs[1].axhspan(-1, 1, color="0.9")
axs[1].set_ylim(-3, 3)
axs[1].set_ylabel("Biquad − ideal (dB)")
logx(axs[1])
common.savefig(fig, "a1_dsp_bass_eq")
plt.close(fig)
common.save_csv("a1_dsp_bass_eq.csv", ["f_hz", "natural_rel_db", "target_db", "eq_ideal_db", "eq_biquad_db",
                                       "realised_biquad_db", "biquad_minus_ideal_db"],
                [F, nat_rel, tgt_db, g_ideal_db, 20 * np.log10(g_bq), rbq_db, err])

# --- Fig 6: add-mass family
masses_show = [0.0, 2.0, 3.5, 6.0, 10.0, 16.0]
fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.2))
cm = plt.get_cmap("viridis")
fam_cols = [F]
fam_hdr = ["f_hz"]
for i, mg in enumerate(masses_show):
    rr = bm.system(F, W, P, VB_FINAL, mg * 1e-3, ql=QL, qa=QA)
    y = bm.spl_pk(rr["p_hs"] * V283)
    axs[0].plot(F, y, color=cm(i / (len(masses_show) - 1)), lw=1.8 if mg == 3.5 else 1.0,
                label=f"{mg:g} g (fb {rr['fb']:.0f} Hz)")
    fam_cols.append(y)
    fam_hdr.append(f"spl_2v83_madd_{mg:g}g_db")
logx(axs[0], 20, 500)
axs[0].set_ylim(55, 95)
axs[0].set_ylabel("SPL at 2.83 V, 1 m, half space (dB)")
axs[0].legend(fontsize=7, title="added mass per PR", title_fontsize=7.5, loc="lower right")
mgs = np.array([r["m_add"] for r in all82]) * 1e3
axs[1].plot(mgs, [r["pink"] for r in all82], color="k", lw=2, label="pink-noise max (binding)")
for key, colr in (("amp V", cols[0]), ("woofer Xmax", cols[1]), ("PR Xmax", cols[3])):
    axs[1].plot(mgs, [r["cand"][key] for r in all82], "--", color=colr, lw=1.1, label=f"{key} limit")
axs[1].axvline(M_CHOSEN * 1e3, color="0.4", lw=0.8)
axs[1].axhline(PINK_REQ, color="0.6", lw=0.8, ls=":")
axs[1].set_ylim(85, 95)
axs[1].set_xlabel("Added mass per PR (g)")
axs[1].set_ylabel("Pink-noise SPL, 1 m half space (dB)")
axs[1].legend(fontsize=7, loc="lower right")
fig.tight_layout()
common.savefig(fig, "a1_pr_mass_sweep")
plt.close(fig)
common.save_csv("a1_pr_mass_family.csv", fam_hdr, fam_cols)
common.save_csv("a1_pr_mass_sweep.csv", ["m_add_g", "fb_hz", "fp_hz", "pink_db", "ampV_db", "wooferXmax_db", "PRXmax_db",
                                         "f3_natural_hz", "max_eq_boost_db"],
                [mgs, [r["sys"]["fb"] for r in all82], [r["sys"]["fp"] for r in all82], [r["pink"] for r in all82],
                 [r["cand"]["amp V"] for r in all82], [r["cand"]["woofer Xmax"] for r in all82],
                 [r["cand"]["PR Xmax"] for r in all82], [r["f3_nat"] for r in all82], [r["max_boost_db"] for r in all82]])

# --- Fig 7: what-ifs
fig, axs = plt.subplots(1, 2, figsize=(6.5, 3.4), gridspec_kw=dict(width_ratios=[1.2, 1]))
show = [0, 2, 4, 5, 6, 8]
wcols = [cols[0], cols[6], cols[1], cols[4], cols[2], cols[3]]
wi_cols, wi_hdr = [F], ["f_hz"]
for j, i in enumerate(show):
    rr = whatif_rows[i]["_curve"]
    y = bm.spl_pk(rr["sys"]["p_hs"] * V283)
    axs[0].plot(F, y, color=wcols[j], lw=1.8 if i == 0 else 1.1, label=whatif_rows[i]["case"])
    wi_cols.append(y)
    wi_hdr.append("spl_2v83_" + "".join(ch if ch.isalnum() else "_" for ch in whatif_rows[i]["case"]))
logx(axs[0], 20, 500)
axs[0].set_ylim(55, 95)
axs[0].set_ylabel("SPL at 2.83 V, PR 3.5 g (dB)")
axs[0].legend(fontsize=6.5, loc="upper left")
labels = [r["case"] for r in whatif_rows]
vals = [r["best_pink_db"] for r in whatif_rows]
yy = np.arange(len(labels))[::-1]
axs[1].barh(yy, np.array(vals) - 85, left=85, color=[cols[0] if v >= PINK_REQ else cols[1] for v in vals])
for y_, v, r in zip(yy, vals, whatif_rows):
    axs[1].text(v + 0.1, y_, f"{v:.1f} ({r['best_pink_limit']}, {r['best_m_add_g']:.1f} g)", va="center", fontsize=6.5)
axs[1].axvline(PINK_REQ, color="k", lw=0.8, ls=":")
axs[1].set_yticks(yy)
axs[1].set_yticklabels(labels, fontsize=6.5)
axs[1].set_xlim(85, 96)
axs[1].set_xlabel("Pink-noise max (dB), PR mass re-optimised")
fig.tight_layout()
common.savefig(fig, "a1_whatif_volume_fill_zeolite")
plt.close(fig)
common.save_csv("a1_whatif_responses.csv", wi_hdr, wi_cols)

# --- Fig 8: electroacPy cross-check
fig, axs = plt.subplots(1, 3, figsize=(6.5, 2.7))
db = lambda q: 20 * np.log10(np.abs(q))
axs[0].plot(ea["f"], bm.spl_pk(ea["p_ea"] * V283), color=cols[1], lw=3, alpha=0.5, label="electroacPy")
axs[0].plot(ea["f"], bm.spl_pk(ea["p"] * V283), "--", color=cols[0], lw=1.2, label="this model")
axs[0].plot(ea["f"], bm.spl_pk(ea["p_rad"] * V283), ":", color="k", lw=1.0, label="this model + air load")
axs[0].set_ylabel("SPL 2.83 V (dB)")
axs[0].set_ylim(55, 95)
axs[1].plot(ea["f"], np.abs(ea["zin_ea"]), color=cols[1], lw=3, alpha=0.5)
axs[1].plot(ea["f"], np.abs(ea["zin"]), "--", color=cols[0], lw=1.2)
axs[1].set_ylabel("|Z| one woofer (Ω)")
axs[2].plot(ea["f"], np.abs(ea["xd_ea"]) * 1e3 * V283, color=cols[1], lw=3, alpha=0.5)
axs[2].plot(ea["f"], np.abs(ea["xd"]) * 1e3 * V283, "--", color=cols[0], lw=1.2)
axs[2].plot(ea["f"], np.abs(ea["xp_ea"]) * 1e3 * V283, color=cols[3], lw=3, alpha=0.5)
axs[2].plot(ea["f"], np.abs(ea["xp"]) * 1e3 * V283, "--", color=cols[2], lw=1.2)
axs[2].text(17, 2.3, "PR", fontsize=8, color=cols[3])
axs[2].text(100, 0.35, "woofer", fontsize=8, color=cols[1])
axs[2].set_ylabel("Excursion 2.83 V (mm)")
for a_ in axs:
    logx(a_, 15, 2000)
    a_.set_xticks([20, 100, 1000])
    a_.set_xticklabels(["20", "100", "1k"])
axs[0].legend(fontsize=6.5, loc="lower right")
fig.tight_layout()
common.savefig(fig, "a1_electroacpy_crosscheck")
plt.close(fig)
common.save_csv("a1_electroacpy_crosscheck.csv",
                ["f_hz", "spl_ea_2v83_db", "spl_ours_2v83_db", "spl_ours_airload_2v83_db", "zmag_ea", "zmag_ours",
                 "xd_ea_mm_2v83", "xd_ours_mm_2v83", "xp_ea_mm_2v83", "xp_ours_mm_2v83"],
                [ea["f"], bm.spl_pk(ea["p_ea"] * V283), bm.spl_pk(ea["p"] * V283), bm.spl_pk(ea["p_rad"] * V283),
                 np.abs(ea["zin_ea"]), np.abs(ea["zin"]), np.abs(ea["xd_ea"]) * 1e3 * V283, np.abs(ea["xd"]) * 1e3 * V283,
                 np.abs(ea["xp_ea"]) * 1e3 * V283, np.abs(ea["xp"]) * 1e3 * V283])

# ============================================================================ 6. machine-readable outputs
common.save_csv("a1_bass_transfer.csv", ["f_hz", "vd_re", "vd_im", "vp_re", "vp_im", "zin_re", "zin_im", "eq_gain_db"],
                [F, s["v_d"].real, s["v_d"].imag, s["v_p"].real, s["v_p"].imag, zin.real, zin.imag, 20 * np.log10(g_bq)])


def at(arr, fq):
    return float(np.interp(np.log(fq), np.log(F), arr))


summary = dict(
    question="PR mass, max SPL, DSP bass EQ for 2x ND65-8 + 2x DMA58-PR in the 0.82-0.85 L capsule on an 18 V TAS5805M",
    assumptions=dict(
        drivers="ND65-8 (woofer) and DMA58-PR, T/S from research/drivers.json (vendor data, Rms from Qms)",
        vb_final_l=VB_FINAL * 1e3, vb_cad_l=VB_NOM * 1e3, ql=QL, qa=QA, crest_factor=CREST,
        amp=f"TAS5805M BTL, PVDD {bm.PVDD} V, woofer limiter {bm.V_PK_MAX} V peak, current limit {bm.I_PK_MAX} A peak",
        radiation="half space (2 pi), 1 m, monopole sum of woofers and PRs (valid below ~300 Hz); "
                  "no radiation impedance added (published Mms includes the air load)",
        voice_coil="Re + j w Le (plain inductor, Le 0.61 mH); no semi-inductance data published",
        pr_usable_excursion_mm=P["xlim_model_m"] * 1e3, woofer_xmax_mm=W["xmax_m"] * 1e3,
        target=f"BW4 high-pass at {F3_TARGET} Hz x BW2 subsonic at {0.45*F3_TARGET:.1f} Hz; boost cap {MAX_BOOST_DB} dB; "
               "EQ rolls off 24 dB/oct below 47 Hz",
        both_woofers_same_signal="bass treated as mono (same voltage on both woofers); stereo programme differs",
    ),
    validation=val,
    chosen=dict(vb_l=VB_FINAL * 1e3, m_add_g_per_pr=M_CHOSEN * 1e3, fb_hz=fb, fp_hz=fp, fc_sealed_equiv_hz=s["fc"],
                f3_natural_hz=fin["f3_nat"], f6_natural_hz=fin["f6_nat"],
                f3_eq_ideal_hz=fin["f3_eq"], f6_eq_ideal_hz=fin["f6_eq"], f3_eq_biquad_hz=f3_bq, f6_eq_biquad_hz=f6_bq,
                max_eq_boost_db_biquad=boost_bq, max_eq_boost_db_ideal=fin["max_boost_db"],
                sensitivity_2v83_db_400hz=at(spl283, 400),
                pink_db=pink_bq, pink_limit=lim_bq, pink_limit_candidates_db=cand_bq,
                woofer_avg_power_w_at_pink=pw_bq, battery_avg_w_est=battery_w,
                eq_sine_ceiling_db=ceiling_bq, eq_sine_ceiling_set_at_hz=ceiling_f_bq,
                sine_max_spl_db={str(fq): at(ms, fq) for fq in (40, 50, 63, 80, 100, 150, 200, 400)},
                sine_limit_at={str(fq): str(fin["which"][np.argmin(np.abs(F - fq))]) for fq in (40, 50, 63, 80, 100, 150, 200, 400)},
                zmin_ohm=float(np.min(np.abs(zin[F < 1000]))), z_at_fb_ohm=at(np.abs(zin), fb),
                pr_mass_optimum_g=best82["m_add"] * 1e3, pr_mass_optimum_pink_db=best82["pink"]),
    nominal_0p85L=dict(fb_hz=nom["sys"]["fb"], pink_db=nom["pink"], pink_limit=nom["pink_lim"],
                       f3_natural_hz=nom["f3_nat"], max_eq_boost_db=nom["max_boost_db"]),
    biquads_fs48k=biquads, biquad_max_error_db_40_1000hz=bq_err_max,
    biquad_sos_fs48k=SOS.tolist(),
    whatif=[{k: v for k, v in r.items() if not k.startswith("_")} for r in whatif_rows],
    runtime_s=time.time() - T0,
)
common.save_json(summary, "a1_bass_summary.json")
print(f"\nbattery estimate at pink limit: {battery_w:.1f} W; runtime {time.time()-T0:.0f} s")
