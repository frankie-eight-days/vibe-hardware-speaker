import json,sys,numpy as np
from matplotlib.path import Path
G=json.load(open(sys.argv[1])); D=0.1
E=[e for e in G['edge'] if len(e)>3][0]
xs=[p[0] for p in E]; ys=[p[1] for p in E]
x0,x1,y0,y1=min(xs)-8,max(xs)+8,min(ys)-2,max(ys)+2
gx,gy=np.meshgrid(np.arange(x0,x1,D)+D/2,np.arange(y0,y1,D)+D/2); pts=np.c_[gx.ravel(),gy.ravel()]
def m(poly): return Path(poly).contains_points(pts).reshape(gx.shape)
board=m(E)
ko=np.zeros_like(board)
for z in G['zones']:
    if z['name'].startswith('ANT') and z['layer']=='F.Cu': ko|=m(z['pts'])
A=(board&~ko).sum()*D*D
res={}
for side in 'FB':
    occ=np.zeros_like(board); s=0
    for f in G['fps']:
        if f['side']!=side or f['ref']=='BRD1': continue
        for c in f['cy']: mm_=m(c); occ|=mm_
    res[side]=(occ&board&~ko).sum()*D*D
print('board %.0f mm2 (keep-out %.0f) | top %.0f -> %.1f %% | bottom %.0f -> %.1f %% | both %.1f %%'%(A,(ko&board).sum()*D*D,res['F'],100*res['F']/A,res['B'],100*res['B']/A,100*(res['F']+res['B'])/(2*A)))
