# Layout principles (from the project owner's post "Vibe hardware is aimed at the wrong half of the job", frankwalsh.tech, 2026-10-04)

The owner is a systems EE. Their view: LLMs are weakest at layout. Demos show boards that *connect*, but "start thinking about ESD, EMC, SI and PI, or about building ten thousand of them, and they fall apart." Most layout "taste" is "physics with a number attached": loop inductance, PDN impedance, return paths. So layouts must be **scored with field solvers and PDN/IR checks**, not just connectivity and DRC.

## Workflow the owner advocates
1. The model reads the stackup, datasheets (layout sections, with page citations) and the fab capability sheet, then writes the **net classes, widths, clearances and layer rules**.
2. An **autorouter does geometry** for non-critical nets.
3. The model checks DRC and diffs the result.
4. **Critical nets (power stages, switch nodes, diff pairs, high current) are routed deliberately and reviewed.**
5. Score the result with physics: openEMS / Elmer / ngspice (loop inductance, PDN, IR drop).

Rules: cite the datasheet page for every pin or layout claim. Treat footprints as ~80 % right until checked against the drawing. Ground is a pour, never a trace.

## The six 30-second checks (must all pass)
1. TVS diode right at the connector.
2. Tiny buck/boost input hot loop: input cap tight against the IC.
3. Small switch node: inductor next to the switch pin.
4. Decoupling caps hugging the IC; passives in rows with one orientation (pick-and-place, rework).
5. Solid, unbroken ground under the USB pair (and under every fast signal).
6. Copper balanced across mirrored layers (L1↔L4, L2↔L3) so the board etches evenly and stays flat in reflow.

## Failure modes seen in AI-routed boards (avoid)
Connectors you can't physically reach or plug into; vias in pads; many track widths in one empty net class; split power planes under signals; bad USB D+/D− routing; sprawling hot loops and giant switch nodes; inductors far from the IC; ground routed as traces. "Every segment looks fine. The board is shorted."
