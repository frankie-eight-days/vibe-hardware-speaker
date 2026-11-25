"""NATIVE STEP 1 (approved exceptions; pcbnew API on a CLOSED board after a Konnect save).
usage: n1.py board.kicad_pcb ops.json   -> applies, in order:
 1 layer count 6 (+ In1/In3/In4 typed as power planes), board thickness 1.6
 2 layer change by UUID (old In2 power zones -> In3); zone outline replace by UUID
 3 track/via delete by UUID
 4 via-net repair to spec + free-via flag on track-less vias
 5 locked flag on every remaining track/via
ops.json = {move_zones:[uuid], del:[uuid], netfix:{uuid:net}}   (built by plan_n1.py from the board + specs, never by hand)"""
import sys,json,pcbnew
bp,opf=sys.argv[1:3]; O=json.load(open(opf)); b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM
log={}
if b.GetCopperLayerCount()!=6:
    b.SetCopperLayerCount(6); b.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
for l in (pcbnew.In1_Cu,pcbnew.In3_Cu,pcbnew.In4_Cu): b.SetLayerType(l,pcbnew.LT_POWER)
b.SetLayerType(pcbnew.In2_Cu,pcbnew.LT_SIGNAL)
U=lambda o:o.m_Uuid.AsString()
zs={U(z):z for z in b.Zones()}; n=0
for u in O['move_zones']: zs[u].SetLayer(pcbnew.In3_Cu); n+=1
log['zones_moved']=n
for u,pts in O.get('zone_replace',{}).items():
    z=zs[u]; ol=pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
    for x,y in pts: ol.Append(pcbnew.FromMM(x),pcbnew.FromMM(y))
    ol.thisown=0; z.SetOutline(ol)
log['zones_replaced']=len(O.get('zone_replace',{}))
tr={U(t):t for t in b.GetTracks()}; n=0
for u in O['del']:
    if u in tr: b.Remove(tr[u]); n+=1
log['deleted']=n
ends=set()
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': ends|={(t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)}
nf=0;fr=0
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': continue
    u=U(t)
    if u in O['netfix'] and t.GetNetname()!=O['netfix'][u]: t.SetNet(b.FindNet(O['netfix'][u])); nf+=1
    if (t.GetX(),t.GetY()) not in ends: t.SetIsFree(True); fr+=1
log['netfix']=nf; log['free']=fr
for t in b.GetTracks(): t.SetLocked(True)
log['locked']=len(b.GetTracks())
pcbnew.SaveBoard(bp,b); print(json.dumps(log))
