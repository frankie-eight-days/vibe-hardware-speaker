"""Build n1 ops from the ORIGINAL (4-layer) board + spec JSONs + deletion rules. usage: plan_n1.py board out.json"""
import sys,json,pcbnew
LS='/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src/'
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM; U=lambda o:o.m_Uuid.AsString()
want={}
for f in ('spec_critical.json','spec_fanout.json','spec_stitch.json'):
    for v in json.load(open(LS+f))['vias']: want[(round(v['x'],2),round(v['y'],2))]=v['net']
O=dict(move_zones=[U(z) for z in b.Zones() if z.GetLayer()==pcbnew.In2_Cu],del_=[],netfix={})
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA':
        k=(round(mm(t.GetX()),2),round(mm(t.GetY()),2))
        if k in want: O['netfix'][U(t)]=want[k]   # every via pinned to its spec net (load-time zone re-netting is nondeterministic)
import n1del; O['del']=n1del.select(b); O['zone_replace']=n1del.zones(b); O.pop('del_')
json.dump(O,open(sys.argv[2],'w'),indent=0); print({k:len(v) for k,v in O.items()}); print('del',len(O['del']))
