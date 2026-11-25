"""Fix stage on a scratch board: add design6 FIX tracks/vias + A* FIX_JOBS (all locked), write spec_fix.json (goes into the SES). usage: fixstage.py board"""
import sys,json,pcbnew,design6 as D
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
bp=sys.argv[1]; b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM
def addT(t):
    tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(t['w'])); tr.SetLayer(b.GetLayerID(t['layer'])); tr.SetNet(b.FindNet(t['net'])); tr.SetLocked(True); b.Add(tr)
def addV(v):
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v['size'])); vi.SetDrill(F(v['drill'])); vi.SetNet(b.FindNet(v['net'])); vi.SetLocked(True); b.Add(vi)
S=dict(tracks=list(D.FIX_TRACKS),vias=list(D.FIX_VIAS))
for t in S['tracks']: addT(t)
for v in S['vias']: addV(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
for jb in D.FIX_JOBS:
    xs=[jb['src'][0],jb['dst'][0]]; ys=[jb['src'][1],jb['dst'][1]]
    Rt=arouter.Router(b,(min(xs)-3,min(ys)-3,max(xs)+3,max(ys)+3),res=0.05,layers=tuple(jb['layers']))
    r=Rt.route(jb['net'],jb['src'],jb['dst'],width=jb['w'],clr=jb['clr'],layers=jb['layers'],start_layer=jb['layers'][0])
    if not r: print('JOB FAIL',jb['name']); continue
    for t in r[0]: addT(t); S['tracks'].append(t)
    for v in r[1]: addV(v); S['vias'].append(v)
    print('job',jb['name'],len(r[0]),'segs',len(r[1]),'vias')
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(S,open('spec_fix.json','w'),indent=0); print('fix tracks',len(S['tracks']),'vias',len(S['vias']))
