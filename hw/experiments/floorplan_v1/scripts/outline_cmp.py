"""Before/after outline comparison in enclosure coordinates with the STL height-clearance map behind.
usage: outline_cmp.py geo_revA.json geo_new.json out.png"""
import sys, json, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle
plt.style.use('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/sim/paper.mplstyle')
A = json.load(open(sys.argv[1])); N = json.load(open(sys.argv[2]))
enc = lambda p: (p[0] - 150, 100 - p[1])
def outline(G): return [enc(p) for p in [e for e in G['edge'] if len(e) > 3][0]]
def area(P):
    x = np.array([p[0] for p in P]); y = np.array([p[1] for p in P]); return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
H = np.load('hmap_top.npy') - 1.0; m = json.load(open('hmap_top_meta.json')); hx, hy = np.array(m['xs']), np.array(m['ys'])
fig, ax = plt.subplots(figsize=(10, 3.6))
cls = np.where(H >= 11.5, 2, np.where(H >= 7.0, 1, 0))
ax.imshow(cls, extent=(hx[0], hx[-1], hy[0], hy[-1]), origin='lower', cmap=matplotlib.colors.ListedColormap(['#d0d0d0', '#fbe3c0', '#ffffff']), alpha=1.0, aspect='equal', zorder=0)
PA, PN = outline(A), outline(N)
ax.add_patch(Polygon(PA, closed=True, fill=False, ec='0.45', lw=1.4, ls='--', zorder=3, label='rev A: 180 x 46 mm, %.0f mm$^2$' % area(PA)))
ax.add_patch(Polygon(PN, closed=True, fc='none', hatch='//', alpha=0.9, ec='#1f77b4', lw=1.8, zorder=4,
                     label='floor plan v1: %.1f x 46 mm, %.0f mm$^2$' % (max(p[0] for p in PN) - min(p[0] for p in PN), area(PN))))
for G, c, ls in ((A, '0.45', '--'), (N, '#1f77b4', '-')):
    for f in G['fps']:
        if f['ref'].startswith('H') and f['ref'][1:].isdigit():
            ax.add_patch(Circle(enc((f['x'], f['y'])), 1.6, fill=False, ec=c, lw=1.0, ls=ls, zorder=5))
for G, c in ((A, '0.45'), (N, '#2ca02c')):
    u = [f for f in G['fps'] if f['ref'] == 'U101'][0]
    xs = [enc(p)[0] for cc in u['cy'] for p in cc]; ys = [enc(p)[1] for cc in u['cy'] for p in cc]
    ax.add_patch(Rectangle((min(xs), min(ys)), max(xs) - min(xs), max(ys) - min(ys), fill=False, ec=c, lw=1.0, zorder=5))
ax.text(70, 14, 'antenna\n(v1)', color='#2ca02c', fontsize=6.5, ha='center')
ax.text(-75, 14, 'antenna\n(rev A)', color='0.45', fontsize=6.5, ha='center')
ax.text(0, 29.2, 'USB-C port (fixed)', fontsize=6.5, ha='center')
ax.axvline(61.5, color='#9467bd', lw=0.8, ls=':'); ax.text(62, 28.5, 'J501 FFC must rise at X > 61.5', fontsize=6, color='#9467bd')
ax.set_xlim(-95, 97); ax.set_ylim(-24, 31)
ax.set_xlabel('enclosure X, mm'); ax.set_ylabel('enclosure Y, mm (rear up)')
h, l = ax.get_legend_handles_labels()
from matplotlib.patches import Patch
h += [Patch(fc='#ffffff', ec='0.7'), Patch(fc='#fbe3c0'), Patch(fc='#d0d0d0')]
l += ['clearance >= 11.5 mm (VH, 470 uF)', '7-11.5 mm', '< 7 mm']
ax.legend(h, l, loc='upper left', bbox_to_anchor=(0, -0.18), ncol=3, fontsize=6.5, frameon=False)
ax.set_title('Main board outline: rev A vs floor plan v1 (top view, enclosure coordinates)', fontsize=9)
plt.savefig(sys.argv[3], dpi=220, bbox_inches='tight')
print('areas', round(area(PA)), round(area(PN)))
