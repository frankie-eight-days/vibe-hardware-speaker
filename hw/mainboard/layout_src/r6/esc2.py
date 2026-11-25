"""Escape a fine-pitch pin to the nearest feasible via (In2) by A*: try via points on a 0.15 mm grid within R mm, nearest first.
usage: esc2.py board out.json NET REF PIN [R]"""
import sys,json,numpy as np,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
bp,outf,net,ref,num=sys.argv[1:6]; RR=float(sys.argv[6]) if len(sys.argv)>6 else 2.5
b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM; mm=pcbnew.ToMM
p=[q for q in b.FindFootprintByReference(ref).Pads() if q.GetNumber()==num][0]; s=(mm(p.GetX()),mm(p.GetY()))
R=arouter.Router(b,(s[0]-RR-1,s[1]-RR-1,s[0]+RR+1,s[1]+RR+1),res=0.025,layers=('F.Cu','In2.Cu'))
Bv=np.zeros(R.X.shape,bool)
for l in R.all: Bv|=R.blocked(l,net,0.225+0.15)
c=[(float(x),float(y)) for x in np.arange(s[0]-RR,s[0]+RR,0.15) for y in np.arange(s[1]-RR,s[1]+RR,0.15)
   if 0.7<np.hypot(x-s[0],y-s[1])<=RR and not Bv[int(round((y-R.y0)/R.res)),int(round((x-R.x0)/R.res))] and not (162<x<172 and 100<y<111)]
c.sort(key=lambda q:np.hypot(q[0]-s[0],q[1]-s[1]))
for d in c[:25]:
    r=R.route(net,s,d,width=0.12,clr=0.15,layers=['F.Cu'],via=(0.45,0.2),start_layer='F.Cu',end_layers=['F.Cu'],maxit=200000)
    if r:
        T=r[0]; V=[dict(net=net,x=round(d[0],3),y=round(d[1],3),size=0.45,drill=0.2)]
        for t in T:
            t['net']=net; tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(t['w'])); tr.SetLayer(b.GetLayerID(t['layer'])); tr.SetNet(b.FindNet(net)); tr.SetLocked(True); b.Add(tr)
        vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(d[0]),F(d[1]))); vi.SetWidth(F(0.45)); vi.SetDrill(F(0.2)); vi.SetNet(b.FindNet(net)); vi.SetLocked(True); b.Add(vi)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
        old=json.load(open(outf)) if __import__('os').path.exists(outf) else dict(tracks=[],vias=[])
        old['tracks']+=T; old['vias']+=V; json.dump(old,open(outf,'w')); print('escaped',net,ref,num,'via',d); break
else: print('NO escape',net,ref,num,len(c),'candidates')
