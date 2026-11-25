from blk_common import *
import geom, place
P=place.P
def pp(ref,num):
    p=[q for q in geom.pads(ref,P) if q['num']==num][0]; return (round(p['x'],4),round(p['y'],4))
def pnet(ref,num): return [q for q in geom.pads(ref,P) if q['num']==num][0]['net']
T=[];V=[];Z=[];J=[]; t,v,z,j=mk(T,V,Z,J,NET)
for side in ('L','R'):
    U='U301' if side=='L' else 'U401'; ux=P[U][0]; s=-1 if side=='L' else 1     # s: direction from IC toward the inductors is -X for L, +X for R
    X=lambda d: ux+s*d          # d measured from IC centre toward the output side
    # PVDD groups at both ends of the output pin row (SLASEH5D 9.1.2: 0.1uF <=1 mm, 10uF <=3 mm); L1 pour + vias to the L3 PVDD plane
    for yy in ((86.2,94.1,92.5),(101.0,108.9,102.7)):
        y0,y1,yk=yy
        if y0<95: pts=[(X(2.4),y0),(X(3.9),y0),(X(3.9),y1),(X(2.07),y1),(X(2.07),yk),(X(2.4),yk)]
        else:     pts=[(X(2.07),y0),(X(3.9),y0),(X(3.9),y1),(X(2.4),y1),(X(2.4),yk),(X(2.07),yk)]
        z('PVDD','F.Cu',pts,name='PVDD_'+U+('_r' if y0<95 else '_f'))
        for yv in ((87.0,88.62,91.2) if y0<95 else (104.4,106.6,108.5)): v('PVDD',X(3.55),yv)
        gy=(86.2,92.45) if y0<95 else (102.75,108.9)
        z('GND','F.Cu',[(X(2.2),gy[0]),(X(-1.1),gy[0]),(X(-1.1),gy[1]),(X(2.2),gy[1])],name='GND_'+U+('_r' if y0<95 else '_f'))
        for yv in ((86.6,88.62,91.0) if y0<95 else (104.3,106.6,108.5)):
            v('GND',X(1.3),yv); v('GND',X(-0.6),yv)
    # GND pins -> PowerPAD (EP has 24 x 0.2 mm thermal vias in the footprint, SLASEH5D 9.1.3.2.1)
    for n in ('19','24','1','5','14'):
        x,y=pp(U,n); t('GND','F.Cu',[(x,y),(ux+ (0.9 if x>ux else -0.9)*1.6 ,y)],0.3)
    # outputs, bootstrap, speaker legs (router, L1, no vias on OUT/BST)
    caps={'L':[('17','C314','18'),('20','C315','21'),('23','C313','22'),('26','C312','25')],
          'R':[('26','C412','25'),('23','C413','22'),('20','C415','21'),('17','C414','18')]}[side]
    for outp,c,bst in caps:
        bnet=pnet(U,bst); cpad_b=[q for q in geom.pads(c,P) if q['net']==bnet][0]
        j(bnet,pp(U,bst),(cpad_b['x'],cpad_b['y']),w=0.25,res=0.025,clr=0.15,name=bnet.split('/')[-1])
    for outp,c,bst in caps:
        outnet=pnet(U,outp); bnet=pnet(U,bst)
        cpad_out=[q for q in geom.pads(c,P) if q['net']==outnet][0]; cpad_b=[q for q in geom.pads(c,P) if q['net']==bnet][0]
        j(outnet,pp(U,outp),(cpad_out['x'],cpad_out['y']),w=0.4,res=0.025,clr=0.15,name=outnet.split('/')[-1]+'_pin')
        L=[r for r in P if r[0]=='L' and r[1] in '34' and r[1]==U[1] and pnet(r,'1')==outnet][0]
        j(outnet,(cpad_out['x'],cpad_out['y']),pp(L,'1'),w=1.0,res=0.05,clr=0.2,name=outnet.split('/')[-1]+'_toL',margin=2)
        spk=pnet(L,'2'); C=[r for r in P if r[0]=='C' and r[1]==U[1] and r in geom.PIN and spk in geom.PIN[r].values()][0]
        Jc=[r for r in P if r[0]=='J' and r[1]==U[1] and spk in geom.PIN[r].values()][0]
        jn=[k for k,vv in geom.PIN[Jc].items() if vv==spk][0]
        cp=[q for q in geom.pads(C,P) if q['net']==spk][0]; cg=[q for q in geom.pads(C,P) if q['net']=='GND'][0]
        j(spk,pp(L,'2'),(cp['x'],cp['y']),w=1.0,res=0.05,clr=0.2,name=spk.split('/')[-1]+'_cap')
        j(spk,(cp['x'],cp['y']),pp(Jc,jn),w=1.0,res=0.05,clr=0.2,layers=['F.Cu','B.Cu'],via=(0.8,0.4),name=spk.split('/')[-1]+'_conn',margin=3)
        v('GND',cg['x']+s*1.15,cg['y'])
        t('GND','F.Cu',[(cg['x'],cg['y']),(cg['x']+s*1.15,cg['y'])],0.5)
