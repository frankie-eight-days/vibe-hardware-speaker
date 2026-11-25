"""GND return vias next to every fast-net layer change (criterion 2): a GND via within 2 mm of each I2S/SPI/PDM/USB via.
usage: stitchfast.py board spec_out.json"""
import sys,json,math,re,numpy as np,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
bp,outf=sys.argv[1:3]; b=pcbnew.LoadBoard(bp); mm=pcbnew.ToMM; F=pcbnew.FromMM
FAST=re.compile(r'(I2S|LCD_|PDM_|USB_D|IO18_R|IO26_R|IO32_R|IO23_R)')
def gnds():
    g=[(mm(t.GetX()),mm(t.GetY())) for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
    return g+[(mm(p.GetX()),mm(p.GetY())) for p in b.GetPads() if p.GetNetname()=='GND' and p.GetDrillSizeX()>0]
G=gnds(); V=[]; miss=[]
ANT=lambda x,y: x<63.3 or (x<75.3 and (y<86 or y>115))
for v in [t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and FAST.search(t.GetNetname())]:
    x,y=mm(v.GetX()),mm(v.GetY())
    if any((x-a)**2+(y-c)**2<=4.0 for a,c in G): continue
    R=arouter.Router(b,(x-2.5,y-2.5,x+2.5,y+2.5),res=0.05,layers=('F.Cu',))
    Bv=np.zeros(R.X.shape,bool)
    for l in R.all: Bv|=R.blocked(l,'GND',0.25+0.2)
    done=False
    for r in (0.9,1.1,1.3,1.5,1.7,1.9):
        for a in np.linspace(0,2*math.pi,32,endpoint=False):
            cx,cy=float(x+r*math.cos(a)),float(y+r*math.sin(a))
            if ANT(cx,cy) or cy<75.9 or cy>120.1 or cx>239.1: continue
            i=int(round((cx-R.x0)/R.res)); j=int(round((cy-R.y0)/R.res))
            if Bv[j,i]: continue
            vi=pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(F(cx),F(cy))); vi.SetWidth(F(0.5)); vi.SetDrill(F(0.25)); vi.SetNet(b.FindNet('GND')); vi.SetIsFree(True); vi.SetLocked(True); b.Add(vi)
            V.append(dict(net='GND',x=round(cx,3),y=round(cy,3),size=0.5,drill=0.25)); G.append((cx,cy)); done=True; break
        if done: break
    if not done: miss.append((v.GetNetname(),round(x,2),round(y,2)))
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(bp,b)
json.dump(dict(tracks=[],vias=V),open(outf,'w')); print('GND return vias added',len(V),'missed',miss)
