# HRO TYPE-C-31-M-12 — USB Type-C 16-pin receptacle, USB 2.0 (J601)

## 1. Sources

| Item | Value |
|---|---|
| Part | Korean Hroparts (HRO) TYPE-C-31-M-12, LCSC **C165948**. 16P mid-mount/SMT receptacle with 4 shell through-hole tabs. Rated 5 A / 20 V. |
| Document | HRO drawing **"TYPE-C-31-M-12", rev. A, drawn 2020-12-08** ("DETECTOR SWITCHS" title-block typo). 1 sheet, AutoCAD PDF, no document number. |
| Durable copy | `kb/datasheets/src/local_cache_20261124/hro_type-c-31-m-12_drawing.pdf` (from the session cache `pw/typec.pdf`) |
| Fetch attempts | `https://datasheet.lcsc.com/lcsc/1811131825_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf` and the `lcsc.com/datasheet/…` variants returned an **HTML page, not a PDF** (2026-11-24). The cached drawing was used. |
| General USB-C layout guidance | Tried ST AN4871 "USB Type-C protection and filtering". **Fetch failed:** st.com dropped the connection or timed out, and the Mouser mirror returned HTML. **No third-party USB-C layout guidance is cited here**; the rules below come only from the HRO drawing and the attached-IC datasheets. |
| Figure render | `kb/datasheets/fig/hro_typec31m12_landpattern_zoom.png` |

## 2. Layout guidance on the drawing ("RECOMMEND P.C.B LAYOUT (COMPONENT SIDE)")

The drawing has no written layout rules. The recommended land pattern is the guidance. Dimensions below are as read from the drawing at 300 dpi.

1. **PCB-layout tolerance ±0.05 mm** (drawing note under the land pattern).
2. **12 SMT signal pads at 0.50 mm pitch**, in one row, labelled left to right (component side): A1/B12, A4/B9, B8, A5, B7, A6, A7, B6, A8, B5, B4/A9, B1/A12.
   - **8 pads 0.30 mm wide** (single signals). Dimension "8-0.30".
   - **4 pads 0.60 mm wide** (paired GND and VBUS pads at both ends). Dimension "4-0.60".
   - Pad-row reference spans of 2.50, 3.50 and 4.80 mm are dimensioned between symmetric pad pairs (4.80 appears to be A4/B9 ↔ B4/A9 centres; the other references are not unambiguous in the drawing).
3. **Pad length:** not dimensioned directly. "0.50" (pad bottom → locating-hole centre) and "1.64" (pad top → hole centre) imply about **1.14 mm**. **Verify against the KiCad footprint** (KiCad uses longer pads for toe fillets).
4. **2 non-plated locating holes Ø0.60 mm**, 5.78 mm apart.
5. **4 shell tabs in plated slots** at 8.65 mm centre-to-centre (across the connector):
   - Front pair: slot 0.60 × 1.70 drill, 0.90 × 2.00 copper (from "0.60/0.90" and "1.70/2.00").
   - Rear pair: 0.60 × 1.40 drill, 0.90 × 1.70 copper.
   - The drawing gives "4.18" between the front slot row and the rear slot centres, and "5.79" from the hole row to the **PCB edge**.
6. **PCB edge:** the land pattern is referenced to the board edge (5.79 mm from the locating-hole row). The receptacle is a board-edge part; the mating face sits at the edge.
7. **Pin map** (table on the drawing):
   - A1/B12/B1/A12 = GND; A4/B9/A9/B4 = VBUS
   - A5 = CC1, B5 = CC2
   - A6/B6 = DP1/DP2, A7/B7 = DN1/DN2
   - A8/B8 = SBU1/SBU2
8. Electrical ratings (notes): **5 A current, 20 V**, insulation 100 MΩ, 100 V AC dielectric withstand. **IR reflow: board peak held for 10 s at 260 °C.**

## 3. Example layout

None beyond the land pattern above.

## 4. Mechanical / thermal

- The 4 shell slots are the mechanical anchors. Fill them with solder (THT); they are electrically the shell.
- At 5 A, each VBUS/GND contact pair carries the current through 0.60 mm pads. Fan out with wide copper directly off the pad ends.
- Overall body: 8.94 mm wide; 7.35 mm long (top-view outline dimensions on the drawing).

## 5. Applied to this board (J601, spec_power v1.3 §1 and §6)

| Check | Value / rule | Basis |
|---|---|---|
| Footprint | KiCad `USB_C_Receptacle_HRO_TYPE-C-31-M-12`. Check pads (0.3/0.6 × 0.5 pitch), Ø0.6 NPTH at 5.78, slots 8.65 apart against the drawing (±0.05) | HRO drawing |
| Board edge | Receptacle front flush with the board edge as drawn (5.79 mm hole-row-to-edge) | HRO drawing |
| D+ / D− | A6–B6 and A7–B7 each **joined right at the receptacle**, then one coupled pair to U601 → U201. Stubs from the B-row pads as short as the footprint allows. | Pin map; CH340C.md §2 |
| CC1/CC2 | A5 / B5 directly to U602 (ESD) then CH224Q pins 7/6 | Pin map; CH224Q.md |
| VBUS/GND | Pour from the four 0.60 mm pads plus the shell to wide copper. Sized for the PD contract current (see spec_power §1.3), max 5 A connector rating. D601 TVS and C601 within a few mm (spec "within 5 mm", project rule). | Ratings note; spec §6 |
| Shell | Tie the slots to GND (or chassis), with stitching vias next to the slots | Project practice |
| Reflow | ≤ 260 °C for 10 s at the board (JLC standard profile is compatible) | Note 6 |

## 6. Spec cross-check

- Spec §1.1: "20 V 5 A, C165948": **consistent** with the drawing notes.
- Spec §6 "D601, U601 and U602 within 5 mm of J601" and "D+/D− 90 Ω differential pair" are **project rules**. Neither HRO nor the cached UMW USBLC6-2SC6 sheet (`pw/usblc6.pdf`) gives a placement distance. A general Type-C/ESD app note could not be fetched (see §1).
