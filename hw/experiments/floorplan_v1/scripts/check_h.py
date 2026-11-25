"""Height check vs mech STL clearance maps (1 mm air included). Body box = F.Fab/B.Fab graphics bbox (else courtyard)."""
import sys, json, importlib, numpy as np, pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1]); P = importlib.import_module(sys.argv[2])
maps = {}
for side, base in (('F', P.HMAP_TOP), ('B', P.HMAP_BOT)):
    H = np.load(base + '.npy') - 1.0; m = json.load(open(base + '_meta.json')); maps[side] = (H, np.array(m['xs']), np.array(m['ys']))
bad = []; n = 0; out = {}
for f in b.GetFootprints():
    r = f.GetReference()
    if r == 'BRD1' or r.startswith(('H', 'FID')): continue
    side = 'B' if f.IsFlipped() else 'F'
    fab = pcbnew.B_Fab if side == 'B' else pcbnew.F_Fab
    bb = None
    for g in f.GraphicalItems():
        if g.GetLayer() == fab:
            x = g.GetBoundingBox(); x = [mm(x.GetX()), mm(x.GetY()), mm(x.GetRight()), mm(x.GetBottom())]
            bb = x if bb is None else [min(bb[0], x[0]), min(bb[1], x[1]), max(bb[2], x[2]), max(bb[3], x[3])]
    if bb is None:
        c = f.GetCourtyard(pcbnew.B_CrtYd if side == 'B' else pcbnew.F_CrtYd).BBox(); bb = [mm(c.GetX()), mm(c.GetY()), mm(c.GetRight()), mm(c.GetBottom())]
    h = P.HEIGHT.get(str(f.GetFPID().GetLibItemName()), 1.5 if side == 'F' else 1.0)
    H, hx, hy = maps[side]
    mx = (hx >= bb[0] - 150 - 0.25) & (hx <= bb[2] - 150 + 0.25); my = (hy >= 100 - bb[3] - 0.25) & (hy <= 100 - bb[1] + 0.25)
    sub = H[np.ix_(my, mx)]; c = float(sub.min()) if sub.size else 99.0
    n += 1; out[r] = (side, h, round(c, 1))
    if c < h: bad.append((r, side, h, round(c, 1)))
print('height check: %d parts, %d fail' % (n, len(bad)), bad)
json.dump(out, open(sys.argv[1] + '.heights.json', 'w'))
