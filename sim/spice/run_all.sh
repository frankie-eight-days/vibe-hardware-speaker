#!/usr/bin/env bash
# Run every SPICE / PDN simulation (S1-S7) and regenerate all figures and result files.
# Requires: ngspice (brew install ngspice) and the project venv (numpy, scipy, matplotlib).
#
#   ./run_all.sh            # everything (the TI switching runs take ~1-2 h on 5 cores)
#   ./run_all.sh --fast     # skip the TI switching model; reuse results/s1_start*/s1_step* CSV+JSON
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PY="$ROOT/.venv/bin/python"
cd "$HERE"

if [[ "${1:-}" != "--fast" ]]; then
  echo "== S1 TPS61178 switching model (TI SLVMC02A, ngspice psa mode; cached raw files are reused)"
  "$PY" s1_boost_switching.py run
  echo "== S1 switching-model analysis";  "$PY" s1_boost_switching.py plot
  rm -f ti_runs/*.raw   # raw files are large; the CSV/JSON in results/ keep everything plotted
fi
echo "== S1 averaged loop model";         "$PY" s1_boost_loop.py
echo "== S2 class-D output filter";       "$PY" s2_classd_filter.py > results/s2_stdout.txt
echo "== S3 battery NTC / TS window";     "$PY" s3_ntc.py > results/s3_stdout.txt
echo "== S4 PVDD_TRIM network";           "$PY" s4_pvdd_trim.py > results/s4_stdout.txt
echo "== S5 ESP32 auto-reset";            "$PY" s5_esp32_reset.py > results/s5_stdout.txt
echo "== S6 FFC signal integrity";        "$PY" s6_ffc_si.py > results/s6_stdout.txt
echo "== S7 PDN (pre-layout)";            "$PY" ../pdn/pdn_rails.py > ../pdn/results/s7_stdout.txt
echo "done: figures in docs/figures/spice and docs/figures/pdn, data in sim/spice/results and sim/pdn/results"
