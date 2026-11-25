"""Scratch emulation of the Konnect ops in a JSON list (same argument names as the Konnect tools). usage: kemu.py board ops.json
ops: {"tool":"add_zone",...add_zone args} | {"tool":"rotate_component","reference":..,"angle":..} | {"tool":"move_component","reference":..,"x":..,"y":..}"""
import sys,json,pcbnew
bp,opf=sys.argv[1:3]; b=pcbnew.LoadBoard(bp); F=pcbnew.FromMM; n=0
for op in json.load(open(opf)):
    t=op['tool']
    if t=='add_zone':
        z=pcbnew.ZONE(b); z.SetLayer(b.GetLayerID(op['layer'])); z.SetNet(b.FindNet(op['net_name']))
        ol=pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
        for p in op['points']: ol.Append(F(p['x']),F(p['y']))
        ol.thisown=0; z.SetOutline(ol); z.SetAssignedPriority(op.get('priority',0)); z.SetLocalClearance(F(op.get('clearance',0.2))); z.SetMinThickness(F(op.get('min_width',0.2)))
        z.SetPadConnection({'solid':pcbnew.ZONE_CONNECTION_FULL,'thermal':pcbnew.ZONE_CONNECTION_THERMAL,'none':pcbnew.ZONE_CONNECTION_NONE}[op.get('pad_connection','thermal')])
        if op.get('name'): z.SetZoneName(op['name'])
        b.Add(z)
    elif t=='rotate_component':
        f=b.FindFootprintByReference(op['reference']); f.SetOrientationDegrees(op['angle'])
    elif t=='move_component':
        f=b.FindFootprintByReference(op['reference']); f.SetPosition(pcbnew.VECTOR2I(F(op['x']),F(op['y'])))
    else: raise SystemExit('unknown '+t)
    n+=1
pcbnew.SaveBoard(bp,b); print('kemu ops',n)
