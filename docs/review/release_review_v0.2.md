# Main board schematic v0.2: delta release review (ECO-002)

**Gate:** schematic → PCB placement.
**Date:** 2026-11-24.
**Scope:** checks affected by ECO-002. Base review: `docs/review/release_review.md` (v0.1). Same skill, read-only.

## Verdict

**Placement can proceed on v0.2. There are no blockers.** ECO-002 closes S2 (placement part), S3, S4, S6, S9, L3 and L5 in the files.

The netlist diff shows only the intended changes. ERC is clean (0/0/0, no exclusions).

Two new should-fix items came from the ECO itself. Neither affects placement: both parts are DNP, and the button is a firmware/UX question.
- **N1:** the C720 fitting rule is wrong in one branch and incomplete in another.
- **N2:** firmware cannot see the new power button.

Still open from v0.1:
- **Before routing:** S11 (tall capacitors, placement plan) and L6 (net-tie).
- **Before fab or production:** S8 (XT30 polarity and harness) and S10 (DNP attribute, now 12 parts).
- **Before the first battery power-on:** S1, S5, S7 and the S3 firmware and bench items.

## 1. New baseline (H05)

| Item | Value |
|---|---|
| Release | `hw/releases/mainboard_v0.2` plus `hw/releases/lib_v0.2`. The lib tables point to `${KIPRJMOD}/../lib_v0.2`. Title block Rev 0.2 |
| Working copy | `hw/mainboard`: all 12 .kicad_sch/.kicad_pro/.kicad_wks files are byte-identical to the release. `hw/lib` = `lib_v0.2` = the v0.1 review snapshot libraries (unchanged) |
| Snapshot | `docs/review/snapshot_v0.2/{mainboard_v0.2,lib_v0.2}`. SHA-256 list in `docs/review/exports_v0.2/snapshot_sha256.txt` |
| Exports | `exports_v0.2/erc.json`, `erc.rpt`, `netlist.xml`, `schematic.pdf` (10 pages), `png/p-01…10.png`. KiCad 10.0.4 |
| Counts | 271 refdes (+14), 179 nets. 12 DNP (C503, C602, C719, C720, **C721**, C956, D951, J502, R601, R710, R956, U501), so 259 fitted, matching ECO-002 #11 |
| Specs | spec_power v1.2, spec_signal v1.2 rev b, spec_ui_board v1.2, eco_002 |

## 2. Netlist diff against the v0.1 snapshot (R05, H05)

The comparison uses (ref, pin) groups, by name and name-independent, plus every field and libsource.

| Change | Result | Intended? |
|---|---|---|
| **C721** added: 100 nF 50 V 0603, C14663, DNP, pin 1 `SFET_G`, pin 2 `CHG_BAT` | Gate–source of Q701, alongside C720/R710 | Yes (ECO-002 #1) |
| **J501.20** moved from `GND` to `CHG_QON` = {U701.12 /QON, SW701.1, J501.20} | GND group 164 → 163 nodes. J501 keeps GND on 1, 4, 6, 11, 13, 19 and MP | Yes (#2) |
| **JP803** outer pads swapped: pin 1 = J803.1 (`BAT_NTC_EXT`), pin 3 = TH801.1 (`BAT_NTC_INT`), pin 2 = `BAT_TS`. Bridged12 footprint unchanged. Value now "bridged 1-2 = J803 pack NTC" | Default selects the pack NTC | Yes (#3) |
| **U201** LCSC field C84681 → C7464026 (both the field and the property) | — | Yes (#4) |
| **13 test points:** TP105 I2C_SDA, TP106 I2C_SCL, TP107 AMP_PDN, TP108 BOOST_EN, TP109 AMP_FAULT, TP110 GND, TP301–303 I2S BCLK/LRCK/SDIN, TP304 PVDD, TP305 GND, TP401 PVDD, TP703 SFET_G | Each is a single pad on the stated net | Yes (#5) |
| Any other net, value, footprint, LCSC, DNP or libsource | **0 changes** | — |

- **Pins against pads:** re-run on all 271 references. Every symbol pin has a pad. The only extra pads are the WROVER-E NC pads, as in v0.1.
- **ERC:** 0 violations at all severities, no exclusions, default ignored-check set.
- **Renders:** pages 1, 3, 4, 6, 8 and 9 re-viewed. The new parts and labels are legible. The root shows CHG_QON as a sheet pin on charger and ui_io and as a bus member.

## 3. Boundary states for the new paths

| State | Trace and result |
|---|---|
| **/QON in ship mode, UI board unpowered** | U701 runs from BATP in ship mode. /QON is pulled up internally (VQON 3.2 V, RQON 200 kΩ; BQ25798 EC: VIH 1.3 V, VIL 0.4 V max). +3V3 is down, so the UI board is unpowered. D2 (ESD5Z5V0) goes to GND only, with no rail steering diode, so there is no clamp path. The line stays high while total leakage stays below (3.2 − 1.3)/200 k = **9.5 µA**. A spurious press needs more than (3.2 − 0.4)/200 k = 14 µA. A 5 V-standoff TVS at 3.2 V typically leaks ≤ 1 µA at 25 °C, a ≥ 9× margin. The UI spec's "≤ 0.1 µA" is optimistic, but the conclusion holds (closure: read the C502546 maker's IR(V,T)). spec_ui_board correctly forbids putting QON on the SRV05-4 (its VP diode would clamp /QON to about 0.6 V in ship mode = a held button). **Verified (calculation)** |
| **FFC out or hot-plugged** | Pin 20 becomes an open stub, and /QON stays high through RQON. SW701 still works. Hot-plugging the FFC cannot drive /QON, because it is passive and goes to GND only. The FFC maps main 20 ↔ UI 1 (outermost contact). Pin 19 is GND next to it, so a skewed insertion shorts QON to GND at worst, which looks like a held button (next row) |
| **Held or stuck button (or a QON short)** | ≥ 1 s exits ship mode. ≥ 10 s does a system power reset: SFET off for 350 ms, plus HIZ if VBUS is present, plus a 30 mA SYS sink. **Whether a continuously held /QON repeats the reset every 10 s is not stated** (BQ25798 §7.3.12.3). If it repeats, a stuck button gives a reset loop and stops ship mode. Bench check (D-list) |
| **QON 10 s reset recovers a hung ESP32** | During the 350 ms SFET-off: VSYS ≈ 80–100 µF effective, discharged by the 30 mA sink plus the ESP/buck load. 7.4 → 4.82 V (buck UVLO) takes about 3–9 ms. +3V3 (≈100 µF) then falls below the ESP brown-out level in under 100 ms if the hung ESP32 draws ≥ 1 mA (a hung running CPU draws tens of mA). EN (C103 2.2 µF, τ 22 ms) discharges into the dead rail. **A reset is achieved (calculation).** A marginal case remains only for a sub-mA hang (deep-sleep-like); bench check |
| **JP803 default with no pack NTC attached** | TS = RT2/(RT1 + RT2) = 30/35.1 = **85.5 % REGN > 73.3 % (cold)**, so charging is suspended, STAT blinks at 1 Hz, and TS_COLD is readable. Fail-safe. However, **a board without its pack NTC never charges**, even with blank firmware. That is a bring-up and assembly note, not a defect. TH801 stays fitted on a stub net (BAT_NTC_INT = {TH801.1, JP803.3}) as the alternate; harmless. An NTC short reads hot (0 %), so it also suspends |
| **C720/C721 rule** | See **N1**. With both fitted (10 nF + 100 nF): hot-plug coupling 8.4 × 10/(10 + 100 + 2.1) = **0.75 V nominal** (spec). With ±10 % tolerances: **0.90 V** against Vth(min) 1.0 V at 25 °C (≈0.85 V at 60 °C). The margin is thin but only sub-threshold leakage results, so it is acceptable. Turn-on now needs SDRV (50–100 nA) to charge ≈112 nF + Ciss: **1.1–4.5 s before conduction**, then 5–10 V/s source-follower ramp (inrush 7.5–15 mA, as the spec says), then about **5–11 s to full enhancement** (+5 V). Turn-off (ship, IBAT_OCP, the 350 ms reset) depends on the SDRV **sink** strength, which the datasheet does not give |
| **R710 alternative in the rule** | R710 = 100 kΩ gate–source against a 100 nA charge pump gives Vgs ≤ **10 mV**. **Q701 would never turn on, so there is no battery power.** TI's EVM leaves the equivalent R16 unfitted (BOM qty 0). See N1 |

## 4. Closure of the v0.1 items

| Item | Status | Evidence |
|---|---|---|
| **S2** | **Closed for placement.** Bench open; rule needs correction (N1) | C721 footprint plus TP703 on SFET_G. spec_power §2.1/§2.2 rule and numbers. ECO-002 #1 |
| **S3** | **Closed (docs).** Firmware and bench open | spec_power §2.3 (ICHG 2 A, ZHCSMD3C Table 9-2), §7 "write ICHG at boot / on every WD_FLAG". The charger sheet note now reads "POR/watchdog ICHG = 2 A". The Q801 1.5 W body-diode case is carried to layout and bench |
| **S4** | **Closed (hardware).** N2 and bench open | J501.20 = CHG_QON. spec_signal §4.2 and spec_ui_board v1.2 (SW4 to GND, D2 GND-only TVS, no pull-up). §3 above |
| **S6** | **Closed** | JP803 default = J803 pack NTC (net swap on the Bridged12 footprint). spec_power §3. Layout note: J803 at the pack-lead exit |
| **S9** | **Closed**, with low leftovers (L10) | spec_power v1.2 has the ECO-001 values (100 k/15 nF, R907/D901 fitted, PM ≥ 79°). spec_signal v1.2 has 68 Ω and 22 ms. FFC is 100 mm, and the 200 mm SI sim is noted as conservative |
| **L3** | **Closed** | U201 LCSC = C7464026. Stock on 2026-11-24: 4,477 at JLC, 0 at LCSC. Assembly draws from the JLC pool; recheck at order |
| **L5** | **Closed** | 13 TPs on the listed nets, with GND pads TP110 (mcu) and TP305 (amp_left). TP401 (amp_right PVDD) has no adjacent GND pad; the spec says to use TP305 or a via |
| S1, S5, S7, S8, S10, S11, L1, L2, L4, L6–L9 | **Carried unchanged** | ECO-002 #7–#12 record owners and stages. S10 now covers 12 parts / 259 fitted. Nothing in v0.2 changes them |

## 5. Delta register (new items)

| # | Rank | Location | Consequence | Evidence | Owner | Earliest blocked stage | Measurable closure |
|---|---|---|---|---|---|---|---|
| **N1** | Should-fix (docs and bench; DNP parts, no placement impact) | spec_power §2.1 C720 note and §2.2; charger sheet note "C720 … only together with C721 ≥ 5 × C720 **or with R710**" | (a) **The "or with R710" branch disables the battery path:** 100 kΩ against SDRV's 100 nA holds Vgs ≤ 10 mV, so Q701 never conducts. (b) With C720 and C721 fitted, Q701 needs about 5–11 s to fully enhance after insertion, ship exit or the 10 s reset. If firmware enables the boost and amps earlier, Q701 carries amps at Vgs ≈ Vth (linear mode, SOA risk). (c) Turn-off for IBAT_OCP, ship mode and the 350 ms reset is slowed by about 112 nF on an unspecified SDRV sink. That can weaken S1 and stress Q701 during an over-current trip. (d) The coupling margin is 0.90 V worst case against Vth(min) 1.0 V | BQ25792 §9.3.12 / BQ25798 §7.3.12 (100 nA typical). BQ2579x EVM BOM: R16 qty 0. NCEP3065QU Ciss 2.1 nF, Vth 1.0–2.0 V | Power + firmware | Before anyone fits C720, C721 or R710 (bring-up) | Delete the R710 branch and mark R710 "never fit with the internal SDRV". Add to the rule: C721 ≥ 10 × C720 (for example 4.7 nF + 100 nF, or 10 nF + 220 nF). Firmware waits until VSYS ≈ VBAT (BQ ADC, ΔV < 50 mV) before BOOST_EN. Bench: SFET_G turn-off time at the IBAT_OCP trip with the caps fitted, within Q701 SOA, and the existing 10-insertion inrush test |
| **N2** | Should-fix (system/UX decision; no hardware change possible) | CHG_QON has no ESP32 input (no spare GPIO). The BQ has no QON status bit | The new "power button" can only **turn on** (ship exit) and do the 10 s reset. Firmware cannot detect a press, so it cannot use the button for **power-off** or mute. Off must come from another control: a long press on a UI ladder button, the web UI, or an idle timer that enters ship mode | Netlist CHG_QON = {U701.12, SW701.1, J501.20}. BQ25798 register map (no QON flag) | System + firmware + UI | Firmware/UX spec (before routing only if a hardware read-back is wanted) | Record the on/off UX in the firmware spec: which control enters ship mode, and that the power button is wake-and-reset only. If a press must be readable, a GPIO has to be freed (for example by sharing the BTN ladder) and the FFC/UI design changed before routing |
| **L10** | Low (docs) | Small leftovers after the spec sync | mcu sheet note still says "400 kHz Fast-mode (t_r ~186 ns at ~100 pF)", against spec_signal v1.2 "100–200 kHz until tr is scoped" (S5). BUILD_NOTES "Still global" list still names CHG_QON (now a sheet-pin bus member). spec_signal gives TP401 as `TestPoint_Pad_D1.0mm`, but the schematic uses D2.0mm. spec_ui_board quotes D2 leakage ≤ 0.1 µA (the datasheet typically gives ≤ 1 µA max; conclusion unchanged). `hw/releases/README.txt` says "release review passed"; the verdict was conditional | Files as cited | Schematic/spec owners | Routing | Text fixes. No electrical change |
| **D-new** | Deferred (bench) | /QON | Behaviour with /QON held low indefinitely (one reset or repeated?) and a reset with a sub-mA hung ESP32 | §3 | Bench | First article | Hold SW4 for 30 s with the scope on VSYS/+3V3. Force a deep-sleep hang and do a 10 s press, check +3V3 drops below 2.4 V |

**Dismissed:** "D2 leakage or the unpowered UI board holds /QON low in ship mode." Dismissed: there is no rail steering, and the leakage margin is ≥ 9× (§3).

## 6. Coverage ledger (IDs affected by ECO-002)

Unlisted IDs carry over from the v0.1 ledger without change.

| ID | Status | Note |
|---|---|---|
| R01 | V | New baseline in §1 |
| R02 | V with O | Power button and NTC now traced. On/off UX open (N2) |
| R03 | V | Changed pages re-rendered and viewed |
| R04 | V | 0 violations, no exclusions |
| R05 | V | Diff in §2: only intended changes |
| R06 | V with O | S9 closed. L10 leftovers |
| L01 | V | Pins against pads re-run on 271 refs |
| L03 | V with O | 271 / 12 DNP / 259 fitted. DNP attribute still unset (S10) |
| L04 | V | C7464026 (JLC stock 4,477, 2026-11-24) |
| P01, P08 | V with O | QON ship exit and 10 s reset traced (§3). Stuck-button behaviour deferred |
| P05 | O | S2 bench, plus the N1 rule |
| P06 | O | S1 unchanged. N1(c) may slow IBAT_OCP turn-off if the caps are fitted |
| P09 | V | /QON crossing into the unpowered UI board: GND-only TVS, no sneak path |
| B04 | V | JP803 default = pack NTC. With no NTC fitted, charging is suspended (fail-safe) |
| I10 | V | FFC in, out or skewed: /QON safe. J501 keeps 6 GND + MP |
| H03 | V | L5 closed |
| H04 | V | §5 register plus the dismissed hypothesis |
| H05 | V | ECO-002 re-check: pin check, ERC, netlist assertions, render. Physical DRC, CAM and paste come later |
| E04 | V with O | A battery-side reset now exists through the external button (S4 closed). Firmware power-off path open (N2) |

**Not established by this desk review:**
- SDRV sink strength and turn-off time with C720/C721 fitted.
- Repeat behaviour of a held /QON.
- IR(V, T) of the D2 maker.
- Everything listed as unverified in v0.1 (inrush, short, thermal, AO3400A Coss, XT30 polarity, electrolytic ripple, antenna).
