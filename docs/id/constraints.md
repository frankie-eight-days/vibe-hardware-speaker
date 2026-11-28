# Industrial design: physics constraints and latitude (v1, 2026-11-27)

This is the brief for the concept designers. It says what the simulations fix, what they leave free, and what each change costs. **HARD** means breaking it fails a requirement or a safety rule. **SOFT** means it can move if the stated cost is paid.

Coordinates are as in `docs/mech_envelope.md`: X runs along the capsule (+X right), −Y is the front (grille side), +Z is up. Today's capsule is Ø95 × 210 mm (216 mm over the PR flanges), with a flat bottom 33 mm wide at Z −44.5.

**New analysis for this note** lives in `sim/acoustics/id_sens/` (no committed script was changed):

| Script | What it does | Output |
|---|---|---|
| `a1_volume_sensitivity.py` | The committed A1 model with changed volume and with leak holes added | `a1_volume_sensitivity.json` |
| `section_check.py` | 2D fit of seven section families around the fixed internal package | `section_check.json`, `section_check.png` |
| `id_quick_estimates.py` | Closed-form or lumped estimates: RF distances, grille loss, flat panels, stability, drop, and a thermal network calibrated to FLOORPLAN §4 | `id_quick_estimates.json` |
| `id_followup.py` | §7 follow-ups: grille cavity resonance, PR halo, octagon section, magnets | `id_followup.json` |

The BEM was **not** re-run, because each case takes 33–75 min. Wherever a shape change would need BEM, the row says so.

## 1. Acoustics

| Constraint | Value | Source | H/S | Latitude: what a change costs |
|---|---|---|---|---|
| Net internal volume | 0.848 L by CAD; 0.82 L planned | `mech/concept/build/report.json`; `docs/mech_envelope.md` §5 | **HARD floor ≈ 0.65 L** | See the sensitivity table below. The pink-noise maximum has only **0.55 dB** of margin over the 90 dB requirement. |
| Volume per mm of length | +6.2 cm³/mm (+0.75 %/mm) | inner section 61.6 cm² (`section_check.json`) | SOFT | +10 mm of length gives +7.5 % volume and about +0.12 dB pink. Tube parts still print up to 218 mm. |
| PR placement | One DMA58-PR on each end cap. Flange 56 × 56 mm, 3 mm proud. Ø50.5 hole on a 64.3 mm bolt circle | `mech_envelope.md` §0/§2; requirement "PRs on end caps (visible)" | HARD | The PRs carry the output below about 60 Hz (A1). The end caps must stay ≥ 62 × 62 mm flat around the PR. |
| PR excursion clearance | Inside: keep-out X ±57.5…68, r < 11 (1.5 × Xmech 7 mm). Outside: the diaphragm moves ±7 mm | `report.json` `pr_keepout_x`; `research/drivers.json` | HARD | Any guard, bumper or grille in front of a PR must sit **≥ 10.5 mm** from the diaphragm's rest plane and be acoustically open. At maximum sine level the PR reaches its 5 mm model limit at 48 Hz (`a1_excursion_vs_xmax`). |
| Woofer spacing and baffle | Centres 66 mm apart (frames 2 mm apart), rear-mounted on a land at Y −30.4 | `mech_envelope.md` §0 | HARD | Cannot move: in X the PR keep-out sets it (1.6 mm margin). |
| Woofer front (baffle step) | On the round Ø95 front the step is smooth, with 0.36 dB ripple from 150 Hz to 2.5 kHz | A3, `results/a3_woofer_diffraction.json` | SOFT | A flat front was **not simulated**. Rule of thumb: edge radius ≥ 15–20 mm. Verify with A3 (bezel case, ~33 min). On a desk the desk itself cancels the step. |
| Woofer tunnel | Mean depth 11.7 mm (13.6 mm at the centre) gives +3–4 dB at 2.5–3.8 kHz; A3 says keep it | A3, `a3_woofer_tunnel_effect` | SOFT | The outer front must sit at Y ≤ −41.0 over \|Z\| ≤ 23 (cone at 1.5 × Xmax + 1 mm + 0.8 mm grille). Going from 13.6 to about 7 mm loses most of the bump; the fix is about +3 dB of EQ plus an A3/A5 re-run. |
| Tweeter angle and bezel | Axis 40° up (requirement 35–45°), X ±83 (166 mm apart), 3 mm conical bezel on a Ø36 boss | A2, `a2_tweeter_directivity.json` | HARD (angle, spacing); SOFT (boss) | Any feature within about 25 mm of the dome: a 3 mm lip adds **2.1 dB** of on-axis ripple, a 10 mm one (the waveguide) **4.7 dB**. Keep reliefs ≤ 3 mm. The knob 13 mm from the right tweeter already costs up to 1.5 dB of L/R pattern asymmetry (BEM mirror check). |
| Desk notch | About 2.8 kHz, −15 dB at the centre seat; tweeter face about 75 mm above the desk | A2 | – | **ID cannot fix it.** The first null is f ≈ c·D/(4·h_t·h_ear) ∝ 1/h_t, so 10 mm feet move it only about 10 %. A2 suggests a 5–10° backward tilt, but that takes the tweeter axis outside the 35–45° row and needs a BEM re-run. |
| Grille | 0.8 mm perforated Al over the woofers only, φ −45…+58°, in a 0.8 mm recess | `mech_envelope.md` §3; BEM treats it as transparent | SOFT | Insertion loss (`id_quick_estimates.json`): Ø2 mm holes at 40 % open: 0.07 / 0.28 / 0.68 dB at 5 / 10 / 16 kHz. Ø1.5 mm at 23 %: 0.26 / 0.95 / 2.1 dB. Over the woofers alone (≤ 4 kHz) ≥ 20 % open is fine. **Over a tweeter**: ≥ 51 % open with ≤ 2 mm to the dome, or cloth (the grille-cavity resonance governs, §7 Q1/Q2). A 3 mm-thick printed grille loses 2 dB at 10 kHz. |
| Panel stiffness | 24 shell modes below 1 kHz, all ≥ 23 dB below the woofers. First mode 269 Hz (ovalling); 447 Hz with the 1.6 mm spine plate | A4, `results/a4_modes.json` | SOFT | Curvature does the work. **Flat 3 mm strips** (clamped/SS f1; peak output re woofer): 50 mm wide → 1.7 k/0.76 kHz, −21 dB; 60 mm → 1.2 k/0.53 kHz, −13 dB; 80 mm → 670/295 Hz, **−0.5 dB**. At 4 mm wall, 60 mm → −20 dB. So: flats ≤ 50 mm at 3 mm, or rib them at ≤ 50 mm pitch. Damping pads (η 0.03 → 0.1) gain about 10 dB, more than any rib. Bolt the woofers hard to the land. |
| Seal | Q_L 10 assumed | A1 | **HARD** | **One unsealed hole:** Ø0.5 mm → 90.52 dB; Ø1 mm → 90.15 dB; Ø1.5 mm → 89.69 dB (**fails**); Ø2 mm → 88.88 dB. Every port must be gasketed to the outside only: mic, USB-C, encoder, buttons, seams. |

**Volume sensitivity.** This is the committed A1 model at Q_L 10, with the PR mass held at 3.5 g and the EQ re-fitted unless stated (`a1_volume_sensitivity.json`).

| Net volume | fb | F3/F6 with EQ | Max EQ boost | Pink max (limit) | Sine max at 50 Hz | If the EQ is NOT re-tuned: F3/F6 |
|---|---|---|---|---|---|---|
| −20 % (0.656 L) | 57.3 Hz | 63.4 / 55.4 | 9.7 dB | **90.05** (amp V) | 76.3 dB | 67.2 / 57.6 (**fails F3**) |
| −10 % (0.738 L) | 55.1 | 63.4 / 55.4 | 9.2 | 90.35 | 77.3 | 65.0 / 56.4 (edge) |
| **0.82 L** | 53.2 | 63.4 / 55.4 | 8.8 | **90.55** | 78.2 | – |
| +10 % (0.902 L) | 51.7 | 63.5 / 55.5 | 8.5 | 90.70 | 79.0 | 62.4 / 54.8 |
| +20 % (0.984 L) | 50.3 | 63.5 / 55.5 | 8.3 | 90.81 | 79.8 | 61.6 / 54.2 |

At −30 % (0.574 L) the system becomes PR-excursion-limited at 89.1 dB. The EQ can always reach F3 ≈ 64 Hz; what volume buys is headroom.

## 2. Thermal

`thermal.py` assumes 45 °C box air and a 0.08–0.17 W/K board-to-air path. ECO-003 #2 (gap pads) assumes an ideal 45 °C sink.

For this note I built a lumped network: board → pads → spreader → room air, plus board → box air → PETG shell → room air. It is calibrated to FLOORPLAN §4:

- junction to sink, per amp: 16.6 K/W;
- U901 (no pad): 55.7 K/W;
- shell: 0.244 W/K;
- h = 10 W/m²K for emissive outer surfaces, 5 W/m²K for bright aluminium.

The touch limit is ≤ 48 °C for metal and ≤ 60 °C for plastic, my reading of IEC 62368-1 TS1 for 1–10 min contact; verify before relying on it.

**Sustained output with every Tj ≤ 125 °C (W)**, room 25 °C / 35 °C:

| Heat path for the pads (3 pads, as ECO-003) | Area | Thermal limit | With the touch limit | With a 4th pad under U901 |
|---|---|---|---|---|
| No pads (v1 without ECO-003 #2) | – | 11.7 / 9.4 | – | – |
| Al spreader loose in the box air | 100 cm² | 18.0 / 15.7 | same | 27.8 / 23.9 |
| **Hidden Al spreader bonded inside the PETG wall** | 100 cm² | **23.2 / 20.5** | 23.2 / 18.4 (plastic skin) | **≥ 40 / 35.9** |
| Same | 200 cm² | 26.9 / 24.0 | same | ≥ 40 |
| Exposed Al, anodised or painted (ε ≈ 0.85) | 100 cm² | 23.9 / 21.2 | **14.3 / 3.3** | ≥ 40 / 38 |
| Same | 200 cm² | 27.6 / 24.6 | 27.6 / 12.3 | ≥ 40 |
| Exposed **bright** Al (ε ≈ 0.05) | 100 cm² | 20.6 / 18.1 | **6.9 / 0** | 34 / 30 |

**Honest reading:**

- A 3 mm PETG wall costs only 1.5 K·W⁻¹ per 100 cm², against 10 K·W⁻¹ per 100 cm² for the outside air film. So **exposing the metal buys about 3 %**, and it moves the touch limit onto the metal.
- The physics wants a ~100 cm² aluminium spreader under the board, bonded to the floor. It can be visible or not. It wants a 4th pad under U901 more than it wants more area.
- A visible metal base is legitimate only if it is emissive (anodised/painted), ≥ 200 cm² or not touched in use (underside), and clear of the antenna (§3).
- **Vents are not allowed:** the box is sealed (§1). Fins on an exposed underside plate are valid, at about +0.1 W/K per 100 cm² of emissive area.
- Firmware caps the long-term average at ~12 W (ECO-003 #1). At 12 W a 100 cm² hidden spreader runs at 48 °C and the box air at 35 °C (room 25 °C).
- Geometry: the landings face down. The board bottom is at Z −35 and the inner floor at −41.5, so the spreader needs about 3.5 mm pedestals for 1 mm pads.

## 3. RF (ESP32-WROVER antenna, floor plan v1)

The antenna area is X 88.2…94.5, Y −20…−2, Z ≈ −33 (`hw/experiments/floorplan_v1/mech/mech_inputs_fp1.json`). The rule is no metal within 15 mm (Espressif HDG via `docs/spec_signal.md` §1.6). Distances are from `id_quick_estimates.json`:

| Item | Distance | Verdict |
|---|---|---|
| Grille as drawn (φ −45…58°, X ±96) | **13.1 mm** | **Violates.** Cut it to \|X\| ≤ 80 (15.4 mm) or \|X\| ≤ 72 (20.8 mm), or start it at φ ≥ −30° for X > 70 (22.5 mm). |
| Right end-cap screw boss at φ 270° (brass insert) | **6.8 mm** | Move it to φ ≥ 200°, or use a plastic snap. |
| Main-board hole H3 (84.5, 3.0): screw and insert | **5.0 mm** | Use a nylon screw and a plain printed boss. |
| Metal right end cap, or a metal trim ring below the axis | 6.5 mm | **Not allowed:** the right end cap must stay plastic. |
| Metal base plate under the antenna (Z −44.5) | 11.1 mm | The plate must stop at X ≤ 73. |
| PR-R basket (r 25) / PR-R diaphragm | 7.7 / 13.9 mm | Inherent. Check the materials (DMA = aluminium cone, verify). RSSI-test the first print. The fallback is WROVER-IE with a U.FL flex antenna (`spec_signal.md` §1.6). |
| Woofer-R frame, tweeter R, PR washers | 23 / 52 / 30 mm | OK |

**Must stay plastic** (no metal, metallic paint or metallised film): the right end cap and the shell region X > 73 with φ < −20° (front-bottom-right), which is the region within 15 mm of the antenna. The left end has no RF constraint.

## 4. Packaging

| Item | Value | Source | H/S |
|---|---|---|---|
| Drivers | 2× ND65-8 woofer (64 sq flange, 48 deep), 2× OT19NC00 tweeter (Ø33.4 face, sealed pod Ø35 × 21.5), 2× DMA58-PR | `speaker_concept.py` P-block | HARD |
| Battery | 109 × 42 × 19.5 mm (±5/±2/±2), +10 % swell, standing upright behind the motors, Y 15.6…39.05, with a 2 mm puncture wall at the front | `mech_envelope.md` §1.1 | HARD |
| Main board | 142.8 × 46 mm at Z −35, enclosure X −54.6…+88.2, 5 standoffs; ≥ 6.5 mm below it for the pads | `FLOORPLAN.md` §1/§6 | HARD |
| UI board | 182 × 31 mm (+ display paddle) at Z 33.4–35. The FFC is 100 mm (150 mm option C64775) | `spec_ui_board.md`, `mech_envelope.md` §7 | HARD (FFC length is SOFT) |
| Harnesses | Battery leads exit −X (flip the pack); tweeter L +75 mm, R +45 mm vs rev A | `FLOORPLAN.md` §6 | SOFT |
| Length | 210 mm body / 216 mm over the PRs. The tube prints on end: ≤ 218 mm on the 220 mm bed | `mech_envelope.md` §0 | Min HARD; +8 mm SOFT |
| **Section hard points** (inner skin must enclose them) | Woofer-flange corners (−30.4, ±32.5); battery corners (37.1, ±23) and (39.05, ±21); board corners (−21/+25, −35); floor (±16, −41.5); UI parts (−9/+20, 39). Outer skin: (0, 47.5) display lens and (−41, ±23) cone/grille | `section_check.py` | HARD |

**Section shapes**, each the minimum outer area that encloses the hard points (`section_check.png`):

| Family | Outer depth × height (mm) | Desk flat | Net volume vs today | Tweeter pod |
|---|---|---|---|---|
| Today's circle | 95 × 92 | 33 mm | 0 | Boss 3.1 mm proud, 1.0 mm to the PR |
| Oval / squircle (n = 2.1) / D-egg | 93–95 × 92 | 33–35 | −0.4 to −1.4 % | Same (pod ≤ 0.3 mm tighter) |
| **Rounded rectangle (pill), r 23.5 corners** | **84 × 92** | 34 | +1.3 % | Boss 5.3 mm proud; touches the UI board's front edge (trim it). Needs the shortened tunnel (§1) |
| Softened triangle, flat base | 107 × 94 | 32 | +18 % | Tweeter drops to 62 mm above the desk |

**Conclusion.** The package is already round. Any convex section that passes the hard points costs ≤ 1.5 % of volume, so **section shape is a free style choice**. Nothing gets smaller in section except front-to-back depth (to 84 mm), and only by trading the woofer tunnel.

**Mechanics** (estimates; total ≈ 1.21 kg, CG 45 mm above the desk):

| Topic | Value | Latitude |
|---|---|---|
| Stability | 33 mm flat: tips at 18.7°, or with 1.7 N sideways at the knob top. 55 mm flat: 30°, 3.0 N | Flat or feet span ≥ 50 mm recommended (SOFT). The round body rolls away once tipped. |
| Carry | 4 × weight = **47.5 N** static per strap anchor (IEC 62368-1 handle test, verify) | Anchor to the rear shell or the seam screws, never the end caps. Load in the layer plane, through a metal insert or plate. |
| Drop, 1 m | Battery and woofer loads: 930 / 890 N at 2 mm crush; **370 / 355 N** at 5 mm crush | The PR flanges stand 3 mm proud and are the first impact point on an end drop. |

## 5. UI

| Element | Position (X) | Movable? | Physics |
|---|---|---|---|
| Round display | 0, top; lens top at Z 47.5 on a pad (+4 mm at \|Y\| = 20 on the circle; flush on the pill) | X: yes, along the UI board | The 334 Hz squash mode moves the top at −8 dB re cone excursion (A4). Bond the lens with foam; add damping pads. |
| Encoder and knob (Ø26 × 13) | +70 | Yes. Moving it to \|X\| ≤ 50 removes the 1.5 dB L/R tweeter asymmetry | Seal it (O-ring or cup): the EC11 is not airtight. |
| 3 buttons + recessed power | −60/−72/−84; power −46 (1 mm below the skin) | Yes, along the top. **Not on the end caps** (PRs). | Silicone membrane: no open holes (§1 seal). |
| MEMS mic, Ø1 port | −30, top, bottom-port T3902 | Yes, on the top | The port gasket must seal to the outside only: an unsealed Ø1 mm port costs −0.4 dB of pink (§1). Keep it ≥ 20 mm from the encoder (detent clicks). Soft-gasket it against top-shell vibration. |

## 6. Printability (Adventurer 5M Pro, PETG/ASA)

| Rule | Value | Consequence for ID |
|---|---|---|
| Build volume | 220³; tube parts print standing on end (202 tall today) | The cross-section prints **in the layer plane**, so any section shape is free, with no stair-steps or supports. Changes **along X** (tapers, swells, end chamfers) cost overhang and stair-stepping. Keep those ≥ 45° from horizontal. |
| Walls | ≥ 3 mm, 4 perimeters (a 3 mm wall prints solid); the land is 40 % gyroid | Flats per §1 |
| Split lines | Seam at Y +24 (φ ≈ ±120°, behind the display); caps at X ±99 with a gasketed spigot | Seams must sit on gasket lands. A deliberate shadow-gap (0.5–1 mm reveal) hides the seam better than a flush joint. |
| Visible surfaces | Tube: fine circumferential layer rings. Cap outer faces print face-down on the bed (textured PEI gives the best surface). | Put premium finish on the cap faces and on surfaces whose normal is ⊥ X. Avoid large top-facing near-horizontal surfaces on the tube. |
| Inserts | M3 heat-set, Ø4.0 hole, boss ≥ Ø8; ≥ 15 mm from the antenna (§3) | – |
| Fabric/metal inserts | FDM ±0.2–0.3 mm. Leave 0.3 mm per side plus a 0.8 mm recess (grille detail today) | Fabric over the antenna corner is RF-safe. |

## 7. Follow-up answers for `docs/id/benchmark.md` §4/§5

Source for this section: `sim/acoustics/id_sens/id_followup.py` → `id_followup.json`. These are closed-form and lumped estimates, except the tweeter-angle row, which uses the committed A2 BEM polar.

**Q1. Grille open area.** The "cavity f0" is the grille's mass resonating on the air gap behind it. Below about f0/2 it lifts the response by up to about 2.5 dB (undamped bound). Above f0 the response falls about 12 dB/oct. For the tweeter band to stay clean, f0 must be ≥ 24 kHz.

| Grille | IL 2.5 / 5 / 10 / 16 kHz (dB) | Cavity f0: woofer tunnel 12 mm | Cavity f0: tweeter gap 2 / 3 / 4 mm | Plate mode over a Ø53 bore | Over woofers | Over tweeters |
|---|---|---|---|---|---|---|
| Fine 23 % (Ø1.6, 0.81 mm) | 0.07 / 0.27 / **1.0 / 2.2** | 6.7 kHz | **16.4 / 13.4 / 11.6 kHz** | 2.6 kHz | **OK.** f0 sits 1.4 oct above the 2.5 kHz LR4 (woofer ≥ 40 dB down there) | **No.** f0 lands inside the band: a peak, then a 12 dB/oct roll-off, plus 2.2 dB IL at 16 kHz |
| Mid 40 % (Ø3.2, 0.81 mm) | 0.02 / 0.10 / 0.38 / 0.92 | 8.7 kHz | 21.2 / 17.3 / 15.0 kHz | 2.3 kHz | OK | Marginal: only with a ≤ 2 mm gap, plus EQ |
| Open 51 % (Ø4.8, 0.81 mm) | 0.01 / 0.06 / 0.23 / 0.57 | 9.9 kHz | **24.2** / 19.7 / 17.1 kHz | 2.0 kHz | OK | **OK** at a ≤ 2 mm gap (IL 0.6 dB at 16 kHz) |
| Grille cloth (resistive) | Flat: 0.21 / 0.41 / 0.81 / 1.45 dB at 20 / 40 / 80 / 150 Pa·s/m | No resonance | No resonance | — | OK | **Best for tweeters** at ≤ 40 Pa·s/m flow resistance (~0.4 dB). Test it by blowing through it. PE cloth is not flame-retardant. |

The **sheet's own plate mode (2.0–2.6 kHz) sits on top of the crossover**, so it is a buzz risk at any open area. Bond the grille to the land all round each woofer bore (VHB ring) and between the bores. Curvature or bends raise the mode.

| Q2. Tweeters behind a continuous grille (instead of the Ø38 clearance holes) | Value | H/S |
|---|---|---|
| Geometry | The Ø36 boss stands up to 6 mm proud, so it must go. The faceplate then sits flush under the grille with the dome ≤ 2 mm behind it. That removes the 3 mm bezel lip, which A2 charges with about 2 dB of on-axis ripple. | SOFT |
| Cost: 51 % metal or ≤ 40 Pa·s/m cloth | ≤ 0.6 dB at 16 kHz; f0 ≥ 24 kHz. The A5 high shelf (+4 dB at 11 kHz) absorbs it. | SOFT |
| Cost: 40 % metal | f0 17–21 kHz: about +1–2 dB at 8–12 kHz, then a roll-off. Needs re-EQ after measurement. | SOFT |
| Cost: 23 % metal | f0 11.6–16 kHz: in-band resonance, then −12 dB/oct. **Not acceptable.** | HARD |
| Directivity | Flush-under-grille was not simulated. Expect it closer to the "infinite baffle" case (0.6 dB ripple) than the bezel case, but **re-run the A2 bezel case without the boss (~33 min)** before committing. | SOFT |
| RF | The tweeter shoulder (X 83, φ 40°) is 52 mm from the antenna, so a grille there is fine. The lower edge rule from §3 still applies. | — |

| Q3. TPU halo or bumper around each PR | Value | H/S |
|---|---|---|
| Radial | Ring ID ≥ **52 mm** if it sits on the flange (surround about Ø50 plus 1 mm each side), or ≥ **78 mm** if it surrounds the flange (56 sq, diagonal ~77 mm), plus screw access | HARD |
| Axial, protection only | Front face ≥ 3 mm beyond the highest point of the PR surround at rest (measure the PR). Not a stand-on surface. | SOFT |
| Axial, if the speaker may rest or play on the halo (on end, or against a wall) | ≥ **10.5 mm** (1.5 × Xmech 7 mm) beyond the surround at rest, **plus** notches of ≥ **3 cm²** total (7 m/s peak at the PR limit; 1 cm² gives 22 m/s and chuffs). A sealed ring against a surface makes a 13–77 cm³ cavity that stiffens the PR **9–56×**, which kills the bass. | HARD |
| Loading | The air plug inside the ring is 0.005–0.009 g, ≤ 0.09 % of the 10.2 g PR moving mass, so fb shifts by < 0.05 %. No radiation effect: λ ≥ 2 m at the PR's working band, and above 150 Hz the PRs contribute nothing (A3). | — |
| Length | Each halo adds its proud height to the 216 mm overall. It must be a separate part, or the cap still prints face-down. The right halo must be non-metal (antenna, §3). | SOFT |

**Q4. Rounded regular octagon** (outer R 6 corners, 47.5 mm inradius, front facet woofers, 45° tweeter facets):

| Quantity | Octagon | Today's circle | Verdict |
|---|---|---|---|
| Minimum inner inradius | **44.48 mm**: the woofer-flange corner (−30.4, 32.5) lies on the 45° facet | 44.5 | HARD: it **cannot shrink**; this is the smallest regular octagon |
| Envelope | 95 across flats (height, with no extra flat cut), **101.8 across corners** | 95 × 92 | — |
| Net volume | **+82 cm³ (+10 %)**: pink +0.15 dB, sine +0.8 dB at 50 Hz | 0 | Good |
| Woofer front | The straight front facet is only **34.4 mm** wide, so the Ø53 bore (+chamfer) crosses both facet edges. The grille's bend lines cross the bores. Mean tunnel depth 13.5 vs 12.2 mm (same method): the bump moves about 10 % lower, roughly the same size. | – | OK; cosmetic detail at the bore |
| PR annulus | Unchanged at the tweeter (facet centre at 47.5 mm, pod 1.0 mm from the PR basket). +3.4 mm at the corners (φ 22.5°/67.5°). The end cap fits the 56 mm flange with ≥ 19 mm to spare. | 22.5 mm | OK |
| Tweeter pod at 45° | 1.0 mm to the PR basket, **0.0 mm to the UI board** envelope (1.9 mm today): trim the UI board's front edge by 2 mm at \|X\| > 65. Face 81 mm above the desk (73 today). | – | SOFT |
| **45° instead of 40°** | The listener moves from 21° to 26° below the axis. A2 BEM polar: Δ = −0.1 / +0.1 / −0.2 / **−0.9 / −1.3 / −1.0 dB** at 2.5 / 5 / 8 / 10 / 12.5 / 16 kHz. | 40° | **Acceptable**: inside the 35–45° row. Costs about 1 dB more HF shelf. Use an irregular octagon with 40° shoulder facets to avoid it. |
| Panels | Facets 34–39 mm wide: f1 ≥ 1.2–2.7 kHz, ≤ −31 dB (§1 strip table). The corners act as ribs. | – | Better than round |
| Top and bottom facets | 34.4 mm straight: the Ø40 lens still needs a raised pad, or a wider top facet (irregular octagon). The desk flat is 34 mm, the same stability as today: add feet ≥ 50 mm. | – | SOFT |

**Q5. N52 Ø1/4" × 1/4" disc magnets.** On-axis field 189 / 86 / 21 / 7.8 / 3.8 / 1.3 mT at 3 / 5 / 10 / 15 / 20 / 30 mm.

| Neighbour | Minimum distance | Why | H/S |
|---|---|---|---|
| PR steel add-mass washers / PR rod (inside, X ≈ ±64–70, r < 10) | **≥ 15 mm** (pull 3 mN, offset 0.008 mm). At 5 mm the pull is 0.8 N and the PR sits **2 mm** off-centre, 40 % of its 5 mm usable stroke. | Or use brass washers for the add-mass | HARD |
| Woofer / tweeter motors and baskets | **≥ 20 mm** (≤ 4 mT, against a ~1 T gap: ΔBl ≪ 0.5 %). Never inside a woofer tunnel or a tweeter bezel. Magnets bonded in the front land are ≥ 35 mm from the woofer motors (fine), but ~10–15 mm from the steel flanges, so they must be captive. | Field and handling | SOFT |
| ESP32 antenna | **≥ 15 mm**: a nickel-plated NdFeB magnet is metal (§3 rule; the field itself does not matter at 2.4 GHz) | RF | HARD |
| Power inductors (L901 boost, L701 charger, amp LC filters) | ≥ 20 mm (≤ 4 mT bias on shielded ferrite) | Inductance and saturation | SOFT |
| Users | Bond or encapsulate the magnets; no loose magnets (ingestion hazard) | Safety | HARD |

**Magnet-free zones:**
1. The right end cap below the axis, and X > 73 at φ < −20° (antenna).
2. Within 15 mm of the PR axis inside the cap.
3. The floor under the board's inductor columns.

Grille-retention magnets in the front land between and outside the woofer bores are fine.

## Physics-driven ID opportunities (ranked)

1. **Thermal floor plate under the board (hidden or underside-visible "keel").** Sustained output goes from 11.7 W to 23 W (100 cm², room 25 °C), and to ≥ 40 W with a 4th pad under U901. It also widens the desk flat to ≥ 50 mm (tip angle 18.7° → ~28°) and lowers the CG. It must stop at X ≤ 73. If visible, it must be anodised (bright Al: touch-limited to 6.9 W).
2. **Elastomer end bumpers** around the PRs, ≥ 5 mm proud of the PR flange, opening ≥ 10.5 mm clear of the diaphragm. A 1 m drop then loads the battery with 370 N instead of 930 N, and they are the natural grip and stand-off for the PR faces.
3. **RF-driven two-material front.** Metal grille over the woofers only (\|X\| ≤ 72 gives 20.8 mm to the antenna); plastic or fabric on the right-front-bottom corner and the whole right cap. Physics makes the asymmetry necessary; ID can make it intentional.
4. **Free section shape** (oval, squircle, D: ±1.5 % volume), or a **pill section 84 mm deep** (+1.3 % volume) with a flat grille front. The flat must be ≤ 50 mm per §1 or ribbed, and the pill costs the woofer tunnel (about +3 dB EQ plus a BEM re-run).
5. **+8 mm of length** within the printer: +6 % volume, +0.1 dB pink, +0.5 dB sine at 50 Hz.
6. **Feet or a flat ≥ 50 mm wide**, decoupled (A4 assumes free-free on soft feet). An optional 5–10° backward tilt (A2) needs a BEM check of the 35–45° tweeter row.
7. **Knob moved inboard** (\|X\| ≤ 50): removes up to 1.5 dB of L/R tweeter pattern asymmetry.

## Things ID must not do

| Don't | Because |
|---|---|
| Add any vent, slot or unsealed hole into the box | Ø1 mm costs −0.40 dB and Ø1.5 mm fails 90 dB; the margin is 0.55 dB (§1) |
| Lose more than ~15 % net volume (hard stop at −20 %) | Pink 90.05 dB at −20 %; the F3 requirement fails at −10 % if the DSP is not re-tuned |
| Put metal within 15 mm of the antenna (grille corner, right end cap, inserts, base plate past X 73) | The grille as drawn is at 13.1 mm, the cap boss at 6.8 mm, H3 at 5.0 mm |
| Cover, load or touch the PRs (handles, buttons, grilles < 10.5 mm away) | Xmech 7 mm; the PRs do all the output below 60 Hz |
| Use flat 3 mm panels wider than 50 mm without ribs | 60 mm reaches −13 dB and 80 mm −0.5 dB re the woofer, against ≤ −23 dB today |
| Raise or sink features > 3 mm within 25 mm of a tweeter dome | 3 mm adds 2.1 dB of ripple, 10 mm adds 4.7 dB |
| Move drivers, change woofer/tweeter spacing (66/166 mm), or change tweeter elevation outside 35–45° | A1–A5 alignment and the crossover rest on them |
| Use a 23 %-open perforated sheet over the tweeters, or a halo that seals the PR against a surface | f0 11.6–16 kHz in-band; a sealed halo stiffens the PR 9–56× (§7) |
| Put magnets within 15 mm of the PR add-mass or the antenna | PR pulled 2 mm off-centre at 5 mm; metal near the antenna (§7) |
| Make a touchable bright-metal surface the heat path | ε 0.05 limits a 100 cm² plate to 6.9 W at the 48 °C touch limit |
| Use a metal or metallic-painted right end cap | 6.5 mm from the antenna |
| Shorten the woofer tunnel "for looks" without the trade | +3–4 dB at 2.5–3.8 kHz is lost; it needs re-EQ and an A3/A5 re-run |
