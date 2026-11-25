"""Offline-only: apply a routing spec (tracks/vias/zones) to a SCRATCH copy of the board with KiCad's pcbnew API,
fill zones and save, so kicad-cli DRC can judge it. The live board is changed only by replaying the same spec through Konnect."""
import sys, json, pcbnew
board_path, *specs = sys.argv[1:]
b=pcbnew.LoadBoard(board_path)
F=pcbnew.FromMM
L={'F.Cu':pcbnew.F_Cu,'In1.Cu':pcbnew.In1_Cu,'In2.Cu':pcbnew.In2_Cu,'B.Cu':pcbnew.B_Cu}
def net(n):
    ni=b.FindNet(n)
    if ni is None: raise SystemExit('no net '+n)
    return ni
nt=nv=nz=0
for sp in specs:
    s=json.load(open(sp))
    for t in s.get('tracks',[]):
        tr=pcbnew.PCB_TRACK(b); tr.SetStart(pcbnew.VECTOR2I(F(t['x1']),F(t['y1']))); tr.SetEnd(pcbnew.VECTOR2I(F(t['x2']),F(t['y2'])))
        tr.SetWidth(F(t['w'])); tr.SetLayer(L[t['layer']]); tr.SetNet(net(t['net'])); b.Add(tr); nt+=1
    for v in s.get('vias',[]):
        vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(v['x']),F(v['y']))); vi.SetWidth(F(v.get('size',0.6))); vi.SetDrill(F(v.get('drill',0.3)))
        vi.SetViaType(pcbnew.VIATYPE_THROUGH); vi.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); vi.SetNet(net(v['net'])); b.Add(vi); nv+=1
    for z in s.get('zones',[]):
        zo=pcbnew.ZONE(b); zo.SetLayer(L[z['layer']]); zo.SetNet(net(z['net']))
        ol=zo.Outline(); ol.NewOutline()
        for x,y in z['pts']: ol.Append(F(x),F(y))
        zo.SetAssignedPriority(z.get('priority',0)); zo.SetLocalClearance(F(z.get('clearance',0.2))); zo.SetMinThickness(F(z.get('min_width',0.2)))
        pc={'solid':pcbnew.ZONE_CONNECTION_FULL,'thermal':pcbnew.ZONE_CONNECTION_THERMAL,'none':pcbnew.ZONE_CONNECTION_NONE}[z.get('pad_connection','thermal')]
        zo.SetPadConnection(pc)
        if z.get('name'): zo.SetZoneName(z['name'])
        b.Add(zo); nz+=1
filler=pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
pcbnew.SaveBoard(board_path,b)
print('added tracks',nt,'vias',nv,'zones',nz)
