# SPICE and PDN simulations (S1–S7)

Pre-layout circuit simulations of the speaker main board, run against `docs/spec_power.md` and `docs/spec_signal.md` (v1.0/v1.1, 2026-11-24). Each section states the question, inputs, method, assumptions, how the model was validated, the results, the figures and a few plain-English talking points.

**Reproduce:** `./run_all.sh` (everything; the TI switching runs take ~0.5–1.5 h each, one at a time) or `./run_all.sh --fast` (skips them and keeps their CSV/JSON results). Tools: ngspice-47 (Homebrew) and the project venv (numpy, scipy, matplotlib). Figures use `sim/paper.mplstyle`.

| Path | Contents |
|---|---|
| `common.py` | ngspice runner, raw-file reader, CSV/JSON writers, MLCC DC-bias model |
| `s1_boost_switching.py`, `s1_boost_loop.py` | S1: TPS61178 switching model (TI), averaged loop model |
| `s2_classd_filter.py` | S2: TAS5805M output LC filter |
| `s3_ntc.py` | S3: BQ25792 TS / NTC window |
| `s4_pvdd_trim.py` | S4: PVDD_TRIM injection network |
| `s5_esp32_reset.py` | S5: ESP32 EN RC and DTR/RTS auto-reset |
| `ffc_field.py`, `s6_ffc_si.py` | S6: 2-D field solver and FFC signal integrity |
| `../pdn/pdn_lib.py`, `../pdn/pdn_rails.py` | S7: reusable PDN library and the 3V3/PVDD rails |
| `models/TPS61178_TRANS.LIB` | TI's unencrypted PSpice transient model (SLVMC02A), unmodified |
| `netlists/`, `ti_runs/` | generated netlists and logs (raw files are deleted after parsing; `ti_runs/*.cir` are the exact TI-model netlists) |
| `results/`, `../pdn/results/` | CSV/JSON behind every figure |
| `../../docs/figures/spice/`, `../../docs/figures/pdn/` | figures, PDF + PNG |

**Vendor models.** TI publishes an *unencrypted* PSpice transient model of the TPS61178 (SLVMC02A). It runs in ngspice with `set ngbehavior=psa` (`ti_runs/.spiceinit`), and S1 uses it as-is. No unencrypted Sunlord/Changjiang inductor or Murata/Samsung MLCC SPICE models usable in ngspice were found. Inductors are therefore modelled as L + DCR from the datasheet. MLCC DC-bias derating uses an empirical `C(V) = C0 / (1 + (V/V50)^1.2)` model fitted to published curve points (see `common.mlcc_cap_dc_bias`; e.g. 10 µF/50 V/1206 → 4.5 µF at 18 V). Replace this table with exported vendor curves once the exact part numbers are fixed.

**ngspice notes.**
- ngspice-47 writes a corrupt binary raw file when `.options interp` is combined with `uic`. The TI runs use a `.control` block with `linearize` + `write` instead.
- Ideal `T` lines failed with "timestep too small" at sharp edges, so S6 uses 40-section LC ladders.
- The TI model needs trapezoidal integration with reltol 2e-3. Gear, or a tighter reltol, stalled at the soft-start/PFM transitions.

---

## S1. TPS61178 boost, VSYS 6.0–8.4 V → PVDD 18 V

**Questions.** Is the loop with Rc/Cc/Cp = 33 k/47 nF/10 pF stable across input voltage, load and bulk capacitance? How large is the dip for a 0.2 → 2 A load step? Does start-up from a ~7 V pre-bias into ~1.5 mF really take "≈9 ms, no hiccup"?

**Inputs.**
- L = 2.2 µH (7 mΩ DCR), fsw = 599 kHz, ILIM via 82 kΩ.
- Divider 300 k / (24 k ∥ 200 k).
- PVDD bank: 16 × 10 µF/50 V (4.5 µF each at 18 V, 72 µF total) plus 3 × 470 µF/35 V electrolytics (ESR 0.15 Ω assumed, swept 0.05–0.34 Ω) = 1.48 mF.
- VSYS source: 30 mΩ plus 2 × 22 µF.

**Method.**
1. **Averaged model** (`s1_boost_loop.py`), from the datasheet's peak-current-mode equations 15–25, generalised to any output network:
   `T = Gm(1−D)(1−s/ωRHP)·He(s)·Zo(s)·kFB·GEA·Zcomp(s)`, with Gm = 12 A/V, GEA = 195 µS, REA = 20 MΩ and Ridley's sampling term He(s).
   - Slope compensation is **extracted from the TI model**, because the datasheet's eq. 21 is typeset wrongly: Se = 2.76 A/µs vs Sn = 3.36 A/µs at 7.4 V, so mc = 1.82. The TI model also supplies the 70 pF internal COMP capacitance.
   - Three load models: resistive (the datasheet convention), constant current, and constant power (−R incremental, as a class-D amp behaves at low frequency).
   - Sweep: VSYS 6.0/7.4/8.4 V × Iout 0.2/0.5/1/2.5 A × 0–3 electrolytics × ESR.
2. **Switching model** (`s1_boost_switching.py`), using TI's transient model, which includes pre-charge, soft start, cycle-by-cycle and short (hiccup) limits, OVP, pre-bias and PFM.
   - Start-up from PVDD = VSYS − 0.5 V. ILIM(min) = 6.3 A is reproduced with RLIM = 118 k, since the model scales as 745 kΩ·A / R.
   - 0.2 → 2 → 0.2 A load steps, applied after the loop has settled (12 ms).
   - Middlebrook injection runs (series source in the FB sense line) were set up (`fra_*` in `runs()`), but they, and the 7.4 V load step with the spec compensation, stalled numerically in ngspice-47 and were dropped (they run only when named explicitly). The switching-model cross-check is the load step instead.

**Validation.**
- **Hand crossover.** fc ≈ Gm(1−D)·GEA·Rc·kFB / (2π·C) = 228 Hz at 7.4 V. The averaged model gives 247 Hz.
- **PVDD impedance peak.** Hand 1/(2π·fc·C) = 0.44 Ω; model 0.46 Ω.
- **Switching model.** The averaged model's step response (inverse FFT of Zo/(1+T)) is overlaid on the TI model in `s1_loadstep`. The shapes and time scales agree. The switching model dips ~1.6× deeper: 0.97 vs 0.62 V at 6 V/33 k, and 0.34 vs 0.21 V at 7.4 V/100 k. That difference is the large-signal effect the linear model leaves out: the EA output is slew-limited (±20 µA in TI's model) and the converter starts the step from PFM.

**Results.**

| Case (design bank, CCM loads) | fc | worst PM | worst GM |
|---|---|---|---|
| VSYS 6.0–8.4 V, 0.5–2.5 A, 1–3 electrolytics, ESR 0.05–0.34 Ω | 0.20–1.0 kHz | **64.8°** (constant-power load, 6 V, 2.5 A) | **22.3 dB** |
| Ceramics only (72 µF, not a production state) | 4.7 kHz | 88° | — |

- The RHP zero is ≥ 58 kHz (2.5 A, 6 V), so fc stays below fRHP/5 = 11.6 kHz.
- At 0.2 A, and at 0.5 A for VSYS ≥ 7.4 V, the converter is in DCM/PFM. The CCM model does not apply there; it is flagged `ccm=false` in `results/s1_loop_margins.csv`.

**The loop is stable, but slow.** With 1.48 mF, crossover is only ~250 Hz. The closed-loop PVDD impedance peaks at **0.46 Ω at ~150 Hz** (0.57 Ω at 6 V; see S7). That is exactly the band where bass draws its current.

**Load step 0.2 → 2 A (TI model):**

| Rc / Cc | VSYS | Dip | Overshoot on release | Ripple at 2 A |
|---|---|---|---|---|
| 33 k / 47 nF (spec) | 6.0 V | **0.97 V** | +1.25 V (PFM cannot sink current) | 97 mV p-p |
| 100 k / 15 nF (what-if) | 7.4 V | **0.34 V** | +0.34 V | 46 mV p-p |

The step needs a 0.3 V move on COMP. The EA output is limited to ±20 µA into 47 nF in the TI model, so the dip is partly slew-limited, which a linear model cannot show.

**Start-up (TI model, EN at t = 0, PVDD pre-biased at VSYS − 0.5 V, amps in PDN):**

| Corner | Time to 98 % of 18 V | Peak IL | Min PVDD after EN | Hiccup? | Final PVDD |
|---|---|---|---|---|---|
| 7.4 V, ILIM typ 9.1 A | 6.7 ms | 9.5 A | 7.2 V | no | **19.4 V** |
| 6.0 V, ILIM min 6.3 A | **11.2 ms** | 6.6 A | 5.78 V (threshold 5.39 V) | no | **21.0 V (OVP)** |
| 6.0 V, ILIM min, Rc/Cc 100 k/15 n | 11.1 ms | 6.6 A | 5.78 V | no | 21.0 V (OVP) |

- **"No hiccup" is confirmed**, but only just at 6.0 V: there is 0.39 V of margin to the 30 % short threshold.
- **The 9 ms figure is optimistic.** At 6 V and ILIM(min), the model runs ~2.5–4 µs periods in current limit (sub-harmonic at D ≈ 0.67). The average inductor current is then 3.3–3.9 A, not the 4.8 A the hand calculation assumed, so the ramp takes 11 ms. The spec's ≥ 20 ms BOOST_EN → PDN wait still covers this.
- **New finding: start-up overshoot.**
  - The internal soft-start reference finishes in 3.2 ms, while the 1.48 mF bank needs 7–11 ms at the current limit, so the error amplifier winds up. In the model, COMP reaches ~4.5 V against ~2.2 V in regulation.
  - When PVDD reaches 18 V, COMP has to slew back at 20 µA into Cc. PVDD keeps charging at the current limit for several ms and **overshoots to 19.4 V (typ) and to the 21 V OVP (worst case)**.
  - With no load (amps in PDN, PFM), PVDD stays there until the amps draw current.
  - Every part tolerates it: TAS5805M 26.4 V, capacitors 35/50 V. But PVDD is not 18 V when PDN is released.
  - A faster compensation does not fix it; the windup is set by the current limit and the soft-start time.
  - Fix, if wanted: fit the DNP trim (R907/D901). Drive PVDD_TRIM high (target ≈ 12.3 V) before BOOST_EN, then ramp the trim down over ~30–50 ms so the converter never enters current limit. Otherwise, accept it and bench-verify.

**Figures** (`docs/figures/spice/`):
- `s1_loop_bode`: Loop gain (magnitude/phase) for the 1.48 mF bank at VSYS 6.0/7.4/8.4 V and 0.5/2.5 A.
- `s1_loop_margins`: Worst phase margin and highest crossover versus PVDD capacitance, for resistive, constant-current and constant-power loads.
- `s1_compensation_options`: Rc sweep with Cc scaled for fz ≈ 103 Hz. Worst PM over the production states (left) and the peak PVDD impedance against the S7 target (right).
- `s1_loadstep`: PVDD dip for 0.2 → 2 A, averaged (linear) model vs TI switching model: spec compensation at 6 V, and Rc/Cc 100 k/15 n at 7.4 V.
- `s1_loadstep_switching`: PVDD and inductor current for the 0.2 → 2 → 0.2 A step (TI model).
- `s1_startup`: Start-up into 1.48 mF from a ~VSYS pre-bias: PVDD and inductor current (with 50 µs average) for the typical and worst corners.

**Data:** `results/s1_loop_margins.csv/json`, `s1_loop_bode.csv`, `s1_compensation_options.json`, `s1_startup.json`, `s1_start_*.csv`, `s1_step*.csv`, `s1_loadstep_switching.json`, `s1_loadstep_avg*.csv/json`.

**Talking points.**
- The vendor's own transient model, run in a free simulator, caught two things the datasheet equations hide: error-amplifier windup at start-up into a large bank, and slew-limited load steps.
- "Stable" is not the same as "good enough". The loop has 65° of margin everywhere, but with 1.5 mF its 250 Hz bandwidth leaves PVDD 3–4× too soft in the bass band.
- Raising Rc to 100 kΩ (Cc 15 nF) costs nothing. It cuts the load-step dip ~3× and keeps PM ≥ 79° in every production state.

---

## S2. TAS5805M output filter (BTL, 10 µH + 1 µF per leg, 768 kHz)

**Questions.** Frequency response into the real drivers vs 8 Ω/4 Ω resistors. Switching ripple for BD and Hybrid (1SPW) modulation. Peak inductor current vs Isat 5.5 A and OCP 5 A at the limiter ceilings.

**Inputs.**
- Per leg: RDS(on) 180 mΩ, L = 10 µH (68 mΩ, 2 pF), C = 1 µF X7R (0.75 µF at 9 V bias, 5 mΩ, 0.6 nH).
- Driver electrical models from `research/drivers.json` (free-air T/S): Re + Le + a motional parallel RLC.
  - ND65-8: Re 7.4 Ω, Le 0.61 mH, fs 102 Hz, Res 86 Ω.
  - OT19NC00-04: Re 3.17 Ω, Le 10 µH, fs 1029 Hz, Res 14.3 Ω.

**Method.** ngspice AC sweeps, and a transient with a behavioural PWM: a triangle carrier at 768 kHz compared in tanh-smoothed B-sources.
- BD: dP = ½ + m/2, dN = ½ − m/2.
- 1SPW, the low-power state of TI's "Hybrid": both legs at d0 = 0.14 idle duty, and one leg modulates.

**Assumptions and limits.**
- Pure Le, which overstates the woofer's HF impedance. Real voice coils are lossy (semi-inductive).
- In-box T/S shifts are ignored.
- Inductor saturation is not simulated. L at the peak current is estimated with a soft-saturation curve (−30 % at Isat).
- The 1SPW idle duty (0.14) is the spec's θ, not a TI-published number.

**Validation.**
- **Filter corner.** f0 = 50.3 kHz and Q = 0.63 (4 Ω) / 1.26 (8 Ω) from the hand formula; SPICE matches.
- **4 Ω at 20 kHz.** SPICE gives −1.36 dB vs −0.43 dB ideal. The difference is the 0.5 Ω RDS + DCR series loss: −1.0 dB broadband at 4 Ω, −0.5 dB at 8 Ω.
- **Idle ripple.** Hand BD idle ripple = 18 × 0.25 / (768 k × 10 µ) = 0.586 A p-p; SPICE 0.585 A. Hand 1SPW = 0.282 A; SPICE 0.282 A.

**Results.**
- **Tweeter channel.** Into the OT19NC00-04 model the response is −1.0 dB (series loss) at 2.5 kHz, −1.8 dB at 10 kHz and **−3.2 dB at 20 kHz**. That is about −2.2 dB of HF droop relative to 2.5 kHz, vs the spec's −0.44 dB estimate, which used 4 Ω and no series resistance.
  - **Spec issue (low):** the tweeter EQ should add a ~+2 dB shelf at 10–20 kHz, not +0.44 dB.
- **Woofer channel.** Flat to 10 kHz (−0.04 dB). The ND65-8's 0.61 mH Le leaves the LC almost unloaded above ~20 kHz, giving **+23 dB peaking at 59 kHz (Q ≈ 14)**. That is harmless because the channel is low-passed at 2.5 kHz. Any ultrasonic content (noise shaping, DSP aliasing) on channel A is amplified there, though.
- **Idle ripple.** Leg inductor ripple is 0.585 A p-p (BD) and 0.282 A p-p (1SPW). In BTL with both legs in phase, this is common-mode current through the filter caps. **The driver sees none of it** (zero ultrasonic current at idle).
  - With signal (4 V pk, 5 kHz), the ultrasonic tweeter current is 0.05 mA rms (BD) and 0.32 mA rms (1SPW), so < 1 µW in Re.
- **Peak inductor current at the limiter ceilings (BD):**

| Case | Speaker V pk | Speaker I pk | Inductor I pk | Margin to OCP 5 A |
|---|---|---|---|---|
| Woofer 15.5 V pk, 150 Hz (near fs) | 15.7 | 1.03 | 1.27 | 3.7 A |
| Woofer 15.5 V pk, 400 Hz (Z minimum) | 15.6 | 2.20 | **2.25** | 2.7 A |
| Woofer 15.5 V pk, 2.5 kHz | 15.5 | 1.37 | 1.51 | 3.5 A |
| Tweeter 8 V pk, 3 kHz | 8.2 | 2.46 | **2.69** | 2.3 A |
| Tweeter 8 V pk, 10 / 20 kHz | 7.5 / 6.4 | 2.39 / 1.90 | 2.60 / 2.06 | ≥ 2.4 A |
| Tweeter hard-clipped (limiter failed), 3 kHz | 16.5 | 5.39 | **5.41** | **−0.41 A** |

- With the limiters, peaks are ≤ 2.7 A (L ≥ 9.0 µH estimated), so both the 5 A OCP and the 80 % inductance rule are met.
- Without the tweeter limiter, the current exceeds OCP and reaches Isat. This confirms the spec's "mandatory tweeter limiter" (spec predicted 5.2 A).

**Figures:**
- `s2_filter_response`: Filter transfer into the driver models, 8 Ω, 4 Ω and open, with the driver impedance curves below.
- `s2_idle_ripple`: Idle inductor ripple and tweeter current for BD and 1SPW.
- `s2_inductor_peaks`: Inductor current over one signal period at the limiter ceilings and with a hard-clipped tweeter, against OCP and Isat.

**Data:** `results/s2_classd_filter.json`, `s2_filter_response.csv`, `s2_driver_impedance.csv`, `s2_idle_*.csv`, `s2_peak_*.csv`.

**Talking points.**
- A loudspeaker is not a resistor. The woofer's voice-coil inductance turns the "Q = 1.3" filter into a Q ≈ 14 resonance at 59 kHz, safely above the woofer's crossover.
- In a bridge-tied output the 0.6 A switching ripple circulates through the filter capacitors and never reaches the drivers.
- The tweeter limiter is not optional: one clipped 3 kHz tone pushes the inductor past the amplifier's 5 A trip point.

---

## S3. Battery NTC network (BQ25792 TS pin)

**Question.** With RT1 = 5.1 k, RT2 = 30 k and a 10 k NTC (B = 3435 or 3380), what charge temperature window results?

**Method.** ngspice `.dc temp` sweep with a behavioural β-model NTC `R25·exp(B(1/T − 1/298.15))`, cross-checked by the same formula in Python (difference 4e-14 %). TS is ratiometric to REGN, so REGN cancels. Thresholds come from the BQ25798 EC table (same comparator block as the BQ25792): VT1 73.3 %, VT5 34.2 %, TS_COOL 68.4 %, TS_WARM 44.8 % (POR defaults).

**Validation.** TI's reference network (5.24 k / 30.31 k, 103AT) recomputed with the β-model gives:

| Point | Model | Datasheet |
|---|---|---|
| 0 °C | 73.8 % | 73.3 % |
| 10 °C | 68.6 % | 68.4 % |
| 45 °C | 44.4 % | 44.8 % |
| 60 °C | 34.1 % | 34.2 % |

The β-model differs from a real R–T table by ≤ 1 °C at the cold end.

**Results.**

| | B = 3435 | B = 3380 |
|---|---|---|
| Cold stop (VT1) | **2.0 °C** (worst case −1.1…4.8 °C) | 1.6 °C |
| Cool (20 % ICHG) below | 11.2 °C | 11.0 °C |
| Warm (VREG − 400 mV) above | 45.3 °C | 45.6 °C |
| Hot stop (VT5) | **60.8 °C** (worst case 58.9…62.7 °C) | 61.5 °C |
| Open NTC | 85.5 % → reads "cold", charging suspended (fail-safe) | |

These match the spec's 2.0/60.8 °C.

**Observations (spec/firmware, low severity).**
- With POR JEITA defaults, the charger keeps charging at full ICHG (VREG − 400 mV) between 45 and 61 °C. Most device-grade pouch packs allow charging only up to 45 °C. Firmware should set **JEITA_ISETH = 0 (suspend) or TS_WARM = 0h (40 °C)** if the pack datasheet says so.
- TH801 sits on the board next to J801, so it measures board temperature, not cell temperature.

**Figure:** `s3_ntc_window`: TS/REGN vs temperature for both B values, with the JEITA thresholds (bands = min/max) and the allowed charge window.

**Data:** `results/s3_ntc.json`, `s3_ntc_ts_curve.csv`.

**Talking point.** Two resistors and a thermistor decide when a lithium pack may charge. The simulation reproduces TI's own reference numbers to within half a degree before trusting our values.

---

## S4. PVDD_TRIM network

**Questions.** What PVDD results from a given trim voltage or PWM duty? How much PWM ripple reaches FB? Is it true that the trim can only lower PVDD?

**Method.**
- The TPS61178 is replaced by an ideal regulator: a gm-C integrator that forces FB = 1.198 V with a ~250 Hz crossover, like S1.
- The network: R908/C917/R909/C918 (10 k/1 µF × 2) → D901 (1N4148W SPICE model) → R907 68 k → FB.
- DC sweep at 0/25/60 °C, and 20 kHz LEDC PWM transients (300 ms) at 50/75/100 % duty.

**Validation.** Compared with the spec's hand table (which assumed a fixed 0.45 V diode drop):

| Trim voltage | Spec | SPICE (25 °C) |
|---|---|---|
| 2.0 V | 16.8 V | 16.43 V |
| 2.5 V | 15.1 V | 14.84 V |
| 3.0 V | 13.4 V | 13.20 V |
| 3.3 V | 12.3 V | 12.20 V |

The offset is real physics: at 5–15 µA the 1N4148W drops ≈ 0.35 V, not 0.45 V. The knee is also soft; 1.6 V already gives 17.58 V, not 17.97 V.

**Results.**
- **Range.** 18.0 → 12.2 V over 1.5–3.3 V. Temperature drift ≈ −8.6 mV/°C on PVDD (spec: 7 mV/°C).
- **Ripple.** 20 kHz PWM ripple is ≈ 2.7 µV p-p at TRIM_RC and < 0.5 µV at FB, at the simulation noise floor. The spec's "≈ 2 µV" is confirmed.
- **Settling.** PVDD needs **70–110 ms** to settle to 90 % after a trim step (two 10 ms RC poles plus the diode knee). Firmware should allow ≥ 150 ms.
- **Resolution.** dPVDD/dVtrim = −3.4 V/V. An 8-bit DAC step (12.9 mV) is 44 mV of PVDD; a 10-bit LEDC step is ≈ 11 mV.
- **"Can only lower PVDD" is true for the drive, but not exactly true for leakage.**
  - With GPIO low or Hi-Z, the reverse-biased D901 leaks current *out of* FB, which raises PVDD by I_R × 300 kΩ.
  - From the 1N4148W limits (25 nA at 25 °C, 50 µA at 150 °C, both at 20 V; ≈ 1/3 at 1.2 V): +2 mV at 25 °C, +19 mV at 60 °C, +86 mV at 85 °C.
  - Harmless, since OVP is 20.5 V min, but the claim should read "can only lower PVDD, apart from < 0.1 V of diode leakage".
- A GPIO stuck high gives 11.6 V (12.2 V simulated); the amps still work.

**Figure:** `s4_pvdd_trim`: PVDD vs trim voltage at 0/25/60 °C with the spec table (left), and PVDD transients for 20 kHz PWM at three duties (right).

**Data:** `results/s4_pvdd_trim.json`, `s4_trim_dc.csv`, `s4_trim_pwm_d*.csv`.

**Talking point.** A diode-OR injection makes the safe direction the default. The simulation still found the two small ways reality differs from the hand calculation: the diode's real drop at microamps, and its leakage.

---

## S5. ESP32 boot / auto-reset

**Question.** During esptool's reset sequence through the CH340C and the 2-transistor network, is GPIO0 low while EN rises? Are the strapping levels right?

**Method.**
- ngspice transient of: R101/C103 (10 k/1 µF), Q201/Q202 (2N3904 model), R201/R202 10 k, R102 10 k plus the internal 45 k pull-up, and LED D101 + R103 on IO0.
- CH340C DTR#/RTS# are 3.3 V outputs with 150 Ω output resistance (assumed).
- esptool v4 sequences: `ClassicReset` (separate DTR and RTS USB requests, with a gap of 0–5 ms between them) and `UnixTightReset` (both lines in one call).
- Pass criterion: IO0 < 0.25 VDD while EN crosses the whole V_IL…V_IH band (0.825–2.475 V), plus the 1 ms strap hold time.

**Results.**
- **Gap tolerance.** Download mode is entered for the tight sequence and for gaps ≤ 2 ms. It **fails for gaps ≥ 3 ms**: during the gap both transistors are off and EN starts rising before IO0 is pulled low.
  - The sim's limit is ≈ 2.5 ms, slightly below the analytic 2.88 ms, because Q201 only pulls EN to 0.12 V.
  - Hold margin after EN reaches V_IH is ≥ 35 ms.
- **Power-up.** +3V3 ramps over 4.8 ms (TPS62933 soft start).
  - The CH340C's DTR# rises with +3V3 and forward-biases Q201's base–collector junction, so a second 10 k path charges C103 and roughly halves the EN delay.
  - EN reaches 0.825 V at 3.96 ms, **0.4 ms before VDD reaches 3.0 V**.
  - Only a chip whose real CHIP_PU threshold is near V_IL would see this; at V_IH, EN crosses at 9.7 ms. Low severity.
- **C103 = 2.2 µF fixes both:** EN crosses V_IL 1.1 ms after VDD = 3.0 V, and the esptool gap tolerance grows to 5 ms.
- **Strapping at reset** (internal pulls 20–80 kΩ, ±1 µA leakage):

| Pin | Level | Required | OK |
|---|---|---|---|
| GPIO0 | ≥ 3.29 V | 1 | ✓ |
| GPIO2 (BOOST_EN) | ≤ 0.04 V | 0 | ✓ |
| GPIO12 (AMP_PDN) | ≤ 0.04 V | 0 | ✓ |
| GPIO15 (LCD_DC) | ≥ 3.22 V | 1 | ✓ |
| GPIO5 (LCD_CS) | ≥ 3.22 V | 1 | ✓ |

**Figures:**
- `s5_autoreset`: DTR#/RTS#, EN and GPIO0 for the tight sequence and 2 ms / 5 ms gaps, with the EN threshold band shaded.
- `s5_powerup`: +3V3 soft start, EN (1 µF vs 2.2 µF) and GPIO0 at power-up.

**Data:** `results/s5_esp32_reset.json`, `s5_*.csv`.

**Talking point.** The classic two-transistor reset circuit works because a 10 ms RC delay hides the time between two USB commands. The simulation puts a number on that hiding time (≈ 2.5 ms) and shows a 2.2 µF capacitor doubling it.

---

## S6. Board-to-board signal integrity (200 mm, 1.0 mm-pitch, 20-way FFC)

**Questions.** What are the FFC's Z0 and delay with the spec's GND interleaving? What do SPI SCLK (40 MHz) and PDM_CLK (3.072 MHz) look like at the far end with the 33 Ω source resistors? What is the maximum safe SPI clock? How large is the crosstalk?

**Method.**
1. **2-D finite-difference field solver** (`ffc_field.py`) for the cable cross-section.
   - 20 zero-thickness strips 0.6 mm wide at 1.0 mm pitch, in a 0.12 mm PET film with εr = 3.2. GND strips held at 0 V; +3V3 strips are AC ground.
   - The far boundary is charge-free, so all return current flows in the cable's own GND strips.
   - Outputs: the Maxwell C matrix with and without dielectric, and L = μ0ε0·C_air⁻¹. Richardson extrapolation from 0.025/0.0125 mm grids.
   - Repeated with the cable lying 1 mm above a metal surface.
2. **ngspice chain:** ESP32 pad (ramp source with R_out) → series R → 40 mm main-board trace (50 Ω) → connector (2 nH/0.3 pF) → FFC (40-section LC ladder + 0.4 Ω conductor/skin loss) → connector → 25 mm UI trace (55 Ω) → 30 mm display-module wiring (70 Ω) → GC9A01 input (6 pF).
   - ESP32 corners from the datasheet IOH/IOL (drive strength 2 ≈ 20 mA): fast 20 Ω/0.6 ns, nominal 30 Ω/1.0 ns, slow 45 Ω/2 ns.
3. **Crosstalk:** a 4-conductor coupled ladder (SCLK, MOSI, CS, DC) with K-coupled inductors and mutual C from the solver matrices.

**Assumptions.**
- Conductor width, film thickness and εr are generic FFC values, not the JUSHUO C12151 drawing.
- Display-module wiring and receiver C are estimated.
- GC9A01 thresholds are 0.3/0.7 VDD, with ≥ 7 ns min high/low (ST7789-class value; check the GC9A01 datasheet).
- Pass criterion for "safe": no extra threshold crossings, high/low time ≥ 7 ns, over/undershoot < 0.9 V (ESD-clamp conduction).

**Validation.** Solver on an isolated G-S-G strip set (0.6/0.4/0.6 mm) in air:

| Grid | 0.05 mm | 0.025 mm | 0.0125 mm | Extrapolated | Conformal mapping (Ghione & Naldi) |
|---|---|---|---|---|---|
| Z0 | 135.1 Ω | 137.7 Ω | 139.0 Ω | **140.30 Ω** | **140.45 Ω** |

Error 0.1 %.

**Results.**
- **Line parameters** (free air / 1 mm above metal):

| Line | Z0 free air | Z0 over metal | εeff | Delay (200 mm) |
|---|---|---|---|---|
| SCLK (pin 5, GND both sides) | 107 Ω | 100 Ω | 1.54 | 0.83 ns |
| PDM_CLK (pin 12, GND both sides) | 108 Ω | | | |
| MOSI | 119 Ω | | | |
| CS, DC (signal neighbours) | 129 Ω | | | |

- **SCLK at 40 MHz with 33 Ω.** The driver (R_out 30 Ω + 33 Ω = 63 Ω) is well below Z0 ≈ 107 Ω, so the open-ended line rings.
  - Overshoot is **0.69 V (nominal) and 1.1 V (fast corner)** above 3.3 V, enough to conduct the receiver's ESD diodes.
  - Timing is fine: 11.9 ns high/low, no false threshold crossings.
- **Series-resistor sweep at 40 MHz (nominal driver):**

| Rs | 33 Ω | 47 Ω | 68 Ω | 82 Ω |
|---|---|---|---|---|
| Overshoot | 0.69 V | 0.33 V | 0.02 V | 0 V |
| High/low time | 11.9 ns | | 11.7 ns | 11.5 ns |

  With **68 Ω the fast corner overshoots only 0.2 V**.
- **Maximum safe SPI clock:** **53 MHz** in every corner with Rs = 68 Ω. With 33 Ω the fast corner fails on overshoot at any frequency. 80 MHz fails the 7 ns minimum high/low time. **40 MHz has margin with 68 Ω.**
- **MOSI eye at 40 Mb/s (PRBS7):** wide open with either resistor; ringing 0.84 V (33 Ω) vs 0.07 V (68 Ω).
- **PDM:**
  - 1.5 ns pad → mic and 1.6 ns mic → ESP32, so the **3.1 ns round trip** is ≪ the 163 ns half period. Timing is no issue.
  - PDM_CLK overshoots 0.8 V at the mic with 33 Ω; 68 Ω would clean it up.
- **Crosstalk (fast corner, 40 MHz aggressor, victims held low):**
  - SCLK, shielded by GND 4 and 6, couples ≤ 160 mV into MOSI/CS/DC at the far end.
  - **MOSI → CS 0.69 V and MOSI → DC 0.53 V** (adjacent, k_L = 0.43). That is below V_IL = 0.99 V, but with only 0.3 V of margin. With 68 Ω sources it falls to 0.49 V / 0.30 V, and SCLK's coupling to ≤ 83 mV.
  - CS and DC are static or sampled away from MOSI edges during a transfer, so this is acceptable. A GND between MOSI and CS would be better on a respin.

**Figures:**
- `s6_sclk_40MHz`: SCLK at the display for Rs = 33/47/68/82 Ω.
- `s6_mosi_eye`: MOSI eye at 40 Mb/s, 33 Ω vs 68 Ω.
- `s6_pdm`: PDM clock at the pad and the mic, and the returning data edge.
- `s6_crosstalk`: Far-end voltages on SCLK/CS/DC with MOSI toggling.

**Data:** `results/s6_ffc_si.json` (line parameters, sweeps, fmax table, crosstalk), `s6_ffc_LC.json` (full L/C matrices, reusable), `s6_*.csv`.

**Talking points.**
- A ribbon cable is a transmission line. With GND on both sides of the clock it is a ~107 Ω line, twice the impedance the "33 Ω for 50 Ω" rule of thumb assumes.
- Matching the source resistor to the cable (68 Ω) removes a volt of overshoot at no cost in speed. 53 MHz still works.
- A 200-line field solver, checked against a 1980s closed-form formula to 0.1 %, is enough to get these numbers before any hardware exists.

---

## S7. PDN, pre-layout (`sim/pdn/`)

**Questions.** What is the impedance of +3V3 and PVDD against target impedances derived from the real load-current steps?

**Method.** `pdn_lib.py` is a small nodal-analysis library.
- Elements: MLCCs (DC-bias-derated C, ESR, mounted ESL by case size), electrolytics, regulator output models, series copper segments.
- **+3V3:** TPS62933 modelled as a current-mode loop `T = (ωc/s)(1 + ωz/s)`, which gives the standard R ∥ L "VRM" branch.
  - fc = 35 kHz assumed (swept 20–60 kHz), fz = fc/5, on 34 µF.
  - The spec's capacitors at the ESP32, amps' DVDD, CH340C and the UI connector.
- **PVDD:** the regulator branch is the S1 closed-loop admittance minus the S1 capacitor admittance, so the boost loop enters exactly. It is combined with the full PVDD capacitor set.
- Placeholder copper (series R–L between the regulator and each load) is listed in the JSON. **After layout, replace it with extracted values via `Rail.series()` and re-run.**

**Targets.**
- **+3V3:** ΔI = 0.33 A (ESP32-WROVER-E 802.11b TX peak 350 mA, Table 16, from ~20 mA) and ΔV = 3 % → **0.30 Ω**.
- **PVDD:** ΔI = 5 A (two woofers at the 15.5 V pk ceiling, 2.2 A each from S2, plus the tweeter share). ΔV = half the headroom between 17.97 V and the 16.6 V the woofer ceiling needs, i.e. 0.68 V → **0.137 Ω**, over the audio band.

**Validation.**
- The PVDD peak matches the hand value 1/(2π·fc·C) = 0.44 Ω (model 0.46 Ω).
- The PVDD model reproduces S1's Zo/(1 + T) at low frequency by construction.

**Results.**
- **+3V3 meets its target with margin.** Max |Z| below 1 MHz is 0.14 Ω at the ESP32 and 0.15 Ω at the UI connector, vs 0.30 Ω. It rises to 0.18–0.19 Ω at 100 MHz (inductive, where the module's internal decoupling takes over). A slower buck loop (fc = 20 kHz) raises the peak to 0.24 Ω, still within target.
- **PVDD misses its target in the bass band.** |Z| peaks at **0.46 Ω at ~150 Hz** (VSYS 7.4 V) and **0.57 Ω** (6.0 V), 3.4–4.2× the 0.137 Ω target.
  - A 5 A bass transient would sag PVDD by ~2.3–2.8 V. The woofer limiter ceiling then clips, and PVDD carries bass-rate ripple.
  - Above ~1 kHz the bank is fine: 10–50 mΩ, and 14 mΩ at 768 kHz.
  - **With Rc/Cc = 100 k/15 nF the peak drops to 0.16 Ω**, which is at target. Rc = 150 k reaches 0.10 Ω but PM falls to 56°.

**Figures** (`docs/figures/pdn/`):
- `s7_pdn_3v3`: +3V3 impedance at the ESP32, UI connector and amps vs the 0.30 Ω target, with buck fc = 20/60 kHz variants.
- `s7_pdn_pvdd`: PVDD impedance at the right amp for three operating points and the Rc = 100 k what-if, vs the 0.137 Ω target.

**Data:** `../pdn/results/s7_pdn.json` (targets, peaks, BOMs, placeholder parasitics), `s7_pdn_impedance.csv`.

**Talking point.** PDN design is usually about nanohenries and gigahertz. Here the worst impedance on the board sits at 150 Hz: a 1.5 mF capacitor bank is only as stiff as the regulator loop behind it.

---

## Summary of spec findings

| # | Severity | Finding | Recommendation |
|---|---|---|---|
| 1 | **Medium** | PVDD closed-loop impedance 0.46–0.57 Ω at ~150 Hz (target 0.14 Ω). 0.2 → 2 A dip ≈ 1 V at 6 V; bass transients sag PVDD by ~2 V (S1, S7) | Rc 33 k → **100 k**, Cc 47 nF → **15 nF** (fz unchanged, PM ≥ 79°, GM ≥ 15 dB, dip 0.34 V). Keep Cp 10 pF |
| 2 | **Medium** | Start-up windup: PVDD overshoots to 19.4 V (typ) and to OVP ≈ 21 V (6 V, ILIM min) and stays there until the amps load it. Ramp is 11 ms, not 9 ms (S1) | Accept (all ratings OK; 20 ms wait still valid) and bench-check, or fit R907/D901 and ramp PVDD_TRIM down after BOOST_EN as a firmware soft start |
| 3 | Low | SPI/PDM 33 Ω series resistors under-terminate the ~107 Ω FFC: 0.7–1.1 V overshoot (S6) | R113/R114 (SCLK/MOSI), R118 (PDM_CLK) → **68 Ω**; 40 MHz keeps margin (fmax ≈ 53 MHz) |
| 4 | Low | Tweeter HF droop is −2.2 dB at 20 kHz (re 2.5 kHz), not −0.44 dB (S2) | Tweeter EQ shelf ≈ +2 dB above 10 kHz |
| 5 | Low | esptool reset fails if the host's DTR/RTS gap exceeds ~2.5 ms; EN can start rising before VDD = 3.0 V at power-up (S5) | C103 1 µF → **2.2 µF** |
| 6 | Low | Charging continues at full current from 45 to 61 °C with POR JEITA defaults (S3) | Firmware: JEITA_ISETH = 0 or TS_WARM = 40 °C, per pack datasheet |
| 7 | Info | Trim curve ~0.3 V lower than the hand table; diode leakage can raise PVDD ≤ 0.09 V at 85 °C; settling ≈ 100 ms (S4) | Firmware calibrates duty → PVDD; wait ≥ 150 ms |

Confirmed as specified: no start-up hiccup; loop stability (PM ≥ 65°, GM ≥ 22 dB); inductor peaks ≤ 2.7 A with the limiters (mandatory tweeter limiter confirmed: 5.4 A without it); idle ripple 0.59/0.28 A (BD/1SPW) never reaches the drivers; NTC window 2.0–60.8 °C; trim ripple < 1 µV at FB; strapping levels; +3V3 PDN.
