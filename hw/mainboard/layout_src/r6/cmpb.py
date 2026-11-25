import sys,pcbnew
A=pcbnew.LoadBoard(sys.argv[1]); B=pcbnew.LoadBoard(sys.argv[2]); mm=pcbnew.ToMM
def zs(b): return sorted((b.GetLayerName(z.GetLayer()),z.GetNetname(),z.GetZoneName(),z.GetAssignedPriority(),round(mm(z.GetLocalClearance() or 0),3),round(mm(z.GetMinThickness()),3),int(z.GetPadConnection()),int(z.GetIslandRemovalMode()),z.Outline().COutline(0).PointCount()) for z in b.Zones())
def fs(b): return sorted((f.GetReference(),round(mm(f.GetX()),3),round(mm(f.GetY()),3),round(f.GetOrientationDegrees(),2),f.GetSide()) for f in b.GetFootprints())
def ts(b): return sorted((t.GetClass(),t.GetNetname(),round(mm(t.GetStart().x),3),round(mm(t.GetStart().y),3),round(mm(t.GetEnd().x),3),round(mm(t.GetEnd().y),3),b.GetLayerName(t.GetLayer()),round(mm(t.GetWidth()),3),t.IsLocked()) for t in b.GetTracks())
for n,f in (('zones',zs),('footprints',fs),('tracks',ts)):
    a,c=set(f(A)),set(f(B)); print(n,'only A',len(a-c),'only B',len(c-a)); [print('  A',x) for x in sorted(a-c)[:4]]; [print('  B',x) for x in sorted(c-a)[:4]]
print('layers',A.GetCopperLayerCount(),B.GetCopperLayerCount())
