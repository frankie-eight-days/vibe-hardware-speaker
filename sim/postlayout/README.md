# Post-layout physics checks (rev A hybrid vs autoroute-only)

Field-solver and FD scores of the routed copper. Boards: `hw/experiments/hybrid_final` (hybrid, rev A) and `hw/experiments/autoroute_only` (Freerouting only). Both boards were copied to `work/` and read with KiCad 10's `pcbnew` API. Nothing in `hw/` was opened or changed.

**Re-run on a new board** (analyses 2–5 take about 2 min; `--full` adds the FastHenry runs, about 20 min):

```
./run_all.sh path/to/speaker_main.kicad_pcb revb [--full]
```

Figures from a re-run get a `_revb` suffix, and `summary.py` prints the comparison table. Figures are in `docs/figures/postlayout/` and numbers in `results/*.json`.

**Tools.** FastHenry 3.0.1 is built from source in `tools/` (5.8 MB). Run it with `-p off`: the default preconditioner spends more than 6 min on `spGetElement` for a 15 k-segment mesh, against 9 s without it. The rest is numpy/scipy in the project venv. openEMS was not installed. Homebrew has no core formula for it, and it needs VTK, HDF5, CGAL and Boost, which is more than 1 GB on a disk with 8 GB free. There is therefore no full-wave cross-check. CalculiX was not used; the thermal model is checked against an analytic case instead.

## Results: hybrid vs autoroute

| Metric | Hybrid (rev A) | Autoroute-only | Target / limit |
|---|---|---|---|
| Boost hot loop SW→VOUT→C914→PGND, nH | **0.20** | 0.35 | small |
| Buck input loop VIN→C953→GND, nH | **0.42** | open (unrouted) | |
| Charger PMID→C707→GND, nH | **0.22** | open (unrouted) | |
| Charger SYS→C716→GND, nH | **0.66** | open (unrouted) | |
| Boost V_SW peak, 2 ns edge, incl. C914 ESL | 20.8 V | 21.4 V | 23 V abs max (SLVSDA7E p.4) |
| SW area (total / without inductor pad), mm²: boost, buck, chg SW1, chg SW2 | 25/8, 12/8, 36/28, 40/32 | 25/8, 15/11, 10/1*, 28/20* | |
| SW capacitance to GND, pF: boost, buck, SW1, SW2 | 5.3, 3.1, 3.5, 2.8 | 0.7, 0.4, 0.4, 0.5 | |
| Fast-net length over a void, of 1.32 m | 249 mm | 1214 mm | 0 |
| Fast-net length on a split edge | 238 mm | 46 mm | |
| Extra return-loop area: voids + unstitched vias | 108 + 120 mm² | 3730 + 362 mm² | |
| Fast-net vias with no GND via ≤ 2 mm | 32 / 46 | 49 / 52 | 0 |
| Copper L1/L2/L3/L4 | 78/90/71/83 % | 20/15/14/11 % | |
| L1−L4 / L2−L3 (5 mm cells > 10 pts) | −5.2 (36 %) / **+18.9 (71 %)** | +9.9 (55 %) / +1.5 (43 %) | ≤ 10 pts |
| PVDD DC drop to amp L / R at 2.7 A each | 46 / 126 mV, pins open† | 66 / 154 mV | |
| PVDD hot spot | **405 A/mm²** (0.2 mm L4 track) | 454 A/mm² | |
| VSYS (charger → boost, 7 A) | **open** (3 islands) | open (6 islands) | |
| +3V3 drop at the ESP32, 0.5 A | 46 mV (92 mΩ) | 65 mV | |
| Battery path PACK_P / VBAT_PACK / CHG_BAT at 7 A | 5 / 29 / 18 mV, 361 mW | 39 / 114 / open mV | |
| GND battery return at 7 A | 20 mV, 142 mW | **2.05 V, 14 W** | |
| PVDD \|Z\| peak in the audio band, with copper | 0.195 Ω (pre-layout 0.159) | 0.202 Ω | 0.137 Ω |
| +3V3 \|Z\| max below 20 MHz | 0.22 Ω | 0.26 Ω | 0.30 Ω |
| Max sustained output for Tj ≤ 125 °C (h = 5 / 10 W/m²K) | **11 / 18 W** | 2 / 7 W | 40 W asked |
| U701 Tj, charging 2 A while playing (h = 5 / 10) | 148 / 122 °C | 278 / 224 °C | TREG 120 °C (SLUSDV2C p.13) |

\* The autoroute charger SW1 run to L701 is unrouted.
† U301 pins 27/28 and U401 pins 15/16 have no copper to PVDD (see fix 1).

The hybrid wins every metric where the autorouter completed the net, usually by a large factor. The autorouter's numbers are often "open": it never closed 3 of the 4 hot loops, VSYS or CHG_BAT, and its GND-as-traces battery return would burn 14 W at 7 A. The hybrid's weaknesses all come from the L3 fragmentation and the unclosed plane joins already listed in LAYOUT_NOTES §6. The solvers turn those DRC lines into volts, amps per mm² and kelvins.

## 1. Hot-loop inductance (FastHenry)

**Method.** `fh_loops.py`:
- Each loop's two nets are rasterised at 0.1 mm on all 4 layers and joined at every via (barrel-equivalent bar, 20 µm plating).
- The mesh keeps the copper within 2 mm of the shortest IC→cap→IC path, plus all other copper in that region as floating conductors, so the L2 image currents are included.
- The IC lands are `.equiv` (die/bars), the HF cap is an ideal short, and the port sits across the IC pins.
- L is reported at 100 MHz (ringing band).

**Validation** (`fh_validate.py`). A 0.5 × 10 mm L1 microstrip over L2, shorted at the far end, gives 2.78 nH, against 2.87 nH from Hammerstad–Jensen at the same filament spacing (−3 %). Centre filaments sit 25 µm further apart than the 100 MHz surface currents, so absolute values run 5–9 % high (conservative).

**Key numbers.** Boost **0.20 nH** (autoroute 0.35), buck 0.42, charger PMID 0.22, charger SYS **0.66 nH**. In the hybrid the SYS loop is 3× the PMID loop because C716 is rotated with its GND pad 3 mm from pin 27 (path 5.5 mm, against 2.5 mm for C707).

**Overshoot** = L·I/t_r. No rise time is given in SLVSDA7E, SLUSEA4D or SLUSDV2C. The TI TPS61178 PSpice model uses ideal switches, so it cannot supply one either. The table brackets t_r at 2–5 ns (TPS62933 abs max "SW transient < 10 ns", SLUSEA4D p.5) and uses the switch current at commutation:

| Loop | I (source) | PCB only, 2 / 5 ns | + 0.5 nH 0603 ESL, 2 ns | Peak vs abs max |
|---|---|---|---|---|
| Boost | 8.0 A, ILIM_SW typ (SLVSDA7E p.5) | 0.81 / 0.32 V | 2.8 V | 20.8 V vs 23 V (p.4): **pass, 2.2 V margin** |
| Buck | 1.23 A (spec_power 4.2.3) | 0.26 / 0.10 V | 0.57 V | 9 V vs 32 V (p.5): pass |
| Charger PMID | 6.1 A (spec_power 2.3) | 0.68 / 0.27 V | 2.2 V | 17 V vs SW1 30 V (SLUSDV2C p.7): pass |
| Charger SYS | 6.1 A | 2.0 / 0.81 V | 3.5 V | 12 V vs SW2 23 V (p.7): pass |

The cap body ESL (about 0.5 nH, assumed) is larger than the copper in three of the four loops. On these boards the cheapest overshoot reduction is a second HF cap or a low-ESL part, not more copper work. Package inductance is not included.

**SW nodes.** Most of the boost and buck SW area is the inductor pad. The charger SW1/SW2 runs are 28–32 mm² of non-pad copper with 7.3/7.4 nH partial inductance (L3+L4, 15 mm path, TI's own topology, SLUSDV2C p.139). That is the largest dv/dt antenna on the board (R4).

**Figures.** `hotloop_current_density` shows |J| per amp on L1 and L2. The image current under the hybrid loops is visible; the autoroute boost has none. `hotloop_L_bar` is the bar chart.

**Hybrid as designed vs as built.** The SES import changed signal routing near the power stages. The as-designed board is `hw/releases/pcb_critical_routed` (tag `designed`). `diff_power.py hybrid designed` compares the stage windows, and `results/diff_power_hybrid_vs_designed.json` has the detail.
- **L1 hot-loop copper:** identical. BST_SW, BUCK_SW, PMID and the C914/C953/C707/C716 lands show no difference above 0.05 mm². The differences are in the fills: L3 is solid VSYS/PVDD in the designed file, and the L1/L4 GND pours grow where the SES tracks are absent.

| Loop, nH at 100 MHz | Hybrid as built (rev A) | Hybrid as designed |
|---|---|---|
| Boost | 0.202 | 0.202 |
| Buck | 0.424 | 0.397 |
| Charger PMID | 0.222 | 0.222 |
| Charger SYS | 0.662 | 0.662 |
| Charger SW1 / SW2 area, mm² | 36 / 40 | 45 / 45 |
| Charger SW1 / SW2 run, partial nH | 7.3 / 7.4 | 6.5 / 6.5 |

- **The hot loops are unchanged** apart from the buck (−6 %, from the larger GND fill).
- **Charger SW links on L3.** In rev A the L3 copper of the SW links is narrower: 6.4 mm² against 14 mm² for SW1, because PDM_CLK, PDM_DATA and AMPR_FAULT_N were autorouted through the gap between the SW1 and SW2 L3 links. They pass 0.22–0.24 mm from SW copper for about 4–10 mm each. That puts a 15 V, 750 kHz switch-node edge next to the PDM clock.
- **The as-designed file carries stale via nets.** These are pre-`native_finalize`, from Konnect finding 6. 14 vias in the stage windows change net between the two files:
  - (127.5, 91.7/94.1/96.5): GND in the designed file, PVDD in rev A.
  - (165.2, 104.4) and (169.6, 104.4): CHG_SW1/SW2 in the designed file, GND fence in rev A.
  - VSYS↔GND swaps at (125.6/126.8, 118.0), (127.5/133.5, 119.3), (133.0, 108.0), (126.26, 114.19) and (98.2, 114.6).
  - The SW1/SW2 area of 45 mm² in the designed file includes two of these vias.
  - **Rev B starts from this file, so these nets must be re-checked before routing.**

## 2. Return paths

**Method.** `return_paths.py` checks 27 fast nets: I2S, SPI, PDM, USB, the amp outputs, and the series-R nets.
- Every 0.1 mm of track is classified by the nearest reference layer, inside ±max(3h, w/2+h): GND, power plane, split edge, far plane only (inner layer), or void.
- For void runs, the extra loop area is (D_geodesic − D_straight)/2 · D_straight, with the geodesic taken through the reference GND copper.
- At a layer change, the nearest GND via must be ≤ 2 mm away.

**Hybrid result.** 249 mm over voids and 238 mm on split edges. 183 mm of that is B.Cu over the fragmented L3, the rev A issue. Also, 32 of 46 signal vias have no GND via within 2 mm (LAYOUT_RULES §5 asks for a pair beside each).
- Worst offenders: USB_DN's L1↔L4 jump at (144–151, 82.0), 4.6–5.6 mm from GND; LCD_MOSI/IO23_R near the ESP32 (6–7 mm); the I2S cluster at X 111–127, Y 97–111.

**Autoroute result.** 92 % of fast-net length has no plane at all. **Fail** for both boards. The hybrid fails on L3 and stitching, which rev B should fix.

**Figure.** `return_paths_map`.

## 3. Copper balance

**Method.** `copper_balance.py` rasterises all copper at 0.05 mm inside the outline (5 mm cells). The hybrid comes out 1–3 points above LAYOUT_NOTES §5, because via rings on inner layers are counted.

**Result.**
- Hybrid L1−L4 −5.2 points: **pass** globally, but 36 % of cells are off by more than 10.
- Hybrid L2−L3 **+18.9 points: fail**, and 71 % of cells fail. That is L3 signal routing again.
- Autoroute: balanced pairs (+9.9 / +1.5), but only 11–20 % copper on every layer.

**Figure.** `copper_balance`.

## 4. DC IR drop and post-layout PDN

**Method.** `ir_drop.py` runs a 2-D FD sheet solve per layer:
- Sheet conductance is σt (35 / 15.2 µm), with via barrels on their annular rings.
- The source pad is held at 0 V and loads draw their current.
- Hot-spot J excludes the terminal pads and via lands.

`pdn_fold.py` then puts the extracted R (DC solve) and L (FastHenry, 1 MHz, port at the regulator, far end shorted at the load) into the S7 rails (`sim/pdn`, Rc/Cc 100 k/15 nF per spec v1.3). The S7 PDN is the Python nodal model in `sim/pdn/pdn_lib.py`, not an ngspice deck; it is reused as is. The extracted R is the supply side only; the GND return is a plane on the hybrid.

**Hybrid results:**
- **PVDD:** amp L 46 mV / 15.8 mΩ / 8 nH; amp R 126 mV / 45 mΩ / 24 nH; 464 mW at 2×2.7 A.
  - **U301 pins 27/28 and U401 pins 15/16 are not connected to PVDD at all.**
  - All of U301's current goes through a 0.2 mm L4 track at (120.2–125.7, 92.4): **405 A/mm²**, about 2.8 A. That trace will overheat; IPC-2152 puts 0.2 mm / 1 oz at about 1 A for ΔT 20 K.
  - The L3 neck at (156.9, 90.6) carries 312 A/mm².
- **PVDD |Z|:** the bass-band peak rises from 0.159 Ω (pre-layout placeholders) to **0.195 Ω**, against 0.137 Ω: **fail**. The copper adds about 35 mΩ to a target that was already marginal.
- **VSYS: open.** Three islands:
  - {U701.25, C711–C716, TP701}
  - {L901.1, U901.12, C901–C903, U951.3, C951–C953}
  - {R951.1}
  - The boost and buck have no copper to the charger.
- **+3V3:** 46 mV (92 mΩ, 25 nH) to the ESP32. |Z| is 0.22 Ω against 0.30 Ω: **pass**.
- **Battery path at 7 A:** PACK_P 5 mV, VBAT_PACK 29 mV (201 mW; LAYOUT_NOTES estimated 70 mW), CHG_BAT 18 mV (237 A/mm² at the U701 BAT pins), BATT_N 3 mV, PROT_D 2 mV. The GND return is 20 mV. Copper total about 0.55 W, all **pass**.
- **Autoroute:** the GND return is 2.05 V / 14 W, and CHG_BAT is open.

**Figures.** `ir_drop_maps` (sheet current, all layers) and `pdn_postlayout`.

## 5. Thermal

**Method.** `thermal.py` is a 2.5-D FD model on a 0.5 mm grid with 4 copper nodes per column:
- In-plane conductance: k_Cu·t·copper fraction + FR4 0.8 W/mK.
- Through-plane: FR4 0.3 W/mK plus every barrel.
- h = 5 or 10 W/m²K on both faces to 45 °C. Component bodies are not counted as fins (conservative).
- Tj = board + P·ψJB: TAS5805M 8.1 (SLASEH5D p.7), TPS61178 14.5 (SLVSDA7E p.4), TPS62933 19.2 (SLUSEA4D p.6), BQ25792 9.7 (SLUSDV2C p.8), NCEP3065QU RθJC 2.3 (p.1).
- Losses:
  - Amp: 18 V × 32.5 mA idle (SLASEH5D p.8) plus P_out·(1/0.9 − 1). The η is read off Fig. 6-32, p.17.
  - Boost: 5.5 % of its output, 2.5 W at 40 W (spec_power §6).
  - U701 1.5 W and Q801 1.5 W (spec_power §6/§2.3).

**Validation.** The board heated uniformly gives 12.11 K/W, against 1/(2hA) = 12.05 K/W. Energy balance is 1.000.

| Hybrid, Tj °C (h = 5 / 10) | U301 | U401 | U901 | L901 (board) | U701 | Q801 |
|---|---|---|---|---|---|---|
| Moderate 2.9 W system | 89 / 75 | 81 / 69 | 84 / 70 | 78 / 64 | 70 / 57 | 64 / 53 |
| 40 W sustained | 229 / 169 | 207 / 151 | 263 / 203 | 202 / 142 | — | 143 / 91 |
| Charge 2 A + moderate | 108 / 82 | 113 / 88 | 107 / 81 | 101 / 76 | **148 / 122** | 87 / 64 |
| Q801 body-diode recovery 1.5 W | — | — | — | — | 107 / 88 | **132 / 110** |

The limit is the total heat into a sealed box, not local spreading. With h = 5–10, the 83 cm² board sheds only 0.08–0.17 W/K. The hybrid sustains **11 W (h 5) to 18 W (h 10)** of output with Tj ≤ 125 °C; 40 W sustained needs another heat path. Radiation in the box adds about 6–8 W/m²K at these temperatures, so h = 10 is the realistic end of the range.
- **No off-the-shelf LCSC heatsink fixes this.** The TAS5805M's top path is 21.8 K/W (p.7), and a clip-on heatsink still dumps heat into the same 45 °C air.
- What works is a gap pad from the L4 GND pour under U301/U401/U901 to the enclosure or a metal plate, or a firmware thermal limit. Music at a 12 dB crest factor averages far below 40 W.
- The charger exceeds TREG 120 °C at h = 5, so it will throttle charge-while-play.
- The autoroute board is 30–200 K hotter everywhere. With no planes, it cannot spread heat.

**Figure.** `thermal_maps` (h = 5).

## Layout fixes for rev B (priority order)

1. **Connect the open amp PVDD pins.** These are U301 pins 27/28 at (112.6, 101.2–101.8) and U401 pins 15/16 at (187.4, 101.2–101.8). Each needs ≥ 3 vias to the PVDD plane, next to its 0.1 µF cap. Today one pin pair per amp is unsupplied.
2. **Remove the 0.2 mm L4 PVDD track** at (120.2–125.7, 92.4), which carries all of U301's 2.8 A at 405 A/mm². Replace it with the planned ≥ 3 mm L4 PVDD spine from U901 to both amps.
   - Expected: amp R drop from 126 to about 35 mV, peak J below 60 A/mm², and PVDD |Z| back to the pre-layout 0.16 Ω.
   - Then apply Rc 150 k or more bulk at the amps to reach 0.137 Ω.
3. **Join VSYS:** U701.25/C711–C716 to L901.1/U901.12/C901–C903/U951.3, with ≥ 3 mm on L3 + L4 and ≥ 12 vias per layer change. Also join R951.1.
   - At 7 A, aim for < 30 mV. A 30 mm × 3 mm L1+L4 band gives about 17 mV.
4. **Rotate C716** at (168.5, 107.6–109.2) so its GND pad lands beside U701 pin 27, mirroring C707.
   - Expected: SYS loop 0.66 → about 0.25 nH, and boost-mode overshoot −60 %.
5. **Add a second 100 nF 0402 across PVDD–PGND at the bottom bar end of U901** (Y 102.2), with 2 GND vias at C914.2 (130.8, 97.7). The nearest GND via is now 3 mm away.
   - Expected: cap-ESL term halved, and the boost SW peak at 2 ns from 20.8 to about 19.8 V.
6. **Stitch the 32 fast-net vias** that lack a GND via within 2 mm (list in `results/return_paths_hybrid.json`).
   - First USB_DN at (144.0 / 149.8 / 150.8, 82.0), then the I2S cluster at X 111–127, Y 97–111, and LCD_MOSI/IO23_R at (71.9, 90.6) and (83.4, 86.6).
   - Expected: −120 mm² of return-loop area.
7. **Make L3 solid under the L4 signals** (the rev B plan). That removes about 183 mm of B.Cu-over-void and brings L2−L3 balance from +18.9 to < 10 points. Keep the L3 signals in the rear corridor with solid L4 GND over them.
8. **Shorten +3V3 to the ESP32**: a ≥ 1 mm L1/L4 trace from C957 (113, 118) to U101 pin 2 (64.2, 106.8), about 55 mm, in place of the 141 mm loop through the L3 fragments.
   - Expected: 92 → about 25 mΩ, 46 → 13 mV.
9. **Thermal path:** put a 0.5–1 mm gap pad (or a thermal pad on bare L4 GND, mask opened) under U301/U401/U901/U701 to the enclosure or an aluminium plate. Add 3×3 GND vias in the L4 pour under U701 (X 165–169, Y 110–114).
   - Otherwise, firmware limits: sustained output ≤ 11–18 W, and ICHG ≤ 1.5 A while playing.
10. **Rev B starts from `pcb_critical_routed`.** First re-apply the via-net restore (`native_finalize`) for the 14 vias listed in section 1. Then keep L3 signals out of X 162–172, Y 100–111, which leaves the charger SW1/SW2 links full width with no PDM or fault lines beside them.
11. **Minor:**
    - Widen the CHG_BAT neck at U701 pins 22/23 (237 A/mm², 169.9/111.2).
    - Widen the VBAT_PACK L4 band neck at (199.2, 118.6).
    - Keep the PDM/I2S runs at Y ≈ 120 at least 0.6 mm inside the GND pour edge.

## Files

| File | What |
|---|---|
| `extract_kicad.py` | pcbnew → JSON (KiCad Python; zones refilled in memory) |
| `pl_common.py` | stack-up, rasteriser, plotting |
| `fh_loops.py`, `fh_validate.py`, `fh_plots.py`, `diff_power.py` | analysis 1; `diff_power.py` diffs stage copper between two boards |
| `return_paths.py`, `copper_balance.py` | analyses 2, 3 |
| `ir_drop.py`, `pdn_fold.py` | analysis 4 |
| `thermal.py` | analysis 5 |
| `summary.py`, `run_all.sh` | comparison table, one-command re-run |
| `work/`, `tools/` | board copies, FastHenry decks and outputs, FastHenry build (gitignored, about 70 MB) |
