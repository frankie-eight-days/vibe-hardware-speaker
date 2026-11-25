# Portable Stereo Bluetooth Speaker — Requirements (v0.1)

Working name: **TBD**. Goal: a "vibe hardware" mixed-signal project (digital + analog + power) that holds its own against a JBL Flip/Charge-class speaker, built from a JLCPCB-assembled PCB, LCSC parts, 3D-printed enclosure (Flashforge Adventurer 5M Pro), and off-the-shelf drivers/hardware.

## 1. Product targets

| Item | Target | Notes |
|---|---|---|
| Channels | Stereo, 2-way per side, **bi-amped** (active DSP crossover) | 4 driver channels total |
| Drivers | 2× woofer (2.5–3.5"), 2× tweeter (~¾"), 2× passive radiator | PRs on end caps (visible) |
| Bass extension | F3 ≤ 65 Hz (with DSP), F6 ≤ 55 Hz | JBL Flip 6 ≈ 63 Hz |
| Max SPL | ≥ 90 dB @ 1 m (pink noise, battery, **on a table / half-space**) | limiter-protected; free-air ≈ 85 dB |
| Driver layout | Woofers rear-mounted on front face (66 mm apart); **tweeters angled up 40° in sealed printed pods** on the front shoulders (166 mm apart), **minimal 3 mm bezel instead of a full waveguide (decided; verify with BEM sim)** | see `docs/mech_envelope.md` |
| Enclosure (decided) | **Ø95 × 210 mm body, 216 mm over PR flanges**, 5 printed PETG parts, ~0.85 L net | nothing in stock fits Ø90 |
| Battery pick (decided) | **Gens ace 2S 5000 mAh TX/RX LiPo** (109×42×19.5 mm, ~$31), bonded 10 k NTC; fallback Gens ace 3500 mAh with spacer | RC-brand, no PCM: board protection covers it; bench-test 6 A |
| Amp power | ~15–20 W/woofer, ~5–10 W/tweeter | boost rail ~18–20 V |
| Source | Bluetooth A2DP sink (SBC required, AAC nice-to-have) | |
| Control | Wi-Fi web UI for live EQ/presets; rotary encoder + push; 2–3 buttons | |
| Display | 1.28" round TFT (GC9A01-class) on top | mode, EQ curve, level meter, battery |
| Mic | 1× digital MEMS mic | placement (bass) compensation + ambient auto-loudness |
| Battery | Off-the-shelf **pre-built 2S pack** (no spot welding), plugs in via **XT30 (power) + JST-XH 3-pin (balance)**; charger/balancing/protection stay on our board. Pouch pack preferred; **no device-grade pack fits the capsule, so the decided pack is the Gens ace 2S 5000 mAh TX/RX LiPo** (see Battery pick row); enclosure needs swell clearance + puncture protection; charge current ≤ 0.5C unless the pack datasheet says otherwise | JLC won't ship cells; ≤ ~40 W avg draw (charger BATFET 6 A RMS) |
| Drivers (**set B8, decided**) | 2× Dayton ND65-8 woofer (8 Ω), 2× Peerless OT19NC00-04 tweeter (4 Ω), 2× Dayton DMA58-PR | $93.54 at Parts Express; F3 64 Hz, ~90.6 dB pink (half-space, A1 refined model), ≥0.50 L net; see `research/drivers.md` |
| Amp rail | **PVDD 18 V** (TPS61178), trim network fitted (ECO-001) for soft start and dynamic PVDD | 8 Ω woofers keep the TAS5805M well under its 5 A OCP |
| Runtime | ≥ 8 h at moderate volume | |
| USB | USB-C: PD sink charging/power, play-while-charging, firmware flashing | USB-audio input = **optional add-on, decide after research** |
| Size | Horizontal capsule, ≤ ~210 mm long, ~80–95 mm dia | printer volume 220×220×220 mm |
| Budget | ~$250 for v1 (5 PCBA, drivers, filament, hardware, UMIK-1 mic) | |

Out of scope: waterproofing, multi-speaker linking, phone app (web UI instead), LDAC/aptX.

## 2. Block diagram

```
 USB-C ──► PD sink ──► 2S charger + power path ──► VSYS (6–8.6 V)
              │               │                       │
              │           2S Li-ion pack ◄── protection/balancing
              │                                       ├──► boost ~18–20 V ──► AMP_L (TAS5805M-class) ──► woofer L / tweeter L
              │                                       │                  └──► AMP_R                ──► woofer R / tweeter R
              │                                       └──► buck 3.3 V ──► ESP32 + UI + mic
              └──► USB-UART (flashing/debug) ──► ESP32-WROVER-E (PSRAM required for BT+Wi-Fi audio)
                                                  ├─ I2S1 TX ──► both amps (I2S)
                                                  ├─ I2S0 PDM RX ◄── MEMS mic (PDM, on UI board)
                                                  ├─ I2C ──► amps (DSP coeffs), charger, fuel gauge
                                                  ├─ SPI ──► round TFT
                                                  └─ GPIO ◄── encoder, buttons, battery sense
```

## 3. DSP split

- **Amp DSP (TAS5805M-class):** crossover, per-driver EQ, DRC/limiter, excursion protection. Safe even if MCU firmware glitches.
- **ESP32:** A2DP decode, user EQ/presets, loudness, bass enhancement, stereo widening, mic-based auto-EQ, web UI, display.

## 4. Manufacturing / mechanical

- PCB: 4-layer, JLCPCB PCBA, LCSC parts, prefer JLC **basic** parts; minimize extended-part count. Main board + possibly small top UI board.
- Enclosure: FDM PETG/ASA, ≥4 perimeters, dense infill, internal bracing, printed tweeter pods with a 3 mm bezel, foam gaskets, brass heat-set inserts, perforated-aluminum grille, polyfill stuffing.
- Hardware from McMaster-Carr / Home Depot.

## 5. Simulation & verification plan

| Domain | Our own tool | Cross-check |
|---|---|---|
| Box/PR alignment | Python lumped-element (T/S) model | WinISD/VituixCAD (Wine) if needed |
| Directivity/diffraction | — | bempp-cl + gmsh on FreeCAD geometry |
| PCB thermal | Python 2D finite-difference solver + heatmaps | FreeCAD FEM (CalculiX) / Elmer |
| Acoustic tuning | — | REW (macOS) + UMIK-1, measured → amp EQ |

## 6. Environment

macOS arm64, KiCad + FreeCAD installed, Python 3.9 (system), Flashforge Adventurer 5M Pro on network.

## 7. Open decisions

- USB-audio input (extra bridge chip) — yes/no after research.
- Boost rail vs 3S pack vs direct-from-battery amp supply.
- Driver set (sets enclosure volume and size).
