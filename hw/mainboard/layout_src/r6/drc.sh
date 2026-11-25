# drc.sh board.kicad_pcb out.json  -> copies board+pro into dd/ as speaker_main, DRC (refill, parity, all severities), summary
cp $1 $SP/dd/speaker_main.kicad_pcb; cp ${1%.kicad_pcb}.kicad_pro $SP/dd/speaker_main.kicad_pro
kicad-cli pcb drc --refill-zones --schematic-parity --severity-all --format json -o $2 $SP/dd/speaker_main.kicad_pcb >/dev/null 2>&1; $KPY $LS/revb/drcsum.py $2
