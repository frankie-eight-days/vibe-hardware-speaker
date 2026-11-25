"""Build the live replay: native deletions (UUIDs) + Konnect add ops, batched for editor sub-agents.
usage: assemble.py outdir spec1.json [spec2.json ...]   (revb_changes.json is always first)"""
import sys,json,os
SP='/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/revb'
out=sys.argv[1]; os.makedirs(out,exist_ok=True)
C=json.load(open(SP+'/w/revb_changes.json'))
dele=dict(tracks=[d['uuid'] for d in C['del_tracks']],vias=[d['uuid'] for d in C['del_vias']],net_fix=C['net_fix'])
json.dump(dele,open(out+'/native_delete.json','w'),indent=0)
ops=[]
for z in C['zones']:
    ops.append(dict(tool='add_zone',args=dict(net_name=z['net'],layer=z['layer'],points=[dict(x=x,y=y) for x,y in z['pts']],priority=z['priority'],clearance=z['clearance'],min_width=z['min_width'],pad_connection=z['pad_connection'],name=z['name'])))
specs=[C]+[json.load(open(f)) for f in sys.argv[2:]]
for s in specs:
    for v in s.get('vias',[]): ops.append(dict(tool='add_via',args=dict(net_name=v['net'],x=round(v['x'],4),y=round(v['y'],4),pad_size=v.get('size',0.6),drill=v.get('drill',0.3))))
    for t in s.get('tracks',[]): ops.append(dict(tool='route_trace',args=dict(net_name=t['net'],layer=t['layer'],x1=round(t['x1'],4),y1=round(t['y1'],4),x2=round(t['x2'],4),y2=round(t['y2'],4),width=t['w'])))
B=130; n=0
for i in range(0,len(ops),B):
    json.dump(ops[i:i+B],open(f'{out}/batch_{n:02d}.json','w')); n+=1
json.dump(ops,open(out+'/all_ops.json','w'))
print('native deletes',len(dele['tracks']),'tracks',len(dele['vias']),'vias; konnect ops',len(ops),'in',n,'batches',
      {k:sum(1 for o in ops if o['tool']==k) for k in ('add_zone','add_via','route_trace')})
