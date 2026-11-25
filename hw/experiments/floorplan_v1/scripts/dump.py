import sys,json,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
def poly(sp):
    out=[]
    for i in range(sp.OutlineCount()):
        o=sp.Outline(i); out.append([[mm(o.CPoint(k).x),mm(o.CPoint(k).y)] for k in range(o.PointCount())])
    return out
G=dict(fps=[],tracks=[],vias=[],zones=[],edge=[])
for f in b.GetFootprints():
    side='B' if f.IsFlipped() else 'F'
    cy=f.GetCourtyard(pcbnew.B_CrtYd if side=='B' else pcbnew.F_CrtYd)
    G['fps'].append(dict(ref=f.GetReference(),side=side,fp=str(f.GetFPID().GetLibItemName()),cy=poly(cy),x=mm(f.GetX()),y=mm(f.GetY()),
        pads=[dict(n=p.GetNumber(),net=p.GetNetname().split('/')[-1],bb=[mm(p.GetBoundingBox().GetX()),mm(p.GetBoundingBox().GetY()),mm(p.GetBoundingBox().GetRight()),mm(p.GetBoundingBox().GetBottom())]) for p in f.Pads()]))
    for g in f.GraphicalItems():
        if g.GetLayer()==pcbnew.Edge_Cuts and g.GetClass()=='PCB_SHAPE':
            G['edge'].append([[mm(p.x),mm(p.y)] for p in (g.GetPolyShape().Outline(0).CPoints() if g.GetShape()==pcbnew.SHAPE_T_POLY else [g.GetStart(),g.GetEnd()])])
for g in b.GetDrawings():
    if g.GetLayer()==pcbnew.Edge_Cuts:
        G['edge'].append([[mm(p.x),mm(p.y)] for p in (g.GetPolyShape().Outline(0).CPoints() if g.GetShape()==pcbnew.SHAPE_T_POLY else [g.GetStart(),g.GetEnd()])])
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': G['vias'].append([mm(t.GetX()),mm(t.GetY()),mm(t.GetWidth(pcbnew.F_Cu)),t.GetNetname().split('/')[-1]])
    else: G['tracks'].append([b.GetLayerName(t.GetLayer()),mm(t.GetStart().x),mm(t.GetStart().y),mm(t.GetEnd().x),mm(t.GetEnd().y),mm(t.GetWidth()),t.GetNetname().split('/')[-1]])
for z in b.Zones():
    for L in z.GetLayerSet().Seq():
        G['zones'].append(dict(name=z.GetZoneName(),net=z.GetNetname().split('/')[-1],layer=b.GetLayerName(L),pts=poly(z.Outline())[0],rule=z.GetIsRuleArea()))
json.dump(G,open(sys.argv[2],'w'))
