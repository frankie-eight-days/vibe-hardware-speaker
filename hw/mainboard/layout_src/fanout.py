"""Plane fan-out for pads of plane nets that the pours do not reach: put a via next to the pad (inside the right plane region)
and a short stub, both checked with the A* router's clearance model. Writes spec_fanout.json."""
import sys, json, re, math, importlib, pcbnew
sys.path.insert(0,'.')
import arouter
from matplotlib.path import Path
bp=sys.argv[1]; drcjson=sys.argv[2]
b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM
mods=[importlib.import_module(m) for m in ('blk_planes','blk_charger','blk_batt','blk_usb')]
REG={'+3V3':[('In2.Cu','L3_3V3')],'/amp_left/PVDD':[('In2.Cu','L3_PVDD')],'/charger/VSYS':[('In2.Cu','L3_VSYS')],
     '/charger/VBUS':[('B.Cu','USB_VBUS_L4')],'/battery/VBAT_PACK':[('In2.Cu','VBAT_PACK_In2')],'/charger/CHG_BAT':[('B.Cu','CHG_BAT_L4')]}
polys={z['name']:z['pts'] for m in mods for z in m.Z if z.get('name')}
d=json.load(open(drcjson)); todo=set()
for u in d['unconnected_items']:
    for it in u['items']:
        m=re.match(r'(?:PTH )?[Pp]ad (\S+) \[([^\]]+)\] of (\S+)',it['description'])
        if m and m.group(2) in REG: todo.add((m.group(3),m.group(1),m.group(2)))
T=[];V=[];fail=[]
for ref,num,net in sorted(todo):
    fp=b.FindFootprintByReference(ref); pad=[p for p in fp.Pads() if p.GetNumber()==num][0]
    px,py=pcbnew.ToMM(pad.GetPosition().x),pcbnew.ToMM(pad.GetPosition().y)
    side='B.Cu' if fp.IsFlipped() else 'F.Cu'
    R=arouter.Router(b,(px-4,py-4,px+4,py+4),res=0.05,layers=(side,))
    vr=0.3+0.2; Bv=None
    for l in R.all:
        bl=R.blocked(l,net,vr); Bv=bl if Bv is None else (Bv|bl)
    regions=[Path(polys[nm]) for _,nm in REG[net] if nm in polys]
    best=None
    for rad in (0.9,1.2,1.5,1.9,2.4,3.0):
        for k in range(16):
            a=2*math.pi*k/16; x=px+rad*math.cos(a); y=py+rad*math.sin(a)
            i=int(round((x-R.x0)/R.res)); jj=int(round((y-R.y0)/R.res))
            if not(0<=i<R.nx and 0<=jj<R.ny) or Bv[jj,i]: continue
            if not(61.2<x<238.8 and 76.2<y<119.8): continue
            if not any(r.contains_point((x,y)) for r in regions): continue
            # inset: via must be >=0.6 mm inside the region outline
            if not any(r.contains_point((x+dx,y+dy)) for r in regions for dx,dy in ((0.6,0),(-0.6,0),(0,0.6),(0,-0.6))): continue
            res=R.route(net,(px,py),(round(x,3),round(y,3)),width=0.3,clr=0.2,layers=[side],start_layer=side,maxit=200000)
            if res: best=(x,y,res); break
        if best: break
    if not best: fail.append((ref,num,net)); continue
    x,y,(tt,vv)=best
    T+=tt; V.append(dict(net=net,x=round(x,3),y=round(y,3),size=0.6,drill=0.3))
    # add to board so later fan-outs see them
    for t in tt:
        tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(t['w'])); tr.SetLayer(arouter.LAY[t['layer']]); tr.SetNet(b.FindNet(net)); b.Add(tr)
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(x),F(y))); vi.SetWidth(F(0.6)); vi.SetDrill(F(0.3)); vi.SetNet(b.FindNet(net)); b.Add(vi)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=T,vias=V,zones=[]),open('spec_fanout.json','w'))
print('fanout ok',len(V),'fail',fail)
