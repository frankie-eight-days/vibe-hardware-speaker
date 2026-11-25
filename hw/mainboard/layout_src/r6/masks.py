"""k3 (In2) / k4 (B.Cu) keep-out masks for bus6.py: charger SW window (+1 mm) on both; antenna handled in bus6."""
import numpy as np,design6 as D
xs=np.arange(60,240,0.25)+0.125; ys=np.arange(73,121,0.25)+0.125; X,Y=np.meshgrid(xs,ys)
x0,y0,x1,y1=D.SW_WINDOW; W=(X>x0-1)&(X<x1+1)&(Y>y0-1)&(Y<y1+1)
K4=W.copy()
for a,c,e,f in D.LANDINGS.values(): K4|=(X>a-0.3)&(X<e+0.3)&(Y>c-0.3)&(Y<f+0.3)
import pcbnew
b=pcbnew.LoadBoard('s3.kicad_pcb'); mm=pcbnew.ToMM
EDGE=(Y<76.05)|(Y>119.95)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH: EDGE|=np.hypot(X-mm(p.GetX()),Y-mm(p.GetY()))<mm(p.GetDrillSizeX())/2+0.55
W|=EDGE; K4|=EDGE
np.save('k3.npy',W); np.save('k4.npy',K4); print(W.shape,W.sum())
