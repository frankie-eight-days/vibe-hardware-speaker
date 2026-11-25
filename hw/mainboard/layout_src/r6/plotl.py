"""plotl.py board layer out.png [x0 y0 x1 y1] [--fill]  net-coloured fills+tracks+vias+pads of one copper layer"""
import sys,pcbnew,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
a=[x for x in sys.argv[1:] if not x.startswith('--')]; bp,ly,out=a[:3]; box=list(map(float,a[3:7])) if len(a)>=7 else [58,72,242,123]
b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM; L=b.GetLayerID(ly)
if '--fill' in sys.argv: pcbnew.ZONE_FILLER(b).Fill(b.Zones())
nets={}; cm=plt.get_cmap('tab20')
def col(n):
    if n=='GND': return (0.75,0.75,0.75)
    if n not in nets: nets[n]=cm(len(nets)%20)
    return nets[n]
W=box[2]-box[0];H=box[3]-box[1];k=max(1/6,min(0.6,12/W));fig,ax=plt.subplots(figsize=(W*k,H*k+1.0))
for z in b.Zones():
    if not z.IsOnLayer(L) or z.GetIsRuleArea(): continue
    n=z.GetNetname().split('/')[-1]; ps=z.GetFilledPolysList(L)
    for i in range(ps.OutlineCount()):
        o=ps.Outline(i); P=[(mm(o.CPoint(j).x),mm(o.CPoint(j).y)) for j in range(o.PointCount())]
        ax.add_patch(Polygon(P,closed=True,fc=col(n),ec='none',alpha=0.8))
        for h in range(ps.HoleCount(i)):
            o2=ps.Hole(i,h); ax.add_patch(Polygon([(mm(o2.CPoint(j).x),mm(o2.CPoint(j).y)) for j in range(o2.PointCount())],fc='white',ec='none'))
for t in b.GetTracks():
    n=t.GetNetname().split('/')[-1]
    if t.GetClass()=='PCB_VIA': ax.add_patch(plt.Circle((mm(t.GetX()),mm(t.GetY())),mm(t.GetWidth(L))/2,fc='k' if n=='GND' else col(n),ec='k',lw=0.2)); continue
    if t.GetLayer()!=L: continue
    ax.plot([mm(t.GetStart().x),mm(t.GetEnd().x)],[mm(t.GetStart().y),mm(t.GetEnd().y)],color=col(n),lw=mm(t.GetWidth())*72/6*1.0,solid_capstyle='round')
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.IsOnLayer(L): continue
        bb=p.GetBoundingBox(); ax.add_patch(plt.Rectangle((mm(bb.GetX()),mm(bb.GetY())),mm(bb.GetWidth()),mm(bb.GetHeight()),fc='none',ec='k',lw=0.2))
for i,(n,c) in enumerate(nets.items()): fig.text(0.01+(i%8)*0.123,0.07-(i//8)*0.025,n[:16],color=c,fontsize=6,weight='bold')
ax.set_xlim(box[0],box[2]); ax.set_ylim(box[3],box[1]); ax.set_aspect('equal'); ax.set_title(ly); ax.grid(alpha=0.3); ax.set_xticks(range(int(box[0]),int(box[2]),5 if W>60 else 2))
ax.tick_params(labelsize=6); fig.subplots_adjust(left=0.03,right=0.99,top=0.95,bottom=0.12); import os; fig.savefig(out,dpi=int(os.environ.get("DPI","90")))
