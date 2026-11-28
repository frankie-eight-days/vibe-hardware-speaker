# Hand-off: industrial design (ID) phase, 2026-11-28

**Why this phase exists:** the owner saw the floor-plan mock-up in FreeCAD (`mech/concept_fp1/speaker_fp1.FCStd`) and said the plain Ø95 × 210 mm capsule "kind of looks stupid" and needs industrial design grounded in our sims.

## Project state

| Item | State |
|---|---|
| Schematic | v0.3, ERC 0 |
| Board floor plan v1 | Done, tag `floorplan-v1` (`hw/experiments/floorplan_v1/`, its `HANDOFF.md`). 142.8 × 46 mm, 66.9 % top density |
| Owner decisions on the floor plan | **All four approved 2026-11-27:** ECO-003 gap pads, revert C716, accept 66.9 %, flip the battery pack + longer tweeter leads |
| Phase 2 (apply + route 6 layers) | **Approved but paused** until the owner picks an ID concept, since ID may move a mounting hole (e.g. H3 needs a nylon screw, 5 mm from the antenna). **Gate:** stop after the post-layout sims, before fab outputs |
| Floor-plan 3D mock-up | `mech/concept_fp1/` (concept enclosure re-run with the fp1 outline + real KiCad STEP; 0 interferences). `speaker_concept.py` gained a variant mode (`SPEAKER_OUT`, `SPEAKER_PARAMS`) |

## ID work so far

| Step | Output | State |
|---|---|---|
| Benchmark (16 products, FDM finishing, hardware list, 5 directions) | `docs/id/benchmark.md` | Done. Web pages were read from search extracts only; re-check McMaster part numbers |
| Physics constraints from our sims | `docs/id/constraints.md` (§7 = follow-ups: grille open area, tweeters behind a grille, PR halo, octagon, magnets); scripts in `sim/acoustics/id_sens/` | Done |
| Concept A **LATHE** (refined cylinder, woofer-only Al grille, UI strip, knurled knob, hidden/anodised keel) | `mech/id/lathe/`, `docs/figures/id/lathe/`, `docs/id/lathe.md` | **Running** (restarted after a network outage on 2026-11-28 ~06:00 killed it before it wrote files) |
| Concept B **HALO** (TPU PR bumper rings as feet, strap, swappable colour deck) | `mech/id/halo/` … `docs/id/halo.md` | **Running** (same restart) |
| Concept C **FACET** (rounded/irregular octagon, 40° shoulder facets, Al base) | `mech/id/facet/` … `docs/id/facet.md` | **Running** (same restart) |

Each concept delivers a headless FreeCAD parametric model around the fp1 board, a scorecard (volume, interference, RF distance, panel widths, tweeter proximity, PR clearance, seal, stability, printability, mass, BOM), Blender renders (hero, front, top, end, underside, in-context, section) and a one-page `.md`.

## The ten constraints that matter most (details and sources in constraints.md)

1. Net volume 0.82 L. −10 % is OK with a DSP re-tune; floor about 0.65 L.
2. **Sealed box:** no vents. A single Ø1.5 mm leak fails the 90 dB target; gasket every port.
3. **RF:** no metal within 15 mm of the ESP32 antenna (front-right corner). The right end cap stays plastic, metal stops at X ≤ 73, and H3 gets a nylon screw.
4. PRs are fixed on the end caps. Anything in front of them sits ≥ 10.5 mm away and stays acoustically open; if the unit rests on rings, add ≥ 3 cm² of notches.
5. Drivers are fixed (woofers 66 mm apart, tweeters 166 mm at 35–45°). Features within 25 mm of a tweeter stay ≤ 3 mm proud.
6. Flat panels ≤ 50 mm wide at a 3 mm wall, else ribbed, 4 mm or damped.
7. Cross-section shape is free (oval, D, squircle and octagon all fit within ±1.5 %; octagon gives +10 % volume). Keep the woofer tunnel.
8. Grille: 23–51 % open over the woofers, bonded round each bore. Over a tweeter only 51 % at a ≤ 2 mm gap, or cloth.
9. Length ≤ 218 mm (printer 220³; the tube prints on end, so tapers along X cost overhangs).
10. Desk flat or feet ≥ 50 mm wide (today's 33 mm tips at 18.7°). Strap 47.5 N; end bumpers cut drop load 930 → 370 N.

Thermal: a hidden 100 cm² Al plate under the gap pads doubles sustained output (≈ 12 → 23 W). Exposing it doesn't help (touch limit). A 4th gap pad under U901 gives about 40 W.

## Next steps

1. Collect the three concept reports, check their scorecards, and show the owner the renders side by side.
2. The owner picks (or mixes) a concept. Then:
   - fold any board impact (mounting holes, H3 nylon, UI-board trim) into the phase-2 plan;
   - re-run the A2 tweeter BEM (~33 min) if the tweeter boss is removed or the tweeter angle changes;
   - re-run the A1 bass model at the final volume.
3. Resume phase 2 routing (`hw/experiments/floorplan_v1/HANDOFF.md` §4), gated before fab outputs.
4. Later: detailed CAD of the chosen concept, then Blender hero renders for the README and write-up.

## Notes for whoever picks this up

- The agents (`id-lathe`, `id-halo`, `id-facet`) live in the lead's Claude session on the Mac mini. On another machine, re-launch them from the briefs implied above: concept text in `benchmark.md` §5, rules in `constraints.md`.
- The autosave loop (git add/commit/push every 15 min) runs only on the Mac mini. Large files are not ignored: 3D/CAD, meshes and large sim outputs go through **Git LFS** (`.gitattributes`), and the loop LFS-tracks any new file over 10 MB. Clone with git-lfs installed.
- Never text-edit KiCad files. Never touch the owner's open KiCad/FreeCAD windows; agents work headless.
