import numpy as np, zsolve, sys
# rev B 6-layer: L1 over L2, JLC06161H-1080B: 1080 prepreg h 0.0764 Er 3.91, 1 oz outer t 0.035, mask 15 um Er 3.8
def Z(w,s,single,mask,dx=0.005,it=6000,om=1.985):
    eps,c1,c2=zsolve.build(w,s,0.0764,0.035,3.91,0.015 if mask else 0,3.8,dx,single)
    v2=0.0 if single else -1.0
    C=zsolve.solveV(eps,c1,c2,v2,iters=it,omega=om); C0=zsolve.solveV(np.ones_like(eps),c1,c2,v2,iters=it,omega=om)
    return 1/(2.998e8*np.sqrt(C*C0)), C/C0
for w,s in [(0.10,0.15),(0.11,0.15),(0.12,0.15)]:
    z,e=Z(w,s,False,True); print(f"diff w={w} s={s} Zdiff={2*z:.1f} eeff={e:.2f}",flush=True)
