# Process log: how the speaker was designed with LLM agents (2026-11-24)

Source material for the write-up's "How it was designed" chapter. One human (the user) made the product decisions; one orchestrating Claude session (the "lead") planned, briefed agents, relayed results, and kept the requirements doc current. Every agent below was a separate Claude instance with its own context; they never saw each other's transcripts, only the files and messages.

## Timeline

| Phase | What happened | Agents |
|---|---|---|
| 0. Idea | User: "vibe hardware" mixed-signal showpiece, JLCPCB-assembled PCB, LCSC parts, 3D printer for mechanics. Bluetooth speaker vs a JBL Flip/Pill. Lead proposed stereo 2-way bi-amped + passive radiators, ESP32 + TAS5805M, USB-C PD + 2S battery. User added: MEMS mic for auto-EQ, round display, stereo, wireless with USB-C. | — |
| 1. Requirements | Lead wrote `docs/requirements.md` (targets, block diagram, DSP split, sim plan) as the single source of truth before any agent ran. | lead |
| 2. Parallel research | Three agents in parallel: electronics parts (LCSC/JLC stock checked via JLC's parts API), drivers (T/S data + first-pass passive-radiator alignment in Python), firmware/DSP + sim-tool install on macOS arm64 (smoke tests: bempp-cl within 0.22 % of the sphere solution). | 3 |
| 3. Cross-agent corrections | Firmware research found ESP32 BT+Wi-Fi audio needs PSRAM → lead switched WROOM-32E → WROVER-E and messaged the still-running electronics agent. Electronics found 4 Ω woofers can trip TAS5805M OCP at 19 V → lead messaged the driver agent. | — |
| 4. Battery + form | User rejected spot-welded 18650/21700 packs → pouch pack with XT30 + JST-XH balance; protection/balancing stays on the PCB. | — |
| 5. The 4 Ω / 8 Ω flip-flop | Lead first relayed "use 6–8 Ω", then reversed to "keep 4 Ω at 16 V", then chose the agent's 8 Ω set B8. Messages arrived out of order; the driver agent built, reverted and rebuilt its files. Lesson: an orchestrator must not send a correction before the agent has acknowledged the previous one; decisions need a single owner and a version. | — |
| 6. Circuit specs | Because the KiCad-drawing agent had no web access, two spec agents (power, signal) wrote pin-exact, value-exact specs from datasheets and TI/Espressif reference designs. They negotiated interfaces directly (net ownership, RefDes ranges, PVDD 18 V, 20 ms PDN delay). | 2 |
| 7. Catches by the spec agents | TAS5805M ADR pin doubles as FAULT → a shared open-drain fault line would give both amps the same I2C address (fixed with 2 FETs). HY2213 balancers need external FETs. CH224Q drags the I2C bus to 2.2 V when USB is unplugged (isolated with 2 FETs). TPS61178 load-disconnect FET can't drive 1.5 mF of PVDD bulk → removed, PVDD rests at VSYS−0.5 V when off. ESP32 GPIO36/39 glitch erratum → encoder switch moved. JST-SH had no JLC stock → 20-pin FFC. | — |
| 8. Mechanical first? | User asked whether mechanics should come first. Answer: schematic is independent of shape; layout is not. Mechanical concept agent built a scripted FreeCAD model; result Ø95 × 210 mm, 0.85 L net, 5 printed parts; no stock device-grade pouch fits → Gens ace 5000 mAh; tweeter waveguide shrinks to a 3 mm bezel (kept as a sim talking point). | 1 (+1 helper) |
| 9. Schematic v1 | One agent drew 9 hierarchical sheets via the Konnect MCP server (never text-editing KiCad files): 257 parts, ERC 0. An independent review agent found no blockers; two "pinout" concerns were refuted by the spec agent against datasheets. | 2 |
| 10. Redraw | User: "these schematics look awful". Lead installed the user's `redraw-kicad-schematics` skill, saved v1, asked for a one-sheet pilot. The agent had already fanned out 4 parallel sub-agents and redrawn all sheets. Connectivity was verified identical to v1 by (reference, pin) set comparison. Lesson: "pilot first" instructions must arrive before work starts; verification by netlist comparison made the redraw safe anyway. | 1 (+4 sub) |
| 11. Simulations | Acoustics (lumped bass, BEM tweeter/woofer directivity on the CAD hull, FEM panel modes, crossover) and SPICE/PDN (TI's TPS61178 model in ngspice, LC filter, NTC window, boot timing, FFC signal integrity, rail impedance). SPICE found PVDD too soft at 150 Hz and a start-up overshoot → ECO-001. | 2 (+sub) |
| 12. Operations | Disk filled to 150 MB from parallel sims + user data; agents paused, caches cleared (≈17 GB freed). A 5-hour usage limit stopped all agents mid-run; work resumed from files on disk. | — |

## What worked
- A single requirements file and spec files as the contract between agents.
- Spec agents with web access writing for a drawing agent without it.
- Independent review agents, then a second pass that challenges claimed defects against datasheets.
- Netlist (reference, pin) comparison as the safety net for any cosmetic edit.
- Every simulation validated against an analytic case before use.

## What went wrong
- Out-of-order corrections (4 Ω/8 Ω) and instructions that arrived after work started (pilot redraw).
- Parallel heavy simulations exhausted disk and RAM.
- Agents occasionally repeated or duplicated notifications; the lead had to deduplicate.
