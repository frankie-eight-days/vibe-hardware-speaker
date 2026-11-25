import sys, os, json, time
from pl_common import extract, load, Grid, save_json, WORK
import fh_loops as F
tag, pcb = sys.argv[1], sys.argv[2]
if not os.path.exists(os.path.join(WORK, tag + '.json')) or '--x' in sys.argv: extract(pcb, tag)
b = load(tag); outdir = os.path.join(WORK, 'fasthenry'); os.makedirs(outdir, exist_ok=True)
res = []
for spec in F.LOOPS:
    t = time.time(); r = F.analyse_loop(b, spec, outdir, grids=False)
    print(tag, spec['name'], r.get('status'), r.get('L_nH'), '%.0fs' % (time.time() - t), flush=True); res.append(r)
save_json(res, 'fh_loops_%s.json' % tag)
