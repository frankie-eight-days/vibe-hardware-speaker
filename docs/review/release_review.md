# Main board schematic: release review for PCB placement

**Gate:** schematic → PCB placement (sign-off before layout).
**Date:** 2026-11-24.
**Method:** `review-schematic-release` skill and its checklist, all 44 IDs.
**Reviewer:** single desk review. No hardware, no purchasing, no design edits.

## Verdict

**Placement can proceed.** No blocker was found. I found no wrong pin, footprint, net, polarity or rating in the native design that would force placed parts to move.

Placement starts with conditions. Four should-fix items change a footprint or a placement constraint, so close them in the first placement session:

- **S2:** add a DNP gate-source footprint at Q701.
- **S6:** choose the JP803 variant and fix the NTC/J803 position.
- **S11:** assign the three 10.2 mm electrolytics to height zones.
- **L5:** add the extra test points.

Routing must not start until **S4** (the FFC pinout) and **S9** (stale spec values) are closed. Fab or production release needs **S8**, **S10** and **L3**. The first power-on with a battery needs the **S1** and **S3** firmware settings and their bench checks.

## 1. Baseline (R01)

| Item | Value |
|---|---|
| Native design | `hw/mainboard/speaker_main.kicad_pro` with 10 sheets: root, usb_power, charger, battery, rails, mcu, usb_uart, ui_io, amp_left, amp_right. 257 refdes. Rev 0.1 (drawing-sheet field), files dated 2026-11-24 16:25 to 16:51 |
| Snapshot | `docs/review/snapshot/{mainboard,lib}`: byte-identical copy (SHA-256 list in `docs/review/exports/snapshot_sha256.txt`). Root sch `29783ffe298d…`, speaker.kicad_sym `6fd3ccd256fb…`, RNW0013A fp `d58b24818121…`, fuse fp `f5d3e4866c4d…`, WROVER fp `88c8f8d587f9…` |
| Tool | KiCad 10.0.4 (`/opt/homebrew/bin/kicad-cli`). Stock libraries are from the KiCad 10.0.4 app bundle |
| Local libraries | `speaker` (TPS61178, CH224Q, R5460x2, HY2213 symbols; RNW0013A and 2410 fuse footprints) and `Espressif` (vendored), both through `${KIPRJMOD}/../lib` |
| Variant | Default build. 11 parts carry a `DNP` property: R601, C602, C719, C720, R710, C956, D951, R956, U501, C503, J502. The KiCad DNP attribute is not set on any of them (S10) |
| Supporting docs (SHA-256 prefix) | spec_power v1.1 `547b8aaf57cb`, spec_signal v1.1 `7dafb9f0b5bf`, eco_001 `51ad5ca35ce0`, requirements v0.1 `138262c2ba20`, mech_envelope v0.1 `af1a7b4f99de`, sim/spice/README `955862d46a57` |
| Exports (from the snapshot) | `exports/erc.json`, `exports/erc.rpt`, `exports/netlist.xml` (KiCad XML), `exports/schematic.pdf` (10 pages, A3), `exports/png/p-01…10.png` (110 dpi renders), `exports/bom_kicad.csv` |
| Datasheets used | Session scratchpad `datasheets/` and `datasheets/pw/`: BQ25798 SLUSDV2C, BQ25792 ZHCSMD3C (Rev C, Aug 2022), TPS61178 SLVSDA7E, TPS62933, TAS5805M SLASEH5D, CH224 manual V2.1, R5460x2 EA-165-160603, HY2213 DS-V05, NCEP3065QU, Littelfuse 451, Amass XT30PW-M, ESP32-WROVER-E v2.4, SN74LVC157A |
| Supply check | LCSC/JLC APIs, 2026-11-24. Raw JSON is in the scratchpad `lcsc/` and `jlc/` folders |

Settled earlier and not re-opened: NCEP3065QU on the CSD17581Q3A symbol with the NexFET footprint, and BQ25792 on the BQ25798 symbol (pin-identical, 0x6B). S3 is a different question: it concerns a register default, not the pinout.

## 2. Issue register (ranked)

Blockers: **none**.

| # | Rank | Location | Consequence | Evidence | Owner | Earliest blocked stage | Measurable closure |
|---|---|---|---|---|---|---|---|
| **S1** | Should-fix (safety, firmware-dependent) | charger U701 REG14; rails U901; battery U801/F801 | Fast battery over-current protection exists only while firmware keeps `SFET_PRESENT=1` and `EN_BATOC=1`. **EN_BATOC is reset by WATCHDOG and REG_RST** (BQ25798 Table 7-30). If firmware is blank, hung or late, a PVDD or VSYS fault is limited only by the R5460 (0.2 V / (2 × ≈2.3–2.5 mΩ) ≈ 40 A for 12 ms) and F801 (10 A, does not open quickly at 10–20 A). PVDD has no disconnect FET, so a PVDD short with EN low runs through L901 and U901's high-side body diode, which U901 cannot limit. A 10–30 A soft fault can run with the BQ BATFET above its 10 A / 1 s rating | BQ25798 §7.3.13.1.7 and Table 7-30. spec_power §0 decision 3 and §4.1.4 accept this but assume firmware. R5460 VDET3 table | Power + firmware | First battery power-up with amps (bring-up) | (a) Firmware contract: write SFET_PRESENT=1, EN_BATOC=1 and WATCHDOG=0 (or re-arm on every WD_FLAG), and verify the readback. (b) Bench: 20 mΩ PVDD short with blank firmware and with armed firmware. Record the trip time and peak IBAT, and check that U901 and U701 survive. (c) If blank-firmware behaviour is unacceptable, record the decision (lower R5460 VDET3 variant, smaller fuse, or restore a disconnect) before routing |
| **S2** | Should-fix (needs a footprint before placement) | charger Q701 / C720 / R710 | (1) The battery-connect inrush into ≈1.5 mF of PVDD plus the VSYS bulk is not bounded. Source-follower ramp ≈ I_SDRV/Crss = 50–100 nA / 15.5–30 pF (NCEP3065QU, 15 V; higher at low V_DS) gives 1.7–6.5 V/ms, or **2.5–9.7 A** through Q701, the BATFET (10 A for 1 s) and U901's body diode. The spec estimate of 3.8 A used 40 pF. (2) **The documented remedy, fitting C720 (10 nF gate–drain) alone, is unsafe** if SDRV is not actively held low while U701 is unpowered. At pack hot-plug the gate would couple to 8.4 × 10/(10 + 2.1 nF Ciss) ≈ 6.9 V, so Q701 turns fully on into the bulk and may trip the R5460 at power-up | NCEP3065QU Ciss 2100 pF, Crss 15.5/30 pF. BQ25798 §7.3.12: 100 nA, ≈50 % duty in battery-only mode. spec_power §4.1.4 and C720 note. SDRV state when unpowered is not stated in the datasheet | Power | **Placement** (add the footprint). Bring-up (value) | Add a DNP 0603 from SFET_G to CHG_BAT (gate–source) next to C720. Rule: C720 is fitted only with C_GS ≥ 5 × C720, or with R710. Bench: 10 pack insertions, scoped IBAT and SFET_G, peak < 6 A, no R5460 trip |
| **S3** | Should-fix | charger U701 (BQ25792); spec_power §2.3; charger sheet note | **The BQ25792 POR and watchdog default is ICHG = 2 A for 2S, not 1 A.** The spec and the sheet quote the BQ25798 value. Blank, hung or watchdog-expired firmware therefore charges at 2 A. That is 0.4C on the 5 Ah pack but **0.57C on the 3500 mAh fallback pack** (over the 0.5C rule). In over-discharge recovery (R5460 DOUT low, cells 3.0 to 3.2 V) the 2 A flows through Q801's body diode: ≈0.7 V × 2 A ≈ **1.5 W** for tens of minutes | BQ25792 ZHCSMD3C Table 9-2 (2S: ICHG 2 A, VSYSMIN 7 V, VREG 8.4 V). BQ25798 Table 7-2 gives 1 A. TI SLUSDG1C online edition gives the same 2 A | Power + firmware | First charge (bring-up). Layout copper for Q801 | Correct spec §2.3 and the charger note. Firmware sets ICHG at boot. If the 3500 mAh pack is used, record the watchdog policy. Layout: give Q801 copper for 1.5 W, and check the BATT_N island temperature against TH801 (it can trip the hot TS limit). Bench: deep-discharged pack recovery with a thermocouple on Q801 |
| **S4** | Should-fix (decide before routing) | ui_io J501; charger SW701/CHG_QON; UI board | No external hardware path reaches /QON. Ship-mode exit is by USB plug-in only. The 10 s full power reset (QON), and the only battery-side reset of a hung ESP32, need the enclosure opened (SW701 and SW101 are on the main board). `mech_envelope.md` §2 recommends wiring UI SW1 to CHG_QON through the FFC. The FFC has no such pin, and UI SW1 is on the ADC ladder | Netlist: CHG_QON = {U701.12, SW701.1}. spec_signal §4.2 J501 table. mech_envelope "Power button" row | System, UI and mech | Routing (FFC pinout, UI board) | Decision recorded. If adopted: reassign one J501 GND pin (19 or 20) to CHG_QON, put a button to GND only on the UI board (internal pull-up, no driven signal), and add ESD. Check: 1 s press exits ship mode, 10 s press resets the system |
| **S5** | Should-fix (unbounded corner) | usb_power Q601/Q602; mcu R104/R105 | At 400 kHz the bus may miss the Fast-mode tr ≤ 300 ns limit. Each line carries one AO3400A drain: Coss is 75 pF at 15 V and estimated 150–250 pF at 0–3.3 V. Add ESP32, BQ, 2× TAS and traces (≈50 pF), and tr = 0.847 × 2.2 kΩ × C gives **240 ns at 130 pF and 420 ns at 225 pF**. The spec assumed ≈100 pF. Same footprint, so placement is unaffected | AO3400A Coss is the vendor value at 15 V. Low-voltage Coss is not verified (estimate). spec_signal §1.5 | Signal | Bring-up (I2C at 400 kHz) | Compute from the AO3400A Coss(V) curve, or scope tr with VBUS absent and present. If > 300 ns: run 100–200 kHz, or fit a low-Coss SOT-23 N-FET (re-ratio R603/R604 if Vth(max) > 1.5 V) |
| **S6** | Should-fix (choose before placement) | battery JP803 / TH801 / J803 | The default build senses **board** temperature next to J801 (JP803 is a *Bridged12* footprint). Requirements and mech say the pack has no NTC, and a 10 kΩ NTC is bonded to the pack face and wired to J803. The pack sits on a tray 7 mm above the board, so the 2.0–60.8 °C charge window then does not track cell temperature. The BQ TS window governs charging only; nothing in hardware stops discharge on pack over-temperature | Netlist JP803 1–2 = TH801. mech_envelope J803 row. requirements "bonded 10 k NTC". BQ25798 §7.3.9.5 | Power and mech | **Placement** (footprint variant, J803/TH801 position) | Record the decision. If the pack NTC is the default, use `SolderJumper-3…Bridged23` (or open plus 0 Ω), place J803 at the pack-lead exit, and record the harness. Firmware: read TS in battery-only mode and stop playback above the pack limit |
| **S7** | Should-fix (procedural) | battery R810/R811, J802 | With the balance lead unplugged, R810/R811 hold BAL_MID at VBAT/2. The R5460 and both HY2213s then see half-pack voltages, so **cell-level OV/UV protection is silently lost**: 4.45 + 3.95 V reads as 4.2 + 4.2 V. There is no ADC on BAL_MID and no spare GPIO to detect it | Netlist BAL_MID. spec_power §3.3 "mid-tap bias" | Power and system | Assembly / first charge | Add an assembly step: check the balance lead is seated (meter at TP803 vs TP802). Record acceptance of the residual risk, or remove R810/R811 after checking the R5460 behaviour with VC floating |
| **S8** | Should-fix (before fab) | battery J801 footprint; pack harness | The J801 + = pad 2 mapping rests on the KiCad library silkscreen. The Amass drawing in hand (XT30PW-M p.2–3) has no legible polarity mark. The builder re-terminates the pack from EC3 to XT30 and no harness drawing exists. A reversed pack at J801 is destructive (body diodes, BQ BAT pin) | Footprint pads: 2 at x = −5 ("+" silk), 1 at x = 0. xt30-2/3.png | Mech and power | Fab release / assembly | Confirm against a physical XT30PW-M and mating female, or a dimensioned Amass drawing with polarity. Add a harness drawing (colour, + to pad 2) and "+"/"BATT" silk at J801 |
| **S9** | Should-fix (docs, R06) | spec_power, spec_signal, charger sheet note | Stale values that layout and firmware will read: spec_power decision 2 and §4.1.3/§4.1.4 still say R903 33 k / C915 47 nF and R907/D901 DNP. spec_signal §1.2 and §4.2 still give 33 Ω for R113/R114/R118, and §1.5 says EN τ = 10 ms (1 µF). The ICHG 1 A default is wrong (S3). SI sim S6 assumes a 200 mm FFC, but mech recommends 100 mm (conservative) | grep of the specs vs netlist values (§4.1.3 line 422–423, §4.1.4 line 443/471/473; spec_signal lines 73, 90, 97, 165) | Spec authors | Routing (layout notes) / firmware | Specs updated to the netlist values and version bumped. Diff of spec values against the netlist is zero |
| **S10** | Should-fix (production) | 11 DNP parts | The KiCad DNP attribute is unset. `--exclude-dnp` BOM/CPL and PCB DNP marking will include U501, J502, R601, … | BUILD_NOTES deviation 2. Netlist has no `dnp` property | Schematic owner | Production outputs | Set DNP in eeschema, re-export, and check that BOM/CPL counts equal 246 fitted parts |
| **S11** | Should-fix (placement constraint) | C301, C401, C920 (10 × 10.2 mm) | Mech allocates "the 470 µF bulk cap" to zone D (X ±6 mm, ≤24 mm). Amps sit in zone B (≤10 mm, so 10.2 mm parts do not fit). spec_signal wants C301/C401 between each amp's PVDD groups | mech_envelope §6 height table. spec_signal §3.6 | Layout and mech | **Placement** | Placement plan: C920 in D, C301/C401 in G (≤21 mm) on the PVDD feed, or move them to the bottom side. 3D check against the STEP envelope |
| L1 | Low | usb_power / charger | Without a PD contract, blank firmware lets the BQ draw up to ILIM_HIZ 2.7–2.9 A from any 5 V source (BC1.2 on D± is disabled, so it reads as "unknown, 3 A"), whatever the Type-C Rp advertises. VINDPM prevents collapse, but a 500 mA port may trip. VBUS sink capacitance ≈ 50 µF vs the 10 µF cSnkBulk guideline (accepted in the spec) | BQ25798 Table 7-4. spec_power §1.3/§2.3 | Firmware and power | Bring-up | Firmware writes IINDPM ≤ 0.5–1.5 A when CH224Q reg 0x09 shows no PD. Bench: laptop USB2 port, no shutdown |
| L2 | Low | C301/C401/C920 C2836436 | Rated ripple is only 286 mA at 120 Hz, life 2000 h at 105 °C, and ESR is unknown. The sim assumed 0.15 Ω (swept to 0.34 Ω) | LCSC listing (agent check) | Power | Bring-up | Bench: cap case temperature and PVDD ripple at full-power pink noise, or choose a low-ESR 105 °C part |
| L3 | Low | U201 CH340C | JLC marks C84681 "no longer manufactured". Replacement code C7464026 (same part, tape and reel) | JLC API 2026-11-24 | Production | Production BOM | Swap the LCSC field, or confirm the JLC pool stock at order time |
| L4 | Low | U201 | The CH340C's internal D+ pull-up is powered from +3V3 when VBUS is absent (battery operation with a cable to an unpowered host), which back-drives D+ | spec_signal §2.5 | Signal | — | Accept and record |
| L5 | Low | test access (H03) | No test points on I2C SDA/SCL, AMP_PDN, BOOST_EN, AMP_FAULT, SFET_G, I2S, or PVDD at the amp end. Only 3 GND points, all near the converters | Netlist TP list | Layout | **Placement** | Add pads (1.0 mm), each with a GND pad within 5 mm of the I2S and switch probes |
| L6 | Low | rails U901 pins 2/6; all analog returns | AGND and PGND are one net, `GND`. The single-point tie exists only as a note | Netlist | Layout | Routing | Net-tie footprint or a DRC rule area, reviewed at routing |
| L7 | Low | battery U801 | After an excess-discharge or short trip, release needs V− back below 0.2 V through the internal pull-down. The residual system load (dividers, BQ Iq) probably holds V− up, so the pack stays off until USB is connected or the pack is unplugged. Recovery exists (USB) | R5460 §VDET3 text | Power | Bring-up | Bench check during the S1 test. Document the recovery in the user notes |
| L8 | Low | ui_io R501–R504 | ENC_A/B/SW and BTN_ADC float if the FFC is out. Pull-ups are on the UI board only | Netlist | Signal | — | Accept, or have firmware ignore inputs until the UI board ID or display responds |
| L9 | Low (E02) | usb_power D601 | SMF24A clamp is 38.9 V at 5.1 A, above BQ VBUS abs max (30 V) and CH224Q VHV (32 V) for surge-level events. The hot-plug snubber is DNP on the "sources attach at 5 V" assumption | SMF24A, BQ, CH224 abs max | Power | — | Accept for ESD/hot-plug per spec, or evaluate SMF20A (VRWM 20 V) |

### Challenged or dismissed hypotheses (H04)

- **"R5460 excess-charge-current (V− < −0.2 V) trips while charging a deep-discharged pack through Q801's body diode (V− ≈ −0.7 V)."** Dismissed. Datasheet §VDET4: the detector is active only "when the battery pack is chargeable and discharge is also possible", i.e. both FETs on.
- **"The ADR/FAULT fault merge breaks the TAS5805M address straps."** Not a defect. The 1 MΩ to GND loads the 4.7 k / 15 k pull-ups by ≤1.5 %. Table 7-5 confirms 4.7 k to DVDD = 0x2C and 15 k = 0x2D. FAULTZ is a driven output (reg 0x61 = 0x0B, then 0x60 = 0x01). Bench closure: both addresses ACK.
- **"CH224Q on the TI DSQ0010A pattern is mis-oriented."** Dismissed. CH224 §9.2 top view puts pin 1 at bottom-left, 1–5 along the bottom, counter-clockwise, EP 1.5 × 0.9 parallel to the rows. Rotated 90° clockwise, that is the KiCad DSQ layout (pads 1–5 down the left at x = −1.0125, EP 0.9 × 1.5, pad 0.725 × 0.2 covering the 0.3 mm lead). Pin table 1 VHV … 10 PG, 0 = GND matches the symbol.
- **"Isolator gate overstress at 20 V PD."** Dismissed. Gate = VBUS/2 = 10 V < 12 V. Only 28 V EPR would exceed it, and that is forbidden in firmware.
- **"Pack with its own PCM in series: its protection is bypassed through the balance wires."** Dismissed for the default build. JP801/JP802 are open, so only the mid tap connects. Two PCMs in series each protect. Residual effect: ours may report a cell OV first.
- **"GPIO12 (AMP_PDN) breaks the WROVER-E 3.3 V flash strap."** Dismissed. R108 100 k to GND plus the internal pull-down. TAS PDN has no pull-up.

## 3. Boundary states exercised on the exported netlist

| State | Trace and result |
|---|---|
| **Dead or absent pack, USB attached** | CH224Q is powered from VBUS and presents Rd, then asks for 15 V. BQ comes up from VBUS. ILIM_HIZ clamps the input at 2.7–2.9 A. VSYS is held at ≥ VSYSMIN 7 V, so +3V3 comes up (UVLO 5.43 V) and programming works. *Absent pack:* Q701 turns on and VBAT_PACK = CHG_BAT ≈ VREG, so J801 pin 2 is live at ≤ 8.4 V. Harmless. *Over-discharged pack (R5460 DOUT low):* charge flows through Q801's body diode; V− ≈ −0.7 V signals the charger; release at 3.2 V/cell (F version); ≈1.5 W in Q801 at the 2 A default (S3). VDET4 stays inactive (dismissed above). With no battery, a high-power load can collapse VSYS (firmware must limit; deferred) |
| **Pack inserted, no USB** | U801 powers from VBAT_PACK through R801. U701 powers from BATP (100 Ω), and I2C is active above 3.4 V. Q701 is off at insertion, so only nF-range capacitance is hot-plugged at the XT30. SDRV then ramps Q701 as a source follower into VSYS and PVDD (through L901 and U901's body diode): 2.5–9.7 A, unbounded (S2). PVDD pre-biases to ≈ VSYS − 0.5 V with amps in PDN (R108) and the boost off (R107) |
| **Blank ESP32 firmware** | BOOST_EN = 0 (R107 plus 800 k internal). AMP_PDN = 0 (R108). PVDD ≈ 6–8 V, and the amps draw µA. AMP_FAULT = 0 (ADR pins high, both 2N7002 on). The charger runs on POR defaults: /CE low, **ICHG 2 A** (S3), VREG 8.4 V, TS window 2.0–60.8 °C, no JEITA tuning (ECO-001 item 6). IBAT_OCP is disarmed (S1). The CH224Q still negotiates 15 V by itself. Flashing works through the CH340C auto-reset (DTR/RTS on Q201/Q202, EN τ = 22 ms) |
| **USB attached while the ESP32 is off** | "Off" here means held in reset, or ship mode. In reset: +3V3 is up, so no domain is unpowered. The GPIOs go Hi-Z, so the pulls set the boost off and the amps in PDN. In ship mode: a VBUS plug-in exits ship mode (BQ25798 §7.3.12.2). In the window before VSYS comes up, the CH224Q internal 10 k pull-ups reach the unpowered +3V3 through Q601/Q602 and the 2.2 k pull-ups: ≈0.27 mA per line, the rail rises by tens of mV, and the I2C pins stay within DVDD + 0.5 V. Benign. With VBUS absent, the isolator gate is 0 V and the body diode is reverse-biased, so there is no CH224Q load on the bus. BQ SDA/SCL/INT are open-drain to the pull-up rail, so there is no sneak path |
| **Charger in ship mode** | SDRV_CTRL = 10 is accepted only with no adapter. Q701 is off, so VSYS, +3V3 and PVDD decay. Drain is ≈ 11–16 µA (BQ IQ_BAT_OFF) + 4–8 µA (R5460) + 2 × 2.5–3.5 µA (HY2213) + 4 µA (R810/R811) ≈ 25–35 µA: years on 5 Ah. **Exits:** USB plug-in (yes), QON ≥ 1 s (on-board SW701 only, S4), register write (impossible, host unpowered). After an R5460 over-discharge trip, the HY2213s and R810/R811 still draw ≈10 µA straight from the cells, so a cut-off pack left for more than about 1 year risks deep discharge (low) |
| **PVDD short** | Boost on, firmware armed: the U901 ILIM cannot stop current through the body-diode path, so IBAT_OCP 9.3 A opens Q701. Boost off or firmware blank: L901 → U901 body diode → short. Limits are only the R5460 at ≈40 A for 12 ms and F801. A soft 10–30 A fault can persist beyond the BATFET rating (S1). USB present: the BQ converter limits, VSYS_SHORT limits to 1 A, and the battery supplements through the BATFET (same as above). Recovery after an R5460 trip likely needs USB (L7) |
| **Pack with its own PCM in series** | Balance B−/B+ jumpers are open, so the pack PCM is never bypassed. If the pack PCM opens, BATT_N floats from the cell negative. Our R5460 and U802 then see BAL_MID − P−, which is undefined but current-limited by 330 Ω, 100 Ω and 1 MΩ. The lower-cell bleed returns through the pack PCM's body diode. No damage path found. A PCM pack's own NTC must be isolated two-wire to use J803 (B− ≠ GND) |
| **Watchdog or firmware crash** | ESP32 reset puts the GPIOs Hi-Z. BOOST_EN and PDN drop together, not PDN first (possible pop; acceptable). With the I2S clock lost, the TAS clock-fault auto-Hi-Z applies. BQ watchdog expiry (40 s) restores ICHG 2 A, VREG 8.4 V and EN_BATOC = 0 (S1, S3). A stuck CH224Q on the bus is cleared by unplugging USB (isolator off): an independent path |
| **Low or weak source** | 5 V from a 500 mA port: BQ VINDPM holds the bus, and the battery supplements play-while-charging. Blank firmware over-draws (L1) |
| **Cold start** | Charging is suspended below 2 °C (TS). Discharge has no hardware temperature limit (S6) |
| **Overvoltage applied to an already powered bank** | A non-compliant source at 15–20 V at insertion rings onto VBUS with the snubber DNP. The TVS clamp exceeds abs max at surge currents (L9) |

## 4. Known-good checks

- **ERC (R04):** 0 errors and 0 warnings across all 10 sheets at all severities. There are no exclusions. The project file has no ERC overrides; the ignored checks are the KiCad 10 defaults (single global label, four-way junction, SPICE model, footprint filter). Known masking: CH340C V3 is power_out on +3V3. The +3V3 source (L951.2, the FB divider) was confirmed in the netlist instead. PWR_FLAGs exist only on genuine sources.
- **Netlist (R05):** 179 nets with no single-node nets. The only nets with ≤1 fitted node are the intentional DNP variant nets (VBUS_SNUB, I2S_EXT_*, I2S_SEL, D951-A). An algorithmic comparison of amp_left and amp_right is identical except for the intended ADR value (4.7 k / 15 k) and the net prefixes.
- **Symbol pins against footprint pads (L01):** all 257 references checked by script. Every symbol pin has a pad. The only extra pads are the WROVER-E NC pads 17–22, 27, 28 and 32 (flash/PSRAM, correctly left without a net).
- **Custom symbols against datasheets:**
  - TPS61178 1–13: names and numbers match SLVSDA7E §6.
  - CH224Q 1–10 plus EP: matches CH224 Table 4-1.
  - R5460 SOT-23-6 (1 DOUT, 2 COUT, 3 V−, 4 VC, 5 VDD, 6 VSS): matches.
  - HY2213 (2 VDD, 3 VSS, 6 OUT, 1/4/5 NC): matches. -BB3A = N-FET drive, active high, VCU 4.200 V.
- **Footprints against dimensioned drawings (L02):**
  - RNW0013A matches the TI example layout exactly: 10 × 0.7 × 0.25 pads at x = ±1.6 and 0.5 mm pitch, pin 1 top-left, 13 top-right; bars 0.25 × 3.4 at 0.55 mm pitch with 6 nearest pins 1–5; 3 paste apertures per bar (≈88 %). One deviation: TI specifies solder-mask-defined bars, and ours are copper-defined. That is acceptable at 0.30 mm copper gap.
  - 2410 fuse: 1.96 × 3.15 pads, 2.95 gap, 6.86 overall = Littelfuse 451 recommended.
  - TAS5805M PWP0028M: 3.4 × 9.7 EP, mask 3.1 × 4.05, matches TI.
  - WROVER-E (vendored): 38 × 1.5 × 0.9 pads at 1.27 mm pitch, rows 17.5 apart, 3 × 3 thermal array, antenna keep-out zone, all matching Espressif Fig. 15.
  - CH224Q on DSQ0010A: see §2.
- **Polarities:** D601 K = VBUS, D901 K = TRIM_K, D701/D101/D951 cathodes correct, C301/C401/C920 + = PVDD, Q701 body diode blocks battery → system, the Q801/Q802 common-drain orientation is correct for low-side protection, and COUT's low level is the V− rail.
- **Straps and boot (I01):** IO0 has a 10 k pull-up with the LED in parallel (reads 1). IO2 = BOOST_EN, 100 k pull-down. IO12 = AMP_PDN, 100 k pull-down (3.3 V flash). IO5 and IO15 have internal pull-ups. GPIO16/17 (PSRAM) and 6–11 (flash) are unused. Input-only pins 34/35/36/39 are used as inputs only. ADC use is on ADC1 only (GPIO39).
- **Values:** buck 3.300 V, UVLO 5.43 / 4.82 V, SS 4.8 ms. Boost 17.97 V (OVP 20.5 V minimum), ILIM 6.3–9.2 A, fsw 599 kHz. ILIM_HIZ 2.72–2.89 A. TS window 2.0 / 60.8 °C recomputed (open NTC reads cold and suspends; short reads hot and suspends). PROG 8.2 k = 2S at 750 kHz. Every capacitor's voltage rating has ≥ 2× headroom except PVDD C920/C301/C401 (35 V at 18 V; OVP 21 V).
- **Footprint geometry at a level that would affect placement:** no mismatch found.
- **Supply (L04):** all 34 high-risk LCSC codes resolve to the expected MPN and package, with normal lifecycle and stock ≥ 796 (2026-11-24). Exceptions: L3 (CH340C) and L2 (ripple rating).
- **ECO-001 (H05):** the 8 changed fields are present in the netlist (R903 100 k, C915 15 nF, R907/D901 fitted, R113/R114/R118 68 Ω, C103 2.2 µF), and connectivity is otherwise unchanged.

## 5. Deferred: bench, firmware and layout verification

**Firmware contract (I11):**
- BQ: SFET_PRESENT = 1, EN_BATOC = 1, WATCHDOG policy, ICHG ≤ 2.5 A (≤ 1.75 A for 3500 mAh), IINDPM from CH224Q 0x50 (≤ 3 A) or ≤ 1.5 A without PD, AUTO_INDET_EN = 0, JEITA warm ≤ 45 °C, TS readout in battery-only mode.
- Boost: trim high before BOOST_EN, then ramp down (ECO-001), wait ≥ 20 ms, then PDN. PDN low before BOOST_EN low.
- TAS: probe 0x2C/0x2D, then the FAULTZ configuration. Ignore AMP_FAULT until both amps are configured.
- Mandatory tweeter limiter.
- IO0 open-drain only.
- espefuse 3.3 V flash.
- Do not request 28 V EPR.

**Bench, first article:**
- S1 short test.
- S2 inrush capture.
- S3 deep-discharge recovery with Q801 temperature.
- S5 I2C rise time.
- L1 weak-source test.
- L2 capacitor temperature and ripple.
- L7 R5460 recovery.
- Boost startup overshoot with and without the trim soft start.
- PVDD load step 0.5 → 2.5 A at 7.4 V (not simulated; ECO-001 "not done").
- Both amp addresses ACK.
- Pack 6 A continuous (B01).
- HY2213 bleed temperature.
- Antenna range in the enclosure.

**Layout (H02):**
- BATT_N copper island and net-class clearance.
- Kelvin FB from C906.
- AGND single point (L6).
- Hot loops: U901 SW–VOUT–PGND < 5 mm; BQ PMID/SYS.
- Bootstrap capacitors with no vias.
- High-current paths: PACK_P/BATT_N/PROT_D 7 A continuous, 10 A peak.
- Thermal copper for U901, L901, U701, Q801 (1.5 W, S3), and R805–R809.
- Antenna: no copper for enclosure X < −75 on any layer; the module overhangs the edge by 4 mm.
- USB D± 90 Ω.
- The 0.4 mm DFN.
- Via-in-pad on the TAS EP and the U901 bars (plugged or tented; JLC capability to confirm).

**Fab and CAM (L05, H05):**
- THT parts: XT30, VH ×4, XH, PH, USB-C shell stakes. This needs JLC standard PCBA.
- NPTH holes near the antenna.
- USB-C tab outline.
- CPL rotation of the DFN, VQFN-HR and WROVER parts.
- A DNP-aware BOM (S10).
- Final DRC and the 3D/height check against `mech/concept` STEP (S11).

## 6. Coverage ledger

Status values: V = verified, O = open (register), D = deferred to layout/firmware/bench, U = unverified, N/A = inapplicable.

| ID | Status | Evidence and limits |
|---|---|---|
| R01 | V | §1 baseline. Snapshot hashed, exports regenerated from the snapshot |
| R02 | V with O | Traced: stereo 2-way bi-amp (2 × TAS5805M BTL A/B); PVDD 18 V, 15 W woofer (DRC 15.5 V pk) and 8 V pk tweeter limiter; A2DP/Wi-Fi on WROVER-E N8R8; PD sink, play-while-charging, flashing (CH340C); encoder, 3 buttons, display, PDM mic over the FFC; 2S pack with protection, balancing, NTC. USB audio is not implemented (I2S_EXT header provision only). The fuel gauge is replaced by the BQ ADC (decision recorded in spec §7). The runtime of 8 h is an estimate only (mech ≈3.3 W). Open: the power on/off UX (S4) |
| R03 | V | All 10 pages rendered and viewed at 110 dpi. Text is legible and title blocks are filled through the drawing sheet. Plain bus crossings are noted on the root. No clipped text found |
| R04 | V | 0 violations, no exclusions, default rule set. The +3V3 masking caveat was checked through the netlist |
| R05 | V | XML netlist parsed. Critical paths traced by physical pin (battery, charger, rails, USB, MCU, amps). No single-node nets. Channel symmetry checked by script |
| R06 | O | S9 (stale specs), S3 (ICHG note), S6 (NTC default vs mech/requirements), S4 (mech recommendation not implemented) |
| L01 | V | Script check of all 257 references. Custom symbols matched to datasheets |
| L02 | V with O | RNW0013A, 2410, PWP0028M, WROVER, DSQ/CH224Q compared to drawings. XT30 polarity is unverified (S8). Stock passive, SOT and connector footprints were accepted as KiCad library without a per-part drawing check (U) |
| L03 | V with O | Stored `out/` BOM regenerated at 16:53 and matches the netlist values, including ECO-001. DNP attribute open (S10). Cable pin order: FFC n ↔ 21 − n is documented. Pack harness undocumented (S8) |
| L04 | V | LCSC/JLC check 2026-11-24 (see L3). Stock is fine for 5 boards |
| L05 | D | THT, via-in-pad, NPTH and antenna overhang listed in §5. CAM/CPL not yet available |
| L06 | O | S11 tall capacitors. Other heights fit the mech zones (XT30 8.5 mm in G, VH 11.5 mm in G, WROVER and inductors ≤ 4 mm) |
| P01 | V | §3 states traced, including back-voltage (J801 live from the charger with the pack absent, the R603/R604 VBUS bleed) |
| P02 | V (estimate) | 40 W at Vin 6 V gives 8.5 A peak, against ILIM 6.3–9.2 A and battery ≤ 6 A RMS (spec). Limiter mandatory (sim S2). Synchronized PWM peaks vs average were not separately computed (U) |
| P03 | V | Headroom: VSYS 6.0–8.6 V vs buck UVLO 4.82 V, boost Vin ≥ 2.7 V. CH224Q VIH max 3.3 V vs a 3.33 V bus (abs max 6.5 V, fine). TAS PVDD ≤ 21 V OVP < 26.4 V |
| P04 | V with O | Compensation per ECO-001 (sim PM ≥ 79°). Effective capacitance: PVDD ceramics 4.5 µF each at 18 V. Electrolytic ESR/ripple open (L2). Output LC caps at 9 V bias ≈ 0.6–0.7 µF (sim used the nominal value; low impact) |
| P05 | O | S2 battery-connect inrush; L1 VBUS sink capacitance; L9 hot-plug |
| P06 | O | S1 over-current protection depends on firmware. Reverse pack is prevented only by connector keying (S8) |
| P07 | D | Spec §6 budget (U901 ≈ 2.5 W worst, U701 1.5 W, path 1 W, balancers 0.6 W) plus Q801 1.5 W (S3). The thermal sim covers the board; the layout carries this |
| P08 | V with O | EN RC 22 ms, straps, reset order, retained PVDD charge with the boost off. The QON exit is internal only (S4) |
| P09 | V | Domain crossings: CH224Q isolator, CH340C/ESP/TAS all on one rail, PVDD_TRIM diode-blocked, BQ open-drain; §3 |
| P10 | D | Bypass values match vendor guidance. Placement rules exist in spec §6 and the sheet notes. Geometry is checked at layout |
| B01 | V with D | Gens ace 2S 5 Ah (no PCM, no NTC): 8.4 V, 0.5C, 10 % swell bay. 6 A continuous rating not published (bench) |
| B02 | O | Defaults audited: ILIM_HIZ wins below IINDPM, PROG, /CE, TS. ICHG POR = 2 A (S3). EN_BATOC watchdog reversion (S1) |
| B03 | V (estimate) | 2.5 A CC on 5 Ah ≈ 1.7 h + CV ≈ 2.5–3 h. Input 15 V × 2.8 A ≫ charge plus idle. Estimate only |
| B04 | O | Window, open and short faults verified. Board vs pack sensing (S6). No discharge-temperature cutoff in hardware |
| B05 | O | R5460 OV/UV 4.29/3.00 V (F version needs a charger to release), excess current ≈ 40 A, recovery path. S7 balance-lead absence. L7 latch |
| B06 | O | PD 15 V, I2C reg map, detach. Non-PD draw (L1). EPR forbidden |
| I01 | V | Supply, straps, reset, PSRAM/flash pins, input-only pins. WROVER-E (ESP32 V3 silicon) errata: GPIO36/39 glitch handled by the pin allocation |
| I02 | V (paper) | I2S1 TX 3.072 MHz on the GPIO matrix. I2S0 PDM RX on GPIO32/33. VSPI on IOMUX pins 18/23/5 for 40 MHz (sim fmax ≈ 53 MHz with 68 Ω). LEDC for TRIM and BL. I2C 400 kHz rise time open (S5) |
| I03 | V | USB-C to CH340C auto-reset (sim S5), TP101–104, BOOT/RESET buttons. Rear USB port reachable |
| I04 | V | USB D± with USBLC6 (VBUS pin to +3V3), CC on a separate USBLC6, no stubs, 470 Ω UART series |
| I05 | O | 2.2 k pull-ups, addresses 0x22/0x23, 0x2C, 0x2D, 0x6B with no conflict. Rise time (S5). Stuck-bus recovery by bit-bang, or a USB unplug for the CH224Q |
| I06 | V | BTN ladder on ADC1 GPIO39 at 12 dB, 1 k + 10 nF τ = 10 µs. Thresholds in the UI spec |
| I07 | V | Speaker BTL outputs (no terminal to GND), LC 10 µH/1 µF (sim S2), limiter mandatory, LEDs ≈ 2 mA |
| I08 | N/A | No matrix or array (ladder plus a quadrature encoder) |
| I09 | D | Antenna keep-out in the footprint plus mech plan (−X overhang, no copper for X < −75). Range test deferred |
| I10 | V with O | FFC hot-plug through 1 k series resistors. Floating inputs (L8) |
| I11 | D | Contract listed in §5. Owner: firmware |
| H01 | D | Outline 180 × 46 mm, origin, 6 holes with board-local coordinates (second point checked: (86, 12) → (176, 33)), zones and connector positions in `mech_envelope.md` §6 |
| H02 | D | Classes and constraints listed in §5 and spec §6 |
| H03 | O | L5 |
| H04 | V | This register plus the dismissed hypotheses |
| H05 | D | ECO-001 re-checked. Physical DRC, CAM and paste come later |
| E01 | V with O | Grades: −40/85 °C or better for all ICs. The electrolytic is 105 °C 2000 h (L2). X5R near hot parts: check at layout |
| E02 | O | L9 VBUS surge. Speaker and FFC exposure is internal |
| E03 | D | Hobby build. Uses a pre-certified module (WROVER-E). A purchased pack carries UN38.3. No mains or hazardous voltage. EMC not assessed |
| E04 | V with O | Safe state on crash or reset through hardware pulls. A lost bus has an independent path (USB unplug for the CH224Q). Hung firmware with battery only and no USB has no external reset path (S4) |

**Areas a desk review could not establish:**
- Actual inrush, short-circuit and thermal behaviour (S1, S2, S3).
- AO3400A low-voltage Coss (S5).
- SDRV pin state when the BQ is unpowered (S2).
- XT30 physical polarity (S8).
- Electrolytic ESR and ripple heating (L2).
- Antenna performance.
- Pack continuous current.
- PVDD load step at 7.4 V.
- Stock passive and connector footprints, not drawing-checked one by one.
- Layout, CAM and CPL artefacts, which do not exist yet.
