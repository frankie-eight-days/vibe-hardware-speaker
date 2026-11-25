import json,collections,sys
d=json.load(open(sys.argv[1]))
print('viol',dict(collections.Counter((v['severity'][0],v['type']) for v in d['violations'])))
print('unconn',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
if len(sys.argv)>2:
    for v in d['violations']:
        if v['type'] in sys.argv[2].split(','): print(v['type'],'|',v['description'][:60],'|',' ; '.join(i['description'][:70]+' @%.2f,%.2f'%(i['pos']['x'],i['pos']['y']) for i in v['items']))
