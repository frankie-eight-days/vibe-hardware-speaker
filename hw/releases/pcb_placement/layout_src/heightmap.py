import numpy as np, glob, os, json
B="/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/mech/concept/build/"
def load(fn):
    d=open(fn,'rb').read()
    if d[:5]==b'solid' and b'facet' in d[:300]:
        raise Exception('ascii')
    n=np.frombuffer(d[80:84],np.uint32)[0]
    a=np.frombuffer(d[84:84+50*n],dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
    return a['v'].reshape(-1,3,3).astype(float)
skip={'mainboard_pcb','mainboard_components','ui_board_pcb','display_module','display_lens','encoder_EC11','knob','buttons','battery_swell_envelope'}
Z0=-33.4
xs=np.arange(-90,90.01,0.5); ys=np.arange(-21,26.51,0.5)
X,Y=np.meshgrid(xs,ys)
H=np.full(X.shape,99.0); WHO=np.full(X.shape,'',dtype=object)
for fn in sorted(glob.glob(B+'*.stl')):
    name=os.path.basename(fn)[:-4]
    if name in skip: continue
    T=load(fn)
    for t in T:
        x0,y0=t[:,0].min(),t[:,1].min(); x1,y1=t[:,0].max(),t[:,1].max()
        if x1<-90 or x0>90 or y1<-21 or y0>26.5: continue
        i0=np.searchsorted(xs,x0); i1=np.searchsorted(xs,x1,'right'); j0=np.searchsorted(ys,y0); j1=np.searchsorted(ys,y1,'right')
        if i1<=i0 or j1<=j0: continue
        px=X[j0:j1,i0:i1]; py=Y[j0:j1,i0:i1]
        (ax,ay,az),(bx,by,bz),(cx,cy,cz)=t
        den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-12: continue
        l1=((by-cy)*(px-cx)+(cx-bx)*(py-cy))/den
        l2=((cy-ay)*(px-cx)+(ax-cx)*(py-cy))/den
        l3=1-l1-l2
        m=(l1>=-1e-9)&(l2>=-1e-9)&(l3>=-1e-9)
        z=l1*az+l2*bz+l3*cz
        m&=z>Z0-0.01
        sub=H[j0:j1,i0:i1]; w=WHO[j0:j1,i0:i1]
        upd=m&(z-Z0<sub)
        sub[upd]=(z-Z0)[upd]; w[upd]=name
np.save('hmap.npy',H); 
json.dump(dict(xs=xs.tolist(),ys=ys.tolist(),who=WHO.tolist()),open('hmap_meta.json','w'))
# print coarse map (5mm), min height in each cell minus 1mm air
for y in np.arange(25,-21.1,-2.5):
    row=[]
    for x in np.arange(-90,90,5):
        m=(X>=x)&(X<x+5)&(Y<=y)&(Y>y-2.5)
        row.append(f"{min(H[m].min()-1,99):4.0f}")
    print(f"{y:6.1f}"," ".join(row))
