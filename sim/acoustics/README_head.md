# Acoustic and structural simulations (A1–A5)

This folder holds every acoustic simulation of the portable stereo speaker (driver set B8: 2× Dayton ND65-8 woofers, 2× Peerless OT19NC00-04 tweeters, 2× Dayton DMA58-PR passive radiators, in the Ø95 × 210 mm printed capsule). Each simulation answers one design question. Each was checked against an analytic case before it was trusted, and each writes its numbers to `results/` so later tools can redraw the figures.

| Sim | Question | Tool | Runtime (M4, 10 cores) |
|---|---|---|---|
| A1 | How should the passive radiators be tuned, how loud can the bass go, and what bass EQ reaches F3 ≈ 64 Hz? | Own lumped-element model, checked against electroacPy | ~10 min |
| A2 | Is the 3 mm tweeter bezel good enough, or is a waveguide worth 10 mm more capsule? | Boundary-element method (bempp-cl) on the real capsule shape | part of the BEM sweep |
| A3 | How large are the woofers' baffle step and diffraction ripple, and does the 14 mm woofer tunnel matter? | BEM (same sweep) + lumped tube model | part of the BEM sweep |
| A4 | Do the printed panels resonate where the woofers play? | Finite elements (CalculiX, bundled with FreeCAD) | ~35 min |
| A5 | What do woofer + tweeter sum to through an LR4 crossover, and what DSP EQ flattens it? | A1 + A2/A3 transfer functions + scipy biquads | < 1 min |
| BEM sweep | Pressure everywhere for 1 m/s on each of the six radiators, 100 Hz–16 kHz | `bem_capsule_run.py` | ~1.5 h for all four cases |

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
| `bem_capsule_run.py` | The heavy BEM sweep (cases `bezel`, `waveguide`, `flush`, `bmcheck`) |
| `bem_results.py`, `drivers_lumped.py` | Loader for the sweeps; tweeter model, baffled-piston formulas |
| `a2_tweeter_bem.py`, `a3_woofer_bem.py`, `a5_crossover_system.py` | A2, A3, A5 post-processing and figures |
| `a4_panel_modes.py`, `a4_post.py` | A4 |
| `run_all.sh` | Runs everything in order, one heavy job at a time |
| `pr_alignment_firstpass.py` | Earlier first-pass alignment (19 V rail, 0.75 L), kept for the record |

