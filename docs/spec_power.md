# Main PCB: power section circuit specification (v1.3)

**Changelog**
- **v1.3 (2026-11-24): v0.2 delta review** (`docs/review/release_review_v0.2.md`).
  - N1: corrected the C720 rule. The R710 branch is deleted (R710 must never be fitted). C721 ≥ 10 × C720. Firmware waits for Q701 to enhance. Turn-off bench checks added.
  - N2: the power button is wake and reset only; the "off" path is now recorded; held-/QON behaviour goes on the bench list.
- **v1.2 (2026-11-24): matches the schematic after ECO-001 and ECO-002** (`docs/eco_001.md`, `docs/eco_002.md`, `docs/review/release_review.md`).
  - Boost compensation: R903 100 k, C915 15 nF.
  - R907/D901 fitted; firmware PVDD soft start.
  - BQ25792 POR/watchdog ICHG is **2 A** (S3).
  - New DNP C721 and the rule for fitting C720 (S2).
  - JP803 default is now the pack NTC (S6).
  - Balance-lead assembly check (S7).
  - CHG_QON is routed to the UI button through the FFC (S4).
  - Firmware protection contract (S1).
- v1.1: Q901 removed; PVDD 18.0 V; C920 footprint CP_Elec_10x10.
- v1.0: initial release.

Status: 2026-11-24. Scope: sheets `usb_power`, `charger`, `battery`, `rails` of the main board. This document is written so the schematic can be drawn **without datasheets**: every pin, value, net and footprint is below. Companion spec: `docs/spec_signal.md` (MCU, amps, UI).

**Conventions** (aligned with `spec_signal.md`)
- Net names in `CODE` are exact. Nets marked **(global)** cross sheets; all others are local labels.
- RefDes ranges: `usb_power` 6xx, `charger` 7xx, `battery` 8xx, `rails` 9xx (boost 90x–92x, buck 95x). The signal sheets own 100–599.
- **B** = JLC Basic, **E** = JLC Extended (JLC parts API, 2026-11-24). "Stock sym/fp" = present in the KiCad 10.0.4 stock libraries (checked locally).
- Default passive footprints: `Resistor_SMD:R_0603_1608Metric`, `Capacitor_SMD:C_0603_1608Metric`, `…C_0805_2012Metric`, `…C_1206_3216Metric`, `Resistor_SMD:R_1206_3216Metric`. Symbols `Device:R`, `Device:C`, `Device:C_Polarized`, `Device:L`, `Device:LED`, `Device:D`, `Device:D_Zener`, `Device:Fuse`, `Device:Thermistor_NTC`.
- "DNP" = footprint placed, part not fitted (set the KiCad DNP attribute).
- Datasheets used (local cache: `/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/datasheets/` and `…/datasheets/pw/`):
  BQ25792 SLUSDG1C (LCSC copy = TI Chinese edition ZHCSMD3C); BQ25798 SLUSDV2C (English, same pinout/sections); BQ2579x EVM guide SLUUCB5E; TPS61178 SLVSDA7E; TPS62933 SLUSEA4D; WCH "CH224 手册1" V2.1; Ricoh R5460x2xx EA-165-160603; HYCON HY2213 DS-V05; NCE NCEP3065QU V6.0; Littelfuse 451/453; MDD SMF24A; UMW USBLC6-2SC6; Amass XT30PW-M.

## Decisions and changes vs. the brief (read first)

1. **PVDD = 18.0 V nominal** (lead decision: 8 Ω woofers, Dayton ND65-8; 4 Ω tweeters). Boost OVP is 21 V typ (21.5 V max), well under the TAS5805M's 26.4 V maximum.
2. **PVDD_TRIM uses a diode-OR injection** (R907 68 k + D901 1N4148W, **fitted** since ECO-001), giving **≈12.2–18.0 V** (SPICE). With the GPIO Hi-Z **or low**, PVDD stays at 18.0 V. There is no DC path from `PVDD_TRIM` to GND or to a rail (only the RC capacitors). A high trim voltage lowers PVDD; the trim cannot raise it except by < 0.1 V of D901 reverse leakage at ≤ 85 °C. Firmware also uses it as a PVDD soft start (§4.1.4).
3. **The TPS61178 load-disconnect FET is NOT used** (DISDRV left open, as the TPS61178 pin table allows). The amp sheets each carry 470 µF + 4×10 µF, and this sheet adds 470 µF, so PVDD holds ≈1.5 mF. TI requires COUT2 ≤ 10 × COUT1 behind the disconnect FET, and the FET must turn on within 3 ms (§9.2.4.2, §9.2.4.4.3). About 40× is not achievable, and start-up would risk hiccup. Consequences, all accepted:
   - With BOOST_EN low, PVDD ≈ VSYS − 0.5 V (6–8 V) through the high-side body diode. The amps sit in PDN shutdown, drawing µA.
   - At battery connect, the bulk charges through Q701, the ship FET, acting as a source follower. The inrush is **not bounded by design**: 2.5–9.7 A estimated (release review S2). C720 (gate–drain) and C721 (gate–source), both DNP, can bound it, subject to the C720 fitting rule in §2.1/§2.2 (v1.3).
   - A PVDD short is cleared by the BQ IBAT_OCP 9.3 A ship-FET trip and by F801, not by the boost's hiccup mode. **The trip needs firmware** (SFET_PRESENT = 1, EN_BATOC = 1, watchdog handled; §7). With blank or hung firmware, only the R5460 (≈40 A for 12 ms) and F801 remain (release review S1).
4. **A ship FET is added on the charger's BAT path** (Q701, NCEP3065QU, the same LCSC part as the protection FETs, so no new line item). The BQ2579x **battery over-current protection (IBAT_OCP 9.3 A) only works with a ship FET fitted** (BQ25798 §7.3.13.1.7). It also gives a true ship/shutdown mode and a QON "power-on" button.
5. **HY2213-BB3A is a gate driver, not a bleeder.** Its OUT pin drives an external N-FET plus bleed resistor (HY2213 §9). Each cell gets AO3400A + 2× 120 Ω.
6. **The R5460 is a low-side protector.** Cell negative (`BATT_N`) is **not** board GND: the protection FETs sit between `BATT_N` and `GND`. Copper and connectors must respect this (§3, §6).
7. **Balance lead: only the middle tap is used by default.** Pins 1 (B−) and 3 (B+) of the JST-XH go through open solder jumpers. If a pack has its own PCM, tying its balance B−/B+ to our main path would let current bypass the pack's protection FETs through the thin balance wires. A 1 MΩ/1 MΩ divider biases the mid node, so the protector and balancers also work with the balance lead unplugged.
8. **CH224Q is isolated from the shared I2C bus when VBUS is absent** (Q601/Q602). Its CFG2/SCL and CFG3/SDA have internal 7–15 kΩ pull-ups to its internal rail (CH224 §8.2.1). Unpowered, that rail sits near 0 V, which would drag the 3.3 V bus to ≈2.2 V, below the ESP32/TAS5805M V_IH.
9. **I2C pull-ups, the CHG_INT pull-up and the BOOST_EN pull-down are not on the power sheets.** They are R104/R105/R106/R107 on the `mcu` sheet. Do not duplicate them.
10. **Charger switching frequency is 750 kHz with 2.2 µH** (PROG = 8.2 kΩ, 2S). TI: 750 kHz works only with 2.2 µH, 1.5 MHz only with 1 µH (BQ25798 §8.2.2.2).

---

## 0. Parts with no stock KiCad symbol and/or footprint

| Part | Symbol | Footprint |
|---|---|---|
| BQ25792RQMR | Use stock **`Battery_Management:BQ25798`**, set Value = `BQ25792RQMR`. **The pinouts are identical**: BQ25792 Table 7-1 and BQ25798 Table 5-1 list the same 29 pins with the same numbers and names, both in the RQM VQFN-29. The KiCad BQ25798 symbol's pins (1 STAT … 29 PMID) match both tables pin for pin (checked). The only text difference: the BQ25792 SDRV note allows the 1 nF to go to GND *or* BAT when no ship FET is used, which doesn't apply here. | Stock `Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm` |
| TPS61178RNWR | **Custom** `power:TPS61178` (pin table §4.1.1) | **Custom** `power:Texas_RNW0013A_VQFN-HR-13_3x3.5mm_P0.5mm` (geometry §4.1.2) |
| CH224Q | **Custom** `power:CH224Q`. Easiest: copy stock `Interface_USB:CH224K` (same pin numbers 1–11) and rename pin 1 → `VHV`, pin 2 → `CFG2/SCL`, pin 3 → `CFG3/SDA` (pin table §1.2) | Stock `Package_DFN_QFN:Texas_DSQ0010A_WSON-10-1EP_2x2mm_P0.4mm_EP0.9x1.5mm` (pad 11 = EP = GND). CH224Q DFN10: body 2.0×2.0, pitch 0.4, lead 0.2×0.3, EP 1.5×0.9 (CH224 §9.2). The TI DSQ pattern has the same geometry rotated 90°, with counter-clockwise numbering from pin 1 like the CH224Q |
| R5460N212AF | **Custom** `power:R5460x2` (pin table §3.2) | Stock `Package_TO_SOT_SMD:SOT-23-6` |
| HY2213-BB3A | **Custom** `power:HY2213` (pin table §3.3) | Stock `Package_TO_SOT_SMD:SOT-23-6` |
| NCEP3065QU | Stock `Transistor_FET:CSD17581Q3A` (= `Q_NMOS_SSSGD_AvalancheRated`: pins 1-2-3 S, 4 G, 5 D), Value = `NCEP3065QU` | Stock `Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET` (pad 5 = drain tab). NCE DFN3.3×3.3-8L: pitch 0.65, lead 0.30, drain pad 2.49×1.88 (NCE p.5), which matches this pattern |
| 0451010.MRL (2410 fuse) | Stock `Device:Fuse` | **Custom** `power:Fuse_2410_6125Metric`: 2 SMD rect pads 1.96 mm (x) × 3.15 mm (y), centres at x = ±2.455 mm (gap 2.95 mm, overall 6.86 mm). Body 6.10 × 2.69 mm. Courtyard 7.4 × 3.7 mm (Littelfuse 451 "Recommended pad layout") |
| SMF24A (unidirectional, SOD-123FL) | Stock `Device:D_Zener` (pin 1 K, 2 A), Value = `SMF24A`. Don't use `Diode:SMF24A`; its A1/A2 pin names are ambiguous | Stock `Diode_SMD:D_SOD-123F` (pad 1 = cathode band) |

Everything else uses stock symbols/footprints, named per row below.

### 0.1 Custom symbol pin tables (electrical types for ERC)

`power:TPS61178`: 1 `FREQ/SYNC` input · 2 `AGND` power_in · 3 `ILIMIT` passive · 4 `COMP` passive · 5 `FB` input · 6 `PGND` power_in · 7 `SW` power_out · 8 `VOUT` power_out · 9 `DISDRV` output · 10 `VCC` power_out · 11 `EN` input · 12 `VIN` power_in · 13 `BST` passive.

`power:CH224Q`: 1 `VHV` power_in · 2 `CFG2/SCL` bidirectional · 3 `CFG3/SDA` bidirectional · 4 `DP` bidirectional · 5 `DM` bidirectional · 6 `CC2` bidirectional · 7 `CC1` bidirectional · 8 `VBUS` input · 9 `CFG1` input · 10 `PG` open_collector · 11 `GND` power_in (exposed pad, "pin 0" in the WCH table).

`power:R5460x2`: 1 `DOUT` output · 2 `COUT` output · 3 `V-` input · 4 `VC` input · 5 `VDD` power_in · 6 `VSS` power_in.

`power:HY2213`: 1 `NC` no_connect · 2 `VDD` power_in · 3 `VSS` power_in · 4 `NC` no_connect · 5 `NC` no_connect · 6 `OUT` output.

---

## Net list summary

| Net | Scope | Description / producer → consumers |
|---|---|---|
| `VBUS` | **global** | USB-C VBUS (5 V at attach, 15 V after PD). J601 → U603, U701 VBUS/VAC1/VAC2, D601 |
| `VSYS` | **global** | BQ25792 SYS output, 6.0–8.6 V (≥ 7.0 V with VBUS present). U701 → U901 boost, U951 buck |
| `VBAT_PACK` | **global** | Pack + after F801 fuse. Battery sheet → Q701 drain, U701 BATP (via R706) |
| `PVDD` | **global** | Amp rail, 18.0 V = TPS61178 VOUT (no disconnect FET) → amp sheets. ≈ VSYS − 0.5 V when BOOST_EN is low |
| `+3V3` | **global** | Buck output → everything logic |
| `GND` | **global** | System ground = protected pack negative (P−) |
| `I2C_SDA`, `I2C_SCL` | **global** | Shared bus. Pull-ups 2.2 kΩ on mcu sheet (R104/R105) |
| `USB_DP`, `USB_DN` | **global** | USB-C D+/D− → CH340C on `usb_uart` |
| `CHG_INT` | **global** | BQ25792 /INT (open drain, 256 µs low pulse). 10 k pull-up on mcu sheet (R106) |
| `BOOST_EN` | **global** | ESP32 GPIO2 (strap) → TPS61178 EN. 100 k pull-down on mcu sheet (R107). No pull-up anywhere; the TPS61178 EN has only an internal 800 kΩ pull-down |
| `PVDD_TRIM` | **global** | ESP32 GPIO25 (DAC1 or LEDC PWM) → trim RC on rails sheet |
| `BAT_TS` | **global (new)** | BQ25792 TS node: RT1/RT2 on charger sheet, NTC select on battery sheet |
| `CHG_QON` | **global** | BQ25792 /QON (internal pull-up). SW701 on the main board **and** the UI-board power button (SW4) through FFC **J501.20** (spec_signal §4.2, ECO-002 #2). Button to GND only, GND-only TVS on the UI board, no pull-up and no driven signal. **Wake and reset only: firmware cannot read it** (§2.3, N2) |
| `CHG_CE` | not used | /CE is tied low through R707 (charging allowed by hardware; firmware uses EN_CHG). No GPIO needed |

Local nets are defined per sheet.

---

## 1. Sheet `usb_power`

### 1.1 Component table

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol | Notes |
|---|---|---|---|---|---|---|---|
| J601 | USB-C 16P TYPE-C-31-M-12 | `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12` | 20 V 5 A | C165948 | E | `Connector:USB_C_Receptacle_USB2.0_16P` | stock sym+fp |
| D601 | SMF24A | `Diode_SMD:D_SOD-123F` | VRWM 24 V, VBR 26.7–29.5 V, Vc 38.9 V @ 5.1 A, 200 W | C123810 | E | `Device:D_Zener` | VBUS TVS at connector |
| C601 | 100 nF | C_0603 | 50 V X7R | C14663 | B | `Device:C` | VBUS HF at connector |
| R601 | 2.0 Ω | R_0805 | 0.125 W | C2930265 | E | `Device:R` | **DNP**. Hot-plug snubber (BQ25798 Fig 8-1 note 1) |
| C602 | 2.2 µF | C_0805 | 50 V X5R | C377773 | B | `Device:C` | **DNP**, in series with R601 |
| U601 | USBLC6-2SC6 | `Package_TO_SOT_SMD:SOT-23-6` | 5 V, 6 A 8/20 µs | C2687116 | E | `Power_Protection:USBLC6-2SC6` | D+/D− ESD |
| C603 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | U601 pin 5 to GND |
| U602 | USBLC6-2SC6 | SOT-23-6 | | C2687116 | E | `Power_Protection:USBLC6-2SC6` | CC1/CC2 ESD (pin 5 not connected) |
| U603 | CH224Q | `Package_DFN_QFN:Texas_DSQ0010A_WSON-10-1EP_2x2mm_P0.4mm_EP0.9x1.5mm` | VHV ≤ 32 V abs | C46061833 | E | **custom** `power:CH224Q` | PD sink |
| C604 | 1 µF | C_0603 | **50 V** X5R | C15849 | B | `Device:C` | VHV decoupling ("注意耐压": mind the voltage rating) |
| R602 | 56 kΩ 1 % | R_0603 | | C23206 | B | `Device:R` | CFG1 → GND: single-resistor mode, **15 V default**, enables I2C (CH224 Table 5-1, §5.2.3) |
| Q601, Q602 | AO3400A | `Package_TO_SOT_SMD:SOT-23` | 30 V, Vgs ±12 V, Vth 0.65–1.45 V | C20917 | B | `Transistor_FET:AO3400A` (1 G, 2 S, 3 D) | I2C isolators for CH224Q |
| R603 | 100 kΩ | R_0603 | | C25803 | B | `Device:R` | VBUS → `PD_ISO_G` |
| R604 | 100 kΩ | R_0603 | | C25803 | B | `Device:R` | `PD_ISO_G` → GND |
| TP601 | VBUS | `TestPoint:TestPoint_Pad_D1.5mm` | | – | – | `Connector:TestPoint` | |
| TP602 | PD_PG | `TestPoint:TestPoint_Pad_D1.5mm` | | – | – | `Connector:TestPoint` | optional |

### 1.2 Pin-by-pin connections

**J601 USB-C** (`USB_C_Receptacle_USB2.0_16P`):

| Pin | Name | Net |
|---|---|---|
| A1, A12, B1, B12 | GND | `GND` |
| A4, A9, B4, B9 | VBUS | `VBUS` |
| A5 | CC1 | `CC1` |
| B5 | CC2 | `CC2` |
| A6, B6 | D+ | `USB_DP` (global) |
| A7, B7 | D− | `USB_DN` (global) |
| A8 | SBU1 | no connect |
| B8 | SBU2 | no connect |
| SH | SHIELD | `GND` |

**D601 SMF24A**: pin 1 (K) `VBUS`, pin 2 (A) `GND`. Place within 3 mm of J601's VBUS pins.

**R601/C602 snubber (DNP)**: R601 pin 1 `VBUS`, pin 2 `VBUS_SNUB`; C602 pin 1 `VBUS_SNUB`, pin 2 `GND`.

**U601 USBLC6-2SC6 (D+/D−)**:

| Pin | Name | Net |
|---|---|---|
| 1 | I/O1 | `USB_DP` |
| 2 | GND | `GND` |
| 3 | I/O2 | `USB_DN` |
| 4 | I/O2 | `USB_DN` |
| 5 | VBUS | `+3V3` (**not** VBUS: VBUS reaches 15–20 V and the USBLC6 rail clamps at 6–9 V). C603 to GND |
| 6 | I/O1 | `USB_DP` |

**U602 USBLC6-2SC6 (CC)**: 1 `CC1`, 2 `GND`, 3 `CC2`, 4 `CC2`, 5 **no connect** (the CC pins can see Vconn up to 5.5 V, so they must not be steered into +3V3; VBR(min) 6 V > 5.5 V), 6 `CC1`.

**U603 CH224Q**:

| Pin | Name | Net | Notes |
|---|---|---|---|
| 1 | VHV | `VBUS` | C604 1 µF/50 V to GND at the pin |
| 2 | CFG2/SCL | `PD_SCL` | internal 10 kΩ pull-up (7–15 k) |
| 3 | CFG3/SDA | `PD_SDA` | internal 10 kΩ pull-up |
| 4 | DP | no connect | USB data goes only to the CH340C. BC1.2/QC on the CH224Q is unused |
| 5 | DM | no connect | |
| 6 | CC2 | `CC2` | Rd is internal (no external 5.1 k, per CH224 §6.1.1) |
| 7 | CC1 | `CC1` | |
| 8 | VBUS | `VBUS` | "需要短接至 VHV": must be shorted to VHV |
| 9 | CFG1 | `PD_CFG1` | R602 56 k to GND |
| 10 | PG | `PD_PG` | open drain, low = PD power good. TP602 only |
| 11 (EP) | GND | `GND` | EP to GND with ≥ 2 vias |

**Q601 / Q602 I2C isolator** (source on the CH224Q side, drain on the bus side):

| Ref | G (1) | S (2) | D (3) |
|---|---|---|---|
| Q601 | `PD_ISO_G` | `PD_SCL` | `I2C_SCL` |
| Q602 | `PD_ISO_G` | `PD_SDA` | `I2C_SDA` |

R603: `VBUS` ↔ `PD_ISO_G`. R604: `PD_ISO_G` ↔ `GND`.

### 1.3 Design notes / calculations

- **PD request.** CFG1 = 56 kΩ → 15 V at attach, and I2C is enabled automatically in single-resistor mode (CH224 §5.2.1, §5.2.3). Firmware can rewrite reg 0x0A (0 = 5 V, 1 = 9, 2 = 12, 3 = 15, 4 = 20 V) and read reg 0x50 (max current in 50 mA units) to program the BQ IINDPM. **Never request 28 V/EPR**: the BQ25792 VBUS operating max is 24 V, and the isolator gate would see 14 V (> AO3400A's ±12 V Vgs).
- **CH224Q I2C address** is "0x22 or 0x23" (CH224 §5.2.3; the manual doesn't say which). Firmware should probe both. Bus map: CH224Q 0x22/0x23, TAS5805M 0x2C (4.7 kΩ ADR) and 0x2D (15 kΩ ADR) (TAS5805M Table 7-5), BQ25792 0x6B (BQ25798 §7.3.14.5). **No collisions.**
- **Isolator.** Gate = VBUS/2: 2.5 V at 5 V and 7.5 V at 15 V; 10 V at 20 V (within the ±12 V Vgs rating).
  - VBUS absent: gate 0 V, so Vgs = 0 and the FET is off. The body diode (anode = source = CH224Q side ≈ 0 V, cathode = drain = bus at 3.3 V) is reverse-biased, so the bus is isolated.
  - VBUS present, CH224Q pulls low: Vgs ≥ 2.5 V > Vth(max) 1.45 V, so the FET is on.
  - VBUS present, ESP32 pulls low: the body diode drags the source to ≈0.6 V, so Vgs ≥ 1.9 V and the FET turns on. This is the standard bidirectional NMOS level shifter.
  - Added bus capacitance is ≈ 2 × 75 pF Coss. That fits within the 400 pF budget at 2.2 kΩ pull-ups (spec_signal §I2C).
- **Back-powering summary (brief question).**
  - BQ25792: powered from BAT (or VBUS) whenever +3V3 exists, since +3V3 derives from VSYS. Its I2C pins are open-drain and rated 6 V abs max. No risk.
  - TAS5805M: DVDD = +3V3, the same rail as the pull-ups. No risk.
  - CH224Q: powered only from VBUS. **Risk, handled by Q601/Q602.** Its CFG2/CFG3 pins tolerate 6.5 V (CH224 §8.1.1), and V_IH(I2C) min is 1.5 V, so 3.3 V logic is fine when it is powered.
- **ESD.** VBUS gets D601 (SMF24A). CC and D± get USBLC6. USB-C sources always attach at 5 V and only step to 15 V after the PD contract, so the BQ ">15 V hot-plug" snubber (R601/C602) stays DNP.
- **VBUS capacitance.** Total sink capacitance (VBUS + PMID, which are DC-connected inside the BQ through its input current sense) is about 50 µF nominal, ≈ 20 µF effective at 15 V. That exceeds the USB Type-C cSnkBulk guideline of 10 µF. TI's recommended values and EVM do the same. Accepted: the source limits inrush at 5 V attach.

---

## 2. Sheet `charger` (BQ25792 NVDC buck-boost charger)

### 2.1 Component table

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol | Notes / citation |
|---|---|---|---|---|---|---|---|
| U701 | BQ25792RQMR | `Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm` | | C2862876 | E | `Battery_Management:BQ25798` (Value BQ25792RQMR) | pinout identical (§0) |
| L701 | 2.2 µH FXL0630-2R2-M | `Inductor_SMD:L_Changjiang_FXL0630` | Isat 10 A / Irms 9.5 A, 15 mΩ, 7×6.6 mm | C167218 | E | `Device:L` | SW1–SW2. Alt: FXL1040-2R2-M C167228 (same as boost, saves a line item, 11.5×10 mm) |
| C701, C702 | 10 µF | C_1206 | **50 V** X5R | C13585 | B | `Device:C` | VBUS (2×10 µF + 0.1 µF, Table 5-1) |
| C703 | 100 nF | C_0603 | 50 V X7R | C14663 | B | `Device:C` | VBUS, closest to pins 2/3 |
| C704, C705, C706 | 10 µF | C_1206 | **50 V** X5R | C13585 | B | `Device:C` | PMID (3×10 µF + 0.1 µF, §8.2.2.3) |
| C707 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | PMID, closest to pin 29 |
| C708 | 47 nF | C_0603 | 50 V X7R | C1622 | B | `Device:C` | BTST1–SW1 (≥10 V, 47 nF, Table 5-1) |
| C709 | 47 nF | C_0603 | 50 V X7R | C1622 | B | `Device:C` | BTST2–SW2 |
| C710 | 4.7 µF | C_0603 | 16 V X5R | C19666 | B | `Device:C` | REGN (10 V+ rated, 4.7 µF) |
| C711–C715 | 10 µF | C_0805 | 25 V X5R | C15850 | B | `Device:C` | SYS (5×10 µF + 0.1 µF, §8.2.2.4; 16 V+ for 2S) |
| C716 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | SYS, closest to pin 25 |
| C717, C718 | 10 µF | C_0805 | 25 V X5R | C15850 | B | `Device:C` | BAT (2×10 µF, Table 5-1) |
| C719 | 47 nF | C_0603 | 50 V | C1622 | B | `Device:C` | **DNP**. BATP filter (Fig 8-2 note 2, 4S only) |
| C720 | 10 nF | C_0603 | 50 V X7R | C57112 | B | `Device:C` | **DNP**. Ship-FET gate–**drain** (`SFET_G`–`VBAT_PACK`). Slows the source-follower ramp at battery connect. **Fitting rule (v1.3): fit C720 only together with C721 ≥ 10 × C720**, and only after the §2.2 bench checks |
| C721 | 100 nF | C_0603 | 50 V X7R | C14663 | B | `Device:C` | **DNP** (ECO-002 #1, S2). Ship-FET gate–**source** (`SFET_G`–`CHG_BAT`), placed next to C720. Holds the gate down against C720's coupling at pack hot-plug |
| R701 | 8.2 kΩ 1 % | R_0603 | | C25981 | B | `Device:R` | PROG → GND: **2S, 750 kHz** (Table 7-1; EVM R30 8.20 k) |
| R702 | 51 kΩ 1 % | R_0603 | | C23196 | B | `Device:R` | REGN → ILIM_HIZ |
| R703 | 100 kΩ 1 % | R_0603 | | C25803 | B | `Device:R` | ILIM_HIZ → GND |
| R704 | 5.1 kΩ 1 % | R_0603 | | C23186 | B | `Device:R` | RT1: REGN → BAT_TS |
| R705 | 30 kΩ 1 % | R_0603 | | C22984 | B | `Device:R` | RT2: BAT_TS → GND |
| R706 | 100 Ω | R_0603 | | C22775 | B | `Device:R` | VBAT_PACK → BATP (Table 5-1: "100 Ω series") |
| R707 | 10 kΩ | R_0603 | | C25804 | B | `Device:R` | /CE → GND (charge enabled in hardware) |
| R708 | 1.0 kΩ | R_0603 | | C21190 | B | `Device:R` | STAT LED series |
| D701 | Green LED KT-0805G | `LED_SMD:LED_0805_2012Metric` | Vf 2.6–3.1 V | C2297 | B | `Device:LED` | Charge status |
| SW701 | TS-1187A-B-A-B | `Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A` | 12 V 50 mA | C318884 | B | `Switch:SW_Push` | QON: wake from ship mode / 10 s = system reset. Paralleled by the UI-board button through the FFC |
| Q701 | NCEP3065QU | `Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET` | 30 V, 1.9 mΩ@10 V, 3.0 mΩ@4.5 V, Vth 1.0–2.0 V | C502964 | E (same part as Q801/Q802) | `Transistor_FET:CSD17581Q3A` (Value NCEP3065QU) | **Ship FET (SFET)** |
| R709 | 0 Ω | R_0603 | | C21189 | B | `Device:R` | SDRV → SFET gate (EVM R17) |
| R710 | 100 kΩ | R_0603 | | C25803 | B | `Device:R` | **DNP: never fit with the internal SDRV.** SFET gate–source (EVM R16, also unfitted on TI's EVM). 100 kΩ against SDRV's ≈100 nA holds Vgs ≈ 10 mV, so Q701 would never turn on and there would be no battery power (N1) |
| TP701 | VSYS | `TestPoint:TestPoint_Pad_D1.5mm` | | – | – | `Connector:TestPoint` | |
| TP702 | CHG_BAT | `TestPoint:TestPoint_Pad_D1.5mm` | | – | – | `Connector:TestPoint` | optional |

### 2.2 U701 pin-by-pin

| Pin | Name | Net | Connection |
|---|---|---|---|
| 1 | STAT | `CHG_STAT` | D701 cathode. D701 anode → R708 → `CHG_REGN` (Fig 8-1: REGN–2.2 k–LED–STAT) |
| 2, 3 | VBUS | `VBUS` | C701, C702, C703 |
| 4 | BTST1 | `CHG_BTST1` | C708 to `CHG_SW1` |
| 5 | REGN | `CHG_REGN` | C710 to GND; feeds R702, R704, R708 only |
| 6 | D+ | no connect | (see §2.3, input current) |
| 7 | D− | no connect | |
| 8 | VAC2 | `VBUS` | "Connect to VBUS if ACFET2/RBFET2 not installed" |
| 9 | VAC1 | `VBUS` | same, for port 1 |
| 10 | ACDRV2 | `GND` | "Tie to GND if no ACFET2/RBFET2" |
| 11 | ACDRV1 | `GND` | "Tie to GND if no ACFET1/RBFET1" |
| 12 | /QON | `CHG_QON` (global) | SW701 to GND, plus the UI button through J501. Internal pull-up (≈3.6–3.8 V), no external resistor |
| 13 | /CE | `CHG_CE_N` | R707 10 k to GND (must not float) |
| 14 | SCL | `I2C_SCL` | pull-up on mcu sheet |
| 15 | SDA | `I2C_SDA` | pull-up on mcu sheet |
| 16 | TS | `BAT_TS` (global) | R704 from REGN, R705 to GND, NTC on battery sheet |
| 17 | ILIM_HIZ | `CHG_ILIM` | R702 from REGN, R703 to GND |
| 18 | BATP | `CHG_BATP` | R706 from `VBAT_PACK` (battery side of the ship FET, EVM JP9 "BATTERY"); C719 DNP to GND |
| 19 | BTST2 | `CHG_BTST2` | C709 to `CHG_SW2` |
| 20 | PROG | `CHG_PROG` | R701 8.2 k to GND |
| 21 | /INT | `CHG_INT` (global) | pull-up on mcu sheet (to +3V3, as §7.3.4.1 recommends, not to REGN) |
| 22, 23 | BAT | `CHG_BAT` | C717, C718; Q701 source |
| 24 | SDRV | `CHG_SDRV` | R709 0 Ω → `SFET_G` |
| 25 | SYS | `VSYS` | C711–C716 |
| 26 | SW2 | `CHG_SW2` | L701 pin 2 |
| 27 | GND | `GND` | power ground, via array |
| 28 | SW1 | `CHG_SW1` | L701 pin 1 |
| 29 | PMID | `CHG_PMID` | C704–C707 only (no load) |

**L701**: pin 1 `CHG_SW1`, pin 2 `CHG_SW2`.

**Q701 ship FET** (orientation as TI EVM Q5: source on the charger BAT side, drain on the battery side, so the body diode blocks battery → system when off):

| Pin | Net |
|---|---|
| 1, 2, 3 (S) | `CHG_BAT` |
| 4 (G) | `SFET_G` |
| 5 (D, tab) | `VBAT_PACK` |

R710 (DNP): `SFET_G` ↔ `CHG_BAT`. C720 (DNP): `SFET_G` ↔ `VBAT_PACK`. C721 (DNP): `SFET_G` ↔ `CHG_BAT`.

**C720/C721 fitting rule (v1.3, N1).** Fit C720 **only together with C721 ≥ 10 × C720**. Never fit R710.
- **Why C720 alone is unsafe.** If SDRV does not actively hold the gate low while U701 is still unpowered (the datasheet doesn't say), a pack hot-plug couples the gate to 8.4 V × 10 nF/(10 nF + 2.1 nF Ciss) ≈ 6.9 V. Q701 would then turn fully on into ≈1.5 mF and could trip the R5460.
- **Why the ratio is 10×.** At 10 nF + 100 nF the coupling is 8.4 × 10/(10 + 100 + 2.1) ≈ 0.75 V nominal. With ±10 % tolerances that becomes 0.90 V, against Vth(min) 1.0 V at 25 °C (≈0.85 V at 60 °C). That margin is thin. Preferred pairs: **4.7 nF + 100 nF** (≈0.36 V), or 10 nF + 220 nF. The present values (10 nF/100 nF) sit exactly at the limit.
- **Why the R710 branch was removed.** R710 = 100 kΩ against SDRV's 50–100 nA gives Vgs ≤ 10 mV, so Q701 never conducts.
- **Turn-on with both fitted.** SDRV must first charge ≈112 nF + Ciss:
  - 1.1–4.5 s before conduction starts.
  - Then a 5–10 V/s source-follower ramp (≈7.5–15 mA into the bulk).
  - Then **≈5–11 s to full enhancement** (+5 V).

  The same delay applies after pack insertion, ship-mode exit and the 10 s QON reset.
- **Firmware consequence.** Before BOOST_EN, and before relying on battery power for any significant load, wait until Q701 is fully on: VSYS ≈ VBAT on the BQ ADC (ΔV < 50 mV), or a fixed ≥ 12 s after power-up from battery. Otherwise Q701 would carry the amp load at Vgs ≈ Vth, in linear mode, with an SOA risk.
- **Turn-off is unverified.** Ship mode, the IBAT_OCP trip and the 350 ms system reset all need SDRV to **sink** the extra ≈112 nF. The datasheet does not give the sink strength, so the extra capacitance may slow the over-current trip (it weakens S1) and stress Q701.
- **Bench gates before fitting either part:**
  1. SFET_G turn-off time (TP703) at an IBAT_OCP trip, a ship-mode entry and a 350 ms reset, with the caps fitted. Check the result against the NCEP3065QU SOA.
  2. 10 pack insertions with IBAT and SFET_G scoped: peak < 6 A, no R5460 trip.
  3. Turn-on time to full enhancement.
- Bench gate for fitting (S2): 10 pack insertions with IBAT and SFET_G scoped; peak < 6 A; no R5460 trip.

### 2.3 Design calculations

- **PROG = 8.2 kΩ ±1 %** selects 2S and 750 kHz at POR (Table 7-1: 1.5 MHz/2S = 6.04 k, 750 kHz/2S = 8.2 k).
  - **BQ25792 POR and watchdog defaults for 2S are VREG 8.4 V, ICHG 2 A, VSYSMIN 7.0 V** (BQ25792 ZHCSMD3C Table 9-2; the TI SLUSDG1C online edition agrees). The 1 A in BQ25798 Table 7-2 does not apply to the BQ25792 (release review S3).
  - Blank, hung or watchdog-expired firmware therefore charges at 2 A: 0.4C on the 5 Ah pack, but **0.57C on a 3.5 Ah fallback pack** (over the 0.5C rule).
  - **Firmware writes ICHG at every boot** (≤ 2.5 A for 5 Ah, ≤ 1.75 A for 3.5 Ah) and after every watchdog expiry (§7). If the 3.5 Ah pack is used, record the watchdog policy.
  - Over-discharge recovery (R5460 DOUT low, cells 3.0–3.2 V): the 2 A default flows through Q801's body diode, ≈0.7 V × 2 A ≈ **1.5 W** for tens of minutes. Layout gives Q801 copper for 1.5 W (§6). Bench: recover a deep-discharged pack with a thermocouple on Q801.
- **Inductor (§8.2.2.2).** ISW(max) = 5 A (ROC §6.3). Ripple ΔI = VSYS·(1 − VSYS/VBUS)/(L·fsw) at VSYS = 8.4 V, L = 2.2 µH, fsw = 750 kHz: 15 V → 2.24 A, 20 V → 2.95 A, 12 V → 1.53 A. Boost mode at 5 V in → 1.23 A. Peak = 5 + 2.95/2 = **6.5 A** < Isat 10 A. Datasheet minimum is "Isat ≥ 2 A for PFM pulses". In practice the 15 V/2.5 A charge-while-play case peaks at ≈ 5 + 1.1 = 6.1 A.
- **ILIM_HIZ hardware clamp** (§7.3.4.3): V = 1 V + 0.8 Ω·ILIM. With REGN 4.8–5.0 V (EC table) and divider 100/(51+100) = 0.662: V = 3.18–3.31 V → **ILIM = 2.72–2.89 A** (3.05 A at REGN 5.2 V max). That keeps a 3 A PD contract within rating. The pin also sets the ceiling the host can program while EN_EXTILIM = 1. Tie to REGN to remove it.
- **D+/D− left open.** USB data belongs to the CH340C, and the BQ's BC1.2 source drive (0.6 V on D+) would disturb enumeration. With open D+/D−, the auto detection ends as SDP (500 mA) or "unknown" (3 A) (Table 7-4). Either is clamped by ILIM_HIZ, and VINDPM (VBUS0 − 1.4 V ≥ 7 V source, §7.3.4.4) protects weak sources. **Firmware:** set AUTO_INDET_EN = 0, read CH224Q reg 0x50, and write IINDPM = min(PD current, 3.0 A). Without PD (5 V legacy), use ICO (EN_ICO = 1) or 1.5 A.
- **TS network** (Fig 7-12, §7.3.9.5). The thermistor is a 10 k NTC, B25/50 = 3435 (= 103AT). RT1/RT2 are E24 Basic values close to TI's 5.24 k/30.31 k (EVM: 5.23 k/30.1 k). Thresholds are VT1 = 73.3 % REGN (cold stop) and VT5 = 34.2 % (hot stop).
  - Computed with a β = 3435 model: **cold stop at 2.0 °C, hot stop at 60.8 °C** (TI values give 1.0/59.9 °C).
  - With a B3380 NTC: 1.6/61.5 °C.
  - Open NTC → TS = 30/35.1 = 85.5 % > 73.3 %, which reads as "cold" and suspends charging (fail-safe).
  - Firmware sets JEITA T2/T3 (TS_COOL/TS_WARM) as desired.
- **Capacitors.** VBUS/PMID parts are 50 V (≥ 20 V PD headroom, TI asks for ≥ 25 V); effective ≈ 3.5–4 µF each at 15–20 V (TI SLUSEA4D quotes 3.45 µF for a 10 µF/50 V 1206 at 24 V), so PMID = 3 × ≈4 = ≈12 µF ≥ 4 µF min (ROC). SYS/BAT parts are 25 V for a ≤ 9 V rail (≥ 16 V required for 2S): ≈ 6 µF each effective, so SYS ≈ 30 µF ≥ 6 µF min, BAT ≈ 12 µF ≥ 3 µF min.
- **Ship FET (Q701).** SDRV is a charge pump that drives the gate 5 V above BAT (§7.3.12), giving Vgs ≈ 5 V → Rds ≈ 2.8 mΩ. BATP is on the battery side (via R706), so the IC still sees the pack in ship mode. Modes (SDRV_CTRL):
  - 00 = on (POR default).
  - 01 = shutdown: I2C off, wake only by adapter.
  - 10 = ship: I2C on, wake by QON low ≥ tSM_EXIT (1 s or 15 ms), adapter, or register write.
  - 11 = 350 ms system power reset.

  Ship/shutdown are only accepted with no adapter. **Firmware must set SFET_PRESENT = 1 and EN_BATOC = 1** to enable the 9.3 A battery over-current cut-off (§7.3.13.1.7). **EN_BATOC is reset by a watchdog expiry and by REG_RST** (BQ25798 Table 7-30), so the full contract is in §7 (S1). Battery-side drain in ship mode is ≈ 15 µA: R5460 4 µA, 2 × HY2213 2.5 µA, mid divider 4.2 µA, BQ ship-mode quiescent. A 5 Ah pack lasts years.
- **QON** (SW701 on the main board, or the UI-board button SW4 through J501.20): press ≥ 1 s (or 15 ms with WKUP_DLY) to exit ship mode; hold ≥ 10 s for a full system power reset (§7.3.12.3). The 10 s reset is also the only battery-side reset for a hung ESP32 with the enclosure closed (S4).
- **Power-button limits and the "off" path (N2).**
  - /QON has no ESP32 input (no spare GPIO), and the BQ has no QON status bit, so **firmware cannot see a press**. The button is **wake (ship-mode exit) and 10 s reset only**.
  - **Off path:** a **long press (≥ 2 s) of the encoder push switch** (ENC_SW, GPIO4) makes firmware enter ship mode. Optional additional triggers: the web UI or an idle timer. Ship mode is reached by muting, PDN low, BOOST_EN low, then writing SDRV_CTRL = 10b (only accepted with no adapter; with USB present, firmware instead enters its own low-power idle).
  - Record this UX in the firmware spec. Reading the button in firmware would need a freed GPIO and an FFC/UI change before routing.
  - **Unverified, on the bench list:** what a continuously held /QON does beyond 10 s (a single reset, or repeated resets every ≈10 s). Also check that the ≥ 1 s wake press can't be confused with the start of a 10 s reset in normal use.
- **/CE** tied low via 10 k: charging starts without firmware (needed for dead-battery recovery). Firmware gates charging with EN_CHG.
- **STAT LED:** I = (4.8 − 2.8) V / 1 k ≈ 2 mA from REGN. REGN only exists with VBUS (or with the ADC on), so the LED never drains the battery. STAT sinks ≤ 6 mA (abs max). Low = charging; blinks 1 Hz on a fault.
- **Battery current limit reminder.** BATFET is 6 A RMS continuous, 10 A ≤ 1 s, 11 mΩ (ROC §6.3). The boost ILIM (§4.1) plus the amp DRC must keep the average battery current ≤ 6 A.

---

## 3. Sheet `battery` (pack connectors, fuse, 2S protection, balancing, NTC)

### 3.1 Component table

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol | Notes |
|---|---|---|---|---|---|---|---|
| J801 | XT30PW-M (male, PCB R/A) | `Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal` | 15 A, 1.2 mΩ | C431092 | E | `Connector_Generic:Conn_01x02` | **Pin 2 = +, pin 1 = −** (the footprint silkscreen shows "+" next to pad 2 at x = −5 and "−" next to pad 1 at x = 0) |
| J802 | B3B-XH-A (JST-XH 3P vertical) | `Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | 3 A | C144394 | E | `Connector_Generic:Conn_01x03` | Balance lead |
| J803 | B2B-PH-K-S (JST-PH 2P) | `Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical` | 2 A | C131337 | E | `Connector_Generic:Conn_01x02` | Pack NTC (**default sensor**, S6). Place at the pack-lead exit |
| F801 | 10 A very fast, 0451010.MRL | **custom** `power:Fuse_2410_6125Metric` (§0) | 125 V, 5.6 mΩ, I²t 26.5 A²s; derate to 7.5 A continuous | C44479 | E | `Device:Fuse` | Pack + |
| U801 | R5460N212AF | SOT-23-6 | OV 4.29 V (rel 4.05), UV 3.00 V (rel 3.20), excess-discharge 0.200 V/12 ms, short 1.1 V/300 µs | C259717 | E | custom `power:R5460x2` | 2S protector |
| R801 | 330 Ω | R_0603 | | C23138 | B | `Device:R` | VDD supply (Ricoh R1) |
| C801 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | VDD–VSS (C1) |
| R802 | 330 Ω | R_0603 | | C23138 | B | `Device:R` | VC (R2) |
| C802 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | VC–VSS (C2) |
| C803 | 10 nF | C_0603 | 50 V | C57112 | B | `Device:C` | VSS–V− (C3, "must mount ≥ 0.01 µF") |
| R803 | 1.0 kΩ | R_0603 | | C21190 | B | `Device:R` | V− sense (R3; R1 + R3 ≥ 1 k, R3 ≤ 3 k) |
| Q801 | NCEP3065QU | `Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET` | 30 V 65 A, 2.5 mΩ@6 V est. | C502964 | E | `Transistor_FET:CSD17581Q3A` | Discharge FET (DOUT) |
| Q802 | NCEP3065QU | same | same | C502964 | E | same | Charge FET (COUT) |
| U802 | HY2213-BB3A | SOT-23-6 | VCU 4.200 ± 0.025 V, VCR 4.190 V, N-FET drive | C113632 | E | custom `power:HY2213` | Lower cell balancer |
| U803 | HY2213-BB3A | SOT-23-6 | | C113632 | E | custom `power:HY2213` | Upper cell balancer |
| R804, R807 | 100 Ω | R_0603 | | C22775 | B | `Device:R` | HY2213 VDD (HY2213 §9: 100–200 Ω) |
| C804, C805 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | HY2213 VDD–VSS |
| Q803, Q804 | AO3400A | `Package_TO_SOT_SMD:SOT-23` | 30 V, Rds 48 mΩ@2.5 V | C20917 | B | `Transistor_FET:AO3400A` | Balance switches |
| R805, R806, R808, R809 | 120 Ω 1 % | `Resistor_SMD:R_1206_3216Metric` | **0.25 W** each | C17909 | B | `Device:R` | Bleed: 2 in parallel per cell |
| R810, R811 | 1.0 MΩ | R_0603 | | C22935 | B | `Device:R` | Mid-tap bias when the balance lead is unplugged |
| TH801 | 10 kΩ NTC, B25/50 = 3435 K, 1 % | `Resistor_SMD:R_0603_1608Metric` | | C2889048 | E | `Device:Thermistor_NTC` | On-board NTC (CMFA103F3435). **Alternate** sensor; fitted but unused in the default jumper position |
| JP801 | open | `Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm` | | – | – | `Jumper:SolderJumper_2_Open` | balance B− Kelvin (default open) |
| JP802 | open | same | | – | – | `Jumper:SolderJumper_2_Open` | balance B+ Kelvin (default open) |
| JP803 | bridged 1–2 | `Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm` | | – | – | `Jumper:SolderJumper_3_Bridged12` | NTC select (ECO-002 #3): **1–2 = pack NTC on J803 (default)**; cut and bridge 2–3 for on-board TH801. KiCad 10 has no stock Bridged23 jumper, so the outer-pad nets are swapped instead |
| TP801 | VBAT | `TestPoint:TestPoint_Pad_D1.5mm` | | – | – | `Connector:TestPoint` | `VBAT_PACK` |
| TP802 | BATT_N | same | | – | – | `Connector:TestPoint` | cell negative |
| TP803 | BAL_MID | same | | – | – | `Connector:TestPoint` | |

### 3.2 Pin-by-pin

**J801 XT30PW-M**: pin 2 (+) `PACK_P`; pin 1 (−) `BATT_N`. The two unnumbered mounting holes are mechanical (no net).

**J802 JST-XH 2S balance** (assumes the standard 2S lead: black 0 V, middle tap, red 8.4 V; **verify the pack's wire order**): pin 1 `BAL_N` → JP801 pin 1; JP801 pin 2 `BATT_N`. Pin 2 `BAL_MID`. Pin 3 `BAL_P` → JP802 pin 1; JP802 pin 2 `PACK_P` (before the fuse, so the fuse still protects).

**F801**: pin 1 `PACK_P`, pin 2 `VBAT_PACK` (global).

**U801 R5460N212AF** (Ricoh typical application, p.18):

| Pin | Name | Net | Connection |
|---|---|---|---|
| 1 | DOUT | `PROT_DO` | Q801 gate |
| 2 | COUT | `PROT_CO` | Q802 gate |
| 3 | V− | `PROT_VM` | R803 1 k to `GND` (= pack P−); C803 10 nF to `BATT_N` |
| 4 | VC | `PROT_VC` | R802 330 Ω from `BAL_MID`; C802 100 nF to `BATT_N` |
| 5 | VDD | `PROT_VDD` | R801 330 Ω from `VBAT_PACK`; C801 100 nF to `BATT_N` |
| 6 | VSS | `BATT_N` | cell negative |

**Q801 (discharge FET)**: S (1,2,3) `BATT_N`, G (4) `PROT_DO`, D (5) `PROT_D`.
**Q802 (charge FET)**: S (1,2,3) `GND`, G (4) `PROT_CO`, D (5) `PROT_D`. The drains are common (back-to-back), as in the Ricoh figure.

**U802 HY2213 (lower cell, between BATT_N and BAL_MID)**: 1 NC, 2 VDD `BAL1_VDD` (R804 100 Ω from `BAL_MID`; C804 to `BATT_N`), 3 VSS `BATT_N`, 4 NC, 5 NC, 6 OUT `BAL1_G`.
**Q803**: G `BAL1_G`, S `BATT_N`, D `BAL1_D`. **R805 ∥ R806** (120 Ω each): `BAL_MID` ↔ `BAL1_D`.

**U803 HY2213 (upper cell, between BAL_MID and VBAT_PACK)**: 2 VDD `BAL2_VDD` (R807 100 Ω from `VBAT_PACK`; C805 to `BAL_MID`), 3 VSS `BAL_MID`, 6 OUT `BAL2_G`, 1/4/5 NC.
**Q804**: G `BAL2_G`, S `BAL_MID`, D `BAL2_D`. **R808 ∥ R809**: `VBAT_PACK` ↔ `BAL2_D`.

**R810**: `VBAT_PACK` ↔ `BAL_MID`. **R811**: `BAL_MID` ↔ `BATT_N`.

**NTC selection**: TH801 pin 1 `BAT_NTC_INT`, pin 2 `GND`. J803 pin 1 `BAT_NTC_EXT`, pin 2 `GND`. JP803: **pin 1 (A) `BAT_NTC_EXT`**, pin 2 (C, common) `BAT_TS` (global), **pin 3 (B) `BAT_NTC_INT`**. With the factory bridge 1–2, the pack NTC is used.

### 3.3 Full current path (pack → BQ BAT pin) and calculations

```
Pack+ ─XT30 pin2─ PACK_P ─F801 10A─ VBAT_PACK ─Q701 ship FET (D→S)─ CHG_BAT ─ U701 BAT(22,23) ─BATFET 11mΩ─ SYS = VSYS
Pack− ─XT30 pin1─ BATT_N ─Q801 (S→D)─ PROT_D ─Q802 (D→S)─ GND (= every ground on the board)
```
Series resistance ≈ connector 2 × 1.2 + fuse 5.6 + Q701 2.8 + 2 × 2.5 (Q801/Q802 at Vgs ≈ VDD ≈ 7 V) + BATFET 11 ≈ **27 mΩ** → 0.19 V and 1.3 W total at 7 A, 0.97 W at 6 A. Q801/Q802 each dissipate 2.5 mΩ × 6² = 90 mW.

- **Protection thresholds (R5460N212AF, selection table).** Over-charge 4.290 V (rel 4.050 V, 1.0 s); over-discharge 3.000 V (rel 3.200 V, 128 ms). "AF" version: over-discharge releases only after a charger is connected, then at the release voltage. Standby ≤ 0.1 µA.
  - Excess discharge current: V− > 0.200 V for 12 ms → 0.2 V / (2 × 2.5 mΩ) ≈ **40 A**.
  - Short: V− > 1.1 V for 300 µs.

  Both are last-resort only. Real over-current protection comes from the BQ IBAT_OCP 9.3 A (with Q701), the boost ILIM (§4.1) and F801.
- **Gate drive.** DOUT/COUT are CMOS outputs swinging VDD (6.0–8.4 V) → Vgs ≈ 6–8 V on the NCEP3065QU (Vth 1.0–2.0 V, Rds 3.0 mΩ@4.5 V, 1.9 mΩ@10 V). No gate resistors (Ricoh figure).
- **Fuse.** 10 A rating, derated 25 % → 7.5 A continuous at 25 °C (Littelfuse note), which is ≥ the 6 A design ceiling. 200 % opens ≤ 5 s.
- **Balancing (HY2213 §6, §9).** HY2213-BB3A switches on above 4.200 V and off below 4.190 V (code A = N-MOSFET drive, OUT active high). Bleed R = 120 ∥ 120 = 60 Ω → I = 4.2/60 = **70 mA**. Each 1206 dissipates 4.2²/120 = **0.147 W** (59 % of 0.25 W). That is ≈ 0.3 W per balancing cell, only at the very end of a charge. HY2213 notes: R(VDD) 100–200 Ω, C 0.01–1 µF.
- **Mid-tap bias.** R810/R811 hold `BAL_MID` = VBAT/2 when the balance plug is out, so neither the R5460 nor the HY2213s see a floating cell (drain 8.4 V / 2 MΩ = 4.2 µA). The real cell junction overrides it when J802 is plugged.
  - **Residual risk (S7, accepted):** with J802 unplugged, **cell-level OV/UV protection is silently lost**. For example, 4.45 V + 3.95 V reads as 4.2 V + 4.2 V. There is no ADC on BAL_MID to detect this.
  - **Assembly step, mandatory before the first charge and after any pack swap:**
    1. Check J802 is fully seated.
    2. With the pack connected, measure TP803 − TP802. It should read the lower cell voltage, 3.0–4.2 V.
    3. Briefly load TP803–TP802 with a 1 kΩ resistor. A seated lead holds the voltage (drop < 10 mV). An unplugged lead collapses toward 0 V, because the 1 MΩ divider can't source current.

    Record the result in the build log.
- **NTC (S6).** Default: a 10 kΩ, B ≈ 3435, **isolated 2-wire** NTC bonded to the pack face and wired to J803 (the pack itself has no NTC). Record it in the pack harness drawing.
  - The pack sits on a tray 7 mm above the board, so TH801, next to J801, would track board temperature, not cell temperature. TH801 remains as the alternate.
  - Don't use a pack NTC that is referenced to the cell negative inside the pack, because B− ≠ GND here.
  - With J803 unplugged, TS reads "cold" (85.5 % of REGN) and **charging is suspended**. This is fail-safe, but the harness NTC must be fitted for the pack to charge.
  - The TS window covers **charging only**. There is no hardware discharge-temperature cut-off, so firmware must read TS in battery mode and stop playback above the pack limit (§7).

---

## 4. Sheet `rails`

### 4.1 TPS61178 boost, VSYS (6.0–8.6 V) → PVDD 18.0 V

#### 4.1.1 Component table

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol | Notes / citation |
|---|---|---|---|---|---|---|---|
| U901 | TPS61178RNWR | **custom** `power:Texas_RNW0013A_VQFN-HR-13_3x3.5mm_P0.5mm` | Vin 2.7–20 V, Vout 4.5–20 V, OVP 21 V (20.5 min) | C127918 | E | **custom** `power:TPS61178` | |
| L901 | 2.2 µH FXL1040-2R2-M | `Inductor_SMD:L_Changjiang_FXL1040` | Irms 12 A, Isat 18 A, 7 mΩ | C167228 | E | `Device:L` | |
| C901, C902 | 22 µF | C_1206 | 25 V X5R | C12891 | B | `Device:C` | VIN bulk (VSYS ≤ 9 V) |
| C903 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | VIN pin 12 |
| C904 | 4.7 µF | C_0603 | 16 V X5R | C19666 | B | `Device:C` | VCC (≥ 10 × CBST, §9.2.4.4.5) |
| C905 | 100 nF | C_0603 | 50 V X7R | C14663 | B | `Device:C` | BST–SW (0.1–1 µF, ≥ 10 V, §9.2.4.4.4) |
| C906–C913 | 10 µF (×8) | C_1206 | **50 V** X5R | C13585 | B | `Device:C` | COUT on `PVDD` at pins 8/6 (≈ 4.5 µF each at 18 V → ≈ 36 µF) |
| C914 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | COUT1 HF, at pins 8/6 |
| R901 | 300 kΩ 1 % | R_0603 | | C23024 | B | `Device:R` | FREQ → AGND: 599 kHz |
| R902 | 82 kΩ 1 % | R_0603 | | C23254 | B | `Device:R` | ILIMIT → AGND |
| R903 | 100 kΩ 1 % | R_0603 | | C25803 | B | `Device:R` | Rc (ECO-001) |
| C915 | 15 nF | C_0603 | 50 V X7R | C1596 | E | `Device:C` | Cc (ECO-001) |
| C916 | 10 pF | C_0603 | 50 V C0G | C1634 | B | `Device:C` | Cp, COMP → AGND |
| R904 | 300 kΩ 1 % | R_0603 | | C23024 | B | `Device:R` | RUP: PVDD → FB |
| R905 | 24 kΩ 1 % | R_0603 | | C23352 | B | `Device:R` | RDOWN1: FB → AGND |
| R906 | 200 kΩ 1 % | R_0603 | | C25811 | B | `Device:R` | RDOWN2: FB → AGND |
| R907 | 68 kΩ 1 % | R_0603 | | C23231 | B | `Device:R` | trim injection, **fitted** (ECO-001) |
| D901 | 1N4148W | `Diode_SMD:D_SOD-123` | 75 V | C81598 | B | `Device:D` (1 K, 2 A) | trim diode, **fitted** (ECO-001) |
| R908, R909 | 10 kΩ | R_0603 | | C25804 | B | `Device:R` | trim RC (fitted) |
| C917, C918 | 1 µF | C_0603 | 50 V X5R | C15849 | B | `Device:C` | trim RC (fitted) |
| C920 | 470 µF | `Capacitor_SMD:CP_Elec_10x10` | **35 V**, 105 °C, 10×10.2 mm (KNSCHA RVT470UF35V67RV0056) | C2836436 | E | `Device:C_Polarized` | PVDD bulk (same part as the amp sheets) |
| TP901 | PVDD | `TestPoint:TestPoint_Pad_D2.0mm` | | – | – | `Connector:TestPoint` | |

Pin types for the custom symbol are in §0.1.

#### 4.1.2 Custom footprint `Texas_RNW0013A_VQFN-HR-13_3x3.5mm_P0.5mm` (TPS61178 §13, RNW0013A land pattern; top view, KiCad coordinates, +y down)

- Body 3.50 (x) × 3.00 (y) mm, 1.0 mm max height. Pin 1 at top-left.
- Pads 1–5: roundrect 0.70 (x) × 0.25 (y) mm, r = 0.05. Centres x = −1.60; y = −1.00 (pin 1), −0.50 (2), 0.00 (3), +0.50 (4), +1.00 (5).
- Pads 13–9: same size, x = +1.60; y = −1.00 (pin 13), −0.50 (12), 0.00 (11), +0.50 (10), +1.00 (9).
- Pads 6, 7, 8 (power bars): roundrect 0.25 (x) × 3.40 (y) mm, centred at y = 0. x = −0.55 (pin 6 PGND), 0.00 (pin 7 SW), +0.55 (pin 8 VOUT). Solder-mask-defined in TI's pattern (mask opening ≈ pad + 0.05 mm per side). The bars extend 0.2 mm past the body top and bottom.
- Courtyard 4.30 × 3.90 mm. Paste 1:1 on pads 1–5/9–13; split the bars into 3 apertures each (TI stencil ≈ 90 %).

#### 4.1.3 U901 pin-by-pin

| Pin | Name | Net | Connection |
|---|---|---|---|
| 1 | FREQ/SYNC | `BST_FREQ` | R901 300 k to AGND (must not float) |
| 2 | AGND | `GND` | quiet ground; tie to PGND at one point (pin 6 pad) |
| 3 | ILIMIT | `BST_ILIM` | R902 82 k to AGND |
| 4 | COMP | `BST_COMP` | R903 100 k → `BST_CZ` → C915 15 nF → AGND; C916 10 pF COMP → AGND |
| 5 | FB | `BST_FB` | R904 from `PVDD`; R905 and R906 to AGND; R907 (fitted) to `TRIM_K` |
| 6 | PGND | `GND` | power ground, thermal vias |
| 7 | SW | `BST_SW` | L901 pin 2; C905 to `BST_BOOT` |
| 8 | VOUT | `PVDD` (global) | C906–C914 at the pin; C920; R904 sense |
| 9 | DISDRV | no connect (KiCad no-connect flag) | Load-disconnect not used (§4.1.4) |
| 10 | VCC | `BST_VCC` | C904 4.7 µF to GND |
| 11 | EN | `BOOST_EN` (global) | from ESP32 GPIO2. 100 k pull-down is R107 on the mcu sheet. Internal 800 k pull-down too |
| 12 | VIN | `VSYS` | C903 at the pin, C901/C902 |
| 13 | BST | `BST_BOOT` | C905 to `BST_SW` |

**L901**: pin 1 `VSYS`, pin 2 `BST_SW`.
**Trim network**: R908 `PVDD_TRIM` ↔ `TRIM_A`; C917 `TRIM_A` ↔ GND; R909 `TRIM_A` ↔ `TRIM_RC`; C918 `TRIM_RC` ↔ GND; D901 anode (pin 2) `TRIM_RC`, cathode (pin 1) `TRIM_K`; R907 `TRIM_K` ↔ `BST_FB`.
**C920 (470 µF)**: + `PVDD`, − `GND`.

#### 4.1.4 Calculations (TPS61178 SLVSDA7E)

- **Output voltage** (§9.2.4, eq. 4; VREF = 1.180/1.198/1.210 V min/typ/max):
  - RDOWN = 24 k ∥ 200 k = 21.43 k. PVDD = 1.198 × (1 + 300 k/21.43 k) = **17.97 V** (17.70–18.15 V over the VREF tolerance, ±1 % resistors add ±0.2 V).
  - Margin to OVP 20.5 V min and to Vout(max) 20 V: ≥ 1.85 V.
  - Divider current 60 µA ≫ 100 × 60 nA FB leakage. RDOWN ≤ 100 k, as TI recommends.
- **PVDD_TRIM** (diode-OR into FB; R907 and D901 **fitted**, ECO-001):
  - Hand model (fixed 0.45 V diode drop): PVDD = 17.97 − 300 k × (Vt − 0.45 − 1.198)/(68 k + 20 k).
  - SPICE (sim S4, 25 °C), which supersedes the hand values (at 5–15 µA the diode drops ≈0.35 V and the knee is soft):

    | Vt | Hand model | SPICE |
    |---|---|---|
    | 1.6 V | 17.97 V | 17.58 V |
    | 2.0 V | 16.8 V | 16.43 V |
    | 2.5 V | 15.1 V | 14.84 V |
    | 3.0 V | 13.4 V | 13.20 V |
    | 3.3 V | 12.3 V | 12.20 V |

    Slope ≈ −3.4 V/V; range **18.0 → 12.2 V over 1.5–3.3 V**.
  - **Hi-Z or 0 V ⇒ nominal 18 V.** The trim can only lower PVDD, apart from D901 reverse leakage: +2 mV at 25 °C, +19 mV at 60 °C, +86 mV at 85 °C (OVP 20.5 V min, harmless). A GPIO stuck high gives ≈12 V, and the amps still work.
  - Two-pole RC filter (10 k/1 µF ×2): fc = 15.9 Hz. A ≥ 20 kHz LEDC PWM leaves < 1 µV of ripple at FB (sim). **A trim step settles in 70–110 ms; allow ≥ 150 ms.** The DAC1 output also works (8-bit = 44 mV of PVDD per LSB; 10-bit LEDC ≈ 11 mV).
  - Temperature drift ≈ −8.6 mV/°C on PVDD while trimming. Firmware should calibrate duty → PVDD once.
- **Switching frequency** (§8.3.7, eq. 2–3): RFREQ = (1/f − 50 ns)/(3 × 1.8 pF). With 300 k: f = 1/(1.62 µs + 0.05 µs) = **599 kHz**. That keeps clear of the amps' 768 kHz and 1.536 MHz: 2 × 599 = 1.198 MHz (338 kHz from 1.536 MHz), 768 − 599 = 169 kHz. Every beat with m + n ≤ 7 is ≥ 91 kHz at nominal. The oscillator tolerance is ±20 % (EC table at 342 k: 400–600 kHz), so high-order beats can land anywhere. Their amplitude is negligible, and they disappear in PFM. External sync is documented only for the forced-PWM TPS611781 (§8.3.8); that part is a drop-in swap (C2862009) if PFM bursts turn out audible.
- **Current limit** (§8.3.5, eq. 1 RLIMIT[kΩ] = 745/ILIMIT[A]; EC table at 80.6 k: 6.4/8.0/9.4 A min/typ/max). 82 k → 9.1 A (eq. 1); scaled EC ≈ **6.3/7.9/9.2 A** (min/typ/max).
  - Load demand: at 40 W out, 18 V: Vin 6.0 V → Iin 7.0 A, ripple 3.04 A, peak 8.5 A. Vin 7.4 V → peak 7.3 A.
  - So a low battery can current-limit at ≈ 30 W. That is intended: it keeps the battery ≤ 6 A RMS and below the BQ's 9.3 A IBAT_OCP.
  - The short-circuit limit (20 A) triggers hiccup (§8.3.6).
- **Inductor** (§9.2.4.1). ΔI = Vin·D/(L·f): 3.04 A (6 V), 3.31 A (7.4 V), 3.40 A (8.4 V). All are below TI's 4 A slope-compensation limit. Recommended range 0.47–3.3 µH. Peak ≤ 9.2 A (ILIM max) ≪ Isat 18 A; Irms ≤ 7.1 A < 12 A.
- **Soft start into ≈ 1.5 mF.** Internal: a 2.6 ms pre-charge to 1.1 × VIN at 500 kHz, then a 3.2 ms reference ramp (§8.3.3). There is no soft-start pin. The hand estimate follows; **sim S1 (TI switching model) supersedes it** (see the end of this item).
  - PVDD is pre-biased at VSYS − 0.5 V (≈ 7 V = 39 % of 18 V). That is above the 30 % "output short" hiccup threshold, and pre-biased start-up is supported (§8.3.11).
  - Pre-charge: 1.5 mF × ≈1.2 V / 2.6 ms ≈ 0.7 A. Benign.
  - Ramp, 7 → 18 V in 3.2 ms: would need 1.5 mF × 11 V / 3.2 ms ≈ 5.2 A output (≈ 15 A input), which exceeds ILIM. The converter therefore runs in cycle-by-cycle current limit: average inductor current ≈ ILIM(min) 6.3 A − ½ × 3 A ripple ≈ 4.8 A, giving Iout ≈ 4.8 × 7/18 × 0.95 ≈ 1.8 A. PVDD reaches 18 V in ≈ **9 ms** (worst case, at minimum ILIM).
  - Neither hiccup trigger is reached: inductor current is held at ILIM ≤ 9.2 A ≪ the 20 A short limit, and VOUT never falls below 30 %. Battery current during this ≈ 10 ms is ≈ 5–8 A, within the BATFET's 10 A ≤ 1 s peak.
  - **Sim S1 result (ECO-001):**
    - At 6.0 V and ILIM(min) the converter runs sub-harmonic in current limit (average IL 3.3–3.9 A), so the ramp takes **11 ms**.
    - No hiccup, but only 0.39 V of margin to the 30 % short threshold.
    - The error amplifier winds up during the current-limited ramp, so **PVDD overshoots to 19.4 V (typ), and to the ≈21 V OVP worst case**. It stays there until the amps load it. All parts tolerate this (TAS5805M 26.4 V; caps 35/50 V), but it is avoided with the firmware soft start below.
  - **Firmware PVDD soft start (R907/D901 fitted):**
    1. Drive `PVDD_TRIM` to 3.3 V (DAC 255 or 100 % duty) **≥ 150 ms before** BOOST_EN, so the RC is charged.
    2. BOOST_EN high. PVDD rises only to ≈12.2 V, which keeps the converter out of current limit and prevents windup.
    3. ≥ 20 ms later, release amp PDN.
    4. Ramp `PVDD_TRIM` down to the target over ≥ 30–50 ms. PVDD settles ≥ 150 ms after the last trim step.
  - **Sequencing (both cases):** BOOST_EN high → wait **≥ 20 ms** (covers the 11 ms ramp) → release amp PDN. Pull PDN low before dropping BOOST_EN.
  - Bench check: scope PVDD and IL at turn-on with all three 470 µF fitted, with and without the trim soft start.
- **Disconnect FET: not used.** DISDRV (pin 9) is left open: "Leave it floating if not using the load disconnect function" (pin table).
  - Why: the PVDD bulk is ≈ 3 × 470 µF + 9 × 10 µF ≈ 1.5 mF (this sheet + both amp sheets), but COUT1 can only be ≈ 36 µF. TI's "COUT2 ≤ 10 × COUT1" rule (§9.2.4.2) and the ≤ 3 ms FET turn-on limit (§9.2.4.4.3) can't be met, so a disconnect FET would risk start-up hiccup.
  - Consequences: with EN low, PVDD = VSYS − Vf(body diode) ≈ 5.5–8 V. Amp PDN is low, so the draw is µA. TPS61178 shutdown current ≤ 3.5 µA; SW reverse leakage ≤ 6.5 µA.
  - Inrush at battery connect: the bulk charges through Q701 as a source follower, ramped by SDRV's 50–100 nA into Crss 15.5–30 pF (higher at low V_DS). That gives 1.7–6.5 V/ms, so **2.5–9.7 A** (release review S2; the v1.0 figure of 3.8 A assumed 40 pF). It is bounded only by fitting C720 together with C721 (rule and numbers in §2.2), after the bench check.
  - With VBUS present, the charger's own soft start limits VSYS inrush.
  - A hard PVDD short (battery → L901 → high-side body diode → short) bypasses the boost's hiccup protection. It is cleared by the BQ IBAT_OCP ship-FET trip **only while the §7 firmware contract holds**. Otherwise only the R5460 (≈40 A for 12 ms) and F801 (slow at 10–20 A) act, and a 10–30 A soft fault can exceed the BATFET's 10 A/1 s rating (S1). Bench: 20 mΩ PVDD short with blank and with armed firmware. Record the trip time and peak IBAT. If the blank-firmware result is unacceptable, record the remedy (a lower-VDET3 R5460 variant, a smaller fuse, or restoring a disconnect) before routing.
- **Output capacitance.** COUT = C906–C913 (8 × 10 µF/50 V ≈ 36 µF effective at 18 V) + C914, all at pins 8/6. PVDD bulk: C920 (470 µF/35 V) on this sheet plus the amp sheets' 2 × 470 µF and 8 × 10 µF. At 18 V the 35 V electrolytic runs at 51 % of rating.
- **Loop compensation** (§9.2.4.4, eq. 15–29; ECO-001). **Rc = R903 = 100 kΩ, Cc = C915 = 15 nF, Cp = C916 = 10 pF.**
  - The zero is unchanged: 1/(2π × 100 k × 15 nF) = 106 Hz.
  - Sim S1/S7 (1.48 mF bank, ESR 0.05–0.34 Ω, Vin 6.0–8.4 V): **PM ≥ 79°, GM ≥ 15 dB**.
  - PVDD closed-loop impedance meets the 0.14 Ω target. A 0.2 → 2 A step at 6 V dips **0.34 V**.
  - History: v1.1's 33 k/47 nF was stable (PM ≥ 66°) but left a 0.46–0.57 Ω impedance peak at ≈150 Hz (≈1 V dip, ≈2 V bass sag).
  - Rejected earlier: TI's 15 k/6.8 nF and 22 k/10 nF (28–36° PM with ≈1.4 mF of low-ESR bulk).
  - The 7.4 V load step was not simulated (ngspice stalled). Verify on the bench with 0.5 → 2.5 A at 6.0 and 7.4 V.

### 4.2 TPS62933 buck, VSYS → +3V3

#### 4.2.1 Component table

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol | Notes |
|---|---|---|---|---|---|---|---|
| U951 | TPS62933DRLR | `Package_TO_SOT_SMD:SOT-583-8` | 3.8–30 V, 3 A, 12 µA IQ (PFM) | C3200405 | E | `Regulator_Switching:TPS62933` | stock sym+fp |
| L951 | 4.7 µH FXL0420-4R7-M | `Inductor_SMD:L_Changjiang_FXL0420` | Irms 2.8 A / Isat 3 A, 105 mΩ | C167208 | E | `Device:L` | Table 10-2 (3.3 V/500 kHz → 4.7 µH) |
| C951, C952 | 10 µF | C_0805 | 25 V X5R | C15850 | B | `Device:C` | VIN |
| C953 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | VIN HF, at pins 3–4 |
| R951 | 300 kΩ 1 % | R_0603 | | C23024 | B | `Device:R` | EN UVLO top (VSYS → EN) |
| R952 | 82 kΩ 1 % | R_0603 | | C23254 | B | `Device:R` | EN UVLO bottom |
| C954 | 33 nF | C_0603 | 50 V X7R | C21117 | B | `Device:C` | SS (≥ 6.8 nF; do not float) |
| R953 | 0 Ω | R_0603 | | C21189 | B | `Device:R` | BST series (TI: < 10 Ω allowed) |
| C955 | 100 nF | C_0603 | 50 V X7R | C14663 | B | `Device:C` | BST–SW (≥ 16 V) |
| R954 | 75 kΩ 1 % | R_0603 | | C23242 | B | `Device:R` | FB top |
| R955 | 24 kΩ 1 % | R_0603 | | C23352 | B | `Device:R` | FB bottom |
| C956 | 10 pF | C_0603 | 50 V C0G | C1634 | B | `Device:C` | **DNP** CFF across R954 |
| C957, C958 | 22 µF | C_1206 | 25 V X5R | C12891 | B | `Device:C` | VOUT |
| C959 | 100 nF | C_0603 | 50 V | C14663 | B | `Device:C` | VOUT HF |
| D951 | Red LED KT-0603R | `LED_SMD:LED_0603_1608Metric` | | C2286 | B | `Device:LED` | **DNP** power LED |
| R956 | 1.0 kΩ | R_0603 | | C21190 | B | `Device:R` | **DNP** (with D951) |
| TP951 | +3V3 | `TestPoint:TestPoint_Pad_D1.5mm` | | – | – | `Connector:TestPoint` | |
| TP952, TP953, TP954 | GND | `TestPoint:TestPoint_Pad_D2.0mm` | | – | – | `Connector:TestPoint` | one near each converter |

#### 4.2.2 U951 pin-by-pin

| Pin | Name | Net | Connection |
|---|---|---|---|
| 1 | RT | no connect (KiCad no-connect flag) | Floating = 500 kHz (Table 9-1) |
| 2 | EN | `BUCK_EN` | R951 from `VSYS`, R952 to GND |
| 3 | VIN | `VSYS` | C951–C953 |
| 4 | GND | `GND` | |
| 5 | SW | `BUCK_SW` | L951 pin 1; C955 pin 2 |
| 6 | BST | `BUCK_BST` | R953 → `BUCK_BST_C` → C955 → `BUCK_SW` |
| 7 | SS | `BUCK_SS` | C954 33 nF to GND |
| 8 | FB | `BUCK_FB` | R954 from `+3V3`, R955 to GND, C956 (DNP) from `+3V3` |

**L951**: pin 1 `BUCK_SW`, pin 2 `+3V3`. **D951/R956 (DNP)**: `+3V3` → R956 → D951 anode; D951 cathode → GND.

#### 4.2.3 Calculations (TPS62933 SLUSEA4D)

- **VOUT** (eq. 14): 0.8 × (1 + 75/24) = **3.300 V** (VFB 0.792–0.808 V at 25 °C → 3.27–3.33 V).
- **UVLO** (§9.3.6, eq. 3–5; VEN_RISE 1.21 V, VEN_FALL 1.17 V, Ip 0.7 µA, Ih 1.4 µA).
  - R1 = 300 k, R2 = 82 k give start = (1.21 − 0.7 µ × 64.4 k) × 382/82 = **5.43 V** and stop = (1.17 − 2.1 µ × 64.4 k) × 4.659 = **4.82 V**. Hysteresis 0.61 V ≥ 0.5 V as recommended.
  - VEN = 2.07 V at 9 V in and 4.43 V even at a 20 V fault, both < 5.5 V max.
  - The battery protector cuts at 6.0 V and VSYSMIN is 7.0 V with VBUS present, so 3V3 never chatters.
- **fsw** 500 kHz (RT floating). Ripple ΔI = 3.3 × (8.6 − 3.3)/(8.6 × 4.7 µ × 500 k) = 0.87 A. Peak at a 0.8 A load = 1.23 A < Isat 3 A.
- **COUT**: 2 × 22 µF/25 V at 3.3 V ≈ 2 × 17 µF ≈ 34 µF effective. Table 10-2: typical 40 µF, minimum 15 µF.
- **SS**: tss = 33 nF × 0.8 V/5.5 µA = **4.8 ms** (§10.2.2.4).
- **Inrush and sequencing.** +3V3 comes up whenever VSYS > 5.43 V, so it is always on with VBUS (VSYS ≥ 7 V). Ship mode turns it off by removing VSYS.

---

## 5. Test points (summary)

| TP | Net | Sheet |
|---|---|---|
| TP601 | `VBUS` | usb_power |
| TP602 | `PD_PG` (optional) | usb_power |
| TP701 | `VSYS` | charger |
| TP702 | `CHG_BAT` (optional) | charger |
| TP801 | `VBAT_PACK` | battery |
| TP802 | `BATT_N` | battery |
| TP803 | `BAL_MID` | battery |
| TP901 | `PVDD` | rails |
| TP951 | `+3V3` | rails |
| TP952–TP954 | `GND` | rails |

Indicators: D701 (charge STAT, fitted) and D951 (3V3 power, DNP to save standby current).

---

## 6. Layout checklist

**Charger (U701)**
- Follow the TI EVM (SLUUCB5E §4).
- PMID caps (C707 first, then C704–C706) on the same layer, straight across PMID (29) ↔ GND (27). This is the buck-mode hot loop through Q1/Q2.
- SYS caps (C716 first) straight across SYS (25) ↔ GND. This is the boost-mode hot loop through Q3/Q4.
- Keep the SW1 (28) and SW2 (26) copper just large enough for L701.
- BTST caps go within 1 mm of their pins.
- REGN cap at pin 5.
- GND pin 27 gets a via array into the inner GND plane.
- PROG/ILIM/TS resistors return to a quiet GND spot, away from SW nodes.

**Boost (U901)**
- Hot loop SW (7) → VOUT (8) → C914 / first C906 → PGND (6) under 5 mm, on the top layer. The bars are 0.55 mm apart, so put C914 directly across pins 8–6.
- Wide pours on VSYS/SW/PVDD, with thermal vias under the PGND bar and the GND pins. Up to ≈ 2 W of IC loss at 40 W.
- AGND (2) connects to PGND only at the pin-6 pad.
- FB divider (R904–R907) within 3 mm of pin 5. Route the R904 sense from the C906 PVDD node as a thin trace away from L901/SW.
- COMP parts next to pin 4.

**Buck (U951)**
- C953/C951 across VIN (3)–GND (4) within 1 mm. SW node small. FB parts at pin 8, away from SW and L951.

**Protection and pack (high current, design for 7 A continuous / 10 A peak)**
- `PACK_P` → F801 → `VBAT_PACK` → Q701 → `CHG_BAT`, and `BATT_N` → Q801 → Q802 → `GND`, need ≥ 3 mm traces on 1 oz plus duplicates on inner/bottom layers, or pours.
- **`BATT_N` is a separate copper island.** It must never touch the GND plane or GND pours (DRC: keep a net-class clearance). Only J801 pin 1, J802 via JP801, Q801 source, U801 VSS, C801/C802/C803, U802/Q803, R811 and TP802 connect to it.
- R803 (V−) returns at the Q802 source / GND junction.
- The common-drain `PROT_D` gets a pour joining both drain tabs.
- **Q801 needs copper for 1.5 W** (body-diode conduction during over-discharge recovery at the 2 A default, S3). Use ≥ 2 cm² on the drain tab and the BATT_N source, with thermal vias into the matching islands (never into GND for BATT_N). Keep it away from the pack NTC lead and TH801.
- Q701: leave room next to it for the DNP C720 (gate–drain) and C721 (gate–source) at SFET_G, plus a test pad on SFET_G (ECO-002 #5).

**Balancing**
- R805/R806/R808/R809 dissipate up to 0.3 W per cell. Spread them out, keep them away from TH801 and U801, and give them copper for heat.

**NTC**
- J803 (the default pack NTC) goes at the pack-lead exit next to J801/J802 (S6). TH801 (alternate) sits next to J801, away from the boost, charger and amps. JP803 is reachable for re-jumpering. The `BAT_TS` trace runs away from SW nodes, with a GND reference.

**USB-C**
- D601, U601 and U602 within 5 mm of J601.
- D+/D− as a 90 Ω differential pair (short; full speed is tolerant).
- U603 (0.4 mm DFN) EP gets ≥ 2 vias; C604 at pin 1.
- Q601/Q602 next to U603.

**Thermal**
- Heat sources: U901 + L901 (≈ 0.5 W typical, ≈ 2.5 W worst), U701 during charge-while-play (≈ 1.5 W), the battery path (≈ 1 W at 6 A), Q801 during over-discharge recovery (≈ 1.5 W, S3), the balancers (≈ 0.6 W, end of charge only). Spread them across the board.

**Bulk**
- C920 (10 × 10.2 mm electrolytic) goes in mech zone D (≤ 24 mm) between the boost output and the amps' PVDD entry, on a wide PVDD pour (≥ 3 A). The amp bulks C301/C401 go in zone G or on the bottom side (S11).

---

## 7. Firmware notes (for the firmware spec)

1. **BQ25792 (0x6B): protection contract (release review S1, ECO-002 #7). Mandatory; do this first at every boot.**
   - Write **SFET_PRESENT = 1, EN_BATOC = 1, WATCHDOG = 0** (watchdog disabled).
   - If the watchdog must stay enabled, re-arm all three and ICHG on every WD_FLAG/INT, because **a watchdog expiry or REG_RST resets EN_BATOC to 0 and ICHG to 2 A** (BQ25798 Table 7-30; BQ25792 Table 9-2).
   - **Read back** and verify. If it fails, keep BOOST_EN low and report a fault.
   - Bench acceptance: 20 mΩ PVDD short with blank firmware and with armed firmware (§4.1.4).
   - Then:
     - Set AUTO_INDET_EN = 0 (D+/D− are not connected).
     - **Write ICHG at boot**: ≤ 2.5 A for 5 Ah, ≤ 1.75 A for 3.5 Ah. The POR default is 2 A.
     - VREG 8.4 V (or 8.3 V for longevity).
     - IINDPM from CH224Q reg 0x50 × 50 mA, capped at 3.0 A. With no PD (CH224Q reg 0x09), use ≤ 0.5–1.5 A (L1).
     - JEITA: stop charging above 45 °C (ECO-001 #6).
     - EN_IBAT (ADC) for coulomb counting.
     - Read TS in battery mode and stop playback above the pack limit (no hardware discharge cut-off, S6).
   - **Power on/off UX (N2):**
     - **On:** the power button (QON ≥ 1 s exits ship mode) or plugging in USB.
     - **Off:** an encoder long-press (≥ 2 s) → mute → PDN low → BOOST_EN low → SDRV_CTRL = 10b (ship mode; with no adapter only).
     - Firmware cannot read the power button. A ≥ 10 s press is a hardware reset.
   - **After power-up from battery** (insertion, ship exit, QON reset): if C720/C721 are fitted, wait until VSYS ≈ VBAT (ΔV < 50 mV on the BQ ADC), or ≥ 12 s, before BOOST_EN (N1, §2.2).
   - I2C: run 100–200 kHz until the rise time is scoped with VBUS present and absent (S5).
2. **CH224Q (0x22/0x23)**: only reachable while VBUS is present. Read reg 0x09 (protocol), 0x50 (current) and 0x60–0x8F (source PDOs). Optional: write 0x0A to change the request. Never select 28 V/EPR.
3. **Boost**
   - Power-up:
     1. `PVDD_TRIM` = 3.3 V for ≥ 150 ms.
     2. BOOST_EN high.
     3. Wait **≥ 20 ms**, then release amp PDN.
     4. Ramp `PVDD_TRIM` to the target over ≥ 30–50 ms.

     This soft start avoids the 19.4–21 V start-up overshoot (§4.1.4).
   - Power-down: PDN low first, then BOOST_EN low.
   - PVDD_TRIM (R907/D901 fitted): 1.5–3.3 V → 18.0–12.2 V (SPICE curve in §4.1.4). Use LEDC ≥ 20 kHz or DAC1. Allow ≥ 150 ms after each trim change.
   - Keep the amp DRC/limiter so the average battery current stays ≤ 6 A.
   - With BOOST_EN low, PVDD is ≈ VSYS − 0.5 V (not 0 V) because there is no disconnect FET. Keep amp PDN low whenever the boost is off. The TAS5805M register setup can happen with PVDD at either level.
   - EN_BATOC = 1 is also the PVDD short-circuit protection (§4.1.4).
