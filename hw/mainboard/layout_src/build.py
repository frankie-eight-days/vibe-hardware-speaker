"""OFFLINE builder: base board + block specs (manual tracks/vias, router jobs, zones) -> scratch board, filled, saved.
Writes the combined replay spec (spec_all.json) that is later replayed onto the live board through Konnect."""
import sys, json, importlib, pcbnew
sys.path.insert(0,'.')
import arouter
F=pcbnew.FromMM
L={'F.Cu':pcbnew.F_Cu,'In1.Cu':pcbnew.In1_Cu,'In2.Cu':pcbnew.In2_Cu,'B.Cu':pcbnew.B_Cu}
bp=sys.argv[1]; mods=sys.argv[2:]
b=pcbnew.LoadBoard(bp)
def add_t(t):
    tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2'])))
    tr.SetWidth(F(t['w'])); tr.SetLayer(L[t['layer']]); tr.SetNet(b.FindNet(t['net'])); b.Add(tr)
def add_v(v):
    vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v.get('size',0.6))); vi.SetDrill(F(v.get('drill',0.3)))
    vi.SetViaType(pcbnew.VIATYPE_THROUGH); vi.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); vi.SetNet(b.FindNet(v['net'])); b.Add(vi)
def add_z(z):
    zo=pcbnew.ZONE(b); zo.SetLayer(L[z['layer']]); zo.SetNet(b.FindNet(z['net']))
    ol=zo.Outline(); ol.NewOutline()
    for x,y in z['pts']: ol.Append(F(x),F(y))
    zo.SetAssignedPriority(z.get('priority',0)); zo.SetLocalClearance(F(z.get('clearance',0.2))); zo.SetMinThickness(F(z.get('min_width',0.2)))
    zo.SetPadConnection({'solid':pcbnew.ZONE_CONNECTION_FULL,'thermal':pcbnew.ZONE_CONNECTION_THERMAL,'none':pcbnew.ZONE_CONNECTION_NONE}[z.get('pad_connection','thermal')])
    if z.get('name'): zo.SetZoneName(z['name'])
    b.Add(zo)
ALL=dict(tracks=[],vias=[],zones=[]); fails=[]
EDGE=[[(0,0),(300,0),(300,75.6),(0,75.6)],[(0,120.4),(300,120.4),(300,200),(0,200)],[(0,0),(60.6,0),(60.6,200),(0,200)],[(239.4,0),(300,0),(300,200),(239.4,200)]]
blocks=[importlib.import_module(m) for m in mods]
for blk in blocks:
    for t in blk.T: add_t(t)
    for v in blk.V: add_v(v)
    ALL['tracks']+=blk.T; ALL['vias']+=blk.V
for blk in blocks:
    for job in getattr(blk,'J',[]):
        net=job['net']; win=job.get('win')
        if not win:
            xs=[job['src'][0],job['dst'][0]]; ys=[job['src'][1],job['dst'][1]]; m=job.get('margin',3)
            win=(min(xs)-m,min(ys)-m,max(xs)+m,max(ys)+m)
        R=arouter.Router(b,win,res=job.get('res',0.05),layers=tuple(job.get('layers',['F.Cu'])))
        keep={l:[z['pts'] for bb in blocks for z in bb.Z if z['net']!=net and z['layer']==l and z.get('keep')]+job.get('keep',[])+EDGE for l in ('F.Cu','In1.Cu','In2.Cu','B.Cu')}
        res=R.route(net,job['src'],job['dst'],width=job.get('w',0.2),clr=job.get('clr',0.2),layers=job.get('layers',['F.Cu']),
                    via=tuple(job.get('via',(0.5,0.25))),keep=keep,start_layer=job.get('start','F.Cu'),end_layers=job.get('end'),maxit=job.get('maxit',600000))
        if res is None: fails.append(job.get('name',net)); print('ROUTE FAIL',job.get('name',net)); continue
        T,V=res
        for t in T: add_t(t)
        for v in V: add_v(v)
        ALL['tracks']+=T; ALL['vias']+=V
        print('routed',job.get('name',net),len(T),'segs',len(V),'vias')
for blk in blocks:
    for z in blk.Z: add_z(z)
    ALL['zones']+=blk.Z
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(bp,b)
json.dump(ALL,open('spec_all.json','w'))
print('TOTAL tracks',len(ALL['tracks']),'vias',len(ALL['vias']),'zones',len(ALL['zones']),'fails',fails)
