import sys,json,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
plt.style.use('/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/sim/paper.mplstyle')
G=json.load(open(sys.argv[1])); B=json.load(open('blocks.json'))
side=sys.argv[3] if len(sys.argv)>3 else 'F'
col={}
pal={'AMP_L':'tab:red','AMP_R':'tab:red','BOOST':'tab:orange','BUCK':'tab:olive','CHG':'tab:purple','BATT':'tab:brown'}
for n,b in B.items():
    for r in b['refs']: col[r]=pal[n]
fig,ax=plt.subplots(figsize=(16,6))
for e in G['edge']: ax.plot([p[0] for p in e],[p[1] for p in e],'k-',lw=1)
for z in G['zones']:
    if z['name'].startswith(('GAPPAD','ANT')) and z['layer']==('F.Cu' if side=='F' else 'B.Cu') or (z['name'].startswith('ANT') and z['layer']=='F.Cu'):
        ax.add_patch(Polygon(z['pts'],closed=True,fc='none',ec='red',lw=0.8,ls='--')); ax.text(z['pts'][0][0],z['pts'][0][1],z['name'],fontsize=4,color='red'); continue
    if z['layer']==('F.Cu' if side=='F' else 'B.Cu') and not z['name'].startswith(('L1_','L2_','L3_','L4_','L5_')):
        ax.add_patch(Polygon(z['pts'],closed=True,fc='0.8',ec='0.5',lw=0.3,alpha=0.6))
for t in G['tracks']:
    if (t[0]=='F.Cu')==(side=='F'): ax.plot([t[1],t[3]],[t[2],t[4]],'-',color='0.4',lw=t[5]*2)
for f in G['fps']:
    if f['side']!=side: continue
    for c in f['cy']: ax.add_patch(Polygon(c,closed=True,fill=True,fc=col.get(f['ref'],'tab:blue'),alpha=0.15,ec=col.get(f['ref'],'tab:blue'),lw=0.5))
    if f['cy']:
        xs=[p[0] for p in f['cy'][0]];ys=[p[1] for p in f['cy'][0]]
        ax.text((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,f['ref'],fontsize=3.5,ha='center',va='center')
ax.set_aspect('equal'); ax.invert_yaxis(); ax.grid(lw=0.2)
ax.set_title(sys.argv[4] if len(sys.argv)>4 else '', fontsize=10); ax.set_xlabel('KiCad X, mm'); ax.set_ylabel('KiCad Y, mm (rear edge at top)')
from matplotlib.patches import Patch
ax.legend([Patch(fc=c,alpha=0.3,ec=c) for c in ('tab:red','tab:orange','tab:olive','tab:purple','tab:brown','tab:blue')],['amp blocks','boost block','buck block','charger block','battery block','free parts'],loc='upper left',bbox_to_anchor=(0,-0.12),ncol=6,frameon=False,fontsize=8)
plt.savefig(sys.argv[2],dpi=150,bbox_inches='tight')
