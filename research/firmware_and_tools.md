# Firmware/DSP stack and simulation toolchain: research notes

> **Superseded hardware facts (2026-11-24):** the mic is a **PDM** MEMS mic (TDK T3902) on **I2S0** (PDM RX is I2S0-only on the classic ESP32); the amps are on **I2S1**. Amp DSP runs at 96 kHz, so biquads must be computed for 96 kHz. See docs/spec_signal.md.


Date: 2026-11-24. Scope: firmware for a portable stereo bi-amped BT speaker (ESP32 + 2× TAS5805M + I2S MEMS mic + GC9A01 + encoder), and the simulation tools that run on this Mac (macOS 26.5.1, Apple M4).
Facts are dated and sourced. **[measured]** means I ran it on this machine. **[estimate]** means my own engineering estimate, not a sourced number.

---

## TL;DR

| Question | Answer |
|---|---|
| Framework | **ESP-IDF (C), not Arduino.** Use v5.5 LTS now, or v6.1 if you want the AAC example. Base it on Espressif's own Bluedroid A2DP-sink example and add esp-dsp, esp_lcd_gc9a01, esp_lvgl_port and esp_http_server. PlatformIO only through the community *pioarduino* fork, so skip it. |
| Module | **Change ESP32-WROOM-32E to ESP32-WROVER-E (PSRAM).** Classic BT + Wi-Fi + a web UI + LVGL on the 520 KB of internal SRAM alone is a known failure mode. Espressif's ADF guide says BT and Wi-Fi "can not coexist without PSRAM". |
| Codecs | SBC works now. **AAC on the classic ESP32** is new: Espressif's `a2dp_sink_stream_aac` example (external-codec path + esp_audio_codec) is on the ESP-IDF v6.1 and master branches, not in v5.5 or v6.0. Treat it as a stretch goal. |
| BT + Wi-Fi | Supported, with caveats. In ESP-IDF's coexistence table, **Wi-Fi STA + BT connected** is "stable" but **SoftAP + BT connected is "C1: supported but the performance is unstable"**. So join the home Wi-Fi as STA and use SoftAP only for provisioning. You also need a large PCM ring buffer and no BLE scanning during playback. |
| Live TAS5805M EQ from the web UI | **Practical.** Biquads live in Book 0xAA as signed **5.27** fixed point, order `b0 b1 b2 −a1 −a2`, a0-normalised. I checked this against a PPC3 dump (see `tools/tas5805m_bq.py`). Writing one biquad takes about 0.6 ms of I2C at 400 kHz. TI documents no shadow/safeload bank, only a `BQ_WR_FIRST_COEF` handshake bit and a `BQ_WR_ERROR` fault flag. So big changes are done as mute-ramp → write → ramp. User EQ is better done on the ESP32 anyway (see A2). |
| ESP32 DSP headroom | Plenty. esp-dsp biquad = **17 cycles/sample** on ESP32. The full effects chain (10-band EQ, loudness, bass enhancer, widener, limiter) comes to about 40 Mcycle/s, roughly 17 % of one 240 MHz core **[estimate]**. |
| Sim tools on this Mac | **Worked [measured]:** Python 3.14.10 venv with numpy, scipy, matplotlib, gmsh 4.15.2, numba 0.68.1, **bempp-cl 0.4.2** (0.22 % error against the analytic pulsating sphere), ElectroacPy 2025.7.1 (lumped-element passive-radiator box, matches closed form within 0.3 %), and the FreeCAD 1.1.3 → STEP → gmsh → bempp pipeline. FreeCAD bundles **CalculiX 2.23** (native arm64) and gmsh 4.15.0. **Did not work:** bempp's OpenCL backend (Apple exposes only a GPU OpenCL device and bempp wants a CPU one). Numba is the backend to use. |

---

## Part A: firmware / DSP

### A1. A2DP sink on ESP32

**Stacks (state as of Nov 2026)**

- **ESP-IDF Bluedroid (`esp_a2dp_api.h`).** This is the reference stack. The current stable release is ESP-IDF **v6.1.1** ([coexist page header](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/coexist.html)). The A2DP sink decodes SBC internally and hands PCM to a data callback. The newer *external codec* mode (`CONFIG_BT_A2DP_USE_EXTERNAL_CODEC=y`, `ESP_A2D_MAX_SEPS ≥ 2`) hands encoded SBC/AAC frames to the application, which decodes them with `esp_audio_codec` ([ESP-IDF A2DP API](https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/bluetooth/esp_a2dp.html)).
  - **AAC.** The example `examples/bluetooth/bluedroid/classic_bt/a2dp_sink_stream_aac` lists ESP32 and ESP32-S31 as targets. I checked which branches have it: **present on `master` and `release/v6.1`, absent on `release/v6.0`, `release/v5.5` and `release/v5.4`** (raw.githubusercontent HTTP 200/404, checked 2026-11-24). AAC-LC decoding takes much more CPU and RAM than SBC. Plan for it only with PSRAM, and measure it.
  - **Sink delay.** The default sink delay is 120 ms, and settings below 120 ms fail. The sink can report its delay to the phone (AVDTP delay reporting), so video lip-sync is handled by the phone ([ESP-IDF A2DP API](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/bluetooth/esp_a2dp.html)). Expect about 150–250 ms end-to-end in practice ([applied-ee overview](https://applied-ee.github.io/embedded/docs/audio-projects/bluetooth-audio/a2dp-audio-streaming/), a secondary source).
- **`espressif/esp_bt_audio` component (v1.2.0).** A new "unified manager for Classic Bluetooth and LE Audio". In sink mode it gives the app *encoded* frames (`esp_bt_audio_stream_acquire_read()`), and the app decodes them ([component readme](https://components.espressif.com/components/espressif/esp_bt_audio/versions/1.2.0/readme), [TechPedia](https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/solution-introduction/multimedia/component-description/esp-bt-audio.html)). It is promising but young. Track it, but don't base v1 on it.
- **pschatzmann ESP32-A2DP + arduino-audio-tools (Arduino).** A thin wrapper over Bluedroid, SBC only out of the box ([repo](https://github.com/pschatzmann/ESP32-A2DP)). It is nice for a weekend prototype. Its wiki notes that RAM use grows with each core version, and the queued variant needs about 33 KB more RAM with a 32 KB ring buffer by default ([wiki: Sink Optimizations](https://github.com/pschatzmann/ESP32-A2DP/wiki/A2DP-Sink-Optimizations), edited Oct 2026). With Arduino core 3.x the legacy I2S API is gone. Arduino-ESP32's latest release is **3.3.13 (IDF 5.5.x)**. 4.0 on IDF 6 is planned ([roadmap](https://github.com/espressif/arduino-esp32/wiki/Release-Roadmap-and-Management)).
- **PlatformIO.** Official `platform-espressif32` still does not support Arduino core 3.x. The community **pioarduino** fork does (latest 55.03.39 = Arduino 3.3.9 / IDF 5.5.4) ([version table](https://github.com/sivar2311/platform-espressif32-versions), [PIO forum](https://community.platformio.org/t/esp32-arduino-core-3-x-and-platformio-status/42008)).

**Recommendation.** Use **ESP-IDF directly** (CMake + `idf.py`, VS Code ESP-IDF extension). Reasons:
1. Coexistence tuning, PSRAM placement of BT/Wi-Fi memory, task-to-core pinning and the I2S full-duplex driver are all menuconfig/IDF-level settings.
2. The AAC example and esp_bt_audio are IDF-only.
3. ESP-IDF v6.0 removed the legacy I2S driver ([v6.0 peripherals migration](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/migration-guides/release-6.x/6.0/peripherals.html)), so Arduino-era I2S code ages badly.

Pin to **v5.5 LTS** for a stable v1, and move to v6.1 if you want AAC. In either case use the new `driver/i2s_std.h` and `driver/i2c_master.h` APIs. The legacy I2C driver is end-of-life in v6.0.

**Wi-Fi + classic BT coexistence (the main risk)**

- The ESP32 has one 2.4 GHz radio, time-sliced between Wi-Fi, BT and BLE ([RF coexistence](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/coexist.html)). Its support table:
  - **STA (scan/connecting/connected) × BR/EDR connected = Y** (stable).
  - **SoftAP connecting/connected × BR/EDR connected = C1** ("supported but the performance is unstable").
  - So the web UI must run with the speaker as a **Wi-Fi station on the user's network**. SoftAP should be a provisioning-only mode, used while not streaming.
- Espressif's advice is to run the Wi-Fi task and the BT controller+host on **different CPUs** (`CONFIG_BTDM_CTRL_PINNED_TO_CORE_CHOICE`, `CONFIG_BT_BLUEDROID_PINNED_TO_CORE_CHOICE`) and to enable software coexistence (same page and the [coexistence FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/coexistence.html)).
- The FAQ says A2DP audio is "lost and lagged" while BLE scans run, and suggests a **RingBuf cache**. So: **disable BLE entirely** (`CONFIG_BTDM_CTRL_MODE_BR_EDR_ONLY`). This also frees about 30 KB.
- **Memory.** ESP-ADF's budget: Wi-Fi 50 KB+, BT 140 KB (95 KB with PSRAM), out of about 290 KB of spare internal RAM. Its guide states "Bluetooth and Wi-Fi can not coexist without PSRAM because it will not leave enough memory for an audio application" ([ADF design considerations](https://esp-adf.readthedocs.io/en/latest/design-guide/design-considerations.html); the sentence is in [this mirror of the older version](https://bio-hdf.readthedocs.io/en/latest/design-guide/design-considerations.html)). Add LVGL (about 40–60 KB), httpd plus websockets, and DSP buffers, and the **WROOM-32E is out of RAM**.
  - → **Use ESP32-WROVER-E (8 MB PSRAM, 4 MB directly mapped)** and enable `CONFIG_BT_ALLOCATION_FROM_SPIRAM_FIRST`, `CONFIG_BT_BLE_DYNAMIC_ENV_MEMORY`, `CONFIG_SPIRAM_TRY_ALLOCATE_WIFI_LWIP` and `CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=4096`.
  - Note: WROVER uses GPIO16/17 for PSRAM. Tell the electronics team.

**LE Audio.** Not possible on the ESP32 (classic). Espressif's LE Audio (LC3, CIS/BIS) is a **preview** on the **ESP32-S31**, which has dual-mode BT 5.4 and classic + LE Audio together ([LE Audio guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s31/api-guides/ble/ble-audio.html), [S31 audio page](https://esp32-s31.espressif.com/en/official-projects/5)). It is worth tracking for a v2: the S31 also runs the AAC example. Not worth it for v1.

### A2. TAS5805M DSP: configuration and live coefficient updates

**Tooling**
- TI **PurePath Console 3 (PPC3)** is how TI expects the process flow, EQ, crossover and DRC to be tuned. Access is **by request**: you order an EVM or request the TAS5805-SW app ([PPC3 page](https://www.ti.com/tool/PUREPATHCONSOLE), [E2E thread](https://e2e.ti.com/support/audio-group/audio/f/audio-forum/885769/tas5805m-purepath-startup-problems)). It is effectively **Windows-first**. A Mac build existed (v3.0.8) but TI staff said it "has not been heavily tested" and recommended Windows ([E2E](https://e2e.ti.com/support/audio-group/audio/f/audio-forum/658326/tas5782mevm-purepathconsole-3-on-mac-don-t-recognize-tas5782)). Use a Windows-on-ARM VM (Parallels or UTM) or a borrowed PC only to export the base config.
- PPC3 exports a **register dump** (`cfg_reg {offset, value}` arrays, the "w 58 7f 8c"-style scripts). Both the Linux driver and the ESP32 drivers replay these at boot.

**Process flows** ([SLOA263A](https://www.ti.com/lit/pdf/sloa263))
- All three flows give **15 biquads per channel (L/R independent)**, an input mixer, click/pop-free volume, 3-band DRC (4th-order crossover), AGL and a clipper.
- **Flow 1: SRC to 96 kHz internally**, inputs at 32/44.1/48/88.2/96 kHz.
- **Flows 2 and 3: 48 kHz, no SRC** (flow 2 adds a 128-tap FIR).
- **Recommendation: Process Flow 1.** A2DP arrives at 44.1 *or* 48 kHz depending on the phone. With the SRC, one set of amp coefficients, designed at 96 kHz, works at either rate. Without the SRC, every biquad would have to be recomputed and rewritten whenever the stream rate changes.
- Supported topologies include **"2.2 Dual Stereo" (one chip drives both tweeters, the other both woofers)**. Our block diagram does "per-side" bi-amping (AMP_L = woofer L + tweeter L). That also works: set the input mixer (Book 0x8C, page 0x29, regs 0x18–0x24, 9.23 format) so both outputs take the Left input, then use each channel's 15 BQs as LR4 low-pass + driver EQ or LR4 high-pass + tweeter EQ. **Tell the electronics team:** the "woofer chip / tweeter chip" split is TI's tested topology, and it puts the woofers' current demand on a single chip.

**Coefficient format, checked against a real PPC3 dump**
- SLOA263A Table 6 lists BQs in **Book 0xAA**, e.g. `CH-L BQ1 B0` at page **0x24**, reg **0x18**. Each coefficient is "4 / **5.27**" and B0 defaults to `0x08000000` (= 1.0).
- Coefficient order is **B0, B1, B2, A1, A2** (20 bytes per BQ), big-endian, a0-normalised, with **A1 = −a1** and **A2 = −a2**.
- SLOA263 Table 3 implies B1 and A1 are divided by 2. **The PPC3-generated tables in the sonocotta driver are not halved.** Decoding their "BQ1 Left, 20 Hz, −15 dB, Q 2" entry gives `[0.99849, −1.99633, 0.99784, +1.99633, −0.99633]`. That matches an RBJ peaking filter at 48 kHz with **b1 ≈ −2 stored as-is and the a-terms negated**. `tools/tas5805m_bq.py` encodes and decodes this and checks it against the dump **[measured]**.
- Volume is in **Book 0x8C / page 0x2A / regs 0x24 and 0x28 (9.23)**. That matches datasheet Example 2 and the Linux driver.
- **BQ addresses depend on the flow loaded at boot.** Always start from a PPC3 (or sonocotta) base dump for the chosen flow, then overwrite BQs at that flow's addresses.

**Safe live-update procedure** ([datasheet SLASEH5D §7.5.2.5, §7.5.3.1, regs 0x5C/0x71](https://www.ti.com/lit/gpn/tas5805m))
1. Startup per the datasheet: PDN high → wait 5 ms → start I2S clocks → put the device in HiZ and enable the DSP → wait ≥ 5 ms → load the coefficient dump → Play.
2. To change a book you must be on page 0. Write all **5 coefficients of a BQ "entirely and sequentially, lowest address to highest"**, as **one 20-byte auto-increment I2C burst**.
3. The datasheet has `BQ_WR_CTRL1` (0x5C) bit 0 **`BQ_WR_FIRST_COEF`** ("indicate the first coefficient of a BQ is starting to write") and the `GLOBAL_FAULT1` bit 6 **`BQ_WR_ERROR`** ("the recent BQ is written failed"). This suggests the DSP latches whole biquads, but TI doesn't spell out the procedure. **Bench-test this.**
4. There is no documented double-buffer/safeload for the whole filter bank. For multi-BQ changes such as a crossover or preset switch: ramp the DSP volume down (the click-free volume block, with an adjustable softening time constant) → write → ramp up. Small single-band gain steps can be written live.
5. Cost: about 25 bytes per BQ including the address, so **≈ 0.6 ms per BQ at 400 kHz**. All 60 BQs (2 chips × 2 ch × 15) take about 40 ms. That is fast enough for slider drags if updates are rate-limited to about 20 Hz.

**Open-source code to reuse or read**
- **Linux `sound/soc/codecs/tas5805m.c`** (mainline). Loads a PPC3 dump as firmware `tas5805m_dsp_<name>.bin`, and does volume via the undocumented-in-datasheet Book 0x8C/page 0x2A. No runtime EQ.
- **[sonocotta/esp32-tas5805m-dac](https://github.com/sonocotta/esp32-tas5805m-dac)** (ESP-IDF/Arduino, active Sep 2026). Startup dumps, a 15-band EQ from **precomputed PPC3 tables** (±15 dB in 1 dB steps), mixer and modulation modes, fault decoding. A good base for the I2C layer.
- **[mrtoy-me/esphome-tas5805m](https://github.com/mrtoy-me/esphome-tas5805m)**, now ESPHome **`tas58xx`** ([docs](https://esphome.io/components/audio_dac/tas58xx/), [HA thread](https://community.home-assistant.io/t/tas58xx-dac-component-with-dsp-controls/994422)). 15-band EQ, plus bi-amp "EQ profiles" with 4th-order LF/HF crossovers at 60–150 Hz.
- **[heytcass/louder-esphome-sendspin](https://github.com/heytcass/louder-esphome-sendspin)**. Computes biquads at runtime and writes them over I2C for room correction. Note: it is AI-written, its helper is named `float_to_9_23`, and its page offsets differ from SLOA263. **Treat it as unverified.**

**Verdict.** Computing coefficients ourselves (Python for design and C on the device) and writing them live is **practical**. Recommended split:
- **On the TAS5805M (fixed, written at boot and changed rarely):** crossover, driver EQ, DRC/AGL, clipper. This is the "safe even if the MCU glitches" layer.
- **On the ESP32 (smooth and glitch-free, parameters interpolated per block):** user EQ, loudness and the auto-EQ correction.
- If more ESP32 headroom is needed later, user EQ can move to spare TAS BQs using the mute-ramp procedure.

### A3. ESP32 DSP headroom

esp-dsp benchmarks for ESP32 ([esp-dsp benchmarks](https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-benchmarks.html), optimised asm column):
- `dsps_biquad_f32`, 1024 samples: **17 442 cycles → 17 cycles/sample**. The ANSI C version is about 31.
- `dsps_fft4r_fc32`, 1024-pt: **75 068 cycles (0.31 ms at 240 MHz)**. `fft2r` 1024-pt: 113 205 cycles.
- `dsps_fir_f32`, 256 taps × 1024 samples: about 1.08 M cycles, i.e. 1053 cycles/sample. Long FIRs are expensive, so use IIR.

Budget at 48 kHz stereo = 96 k samples/s **[estimate]**:

| Block | Implementation | Mcycle/s |
|---|---|---|
| User EQ, 10 peaking biquads | esp-dsp biquad ×10 ×2 ch | 16 |
| Loudness (volume-tracking low and high shelf) | 2 BQ ×2 ch + gain smoothing | 4 |
| Bass enhancer ("virtual bass") | Mono sum → BP 60–120 Hz → full-wave/poly nonlinearity → BP/HP → mix, about 5 BQ | 6 |
| Stereo widener | M/S, shelving on S, about 2 BQ | 4 |
| Look-ahead limiter (1–2 ms) | Peak detector + gain smoother + delay line | 4–6 |
| Format conversion, volume, dither | | 3 |
| **Total** | | **≈ 40 (≈ 17 % of one core)** |

- SBC decoding in Bluedroid adds roughly another 5–10 % of a core **[estimate]**.
- AAC-LC decoding is several times heavier than SBC **[estimate, measure]**.
- LVGL partial redraws and httpd are bursty but light.
- **Conclusion:** everything in the requirements fits with more than 50 % margin, as long as the processing is single-precision float (the ESP32 FPU is SP only; avoid `double` and divides in the hot loop).

### A4. Mic-based auto-EQ

**How the big products do it**
- **Sonos Auto Trueplay** uses the built-in mics, works on *the music playing* rather than test tones, and re-tunes as the speaker moves. Sonos says it is limited because it "can only respond to sound in the immediate vicinity of the product" ([Sonos tech blog](https://tech-blog.sonos.com/posts/trueplay-spectral-correction/), [support](https://support.sonos.com/en-us/article/automatic-trueplay-tm)). Manual Trueplay uses a crafted test tone and a moving phone mic.
- **Apple HomePod.** Apple's marketing describes "room sensing" from reflections plus a bass-EQ mic that "dynamically tunes low frequencies in real time" ([HomePod page](https://www.apple.com/uk/homepod-2nd-generation)). The related patent, filed Jan 2016, uses mics **inside and outside** the sealed enclosure: the inside mic gives driver output (cone volume velocity) and the outside mic sees the boundary loading. Adaptive EQ then corrects boundary bass build-up ([AppleInsider](https://appleinsider.com/articles/17/07/06/apple-invention-appears-to-detail-homepods-adaptive-acoustics)).
- **Amazon Echo Studio** plays tones at setup, then "continuously" adjusts filters using its far-field mics ([Amazon](https://www.aboutamazon.com/news/devices/amazon-echo-dot-max-echo-studio-sound-quality-bass)). No algorithmic detail is published.
- **Classic measurement method.** An exponential sine sweep (Farina) plus inverse-filter deconvolution gives the impulse response and separates harmonic distortion. MLS is the alternative but is more sensitive to distortion and time variance. REW uses log sweeps ([REW features](https://roomeqwizard.com/features.html)).

**Our mic's limits**
- INMP441: SNR 61 dBA, so self-noise ≈ 33 dBA, AOP 120 dB SPL. ICS-43434: SNR 65 dBA, self-noise ≈ 29 dBA, AOP 120 dB ([TDK INMP441](https://invensense.tdk.com/digital/inmp441), [ICS-43434 DS](https://cdn.sparkfun.com/assets/a/9/c/9/1/DS-000069-ICS-43434-v1.2.pdf)). Users report the self-noise of cheap ESP32 modules varies with I2S configuration ([esp32-i2s-slm #19](https://github.com/ikostoski/esp32-i2s-slm/issues/19)). **Prefer the ICS-43434** (LCSC-available, better SNR, 24-bit).
- **It is a near-field mic.** On the enclosure it sees mostly direct woofer output. It can only detect nearby boundaries (wall or table within about 0.5 m), which is exactly the placement case we care about, but not the room's modal response.
- **Structure-borne vibration is the biggest risk.** The enclosure walls and the PR end caps move. Mount the mic on a small flex or daughterboard with a gasket and a **sealed acoustic port to the outside**. It must be isolated from the internal cavity, which runs about 20–30 dB hotter. Put it on the top, away from the PRs. Plan a bench check: with the speaker playing in free field, the mic's 50–300 Hz response must be repeatable within ±1 dB across units.
- **Overload.** 90 dB @ 1 m can be 110–115 dB SPL at a few cm. That is under the 120 dB AOP, but keep a −6 dB margin in the measurement mode.
- **Sync.** Run the mic on the **same I2S peripheral in full duplex** (I2S0 TX → amps, I2S0 RX ← mic, shared BCLK/LRCLK). Capture is then sample-locked to playback, with no drift, which makes deconvolution trivial.

**Concrete v1 algorithms**

*(a) Placement (boundary) bass compensation: "Tune" button plus automatic check on wake*
1. **Factory reference.** With the speaker in free space (outdoors, or on a stand in a big room, ≥ 1.5 m from surfaces), play a 2 s log sweep 30 Hz–2 kHz at −20 dBFS through the woofers. Record with the onboard mic. Store the 1/6-octave magnitude response `R_ref(f)` in NVS (per unit or per design).
2. **In use.** Fade the music, play the same sweep at a comfortable level (about 70 dB @ 1 m), capture, deconvolve via FFT (esp-dsp, 8k–16k points from PSRAM), and window the IR to about 20 ms. That window keeps near boundaries (≤ 3 m path) and rejects late room reverb. Compute `R(f)`.
3. Take `Δ(f) = smooth(R − R_ref)` over 40–400 Hz and normalise to the 500 Hz–1 kHz band so the volume setting cancels out.
4. Fit a **single low-shelf** (fc 80–250 Hz, gain −8…+2 dB) and optionally one peaking cut, by least squares with limits (cut-biased: boost ≤ +2 dB to protect excursion).
5. Apply it on the ESP32 EQ (or a spare TAS BQ) with a 2 s crossfade.
6. Simpler fallback: classify `Δ` over 60–200 Hz into {free, near wall/table, corner} → presets {0, −3, −6 dB} at 150 Hz.
7. Later "music-based" (Auto-Trueplay-like) v2: estimate H = S_xy/S_xx continuously from the known output x and mic signal y, averaged over minutes, and only update when coherence > 0.9.

*(b) Ambient-noise adaptive loudness*
1. Every 100 ms compute band levels (A-weighted, or 3 bands) of mic `y` and of the predicted speaker contribution `ŷ = H·x`, using H from (a) or a calibration.
2. Ambient estimate `N = power(y) − power(ŷ)` over bands where `ŷ` is at least 6 dB below `y`. Also use a **minimum-statistics** tracker over a 10–20 s window, so music peaks and transients don't count as noise.
3. Gain rule: `boost = clamp(0.5·(N − 45 dBA), 0, +10 dB)`, slewed at ≤ 1 dB per 3 s with 3 dB hysteresis, and capped by the limiter and battery headroom. Feed the same offset into the loudness shelf (less bass boost as level rises, per equal-loudness contours).
4. Disable it when the measured `N` is below about 40 dBA, because that is near the mic's self-noise plus vibration floor.

Feasibility: everything above is FFT plus biquads at a low update rate. It costs a few % of a core, plus about 64–128 KB of PSRAM for capture buffers.

### A5. Display / UI (GC9A01 + LVGL)

- **Drivers:** `espressif/esp_lcd_gc9a01` (esp_lcd panel driver) + `espressif/esp_lvgl_port`, with LVGL v9.x. A 2026 forum setup used ESP-IDF 6.0, LVGL 9.5 and esp_lcd_gc9a01 2.0.4 ([esp32.com thread](https://esp32.com/viewtopic.php?p=154440)).
- **Bandwidth.**
  - 240×240×16 bit = 115 KB per full frame. At 40 MHz SPI that is about 23 ms per frame (≈ 40 fps max). At 80 MHz (IOMUX pins of SPI2/3 only) it is about 12 ms **[estimate]**.
  - A level meter or rotary-arc UI only redraws small areas, so 30 fps is easy.
  - There is no tearing-effect sync over SPI: Espressif's adapter only supports tear-avoid modes on RGB/MIPI ([ESP LVGL adapter](https://docs.espressif.com/projects/esp-iot-solution/en/latest/display/tools/esp_lvgl_adapter.html)). Design animations to tolerate it.
- **RAM.**
  - Two partial draw buffers of 240×24 px × 2 B = **2 × 11.5 KB in internal DMA-capable RAM**. SPI DMA cannot read PSRAM directly; esp_lcd bounces through an internal buffer if you try.
  - Use 10–25 % of the screen for the draw buffers. Above 25 % gives little gain, and below 10 % hurts ([esp_lvgl_port perf notes](https://github.com/Lzw655/esp-bsp/blob/master/components/esp_lvgl_port/docs/performance.md)).
  - LVGL heap goes in PSRAM.
- Put the LVGL task on the **same core as Wi-Fi (core 1 in the plan below) at low priority**. Its SPI DMA does not compete with I2S DMA in any meaningful way.

---

## Recommended firmware architecture (ESP-IDF, ESP32-WROVER-E)

```
            ┌──────────────────────────── CORE 0 ────────────────────────────┐
 Phone ──BT─►  BT controller + Bluedroid (A2DP sink, AVRCP; SBC decode)       │
            │     a2d data cb ──► PCM ring buffer (RingBuf, 32 KB internal or  │
            │                      64–96 KB PSRAM ≈ 200–400 ms @44.1k/16b/st)  │
            │  ctrl_task (prio 10): encoder/buttons (PCNT+GPIO ISR), power,    │
            │     fuel gauge/charger poll, NVS presets                         │
            │  i2c_task (prio 9): sole owner of I2C bus → TAS5805M ×2 (boot    │
            │     dumps, BQ/vol updates w/ ramp), charger, gauge; fault poll   │
            └──────────────────────────────────────────────────────────────────┘
            ┌──────────────────────────── CORE 1 ────────────────────────────┐
            │  audio_task (prio 22, highest app prio): block = 256 frames      │
            │     ring buf → int16→f32 → [param swap @block edge] → user EQ →  │
            │     loudness → bass enh → widener → limiter → vol → s32 → I2S0 TX│
            │     I2S0 RX (mic, same clocks) → mic ring buffer                 │
            │  Wi-Fi/lwIP (IDF prio 23) + esp_http_server + websocket          │
            │     (static SPA from LittleFS; JSON param msgs; meter stream)    │
            │  mic_task (prio 5): FFT, sweep/deconv, noise tracker → params    │
            │  lvgl_task (prio 3): esp_lvgl_port, 30 fps, partial buffers      │
            └──────────────────────────────────────────────────────────────────┘
 I2S0 (APLL clocked, full duplex): BCLK/LRCLK/DOUT → both TAS5805M (DIN shared, ADR-pin addresses)
                                   DIN ← ICS-43434
 I2S DMA: 6 desc × 256 frames (~35 ms) ; total added latency ≈ ring 200 ms + DMA 35 ms + TAS SRC
 Control plane: web/encoder → param_store (NVS) → queue → audio_task (atomic double-buffered coeffs,
                interpolated over 1 block) or i2c_task (TAS writes, rate-limited 20 Hz)
```

Key settings:
- BR/EDR-only controller (no BLE), software coexistence on, BT controller + host pinned to core 0, Wi-Fi to core 1.
- BT, Wi-Fi and LwIP allocated from SPIRAM first.
- STA mode for the UI; SoftAP + captive portal only for provisioning while not streaming.
- AVRCP absolute volume mapped to ESP32 digital volume, not TAS volume. TAS volume is reserved for click-free mute ramps.
- OTA over Wi-Fi with two OTA partitions in 4 MB+ flash.
- Each I2S sample-rate change (44.1↔48) re-clocks I2S0. TAS flow 1's SRC absorbs it, so no TAS rewrite is needed.

---

## Part B: simulation tools on macOS arm64

### What I installed and tested [measured]

| Package | Version | Result |
|---|---|---|
| Python (Homebrew) | **3.14.10** | Venv at `.venv/` (3.14.6 at creation; `brew install python-tk@3.14` bumped it) |
| numpy / scipy / matplotlib | 2.5.5 / 1.18.1 / 3.11.2 | OK. `sim/smoke/basic_stack.py`: 2nd-order HP F3 = 64.9 Hz (expected 65), bilinear biquad, PNG written |
| gmsh (pip wheel, includes CLI) | 4.15.2 | OK. OCC capsule (210 × 90 mm) surface mesh, 764 triangles at 4 kHz/6 el per λ |
| numba / llvmlite | 0.68.1 / 0.50.0 | OK (bempp backend) |
| **bempp-cl** | **0.4.2** (import name `bempp_cl`) | **OK.** `sim/smoke/bempp_pulsating_sphere.py`: 5 cm pulsating sphere at 1 kHz, 1066 P1 DOFs, direct BIE + GMRES, **rel. error 0.22 %** at 0.2/0.5/1 m against the analytic monopole, **16 s** on M4 (numba) |
| bempp OpenCL backend | pyopencl 2026.1.5 | **Fails.** Apple's OpenCL only exposes the M4 GPU and bempp requires a CPU OpenCL device ("Could not find suitable OpenCL CPU driver"). pyopencl removed again; numba is the default. |
| **ElectroacPy** | 2025.7.1 | **OK** after `brew install python-tk@3.14` (it imports tkinter). Pulls in pyvista/vtk 9.7.2 and pandas. `sim/smoke/electroacpy_pr_box.py`: sealed fc 139.9 Hz vs closed form 139.3 Hz; **passive radiator** box/PR resonance 86.2 Hz vs closed form 86.4 Hz |
| FreeCAD → STEP → gmsh → bempp | FreeCAD 1.1.3 `freecadcmd` | **OK.** `sim/smoke/freecad_make_capsule.py` (headless STEP export) → `sim/smoke/step_to_bempp.py` → `bempp.import_grid` (762 triangles). **STEP is in mm**: scale to m (`gmsh.option.setNumber("Geometry.OCCScaling", 1e-3)`) before BEM. |

Gotcha: bempp finds gmsh by looking for the `gmsh` executable on `PATH`. **Activate the venv** (or `export PATH=$PWD/.venv/bin:$PATH`), otherwise `bempp.shapes.*` fails with "Gmsh is not found".

### Other tools (availability on this Mac)

- **FreeCAD FEM + CalculiX.** FreeCAD 1.1.3 bundles **`ccx` 2.23 (native arm64)** at `/Applications/FreeCAD.app/Contents/Resources/bin/ccx`, plus **gmsh 4.15.0** **[measured]**. Steady-state and transient thermal analysis work in the FEM workbench with no extra install.
- **Elmer FEM.** No Homebrew formula in core. The official tap `elmercsc/homebrew-elmerfem` has a history of build failures. Apple Silicon builds need a custom toolchain with Homebrew gcc/gfortran ([tap issues](https://www.github.com/ElmerCSC/homebrew-elmerfem/issues/11), [MacPorts port](https://ports.macports.org/port/elmerfem/), last updated about 2 years ago). **Skip it.** CalculiX plus our own finite-difference solver cover PCB thermal.
- **REW.**
  - Stable V5.31.3 (Jul 2024) and **beta V5.40 (b118 Feb 2026+)**. The macOS build bundles its own Java runtime, 17 in the recent betas ([REW](https://roomeqwizard.com), [beta notes](https://www.roomeqwizard.com/beta.html)).
  - I couldn't confirm a native arm64 build from an authoritative source. It runs under Rosetta if it isn't native. **Rosetta's end is announced:** CodeWeavers says the next macOS is the last with Rosetta, so check arm64 status in the newest beta.
  - **UMIK-1** is recognised natively. Load the per-serial cal file, and REW reads the sensitivity from it. On macOS, grant Microphone permission, or run `tccutil reset Microphone` ([REW setup](https://www.roomeqwizard.com/help/help/html/calsoundcard.html)).
  - Use REW's EQ export (biquad text) as input to our `tas5805m_bq.py` encoder.
- **VituixCAD, WinISD, Hornresp, ABEC3** are all **Windows-only**.
  - Options on Apple Silicon:
    - **CrossOver** (paid, `brew install --cask crossover`, v26.3.0). A preview build has native ARM64 Wine on macOS 26.5+, which this Mac has ([CodeWeavers blog, Jul 2026](https://www.codeweavers.com/blog/mjohnson/2026/07/31/crossover-preview-the-right-to-bear-arm64-on-mac)).
    - **Kegworks/Wineskin** (free).
    - **Whisky** is discontinued (Apr 2025) ([MacRumors](https://www.macrumors.com/2025/04/23/whisky-ends-mac-gaming-tool-crossover/)).
    - **Windows 11 ARM in Parallels/UTM** runs x64 apps through Microsoft's emulator, and is the most reliable route.
  - VituixCAD's CrossOver compatibility entry is **unrated** ([CodeWeavers DB](https://www.codeweavers.com/compatibility/crossover/vituixcad)). It is a .NET app, so a Windows-ARM VM is the safer bet.
  - **Recommendation:** use a UTM/Parallels Win11-ARM VM for VituixCAD, PPC3 and (optionally) WinISD/Hornresp, and use them only as cross-checks.
- **Python lumped-element loudspeaker libraries.**
  - **ElectroacPy** (above) has sealed, vented, **passive radiator**, 4th/6th-order bandpass, crossover design, and a bempp-cl BEM front-end ([docs](https://electroacpy.readthedocs.io/en/latest/01-ac-LEM.html)). It is the only mature option that covers PRs.
  - The others are teaching-grade: Scimpy, `eridgraves/single_driver_br_python` and `jmpolom/Vented` (sealed/ported only).
  - **Recommendation:** write our own small T/S + PR model (it's about 150 lines and is the point of the learning exercise), and **validate it against ElectroacPy** and WinISD.
- **FreeCAD → gmsh for BEM.** Export STEP (headless `freecadcmd` script shown above, or GUI) → gmsh Python API `occ.importShapes` → set `Mesh.MeshSizeMax` ≈ λ_min/6 → tag diaphragm faces as physical groups so they become bempp domain indices for velocity BCs → write MSH 2.2 → `bempp.import_grid`. FreeCAD's FEM workbench also has a built-in Gmsh mesher (FEM → Mesh from shape by Gmsh), but the scripted route is reproducible.

### Build ourselves vs off the shelf

| Domain | Write ourselves (learning + visualisation) | Use off the shelf |
|---|---|---|
| Box/PR alignment | **Yes.** T/S + PR lumped model, excursion, port/PR velocity, with DSP EQ applied, as matplotlib/plotly dashboards | ElectroacPy as the numerical cross-check; WinISD/VituixCAD in a VM optional |
| Crossover / EQ / TAS coefficients | **Yes.** scipy biquad design → `tas5805m_bq.py` → register dump; plot the summed response | PPC3 once for the base dump and flow; REW for measured EQ |
| Directivity / diffraction | Thin wrapper only (mesh, BCs, polar plots) | **bempp-cl** solver; ElectroacPy BEM helpers |
| PCB thermal | **Yes.** 2-D finite-difference heat spreading with heatmaps (fast, intuitive) | **CalculiX via FreeCAD FEM** for the 3-D cross-check |
| Acoustic measurement | No | **REW + UMIK-1** |
| Auto-EQ algorithms | **Yes.** Prototype sweep/deconv and noise tracker in numpy against REW captures, then port to C | — |

### Exact environment-setup commands (all ran successfully on 2026-11-24)

```bash
cd /Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test
/opt/homebrew/bin/python3.14 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install numpy scipy matplotlib gmsh numba bempp-cl   # bempp-cl pulls meshio, rich
brew install python-tk@3.14                                         # needed by ElectroacPy (tkinter)
.venv/bin/pip install electroacpy                                   # pulls pyvista, vtk, pandas, plotly
.venv/bin/pip freeze > requirements-sim.txt                         # 47 pinned packages

# smoke tests (activate so bempp finds the gmsh CLI on PATH)
source .venv/bin/activate
python sim/smoke/basic_stack.py
python sim/smoke/bempp_pulsating_sphere.py          # PASS, 0.22 % error, ~16 s
MPLBACKEND=Agg python sim/smoke/electroacpy_pr_box.py
CAPSULE_STEP=$PWD/sim/smoke/out/capsule.step \
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd sim/smoke/freecad_make_capsule.py
python sim/smoke/step_to_bempp.py sim/smoke/out/capsule.step 4000
python tools/tas5805m_bq.py                          # TAS5805M 5.27 encoder vs PPC3 dump
/Applications/FreeCAD.app/Contents/Resources/bin/ccx -v   # CalculiX 2.23
```

Rebuild from the lock file: `python3.14 -m venv .venv && .venv/bin/pip install -r requirements-sim.txt` (still needs `python-tk@3.14` from brew).

---

## Key risks (ranked)

1. **RAM / BT+Wi-Fi coexistence on WROOM-32E.** High likelihood of OOM or dropouts. → Switch to WROVER-E (PSRAM). STA-only while streaming. BR/EDR-only BT. Large ring buffer. Test early with a dev board doing A2DP + httpd + websocket meter + LVGL simultaneously.
2. **TAS5805M live-update glitches.** No documented safeload. → One-burst-per-BQ, mute-ramp for multi-BQ changes, keep user EQ on the ESP32, verify the `BQ_WR_FIRST_COEF`/`BQ_WR_ERROR` behaviour on the bench.
3. **PPC3 access and platform.** It is request-gated and Windows-first. → Get access now; run it in a Win11-ARM VM. Our own coefficient encoder covers the rest.
4. **Mic auto-EQ validity.** Vibration pickup and near-field bias. → Mechanical isolation of the mic port, a factory reference curve, cut-biased limits, and a 3-preset classifier as fallback.
5. **AAC** only on IDF ≥ 6.1 with software decode. Treat it as stretch. SBC at bitpool 53 is what most Android/iOS phones send to a non-AAC sink anyway.

## Sources

- ESP-IDF RF coexistence (v6.1.1): https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/coexist.html
- ESP FAQ coexistence: https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/coexistence.html
- ESP-IDF A2DP API: https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/bluetooth/esp_a2dp.html
- ESP-ADF design considerations: https://esp-adf.readthedocs.io/en/latest/design-guide/design-considerations.html ; older-version mirror: https://bio-hdf.readthedocs.io/en/latest/design-guide/design-considerations.html
- esp_bt_audio 1.2.0: https://components.espressif.com/components/espressif/esp_bt_audio/versions/1.2.0/readme
- ESP-BT-AUDIO TechPedia: https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/solution-introduction/multimedia/component-description/esp-bt-audio.html
- ESP-IDF LE Audio (ESP32-S31): https://docs.espressif.com/projects/esp-idf/en/latest/esp32s31/api-guides/ble/ble-audio.html ; https://esp32-s31.espressif.com/en/official-projects/5
- ESP-IDF v6.0 peripherals migration: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/migration-guides/release-6.x/6.0/peripherals.html
- pschatzmann ESP32-A2DP: https://github.com/pschatzmann/ESP32-A2DP ; wiki: https://github.com/pschatzmann/ESP32-A2DP/wiki/A2DP-Sink-Optimizations
- Arduino-ESP32 roadmap: https://github.com/espressif/arduino-esp32/wiki/Release-Roadmap-and-Management
- pioarduino versions: https://github.com/sivar2311/platform-espressif32-versions ; PIO forum: https://community.platformio.org/t/esp32-arduino-core-3-x-and-platformio-status/42008
- esp-dsp benchmarks: https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-benchmarks.html
- TI SLOA263A process flows: https://www.ti.com/lit/pdf/sloa263 ; TAS5805M datasheet SLASEH5D: https://www.ti.com/lit/gpn/tas5805m
- TI PPC3: https://www.ti.com/tool/PUREPATHCONSOLE ; E2E threads: https://e2e.ti.com/support/audio-group/audio/f/audio-forum/885769/tas5805m-purepath-startup-problems , https://e2e.ti.com/support/audio-group/audio/f/audio-forum/658326/tas5782mevm-purepathconsole-3-on-mac-don-t-recognize-tas5782
- Linux tas5805m driver: https://github.com/torvalds/linux/blob/master/sound/soc/codecs/tas5805m.c
- sonocotta/esp32-tas5805m-dac: https://github.com/sonocotta/esp32-tas5805m-dac ; mrtoy-me/esphome-tas5805m: https://github.com/mrtoy-me/esphome-tas5805m ; ESPHome tas58xx: https://esphome.io/components/audio_dac/tas58xx/ ; HA thread: https://community.home-assistant.io/t/tas58xx-dac-component-with-dsp-controls/994422 ; heytcass/louder-esphome-sendspin: https://github.com/heytcass/louder-esphome-sendspin
- Sonos Trueplay: https://tech-blog.sonos.com/posts/trueplay-spectral-correction/ ; https://support.sonos.com/en-us/article/automatic-trueplay-tm
- Apple: https://www.apple.com/uk/homepod-2nd-generation ; https://appleinsider.com/articles/17/07/06/apple-invention-appears-to-detail-homepods-adaptive-acoustics
- Amazon: https://www.aboutamazon.com/news/devices/amazon-echo-dot-max-echo-studio-sound-quality-bass
- TDK INMP441: https://invensense.tdk.com/digital/inmp441 ; ICS-43434 DS: https://cdn.sparkfun.com/assets/a/9/c/9/1/DS-000069-ICS-43434-v1.2.pdf ; esp32-i2s-slm issue: https://github.com/ikostoski/esp32-i2s-slm/issues/19
- GC9A01/LVGL: https://esp32.com/viewtopic.php?p=154440 ; https://docs.espressif.com/projects/esp-iot-solution/en/latest/display/tools/esp_lvgl_adapter.html ; https://github.com/Lzw655/esp-bsp/blob/master/components/esp_lvgl_port/docs/performance.md
- REW: https://roomeqwizard.com ; https://www.roomeqwizard.com/beta.html ; https://www.roomeqwizard.com/help/help/html/calsoundcard.html ; https://roomeqwizard.com/features.html
- CrossOver ARM64 preview: https://www.codeweavers.com/blog/mjohnson/2026/07/31/crossover-preview-the-right-to-bear-arm64-on-mac ; VituixCAD entry: https://www.codeweavers.com/compatibility/crossover/vituixcad ; Whisky end: https://www.macrumors.com/2025/04/23/whisky-ends-mac-gaming-tool-crossover/
- Elmer on macOS: https://www.github.com/ElmerCSC/homebrew-elmerfem/issues/11 ; https://ports.macports.org/port/elmerfem/
- ElectroacPy: https://electroacpy.readthedocs.io/en/latest/01-ac-LEM.html
