import pcbnew, json, sys
FP="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
HW="/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/lib"
loc={"Espressif":HW+"/Espressif/Espressif.pretty","speaker":HW+"/speaker/speaker.pretty"}
nl=json.load(open('netlist.json'))
out={}
mm=pcbnew.ToMM
for fpid in sorted(set(c['fp'] for c in nl['comps'].values())):
    lib,name=fpid.split(':')
    path=loc.get(lib,f"{FP}/{lib}.pretty")
    f=pcbnew.FootprintLoad(path,name)
    xs=[];ys=[]
    for g in f.GraphicalItems():
        if g.GetLayer()==pcbnew.F_CrtYd:
            b=g.GetBoundingBox()
            xs+= [mm(b.GetLeft()),mm(b.GetRight())]; ys+=[mm(b.GetTop()),mm(b.GetBottom())]
    cy=[min(xs),min(ys),max(xs),max(ys)] if xs else None
    pads=[]
    for p in f.Pads():
        pos=p.GetPosition(); sz=p.GetSize(pcbnew.F_Cu)
        pads.append([p.GetNumber(),round(mm(pos.x),4),round(mm(pos.y),4),round(mm(sz.x),3),round(mm(sz.y),3),p.GetShape(pcbnew.F_Cu),p.GetAttribute(),round(mm(p.GetDrillSize().x),3), p.GetOrientationDegrees(), p.IsOnLayer(pcbnew.F_Cu)])
    out[fpid]=dict(cy=cy,pads=pads)
    print(fpid, cy, len(pads), flush=True)
json.dump(out,open('fpgeom.json','w'))
