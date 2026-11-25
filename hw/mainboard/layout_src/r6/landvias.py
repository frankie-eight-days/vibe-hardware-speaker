"""GND stitching vias inside the thermal landings (2.5 mm grid, 0.5/0.25), only where every layer is clear for a GND via. usage: landvias.py board spec_out.json"""
import sys,json,numpy as np,pcbnew,design6 as D
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
bp,outf=sys.argv[1:3]; b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM; V=[]
for n,(x0,y0,x1,y1) in D.LANDINGS.items():
    R=arouter.Router(b,(x0,y0,x1,y1),res=0.05,layers=('F.Cu',))
    Bv=np.zeros(R.X.shape,bool)
    for l in R.all: Bv|=R.blocked(l,'GND',0.25+0.2)
    g=[(t.GetX()/1e6,t.GetY()/1e6) for t in b.GetTracks() if t.GetClass()=='PCB_VIA']
    for x in np.arange(x0+1.0,x1-0.9,2.5):
        for y in np.arange(y0+1.0,y1-0.9,2.5):
            # snap to the nearest free cell within 0.5 mm
            best=None
            for dx in np.arange(-0.5,0.51,0.1):
                for dy in np.arange(-0.5,0.51,0.1):
                    cx,cy=x+dx,y+dy; i=int(round((cx-R.x0)/R.res)); j=int(round((cy-R.y0)/R.res))
                    if 0<=j<Bv.shape[0] and 0<=i<Bv.shape[1] and not Bv[j,i] and all((cx-a)**2+(cy-c)**2>0.9**2 for a,c in g):
                        d=dx*dx+dy*dy
                        if best is None or d<best[0]: best=(d,cx,cy)
            if best:
                _,cx,cy=best; vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(cx),F(cy))); vi.SetWidth(F(0.5)); vi.SetDrill(F(0.25)); vi.SetNet(b.FindNet('GND')); vi.SetIsFree(True); vi.SetLocked(True); b.Add(vi)
                g.append((cx,cy)); V.append(dict(net='GND',x=round(cx,3),y=round(cy,3),size=0.5,drill=0.25,land=n))
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=[],vias=V),open(outf,'w')); import collections; print('landing vias',dict(collections.Counter(v['land'] for v in V)))
