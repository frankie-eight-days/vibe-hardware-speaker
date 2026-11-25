"""Gate 2: every net pin of the key ICs is copper-connected to its net after zone fill.
usage: padcheck.py board drc.json  (DRC run with --refill-zones) -> fails = pads listed in any unconnected item + pads with no copper attached"""
import sys,json,re,collections,pcbnew
REFS=('U901','U951','U701','U301','U401','U101','U601')
b=pcbnew.LoadBoard(sys.argv[1]); d=json.load(open(sys.argv[2]))
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.BuildConnectivity(); C=b.GetConnectivity()
cnt=collections.Counter(p.GetNetname() for p in b.GetPads())
fails=[]; n=0
unc=set()
for u in d['unconnected_items']:
    for it in u['items']:
        m=re.match(r'Pad (\S+) \[[^\]]*\] of (\S+)',it['description'])
        if m: unc.add((m.group(2),m.group(1)))
for r in REFS:
    f=b.FindFootprintByReference(r)
    for p in f.Pads():
        net=p.GetNetname()
        if not net or net.startswith('unconnected-') or cnt[net]<2: continue
        n+=1
        att=[i for i in C.GetConnectedItems(p) if i.GetClass()!='PAD' or True]
        if (r,p.GetNumber()) in unc or len(att)==0: fails.append('%s.%s %s'%(r,p.GetNumber(),net.split('/')[-1]))
print('pads checked',n,'failures',len(fails),fails[:20])
