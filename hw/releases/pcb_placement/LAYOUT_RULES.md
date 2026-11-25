# Main board layout rules (speaker_main, layout rev A, 2026-11-24)

These rules come before placement and routing. Each number cites its source: the fab capability page, the stackup, a calculation in this file, or a datasheet layout section from `kb/datasheets/` (with page numbers). The KiCad project carries the net classes and board minimums from this file. Items that Konnect cannot write into KiCad are flagged **[not in DRC]**; those are checked by hand or by script.

## 1. Fabrication contract: JLCPCB 4-layer, 1.6 mm

Source: jlcpcb.com/impedance and jlcpcb.com/capabilities/pcb-capabilities, both read on 2026-11-24.

| Layer | Material | Thickness | Er |
|---|---|---|---|
| L1 top (F.Cu) | Cu, 1 oz finished | 0.035 mm | |
| Prepreg | 7628 ×1 | **0.2104 mm** | 4.4 |
| L2 (In1.Cu) | Cu, 0.5 oz | 0.0152 mm | |
| Core | "1.1 mm H/HOZ with copper" | 1.065 mm | 4.6 |
| L3 (In2.Cu) | Cu, 0.5 oz | 0.0152 mm | |
| Prepreg | 7628 ×1 | 0.2104 mm | 4.4 |
| L4 bottom (B.Cu) | Cu, 1 oz finished | 0.035 mm | |
| Solder mask | | 0.6–1.2 mil | 3.8 |

- **Order as JLC04161H-7628**, 1.6 mm, 1 oz outer, 0.5 oz inner, ENIG (ENIG suits the 0.4 mm QFNs and the fine pitch of the TSSOP thermal pads).
- Konnect has no stackup tool, so the KiCad Board Setup → Physical Stackup still holds generic values. **[not in DRC]** The fab notes and this table are the authority.

| JLC capability (multilayer, 1 oz) | Value | Used here |
|---|---|---|
| Min trace / space | 0.09 / 0.09 mm | **0.127 / 0.127 mm** board minimum, 0.15 mm default clearance |
| Min via hole / diameter | 0.15 / 0.25 mm, with a surcharge below 0.3 mm unless the via diameter is ≥ 0.45 mm | Standard via **0.3 / 0.6 mm**. Fine via **0.25 / 0.5 mm**, used only where the BQ25792 SW/GND fan-out under the IC needs it; it is surcharge-free because the diameter is ≥ 0.45 mm |
| Via hole-to-hole | 0.2 mm | 0.25 mm |
| Copper to routed edge | ≥ 0.2 mm | 0.3 mm |
| Silkscreen | Line ≥ 0.15 mm, text ≥ 1.0 mm | Board text 1.0–1.5 mm |
| Via-in-pad (POFV) | Option on 4-layer: epoxy- or copper-filled and capped | **Not used**, except the TAS5805M PowerPAD thermal vias (§5) |

## 2. Layer use

| Layer | Use |
|---|---|
| L1 F.Cu | Every component (single-sided JLC assembly) except the bottom test pads. Power-stage hot loops, switch nodes, short signals. GND pour in the leftover space, stitched to L2. |
| L2 In1.Cu | **Solid GND, no traces**. The only voids are the via and hole antipads and the antenna keep-out. |
| L3 In2.Cu | Power pours: PVDD (middle band), VSYS (front strip, charger → boost → buck), VBAT_PACK (front-right, fuse → ship FET), +3V3 (rear strip and the ESP32 end). GND fill between them. A few slow signals. The charger SW1/SW2 links run here, from vias under U701 to L701, per TI SLUSDV2C §8.4.1 item 2 (p.139). L4 is kept clear directly above them. |
| L4 B.Cu | Signals (the long SPI/PDM/ENC bus to J501, I2C, slow control), bottom test pads, duplicate high-current pours (VBAT_PACK, BATT_N island). The GND pour fills the rest, stitched to L2. |

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
| USB_DIFF | USB_DP, USB_DN | FS 12 Mb/s | **0.28, gap 0.20** | 0.20 | 0.6/0.3 (none planned) | 90 Ω differential on L1 over L2 (§4) |
| CLOCK | I2S_BCLK, I2S_BCLK_MCU, IO26_R, LCD_SCLK, IO18_R, PDM_CLK, IO32_R | edge-rate limited | 0.20 | 0.25 | 0.6/0.3 | spec_signal §4.4: ≥ 3× width from other signals; series R at the source (68 Ω SPI/PDM, 33 Ω I2S) |

- The diff-pair gap (0.20 mm) and the 3W spacing for CLOCK are fixed by construction, because Konnect's `create_netclass` exposes only width, clearance and via. **[gap not in DRC]**
- **Class clearances are capped by the fine-pitch footprints.** KiCad checks pad-to-pad gaps inside a footprint against the larger of the two net classes. The tightest gaps are BQ25792 (0.4 mm pitch, 0.2 mm pads: 0.20 mm), CH224Q (0.20 mm), TAS5805M (0.25 mm) and TPS61178 (0.25 mm; the bars are 0.30 mm apart). So power classes use 0.20 mm, and SWITCH/CLOCK use 0.25 mm. Wider spacing to sensitive nets is a placement and routing rule, checked by review, not by DRC.
- BATT_N must never touch GND (spec_power §6). DRC's short check enforces this, because BATT_N and GND are different nets. Its 0.25 mm class clearance keeps pours apart.

## 4. Controlled impedance: USB D+/D− (90 Ω ±10 %)

I wrote a 2-D finite-difference Laplace solver for edge-coupled microstrip on L1 over L2: `hw/mainboard/layout_src/zsolve.py`, red-black SOR in numpy.
- Inputs: h = 0.2104 mm, Er 4.4, t = 0.035 mm, mask 15 µm at Er 3.8.
- Validation:
  - Single 0.36 mm trace: 50.8 Ω without mask, against 51.0 Ω from Hammerstad–Jensen (0.4 %).
  - Air microstrip at w/h = 1: 119.8 Ω, against about 122 Ω from Wheeler with thickness correction (−2 %).

| w / s (mm) | Zdiff |
|---|---|
| 0.20 / 0.13 | **88.6 Ω** |
| 0.18 / 0.13 | 94.0 Ω |
| 0.20 / 0.15 | 98.2 Ω |
| 0.24 / 0.15 | 92.5 Ω |

- Extra runs at a 0.20 mm gap: 0.28 / 0.20 gives **89.6 Ω**; 0.30 / 0.20 gives 87.3 Ω; 0.32 / 0.20 gives 85.2 Ω.
- **Chosen: w = 0.28 mm, s = 0.20 mm, which gives 89.6 Ω (−0.4 %).** I took the 0.20 mm gap over the 0.13 mm option (88.6 Ω) so that the pair gap equals the net-class clearance. DRC then checks it, and the USB-C A6/A7 pads (0.20 mm apart) need no exception.
- The pair runs on L1 over unbroken L2 GND, at least 0.5 mm from other copper, with no vias and no stubs.
- Length: about 20 mm (J601 → U601 → U201), well under spec_signal §2.6's < 50 mm.

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
