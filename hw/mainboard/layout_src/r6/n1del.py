"""Track/via deletions + zone replacements for native step 1, resolved to full UUIDs on the original board from design6 rules."""
import pcbnew,collections,design6 as D
def select(b):
    mm=pcbnew.ToMM; U=lambda o:o.m_Uuid.AsString(); out=[]
    near=lambda P,Q: abs(P[0]-Q[0])<0.06 and abs(P[1]-Q[1])<0.06
    seen=collections.defaultdict(list)
    for t in b.GetTracks():
        u=U(t); n=t.GetNetname()
        if any(u.startswith(p) for p in D.DEL_TRACK_PREFIX): out.append(u); continue
        if t.GetClass()=='PCB_VIA':
            k=(round(mm(t.GetX()),2),round(mm(t.GetY()),2)); seen[(round(k[0],1),round(k[1],1))].append(u)
            if any(n==dn and near(k,(x,y)) for dn,x,y in D.DEL_VIAS_AT): out.append(u)
        else:
            e=[(mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y))]
            if any(n==fn and b.GetLayerName(t.GetLayer())==fl and all(any(near(p,q) for q in (a,c)) for p in e) for fn,fl,a,c in D.DEL_TRACK_RULES): out.append(u)
    if D.DEL_DUP_VIAS: out+=[u for v in seen.values() for u in v[1:]]
    # close same-net via pairs (hole gap < 0.25 mm): drop the track-less one
    ends=set()
    for t in b.GetTracks():
        if t.GetClass()!='PCB_VIA': ends|={(t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)}
    V=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and U(t) not in out]
    for i,a in enumerate(V):
        for c in V[i+1:]:
            d=((a.GetX()-c.GetX())**2+(a.GetY()-c.GetY())**2)**0.5
            if d<(a.GetDrillValue()+c.GetDrillValue())/2+pcbnew.FromMM(0.25):
                fr=[v for v in (a,c) if (v.GetX(),v.GetY()) not in ends]
                if fr and U(fr[-1]) not in out: out.append(U(fr[-1]))
    return sorted(set(out))
def zones(b):
    R={}
    for z in b.Zones():
        for p,pts in D.ZONE_REPLACE.items():
            if z.m_Uuid.AsString().startswith(p): R[z.m_Uuid.AsString()]=pts
    assert len(R)==len(D.ZONE_REPLACE),R.keys()
    return R
