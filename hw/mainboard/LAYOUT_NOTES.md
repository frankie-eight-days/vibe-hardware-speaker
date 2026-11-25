# Main board layout notes (speaker_main, layout rev A, 2026-11-24)

These notes cover what the layout does and why, how it was checked, what changed from the inputs, and what is still open. The rules are in [LAYOUT_RULES.md](LAYOUT_RULES.md). The datasheet layout extracts, with page citations, are in `kb/datasheets/` (index: `kb/datasheets/index.md`). Every script that generated geometry is in `hw/mainboard/layout_src/`.

<!-- SECTIONS FILLED BELOW -->

## 1. How the board was built (process and tool findings)

| Step | What happened | Tool |
|---|---|---|
| Stack-up, rules | JLC04161H-7628 4-layer. Net classes, board minimums and pre-defined sizes are in the `.kicad_pro`. USB geometry comes from a 2-D field solve (LAYOUT_RULES §4) | Konnect (`create_netclass`, `assign_net_to_class`, `set_design_rules`, `set_predefined_sizes`) |
| Netlist → board | **KiCad-native one-time import**: `layout_src/kicad_native_import.py`, using KiCad's `pcbnew` API on the closed board. Lead ruling on 2026-11-24: option B. Proof: `kicad-cli pcb drc --schematic-parity` showed 0 parity issues, and Konnect `update_pcb_from_schematic` dry-run returned `"status":"noop"` with 0 changes | pcbnew Python (KiCad 10.0.4) |
| Outline | Unfilled Edge.Cuts polygon, carried by the board-only footprint `speaker:BoardOutline_speaker_main`. It is placed at (0,0) as BRD1 | Konnect (`create_footprint`, `set_footprint_graphics`, `place_component`) |
| Placement | All 271 parts, the 6 holes and 3 fiducials. 29 test points flipped to B.Cu | Konnect (`set_component_placements`, `place_component`, `flip_component` via the closed-board path) |
| Critical routing | Designed offline on a scratch copy, DRC'd with KiCad, then replayed onto the live board item by item: 61 zones, 264 vias, 400 tracks, and later 231 stitching vias | Konnect (`add_zone`, `add_via`, `route_trace`, `refill_zones`) |
| Remaining signal routing | Freerouting 2.4.1 on a DSN reduced to the still-unconnected pins. L2 was declared a plane so it stays solid. The SES was imported with KiCad's own importer | Freerouting + pcbnew `ImportSpecctraSES` (approved exception, see §1.2) |

### 1.1 Konnect 0.12.1 findings (for the write-up)

1. **Custom-shape pads cannot be instantiated.** Both `update_pcb_from_schematic` and `place_component` refused U701 (RQM0029A), Q701/Q801/Q802 (NexFET VSON-8) and JP801–JP803 (rounded solder jumpers). The live path and the closed-file path give the same error, verbatim: `custom-shape pads are not supported by KiCad 10's typed placement path` (diagnostic `footprint_library_resolution_failed`). Moving those parts afterwards with `set_component_placements` works.
2. **IPC placement and moves rewrite footprints cosmetically.** Stroke type default→solid, the closing polygon point is dropped, graphics are reordered. This raises 11 `lib_footprint_mismatch` warnings. The pads were checked and are unaffected.
3. **`place_component` over IPC drops library attributes and pad-local properties.** On the fiducials it dropped `board_only`, `solder_mask_margin 0.5` and `clearance 0.6`, which caused parity "Extra footprint" errors. The closed-board file path keeps them, so the holes and fiducials were re-placed that way. `update_footprints_from_library` refuses pads with `solder_mask_margin`.
4. **`import_svg_logo` cannot make a board outline.** It creates a *filled* polygon, which makes DRC treat the whole board as edge. It also scales absolute SVG coordinates by 25.4/96 and ignores `width_mm`/viewBox.
5. **No unfilled Edge.Cuts polygon/line tool, no keep-out (rule-area) tool, no stack-up tool, no via-delete tool, no "free via" control.**
6. **Vias added over IPC take the net of a zone they sit in.** On KiCad's connectivity update, 72 of 495 vias that touch no track (PVDD, 3V3, VSYS, VBAT_PACK and GND stitching vias inside the L2/L3 planes) were re-netted to an overlapping zone's net. Fix: the native step in §1.2 restores those nets and marks free vias.
7. **Specctra export/import is limited to 2 layers.** `export_specctra_dsn` supports two copper layers only, and `apply_specctra_ses` needs that exporter's manifest. So this 4-layer board cannot use Konnect's Freerouting round trip.
8. **Editing tools loaded mid-session are invisible to the agent that loaded them.** Every board edit therefore ran in a fresh editor sub-agent with an exact brief, and its result was read back from the saved file.
9. **IPC endpoint.** The Konnect server started with no IPC endpoint configured. I pointed it at a dedicated pcbnew instance through `/Users/frankwalsh/Documents/vibecoding/konnect.toml` (`ipc_socket_path`). The pcbnew already running had another project open (mechKeyboard), and I did not touch it. **The `konnect.toml` was deleted at the end; there was no prior config file.**

### 1.2 KiCad-native exceptions to "all edits through Konnect"

Each step below ran KiCad's own `pcbnew` Python API on the **closed** board, after a Konnect save. Each was followed by the parity proof (kicad-cli DRC `--schematic-parity`, plus the Konnect sync dry run returning `noop`).

1. The netlist import into the empty board (§1, Konnect finding 1). The lead approved this, option B.
2. `native_finalize.py`. I proposed this to the lead at about 21:00 with a 30-minute objection window, and no objection came:
   - Freerouting SES import (`pcbnew.ImportSpecctraSES`, equivalent to File > Import > Specctra Session).
   - Restore the nets of vias that KiCad had re-netted (finding 6).
   - Set the free-via flag on track-less vias so their nets stick.

No text tool ever touched a `.kicad_*` file.

## 2. Floor plan and placement decisions

Coordinates: KiCad X = enclosure X + 150, KiCad Y = 100 − enclosure Y. The rear edge is at Y 75 and the front at Y 121. The board measures 180 × 46 mm, with the USB-C tab at X 143–157 reaching Y 73.5. Holes match mech_envelope §6 exactly: (80,79), (80,117), (150,117), (168,79), (236,117), (236,88).

| Block | Where | Why |
|---|---|---|
| ESP32-WROVER-E (U101) | X 55.5–87.5, Y 88–108; the antenna end overhangs the −X edge by 4.5 mm | mech §6 asks for about 4 mm; 4.5 mm clears J302. The module sits in the middle of the width, not at a corner, because holes (80,79) and (80,117) leave only Y 82.3–113.7 free. Espressif HDG Fig. 23 prefers a corner ("①/② not recommended"), so this is **open risk R1** |
| Antenna keep-out | No copper on any layer at X < 63.3 (antenna area 6.3 mm + 0.7 mm). No copper at X < 75.3 outside Y 86–115 | Espressif HDG §1.4.8 (p.30–32) keeps copper out of the antenna area. The mech "15 mm" strip is applied everywhere except the module band. A literal "no copper X < 75" would make module pins 1–10 / 29–38 unconnectable. The HDG "15 mm in all directions" is an enclosure clearance (kb ESP32 file §6) |
| Speaker connectors | J302/J301 (left) at mech positions. **J401 (woofer R) and J402 (tweeter R) are swapped relative to the mech table**: woofer rear, tweeter front | The TAS5805M pin order mirrors on the right amp (U401 rot 0). Keeping mech's order would cross the woofer and tweeter output pairs. **Requested action (mech/harness):** the right woofer lead goes to the rear VH socket and the tweeter lead to the front. Silk labels the sockets |
| Amps U301/U401 | Zone B, power pin row facing the connectors | TI SLASEH5D Fig. 9-2: inductors in a column next to the output pins, BST caps between the pins and the inductors, PVDD 0.1 µF at both pin-row ends |
| Tall bulk caps C920, C301, C401 (10.2 mm) | Centre column X 139–161, Y 86–111 (enclosure \|X\| < 11) | The STL height map gives ≥ 25 mm there (98 mm under \|X\| < 10). Zone G is taken by the module and connectors, and the bottom side is limited to ≤ 2 mm. This **deviates from S11's "zone G or bottom"**, but the purpose of S11 (height compliance) is met with margin. C301/C401 sit 25–30 mm from their amps on the PVDD plane; HF decoupling (4 × 10 µF + 0.1 µF) stays at each amp |
| Boost U901/L901 | X 122–140, between amp L and the centre column. The C_OUT stack is on the rear side, L901 on the front | It feeds PVDD to both amps and the centre bulks with short runs. Its VSYS input is next to the front-strip VSYS plane |
| Charger U701/L701/Q701 | Front strip X 157–182 | VBUS comes straight down from USB-C (X 150). The BAT side faces the battery (right). SYS joins the boost on the L3 VSYS plane |
| Buck U951 | Front strip X 96–122 | +3V3 sits next to the ESP32 end and the front-left 3V3 plane |
| Battery / protection | J801 (XT30, plug enters from +X), F801, Q801/Q802 common-drain pair right under J801, U801/balancers in the front-right strip | Shortest pack path. The BATT_N island is separate from GND. Q801 gets copper on 3 layers (S3) |
| J803 (pack NTC) / J802 (balance) | J803 at (230.5, 94): pack-lead exit, zone E (7.6 mm available, PH is 6 mm). J802 turned 90° at X 222.6–229.4 | S6: J803 at the pack-lead exit. J802 moved slightly toward +X from the mech box, because the protection FETs need the area under J801 |
| J501 FFC | Mech position, rear-right edge, FFC exits +Y. 0.4 mm of its courtyard (not body) sits past the rear edge | mech §6 |
| USB-C J601 | On the tab; the receptacle face is 1 mm past the tab edge | mech §6 |
| Test points | All 29 on **B.Cu**, on a 2.54 mm grid from origin (60,75) | Bed-of-nails friendly; no assembly cost (bare pads) |

Height check: `layout_src/check.py` checks every part's body box against a 0.5 mm clearance map ray-cast from the mech STL set, with 1 mm air included. All parts pass (J502 DNP header 8.5 mm: 77 mm available; C920/C301/C401: ≥ 30 mm; VH: 21 mm; XT30: 21 mm; J802: 7.7 mm vs 7.0 mm).

## 3. Critical routing (hand-designed, `layout_src/blk_*.py`)

Power copper is drawn as zones on purpose, so it pours into shape. Short critical nets were routed by a deterministic A* router (`layout_src/arouter.py`), on layers and windows I chose. It keeps out of switch-node polygons, and every result was checked with KiCad DRC before replay.

**Boost TPS61178 (U901)**, SLVSDA7E §11.1/Fig. 36, p.30; land pattern p.38–39:
- U901 is turned so the bars run vertically: VOUT is left, PGND right, SW in the middle.
- **Hot loop:** SW bar → VOUT bar top end → C914 (100 nF, 0.6 mm past the bar ends) → PGND bar.
  - About 2.5 mm loop path, all on L1, no vias.
  - C906–C913 (8 × 10 µF) stack directly behind C914, with the PVDD band between the two cap columns.
- **SW node:** only a 2 mm neck from the SW bar to the L901 pad, on L1, with no vias. C905 (BST) is on the IC's left at BST/SW.
- **AGND island (L6):** an L1 copper island carries R901/R902/C916/R903/C915/R905/R906 grounds.
  - It is joined to PGND at exactly one point: a 0.65 mm trace from pin 2 (AGND) to the pin-6 bar.
  - It has no vias, and the global GND pours stop short of it.
- **FB divider (R904–R907):**
  - Within 3 mm of pin 5.
  - The R904 "RUP" is a Kelvin sense from C906's PVDD pad on L4, on the far side from SW (TI Fig. 36 does the same with VOUT2).
- **Thermal:** a 12-via GND array in the PGND pour beside the C_OUT grounds. No vias are in the 0.25 mm bars (p.38 note 4).

**Charger BQ25792 (U701)**, SLUSDV2C §8.4.1 p.139, Fig. 8-21, EVM SLUUCB5E §3:
- **0.1 µF placement:** C707 (PMID–GND) and C716 (SYS–GND) sit directly above the top pin row on L1. PMID/SYS bulk sits beside them on the same layer with no vias (items 1–2).
- **SW1/SW2:** each drops through 3 × 0.25/0.5 mm vias inside the package outline (not in pads; item 2). They run to L701 on **L3 and L4 in parallel**, and L701 has 3 vias per terminal.
  - The SW links are about 10 mm long. TI's own Fig. 8-21 does the same.
  - The 0.5 oz inner layer alone would be too thin for 5 A, hence the L4 copy.
- **REGN cap and BTST caps:** REGN cap at pin 5. BTST caps beside their pins, with the SW side through one via (EVM item 3).
- **BAT band:** from pins 22/23 to Q701, on L1 plus an L4 mirror with 5 vias. The BAT caps sit on the band.
- **Quiet signals:** PROG/ILIM/TS/CE/BATP route away from SW (item 7).
- **Ground:** pin-27 GND via under the package; the cap-ground band has 11 vias.

**Buck TPS62933 (U951)**, SLUSEA4D §12.1 p.40:
- C953 sits across VIN/GND with about 1 mm of copper.
- The SW pour runs only between pin 5 and the L951 pad, about 1.3 mm.
- FB/SS/EN go away from SW, with vias where needed.

**Battery path (7 A cont / 10 A pk):**
- **PACK_P** (J801 pin 2 → F801): a pour on L1, L3 and L4 with 9 vias.
- **BATT_N island:** J801 pin 1 → Q801 source, on L1/L3/L4 with 8 vias. It never touches GND; DRC checks that.
- **PROT_D:** a common-drain pour on L1/L3/L4 with 6 thermal vias.
- **Q801 copper (S3):** BATT_N plus PROT_D copper on three layers comes to about 2.3 cm², against the ≥ 2 cm² asked for.
- **VBAT_PACK** (F801 → Q701 drain): an L3 + L4 plane band, about 9 × 38 mm. That is roughly 1.5 mΩ, or 70 mW at 7 A.
- **Q802 source:** a 3-via GND array.
- **R803 (V−):** returns to the Q802 source copper (spec_power §6).

**Amps:**
- **PVDD:** the 0.1 µF 0402 cap at each pin-row end is about 0.5 mm from pins 15/16 and 27/28, with the 10 µF parts within 3 mm (SLASEH5D §9.1.2).
  - L1 PVDD pours feed L3 through 3 vias per end.
  - The cap grounds have 6 vias per end.
- **BST caps:** pin-to-pin with no vias, placed between the output traces as on the SLOU510 EVM.
- **Outputs:** 0.4 mm necks at the pins, then 1.0 mm to the inductors and on to the connectors.
- **Output caps:** each output cap has its own GND via.
- **Inductors:** no traces under them.
- **PowerPAD:** 24 × 0.2 mm footprint vias (3 × 8), plus GND pins 1/5/14/19/24 strapped to the pad.

**USB:**
- **DP/DN** from receptacle to U601 (flow-through ESD) to CH340C: 0.28 mm traces over solid L2. DP is joined under the pads on L1; DN is joined by an L4 jumper and runs on L4 to U601.
  - About 30 mm total.
  - They are not a length-matched coupled pair over the whole length. At full speed (12 Mb/s, edges ≥ 4 ns) that is harmless.
- **VBUS:** L1 pads → vias → a 2.8 mm L4 band → the charger VBUS pour.
- **TVS:** D601 is 3 mm from the VBUS pads.
- **CC1/CC2:** to U602 (ESD) and the CH224Q. CC2 hops on L3 because the VBUS and DP copper box it in.

**MCU:**
- **3V3 decoupling:** C102 (100 nF) is 1.5 mm from pin 2, with C101 behind it. Each has its own GND via.
- **EPAD:** 4 vias in the gaps between the sub-pads.
- **Strapping nets** (EN, IO0, IO2 = BOOST_EN, IO12 = AMP_PDN, IO5, IO15) go straight to their pull resistors.
- **Clocks:**
  - I2S BCLK (IO26), SPI SCLK (IO18) and PDM CLK (IO32) each meet their series R within 3 mm of the module pin (R110 33 Ω, R113 68 Ω, R118 68 Ω).
  - BCLK then runs R505 → U301 pin 7, and SCLK runs to J501 in the CLOCK class (0.25 mm clearance).

**Planes:**
- **L2:** solid GND. The only voids are the antenna keep-out and the antipads.
- **L3:** PVDD (middle band), VSYS (front strip, boost/charger), +3V3 (rear strip, ESP32 end, front-left), with GND fill around them. VBAT_PACK, BATT_N, PROT_D and PACK_P have their own islands.
- **L1/L4:** GND pours with solid connections.
- **Stitching:** 231 GND vias in all: an edge fence at 3 mm pitch, an interior grid at 5 mm, and rings at 2.5 mm around the three switchers.

## 4. Remaining routing (autorouter) and what it cost

- **Freerouting 2.4.1, 40 passes.** I removed GND and all plane-connected pins from the DSN, so only the still-open connections went in.
  - L2 was declared a plane.
  - L3 was left routable after a first run without it left 53 connections open.
  - Result: 25 unrouted out of 197 nets.
  - My A* router then closed 35 of the remaining pairs (205 tracks, 50 vias). Those routed pairs are in `spec_residual.json`.
- **L3 now carries 2.55 m of signal wiring** (UI bus, I2C, faults, PDM). That fragments the L3 PVDD/VSYS/3V3 planes, which is the "split planes under signals" failure the owner warns about. **This is the main quality gap of rev A.**
  - I tried twice to confine L3 routing to a rear corridor with DSN wire keep-outs. Completion collapsed both times: 94 unrouted with keep-outs, and 145 unconnected after the partial re-route.
  - PVDD still reaches every amp, through the L1 PVDD band from the boost to C920/C401, the L3 plane fragments, and the 3 vias per amp group.
  - However, the DRC lists 3 PVDD and 2 VSYS plane-fragment disconnects (§6).
- **Fix for rev B (recommended):**
  - Move the 13-line UI/FFC bus and I2C onto L3 inside a dedicated corridor along the rear edge, and drop the rear-strip +3V3 pour; +3V3 is under 1 A and can run on L1/L4 traces.
  - Give PVDD a 3 mm L4 spine from the boost to both amps.
  - Alternatively, go to 6 layers (JLC 6-layer adds about $10 at this size).

## 5. The six 30-second checks (layout_principles.md)

All coordinates are KiCad mm. Images are in `docs/figures/pcb/` (`layer_*.png`, `assembly_top.png`, `render_*.png`).

1. **TVS right at the connector: PASS.**
   - D601 (SMF24A, VBUS) sits 3.3 mm from the J601 VBUS pads (152.45, 80.72) to its cathode (152.8, 84.0).
   - U602 (CC ESD) is 7 mm away. U601 (D+/D− ESD) is 6 mm from the DP pads (spec asks ≤ 5 mm; **minor miss**).
   - The battery, speaker and FFC connectors have no TVS in the schematic. The UI-side ESD is on the UI board (ECO-002).
2. **Tight input hot loops: PASS.**
   - Boost: the output hot loop SW→VOUT→C914→PGND is about 2.5 mm, all on L1. C903 sits at VIN pin 12.
   - Buck: C953 spans VIN/GND with about 1 mm of copper.
   - Charger: C707 (PMID–GND) and C716 (SYS–GND) sit directly above pins 29/27/25, as in TI Fig. 8-21.
3. **Small switch nodes, inductor next to SW: PASS for the boost and buck; COMPROMISE for the charger.**
   - Boost: 2 mm SW neck to L901.
   - Buck: about 1.3 mm SW to L951.
   - Charger: SW1/SW2 reach L701 through vias plus about 10 mm of L3/L4 copper. That is TI's own topology (SLUSDV2C §8.4.1 item 2), but the SW area is larger than for the other two.
4. **Decoupling hugging the IC; passives in rows: PASS, with notes.**
   - TAS5805M: PVDD 0.1 µF about 0.5 mm from the pin-row ends. 10 µF caps within 3 mm.
   - ESP32: C102 1.5 mm from pin 2.
   - BQ25792: REGN and BTST caps within 1 mm.
   - Passive groups use one orientation per row. Exceptions: the amp BST caps (alternating vertical, per the EVM) and the charger signal resistors (two rows).
5. **Solid ground under USB and fast signals: PASS for USB; PARTIAL for the other fast signals.**
   - L2 is a solid GND plane everywhere. Its only voids are via antipads and the antenna keep-out. The USB pair (L1/L4) runs over that unbroken L2.
   - The clocks on L4 reference L3, and L3 is now fragmented in places (§4).
6. **Copper balance: L1↔L4 PASS; L2↔L3 FAIL.**

   | Layer | Coverage |
   |---|---|
   | L1 | 76.1 % |
   | L2 | 89.2 % |
   | L3 | 67.7 % |
   | L4 | 81.7 % |

   - L1 vs L4 differ by 5.6 points (within 10 %).
   - L2 vs L3 differ by 21.5 points, outside the 10–15 % target, because of the L3 signal routing in §4.
   - Mitigation: let JLC add thieving on L3, or apply the rev B fix in §4.
   - Method: `layout_src/copper_balance.py` (KiCad copper polygons ÷ outline area; zones filled).

## 6. DRC and parity

The report is `out/fab/speaker_main_drc.rpt`. It was run with kicad-cli (`--severity-all --schematic-parity`), zones filled.

- **Errors: 1.**
  - CC1 track is 0.21 mm from the J601 NPTH locating peg; the rule is 0.25 mm hole clearance. Fix in KiCad with a 0.05 mm nudge.
- **Unconnected: 40.**
  - **Not closed:** 6 signal nets were not completed by either router: `LCD_SCLK` (MCU→J501), `CHG_INT`, `I2C_SDA`/`I2C_SCL` at U701, `IO5_R`, and `PD_CFG1`/`PD_SDA`/`PD_PG` at the CH224Q. Small charger/buck fan-outs are also open: `BUCK_EN`/`BUCK_SS`, `CHG_CE_N`, `CHG_BATP`, and the SW1/SW2 BTST-cap via links.
  - **Plane-fragment disconnects:** amp PVDD L1 groups, VSYS boost↔charger, +3V3 front↔rear, the VBUS L1↔L4 pour pair at the charger, JP802↔PACK_P, and BATT_N L1↔L3.
  - **GND:** GND pour slivers.
  - **The board is not fab-ready until these are closed.** Each is a short manual route in pcbnew, about 1–2 h of work. They are listed one by one in the DRC JSON.
- **Warnings:**
  - Silk: 199 overlap, 199 over copper, 10 at the edge. These are reference designators on 0402/0603 parts and the BRD1/J501 courtyard; cosmetic.
  - 11 `lib_footprint_mismatch` (Konnect finding 2).
  - 9 `hole_to_hole` near TAS PowerPAD vias (0.2 mm drills).
  - Dangling tracks/vias left over from the autorouter.
- **Schematic parity: 0 issues.** The Konnect `update_pcb_from_schematic` dry run returns `noop` (0 changes).

## 7. Experiment: autorouter-only vs hybrid

| | Autoroute-only (`hw/experiments/autoroute_only`) | Hybrid final (`hw/mainboard`, copy in `hw/experiments/hybrid_final`) |
|---|---|---|
| Routing | Freerouting on all nets and all 4 layers (GND routed as traces, no pours) | Hand-designed power stages and pours, then Freerouting, then A* residual |
| Connections routed | 603 / 637 (94.7 %); 34 unrouted | ≥ 94 % of pin pairs; 40 unconnected items (§6), most of them plane fragments |
| Vias | 294 | 708, including 231 GND stitching, 33 plane fan-outs and about 150 power/thermal |
| Track length | 6.90 m | 5.63 m (of which 2.55 m on L3) |
| DRC errors | 3 (clearance at I2S_BCLK vias) | 1 (hole clearance) |
| Copper L1/L2/L3/L4 | 18.5 / 13.5 / 11.3 / 9.6 % | 76.1 / 89.2 / 67.7 / 81.7 % |
| Gerbers | `autoroute_only/gerbers/` | `out/fab/gerbers/`, `hybrid_final/gerbers/` |

For the analysis agent:
- The autoroute-only board has no planes. GND, PVDD and VSYS are all traces, and L2 is not solid. Expect large hot-loop and return-path inductance there.
- The hybrid board's power-stage geometry is in `layout_src/blk_boost.py`, `blk_charger.py`, `blk_buck.py`, `blk_batt.py` and `blk_amps.py`, with coordinates you can use for field-solver ports.

## 8. Requested schematic / mech changes (none applied; schematic frozen at v0.2)

1. **Mech/harness:** J401 (woofer R) is the rear socket and J402 (tweeter R) the front socket, mirrored from the left side (§2). Silk labels both.
2. **Mech:** C301/C401 sit in the centre column, not zone G (§2). Recheck in the STEP export `out/speaker_main.step`.
3. **Schematic (optional, rev B):**
   - Give U701's BTST caps C708/C709 a bottom-side variant, as on TI's EVM, or an 0402 footprint, so they can sit on top next to the pins without SW vias.
   - Change the CH224Q footprint to a dedicated CH224Q DFN10 pattern; pin-1 orientation is still to be checked on a render.
4. **S8:** XT30PW-M polarity is still **unconfirmed**. The silk marks "+BATT" at pad 2 (rear pin, PACK_P) and "−" at pad 1. Confirm against a physical part before release.
5. **S10:** the DNP attribute is still unset in the schematic. The JLC BOM/CPL (`out/fab/*_JLC.csv`) exclude by the `DNP=DNP` field (12 parts) and by "no LCSC number" (29 test pads, 3 solder jumpers): 227 placements, 87 BOM lines. JLC rotation offsets still need the usual check in JLC's CPL preview.

## 9. Open risks

- **R1, antenna:** the module sits mid-width with its antenna overhanging the edge, not at a corner (the holes force this). Test range. Fallback: WROVER-IE (spec §1.6).
- **R2, L3 plane fragmentation and the unclosed connections** (§4, §6): this is the blocking item for fab.
- **R3, SPI/PDM length:** the ESP32 → J501 runs are about 150 mm on the board plus 100 mm of FFC, against a spec target of ≤ 60 mm. The 68 Ω source resistors help. Re-run the SI sim (S6) at this length.
- **R4, charger SW area:** SW1/SW2 run on L3/L4, about 10 mm each. Check EMI at 750 kHz harmonics during charge.
- **R5, thermal:** U901/L901 and U701 sit about 25 mm apart under the left motor and centre, and Q801 has its 2.3 cm². No thermal sim has been run on the final copper.
- **R6, Konnect re-netting:** if anyone re-adds vias through Konnect, check their nets afterwards (finding 6).
