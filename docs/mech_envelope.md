# Mechanical concept and PCB envelopes (v0.1, 2026-11-24)

This document covers packaging only. The parts are not print-ready. Everything here comes from the parametric FreeCAD model `mech/concept/speaker_concept.py`, so any number can be regenerated after a parameter change.

| File | What it is |
|---|---|
| `mech/concept/speaker_concept.py` | Headless FreeCAD script. Parameters are at the top. It writes everything below plus `build/report.json` (volumes, interference matrix, clearances, PCB data). Run: `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd mech/concept/speaker_concept.py` |
| `mech/concept/speaker_concept.FCStd`, `.step` | Assembly with one named solid per part (shells, caps, drivers, keep-outs, battery, PCBs, grille) |
| `mech/concept/render_views.py` | pyvista renders. Run: `.venv/bin/python mech/concept/render_views.py` |
| `mech/concept/view_*.png` | Iso, iso with internals, rear iso, front, top, cross-sections at X = 0 / +33 / +83, horizontal sections at Z = +2 and Z = −30 |
| `mech/concept/plot_pcb_envelopes.py` → `mainboard_envelope.png`, `uiboard_envelope.png` | PCB outline, holes, height zones, connector placements, keep-outs |
| `mech/concept/mainboard_outline.dxf/.svg`, `uiboard_outline.dxf/.svg` | Board outlines (Edge.Cuts layer, mm, enclosure X/Y coordinates) plus mounting holes |

**Coordinates (used throughout):** X runs along the capsule axis (+X = right when facing the speaker), −Y is the **front** (grille side), +Z is up. The origin is the capsule centre. Polar angle φ on the cross-section is measured from the front toward the top, so φ = 90° is the top and φ = −90° the bottom.

---

## 0. Results and conflicts with the requirements

| Item | Result |
|---|---|
| Capsule | **Ø95 mm**, body **210 mm**, **216 mm over the two PR flanges** (each stands 3 mm proud of its end cap). Flat bottom: a 33 mm-wide flat at Z = −44.5. Envelope 216 × 95 × 92 mm. The knob adds 14 mm on top and the tweeter bosses up to 6 mm on the front shoulders. |
| Net acoustic volume | **0.85 L** (requirement ≥ 0.50 L, target 0.75 L). See §5. |
| Woofers | 2× ND65-8, rear-mounted on an internal land at Y = −30.4. **Centres 66 mm apart** (X = ±33); the frames are 2 mm apart. |
| Tweeters | 2× OT19NC00-04, **axis 40° up**, on the front-upper shoulders at X = ±83, **166 mm apart**. Each has a sealed printed pod. |
| PRs | 2× DMA58-PR on the end caps. Rear-excursion keep-out of 1.5 × 7 mm stays clear (≥ 1.6 mm margin). |
| Battery | Gens ace 2S1P 5000 mAh, 109 × 42 × 19.5 mm. It stands upright behind the woofer motors in a printed tray, with a 10 % swell allowance (§1). |
| Main PCB | Horizontal on the floor. **Maximum 180 × 46 mm**, plus a 14 × 1.5 mm USB-C tab. 4-layer, 1.6 mm, 6× M3. ESP32 antenna at the −X end, under plastic (§6). |
| UI PCB | Under the top, 182 × 31 mm plus a 44 × 11 mm paddle under the display (§7). |
| Print | Five printed shell parts, all within 220 × 220 × 220 (largest 202 × 74 × 92 mm). About 310 g PETG. |
| Interferences | None. The model checks every solid pair. Tightest clearances: tweeter pod to PR basket 1.0 mm, pod to woofer frame 0.5 mm, woofer basket to PR keep-out 1.6 mm. |

**Conflicts and deviations, for the team lead's decision:**

1. **Diameter is 95 mm, the top of the 80–95 mm range, not ~90 mm.**
   - The ND65-8 is 48 mm deep and, rear-mounted, its flange plane must sit ≥ 30 mm off the axis. That leaves only a 19–23 mm slab behind the motors.
   - At Ø90 the slab is about 16 mm, so the chosen 19.5 mm pack does not fit. Ø90 needs a pack ≤ 13 mm thick (≤ 45 × 125 mm).
2. **Overall length is 216 mm over the PR flanges (body 210).**
   - In X, everything is set by the PR rear-excursion keep-out:
     - DMA58-PR depth: 35 mm + 2 mm add-mass + 1.5 × 7 mm.
     - It must clear the woofer basket and motor.
   - Mounting the PR flange proud of the cap face buys the 3 mm per side needed. The woofers cannot move outward to compensate, because the two frames are already 2 mm apart.
   - Holding 210 overall would need either a 1.5 × 5 mm clearance (the model's usable Xmax) or a shallower PR.
3. **Woofer spacing is only 66 mm.** Stereo separation is carried by the tweeters (166 mm apart) and DSP widening.
4. **The tweeter "waveguide" is only a 3 mm conical bezel on a raised boss.** The boss stands up to about 6 mm proud on the shoulders.
   - There is no other free space for the tweeters. Above the woofers, the 38 mm pod would hit the woofer baskets and motors (checked).
   - Outboard, the pod must fit the 22.5 mm annulus between the PR basket (Ø50) and the skin, and the sealed pod is 21.5 mm deep. So the faceplate sits flush at the skin and there is no room for a deeper flare.
   - Axis elevation is 40°, inside the required 35–45°.
5. **Woofer front opening is a Ø53 × ~14 mm tunnel through the thick baffle land.**
   - A 3 mm chamfer softens it.
   - The estimated tunnel quarter-wave is about 3 kHz, just above the 2.5 kHz LR4 crossover. Measure it and EQ in the amp DSP.
6. **Battery:** no stocked *device-grade Li-ion pouch with PCM* was found in this envelope. The chosen pack is an RC TX/RX LiPo:
   - low-C, no PCM;
   - JST-XH balance lead;
   - **no NTC**, so a 10 k NTC is bonded to the pack and wired to J803 (already on the power sheet);
   - **no published continuous-current rating**. Bench-test it at 6 A before committing.
   This matches the main-board protection architecture in `docs/spec_power.md`, but not the "device-grade" wording.

---

## 1. Battery

Our main board already carries protection, balancing, charging and NTC handling (`docs/spec_power.md` §3). Requirements for the pack:

- ≥ 6 A capability;
- a balance mid-tap;
- leads we can re-terminate to XT30 + JST-XH 3P.

Candidates found (prices and stock checked 2026-11-24):

| # | Pack | Link | mAh / Wh | L × W × T mm | g | PCM | NTC | Balance | Leads | Price | Fits Ø95 bay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A (chosen)** | Gens ace 5000 mAh 2S1P TX/RX, GA-B-RX-5000-2S1P-EC3 | [genstattu.com](https://www.genstattu.com/gens-ace-5000mah-2s-ec3-jr/) | 5000 / 37 | 109 (±5) × 42 (±2) × 19.5 (±2) | 189 | no | no | JST-XH 3P, 100 mm | EC3 + JR, 16 AWG, 100 mm | $31.19 (sale), US stock | **yes**: 1.0 mm to the shell nominal |
| B | Gens ace 4000 mAh 2S TX, GA-B-TX-4000-2S1P-EC3 | [genstattu.com](https://www.genstattu.com/gens-ace-4000mah-2s-7-4v-lipo-battery-ec3-plug-tx-rx/) | 4000 / 29.6 | 83 × 40 × 19 | 142 | no | no | JST-XH 3P | EC3, 20 AWG | $28.07 | yes (shorter; same tray works with a spacer) |
| C | Gens ace 3800 mAh 2S TX (QX7), GA-B-TX-3800-2S1P | [genstattu.com](https://www.genstattu.com/gens-ace-3800mah-2s-7-4v-lipo-battery-jst-syp-2p-plug-tx-rx/) | 3800 / 28.1 | 70 × 52 × 18.5 | 136 | no | no | JST-XH 3P | JST-SYP | $26.39 | **no**: 52 mm is taller than the 46 mm bay |
| D | BatterySpace CU-N103 2S2P PL-605060 | [batteryspace.com](https://www.batteryspace.com/custom-polymer-li-ion-battery-7-4v-4000mah-29-60wh-battery-2-40.aspx) | 4000 / 29.6 | 105 × 65 × 13 | 147 | yes, **5 A** limit | no | no | 2 wires | $65.49 | no: 65 mm wide. Also a 5 A PCM and no mid-tap |
| E | BatterySpace CU-J827 2× 5545135 side by side | [batteryspace.com](https://www.batteryspace.com/custom-polymer-li-ion-battery-7-4v-3650mah-27wh-8-0a-rate-battery-2-19.aspx) | 3650 / 27 | 140 × 93 × 8 | 170 | 8 A | 10 k | no | 4 wires | $33.52 | no: 93 mm wide |
| F | Cameron Sino JBL Xtreme replacement (GSP0931134) | [amazon](https://www.amazon.com/dp/B0BG4WP6WL) | 5000 / 37 | 146.6 × 33.3 × 17.8 | 176 | yes, rating n/a | n/a | n/a | proprietary plug | $15.99 | no: 147 mm is too long for the 119 mm bay |

**Why A:**

- It has the target capacity, verified dimensions and a balance lead, and costs about $31 from US stock.
- With no PCM, nothing limits the 6 A peak.
- Wh check: 37 Wh at 2.9 W "moderate" average (electronics §12) gives about 12.8 h, comfortably over the 8 h target.
- It is the only ≥ 4500 mAh candidate that physically fits.

**Risks:**

- It is an RC-brand LiPo, not a "device-grade Li-ion" pack.
- It has no NTC.
- Its continuous-current rating is unpublished.

A second search for slim packs is in §1.2.

### 1.1 Battery bay (rear shell)

- **Position:** the pack stands upright behind the woofer motors, with its long side along X:
  - X −54.5…+54.5;
  - Y 17.6…39.05 (swell envelope);
  - Z ±21.
  - Its 42 mm side is vertical and its faces are normal to Y.
- **Bay size:** **119 × 46 × 21.45 mm**. That is the 109 × 42 nominal plus vendor tolerance (±5 L, ±2 W), with the thickness at **19.5 + 10 % swell**.
  - The nominal pack face is 1.0 mm from the rear shell.
  - The swell envelope clears the shell at nominal width. At the +2 mm width tolerance, the extreme rear top and bottom corners would touch the shell (0.19 cm³). Pouches swell at the face centre, so this is acceptable.
  - Measure the delivered pack. If T > 19.5 mm, the swell margin shrinks one-for-one.
- **Tray:** printed integral with the rear shell, 2 mm walls on four sides, open toward the rear wall.
  - The **front wall (Y 15.6–17.6) is the puncture shield** against the woofer motors, screws and wiring: solid 2 mm PETG, 100 % infill, no inserts or screws pointing at the pack. Optionally bond a 0.5 mm G10/FR4 sheet to it.
  - Add 1 mm closed-cell foam on the rear-wall face and the tray floor, so the pack is clamped softly and swell compresses the foam first.
  - Retain the pack with a printed strap or hook-and-loop across the +Y opening; there is no lid.
- **Leads:** they exit at the +X end (X ≈ +55) and drop straight down to J801/J802 on the main board at X 64–74.
- **Clearances:** the tray floor is 8.4 mm below the UI board, and 7 mm above the main board's top-side parts in zone C.

### 1.2 Slim-pack follow-up (T ≤ 16 mm, W ≤ 45 mm, L ≤ 125 mm)

Searched 2026-11-24. AliExpress, Ufine, LiPol, HobbyKing and RobotShop blocked automated access, so they are not covered.

| Option | Link | mAh | L × W × T mm | Notes |
|---|---|---|---|---|
| Gens ace GA-B-RX-3500-2S1P-EC3 | [genstattu.com](https://www.genstattu.com/gens-ace-3500mah-2s-7-4v-lipo-battery-ec3-jr-plug-tx-rx/) | 3500 / 25.9 Wh | 97 (±5) × 45 (±2) × 16 (±2) | **Only stock pack in the envelope.** No PCM, no NTC, JST-XH 3P. Burst 2C = 7 A; continuous not stated. $24.79. |
| Custom 2S from 2× BatterySpace PL-7250115-2C | [batteryspace.com](https://www.batteryspace.com/polymer-li-ion-cell-3-7v-5000-mah-7250115-2c-18-5wh-10-0a-rate.aspx) | 5000 | ~125 × 50 × 15 (est.) | 10 A cells, $30.48 each. Pack is quote-only (mid-tap + 10 k NTC, no PCM). 5 mm too wide for the 46 mm bay. |
| Custom 2S from 2× PL-5545135-2C | [batteryspace.com](https://www.batteryspace.com/polymer-li-ion-cell-3-7v-3650-mah-5545135-2c-13-50wh-7-3a---ul-listed-un38-3-passed-ndgr.aspx) | 3650 | ~145 × 45 × 12 (est.) | Thin enough for Ø90, but about 20 mm too long for the bay between the ribs and PR keep-outs. |

**Conclusion:**

- Nothing in stock makes a **Ø90** capsule possible. Ø90 needs a pack ≤ 13 mm thick, and the 3500 mAh Gens ace is 16 ± 2 mm.
- At Ø95 the 3500 mAh pack would give about 5 mm of extra swell margin but 30 % less energy (25.9 Wh / 2.9 W ≈ 8.9 h, just over the 8 h target).
- **Keep pack A (5000 mAh) at Ø95.** The 3500 mAh RX pack is the drop-in fallback: the same tray works with a 3.5 mm foam spacer.
- A custom BatterySpace pack is the route to a "device-grade" pack with NTC, but it needs a quote and a 50 mm-wide bay.

---

## 2. Packaging description

See `view_iso_internals.png`, `view_section_xp33_woofer.png`, `view_section_xp83_tweeter.png` and `view_section_z_mid.png`.

| Zone | Contents |
|---|---|
| **Front band**, φ −45…+45°, X ±67 | Solid baffle land, flat at Y = −30.4 inside, 14 mm thick at the centre. The two ND65-8s are rear-mounted against it at X = ±33, each with 4× M3 into heat-set inserts on the 66 mm bolt circle. Ø53 openings with a 3 mm chamfer. A perforated aluminium grille covers φ −45…+58°, X ±96. |
| **Front-upper shoulders**, X ±(65.5…100.5), φ 18…62° | Tweeter pods, radial at φ = 40°. Faceplate front flush at R = 47.5 on a Ø36 raised boss with a 3 mm conical bezel. The **sealed back chamber** is Ø32 × 21.5 mm with 1.5 mm walls, and its back wall is 1.0 mm outside the PR basket. The grille has Ø38 clearance holes for the bosses. |
| **Woofer motors**, Y −5.9…+14.1 | Ø38 motors (estimated; not dimensioned on the sheet), 5.5 mm from the PR keep-out. |
| **Rear slab**, Y 15.6…41 | Battery tray (§1.1). |
| **Floor**, Z −35…−33.4 | Main PCB on 6 standoffs (6.5 mm) rising from the flat bottom. |
| **Top**, Z 33.4…35 | UI PCB hanging from 6 bosses. Above it, on raised flat pads that are flush with the top: display window (Ø46 pad) at X = 0, encoder knob (Ø32 pad, Ø26 × 13 knob) at X = +70, and 3 buttons on a 38 × 14 pad at X = −60/−72/−84. Mic port (Ø1) at X = −30. |
| **End caps** | 4 mm plates with radial ribs. Each carries a DMA58-PR surface-mounted on its outer face (flange 3 mm proud, 4× M3 on the 64.3 mm bolt circle, Ø50.5 through-hole). |
| **PR keep-out** | X ±(57.5…68), Ø22 behind each PR's add-mass: 1.5 × Xmech 7 mm. Nothing may enter it, wiring included. |
| **USB-C** | Rear, bottom, centred (X = 0, Z ≈ −31.8). 1 mm wall at the receptacle and a 14 × 8 mm recess outside for the plug overmold. |
| **Power button** | SW4 (charger /QON via FFC, own TVS D2) on the UI board at **(X −46, Y 0)**, on the top centreline between the mic port (X −30) and the 3-button pad (X −53…−91). It is actuated through a **recessed Ø10 × 2 mm pocket** in the top skin: the plunger top sits 1 mm *below* the surface, so a palm or bag cannot press it, but a fingertip can. The plunger acts through the same silicone membrane as the other buttons (no open hole). The ≥ 1 s QON hold adds further protection. Not on the end caps, which are a carry grip and carry the PRs. RESET/BOOT stay internal; auto-reset over USB handles flashing. |
| **Bracing** | The baffle land is itself a 134 × 14 mm solid beam. Add: <br>• 2 rear ring ribs at X = ±64 (φ 130…230°, 5 mm deep, 3 mm thick); <br>• the battery-tray front wall, which spans the rear shell across Z ±24; <br>• the main-board standoffs (floor) and UI bosses (top). <br>Print walls at ≥ 4 perimeters plus 40 % gyroid, or solid. |

Where the electronics sit relative to the drivers:

- Electronics and battery share the woofer chamber.
- The tweeter pods are sealed.
- Fill the volume ahead of the battery and around the motors loosely with polyfill, but **not** inside the PR keep-out or within 10 mm of the PR baskets.

---

## 3. Part split, printing, fasteners, gaskets

| Part | Bounding box (mm) | Print orientation | Notes |
|---|---|---|---|
| **Front shell** (everything with Y < +24) | 202 × 74 × 92 | **Standing on end** (X vertical, 202 ≤ 220) | Contains the baffle land, tweeter pods, top UI pads and bosses, floor standoffs and seam lips. Walls print vertical, so only the opening tops need teardrop/chamfer relief; the pod and pad undersides need tree supports. |
| **Rear shell** (Y > +24, with the battery tray) | 202 × 24 (+8 tray) × 82 | Standing on end | Battery tray, rear ribs, USB-C pocket. The seam at Y = +24 sits at φ ≈ 120° and −120°, behind the display. |
| **End cap ×2** | 95 × 92 × 4 (+ ribs/spigot) | Outer face down | A 5 mm spigot ring enters the tube with a gasket. 5 axial screw bosses: φ 0, 90, 270 in the front shell; φ 150, 210 in the rear shell. |
| Knob, button plungers | small | — | Printed. Lens: 40 × 1.5 mm clear acrylic disc (laser-cut) or a polycarbonate disc. |
| Grille | 0.8 mm perforated Al, rolled to R 48.3, 192 × ~87 mm developed | — | Sits in a 0.8 mm recess, held by 4 tabs into slots plus VHB. Ø38 holes for the tweeter bosses. Covers no part of the bottom/rear (ESP32 antenna side). |

Shell mass is about 310 g PETG solid (front 142 cm³, rear 61, caps 2 × 20). PETG for v1; ASA if the speaker will sit in sun or a car.

**Fasteners** (M3 brass heat-set inserts, M3 × 5.7, Ø4.0 hole, in ≥ 8 mm Ø bosses):

| Joint | Qty | Detail |
|---|---|---|
| End caps → shells | 2 × 5 | M3 × 10 SHCS axial, into inserts in 12 mm-long bosses at R 42. |
| Rear shell → front shell (seam) | 4 | M3 × 8 from the rear-shell outside, at X = ±50, top and bottom seam lips. Heads go in counterbores, covered by a rubber strip or left visible. |
| Woofers | 2 × 4 | M3 × 8 + washer from inside, through the frame's Ø4.2 holes into inserts in the land. |
| PRs | 2 × 4 | M3 × 8 through the Ø3.3 flange holes into cap inserts. |
| Tweeters | 2 | Faceplate has no screw holes, so retain it with a printed bezel ring (2× M2 self-tap) or a ring of RTV. Add 0.5 mm foam under the faceplate. |
| Main PCB | 6 | M3 × 6 into inserts in the floor standoffs. |
| UI PCB | 6 | M2.5 × 6 self-tapping into Ø6 bosses hanging from the top (or M3 inserts). |

**Gaskets and leak paths.** The PR alignment assumes QL ≈ 10, so every leak counts.

- **Seam (Y = +24) and cap spigots:** 3 × 1.5 mm closed-cell EPDM or neoprene foam strip in a 3 mm groove in the front-shell seam face, with a tongue on the rear shell. The cap spigots get 2 mm EPDM cord or a foam ring.
- **Drivers:** 1 mm foam ring under each woofer frame (rear-mounted, so it goes between the frame and the land), each PR flange and each tweeter faceplate.
- **Tweeter wires:** they leave each pod through a Ø2.5 hole sealed with RTV.
- **Leaks to design out:**
  - **Encoder:** the EC11 body is not airtight. Fit an O-ring or foam washer between the bushing and the pad, or enclose the encoder in a printed cup sealed to the UI board.
  - **Buttons:** clamp a 0.8 mm silicone keypad membrane under the button pad. Plungers press through the membrane, so there are no open holes.
  - **USB-C:** use a sealed receptacle, or pot or gasket the receptacle-to-wall interface. An open receptacle is a direct leak.
  - **Mic port:** gasket ring from the shell port to the UI board (spec_ui_board says ≥ 2 mm keep-out). The mic must not hear the box.
  - **Display:** glue the lens in with a foam ring. The 1 mm printed web under the lens seals the opening, and the module itself can leak.

---

## 4. Clearance checks (from `build/report.json`)

| Check | Value |
|---|---|
| Pairwise interference of all solids (drivers, keep-outs, battery + swell envelope, tray, PCBs, UI, shells) | none |
| Woofer frame ↔ woofer frame | 2.0 mm |
| Woofer motor ↔ PR excursion keep-out | 5.5 mm |
| Woofer basket ↔ PR excursion keep-out | 1.6 mm |
| Tweeter pod ↔ PR basket (Ø50) | 1.0 mm |
| Tweeter pod ↔ woofer frame edge | 0.5 mm |
| UI board ↔ tweeter pods | 2.3 mm |
| UI board ↔ battery tray | 8.4 mm |
| Battery (nominal) ↔ shell | 1.0 mm |

Several clearances are under 1 mm because the driver envelopes are taken straight from the drawings. The ND65-8 motor diameter (Ø38) is scaled from the drawing, not dimensioned. **Measure the real drivers on arrival** and re-run the script (`w_motor_d`, `w_basket_*`, `pr_basket_d`, `t_body_d`).

---

## 5. Net internal volume

Displacements are computed from the model's solids. Open-frame parts get a fill factor: woofer basket envelope 0.25 (struts, cone, spider), PR basket 0.2. Everything else counts as solid.

| Item | cm³ |
|---|---|
| Gross tube interior (Ø89 × 202 mm, flat floor) | 1243.6 |
| Shell intrusions: woofer baffle land, ribs, bosses, standoffs, pads, battery tray walls | −75.8 |
| Tweeter pods (sealed, excluded) | −26.2 |
| Woofer front openings (air in front of the cones, outside the box) | −39.3 |
| Woofers ×2 (frame + surround + Ø38 motor + 25 % basket) | −92.1 |
| PRs ×2 (inside portion: 20 % basket + post + add-mass) | −20.1 |
| Battery (nominal 109 × 42 × 19.5) | −89.3 |
| Main PCB + modelled parts | −21.3 |
| UI PCB + display + encoder + buttons | −14.6 |
| Wiring, foam, gasket intrusion (allowance) | −15.0 |
| **Net box volume** | **≈ 848 cm³ = 0.85 L** |

- This exceeds the 0.75 L target, which the B8 alignment used, by about 0.10 L.
- Unmodelled main-board parts and the real driver shapes will cost perhaps another 20–30 cm³, so plan on about **0.82 L**.
- The battery swell gap (~9 cm³) and the polyfill are counted as box air.
- No adjustment was needed. If a later change pushes the net below 0.75 L, the cheapest recovery is the baffle land: a recessed flat front facet instead of the full-thickness land would gain about 30 cm³.

---

## 6. Main PCB envelope

See `mech/concept/mainboard_envelope.png` and `mainboard_outline.dxf/.svg`. **Origin for layout:** board-local (0, 0) = enclosure (X = −90, Y = −21), the front-left corner seen from above. The +Y edge is the rear.

```
 enclosure Y
  +26.5            +---USB-C tab (X -7..+7)---+
  +25.0  +---------+                          +------------------------------------+  REAR EDGE
         |o(-70,21)          C: <=7 (under battery tray)      o(18,21)  J501 FFC20 |
  +15.1  |U101 WROVER      |..........B: <=10 under motors..........| G: <=21 J402 J801  o(86,12)
         |<-antenna over-  | J302 VH                              |    J401 J802 J803  |
  -6.5   |   hangs -X edge | J301 VH       D: <=24 (centre)       |                    |
         |KEEP-OUT  A: <=7.5 (under woofer baskets)  amp L/R LC filters  <=3 mm        |
  -21.0  +o(-70,-17)--------------------o(0,-17)-------------------------o(86,-17)----+  FRONT EDGE
        X=-90   -75                     0                                          +90
```

- **Outline:** rectangle **180 × 46 mm** (X −90…+90, Y −21…+25), plus a USB-C tab X −7…+7 to Y = +26.5.
  - The board edge clears the shell by about 1.5 mm at the rear-bottom corners, because the tube curves.
  - Corner radius ≤ 2 mm.
  - It may be **shorter** (recommended 150–170 mm, keeping the −X end for the antenna) but **not wider**: at Z −35 the tube chord is 55 mm and the standoffs need the rest.
- **Stack-up and position:** 4-layer, 1.6 mm. Bottom face at Z = −35. Bottom-side parts ≤ 2 mm (prefer none: JLC single-side assembly).
- **Mounting holes:** 6× M3 (Ø3.2, Ø6.5 pad keep-out).

  | Enclosure (X, Y) | Board-local |
  |---|---|
  | (−70, −17) | (20, 4) |
  | (−70, 21) | (20, 42) |
  | (0, −17) | (90, 4) |
  | (18, 21) | (108, 42) |
  | (86, −17) | (176, 4) |
  | (86, 12) | (176, 33) |

  The two −X holes are outside the antenna keep-out. Use NPTH, or tie them to GND away from the antenna.
- **Antenna:**
  - U101 (WROVER-E) sits at the −X end with its antenna end **overhanging the X = −90 edge by about 4 mm**.
  - **No copper on any layer for X < −75**, outside the module pads (Espressif ≥ 15 mm rule; `spec_signal.md` §1).
  - The antenna then faces the bottom-rear-left plastic: about 30 mm from the nearest grille edge, 35 mm from the battery pouch, about 5 mm below the PR basket's Ø50 envelope (frame material unknown; check).
  - Fallback if range is poor: WROVER-IE with a U.FL flex antenna on the rear-shell inner wall (same footprint).
- **Height limits** above the top surface (Z −33.4), from probing the model with 1 mm air:

  | Zone | X | Y | Max height (mm) |
  |---|---|---|---|
  | A: under woofer baskets (front strip) | −90…+90 | −21…−6.5 | **7.5** |
  | B: under woofer motors | ±(13.5…52.5) | −6.5…+15.1 | **10** |
  | C: under battery tray (rear strip) | ±61.5 | +15.1…+25 | **7** |
  | D: centre, between woofers | −6…+6 | −21…+15.1 | **24** (470 µF bulk cap, 10.5 mm) |
  | G: between motor and PR | ±(53.5…77) | −6.5…+15.1 | **21** (speaker and battery connectors) |
  | H: rear-right | +62…+77 | +15.1…+25 | **24** |
  | E: ends under the PR baskets | \|X\| > 77 | full | **7** |

- **Connector placements** (enclosure X / Y, mating direction):

  | Ref | Part | X | Y | Height / mating | Reason |
  |---|---|---|---|---|---|
  | J601 | USB-C (HRO TYPE-C-31-M-12) | −4.5…+4.5 | +20…+27.5 | Rear edge, on the tab, receptacle face ~1 mm past the tab edge; centreline Z ≈ −31.8, mates along +Y | Rear port; the shell is 1 mm thick there |
  | J801 | XT30PW-M | +64…+74.5 | +3…+11.5 | 8.5 mm, opening toward +X / up | Zone G, under the battery lead exit |
  | J802 | B3B-XH-A balance | +64…+74 | −6…0 | ≤ 10 mm | Zone G |
  | J803 | B2B-PH-K NTC | +76…+82 | +4…+10 | ≤ 7 mm | Pack has no NTC; NTC bonded to the pack face |
  | J501 | FFC 20P (AFA07-S20FCA) | +63…+89 | +19.5…+24.5 | Rear-right edge, FFC exits +Y | Runs up the rear-right inside wall to the UI board at r < 39 (clears the X = +64 rib). **Path is ~90 mm: confirmed, use a 100 mm FFC (not 200).** |
  | J301 / J302 | VH 2P woofer L / tweeter L | −62…−54 | −6…+1 / +3…+10 | 11.5 mm | Zone G left (the −X end beyond X −62 is the ESP32) |
  | J401 / J402 | VH 2P woofer R / tweeter R | +54…+62 | −6…+1 / +3…+10 | 11.5 mm | Zone G right |

- **Tall parts:** the 470 µF bulk cap goes in zone D. The FXL1040 boost inductor (4 mm) and FXL0630 LC filters (3 mm) fit anywhere.
- **Heat:** the amps, boost and charger (1–3 W each) should go under the woofer motors and centre (B/D), with ≥ 8 mm of air above them. Keep them away from the battery strip (C).
- **Speaker and lead routing:**
  - Woofer leads drop from the basket terminals.
  - Tweeter leads come down the front-upper end region, outside the PR keep-out.
  - Battery leads drop at the +X end of the tray.
  - No wire may cross the PR keep-out cylinders (X ±57.5…68, r < 11).

## 7. UI board envelope

See `mech/concept/uiboard_envelope.png` and `uiboard_outline.dxf/.svg`.

- **Outline:** X −91…+91 × Y −9…+22, plus a paddle X −22…+22 down to Y = −20 under the display.
  - Top face at Z = +35, 1.6 mm thick (2-layer is fine, per `spec_ui_board.md`).
  - The front edge is limited by the tweeter pods at |X| > 65 (2.3 mm clearance); the rear edge by the shell curve at Y ≈ +22.
- **Standoffs:** 6, at (−80, 18.5), (87, 6), (±16, −15), (±60, −12). M2.5 self-tap or M3 inserts, hanging from the top shell.
- **Display (J2):**
  - The Waveshare module (Ø37.5, 40.4 mm including tab) is centred at (0, 0), glass up.
  - **Glass top at Z = 45.0** under a 1 mm printed web and a 1.5 mm lens. The view hole is Ø33.5, and the module pocket is Ø38.1 with a slot for the tab toward +Y.
  - So the module PCB underside sits at Z ≈ 41, **6 mm above the UI board**. The standard 8.5 mm 2.54 socket is too tall: use a low-profile socket (≤ 5 mm) or solder the module header directly with a 6 mm spacer.
  - The header row is assumed at Y ≈ +13. **Check the module's actual header location on receipt.**
- **Encoder:** EC11 at (+70, 0), body ≤ 6.5 mm, shaft through a Ø7.2 hole in the knob pad. Use the **20 mm shaft** variant (the knob sits 1 mm above the pad). The knob is Ø26 × 13.
- **Buttons:** 3× TS-1187A at (−60, 0), (−72, 0), (−84, 0), under printed plungers (Ø5, ~10 mm long) acting through a silicone membrane.
- **Power button SW4:** TS-1187A at (−46, 0), under a recessed plunger (top 1 mm below the skin, in a Ø10 × 2 mm pocket). Keep 4 mm of copper/part clearance round it for the pocket boss. See §2.
- **Mic:** T3902 on the **bottom side** at (−30, 0), with a 0.8 mm board hole. A gasketed printed tube bridges the 9.5 mm gap from the board top to the Ø1 shell port.
- **UI-side FFC connector J1:** X +58…+84, Y +16.5…+22, cable exits +Y. It must not sit over the standoff at (87, 6).
- **Height limits:**
  - Top side: ≤ 6.5 mm near the centreline (|Y| < 12), ≤ 4 mm at Y = ±20 (shell curve). The display pad, knob pad and button pad give local relief.
  - Bottom side: ≤ 2 mm (pods and battery tray below).

---

## 8. Next steps

1. Buy one of each driver plus the pack. Measure the ND65-8 motor and basket, the DMA58-PR basket and post, the OT19 body, the Waveshare module (header position) and the pack. Update the parameters and re-run. The sub-1 mm clearances must be confirmed.
2. Team lead to decide on Ø95 / 216 mm. If 210 overall is mandatory, accept a 1.5 × 5 mm PR keep-out (Xmax used in the alignment), which removes the proud PR flanges.
3. Detail design:
   - seam tongue and groove;
   - cap spigots and ribs;
   - insert bosses with exact hole sizes;
   - teardrop reliefs;
   - grille tabs;
   - battery strap;
   - encoder seal cup.
4. Print a front-shell slice (X −10…+40) to check the woofer land, the tunnel chamfer and the tweeter pod / PR basket clearance before the full print.
