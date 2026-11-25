java -Djava.awt.headless=true -jar ~/tools/freerouting/freerouting-2.4.1.jar -de f.dsn -do f.ses -mp 30 -mt 4 > f.log 2>&1
grep -E "pass #[0-9]+ .*was completed" f.log | tail -1 | cut -c60-200
cp s6.kicad_pcb t.kicad_pcb; cp s6.kicad_pro t.kicad_pro
kp -c "
import pcbnew; b=pcbnew.LoadBoard('t.kicad_pcb'); n0=len(b.GetTracks()); ok=pcbnew.ImportSpecctraSES(b,'f.ses')
for t in b.GetTracks(): t.SetLocked(True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard('t.kicad_pcb',b); print('FR import',ok,n0,'->',len(b.GetTracks()))"
source drc.sh t.kicad_pcb tdrc.json
python3 $LS/revb/jobs_from_drc.py tdrc.json jobs_res.json
python3 -c "
import json,math;J=json.load(open('jobs_res.json')); J.sort(key=lambda j:math.dist(j[2][1:3],j[3][1:3])); json.dump(J,open('jobs_res.json','w')); print('residual jobs',len(J))"
$KPY bus6.py t.kicad_pcb k3.npy k4.npy spec_res.json --jobs=jobs_res.json --tiers=2 2>&1 | grep -v -e assert -e Debug -e "memory leak" > res.log; grep -c "^ok" res.log; grep "^fails" res.log | cut -c1-300
kp islands6.py t.kicad_pcb spec_isl.json
kp stitchfast6.py t.kicad_pcb spec_stf.json
source drc.sh t.kicad_pcb tdrc2.json
