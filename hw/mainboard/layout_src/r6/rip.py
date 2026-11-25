"""rip.py base board net1,net2,... : delete routed items (not present in base) of the given nets (suffix match)"""
import sys,collections,pcbnew
base,bp,nets=sys.argv[1],sys.argv[2],sys.argv[3].split(','); mm=pcbnew.ToMM
A=pcbnew.LoadBoard(base); B=pcbnew.LoadBoard(bp)
key=lambda t:(t.GetClass(),t.GetNetname(),round(mm(t.GetStart().x),4),round(mm(t.GetStart().y),4),round(mm(t.GetEnd().x),4),round(mm(t.GetEnd().y),4),t.GetLayer())
old=collections.Counter(key(t) for t in A.GetTracks()); n=0
for t in list(B.GetTracks()):
    k=key(t)
    if old[k]>0: old[k]-=1; continue
    if any(t.GetNetname().endswith(x) for x in nets): B.Remove(t); n+=1
pcbnew.SaveBoard(bp,B); print('ripped',n)
