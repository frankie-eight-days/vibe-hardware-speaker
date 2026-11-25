# Main PCB: MCU, audio and interface circuit specification (v1.2: ECO-001 / ECO-002)

Status: v1.2, 2026-11-24 (changelog at the end). Scope: sheets `mcu`, `usb_uart`, `amp_left`, `amp_right`, `ui_io` of the main board (`hw/mainboard/speaker_main`). Power is a separate spec. This document is written so the schematic can be drawn without datasheets: every pin, value and net is listed below.

**Conventions**
- Net names in `CODE` are exact. Global nets shared with the power sheet: `+3V3`, `PVDD` (18.0 V), `VSYS`, `GND`, `USB_DP`, `USB_DN`, `I2C_SDA`, `I2C_SCL`, `CHG_INT`, `CHG_QON`, `BOOST_EN`, `PVDD_TRIM`. All other nets listed here are global labels unless marked *(local)*.
- RefDes ranges: `mcu` 1xx, `usb_uart` 2xx, `amp_left` 3xx, `amp_right` 4xx, `ui_io` 5xx. The power sheet must not use 100–599.
- **B** = JLC Basic, **E** = JLC Extended (checked against the JLC parts API on 2026-11-24). "Stock sym" means the symbol is in the KiCad 10.0.4 stock library.
- Default passive footprints: 0402 → `Resistor_SMD:R_0402_1005Metric` / `Capacitor_SMD:C_0402_1005Metric`; 0603 → `Capacitor_SMD:C_0603_1608Metric`; 0805 → `Capacitor_SMD:C_0805_2012Metric`; 1206 → `Capacitor_SMD:C_1206_3216Metric`. Symbols: `Device:R`, `Device:C`, `Device:C_Polarized`, `Device:L`, `Device:LED`.

**Changes vs. the brief.** Each is explained in its section.
1. **AMP_FAULT cannot be a plain shared open-drain line.** On the TAS5805M the FAULT output *is* the I2C-address strap pin (pin 3 `ADR/FAULT`). Tying the two pins together would put both address resistors in parallel, so both amps would decode the same address. The FAULTZ output is also a driven GPIO output, not open-drain. Instead, each amp keeps its own address resistor, and a 2× 2N7002 series "NAND" (high-impedance gates) merges the two FAULTZ signals into one ESP32 input. `AMP_FAULT` is therefore **active-HIGH** (§1.4).
2. **ENC_SW is on GPIO4, not GPIO36.** ESP32 erratum: GPIO36/39 inputs glitch low for about 80 ns whenever SAR ADC1 powers up, and the button ladder uses ADC1. GPIO36 instead carries `AMP_FAULT`, where a glitch is harmless.
3. **No spare GPIO.** All 22 usable GPIO plus GPIO0 are assigned. The status LED shares GPIO0 (the BOOT pin), and JTAG is unavailable (GPIO12–15 are used).
4. **UI cable:** JST-SH has no JLC stock, so the UI link uses a **1.0 mm 20-pin FFC** (JUSHUO AFA07-S20FCA-00, C262724, 7.8 k in stock, stock KiCad footprint).
5. **I2S mux:** footprint provided, **DNP by default**, with 0 Ω bypass links fitted. This saves an extended-part slot in v1.
6. The TAS5805M has **no GVDD pin**: the datasheet mentions one in §9.2, which is a copy error. The gate-drive regulator output is AVDD (pin 13).

---

## 0. Parts with no stock KiCad symbol or footprint

| Part | Resolution |
|---|---|
| ESP32-WROVER-E-N8R8 | Not in KiCad 10.0.4 stock libs. **Vendored Espressif's official symbol and footprint** (CC-BY-SA 4.0 with the KiCad design exception) to `hw/lib/Espressif/`. The symbol is `Espressif:ESP32-WROVER-E` in `hw/lib/Espressif/Espressif.kicad_sym`; the footprint is `Espressif:ESP32-WROVER-E` in `hw/lib/Espressif/Espressif.pretty/`. Add both to the project library tables with nickname `Espressif` and path `${KIPRJMOD}/../lib/Espressif/...`. Both load in kicad-cli 10.0.4. The pin table and footprint geometry are in §1.2 and §1.7, in case the files are lost. |
| SN74LVC157APWR | No 74LVC157 in stock. Use **`74xx:74LS157`**: the pinout is identical (checked pin by pin against the TI SCAS292 table). Set Value = `SN74LVC157APWR` and Footprint = `Package_SO:TSSOP-16_4.4x5mm_P0.65mm`. |

All other parts have stock symbols and footprints, listed per sheet.

---

## 1. Sheet `mcu`: ESP32-WROVER-E

### 1.1 Components

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol (stock?) | Function |
|---|---|---|---|---|---|---|---|
| U101 | ESP32-WROVER-E-N8R8 | `Espressif:ESP32-WROVER-E` (vendored) | 3.0–3.6 V | C2973667 | E | `Espressif:ESP32-WROVER-E` (vendored) | MCU |
| C101 | 22 µF | 0805 | 25 V X5R | C45783 | B | Device:C (yes) | 3V3 bulk at pin 2 (Espressif Fig. 11 C1) |
| C102 | 100 nF | 0402 | 16 V X7R | C1525 | B | Device:C | 3V3 HF at pin 2 (Fig. 11 C2) |
| R101 | 10 kΩ | 0402 | 1 % | C25744 | B | Device:R | EN pull-up |
| C103 | **2.2 µF** (ECO-001) | 0402 | 16 V X5R | C170151 | E | Device:C | EN delay (R101·C103 = 22 ms) |
| SW101 | RESET | `Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A` | 12 V 50 mA | C318884 | B | Switch:SW_Push | EN to GND |
| SW102 | BOOT | same as SW101 | | C318884 | B | Switch:SW_Push | IO0 to GND |
| R102 | 10 kΩ | 0402 | | C25744 | B | Device:R | IO0 pull-up |
| D101 | Red LED | `LED_SMD:LED_0603_1608Metric` | Vf 1.8–2.4 V | C2286 | B | Device:LED | Status LED (debug), on IO0 |
| R103 | 1 kΩ | 0402 | | C11702 | B | Device:R | LED current ≈ 1.2 mA |
| R104, R105 | 2.2 kΩ | 0402 | | C25879 | B | Device:R | I2C pull-ups (only ones on the bus) |
| R106 | 10 kΩ | 0402 | | C25744 | B | Device:R | CHG_INT pull-up |
| R107 | 100 kΩ | 0402 | | C25741 | B | Device:R | BOOST_EN pull-down (GPIO2 strap) |
| R108 | 100 kΩ | 0402 | | C25741 | B | Device:R | AMP_PDN pull-down (GPIO12 strap; amps off at boot) |
| R109 | 100 kΩ | 0402 | | C25741 | B | Device:R | AMP_FAULT pull-up |
| R110–R112, R115–R117 | 33 Ω | 0402 | | C25105 | B | Device:R | Source series resistors (see pin table) |
| R113, R114, R118 | **68 Ω** (ECO-001 #3) | 0402 | | C25131 | E | Device:R | SCLK / MOSI / PDM_CLK source series: damps the 0.7–1.1 V FFC overshoot seen with 33 Ω (sim S6) |
| C104 | 10 nF | 0402 | 50 V X7R | C15195 | B | Device:C | BTN_ADC anti-alias at the ESP32 pin |
| Q101, Q102 | 2N7002 | `Package_TO_SOT_SMD:SOT-23` | 60 V, 115 mA | C8545 | B | Transistor_FET:2N7002 (1 G, 2 S, 3 D) | AMP fault merge (NAND) |
| R119, R120 | 1 kΩ | 0402 | | C11702 | B | Device:R | FET gate series. Remove to isolate the ADR pins if address detection misbehaves |
| R121, R122 | 1 MΩ | 0402 | | C26083 | B | Device:R | Gate to GND (holds the gate off if R119/R120 are removed) |
| TP101–TP104 | test pad | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | EN, IO0, TXD0, RXD0 |
| TP105–TP109 | test pad (ECO-002 #5) | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | `I2C_SDA`, `I2C_SCL`, `AMP_PDN`, `BOOST_EN`, `AMP_FAULT` |
| TP110 | test pad, GND | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | GND within 5 mm of TP105–TP109 |

### 1.2 U101 pin-by-pin

The vendored symbol omits the NC pins (17–22, 27, 28, 32). Leave them unconnected: 17–22 are internal flash, and **27/28 = GPIO16/17 go to the PSRAM**.

| Pin | Name | Net | Notes |
|---|---|---|---|
| 1 | GND | `GND` | |
| 2 | 3V3 | `+3V3` | C101 + C102 within 3 mm |
| 3 | EN | `ESP_EN` | R101 to +3V3, C103 (2.2 µF) to GND, SW101 to GND, Q201 collector (usb_uart), TP101 |
| 4 | SENSOR_VP / GPIO36 | `AMP_FAULT` | Input-only. R109 100 k to +3V3. Driven by Q102 drain. TP109 |
| 5 | SENSOR_VN / GPIO39 | `BTN_ADC` | Input-only, ADC1_CH3. C104 10 nF to GND at the pin |
| 6 | IO34 | `ENC_A` | Input-only (pull-ups on the UI board) |
| 7 | IO35 | `ENC_B` | Input-only |
| 8 | IO32 | → R118 **68 Ω** → `PDM_CLK` | Every "pin → R → net" row: the short net between the module pin and the resistor is local, named `IOxx_R` (here `IO32_R`) |
| 9 | IO33 | `PDM_DATA` | |
| 10 | IO25 | `PVDD_TRIM` | DAC1 or LEDC PWM; high-Z at reset ⇒ PVDD = 18.0 V nominal |
| 11 | IO26 | → R110 33 Ω → `I2S_BCLK_MCU` | |
| 12 | IO27 | → R111 33 Ω → `I2S_LRCK_MCU` | |
| 13 | IO14 | → R117 33 Ω → `LCD_BL` | |
| 14 | IO12 (MTDI) | `AMP_PDN` | **Strap: must be LOW at reset** (3.3 V flash). R108 100 k to GND. TP107 |
| 15 | GND | `GND` | |
| 16 | IO13 | → R112 33 Ω → `I2S_DOUT_MCU` | |
| 17–22 | NC | — | no-connect |
| 23 | IO15 (MTDO) | → R116 33 Ω → `LCD_DC` | Strap (U0TXD boot log); internal pull-up, leave |
| 24 | IO2 | `BOOST_EN` | Strap: must be low or floating for download mode. R107 100 k to GND. TP108 |
| 25 | IO0 | `ESP_IO0` | Strap (boot). R102 10 k to +3V3, SW102 to GND, Q202 collector, LED D101 + R103, TP102 |
| 26 | IO4 | `ENC_SW` | RTC_GPIO10: ext0 wake source |
| 27 | NC (GPIO16, PSRAM) | — | **do not connect** |
| 28 | NC (GPIO17, PSRAM) | — | **do not connect** |
| 29 | IO5 | → R115 33 Ω → `LCD_CS` | Strap (SDIO timing only); internal pull-up keeps CS high at boot |
| 30 | IO18 | → R113 **68 Ω** → `LCD_SCLK` | VSPICLK (IO_MUX, good to 80 MHz) |
| 31 | IO19 | `CHG_INT` | R106 10 k to +3V3 |
| 32 | NC | — | |
| 33 | IO21 | `I2C_SDA` | R104 2.2 k to +3V3. TP105 |
| 34 | RXD0 (GPIO3) | `ESP_RXD0` | From usb_uart R203. TP104 |
| 35 | TXD0 (GPIO1) | `ESP_TXD0` | To usb_uart R204. TP103 |
| 36 | IO22 | `I2C_SCL` | R105 2.2 k to +3V3. TP106 |
| 37 | IO23 | → R114 **68 Ω** → `LCD_MOSI` | VSPID (IO_MUX) |
| 38 | GND | `GND` | |
| 39 | GND (EPAD, 9 pads) | `GND` | Solder it; via-stitch to GND |

**Status LED:** D101 anode → `+3V3`; D101 cathode → R103 → `ESP_IO0`. The LED lights when IO0 is low, which happens in three cases: firmware drives it low, BOOT is pressed, or esptool enters download mode. Firmware must drive GPIO0 in **open-drain mode** (only low or Hi-Z), so that pressing BOOT can never short a high output. With IO0 high-Z, the LED and R102 both pull toward +3V3, so the boot strap reads 1.

### 1.3 GPIO map (for firmware)

| GPIO | Module pin | Signal | Dir | Peripheral | Strap / ADC2 / errata notes |
|---|---|---|---|---|---|
| 0 | 25 | BOOT button / STATUS_LED (active-low) | I/O (open-drain) | GPIO | Strap (1 = SPI boot). ADC2 (unused) |
| 1 | 35 | U0TXD → CH340C RXD | O | UART0 | Boot log |
| 2 | 24 | BOOST_EN (1 = boost on) | O | GPIO | Strap (must be 0/floating with IO0 = 0). 100 k PD on board |
| 3 | 34 | U0RXD ← CH340C TXD | I | UART0 | |
| 4 | 26 | ENC_SW (0 = pressed) | I | GPIO / RTC ext0 wake | Internal pull-down active after reset: disable it in firmware (external 10 k pull-up on UI board) |
| 5 | 29 | LCD_CS | O | VSPI CS0 (IO_MUX) | Strap (SDIO timing, irrelevant). High at boot |
| 12 | 14 | AMP_PDN (1 = amps enabled) | O | GPIO | **Strap MTDI: must be 0 at reset** (100 k PD). Recommend also burning `espefuse.py set_flash_voltage 3.3V` in production |
| 13 | 16 | I2S_DOUT (amps SDIN) | O | I2S1 DOUT | JTAG TCK lost |
| 14 | 13 | LCD_BL (PWM, 1 = on) | O | LEDC | Emits a short PWM burst during ROM boot (backlight flicker) |
| 15 | 23 | LCD_DC | O | GPIO | Strap MTDO (boot-log enable), internal PU |
| 18 | 30 | LCD_SCLK | O | VSPI CLK (IO_MUX) | Up to 40 MHz over the FFC (sim f_max ≈ 53 MHz with 68 Ω) |
| 19 | 31 | CHG_INT (active-low pulse, BQ2579x) | I | GPIO (falling-edge IRQ) | 10 k PU |
| 21 | 33 | I2C_SDA | I/O OD | I2C0 | **100 kHz at bring-up (≤ 200 kHz)** until t_r is scoped (ECO-002 #8). External 2.2 k |
| 22 | 36 | I2C_SCL | O OD | I2C0 | |
| 23 | 37 | LCD_MOSI | O | VSPI D (IO_MUX) | |
| 25 | 10 | PVDD_TRIM | O (analog) | DAC1 (8-bit) or LEDC PWM | Hi-Z at reset ⇒ PVDD = 18.0 V nominal |
| 26 | 11 | I2S_BCLK (amps SCLK) | O | I2S1 BCK | 64·fs |
| 27 | 12 | I2S_LRCK (amps LRCLK) | O | I2S1 WS | |
| 32 | 8 | PDM_CLK (mic) | O | I2S0 WS (PDM RX clock) | PDM RX exists only on I2S0 |
| 33 | 9 | PDM_DATA (mic) | I | I2S0 DIN | |
| 34 | 6 | ENC_A | I | PCNT | Input-only, no internal pulls |
| 35 | 7 | ENC_B | I | PCNT | Input-only |
| 36 | 4 | AMP_FAULT (**1 = fault** in either amp) | I | GPIO (rising-edge IRQ) | Input-only. Erratum 3.11 80 ns low glitch when ADC1 starts: harmless here, but confirm via I2C reg 0x70–0x72 |
| 39 | 5 | BTN_ADC | I (analog) | ADC1_CH3, 12 dB atten | ADC1 works with Wi-Fi on (ADC2 does not) |
| 6–11 | — | flash | — | — | Not brought out |
| 16, 17 | 27, 28 | PSRAM | — | — | **Never use** |

Spare GPIO: **none**. JTAG is not available; debug over UART0 or USB-serial.

Firmware notes:
- I2S1 runs as std Philips master TX, 32-bit slots, stereo (BCLK = 64·fs: 2.8224 MHz at 44.1 kHz, 3.072 MHz at 48 kHz). The TAS5805M accepts 32·fs or 64·fs with fs = 32–96 kHz, and SCLK ≤ 24.576 MHz (datasheet §6.5, Table 7-1).
- PDM RX on I2S0: PDM clock = 64·fs → 3.072 MHz at fs = 48 kHz, inside the mic's 2.0–3.3 MHz High-Quality-mode range. For an ambient-level-only mode, fs = 8–12 kHz gives 512–768 kHz, which falls in the mic's Low-Power mode (400–800 kHz). Check the IDF `dn_sample_mode` setting so that clk = 64·fs.

### 1.4 Amplifier fault merge (on the `mcu` sheet)

`AMPL_FAULT_N` and `AMPR_FAULT_N` are the ADR/FAULT pins (pin 3) of U301 and U401. Each has its own address resistor to +3V3 on the amp sheet.

| Part | Pin | Net |
|---|---|---|
| R119 | 1 / 2 | `AMPL_FAULT_N` / `Q101_G` *(local)* |
| R121 | 1 / 2 | `Q101_G` / `GND` |
| Q101 | 1 G / 2 S / 3 D | `Q101_G` / `GND` / `FAULT_MID` *(local)* |
| R120 | 1 / 2 | `AMPR_FAULT_N` / `Q102_G` *(local)* |
| R122 | 1 / 2 | `Q102_G` / `GND` |
| Q102 | 1 G / 2 S / 3 D | `Q102_G` / `FAULT_MID` / `AMP_FAULT` |
| R109 | 1 / 2 | `AMP_FAULT` / `+3V3` |

How it works:
- **Both amps OK.** Both FAULTZ pins are high, so both FETs conduct and `AMP_FAULT` = 0.
- **Either amp faults.** That amp's FAULTZ goes low, the series path opens, and R109 pulls `AMP_FAULT` = 1.
- **Shutdown (PDN low).** The ADR pins sit at +3V3 through their address resistors, so `AMP_FAULT` = 0. The standby draw is 3.3 V / 100 kΩ = 33 µA.

Why gates: the 2N7002 gate leakage (≤100 nA, ×4.7 kΩ ≈ 0.5 mV) and the 1 MΩ to GND (it moves the effective 15 kΩ strap to 14.8 kΩ, which is a 1.5 % change against strap values spaced 3× apart) leave the address detection intact. The gate capacitance (≈25–50 pF) is charged long before PDN rises. **Bench check:** both amps must ACK at 0x2C and 0x2D. If not, remove R119/R120 and fall back to polling fault registers over I2C.

Firmware: after init, configure the pin as FAULTZ with reg 0x61 = 0x0B and then 0x60 = 0x01 (datasheet Table 5-1, pin 3). Before this, `AMP_FAULT` is meaningless, so ignore it until both amps are configured.

### 1.5 Calculations

- **EN delay:** τ = 10 kΩ × 2.2 µF = **22 ms** (ECO-001 #4). This exceeds Espressif's t_STBL ≥ 50 µs (WROVER-E datasheet Table 9) with large margin. It also keeps EN low until +3V3 is valid at power-up. With 1 µF, the esptool auto-reset failed in sim S5 if the DTR/RTS gap exceeded about 2.5 ms.
- **I2C pull-ups (2.2 kΩ):** sink current = 3.3 V / 2.2 kΩ = 1.5 mA, under the 3 mA limit. The TAS5805M allows 400 pF per line (§6.5).
  - **Bus capacitance is the open item (review S5).** The v1.1 estimate was about 100 pF, which gives t_r = 0.8473 × 2.2 kΩ × 100 pF = 186 ns.
  - Each line also carries one AO3400A drain from the CH224Q isolator (Q601/Q602, power sheet). Its Coss at 0–3.3 V is about 150–250 pF (estimate), giving C ≈ 130–225 pF and **t_r ≈ 240–420 ns**. That may exceed the 300 ns Fast-mode limit.
  - **Run I2C at 100 kHz (Standard mode, t_r ≤ 1000 ns ✓) or at most 200 kHz until t_r is scoped with VBUS both present and absent** (ECO-002 #8). Go to 400 kHz only if the scoped t_r ≤ 300 ns.
  - Bus time is not critical: one TAS biquad is ≈ 2.4 ms at 100 kHz versus 0.6 ms at 400 kHz, so a full DSP load takes a few hundred ms longer.
- **Strap levels:** the ESP32 has V_IL ≤ 0.25·VDD = 0.825 V and V_IH ≥ 0.75·VDD = 2.475 V, with internal pull-ups and pull-downs of about 45 kΩ (ESP32 datasheet DC table).
  - GPIO12 with 100 k external plus the internal pull-down reads 0 ✓.
  - GPIO2 with 100 k PD reads 0 ✓.
  - GPIO0 with 10 k PU reads 1 ✓.
- **LED:** (3.3 − 2.0) V / 1 kΩ ≈ 1.3 mA, well inside the GPIO0 sink rating of 28 mA.

### 1.6 Layout notes (MCU)

- **Antenna:** place U101 at the board edge with the antenna end (the pin 1/38 end, the 18 × 6.22 mm "Antenna Area") overhanging the board edge or flush with it.
  - Keep copper off **all layers** under the antenna area. The footprint's keep-out polygon covers only the module outline, so add a board-level keep-out of ≥ 15 mm around the antenna in the plane of the board (Espressif HW design guidelines, "Positioning a module on a base board").
  - No PVDD, inductors, boost or speaker leads near it, and no metal grille directly over it. If the enclosure forces metal over the antenna, swap to WROVER-IE-N8R8 (C701351, same footprint, U.FL).
- C101 and C102 go at pin 2, with GND vias next to them.
- Stitch the EPAD (pin 39, a 3×3 array of 0.9 mm pads) to the GND plane.
- Keep the I2S traces (IO26/27/13) and the SPI traces (IO18/23/5) away from the module's crystal and RF side.

### 1.7 WROVER-E footprint geometry (backup if the vendored file is lost)

Source: WROVER-E datasheet v2.4 Fig. 15, matching Espressif's `ESP32-WROVER-E.kicad_mod`. Origin at the module centre; +y points away from the antenna.
- **Module outline:** 18.00 × 31.40 mm, x = ±9.0, y = −15.695 … +15.705.
- **Pads 1–19:** x = −8.75, rectangular 1.5 (x) × 0.9 (y) mm, pitch 1.27 mm. Pad 1 at y = −8.255; pad n at y = −8.255 + (n−1)·1.27; pad 19 at +14.605.
- **Pads 20–38:** x = +8.75, same size. Pad 20 at y = +14.605, counting up the side to pad 38 at y = −8.255.
- Pads protrude 0.5 mm beyond the module edge.
- **Pad 39 (GND EPAD):** a 3×3 array of 0.9 × 0.9 mm pads at x ∈ {−2.9, −1.5, −0.1} and y ∈ {−1.86, −0.46, +0.94} (0.5 mm gaps, 3.7 × 3.7 mm overall). Its centre is 7.5 mm from the pin-1 edge and 16.16 mm from the far edge.
- **Antenna keep-out:** x = −9 … +9, y = −15.695 … −9.395 (6.3 mm deep), all copper layers.

---

## 2. Sheet `usb_uart`: CH340C + auto-reset

### 2.1 Components

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol (stock?) |
|---|---|---|---|---|---|---|
| U201 | CH340C | `Package_SO:SOIC-16_3.9x9.9mm_P1.27mm` | 3.3 V supply | **C7464026** (ECO-002 #4; C84681 is "no longer manufactured" at JLC) | E | Interface_USB:CH340C (yes) |
| C201 | 100 nF | 0402 | 16 V | C1525 | B | Device:C |
| R201, R202 | 10 kΩ | 0402 | | C25744 | B | Device:R |
| Q201, Q202 | MMBT3904 | `Package_TO_SOT_SMD:SOT-23` | 40 V 200 mA | C20526 | B | Transistor_BJT:MMBT3904 (1 B, 2 E, 3 C) |
| R203, R204 | 470 Ω | 0402 | | C25117 | B | Device:R |

**Crystal:** not needed. The WCH CH340 datasheet V3D §3 note and §5.1 say "CH340C/N/K/E/X/B have a built-in clock, no external crystal". Pin 7 (XI on CH340G) is an empty pin on the CH340C and must be left floating.

### 2.2 U201 pin-by-pin

| Pin | Name | Net | Notes |
|---|---|---|---|
| 1 | GND | `GND` | |
| 2 | TXD | `CH_TXD` *(local)* → R203 → `ESP_RXD0` | |
| 3 | RXD | `CH_RXD` *(local)* ← R204 ← `ESP_TXD0` | Internal pull |
| 4 | V3 | `+3V3` | At 3.3 V supply, V3 ties to VCC (WCH §4, §5.1) |
| 5 | UD+ | `USB_DP` | **No series resistor** (WCH: "connect directly") |
| 6 | UD− | `USB_DN` | No series resistor |
| 7 | NC | — | Must float |
| 8 | OUT# | — | NC |
| 9 | CTS# | — | NC (WCH: unused pins may dangle) |
| 10 | DSR# | — | NC |
| 11 | RI# | — | NC |
| 12 | DCD# | — | NC |
| 13 | DTR# | `DTR_N` *(local)* | |
| 14 | RTS# | `RTS_N` *(local)* | |
| 15 | R232 | `GND` | Has an internal pull-down; tied low for robustness |
| 16 | VCC | `+3V3` | C201 within 2 mm |

### 2.3 Auto-reset (Espressif DevKitC topology)

| Part | Pin | Net |
|---|---|---|
| R201 | 1 / 2 | `DTR_N` / `Q201_B` |
| Q201 | 1 B / 2 E / 3 C | `Q201_B` / `RTS_N` / `ESP_EN` |
| R202 | 1 / 2 | `RTS_N` / `Q202_B` |
| Q202 | 1 B / 2 E / 3 C | `Q202_B` / `DTR_N` / `ESP_IO0` |

| DTR# | RTS# | Q201 | Q202 | EN | IO0 |
|---|---|---|---|---|---|
| 1 | 1 | off | off | high (R101) | high |
| 0 | 0 | off | off | high | high |
| 1 | 0 | **on** | off | **low (reset)** | high |
| 0 | 1 | off | **on** | high | **low (boot)** |

esptool steps (1,0) → (0,1), so EN rises while IO0 is held low, which enters download mode. Q201 must discharge C103 (2.2 µF). Base drive is (3.3 − 0.7) V / 10 kΩ ≈ 0.26 mA; with β ≥ 100 the collector sinks ≥ 20 mA, so EN falls through 0.6 V in about 0.3 ms, well inside esptool's 100 ms pulse. Sim S5 verified the full auto-reset with 2.2 µF.

### 2.4 UART crossover

ESP32 U0TXD (pin 35, `ESP_TXD0`) → R204 → CH340C RXD (pin 3). CH340C TXD (pin 2) → R203 → ESP32 U0RXD (pin 34, `ESP_RXD0`). The 470 Ω resistors limit the current if either side is unpowered or misconfigured, and damp the edges; that is under 0.1 % of a bit time at 2 Mbit/s with about 20 pF.

### 2.5 Back-powering

- CH340C, ESP32 and the TAS5805M DVDDs all run from the same `+3V3`, so no UART or strap pin can back-power one IC from another.
- The CH340C's internal D+ pull-up runs from V3 (+3V3) and cannot feed VBUS. The host does not drive D+/D− until a device pull-up appears.
- `+3V3` is up whenever VBUS is present (VBUS → charger → VSYS → buck), so the case "USB connected but 3V3 off" does not occur. **Residual risk:** if the power sheet ever gates the 3V3 buck off while VBUS is present, a host could see a dead device. That is harmless, but the CH340C draws ≈ 50 µA in suspend; it is accepted, not mitigated.
- The CH340C idles with TXD high, so it holds U0RXD high when no host is connected. Its DTR#/RTS# idle high, so both transistors are off.

### 2.6 Layout

- Route USB_DP/USB_DN as a 90 Ω differential pair from the USB-C ESD device (power sheet) to U201, under 50 mm, over unbroken GND.
- Place C201 at pin 16.
- Put Q201 and Q202 near U101 pins 3 and 25 rather than near U201, which keeps the EN/IO0 stubs short.

---

## 3. Sheets `amp_left` and `amp_right`: TAS5805MPWPR, BTL, ch A = woofer, ch B = tweeter

Draw **two separate sheet files** (`amp_left.kicad_sch`, `amp_right.kicad_sch`) rather than one sheet instanced twice, because the ADR resistor value and the output net names differ. The right sheet is identical except: RefDes 4xx, net prefix `AR_` instead of `AL_`, **R401 = 15 kΩ** (I2C 0x2D), fault net `AMPR_FAULT_N`, and speaker nets `SPK_WR_*` / `SPK_TR_*`.

### 3.1 Operating point and filter choice

Loads (brief revision 2): **ch A = woofer, Dayton ND65-8, 8 Ω (Re 7.40 Ω, 15 W rms)**; **ch B = tweeter, Peerless OT19NC00-04, 4 Ω (Re 3.17 Ω)**, gain-limited in the DSP. **PVDD = 18.0 V.**

- **Fsw = 768 kHz** (FSW_SEL = 000, the reset default, reg 0x02 bits 6:4). Modulation: **Hybrid** (DAMP_MOD = 10) for low idle current, or BD if THD is preferred.
- **Required inductance** (datasheet Table 8-2): PVDD > 12 V at 384 kHz needs 10 µH (BD) or 15 µH (1SPW/Hybrid). Scaled to 768 kHz (L_min × 384/768): 5 µH (BD) and **7.5 µH (Hybrid)**. Choose **10 µH**, which covers every modulation, and still meets the ≥ 80 % rule (≥ 7.5 µH at peak current) with up to 25 % saturation droop.
  - The alternative, Hybrid at 384 kHz, would need 15 µH. In the 7 mm molded size that means Isat ≈ 4 A, below the clipped-tweeter current. Rejected.
- **Filter capacitor: 1.0 µF X7R 50 V 0805 per leg (C28323, Basic)** on all four legs (one part type). Bias is about 9 V DC per leg, so roughly 0.75 µF effective.
- **Start-up peak, Eq. (1):** I ≈ PVDD·√(C/L)·sin(θ / (Fsw·√(LC))). This is load-independent, so it is the same for 4 Ω and 8 Ω.
  - Check of the formula against Table 8-1: 24 V / 4.7 µH / 0.68 µF / 384 kHz / θ = 0.5 gives 24 × 0.380 × sin(0.728) = 6.07 A, matching TI's 6.07 A.
  - Ours, 18 V, 10 µH, 1 µF, 768 kHz: √(C/L) = 0.316; ω₀ = 1/√(LC) = 316 krad/s.
  - BD (θ = 0.5): sin(0.206) = 0.204, so **I = 1.16 A**. Hybrid (θ = 0.14): sin(0.0576), so **0.33 A**. With C derated to 0.75 µF: 1.16 A. **Far below the 5 A OCP on both channels.**
  - For reference, the "4.7 µH + 0.68 µF at 384 kHz" combination would give 4.55 A at 18 V. Don't use it.
- **Clipping transient, Eq. (2):** I ≈ PVDD·(1−θ)/(Fsw·L) = 18 × 0.5 / (768 k × 10 µ) = 1.17 A (BD), or 2.02 A (θ = 0.14).
- **Ripple:** 18 × 0.25 / (768 k × 10 µ) = 0.59 A p-p in BD, ±0.29 A on top of the load current.
- **Load current at hard clipping.** RDS(on) is 180 mΩ per FET, two per BTL path (§6.5); DCR is 68 mΩ × 2; total series ≈ 0.50 Ω.
  - Woofer (ND65-8, Re 7.40 Ω): 18 / (7.40 + 0.50) = **2.28 A peak**, +0.29 ripple = 2.6 A. Large margin to the 5 A OCE.
  - The clipped woofer delivers V_pk ≈ 18 × 7.40 / 7.90 = 16.9 V, which is ≈ 17.8 W into 8 Ω and above the ND65-8's 15 W rating. **Woofer DRC/AGL at ≤ 15.5 V peak** (15 W into 8 Ω).
  - Tweeter (OT19NC00-04, Re 3.17 Ω): 18 / 3.67 = **4.91 A peak**, +0.29 ripple = **5.2 A, above OCETHRES (5 A)**. A hard-clipped full-scale tweeter signal *would* trip OCP: the cycle-by-cycle current limit acts first, and OCSD shuts down on a severe event (§7.5.3.3.1).
  - **Mandatory: tweeter limiter at ≤ 8 V peak after the crossover** (8 / 3.67 = 2.2 A, +0.3 A ripple = 2.5 A), and channel-B digital volume capped so 0 dBFS never reaches the rail.
  - The datasheet's 6 Ω minimum BTL load (§6.3) is footnoted "lower load supported if output peak current < 5 A"; the limiter guarantees that.
  - The start-up and idle currents (≤ 1.16 A) are well inside OCP regardless of the limiter.
- **Inductor requirements:** Isat ≥ the OCP threshold (5 A), so the inductor cannot saturate before the amp's own protection acts. Irms ≥ 1.5 A (woofer at 17.8 W: √(17.8/8) = 1.49 A rms; limited tweeter < 1.6 A rms).
  - **FXL0630-100-M: 10 µH, Isat 5.5 A, Irms 4.5 A, 68 mΩ ✓.**
  - Alternatives: Sunlord MWSA0603S-100MT (C132141), same size and specs; FXL0640-100-M (C5359185), 6 A Isat, which uses footprint `L_Changjiang_FXL0640`.
- **Filter response, BTL with caps to GND:** the differential equivalent is L_d = 2L = 20 µH and C_d = C/2 = 0.5 µF, so f₀ = 1/(2π√(L_d·C_d)) = **50.3 kHz**, and Q = R·√(C_d/L_d) = R × 0.158.
  - **Ch B, 4 Ω tweeter:** Q = 0.63, |H(20 kHz)| = −0.44 dB with a resistive 4 Ω and nominal C.
  - SPICE sim S2 (real tweeter impedance, DC-bias-derated C) gives **−2.2 dB at 20 kHz**. Firmware therefore adds a **+≈2 dB high shelf on ch B** (corner ≈ 10–12 kHz) in the tweeter EQ (ECO-001 #5).
  - **Ch A, 8 Ω woofer:** Q = 1.26, about +2.5 dB peaking near 45 kHz and +0.9 dB at 20 kHz. Both are irrelevant because ch A is low-passed at about 2.5 kHz, where |H| deviates < 0.03 dB.
  - The same 1 µF is used on ch A for one part type; 0.68 µF on ch A would give Q = 1.04 and changes nothing audible.
- **Inductor loss:** woofer at 15 W: 1.37 A rms² × 68 mΩ = 0.13 W per inductor.
- **Snubbers:** none. TI's inductor-filter BOM (Table 8-4) has none; the 68 Ω / 2.2 nF RC is only for the ferrite-bead variant (Table 8-3).
- **Analog gain (firmware):** AGAIN reg 0x54 sets full scale as 29.5 V × 10^(−n·0.5/20). Use **n = 8 (−4.0 dB → 18.6 Vp/FS)**, so 0 dBFS ≈ PVDD. TI's 18 V characterization used 20.8–22.1 Vp/FS.
- **Voltage ratings at 18 V (every PVDD- or output-connected part):**
  - PVDD 10 µF and 100 nF ceramics: 50 V ✓.
  - Bulk 470 µF: changed from 25 V (C2895277) to **35 V (C2836436)**, same 10×10.2 can, 58 k in stock.
  - Output filter caps (C316–C319, which swing 0…PVDD): 50 V ✓.
  - Bootstrap caps C312–C315 (C21120, 220 nF 25 V): they float on OUT_x and see only AVDD ≈ 5 V across them, so 25 V is ample (TI's BOM uses 50 V).
  - The TAS5805M absolute maximum is 30 V (26.4 V recommended), so boost OVP must stay ≤ 26 V (power sheet).

### 3.2 Components (amp_left; amp_right = 4xx)

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol (stock?) | Function / TI ref (Fig. 8-2, Table 8-4) |
|---|---|---|---|---|---|---|---|
| U301 | TAS5805MPWPR | `Package_SO:TSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.7mm_Mask3.1x4.05mm_ThermalVias` | PVDD 4.5–26.4 V | C478472 | E | Amplifier_Audio:TAS5805MPWP (yes; this is its default FP, matching the TI PWP0028M land pattern) | |
| C301 | 470 µF | `Capacitor_SMD:CP_Elec_10x10` | **35 V** Al, 10×10.2 (KNSCHA RVT470UF35V67RV0056) | C2836436 | E (asked power-spec to use the same part for its bulk) | Device:C_Polarized | PVDD bulk (TI: C1/C6 390 µF ×2; one 470 µF per amp here, since the boost output is close and adds its own bulk) |
| C302, C303 | 10 µF | 1206 | 50 V X5R | C13585 | B | Device:C | PVDD, pins 15/16 (TI C2: 22 µF/35 V) |
| C304 | 100 nF | 0402 | 50 V X7R | C307331 | B | Device:C | PVDD HF, pins 15/16 (TI C3) |
| C305, C306 | 10 µF | 1206 | 50 V X5R | C13585 | B | Device:C | PVDD, pins 27/28 (TI C5) |
| C307 | 100 nF | 0402 | 50 V X7R | C307331 | B | Device:C | PVDD HF, pins 27/28 (TI C4) |
| C308 | 4.7 µF | 0603 | 16 V X5R | C19666 | B | Device:C | DVDD (TI C7) |
| C309 | 100 nF | 0402 | 16 V X7R | C1525 | B | Device:C | DVDD (TI C8) |
| C310 | 1 µF | 0603 | 50 V X5R | C15849 | B | Device:C | AVDD (TI C9) |
| C311 | 1 µF | 0603 | 50 V X5R | C15849 | B | Device:C | VR_DIG (TI C10) |
| C312–C315 | 220 nF | 0603 | 25 V X7R | C21120 | B | Device:C | Bootstrap (TI C11–C14 = 0.22 µF; sees only about 5 V) |
| L301–L304 | 10 µH | `Inductor_SMD:L_Changjiang_FXL0630` | Isat 5.5 A, Irms 4.5 A, 68 mΩ | C167223 | E | Device:L | Output LC (§3.1) |
| C316–C319 | 1 µF | 0805 | 50 V X7R | C28323 | B | Device:C | Output LC, leg to GND |
| R301 | **4.7 kΩ** (R401 = **15 kΩ**) | 0402 | 1 % | C25900 (R401: C25756) | B | Device:R | ADR strap to DVDD → 0x2C (left) / 0x2D (right) (Table 7-5) |
| J301 | Woofer L (ND65-8, 8 Ω) | `Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical` | 10 A, 250 V | C160315 (B2P-VH(LF)(SN)) | E | Connector_Generic:Conn_01x02 | Mates with VHR-2N + SVH-21T-P1.1 |
| J302 | Tweeter L (OT19NC00-04, 4 Ω) | same | 10 A | C160315 | E | Connector_Generic:Conn_01x02 | |
| TP301–TP303 | test pads (ECO-002 #5), **amp_left only** | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | `I2S_BCLK`, `I2S_LRCK`, `I2S_SDIN` at U301 pins 7/6/8 |
| TP304 | test pad, `PVDD` (amp_left) | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | Within 5 mm of C304/C307 |
| TP305 | test pad, `GND` (amp_left) | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | Within 5 mm of TP301–TP304 |
| TP401 | test pad, `PVDD` (**amp_right**; the only TP on that sheet) | `TestPoint:TestPoint_Pad_D1.0mm` | | — | — | Connector:TestPoint | Within 5 mm of C404/C407. Ground the probe on TP305 or a via |

ADR values (datasheet Table 7-5, resistor to DVDD): 4.7 kΩ → 0x2C, 15 kΩ → 0x2D, 47 kΩ → 0x2E, 120 kΩ → 0x2F (7-bit addresses).

### 3.3 U301 pin-by-pin (TAS5805M datasheet Table 5-1)

| Pin | Name | Net (left) | Connected parts |
|---|---|---|---|
| 1 | DGND | `GND` | |
| 2 | DVDD | `+3V3` | C308 4.7 µF + C309 100 nF to GND |
| 3 | ADR/FAULT | `AMPL_FAULT_N` | R301 4.7 k to +3V3. Goes to the mcu sheet (R119). Right: `AMPR_FAULT_N`, R401 15 k |
| 4 | VR_DIG | `AL_VRDIG` *(local)* | C311 1 µF to GND. Nothing else (1.5 V internal regulator) |
| 5 | DGND | `GND` | |
| 6 | LRCLK | `I2S_LRCK` | |
| 7 | SCLK | `I2S_BCLK` | |
| 8 | SDIN | `I2S_SDIN` | |
| 9 | SDOUT | — | NC (no-connect flag) |
| 10 | SDA | `I2C_SDA` | |
| 11 | SCL | `I2C_SCL` | |
| 12 | PDN | `AMP_PDN` | Shared by both amps; pull-down R108 is on the mcu sheet |
| 13 | AVDD | `AL_AVDD` *(local)* | C310 1 µF to GND. Nothing else (5 V internal gate-drive regulator) |
| 14 | AGND | `GND` | |
| 15 | PVDD | `PVDD` | C302, C303, C304 at pins 15/16 |
| 16 | PVDD | `PVDD` | |
| 17 | OUT_B+ | `AL_OUTB_P` | C314 (to pin 18), L303 |
| 18 | BST_B+ | `AL_BSTB_P` | C314 220 nF to `AL_OUTB_P` |
| 19 | PGND | `GND` | |
| 20 | OUT_B− | `AL_OUTB_N` | C315, L304 |
| 21 | BST_B− | `AL_BSTB_N` | C315 220 nF to `AL_OUTB_N` |
| 22 | BST_A− | `AL_BSTA_N` | C313 220 nF to `AL_OUTA_N` |
| 23 | OUT_A− | `AL_OUTA_N` | C313, L302 |
| 24 | PGND | `GND` | |
| 25 | BST_A+ | `AL_BSTA_P` | C312 220 nF to `AL_OUTA_P` |
| 26 | OUT_A+ | `AL_OUTA_P` | C312, L301 |
| 27 | PVDD | `PVDD` | C305, C306, C307 at pins 27/28 |
| 28 | PVDD | `PVDD` | |
| 29 | EP (PowerPAD) | `GND` | Thermal pad to GND |

C301 (470 µF): + to `PVDD`, − to `GND`, placed between the two PVDD pin groups.

### 3.4 Output filter and connectors (left; right uses AR_/SPK_WR/SPK_TR)

| Part | Pin 1 | Pin 2 |
|---|---|---|
| L301 | `AL_OUTA_P` | `SPK_WL_P` |
| L302 | `AL_OUTA_N` | `SPK_WL_N` |
| L303 | `AL_OUTB_P` | `SPK_TL_P` |
| L304 | `AL_OUTB_N` | `SPK_TL_N` |
| C316 | `SPK_WL_P` | `GND` |
| C317 | `SPK_WL_N` | `GND` |
| C318 | `SPK_TL_P` | `GND` |
| C319 | `SPK_TL_N` | `GND` |
| J301 (woofer) | `SPK_WL_P` (+, red) | `SPK_WL_N` (−) |
| J302 (tweeter) | `SPK_TL_P` (+) | `SPK_TL_N` (−) |

Amp right: J401 = woofer R (`SPK_WR_P/N`), J402 = tweeter R (`SPK_TR_P/N`).

**Never tie either speaker terminal to GND.** Both outputs are BTL and float about PVDD/2.

### 3.5 Power-up / power-down sequence (datasheet §7.5.3.1)

1. `+3V3` comes up (DVDD). `AMP_PDN` = 0 (R108) and `BOOST_EN` = 0 (R107) during ESP32 boot.
   - **PVDD is not 0 V while the boost is off.** The power sheet has no load-disconnect FET, so with BOOST_EN low PVDD ≈ VSYS − 0.5 V (5.5–8 V) whenever the battery is connected.
   - This is fine for the TAS5805M: PVDD is within the 4.5–26.4 V operating range. Shutdown draws 7.2 µA from PVDD (specified at 13.5 V) and 5.5 µA from DVDD (§6.5), so ≈ 30 µA for both amps.
   - Supply order is unconstrained (§7.5.3.1 step 2: "it does not matter if PVDD or DVDD comes up first").
2. **PVDD soft start** (spec_power v1.2 §4.1.4, R907/D901 fitted per ECO-001):
   1. Drive `PVDD_TRIM` (GPIO25) to 3.3 V (DAC 255 or 100 % duty) **≥ 150 ms before** BOOST_EN, so the trim RC is charged.
   2. Set `BOOST_EN` = 1. PVDD rises only to ≈ 12.2 V, which keeps the boost out of current limit, so its error amplifier does not wind up.
   - **Why:** without the soft start, SPICE sim S1 shows an **11 ms** current-limited ramp (6 V input, minimum ILIM). The error amplifier then winds up and PVDD overshoots to 19.4 V typical (≈ 21 V OVP worst case) and stays there until the amps load it. That is harmless to the parts but avoidable.
   - Releasing PDN at the pre-biased 6–8 V would work electrically (above UVLO 4.2 V), but don't: the gain and limiter settings assume 18 V.
3. Wait **≥ 20 ms** after BOOST_EN (covers the 11 ms worst-case ramp), then set `AMP_PDN` = 1 and wait **≥ 5 ms**. The ADR straps are latched now, so both amps must answer at 0x2C and 0x2D.
   - Then ramp `PVDD_TRIM` down to the target (0 V or Hi-Z for 18.0 V) over **≥ 30–50 ms**.
   - PVDD settles ≥ 150 ms after the last trim step (70–110 ms in sim). Steps 4–6 can run meanwhile, with the amps in Hi-Z.
   - **Do not enter Play (step 7) until PVDD has settled.** Every later trim change also needs ≥ 150 ms, with the amps muted or with the DRC thresholds re-scaled.
4. Start I2S1 BCLK/LRCK (data = 0).
5. Over I2C, for each amp: book 0 / page 0 (reg 0x00 = 0, reg 0x7F = 0); reg 0x03 = 0x02 (Hi-Z, DSP out of reset; DIS_DSP = 0); wait ≥ 5 ms.
6. Load the DSP coefficients (crossover, EQ, DRC). Set reg 0x02 = 0x02 (768 kHz, BTL, Hybrid) and AGAIN reg 0x54 = 0x08. Set 0x61 = 0x0B, 0x60 = 0x01 (FAULTZ output).
7. Once PVDD has settled (≥ 150 ms after the last trim step): reg 0x03 = 0x03 (Play). Unmute with a volume ramp.

Power down: reg 0x03 = 0x0B (mute + Hi-Z), wait 10 ms, 0x03 = 0x00 (deep sleep). Then stop the I2S clocks, set `AMP_PDN` = 0, and only after that set `BOOST_EN` = 0 (PDN always goes low before the boost turns off).

The I2S clocks must be stable before the DSP is enabled (§7.3.3). On a sample-rate change, mute → Hi-Z → change the clocks → Play. Clock-halt auto-recovery (§7.3.4) covers glitches.

### 3.6 Layout notes (amps)

- **PVDD decoupling.** The 100 nF caps (C304/C307) go on the same layer as the IC, ≤ 1 mm from pins 15/16 and 27/28, with their GND via at the cap pad. The 10 µF parts go within 3 mm. TI §9.1.2 warns that distant PVDD caps cause output ringing beyond the absolute-maximum ratings.
- **Bootstrap caps** C312–C315 go directly between the BST_x and OUT_x pins on the top layer, with no vias.
- **PowerPAD.** The chosen footprint has 24 vias (3 × 8 at 1.2 mm pitch, 0.2 mm drill, 0.5 mm pad). JLC 4-layer charges extra below 0.3 mm drill. If so, use the non-ThermalVias variant and hand-place 0.3/0.6 mm vias (≥ 3 × 7 under the pad), plus more GND vias in the copper around the package.
  - No thermal relief on these vias.
  - Unbroken GND pour on L2, and on L3/L4 where possible, out to all four sides.
  - Paste coverage 70–80 % as an aperture array (§9.1.3.2).
  - RθJA ≈ 24 °C/W on the TI 4-layer EVM: at 2 W dissipation the junction is about 48 °C above ambient.
- **Output LC loop.** OUT_x → L → C → GND return goes straight back to the PGND pins and PowerPAD.
  - Keep each leg's L and C pair tight and the + and − legs symmetric.
  - Mount the inductors with no other traces underneath.
  - Put the filter caps' GND vias next to the cap pads and route speaker pairs as tightly coupled pairs to J301/J302.
  - Route the OUT traces ≥ 1.0 mm wide (≥ 4 A peak) on the top layer.
- Keep `I2S_*`, `I2C_*` and `AMPx_FAULT_N` away from the OUT_x and switch-node areas; cross them only at 90° on another layer over GND.
- Place both amps so their speaker connectors sit at the board edge, far from the ESP32 antenna and from the boost inductor.
- Bring PVDD from the boost output with a ≥ 2 mm wide trace or a plane.
- TP304/TP401 (PVDD) sit beside the PVDD decoupling at each amp. TP301–TP303 (I2S) and TP305 (GND) sit at U301 so the I2S lines can be probed at the receiver with a short ground spring.

---

## 4. Sheet `ui_io`: UI board link and I2S expansion

### 4.1 Components

| Ref | Value | Footprint | Rating | LCSC | B/E | Symbol (stock?) |
|---|---|---|---|---|---|---|
| J501 | FPC 1.0 mm 20P, bottom contact, slide lock (JUSHUO AFA07-S20FCA-00) | `Connector_FFC-FPC:JUSHUO_AFA07-S20FCA-00_1x20-1MP_P1.0mm_Horizontal` | 50 V, ~0.5 A/contact | C262724 | E | Connector_Generic_MountingPin:Conn_01x20_MountingPin |
| — (cable, buy separately) | FFC 20P 1.0 mm **100 mm** (mech, ECO-002 #6), **same-side ("Type A")** | — | | C63014 (150 mm: C64775; 200 mm: C12151) | E | — |
| R501–R504 | 1 kΩ | 0402 | | C11702 | B | Device:R |
| C501 | 10 µF | 0603 | 10 V X5R | C19702 | B | Device:C |
| C502 | 100 nF | 0402 | 16 V | C1525 | B | Device:C |
| U501 | SN74LVC157APWR | `Package_SO:TSSOP-16_4.4x5mm_P0.65mm` | 2–3.6 V | C406871 | E | 74xx:74LS157 (pin-identical; set Value) | **DNP (default)** |
| C503 | 100 nF | 0402 | 16 V | C1525 | B | Device:C | **DNP with U501** |
| R505–R507 | 0 Ω | 0402 | | C17168 | B | Device:R | **Fitted (default)**; remove when U501 is fitted |
| R508–R511 | 10 kΩ | 0402 | | C25744 | B | Device:R | Pull-downs on the external I2S inputs and SEL (fit always) |
| J502 | 1×5 header 2.54 mm | `Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical` | | — | — | Connector_Generic:Conn_01x05 | **DNP** (hand-fit) |

### 4.2 J501 pinout (main board), and why

| Pin | Net | Main-board connection |
|---|---|---|
| 1 | `GND` | |
| 2 | `+3V3` | C501, C502 at the connector |
| 3 | `+3V3` | |
| 4 | `GND` | shield for SCLK |
| 5 | `LCD_SCLK` | from R113 (68 Ω at the ESP32) |
| 6 | `GND` | shield for SCLK and MOSI |
| 7 | `LCD_MOSI` | from R114 |
| 8 | `LCD_CS` | from R115 |
| 9 | `LCD_DC` | from R116 |
| 10 | `LCD_BL` | from R117 |
| 11 | `GND` | shield for PDM_CLK |
| 12 | `PDM_CLK` | from R118 |
| 13 | `GND` | shield for PDM_CLK |
| 14 | `PDM_DATA` | direct to U101 pin 9 (33 Ω source resistor is on the UI board at the mic) |
| 15 | `UI_ENC_A` | → R501 1 k → `ENC_A` |
| 16 | `UI_ENC_B` | → R502 1 k → `ENC_B` |
| 17 | `UI_ENC_SW` | → R503 1 k → `ENC_SW` |
| 18 | `UI_BTN_ADC` | → R504 1 k → `BTN_ADC` |
| 19 | `GND` | Separates `UI_BTN_ADC` (18) from `CHG_QON` |
| 20 | **`CHG_QON`** (ECO-002 #2) | Direct to the charger sheet net `CHG_QON` (U701 /QON, SW701). UI board: button to GND only |
| MP | `GND` | mounting pads |

Design notes:
- Both fast clocks (SCLK, 5; PDM_CLK, 12) have GND on both sides, and MOSI sits next to a GND.
- The display data group (5–10) and the mic group (12–14) are separated by GND 11.
- There are 2 supply pins and 7 GNDs (including MP). Expected 3V3 load is ≤ 100 mA (display logic + backlight ≈ 50–80 mA, mic 0.65 mA). The cable is 100 mm of about 0.6 mm × 35 µm copper, roughly 0.08 Ω per conductor, so ≈ 0.04 Ω for 2 pins in parallel: ≤ 4 mV drop.
- **CHG_QON (pin 20, ECO-002 #2, as drawn in the schematic).** Pin 19 stays GND, which separates `CHG_QON` from `UI_BTN_ADC` (18). The clock shields (4, 6, 11, 13) are unchanged, and the MP pads remain GND at the connector ends. Main pin 20 = UI pin 1.
  - /QON has an internal 200 kΩ pull-up to about 3.2–3.8 V (BQ25798 §6.5: V_QON, R_QON). Low ≤ 0.4 V is a press.
  - Press ≥ 1 s exits ship mode; hold ≥ 10 s does a full system power reset (BQ25798 §7.3.12).
  - No pull-up, series part or rail-referenced ESD on this line: a diode to +3V3 would clamp /QON low whenever +3V3 is down (ship mode) and look like a held button.
  - Pin 20 is the outermost contact, with GND (19) on one side and the GND mounting pad on the other. Its high impedance (200 k) is acceptable because the charger qualifies presses over ≥ 15 ms–1 s.
- The 1 kΩ series resistors protect the input-only ESP32 pins from cable ESD and hot-plug. They are negligible against the UI-board pull-ups (10 k) and the ADC source (C104 10 nF gives τ = 10 µs).
- SPI clock up to 40 MHz over the FFC with **68 Ω** source termination on SCLK/MOSI (and PDM_CLK). Sim S6 at 200 mm: overshoot is damped, f_max ≈ 53 MHz, and MOSI→CS crosstalk is 0.49 V, below the 0.99 V V_IL. The production cable is 100 mm, so the 200 mm sim is conservative. If the display shows errors, drop to 26.7 or 20 MHz.

**Cable orientation.** A same-side cable between two bottom-contact connectors, both top-mounted with their openings facing each other, connects **main pin n ↔ UI pin (21 − n)**. The UI board spec is written for this. If the mechanical design flips the UI board so the cable must twist, re-derive the mapping or use the reverse-type cable (C12159).

### 4.3 I2S source mux (provision) and expansion header

**Default build:** U501 and C503 DNP; R505–R507 fitted. The ESP32 drives the amps directly.

| Part | Pin 1 | Pin 2 |
|---|---|---|
| R505 | `I2S_BCLK_MCU` | `I2S_BCLK` |
| R506 | `I2S_LRCK_MCU` | `I2S_LRCK` |
| R507 | `I2S_DOUT_MCU` | `I2S_SDIN` |
| R508 | `I2S_EXT_BCLK` | `GND` |
| R509 | `I2S_EXT_LRCK` | `GND` |
| R510 | `I2S_EXT_DATA` | `GND` |
| R511 | `I2S_SEL` | `GND` |

U501 (SN74LVC157A; function: G = L, A/B = L → Y = A, so the ESP32 is selected by default):

| Pin | Name (TI) / (74LS157 sym) | Net |
|---|---|---|
| 1 | A/B / S | `I2S_SEL` |
| 2 | 1A / I0a | `I2S_BCLK_MCU` |
| 3 | 1B / I1a | `I2S_EXT_BCLK` |
| 4 | 1Y / Za | `I2S_BCLK` |
| 5 | 2A / I0b | `I2S_LRCK_MCU` |
| 6 | 2B / I1b | `I2S_EXT_LRCK` |
| 7 | 2Y / Zb | `I2S_LRCK` |
| 8 | GND | `GND` |
| 9 | 3Y / Zc | `I2S_SDIN` |
| 10 | 3B / I1c | `I2S_EXT_DATA` |
| 11 | 3A / I0c | `I2S_DOUT_MCU` |
| 12 | 4Y / Zd | NC |
| 13 | 4B / I1d | `GND` (unused inputs must not float) |
| 14 | 4A / I0d | `GND` |
| 15 | G / E (active-low strobe) | `GND` |
| 16 | VCC | `+3V3` (C503 100 nF) |

J502 (I2S input header): 1 `I2S_EXT_BCLK`, 2 `I2S_EXT_LRCK`, 3 `I2S_EXT_DATA`, 4 `GND`, 5 `I2S_SEL` (drive high to select the external source). The external source must be a 3.3 V I2S master; LVC inputs are 5.5 V tolerant. A daughterboard needs its own supply (no +3V3 pin, as briefed). Consider a 6th pin `+3V3` if v1.1 needs it.

**Variant "I2S_EXT":** fit U501 and C503, remove R505–R507.

Firmware cannot read `I2S_SEL` (no spare GPIO). When a source switches, the TAS5805M flags a clock error and auto-mutes, then recovers (§7.3.4). For a clean switch, mute the amps over I2C first.

**Timing check.** SN74LVC157A at 3.3 V ± 0.3 V, −40…85 °C (SCAS292 §4.9): t_pd (A/B data → Y) = 1.0–5.2 ns, and output skew t_sk(o) ≤ 1 ns. All three I2S lines pass through the same package, so the relative skew BCLK↔LRCK/DATA is ≤ 1 ns.
- The ESP32 changes WS/DATA on the BCLK falling edge, and the TAS samples on the rising edge (§7.3.3). At 3.072 MHz the half-period is 163 ns, so ≥ 155 ns of setup/hold margin remains against the TAS's t_DLY ≥ 5 ns LRCLK→SCLK requirement (§6.5).
- Even at the TAS maximum SCLK of 24.576 MHz (20 ns half-period), the margin is still ≥ 14 ns.
- **The mux is fine for I2S.** TI's own TAS5805MEVM routes I2S through SN74LVC2G157 muxes (SLOU510 Fig. 3).

### 4.4 Layout (ui_io)

- Place J501 at the board edge nearest the UI board. Keep the SPI and PDM traces over unbroken GND, run them on the same layer as the module's pins, and keep them ≤ 60 mm with no stubs.
- Place U501 / R505–R507 between the ESP32 and the amps on the I2S path. Route `I2S_BCLK` as a daisy chain U501/R505 → U301 → U401 with ≤ 5 mm stubs, and keep it ≥ 3× its width from other signals and from the inductors.
- Keep J502 near U501.

---

## 5. Status LED

D101 on GPIO0 (§1.2) is the only LED driven by the ESP32. There is no spare GPIO for a user-visible LED on the UI board: the round display carries status, and the charger's STAT LED (power sheet) shows charging when the display is off. D101 sits inside the enclosure and is for bench debug.

---

## 6. Global nets from these sheets (for the power sheet and the sheet hierarchy)

| Net | Driven by | Used on |
|---|---|---|
| `ESP_EN`, `ESP_IO0`, `ESP_TXD0`, `ESP_RXD0` | mcu / usb_uart | mcu, usb_uart |
| `I2S_BCLK_MCU`, `I2S_LRCK_MCU`, `I2S_DOUT_MCU` | mcu | ui_io |
| `I2S_BCLK`, `I2S_LRCK`, `I2S_SDIN` | ui_io (mux / 0 Ω) | amp_left, amp_right |
| `AMP_PDN` | mcu | amps |
| `AMPL_FAULT_N`, `AMPR_FAULT_N` | amps | mcu |
| `AMP_FAULT` | mcu | mcu |
| `LCD_SCLK`, `LCD_MOSI`, `LCD_CS`, `LCD_DC`, `LCD_BL`, `PDM_CLK` | mcu | ui_io |
| `PDM_DATA`, `ENC_A`, `ENC_B`, `ENC_SW`, `BTN_ADC` | ui_io | mcu |
| `USB_DP`, `USB_DN` | power (USB-C, ESD) | usb_uart |
| `I2C_SDA`, `I2C_SCL` | mcu (pull-ups) | amps, power |
| `CHG_INT` | power (open-drain) | mcu (pull-up) |
| `BOOST_EN` | mcu (100 k PD) | power. **No pull-up allowed on the power sheet** |
| `PVDD_TRIM` | mcu (GPIO25) | power. The network must give 18.0 V when the pin is Hi-Z |
| `PVDD` | power | amps |
| `CHG_QON` | power (BQ /QON, internal pull-up) | ui_io J501 pin 20 → UI power button (UI pin 1) |

## 7. Extended parts added by these sheets

ESP32-WROVER-E-N8R8, CH340C, TAS5805MPWPR (×2), FXL0630-100-M (×8), 470 µF 35 V C2836436 (×2; ideally shared with the power sheet), B2P-VH(LF)(SN) (×4), AFA07-S20FCA-00, (DNP) SN74LVC157APWR, plus the ECO-001 values 68 Ω 0402 (C25131) and 2.2 µF 0402 (C170151). Everything else here is Basic.

## 8. Sources

- TI TAS5805M datasheet SLASEH5D (Nov 2020, rev. 2022):
  - Table 5-1 pins; §6.3 min load footnote; §6.5 RDS(on) 180 mΩ, OCE 5 A, Fsw 384/768 kHz, t_DLY, SCLK limits
  - §7.3.1 supplies; §7.3.3 clock rates; Table 7-5 ADR; §7.5.3.1 start-up
  - Regs 0x02 / 0x03 / 0x54 / 0x60 / 0x61
  - §8.1.1 bootstrap 0.22 µF; §8.1.2 Eq. 1–4, Tables 8-1 and 8-2; §8.1.3 decoupling
  - Fig. 8-2 and Table 8-4 (inductor-filter BTL application); §9 layout; PWP0028M land pattern
- TI TAS5805MEVM user's guide SLOU510 (May 2018): Fig. 3 (I2S muxes SN74LVC2G157), Fig. 5 (amp schematic: PDN 10 k, ADR 15 k, 4.7 µH + 0.68 µF at 768 kHz), BOM.
- Espressif ESP32-WROVER-E/IE datasheet v2.4: Table 3 pins; Table 4 strapping defaults; §4.2 MTDI/VDD_SDIO; Table 9 timing; Fig. 11 peripheral schematic (22 µF + 0.1 µF, EN RC 10 k / 1 µF, "IO12 kept low"); Fig. 15 land pattern; §11.2 placement.
- Espressif ESP32 series datasheet: DC characteristics (V_IH/V_IL, R_PU 45 k), IO_MUX reset states. ESP32 errata 3.11 (GPIO36/39 glitch).
- Espressif kicad-libraries (github.com/espressif/kicad-libraries), `ESP32-WROVER-E` symbol and footprint, vendored.
- WCH CH340 datasheet V3D: §3 note (CH340C built-in clock), §4 pin table, §5.1 V3/VCC at 3.3 V, UD± direct.
- TI SN74LVC157A datasheet SCAS292S (Dec 2024): pin table, function table, §4.9 switching characteristics.
- TDK T3903 datasheet DS-000358 (T3902 sibling): PDM clock ranges and pin table. The T3902 PDF could not be retrieved, so verify it.
- JLCPCB parts API (stock and Basic/Extended), 2026-11-24.

## 9. Changelog

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-11-24 | First issue (PVDD 16 V, 4 Ω woofers). |
| v1.1 | 2026-11-24 | PVDD 18.0 V; ND65-8 8 Ω woofers on ch A. Peak-current and limiter calcs redone. Bulk cap 470 µF 35 V C2836436. AGAIN 0x08. PVDD pre-biased at about VSYS with the boost off. BOOST_EN → ≥ 20 ms → PDN; PDN low before BOOST_EN low. |
| v1.2 | 2026-11-24 | **ECO-001:** R113/R114/R118 33 → 68 Ω; C103 1 → 2.2 µF (EN τ 22 ms); tweeter +≈2 dB high shelf (firmware). **ECO-002:** J501 pin 20 GND → `CHG_QON` (UI pin 1, power button; pin 19 stays GND); CH340C LCSC C84681 → C7464026; test points added per the schematic netlist: TP105–TP110 (mcu: I2C_SDA, I2C_SCL, AMP_PDN, BOOST_EN, AMP_FAULT, GND), TP301–TP305 (amp_left: I2S_BCLK/LRCK/SDIN, PVDD, GND), TP401 (amp_right: PVDD); TP703 (SFET_G) is on the power spec; FFC 100 mm (C63014); I2C at 100–200 kHz until t_r is scoped (review S5). |
| v1.2 rev b | 2026-11-24 | Test points renumbered to match the schematic netlist (TP301–TP305, TP401; no TP402, no TP501–TP504). §3.5: PVDD soft-start sequence via PVDD_TRIM (spec_power v1.2 §4.1.4) and the 11 ms ramp from sim S1 (replaces 9 ms). |
