"""Grid-alignment sensitivity: run a loop with the 0.1 mm raster grid shifted by (dx, dy)."""
import sys, os
import pl_common, fh_loops as F
from pl_common import load, Grid
tag, loop = sys.argv[1], sys.argv[2]; shifts = [(a, c) for a in (0, 0.05) for c in (0, 0.05)]
orig = Grid.from_bbox.__func__
b = load(tag); spec = [s for s in F.LOOPS if s['name'] == loop][0]; res = []
for dx, dy in shifts:
    Grid.from_bbox = classmethod(lambda cls, bb, p, margin=0.0, dx=dx, dy=dy: orig(cls, (bb[0] - dx, bb[1] - dy, bb[2], bb[3]), p, margin))
    r = F.analyse_loop(b, spec, os.path.join('work', 'fasthenry')); res.append(r['L_nH']['1e+08'] if r.get('L_nH') else None)
print(tag, loop, [round(x, 3) for x in res], 'mean %.3f' % (sum(res) / len(res)))
