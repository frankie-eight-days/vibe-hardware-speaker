"""Freerouting SES -> spec JSON (tracks/vias in KiCad mm) for the via-net gate and the A*/FR split. usage: ses2spec.py f.ses out.json"""
import sys,re,json
s=open(sys.argv[1]).read(); s=s[s.index('(network_out'):]
res=float(re.search(r'\(resolution um (\d+)\)',open(sys.argv[1]).read()).group(1)); k=1/(1000*res)
T=[];V=[]
for m in re.finditer(r'\(net ("[^"]*"|\S+)(.*?)\n      \)',s,re.S):
    net=m.group(1).strip('"'); body=m.group(2)
    for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)',body):
        c=list(map(int,w.group(3).split())); P=[(c[i]*k,-c[i+1]*k) for i in range(0,len(c),2)]
        for a,b in zip(P,P[1:]): T.append(dict(net=net,layer=w.group(1),x1=a[0],y1=a[1],x2=b[0],y2=b[1],w=int(w.group(2))*k))
    for v in re.finditer(r'\(via "?([^"\s]+)"? (-?\d+) (-?\d+)',body): V.append(dict(net=net,x=int(v.group(2))*k,y=-int(v.group(3))*k))
json.dump(dict(tracks=T,vias=V),open(sys.argv[2],'w')); print('FR wires',len(T),'vias',len(V))
