# UI (top) board: circuit specification (v1.2, short)

Status: v1.2, 2026-11-24 (changelog at the end). This board gets its own KiCad project later. It connects to the main board connector J501 (see `docs/spec_signal.md` §4.2) through a **20-pin 1.0 mm same-side FFC, 100 mm long** (LCSC C63014; length per `mech_envelope.md`; 150 mm: C64775).

It carries:
- the 1.28" round display (Waveshare GC9A01 module, plugged in through its 8-pin header);
- the PDM MEMS mic (TDK T3902);
- the EC11 encoder with push switch;
- 3 tactile buttons on an ADC ladder;
- the **power button** (to the charger /QON through the FFC; ECO-002 #2);
- ESD protection for everything the user can touch.

No ICs other than the mic and the ESD array.

## 1. Components

| Ref | Value / part | Footprint | LCSC | B/E | Symbol |
|---|---|---|---|---|---|
| J1 | FPC 1.0 mm 20P bottom-contact slide-lock, JUSHUO AFA07-S20FCA-00 | `Connector_FFC-FPC:JUSHUO_AFA07-S20FCA-00_1x20-1MP_P1.0mm_Horizontal` | C262724 | E | Connector_Generic_MountingPin:Conn_01x20_MountingPin |
| J2 | 1×8 2.54 mm socket for the Waveshare module (hand-fit) | `Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical` | — | DNP/hand | Connector_Generic:Conn_01x08 |
| U1 | TDK T3902 MMICT390200012, PDM, **bottom port** | LGA-5 3.5×2.65 mm. Start from `Sensor_Audio:Knowles_LGA-5_3.5x2.65mm` and **verify pad map and port position against the TDK T3902 drawing** | C3171752 | E | custom (5 pins, below) |
| ENC1 | ALPS EC11E18244AU (18 detents, push) or Bourns PEC11R-4215F-S0024 | `Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm` | C202365 / C143790 | E | Device:RotaryEncoder_Switch (A, B, C, S1, S2) |
| SW1–SW3 | Tactile TS-1187A-B-A-B | `Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A` | C318884 | B | Switch:SW_Push |
| SW4 | Power button, TS-1187A-B-A-B (or a panel-feel switch chosen by mech) | `Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A` | C318884 | B | Switch:SW_Push |
| D2 | ESD5Z5V0 TVS, 5 V standoff, unidirectional, **to GND only** | `Diode_SMD:D_SOD-523` | C502546 | E | Device:D_TVS |
| D1 | SRV05-4, 4-line ESD | `Package_TO_SOT_SMD:SOT-23-6` | C7420376 | E (preferred, no loading fee) | Power_Protection:SRV05-4 |
| R1–R3 | 10 kΩ (encoder A/B/SW pull-ups) | 0402 | C25744 | B | Device:R |
| R4–R6 | 10 kΩ (encoder A/B/SW series) | 0402 | C25744 | B | Device:R |
| C1–C3 | 10 nF (encoder debounce) | 0402 | C15195 | B | Device:C |
| R7 | 10 kΩ (ladder top) | 0402 | C25744 | B | Device:R |
| R8 | 3.3 kΩ (ladder SW2) | 0402 | C25890 | B | Device:R |
| R9 | 10 kΩ (ladder SW3) | 0402 | C25744 | B | Device:R |
| R10 | 33 Ω (PDM_DATA source series, at the mic) | 0402 | C25105 | B | Device:R |
| R11 | 0 Ω (mic SELECT → +3V3, fitted) | 0402 | C17168 | B | Device:R |
| R12 | 0 Ω (mic SELECT → GND, **DNP**) | 0402 | C17168 | B | Device:R |
| C4 | 100 nF (mic VDD, ≤ 1 mm from pin 5) | 0402 | C1525 | B | Device:C |
| R13, C5 | 10 kΩ + 1 µF (display RST power-on RC) | 0402 | C25744 / C52923 | B | Device:R / Device:C |
| C6, C7 | 10 µF + 100 nF (+3V3 at J1) | 0603 / 0402 | C19702 / C1525 | B | Device:C |

## 2. J1 pinout (UI side, mirrored)

A same-side FFC between two bottom-contact connectors, both mounted on the top side with their openings facing each other, maps **UI pin k = main pin 21 − k**. Re-check against the enclosure CAD before layout. If the cable has to twist, use the reverse-type cable C12159 and then UI pin k = main pin k.

| UI pin | Net | Main pin |
|---|---|---|
| 1 | **CHG_QON** | 20 |
| 2 | GND | 19 |
| 3 | BTN_ADC | 18 |
| 4 | ENC_SW | 17 |
| 5 | ENC_B | 16 |
| 6 | ENC_A | 15 |
| 7 | PDM_DATA | 14 |
| 8 | GND | 13 |
| 9 | PDM_CLK | 12 |
| 10 | GND | 11 |
| 11 | LCD_BL | 10 |
| 12 | LCD_DC | 9 |
| 13 | LCD_CS | 8 |
| 14 | LCD_MOSI | 7 |
| 15 | GND | 6 |
| 16 | LCD_SCLK | 5 |
| 17 | GND | 4 |
| 18 | +3V3 | 3 |
| 19 | +3V3 | 2 |
| 20 | GND | 1 |
| MP | GND | — |

## 3. Connections

**Display (J2, Waveshare 1.28" module header order; confirm against the module silkscreen):**

| J2 pin | Module pin | Net |
|---|---|---|
| 1 | VCC | +3V3 |
| 2 | GND | GND |
| 3 | DIN | LCD_MOSI |
| 4 | CLK | LCD_SCLK |
| 5 | CS | LCD_CS |
| 6 | DC | LCD_DC |
| 7 | RST | LCD_RST (R13 10 k to +3V3, C5 1 µF to GND, τ = 10 ms; firmware also sends SWRESET 0x01) |
| 8 | BL | LCD_BL (PWM from ESP32 GPIO14) |

**Mic U1** (pin map from the T3902/T3903 family, top view, terminal side down: 1 DATA, 2 SELECT, 3 GND, 4 CLK, 5 VDD; **verify against T3902 DS-000357 before layout**):

| Pin | Name | Net |
|---|---|---|
| 1 | DATA | → R10 33 Ω → PDM_DATA |
| 2 | SELECT | R11 0 Ω to +3V3 (left channel, data valid on the falling clock edge). R12 0 Ω to GND DNP (right channel) |
| 3 | GND | GND |
| 4 | CLK | PDM_CLK |
| 5 | VDD | +3V3, C4 100 nF |

- Clock: 2.0–3.3 MHz for High-Quality mode (3.072 MHz at fs = 48 kHz), or 400–800 kHz for Low-Power mode.
- **Acoustic port:** a 0.8 mm non-plated hole through the PCB, centred on the mic port, inside an unbroken GND ring.
- Gasket or acoustic mesh from the PCB back to the enclosure opening, sealed so the mic does not hear the cabinet interior.
- Keep the mic away from the encoder detent noise and the display backlight switching.

**Encoder ENC1** (Bourns application filter, per line):
- A: ENC1.A → `ENC_A_RAW`; R1 10 k from `ENC_A_RAW` to +3V3; R4 10 k from `ENC_A_RAW` to `ENC_A`; C1 10 nF from `ENC_A` to GND. Same for B (R2, R5, C2) and SW (ENC1.S1 → R3, R6, C3; ENC1.S2 → GND). ENC1.C → GND; ENC1.MP (bushing and tabs) → GND.
- Debounce τ = 10 kΩ × 10 nF = 0.1 ms. That passes about 180 detents/s (5 rev/s × 36 pulses) with margin.
- ENC_SW is the ESP32 deep-sleep wake source (GPIO4, active low).

**Buttons (ADC ladder on `BTN_ADC`, ESP32 GPIO39, ADC1, 12 dB attenuation):**
- R7 10 k from +3V3 to `BTN_ADC`.
- SW1 from `BTN_ADC` to GND → 0 V.
- SW2 from `BTN_ADC` → R8 3.3 k → GND → 3.3 × 3.3/13.3 = **0.82 V**.
- SW3 from `BTN_ADC` → R9 10 k → GND → **1.65 V**.
- Idle → 3.3 V (ADC saturates; that is fine).
- Firmware thresholds: < 0.41 V = SW1; 0.41–1.24 V = SW2; 1.24–2.4 V = SW3; > 2.4 V = none. One press at a time; the lowest resistance wins.
- Maximum current 0.33 mA. The main board adds 1 kΩ series and 10 nF at the ESP32 pin.

**Power button SW4 (ECO-002 #2):**
- SW4 from `CHG_QON` (J1 pin 1, the outermost contact; pin 2 is GND) to GND. **No pull-up and no other parts:** the BQ25792 /QON has an internal 200 kΩ pull-up to about 3.2–3.8 V.
- Press ≥ 1 s wakes from ship mode, i.e. power on. Hold ≥ 10 s does a full system power reset, which also recovers a hung ESP32 on battery.
- D2 (ESD5Z5V0): cathode → `CHG_QON`, anode → GND, next to SW4.
- **Do not put CHG_QON on the SRV05-4.** Its VP steering diode to +3V3 would clamp /QON to about 0.6 V whenever +3V3 is down (ship mode), which reads as a held button.
- D2 leakage (≤ 0.1 µA × 200 kΩ ≈ 20 mV) is negligible against V_IH_QON = 1.3 V.
- Route the pin-1 trace straight to SW4 and D2, keeping it away from the display SPI lines. UI pin 2 (GND) separates it from BTN_ADC (pin 3).

**ESD D1 (SRV05-4):**
- Pin 1 → ENC_A, pin 3 → ENC_B, pin 4 → ENC_SW, pin 6 → BTN_ADC.
- Pin 5 (VP) → +3V3, pin 2 (VN) → GND.
- Place it between the user parts and the connector, with a short GND via.

## 4. Layout notes

- 2-layer board is acceptable. Put a solid GND pour on the bottom layer, and keep SCLK/MOSI and PDM_CLK over unbroken GND from J1 to the display header and the mic.
- The display module mounts on the top side; the encoder shaft passes through the top cover. Leave a ≥ 2 mm keep-out around the mic port hole for the gasket.
- Every part on this board is SMD except the encoder and J2. Consider the SMD EC11J1525402 (C209762) to avoid JLC's THT fee.

## 5. Changelog

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-11-24 | First issue. |
| v1.2 | 2026-11-24 | (Numbered to match spec_signal v1.2.) ECO-002 #2: UI pin 1 (main pin 20) GND → `CHG_QON` (UI pin 2 stays GND), plus SW4 power button to GND and a GND-only TVS D2 (ESD5Z5V0, C502546). ECO-002 #6: FFC 100 mm (C63014). Main-board source resistors on SCLK/MOSI/PDM_CLK are now 68 Ω (ECO-001 #3); there is no change on this board. |
