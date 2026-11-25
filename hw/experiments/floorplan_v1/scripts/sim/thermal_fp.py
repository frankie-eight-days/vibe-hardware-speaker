"""thermal.py + optional gap pads: 15x15 mm, 1 mm, 3 W/mK from the bottom landings to a 45 C wall.
usage: thermal_fp.py TAG [gappads.json]  (TAG ending in _pad uses the pads)"""
import sys, json, numpy as np
from scipy import sparse
import thermal as T
K_PAD, T_PAD = 3.0, 1.0e-3
GAPS = []
_build = T.build
def build(b, h):
    g, M, conv, on, idx, frac, inside = _build(b, h)
    if GAPS:
        nl = len(b.layers); add = np.zeros(M.shape[0]); A = (T.DX * 1e-3) ** 2
        xs = g.x0 + (np.arange(g.nx) + 0.5) * T.DX; ys = g.y0 + (np.arange(g.ny) + 0.5) * T.DX
        X, Y = np.meshgrid(xs, ys); bot = idx(nl - 1)
        for (x0, y0, x1, y1) in GAPS:
            m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & on
            add[bot[m]] += K_PAD * A / T_PAD
        M = (M + sparse.diags(add)).tocsc()
    return g, M, conv, on, idx, frac, inside
T.build = build
tag = sys.argv[1]
if len(sys.argv) > 2 and tag.endswith('_pad'): GAPS[:] = list(json.load(open(sys.argv[2])).values())
o, maps, b = T.analyse(tag)
print(tag, 'gaps', len(GAPS), o['validation'], 'max sustained W:', o['max_sustained_W'])
for cn, d in o['cases'].items():
    print(' ', cn, {h: {r: round(v['T_j_C'], 1) for r, v in dd['parts'].items() if v['P_W'] > 0} for h, dd in d.items()})
import pickle; pickle.dump({k: (v[0], v[1].x0, v[1].y0, v[1].nx, v[1].ny, v[2]) for k, v in maps.items()}, open('work/maps_%s.pkl' % tag, 'wb'))
