"""S8: USB-C VBUS hot-plug ringing. Cable L/R into the sink's MLCC bank, with/without damping.
Board: D601 SMF24A TVS, C701/C702 2x10uF 1206 50V X5R + C703 100nF on VBUS, C604 1uF (CH224Q VHV),
PMID C704-C706 3x10uF + C707 via BQ25792 RBFET body diode. MLCC capacitance derated for DC bias at the final voltage."""
import subprocess, itertools, re, json
def derate(v):  # 1206 10uF 50V X5R effective fraction (Samsung/Murata curves, approx.)
    return {5:0.85, 15:0.45, 20:0.38}[v]
cables={'0.3m':(0.25e-6,0.04),'1m':(0.75e-6,0.10),'2m':(1.5e-6,0.20)}   # loop L, round-trip R
damp={'none':None,'TI 2R+2.2u (R601/C602)':(2.0,2.2e-6),'1R+10u 1206':(1.0,10e-6),'ideal 47u ESR 0.3R':(0.3,47e-6)}
# ECO-004 C605: Lelon VZH470M1VTR-0606 (C134832), 47uF +-20% 35V, Z<=0.44R @100kHz/20C, tan d 0.13 @120Hz (ESR120 <= 3.7R),
# Z(-25C)/Z(20C) <= 2. Al-electrolytic C is not DC-bias derated. ESR at the ~40 kHz ring is taken as the 100 kHz Z max.
damp.update({'C605 47u ESR 0.44R (Zmax 20C)':(0.44,47e-6),
             'C605 37.6u (-20%) ESR 0.44R':(0.44,37.6e-6),
             'C605 37.6u ESR 0.88R (-25C)':(0.88,37.6e-6),
             'C605 47u 0.44R + R605 0.5R 0805':(0.94,47e-6)})
res=[]
for (v,(cn,(L,R)),(dn,d)) in itertools.product([5,15,20],cables.items(),damp.items()):
    k=derate(v); c10=10e-6*k
    snub='' if d is None else f"Rs vbus sn {d[0]}\nCs sn 0 {d[1]*(k if d[1]<=10e-6 else 1)}\n"
    net=f"""* hotplug
Vs src 0 PWL(0 0 1u 0 1.05u {v})
Rsrc src a 0.02
Lc a b {L}
Rc b vbus {R}
.model tvs D(BV=27.5 IBV=1m RS=2.1 CJO=300p)
Dt 0 vbus tvs
C1 vbus x1 {c10}
R1 x1 x2 5m
L1 x2 0 1n
C2 vbus y1 {c10}
R2 y1 y2 5m
L2 y2 0 1n
C3 vbus 0 {100e-9}
C4 vbus 0 {1e-6*k}
.model bd D(RS=0.01)
Db vbus pmid bd
Cp pmid z1 {3*c10}
Rp z1 0 3m
{snub}.tran 2n 60u
.control
run
meas tran vpk MAX v(vbus)
meas tran ppk MAX v(pmid)
.endc
.end
"""
    open('deck.cir','w').write(net)
    o=subprocess.run(['ngspice','-b','deck.cir'],capture_output=True,text=True).stdout
    vp=float(re.search(r'vpk\s*=\s*([-\d.e+]+)',o).group(1)); pp=float(re.search(r'ppk\s*=\s*([-\d.e+]+)',o).group(1))
    res.append(dict(V=v,cable=cn,damping=dn,vbus_pk=round(vp,2),pmid_pk=round(pp,2)))
json.dump(res,open('results.json','w'),indent=1)
for v in [5,15,20]:
    print(f"\n== {v} V hot-plug: VBUS peak (V) ==")
    print(f"{'damping':34s}"+''.join(f"{c:>8s}" for c in cables))
    for dn in damp:
        print(f"{dn:34s}"+''.join(f"{r['vbus_pk']:8.1f}" for c in cables for r in res if r['V']==v and r['cable']==c and r['damping']==dn))
