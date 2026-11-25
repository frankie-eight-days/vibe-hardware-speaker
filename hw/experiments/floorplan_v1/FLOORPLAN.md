# Main board floor plan v1 (phase 1: placement only, 2026-11-25)

Board: `speaker_main.kicad_pcb` (offline copy, pcbnew API). All 272 parts are placed, the six power blocks carry their designed copper, L2/L5 are solid GND zones, and there is no other routing. Schematic v0.3, with C605 added. Figures are in `docs/figures/pcb/floorplan/`. Scripts are in `scripts/`; `run.sh plan3 <tag>` rebuilds the board and re-runs every check below.

## 1. Outline and density

| | Rev A | v1 |
|---|---|---|
| Outline | 180 × 46 mm + USB tab | **142.8 × 46 mm** + the same tab (enclosure X −54.6 … +88.2) |
| Area | 8300 mm² | **6590 mm²** (−21 %) |
| Top density | 55.6 % as quoted (53.7 % by the v1 metric) | **66.9 %** |
| Both sides | 27.7 % | 34.8 % |
| Mounting holes | 6 | 5 |

**Density metric:** Σ top courtyard area, clipped to the board ÷ (board area − on-board antenna keep-out). The keep-out is 41 mm², because the antenna fully overhangs the edge. Script: `scripts/density.py`.

**70 % was not reached.**
- **Rigid power blocks.** The six blocks fill only 55 % of their own courtyard bounding boxes, because their hot-loop pours, SW links and battery bands are copper, not courtyards. They occupy 3181 mm², or 49 % of the board. Everything outside the blocks is packed at **78 %**.
- **The ceiling.** With the blocks untouched and the rest of the board at 100 %, top density would be 78 %.
- **Height zones** (STL map) fix where the tall parts can go:
  - The woofer-basket front strips (enclosure X −46…−20 and +20…+49) and the battery-tray rear strip allow ≤ 7–9.5 mm.
  - The 4 VH connectors, the 3 × 470 µF caps, XT30 and XH need 8–11.5 mm, so they can sit only in the T zones on the block map.
  - The USB-C port at X = 0 and the VH T-zones pin both amps to X −28…+29.
- **Bottom side.** Moving passives to the bottom would lower top density, since the board length is set by the block columns, not by the passives. So the bottom holds only physics-driven parts.

## 2. Block positions (enclosure X, front = −Y)

| Block | Where | Why |
|---|---|---|
| ESP32 U101 | Front-right corner, rot 270. The antenna overhangs the +X edge by the full 6.3 mm, with the feed point at the corner | Espressif HDG Fig. 23 ④, the recommended case. This **closes rev A risk R1** (mid-edge). Switch-node copper is ≥ 45.8 mm from the antenna |
| J501 FFC | Rear-right, X 60.2–88.2 | The FFC rises at X 63.7–84.7 (> 61.5). MCU→J501 SPI/PDM lanes are about 35 mm (rev A: 150 mm) |
| AMP L / AMP R | X −28…0 / 0…+29, rotated ±90°. LC outputs face front, I2S pins face the rear corridor. VH sockets are in the front T-zone | Short LC→VH runs. I2S arrives from the rear lane with no switch node in the way. USB-C sits in the joint rear corridor |
| Boost | X 29.5–49 front, upright | It feeds PVDD to AMP R directly and to AMP L over the L4 spine |
| Bulk caps C920/C401/C301 | Stacked column at X 50–62, beside the boost | Only T-zone (11.5 mm) slot left. All three are on the PVDD plane next to the boost output |
| Buck | Rear strip, X 29–52 | 3V3 runs about 15 mm to the MCU column |
| Charger | Front-left, under the woofer-L basket (all parts ≤ 3 mm) | Next to the battery: VBAT_PACK stays in the left column |
| Battery path J801/F801/Q801/Q802 | Left end, rot 180, XT30 opening −X at the board edge | Plug lands off-board. The pack must be flipped so its leads exit the −X end of the tray (see §6) |
| Gap-pad landings | 15 × 15 mm under U301, U401 and U701 (B.Cu rule areas `GAPPAD_*`) | ECO-003 item 2 |

## 3. Hot loops: rigid-move proof and FastHenry

- **Rigid move.** All block items sit at their designed relative geometry to within 1 nm, including footprint orientations (`scripts/blockdiff.py`, `*.blockdiff.json`).
- **Pruned items.** Only stubs that ended on parts outside the blocks were removed:
  - quiet fan-out to R70x/R95x, the amp output tails to the VH sockets, and FAULT/TS/PROG pins;
  - the R904 Kelvin track, which was already a known rev A defect (no via).
- **Added to the blocks.** The GND stitching vias inside each block box.
- **Zones** are refilled on the moved board.

FastHenry is `fh_loops.py` at 100 MHz. Phase-2 GND pours are assumed (L1/L3/L6 GND fill, L2/L5 solid). Each value is the mean of 4 raster-grid offsets, because one 0.1 mm grid alone varies ±10 %.

| Loop, nH | Rev A (4L) | Same blocks before the move (6L, live-board fills) | **v1** | vs rev A |
|---|---|---|---|---|
| Boost SW→VOUT→C914→PGND | 0.20 | 0.173 | **0.173** | −13 %, pass |
| Buck VIN→C953→GND | 0.42 | 0.320 | **0.310** | −26 %, pass |
| Charger PMID→C707→GND | 0.22 | 0.214* | **0.268** | **+22 %, fail (inherited, see below)** |
| Charger SYS→C716→GND | 0.66 | – | **0.609** | −8 %, pass (not the ~0.25 the C716 rotation aimed for) |

**Why PMID fails (\*).** This is not the move:
- The block copper is identical.
- **The C716 rotation from rev B (`02_konnect1`) left a stale CHG_PGND_TOP fill.** That fill puts 0.85 mm² of GND copper on top of C716 pad 1 (VSYS). That is a real short on the live board, and it is the base DRC clearance error at C716.
- **Refilling removes that copper.** The rotated C716's VSYS pad then sits on the PMID ground return.
- **Swap test.** Swapping the old L1 GND copper back in gives 0.219 nH. So only the L1 copper differs; the move doesn't.

**Fix before or during phase 2** (charger block owner): either revert C716 to its rev A orientation (PMID 0.22, SYS 0.66), or redraw CHG_PGND_TOP so the PMID return goes around C716. Then re-score both loops.

## 4. Thermal pre-check

`thermal.py`, plus a gap-pad conductance term (`scripts/sim/thermal_fp.py`). Assumed copper:
- L1/L3/L6 GND pours;
- L4 as a full power-plane fill;
- L2/L5 solid;
- a 3 × 3 GND via array under U701.

Rev A was re-run with the same script.

| T_j °C, h = 5 / 10 W/m²K | Rev A | v1, no pads | v1 + 3 gap pads |
|---|---|---|---|
| Moderate 2.9 W: U301 / U401 / U901 | 89.5 / 81.3 / 84.2 ; 74.6 / 69.1 / 69.8 | 89.8 / **91.4** / 86.7 ; 73.1 / 74.5 / 69.8 | **56.6 / 57.9 / 61.1 ; 56.5 / 57.4 / 59.0** |
| Sustained output for T_j ≤ 125 °C | 11.1 / 18.2 W | 10.5 / 19.4 W | **28.2 / 30.5 W** (limit: U901, which has no pad) |
| U701, charging 2 A while playing | 148 / 122 | 167 / 132 | 80 / 80 |
| Q801, body-diode recovery | 132 / 110 | 144 / 118 | 92 / 90 |

**Gate with gap pads: PASS.** Every T_j is 20–30 K below rev A, and the sustained limit is ×2.5 / ×1.7.

**Without pads the smaller board runs hotter:**
- moderate case: up to +10 K (U401);
- charge-while-play: +19 K.

The total heat into the sealed box is area-limited, so matching rev A without pads would need about rev A's area. **The shrink depends on ECO-003 item 2 (gap pads).** A fourth pad under U901 would lift the 28 W limit.

## 5. EMC zoning (`block_map.png`)

- **Zones.**
  - Noisy, X ≤ 49: charger, amps, boost, buck.
  - Quiet, X ≥ 50: MCU, J501, the U501 I2S mux, MCU support parts.
  - The USB-UART (CH340) sits beside the USB-C port in the rear corridor.
- **Antenna.** It is at the far end from every switcher; the nearest switch-node copper is 45.8 mm away.
- **Planned L3 lanes** (distance to switch-node copper on any layer, excluding the last 2 mm at the pin):

  | Lane | Route | Distance to switch node |
  |---|---|---|
  | I2S | U501 → rear-middle lane at Y +14 → U401/U301 pins | 4.4 mm |
  | UART | U201 → Y +14.6 lane → under the module | 3.8 mm |
  | I2C | Down the BATT/AMP-L gap → under the charger's quiet bottom edge to U701 pins 14/15 | 2.8 mm |
  | SPI/PDM/UI | MCU → J501 | 30.5 mm |

  No lane crosses a switch node.
- **USB D±:** J601 → U601 (ESD, 6 mm) → U201, about 15 mm, over solid L2.
- **TVS D601 and C605** sit at the receptacle.
- **Planned L4:**
  - a PVDD spine Y +0…+14 across both amps to the boost and the bulks;
  - a VSYS band along the front strip, charger → boost;
  - 3V3 in the rear-right.

## 6. Mech changes and harness lengths

**Handoff files:** `mech/mainboard_outline_fp1.dxf` and `mech/mech_inputs_fp1.json` (enclosure coordinates).

**Script parameter changes:**
- `mb_x = (−54.6, 88.2)`.
- `mb_holes = (−34.5, 18.6), (−10.0, 21.3), (84.5, 3.0), (24.0, −17.3), (−24.8, −17.3)`. The new standoff bosses replace the old six.
- `mb_antenna_keepout_x` is replaced by the overhang at the +X end. Re-check the 15 mm housing clearance there: the PR-R basket, tweeter-R leads, and the X = +64 rib versus the FFC.
- **J501 rib check.** Its FFC now rises at X 63.7–84.7, against rev A's 75.5 centre, so the rib question becomes a check of the FFC against the X = +64 rib (mech).

**Harness changes:**
- **Battery and balance:** flip the pack so its leads exit the −X end of the tray (lead length about the same as rev A). Otherwise the leads need about 105 mm more.
- **Tweeter L (J302):** about 75 mm longer.
- **Tweeter R (J402):** about 45 mm longer.
- **Woofers:** about the same.
- **NTC (J803):** moves with the pack, to the left end.

**Heights:**
- Top: `check_h.py` against the STL height map, 1 mm of air included, 0 failures.
- Bottom: a new STL height map (`hmap_bot.npy`). All bottom parts are ≤ 2 mm and clear the standoffs. 0 failures.

## 7. Manufacturability

- **DRC:** courtyard overlap 0, parity 0 (`kicad-cli --schematic-parity`), copper-to-edge 0.
- **Remaining DRC items, all inherited from rev A block copper:**
  - BOOST_AGND_ISLAND is reported as isolated copper (single-point join by design);
  - one PVDD via pair in AMP R violates hole-to-hole spacing.
- **Fiducials:** 3 top, plus 3 new bottom ones (FID4–6).
- **Test points:** 29, on the bottom, on a 2.54 mm grid from the board's rear-left corner. They avoid the gap-pad landings and the standoffs.
- **Bottom parts:**
  - **7 assembled:** C101 (0805), C103/C102/C201/C502/C503 (0402) and C501 (0603), all decoupling directly under U101, U201 and U501;
  - not assembled: 29 TP pads and 3 fiducials.
  - Any of the 7 can be hand-soldered.
- **Passive rows:** they mostly follow their block's orientation. The packer used 0°/90° only, so phase 2 should tidy the rows.

## 8. Risks for phase-2 routing

1. **VSYS charger → boost is about 65 mm** (rev A about 30 mm). It needs an L4 band of at least 6 mm along the front strip, plus an L1 or L6 strip: about 20 mV at 7 A. The amps pin the X layout, so the boost cannot sit next to the charger.
2. **VBAT_PACK, F801 → Q701, is about 50 mm** inside the left column. It needs an L4 band of at least 6 mm in the 6 mm channel between BATT and AMP L. The I2C lane (L3) and VBUS (L6) share that channel.
3. **VBUS, USB-C → charger input, is about 60 mm.** Run it on L6 along the front edge, under the charger, which keeps it 1.7 mm from the ends of the SW links.
4. **Rev A charger defects remain inside the block:** the BTST links and the SW2 pin-to-pour contact. Apply `spec_fix.json` in phase 2.
5. **Gap pads are now load-bearing** for thermals (§4).
6. **Woofer-zone strips stay low:** parts there must be ≤ 7 mm. Re-check if any connector or electrolytic gets substituted.
7. **KiCad 10 outline quirk:** KiCad 10 does not recognise the board outline once it shrinks if it is drawn inside the board-only footprint BRD1. So v1 removes BRD1 and uses a board-level Edge.Cuts polygon. On the live board that needs one native step, because Konnect cannot draw an unfilled Edge.Cuts polygon.
8. **Live-board short, independent of this floor plan:** the live board and `02_konnect1` carry a stale CHG_PGND_TOP fill that overlaps C716 pad 1 (VSYS) by 0.85 mm². It must be refilled before any fab output (see §3).

**Option B** (a narrower or longer board) was not built. The USB-C port at X = 0, the VH T-zones and J801 at the board end fix the column order, and every rearrangement I checked came out 6–20 mm longer.
