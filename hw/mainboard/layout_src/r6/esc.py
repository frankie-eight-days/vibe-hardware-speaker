import sys,json,numpy as np,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
b=pcbnew.LoadBoard('t2.kicad_pcb'); F=pcbnew.FromMM; mm=pcbnew.ToMM
def pad(r,n):
    for p in b.FindFootprintByReference(r).Pads():
        if p.GetNumber()==n: return (mm(p.GetX()),mm(p.GetY()))
jobs=[('/charger/CHG_INT',pad('U701','21'),(169.6,112.15)),('/I2C_SDA',pad('U701','15'),(168.0,115.6))]
S=dict(tracks=[],vias=[])
for net,s,d in jobs:
    for w,c in ((0.12,0.15),(0.1,0.13)):
        Rt=arouter.Router(b,(min(s[0],d[0])-1.5,min(s[1],d[1])-1.5,max(s[0],d[0])+1.5,max(s[1],d[1])+1.5),res=0.025,layers=('F.Cu','In2.Cu'))
        Bl=Rt.blocked('F.Cu',net,w/2+c); i=int(round((s[0]-Rt.x0)/Rt.res)); j=int(round((s[1]-Rt.y0)/Rt.res))
        print(net,'w',w,'start blocked',bool(Bl[j,i]))
        r=Rt.route(net,s,d,width=w,clr=c,layers=['F.Cu','In2.Cu'],via=(0.45,0.2),start_layer='F.Cu',end_layers=['In2.Cu'])
        print(' ->',bool(r))
        if r:
            S['tracks']+=r[0]; S['vias']+=r[1]
            for t in r[0]:
                tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(t['w'])); tr.SetLayer(b.GetLayerID(t['layer'])); tr.SetNet(b.FindNet(net)); tr.SetLocked(True); b.Add(tr)
            for v in r[1]:
                vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v.get('size',0.45))); vi.SetDrill(F(v.get('drill',0.2))); vi.SetNet(b.FindNet(net)); vi.SetLocked(True); b.Add(vi)
            break
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard('t2.kicad_pcb',b); json.dump(S,open('spec_esc.json','w'))
