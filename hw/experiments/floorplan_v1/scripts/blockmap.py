"""Block map: zoning (noisy / quiet / power / RF), blocks, planned L3 lanes and L4 power regions.
usage: blockmap.py geo.json out.png"""
import sys, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
plt.style.use('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/sim/paper.mplstyle')
G = json.load(open(sys.argv[1])); B = json.load(open('blocks.json'))
F = {f['ref']: f for f in G['fps']}
def pad(r, n):
    p = [q for q in F[r]['pads'] if q['n'] == n][0]['bb']; return ((p[0] + p[2]) / 2, (p[1] + p[3]) / 2)
def box(refs, grow=0.3):
    xs, ys = [], []
    for r in refs:
        for c in F[r]['cy']:
            xs += [p[0] for p in c]; ys += [p[1] for p in c]
    return min(xs) - grow, min(ys) - grow, max(xs) + grow, max(ys) + grow
COL = {'noisy': '#d62728', 'quiet': '#1f77b4', 'power': '#ff7f0e', 'rf': '#2ca02c'}
ZONES = [  # (label, kind, refs)
    ('BOOST TPS61178\n(SW, hot loop)', 'noisy', B['BOOST']['refs']),
    ('BUCK\nTPS62933', 'noisy', B['BUCK']['refs']),
    ('CHARGER BQ25792\n(SW1/SW2 links L4/L6)', 'noisy', B['CHG']['refs']),
    ('AMP L\nTAS5805M + LC', 'noisy', B['AMP_L']['refs']),
    ('AMP R\nTAS5805M + LC', 'noisy', B['AMP_R']['refs']),
    ('BATTERY PATH\nXT30, fuse, prot FETs', 'power', B['BATT']['refs']),
    ('PVDD bulk\n3 x 470 uF', 'power', ['C920', 'C401', 'C301']),
    ('USB-C in\nTVS, 47 uF, PD', 'power', ['J601', 'D601', 'C605']),
    ('ESP32-WROVER-E', 'rf', ['U101']),
    ('UI FFC J501', 'quiet', ['J501']),
    ('USB-UART', 'quiet', ['U201']),
    ('I2S mux', 'quiet', ['U501']),
]
fig, ax = plt.subplots(figsize=(11, 4.6))
E = [e for e in G['edge'] if len(e) > 3][0]
ax.add_patch(Polygon(E, closed=True, fc='#f7f7f7', ec='k', lw=1.2, zorder=0))
for f in G['fps']:
    if f['side'] != 'F': continue
    for c in f['cy']: ax.add_patch(Polygon(c, closed=True, fill=False, ec='0.6', lw=0.25, zorder=1))
for lab, kind, refs in ZONES:
    x0, y0, x1, y1 = box(refs)
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=COL[kind], alpha=0.16, ec=COL[kind], lw=1.0, zorder=2))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, lab, ha='center', va='center', fontsize=6.2, color=COL[kind], weight='bold', zorder=6)
# antenna: overhang region + on-board keep-out strip + 25 mm switcher circle
XR = max(p[0] for p in E)
u = F['U101']; ys = [p[1] for c in u['cy'] for p in c]
ax.add_patch(Rectangle((XR, 102.0), 6.3, 18.0, fc=COL['rf'], alpha=0.35, ec=COL['rf'], hatch='///', lw=1, zorder=3))
ax.text(XR + 3.2, 98.5, 'antenna\n(off-board)', fontsize=5.5, color=COL['rf'], ha='center')
for z in G['zones']:
    if z['name'].startswith('ANT') and z['layer'] == 'F.Cu':
        ax.add_patch(Polygon(z['pts'], closed=True, fc='none', ec=COL['rf'], ls='--', lw=1, zorder=3))
ax.add_patch(Circle((XR, 111.0), 25.0, fill=False, ec=COL['rf'], ls=':', lw=1.0, zorder=3))
ax.text(XR - 25.5, 121.8, '25 mm from antenna', fontsize=5.5, color=COL['rf'], va='top', ha='right')
# planned L3 lanes (quiet signals) -- polylines through pad positions
LANES = {}
def lane(pts, c, lab, dy=0):
    LANES[lab] = [(p[0], p[1] + dy) for p in pts]
    xs = [p[0] for p in pts]; ys = [p[1] + dy for p in pts]
    ax.plot(xs, ys, '-', color=c, lw=2.2, alpha=0.85, zorder=5, solid_capstyle='round')
    ax.text(xs[len(xs) // 2 - 1] / 2 + xs[len(xs) // 2] / 2, ys[len(ys) // 2] - 0.8, lab, fontsize=5.5, color=c, ha='center', va='bottom', zorder=7)
mcuI2S = pad('U501', '4'); a1 = pad('U301', '7'); a2 = pad('U401', '7')
lane([mcuI2S, (mcuI2S[0], 86.0), (a2[0], 86.0), a2, (a2[0], 86.0), (a1[0], 86.0), a1], '#9467bd', 'L3: I2S (BCLK/LRCK/SDIN) MCU -> U501 -> amps')
i2c = pad('U101', '36'); c1 = pad('U701', '14')
lane([i2c, (i2c[0] - 1.5, 104.0), (i2c[0] - 1.5, 87.2), (117.6, 87.2), (117.6, 119.9), (c1[0], 119.9), c1], '#8c564b', 'L3: I2C to amps, PD, charger', dy=0)
spi = pad('U101', '30'); j = pad('J501', '5')
lane([spi, (spi[0] - 4, 104), (spi[0] - 4, 90.0), (j[0], 90.0), j], '#17becf', 'SPI/PDM/UI -> J501')
ux = pad('U201', '2'); m = pad('U101', '35')
lane([ux, (ux[0], 85.4), (m[0] + 2.2, 85.4), (m[0] + 2.2, 119.6), m], '#7f7f7f', 'L3: UART (U201 -> MCU)')
usb = pad('U601', '3')
ax.plot([150, usb[0], pad('U201', '6')[0]], [77.5, usb[1], pad('U201', '6')[1]], '-', color='#e377c2', lw=2.2, zorder=5)
ax.text(140, 86.5, 'USB D+/D- (L1/L6 over L2/L5)', fontsize=5.5, color='#e377c2')
# planned L4 power regions
L4 = [('L4 PVDD spine', (123, 86.5, 212, 100.5), '#ff7f0e'),
      ('L4 VSYS band (CHG -> boost, front)', (115, 113.5, 181, 120.3), '#bcbd22'),
      ('L4 3V3 (buck -> MCU)', (186, 75.6, 212, 84.0), '#2ca02c')]
for lab, (x0, y0, x1, y1), c in L4:
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=c, lw=1.3, ls=(0, (4, 2)), zorder=4))
    ax.text(x0 + 0.6, y1 - 0.5, lab, fontsize=5.2, color=c, va='bottom', zorder=7)
from matplotlib.lines import Line2D
h = [Rectangle((0, 0), 1, 1, fc=COL[k], alpha=0.3, ec=COL[k]) for k in ('noisy', 'quiet', 'power', 'rf')] + \
    [Line2D([0], [0], color='#9467bd', lw=2), Rectangle((0, 0), 1, 1, fill=False, ec='k', ls='--')]
ax.legend(h, ['noisy (switchers, class-D)', 'quiet (MCU, UI, UART)', 'power (battery, bulk, VBUS)', 'RF (module, antenna)',
              'planned L3 lanes', 'planned L4 power regions'], loc='upper left', bbox_to_anchor=(0, -0.16), ncol=3, fontsize=6, frameon=False)
x0e = min(p[0] for p in E)
ax.set_xlim(x0e - 2, XR + 9); ax.set_ylim(123.5, 72); ax.set_aspect('equal')
ax.set_xlabel('KiCad X, mm (enclosure X = X - 150)'); ax.set_ylabel('KiCad Y, mm (rear edge at top)')
ax.set_title('Floor plan v1: zoning, blocks and planned lanes (top view)', fontsize=9)
plt.savefig(sys.argv[2], dpi=220, bbox_inches='tight')

# ---- EMC numbers: switch-node copper vs antenna and vs planned lanes ----
import re, math, numpy as np
SW = re.compile(r'^(BST_SW|BUCK_SW|CHG_SW1|CHG_SW2|A[LR]_OUT[AB]_[PN])$')
pts = []
for z in G['zones']:
    if SW.match(z['net']): pts += z['pts']
for t in G['tracks']:
    if SW.match(t[6]):
        n = max(2, int(math.hypot(t[3] - t[1], t[4] - t[2]) / 0.2)); pts += [(t[1] + (t[3] - t[1]) * k / n, t[2] + (t[4] - t[2]) * k / n) for k in range(n + 1)]
for f in G['fps']:
    for p in f['pads']:
        if SW.match(p['net']): pts += [(p['bb'][0], p['bb'][1]), (p['bb'][2], p['bb'][3]), (p['bb'][0], p['bb'][3]), (p['bb'][2], p['bb'][1])]
P = np.array(pts)
ant = (XR, 102.0, XR + 6.3, 120.0)
dx = np.maximum(ant[0] - P[:, 0], 0); dy = np.maximum(np.maximum(ant[1] - P[:, 1], P[:, 1] - ant[3]), 0)
d = np.hypot(dx, dy); print('switch-node copper to antenna: min %.1f mm' % d.min())
for lab, L in LANES.items():
    seg = []
    for (x1, y1), (x2, y2) in zip(L, L[1:]):
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.25)); seg += [(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n) for k in range(n + 1)]
    S = np.array(seg); S = S[(np.hypot(S[:, 0] - L[0][0], S[:, 1] - L[0][1]) > 2.0) & (np.hypot(S[:, 0] - L[-1][0], S[:, 1] - L[-1][1]) > 2.0)]; dd = np.sqrt(((S[:, None, :] - P[None, :, :]) ** 2).sum(-1)).min()
    print('lane %-45s min distance to switch-node copper (any layer, last 2 mm at the pins excluded) %.1f mm' % (lab[:45], dd))
