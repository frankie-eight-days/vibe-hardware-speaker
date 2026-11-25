# Main board layout rules (speaker_main, layout rev B, 6 layers, 2026-11-25)

These rules come before placement and routing. Each number cites its source: the fab capability page, the stackup, a calculation in this file, or a datasheet layout section from `kb/datasheets/` (with page numbers). The KiCad project carries the net classes and board minimums from this file. Items that Konnect cannot write into KiCad are flagged **[not in DRC]**; those are checked by hand or by script.

## 1. Fabrication contract: JLCPCB 6-layer, 1.6 mm (rev B)

Source: JLC impedance-calculator template "JLC06161H-1080B", read 2026-11-25. The rev A 4-layer table (JLC04161H-7628) is in §7 of LAYOUT_NOTES as history.

| Layer | Use | Material | Thickness (mm) | Er |
|---|---|---|---|---|
| L1 F.Cu | signal, parts | Cu 1 oz finished | 0.035 | |
| | | 1080 prepreg | **0.0764** | 3.91 |
| L2 In1.Cu | GND plane | Cu 0.5 oz | 0.0152 | |
| | | core | 0.10 | 4.36 |
| L3 In2.Cu | signal | Cu 0.5 oz | 0.0152 | |
| | | 7628 + 0.7 mm core + 7628 | 1.1208 | 4.4 / 4.53 / 4.4 |
| L4 In3.Cu | power planes | Cu 0.5 oz | 0.0152 | |
| | | core | 0.10 | 4.36 |
| L5 In4.Cu | GND plane | Cu 0.5 oz | 0.0152 | |
| | | 1080 prepreg | 0.0764 | 3.91 |
| L6 B.Cu | signal, test pads, thermal landings | Cu 1 oz finished | 0.035 | |

- **Order as JLC06161H-1080B**, 1.6 mm, 1 oz outer / 0.5 oz inner, ENIG. Mask: 0.6–1.2 mil, Er 3.8.
- KiCad's Python API has no stack-up binding, so Board Setup → Physical Stackup may still show generic dielectrics **[not in DRC]**; this table and the fab notes are the authority.
- JLC 6-layer capability: 0.09/0.09 mm trace/space. Board minimum here: **0.10 mm track** (USB pair only), 0.127 mm clearance, vias 0.6/0.3 standard, 0.5/0.25 and 0.45/0.2 fine (no surcharge at ≥ 0.45 mm pad).

## 2. Layer use (rev B)

| Layer | Use |
|---|---|
| L1 F.Cu | All parts. Hot loops, switch nodes, short signals. GND pour stitched to L2/L5. |
| L2 In1.Cu | **Solid GND**, no traces. Voids: antipads and the antenna keep-out. |
| L3 In2.Cu | **Main signal layer** (long buses, I2S, I2C, UI/FFC bus), referenced to L2 GND. GND fill around the signals. No signals in the charger SW window (X 162–172, Y 100–111). |
| L4 In3.Cu | **Power planes**: PVDD (middle band, boost → both amps), VSYS (front strip, charger → boost; +3 mm B.Cu band on to the buck), +3V3 (rear strip and the ESP32 end), VBAT_PACK/BATT_N/PACK_P/PROT_D islands, the charger SW1/SW2 links. GND fill elsewhere. No signals. |
| L5 In4.Cu | **Solid GND**, no traces. |
| L6 B.Cu | Signals referenced to L5, bottom test pads, duplicate high-current pours (VBAT_PACK, BATT_N, PROT_D, PACK_P, CHG_BAT, SW links, VBUS band), VSYS band to the buck, three exposed-GND thermal landings. GND pour elsewhere. |

## 3. Net classes (in `speaker_main.kicad_pro`)

Widths use the IPC-2221 external-conductor formula, I = 0.048·ΔT^0.44·A^0.725 (A in mil²), at ΔT = 20 °C on 1 oz (35 µm). It is conservative against IPC-2152 for outer layers. The 0.5 oz inner layers carry only about ⅓ of that current for the same width, so they are treated as parallel paths, never the only path.

| Class | Nets | Current (cont / peak) | Track | Clearance | Via (dia/drill) | Basis |
|---|---|---|---|---|---|---|
| Default | everything else | < 0.5 A | 0.20 | 0.15 | 0.6/0.3 | JLC capability |
| PWR_BATT | PACK_P, VBAT_PACK, CHG_BAT, BATT_N, PROT_D, VSYS | 7 A / 10 A | **3.0 mm**, or pours on 2–3 layers | 0.20 | 0.6/0.3, ≥ 12 per layer change | 7 A gives 157 mil² = 2.9 mm on 1 oz external (formula above); spec_power §6 asks ≥ 3 mm |
| PVDD | PVDD | 2.2 A avg (40 W / 18 V) / 4 A | 1.5 | 0.20 | 0.6/0.3, ≥ 6 per transition | 3 A needs 0.9 mm. spec_signal §3.6 asks ≥ 2 mm or a plane: PVDD is an L3 plane plus L1 pours |
| VBUS | VBUS, CHG_PMID | 3 A (ILIM_HIZ 2.7–2.9 A) | 1.5 | 0.20 | 0.6/0.3 | 3 A needs 0.9 mm, so 1.5 mm gives margin. 15–20 V |
| SWITCH | BST_SW, CHG_SW1, CHG_SW2, BUCK_SW | 9 A pk (boost ILIM) | 1.0 (pour-shaped) | 0.25 | n/a (boost and buck SW have no vias) | Keep the copper minimal (TPS61178 §11.1 rule 2, p.30; BQ25792 §12.1 item 5, p.135) |
| SPEAKER | AL/AR_OUT*, SPK_* | 2 A rms / 4 A pk | 1.0 | 0.20 | 0.6/0.3 | spec_signal §3.6: "≥ 1.0 mm (≥ 4 A peak)" |
| PWR_3V3 | +3V3 | 0.8 A | 0.5 | 0.15 | 0.6/0.3 | 1 A needs 0.25 mm |
| USB_DIFF | USB_DP, USB_DN | FS 12 Mb/s | **0.11, gap 0.15** | 0.15 | 0.6/0.3 (none planned) | 90 Ω differential on L1 over L2 (rev B, §4) |
| CLOCK | I2S_BCLK, I2S_BCLK_MCU, IO26_R, LCD_SCLK, IO18_R, PDM_CLK, IO32_R | edge-rate limited | 0.20 | 0.25 | 0.6/0.3 | spec_signal §4.4: ≥ 3× width from other signals; series R at the source (68 Ω SPI/PDM, 33 Ω I2S) |

- The diff-pair gap (0.20 mm) and the 3W spacing for CLOCK are fixed by construction, because Konnect's `create_netclass` exposes only width, clearance and via. **[gap not in DRC]**
- **Class clearances are capped by the fine-pitch footprints.** KiCad checks pad-to-pad gaps inside a footprint against the larger of the two net classes. The tightest gaps are BQ25792 (0.4 mm pitch, 0.2 mm pads: 0.20 mm), CH224Q (0.20 mm), TAS5805M (0.25 mm) and TPS61178 (0.25 mm; the bars are 0.30 mm apart). So power classes use 0.20 mm, and SWITCH/CLOCK use 0.25 mm. Wider spacing to sensitive nets is a placement and routing rule, checked by review, not by DRC.
- BATT_N must never touch GND (spec_power §6). DRC's short check enforces this, because BATT_N and GND are different nets. Its 0.25 mm class clearance keeps pours apart.
- **Inner copper (rev B, 0.5 oz = 15.2 µm):** inner layers carry planes and signals only. IPC-2221 internal (k = 0.024) gives 0.25 A for a 0.2 mm track at ΔT 20 °C, far above any In2 signal. Power classes never route as traces on inner layers; their inner copper is plane (In3). The postlayout IR solve checks the In3 planes (PVDD, VSYS, +3V3).

## 4. Controlled impedance: USB D+/D− (90 Ω ±10 %), rev B

Same 2-D solver (`layout_src/zsolve.py`, run `layout_src/zrun6.py`), now L1 over L2 with h = 0.0764 mm 1080 prepreg, Er 3.91, t = 0.035 mm, mask 15 µm Er 3.8, 5 µm grid.

| w / s (mm) | Zdiff (2-D solver) | JLC calculator (Er 3.91 / its default 4.3) |
|---|---|---|
| 0.10 / 0.15 | 92.2 Ω | |
| **0.11 / 0.15** | **90.0 Ω** | ≈ 91 / 88 Ω (90 Ω at 0.115 / 0.106 mm) |
| 0.12 / 0.15 | 86.8 Ω | 88.3 / 85.4 Ω |

- **Chosen: w = 0.11 mm, s = 0.15 mm (90.0 Ω).** The pair gap equals the class clearance, so DRC checks it. L6 over L5 is the same geometry (symmetric stack-up), used for the DN jumper under J601.
- Route: J601 → U601 (flow-through: pin 1→6, pin 3→4 under the package) → CH340C as a coupled pair along Y 85.0–85.2, over solid L2. About 25 mm. FS USB (12 Mb/s, ≥ 4 ns edges) does not need length matching.

## 5. Vias and thermal pads

- **No via-in-pad on signal or passive pads.** Vias sit at least 0.15 mm from pad edges and connect through a short neck.
- **TAS5805M PowerPAD (U301/U401)** uses the KiCad footprint `…EP3.4x9.7mm…_ThermalVias`: 24 vias of 0.2 mm drill / 0.5 mm pad at 1.2 mm pitch (3×8). This matches TI SLASEH5D §9.1.3.2.1 (p.100, 3×8 at 1.2 mm, small vias) and adds no JLC surcharge, because the diameter is ≥ 0.45 mm. They are in-pad by design. **Fab note:** order JLC "via plugging / epoxy-filled & capped" for these, or accept TI's open-via guidance (small drills limit wicking). Paste is the footprint's aperture array (§9.1.3.2.2 p.90–91, 70–80 %).
- **TPS61178 (U901):** no vias in the 0.25 mm bars (land pattern p.38 note 4). GND vias go on the PGND pour beside bar 6 and at the C_OUT grounds.
- **BQ25792 (U701):** SW1/SW2 drop through 0.25/0.5 vias inside the package outline (not in the pads), per SLUSDV2C §8.4.1 item 2 (p.139). REGN and VBUS cap grounds get ≥ 2 vias each (items 3–4).
- **ESP32 EPAD:** GND vias in the gaps between the 9 sub-pads (WROVER-E v2.4 Fig. 15, p.45).
- **Q801 (S3, 1.5 W):** ≥ 2 cm² of copper on the drain (PROT_D) and on the BATT_N source, on L1 plus L4, with thermal vias into **matching** islands only. BATT_N never stitches to GND.
- **Stitching:**
  - GND vias on a ≤ 5 mm grid along all board edges (outside the antenna keep-out).
  - A fence around each switcher (boost, charger, buck) at ≤ 3 mm pitch.
  - Pairs of GND vias beside every L1 to L4 signal transition.

## 6. Keep-outs and zones **[partly not in DRC]**

Konnect cannot create KiCad rule areas (keep-out zones). So:
- **Antenna (U101):**
  - The footprint's own keep-out covers the 18 × 6.3 mm antenna area (KiCad DRC enforces it).
  - The board-level rule is enforced by construction: no copper on any layer for **X < 63 mm** (antenna area plus 0.7 mm, full board width), and none for **X < 75 mm outside Y 86–115** (mech_envelope §6, "15 mm from the board edge").
  - Pours are drawn with that cut-out. Within the module band, only module pads, C101/C102 and fan-out are allowed.
  - Basis: Espressif HDG §1.4.8, Fig. 23/25 (p.30–32). The mech "no copper X < −75" rule would forbid connecting module pins 1–10 and 29–38. The Espressif rule concerns the antenna area itself, and the antenna overhangs the edge by 4.5 mm. See LAYOUT_NOTES.
- **Mounting holes (6× NPTH M3):**
  - Components keep out of Ø 6.5 mm.
  - No tracks on L1 within Ø 6.5 mm, where the screw head sits.
  - Pours stay ≥ 0.5 mm from the hole.
- **Height zones:** checked by `layout_src/check.py` against a clearance map ray-cast from the mech STL set (`mech/concept/build/*.stl`), with 1 mm air included. This is stricter than, and supersedes, the strip minima in mech_envelope §6.
- **BATT_N island:** its own pours on L1/L4. L2 stays GND underneath, which is acceptable: a plane at a different potential under an island is not a short. DRC's net-short check enforces separation.

## 7. Placement rules applied

- Hot loops on L1, input and output caps on the IC's layer (TPS61178 §11.1, p.30; BQ25792 §12.1 items 1–4, p.135; TPS62933 §12.1, p.40).
- Decoupling ≤ 1 mm (TAS5805M PVDD 0.1 µF) and ≤ 3 mm (10 µF) from the pins (SLASEH5D §9.1.2, p.89).
- Passives in rows with one orientation per row.
- Test points on **B.Cu** on a 2.54 mm grid from the board origin (60, 75), for a bed-of-nails fixture.
