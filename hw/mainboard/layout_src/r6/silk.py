"""Reference-field placement (native step: refdes visibility/position/rotation/size only).
usage: silk.py board out.json [--apply]
Each visible refdes goes beside its courtyard (above/below at 0 deg, else left/right at 90 deg), 1.0 mm text (0.8 mm fallback, 0.15 stroke),
never over a pad / mask opening / other text / footprint silk / board edge (0.3 mm). Unplaceable -> hidden, grouped for block labels."""
import sys,json,collections,re,pcbnew
bp,outf=sys.argv[1:3]; APPLY='--apply' in sys.argv
b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM; F=pcbnew.FromMM
class R:
    def __init__(s,x0,y0,x1,y1): s.b=(x0,y0,x1,y1)
    def hit(s,o,m=0.0): a=s.b; c=o.b; return not (a[2]+m<=c[0] or c[2]+m<=a[0] or a[3]+m<=c[1] or c[3]+m<=a[1])
def bb(o):
    q=o.GetBoundingBox(); return R(mm(q.GetLeft()),mm(q.GetTop()),mm(q.GetRight()),mm(q.GetBottom()))
ol=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol,True)
def inboard(r):
    x0,y0,x1,y1=r.b; return all(ol.Contains(pcbnew.VECTOR2I(F(x),F(y))) for x,y in ((x0-.3,y0-.3),(x1+.3,y0-.3),(x0-.3,y1+.3),(x1+.3,y1+.3)))
obs={0:[],1:[]}   # per side: (bbox, polyset) of pads (+0.12), footprint silk strokes, board texts, mask openings
def shp(o,layer,m):
    ps=pcbnew.SHAPE_POLY_SET(); o.TransformShapeToPolygon(ps,layer,F(m),F(0.01),pcbnew.ERROR_OUTSIDE); return ps
for f in b.GetFootprints():
    for p in f.Pads():
        for side,L in ((0,pcbnew.F_Cu),(1,pcbnew.B_Cu)):
            if p.IsOnLayer(L): obs[side].append((bb(p),shp(p,L,0.12)))
    for g in f.GraphicalItems():
        l=g.GetLayer()
        if g.GetClass()=='PCB_FIELD': continue
        for side,LL in ((0,(pcbnew.F_SilkS,pcbnew.F_Mask)),(1,(pcbnew.B_SilkS,pcbnew.B_Mask))):
            if l in LL: obs[side].append((bb(g),shp(g,l,0.1)))
for d in b.GetDrawings():
    for side,L in ((0,pcbnew.F_SilkS),(1,pcbnew.B_SilkS)):
        if d.GetLayer()==L: obs[side].append((bb(d),shp(d,L,0.15)))
def collide(t,side):
    tp=pcbnew.SHAPE_POLY_SET(); tp.NewOutline()
    x0,y0,x1,y1=t.b
    for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)): tp.Append(F(x),F(y))
    for r,ps in obs[side]:
        if not t.hit(r,0.2): continue
        q=pcbnew.SHAPE_POLY_SET(tp); q.BooleanIntersection(ps)
        if q.OutlineCount(): return True
    return False
placed={0:[],1:[]}; res=[]; hidden=[]
FPS=sorted(b.GetFootprints(),key=lambda f:(-(f.GetReference()[0] in 'UJQLDY' or f.GetReference().startswith('SW')),mm(f.GetY()),mm(f.GetX())))   # ICs/connectors/inductors first
for f in FPS:
    ref=f.Reference(); r=f.GetReference()
    if f.IsBoardOnly() or r.startswith(('BRD','TL','H')) or not ref.IsVisible(): continue
    side=1 if f.IsFlipped() else 0
    cy=f.GetCourtyard(pcbnew.B_CrtYd if side else pcbnew.F_CrtYd)
    c=R(*[mm(v) for v in (cy.BBox().GetLeft(),cy.BBox().GetTop(),cy.BBox().GetRight(),cy.BBox().GetBottom())]) if cy.OutlineCount() else bb(f)
    x0,y0,x1,y1=c.b; xc=(x0+x1)/2; yc=(y0+y1)/2; done=False
    for h in (1.0,0.8):
        ref.SetTextSize(pcbnew.VECTOR2I(F(h),F(h))); ref.SetTextThickness(F(0.15))
        cands=[(xc,yc,0),(xc,yc,90)]
        big=f.GetReference()[0] in 'UJQLDY' or f.GetReference().startswith('SW')
        for d in ((0.15,0.6,1.1,1.6,2.2,2.8) if big else (0.15,0.6,1.1)):
            for sh in ((0,-0.6,0.6,-1.2,1.2,-2,2,-3,3) if big else (0,-0.6,0.6,-1.2,1.2)):
                cands+=[(xc+sh,y0-h/2-d,0),(xc+sh,y1+h/2+d,0),(x0-h/2-d,yc+sh,90),(x1+h/2+d,yc+sh,90)]
        for x,y,a in cands:
            ref.SetTextAngleDegrees(a); ref.SetPosition(pcbnew.VECTOR2I(F(x),F(y)))
            t=bb(ref)
            if not inboard(t) or any(t.hit(o,0.15) for o in placed[side]) or collide(t,side): continue
            placed[side].append(t); res.append(dict(ref=r,x=round(x,3),y=round(y,3),angle=a,size=h,visible=True)); done=True; break
        if done: break
    if not done:
        ref.SetVisible(False); hidden.append(r); res.append(dict(ref=r,visible=False))
json.dump(res,open(outf,'w'),indent=0)
grp=collections.defaultdict(list)
for r in hidden: grp[re.match(r'[A-Z]+\d?',r).group(0)].append(r)
print('placed',sum(1 for x in res if x['visible']),'hidden',len(hidden)); print(dict(grp))
if APPLY: pcbnew.SaveBoard(bp,b)
