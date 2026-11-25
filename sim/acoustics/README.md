# Acoustic and structural simulations (A1–A5)

This folder holds every acoustic simulation of the portable stereo speaker (driver set B8: 2× Dayton ND65-8 woofers, 2× Peerless OT19NC00-04 tweeters, 2× Dayton DMA58-PR passive radiators, in the Ø95 × 210 mm printed capsule). Each simulation answers one design question. Each was checked against an analytic case before it was trusted, and each writes its numbers to `results/` so later tools can redraw the figures.

| Sim | Question | Tool | Runtime (M4, 10 cores) |
|---|---|---|---|
| A1 | How should the passive radiators be tuned, how loud can the bass go, and what bass EQ reaches F3 ≈ 64 Hz? | Own lumped-element model, checked against electroacPy | ~10 min |
| A2 | Is the 3 mm tweeter bezel good enough, or is a waveguide worth 10 mm more capsule? | Boundary-element method (bempp-cl) on the real capsule shape | part of the BEM sweep |
| A3 | How large are the woofers' baffle step and diffraction ripple, and does the 14 mm woofer tunnel matter? | BEM (same sweep) + lumped tube model | part of the BEM sweep |
| A4 | Do the printed panels resonate where the woofers play? | Finite elements (CalculiX, bundled with FreeCAD) | ~35 min |
| A5 | What do woofer + tweeter sum to through an LR4 crossover, and what DSP EQ flattens it? | A1 + A2/A3 transfer functions + scipy biquads | < 1 min |
| BEM sweep | Pressure everywhere for 1 m/s on each of the six radiators, 105 Hz–16 kHz | `bem_capsule_run.py` | ~75 min for all four cases, plus a 10 min convergence check |

**Run everything:** `sh sim/acoustics/run_all.sh` (reuses cached BEM/FEM results; `FORCE=1` recomputes all, ~2.5 h, peak RAM ≈ 3 GB). Each script also runs on its own from the venv, for example `.venv/bin/python sim/acoustics/a2_tweeter_bem.py`. The venv's `bin` must be on `PATH` because bempp calls the `gmsh` executable.

**Conventions used everywhere.**
- Coordinates as in `docs/mech_envelope.md`: x along the capsule (+x = right when facing the speaker), −y = front (grille), +z = up, origin at the capsule centre.
- Complex results use the engineering time convention e^{+jωt}. bempp works in e^{−iωt}, so `bem_core.py` conjugates its output once.
- SPL is re 20 µPa, rms. "Half space" means the speaker standing on a large table (2π radiation), as in the requirement.
- Air: ρ = 1.20 kg/m³, c = 343 m/s.
- The figure style is `sim/paper.mplstyle`. Every figure is saved as PDF (vector) and PNG in `docs/figures/acoustics/`.

**The seated listener** used by A2, A3 and A5: the speaker stands on its flat bottom on a desk, and the listener's ears are 1.0 m in front of the capsule centre (horizontally) and 0.40 m above the desk top. Seen from the left tweeter, that is 1.02 m away and 21° below the tweeter axis (5° to the side). The desk is a rigid infinite plane, added with an image source (see the BEM section for what that leaves out). A grid of 15 seats (±0.15 m and ±0.30 m sideways, ears 0.30/0.40/0.50 m above the desk) gives a "listening window" average.

## Files

| File | Role |
|---|---|
| `common.py` | Paths, constants, figure style, JSON/CSV helpers, parser for the CAD parameter block |
| `bass_model.py`, `a1_bass_lumped.py` | A1 |
| `capsule_geometry.py` | Builds the acoustic hull from the CAD parameters with gmsh/OpenCASCADE and tags the pistons |
| `bem_core.py` | bempp-cl wrapper: direct boundary-integral equation, CHIEF and Burton–Miller, field evaluation |
| `bem_validation.py` | BEM check against the exact piston-on-a-sphere solution |
| `bem_geometry_fig.py` | Hull mesh figure and hull-versus-CAD section check |
| `bem_capsule_run.py` | The heavy BEM sweep (cases `bezel`, `waveguide`, `flush`, `bmcheck`); checkpointed and restartable |
| `bem_convergence_check.py` | Mesh and formulation convergence at 5 kHz (why the tweeters get local refinement) |
| `bem_results.py`, `drivers_lumped.py` | Loader for the sweeps; tweeter model, baffled-piston formulas |
| `a2_tweeter_bem.py`, `a3_woofer_bem.py`, `a5_crossover_system.py` | A2, A3, A5 post-processing and figures |
| `a4_panel_modes.py`, `a4_post.py` | A4 |
| `biquad_export.py` | All DSP biquads at 96 kHz and 48 kHz in TAS5805M 5.27 format |
| `run_all.sh` | Runs everything in order, one heavy job at a time |
| `pr_alignment_firstpass.py` | Earlier first-pass alignment (19 V rail, 0.75 L), kept for the record |

## Key findings (all sims)

| Topic | Result | Verdict |
|---|---|---|
| Bass (A1) | PRs +3.5 g each → fb 53 Hz. With a 4-biquad bass EQ (+8.8 dB max): F3 / F6 = 63.7 / 55.3 Hz. Pink-noise max 90.6 dB (half space, 1 m), set by the 15.5 V woofer limiter | **Requirement met with only 0.5 dB margin**; F6 misses 55 Hz by 0.3 Hz |
| Tweeter bezel (A2) | Listener 21° below the tweeter axis is within 2 dB of on-axis to 10 kHz; the bezel adds ~2 dB of ripple. A 10 mm waveguide gives +3–4 dB and a narrower beam but twice the ripple | **Keep the 3 mm bezel**; a longer capsule is not justified |
| Desk (A2/A3/A5) | The desk reflection notches the tweeter at ~2.8 kHz at the centre seat (−15 dB; −5.6 dB averaged over 15 seats). It also lifts the low woofers by ~5 dB from 0.2 to 2 kHz | Leave the notch to placement, never EQ. The desk cancels the baffle step for free |
| Woofer baffle step / tunnel (A3) | Step −5.6 dB, smooth (0.36 dB ripple). The 14 mm tunnel is a low-Q horn bump of +3–4 dB at 2.5–3.8 kHz | **Keep the tunnel**; it offsets the woofer's Le roll-off |
| Panels (A4) | 24 shell modes below 1 kHz, but their net output is ≥ 23 dB below the woofers. First mode 269 Hz (ovalling) | Add a 1.6 mm spine plate between the woofers (→ 447 Hz), firm battery clamping, and damping pads on the top and bottom flats |
| Crossover (A5) | LR4 at 2.5 kHz, tweeter −9.7 dB, +110 µs, normal polarity. Sum within 0.05 dB of ideal. 2.0 / 3.0 kHz are no better | **Keep 2.5 kHz**. A 7-biquad system EQ (≤ +3 dB boost) brings the 15-seat average to ±2.5 dB |
| DSP export | All biquads at 96 kHz (TAS5805M rate) and 48 kHz, in TAS5805M 5.27 hex | `results/biquads_tas5805m.json/.csv` |

**Threats to the requirements:**
- the ≥ 90 dB pink-noise target holds by only 0.5 dB (A1);
- F6 sits at 55.3 Hz against ≤ 55 Hz (A1).

Both rest on vendor T/S data, so measure the drivers first. A1 lists the levers: a 17.1 V limiter (+0.9 dB, the woofer then runs above its rating), or an EQ target with F3 ≈ 61 Hz.

**Recommended design changes:**
1. A spine plate plus battery-tray gussets and damping pads (A4).
2. Optional feet giving a 5–10° backward tilt, or more tweeter height, to move the desk notch (A2).
3. Two placement EQ presets: on the desk (default) and free-standing (+5 dB baffle-step shelf). The mic auto-EQ chooses between them (A3/A5).
4. Do not lengthen the capsule for a waveguide. Do not shorten the woofer tunnel.

---

## A1. Bass system (lumped model)

**Question.** In the real capsule (0.85 L by CAD, about 0.82 L once every part is in), with the real amplifier limits, how much mass should go on each passive radiator (PR)? How loud can the bass play before the amplifier, the woofers or the PRs run out? What DSP bass EQ gives F3 ≈ 64 Hz? What would polyfill or zeolite buy?

**Inputs.**
- Drivers: 2× Dayton ND65-8 and 2× Dayton DMA58-PR, using the vendor T/S data in `research/drivers.json`.
- Box: net volume 0.82 L (final) and 0.85 L (CAD nominal, `mech/concept/build/report.json`).
- Amplifier: TAS5805M in BTL on PVDD = 18.0 V. The woofer-channel limiter is set to **15.5 V peak**, about 15 W into 8 Ω. The current limit is 4.5 A peak (the 5 A OCP less 10 %).

**Method.** `bass_model.py` is a small-signal Thiele/Small circuit.
- Each woofer: Re + jωLe, Bl, Mms, Cms, Rms.
- The two woofers drive one shared box. The box is an acoustic compliance Cab, with absorption Rab (Q_A) in series and leakage Ral (Q_L) in parallel.
- The two PRs: Mmp + m_add, Cmp, Rmp.
- Output is the monopole sum of the woofer and PR volume velocities, in half space (speaker on a table) at 1 m.

`a1_bass_lumped.py` then does six things:
1. Sweeps the PR added mass from 0 to 16.75 g in 0.25 g steps (2.5 × the bare PR mass).
2. Computes the sine maximum SPL at each frequency. This is the lowest of four limits: amp voltage, amp current, woofer Xmax (3.5 mm) and PR excursion (5 mm usable of 7 mm Xmech).
3. Designs the DSP bass EQ. The target is a 4th-order Butterworth at 63 Hz times a 2nd-order subsonic at 28 Hz. Boost is capped at 18 dB, and the EQ rolls off at 24 dB/oct below 47 Hz so it never chases the PR notch.
4. Fits that EQ with real 48 kHz biquads.
5. Estimates the long-term pink-noise level. This uses 1/3-octave bands from 20 Hz to 20 kHz, crest factor 3 (9.5 dB) after the limiter, the woofer's 15 W thermal rating, and an LR4 low-pass at 2.5 kHz.
6. Runs the what-ifs, re-optimising the PR mass for each one.

**Assumptions and limits.**
- Linear, small-signal model. Bl(x), Cms(x) and Le(x) are not modelled, so near Xmax the real driver compresses and distorts earlier than shown.
- Q_L = 10 (gasketed print). Q_A = 100 for the empty box.
- The voice coil is a plain inductor (Le = 0.61 mH). No semi-inductance data are published. The woofer roll-off above about 2 kHz is therefore only indicative; A5 and measurements set the crossover region.
- No radiation impedance is added, because the published Mms already includes the air load. Adding a baffled-piston air load changes the SPL by at most 0.14 dB.
- Monopole radiation in half space is valid below about 300 Hz. Above that, the baffle step and diffraction come from the BEM (A3).
- Both woofers get the same signal. Real stereo bass differs between channels, so sharing one box is a slight simplification.
- The polyfill what-if follows the usual approximation. Fibre fill makes the compression partly isothermal: light fill gives Vb_eff = 1.10 × Vb with Q_A = 30, heavy fill gives 1.20 × Vb with Q_A = 10.
- The zeolite what-if simply multiplies Cab by 1.3, 1.5 or 2 with Q_A = 30. It ignores the volume the zeolite bag itself takes up and the effect's dependence on humidity and level.
- Pink-noise levels are estimates for a DRC-limited signal, not a measurement standard.

**Validation.**
- Sealed box (2 woofers, 0.82 L): the closed-form fc = fs·√(1 + 2Vas/Vb) = 140.03 Hz. The model's impedance peak is at 140.04 Hz (Le = 0).
- Symmetry: 2 woofers + 2 PRs in Vb equals 1 + 1 in Vb/2 to machine precision.
- A lossless PR gives a zero in the output at fp (notch −137 dB), as theory requires.
- **electroacPy 2025.7.1 cross-check** (same drivers, box, PR mass and losses):
  - SPL agrees within **0.013 dB**.
  - |Z| agrees within **0.22 %**.
  - Woofer and PR excursion agree within **0.025 dB**, from 15 Hz to 2 kHz.
  - Finding: electroacPy's `radiator` element uses ρc(R1 + jX1) as the acoustic radiation impedance, without the 1/S factor. Its air load is therefore negligible, which matches our default of no added air load.

**Results (0.82 L, 3.5 g per PR).**

| Quantity | Value |
|---|---|
| PR added mass | **3.5 g per PR** (the optimum is 2.5 g, flat within 0.05 dB from 2.5 to 4 g) |
| Box tuning fb / PR notch fp | **53.2 Hz / 32.2 Hz** (impedance minimum ≈ 61 Hz; the upper impedance peak is at 140 Hz) |
| Natural (no EQ) F3 / F6 | 120 / 96 Hz |
| With the DSP bass EQ: F3 / F6 | **63.7 / 55.3 Hz** (requirement ≤ 65 / ≤ 55 Hz). F6 misses by 0.3 Hz, which is within model accuracy. |
| Maximum EQ boost | **+8.8 dB** at about 68 Hz |
| Sensitivity, 2.83 V on each woofer, 400 Hz | 86.7 dB (half space, 1 m) |
| Sine maximum at 40 / 50 / 63 / 80 / 100 / 200 Hz | 66.7 / 78.2 / 86.7 / 89.3 / 91.7 / 98.8 dB. The limits are PR excursion below 60 Hz, amp voltage at 63 Hz, woofer Xmax from 75 to 150 Hz, and amp voltage above that. |
| Flat-passband sine ceiling with the bass EQ | 87.0 dB, set by PR excursion at 48 Hz |
| **Pink-noise maximum** (half space, 1 m) | **90.55 dB, limited by amp voltage.** The other limits are woofer Xmax at 91.6 dB, PR at 92.0 dB, thermal at 99.0 dB and current at 99.5 dB. |
| Same at 0.85 L | 90.61 dB |
| Average woofer power at that level | 2.4 W per woofer; estimated battery draw about 9 W |
| Minimum impedance | 7.46 Ω, so the current limit is never reached |

The bass EQ as four biquads, fitted at fs = 48 kHz (`results/a1_bass_summary.json` also holds the SOS coefficients). The same filters at 96 kHz, the TAS5805M's actual DSP rate, are in `results/biquads_tas5805m.json` and differ by < 0.0001 dB:

| # | Type | fc (Hz) | Q | Gain (dB) |
|---|---|---|---|---|
| 1 | High-pass (BW4 subsonic, stage 1) | 49.8 | 0.541 | – |
| 2 | High-pass (BW4 subsonic, stage 2) | 49.8 | 1.307 | – |
| 3 | Low shelf | 113.0 | 1.03 | +5.8 |
| 4 | Peaking | 65.9 | 1.40 | +2.9 |

These stay within **0.55 dB** of the ideal EQ from 40 Hz to 1 kHz.

**Why 3.5 g and not the 2.5 g optimum.** At 2.5 g the PRs sit only 0.3 dB from their excursion limit. At 3.5 g both the PR and the woofer have at least 1.1 dB of excursion margin over the binding amp-voltage limit, for a cost of 0.04 dB. That margin covers tolerance in Cms, Mms and Q_L. It is also easy to build: a few M3/M4 washers on the DMA58-PR rod, then fine-tune by measuring the impedance dip.

**What-ifs** (pink-noise maximum with the PR mass re-optimised; values at 3.5 g in brackets):

| Case | Pink max (dB) | Best m_add | fb at 3.5 g |
|---|---|---|---|
| Baseline, 0.82 L, Q_L 10 | 90.6 (90.6) | 2.5 g | 53.2 Hz |
| Leaky box, Q_L 5 | 90.3 (90.3) | 2.8 g | 53.2 Hz |
| Tight box, Q_L 20 | 90.7 (90.7) | 2.5 g | 53.2 Hz |
| Polyfill, light (×1.10, Q_A 30) | 90.6 (90.6) | 2.3 g | 51.7 Hz |
| Polyfill, heavy (×1.20, Q_A 10) | 90.4 (90.4) | 2.0 g | 50.3 Hz |
| Zeolite ×1.3 | 90.9 (90.8) | 2.0 g | 49.2 Hz |
| Zeolite ×1.5 | 91.0 (90.8) | 1.8 g | 47.3 Hz |
| Zeolite ×2.0 | 90.7, woofer-Xmax-limited (90.1) | 1.2 g | 44.0 Hz |
| Limiter at 17.1 V (the BTL clip point at 18 V PVDD) | **91.4** (91.4) | 3.0 g | 53.2 Hz |

Reading the what-ifs:
- **The system is amplifier-voltage-limited, so neither stuffing nor zeolite moves the pink-noise number by more than ±0.5 dB.**
- More virtual volume lowers fb and helps the 50 Hz sine maximum: +2.3 dB with zeolite ×1.5, +1.6 dB with heavy polyfill. That is real but small.
- At ×2, the woofer becomes Xmax-limited.
- The only lever worth 1 dB is the limiter voltage, 15.5 → 17.1 V (+0.9 dB), at the price of running the woofer at about 18 W (rated 15 W RMS; the DRC must then manage average power).
- Recommendation: use light polyfill only, for damping internal standing waves (not modelled here). Keep it at least 10 mm away from the PRs and out of the PR keep-out. Skip zeolite.

**Threats to the requirements.**
- Pink-noise SPL is **90.55 dB against a 90 dB requirement**, a margin of only 0.5 dB. It holds only in half space with a 9.5 dB crest after the DRC.
- F6 is 55.3 Hz against a requirement of ≤ 55 Hz. This is marginal, and a slightly lower EQ target (F3 61 Hz) would fix it.
- Both results rest on vendor T/S data. Measure the drivers (DATS/REW), update `drivers.json`, and re-run.
- Compared with the first pass (0.75 L, 18 V cap: 91.4 dB), the 15.5 V limiter costs about 0.9 dB, and the extra 0.07 L gives back less than 0.1 dB.

**Figures** (`docs/figures/acoustics/`, PDF + PNG):
- `a1_spl_halfspace_1m`: SPL at 1 m in half space. Shows 2.83 V with the woofer-only and PR-only contributions, full 15.5 V drive, and the EQ'd maximum clean sine level, with fb and fp marked.
- `a1_excursion_vs_xmax`: woofer and PR excursion against their limits. (a) 15.5 V sine with no EQ. (b) With the bass EQ at the maximum clean level; the PR reaches its 5 mm limit at 48 Hz.
- `a1_impedance`: impedance magnitude and phase of one woofer in the PR box, with fb and fp marked.
- `a1_max_spl_vs_frequency`: sine maximum SPL coloured by the limiting mechanism, the EQ'd flat ceiling, and the pink-noise estimate against the 90 dB requirement.
- `a1_dsp_bass_eq`: natural response, target, ideal EQ, 4-biquad EQ and realised response (F3 64 Hz, F6 55 Hz). The lower panel shows the biquad error (≤ 0.55 dB, 40 Hz–1 kHz).
- `a1_pr_mass_sweep`: SPL family for 0–16 g added mass per PR, and the pink-noise maximum with each limiting mechanism as a function of added mass.
- `a1_whatif_volume_fill_zeolite`: responses and pink-noise maxima for leakage, polyfill, zeolite and limiter variants.
- `a1_electroacpy_crosscheck`: SPL, impedance and excursion from this model against electroacPy (differences ≤ 0.013 dB / 0.22 % / 0.025 dB).

**Data** (`sim/acoustics/results/`):
- `a1_bass_summary.json`: all the numbers above, the assumptions, the biquads and the SOS coefficients.
- `a1_bass_transfer.csv`: per-volt woofer and PR velocity, Zin and the bass EQ, 10 Hz–20 kHz. Used by A3 and A5.
- One CSV per figure.
- `a1_bass_lumped_output.txt`: console log.

**Talking points.**
- "Two 2.5-inch woofers and two passive radiators in under a litre reach 64 Hz. The passive radiators do the work below about 60 Hz. A gentle +9 dB DSP lift, four biquads in the amplifier, does the rest."
- "A few grams of washers on each passive radiator tune the box to 53 Hz. That is the single cheapest acoustic adjustment in the whole speaker."
- "The bass is limited by the battery-powered amplifier's voltage, not by cone travel. That is why we skipped zeolite: it would add complexity for less than half a decibel."

---

## The BEM model shared by A2, A3 and A5

**What is solved.** The capsule is a rigid closed body in free air. Each radiator (2 woofers, 2 PRs, 2 tweeters) is a rigid piston of the driver's published Sd, moving with 1 m/s normal velocity while everything else stays still. For each frequency, bempp-cl solves the Helmholtz equation outside the body and returns the pressure anywhere in the air. Because the problem is linear, any real drive is a weighted sum of these six unit solutions; A3 and A5 weight them with the cone and PR velocities from the lumped models.

**Geometry (`capsule_geometry.py`).** The hull is rebuilt in gmsh/OpenCASCADE from the parameter block of the FreeCAD concept model (`mech/concept/speaker_concept.py`), with the same construction formulas. A parameter change in the CAD therefore flows into the BEM.
- Modelled: the Ø95 × 210 mm body with 3 mm end fillets and the flat bottom; the PR flanges standing 3 mm proud on the end caps; the Ø53 woofer tunnels with their 3 mm chamfer, ending at the front of the woofer surround; the tweeter's Ø36 raised boss with the 3 mm conical bezel; the volume knob on top.
- Left out: the perforated grille (thin, flush in its recess, assumed acoustically transparent), the display lens, buttons, mic hole and USB pocket (flush or tiny), and the curvature of the cones and dome (all pistons are flat).
- Check: `a2_a3_bem_hull_mesh_and_cad_check` overlays sections of the hull on the CAD solids at the woofer and tweeter planes. The median distance from the hull section to the CAD outline is 0.7–0.9 mm (`results/bem_geometry_check.json`). The few larger gaps are the simplifications above (the surround/flange step at the tunnel bottom).

**Pistons.** Woofer Sd 16.5 cm² (Ø45.8 mm) at the bottom of its tunnel; PR Sd 14.5 cm² flush with the flange face; tweeter Sd 4.5 cm² (Ø24 mm, from the Vifa/Tymphany datasheet) at the bottom of the bezel cup. A straight-edged mesh slightly under-fills a circle (by 1–3 %), so each piston's velocity is scaled to give exactly Sd × v of volume velocity.

**Formulation (`bem_core.py`).** Direct boundary-integral equation, (½I − K)p = −V(∂p/∂n), with continuous piecewise-linear (P1) pressure on the surface and piecewise-constant Neumann data (∂p/∂n = jωρv) only on the piston. The plain direct equation has spurious solutions at the interior resonances of the body; the capsule's first is near 2.9 kHz. Two fixes are coded:
- **CHIEF** (production): 40 random points inside the capsule must have zero pressure. The over-determined system is solved exactly in the least-squares sense with one in-place LU factorisation plus a small Woodbury correction, so memory stays at about one dense matrix (≈1.5 GB at the top mesh).
- **Burton–Miller** (check only): adds the hypersingular operator. It is robust but about 5× slower to assemble.

**Meshes.** Element size h ≤ λ/6 at the top frequency of each band, with a 9 mm ceiling, curvature refinement and a local refinement around the tweeters:

| Band | Global h | Around the tweeters | Unknowns (bezel / waveguide) | 95th-percentile edge | λ/6 at band top |
|---|---|---|---|---|---|
| 100 Hz – 6.35 kHz | 9 mm | 2.8 mm | 4210 / 4724 | 8.8 mm | 9.0 mm |
| 6.73 – 10.1 kHz | 5.6 mm | 2.8 mm | 6047 / 6469 | 5.6 mm | 5.7 mm |
| 10.7 – 16 kHz | 3.5 mm | 2.8 mm | 9763 / 10257 | 3.7 mm | 3.6 mm |

Around the tweeters, a size field holds h = 2.8 mm within 25 mm of each tweeter centre, grading to the global size at 50 mm. This is needed because the Ø24 mm dome and the 3 mm bezel lip are smaller than λ/6 suggests (see the convergence check below). The flush-woofer diagnostic mesh has no local refinement (2966 / 4850 unknowns up to 8 kHz).

Runtimes on the M4: bezel 88 frequencies in 33 min, waveguide 49 in 25 min, flush 65 in 7 min, Burton–Miller check 7 min. Peak memory stays below about 3 GB at the 10 k-unknown level: one 1.5 GB dense matrix plus assembly buffers. The sweep checkpoints each frequency to `results/bem_ckpt_<case>/` and skips finished frequencies on restart. The checkpoints are deleted when the case completes.

gmsh treats h as a target, so a few percent of edges come out longer (the table lists the 95th-percentile edge). **Top frequency: 16 kHz**, in 1/12-octave steps from 105 Hz.

**Validation.**
1. *Piston on a rigid sphere* (`bem_validation.py`, exact series solution from Morse & Ingard). Sphere radius 50 mm with a 27° cap (cap radius 22.7 mm, close to the woofer), meshed with the same rules at h = λ/6 for 8 kHz (782 unknowns). Maximum error over all angles at 1 m:

   | f | ka | direct | CHIEF | Burton–Miller |
   |---|---|---|---|---|
   | 1 kHz | 0.92 | 0.010 dB | 0.010 dB | 0.010 dB |
   | 3.43 kHz | π | 0.080 dB | 0.079 dB | 0.083 dB |
   | 8 kHz | 7.3 | 0.34 dB | 0.34 dB | 0.35 dB |

   A 3 Hz-step sweep through the sphere's first interior resonance shows the failure that CHIEF exists to fix: the plain direct equation is off by 0.88 dB at 3438 Hz, while CHIEF stays within 0.087 dB across the whole sweep (`a2_a3_bem_validation_irregular_frequency`). The earlier smoke test (pulsating sphere, 0.22 %) is in `sim/smoke/`.
2. *CHIEF against Burton–Miller on the real capsule* (`bem_capsule_run.py bmcheck`, production meshes) at 2.9, 5 and 9 kHz. The front-hemisphere tweeter polar patterns agree within 0.15 dB.
3. *Mesh convergence at 5 kHz* (`bem_convergence_check.py`, reference: h = 5.6 mm with 2 mm at the tweeters, Burton–Miller). Values are the maximum / median dB difference over directions within 20 dB of the pattern maximum:

   | Mesh, method | Tweeter | Woofer |
   |---|---|---|
   | h 9 mm, no local refinement, CHIEF (first attempt) | 1.33 / 0.57 | 0.73 / 0.08 |
   | Same, 80 CHIEF points instead of 40 | 1.32 / 0.58 | 0.72 / 0.08 |
   | h 9 mm, no local refinement, Burton–Miller | 1.67 / 0.24 | 0.57 / 0.09 |
   | **h 9 mm + 2.8 mm at the tweeters, CHIEF (production)** | **0.29 / 0.15** | **0.36 / 0.05** |
   | h 5.6 mm + 2.8 mm, CHIEF (production, 6.7–10 kHz) | 0.28 / 0.14 | 0.11 / 0.02 |
   | h 5.6 mm + 2.0 mm, CHIEF | 0.09 / 0.05 | 0.06 / 0.02 |

   The first sweep used a uniform mesh. The check showed that its tweeter error (up to 1.3 dB) came from the mesh, not from CHIEF: doubling the CHIEF points changed nothing, and Burton–Miller on the same mesh was no closer. So the tweeter zones were refined and the bezel, waveguide and check cases were re-run. The production meshes are within 0.3 dB of the reference.
4. *BEM against the lumped model (A1).* At 100–200 Hz the BEM pressure of both woofers plus both PRs at the seated listener, desk included, is 0.43 dB above A1's half-space monopole (0.49 dB at most), where the two should agree. That ties the absolute level of the BEM to A1. The small excess is the capsule's own size and the woofers' 44 mm height above the desk.
5. *Left/right mirror check.* The left tweeter's pattern against the mirrored right tweeter's: median 0.26 dB, ≤ 1.5 dB wherever the level is within 10 dB of the maximum. The geometry is not perfectly symmetric (the volume knob sits at x = +70 mm, next to the right tweeter), and the two meshes are independent.

**Limits.**
- Rigid pistons: no cone or dome break-up, no surround radiation. The ND65-8's aluminium cone will add its own break-up peak above the crossover (the LR4 low-pass attenuates it).
- The desk is an image source: p = p_free(listener) + p_free(listener mirrored in the desk). This is exact for a point source above a rigid plane. It leaves out the re-scattering of the desk reflection by the capsule body. The reflection leaves the tweeter downward and forward, away from the body, so this error should be small; the desk is also treated as infinite and rigid.
- No room, no grille, no internal box modes (the BEM has no interior air).

---

## A2. Tweeter directivity (BEM)

**Question.** The tweeters sit on the 40°-up shoulders behind only a 3 mm bezel, because there was no room for a waveguide. Is that good enough? Would a proper ~10 mm waveguide (needing a capsule about 10 mm longer) be worth it? And what does a seated listener on a desk actually hear?

**Inputs.**
- Peerless OT19NC00-04: Sd 4.5 cm² (Ø24 mm piston). Its T/S data (Re 3.17 Ω, Bl 1.64 T·m, Mms 0.20 g, Fs 1029 Hz, Qms 7.03) drive the lumped velocity model in `drivers_lumped.py`. The tweeter is closed-back, so its sealed printed pod does not load it.
- Hull variants:
  - (a) bezel, as designed (`bem_bezel.npz`);
  - (b) waveguide: faceplate 10 mm deeper at the throat of an oblate-spheroid flare (r(z) = √(r₀² + z² tan²60°), mouth Ø49 mm), cut into a 220 mm capsule with the tweeter still at x = ±83 mm (`bem_waveguide.npz`);
  - (c) analytic piston in an infinite flat baffle, 2J₁(ka sin θ)/(ka sin θ).

**Method.** BEM sweep 1–16 kHz (see the BEM section), left tweeter, 1 m/s. Polar planes are in the tweeter's own frame:
- *horizontal* contains the tweeter axis and the capsule's long axis (+ = toward +x, i.e. toward the capsule centre for the left tweeter);
- *vertical* contains the tweeter axis and the capsule cross-section (+ = up and back over the top, − = down toward the desk and the listener).

Patterns are far-field and normalised to on-axis at each frequency. Absolute levels use the lumped velocity at 2.83 V. Directivity index (DI) comes from a 400-direction sphere.

**Assumptions.**
- Rigid flat piston: the real dome adds its own directivity above ~10 kHz and its break-up.
- No grille.
- The waveguide is a quick, unoptimised OS profile, enough to answer "is 10 mm of depth worth it", not a finished design.

**Validation.** See the BEM section: sphere piston (≤ 0.34 dB at ka = 7.3); CHIEF against Burton–Miller on this hull (tweeter ≤ 0.15 dB); mesh convergence at the tweeter (≤ 0.3 dB). As a level check, the bezel tweeter gives 87.6 dB at 5 kHz, 1 m on axis, 2.83 V, against 87.3 dB for the same lumped driver in an infinite baffle and 88.8 dB on the datasheet (a band average on an IEC baffle).

**Results.**

| | 3 mm bezel (as built) | 10 mm waveguide | Infinite baffle |
|---|---|---|---|
| −6 dB beamwidth, horizontal, 2.5 / 5 / 10 kHz | ~310° / 190° / 110° | 235° / 128° / 70° | 185° / 185° / 185° (half space) |
| −6 dB beamwidth, vertical, 10 kHz | 110° | 75° | 185° |
| Directivity index, 2.5 / 10 kHz | 3.0 / 7.9 dB | 3.8 / 11.1 dB | 3.2 / 6.5 dB |
| On-axis SPL, 2.83 V, 1 m, at 2.5 / 5 / 10 kHz | 86.6 / 87.6 / 88.0 dB | 89.5 / 92.1 / 89.7 dB | 88.0 / 87.3 / 87.0 dB |
| On-axis ripple 2–12 kHz (peak-to-peak about a straight-line fit) | 2.1 dB | 4.7 dB | 0.6 dB |
| Listener direction (21° below axis) re on-axis, at 5 / 10 kHz | +0.8 / −1.8 dB | −0.2 / −2.6 dB | −0.2 / −0.8 dB |
| Ripple at the listener, free field, 2–12 kHz | 4.1 dB | 6.4 dB | — |
| Desk-reflection dip, centre seat / 15-seat average | −14.8 dB at 2.8 kHz / −5.6 dB | −11.8 dB at 3.0 kHz / −5.3 dB | — |

What the numbers say:
- **The 3 mm bezel is acceptable.** The tweeter radiates almost like a piston on a curved baffle. The seated listener, 21° below the axis, gets within 2 dB of the on-axis level up to 10 kHz with no deep notch in free field. The bezel adds about 2 dB of diffraction ripple on axis, which the EQ in A5 can partly flatten.
- **A 10 mm waveguide is not worth lengthening the capsule.**
  - It buys about +3–4 dB of sensitivity from 3 to 8 kHz and a narrower beam (DI +3 dB at 10 kHz).
  - The tweeter channel already runs at −9.7 dB trim (A5), so the extra sensitivity buys nothing useful.
  - This short, unoptimised flare roughly doubles the response ripple (4.7 vs 2.1 dB on axis; 6.4 vs 4.1 dB at the listener).
  - It only softens the desk dip by 3 dB at the centre seat, and by 0.3 dB averaged over seats.
  - Recommendation: **keep the bezel**. Revisit only with an optimised waveguide of 15 mm or more.
- **The real tweeter problem is the desk, not the bezel.** At the centre seat the desk reflection cancels the direct sound around 2.8 kHz (−15 dB), and again near 9 kHz. The dip moves with ear height, so averaged over the 15 seats it shrinks to about −5.6 dB. It sits right at the crossover. EQ must not fill it (see A5). The physical cures are:
  - more tweeter height above the desk (each centimetre moves the notch up);
  - a ~5–10° backward tilt of the whole speaker using feet;
  - placing the speaker near the front edge of the desk.

**Figures** (`docs/figures/acoustics/`):
- `a2_a3_bem_hull_mesh_and_cad_check`: the bezel and waveguide hull meshes, with pistons coloured, and sections of the BEM hull over the CAD solids at the woofer and tweeter planes.
- `a2_a3_bem_validation_sphere_piston`: BEM (direct, CHIEF, Burton–Miller) against the exact series for a piston on a sphere at ka = 0.9, π and 7.3.
- `a2_a3_bem_validation_irregular_frequency`: sweep through the sphere's first interior resonance. The plain direct equation fails (0.9 dB) and CHIEF does not (≤ 0.09 dB).
- `a2_tweeter_polar_maps_bezel_waveguide_baffle`: horizontal and vertical polar maps, 1–16 kHz, normalised to on-axis, for the bezel, waveguide and flat baffle. The white dashed line is −6 dB and the blue dashed line is the seated listener.
- `a2_tweeter_onaxis_and_listening_axis`: SPL for 2.83 V on axis at 1 m, and at the seated listener, free field and with the desk reflection.
- `a2_tweeter_beamwidth_and_DI`: −6 dB beamwidth (horizontal and vertical) and directivity index against frequency.

**Data:** `results/a2_tweeter_directivity.json` (beamwidths, DI, summary, checks, listener geometry); `results/a2_tweeter_responses.csv`; `results/a2_polar_<case>_<h|v>.csv` (polar maps, dB re on-axis; rows = frequency, columns = angle); `results/bem_bezel.npz` and `bem_waveguide.npz` (complex pressure per m/s for every direction and point).

**Talking points.**
- "We simulated the tweeter on the real 3D-printed body with a boundary-element solver, about 10 000 unknowns per frequency, up to 16 kHz, on a laptop. The tiny 3 mm bezel turned out to be fine: a listener at the desk hears within 2 dB of the on-axis sound."
- "A proper waveguide would make it 4 dB louder but lumpier, and would need a longer speaker. We kept the short one."
- "The biggest dent in the treble isn't the speaker at all. It's the desk: its reflection cancels the direct sound near 3 kHz. No EQ can fix that, so the tweeters point up and over it."

---

## A3. Woofer diffraction, baffle step and the woofer tunnel (BEM)

**Question.** How large are the ND65-8's baffle step and diffraction ripple on the real Ø95 mm front, 100 Hz–5 kHz? What does the stereo pair (with the PRs) deliver at the listener? Does the 14 mm tunnel through the baffle land, with its ~3 kHz quarter-wave estimate, matter?

**Inputs.**
- Woofer piston Sd 16.5 cm² at the bottom of the Ø53 tunnel. The piston sits 13.6 mm below the skin at the centre, 11.7 mm on average and 5.5 mm at the bore edge, because the skin curves away.
- PR pistons Sd 14.5 cm² on the end caps.
- Woofer and PR velocities per volt from A1 (`results/a1_bass_transfer.csv`).
- Hulls: as designed (`bem_bezel.npz`) and a diagnostic with the woofer pistons flush on the skin (`bem_flush.npz`).

**Method.**
- *Diffraction* = on-axis pressure at 1 m divided by the exact on-axis pressure of the same piston in an infinite baffle, so the curve starts near −6 dB (the capsule radiates into the full sphere at low frequency) and shows the baffle step and the ripple.
- *Tunnel effect* = as designed ÷ flush, on axis and in radiated power. It is compared with a lumped model: a plane-wave tube with the bore's area, driven by the cone and loaded by a flanged-piston radiation impedance at the mouth.
- *System at the listener* = both woofers + both PRs with the A1 velocities at 2.83 V per woofer, free field and on the desk.

**Assumptions.**
- Rigid pistons and no grille. The bore is a plain cylinder: the 1.5 mm gap between the surround and the bore is ignored.
- Bass is identical in both channels (as in A1).
- The desk is an image plane (see the BEM section).

**Validation.**
- At 100–200 Hz the BEM system level at the desk listener matches A1's half-space lumped model within 0.43 dB on average (≤ 0.49 dB).
- The low-frequency diffraction value is −5.6 dB, close to the −6 dB expected for full-space against half-space radiation from a small box.
- The baffle step has the textbook shape. It is centred lower (−3 dB at 676 Hz for the flush case) than the flat-baffle rule of thumb (f₃ ≈ 115/W ≈ 1.2 kHz for W = 95 mm), because sound has a longer way round the round body than across a 95 mm flat front.
- CHIEF against Burton–Miller at 2.9, 5 and 9 kHz: woofer patterns agree within 0.41 dB and PR patterns within 0.06 dB (directions within 20 dB of the maximum).

**Results.**
- **Baffle step.** −5.6 dB at 100–130 Hz, rising through −3 dB at 643 Hz (676 Hz flush) and reaching 0 dB at about 1.1 kHz. On the round front it is a smooth shelf: diffraction ripple about the trend is only **0.36 dB peak-to-peak from 150 Hz to 2.5 kHz**. Values against the infinite baffle: −4.2 / −0.45 / +1.9 / +3.8 dB at 0.5 / 1 / 2 / 4 kHz.
- **On the desk the step is (mostly) gone.** The woofers sit 44 mm above the desk, so up to about 2 kHz the desk reflection adds coherently. The centre-seat level rises from 79.9 to 85.3 dB (200 Hz–2 kHz average, 2.83 V per woofer), and the 15-seat average is 85.0 dB. Placed on a desk, the speaker therefore needs no baffle-step boost, which matters because the woofer is the voltage-limited driver (A1). A free-standing EQ preset would need about +5 dB below 600 Hz, at the cost of about 5 dB of bass headroom. The planned mic-based placement compensation can choose between the two presets.
- **The tunnel matters, but it helps.** It acts as a short, wide horn throat with a low-Q resonance:
  - +3.1 dB on axis and +3.4 dB in power at 2.5 kHz;
  - peak +4.0 dB in power at 3.0 kHz and +4.7 dB on axis at 3.8 kHz;
  - back to about 0 dB by 6 kHz.

  The lumped tube (mean depth 11.7 mm) predicts the same +4.7 dB peak at 2.7 kHz. It is about 10 % low in frequency, because it ignores the curved, chamfered mouth. The bump partly cancels the woofer's voice-coil inductance roll-off (A1), so it is not harmful. It is smooth and minimum-phase-like, already inside every A5 curve, and the A5 EQ needs no special filter for it. **Keep the tunnel as designed. Do not try to shorten it.**
- **Woofer coverage.** −6 dB beamwidth (horizontal / vertical): wider than 180° up to 1 kHz, 193° / 188° at 2.5 kHz, 128° / 145° at 4 kHz. There is no beaming problem at the 2.5 kHz crossover.
- **PRs.** Above 150 Hz they add almost nothing at the listener (the woofers-only curve lies on top of the full one). Their role is below fb, which A1 covers.

**Figures:**
- `a3_woofer_baffle_step_and_diffraction`: on-axis level relative to an infinite baffle: left woofer in its tunnel, both woofers, flush woofer, and a textbook baffle-step shelf.
- `a3_woofer_tunnel_effect`: level change caused by the tunnel (BEM on axis and power) against the lumped tube model.
- `a3_woofer_polar_maps`: horizontal and vertical polar maps of the left woofer, 100 Hz–6.3 kHz.
- `a3_woofers_and_prs_at_listener`: SPL at the seated listener for 2.83 V per woofer (woofers + PRs): desk, free field, 15-seat average, woofers only, and A1's half-space model.

**Data:** `results/a3_woofer_diffraction.json`, `results/a3_woofer_responses.csv`, `results/a3_polar_woofer_L_<h|v>.csv`, `results/bem_flush.npz`.

**Talking points.**
- "Small speakers lose about 6 dB of bass-mid because sound wraps around the body. Our solver shows that on a desk, the desk gives almost all of it back, so we don't spend precious amplifier voltage on it."
- "The woofers sit at the bottom of a 14 mm tunnel. Instead of hurting, it acts as a tiny horn and adds 3–4 dB right where the woofer starts to run out of steam. Two independent models agree on the size of the bump."

---

## A4. Panel vibration modes (FEM, CalculiX)

**Question.** Which structural modes of the printed PETG enclosure sit inside the woofer band, especially below 1 kHz? How hard can the woofers drive them, and which ribs or braces would help?

**Script.** `sim/acoustics/a4_panel_modes.py` builds the meshes, solves every case and makes the figures. It takes about 35 min on the M4. `sim/acoustics/a4_post.py` regenerates the figures and tables from the cached results. Both run from the venv: `.venv/bin/python sim/acoustics/a4_panel_modes.py [validate|solve|ribs|post]`.

### Inputs

- **Geometry:** the concept CAD, `mech/concept/speaker_concept.step`. The model uses the named solids `shell_front`, `shell_rear`, `battery_tray`, `end_cap_L` and `end_cap_R`. The CAD was not edited.
- **Material:** PETG with E = 2.1 GPa, ν = 0.38 and ρ = 1270 kg/m³.
- **Lumped masses:**
  - ND65-8 woofer: 181 g each (Dayton lists 0.4 lb).
  - DMA58-PR plus 3.5 g add-mass: 71.5 g each (Dayton lists 0.15 lb).
  - Battery: 189 g.
- **Acoustic numbers:** Vb = 0.85 L. ND65-8 Mms = 2.6 g, Sd = 16.5 cm².

### Method

1. **Meshing.** gmsh imports the STEP file and *fragments* the five printed solids into one conformal body. Every printed joint (seam, cap spigots, tray) is therefore treated as **tied**. The mesh uses 10-node tetrahedra (C3D10) at a 3.5 mm target size, with straight-sided edges. That gives 167 k nodes and 0.5 M DOF.
2. **Solver.** We write the CalculiX deck ourselves and run `ccx` 2.23, the copy bundled with FreeCAD. It is a `*FREQUENCY` step with 30 modes. The eigenvectors are mass-normalised. One run takes about 2 min.
3. **Infill.** Walls are 3 mm thick. Four perimeters at 0.45 mm put 1.8 mm of solid skin on each face, so a 3 mm wall prints fully solid. Infill only exists in the thick features, mainly the 14 mm woofer baffle land.
   - Elements whose centroid is more than 1.8 mm from every surface are assigned a **40 % gyroid core**.
   - The core properties come from Gibson–Ashby with a bending-dominated exponent of 2: E = 2.1 × 0.4² = 0.34 GPa and ρ = 508 kg/m³.
   - This applies to 7.7 % of the elements.
4. **Lumped masses.** Woofer and PR masses are spread as point masses over the nodes they are bolted to:
   - each woofer over its flange footprint on the inner face of the land (y = −30.4);
   - each PR over its flange annulus on the cap.
   - The battery is optional. When included, it is spread over the inner face of the tray's front wall, which couples it rigidly.
5. **Excitation indices.** Each mode gets an index in dB, relative to the volume velocity of the two woofer cones, evaluated at the modal resonance. Two drive paths are considered:
   - **Box pressure:** the lumped box pressure acts on the skin. This path is valid below about 800 Hz, the first axial box mode.
   - **Cone reaction:** the inertial reaction force of each cone (Mms·ω²·x) acts on its land, with both woofers in phase.

   The modal "radiator strength" is the net outward volume displacement of the outer skin, Vm = ∮φ·n dA.
6. **Combined response.** A modal-superposition FRF adds both paths with their phases. The result is the shell's net outward volume velocity relative to the woofers' (`a4_shell_vs_woofer_output`). As a rule of thumb, −20 dB means about ±1 dB of ripple in the summed output.

### Cases

| Case | Description |
|---|---|
| **Main** | Tied assembly, free-free (on a desk the speaker sits on soft feet), 40 % core, woofer and PR masses |
| Sensitivities | 100 % solid; no driver masses; battery rigidly coupled; a finer 2.8 mm mesh |
| Bounding cases, single parts | Rear shell with seam and end edges clamped (upper bound) |
| | Rear shell held only at its 4 seam screws and 4 cap-screw bosses (lower bound) |
| | Front shell with seam and ends clamped, woofers included |
| | End cap with its rim clamped, PR included |
| What-ifs (FE model only, the CAD is untouched) | Top-arc ribs, tray gussets, a centre spine plate, cap gussets |

### Assumptions and limitations

- **Isotropic PETG.** Real prints are layered: the shells print standing on end, so the layers are normal to the capsule axis. Inter-layer stiffness is about 10–20 % lower, which would lower the frequencies by about 5–10 %.
- **Joints are tied.** The gasketed seam with only 4 screws is in reality softer, and joints add damping.
- **Woofers are translational point masses.** The model has no rotary inertia and treats the frames as rigid. The real motor sits about 25 mm behind the flange, so the woofer-rocking modes (434–635 Hz) will be **lower** in reality.
- **Items not modelled:**
  - the grille (bonded aluminium; it adds mass and stiffness to the front);
  - the PCBs, wiring and polyfill;
  - fluid loading, which lowers panel frequencies by a few %.
- **Damping:** the loss factor is assumed to be η = 0.03 (ζ = 1.5 %) for printed PETG. Every resonant index scales as 1/η: doubling η gives −6 dB.
- **Effective modal mass is not used.** It is zero for the flexible modes of a free-free body, so it carries no information here. The volume-displacement indices replace it.
- **The indices are upper-bound flavoured.** Each mode is assumed to be driven exactly at resonance.

### Validation

**Against an analytic case.** A fully clamped 100 × 100 × 3 mm PETG plate was meshed with the same element type and sizes and compared with Leissa's thin-plate eigenvalues (λ = 35.985, 73.394, 73.394, 108.22, 131.58, 132.20 → f₁ = 689.5 Hz).

| Mesh | f₁ | Error, f₁ | Error, modes 1–6 |
|---|---|---|---|
| Production mesh, h = 3.5 mm | 691.1 Hz | +0.2 % | within 1.5 % |
| h = 2.5 mm | — | — | −0.2 … −1.9 % |
| h = 1.5 mm | 685.5 Hz | — | −0.6 … −2.6 % |

As the mesh is refined, the FE frequencies settle slightly *below* thin-plate theory. That is expected: thin-plate (Kirchhoff) theory ignores shear deformation and rotary inertia, and their effect grows with mode order. The production mesh is therefore at most about 1.1 % stiff.

**Assembly convergence.** Going from a 3.5 mm to a 2.8 mm mesh (167 k → 232 k nodes) changes the first 8 frequencies by ≤ 0.4 %.

### Results

| Case | Lowest modes (Hz) | Modes < 1 kHz | Shell/woofer output, max (50 Hz–2.5 kHz) |
|---|---|---|---|
| Shell only, 100 % solid | 446, 529, 824, 965 | 6 | −5 dB at 529 Hz (no woofer mass on the land) |
| Shell only, 40 % core | 446, 529, 839, 891 | 6 | −2 dB at 529 Hz |
| **Main: 40 % core + woofer/PR masses** | **269, 334, 434, 465, 526, 550** | **24** | **−25 dB at 861 Hz** |
| Main + battery rigidly coupled | 211, 240, 324, 344 | 30 | −23 dB at 240 Hz |
| Front shell alone, edges clamped, woofers | 306, 373, 470 | 11 | — |
| Rear shell + tray alone, edges clamped / screws only | 1153 / 686 | 0 / 2 | — |
| End cap + PR, rim clamped | 1072, 1167, 1196 | 0 | — |

**What the main-case modes are** (see `a4_mode_shapes_main_assembly`):

| Frequency | Mode | Index |
|---|---|---|
| 269 Hz | n = 2 **ovalling** of the tube cross-section, loaded by the 2 × 181 g woofers on the front land | −46 dB |
| **334 Hz** | Front–back squash with the top and bottom bulging. Both woofer lands move in phase in y, so this is the **most strongly driven low mode**. Peak skin motion at the top, near the display and buttons, reaches −8 dB re cone excursion. | −33 dB |
| 434, 465, 550, 607 Hz | Woofers **rocking** on the land (L/R antisymmetric). Net radiation is negligible, but local motion reaches −10 to −20 dB re cone. | ≤ −60 dB |
| 561, 602, 722–732 Hz | End regions, end caps and tweeter shoulders | −26 to −60 dB |
| 859 Hz | End region | −25 dB |

**Bottom line.** The shell has **many modes in the woofer band (24 below 1 kHz)**, but their net acoustic output stays **≤ −23 to −25 dB re the woofers**, which is **under ±0.5 dB of ripple**.

- The real risks are **local**: buzz and rattle of the top UI area, the lens, the knob, and the battery in its tray around 210–350 Hz.
- Without the woofers' own mass on the land, the bare shell has a 529 Hz mode that the cone reaction could drive to −2 dB. **The heavy driver frames are what keeps this benign**, so the woofer must be bolted hard to the land. The 1 mm foam ring under the frame must be thin and fully compressed.
- **Wall flex adds only 0.13–0.21 % to the box compliance.** It is negligible for the A1 bass alignment.

**What-ifs** (all with the main masses):

| Change (FE model only) | Lowest modes (Hz) | Shell/woofer max | Peak local motion < 1 kHz |
|---|---|---|---|
| Main (baseline) | 269, 334 | −25 dB | −7.9 dB |
| + top-arc ribs at x = ±40 (5 × 3 mm, φ ≈ 40–117°) | 274, 350 | −24 dB | −9.0 dB |
| + tray gussets (4 plates tying the tray top and bottom walls to the rear shell, x = ±30) | 275, 365 | −24 dB | −9.0 dB |
| **+ centre spine plate** (x = 0, 1.6 mm, in the 2 mm gap between the woofer flanges, from the land back to the tray front wall, z −20…+24) | **447, 459** | −19 dB at 582 Hz | −9.3 dB |
| Spine + top ribs + tray gussets + 10 cap gussets ("all braces") | 450, 466 | −22 dB at 505 Hz | −10.1 dB |
| Battery coupled: baseline → spine + top + gussets | 211 → **339** | −23 → −22 dB | −9.6 → −14.5 dB |

The spine plate is the only change that moves the low modes a lot. It removes the 269/334 Hz ovalling and squash modes and **raises the first mode by 66 %, to about 450 Hz**. None of the braces lower the net shell output, which is already small. They do push stiffness up and local motion down by 1–7 dB, and the 3–5 mm ribs barely move anything.

### Recommendations

These are not yet in the CAD. They are listed in priority order.

1. **Centre spine plate.**
   - **What:** 1.6 mm thick, at x = 0, printed with the front shell, running from the inner face of the baffle land (y = −30.4) to the battery-tray front wall (y = 15.6), z −20…+24.
   - **Clearances:** it fits the 2 mm gap between the woofer flanges. The baskets are ≥ 7 mm away and the motors ≥ 14 mm. It stays clear of the 10.5 mm bulk cap and the UI paddle.
   - **Fixing:** end it in a slot in the tray front wall, bonded (the FE treats it as bonded).
   - **Effect:** first mode 269 → 447 Hz. The woofer land no longer "breathes" with the tube at about 330 Hz.
   - **Check:** confirm wiring routes around it.
2. **Battery retention plus tray gussets.**
   - The battery is foam-clamped. With 1 mm foam the mount resonance is estimated at about 0.5 kHz, so the pack is partly coupled.
   - Use firm foam on all faces and a strap.
   - Add 4 × 2.5 mm gussets from the tray's top and bottom walls to the rear shell at x = ±30. The bottom pair should start at y ≥ 27 to clear the main board.
   - With the spine, this lifts the battery-coupled modes from 211/240 Hz to 339/372 Hz and cuts peak local motion by 5 dB.
3. **Damping before more ribs.**
   - A 1.5–2 mm butyl or bitumen pad, or a constrained-layer patch, on the inside of the top flat (under the UI) and the bottom flat. These are the antinodes of the 334/495–507 Hz modes.
   - Raising η from 0.03 to about 0.1 lowers *every* resonant term by about 10 dB, which is more than any rib achieves here.
   - Polyfill helps the box modes above 800 Hz.
4. **Optional, small effect.**
   - Top-arc ribs at x = ±40: +16 Hz on the top mode.
   - Radial cap gussets at φ = 120/180/240/315/−15°: +25 Hz on the cap/shoulder mode.
   - Only add them if a tap test or accelerometer measurement shows a problem.
5. **Bolt the woofers hard to the land.** The woofers' 181 g mass is what keeps the land modes benign.
6. **Verify on the prototype.**
   - Do a tap test, or put a sweep through the woofers and measure with a phone accelerometer or contact mic, on the top, the bottom flat and the caps.
   - Check for buzz at 200–700 Hz at full level.
   - Expect the measured frequencies to be about 5–15 % lower than computed (layer anisotropy, compliant joints).

### Figures (docs/figures/acoustics/)

- `a4_validation_clamped_plate`: CalculiX C3D10 against Leissa's clamped-plate eigenvalues for three mesh sizes. The error is ≤ 1.5 % at the 3.5 mm production mesh.
- `a4_modal_frequency_map`: every natural frequency per case on a log axis, coloured by excitation index, with the woofer band (to the 2.5 kHz crossover) and the 1 kHz flag marked.
- `a4_shell_vs_woofer_output`: modal-superposition estimate of the shell's net volume velocity relative to the woofers, for the bare shell, the main case, the spine plate and all braces, plus the pressure-only and force-only paths for the main case.
- `a4_mode_shapes_main_assembly`: first six mode shapes of the main case, exaggerated and coloured by |u|. They show ovalling at 269 Hz, the squash mode at 334 Hz, woofer rocking at 434/465/550 Hz and the rear-shell mode at 526 Hz.
- `a4_mode_shapes_all_braces`: first three mode shapes with all braces. The lowest mode is now about 450 Hz, the woofer-rocking mode.

### Data (sim/acoustics/results/)

| File | Contents |
|---|---|
| `a4_modes.json` | Summary per case: frequencies, modes below 1 kHz with index and location, wall-compliance fraction, FRF peak |
| `a4_modes.csv` | Every mode of every case with all indices |
| `a4_modes_raw.json` | Full per-mode data and FRF curves |
| `a4_shell_vs_woofer_output.csv` | FRF curves |
| `a4_validation.json` | Validation results |
| `a4_work/*.dat` | CalculiX eigenvalue output |
| `a4_work/*_modes.npz` | Mesh and first 10 mode shapes for the bare, main and all-braces cases, for later visualisation |

### Talking points

- "We put the 3D-printed body through a full finite-element vibration analysis: half a million degrees of freedom, solved in two minutes on a laptop with free CalculiX. The solver was first checked against a textbook plate result to within 1.5 %."
- "The shell has two dozen resonances in the woofer's range, but the simulation shows they radiate at least 23 dB below the woofers. Adding up all of them shifts the sound by less than half a dB. The heavy woofer frames bolted to the thick front baffle are what keep it quiet."
- "One printed 1.6 mm plate, hidden in a 2 mm gap between the woofers, moves the lowest body resonance from 270 Hz to 450 Hz. For buzz, a strip of damping tape beats more ribs."

---

## A5. Crossover, system response and DSP EQ

**Question.** Through an LR4 crossover near 2.5 kHz, what do the woofer (+PR) and tweeter of one side sum to, on the front axis and at the seated listener? Is 2.5 kHz the right crossover frequency? What EQ should the amp DSP run?

**Inputs.** A1 velocities and bass EQ; the tweeter lumped model; BEM transfer functions of the as-designed capsule. Filters are biquads at **96 kHz, the TAS5805M's DSP rate** (process flow 1 resamples 44.1/48 kHz to 96 kHz). `biquad_export.py` also writes 48 kHz versions.

**Method** (`a5_crossover_system.py`).
- Woofer channel = A1 bass EQ × LR4 low-pass. Tweeter channel = trim × LR4 high-pass × delay × polarity.
- The trim matches the tweeter band (4–10 kHz) to the woofer band (0.4–1.2 kHz) in the 15-seat average on the desk, the intended use.
- Delay and polarity are chosen on the free-field centre-seat axis, searching −200…+200 µs in 5 µs steps and both polarities, so that the sum best equals the in-phase sum |W| + |T| over fx/2…2fx.
- Per-side sum = left woofer + left PR + left tweeter (the box in A1's state).
- System EQ: up to 6 peaking filters plus a high shelf, least-squares fitted to the 1/3-octave-smoothed 15-seat desk average, against a flat target at the 300 Hz–3 kHz level, from 150 Hz to 14 kHz.
- **Cuts up to −12 dB, but the combined boost is held to about +3 dB** (penalty term). Narrow dips from the desk reflection and from left/right interference move with the listener and must not be filled.

**Assumptions.**
- Linear, small-signal models. No room. The desk is an image plane.
- Mono bass in A1's box.
- The response is "per 2.83 V input" before limiter and DRC. A2 and A3 give the per-driver absolute levels.
- The rigid-piston limits (no cone or dome break-up) apply. The ND65-8's aluminium-cone break-up is not modelled. The LR4 low-pass is already 48 dB down two octaves above 2.5 kHz, but measure it.

**Validation.**
- The LR4 sum at the free-field centre seat matches the ideal in-phase sum within 0.05 dB rms over 1.25–5 kHz.
- Each EQ biquad realised at 96 kHz and at 48 kHz agrees within 0.005 dB below 2 kHz. Above that, only the 48 kHz bilinear cramping near Nyquist differs: ≤ 0.4 dB for the EQ, ≤ 0.23 dB for the high-pass. The low-pass differs only in its deep stop band.
- Every encoded TAS5805M word decodes back to its coefficient within 2⁻²⁶.

**Results.**

*Crossover frequency* (each option re-aligned):

| LR4 at | Tweeter trim | Tweeter delay | Sum error re ideal (rms) | Seat-to-seat spread around fx | Deepest vertical dip, −50…+10° re listener | Tweeter excursion at fx/2, 10 V peak input |
|---|---|---|---|---|---|---|
| 2.0 kHz | −10.1 dB | 120 µs | 0.12 dB | 0.55 dB | −3.3 dB | 0.015 mm |
| **2.5 kHz** | **−9.7 dB** | **110 µs** | **0.05 dB** | 0.66 dB | −3.3 dB | 0.011 mm |
| 3.0 kHz | −9.3 dB | 100 µs | 0.04 dB | 0.67 dB | −3.1 dB | 0.008 mm |

The data do not argue for moving the crossover. All three are well behaved: the drivers are 59 mm apart centre-to-centre, below half a wavelength at 2.5 kHz (69 mm), so there is no deep vertical null between −50° and +10°. Going lower costs tweeter excursion and summation accuracy. Going higher pushes the woofer further into its tunnel bump and Le roll-off. **Keep LR4 at 2.5 kHz**, normal polarity, with the tweeter delayed by about 110 µs (10.6 samples at 96 kHz). The tweeter runs about 10 dB below the woofer channel, so the woofer sets the maximum SPL (A1) and the tweeter has a lot of headroom.

*Response per side* (1/6-octave smoothed, 150 Hz–14 kHz, peak-to-peak):

| Position | Before EQ | With EQ |
|---|---|---|
| 15-seat average on the desk (EQ target) | 10.8 dB | **5.0 dB** (σ = 0.9 dB). The remainder is the ~3 kHz desk dip, deliberately left alone. |
| Centre seat on the desk | 16.2 dB | 10.6 dB (desk notches at 2.8 and 9 kHz) |
| Centre seat, free field | 7.2 dB | 7.7 dB: the desk-tuned EQ leaves the free-field baffle step |
| Front axis, 1 m, free field | 8.3 dB | 6.8 dB |

Sensitivity of the EQ'd system: 78.3 dB at 2.83 V per side (15-seat average, desk). The stereo pair with a mono signal is about 6 dB higher at the centre seat. Off-centre (±0.15 to ±0.30 m), mono content combs above about 3 kHz because the two tweeters are 166 mm apart. That is normal for any stereo pair and is absent for real stereo content.

*The DSP EQ per side* (96 kHz; apply to both the woofer and tweeter channels of the side, or keep each filter only in the channel whose band it touches):

| # | Type | fc (Hz) | Q | Gain (dB) |
|---|---|---|---|---|
| 1 | Peaking | 1176 | 1.46 | −2.6 |
| 2 | Peaking | 2494 | 4.44 | +1.9 |
| 3 | Peaking | 3083 | 2.30 | +3.0 |
| 4 | Peaking | 3822 | 4.24 | +2.3 |
| 5 | Peaking | 6029 | 1.88 | −3.3 |
| 6 | Peaking | 12040 | 6.0 | +0.9 |
| 7 | High shelf | 11221 | 0.79 | +4.0 |

Filters 2–4 together add only about +3 dB. They lift the edges of the desk dip and do not fill its centre. Filter 7 compensates the piston/bezel roll-off above 10 kHz. This rests on a rigid-piston model, so **confirm filters 6–7 by measurement** before relying on them. Treat this EQ as the starting point for the REW/UMIK-1 measurement loop, not as final.

**Figures:**
- `a5_crossover_branches_lr4_2k5`: woofer+PR branch, tweeter branch and sum (before EQ) on the front axis and at the free-field centre seat.
- `a5_system_response_per_side_with_eq`: per-side response with EQ at four positions (front axis, listener free field, listener on desk, 15-seat desk average), the average before EQ, and the EQ curve.
- `a5_stereo_pair_mono_at_seats`: both sides with a mono signal, on the desk, at five lateral seats.
- `a5_vertical_lobing_vs_crossover_frequency`: combined woofer+tweeter level in the tweeter's vertical plane relative to the listener direction, for LR4 at 2.0, 2.5 and 3.0 kHz.

**Data:** `results/a5_crossover_system.json` (alignments, comparison, EQ table and SOS), `results/a5_system_responses.csv`.

**Talking points.**
- "We simulated the whole chain, from amplifier volts through driver physics and the 3D body to the listener's ear, before cutting any plastic. The crossover sums within 0.05 dB of ideal at the listening position."
- "The EQ is deliberately modest: about 3 dB of cut or boost. The simulation told us which dips come from the desk and must be left alone."

---

## DSP coefficient export for the TAS5805M

`biquad_export.py` converts every filter above, plus A1's bass EQ, into RBJ-cookbook biquads **at 96 kHz (load these)** and at 48 kHz (reference). It encodes each one with `tools/tas5805m_bq.py`: signed 5.27, big-endian, order b0 b1 b2 −a1 −a2, 20 bytes per biquad, burst-written at the biquad's B0 register. That format was checked against a PPC3 dump. Output: `results/biquads_tas5805m.json` and `.csv` (type, fc, Q, gain, float coefficients and the hex words, for both rates).

| Chain | Biquads (96 kHz) | Notes |
|---|---|---|
| Woofer channel | A1 bass EQ (4: HP 49.8 Hz Q 0.541, HP 49.8 Hz Q 1.307, low shelf 113 Hz Q 1.03 +5.8 dB, peak 65.9 Hz Q 1.40 +2.9 dB) + LR4 LP 2.5 kHz (2 × BW2, Q 0.707) + system EQ (7) | 13 biquads. The A1 EQ was fitted at 48 kHz; re-realised at 96 kHz it differs by < 0.0001 dB |
| Tweeter channel | LR4 HP 2.5 kHz (2) + system EQ (7) | 9 biquads. Also: trim −9.7 dB, polarity normal, delay 110 µs = 10.6 samples at 96 kHz (round to 11) |

Check the biquad count per channel and the register map of the PPC3 process flow that is actually loaded. If biquads run short, keep each system-EQ filter only in the channel whose band it acts on: filter 1 in the woofer channel, filters 2–7 in the tweeter channel.

