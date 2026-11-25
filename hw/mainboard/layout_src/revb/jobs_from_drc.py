# DRC unconnected pairs -> bus.py job list (skip GND and zone items)
import json,re,sys
d=json.load(open(sys.argv[1])); J=[]
def ep(it):
    ds=it['description']; x,y=round(it['pos']['x'],4),round(it['pos']['y'],4)
    if 'Zone' in ds: return None
    if ds.startswith('Via'): return ['xy',x,y,['F.Cu','In2.Cu','B.Cu']]
    if 'on B.Cu' in ds and 'F.Cu' not in ds: return ['xy',x,y,['B.Cu']]
    if 'on In2.Cu' in ds: return ['xy',x,y,['In2.Cu']]
    if re.match(r'(PTH )?[Pp]ad',ds) and 'PTH' in ds: return ['xy',x,y,['F.Cu','B.Cu']]
    return ['xy',x,y,['F.Cu']]
for k,u in enumerate(d['unconnected_items']):
    it=u['items']; m=re.search(r'\[([^\]]+)\]',it[0]['description'])
    if not m or len(it)<2 or m.group(1)=='GND': continue
    a,c=ep(it[0]),ep(it[1])
    if a and c: J.append(['u%d'%k,m.group(1),a,c])
json.dump(J,open(sys.argv[2],'w')); print('jobs',len(J))
