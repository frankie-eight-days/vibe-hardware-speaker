import json, pickle, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.style.use('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/sim/paper.mplstyle')
R = {t: json.load(open('results/thermal_%s.json' % t)) for t in ('revA', 't4th_nopad', 't4th_pad')}
lab = {'revA': 'rev A (83 cm$^2$)', 't4th_nopad': 'v1, no gap pads (65 cm$^2$)', 't4th_pad': 'v1 + 3 gap pads'}
col = {'revA': '0.55', 't4th_nopad': '#d62728', 't4th_pad': '#1f77b4'}
fig = plt.figure(figsize=(11, 6.2)); gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.05])
parts = ['U301', 'U401', 'U901', 'L901', 'U951', 'U101']
for k, h in enumerate(('h5', 'h10')):
    ax = fig.add_subplot(gs[0, k]); x = np.arange(len(parts))
    for i, t in enumerate(R):
        v = [R[t]['cases']['moderate 2.9 W'][h]['parts'][p]['T_j_C'] for p in parts]
        ax.bar(x + (i - 1) * 0.27, v, 0.27, color=col[t], label=lab[t])
    ax.set_xticks(x); ax.set_xticklabels(parts, fontsize=7); ax.set_ylim(40, 100); ax.set_ylabel('T$_j$, C')
    ax.set_title('Moderate 2.9 W case, h = %s W/m$^2$K' % h[1:], fontsize=8)
    if k == 0: ax.legend(fontsize=6.5, loc='upper right')
ax = fig.add_subplot(gs[0, 2])
cases = [('max sustained', None), ('charge 2 A + moderate', 'U701'), ('Q801 recovery 1.5 W', 'Q801')]
xl = ['sustained output\n(W, Tj <= 125 C)', 'U701 Tj charge\n2 A + play (C)', 'Q801 Tj body-\ndiode recovery (C)']
for i, t in enumerate(R):
    v = [R[t]['max_sustained_W']['h5'], R[t]['cases']['charge 2 A + moderate']['h5']['parts']['U701']['T_j_C'], R[t]['cases']['Q801 recovery 1.5 W']['h5']['parts']['Q801']['T_j_C']]
    b = ax.bar(np.arange(3) + (i - 1) * 0.27, v, 0.27, color=col[t])
    for bb, vv in zip(b, v): ax.text(bb.get_x() + bb.get_width() / 2, vv + 2, '%.0f' % vv, ha='center', fontsize=6)
ax.set_xticks(range(3)); ax.set_xticklabels(xl, fontsize=6.5); ax.set_title('Limits, h = 5 W/m$^2$K', fontsize=8)
for k, t in enumerate(('t4th_nopad', 't4th_pad')):
    M = pickle.load(open('work/maps_%s.pkl' % t, 'rb'))
    T, x0, y0, nx, ny, on = M[('moderate 2.9 W', 5.0)]
    ax = fig.add_subplot(gs[1, 0:2] if False else gs[1, k * 1 + (0 if k == 0 else 0)] if False else gs[1, k])
    im = ax.imshow(np.where(on, T, np.nan), extent=(x0, x0 + nx * 0.5, y0 + ny * 0.5, y0), cmap='inferno', vmin=45, vmax=95)
    ax.set_title(('v1 without gap pads' if k == 0 else 'v1 with gap pads under U301/U401/U701') + ', moderate, h = 5', fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
    if k == 1:
        for (a, b2, c, d) in json.load(open('../t4_th.kicad_pcb.gappads.json')).values():
            ax.add_patch(plt.Rectangle((a, b2), c - a, d - b2, fill=False, ec='c', ls='--', lw=0.8))
cax = fig.add_subplot(gs[1, 2]); cax.axis('off'); fig.colorbar(im, ax=cax, fraction=0.6, label='L1 temperature, C (45 C air)')
fig.suptitle('Thermal pre-check, floor plan v1 vs rev A (sim/postlayout/thermal.py + gap-pad term; pad 15 x 15 mm, 1 mm, 3 W/mK to a 45 C wall)', fontsize=9)
plt.tight_layout(); plt.savefig('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/docs/figures/pcb/floorplan/thermal_precheck.png', dpi=200)
