import json,sys,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, numpy as np
s=json.load(open(sys.argv[1])); out=sys.argv[2]
fig,ax=plt.subplots(figsize=(18,5)); C={'F.Cu':'red','In2.Cu':'orange','B.Cu':'blue'}
if len(sys.argv)>3:
    K=np.load(sys.argv[3]); ax.imshow(K,extent=(60,60+K.shape[1]*0.25,73+K.shape[0]*0.25,73),cmap='Greys',alpha=0.25)
for t in s['tracks']: ax.plot([t['x1'],t['x2']],[t['y1'],t['y2']],color=C[t['layer']],lw=1)
for v in s['vias']: ax.plot(v['x'],v['y'],'ko',ms=2)
ax.set_xlim(60,240); ax.set_ylim(121,73); ax.set_aspect('equal'); ax.grid(alpha=.3); plt.tight_layout(); plt.savefig(out,dpi=80)
