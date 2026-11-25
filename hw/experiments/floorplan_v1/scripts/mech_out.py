"""Mech hand-off: board outline + holes as DXF R12 (enclosure X/Y = KiCad X-150, 100-Y), connector table, params.
usage: mech_out.py geo.json outdir"""
import sys, json, os
G = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
E = [e for e in G['edge'] if len(e) > 3][0]
enc = lambda x, y: (round(x - 150, 3), round(100 - y, 3))
F = {f['ref']: f for f in G['fps']}
holes = sorted((r, enc(F[r]['x'], F[r]['y'])) for r in F if r.startswith('H') and r[1:].isdigit())
def dxf_line(x1, y1, x2, y2, layer):
    return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0\n11\n{x2}\n21\n{y2}\n31\n0\n"
s = "0\nSECTION\n2\nENTITIES\n"
P = [enc(*p) for p in E]
for a, b in zip(P, P[1:] + P[:1]): s += dxf_line(*a, *b, 'OUTLINE')
for r, (x, y) in holes: s += f"0\nCIRCLE\n8\nHOLES\n10\n{x}\n20\n{y}\n30\n0\n40\n1.6\n"
s += "0\nENDSEC\n0\nEOF\n"
open(os.path.join(out, 'mainboard_outline_fp1.dxf'), 'w').write(s)
def bbox(r):
    xs = [p[0] for c in F[r]['cy'] for p in c]; ys = [p[1] for c in F[r]['cy'] for p in c]
    (x0, y1), (x1, y0) = enc(min(xs), min(ys)), enc(max(xs), max(ys))
    return x0, x1, y0, y1
conn = {r: bbox(r) for r in ('J601', 'J501', 'J801', 'J802', 'J803', 'J301', 'J302', 'J401', 'J402', 'U101', 'C920', 'C301', 'C401')}
xs = [p[0] for p in P]; ys = [p[1] for p in P]
params = dict(mb_x=(min(xs), max(xs)), mb_y=(min(ys), 25.0), mb_usb_tab=(-7.0, 7.0, 26.5), mb_holes=[h for _, h in holes],
              mb_antenna='U101 at the +X end, antenna overhangs X = %.1f by 6.3 mm (front-right corner, feed point at the corner)' % max(xs))
json.dump(dict(params=params, holes=dict(holes), connectors=conn), open(os.path.join(out, 'mech_inputs_fp1.json'), 'w'), indent=1)
print(json.dumps(params)); print({r: tuple(round(v, 1) for v in b) for r, b in conn.items()})
