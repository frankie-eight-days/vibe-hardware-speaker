"""Scratch-board prep for rev B (pcbnew API on a COPY). Writes w/revb_changes.json = the exact edits to replay on the live board.
usage: prep.py in.kicad_pcb out.kicad_pcb"""
import sys,json,pcbnew
from matplotlib.path import Path
sys.path.insert(0,'/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/revb')
import design as D
LS='/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src/'
src,dst=sys.argv[1:3]; b=pcbnew.LoadBoard(src); mm=pcbnew.ToMM; F=pcbnew.FromMM
L={'F.Cu':pcbnew.F_Cu,'In1.Cu':pcbnew.In1_Cu,'In2.Cu':pcbnew.In2_Cu,'B.Cu':pcbnew.B_Cu}
want={}
for f in ('spec_critical.json','spec_fanout.json','spec_stitch.json'):
    for v in json.load(open(LS+f))['vias']: want[(round(v['x'],2),round(v['y'],2))]=(v['net'],f)
stitch={(round(v['x'],2),round(v['y'],2)) for v in json.load(open(LS+'spec_stitch.json'))['vias']}
inP=lambda poly,x,y: Path(poly).contains_point((x,y))
old3v3=Path(D.L3_3V3_OLD)
C=dict(net_fix=[],del_tracks=[],del_vias=[],zones=D.ZONES,vias=D.VIAS_ADD)
# 1) via nets back to spec (KiCad re-nets track-less vias to the zone they sit in)
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': continue
    k=(round(mm(t.GetX()),2),round(mm(t.GetY()),2))
    if k in want and t.GetNetname()!=want[k][0]:
        C['net_fix'].append(dict(uuid=t.m_Uuid.AsString(),x=k[0],y=k[1],net=want[k][0])); t.SetNet(b.FindNet(want[k][0]))
# 2) deletions
kill=set()
for t in b.GetTracks():
    n=t.GetNetname(); u=t.m_Uuid.AsString()
    if t.GetClass()=='PCB_VIA':
        k=(round(mm(t.GetX()),2),round(mm(t.GetY()),2)); x,y=k
        # interior 5 mm grid stitch vias inside the corridor lanes (edge fence at Y76.7 stays)
        if k in stitch and y>77.5 and (inP(D.REAR,x,y) or inP(D.DIP,x,y)): kill.add(u); C['del_vias'].append(dict(uuid=u,x=x,y=y,net=n,why='stitch in L3 corridor'))
        # +3V3 plane fan-out vias into the dropped L3 +3V3 pour
        elif any(abs(x-a)<0.05 and abs(y-c)<0.05 for a,c in D.DEL_VIAS_AT): kill.add(u); C['del_vias'].append(dict(uuid=u,x=x,y=y,net=n,why='bulk-cap PVDD via inside corridor dip'))
        elif n=='+3V3' and want.get(k,('',''))[0]=='+3V3' and old3v3.contains_point(k): kill.add(u); C['del_vias'].append(dict(uuid=u,x=x,y=y,net=n,why='3V3 L3 fan-out'))
    else:
        k2={(round(mm(t.GetStart().x),2),round(mm(t.GetStart().y),2)),(round(mm(t.GetEnd().x),2),round(mm(t.GetEnd().y),2))}
        near=lambda P,Q: abs(P[0]-Q[0])<0.06 and abs(P[1]-Q[1])<0.06
        if any(n==fn and t.GetLayer()==L[fl] and all(any(near(e,q) for q in (a,c)) for e in k2) for fn,fl,a,c in D.FIX_DEL_TRACKS): kill.add(u); C['del_tracks'].append(dict(uuid=u,net=n,why='R904 via fix'))
        if n=='/mcu/LCD_SCLK' and t.GetLayer()==pcbnew.B_Cu: kill.add(u); C['del_tracks'].append(dict(uuid=u,net=n,why='rev A L4 SCLK, rerouted in L3 corridor'))
# stubs of the deleted 3V3 fan-out vias
dv={(d['x'],d['y']) for d in C['del_vias'] if d['why']=='3V3 L3 fan-out'}
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA' or t.GetNetname()!='+3V3': continue
    e={(round(mm(t.GetStart().x),2),round(mm(t.GetStart().y),2)),(round(mm(t.GetEnd().x),2),round(mm(t.GetEnd().y),2))}
    if any(abs(e0[0]-d0[0])<0.06 and abs(e0[1]-d0[1])<0.06 for e0 in e for d0 in dv): kill.add(t.m_Uuid.AsString()); C['del_tracks'].append(dict(uuid=t.m_Uuid.AsString(),net='+3V3',why='3V3 fan-out stub'))
GRAVE=[t for t in b.GetTracks() if t.m_Uuid.AsString() in kill]
for t in GRAVE: b.Remove(t)
# 3) additions
for z in D.ZONES:
    zo=pcbnew.ZONE(b); zo.SetLayer(L[z['layer']]); zo.SetNet(b.FindNet(z['net'])); ol=pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
    for x,y in z['pts']: ol.Append(F(x),F(y))
    ol.thisown=0; zo.SetOutline(ol)
    zo.SetAssignedPriority(z['priority']); zo.SetLocalClearance(F(z['clearance'])); zo.SetMinThickness(F(z['min_width']))
    zo.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if z['pad_connection']=='solid' else pcbnew.ZONE_CONNECTION_THERMAL); zo.SetZoneName(z['name']); b.Add(zo)
for v in D.VIAS_ADD:
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v['size'])); vi.SetDrill(F(v['drill'])); vi.SetNet(b.FindNet(v['net'])); b.Add(vi)
def addT(t):
    tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(t['w'])); tr.SetLayer(L[t['layer']]); tr.SetNet(b.FindNet(t['net'])); b.Add(tr)
def addV(v):
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v['size'])); vi.SetDrill(F(v['drill'])); vi.SetNet(b.FindNet(v['net'])); b.Add(vi)
for t in D.FIX_ADD_TRACKS: addT(t)
for v in D.FIX_ADD_VIAS: addV(v)
C['tracks']=list(D.FIX_ADD_TRACKS); C['vias']=list(D.VIAS_ADD)+list(D.FIX_ADD_VIAS)
sys.path.insert(0,LS); import arouter
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
for jb in D.JOBS:
    xs=[jb['src'][0],jb['dst'][0]]; ys=[jb['src'][1],jb['dst'][1]]
    Rt=arouter.Router(b,(min(xs)-3,min(ys)-3,max(xs)+3,max(ys)+3),res=0.05,layers=tuple(jb['layers']))
    r=Rt.route(jb['net'],jb['src'],jb['dst'],width=jb['w'],clr=jb['clr'],layers=jb['layers'],start_layer=jb['layers'][0])
    if not r: print('JOB FAIL',jb['name']); continue
    for t in r[0]: addT(t); C['tracks'].append(t)
    for v in r[1]: addV(v); C['vias'].append(v)
    print('job',jb['name'],len(r[0]),'segs',len(r[1]),'vias')
# 4) free + lock every existing via/track (critical geometry frozen before any autorouting)
ends=set()
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': ends|={(t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)}
nfree=0
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA' and (t.GetX(),t.GetY()) not in ends: t.SetIsFree(True); nfree+=1
    t.SetLocked(True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(dst,b)
json.dump(C,open('/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/revb/w/revb_changes.json','w'),indent=0)
print('netfix',len(C['net_fix']),'del vias',len(C['del_vias']),'del tracks',len(C['del_tracks']),'zones',len(D.ZONES),'vias+',len(D.VIAS_ADD),'free',nfree)
