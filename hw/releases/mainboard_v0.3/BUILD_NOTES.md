# Main board schematic: build notes

Date: 2026-11-24. KiCad 10.0.4. Every change to the design files went through the Konnect MCP tools (v0.12.1). The outputs were exported with `kicad-cli`, which only reads the design.

## What was built

- **Project:** `hw/mainboard/speaker_main.kicad_pro`. The root sheet (A3) is a block diagram of the 9 hierarchical sheets. Each child sheet is A3 landscape.

  | Page | Sheet | File | Parts | Main ICs |
  |---|---|---|---|---|
  | 2 | usb_power | `usb_power.kicad_sch` | 17 | J601 USB-C, U603 CH224Q, U601/U602 USBLC6, Q601/Q602 I2C isolators |
  | 3 | charger | `charger.kicad_sch` | 37 | U701 BQ25792 (stock `BQ25798` symbol), Q701 ship FET |
  | 4 | battery | `battery.kicad_sch` | 34 | U801 R5460N212AF, U802/U803 HY2213, Q801/Q802, F801, J801–J803 |
  | 5 | rails | `rails.kicad_sch` | 54 | U901 TPS61178 boost (PVDD 18.0 V), U951 TPS62933 buck (+3V3) |
  | 6 | mcu | `mcu.kicad_sch` | 36 | U101 ESP32-WROVER-E, fault merge Q101/Q102 |
  | 7 | usb_uart | `usb_uart.kicad_sch` | 8 | U201 CH340C, auto-reset Q201/Q202 |
  | 8 | ui_io | `ui_io.kicad_sch` | 17 | J501 20P FFC, U501 I2S mux (DNP), J502 |
  | 9 | amp_left | `amp_left.kicad_sch` | 27 | U301 TAS5805M (0x2C) |
  | 10 | amp_right | `amp_right.kicad_sch` | 27 | U401 TAS5805M (0x2D) |

  **Total: 257 parts.** The RefDes set matches the spec tables exactly. A script compared the two sets: nothing in the specs is missing from the schematic. The only RefDes not listed in a spec table are the 4xx amp_right parts, which the spec defines as "amp_left with 4xx".
- **Connectivity between sheets:** originally (v1), global labels for every net the specs mark global, plus KiCad power symbols for `GND` and `+3V3`. Since the root rework, the cross-sheet nets are hierarchical labels and sheet pins wired on the root; see "Root sheet block diagram" below. Nets that stay on one sheet use local labels named exactly as in the spec.
- **Fields:** every symbol has Value, Footprint (full `Lib:Name`) and an `LCSC` field. The `LCSC` field is empty only on test points, solder jumpers and J502, where the specs list no part number.
- **Design notes:** each sheet carries a text note with its key values: FB dividers and resulting voltages, ILIM, fsw, compensation, I2C addresses, TS thresholds, protector thresholds and DNP list.
- **18 V build:** PVDD uses the 18.0 V resistor set (R904 300k, R905 24k ∥ R906 200k → 17.97 V; R907 68k). The 16 V alternate was not used.
- **Schematic built from the current specs:** the build used `spec_power.md` and `spec_signal.md` as of 11:26 on 2026-11-24. That version of the power spec drops the load-disconnect FET Q901 (TPS61178 DISDRV gets a no-connect flag) and changes the boost compensation to R903 33k / C915 47 nF / C916 10 pF. It also makes C920 470 µF **35 V** (C2836436).
- **Verification:** every IC, transistor and connector was checked pin by pin against the spec pin tables, using the nets read back after wiring (`get_component_nets`). No-connect flags were checked too. The exported netlist was also reviewed net by net across all sheets: the I2C, I2S, VBUS, VSYS, VBAT_PACK, PVDD, +3V3 and GND membership was checked against the specs.

### Custom library items (`hw/lib/speaker/`, nickname `speaker`, project scope)

| Item | Type | Source |
|---|---|---|
| `speaker:TPS61178` | symbol, 13 pins | spec_power §0.1. Pin numbers, names and types were cross-checked against the cached TPS61178 datasheet text |
| `speaker:CH224Q` | symbol, 11 pins (pin 11 = EP GND) | spec_power §0.1, checked against the CH224 manual |
| `speaker:R5460x2` | symbol, 6 pins | spec_power §0.1, checked against the Ricoh datasheet |
| `speaker:HY2213` | symbol, 6 pins (1/4/5 typed no_connect) | spec_power §0.1, checked against the HY2213 datasheet |
| `speaker:Texas_RNW0013A_VQFN-HR-13_3x3.5mm_P0.5mm` | footprint | spec_power §4.1.2. Each power bar has 3 separate paste openings (≈88 %) |
| `speaker:Fuse_2410_6125Metric` | footprint | spec_power §0 (Littelfuse 451 land pattern) |

The vendored Espressif library (`hw/lib/Espressif/`) is registered as `Espressif`, for both symbols and footprints, with project scope. The library tables are `hw/mainboard/sym-lib-table` and `fp-lib-table`, and use `${KIPRJMOD}/../lib/...` paths.

### Outputs (`hw/mainboard/out/`)

- `speaker_main_schematic.pdf`: all 10 pages.
- `speaker_main.net`: KiCad netlist.
- `speaker_main_bom.csv`: grouped by Value, Footprint, LCSC and DNP. Columns: Designator, Value, Footprint, LCSC, DNP, Qty. It has 125 rows, 272 parts in total (after ECO-004).
- `speaker_main_erc.rpt` and `speaker_main_erc.json`: the ERC reports.

## ERC results

`kicad-cli sch erc --severity-all` on the root reports **0 violations** (errors, warnings and info). No ERC exclusions are defined in the project.

- **PWR_FLAGs were added only where ERC reported an undriven supply that really is a source:**
  - usb_power: `VBUS` (sourced by the USB-C connector) and `GND`.
  - battery: `BATT_N` and `BAL_MID` (cell nodes reached through passive connector pins), plus `PROT_VDD`, `BAL1_VDD` and `BAL2_VDD` (supply pins fed from the cells through resistors).
- **Nets that needed no flag:** `VSYS` is driven by the BQ SYS pin and `PVDD` by the TPS61178 VOUT pin, both power_out. The TAS5805M AVDD and VR_DIG pins are also power_out.
- **Caveat on `+3V3`:** the stock CH340C symbol types pin 4 (V3) as power_out, and it is tied to `+3V3` as the spec requires. ERC therefore treats `+3V3` as driven by U201, which would hide a missing driver on that net. Connectivity was confirmed by netlist review instead: L951 pin 2, the buck FB divider and all loads are on `+3V3`.
- **Duplicate power-symbol references:** `#PWR` references restarted at 001 on every sheet. They were renumbered by sheet (`#PWR1xx` on mcu … `#PWR9xx` on rails), so the "annotation errors" warning is gone.

## Deviations from the specs, and why

1. **Custom library nickname is `speaker:`, not `power:`.** spec_power §0 names the custom parts `power:TPS61178`, etc. `power` is KiCad's stock power-symbol library, so that nickname would collide with it. The library is `hw/lib/speaker/speaker.kicad_sym`, as the build brief asked.
2. **The DNP attribute is NOT set.** Konnect 0.12.1 has no tool to set a schematic symbol's `dnp` flag. All 12 DNP parts instead carry a visible-in-BOM property `DNP` = `DNP`: R601, C602, C719, C720, C721, R710, C956, D951, R956, U501, C503, J502. (R907 and D901 were DNP in v1; ECO-001 makes them fitted. ECO-002 adds C721.) The KiCad attribute still reads `(dnp no)` on all of them.
   - **Action:** before generating assembly outputs, set "Do not populate" on these 12 parts in eeschema (Symbol Properties). Until then, `--exclude-dnp` and PCB DNP markings will not exclude them.
3. **#PWR references were renumbered by sheet** (cosmetic; see ERC above).
4. **Cosmetic limits of the stock symbols:**
   - TAS5805M: the symbol stacks its PVDD pins 15/16/27/28 at one point. The two decoupling groups (pins 15/16 and 27/28) therefore can't be drawn separately; the sheet note states the placement rule.
   - J601 USB-C: the symbol stacks its GND and VBUS pins.
   - Q701/Q801/Q802 (CSD17581Q3A symbol): the source pins 1–3 are stacked.
5. **Title blocks are filled only at export time.** No Konnect tool sets title-block fields, so the .kicad_sch title blocks are still empty. `hw/mainboard/speaker_titleblock.kicad_wks` is the stock drawing sheet with Title "Portable stereo BT speaker: main board", Rev 0.1 and Date 2026-11-24 written in. The PDF is exported with `kicad-cli sch export pdf --drawing-sheet speaker_titleblock.kicad_wks`; the sheet name comes from KiCad's "Sheet:" field. To make the fields permanent in the files, set them once in eeschema (Page Settings, "Export to other sheets").

## Spec issues

None open. The specs are at **v1.2** and match the schematic: C920 `CP_Elec_10x10`, the ECO-001 values, CHG_QON on J501 pin 20, the JP803 net swap, C721 100nF 50V DNP, and POR/watchdog ICHG = 2 A. The earlier items are closed:
- **470 µF footprint:** C920, C301 and C401 all use `CP_Elec_10x10`.
- **spec_power version:** the header is now v1.2.
- **CH340C pin 8 naming and the R708 figure reference:** cosmetic only, no electrical impact.

## Review fixes and readability redraw (after v1)

v1 (pre-redraw) is archived at `hw/releases/mainboard_v1`.

- **Review fixes:**
  - C920 footprint → `CP_Elec_10x10` (see Spec issue 1).
  - U501 keeps Value `SN74LVC157APWR`. Its Description and Datasheet now name the SN74LVC157A. The stock libraries have no 74LVC157 or 74HC157 symbol, so `74xx:74LS157` (pin-identical) stays.
  - The no-connect flags on U701 pins 6/7 (D+/D−) and on U603 CH224Q pins 4/5 (DP/DM) were confirmed on the correct pin endpoints.
- **Readability redraw:** all 9 child sheets and the root were redrawn through Konnect following the `redraw-kicad-schematics` guidance:
  - Power flow runs left to right. Bootstrap caps sit between their two pins, and FB, COMP, EN and TS dividers are wired at their pins.
  - Global labels sit at the sheet edges, each page has a title, and the notes blocks are clear of everything else.
  - The spec's local net names are kept (`IOxx_R`, `DTR_N`, `UI_ENC_*`, …).
  - On the battery sheet, the designators Q801/Q802 were swapped between the two identical symbols to suit the layout. Each designator keeps exactly its spec pins and nets.
  - The root sheet was then reworked; see "Root sheet block diagram" below.
- **Connectivity vs v1:**
  - The netlists were exported with `kicad-cli` and compared as sets of (reference, pin) groups: **0 differences**, both by net name and name-independent.
  - The only field change is the C920 footprint.
  - Power-symbol references were renumbered again after the redraw (mcu #PWR101–120, usb_uart #PWR201–204, ui_io #PWR501–522). There are no duplicate references, and there is no annotation warning.
  - ERC: **0 violations**, all severities.

## ECO-001 (docs/eco_001.md, items 1–4)

| # | Part | v1 | Now | LCSC (confirmed in the Konnect JLCPCB database) |
|---|---|---|---|---|
| 1 | R903 (boost Rc) | 33k 1% 0603, C4216 | **100k 1%** 0603 | C25803 (Basic) |
| 1 | C915 (boost Cc) | 47nF 50V 0603, C1622 | **15nF 50V** X7R 0603 | C1596 (Extended; no Basic 15 nF 0603) |
| 2 | R907, D901 (PVDD_TRIM injection) | DNP | **fitted** (values unchanged: 68k 1% C23231, 1N4148W C81598) | `DNP` property cleared to empty (Konnect cannot delete a property) |
| 3 | R113, R114, R118 (SPI/PDM source R) | 33R 0402, C25105 | **68R** 1% 0402 | C25131 (Extended; no Basic 68R 0402) |
| 4 | C103 (ESP32 EN delay) | 1uF 25V 0402, C52923 | **2.2uF 16V** X5R 0402 | C170151 (Extended; the only Basic 2.2 µF 0402 is C12530, rated 6.3 V) |

- The rails and mcu sheet notes are updated: compensation 100k/15nF/10pF, PM ≥ 79° and a 0.34 V dip for a 0.2→2 A step at 6 V; R907/D901 fitted for PVDD_TRIM soft-start; firmware waits ≥ 150 ms after a trim change; EN RC is now 22 ms; 68R FFC source resistors.
- ECO items 5–6 are firmware-only and do not touch the schematic.
- **Verification:**
  - The (reference, pin) groups match v1 with **0 differences**.
  - The only field changes versus v1 are the 8 ECO parts above plus C920's footprint.
  - ERC reports **0 violations**.

## Root sheet block diagram

- **Layout:**
  - The power path runs along the top: usb_power → VBUS → charger ↔ VBAT_PACK/BAT_TS ↔ battery; charger → VSYS → rails → PVDD → amp_left/amp_right, which are stacked at the right.
  - The data path runs below: usb_uart ↔ ESP_EN/IO0/TXD0/RXD0 ↔ mcu → 14 parallel wires → ui_io → I2S → amps.
  - USB_DP/DN run down the left margin from usb_power to usb_uart.
  - CHG_INT, BOOST_EN and PVDD_TRIM run up from mcu to charger and rails.
  - A labelled bus `{I2C_SCL I2C_SDA AMP_PDN AMPL_FAULT_N AMPR_FAULT_N I2S_BCLK I2S_LRCK I2S_SDIN}` carries the multi-drop control nets to usb_power, charger, mcu, ui_io and both amps.
- **Conversion:** all 104 global labels of cross-sheet nets became hierarchical labels at the same position and orientation, each matched by a sheet pin on the root (`validate_sheet_pins`: 0 issues).
- **Still global:** the single-sheet nets AMP_FAULT, CHG_QON, I2S_EXT_BCLK/LRCK/DATA and I2S_SEL, plus the +3V3/GND power symbols. The root notes list them.
- **Net names:** cross-sheet nets now carry a hierarchical path (e.g. `/VSYS`). The (reference, pin) connectivity is unchanged.
- **Known drawing compromises:**
  - The three mcu→charger/rails control wires cross the bus. These are plain crossings with no junction dots.
  - Konnect's orphan check flags wire ends at bus entries; KiCad ERC accepts them.

## ECO-002 (docs/eco_002.md, items 1–5; release review S2, S4, S6, L3, L5)

| # | Change | Where |
|---|---|---|
| 1 (S2) | **C721** added: 100nF placeholder, 0603, C14663, **DNP**, SFET_G ↔ CHG_BAT (Q701 gate–source), next to C720/R710. Note rule: C720 may be fitted only with C721 ≥ 5 × C720 or with R710 | charger |
| 2 (S4) | **J501 pin 20: GND → CHG_QON**. Pin 19 stays GND, so BTN_ADC (18) and CHG_QON (20) are separated and the clock pins keep their GND neighbours. CHG_QON is now a hierarchical net (charger ↔ ui_io) and a member of the root bus. A UI-board button to GND (BQ internal pull-up): a 1 s press exits ship mode, a 10 s press resets the system. **ESD goes on the UI board**: no suitable low-voltage single-line TVS is in the BOM. With a same-side FFC, main pin 20 = UI pin 1 | ui_io, charger, root |
| 3 (S6) | **JP803 default = pack NTC on J803.** The stock library has no Bridged23 jumper, so the Bridged12 symbol and footprint are kept and the outer pins swapped: pin 1 = BAT_NTC_EXT (J803), pin 2 = BAT_TS, pin 3 = BAT_NTC_INT (TH801). The copper-bridged 1–2 default selects J803; to use TH801 on the board, cut 1–2 and bridge 2–3. JP803 was re-placed (Konnect mirrors only at placement), so its symbol UUID changed; re-link it when the PCB is first updated | battery |
| 4 (L3) | U201 CH340C LCSC C84681 → **C7464026** | usb_uart |
| 5 (L5) | 13 test points added (6 mcu + 1 charger + 5 amp_left + 1 amp_right; 29 TPs in total). **mcu:** TP105 I2C_SDA, TP106 I2C_SCL, TP107 AMP_PDN, TP108 BOOST_EN, TP109 AMP_FAULT (1.0 mm), TP110 GND (2.0 mm). **charger:** TP703 SFET_G. **amp_left:** TP301–TP303 I2S_BCLK/LRCK/SDIN (1.0 mm), TP304 PVDD and TP305 GND (2.0 mm). **amp_right:** TP401 PVDD. LCSC is empty on all of them | mcu, charger, amp_left, amp_right |

**Verification** against the post-ECO-001 netlist, by (reference, pin):
- **Added parts:** C721 and the 13 test points, each on its intended net. Checked by membership; e.g. TP108 is on {R107.2, U101.24, U901.11}.
- **Field changes:** U201 (LCSC) and JP803 (Value).
- **Connectivity changes:**
  - J501.20 left GND and joined {U701.12, SW701.1}. Every other GND pin shows only the loss of J501.20.
  - JP803.1 and JP803.3 swapped between J803.1 and TH801.1.
  - Nothing else changed.
- ERC: **0 violations**. `validate_sheet_pins`: 0 issues. No duplicate references.

## Open questions / follow-ups

- **DNP attribute:** set it on the 12 parts listed above (manual step in eeschema, or a future Konnect tool).
- **CH224Q on the TI DSQ0010A footprint:** the spec says the TI pattern is the same geometry rotated 90°, with CCW numbering, and that the EP pad is number 11 (confirmed). Check pin-1 orientation against CH224 §9.2 during PCB layout, in a rendered board view.
- **Custom footprints:** both were read back and checked against the spec geometry. No board-level render or 3D check has been done yet; do it at layout.
- **ECO-001 part classes:** C915, C103 and R113/R114/R118 have no JLC Basic option in the required package, so they add Extended lines (see ECO-001). If assembly cost matters, consider C103 = C12530 (2.2 µF 6.3 V Basic). That leaves only 1.9× margin on a 3.3 V net, so it was not chosen.
- **Root sheet:** the tools can't put sheet pins on the top or bottom edges of a box, or enlarge the Sheetname field. The power path therefore enters the boxes from the side, and the large box names are text items.
- **Charger sheet note:** fixed. It now reads "POR/watchdog ICHG = 2 A (BQ25792, 2S); firmware sets ICHG at boot". C721's Value is `100nF 50V`.
- **Release snapshot:** v0.2 is snapshotted at `hw/releases/mainboard_v0.2`. The title block (`speaker_titleblock.kicad_wks`) reads Rev 0.2, and `out/` (PDF, netlist, BOM) was re-exported at Rev 0.2.
- **ECO-004 (v0.3, 2026-11-25):** adds C605, a 47 µF 35 V Al-elec (Lelon VZH470M1VTR-0606, C134832), from VBUS to GND on usb_power next to D601. It is the ESR-damped hot-plug bulk cap (S8; `docs/eco_004.md`). ERC: 0 violations. Against v0.2 by (ref, pin, net), the only change is C605 added. Snapshot: `hw/releases/mainboard_v0.3`, without the .kicad_pcb, which is live in layout.
- **Tooling note:** Konnect tools enabled with `load_toolset` mid-session were not visible to the agent that loaded them; only agents started afterwards could call them. The build was therefore run through sub-agents, one setup agent and then one agent per group of sheets, each editing only its own files.
