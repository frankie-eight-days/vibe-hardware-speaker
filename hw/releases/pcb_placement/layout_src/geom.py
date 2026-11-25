import json, math
G=json.load(open('/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/pcb/fpgeom.json'))
NL=json.load(open('/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/pcb/netlist.json'))
PIN={}
for n,mem in NL['nets'].items():
    for r,p in mem: PIN.setdefault(r,{})[p]=n
G['speaker:MountingHole_3.2mm_M3']=dict(cy=[-3.45,-3.45,3.45,3.45],pads=[['',0,0,3.2,3.2,0,0,3.2,0,False]],fab=None)
G['speaker:Fiducial_1mm_Mask2mm']=dict(cy=[-1.25,-1.25,1.25,1.25],pads=[['',0,0,1,1,0,0,0,0,True]],fab=None)
def fp(ref): return NL['comps'][ref]['fp'] if ref in NL['comps'] else {'H':'speaker:MountingHole_3.2mm_M3','F':'speaker:Fiducial_1mm_Mask2mm'}[ref[0]]
def rot(x,y,deg):
    t=math.radians(deg); c=round(math.cos(t),12); s=round(math.sin(t),12)
    return (x*c+y*s, -x*s+y*c)
def xf(ref,P,lx,ly):
    x,y,r,side=P[ref]
    if side=='B': lx=-lx  # bottom side mirrors X before rotation (KiCad flip)
    dx,dy=rot(lx,ly,r); return (x+dx,y+dy)
def courtyard(ref,P):
    g=G[fp(ref)]; c=g['cy'] or [-0.5,-0.5,0.5,0.5]
    pts=[xf(ref,P,c[0],c[1]),xf(ref,P,c[2],c[1]),xf(ref,P,c[2],c[3]),xf(ref,P,c[0],c[3])]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return (min(xs),min(ys),max(xs),max(ys))
def fabbox(ref,P):
    g=G[fp(ref)]; c=g.get('fab') or g['cy']
    pts=[xf(ref,P,c[0],c[1]),xf(ref,P,c[2],c[1]),xf(ref,P,c[2],c[3]),xf(ref,P,c[0],c[3])]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return (min(xs),min(ys),max(xs),max(ys))
def pads(ref,P):
    out=[]
    for p in G[fp(ref)]['pads']:
        num,lx,ly,sx,sy,shape,attr,drill,prot,ontop=p
        x,y=xf(ref,P,lx,ly)
        r=(P[ref][2]+prot)%180
        w,h=(sx,sy) if abs(r-90)>1 else (sy,sx)
        net=PIN.get(ref,{}).get(num,'')
        out.append(dict(num=num,x=x,y=y,w=w,h=h,net=net,drill=drill,shape=shape))
    return out
def pad(ref,P,num):
    return [p for p in pads(ref,P) if p['num']==num]
