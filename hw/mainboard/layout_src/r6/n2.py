"""NATIVE STEP 2 (approved: SES import, via-net repair + free flag, locked flag; CLOSED board after a Konnect save).
usage: n2.py board.kicad_pcb revb.ses vianets.json
 1 pcbnew.ImportSpecctraSES (every existing item is locked beforehand by n1/Konnect save -> kept; SES adds only new wires/vias)
 2 every via pinned to its spec net by position (vianets.json: [[x,y,net],...] from spec_critical/fanout/stitch + rev B specs), free flag on track-less vias
 3 lock every track/via; zones refilled; save"""
import sys,json,pcbnew
bp,ses,vf=sys.argv[1:4]; b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM
pre={t.m_Uuid.AsString() for t in b.GetTracks()}
unl=[t for t in b.GetTracks() if not t.IsLocked()]
assert not unl, 'unlocked items before import: %d'%len(unl)
ok=pcbnew.ImportSpecctraSES(b,ses)
want={(round(x,2),round(y,2)):n for x,y,n in json.load(open(vf))}
ends=set()
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': ends|={(t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)}
nf=fr=miss=0
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': continue
    k=(round(mm(t.GetX()),2),round(mm(t.GetY()),2))
    if k not in want: miss+=1; continue
    if t.GetNetname()!=want[k]: t.SetNet(b.FindNet(want[k])); nf+=1
    if (t.GetX(),t.GetY()) not in ends: t.SetIsFree(True); fr+=1
for t in b.GetTracks(): t.SetLocked(True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
new=[t for t in b.GetTracks() if t.m_Uuid.AsString() not in pre]
print(json.dumps(dict(ses_import=ok,new_items=len(new),netfix=nf,free=fr,vias_not_in_spec=miss,total=len(b.GetTracks()))))
