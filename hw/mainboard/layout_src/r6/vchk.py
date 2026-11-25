"""Via net check vs spec (spec_critical/fanout/stitch[/extra specs]). usage: vchk.py board [extra_spec.json ...]"""
import sys,json,collections,pcbnew
LS='/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src/'
want={}; src=collections.Counter(); dup=0
for f in [LS+'spec_critical.json',LS+'spec_fanout.json',LS+'spec_stitch.json']+sys.argv[2:]:
    for v in json.load(open(f)).get('vias',[]):
        k=(round(v['x'],2),round(v['y'],2))
        if k in want and want[k]!=v['net']: dup+=1
        want[k]=v['net']; src[f.split('/')[-1]]+=1
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
bad=[];miss=0;n=0;seen=set()
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': continue
    n+=1; k=(round(mm(t.GetX()),2),round(mm(t.GetY()),2)); seen.add(k)
    if k not in want: miss+=1; continue
    if t.GetNetname()!=want[k]: bad.append((k,t.GetNetname().split('/')[-1],want[k].split('/')[-1]))
print('spec vias',dict(src),'conflicting dup',dup,'| board vias',n,'not in spec',miss,'wrong net',len(bad),'spec missing on board',len(set(want)-seen))
c=collections.Counter((a,w) for _,a,w in bad); print(c.most_common(12))
