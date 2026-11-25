import json,sys,re,collections,math
d=json.load(open(sys.argv[1])); c=collections.defaultdict(list)
for u in d['unconnected_items']:
    it=u['items']; m=re.search(r'\[([^\]]+)\]',it[0]['description']); n=m.group(1) if m else '?'
    p=[(i['pos']['x'],i['pos']['y']) for i in it]; c[n].append(math.dist(*p[:2]) if len(p)>1 else 0)
for n,l in sorted(c.items(),key=lambda x:-sum(x[1])): print('%-28s %3d  %6.1f'%(n[-28:],len(l),sum(l)))
