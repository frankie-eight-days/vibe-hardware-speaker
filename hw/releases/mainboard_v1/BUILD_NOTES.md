# Main board schematic: build notes

Date: 2026-11-24. KiCad 10.0.4. Every change to the design files went through the Konnect MCP tools (v0.12.1). The outputs were exported with `kicad-cli`, which only reads the design.

## What was built

- **Project:** `hw/mainboard/speaker_main.kicad_pro`. The root sheet (A4) holds the title notes and 9 hierarchical sheets. Each child sheet is A3 landscape.

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
- **Connectivity between sheets:** global labels for every net the specs mark global, and KiCad power symbols for `GND` and `+3V3`. There are no sheet pins. Nets that stay on one sheet use local labels named exactly as in the spec.
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
- `speaker_main_bom.csv`: grouped by Value, Footprint, LCSC and DNP. Columns: Designator, Value, Footprint, LCSC, DNP, Qty. It has 114 rows, 257 parts in total.
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
2. **The DNP attribute is NOT set.** Konnect 0.12.1 has no tool to set a schematic symbol's `dnp` flag. All 13 DNP parts instead carry a visible-in-BOM property `DNP` = `DNP`: R601, C602, C719, C720, R710, R907, D901, C956, D951, R956, U501, C503, J502. The KiCad attribute still reads `(dnp no)` on all of them.
   - **Action:** before generating assembly outputs, set "Do not populate" on these 13 parts in eeschema (Symbol Properties). Until then, `--exclude-dnp` and PCB DNP markings will not exclude them.
3. **#PWR references were renumbered by sheet** (cosmetic; see ERC above).
4. **Cosmetic limits of the stock symbols:**
   - TAS5805M: the symbol stacks its PVDD pins 15/16/27/28 at one point. The two decoupling groups (pins 15/16 and 27/28) therefore can't be drawn separately; the sheet note states the placement rule.
   - J601 USB-C: the symbol stacks its GND and VBUS pins.
   - Q701/Q801/Q802 (CSD17581Q3A symbol): the source pins 1–3 are stacked.
5. **Title blocks are empty.** No Konnect tool sets the title block. Sheet names and the root notes identify each page.

## Spec issues

1. **One part, two footprints for the 470 µF / 35 V bulk cap (C2836436, KNSCHA 10 × 10.2 mm).** spec_power C920 calls for `Capacitor_SMD:CP_Elec_10x10.5`; spec_signal C301/C401 call for `Capacitor_SMD:CP_Elec_10x10`. Each sheet was built per its own spec, so the BOM shows C920 as a separate line. Pick one footprint (check the KNSCHA land pattern) and align the specs.
2. **spec_power still says "v1.0" in its header**, although it was revised substantially during this session (Q901 removed, compensation 22k/10nF → 33k/47nF, C920 25 V → 35 V). The build follows the revised text. A version bump would make the history clear.
3. **CH340C pin 8:** spec_signal §2.2 calls it "OUT#"; the stock KiCad `CH340C` symbol calls it `NC` and types it no_connect. It has a no-connect flag either way, so nothing changes electrically.
4. **Minor wording, no change made:**
   - spec_power §2.2 cites TI Fig 8-1 ("REGN–2.2 k–LED–STAT"), but the BOM specifies R708 = 1.0 k. The 1 k matches the spec's own ≈2 mA calculation, so it was used.
   - spec_signal's "global unless marked local" rule makes `I2S_EXT_*` and `I2S_SEL` global labels, although they only appear on ui_io. They were built as global, per the rule.

## Open questions / follow-ups

- **DNP attribute:** set it on the 13 parts listed above (manual step in eeschema, or a future Konnect tool).
- **CH224Q on the TI DSQ0010A footprint:** the spec says the TI pattern is the same geometry rotated 90°, with CCW numbering, and that the EP pad is number 11 (confirmed). Check pin-1 orientation against CH224 §9.2 during PCB layout, in a rendered board view.
- **Custom footprints:** both were read back and checked against the spec geometry. No board-level render or 3D check has been done yet; do it at layout.
- **470 µF footprint:** choose one (Spec issue 1).
- **Tooling note:** Konnect tools enabled with `load_toolset` mid-session were not visible to the agent that loaded them; only agents started afterwards could call them. The build was therefore run through sub-agents, one setup agent and then one agent per group of sheets, each editing only its own files.
