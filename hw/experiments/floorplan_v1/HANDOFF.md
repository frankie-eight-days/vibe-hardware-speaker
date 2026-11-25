# Hand-off: floor plan v1 → phase 2 (apply + route), 2026-11-25

**For:** the next layout owner (a fresh agent or a human).
**Read first:** `FLOORPLAN.md` (this folder), `hw/mainboard/LAYOUT_NOTES.md` §1.1–1.2 and §12, `docs/layout_principles.md`, and the PCB line in `docs/requirements.md`.
**Git tag:** `floorplan-v1`.

## 1. Where things stand

| Item | State |
|---|---|
| Schematic | v0.3 (ECO-004: C605 47 µF VBUS damping cap). ERC 0. Out: `hw/releases/mainboard_v0.3/`, `out/` |
| Stack-up | 6 layers, JLC06161H-1080B: L1 SIG / L2 GND / L3 SIG / L4 PWR / L5 GND / L6 SIG. USB 90 Ω at 0.115/0.15 mm |
| Floor plan v1 | **Done, offline.** `speaker_main.kicad_pcb` in this folder: all 272 parts placed, six power blocks carry their designed copper, L2/L5 solid GND, no other routing |
| Live board `hw/mainboard/speaker_main.kicad_pcb` | **Not changed.** Byte-identical to `hw/releases/pcb_04_revB_6L/02_konnect1` (old 180 mm placement, no C605) |
| Rev B 6-layer routing pipeline | Archived from scratch to `hw/mainboard/layout_src/r6/` (`design6.py`, `pipe.sh`, `n1.py`, `n2.py`, `bus6.py`, `fixstage.py`, `spec_fix.json`, `gates.sh` …). It was written for the **old** placement: reuse the tools and specs, not the coordinates |

Numbers: 142.8 × 46 mm (−21 %), top density 66.9 % (target 70 %, ceiling 78 % with rigid blocks). Hot loops: boost 0.173, buck 0.310, SYS 0.609 nH pass; **PMID 0.268 nH fails** (cause below). Thermal passes **only with gap pads**.

## 2. Owner decisions still open (ask before phase 2 starts)

The owner liked the floor plan ("looks unreal") but has **not** answered these. Recommendations in bold.

1. **ECO-003 gap pads** under U301/U401/U701 (15 × 15 mm, 3 W/mK, to a printed boss or Al plate). The shrink is only thermally valid with them. **Recommend: adopt.** (Optional fourth pad under U901 lifts the 28 W sustained limit.)
2. **C716 fix:** revert to its rev A orientation, or redraw `CHG_PGND_TOP` around it. **Recommend: revert** (measured 0.219 nH PMID with the old copper).
3. **Density:** accept 66.9 %, or push further by re-drawing power blocks. **Recommend: accept**; past ~70 % costs loop inductance.
4. **Mech:** flip the battery pack (leads exit −X), tweeter leads +75 mm (L) / +45 mm (R). **Recommend: accept.**

## 3. Known defects to fix during phase 2

- **Live-board VSYS–GND short:** a stale `CHG_PGND_TOP` fill overlaps C716 pad 1 by 0.85 mm² (confirmed by kicad-cli DRC, clearance, on the live board). Refill zones before any fab output. Nothing has been fabricated from this board.
- **Rev A charger block defects** still inside the block: BTST links, SW2 pin-to-pour contact → apply `layout_src/r6/spec_fix.json` (translated to the new block position).
- **Pruned stubs** (by design): quiet fan-out to R70x/R95x, amp output tails to the VH sockets, FAULT/TS/PROG; the R904 Kelvin track (rev A defect, had no via). Re-route these.
- **Inherited DRC items:** BOOST_AGND_ISLAND reported isolated (single-point join, intentional → exclude with a note); one PVDD via pair in AMP R violates hole-to-hole → fix.
- Passive rows use 0°/90° from the packer: tidy to one orientation per row (30-second check 4).

## 4. Phase 2 plan

1. Get the four decisions (§2).
2. **Apply v1 to the live board.** Konnect for part moves/zones/texts; the approved native closed-board steps (LAYOUT_NOTES §1.2) for the rest. Each native step is followed by the parity proof (kicad-cli DRC `--schematic-parity` = 0 and Konnect `update_pcb_from_schematic` dry run = noop) and a log line in §1.2.
   - **Sync C605** from schematic v0.3 first (Konnect `update_pcb_from_schematic`).
   - **Outline:** KiCad 10 ignores an outline drawn inside the BRD1 board-only footprint once the board shrinks. v1 removes BRD1 and uses a board-level Edge.Cuts polygon. Konnect cannot draw that, so this is **one new native step: get the owner's OK** (not yet on the §1.2 list).
   - Gap-pad landings are B.Cu rule areas `GAPPAD_*` plus the `ThermalLanding_*` footprints.
   - Check the result against this folder's board: block geometry with `scripts/blockdiff.py` (≤ 1 nm), placements by reference.
3. **Route in this order:** USB D± (J601 → U601 → U201, ~15 mm over solid L2) → power bands on L4 (PVDD spine Y +0…+14; VSYS band ≥ 6 mm along the front, charger → boost ~65 mm; VBAT_PACK ≥ 6 mm in the BATT/AMP-L channel; 3V3 rear-right) → VBUS on L6 along the front edge → planned L3 lanes (I2S, I2C, UART, SPI/PDM; see `block_map.png`) → Freerouting for the rest.
   - **Lock all critical routing before the DSN export**; use `wire_keepout`, not `keepout`; declare the plane layers. Diff the SES against the locked copper: 0 changes allowed (LAYOUT_NOTES §10).
4. **Release gates** (all must pass): DRC 0 errors / 0 unconnected; parity 0; per-pad connectivity script for U901/U951/U701/U301/U401/U101/U601; every via net = spec net (pin by UUID + free flag, KiCad re-nets non-free vias on load); reference-plane script 0 violations; copper balance L1↔L6, L2↔L5, L3↔L4 within 10 points; the six 30-second checks; silk cleanup.
5. **Re-score:** `sim/postlayout/run_all.sh <board> revb --full` (FastHenry hot loops, return paths, IR drop, PVDD |Z| vs 0.137 Ω, thermal with pads). Loops must not be worse than §1.
6. **Outputs:** checkpoint to `hw/releases/pcb_05_*`, fab files (JLC BOM/CPL via `layout_src/jlc_bom_cpl.py`), STEP, figures, LAYOUT_NOTES update.

## 5. Rules and gotchas (learned the hard way)

- **Never text-edit** `.kicad_pcb/.kicad_sch/.kicad_pro/.kicad_sym/.kicad_mod`/lib tables. Konnect MCP or an approved native exception only. pcbnew Python on experiment copies is fine.
- Never touch the owner's own pcbnew windows. Run edits in your own instance. Delete any `konnect.toml` you create.
- Vias added over IPC take the net of the zone they sit in → pin every via to its spec net.
- Konnect tools loaded mid-session can be invisible → do edits in a fresh sub-agent if a tool goes missing.
- FastHenry: average 4 grid offsets (one grid varies ±10 %); run with `-p off`.
- Commit/push happens every ~15 min (autosave loop); make a named commit at each milestone.

## 6. Downstream work after routing

- **Mech:** new outline/holes from `mech/mainboard_outline_fp1.dxf` and `mech/mech_inputs_fp1.json`; gap-pad bosses; pack flip; harness lengths; antenna-end clearance (PR-R basket, tweeter-R leads, X = +64 rib vs FFC).
- **ECO-003:** firmware thermal limiter (~12 W average), ICHG 1.5 A while playing, second 0402 100 nF at U901 (proposed), PVDD |Z| re-check.
- **Write-up:** layout chapter (rev A, autoroute experiment, 4-layer failure, 6-layer, floor plan v1, post-layout physics, ECO-004), kept short. README: "4-layer" → "6-layer". Blender renders after detailed CAD.

## 7. Reproduce the floor plan

```sh
cd hw/experiments/floorplan_v1/scripts
./run.sh plan3 t4     # copies 02_konnect1 as base.kicad_pcb if missing, then builds and runs every check
```

Needs KiCad 10 (its bundled Python), the repo `.venv`, and FastHenry from `sim/postlayout/tools`.

## 8. Setting up on a new machine

The work moved to another Mac on 2026-11-25. Nothing below is in git, so set it up first:

```sh
git clone https://github.com/frankie-eight-days/vibe-hardware-speaker.git && cd vibe-hardware-speaker
python3 -m venv .venv && .venv/bin/pip install -r requirements-sim.txt
# FastHenry (gitignored build), expected at sim/postlayout/tools/fh2src/bin/fasthenry
git clone https://github.com/ediloren/FastHenry2.git sim/postlayout/tools/fh2src
make -C sim/postlayout/tools/fh2src      # if the Makefile needs it: run its config step first (see its README)
brew install ngspice                     # for sim/spice
```

- **KiCad 10** in `/Applications/KiCad` (scripts call its bundled Python and `kicad-cli`).
- **Konnect MCP** server configured in Claude Code, plus the `konnect` skill.
- **Freerouting** at `~/tools/freerouting`.
- Vendor datasheet PDFs are not in git (`kb/datasheets/src/`); the markdown extracts with page citations are.
- The old machine's Claude memory doesn't carry over. This file, `LAYOUT_NOTES.md` and `docs/requirements.md` hold everything the next session needs.
- The 15-minute autosave loop was stopped on the old machine. There is no autosave now: commit by hand.
