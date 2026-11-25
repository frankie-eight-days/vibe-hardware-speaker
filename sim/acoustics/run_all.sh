#!/bin/sh
# Re-run every acoustics simulation (A1-A5).  Heavy jobs run strictly one after another.
#   sh sim/acoustics/run_all.sh          # reuse existing BEM sweeps / FEM results if present
#   FORCE=1 sh sim/acoustics/run_all.sh  # recompute everything (~2.5 h on an M4, peak RAM ~3 GB)
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/sim/acoustics"
export PATH="$ROOT/.venv/bin:$PATH"      # bempp needs the gmsh CLI from the venv on PATH
export MPLBACKEND=Agg
PY="$ROOT/.venv/bin/python"

echo "== A1 bass system (lumped, + electroacPy cross-check)";  $PY a1_bass_lumped.py
echo "== BEM validation (piston on a sphere, exact series)";    $PY bem_validation.py
echo "== BEM hull mesh vs CAD figure";                          $PY bem_geometry_fig.py
for c in bezel waveguide flush bmcheck; do   # restartable: finished frequencies are checkpointed
  if [ "${FORCE:-0}" = "1" ] || [ ! -f "results/bem_$c.npz" ]; then
    echo "== BEM sweep: $c";  $PY bem_capsule_run.py "$c"
  else
    echo "== BEM sweep: $c (cached results/bem_$c.npz)"
  fi
done
if [ "${FORCE:-0}" = "1" ] || [ ! -f "results/bem_convergence_check.json" ]; then
  echo "== BEM mesh-convergence check at 5 kHz (~10 min)"; $PY bem_convergence_check.py
fi
echo "== A2 tweeter directivity";                $PY a2_tweeter_bem.py
echo "== A3 woofer diffraction + tunnel";        $PY a3_woofer_bem.py
echo "== A5 crossover + system response + EQ";   $PY a5_crossover_system.py
echo "== TAS5805M biquad export (96 kHz + 48 kHz)"; $PY biquad_export.py
if [ "${FORCE:-0}" = "1" ] || [ ! -f "results/a4_modes.json" ]; then
  echo "== A4 panel modes (CalculiX, ~35 min)";  $PY a4_panel_modes.py all
else
  echo "== A4 panel modes: figures from cached results"; $PY a4_post.py
fi
echo "done: figures in docs/figures/acoustics, data in sim/acoustics/results"
