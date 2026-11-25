"""Export DSN from a prepped scratch board, reduce to open connections, L2 plane, L3 corridor-only + L4 split/corridor keep-outs.
usage: dsn.py board.kicad_pcb drc.json out.dsn [res_mm]"""
import sys,json,re,subprocess,numpy as np,pcbnew
from matplotlib.path import Path
SP='/private/tmp/claude-501/-Users-frankwalsh-Documents-vibecoding/8f7148fa-1ea7-42b7-910f-60a1668ad40c/scratchpad/revb'
sys.path.insert(0,SP); import design as D
bp,drcj,out=sys.argv[1:4]; R=0.25; L3POWER='--l3power' in sys.argv
b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM
raw=out.replace('.dsn','_raw.dsn'); ok=pcbnew.ExportSpecctraDSN(b,raw); print('export',ok)
import reduce2
dsn,kept,full=reduce2.reduce(drcj,open(raw).read()); print('nets kept',len(kept),'full-pin nets',sorted(full))
dsn=re.sub(r'    \(plane \+3V3 \(polygon In2\.Cu[^)]*\)\)\n','',dsn)
dsn=dsn.replace('(layer In1.Cu\n      (type signal)','(layer In1.Cu\n      (type power)')
# class rules: KiCad exports every clearance as the board minimum; restore class clearances (+10 um margin), thin the power classes for the small-signal branches
CR={'kicad_default':(200,160),'SWITCH':(400,260),'VBUS':(500,210),'PWR_3V3':(500,160),'SPEAKER':(1000,210),'USB_DIFF':(280,210),'PWR_BATT':(500,210),'PVDD':(500,210),'CLOCK':(200,260)}
def fixcls(m):
    name=m.group(1).split(',')[0]; w,c=CR.get(name,(200,160))
    blk=re.sub(r'\(width \d+\)',f'(width {w})',m.group(0)); blk=re.sub(r'\(clearance \d+\)',f'(clearance {c})',blk)
    return blk.replace('(use_via "Via[0-3]_600:300_um")','(use_via "Via[0-3]_500:250_um" "Via[0-3]_600:300_um")')
dsn=re.sub(r'    \(class (\S+)[^\n]*\n(?:      [^\n]*\n)*?    \)\n',fixcls,dsn)
# raster grid
x0,y0,x1,y1=60.0,73.0,240.0,121.0
xs=np.arange(x0,x1,R)+R/2; ys=np.arange(y0,y1,R)+R/2; X,Y=np.meshgrid(xs,ys); P=np.c_[X.ravel(),Y.ravel()]
def pmask(poly): return Path(poly).contains_points(P).reshape(X.shape)
ol=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol,True)
board=np.zeros(X.shape,bool)
for i in range(ol.OutlineCount()):
    o=ol.Outline(i); board|=pmask([(mm(o.CPoint(k).x),mm(o.CPoint(k).y)) for k in range(o.PointCount())])
def shift_or(M,r):
    k=int(np.ceil(r/R)); O=M.copy()
    for dj in range(-k,k+1):
        for di in range(-k,k+1):
            if (dj*dj+di*di)*R*R<=r*r: O|=np.roll(np.roll(M,dj,0),di,1)
    return O
def erode(M,r): return ~shift_or(~M,r)
# through items (pads with drill, vias): keep-outs must not cover them
thr=np.zeros(X.shape,bool)
pts=[(mm(t.GetX()),mm(t.GetY()),mm(t.GetWidth(pcbnew.F_Cu))/2) for t in b.GetTracks() if t.GetClass()=='PCB_VIA']
pts+=[(mm(p.GetX()),mm(p.GetY()),max(mm(p.GetSizeX()),mm(p.GetSizeY()))/2) for p in b.GetPads() if p.GetDrillSizeX()>0]
for x,y,r in pts:
    j0=int((y-r-0.5-y0)/R); j1=int((y+r+0.5-y0)/R)+1; i0=int((x-r-0.5-x0)/R); i1=int((x+r+0.5-x0)/R)+1
    sub=(X[j0:j1,i0:i1]-x)**2+(Y[j0:j1,i0:i1]-y)**2<(r+0.35)**2; thr[j0:j1,i0:i1]|=sub
corr=np.zeros(X.shape,bool)
for c in D.CORR: corr|=pmask(c)
K3=board&~corr&~thr
# L4: allowed only over L3 copper of one net (per-net closing fills antipads), never over the L3 corridor
L3=pcbnew.In2_Cu; nets={}
for z in b.Zones():
    if z.GetIsRuleArea() or not z.IsOnLayer(L3) or not z.HasFilledPolysForLayer(L3): continue
    fp=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(L3)); fp.Unfracture(); m=nets.setdefault(z.GetNetname(),np.zeros(X.shape,bool))
    for i in range(fp.OutlineCount()):
        o=fp.Outline(i); m|=pmask([(mm(o.CPoint(k).x),mm(o.CPoint(k).y)) for k in range(o.PointCount())])
        for h in range(fp.HoleCount(i)):
            hh=fp.Hole(i,h); bb=hh.BBox()
            if max(mm(bb.GetWidth()),mm(bb.GetHeight()))>2.0: m&=~pmask([(mm(hh.CPoint(k).x),mm(hh.CPoint(k).y)) for k in range(hh.PointCount())])
allowed=np.zeros(X.shape,bool)
for n,m in nets.items(): allowed|=erode(m,0.3)
pcorr=np.zeros(X.shape,bool)
for c in (D.REAR,D.DIP): pcorr|=pmask(c)
K4=board&(~allowed|pcorr)&~thr
# bottom test pads inside the corridor: L4 may stub to them, L3 lanes keep 1.6 mm away
tpd=np.zeros(X.shape,bool)
for p in b.GetPads():
    if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu):
        x,y=mm(p.GetX()),mm(p.GetY()); tpd|=(X-x)**2+(Y-y)**2<1.6**2
np.save(out.replace('.dsn','_k4.npy'),K4); np.save(out.replace('.dsn','_k3.npy'),K3); np.save(out.replace('.dsn','_k3raw.npy'),(board&~corr)|tpd); np.save(out.replace('.dsn','_k4raw.npy'),board&(~allowed|(pcorr&~tpd)))
def rects(M):
    runs={}
    for j in range(M.shape[0]):
        row=M[j]; d=np.diff(np.r_[0,row.astype(int),0]); st=np.where(d==1)[0]; en=np.where(d==-1)[0]
        for a,e in zip(st,en): runs.setdefault((a,e),[]).append(j)
    out=[]
    for (a,e),js in runs.items():
        js=sorted(js); s=js[0]; p=js[0]
        for j in js[1:]+[None]:
            if j is not None and j==p+1: p=j; continue
            out.append((x0+a*R,y0+s*R,x0+e*R,y0+(p+1)*R)); 
            if j is not None: s=p=j
    return out
def kos(M,layer,tag):
    s=''
    for k,(a,bq,c,d) in enumerate(rects(M)):
        s+=f'    (wire_keepout "{tag}{k}" (polygon {layer} 0 {a*1000:.0f} {-bq*1000:.0f} {c*1000:.0f} {-bq*1000:.0f} {c*1000:.0f} {-d*1000:.0f} {a*1000:.0f} {-d*1000:.0f}))\n'
    return s
# L4 must not run over L3 signal tracks either
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA' and t.GetLayer()==pcbnew.In2_Cu:
        x1,y1,x2,y2=mm(t.GetStart().x),mm(t.GetStart().y),mm(t.GetEnd().x),mm(t.GetEnd().y); n=int(max(abs(x2-x1),abs(y2-y1))/0.1)+1
        for k in range(n+1):
            x=x1+(x2-x1)*k/n; y=y1+(y2-y1)*k/n
            j0=max(int((y-0.8-y0)/R),0); j1=int((y+0.8-y0)/R)+1; i0=max(int((x-0.8-x0)/R),0); i1=int((x+0.8-x0)/R)+1
            K4[j0:j1,i0:i1]|=((X[j0:j1,i0:i1]-x)**2+(Y[j0:j1,i0:i1]-y)**2<0.6**2)&~thr[j0:j1,i0:i1]
np.save(out.replace('.dsn','_k4.npy'),K4)
K4r=np.load(out.replace('.dsn','_k4raw.npy'))
for t in b.GetTracks():
    pass
k3='' if L3POWER else kos(K3,'In2.Cu','k3_'); k4=kos(K4,'B.Cu','k4_')
if L3POWER: dsn=dsn.replace('(layer In2.Cu\n      (type signal)','(layer In2.Cu\n      (type power)')
i=dsn.index('    (via ')
dsn=dsn[:i]+k3+k4+dsn[i:]
dsn=dsn.replace('      (width 200)\n      (clearance 127)\n      (clearance 31.75 (type smd_smd))','      (width 200)\n      (clearance 160)\n      (clearance 31.75 (type smd_smd))',1)
open(out,'w').write(dsn)
print('keepouts L3',k3.count('wire_keepout'),'L4',k4.count('wire_keepout'),'L3 nets',list(nets))
