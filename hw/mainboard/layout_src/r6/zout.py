import sys,re,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM; pat=re.compile(sys.argv[2])
for z in b.Zones():
    if pat.search(z.GetNetname()+'|'+z.GetZoneName()):
        o=z.Outline().COutline(0); print(b.GetLayerName(z.GetLayer()),z.GetNetname().split('/')[-1],z.GetZoneName(),'pri',z.GetAssignedPriority(),'clr',mm(z.GetLocalClearance() or 0),z.m_Uuid.AsString()[:8],[(round(mm(o.CPoint(i).x),2),round(mm(o.CPoint(i).y),2)) for i in range(o.PointCount())])
