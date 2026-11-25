"""Thermal variant of a floor-plan board: assumed phase-2 copper = GND pour on L1/L3/L6, L4 power planes
(modelled as a full fill), L2/L5 solid GND (already present), 3x3 GND via array under U701."""
import sys, pcbnew
mm, MM = pcbnew.ToMM, pcbnew.FromMM
b = pcbnew.LoadBoard(sys.argv[1]); gnd = b.GetNetsByName()['GND']
src = [z for z in b.Zones() if z.GetZoneName() == 'L2_GND'][0]
new = []
for L, name in ((pcbnew.F_Cu, 'TH_L1'), (pcbnew.In2_Cu, 'TH_L3'), (pcbnew.B_Cu, 'TH_L6')):
    z = pcbnew.ZONE(b); z.SetLayer(L); z.SetZoneName(name); z.SetNet(gnd); z.SetAssignedPriority(0)
    o = z.Outline(); o.NewOutline(); so = src.Outline().Outline(0)
    for i in range(so.PointCount()): o.Append(so.CPoint(i).x, so.CPoint(i).y)
    z.SetMinThickness(MM(0.2)); z.SetLocalClearance(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); b.Add(z); new.append(z)
u = [f for f in b.GetFootprints() if f.GetReference() == 'U701'][0]
for i in ():
    for j in (-1, 0, 1):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(u.GetX() + MM(1.0 * i), u.GetY() + MM(1.0 * j)))
        v.SetWidth(MM(0.5)); v.SetDrill(MM(0.25)); v.SetNet(gnd); v.SetIsFree(True); b.Add(v)
new += [z for z in b.Zones() if z.GetZoneName() in ('L2_GND', 'L5_GND')]
pcbnew.ZONE_FILLER(b).Fill(new)   # block zones keep their designed fill
b.Save(sys.argv[2])
gp = [(z.GetZoneName(), [mm(z.Outline().Outline(0).CPoint(k).x) for k in range(4)], [mm(z.Outline().Outline(0).CPoint(k).y) for k in range(4)]) for z in b.Zones() if z.GetZoneName().startswith('GAPPAD')]
import json; json.dump({n: [min(x), min(y), max(x), max(y)] for n, x, y in gp}, open(sys.argv[2] + '.gappads.json', 'w'))
print('ok', len(gp))
