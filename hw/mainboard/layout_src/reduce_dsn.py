# Keep in the DSN network only the pins KiCad still reports unconnected (zones are invisible to Freerouting).
import json,re,sys
d=json.load(open(sys.argv[1])); dsn=open(sys.argv[2]).read()
need={}
for u in d['unconnected_items']:
    for it in u['items']:
        m=re.match(r'(?:PTH )?[Pp]ad (\S+) \[([^\]]+)\] of (\S+)',it['description'])
        if m: need.setdefault(m.group(2),set()).add(f"{m.group(3)}-{m.group(1)}")
        else: need.setdefault('__nonpad__',set()).add(it['description'][:60])
print('nonpad items:',need.pop('__nonpad__',set()))
out=[];i=0
start=dsn.index('  (network')
net_re=re.compile(r'    \(net (\S+)\n      \(pins ([^)]*)\)\n    \)\n',re.S)
def repl(m):
    name=m.group(1).strip('"'); pins=m.group(2).split()
    if name not in need: return ''
    keep=[p for p in pins if p.split('@')[0] in need[name]]
    if len(keep)<2: return ''
    return f"    (net {m.group(1)}\n      (pins {' '.join(keep)})\n    )\n"
body=net_re.sub(repl,dsn[start:])
open(sys.argv[3],'w').write(dsn[:start]+body)
print('nets kept',len(re.findall(r'\(net \S+\n      \(pins',body)),'of',len(re.findall(r'\(net \S+\n      \(pins',dsn[start:])))
