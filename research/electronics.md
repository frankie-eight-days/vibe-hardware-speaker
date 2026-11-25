# Electronics Parts Research: Portable Stereo BT Speaker

Status: research v1, 2026-11-24. Scope: main PCB (JLCPCB PCBA, LCSC parts) per `docs/requirements.md`.

**How stock and price were checked:** live queries to the JLCPCB parts-library API (`jlcpcb.com/api/.../selectSmtComponentList`) on 2026-11-24. "Stock" is JLC's assembly inventory, which is what PCBA draws from. "$@10" is JLC's unit price for the 10–29 tier (or the first tier if that's higher). **B** = JLC Basic, **E** = Extended. None of the ICs is Basic. Stock moves daily, so re-check before ordering. A board needs 2 of some parts, so 5 boards need 10.

Datasheet links: TI parts use `https://www.ti.com/lit/ds/symlink/<part>.pdf`. Other parts link to their LCSC product page, `https://www.lcsc.com/product-detail/<Cxxxx>.html`, which carries the PDF.

---

## 0. Architecture verdict (changes vs. the assumed block diagram)

The assumed architecture holds: ESP32 classic → I2S → 2× TAS5805M (one per side, bi-amped) → boost to 19–20 V, 2S pack with USB-C PD. The changes and constraints:

1. **I2S peripheral swap.** On the classic ESP32, PDM RX exists only on **I2S0**. Put the PDM mic on I2S0 and the amps on **I2S1** (std TX). The block diagram currently shows the reverse.
2. **The charger is a buck-boost NVDC charger with integrated FETs (BQ25792/BQ25798),** fed by a separate PD sink (CH224Q). The charger has no PD engine, so the PD chip stays. The BQ2579x includes a 16-bit ADC (VBUS/IBUS/VBAT/IBAT/VSYS/TS), so **no separate fuel gauge**: coulomb-count in firmware.
3. **Battery current ceiling.** The BQ2579x BATFET is rated **6 A RMS continuous, 10 A peak (≤1 s), with IBAT_OCP at 9.3 A** (datasheet §6.3/6.5). Every load including the boost hangs off VSYS. So the boost's input current limit plus amp DRC must keep average battery current at or below ~6 A (≈40 W into the boost at 6.5 V). That still covers 2×20 W + 2×5 W **program** material, but not 60 W of sustained clipping. Don't bypass the BATFET by hanging the boost on BAT: it breaks the charger's current regulation and termination.
4. **Woofer impedance should be 6–8 Ω, not 4 Ω.** TAS5805M OCP is 5 A (datasheet §8.1.2). At PVDD 19–20 V, a 4 Ω load can hit 4.75–5 A peak at clipping and trip OCP. With 8 Ω at 19–21 V the part gives 20–23 W/ch at 1 % THD, which meets the 15–20 W woofer target. Feed this into the driver selection (requirements §7).
5. **The 8 h runtime target is marginal with 2×3000 mAh 18650s** (≈6.7 h estimated at moderate volume, §12). It needs either 21700s or ≥3500 mAh 18650s, *or* the firmware power measures in §12 (dynamic PVDD, display/Wi-Fi idle-off).
6. **Use a module with PSRAM** (WROVER-E). AAC sink support in ESP-IDF v6.x hands undecoded frames to the app (external-codec path), so the AAC decoder, Wi-Fi web UI and LVGL all compete for internal SRAM. PSRAM costs GPIO16/17. The pin budget still closes (§1.3).

---

## 1. Bluetooth / MCU

**Decision (team lead, 2026-11-24): ESP32-WROVER-E with PSRAM.** The firmware research found that Espressif's audio framework says BT and Wi-Fi can't coexist in an audio app without PSRAM, and without it there's no RAM left for the web UI and LVGL. **GPIO16/17 are used by PSRAM and are excluded from the pin plan.**

WROVER-E family on JLC, 2026-11-24 (all Extended; module is 18×31.4×3.2 mm, ESP32-D0WD-V3; PSRAM is 8 MB with 4 MB directly mappable):

| Part | LCSC | B/E | Stock | $@10 | Flash / PSRAM | Antenna | Notes |
|---|---|---|---|---|---|---|---|
| ESP32-WROVER-E-N4R8 | C967023 | E | 1,571 | 4.25 | 4 MB / 8 MB | PCB | 4 MB is too small for 2× OTA + web-UI FS + AAC; also pricier than N8R8 |
| **ESP32-WROVER-E-N8R8** | **C2973667** | E | **3,808** | **3.73** | 8 MB / 8 MB | PCB | **Pick.** Cheapest and enough: 2× 3 MB OTA + ~1.9 MB LittleFS |
| ESP32-WROVER-E-N16R8 | C529589 | E | 6,524 | 5.20 | 16 MB / 8 MB | PCB | Same footprint fallback, highest stock |
| ESP32-WROVER-IE-N8R8 | C701351 | E | 1,327 | 4.38 | 8 MB / 8 MB | U.FL (IPEX) | Use if the antenna would sit under the metal grille |
| ESP32-WROVER-IE-N16R8 | C701352 | E | 2,642 | 4.82 | 16 MB / 8 MB | U.FL | |
| (C529587 N4R8, C529588, C701347, C701349, C2973645/46, C6552379) | | E | 0–1 | | | | Duplicate/old listings, no stock |

Other modules considered earlier, for reference:

| Part | LCSC | B/E | Stock | $@10 | Pkg | Notes |
|---|---|---|---|---|---|---|
| ESP32-WROOM-32E-N8 | C701342 | E | 26,182 | 4.04 | 18×25.5 mm | 8 MB flash, no PSRAM (rejected) |
| ESP32-WROOM-32E-N16 | C701343 | E | 21,769 | 4.50 | 18×25.5 mm | 16 MB flash, no PSRAM |
| ESP32-WROOM-32E-N8R2 | C5361945 | E | 2,582 | 4.36 | 18×25.5 mm | 2 MB in-package PSRAM (D0WDR2-V3); IO16 used by PSRAM |
| **ESP32-WROVER-E-N8R8** | **C2973667** | E | 3,808 | **3.73** | 18×31.4 mm | 8 MB flash + 8 MB PSRAM (4 MB mappable); GPIO16/17 used by PSRAM |
| ESP32-WROVER-E-N16R8 | C529589 | E | 6,524 | 5.20 | 18×31.4 mm | Drop-in fallback, 16 MB flash |
| ESP32-WROOM-32UE-N4 | C701344 | E | 9,512 | 3.58 | 19.2×18 mm | U.FL antenna variant. Consider it if the antenna must sit inside a metal grille |

Datasheets: [WROVER-E](https://www.espressif.com/sites/default/files/documentation/esp32-wrover-e_esp32-wrover-ie_datasheet_en.pdf), [WROOM-32E](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf).

**1.1 Is PSRAM worth it?** Yes. BT Classic plus Wi-Fi coexistence with Bluedroid leaves roughly 100–150 KB of usable internal heap. LVGL at 240×240×16 bpp needs 115 KB for one full frame (partial buffers work, but they're tight). The AAC decoder needs tens of KB plus buffers. With PSRAM you can put LVGL buffers, LwIP/Wi-Fi buffers and the web-UI assets there. WROVER-E-N8R8 is also *cheaper* at qty 10 than WROOM-32E-N8. The costs are 6 mm more length and losing GPIO16/17.

**1.2 AAC/aptX alternatives on LCSC.** None stocked. Qualcomm QCC3034/3040, BK3266 and Feasycom FSC-BT1026 all show 0 stock or sourcing-only. ESP-IDF v6.x includes an `a2dp_sink_stream_aac` example (external-codec path, `BT_A2DP_USE_EXTERNAL_CODEC=y`, ≥2 SEPs), so AAC on the ESP32 is a firmware task. aptX is out of scope per the requirements.

**1.3 GPIO budget on WROVER-E** (22 usable GPIO plus UART0). Allocation: I2S1 TX (BCLK, LRCK, DOUT) = 3. PDM on I2S0 (CLK, DATA) = 2. I2C = 2. LCD SPI (SCLK, MOSI, CS, DC) + BL PWM = 5 (tie LCD RST to an RC or the shared reset). Encoder A/B/SW = 3 on input-only GPIO34/35/36 with external pull-ups. Buttons = 1 ADC resistor ladder on GPIO39. Amp PDN (shared) = 1. Amp FAULT (shared open-drain) = 1. Charger INT = 1. Boost EN = 1. **Total 20.** Keep GPIO12 low at boot (flash-voltage strap) and leave GPIO0 for BOOT.

**Recommendation: ESP32-WROVER-E-N8R8 (C2973667),** with N16R8 (C529589) as the same-footprint fallback. If enclosure tests show the PCB antenna is shielded by the grille, switch to WROVER-IE-N8R8 (C701351) on the same footprint. GPIO16/17 must stay unconnected; they are PSRAM.

---

## 2. Amplifiers (I2S + DSP)

| Part | LCSC | B/E | Stock | $@10 | Pkg | Power (datasheet) | DSP | Notes |
|---|---|---|---|---|---|---|---|---|
| **TAS5805M** (TAS5805MPWPR) | **C478472** | E | **2,244** | **1.51** | HTSSOP-28 PowerPAD | 2×23 W 8 Ω @21 V 1 %; 2×21 W 6 Ω @18 V 1 % (25 W @10 %); PBTL 45 W 4 Ω | 15 BQ/ch, 3-band 4th-order DRC, full-band AGL, THD manager, input mixer + crossbar, level meter, 96 kHz | OCP 5 A; PVDD 4.5–26.4 V; Hybrid modulation idle 16.5 mA @13.5 V; RθJB 8.2 °C/W |
| TAS5806M (TAS5806MDCPR) | C2866082 | E | 130 | 2.60 | HTSSOP-38 | Same class as 5805M | Similar | Low stock |
| TAS5825M (TAS5825MRHBR) | C471049 | E | **29** | 2.37 | VQFN-32 5×5 | 38 W 8 Ω | More BQs, higher OCP | Stock too low for 10 pcs plus spares |
| TAS5827 (TAS5827RHBR) | C22428298 | E | 1,836 | 4.11 | VQFN-32 5×5 | 2×47 W 6 Ω, 2×55 W 4 Ω | DSP plus **Class-H envelope-tracking output** (can steer the boost rail) | Good v2 upgrade for battery life; QFN is harder to rework |
| TAS5828M (TAS5828MDADR) | C5214953 | E | 88 | 2.19 | HTSSOP-32 | 2×50 W 4 Ω | DSP | Low stock |
| MA12070P (Infineon) | C538534 | E | 51 | 5.44 | QFN-64 9×9 | 2×80 W 4 Ω (26 V) | Volume/limiter/power-mode profiles, no general biquad EQ | Low stock, filterless; would need crossover/EQ on the ESP32 |

Datasheets: [TAS5805M](https://www.ti.com/lit/ds/symlink/tas5805m.pdf), [TAS5825M](https://www.ti.com/lit/ds/symlink/tas5825m.pdf), [TAS5827](https://www.ti.com/lit/ds/symlink/tas5827.pdf), [MA12070P (LCSC)](https://www.lcsc.com/product-detail/C538534.html).

**Configuration.** Use 2× TAS5805M in **BTL**: amp L has ch A = woofer L and ch B = tweeter L; amp R likewise. Both amps share one I2S1 bus (BCLK/LRCK/SDIN, no MCLK needed). Each amp's input mixer routes the same I2S slot (L or R) to both of its channels. Each channel gets its own crossover (LR4 = 2 BQ), driver EQ (≈8–10 BQ) and DRC/limiter, which leaves 3–5 spare BQs per channel. Set I2C addresses with the ADR resistor: 4.7 k → 0x2C, 15 k → 0x2D (7-bit). Coefficients load at runtime over I2C via book/page writes (datasheet §7.6). Do it in deep-sleep/Hi-Z, or use the documented on-the-fly BQ update sequence.

**Output filter.** Ferrite-bead-only filters are only for PVDD ≤ ~14 V. At 19–20 V use an **LC filter: 10 µH + 0.68 µF** per output leg, 4 legs per amp, so 8 inductors per board. At 384 kHz/24 V, a 4.7 µH inductor gives a 6 A start-up peak, above OCP. Use 10 µH, or Fsw = 768 kHz (datasheet Table 8-1). The inductor needs Isat > 5 A.

| Filter part | LCSC | B/E | Stock | $@10 | Specs |
|---|---|---|---|---|---|
| **Sunlord MWSA0603S-100MT** | **C132141** | E | 13,688 | 0.079 | 10 µH, Irms 4.5 A, Isat 5.5 A, 67 mΩ, 7×6.6 mm |
| cjiang FXL0630-100-M | C167223 | E | 408,952 | 0.095 | 10 µH, 4.5 A / 5.5 A, 68 mΩ, 7×6.6 mm (best stock) |
| Sunlord MWSA0605S-100MT | C408467 | E | 4,196 | 0.18 | 10 µH, 4.5 A / 5.3 A, 60 mΩ |
| Bourns SRP7028A-100M | C2687402 | E | 2,736 | 0.66 | 10 µH, 3.5 A / 6 A, 75 mΩ |
| Filter cap 0.68 µF 50 V X7R 0805 (CCTC) | C282780 | E | 11,459 | 0.014 | Basic alternative: 1 µF 50 V X7R 0805 **C28323 (B)**, which saves an extended slot at the cost of slightly higher idle current |

**PVDD decoupling (per amp):** 2× 10 µF 50 V X5R 1206 **C13585 (Basic)** + 100 nF, plus one shared bulk 470 µF 25 V electrolytic (C2895277, E, 6,231, $0.13) or a 330 µF 25 V polymer.

**Thermal.** PowerPAD to a 4-layer ground pour with a ≥ 4×5 via array (RθJA ≈ 24 °C/W on a JEDEC board). Music at a −10 dB crest factor keeps dissipation under ~1 W per amp. Sustained full-power pink noise is limited by DRC and thermal foldback.

**Recommendation: TAS5805MPWPR ×2 (C478472)** plus FXL0630-100-M or MWSA0603S-100MT ×8, with 6–8 Ω woofers. TAS5827 is the step-up if a later revision wants Class-H rail tracking.

---

## 3. Battery: 2S charger, power path, protection, balancing, gauge

### 3.1 Charger with power path

| Part | LCSC | B/E | Stock | $@10 | Pkg | Key specs | Verdict |
|---|---|---|---|---|---|---|---|
| **BQ25792RQMR** | **C2862876** | E | 6,484 | **1.79** | QFN-29 4×4 | 1–4S **buck-boost NVDC**, 3.6–24 V in (30 V abs), 5 A charge, IINDPM 0.1–3.3 A, 4 integrated FETs + 11 mΩ BATFET, I2C, 16-bit ADC, dual input, BC1.2/HVDCP on D+/D− | **Pick.** Charges 2S from 5 V *or* PD 9–20 V with play-while-charging |
| BQ25798RQMR | C2876593 | E | 6,942 | 2.56 | QFN-29 4×4 | Same plus MPPT and backup mode | Same footprint, fallback. TI EVM/app notes target 98 |
| BQ25713RSNR | C2878935 | E | 499 | 5.01 | QFN-32 | NVDC buck-boost *controller* (4 external FETs + 2 sense resistors) | More parts, more layout risk |
| BQ25887RGER | C2761614 | E | 401 | 4.63 | QFN-24 | 2S **boost** charger 3.9–6.2 V in, 2.2 A, cell balancing | 5 V only (~15 W), wastes PD |
| Injoinic IP2326 | C2832094 | E | 12,476 | 0.52 | QFN-24 | 5 V → 2S boost charger, 1.5 A, balancing | No power path, no PD, no I2C. Cheap fallback only |
| Injoinic IP2365 | C2763591 | E | 5,739 | 0.62 | QFN-24 | 1–4S *buck* charger 5–26 V, 3 A, I2C | Can't charge 2S from 5 V; English docs are thin |

Datasheets: [BQ25792](https://www.ti.com/lit/ds/symlink/bq25792.pdf), [BQ25798](https://www.ti.com/lit/ds/symlink/bq25798.pdf), [BQ25887](https://www.ti.com/lit/ds/symlink/bq25887.pdf), [BQ25713](https://www.ti.com/lit/ds/symlink/bq25713.pdf), [IP2326](https://www.lcsc.com/product-detail/C2832094.html).

**Notes.**
- Set the VSYSMIN cell count to 2S (via the PROG resistor).
- Charge current: about 2 A for 2×3000 mAh, 2.5–3 A for 21700s.
- Put the cell NTC on the TS pin.
- Leave the BQ D+/D− pins unconnected, because the USB data pair goes to the USB-UART. Firmware sets IINDPM from the CH224Q's reported current over I2C. The VINDPM loop protects weak 5 V sources automatically.
- ADC IBAT discharge sensing (EN_IBAT) provides the coulomb counter.
- Charger loss at 15 V in, 8.4 V/2 A charge plus 1 W system is ≈1.2–1.5 W. That's the second thermal hotspot during charge-while-play.

### 3.2 2S protection and balancing (user-supplied cells, so protection must be on the main PCB)

| Part | LCSC | B/E | Stock | $@10 | Pkg | Specs |
|---|---|---|---|---|---|---|
| **Ricoh/Nisshinbo R5460N212AF** | **C259717** | E | 2,770 | 0.29 | SOT-23-6 | 2S: OV 4.29 V (rel 4.05), UV **3.00 V** (rel 3.20), excess-discharge 0.200 V, short-circuit, delays 1 s / 128 ms / 12 ms / 8 ms ([datasheet](https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_Ricoh-Elec-Devices-R5460N208AA-TR-FE_C259714.pdf), selection table) |
| R5460N208AA | C259714 | E | 2,815 | 0.34 | SOT-23-6 | OV 4.25 V, UV 2.40 V. Only 50 mV above the 4.20 V charge voltage, so an imbalanced pack trips it. Second choice |
| BQ7718xx | C555148 | E | 2,674 | 0.35 | WSON-8 | 2–5S *secondary* OVP only (no UV/OC) |
| BQ29209DRBR | C139352 | E | 386 | 0.88 | SON-8 | 2S OVP + balancing, secondary only |
| **HYCON HY2213-BB3A** (×2, one per cell) | **C113632** | E | 5,506 | 0.13 | SOT-23-6 | Single-cell balancer, bleeds above 4.19 V through an external resistor (≈68 Ω → ~60 mA) |
| **NCE NCEP3065QU** (×2, back-to-back CHG/DSG) | **C502964** | E | 15,127 | 0.55 | DFN3.3×3.3 | 30 V N-FET, 1.9 mΩ @10 V. Gate is driven from pack voltage (6–8.4 V) |
| AON7410 (budget alt) | C269266 | E | 9,879 | 0.09 | DFN3×3 | 30 V, 20 mΩ @10 V. Too lossy at 6 A (0.7 W per FET); rejected |
| **Littelfuse 0451010.MRL** pack fuse | **C44479** | E | 19,746 | 0.24 | 2410 | 10 A fast fuse in series with pack + |

The R5460's excess-current threshold (0.2 V across ~5 mΩ of FETs → ≈40 A) only works as short-circuit protection. Normal overcurrent is limited by the BQ2579x IBAT_OCP (9.3 A), the boost ILIM and the fuse.

**Recommendation:** R5460N212AF + 2× NCEP3065QU + 2× HY2213-BB3A + 10 A fuse. Tell users to use **matched cells** of the same brand, batch and charge state. Top balancing at ≤60 mA only corrects slow drift.

### 3.3 Fuel gauge (optional)

| Part | LCSC | B/E | Stock | $@10 | Notes |
|---|---|---|---|---|---|
| BQ34Z100PWR-G1 | C91302 | E | 4,546 | 2.49 | Multi-cell Impedance Track. Needs bqStudio + EV2400 to learn/configure: high effort |
| MAX17263LETD+T | C5280562 | E | 110 | 8.90 | Multi-cell ModelGauge m5. Low stock, expensive |
| BQ27220YZFR | C528617 | E | 11,680 | 0.53 | **1S only**, not applicable |

**Recommendation: none.** Use the BQ2579x ADC (VBAT + signed IBAT) for coulomb counting plus an OCV table in firmware. This saves one extended part.

---

## 4. USB-C PD sink + protection

| Part | LCSC | B/E | Stock | $@10 | Pkg | Notes |
|---|---|---|---|---|---|---|
| **WCH CH224Q** | **C46061833** | E | 19,470 | 0.36 | DFN-10 2×2 (0.4 mm) | PD 3.2 incl. EPR/AVS/PPS, 5–28 V. Config by single resistor *or* **I2C (0x22/0x23)**: reg 0x0A requests voltage, 0x50 reports max current, 0x60–0x8F hold source PDOs. Lets firmware set IINDPM correctly |
| WCH CH224A | C42459160 | E | 1,153 | 0.35 | ESSOP-10 | Same family, easier package; I2C single-byte only |
| WCH CH224D | C3975094 | E | 13,227 | 0.35 | QFN-20 | Older; resistor/pin config |
| WCH CH224K | C970725 | E | **0** | 0.32 | ESSOP-10 | Out of stock |
| Hynetek HUSB238 | C7471904 | E | 16,199 | 0.47 | DFN-10 3×3 | I2C-configurable PD sink, good alternative |
| ST STUSB4500 | C2678061 | E | 5,679 | 2.41 | QFN-24 | NVM-configured, mature, 6× the price |
| TI TPS25750 | C2868209 | E | 322 | 2.84 | WQFN-38 | Full PD controller with power path; overkill, low stock |

Does the charger already include PD? **No.** BQ2579x only does BC1.2/HVDCP on D+/D−, so a PD sink is still needed.

**Recommendation: CH224Q.**
- Request **15 V** (fallback 12 V/9 V; 5 V still charges through buck-boost). Keep 20 V out of the default request to keep the VBUS ceramic voltage rating and charger switching loss down.
- Firmware reads 0x50 and programs BQ IINDPM.
- Leave CH224Q's BC1.2 D+/D− function unconnected, so USB data goes only to the USB-UART. Confirm the pin function in the datasheet.
- No VBUS load switch is planned. The source only raises VBUS after a contract, and the BQ2579x tolerates 30 V on VBUS. Its optional external ACFET/RBFET pair can be added if a second input is wanted. Verify this against the BQ25792 EVM schematic.

| Protection | LCSC | B/E | Stock | $@10 | Notes |
|---|---|---|---|---|---|
| USBLC6-2SC6 (UMW) | C2687116 | E | 158,937 | 0.048 | D+/D− ESD. ST original C7519 (44,752, $0.15) |
| SMF24A TVS (MDD) | C123810 | E | 49,185 | 0.03 | VBUS TVS, 24 V standoff, SOD-123FL (OK for ≤20 V PD) |
| USB-C receptacle TYPE-C-31-M-12 | C165948 | E | 446,008 | 0.19 | 16-pin, 5 A, USB 2.0 + CC. Alternative: C2765186 SHOU HAN, 1.08 M stock, $0.07 |

CC1/CC2 go straight to the CH224Q, which has internal Rd. Add ESD on CC if the connector is exposed (USBLC6 second channel, or a dedicated 2-line TVS).

---

## 5. Boost converter (battery 6–8.4 V → PVDD 19 V)

| Part | LCSC | B/E | Stock | $@10 | Pkg | Specs | Verdict |
|---|---|---|---|---|---|---|---|
| **TI TPS61178RNWR** | **C127918** | E | 5,726 | **0.89** | VQFN-13 HotRod 3×3.5 | Sync boost, 2 × 16 mΩ integrated FETs, Vin 2.7–20 V, **Vout 4.5–20 V**, programmable peak ILIM up to 10 A (8 A typ at 80.6 kΩ), 0.2–2.2 MHz + sync, auto-PFM, load-disconnect gate driver, hiccup short protection. Datasheet's target application is **"Portable Speaker"**; quoted 96 % at 7.2→16 V/2 A | **Pick** |
| TPS611781RNWR | C2862009 | E | 3,057 | 0.97 | same | Forced-PWM version (no PFM) | Use if PFM ripple is audible; costs idle current |
| TPS61288RQQR | C5219223 | E | 7,159 | 1.65 | VQFN-11 | 15 A valley ILIM, **Vout max 18 V** | Caps PVDD at 18 V (−1.5 dB vs 21 V) |
| LM5156DSSR | C3187944 | E | 153 | 1.07 | WSON-12 | 60 V controller, external FET (non-sync with diode) | More parts, diode loss ~1 W at 2.5 A out, low stock |
| LM5155DSSR | C545416 | E | 10,473 | 1.62 | WSON-12 | 45 V controller, external FET | Viable if >40 W is ever needed |
| TPS55340RTER | C169167 | E | 23,286 | 1.98 | WQFN-16 | 5.25 A switch, non-sync | Current too low at 6 V in |

Datasheets: [TPS61178](https://www.ti.com/lit/ds/symlink/tps61178.pdf), [TPS61288](https://www.ti.com/lit/ds/symlink/tps61288.pdf), [LM5156](https://www.ti.com/lit/ds/symlink/lm5156.pdf).

**Boost inductor (2.2 µH, Isat ≥ 12 A):**

| Part | LCSC | B/E | Stock | $@10 | Specs |
|---|---|---|---|---|---|
| **cjiang FXL1040-2R2-M** | **C167228** | E | 5,349 | 0.31 | 2.2 µH, Irms 12 A, Isat 18 A, 7 mΩ, 11.5×10 mm |
| Sunlord MWSA1004S-2R2MT | C408482 | E | 2,378 | 0.27 | 2.2 µH, 12 A / 16.5 A, 7 mΩ |
| KOHER MDA1050-2R2M | C2847559 | E | 445 | 0.88 | 2.2 µH, 19.5 A / 20 A, 5.1 mΩ |

Output caps: 4–6× 10 µF 50 V 1206 **C13585 (Basic)**. X5R loses ~60 % at 19 V bias, so count on ~4 µF each. Add the shared 470 µF bulk from §2. Input: 2× 22 µF 25 V 1206 **C12891 (Basic)**.

**Settings:**
- Vout 19.0 V. OVP margin to the TAS5805M's 26.4 V is fine.
- fsw ≈ 600 kHz, keeping harmonics away from the 384/768 kHz amp PWM. Better: sync the boost to the amp, or spread-spectrum both.
- ILIM ≈ 9–10 A peak.
- EN driven by the ESP32, and up before the amps' PDN releases.

**Loss estimate (for the thermal sim).** Analytical model: Rds 20 mΩ hot for each FET, DCR 7 mΩ, fsw 600 kHz, 8 ns total edge time. The model is optimistic, so plan on 1.5–2 points lower efficiency.

| Vin | Pout | Iin | Ipk (L) | Loss total | of which IC | of which L | η (model) |
|---|---|---|---|---|---|---|---|
| 7.4 V | 2 W | 0.29 A | 2.0 A | 0.16 W | 0.11 | 0.05 | 92 % |
| 7.4 V | 5 W | 0.71 A | 2.4 A | 0.22 W | 0.17 | 0.05 | 96 % |
| 7.4 V | 15 W | 2.1 A | 3.8 A | 0.47 W | 0.39 | 0.08 | 97 % |
| 7.4 V | 30 W | 4.2 A | 5.9 A | 1.06 W | 0.89 | 0.17 | 96.6 % |
| 6.2 V | 30 W | 5.1 A | 6.7 A | 1.36 W | 1.13 | 0.22 | 95.7 % |
| 6.2 V | 40 W | 6.8 A | 8.4 A | 2.10 W | 1.73 | 0.37 | 95 % |

For thermal-sim inputs, use **IC ≈ 0.4 W / L ≈ 0.1 W at moderate-loud**, and **IC ≈ 2 W / L ≈ 0.5 W worst case** (low battery, 40 W). The HotRod package relies on wide copper on SW/VOUT/GND plus thermal vias under the GND pins.

**Recommendation: TPS61178RNWR + FXL1040-2R2-M.**

---

## 6. 3.3 V buck (VSYS 6–9 V → 3.3 V, ~500 mA peaks)

| Part | LCSC | B/E | Stock | $@10 | Pkg | Specs |
|---|---|---|---|---|---|---|
| **TI TPS62933DRLR** | **C3200405** | E | 9,555 | 0.36 | SOT-583 | 3.8–30 V, 3 A, **12 µA Iq** (PFM), 200 k–2.2 MHz |
| TI TPS62162DSGR | C40256 | E | 2,101 | 0.94 | WSON-8 2×2 | Fixed 3.3 V, 1 A, 17 µA Iq, 3–17 V |
| TI TPS54202DDCR | C191884 | E | 200,511 | 0.17 | SOT-23-6 | 4.5–28 V, 2 A, Eco-mode, 500 kHz |
| TI TPS563201DDCR | C116592 | E | 119,467 | 0.064 | SOT-23-6 | 4.5–17 V, 3 A. Cheapest; higher light-load Iq |
| Silergy SY8120IABC | C479076 | E | 30,834 | 0.09 | SOT-23-6 | 4.2–18 V, 2 A |

Inductor: 4.7 µH Sunlord SWPA4030S4R7MT (C57269, E, 49,209, $0.055) or FXL0420-4R7-M (C167208, E, 98,554, $0.12).

**Recommendation: TPS62933DRLR.** Low Iq matters for standby drain, and 30 V input means it survives a VBUS-to-VSYS fault. TPS54202 is the high-stock fallback.

---

## 7. USB-UART for flashing + auto-reset

| Part | LCSC | B/E | Stock | $@10 | Pkg | Notes |
|---|---|---|---|---|---|---|
| **WCH CH340C** | **C84681** | E | 79,244 | 0.46 | SOP-16 | Internal oscillator, 2 Mbps, 3.3 V or 5 V supply, DTR/RTS. Easy to hand-rework |
| WCH CH340N | C2977777 | E | 37,446 | 0.50 | SOP-8 | **No DTR**, so auto-reset needs a hack. Not recommended |
| WCH CH340K | C968586 | E | 25,282 | 0.55 | ESSOP-10 | Has RTS + DTR |
| WCH CH343P | C2846043 | E | 16,192 | 0.88 | QFN-16 | 6 Mbps, faster flashing |
| SiLabs CP2102N-A02-GQFN28R | C964632 | E | 28,240 | 1.58 | QFN-28 | Most mature drivers; 3.4× the price |

**Auto-reset:** the classic dual-NPN cross-coupled circuit (DTR/RTS → EN/IO0) using 2× **MMBT3904 C20526 (Basic)** or S8050 C2146 (Basic), 10 kΩ bases, plus 1 µF on EN. A UMH3N (C62892) dual saves board space but is extended.

Power the CH340C from 3V3, with V3 tied to VCC. It suspends at about 50 µA when the cable is out.

**Recommendation: CH340C + 2× MMBT3904.**

---

## 8. Digital MEMS microphone

| Part | LCSC | B/E | Stock | $@10 | Pkg / port | Interface | Specs |
|---|---|---|---|---|---|---|---|
| **TDK T3902 (MMICT390200012)** | **C3171752** | E | 6,018 | 1.30 | LGA-5 3.5×2.65 mm, **bottom port** | PDM | 64 dBA SNR, 1.65–3.63 V, 650 µA |
| MEMSensing MSM261DDB020 | C27636198 | E | 6,171 | 0.53 | LGA-5 3.5×2.7 | PDM | −26 dBFS, 64 dB SNR. Port side not stated in listing; check datasheet |
| LinkMems LMD3526B261-OFA03 | C41347997 | E | 7,634 | 0.32 | 3.5×2.7 ("B" = bottom port, inferred) | PDM | −26 dBFS, 65 dB SNR |
| TDK ICS-43434 | C5656610 | E | **4** | 3.68 | LGA-6 | **I2S** | Out of stock in practice |
| Knowles SPH0645LM4H-B | various | E | **0** | — | | I2S | Out of stock |
| MSM261S4030H0R | C2840615 | E | **0** | — | | I2S | Out of stock |

The I2S-output mics are effectively unavailable, so use **PDM** on ESP32 I2S0 (PDM RX is I2S0-only on the classic ESP32).

**Bottom vs top port:**
- Bottom port needs a 0.6–1.0 mm non-plated hole under the acoustic port. JLC assembles these routinely.
- Seal the hole to the enclosure with a gasket/acoustic mesh. Without the seal the mic hears the cabinet interior.
- A top-port part would face the enclosure wall and need its own gasket on the can.
- Put the mic on the small top UI board near the display, away from the woofers' back wave. Route PDM CLK at no more than ~3.2 MHz with a 33 Ω series resistor.

**Recommendation: TDK T3902 (C3171752);** LMD3526B261 is the budget fallback.

---

## 9. Display: 1.28" round GC9A01 240×240

LCSC/JLC stocks **no** GC9A01 panel. The only listing, Pacific Goal PG1301HA-ZA0, shows 0 stock at $37. Bare panels from different vendors share the GC9A01 driver but **not FPC pin order or pitch**, so an FPC footprint can't be designed until a specific panel is bought and its drawing checked.

| Option | Source | Interface | Notes |
|---|---|---|---|
| **Waveshare 1.28" LCD Module** ([page](https://www.waveshare.com/1.28inch-lcd-module.htm)) | Waveshare / Amazon / AliExpress | 8-pin 2.54 mm header: VCC, GND, DIN, CLK, CS, DC, RST, BL | Onboard regulator and backlight transistor; BL accepts PWM. **Recommended for v1** |
| Bare GC9A01 panel + FPC connector | AliExpress (vendor-specific) | Usually 12–18-pin FPC, 0.5 mm or 0.8 mm | Needs the vendor drawing; LEDA/LEDK on the FPC |
| FPC connector if a 12-pin 0.5 mm panel is chosen | JUSHUO AFC01-S12FCA-00, **C262661** | E, 127,213 stock, $0.086 | Bottom contact, flip lock |

**Backlight driver for a bare panel:** AO3400A **C20917 (Basic)** low-side N-FET, PWM from the ESP32 LEDC, with a series resistor sized for ~20–30 mA of LED current.

**Connection:** a JST-SH or 2.54 mm cable from the main board to the top UI board, carrying 3V3, GND, 5× SPI, BL, plus encoder, buttons and PDM mic. Add 22–33 Ω series resistors on SCLK/MOSI. The cable is 15–20 cm, so run SPI at ≤40 MHz with GND interleaved.

**Recommendation:** Waveshare module (hand-installed) on the top UI board. No extended part on the main board.

---

## 10. Encoder + buttons

| Part | LCSC | B/E | Stock | $@10 | Notes |
|---|---|---|---|---|---|
| **ALPS EC11E18244AU** | **C202365** | E | 1,464 | 1.99 | EC11, 18 detents/36 pulses, push switch, THT |
| ALPS EC11E1834403 | C361165 | E | 3,008 | 1.47 | EC11E variant with push switch. Check shaft length vs the knob/enclosure |
| Bourns PEC11R-4215F-S0024 | C143790 | E | 3,890 | 1.97 | 24 PPR, 24 detents, push, THT |
| ALPS EC11J1525402 | C209762 | E | 1,193 | 2.60 | **SMD** EC11 (15 detents/30 pulses). Avoids THT assembly fees |
| **XKB TS-1187A-B-A-B** tactile | **C318884** | **B** | 676,127 | 0.02 | 5.1×5.1 mm SMD |

Encoder A/B go to input-only GPIO34/35 with 10 k pull-ups and 10 nF RC debounce. Buttons use a resistor ladder on one ADC pin (GPIO39).

**Recommendation:** PEC11R-4215F-S0024 or EC11E18244AU, picked by shaft length once the knob is chosen. If the UI board is otherwise all-SMD, the SMD EC11J1525402 avoids JLC's THT surcharge.

---

## 11. Optional: USB audio input (laptop → speaker)

| Option | LCSC | Stock | $@10 | How it works | Verdict |
|---|---|---|---|---|---|
| SiLabs CP2615-A02-GM | C1521596 | **6** | 9.53 | USB Audio Class → I2S (+ I2C master), no firmware | Out of stock |
| TI PCM2706CPJTR | C2651268 | 223 | 8.22 | USB → I2S out (16-bit, ≤48 kHz) + 12 MHz crystal; device is clock master (adaptive) | Works, but expensive and 16-bit only |
| ESP32-S3-WROOM-1-N8 / MINI-1-N8 | C2913198 / C2913206 | 4,030 / 17,704 | 4.25 / 4.17 | TinyUSB UAC2 → I2S master; firmware heavy | Most flexible: 24-bit/48 k, could also replace the CH340 |

**Integration problems in every option:**
- **I2S switching.** The amps take one I2S source. The ESP32's two I2S peripherals are already used (PDM mic + amp TX), so it can't ingest a third stream. The practical design is a **digital mux:** SN74LVC157APWR (C406871, 1,472 stock, $0.40) switching BCLK/LRCK/DATA between the ESP32 and the USB bridge under ESP32 GPIO control. Put the amps in deep-sleep while switching, because the TAS5805M re-locks to the new rate.
- **What USB audio skips.** It bypasses the ESP32's user-EQ, loudness and auto-EQ. The amp DSP (crossover, driver EQ, limiter) still applies.
- **USB data contention.** The single USB-C port's D+/D− currently go to the CH340C. USB audio needs them too. You'd need a USB 2.0 switch, *or* the ESP32-S3 replaces the CH340C and acts as the classic ESP32's flasher (esp-serial-flasher). That's more firmware.
- **Cost/complexity.** About $5–9 BOM, 2–3 extended parts, one more firmware project and USB-switch layout.

**Recommendation: No for v1.** Spend ~$0.40 of provision instead: footprint the SN74LVC157A mux (or 0 Ω jumpers) plus a 5-pin I2S input header (BCLK, LRCK, DATA, GND, SEL). A v1.1 can then add an ESP32-S3 or PCM2706 daughterboard without re-spinning the main PCB.

---

## 12. Rough power budget and runtime

### 12.1 Assumptions

These are estimates, to be replaced by bench measurements.

- **ESP32 (WROVER, 240 MHz):** BT A2DP streaming + Wi-Fi in modem-sleep ≈ 150 mA @ 3.3 V.
- **Display:** logic + dimmed backlight ≈ 30 mA.
- **Amp DVDD:** 2× ≈ 15 mA.
- **Mic, CH340 suspend, misc:** ≈ 5 mA.
- **3V3 rail total:** ≈ 0.72 W; buck η 88 % → **0.82 W** from VSYS.
- **TAS5805M idle** (Hybrid modulation, LC filter): datasheet 16.5 mA @ 13.5 V = 0.22 W; scaled to 19 V ≈ **0.35 W each, 0.7 W for both**.
- **Boost efficiency:** ≈ 90 % at light load (PFM), 94–95 % at moderate/high.
- **Class-D efficiency:** ≈ 85–88 % at mid/high output.
- **"Moderate volume":** ≈ 1 W average total electrical into the four drivers, roughly 80–85 dB SPL @ 1 m with ~85 dB/W/m drivers plus passive radiators. Loud/limiter-capped pink noise ≈ 10 W average.
- **Usable energy:** 90 % of nominal (3.0 V/cell cutoff). 2×3000 mAh × 7.2 V = 21.6 Wh → **19.5 Wh**. 2×5000 mAh 21700 = 36 Wh → **32.4 Wh**.

### 12.2 Budget

| State | Logic (from VSYS) | Amps + boost (from VSYS) | Total | I_batt @ 7.4 V | Runtime 2×3000 mAh 18650 | Runtime 2×5000 mAh 21700 |
|---|---|---|---|---|---|---|
| Idle (connected, silent, display on) | 0.82 W | 0.78 W | **1.65 W** | 0.22 A | **≈ 11.8 h** | **≈ 19.6 h** |
| Moderate (≈1 W audio) | 0.82 W | 2.0 W | **≈ 2.9 W** | 0.39 A | **≈ 6.7 h** | **≈ 11.2 h** |
| Loud sustained (≈10 W audio, limiter) | 0.82 W | 12.8 W | **≈ 13.7 W** | 1.85 A (2.2 A @ 6.2 V) | **≈ 1.4 h** | **≈ 2.4 h** |
| Peak transient (all 4 ch clipping, ~60 W audio) | — | ~70 W | **~70 W** | ~9.5 A | Not allowed: cap at ≤ 6 A average (BQ2579x BATFET) with boost ILIM + amp DRC | |
| Standby / "off" (ship mode or ESP32 deep sleep) | — | — | < 1 mW (ship) / ~1 mW | | months | months |

### 12.3 Reaching ≥ 8 h at moderate volume with 18650s

The target is borderline. These measures add up:

1. **Dynamic PVDD.** Drop the boost to ~12 V when the volume setting allows it, by injecting into the TPS61178 FB node from the ESP32 DAC/PWM-RC. That saves ~0.3 W of amp idle plus switching loss. TAS5805M Hybrid modulation tracks PVDD.
2. **Display auto-off** after 30 s: saves ~0.1 W.
3. **Wi-Fi off** unless the web UI is in use, and CPU at 160 MHz: saves ~0.1–0.2 W.
4. **Amp deep-sleep** on detected digital silence.

Together these get to ≈ 2.3 W, which is ≈ 8.5 h on 3000 mAh, ≈ 9.6 h on 3400–3500 mAh cells, and ≈ 14 h on 21700s. **Recommend specifying 21700 (≥ 4000 mAh) cells as the default.**

---

## 13. Recommended set and extended-part count

| # | Function | Part | LCSC | B/E |
|---|---|---|---|---|
| 1 | MCU/BT | ESP32-WROVER-E-N8R8 | C2973667 | E |
| 2 | Amp ×2 | TAS5805MPWPR | C478472 | E |
| 3 | Amp filter L ×8 | FXL0630-100-M | C167223 | E |
| 4 | Amp filter C ×8 | 0.68 µF 50 V 0805 X7R (or Basic 1 µF C28323) | C282780 | E (→B) |
| 5 | Charger | BQ25792RQMR | C2862876 | E |
| 6 | PD sink | CH224Q | C46061833 | E |
| 7 | 2S protection | R5460N212AF | C259717 | E |
| 8 | Protection FETs ×2 | NCEP3065QU | C502964 | E |
| 9 | Balancer ×2 | HY2213-BB3A | C113632 | E |
| 10 | Pack fuse | 0451010.MRL | C44479 | E |
| 11 | Boost | TPS61178RNWR | C127918 | E |
| 12 | Boost L | FXL1040-2R2-M | C167228 | E |
| 13 | 3V3 buck | TPS62933DRLR | C3200405 | E |
| 14 | Buck L | SWPA4030S4R7MT | C57269 | E |
| 15 | USB-UART | CH340C | C84681 | E |
| 16 | USB ESD | USBLC6-2SC6 (UMW) | C2687116 | E |
| 17 | VBUS TVS | SMF24A | C123810 | E |
| 18 | USB-C receptacle | TYPE-C-31-M-12 | C165948 | E |
| 19 | Bulk cap | 470 µF 25 V electrolytic | C2895277 | E |
| 20 | PVDD/boost ceramics | 22 µF 35 V 1206 (if more than the Basic 10 µF/50 V is wanted) | C342620 | E (optional) |
| 21 | Mic (UI board) | T3902 MMICT390200012 | C3171752 | E |
| 22 | Encoder (UI board) | PEC11R-4215F-S0024 / EC11E18244AU | C143790 / C202365 | E |
| 23 | Battery connector | XT30PW-M (or JST-VH) | C431092 | E |
| 24 | (provision) I2S mux | SN74LVC157APWR | C406871 | E (optional) |
| — | Auto-reset NPN, BL FET, tactile, R/C, 10 µF 50 V, 1 µF 50 V, 22 µF 25 V | MMBT3904 C20526, AO3400A C20917, TS-1187A C318884, C13585, C28323, C12891 | | **B** |

**Extended types:**
- **Main board:** ~20 (#1–19 and #23). Use the Basic 1 µF filter cap and skip the 22 µF/35 V to get to 18–19.
- **UI board:** +2 (mic, encoder).
- **Optional:** +1 (mux).

JLC charges a per-type loading fee for each extended part, about $3 per type per order, so ≈ $60–70 per order across both boards. "Preferred extended" parts may waive this; none of the above showed the preferred flag. Possible savings:
- Use the same 10 µH and 2.2 µH inductor family to share types.
- Use Basic caps wherever voltage allows.
- Buy the display module separately; it needs no LCSC part.

---

## 14. Risks

**Stock**
- TAS5805M: 2,244 in stock, enough for 5 boards. TI parts swing, though; consider a JLC parts pre-order/"global sourcing" reservation.
- CH224K is already at 0, which is why CH224Q was chosen.
- I2S MEMS mics: 0 (PDM chosen). GC9A01 panel: none on LCSC (module bought separately).
- R5460N212AF: 2,770; check before ordering.

**Layout difficulty**
- **TAS5805M:** PowerPAD via array; PVDD decoupling within 2 mm of the pins; bootstrap caps; symmetric LC filter routing; output loops kept small for EMI. Spread spectrum and 768 kHz help EMI.
- **TPS61178 HotRod:** hot loop (SW–VOUT–GND cap) under 5 mm with ceramics right at the pins. The FB divider must stay away from SW.
- **BQ2579x:** 4-switch buck-boost with two switch nodes. Follow the EVM layout closely. The QFN-29 pin pitch is fine.
- **CH224Q:** 0.4 mm-pitch DFN. JLC can assemble it, but it can't be reworked by hand. CH224A (ESSOP-10) is the friendlier fallback.
- **Wi-Fi/BT antenna:** WROVER antenna at the board edge with a ≥15 mm copper keep-out, and no metal grille directly over it. Otherwise use the U.FL WROOM-32UE with an external antenna.

**Thermal hotspots** (inputs to the thermal sim)
- Boost IC + inductor: 0.5 W moderate, ~2.5 W worst case.
- Amps: ~0.4 W each idle; 1–3 W each when loud.
- Charger during charge-while-play: ~1.5 W.
- Protection FETs: ~0.2 W at 6 A.
- All of these sit in a sealed enclosure with no airflow. Spread them out and use the 4-layer inner planes as heat spreaders.

**Electrical**
- 4 Ω woofers at 19–20 V risk amp OCP trips.
- Battery peak current must stay within the BQ2579x BATFET rating (6 A RMS / 9.3 A OCP).
- With user-supplied, unmatched cells, the protector trips on OV during charge. Balancing is slow, so document a cell-matching requirement.
- Boost (600 kHz) and amp (384/768 kHz) PWM beat frequencies can land in the audio band. Sync them or pick frequencies carefully.
- PDM clock and the SPI display share the UI cable. Keep ground returns adjacent.

**Firmware:** AAC sink depends on ESP-IDF v6.x's external-codec A2DP path, which is new. Plan SBC-first.
