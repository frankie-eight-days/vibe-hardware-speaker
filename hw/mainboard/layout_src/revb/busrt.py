"""A* router variant for the rev B corridor bus: per-layer step cost, raster keep-out masks (K3: L3 outside corridor, K4: L4 over L3 splits/corridor)."""
import sys,math,heapq,numpy as np,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
X0,Y0,R0=60.0,73.0,0.25
import re
SWRE=re.compile(r'(SW|AGND)')
class BusRouter(arouter.Router):
    def _collect(s,ln):
        super()._collect(ln)
        # tag zone fills so they can be softened near endpoints
        L=arouter.LAY[ln]; zl=[]
        for z in s.b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(L) or not z.HasFilledPolysForLayer(L) or z.GetAssignedPriority()<=1: continue
            zl.append(z.GetNetname())
        s.zonenets=getattr(s,'zonenets',{}); s.zonenets[ln]=zl
    def _blocked_nozone(s,ln,net,r,extra=()):
        saved=s.items[ln]
        nz=len(s.zonenets.get(ln,[]))
        s.items[ln]=saved[:len(saved)-nz] if nz else saved
        B=arouter.Router.blocked(s,ln,net,r,extra)
        s.items[ln]=saved
        M=s.masks.get(ln)
        if M is not None:
            j=np.clip(((s.Y-Y0)/R0).astype(int),0,M.shape[0]-1); i=np.clip(((s.X-X0)/R0).astype(int),0,M.shape[1]-1); B|=M[j,i]
        # keep switch-node pours hard
        for k,(kind,n,g) in enumerate(saved[len(saved)-nz:] if nz else []):
            if SWRE.search(n) and n!=net:
                s.items[ln]=[(kind,n,g)]; B|=arouter.Router.blocked(s,ln,net,r,extra); s.items[ln]=saved
        return B
    def __init__(s,board,window,res,layers,masks):
        super().__init__(board,window,res,layers); s.masks=masks
    soft=[]   # (x,y,rad): pour fills (non-switch nets) are ignored near these points (the pour re-fills around the escape)
    def blocked(s,ln,net,r,extra=()):
        B=super().blocked(ln,net,r,extra)
        if s.soft:
            near=np.zeros(s.X.shape,bool)
            for x,y,rad in s.soft: near|=(s.X-x)**2+(s.Y-y)**2<rad*rad
            if near.any(): B=np.where(near,s._blocked_nozone(ln,net,r,extra),B)
        M=s.masks.get(ln)
        if M is not None:
            j=np.clip(((s.Y-Y0)/R0).astype(int),0,M.shape[0]-1); i=np.clip(((s.X-X0)/R0).astype(int),0,M.shape[1]-1)
            B|=M[j,i]
        return B
    def route2(s,net,src,dst,width=0.2,clr=0.2,layers=('F.Cu','In2.Cu','B.Cu'),via=(0.5,0.25),via_cost=40,lcost=None,start_layers=None,end_layers=None,maxit=20000000,keep=()):
        lcost=lcost or {l:1.0 for l in layers}
        r=width/2+clr
        Bl={l:s.blocked(l,net,r,keep) for l in layers}
        vr=via[0]/2+clr; Bv=np.zeros(s.X.shape,bool)
        for l in s.all: Bv|=arouter.Router.blocked(s,l,net,vr,keep)
        for l in layers:
            M=s.masks.get(l)  # vias may sit in keep-out cells (they are not wires) - nothing to add
        def idx(p): return (int(round((p[1]-s.y0)/s.res)),int(round((p[0]-s.x0)/s.res)))
        sj,si=idx(src); g=idx(dst)
        start_layers=start_layers or ['F.Cu']; end_layers=end_layers or ['F.Cu']
        Li={l:k for k,l in enumerate(layers)}
        dirs=[(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
        h=lambda j,i: 1.4*math.hypot(j-g[0],i-g[1])*min(lcost.values())
        openq=[]; best={}; came={}
        for sl in start_layers:
            n0=(sj,si,Li[sl],-1); best[n0]=0.0; heapq.heappush(openq,(h(sj,si),0.0,n0,None))
        it=0
        while openq and it<maxit:
            f,c,node,par=heapq.heappop(openq); it+=1
            if node in came: continue
            came[node]=par; j,i,li,d=node
            if (j,i)==g and layers[li] in end_layers: return s._emit(net,node,came,layers,width,via)
            lc=lcost[layers[li]]
            for k,(dj,di) in enumerate(dirs):
                nj,ni=j+dj,i+di
                if not(0<=nj<s.ny and 0<=ni<s.nx) or Bl[layers[li]][nj,ni]: continue
                step=(1.4142 if dj and di else 1.0)*lc; turn=0 if d in(-1,k) else 3.0
                nn=(nj,ni,li,k); nc=c+step+turn
                if nc<best.get(nn,1e18): best[nn]=nc; heapq.heappush(openq,(nc+h(nj,ni),nc,nn,node))
            if not Bv[j,i]:
                for lj in range(len(layers)):
                    if lj==li: continue
                    nn=(j,i,lj,-1); nc=c+via_cost
                    if nc<best.get(nn,1e18): best[nn]=nc; heapq.heappush(openq,(nc+h(j,i),nc,nn,node))
        return None
