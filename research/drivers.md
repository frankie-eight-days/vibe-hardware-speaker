# Driver selection: woofers, tweeters, passive radiators (v0.2, 2026-11-24)

**Changes in v0.2.** Electronics research set new amplifier limits: a 19 V boost rail, TAS5805M in BTL, and a 5 A overcurrent limit (OCP). Woofers should therefore be **6–8 Ω** (about 20 W into 8 Ω, about 25 W into 6 Ω). The average battery draw must stay at or below about 40 W.

- **All three recommended sets changed** to 8 Ω woofers. The PRs and the OT19NC00-04 tweeter are unchanged; tweeters may be 4–8 Ω.
- The alignment script now models the amp as a peak-voltage limit (18 V) and a peak-current limit (4.5 A) at each frequency, instead of a flat "20 W". It also estimates battery power.
- The v0.1 4 Ω picks remain in the tables and the script as comparison rows only.

**Decision (team lead, 2026-11-24): set B8 is selected.**

Companion files:

- `research/drivers.json`: SI-unit T/S and mechanical data with a source URL for each part.
- `sim/acoustics/pr_alignment_firstpass.py`: uses numpy only and runs on system Python 3.9. Writes `pr_alignment_firstpass_output.txt`, `pr_alignment_firstpass_results.json` and `pr_alignment_firstpass.png`.

Prices and stock come from the Parts Express (PE) item API, checked 2026-11-24. They exclude shipping.

---

## 1. Recommendation (8 Ω)

**Set B8: 2× Dayton ND65-8 woofers, 2× Dayton DMA58-PR passive radiators, 2× Peerless OT19NC00-04 tweeters.** Drivers cost **$93.54**, and all are in stock at PE.

Results at 0.75 L net, 19 V rail, 1 m, half space:

| Metric | Set B8 |
|---|---|
| F3 / F6 with DSP EQ (Butterworth 4th order at 63 Hz plus subsonic; boost ≤ +18 dB) | **64 / 56 Hz** |
| Natural (no-EQ) F3 / F6 | 120 / 97 Hz |
| Tuning fb / PR notch fp | 54 Hz / 32 Hz. Needs about **+3.5–6 g on each PR rod** |
| Sine max SPL at 50 / 63 / 80 / 100 Hz | 77 / 87 / 90 / 92 dB |
| Passband sine max (both woofers, about 21 W each) | ≈ 100 dB |
| Long-term pink-noise estimate (crest 3) | **91.4 dB**. Limited by amp voltage, with PR and woofer excursion within 0.5 dB of the limit |
| Average woofer power at that level | 3.3 W per woofer. Estimated battery draw **≈ 12 W** (budget 40 W) |
| Minimum net volume for F3 ≤ 65 Hz and ≥ 90 dB pink | **≈ 0.50 L** |

Why B8:

- Among **in-stock 8 Ω** drivers that reach 2.5 kHz, the ND65-8 is the best match. Its 3.5 mm Xmax gives Vd 5.8 cm³, and its published T/S data is self-consistent (Fs and Qes recompute within 2%).
- Its **64 mm round frame is the smallest woofer here**. That shortens the front stack to 2 × 64 + 2 × 33.4 + 9 ≈ 204 mm flush-mounted, or ≈ 192 mm rear-mounted through its 52 mm cutout. **Rear-mounted, it fits the ~194 mm front face of a 210 mm capsule.**
- It needs the least volume of any 8 Ω set (0.50 L) and is not Xmax-limited at 0.75 L.
- The DMA58-PR (about 77 mm diagonal) fits an 80–90 mm end cap without modification.

Trade-offs:

- Low sensitivity: 79.6 dB at 2.83 V. The passband ceiling is about 100 dB, 3–4 dB below the other 8 Ω drivers. The bass, which the pink-noise number depends on, is unaffected.
- At $23.98 it is the most expensive 2.5" option.
- Le of 0.61 mH with Re 7.4 Ω rolls the top end off above about 2 kHz. Cross at 2.5 kHz (LR4) and add a small high-shelf EQ.

**Variant B8':** the same woofers with **DMA70-PR** gives 91.8 dB and needs only 0.45 L. That is +0.4 dB, but the 96 mm-diagonal square frame needs a 98 mm-plus end cap or trimmed corners.

## 2. Packaging constraints

1. **Front-face length.** In a line, two woofers plus two tweeters must fit the ~194 mm front face of a 210 mm capsule:

   | Layout | Length needed |
   |---|---|
   | ND65-8, flush-mounted | 204 mm |
   | ND65-8, rear-mounted through the 52 mm cutout | ≈ 192 mm (fits) |
   | 69–70 mm square-frame woofers (DMA70-8, PLS-65F25AL02-08) | 214–216 mm |

   Other fixes: move the tweeters 35–45° up from the woofer axis, use the 26 mm OC16SC04-04 tweeter (crossover 3.5 kHz or higher, −5 dB), or lengthen to about 225 mm (two-piece print).
2. **Woofer flange on a cylinder.** A 64–70 mm frame fits a 90 mm OD tube with a local spot-face. 83–85 mm frames (PC83-8, ND91-8, FSF030.70) need **≥ 95 mm OD**. The 89 mm HiVi M3N does not fit.
3. **PR on the end cap.**

   | PR | Frame | Fit |
   |---|---|---|
   | DMA58-PR | ≈ 77 mm diagonal | fits a ≥ 80 mm cap |
   | DMA70-PR | ≈ 96 mm diagonal | needs a ≥ 98 mm cap, or corners trimmed to ~90 mm (holes on an 82.6 mm bolt circle) |
   | DMA80-PR | ≈ 111 mm diagonal | ruled out |

4. **Depth.** The ND65-8 is 51 mm deep. With the baffle about 28 mm off-axis, the motor ends about 23 mm past the tube axis. Keep the battery and PCB beside the motors.

### Net internal volume estimate (unchanged from v0.1)

The estimate assumes a 3 mm wall, 5 mm end caps and an internal length of about 200 mm.

| Item | 90 mm OD | 95 mm OD |
|---|---|---|
| Gross internal | 1.11 L | 1.24 L |
| Woofer motors and frames | −0.06–0.07 | −0.06–0.07 |
| PR frames and add-mass | −0.02 | −0.02 |
| Tweeter backs and mounts | −0.03 | −0.03 |
| 2×18650 + holder (2×21700: −0.08) | −0.06 | −0.06 |
| PCB, connectors, wiring | −0.04 | −0.04 |
| Top UI | −0.02 | −0.02 |
| Bracing, bosses, inserts | −0.04 | −0.04 |
| Woofer spot-faces (a full flat front costs about −0.14) | −0.06 | −0.06 |
| **Net** | **≈ 0.75 L** | **≈ 0.88 L** |

An 80 mm OD capsule gives about 0.50 L, which B8 still meets on paper with no margin.

## 3. Candidate tables

Vas is recomputed from Cms and Sd, and Rms from Qms. Mms is as published and includes air load. For the PLS-65F25AL02-08, Cms is derived from Fs and Mms because it is not published.

### Woofers, 8 Ω (current candidates)

| Woofer | Ω | Fs Hz | Qts | Qes | Qms | Vas L | Re Ω | Le mH | Bl Tm | Mms g | Cms mm/N | Rms kg/s | Sd cm² | Xmax mm | Vd cm³ | SPL 2.83V | P rms W | OD / cutout / depth mm | Price | PE stock |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [**ND65-8**](https://www.parts-express.com/Dayton-Audio-ND65-8-2-1-2-Aluminum-Cone-Full-Range-Driver-8-290-206) | 8 | 102 | 0.65 | 0.71 | 8.23 | 0.35 | 7.40 | 0.61 | 4.20 | 2.60 | 0.93 | 0.20 | 16.5 | 3.50 | 5.8 | 79.6 | 15 | 64 rd / 52 / 51 | $23.98 | in stock (530) |
| [PLS-65F25AL02-08](https://www.parts-express.com/Peerless-65F25AL02-2-1-2-Aluminum-Full-Range-Speaker-264-1182) | 8 | 104 | 0.70 | 0.81 | 4.80 | 0.77 | 6.10 | 0.05 | 3.19 | 2.07 | 1.13* | 0.28 | 22.1 | 2.60 | 5.7 | 83.3 | **10** | 69 flats, 85 diag / 60 / 45 | $15.00 | in stock (177) |
| [DMA70-8](https://www.parts-express.com/Dayton-Audio-DMA70-8-2-1-2-Dual-Magnet-Aluminum-Cone-Full-Range-Driver-8-Ohm-295-585) | 8 | 114 | 0.50 | 0.66 | 2.06 | 0.53 | 7.50 | 0.47 | 4.70 | 2.60 | 0.73 | 0.90 | 22.9 | 2.00 | 4.6 | 82.9 | 20 | 70 sq / 64 / 38 | $16.98 | in stock (244) |
| [ND91-8](https://www.parts-express.com/Dayton-Audio-ND91-8-3-1-2-Aluminum-Cone-Full-Range-Driver-8-290-226) | 8 | 71 | 0.47 | 0.53 | 4.29 | 1.35 | 7.80 | 1.24 | 5.63 | 4.80 | 1.05 | 0.50 | 30.4 | **5.10** | **15.5** | 82.1 | 30 | 85 rd / 76 / 56 | $27.98 | **OUT**, next PO 2026-12-04 |
| [PC83-8](https://www.parts-express.com/Dayton-Audio-PC83-8-3-Full-Range-Poly-Cone-Driver-295-156) | 8 | 82 | 0.63 | 0.76 | 3.68 | 1.77 | 6.80 | 0.38 | 3.50 | 2.70 | 1.40 | 0.38 | 30.2 | 2.00 | 6.0 | 83.8 | 30 | 83 rd / 77 / 50 | $15.49 | in stock (1240) |
| [PLS-P830986](https://www.parts-express.com/Peerless-830986-3-Full-Range-Woofer-264-1056) | 8 | 102 | 0.76 | 0.89 | 5.10 | 0.93 | 6.20 | 0.05 | 3.43 | 2.56 | 0.90 | 0.32 | 27.3 | 2.05 | 5.6 | 83.6 | 12 | 78 / 72 / 54 | $19.50 | in stock (180) |
| [DMA80-8](https://www.parts-express.com/Dayton-Audio-DMA80-8-3-Dual-Magnet-Aluminum-Cone-Full-Range-Driver-8-Ohm-295-587) | 8 | 98 | 0.47 | 0.61 | 2.06 | 1.32 | 7.50 | 0.50 | 4.52 | 2.70 | 0.98 | 0.80 | 31.2 | 2.50 | 7.8 | 85.3 | 25 | 80 sq / 74 / 39 | $17.98 | **OUT**, next PO 2027-04-02 |
| [HiVi M3N](https://www.parts-express.com/HiVi-M3N-3-Aluminum-Magnesium-Midbass-297-433) | 8 | 91 | 0.80 | 1.03 | 4.20 | 1.02 | 6.50 | – | 3.00 | 2.60 | 0.82 | 0.35 | 30.0 | 3.00 | 9.0 | 82.0 | 15 | 89 rd (too wide) / 76 / 67 | $14.98 | in stock (21) |
| [LaVoce FSF030.70](https://www.parts-express.com/LaVoce-FSF030.70-3-Full-Range-Woofer-8-Ohm-293-705) | 8 | 114 | 0.72 | 0.85 | 4.60 | 1.38 | 6.40 | 0.05 | 3.30 | 2.00 | 0.90 | 0.31 | 33.2 | 2.10 | 7.0 | 87.5 | 30 | 84 rd / 70 / 52 | $22.00 | only 1 in stock |

\* Derived value.

Rejected 8 Ω parts:

- **FaitalPRO 3FE22/3FE25**: tabs span 106 mm, Xmax 1.8 mm, only 5–8 in stock.
- **Visaton FRS7/FRS7W**: Xmax 0.75 mm or not published.
- **Tectonic TEBM65C20F-8**: 108 mm and out of stock.
- **ND90-8 / PS95-8**: 98–103 mm.
- **DMA58-8**: Vd 2.9 cm³.

**No 6 Ω woofers** of a suitable size turned up at PE. **The SLS-65S25PR03-04 has no 8 Ω version.**

### Woofers, 4 Ω (v0.1 candidates; comparison only)

| Woofer | Fs | Qts | Vas L | Re | Bl | Mms g | Sd cm² | Xmax | Vd cm³ | SPL | P rms | OD mm | Price / stock |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [SLS-65S25PR03-04](https://www.parts-express.com/Peerless-by-Tymphany-SLS-65S25PR03-04-SLS-Series-2.5-Woofer-4-Ohm-264-1013) | 94 | 0.55 | 0.55 | 3.80 | 3.59 | 3.57 | 22.1 | 4.33 | 9.6 | 81.9 | 10 | 69 | $15.75, 164 |
| [DMA70-4](https://www.parts-express.com/Dayton-Audio-DMA70-4-2-1-2-Dual-Magnet-Aluminum-Cone-Full-Range-Driver-4-Ohm-295-584) | 113 | 0.44 | 0.52 | 3.98 | 3.70 | 2.80 | 22.9 | 2.00 | 4.6 | 86.2 | 20 | 70 sq | $15.98, 615 |
| [DMA80-4](https://www.parts-express.com/Dayton-Audio-DMA80-4-3-Dual-Magnet-Aluminum-Cone-Full-Range-Driver-4-Ohm-295-586) | 94 | 0.41 | 1.30 | 4.00 | 3.74 | 3.02 | 31.2 | 2.50 | 7.8 | 88.1 | 25 | 80 sq | $16.98, OUT to 2027-01-22 |
| [ND65-4](https://www.parts-express.com/Dayton-Audio-ND65-4-2-1-2-Aluminum-Cone-Full-Range-Driver-290-204) | 90 | 0.61 | 0.43 | 3.50 | 2.68 | 2.50 | 15.6 | 3.50 | 5.5 | 83.0 | 15 | 64 rd | $23.98, 155 |
| [PC83-4](https://www.parts-express.com/Dayton-Audio-PC83-4-3-Full-Range-Poly-Cone-Driver-295-154) | 80 | 0.54 | 1.86 | 3.90 | 2.90 | 2.70 | 30.2 | 2.00 | 6.0 | 86.8 | 30 | 83 rd | $15.49, 1074 |
| [ND91-4](https://www.parts-express.com/Dayton-Audio-ND91-4-3-1-2-Aluminum-Cone-Full-Range-Driver-4-290-224) | 74 | 0.41 | 1.23 | 4.30 | 4.59 | 4.80 | 30.4 | 4.60 | 14.0 | 85.6 | 30 | 85 rd | $27.98, OUT |
| [W3-2052SC](https://www.parts-express.com/Tang-Band-W3-2052SC-3-RBM-Neodymium-Subwoofer-4-Ohm-299-572) | 59 | 0.49 | 0.58 | 4.30 | 6.60 | 14.8 | 28.8 | 5.00 | 14.4 | 78.3 | 15 | 83 rd | $29.98; FR 50–800 Hz, rejected |
| [SB65WBAC25-4](https://sbacoustics.com/product/2-5in-sb65wbac25-4/) | 115 | 0.68 | 0.43 | 3.60 | 2.90 | 2.50 | 20.0 | 2.65 | 5.3 | 83.5 | 20 | – | not at PE |

### Passive radiators (unchanged)

| PR | Fs Hz | Qms | Mms g | Cms mm/N | Rms kg/s | Vas L | Sd cm² | Xmech mm | Vd at 5 mm, cm³ | Frame | cutout / depth mm | Price | PE stock |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [**DMA58-PR**](https://www.parts-express.com/Dayton-Audio-DMA58-PR-2-DMA-Series-Passive-Radiator-295-593) | 39.8 | 3.93 | 6.7 | 2.40 | 0.43 | 0.70 | 14.5 | 7 | 7.3 | 56 mm square (≈77 diag) | 50 / 38 | $7.79 | in stock (487) |
| [DMA70-PR](https://www.parts-express.com/Dayton-Audio-DMA70-PR-2-1-2-DMA-Series-Passive-Radiator-295-594) | 34.5 | 3.86 | 12.0 | 1.77 | 0.67 | 1.29 | 22.9 | 7 | 11.5 | 70 mm square (≈96 diag) | 64 / 44 | $8.49 | in stock (201) |
| [DMA80-PR](https://www.parts-express.com/Dayton-Audio-DMA80-PR-3-DMA-Series-Passive-Radiator-295-595) | 34.6 | 8.91 | 13.7 | 1.41 | 0.33 | 1.91 | 31.2 | 7 | 15.6 | 80.5 mm square (≈111 diag) | 74 / 45 | $9.49 | in stock (371) |
| [ND65-PR](https://www.parts-express.com/Dayton-Audio-ND65-PR-2-1-2-Aluminum-Cone-Passive-Radiator-290-205) | 73.0 | 2.69 | 3.2 | 1.45 | 0.55 | 0.49 | 15.6 | 5 | 7.8 | 64 mm round | 52 / 48 | $9.49 | in stock (1158) |
| [ND90-PR](https://www.parts-express.com/Dayton-Audio-ND90-PR-3-1-2-Aluminum-Cone-Passive-Radiator-290-209) | 53.8 | 6.15 | 8.1 | 1.09 | 0.45 | 1.47 | 31.2 | 9 | 15.6 | 103 mm round (too big) | 76 / 61 | $10.49 | in stock (163) |

Notes:

- The DMA PRs have a threaded rod and wing nut for add-mass. Dayton's 7 mm figure is **Xmech**; the model uses 5 mm as the usable limit.
- The DMA70-PR description gives Rms = 1.49 kg/s, which contradicts its Qms (0.67 kg/s). The model uses Qms.
- The ND65-PR has no add-mass hardware. With ND65-8 woofers it reaches only 88.7 dB pink, because it runs out of PR excursion.

### Tweeters (unchanged; 4–8 Ω all acceptable)

| Tweeter | Ω | Fs Hz | Re Ω | SPL 2.83V | P rms W | Faceplate | cutout / depth mm | Price | PE stock |
|---|---|---|---|---|---|---|---|---|---|
| [**OT19NC00-04**](https://www.parts-express.com/Peerless-OT19NC00-04-3-4-Fabric-Dome-Tweeter-4-Ohm-264-1122) | 4 | **1029** | 3.17 | 88.8 | 40 | Ø33.4 | 31 / 17 | $15.00 | in stock (278) |
| [ND20FB-4](https://www.parts-express.com/Dayton-Audio-ND20FB-4-Rear-Mount-3-4-Soft-Dome-Neodymium-Tweeter-275-035) | 4 | 2072 | 3.20 | 90.0 | 15 | Ø39, rear mount | 36 / 19 | $12.98 | in stock (39) |
| [ND20FA-6](https://www.parts-express.com/Dayton-Audio-ND20FA-6-3-4-Soft-Dome-Neodymium-Tweeter-275-030) | 6 | 2005 | 5.20 | 90.0 | 15 | Ø45 | 33 / 15 | $10.98 | in stock (45) |
| [ND16FA-6](https://www.parts-express.com/Dayton-Audio-ND16FA-6-5-8-Soft-Dome-Neodymium-Tweeter-275-025) | 6 | 1774 | 6.10 | 87.5 | 10 | Ø32.5 | 33 / 14 | $8.98 | in stock (731) |
| [OC16SC04-04](https://www.parts-express.com/Peerless-OC16SC04-04-16mm-Fabric-Dome-OC-Tweeter-4-Ohm-264-1524) | 4 | 2153 | 3.93 | 83.7 | 100 | Ø26 | 22 / 9 | $6.50 | in stock (356) |
| [DX20BF00-04](https://www.parts-express.com/Peerless-DX20BF00-04-3-4-Silk-Dome-Tweeter-4-Ohm-264-1472) | 4 | 822 | 2.81 | 86.9 | 60 | Ø66 (too wide) | 49 / 35 | $16.50 | in stock (129) |
| [CF18N-4](https://www.parts-express.com/Dayton-Audio-CF18N-4-3-4-Carbon-Fiber-Dome-Neodymium-Tweeter-4-Ohm-275-411) | 4 | 1100 | 3.50 | 90.0 | 40 | Ø58 | 38 / 36 | $25.98 | only 3 in stock |

Tweeter notes:

- **The OT19NC00-04 is still the pick.** Its 1029 Hz Fs and 33.4 mm faceplate allow an LR4 crossover at about 2.5 kHz. Some EU sellers list it as discontinued (replacement OX20SC00-04); PE and DigiKey list it as active. **Buy spares.**
- Tweeter current is not a problem. At 92 dB pink each tweeter draws well under 1 W, and a 4 Ω tweeter at the low levels needed stays far below 5 A. If the electronics team wants every channel at 6 Ω or above, use the ND20FA-6 or ND16FA-6, but those need a crossover at 3.5 kHz or higher.

## 4. Driver sets (8 Ω; all changed from v0.1)

| Set | Woofers ×2 | PRs ×2 | Tweeters ×2 | Crossover | Cost (6 drivers) | Pink at 0.75 L | Min net Vb | Stock |
|---|---|---|---|---|---|---|---|---|
| **A8 budget** | PLS-65F25AL02-08 ($15.00) | DMA58-PR ($7.79) | OT19NC00-04 ($15.00) | LR4 at 2.5 kHz | **$75.58** | 90.7 dB (woofer Xmax) | 0.60 L | all in stock |
| A8' all-Dayton fallback | DMA70-8 ($16.98) | DMA70-PR ($8.49) | OT19NC00-04 | LR4 at 2.5–3 kHz | $80.94 | 89.9 dB (Xmax; misses 90 by 0.1) | – | all in stock |
| **B8 recommended** | **ND65-8 ($23.98)** | **DMA58-PR ($7.79)** | **OT19NC00-04 ($15.00)** | LR4 at 2.5 kHz | **$93.54** | **91.4 dB** (amp V) | **0.50 L** | all in stock |
| **C8 premium** | ND91-8 ($27.98) | DMA70-PR ($8.49) | OT19NC00-04 | LR4 at 2.5 kHz (Le 1.24 mH; needs EQ) | **$102.94** | 91.1 dB (amp V); 92.8 dB at 1.2 L | 0.65 L | **ND91-8 out of stock**, next PO 2026-12-04; needs ≥ 95 mm OD |

Notes on the sets:

- **A8** uses a cheap driver whose Cms is derived, and it is **rated only 10 W RMS**. That rating is fine at the pink limit (4.4 W average), but the thermal limiter must cap it at about 8 W.
- **A8'** is best documented, but it is Xmax-limited at 2 mm, so extra volume does not help.
- **C8** wins only when the box is above about 0.9 L, which in practice means a 95 mm-plus capsule.

## 5. PR alignment (re-run with the 19 V / 5 A amplifier limits)

Run: `python3 sim/acoustics/pr_alignment_firstpass.py`.

**What changed in the model.** The amp limit is now applied per frequency as **V_peak ≤ min(18 V, 4.5 A × |Zin(f)|)**:

- 18 V is about 0.95 × the 19 V rail in BTL, which gives ≈ 20 W into 8 Ω.
- 4.5 A is the 5 A OCP less 10% margin.

The pink-noise check also limits CREST × I_rms ≤ 4.5 A and voice-coil power (I_rms² × Re) ≤ the rated RMS. It reports the average electrical power per woofer and an estimated battery draw: 2 woofers + 10% for the tweeters, ÷ 0.75 amp-chain efficiency, + 2 W for the system.

Everything else is unchanged:

- Two woofers in mono, one shared box, two PRs.
- QL 10, 1 m, half space (subtract 6 dB for free field).
- Usable PR excursion 5 mm.
- DSP target: Butterworth 4th order at 63 Hz plus a 2nd-order subsonic at 28 Hz (F3 64 Hz / F6 56 Hz). EQ boost ≤ +18 dB, rolling off at 24 dB/oct below 47 Hz.
- Pink-noise crest factor 3.
- PR add-mass optimised for the pink-noise estimate.

### Results at 0.75 L net (from `pr_alignment_firstpass_output.txt`)

| Set | m_add per PR | fb / fp Hz | no-EQ F3 / F6 | Max SPL at 50 / 63 / 80 / 100 Hz | Passband max | Amp W into woofer at 400 Hz | **Pink est.** (limit) | Woofer avg W / battery W at pink | Same drivers sealed | **Min Vb** |
|---|---|---|---|---|---|---|---|---|---|---|
| A8 PLS-65F25AL02-08 + DMA58-PR | 6.2 g | 48 / 29 | 142 / 121 | 81 / 86 / 88 / 91 | 103.8 | 22.8 | **90.7** (woofer Xmax) | 4.4 / 15.0 | 87.4 | 0.60 L |
| A8' DMA70-8 + DMA70-PR | 9.5 g | 54 / 26 | 170 / 132 | 82 / 87 / 88 / 90 | 103.1 | 17.6 | 89.9 (woofer Xmax) | 2.5 / 9.4 | 85.4 | not met |
| **B8 ND65-8 + DMA58-PR** | **3.5 g** | **54 / 32** | 120 / 97 | 77 / 87 / 90 / 92 | 99.7 | 20.8 | **91.4** (amp V) | **3.3 / 11.7** | 87.5 | **0.50 L** |
| B8' ND65-8 + DMA70-PR | 6.0 g | 59 / 28 | 117 / 94 | 80 / 89 / 91 / 93 | 99.7 | 20.8 | 91.8 (amp V) | 3.3 / 11.8 | 87.5 | 0.45 L |
| C8 ND91-8 + DMA70-PR | 8.5 g | 56 / 26 | 128 / 107 | 81 / 87 / 91 / 95 | 102.1 | 20.5 | 91.1 (amp V) | 3.3 / 11.6 | 90.4 | 0.65 L |
| ref ND91-8 + DMA80-PR | 14.0 g | 63 / 25 | 126 / 106 | 81 / 87 / 91 / 95 | 102.2 | 20.5 | 91.4 (amp V) | 3.3 / 11.6 | 90.4 | 0.60 L |
| ref PC83-8 + DMA70-PR | 7.5 g | 57 / 27 | 152 / 133 | 81 / 84 / 89 / 93 | 104.9 | 22.4 | 90.1 (amp V) | 4.9 / 16.3 | 87.9 | 0.75 L |
| ref PLS-P830986 + DMA70-PR | 12.8 g | 51 / 24 | 150 / 130 | 82 / 85 / 89 / 91 | 104.7 | 22.7 | 90.7 (woofer Xmax) | 5.2 / 17.3 | 87.2 | 0.65 L |
| ref DMA80-8 + DMA80-PR (OOS) | 12.0 g | 65 / 26 | 179 / 149 | 80 / 86 / 89 / 93 | 106.1 | 17.9 | 91.1 (amp V) | 4.2 / 14.3 | 89.7 | 0.70 L |
| old 4 Ω SLS-65 + DMA58-PR | 8.8 g | 44 / 26 | 129 / 104 | 83 / 90 / 92 / 95 | 103.8 | 39.2 | 94.4 (amp V) | 6.8 / 22.1 | 91.8 | 0.35 L |
| old 4 Ω DMA70-4 + DMA70-PR | 9.5 g | 54 / 26 | 175 / 132 | 82 / 89 / 88 / 90 | 105.7 | 32.9 | 90.0 (woofer Xmax) | 2.3 / 8.8 | 85.4 | 0.75 L |

### Pink-noise estimate (dB) vs net volume, PR mass re-optimised at each volume

| Vb (L) | 0.50 | 0.60 | 0.75 | 0.90 | 1.00 | 1.20 |
|---|---|---|---|---|---|---|
| A8 PLS-65F25AL02-08 + DMA58-PR | 89.1 | 90.2 | 90.7 | 90.7 | 90.7 | 90.7 |
| A8' DMA70-8 + DMA70-PR | 89.5 | 89.8 | 89.9 | 90.0 | 89.9 | 89.8 |
| **B8 ND65-8 + DMA58-PR** | 90.1 | 90.7 | **91.4** | 91.5 | 91.4 | 91.2 |
| B8' ND65-8 + DMA70-PR | 90.6 | 91.2 | 91.8 | 92.1 | 92.2 | 92.1 |
| C8 ND91-8 + DMA70-PR | 88.9 | 90.0 | 91.1 | 91.9 | 92.3 | 92.8 |
| old 4 Ω SLS-65 + DMA58-PR | 92.7 | 93.5 | 94.4 | 94.9 | 94.9 | 94.9 |

### Sensitivity of the B8 result (0.75 L)

| Change | Pink est. |
|---|---|
| Crest factor 4 (12 dB) | 88.9 dB (−2.5) |
| 20 V rail (19 V peak) | 91.7 dB (becomes woofer-Xmax-limited) |
| QL 5 / 30 | 91.1 / 91.5 dB |
| F3 target 55 / 70 Hz | 91.0 / 91.5 dB (PR mass 6.2 / 2.8 g) |

### Reading the results

- **Switching to 8 Ω costs about 1–3 dB against the old 4 Ω SLS-65 set,** whose pink estimate under the new limits is 94.4 dB. Every 8 Ω set at 0.75 L lands at 89.9–91.8 dB pink in half space, so the ≥ 90 dB requirement is still met, but only by 1–2 dB, and only in half space with about 9.5 dB crest after DRC. In free field it is about 84–86 dB.
- **The 4 Ω SLS-65 is still the best-performing driver by about 3 dB.** Under the 4.5 A model it is current-limited only near its 3.8 Ω impedance minimum. If the electronics team can clamp the woofer channel's peak output to about 15 V in the TAS5805M (≤ about 4 A into Re 3.8 Ω), it still reaches 92.9 dB pink (91.8 dB at a 13 V clamp), beating every 8 Ω option. **That is the electronics team's decision.** I have followed the 6–8 Ω directive.
- **Battery:** every set draws an estimated **9–17 W average** at its pink-noise limit (4 Ω SLS: about 22 W), well inside the 40 W budget. Sustained sine at full output would be about 2 × 20 W into the woofers, so the DRC must also manage average power.
- **PR tuning: fb ≈ 54 Hz** (closed form; the impedance-dip frequency is about 4 Hz higher), with about 3.5–6 g on each DMA58-PR. Tune on the prototype by measurement.

## 6. Impedance

**Woofers: 8 Ω** for the reasons above. The amp delivers about 20 W at 400 Hz into the 8 Ω picks. Most sets are amp-voltage-limited in the passband and Xmax- or PR-limited in the deep bass, so 8 Ω costs about 1 dB against an ideal 6 Ω driver.

No suitable 6 Ω woofer was found at PE. If one appears (≤ 70 mm frame, Xmax ≥ 3 mm), it would gain about +1 dB at about 25 W.

**Tweeters: 4 Ω is fine** (OT19NC00-04).

## 7. Where to buy

| Part | Parts Express (verified 2026-11-24) | Other sources (prices not verified) |
|---|---|---|
| ND65-8 | $23.98, 530 in stock, PE 290-206 | Amazon (Dayton Audio store), Madisound |
| DMA58-PR | $7.79, 487 in stock, PE 295-593 | Amazon, Madisound |
| DMA70-PR | $8.49, 201 in stock, PE 295-594 | Amazon, Madisound |
| OT19NC00-04 | $15.00, 278 in stock, PE 264-1122 | [DigiKey 6557475](https://www.digikey.com/en/products/detail/peerless-by-tymphany/OT19NC00-04/6557475) |
| PLS-65F25AL02-08 | $15.00, 177 in stock, PE 264-1182 | DigiKey and Mouser (Peerless by Tymphany) |
| DMA70-8 | $16.98, 244 in stock, PE 295-585 | Amazon, Madisound |
| ND91-8 | $27.98, **out of stock**, next PO 2026-12-04, PE 290-226 | Madisound or Amazon may have stock |

PE links for every part are in the tables above and in `drivers.json` (`source_url`).

**AliExpress / eBay** have cheap PRs and 2–3" drivers with no T/S or Xmax data. Use them for mock-ups only unless they are measured first.

## 8. Next steps

1. Order the B8 drivers plus 1 spare each, and 2× PLS-65F25AL02-08 as the budget fallback (about $140). Measure T/S with DATS or REW, then update `drivers.json` and re-run the script.
2. Decide on rear-mount versus off-axis tweeters (see §2). With the ND65-8 rear-mounted, the line layout fits a 210 mm × 90 mm capsule.
3. TAS5805M setup:
   - subsonic HPF at about 47 Hz, 24 dB/oct, ahead of the bass boost;
   - DRC/limiter on the woofer channel to keep long-term woofer power ≤ 10 W (ND65-8 is rated 15 W);
   - peak output ≤ 18 V.
4. Optional: ask electronics whether a 4 Ω woofer channel with an output clamp of about 15 V peak is acceptable. That would re-enable the SLS-65 (+2–3 dB).

Sources: the Parts Express item API (all PE rows); [SB Acoustics SB65WBAC25-4](https://sbacoustics.com/product/2-5in-sb65wbac25-4/); [DigiKey OT19NC00-04](https://www.digikey.com/en/products/detail/peerless-by-tymphany/OT19NC00-04/6557475); [loudspeakerdatabase SB65WBAC25-4](https://loudspeakerdatabase.com/SB/SB65WBAC25-4); [diyAudio thread on unspecified cheap PRs](https://www.diyaudio.com/community/goto/post?id=6059112).
