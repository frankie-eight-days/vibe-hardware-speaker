# ESP32-WROVER-E (N8R8) — Wi-Fi/BT module with PCB antenna (U101)

## 1. Sources

| Item | Value |
|---|---|
| Part | Espressif ESP32-WROVER-E-N8R8, 18.0 × 31.4 × 3.3 mm, 38 castellated pins + 9-pad GND EPAD (pin 39) |
| Doc A | **ESP32-WROVER-E & ESP32-WROVER-IE Datasheet v2.4**, 53 pp. Fig. 5 pin layout, Fig. 11 peripheral schematic, Fig. 12 dimensions, **§11 PCB Layout Recommendations** (Fig. 15 land pattern, §11.2 placement). |
| Doc B | **Espressif "ESP Hardware Design Guidelines", ESP32 edition, "Release master", PDF dated Nov 12 2026**, 38 pp. **§1.4.8 "General Principles of PCB Layout for Modules (Positioning a Module on a Base Board)"**. The old URL `espressif.com/.../esp32_hardware_design_guidelines_en.pdf` now redirects to the HTML docs. The PDF was fetched from https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/esp-hardware-design-guidelines-en-master-esp32.pdf on 2026-11-24 (treated as untrusted data; content read, nothing executed). |
| Durable copies | `kb/datasheets/src/local_cache_20261124/esp32-wrover-e_datasheet_v2.4.pdf`; `kb/datasheets/src/web_fetch_20261124/esp-hardware-design-guidelines-en-master-esp32.pdf` (+ `espressif_hdg_pcb-layout-design.html`) |
| URL (Doc A) | https://espressif.com/documentation/esp32-wrover-e_esp32-wrover-ie_datasheet_en.pdf |
| Figure renders | `kb/datasheets/fig/wrover_p45_fig15_landpattern.png`, `esp32_hdg_p30_fig23_placement.png`, `esp32_hdg_p32_fig25_keepout_zoom.png` |

**Page convention:**
- Doc A: "p.N" is the PDF page; the printed page is N−1 (e.g. Fig. 15 is PDF p.45 = printed p.44).
- Doc B: "p.N" is the PDF page; the printed page is N−3 (e.g. §1.4.8 is PDF p.30 = printed p.27).

## 2. Layout guidelines

### Module placement and antenna (Doc B §1.4.8, p.30–32; Doc A §11.2 p.46 defers to it; Doc A Fig. 5 Note A p.12 likewise)

1. **Put the module's PCB antenna outside the base board**, with the **antenna feed point close to the board edge**. In Fig. 23 (p.30), only positions ③ (antenna overhanging the top edge, feed point at the corner) and ④ (antenna overhanging the side edge at a corner) are marked recommended. Antenna over the board (①, ②) and ⑤ are not recommended (p.30, §1.4.8).
2. If the antenna cannot extend past the edge, **keep the feed point as close to the edge as possible and cut away the base board on both sides of and below the antenna**. **Do not** put the module in the middle of the board with a clearance hollowed out on all four sides (p.30).
3. **Fig. 25 clearance** (p.32), base-board cut-out (red dashed "Clearance Area"):
   - The cut-out extends **≥ 15 mm ("Min15")** beyond the antenna on the side **away from the feed point**.
   - Antenna region depth is **6.19 mm**.
   - Two small limits on the feed-point side: **"Max 2"** horizontally, between the clearance edge and the module edge, and **"Max 1"** vertically, at the antenna's outer edge. The drawing does not say what they reference; read them as "the board may extend at most 2 mm / 1 mm into those regions". **This is an interpretation; verify against the HDG HTML or ask Espressif if it matters.**
4. **Put sufficient ground copper and dense ground vias on the base board near the antenna** (p.30).
5. **Enclosure:** the antenna needs a clearance area inside the housing as well. **"A clearance of at least 15 mm is recommended in all directions"** (p.30). This sentence is about the **housing/enclosure**, not about copper on the PCB.
6. Test the final product for throughput and range (p.30).

### Module footprint and keep-out (Doc A)

7. The **antenna keep-out zone** is the dotted area on Fig. 5 (p.11–12, Note A). The WROVER-IE has no keep-out.
8. **Fig. 15 land pattern** (p.45, §11.1):
   - Module 18 × 31.4 mm. **"Antenna Area" 18 × 6.22 mm** at the pin-1/38 end; 7.44 mm from the module edge to the pin-1 pad centre-line.
   - Pads **38 × 1.5 × 0.9 mm at 1.27 mm pitch**, extending 0.5 mm outside the module outline.
   - Pad columns 17.5 mm apart (centre-to-centre).
   - First pad 1.1 mm from the module edge (at the 19/20 end); 22.86 mm pin-1-to-19 span.
9. **EPAD (pin 39, GND):** **3 × 3 array of 0.9 × 0.9 mm pads with 0.5 mm gaps, 3.7 × 3.7 mm overall.**
   - Its centre is **7.5 mm** from the module's pin-1–19 edge and **16.16 mm** from the pin-19/20 end.
   - Fig. 15 shows **small "via for thermal pad" circles in the gaps between the 9 sub-pads** (12 vias drawn).
   - Doc A p.40 (§9 notes): "**Soldering the EPAD to the ground of the base board is not a must, however, it can optimize thermal performance.** If you choose to solder it, apply the correct amount of solder paste. Too much paste may increase the gap between the module and the base board, and the other pins may then adhere poorly."

### Decoupling and peripherals (Doc A §9 Fig. 11, p.40)

10. **3V3 (pin 2): C1 = 22 µF and C2 = 0.1 µF to GND** (R1 "TBD" footprint in series is optional).
11. EN: RC delay, R = 10 kΩ, C = 1 µF (adjust for power-up timing). C4 = 0.1 µF is on the reset button. IO12 must be low at power-up.
12. Doc B (chip-level, also applicable to the 3V3 feed): **10 µF on the rail** is "highly recommended" (p.10). Doc B's 4-layer chip-layout rules (p.22–23: power traces ≥ 20 mil, etc.) apply to chip-down designs, not module-on-board.
13. UART: **U0TXD/U0RXD short on the top layer, surrounded by ground copper and ground-via stitching** (Doc B p.28–30, §1.4.7).
14. **Supply ripple target at the chip while transmitting:** **< 80 mV p-p** (11n MCS7) and **< 120 mV p-p** (11b 11 MHz). If ripple is the cause of poor TX, add a 10 µF cap close to the analog supply (Doc B p.34, §1.4.11). Keep crystals, UART/SDIO traces and inductors away from the antenna (same section).

## 3. Example-layout description

- **Doc B Fig. 23 (p.30), "Placement of ESP32 Modules on Base Board (antenna feed point on the right)".**
  - Five candidate positions.
  - ✓③: module at the top edge, **right corner**, antenna fully outside the board, feed point (right end of the antenna) at the board corner.
  - ✓④: module at the bottom-right corner, rotated 90°, with the antenna hanging off the right edge.
  - ①/②: antenna overhang at the top-left or centre, feed point not at a corner. ⑤ is mirrored to the left side. None of these is recommended.
  - Fig. 24 (p.31) is the mirror set for modules whose feed point is on the left.
- **Doc B Fig. 25 (p.32), "Keepout Zone for ESP32 Module's Antenna (antenna feed point on the right)".**
  - The base board is drawn with a notch: the module sits at the top-right; the antenna (6.19 mm deep) is level with the top edge.
  - The board material to the **left of the antenna is removed for ≥ 15 mm**, and the notch's lower edge is level with the bottom of the antenna region.
  - On the right, the board edge is at most "Max 2" mm outside the module; vertically the clearance goes "Max 1" mm beyond the antenna top.
- **Doc A Fig. 15 (p.45):** the land pattern as in item 8–9, with the 9-pad EPAD and its gap vias.

**WROVER-E feed-point side.** WROVER-E Fig. 5 (p.11) shows the antenna at the pin-1/38 end. The datasheet does not state the feed point's left/right position; determine it from the module's 3D model or a photo before choosing Fig. 23 position ③ vs. its mirror.

## 4. Thermal pad / vias / land pattern summary

- EPAD: 9 × (0.9 × 0.9) pads, 0.5 mm gaps, 3.7 mm square. GND vias in the gaps (Fig. 15). Soldering is **optional** but improves thermal performance; control paste volume (p.40).
- Signal pads 1.5 × 0.9 mm at 1.27 mm, 0.5 mm outside the outline (p.45).
- Antenna Area 18 × 6.22 mm (Doc A p.45) vs. 6.19 mm (Doc B Fig. 25): **0.03 mm difference between Espressif's two documents**. Use the larger.
- MSL 3, 168 h floor life; single reflow, peak 235–250 °C (Doc A p.47, §12).

## 5. Applied to this board (U101, spec_signal v1.2 §1)

| Check | Value / rule | Basis |
|---|---|---|
| Module position | At a board **corner**, antenna end overhanging (preferred) or flush, **feed point at the corner** | Doc B Fig. 23 ③/④ |
| Copper under the antenna | None on **any layer** within the 18 × 6.22 mm antenna area (or 6.3 mm per the KiCad footprint). No board material either, if overhanging. | Doc A Fig. 5/15; Doc B §1.4.8 |
| If not overhanging | Board cut-out ≥ **15 mm** on the side away from the feed point, flush with the antenna depth; board edge ≤ 2 mm beyond the module on the feed side | Doc B Fig. 25 |
| Enclosure | ≥ **15 mm** clearance from the antenna to metal, grilles and batteries in all directions inside the housing | Doc B p.30 |
| GND near the antenna | Solid GND pour plus dense stitching vias along the module's antenna-side edge, on the board side only | Doc B p.30 |
| C101 (22 µF) + C102 (100 nF) | At pin 2 (3V3), with GND vias at the cap pads; C102 nearest | Doc A Fig. 11 |
| EPAD | Pads and gap vias into L2 GND (Fig. 15 pattern). Paste reduced (window-pane per sub-pad, not 100 %) to avoid lifting the module. | Doc A p.40, p.45 |
| UART TX/RX | Top layer, short, GND-guarded | Doc B §1.4.7 |
| +3V3 ripple at pin 2 | < 80 mV p-p during Wi-Fi TX (measure at C102) | Doc B §1.4.11 p.34 |
| Noise sources | Boost/charger inductors, PVDD and speaker leads away from the antenna end (project rule) | spec §1.6 |

## 6. Spec cross-check (spec_signal.md §1.6 and §1.7)

- **Discrepancy (important):** spec §1.6 says "add a **board-level keep-out of ≥ 15 mm around the antenna in the plane of the board** (Espressif HW design guidelines, 'Positioning a module on a base board')". The HDG says something different:
  - (a) the **≥ 15 mm "in all directions"** is a **clearance inside the housing**, not a PCB copper keep-out (p.30);
  - (b) the in-plane 15 mm figure is a **base-board cut-out on one side** of a non-overhanging antenna (Fig. 25, p.32).
  
  If the antenna overhangs the edge (Fig. 23 ③), no 15 mm in-plane keep-out is required; the requirement is no copper or board under the antenna area plus enclosure clearance. Requiring 15 mm of empty copper around the antenna on the PCB is stricter than Espressif and costs board area, though it is not harmful.
- §1.6 "Stitch the EPAD … to GND": acceptable. Espressif says it is **optional** and warns about excess paste (Doc A p.40). Add a paste-reduction note.
- §1.7 "Antenna keep-out … y = −15.695 … −9.395 (6.3 mm deep)": Doc A Fig. 15 says **6.22 mm** and Doc B Fig. 25 says **6.19 mm**. The 6.3 mm is from the KiCad footprint. It is conservative, so keep it.
- §1.7 EPAD geometry (3 × 3 × 0.9 mm, 0.5 mm gaps, 3.7 mm, centre 7.5 mm / 16.16 mm): **matches** Fig. 15 (p.45). The spec's "7.5 mm from the pin-1 edge" means the pin-1…19 long edge.
- §1.7 pads "1.5 × 0.9 mm, pitch 1.27, protrude 0.5 mm": **matches** Fig. 15.
- §8 cites "§11.2 placement": correct, but §11.2 (Doc A p.46) only defers to the HDG; the actual rules are in Doc B §1.4.8.
