"""Tie isolated GND fill islands (any copper layer) to the GND system with a via (L2 is solid GND). usage: islands.py board spec_out.json"""
import sys,json,numpy as np,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
from matplotlib.path import Path
bp,outf=sys.argv[1:3]; b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM; F=pcbnew.FromMM
anchors=[(t.GetX(),t.GetY()) for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
anchors+=[(p.GetX(),p.GetY()) for p in b.GetPads() if p.GetNetname()=='GND' and p.GetDrillSizeX()>0]   # SMD pads do not tie a fill piece to the planes
V=[];skipped=0
ANT=lambda x,y: x<63.3 or (x<75.3 and (y<86 or y>115))
for z in b.Zones():
    if z.GetNetname()!='GND' or z.GetIsRuleArea() or 'AGND' in z.GetZoneName(): continue   # boost AGND island: single-point tie, never a via
    for l in z.GetLayerSet().Seq():
        if l==pcbnew.In1_Cu or not z.HasFilledPolysForLayer(l): continue
        fp=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(l)); fp.Unfracture()
        for i in range(fp.OutlineCount()):
            one=pcbnew.SHAPE_POLY_SET(); one.AddOutline(fp.Outline(i))
            for h in range(fp.HoleCount(i)): one.AddHole(fp.Hole(i,h))
            if one.Area()<0.6e12: skipped+=1; continue   # < 0.6 mm^2: sliver, leave
            if any(one.Contains(pcbnew.VECTOR2I(int(x),int(y))) for x,y in anchors): continue
            bb=fp.Outline(i).BBox(); x0,y0,x1,y1=mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())
            R=arouter.Router(b,(x0-1,y0-1,x1+1,y1+1),res=0.05,layers=('F.Cu',))
            Bv=np.zeros(R.X.shape,bool)
            for ll in R.all: Bv|=R.blocked(ll,'GND',0.25+0.2)
            ok=False
            for j,ii in zip(*np.where(~Bv)):
                x,y=float(R.X[j,ii]),float(R.Y[j,ii])
                if ANT(x,y) or not one.Contains(pcbnew.VECTOR2I(F(x),F(y))): continue
                # keep the via 0.3 mm inside the island
                if not all(one.Contains(pcbnew.VECTOR2I(F(x+dx),F(y+dy))) for dx,dy in ((0.3,0),(-0.3,0),(0,0.3),(0,-0.3))): continue
                vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(x),F(y))); vi.SetWidth(F(0.5)); vi.SetDrill(F(0.25)); vi.SetNet(b.FindNet('GND')); vi.SetIsFree(True); vi.SetLocked(True); b.Add(vi)
                anchors.append((F(x),F(y))); V.append(dict(net='GND',x=round(x,3),y=round(y,3),size=0.5,drill=0.25)); ok=True; break
            if not ok: print('no via spot for island',b.GetLayerName(l),round(x0,1),round(y0,1),round(x1,1),round(y1,1))
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=[],vias=V),open(outf,'w')); print('island vias',len(V),'slivers skipped',skipped)
