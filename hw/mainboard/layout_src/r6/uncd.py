import json,sys,re
d=json.load(open(sys.argv[1])); pat=re.compile(sys.argv[2])
def s(i):
    ds=i['description']; ds=re.sub(r'\[[^\]]*\]','',ds); ds=ds.replace(' of ',' ').replace('Through hole ','TH ')
    return '%s@(%.2f,%.2f)'%(ds.strip()[:38],i['pos']['x'],i['pos']['y'])
for u in d['unconnected_items']:
    m=re.search(r'\[([^\]]+)\]',u['items'][0]['description']); n=m.group(1) if m else '?'
    if pat.search(n): print(n.split('/')[-1],'|',' <-> '.join(s(i) for i in u['items']))
