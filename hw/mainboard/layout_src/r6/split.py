"""Track/via stats per layer for a stage = items in board B not in board A. usage: split.py A B label"""
import sys,collections,pcbnew,json
A=pcbnew.LoadBoard(sys.argv[1]); B=pcbnew.LoadBoard(sys.argv[2]); mm=pcbnew.ToMM
key=lambda t:(t.GetClass(),t.GetNetname(),round(mm(t.GetStart().x),3),round(mm(t.GetStart().y),3),round(mm(t.GetEnd().x),3),round(mm(t.GetEnd().y),3),t.GetLayer())
old=collections.Counter(key(t) for t in A.GetTracks()); L=collections.Counter(); N=collections.Counter(); V=0; nets=set()
for t in B.GetTracks():
    k=key(t)
    if old[k]>0: old[k]-=1; continue
    nets.add(t.GetNetname())
    if t.GetClass()=='PCB_VIA': V+=1
    else: ly=B.GetLayerName(t.GetLayer()); L[ly]+=mm(t.GetLength()); N[ly]+=1
print(json.dumps(dict(stage=sys.argv[3],nets=len(nets),vias=V,segs=dict(N),len_mm={k:round(v,1) for k,v in L.items()},removed=sum(v for v in old.values() if v>0))))
