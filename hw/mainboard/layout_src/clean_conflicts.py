import pcbnew, json, sys
bp,drcj=sys.argv[1:3]; b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM
d=json.load(open(drcj)); kill=set()
for x in d['violations']:
    if x['type'] not in ('clearance','shorting_items','hole_clearance'): continue
    for it in x['items']:
        u=it.get('uuid')
        if u: kill.add(u)
rm=[]
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in kill and not t.IsLocked(): rm.append(t)
dl=[]
for t in rm:
    dl.append(dict(kind=t.GetClass(),net=t.GetNetname(),uuid=t.m_Uuid.AsString())); b.Remove(t)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dl,open('conflict_deleted.json','w')); print('deleted',len(dl),[x['kind'] for x in dl].count('PCB_VIA'),'vias')
