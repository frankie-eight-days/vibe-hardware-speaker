# Rev B handoff (from pcb-layout rev A agent, context exhausted)

## Environment
- Konnect reaches pcbnew only when `ipc_socket_path` is set. The fix used in rev A:
  - Put a `konnect.toml` in the Konnect server's cwd (`/Users/frankwalsh/Documents/vibecoding/`) containing `ipc_socket_path = "ipc:///tmp/kicad/api.sock"`.
  - Then call `reload_server(confirm, allow_same_version)`.
  - **Delete the file when done.** It has already been deleted once.
- Launch a dedicated pcbnew with `open -n -a /Applications/KiCad/KiCad.app/Contents/Applications/pcbnew.app --args <board>`.
- To close it: kill the PID, then remove `~speaker_main.kicad_{pcb,pro}.lck` in `hw/mainboard`.
- KiCad Python: `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`. Pipe its output through `grep -v "assert\|Debug\|memory leak"`; the noise is huge.
- Konnect editing tools are only visible to sub-agents spawned after `load_toolset`. Use one foreground editor sub-agent per batch and ask for 20 parallel calls per message.

## Konnect traps (LAYOUT_NOTES §1.1)
- Custom-pad footprints cannot be placed, but they can be moved.
- Track-less vias get re-netted to the zone they sit in. Fix this natively with `SetIsFree(True)`.
- There is no tool for zone edit/delete, via delete, keep-out, or unfilled Edge.Cuts.
- `create_netclass` edits the `.kicad_pro`. Do it while pcbnew is closed.
- `place_component` over IPC loses attributes. Use the closed-file path for board-only parts.

## Offline pipeline (scratch copies only; replay to live via Konnect)
Scripts are in this folder:
- `place.py` and `tps.py`: the placement plan (KiCad coords).
- `check.py`: courtyard, height (STL map), holes and antenna checks.
- `build.py` + `blk_*.py`: zones, vias, manual tracks and A* jobs, using `arouter.py`.
  - `blk_boost.py`, `blk_charger.py` and `blk_buck.py`, plus the amp power pins in `blk_amps.py`, are **frozen**. The lead's analysis agent is scoring them.
- `fanout.py`: plane fan-out vias.
- `stitch.py`: GND stitching.
- `reduce_dsn.py`: keeps only the still-unconnected pins in the DSN.
- `native_finalize.py`: SES import, via-net restore and free flag.
- `residual.py`: A* on the unconnected pairs left after Freerouting.
- `restore.py` and `clean_conflicts.py`: restore critical geometry after the SES import.
- **LOCK critical tracks before DSN export.** Rev A failed this: Freerouting moved 63 segments and 14 vias. Mark them locked, or export them as protected wires (`(type protect)`) in the DSN.
- To limit L3 routing in Freerouting, add `(wire_keepout "x" (polygon In2.Cu 0 x y ...))` to `(structure)`. Units are µm and DSN y = −KiCad y.
  - Do **not** use `keepout`: it also blocks vias, and completion collapses.
  - THT pads and the TAS5805M PowerPAD via pads that fall inside a wire keep-out count as violations. Carve them out.
- Set L2 to plane in the DSN: change `(layer In1.Cu (type signal))` to `(type power)`.

## Rev B design facts
- KiCad X = enclosure X + 150, KiCad Y = 100 − enclosure Y. The board spans X 60–240 and Y 75–121.
- J501 (FFC) is at the rear-right, X 211.5–239.5. The MCU sits at the left end, X 55–88.
- The UI bus is 13 lines (LCD_SCLK/MOSI/CS/DC/BL, PDM_CLK/DATA, ENC_A/B/SW, BTN_ADC, CHG_QON, 3V3/GND). Its series resistors sit at the MCU rear side, X 84–89, Y 86.
- Mech check requested by the lead: can J501 or the FFC exit move toward the MCU end? Read `docs/mech_envelope.md` §6–7 (FFC path to the UI board is about 90 mm, routed up the rear-right inside wall; "use a 100 mm FFC") and `mech/concept/speaker_concept.py`.
- In rev A, the L3 +3V3 pour is a zone at priority 1; zones cannot be deleted through Konnect. Either override it with a higher-priority GND zone on L3, or remove it natively. The second needs lead approval.
- Live board state: rev A with 40 unconnected. `hw/experiments/hybrid_restore_wip` holds the offline repair (35 unconnected).
