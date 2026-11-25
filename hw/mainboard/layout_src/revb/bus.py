"""Deliberate corridor routing of the long nets (rev B): A* on L1/L3/L4, L3 only inside the corridor, L4 only over solid L3.
usage: bus.py board k3.npy k4.npy spec_out.json [job names...]"""
import sys,json,time,numpy as np,pcbnew
SP='/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/revb'
sys.path.insert(0,SP); import busrt, arouter
bp,k3f,k4f,outf=sys.argv[1:5]; only=set(a for a in sys.argv[5:] if not a.startswith('--'))
b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM; mm=pcbnew.ToMM
M={'In2.Cu':np.load(k3f),'B.Cu':np.load(k4f)}
K1=np.zeros_like(M['In2.Cu'])   # L1: nothing under inductors (switch-node / output chokes)
for f in b.GetFootprints():
    if f.GetReference().startswith('L'):
        bb=f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False,False)
        x0,y0,x1,y1=mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())
        K1[max(int((y0-73)/0.25),0):int((y1-73)/0.25)+1,max(int((x0-60)/0.25),0):int((x1-60)/0.25)+1]=True
M['F.Cu']=K1
# board edge (0.5 mm) and antenna keep-out on every layer
from matplotlib.path import Path
xs=np.arange(60,240,0.25)+0.125; ys=np.arange(73,121,0.25)+0.125; GX,GY=np.meshgrid(xs,ys); PP=np.c_[GX.ravel(),GY.ravel()]
ol=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol,True); ol.Deflate(F(0.55),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,F(0.01))
INB=np.zeros(GX.shape,bool)
for i in range(ol.OutlineCount()):
    o=ol.Outline(i); INB|=Path([(mm(o.CPoint(k).x),mm(o.CPoint(k).y)) for k in range(o.PointCount())]).contains_points(PP).reshape(GX.shape)
ANT=(GX<63.3)|((GX<75.3)&((GY<86)|(GY>115)))
OUT=~INB|ANT
for k in ('F.Cu','In2.Cu','B.Cu'): M[k]=M[k]|OUT
M['F.Cu']=M['F.Cu']|((GY<76.4)&(GX>63))   # no L1 signal between the edge fence (Y76.7) and the rear edge
def raster_seg(Mk,x1,y1,x2,y2,r):
    n=int(max(abs(x2-x1),abs(y2-y1))/0.1)+1
    for k in range(n+1):
        x=x1+(x2-x1)*k/n; y=y1+(y2-y1)*k/n
        j0=int((y-r-73)/0.25); j1=int((y+r-73)/0.25)+1; i0=int((x-r-60)/0.25); i1=int((x+r-60)/0.25)+1
        jj,ii=np.mgrid[max(j0,0):max(j1,0),max(i0,0):max(i1,0)]
        if jj.size: Mk[jj,ii]|=((60+ii*0.25+0.125-x)**2+(73+jj*0.25+0.125-y)**2)<=r*r
L2V=np.zeros_like(K1)
for z in b.Zones():
    if z.GetZoneName()!='L2_GND_SOLID': continue
    fp=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(pcbnew.In1_Cu)); fp.Unfracture()
    for i in range(fp.OutlineCount()):
        for h in range(fp.HoleCount(i)):
            hh=fp.Hole(i,h); bb=hh.BBox()
            if max(mm(bb.GetWidth()),mm(bb.GetHeight()))>2.0:
                L2V|=Path([(mm(hh.CPoint(k).x),mm(hh.CPoint(k).y)) for k in range(hh.PointCount())]).contains_points(PP).reshape(GX.shape)
L2V=L2V|np.roll(L2V,1,0)|np.roll(L2V,-1,0)|np.roll(L2V,1,1)|np.roll(L2V,-1,1)
MF0=M['F.Cu'].copy(); M['F.Cu']|=L2V; M['In2.Cu']|=L2V
SIGRE=__import__('re').compile(r'(^GND$|PVDD|VSYS|VBUS|VBAT_PACK|BATT_N|PACK_P|CHG_BAT$|PROT_D|CHG_PMID|\+3V3|SW)')
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA' or SIGRE.search(t.GetNetname()): continue
    if t.GetLayer() in (pcbnew.B_Cu,pcbnew.In2_Cu):
        raster_seg(M['In2.Cu' if t.GetLayer()==pcbnew.B_Cu else 'B.Cu'],mm(t.GetStart().x),mm(t.GetStart().y),mm(t.GetEnd().x),mm(t.GetEnd().y),0.6)
for z in b.Zones():
    if z.GetZoneName()=='L3_GND_REVB_CORR': z.SetAssignedPriority(1); ZC=z
def pad(ref,num):
    f=b.FindFootprintByReference(ref)
    for p in f.Pads():
        if p.GetNumber()==num: return p
CLK=('LCD_SCLK','PDM_CLK','I2S_BCLK')
J=[ # name, net, src, dst   (src/dst: ('pad',ref,num) or ('via',x,y))
('BCLK_R','/I2S_BCLK',('pad','U301','7'),('pad','U401','7')),
('LRCK_R','/I2S_LRCK',('pad','U301','6'),('pad','U401','6')),
('SDIN_R','/I2S_SDIN',('pad','U301','8'),('pad','U401','8')),
('SCL','/I2C_SCL',('pad','R105','2'),('pad','U401','11')),
('SDA','/I2C_SDA',('pad','R104','2'),('pad','U401','10')),
('PDN','/AMP_PDN',('pad','U101','14'),('pad','U401','12')),
('FLT_R','/AMPR_FAULT_N',('pad','R120','1'),('pad','U401','3')),
('INT','/charger/CHG_INT',('pad','R106','2'),('pad','U701','21')),
('SCLK','/mcu/LCD_SCLK',('via',86.0,85.8),('pad','J501','5')),
('MOSI','/mcu/LCD_MOSI',('pad','R114','2'),('pad','J501','7')),
('CS','/mcu/LCD_CS',('pad','R115','2'),('pad','J501','8')),
('DC','/mcu/LCD_DC',('pad','R116','2'),('pad','J501','9')),
('BL','/mcu/LCD_BL',('pad','R117','2'),('pad','J501','10')),
('PCLK','/mcu/PDM_CLK',('pad','R118','2'),('pad','J501','12')),
('PDAT','/mcu/PDM_DATA',('pad','U101','9'),('pad','J501','14')),
('ENCA','/mcu/ENC_A',('pad','U101','6'),('pad','R501','2')),
('ENCB','/mcu/ENC_B',('pad','U101','7'),('pad','R502','2')),
('ENCSW','/mcu/ENC_SW',('pad','U101','26'),('pad','R503','2')),
('BTN','/mcu/BTN_ADC',('pad','U101','5'),('pad','R504','2')),
('PDSCL','/usb_power/PD_SCL',('pad','Q601','2'),('pad','U603','2')),
('PDSDA','/usb_power/PD_SDA',('pad','Q602','2'),('pad','U603','3')),
('TS','/battery/BAT_TS',('pad','U701','16'),('pad','JP803','2')),
('BEN','/mcu/BOOST_EN',('via',80.7,87.9),('via',124.4,100.5)),
('TXD','/mcu/ESP_TXD0',('pad','U101','35'),('pad','R204','2')),
('RXD','/mcu/ESP_RXD0',('pad','U101','34'),('pad','R203','2')),
('DTR','/usb_uart/DTR_N',('pad','U201','13'),('pad','Q202','2')),
('RTS','/usb_uart/RTS_N',('pad','U201','14'),('pad','R202','1')),
('TRIM','/mcu/PVDD_TRIM',('pad','U101','10'),('pad','R908','1')),
]
T=[];V=[];fails=[];LOG=[]
LC={'F.Cu':2.0,'In2.Cu':1.0,'B.Cu':1.8}
JOBF=[a.split('=',1)[1] for a in sys.argv if a.startswith('--jobs=')]
MARG=(6,12)
if JOBF: J=[tuple(x) for x in json.load(open(JOBF[0]))]; MARG=(3,3); only=set()
else: JD={j[0]:j for j in J}; J=[JD[k] for k in ['BCLK_R','SDIN_R','LRCK_R','SCL','SDA','INT','FLT_R','PDN','TS','PDAT','SCLK','MOSI','CS','DC','BL','PCLK','ENCA','ENCB','ENCSW','BTN','PDSCL','PDSDA','RTS','DTR','TXD','RXD','BEN','TRIM']]
TODO=list(J)
NT=int(([a.split('=')[1] for a in sys.argv if a.startswith('--tiers=')] or ['3'])[0])
for TIER,SPACING in ((0,1.3),(1,0.0),(2,0.0))[:NT]:
  if TIER==2: M['F.Cu']=MF0|(M['F.Cu']&~L2V)
  RETRY=[]
  for name,net,s,d in TODO:
        if only and name not in only: continue
        t0=time.time(); ends=[]; novia=[]
        for e in (s,d):
            if e[0]=='pad':
                p=pad(e[1],e[2]); ends.append(((mm(p.GetX()),mm(p.GetY())),['F.Cu'] if not p.IsOnLayer(pcbnew.B_Cu) else ['B.Cu'] if not p.IsOnLayer(pcbnew.F_Cu) else ['F.Cu','B.Cu']))
                novia.append(arouter.poly_pts(p.GetEffectivePolygon(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu,pcbnew.ERROR_INSIDE)))
            elif e[0]=='xy': ends.append(((e[1],e[2]),e[3]))
            else: ends.append(((e[1],e[2]),['F.Cu','In2.Cu','B.Cu']))
        (a,la),(c,lc)=ends
        MG=MARG if (abs(a[0]-c[0])+abs(a[1]-c[1]))<18 else (6,12)
        win=(max(min(a[0],c[0])-MG[0],60.2),max(min(a[1],c[1])-MG[1],75.2),min(max(a[0],c[0])+MG[0],239.8),min(max(a[1],c[1])+MG[1],120.8))
        res=0.05 if (name.startswith('PD') or TIER>=1) else 0.1
        R=busrt.BusRouter(b,win,res,('F.Cu','In2.Cu','B.Cu'),M)
        R.soft=[(a[0],a[1],1.6),(c[0],c[1],1.6)] if TIER>=1 else []
        # forbid vias inside/near the endpoint pads (no via-in-pad)
        keepv=[P for pl in novia for P in pl]
        cl=0.17
        w=0.15 if (name.startswith('PD') or TIER>=1) else (0.3 if net=='+3V3' else 0.2)
        cl=0.155 if (name.startswith('PD') or TIER>=1) else cl
        # via keep: emulate by adding pad polys (grown) to a temporary via-only mask
        def vmask(R):
            Bm=np.zeros(R.X.shape,bool)
            from matplotlib.path import Path
            for P in keepv:
                Pp=Path(P); ins=Pp.contains_points(np.c_[R.X.ravel(),R.Y.ravel()]).reshape(R.X.shape)
                d=np.full(R.X.shape,1e9)
                for q1,q2 in zip(P,np.roll(P,-1,0)): d=np.minimum(d,arouter.seg_dist(R.X,R.Y,q1,q2))
                Bm|=ins|(d<0.25+0.15)
            return Bm
        VM=vmask(R)
        for t in b.GetTracks():
            if t.GetClass()!='PCB_VIA' or t.GetNetname()==net: continue
            vx,vy=mm(t.GetX()),mm(t.GetY())
            if win[0]-2<vx<win[2]+2 and win[1]-2<vy<win[3]+2: VM|=((R.X-vx)**2+(R.Y-vy)**2)<SPACING**2
        orig=arouter.Router.blocked
        def bl2(self,ln,netn,r,extra=(),_o=orig): 
            B=_o(self,ln,netn,r,extra)
            return B|VM if abs(r-(0.25+cl))<1e-9 else B
        arouter.Router.blocked=bl2
        out=R.route2(net,a,c,width=w,clr=cl,via=(0.5,0.25),via_cost=40,lcost=LC,start_layers=la,end_layers=lc)
        arouter.Router.blocked=orig
        if not out: RETRY.append((name,net,s,d)); print('defer',name,TIER,flush=True); continue
        tt,vv=out
        for t in tt:
            tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(w)); tr.SetLayer(arouter.LAY[t['layer']]); tr.SetNet(b.FindNet(net)); tr.SetLocked(True); b.Add(tr)
        for v in vv:
            vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(0.5)); vi.SetDrill(F(0.25)); vi.SetNet(b.FindNet(net)); vi.SetLocked(True); b.Add(vi)
        T+=tt; V+=vv
        for t in tt:
            if t['layer'] in ('In2.Cu','B.Cu'): raster_seg(M['B.Cu' if t['layer']=='In2.Cu' else 'In2.Cu'],t['x1'],t['y1'],t['x2'],t['y2'],0.6)
        L={}; [L.__setitem__(t['layer'],L.get(t['layer'],0)+((t['x2']-t['x1'])**2+(t['y2']-t['y1'])**2)**0.5) for t in tt]
        print('ok',name,len(tt),'segs',len(vv),'vias',{k:round(x,1) for k,x in L.items()},round(time.time()-t0,1),'s',flush=True)

  TODO=RETRY
  print('tier',TIER,'deferred',[r[0] for r in RETRY],flush=True)
fails=[r[0] for r in TODO]
ZC.SetAssignedPriority(2)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=T,vias=V),open(outf,'w')); print('fails',fails)
