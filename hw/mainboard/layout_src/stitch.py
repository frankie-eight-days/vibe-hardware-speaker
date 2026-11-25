"""GND stitching vias: edge fence (3 mm pitch, 1.2 mm in from the outline), interior grid (5 mm), and a 2.5 mm ring around the three switchers.
Each candidate is kept only if a 0.6/0.3 via clears every non-GND item on all four layers (pours of priority <=1 are ignored; they re-fill)."""
import sys, json, pcbnew, numpy as np
sys.path.insert(0,'.')
import arouter
from matplotlib.path import Path
bp=sys.argv[1]; b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM
G=Path([(75.3,75.5),(142.6,75.5),(157.4,75.5),(239.5,75.5),(239.5,120.5),(75.3,120.5),(75.3,115.0),(63.3,115.0),(63.3,86.0),(75.3,86.0)])
cand=[]
for x in np.arange(76.5,239.0,3.0): cand+= [(x,76.7),(x,119.3)]
for y in np.arange(76.7,119.4,3.0): cand+= [(238.3,y)]
for y in np.arange(87.5,114.0,3.0): cand+= [(64.5,y)]
for x in np.arange(78,238,5.0):
    for y in np.arange(78,120,5.0): cand.append((x,y))
for cx,cy,r in ((130,106,9.0),(167,106,10.0),(104,116.2,5.5)):
    for a in np.linspace(0,2*np.pi,int(2*np.pi*r/2.5),endpoint=False): cand.append((cx+r*np.cos(a),cy+r*np.sin(a)))
V=[]; placed=[]
R=arouter.Router(b,(60,73,240,122),res=0.1,layers=('F.Cu',))
Bv=None
for l in R.all:
    bl=R.blocked(l,'GND',0.3+0.2); Bv=bl if Bv is None else (Bv|bl)
for x,y in cand:
    if not G.contains_point((x,y)): continue
    i=int(round((x-R.x0)/R.res)); j=int(round((y-R.y0)/R.res))
    if Bv[j-2:j+3,i-2:i+3].any(): continue
    if any((x-px)**2+(y-py)**2<1.5**2 for px,py in placed): continue
    if any((x-fx)**2+(y-fy)**2<2.2**2 for fx,fy in ((101.5,77.5),(227,119),(144.5,119.5))): continue
    placed.append((x,y)); V.append(dict(net='GND',x=round(float(x),3),y=round(float(y),3),size=0.6,drill=0.3))
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(float(x)),F(float(y)))); vi.SetWidth(F(0.6)); vi.SetDrill(F(0.3)); vi.SetNet(b.FindNet('GND')); b.Add(vi)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=[],vias=V,zones=[]),open('spec_stitch.json','w')); print('stitch vias',len(V),'of',len(cand))
