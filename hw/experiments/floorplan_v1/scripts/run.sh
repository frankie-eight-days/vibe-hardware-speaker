#!/bin/zsh
# usage: run.sh plan tag   -> builds, DRC, blockdiff, heights, density, FH (with phase-2 pours), thermal (pads/no pads)

source ./env.sh
[ -f base.kicad_pcb ] || { cp $PRJ/hw/releases/pcb_04_revB_6L/02_konnect1/speaker_main.kicad_pcb base.kicad_pcb; cp $PRJ/hw/releases/pcb_04_revB_6L/02_konnect1/speaker_main.kicad_pro base.kicad_pro; }
P=$1; T=$2; KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KPY build.py base.kicad_pcb $T.kicad_pcb $P 2>&1 | grep -v "memory leak\|^$\|assert" | grep -v " box " > $T.build.log
cp base.kicad_pro $T.kicad_pro
$KC pcb drc --format json --severity-all -o $T.drc.json $T.kicad_pcb >/dev/null 2>&1 || true
kp blockdiff.py base.kicad_pcb $T.kicad_pcb > $T.blockdiff.log
kp check_h.py $T.kicad_pcb $P > $T.heights.log
kp dump.py $T.kicad_pcb geo_$T.json; python3 density.py geo_$T.json > $T.density.log
kp mk_fhvar.py $T.kicad_pcb ${T}_fhp.kicad_pcb > /dev/null; kp mk_thermal.py $T.kicad_pcb ${T}_th.kicad_pcb > /dev/null
cd sim; source vp.sh; rm -f work/${T}p.json work/${T}th_*.json
$VP fhrun.py ${T}p ../${T}_fhp.kicad_pcb > fh_${T}p.log 2>&1
$VP -c "from pl_common import extract; extract('../${T}_th.kicad_pcb','${T}th_nopad')" > /dev/null 2>&1; cp work/${T}th_nopad.json work/${T}th_pad.json
for t in ${T}th_nopad ${T}th_pad; do $VP thermal_fp.py $t ../${T}_th.kicad_pcb.gappads.json; done > th_${T}.log 2>&1
echo DONE > ../$T.done
