#!/bin/bash
# Post-layout physics checks on a KiCad board, compared against the rev A hybrid board.
#   ./run_all.sh BOARD.kicad_pcb [TAG] [--full]
# Default runs analyses 2-5 (return paths, copper balance, IR drop, thermal), ~2 min.
# --full adds FastHenry: hot loops (analysis 1, ~5 min) and the PDN fold-in (~15 min).
# The board is copied into work/ and read with KiCad's Python; it is never modified.
# Figures get the suffix _TAG so the rev A set is kept.
set -euo pipefail
cd "$(dirname "$0")"
BOARD=${1:?usage: run_all.sh BOARD.kicad_pcb [TAG] [--full]}
TAG=${2:-revb}
FULL=${3:-}
PY=../../.venv/bin/python
CMP=${POSTLAYOUT_COMPARE:-hybrid}
export POSTLAYOUT_FIGSUFFIX="_${TAG}"
$PY -c "import pl_common as p; print(p.extract('$BOARD', '$TAG'))"
for t in $CMP; do [ -f "work/$t.json" ] || { echo "missing work/$t.json (run extract on it)"; exit 1; }; done
$PY return_paths.py $CMP "$TAG"
$PY copper_balance.py $CMP "$TAG"
$PY ir_drop.py $CMP "$TAG"
$PY thermal.py $CMP "$TAG"
if [ "$FULL" = "--full" ]; then
  $PY fh_loops.py "$TAG"
  $PY fh_plots.py $CMP "$TAG"
  $PY pdn_fold.py $CMP "$TAG"
fi
$PY summary.py $CMP "$TAG"
