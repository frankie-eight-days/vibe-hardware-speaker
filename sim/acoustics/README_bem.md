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

Runtimes on the M4: bezel 88 frequencies in 33 min, waveguide 49 in 25 min, flush 65 in 7 min, Burton–Miller check 7 min. Peak memory is about 1.6 GB, at the 10 k-unknown level. The sweep checkpoints each frequency to `results/bem_ckpt_<case>/` and skips finished frequencies on restart. The checkpoints are deleted when the case completes.

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
