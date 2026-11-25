import sys,json
sys.path.insert(0,'.')
from sexp import *
n=parse(open('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/out/speaker_main.net').read())
comps={}
for c in find(get(n,'components'),'comp'):
    ref=get(c,'ref')[1]; fp=get(c,'footprint'); val=get(c,'value')[1]
    props={p[1][1]:p[2][1] for p in find(c,'property') if len(p)>2}
    comps[ref]=dict(fp=fp[1] if fp else None,val=val,dnp=props.get('DNP',''),sheet=get(c,'sheetpath')[1][1] if get(c,'sheetpath') else '')
nets={}
for ne in find(get(n,'nets'),'net'):
    name=get(ne,'name')[1]
    nets[name]=[(get(x,'ref')[1],get(x,'pin')[1]) for x in find(ne,'node')]
json.dump(dict(comps=comps,nets=nets),open('netlist.json','w'),indent=0)
print(len(comps),'comps',len(nets),'nets')
big=sorted(nets.items(),key=lambda kv:-len(kv[1]))
for k,v in big[:25]: print(len(v),k)
print([k for k,v in nets.items() if len(v)==1][:60])
