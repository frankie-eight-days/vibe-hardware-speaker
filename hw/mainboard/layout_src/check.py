import json, math, importlib, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import geom, place; importlib.reload(place)
P=dict(place.P)
try:
    import tps; P.update(tps.TPS)
except Exception as e: print('tps',e)
NL=geom.NL
missing=[r for r in NL['comps'] if r not in P]
print('missing',len(missing),missing)
H=np.load('hmap.npy'); meta=json.load(open('hmap_meta.json')); hx=np.array(meta['xs']); hy=np.array(meta['ys'])
HEIGHT={'Capacitor_SMD:CP_Elec_10x10':10.5,'Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical':11.5,'Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal':8.5,
 'Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical':7.0,'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical':6.0,'Inductor_SMD:L_Changjiang_FXL1040':4.0,
 'Inductor_SMD:L_Changjiang_FXL0630':3.0,'Inductor_SMD:L_Changjiang_FXL0420':2.0,'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12':3.3,
 'Connector_FFC-FPC:JUSHUO_AFA07-S20FCA-00_1x20-1MP_P1.0mm_Horizontal':2.5,'Espressif:ESP32-WROVER-E':3.3,'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical':8.5,
 'Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A':1.6,'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm':1.75,'speaker:Fuse_2410_6125Metric':2.7}
def clearance_at(b):
    x0,y0,x1,y1=b  # kicad -> enclosure
    ex0,ex1=x0-150,x1-150; ey0,ey1=100-y1,100-y0
    m=(hx>=ex0-0.25)&(hx<=ex1+0.25); n=(hy>=ey0-0.25)&(hy<=ey1+0.25)
    sub=H[np.ix_(n,m)]
    return sub.min()-1.0 if sub.size else 99
bad=[]
cys={r:geom.courtyard(r,P) for r in P}
refs=list(P)
ov=[]
for i,a in enumerate(refs):
    for b in refs[i+1:]:
        if P[a][3]!=P[b][3]: continue
        A=cys[a];B=cys[b]
        if A[0]<B[2]-0.01 and B[0]<A[2]-0.01 and A[1]<B[3]-0.01 and B[1]<A[3]-0.01:
            ov.append((a,b,round(min(A[2],B[2])-max(A[0],B[0]),2),round(min(A[3],B[3])-max(A[1],B[1]),2)))
print('courtyard overlaps',len(ov)); [print('  ',o) for o in ov]
holes=[(80,79),(80,117),(150,117),(168,79),(236,117),(236,88)]
for r in refs:
    if r[0]=='H': continue
    x0,y0,x1,y1=cys[r]
    if P[r][3]=='F' and (x0<60 and r!='U101' or x1>240 or y0<75 and r!='J601' or y1>121): print('OUT of board',r,cys[r])
    for hx_,hy_ in holes:
        dx=max(x0-hx_,0,hx_-x1); dy=max(y0-hy_,0,hy_-y1)
        if math.hypot(dx,dy)<3.25 and P[r][3]=='F': print('HOLE keepout',r,(hx_,hy_),round(math.hypot(dx,dy),2))
    # antenna strip X<75 allowed only for Y 86..112
    if P[r][3]=='F' and r!='U101' and x0<75 and (y0<86 or y1>115): print('ANTENNA strip',r,cys[r])
    if P[r][3]=='F' and x0<63 and r!='U101': print('ANTENNA area',r)
    hgt=HEIGHT.get(geom.fp(r),1.5) if P[r][3]=='F' else 0
    if hgt>0:
        c=clearance_at(geom.fabbox(r,P))
        if c<hgt: print('HEIGHT',r,'needs',hgt,'has',round(c,1))
# plot
fig,ax=plt.subplots(figsize=(36,10))
ax.add_patch(Rectangle((60,75),180,46,fill=False,lw=1.5)); ax.add_patch(Rectangle((143,73.5),14,1.5,fill=False))
ax.add_patch(Rectangle((60,75),15,46,color='red',alpha=0.08)); ax.add_patch(Rectangle((55.5,90),6.3,18,color='red',alpha=0.2))
for (zx0,zx1,zy0,zy1,c) in [(144,156,84.9,121,'green')]: ax.add_patch(Rectangle((zx0,zy0),zx1-zx0,zy1-zy0,color=c,alpha=0.05))
for hx_,hy_ in holes: ax.add_patch(Circle((hx_,hy_),3.25,fill=False,ls='--'))
col={'F':'tab:blue','B':'tab:orange'}
for r in refs:
    x0,y0,x1,y1=cys[r]
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec=col[P[r][3]],lw=0.6))
    if r[0] not in 'HF' or r.startswith('FID'):
        for p in geom.pads(r,P):
            ax.add_patch(Rectangle((p['x']-p['w']/2,p['y']-p['h']/2),p['w'],p['h'],color=('gray' if p['net'].endswith('GND') else 'tab:red') if P[r][3]=='F' else 'tab:orange',alpha=0.5,lw=0))
    ax.text((x0+x1)/2,(y0+y1)/2,r,fontsize=4.5,ha='center',va='center')
ax.set_xlim(54,242); ax.set_ylim(123,71); ax.set_aspect('equal'); ax.grid(True,lw=0.2)
ax.set_xticks(range(55,245,5)); ax.set_yticks(range(72,124,2))
plt.savefig(sys.argv[1] if len(sys.argv)>1 else 'place.png',dpi=110,bbox_inches='tight')
