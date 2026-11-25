"""Floor-plan builder (pcbnew, offline copy). usage: build.py base.kicad_pcb out.kicad_pcb plan_module
Blocks move rigidly (footprints + their critical copper, by UUID). Everything else is placed by plan
(fixed) or by a courtyard-to-courtyard raster packer near an anchor. All other copper is deleted."""
import sys, json, math, importlib
import numpy as np
import pcbnew
mm, MM = pcbnew.ToMM, pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(float(x)), MM(float(y)))
b = pcbnew.LoadBoard(sys.argv[1])
P = importlib.import_module(sys.argv[3])
B = json.load(open('blocks.json'))
fps = {f.GetReference(): f for f in b.GetFootprints()}
owner = {r: n for n, v in B.items() for r in v['refs']}
log = []

# ---------------- 1. keep only block copper ----------------
keep = {u for v in B.values() for u in v['items']}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() not in keep: b.Delete(t)
for z in list(b.Zones()):
    if z.m_Uuid.AsString() not in keep: b.Delete(z)
# clip the boost PVDD distribution pour to the C_OUT stack
for z in b.Zones():
    if z.GetZoneName() == 'BOOST_VOUT_PVDD':
        x0, y0, x1, y1 = P.CLIP_BOOST_PVDD
        r = pcbnew.SHAPE_POLY_SET(); r.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)): r.Append(MM(x), MM(y))
        o = z.Outline(); o.BooleanIntersection(r)
# prune: tracks that end on a pad of a footprint outside the block, then dangling stubs
def prune():
    pads = [(p, f.GetReference()) for f in b.GetFootprints() for p in f.Pads()]
    zones = list(b.Zones())
    removed = 0
    while True:
        tr = [t for t in b.GetTracks() if t.GetClass() != 'PCB_VIA']
        vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
        pts = {}
        for t in tr:
            for p in (t.GetStart(), t.GetEnd()): pts.setdefault((p.x, p.y, t.GetLayer(), t.GetNetCode()), []).append(t)
        kill = []
        for t in tr:
            blk = None
            for p in (t.GetStart(), t.GetEnd()):
                ext = own = False
                for pd, r in pads:
                    if pd.GetNetCode() == t.GetNetCode() and pd.IsOnLayer(t.GetLayer()) and pd.HitTest(p):
                        if owner.get(r) is None: ext = True
                        else: own = True
                if ext and not own: kill.append(t); break
                anch = own or len(pts[(p.x, p.y, t.GetLayer(), t.GetNetCode())]) > 1
                anch = anch or any(v.GetNetCode() == t.GetNetCode() and (v.GetPosition() - p).EuclideanNorm() < MM(0.05) for v in vias)
                anch = anch or any(z.GetNetCode() == t.GetNetCode() and z.IsOnLayer(t.GetLayer()) and z.Outline().Contains(p) for z in zones)
                if not anch: kill.append(t); break
        if not kill: break
        seen=set()
        for t in kill:
            u=t.m_Uuid.AsString()
            if u in seen: continue
            seen.add(u); b.Delete(t); removed += 1
    return removed
log.append(('pruned', prune()))

# ---------------- 2. rigid block moves ----------------
def rot_pt(x, y, cx, cy, deg):   # KiCad rotation: +deg is CCW on screen (y down)
    a = math.radians(deg); c, s = round(math.cos(a), 12), round(math.sin(a), 12)
    dx, dy = x - cx, y - cy
    return cx + dx * c + dy * s, cy - dx * s + dy * c
items = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
items.update({z.m_Uuid.AsString(): z for z in b.Zones()})
def block_box(name):
    bb = None
    for r in B[name]['refs']:
        c = fps[r].GetCourtyard(pcbnew.F_CrtYd).BBox()
        x = [mm(c.GetX()), mm(c.GetY()), mm(c.GetRight()), mm(c.GetBottom())]
        bb = x if bb is None else [min(bb[0], x[0]), min(bb[1], x[1]), max(bb[2], x[2]), max(bb[3], x[3])]
    for u in B[name]['items']:
        it = items.get(u)
        if it is None: continue
        c = it.GetBoundingBox(); x = [mm(c.GetX()), mm(c.GetY()), mm(c.GetRight()), mm(c.GetBottom())]
        bb = [min(bb[0], x[0]), min(bb[1], x[1]), max(bb[2], x[2]), max(bb[3], x[3])]
    return bb
XF = {}
for name, spec in P.BLOCKS.items():
    bb = block_box(name); cx, cy = round((bb[0] + bb[2]) / 2 / 0.05) * 0.05, round((bb[1] + bb[3]) / 2 / 0.05) * 0.05
    if len(spec) == 3: deg, nx, ny = spec
    else:
        deg, al, ax, ay = spec
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        if deg % 180: w, h = h, w
        nx = ax + w / 2 if 'l' in al else ax - w / 2
        ny = ay + h / 2 if 't' in al else ay - h / 2
        nx, ny = round(nx / 0.05) * 0.05, round(ny / 0.05) * 0.05
    if nx is None: nx, ny = cx, cy
    objs = [fps[r] for r in B[name]['refs']] + [items[u] for u in B[name]['items'] if u in items]
    for o in objs:
        if deg: o.Rotate(V(cx, cy), pcbnew.EDA_ANGLE(deg, pcbnew.DEGREES_T))
        o.Move(V(nx - cx, ny - cy))
    XF[name] = dict(deg=deg, c0=(cx, cy), c1=(nx, ny))
    log.append((name, 'box', [round(v, 2) for v in block_box(name)], 'centre', (nx, ny)))
json.dump(XF, open(sys.argv[2] + '.xf.json', 'w'))

# rev A silk labels sit at rev A positions; phase 2 redoes silk
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT': b.Delete(d)
# ---------------- 3. outline: board-level Edge.Cuts polygon (a footprint-level polygon in BRD1 is not
# recognised by KiCad 10 once the outline shrinks, so BRD1 is removed; see FLOORPLAN.md)
b.Delete(fps.pop('BRD1'))
sh = pcbnew.PCB_SHAPE(b); sh.SetShape(pcbnew.SHAPE_T_POLY); sh.SetLayer(pcbnew.Edge_Cuts); sh.SetFilled(False); sh.SetWidth(MM(0.05))
ps = pcbnew.SHAPE_POLY_SET(); ps.NewOutline()
for x, y in P.OUTLINE: ps.Append(MM(x), MM(y))
sh.SetPolyShape(ps); b.Add(sh)

# ---------------- 4. add C605 (ECO-004, v0.3) ----------------
if 'C605' not in fps:
    lib = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Capacitor_SMD.pretty'
    f = pcbnew.FootprintLoad(lib, 'CP_Elec_6.3x5.7')
    f.SetFPIDAsString('Capacitor_SMD:CP_Elec_6.3x5.7')
    f.SetReference('C605'); f.SetValue('47uF 35V')
    f.SetPath(pcbnew.KIID_PATH('/4b3dcb14-9b65-443e-80f4-202b0c3d1695/f81ae168-78b9-4ed2-adbb-5b88ab72edf1'))
    f.SetSheetname('usb_power'); f.SetSheetfile('usb_power.kicad_sch')
    for k, v in (('LCSC', 'C134832'), ('Description', 'Polarized capacitor')): f.SetField(k, v)
    nets = b.GetNetsByName()
    for p in f.Pads():
        p.SetNet(nets['/charger/VBUS'] if p.GetNumber() == '1' else nets['GND'])
    b.Add(f); fps['C605'] = f
# bottom fiducials (board-only copies of FID1)
for i, r in enumerate(getattr(P, 'BOTTOM_FIDS', [])):
    if r not in fps:
        f = pcbnew.FootprintLoad('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/lib/speaker/speaker.pretty', 'Fiducial_1mm_Mask2mm')
        f.SetFPIDAsString('speaker:Fiducial_1mm_Mask2mm'); f.SetReference(r); f.SetValue('Fiducial')
        f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(False)
        f.SetPosition(V(0, 0)); b.Add(f); fps[r] = f
# delete unused holes
for r in P.DELETE:
    if r in fps: b.Remove(fps.pop(r))

# ---------------- 5. raster occupancy ----------------
X0, Y0, X1, Y1 = P.BBOX; D = 0.05
NX, NY = int(round((X1 - X0) / D)), int(round((Y1 - Y0) / D))
def poly_mask(pts, grow=0.0):
    m = np.zeros((NY, NX), bool)
    pts = np.array(pts); ys = Y0 + (np.arange(NY) + 0.5) * D
    xs_c = X0 + (np.arange(NX) + 0.5) * D
    x1, y1 = pts[:, 0], pts[:, 1]; x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    for j, y in enumerate(ys):
        c = ((y1 <= y) & (y2 > y)) | ((y2 <= y) & (y1 > y))
        if not c.any(): continue
        xi = np.sort(x1[c] + (y - y1[c]) * (x2[c] - x1[c]) / (y2[c] - y1[c]))
        for a, bnd in zip(xi[0::2], xi[1::2]):
            m[j, (xs_c >= a) & (xs_c <= bnd)] = True
    if grow > 0:
        k = int(math.ceil(grow / D)); g = m.copy()
        for dj in range(-k, k + 1):
            for di in range(-k, k + 1):
                if di * di + dj * dj <= k * k: g |= np.roll(np.roll(m, dj, 0), di, 1)
        m = g
    return m
def rect_cells(x0, y0, x1, y1):   # cells touched by rect (conservative)
    i0 = int(math.floor((x0 - X0) / D + 1e-6)); i1 = int(math.ceil((x1 - X0) / D - 1e-6))
    j0 = int(math.floor((y0 - Y0) / D + 1e-6)); j1 = int(math.ceil((y1 - Y0) / D - 1e-6))
    return max(i0, 0), max(j0, 0), min(i1, NX), min(j1, NY)
board = poly_mask(P.OUTLINE)
inner = board.copy()
k = int(round(P.EDGE_MARGIN / D))
for dj in range(-k, k + 1):
    for di in range(-k, k + 1):
        inner &= np.roll(np.roll(board, dj, 0), di, 1)
OCC = {'F': ~inner, 'B': ~inner}
for side, rects in P.KEEPOUT.items():
    for (x0, y0, x1, y1) in rects:
        i0, j0, i1, j1 = rect_cells(x0, y0, x1, y1); OCC[side][j0:j1, i0:i1] = True
# clearance maps (enclosure coords: X=Xk-150, Y=100-Yk), values = clearance minus 1 mm air
def clear_map(npy, meta):
    H = np.load(npy) - 1.0; m = json.load(open(meta)); hx = np.array(m['xs']); hy = np.array(m['ys'])
    xk = X0 + (np.arange(NX) + 0.5) * D; yk = Y0 + (np.arange(NY) + 0.5) * D
    ii = np.clip(np.searchsorted(hx, xk - 150) , 0, len(hx) - 1); jj = np.clip(np.searchsorted(hy, 100 - yk), 0, len(hy) - 1)
    C = H[np.ix_(jj, ii)]
    out = ((xk - 150 < hx[0]) | (xk - 150 > hx[-1]))[None, :] | ((100 - yk < hy[0]) | (100 - yk > hy[-1]))[:, None]
    C[out] = 0.0
    # conservative: min over a 0.5 mm neighbourhood
    return C
CLR = {'F': clear_map(P.HMAP_TOP + '.npy', P.HMAP_TOP + '_meta.json'), 'B': clear_map(P.HMAP_BOT + '.npy', P.HMAP_BOT + '_meta.json')}
def height_of(f):
    side = 'B' if f.IsFlipped() else 'F'
    return P.HEIGHT.get(str(f.GetFPID().GetLibItemName()), P.HEIGHT.get(f.GetReference(), 1.5 if side == 'F' else 1.0))
GAP = {}
for r in P.GAPPAD_REFS:
    x, y = mm(fps[r].GetX()), mm(fps[r].GetY()); h = P.GAPPAD / 2
    x = min(max(x, P.OUTLINE_BOX[0] + h + 0.3), P.OUTLINE_BOX[2] - h - 0.3); y = min(max(y, P.OUTLINE_BOX[1] + h + 0.3), P.OUTLINE_BOX[3] - h - 0.3)
    GAP['GAPPAD_' + r] = [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)]
    i0, j0, i1, j1 = rect_cells(x - h, y - h, x + h, y + h); OCC['B'][j0:j1, i0:i1] = True
def cy_box(f):
    side = 'B' if f.IsFlipped() else 'F'
    c = f.GetCourtyard(pcbnew.B_CrtYd if side == 'B' else pcbnew.F_CrtYd)
    if c.OutlineCount() == 0:
        bb = f.GetBoundingBox(False, False)
    else: bb = c.BBox()
    return side, (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
def mark(f):
    side, (x0, y0, x1, y1) = cy_box(f)
    i0, j0, i1, j1 = rect_cells(x0, y0, x1, y1); OCC[side][j0:j1, i0:i1] = True
    other = 'B' if side == 'F' else 'F'
    for p in f.Pads():   # through-hole pads also block the other side
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            bb = p.GetBoundingBox(); i0, j0, i1, j1 = rect_cells(mm(bb.GetX()) - .35, mm(bb.GetY()) - .35, mm(bb.GetRight()) + .35, mm(bb.GetBottom()) + .35)
            OCC[other][j0:j1, i0:i1] = True
# block copper on outer layers (+0.2 mm)
for name in B:
    for u in B[name]['items']:
        it = items.get(u)
        if it is None: continue
        for L, side in ((pcbnew.F_Cu, 'F'), (pcbnew.B_Cu, 'B')):
            if it.GetClass() == 'ZONE' and it.IsOnLayer(L):
                for k_ in range(it.Outline().OutlineCount()):
                    o = it.Outline().Outline(k_)
                    OCC[side] |= poly_mask([(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())], 0.4)
            elif it.GetClass() == 'PCB_VIA':
                x, y, r = mm(it.GetX()), mm(it.GetY()), mm(it.GetWidth(pcbnew.F_Cu)) / 2 + (0.35 if side == 'B' else 0.3)
                i0, j0, i1, j1 = rect_cells(x - r, y - r, x + r, y + r); OCC[side][j0:j1, i0:i1] = True
            elif it.GetClass() == 'PCB_TRACK' and it.GetLayer() == L:
                bb = it.GetBoundingBox(); i0, j0, i1, j1 = rect_cells(mm(bb.GetX()) - .2, mm(bb.GetY()) - .2, mm(bb.GetRight()) + .2, mm(bb.GetBottom()) + .2)
                OCC[side][j0:j1, i0:i1] = True

# ---------------- 6. fixed placements ----------------
def place(f, x, y, rot, side):
    if (side == 'B') != f.IsFlipped(): f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(rot); f.SetPosition(V(x, y))
for r, (x, y, rot, side) in P.FIXED.items():
    place(fps[r], x, y, rot, side)
placed = set(owner) | set(P.FIXED)
for r in placed:
    if r in fps and r != 'BRD1': mark(fps[r])

# ---------------- 7. packer ----------------
def pad_xy(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == num: return mm(p.GetX()), mm(p.GetY())
    raise KeyError((ref, num))
def free_map(side, wc, hc, hgt=0):
    O = (OCC[side] | (CLR[side] < hgt)).astype(np.int32); S = np.zeros((NY + 1, NX + 1), np.int64); S[1:, 1:] = O.cumsum(0).cumsum(1)
    s = S[hc:, wc:] - S[:-hc, wc:] - S[hc:, :-wc] + S[:-hc, :-wc]
    return s == 0     # s[j,i]: rect occupying cells [j,j+hc)x[i,i+wc) is free
unplaced = []
for grp in P.GROUPS:
    refs, side, anchor, rots, maxr = grp[:5]; grid = grp[5] if len(grp) > 5 else None
    for r in refs:
        if r not in fps: unplaced.append(r); continue
        f = fps[r]
        if isinstance(anchor, tuple) and isinstance(anchor[0], str):
            tx, ty = pad_xy(*anchor) if anchor[1] else (mm(fps[anchor[0]].GetX()), mm(fps[anchor[0]].GetY()))
            if len(anchor) > 2: tx, ty = tx + anchor[2], ty + anchor[3]
        elif callable(anchor): tx, ty = anchor(r, pad_xy)
        else: tx, ty = anchor
        best = None
        for rot in rots:
            place(f, tx, ty, rot, side)
            _, (x0, y0, x1, y1) = cy_box(f)
            w, h = x1 - x0, y1 - y0; ox, oy = mm(f.GetX()) - x0, mm(f.GetY()) - y0
            wc, hc = int(math.ceil((w + 0.02) / D)), int(math.ceil((h + 0.02) / D))
            fm = free_map(side, wc, hc, height_of(f))
            if grid:
                gx0, gy0, g = grid
                ex, ey = ox - (mm(f.GetX()) - (x0 + x1) / 2 + ox) + ox, 0
                kx = np.arange(math.ceil((X0 - gx0) / g), math.floor((X1 - gx0) / g) + 1); ky = np.arange(math.ceil((Y0 - gy0) / g), math.floor((Y1 - gy0) / g) + 1)
                GX, GY = np.meshgrid(gx0 + kx * g, gy0 + ky * g)          # candidate footprint positions
                cxx = GX - (mm(f.GetX()) - (x0 + x1) / 2); cyy = GY - (mm(f.GetY()) - (y0 + y1) / 2)   # courtyard centres
                ii = np.floor((cxx - w / 2 - X0) / D + 1e-6).astype(int).ravel(); jj = np.floor((cyy - h / 2 - Y0) / D + 1e-6).astype(int).ravel()
                ok = (ii >= 0) & (jj >= 0) & (ii < fm.shape[1]) & (jj < fm.shape[0])
                ii, jj = ii[ok], jj[ok]; GXo, GYo = GX.ravel()[ok], GY.ravel()[ok]
                ok = fm[jj, ii]; ii, jj, GXo, GYo = ii[ok], jj[ok], GXo[ok], GYo[ok]
                if not len(ii): continue
                d2 = (GXo - tx) ** 2 + (GYo - ty) ** 2; k_ = int(np.argmin(d2))
                if d2[k_] > maxr ** 2: continue
                if best is None or d2[k_] < best[0] - 1e-9: best = (d2[k_], rot, GXo[k_], GYo[k_])
                continue
            jj, ii = np.nonzero(fm)
            if not len(ii): continue
            cx = X0 + (ii + wc / 2) * D; cy = Y0 + (jj + hc / 2) * D
            d2 = (cx - tx) ** 2 + (cy - ty) ** 2
            k_ = int(np.argmin(d2))
            if d2[k_] > maxr ** 2: continue
            if best is None or d2[k_] < best[0] - 1e-9:
                best = (d2[k_], rot, X0 + ii[k_] * D + 0.01 + ox, Y0 + jj[k_] * D + 0.01 + oy)
        if best is None: unplaced.append(r); continue
        place(f, best[2], best[3], best[1], side); mark(f); placed.add(r)
        if r.startswith('H'):   # standoff boss under the board
            _, (a0, b0, a1, b1) = cy_box(f); i0, j0, i1, j1 = rect_cells(a0, b0, a1, b1); OCC['B'][j0:j1, i0:i1] = True
for i, r in enumerate(unplaced):
    if r in fps: place(fps[r], X1 + 5 + (i % 4) * 14, Y0 + 6 + (i // 4) * 14, 0, 'F')
rest = [r for r in fps if r not in placed and r not in unplaced]
log.append(('unplaced', unplaced)); log.append(('not in plan', rest))

# ---------------- 8. planes + antenna keep-out ----------------
def add_zone(net, layer, pts, name, pri=0, rule=False):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetZoneName(name)
    o = z.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    if rule:
        z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET.AllCuMask(); z.SetLayerSet(ls)
    else:
        z.SetNet(b.GetNetsByName()[net]); z.SetAssignedPriority(pri); z.SetMinThickness(MM(0.2))
        z.SetLocalClearance(MM(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    b.Add(z); return z
for (net, layer, name) in P.PLANES:
    add_zone(net, getattr(pcbnew, layer), P.PLANE_OUTLINE, name)
for name, pts in P.RULE_AREAS.items():
    add_zone(None, pcbnew.F_Cu, pts, name, rule=True)
for name, pts in GAP.items():   # bottom footprint keep-out for gap-pad landings
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.B_Cu); z.SetZoneName(name); o = z.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    z.SetIsRuleArea(True); z.SetDoNotAllowFootprints(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(False); b.Add(z)
for r in placed:
    if r in fps: fps[r].SetLocked(r in owner)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())   # fills follow the moved copper and new neighbours
b.Save(sys.argv[2])
for l in log: print(*l)
