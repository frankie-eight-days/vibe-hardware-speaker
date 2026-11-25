"""Criterion 2: every signal segment on L1/L3/L4 lies over unbroken filled copper of ONE net on the adjacent plane layer
(L1->L2, L3->L2 (also reports L4 side), L4->L3). Plane fills are closed by 0.6 mm per net so via antipads don't count as breaks.
Also: fast-net vias (layer changes) without a GND via within 2 mm. usage: refcheck.py board [json_out]"""
import sys,json,re,collections,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM; F=pcbnew.FromMM
POW=re.compile(r'(^GND$|PVDD|VSYS|VBUS|VBAT_PACK|BATT_N|PACK_P|CHG_BAT$|PROT_D|CHG_PMID|\+3V3|_SW$|SW1|SW2|SPK_|_OUT[AB]_)')
FAST=re.compile(r'(I2S|LCD_|PDM_|USB_D|IO18_R|IO26_R|IO32_R|IO23_R)')
CS=pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS
def fills(layer):
    d={}
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer) or not z.HasFilledPolysForLayer(layer): continue
        fp=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(layer)); fp.Unfracture(); o=pcbnew.SHAPE_POLY_SET(); hb=pcbnew.SHAPE_POLY_SET()
        for i in range(fp.OutlineCount()):
            o.AddOutline(fp.Outline(i))
            for h in range(fp.HoleCount(i)):
                hh=fp.Hole(i,h); bb=hh.BBox()
                if max(mm(bb.GetWidth()),mm(bb.GetHeight()))>2.0: hb.AddOutline(hh)   # real splits; small holes = via/pad antipads
        o.BooleanSubtract(hb)
        p=d.setdefault(z.GetNetname(),pcbnew.SHAPE_POLY_SET()); p.BooleanAdd(o)
    return d
PL={pcbnew.F_Cu:fills(pcbnew.In1_Cu),pcbnew.In2_Cu:fills(pcbnew.In1_Cu),pcbnew.B_Cu:fills(pcbnew.In2_Cu)}
L4ref=fills(pcbnew.B_Cu)
OWNV={}
for v in b.GetTracks():
    if v.GetClass()=='PCB_VIA': OWNV.setdefault(v.GetNetname(),[]).append((v.GetX(),v.GetY()))
for p in b.GetPads():
    if p.GetDrillSizeX()>0: OWNV.setdefault(p.GetNetname(),[]).append((p.GetX(),p.GetY()))
bad=collections.Counter(); badlen=collections.Counter(); tot=collections.Counter(); out=[]; l3_l4side=0
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA' or POW.search(t.GetNetname()): continue
    l=t.GetLayer()
    if l not in PL: continue
    sp=pcbnew.SHAPE_POLY_SET(); t.TransformShapeToPolygon(sp,l,0,F(0.005),pcbnew.ERROR_INSIDE)
    for e in (t.GetStart(),t.GetEnd()):   # the layer transition itself (own via/pad) is not a referenced run
        if any(abs(e.x-vx)<F(0.02) and abs(e.y-vy)<F(0.02) for vx,vy in OWNV.get(t.GetNetname(),())):
            c=pcbnew.SHAPE_POLY_SET(); c.NewOutline()
            import math
            for k in range(24): c.Append(int(e.x+F(0.75)*math.cos(k*math.pi/12)),int(e.y+F(0.75)*math.sin(k*math.pi/12)))
            sp.BooleanSubtract(c)
    A=sp.Area()
    if A<=0: continue
    tot[l]+=1; ok=False; bestr=None
    for n,p in PL[l].items():
        r=pcbnew.SHAPE_POLY_SET(sp); r.BooleanSubtract(p)
        ua=sum(pcbnew.SHAPE_POLY_SET(r.Outline(i)).Area() for i in range(r.OutlineCount()) if min(r.Outline(i).BBox().GetWidth(),r.Outline(i).BBox().GetHeight())>F(0.08))
        if ua<2e9: ok=True; break   # <0.002 mm^2 uncovered (slivers <0.08 mm ignored)
        if bestr is None or r.Area()<bestr[1]: bestr=(n,r.Area(),r)
    if not ok:
        bad[l]+=1; badlen[l]+=mm(t.GetLength()); out.append(dict(net=t.GetNetname(),layer=t.GetLayerName(),x1=round(mm(t.GetStart().x),2),y1=round(mm(t.GetStart().y),2),x2=round(mm(t.GetEnd().x),2),y2=round(mm(t.GetEnd().y),2),len=round(mm(t.GetLength()),2),bestnet=bestr[0][-10:] if bestr else '',unc=[(round(mm(bestr[2].Outline(i).BBox().GetX()),2),round(mm(bestr[2].Outline(i).BBox().GetY()),2),round(mm(bestr[2].Outline(i).BBox().GetWidth()),2),round(mm(bestr[2].Outline(i).BBox().GetHeight()),2)) for i in range(min(bestr[2].OutlineCount(),3))] if bestr else []))
    if l==pcbnew.In2_Cu:
        if not any((lambda r:(r.BooleanSubtract(p),r.Area())[1])(pcbnew.SHAPE_POLY_SET(sp))<2e9 for p in L4ref.values()): l3_l4side+=1
gv=[(t.GetX(),t.GetY()) for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
gv+=[(p.GetX(),p.GetY()) for p in b.GetPads() if p.GetNetname()=='GND' and p.GetDrillSizeX()>0]
fastv=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and FAST.search(t.GetNetname())]
nost=[dict(net=v.GetNetname(),x=round(mm(v.GetX()),2),y=round(mm(v.GetY()),2)) for v in fastv if not any((v.GetX()-x)**2+(v.GetY()-y)**2<=F(2.0)**2 for x,y in gv)]
nm={pcbnew.F_Cu:'L1',pcbnew.In2_Cu:'L3',pcbnew.B_Cu:'L4'}
print('segments checked',{nm[k]:v for k,v in tot.items()},'violations',{nm[k]:v for k,v in bad.items()},'len_mm',{nm[k]:round(v,1) for k,v in badlen.items()})
print('L3 segments whose L4 side is not one solid net (info)',l3_l4side)
print('fast-net vias',len(fastv),'without GND via <=2 mm',len(nost))
if len(sys.argv)>2: json.dump(dict(viol=out,nostitch=nost),open(sys.argv[2],'w'),indent=0)
