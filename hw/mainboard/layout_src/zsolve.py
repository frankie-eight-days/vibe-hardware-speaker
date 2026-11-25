# 2D finite-difference Laplace solver (red-black SOR, numpy) for microstrip / coupled microstrip. Units mm.
import numpy as np
def build(w,s,h,t,er,mask_t,er_mask,dx,single):
    W=2*w+s+14*h+1.5; H=h+t+10*h+1.0
    nx=int(W/dx)|1; ny=int(H/dx)
    xs=(np.arange(nx)-nx//2)*dx; ys=(np.arange(ny)+0.5)*dx
    X,Y=np.meshgrid(xs,ys)
    eps=np.ones((ny,nx)); eps[Y<h]=er
    if single:
        c1=(np.abs(X)<=w/2)&(Y>=h)&(Y<=h+t); c2=np.zeros_like(c1)
    else:
        xc=(w+s)/2
        c1=(np.abs(X+xc)<=w/2)&(Y>=h)&(Y<=h+t); c2=(np.abs(X-xc)<=w/2)&(Y>=h)&(Y<=h+t)
    if mask_t>0:
        m=(Y>=h)&(Y<h+mask_t); m|=(Y>=h)&(Y<h+t+mask_t)&(np.abs(X)<=(w+s)/2+w/2+mask_t if not single else np.abs(X)<=w/2+mask_t)
        eps[m&~(c1|c2)]=er_mask
    return eps,c1,c2
def solveV(eps,c1,c2,v2,iters=6000,omega=1.9):
    ny,nx=eps.shape
    eps=eps.copy(); eps[c1|c2]=1e9  # conductor faces: field sees only the adjacent medium
    E=np.pad(eps,1,mode='edge')
    def harm(a,b): return 2*a*b/(a+b)
    eN=harm(E[1:-1,1:-1],E[2:,1:-1]); eS=harm(E[1:-1,1:-1],E[:-2,1:-1]); eS[0,:]=2*eps[0,:]  # ground plane half a cell below row0
    eE=harm(E[1:-1,1:-1],E[1:-1,2:]); eW=harm(E[1:-1,1:-1],E[1:-1,:-2])
    D=eN+eS+eE+eW
    V=np.zeros((ny+2,nx+2))  # padded with 0 (ground at boundaries)
    fixed=c1|c2
    jj,ii=np.indices((ny,nx)); red=((jj+ii)%2==0)
    for it in range(iters):
        for msk in (red,~red):
            Vc=V[1:-1,1:-1]
            nb=(eN*V[2:,1:-1]+eS*V[:-2,1:-1]+eE*V[1:-1,2:]+eW*V[1:-1,:-2])/D
            upd=msk&~fixed
            Vc[upd]+=omega*(nb[upd]-Vc[upd])
            Vc[c1]=1.0; Vc[c2]=v2
    Vc=V[1:-1,1:-1]
    # charge on c1: sum over c1 cells of flux to non-c1 neighbours
    Q=0.0
    for (d,ee) in (((1,0),eN),((-1,0),eS),((0,1),eE),((0,-1),eW)):
        nbV=V[1+d[0]:ny+1+d[0],1+d[1]:nx+1+d[1]]
        nbin=np.roll(c1,(-d[0],-d[1]),axis=(0,1))
        Q+=np.sum((ee*(Vc-nbV))[c1&~nbin])
    return Q*8.854e-12
def Z(w,s,h=0.2104,t=0.035,er=4.4,mask_t=0.015,er_mask=3.8,dx=0.01,single=False):
    eps,c1,c2=build(w,s,h,t,er,mask_t,er_mask,dx,single)
    v2=0.0 if single else -1.0
    C=solveV(eps,c1,c2,v2); C0=solveV(np.ones_like(eps),c1,c2,v2)
    z=1/(2.998e8*np.sqrt(C*C0)); return z,C/C0
if __name__=='__main__':
    import sys
    for w in (0.30,0.34,0.36): z,e=Z(w,0,single=True); print(f"single L1 w={w}: Z0={z:.1f} ohm eeff={e:.2f}",flush=True)
    for w,s in [(0.15,0.15),(0.18,0.15),(0.20,0.15),(0.20,0.20),(0.22,0.20)]:
        z,e=Z(w,s); print(f"diff L1 w={w} s={s}: Zdiff={2*z:.1f} ohm",flush=True)
