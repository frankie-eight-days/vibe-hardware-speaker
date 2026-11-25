"""Diff final scratch board vs the Konnect-state board (s2 == live): every new track/via -> revb.ses; all via nets -> vianets.json;
per-source split (A*/Freerouting) from the spec JSONs. usage: assemble6.py base.kicad_pcb final.kicad_pcb out_dir"""
import sys,json,os,collections,pcbnew,sesw
base,fin,od=sys.argv[1:4]; os.makedirs(od,exist_ok=True); mm=pcbnew.ToMM
A=pcbnew.LoadBoard(base); B=pcbnew.LoadBoard(fin)
key=lambda t:(t.GetClass(),t.GetNetname(),round(mm(t.GetStart().x),4),round(mm(t.GetStart().y),4),round(mm(t.GetEnd().x),4),round(mm(t.GetEnd().y),4),t.GetLayer() if t.GetClass()!='PCB_VIA' else -1,round(mm(t.GetWidth()),4) if t.GetClass()!='PCB_VIA' else 0)
old=collections.Counter(key(t) for t in A.GetTracks())
T=[];V=[]
for t in B.GetTracks():
    k=key(t)
    if old[k]>0: old[k]-=1; continue
    if t.GetClass()=='PCB_VIA': V.append(dict(net=t.GetNetname(),x=round(mm(t.GetX()),4),y=round(mm(t.GetY()),4),size=round(mm(t.GetWidth(pcbnew.F_Cu)),3),drill=round(mm(t.GetDrillValue()),3)))
    else: T.append(dict(net=t.GetNetname(),layer=B.GetLayerName(t.GetLayer()),x1=k[2],y1=k[3],x2=k[4],y2=k[5],w=k[7]))
gone=sum(v for v in old.values() if v>0)
L=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
sesw.write(od+'/revb.ses',T,V,L)
json.dump([[round(mm(t.GetX()),4),round(mm(t.GetY()),4),t.GetNetname()] for t in B.GetTracks() if t.GetClass()=='PCB_VIA'],open(od+'/vianets.json','w'))
json.dump(dict(tracks=T,vias=V),open(od+'/new_items.json','w'))
print(json.dumps(dict(new_tracks=len(T),new_vias=len(V),items_in_base_missing_from_final=gone)))
