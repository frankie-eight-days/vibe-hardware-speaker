import sys,collections,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
print('layers',b.GetCopperLayerCount())
z=collections.Counter(); 
for zo in b.Zones(): z[(b.GetLayerName(zo.GetLayer()) if not zo.IsOnCopperLayer() or len(list(zo.GetLayerSet().Seq()))==1 else 'multi',zo.GetNetname().split('/')[-1],zo.GetIsRuleArea())]+=1
for k,v in sorted(z.items()): print('Z',k,v)
t=collections.Counter(); L=collections.Counter(); vi=collections.Counter()
for tr in b.GetTracks():
    if tr.GetClass()=='PCB_VIA': vi[tr.GetNetname().split('/')[-1]]+=1; continue
    ly=b.GetLayerName(tr.GetLayer()); t[ly]+=1; L[ly]+=mm(tr.GetLength())
print('tracks',dict(t),{k:round(v) for k,v in L.items()},'vias',sum(vi.values()))
if len(sys.argv)>2:
    n=collections.Counter(tr.GetNetname().split('/')[-1] for tr in b.GetTracks() if tr.GetClass()!='PCB_VIA' and b.GetLayerName(tr.GetLayer())==sys.argv[2])
    print(sys.argv[2],dict(n))
