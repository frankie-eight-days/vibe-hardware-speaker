"""KiCad-native netlist import (equivalent of pcbnew Tools > Update PCB from Schematic on an empty board).
Used ONCE because Konnect 0.12.1 cannot instantiate footprints with custom-shape pads (U701, Q701, Q801, Q802, JP801-803).
Runs KiCad's own pcbnew Python API (FootprintLoad / BOARD.Add / SaveBoard) on the CLOSED board; no text editing.
Also sets the physical stackup to JLC04161H-7628 (no Konnect tool exists for the stackup)."""
import sys, pcbnew
sys.path.insert(0,'.')
from sexp import parse, find, get
BOARD=sys.argv[1]; NET=sys.argv[2]
FP="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
HW="/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/lib"
loc={"Espressif":HW+"/Espressif/Espressif.pretty","speaker":HW+"/speaker/speaker.pretty"}
b=pcbnew.LoadBoard(BOARD)
assert len(b.GetFootprints())==0, "board not empty"
n=parse(open(NET).read())
# nets
netitems={}
for ne in find(get(n,'nets'),'net'):
    name=get(ne,'name')[1]
    ni=pcbnew.NETINFO_ITEM(b,name); b.Add(ni); netitems[name]=ni
padnet={}
for ne in find(get(n,'nets'),'net'):
    name=get(ne,'name')[1]
    for nd in find(ne,'node'):
        r=get(nd,'ref')[1]; p=get(nd,'pin')[1]
        pf=get(nd,'pinfunction'); pt=get(nd,'pintype')
        padnet[(r,p)]=(name, pf[1] if pf else '', pt[1] if pt else '')
mm=pcbnew.FromMM
i=0
for c in find(get(n,'components'),'comp'):
    ref=get(c,'ref')[1]; val=get(c,'value')[1]; fpid=get(c,'footprint')[1]
    lib,name=fpid.split(':')
    f=pcbnew.FootprintLoad(loc.get(lib,f"{FP}/{lib}.pretty"),name)
    f.SetFPIDAsString(fpid)
    f.SetReference(ref); f.SetValue(val)
    ds=get(c,'datasheet'); desc=get(c,'description')
    if ds: f.GetField(pcbnew.FIELD_T_DATASHEET).SetText(ds[1])
    if desc: f.GetField(pcbnew.FIELD_T_DESCRIPTION).SetText(desc[1])
    flds=get(c,'fields')
    for fl in (find(flds,'field') if flds else []):
        fname=get(fl,'name')[1]; fval=fl[2] if len(fl)>2 and isinstance(fl[2],str) else ''
        if fname in ('Footprint','Datasheet','Description','Reference','Value'): continue
        f.SetField(fname,fval)
        fo=f.GetField(fname)
        if fo: fo.SetVisible(False); fo.SetLayer(pcbnew.F_Fab)
    props={get(p,'name')[1]:get(p,'value')[1] for p in find(c,'property')}
    sp=get(c,'sheetpath'); ts=get(c,'tstamps')[1]
    path=get(sp,'tstamps')[1]+ts
    f.SetPath(pcbnew.KIID_PATH(path))
    # symbol is in BOM (netlist carries no exclude_from_bom) -> clear the library footprint's BOM exclusion, as Update PCB does
    if 'exclude_from_bom' not in props: f.SetAttributes(f.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)
    if 'dnp' in props: f.SetAttributes(f.GetAttributes() | pcbnew.FP_DNP)
    f.SetSheetname(props.get('Sheetname','')); f.SetSheetfile(props.get('Sheetfile',''))
    f.SetPosition(pcbnew.VECTOR2I(mm(10+ (i%25)*8), mm(140+(i//25)*8))); i+=1
    for pad in f.Pads():
        k=(ref,pad.GetNumber())
        if k in padnet:
            nm,pfn,ptp=padnet[k]
            pad.SetNet(netitems[nm]); pad.SetPinFunction(pfn); pad.SetPinType(ptp)
    b.Add(f)
# stackup JLC04161H-7628 (jlcpcb.com/impedance, 2026-11-24)
ds=b.GetDesignSettings()
ds.SetCopperLayerCount(4); b.SetCopperLayerCount(4)
b.SetEnabledLayers(b.GetEnabledLayers())
pcbnew.SaveBoard(BOARD,b)
print("footprints",len(b.GetFootprints()),"nets",b.GetNetCount())
