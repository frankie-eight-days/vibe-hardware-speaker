# NCEP3065QU — 30 V / 65 A N-MOSFET, DFN3.3 × 3.3-8L (Q701 ship FET; Q801/Q802 protection FETs)

## 1. Source

| Item | Value |
|---|---|
| Part | Wuxi NCE Power NCEP3065QU, DFN3.3X3.3-8L |
| Document | NCE datasheet **V6.0**, 7 pp. ("Microsoft Word - NCEP3065QU1 data sheet.doc") |
| Durable copy | `kb/datasheets/src/local_cache_20261124/ncep3065qu_V6.0.pdf` |
| URL | http://www.ncepower.com (product page; PDF obtained via LCSC C502964 in the session cache) |
| Figure render | `kb/datasheets/fig/ncep3065qu_p5_package.png` |

Page numbers are PDF pages, and they equal the printed "Page n".

Pins (p.1, top/bottom view and schematic): **1, 2, 3 = S; 4 = G; 5, 6, 7, 8 = D**. The large bottom pad is the drain and is continuous with pins 5–8.

## 2. Layout guidance

**The datasheet has no layout section.** Thermal ratings are the only layout-relevant data:
1. **RθJC = 2.3 °C/W** (p.1, Thermal Characteristic). PD = 55 W and ID = 65 A are at TC = 25 °C, which is not achievable on a PCB.
2. Note 2 (p.2): "RθJA is measured with the device **mounted on 1 in² FR-4 board with 2 oz copper**, still air, TA = 25 °C." **No RθJA value is printed** anywhere in V6.0. The note references a missing table entry, which is a datasheet defect.
3. RDS(on) is 1.9 mΩ typ. at VGS = 10 V and 3.0 mΩ typ. at 4.5 V (p.1). Conduction loss, not switching, dominates in this application.

## 3. Example layout

None.

## 4. Package and land pattern (p.5, "DFN3.3X3.3-8L Package Information")

- Body **D 3.35 × E 3.20 mm** nominal (D1 3.10, E1 3.15); height A 0.75.
- Leads **b 0.30 mm** at **e 0.65 mm**, length **L 0.40**.
- **Drain pad D2 1.88 × E2 2.49 mm** nominal (1.78–1.98 × 2.39–2.59).
- H 0.39 (pad-to-lead gap reference); θ 10–12°.
- **No recommended land pattern or via pattern** is given. The project uses TI's `VSON-8_3.3x3.3mm_P0.65mm_NexFET` pattern (CSD17581Q3A) as a substitute; check its drain pad covers 1.88 × 2.49 and its lead pads suit b = 0.30 / L = 0.40.

## 5. Applied to this board

| Check | Value / rule | Basis |
|---|---|---|
| Drain pad copper | Large pour on the drain (pins 5–8 + pad). Thermal vias in the pad (tented or plugged, JLC via-in-pad) into a **same-net** island on the inner/bottom layers. | p.2 note 2 (1 in² 2 oz reference) |
| Q801 (over-discharge recovery, ≈ 1.5 W) | ≥ 2 cm² on the drain tab and on the BATT_N source copper (spec), with thermal vias into matching islands, **never into GND for BATT_N** | spec §6; RθJC p.1 |
| Q802 / Q701 (conduction only) | At 7 A and ≈ 2.5–3 mΩ hot: ≈ 0.15 W each. Copper for current (≥ 3 mm traces or pours, spec), not heat. | p.1 RDS(on) |
| Gate (pin 4) | Short trace from DOUT/COUT/SDRV; DNP C720/C721 next to Q701 gate (spec) | spec §6 |
| Footprint check | Lead pads 0.65 pitch; drain pad ≥ 1.88 × 2.49 | p.5 |

## 6. Spec cross-check

- Spec §0: "NCE DFN3.3×3.3-8L: pitch 0.65, lead 0.30, drain pad 2.49 × 1.88 (NCE p.5)": **matches** p.5.
- Spec §0 pin mapping "1-2-3 S, 4 G, 5 D": **matches** p.1.
- Spec §6 "Q801 needs copper for 1.5 W … ≥ 2 cm²": project estimate. **NCE gives no RθJA to verify it**; only the 1 in² / 2 oz test condition is stated.
