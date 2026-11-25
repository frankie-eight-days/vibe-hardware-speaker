# S8: USB-C VBUS hot-plug ringing

`run.py` (ngspice) models a step source, then cable loop L/R (0.3 m 0.25 µH/40 mΩ; 1 m 0.75 µH/0.1 Ω; 2 m 1.5 µH/0.2 Ω), then the board: D601 SMF24A, 2×10 µF + 100 nF + 1 µF on VBUS, and 3×10 µF PMID behind the BQ25792 RBFET body diode. MLCC capacitance is derated for DC bias at the final voltage.

Peak VBUS (V), shortest cable (worst case):

| Damping | 5 V attach | 15 V hot-plug | 20 V hot-plug |
|---|---|---|---|
| None (as built) | 6.0 | 20.1 | 27.6 |
| TI 2 Ω + 2.2 µF (R601/C602, DNP) | 5.9 | 19.9 | 27.2 |
| 1 Ω + 10 µF | 5.7 | 19.2 | 26.2 |
| Ideal 47 µF, ESR 0.3 Ω | 5.1 | 15.9 | 21.4 |
| **C605** Lelon VZH 47 µF / 35 V, ESR 0.44 Ω (Z max, 20 °C) | 5.2 | 16.8 | 22.8 |
| C605 at −20 % C (37.6 µF), 0.44 Ω | 5.3 | 17.0 | **22.9** |
| C605 at −20 % C, 0.88 Ω (−25 °C, Z ratio 2) | 5.6 | 18.2 | 24.8 |
| C605 + R605 0.5 Ω 0805 in series | 5.6 | 18.3 | 24.9 |

- A compliant USB-C source attaches at 5 V, which peaks at 6 V. Cable R and the PMID bank behind the body diode damp it.
- Only a non-compliant source that is already at 15–20 V gets close to the 30 V VBUS abs max (BQ2579x; confirm on the datasheet).
- TI's 2 Ω / 2.2 µF snubber barely helps against our ~50 µF nominal bank. An ESR-damped bulk cap is the effective option.
- ECO-004 fits C605 = Lelon VZH470M1VTR-0606 (LCSC C134832, 6.3 × 5.7 mm). The datasheet gives Z ≤ 0.44 Ω at 100 kHz (taken as the ESR at the ~40 kHz ring) and tan δ 0.13 at 120 Hz (ESR120 ≤ 3.7 Ω). Worst case at 20 °C is 22.9 V, which meets the ≤ 24 V target.
- In a 47 µF ESR sweep the peak is 20.0–21.6 V from 0.035 Ω (polymer) to 0.3 Ω, with the minimum at about 0.15 Ω. It rises above about 0.5 Ω, so too much ESR is the real risk. A generic tan δ-only part (ESR120 ~4.5 Ω, HF ESR unspecified) gives 26–27 V, so the 100 kHz Z spec matters. A series R only adds to the ESR, so there is no R605.

Limits: fixed derated C (the real C drops further at the peak), no contact bounce, no source-side capacitance.
