#!/bin/zsh
# iteration driver: run2.sh <dir>
SP=/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/revb
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
LS=/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src
D=$SP/w/$1; mkdir -p $D; cd $SP
F() { grep -v "assert\|Debug\|memory leak" }
echo "== prep $(date +%T)"
$KPY prep.py /Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/releases/pcb_critical_routed/speaker_main.kicad_pcb $SP/w/b/speaker_main.kicad_pcb 2>&1 | F
(cd w/b; kicad-cli pcb drc --severity-all --format json -o $SP/w/drc_prep.json speaker_main.kicad_pcb >/dev/null 2>&1); python3 drcsum.py w/drc_prep.json | head -2
$KPY dsn.py w/b/speaker_main.kicad_pcb w/drc_prep.json $D/m.dsn --l3power 2>&1 | F | grep keepouts
cp w/b/speaker_main.kicad_pcb $D/s.kicad_pcb; cp w/b/speaker_main.kicad_pro $D/s.kicad_pro
python3 jobs_from_drc.py w/drc_prep.json $D/jobs_all.json
python3 -c "
import json,math;J=json.load(open('$D/jobs_all.json'))
S=[j for j in J if math.dist(j[2][1:3],j[3][1:3])<8]; S.sort(key=lambda j:math.dist(j[2][1:3],j[3][1:3]))
json.dump(S,open('$D/jobs_short.json','w')); print('short jobs',len(S))"
echo "== short $(date +%T)"
$KPY bus.py $D/s.kicad_pcb $D/m_k3raw.npy $D/m_k4raw.npy $D/spec_short.json --jobs=$D/jobs_short.json --tiers=2 2>&1 | F > $D/short.log; grep -c "^ok" $D/short.log; grep "^fails" $D/short.log | cut -c1-200
echo "== bus $(date +%T)"
$KPY bus.py $D/s.kicad_pcb $D/m_k3raw.npy $D/m_k4raw.npy $D/spec_bus.json --tiers=2 2>&1 | F > $D/bus.log; grep -c "^ok" $D/bus.log; grep "^fails" $D/bus.log
(cd $D; kicad-cli pcb drc --severity-all --format json -o $D/drc_s.json s.kicad_pcb >/dev/null 2>&1); python3 drcsum.py $D/drc_s.json clearance,shorting_items | head -6
echo "== FR $(date +%T)"
$KPY dsn.py $D/s.kicad_pcb $D/drc_s.json $D/f.dsn --l3power 2>&1 | F | grep "nets kept" | cut -c1-80
python3 -c "
import re;s=open('$D/f.dsn').read();open('$D/f.dsn','w').write(re.sub(r'    \(wire_keepout [^\n]*\n','',s))"
java -Djava.awt.headless=true -jar ~/tools/freerouting/freerouting-2.4.1.jar -de $D/f.dsn -do $D/f.ses -mp 20 > $D/f.log 2>&1
grep -E "pass #[0-9]+ .*was completed" $D/f.log | tail -1 | cut -c60-200
cp $D/s.kicad_pcb $D/t.kicad_pcb; cp $D/s.kicad_pro $D/t.kicad_pro
(cd $LS; $KPY native_finalize.py $D/t.kicad_pcb $D/s.kicad_pcb $D/f.ses 2>&1 | F)
(cd $D; kicad-cli pcb drc --severity-all --format json -o $D/drc_t.json t.kicad_pcb >/dev/null 2>&1); python3 drcsum.py $D/drc_t.json clearance,shorting_items | head -6
echo "== residual $(date +%T)"
python3 jobs_from_drc.py $D/drc_t.json $D/jobs_res.json
python3 -c "
import json,math;J=json.load(open('$D/jobs_res.json')); J.sort(key=lambda j:math.dist(j[2][1:3],j[3][1:3])); json.dump(J,open('$D/jobs_res.json','w'))"
$KPY bus.py $D/t.kicad_pcb $D/m_k3raw.npy $D/m_k4raw.npy $D/spec_res.json --jobs=$D/jobs_res.json --tiers=2 2>&1 | F > $D/res.log; grep -c "^ok" $D/res.log
$KPY islands.py $D/t.kicad_pcb $D/spec_isl.json 2>&1 | F
$KPY stitchfast.py $D/t.kicad_pcb $D/spec_stf.json 2>&1 | F
(cd $D; kicad-cli pcb drc --severity-all --format json -o $D/drc_final.json t.kicad_pcb >/dev/null 2>&1); python3 drcsum.py $D/drc_final.json clearance,shorting_items,hole_clearance | head -12
python3 unc.py $D/drc_final.json | column -c 200
$KPY refcheck.py $D/t.kicad_pcb $D/ref.json 2>&1 | F
$KPY $LS/copper_balance.py $D/t.kicad_pcb 2>&1 | F
echo "== done $(date +%T)"
