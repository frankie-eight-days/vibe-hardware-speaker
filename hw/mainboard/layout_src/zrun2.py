import numpy as np, zsolve
def Z(w,s,single,mask,dx=0.0175,it=3000,om=1.975):
    eps,c1,c2=zsolve.build(w,s,0.2104,0.035,4.4,0.015 if mask else 0,3.8,dx,single)
    v2=0.0 if single else -1.0
    C=zsolve.solveV(eps,c1,c2,v2,iters=it,omega=om); C0=zsolve.solveV(np.ones_like(eps),c1,c2,v2,iters=it,omega=om)
    return 1/(2.998e8*np.sqrt(C*C0)), C/C0
print("single 0.36 nomask", Z(0.36,0,True,False),flush=True)
print("single 0.36 mask", Z(0.36,0,True,True),flush=True)
for w,s in [(0.16,0.13),(0.18,0.13),(0.20,0.13),(0.18,0.15),(0.20,0.15),(0.22,0.15),(0.24,0.15)]:
    z,e=Z(w,s,False,True); print(f"diff w={w} s={s} Zdiff={2*z:.1f}",flush=True)
