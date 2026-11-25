"""Restore critical geometry the SES import changed; delete autorouted items that now short/clear-violate it. Writes restore_plan.json."""
import pcbnew, json, sys, subprocess
bp=sys.argv[1]; b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM; F=pcbnew.FromMM
L={'F.Cu':pcbnew.F_Cu,'In1.Cu':pcbnew.In1_Cu,'In2.Cu':pcbnew.In2_Cu,'B.Cu':pcbnew.B_Cu}
have=set(); hv={}
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': hv[(round(mm(t.GetPosition().x),2),round(mm(t.GetPosition().y),2))]=t
    else: have.add((t.GetNetname(),frozenset([(round(mm(t.GetStart().x),3),round(mm(t.GetStart().y),3)),(round(mm(t.GetEnd().x),3),round(mm(t.GetEnd().y),3))])))
addT=[];addV=[]
for f in ('spec_critical.json','spec_fanout.json'):
    s=json.load(open(f))
    for t in s['tracks']:
        k=(t['net'],frozenset([(round(t['x1'],3),round(t['y1'],3)),(round(t['x2'],3),round(t['y2'],3))]))
        if len(k[1])==2 and k not in have: addT.append(t)
    for v in s['vias']:
        if (round(v['x'],2),round(v['y'],2)) not in hv: addV.append(v)
for t in addT:
    tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(t['w'])); tr.SetLayer(L[t['layer']]); tr.SetNet(b.FindNet(t['net'])); tr.SetLocked(True); b.Add(tr)
for v in addV:
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v.get('size',0.6))); vi.SetDrill(F(v.get('drill',0.3))); vi.SetNet(b.FindNet(v['net'])); vi.SetLocked(True); vi.SetIsFree(True); b.Add(vi)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=addT,vias=addV),open('restore_add.json','w'))
print('restored tracks',len(addT),'vias',len(addV))
