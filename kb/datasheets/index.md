# Datasheet layout knowledge base: index

Scope: PCB **layout** rules for the portable stereo BT speaker main board (4-layer, 1.6 mm, JLCPCB).

Compiled 2026-11-24 from the datasheets listed below. Every rule in the per-part files carries a page and section citation.
- "p.N" means the **PDF page**. TI and WCH printed pages equal the PDF pages; Espressif documents are offset (noted in that file).
- Numbers marked "project rule/target" come from `docs/spec_*.md`, not from a vendor.

## Files

| File | Part (refdes) | Primary document(s) | Most important layout rule |
|---|---|---|---|
| [TPS61178.md](TPS61178.md) | TPS61178 boost (U901) | TI **SLVSDA7E** (Aug 2019) §11, p.30; RNW0013A p.37–39 | Minimise the SW → VOUT → C_OUT → PGND loop on the top layer with the small cap nearest the bars. The bars are 0.25 mm wide at 0.55 mm pitch (0.30 mm gap), so the HF cap goes at the bar ends, not across them. (p.30 §11.1 #1; p.38) |
| [BQ25792.md](BQ25792.md) | BQ25792 charger (U701), also BQ25798 | TI **SLUSDV2C** (BQ25798, Jun 2026) §8.4 p.139–140; TI **ZHCSMD3C** (BQ25792 CN, Aug 2022) §12 p.135–136; EVM **SLUUCB5E** §3 p.14, §4.1 p.15–18. English SLUSDG1C **not fetchable** (TI 404). | 0.1 µF 0402/0201 caps on the IC layer directly across PMID–GND and SYS–GND with no vias. SW1/SW2 drop through vias under the IC to an inner layer to reach the inductor. (SLUSDV2C p.139 #1–2, Fig. 8-21 p.140) |
| [TPS62933.md](TPS62933.md) | TPS62933 buck (U951) | TI **SLUSEA4D** (Aug 2022) §12, p.40–41; DRL0008A p.48–50 | C_IN (0.1 µF + 10 µF) tight across VIN (3) – GND (4); all power parts on one layer; BST/FB/SS/RT traces > 10 mil. (p.40 §12.1) |
| [TAS5805M.md](TAS5805M.md) | TAS5805M amps (U301, U401) | TI **SLASEH5D** (Nov 2020) §9, p.89–91; PWP0028M p.99–101; EVM guide **SLOU510** (May 2018) Fig. 7/8 p.6–7 | PVDD HF caps no farther from pins 15/16 and 27/28 than in TI's example; distant caps cause ringing above the abs-max rating. PowerPAD: 3 × 8 × Ø0.2 mm vias at 1.2 mm, no thermal relief, paste 70–80 %. (p.89 §9.1.2; p.90–91 §9.1.3.2; p.100) |
| [ESP32-WROVER-E.md](ESP32-WROVER-E.md) | ESP32-WROVER-E-N8R8 (U101) | Espressif **WROVER-E/IE datasheet v2.4** §11 (PDF p.45–46), Fig. 11 (p.40); Espressif **ESP Hardware Design Guidelines (ESP32, release master, Nov 2026)** §1.4.8 (PDF p.30–32) | Antenna overhanging the board edge at a corner, feed point at the edge. No copper under the 18 × 6.22 mm antenna area. ≥ 15 mm **enclosure** clearance in all directions; ≥ 15 mm board cut-out only on the far side if the antenna cannot overhang. (HDG p.30, Fig. 23/25) |
| [CH224Q.md](CH224Q.md) | CH224Q PD sink (U603) | WCH **CH224DS1 v2.1** p.3, p.8, p.15 | No layout section. 1 µF (voltage-rated) at VHV pin 1, VBUS pin 8 shorted to VHV, EP = GND. (p.3 Table 4-1) |
| [CH340C.md](CH340C.md) | CH340C USB-UART (U201) | WCH **CH340DS1 V3D** §5.1 p.5, §7.1 p.10 | 0.1 µF at VCC (16), V3 tied to VCC at 3.3 V; D+/D− parallel with ground on both sides and **no series resistors**. (p.5, p.10) |
| [HRO_TYPE-C-31-M-12.md](HRO_TYPE-C-31-M-12.md) | USB-C receptacle (J601) | HRO drawing TYPE-C-31-M-12 rev. A (2020-12-08), recommended PCB layout. LCSC PDF and ST AN4871 **not fetchable**. | Land pattern ±0.05 mm: 12 pads (8 × 0.30, 4 × 0.60) at 0.5 mm pitch, Ø0.60 NPTH 5.78 apart, 4 shell slots 8.65 apart, referenced to the board edge. 5 A / 20 V. |
| [R5460N212AF.md](R5460N212AF.md) | R5460 2S protector (U801) | Ricoh **EA-165-160603** p.5, p.18 | No layout section. Mount C3 ≥ 0.01 µF; R1/R2 < 1 kΩ with C1/C2 ≥ 0.01 µF; R1 + R3 ≥ 1 kΩ, R3 ≤ 3 kΩ; VSS on the BATT_N island. (p.18) |
| [NCEP3065QU.md](NCEP3065QU.md) | NCEP3065QU N-FET (Q701, Q801, Q802) | NCE datasheet **V6.0** p.1, p.2, p.5 | No layout section and **no RθJA printed** (only RθJC 2.3 °C/W, with a "1 in² 2 oz" test note). Drain pad 1.88 × 2.49 mm needs a large same-net pour with vias. (p.1–2, p.5) |

## Sources on disk

- `src/local_cache_20261124/`: durable copies of the session-cache PDFs (TI, Espressif, WCH, HRO, Ricoh, NCE).
- `src/web_fetch_20261124/`: fetched 2026-11-24 and treated as untrusted data:
  - Espressif HDG PDF (`esp-hardware-design-guidelines-en-master-esp32.pdf`) and HTML pages
  - TI `slou510.pdf` (byte-identical to the cached copy)
- `fig/`: page renders of the layout figures cited in the files.

## Fetch failures (2026-11-24)

| Wanted | Result |
|---|---|
| TI BQ25792 English **SLUSDG1C** | ti.com `/lit/ds/symlink/bq25792.pdf`, `/lit/gpn/bq25792`, `/lit/pdf/slusdg1`: HTTP 404 to curl and WebFetch (TI bot block). Used the Chinese edition ZHCSMD3C plus BQ25798 SLUSDV2C. |
| HRO TYPE-C-31-M-12 from LCSC (C165948) | LCSC URLs returned HTML, not a PDF. Used the cached HRO drawing. |
| ST AN4871 (USB Type-C protection/layout) | st.com closed the connection or timed out; the Mouser mirror returned HTML. No general USB-C layout app note is cited. |
| Old Espressif `esp32_hardware_design_guidelines_en.pdf` URL | Redirects to HTML docs. The current PDF was fetched from docs.espressif.com instead. |

## Spec discrepancies found (details in each file's §6)

1. **ESP32 antenna keep-out (spec_signal §1.6).** The spec's "board-level keep-out ≥ 15 mm around the antenna in the plane of the board" misreads the HDG:
   - "≥ 15 mm in all directions" is **enclosure** clearance (HDG p.30);
   - the in-plane 15 mm is a **one-sided board cut-out** used only when the antenna cannot overhang (Fig. 25, p.32).
   
   Also, the antenna area is 6.22 mm (datasheet) / 6.19 mm (HDG), against the spec's 6.3 mm (conservative; keep it).
2. **TPS61178 C914 "directly across pins 8–6" (spec_power §6).** Not possible: bars 6 and 8 are 1.1 mm apart with the 0.25 mm SW bar between them. "0.55 mm apart" is the pitch, not the gap. Place C914 at the bar ends (Fig. 36). The footprint stencil is 87 % per TI p.39, not ≈ 90 %.
3. **BQ25792 (spec_power §6).**
   - The spec cites "SLUUCB5E §4"; the guidelines are §3, p.14.
   - The spec omits "SW1/SW2 via down under the IC to an inner layer" and "≥ 2 GND vias on the REGN/VBUS caps".
   - The spec uses 0603 for C707/C716; TI asks for 0402/0201.
   - "BTST within 1 mm" is a project number; TI's own example puts BTST caps on the bottom layer.
   - TI's documents also disagree with each other: EVM text names C3, but the fitted part is C32; vias on one side of the BTST caps (EVM) vs. both sides (SLUSDV2C).
4. **TAS5805M (spec_signal §3.6).**
   - The "0.5 mm via pad" is not in TI's drawing.
   - The 0.3/0.6 mm via fallback goes against TI's small-via ("8 mm", read as 8 mil) guidance.
   - Missing from the spec: "IC away from board edge", "radial via columns, no via strings across the heat path", "narrow end of passives toward IC".
   - TI's own docs conflict: the stencil addendum shows a single opening, while §9.1.3.2.2 asks for a 70–80 % aperture array.
5. **NCEP3065QU.** The spec's Q801 "≥ 2 cm² for 1.5 W" cannot be checked against the datasheet, because NCE prints no RθJA value.
6. **CH224Q "EP ≥ 2 vias", USB-C "ESD within 5 mm", "90 Ω pair".** These are project rules with no vendor source; they are labelled as such in the files.
