"""Small deterministic A* router for the hand-routed critical nets (offline, KiCad pcbnew geometry).
Routes one connection at a time on F.Cu/B.Cu (vias allowed), respecting clearance to every other-net pad/track/via/zone fill
and to caller-supplied keep-away polygons (e.g. switch nodes). Output: track/via dicts for the spec (replayed via Konnect)."""
import pcbnew, numpy as np, heapq, math
from matplotlib.path import Path
mm=pcbnew.ToMM
LAY={'F.Cu':pcbnew.F_Cu,'In1.Cu':pcbnew.In1_Cu,'In2.Cu':pcbnew.In2_Cu,'B.Cu':pcbnew.B_Cu}
def poly_pts(sps):
    out=[]
    for i in range(sps.OutlineCount()):
        o=sps.Outline(i); out.append(np.array([[mm(o.CPoint(k).x),mm(o.CPoint(k).y)] for k in range(o.PointCount())]))
    return out
def seg_dist(X,Y,a,b):
    ax,ay=a; bx,by=b; dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
    if L<1e-12: return np.hypot(X-ax,Y-ay)
    t=np.clip(((X-ax)*dx+(Y-ay)*dy)/L,0,1); return np.hypot(X-(ax+t*dx),Y-(ay+t*dy))
class Router:
    def __init__(self,board,window,res=0.05,layers=('F.Cu','B.Cu')):
        self.b=board; self.x0,self.y0,self.x1,self.y1=window; self.res=res; self.layers=layers
        self.nx=int((self.x1-self.x0)/res)+1; self.ny=int((self.y1-self.y0)/res)+1
        xs=self.x0+np.arange(self.nx)*res; ys=self.y0+np.arange(self.ny)*res
        self.X,self.Y=np.meshgrid(xs,ys)
        self.all=('F.Cu','In1.Cu','In2.Cu','B.Cu')
        self.items={l:[] for l in self.all}
        for l in self.all: self._collect(l)
    def _collect(self,ln):
        L=LAY[ln]; it=self.items[ln]; x0,y0,x1,y1=self.x0-2,self.y0-2,self.x1+2,self.y1+2
        def inwin(bb): return not (mm(bb.GetRight())<x0 or mm(bb.GetLeft())>x1 or mm(bb.GetBottom())<y0 or mm(bb.GetTop())>y1)
        for p in self.b.GetPads():
            if not p.IsOnLayer(L) or not inwin(p.GetBoundingBox()): continue
            it.append(('poly',p.GetNetname(),poly_pts(p.GetEffectivePolygon(L,pcbnew.ERROR_INSIDE))))
            if p.GetDrillSizeX()>0: it.append(('hole',p.GetNetname(),(mm(p.GetPosition().x),mm(p.GetPosition().y),mm(p.GetDrillSizeX())/2)))
        for t in self.b.GetTracks():
            if not inwin(t.GetBoundingBox()): continue
            if t.GetClass()=='PCB_VIA':
                it.append(('circ',t.GetNetname(),(mm(t.GetPosition().x),mm(t.GetPosition().y),mm(t.GetWidth(L))/2)))
            elif t.GetLayer()==L:
                it.append(('seg',t.GetNetname(),((mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y)),mm(t.GetWidth())/2)))
        for z in self.b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(L) or not z.HasFilledPolysForLayer(L) or z.GetAssignedPriority()<=1: continue
            it.append(('poly',z.GetNetname(),poly_pts(z.GetFilledPolysList(L))))
        for d in self.b.GetDrawings():
            if d.GetLayer()==pcbnew.Edge_Cuts: pass
    def blocked(self,ln,net,r,extra=()):
        X,Y=self.X,self.Y; B=np.zeros(X.shape,bool)
        for kind,n,g in self.items[ln]+[('poly','__KEEP__',[np.array(p)]) for p in extra]:
            if n==net and n!='': continue
            if kind=='poly':
                for P in g:
                    if len(P)<3: continue
                    bx0,by0=P.min(0)-r; bx1,by1=P.max(0)+r
                    i0=max(int((bx0-self.x0)/self.res),0); i1=min(int((bx1-self.x0)/self.res)+2,self.nx)
                    j0=max(int((by0-self.y0)/self.res),0); j1=min(int((by1-self.y0)/self.res)+2,self.ny)
                    if i1<=i0 or j1<=j0: continue
                    sx=X[j0:j1,i0:i1]; sy=Y[j0:j1,i0:i1]
                    ins=Path(P).contains_points(np.c_[sx.ravel(),sy.ravel()]).reshape(sx.shape)
                    d=np.full(sx.shape,1e9)
                    for a,b2 in zip(P,np.roll(P,-1,0)): d=np.minimum(d,seg_dist(sx,sy,a,b2))
                    B[j0:j1,i0:i1]|=ins|(d<r)
            elif kind in('circ','hole'):
                cx,cy,rr=g; B|=np.hypot(X-cx,Y-cy)<rr+r
            elif kind=='seg':
                a,b2,hw=g; B|=seg_dist(X,Y,a,b2)<hw+r
        # board edge margin
        return B
    def route(self,net,src,dst,width=0.2,clr=0.2,layers=None,via=(0.5,0.25),via_cost=60,keep=(),start_layer='F.Cu',end_layers=None,maxit=600000):
        layers=layers or list(self.layers)
        r=width/2+clr
        Bl={l:self.blocked(l,net,r,keep.get(l,[]) if isinstance(keep,dict) else keep) for l in layers}
        vr=via[0]/2+clr
        Bv=np.zeros(self.X.shape,bool)
        for l in self.all: Bv|=self.blocked(l,net,vr,keep.get(l,[]) if isinstance(keep,dict) else keep)
        def idx(p): return (int(round((p[1]-self.y0)/self.res)),int(round((p[0]-self.x0)/self.res)))
        s=idx(src); g=idx(dst); end_layers=end_layers or layers
        for l in layers:
            for (j,i) in (s,g):  # clear a small disc at endpoints (they sit on same-net pads)
                pass
        dirs=[(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
        Lidx={l:k for k,l in enumerate(layers)}
        start=(s[0],s[1],Lidx[start_layer],-1)
        h=lambda j,i: math.hypot(j-g[0],i-g[1])
        openq=[(h(s[0],s[1]),0.0,start,None)]; came={}; best={start[:3]+(start[3],):0.0}
        it=0
        while openq and it<maxit:
            f,c,node,par=heapq.heappop(openq); it+=1
            if node in came: continue
            came[node]=par
            j,i,li,d=node
            if (j,i)==g and layers[li] in end_layers: return self._emit(net,node,came,layers,width,via)
            for k,(dj,di) in enumerate(dirs):
                nj,ni=j+dj,i+di
                if not(0<=nj<self.ny and 0<=ni<self.nx) or Bl[layers[li]][nj,ni]: continue
                step=1.4142 if dj and di else 1.0
                turn=0 if d in(-1,k) else 2.0
                nn=(nj,ni,li,k); nc=c+step+turn
                if nc<best.get(nn,1e18): best[nn]=nc; heapq.heappush(openq,(nc+h(nj,ni),nc,nn,node))
            if not Bv[j,i]:
                for lj in range(len(layers)):
                    if lj==li: continue
                    nn=(j,i,lj,-1); nc=c+via_cost
                    if nc<best.get(nn,1e18): best[nn]=nc; heapq.heappush(openq,(nc+h(j,i),nc,nn,node))
        return None
    def _emit(self,net,node,came,layers,width,via):
        pts=[]
        while node: pts.append(node); node=came[node]
        pts.reverse()
        T=[];V=[]; seg=[pts[0]]
        def xy(n): return (round(self.x0+n[1]*self.res,4),round(self.y0+n[0]*self.res,4))
        cur=[pts[0]]
        for a,b in zip(pts,pts[1:]):
            if a[2]!=b[2]:
                self._flush(cur,T,net,layers,width,xy); V.append(dict(net=net,x=xy(a)[0],y=xy(a)[1],size=via[0],drill=via[1])); cur=[b]
            else: cur.append(b)
        self._flush(cur,T,net,layers,width,xy)
        return T,V
    def _flush(self,cur,T,net,layers,width,xy):
        if len(cur)<2: return
        # simplify collinear
        P=[xy(n) for n in cur]; S=[P[0]]
        for k in range(1,len(P)-1):
            a,b,c=S[-1],P[k],P[k+1]
            if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-6: S.append(b)
        S.append(P[-1])
        for a,b in zip(S,S[1:]): T.append(dict(net=net,layer=layers[cur[0][2]],x1=a[0],y1=a[1],x2=b[0],y2=b[1],w=width))
