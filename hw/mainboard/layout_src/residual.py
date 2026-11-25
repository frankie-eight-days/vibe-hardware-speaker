"""Route what Freerouting left unrouted: for each KiCad-reported unconnected pair (signal nets), A* on F.Cu/B.Cu(/In2.Cu)
between the two item positions. Writes spec_residual.json (replayed via Konnect)."""
import sys, json, re, pcbnew
sys.path.insert(0,'.')
import arouter
bp,drcj=sys.argv[1:3]
b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM
d=json.load(open(drcj)); T=[];V=[];fail=[]
EDGE=[[(0,0),(300,0),(300,75.6),(0,75.6)],[(0,120.4),(300,120.4),(300,200),(0,200)],[(0,0),(60.6,0),(60.6,200),(0,200)],[(239.4,0),(300,0),(300,200),(239.4,200)],
      [(0,0),(63.3,0),(63.3,200),(0,200)],[(0,0),(75.3,0),(75.3,86),(0,86)],[(0,115),(75.3,115),(75.3,200),(0,200)]]
for u in d['unconnected_items']:
    it=u['items']; m=re.search(r'\[([^\]]+)\]',it[0]['description'])
    if not m: continue
    net=m.group(1)
    if net=='GND': continue
    a=(round(it[0]['pos']['x'],4),round(it[0]['pos']['y'],4)); c=(round(it[1]['pos']['x'],4),round(it[1]['pos']['y'],4))
    def lay(desc): return 'B.Cu' if 'on B.Cu' in desc else ('In2.Cu' if 'In2.Cu' in desc else 'F.Cu')
    la,lc=lay(it[0]['description']),lay(it[1]['description'])
    if 'Zone' in it[0]['description'] or 'Zone' in it[1]['description']: fail.append((net,'zone')); continue
    m3=3; win=(min(a[0],c[0])-m3,min(a[1],c[1])-m3,max(a[0],c[0])+m3,max(a[1],c[1])+m3)
    area=(win[2]-win[0])*(win[3]-win[1]); res=0.05 if area<400 else 0.1
    R=arouter.Router(b,win,res=res,layers=('F.Cu','B.Cu'))
    w=0.2; clr=0.2 if net in ('/I2S_BCLK','/mcu/LCD_SCLK','/mcu/PDM_CLK','/mcu/I2S_BCLK_MCU','/mcu/IO26_R','/mcu/IO18_R','/mcu/IO32_R') else 0.15
    out=R.route(net,a,c,width=w,clr=clr,layers=['F.Cu','B.Cu'],via=(0.45,0.2),keep={l:EDGE for l in ('F.Cu','In1.Cu','In2.Cu','B.Cu')},start_layer=la if la!='In2.Cu' else 'F.Cu',end_layers=[lc] if lc!='In2.Cu' else None,maxit=4000000)
    if not out: fail.append((net,a,c)); continue
    tt,vv=out; T+=tt; V+=vv
    for t in tt:
        tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2']))); tr.SetWidth(F(w)); tr.SetLayer(arouter.LAY[t['layer']]); tr.SetNet(b.FindNet(net)); b.Add(tr)
    for v in vv:
        vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(0.45)); vi.SetDrill(F(0.2)); vi.SetNet(b.FindNet(net)); b.Add(vi)
    print('routed',net,len(tt),len(vv),flush=True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=T,vias=V,zones=[]),open('spec_residual.json','w'))
print('residual tracks',len(T),'vias',len(V),'fail',fail)
