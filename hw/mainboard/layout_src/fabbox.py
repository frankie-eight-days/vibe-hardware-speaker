import pcbnew, json
FP="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
HW="/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/lib"
loc={"Espressif":HW+"/Espressif/Espressif.pretty","speaker":HW+"/speaker/speaker.pretty"}
g=json.load(open('fpgeom.json'))
mm=pcbnew.ToMM
for fpid in g:
    lib,name=fpid.split(':')
    f=pcbnew.FootprintLoad(loc.get(lib,f"{FP}/{lib}.pretty"),name)
    xs=[];ys=[]
    for it in f.GraphicalItems():
        if it.GetLayer()==pcbnew.F_Fab and it.GetClass()!='PCB_TEXT':
            b=it.GetBoundingBox(); xs+=[mm(b.GetLeft()),mm(b.GetRight())]; ys+=[mm(b.GetTop()),mm(b.GetBottom())]
    g[fpid]['fab']=[min(xs),min(ys),max(xs),max(ys)] if xs else None
    h=None
    for m in f.Models(): h=m.m_Filename
    g[fpid]['model']=h
json.dump(g,open('fpgeom.json','w'))
for k in g:
  if 'Conn' in k or 'CP_' in k or 'FXL' in k or 'ESP' in k or 'SW_' in k: print(k.split(':')[1][:40], 'fab',[round(v,2) for v in g[k]['fab']] if g[k]['fab'] else None,'cy',g[k]['cy'])
