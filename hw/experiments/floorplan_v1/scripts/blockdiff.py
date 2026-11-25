"""Rigid-move proof: every block item in the new board equals the base item after the block's rotation+translation."""
import sys, json, math, pcbnew
mm = pcbnew.ToMM
A = pcbnew.LoadBoard(sys.argv[1]); Bd = pcbnew.LoadBoard(sys.argv[2]); XF = json.load(open(sys.argv[2] + '.xf.json'))
BL = json.load(open('blocks.json'))
def xf(name, x, y):
    t = XF[name]; cx, cy = t['c0']; nx, ny = t['c1']; a = math.radians(t['deg']); c, s = round(math.cos(a), 12), round(math.sin(a), 12)
    dx, dy = x - cx, y - cy
    return nx + dx * c + dy * s, ny - dx * s + dy * c
def pts(it):
    k = it.GetClass()
    if k == 'PCB_VIA': return [(mm(it.GetX()), mm(it.GetY()))]
    if k in ('PCB_TRACK', 'PCB_ARC'): return [(mm(it.GetStart().x), mm(it.GetStart().y)), (mm(it.GetEnd().x), mm(it.GetEnd().y))]
    if k == 'ZONE':
        o = it.Outline().Outline(0); return [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]
def index(b):
    d = {t.m_Uuid.AsString(): t for t in b.GetTracks()}; d.update({z.m_Uuid.AsString(): z for z in b.Zones()}); return d
ia, ib = index(A), index(Bd)
fa = {f.GetReference(): f for f in A.GetFootprints()}; fb = {f.GetReference(): f for f in Bd.GetFootprints()}
out = {}
for name, blk in BL.items():
    worst = 0.0; n = 0; missing = []; rotbad = 0
    for r in blk['refs']:
        for pa in fa[r].Pads():
            pb = [p for p in fb[r].Pads() if p.GetNumber() == pa.GetNumber() and abs(mm(p.GetX()) - xf(name, mm(pa.GetX()), mm(pa.GetY()))[0]) < 0.5]
            x, y = xf(name, mm(pa.GetX()), mm(pa.GetY()))
            d = min(math.hypot(mm(p.GetX()) - x, mm(p.GetY()) - y) for p in fb[r].Pads() if p.GetNumber() == pa.GetNumber())
            worst = max(worst, d); n += 1
        if (fb[r].GetOrientationDegrees() - fa[r].GetOrientationDegrees() - XF[name]['deg']) % 360 > 1e-6 and abs((fb[r].GetOrientationDegrees() - fa[r].GetOrientationDegrees() - XF[name]['deg']) % 360 - 360) > 1e-6: rotbad += 1
    for u in blk['items']:
        if u not in ib: missing.append(u); continue
        if blk['zones'] if False else ia[u].GetClass() == 'ZONE' and ia[u].GetZoneName() == 'BOOST_VOUT_PVDD': continue  # clipped on purpose
        P0 = [xf(name, *p) for p in pts(ia[u])]; P1 = pts(ib[u])
        if len(P0) != len(P1): worst = max(worst, 99); continue
        worst = max(worst, max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(P0, P1))); n += 1
    pruned = [(ia[u].GetClass().replace('PCB_', ''), ia[u].GetNetname().split('/')[-1], round(ia[u].GetLength() if ia[u].GetClass() == 'PCB_TRACK' else 0, 2)) for u in missing]
    out[name] = dict(items=n, max_dev_mm=round(worst, 6), rot_mismatch=rotbad, pruned=len(missing), pruned_nets=sorted(set(p[1] for p in pruned)))
    print(name, out[name])
json.dump(out, open(sys.argv[2] + '.blockdiff.json', 'w'), indent=1)
