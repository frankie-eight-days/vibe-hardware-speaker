# Read-only: JLC BOM + CPL from the saved board. Excludes DNP (DNP field == "DNP"; KiCad DNP flag is unset, schematic S10),
# board-only items, and parts without an LCSC number (test pads, solder jumpers, DNP header).
import sys, csv, pcbnew, collections
b=pcbnew.LoadBoard(sys.argv[1]); out=sys.argv[2]; mm=pcbnew.ToMM
rows=[]; skipped=[]
for f in b.GetFootprints():
    ref=f.GetReference()
    if f.GetAttributes() & pcbnew.FP_BOARD_ONLY: continue
    dnp=f.GetFieldText('DNP') if f.HasField('DNP') else ''
    lcsc=f.GetFieldText('LCSC') if f.HasField('LCSC') else ''
    if dnp.strip().upper()=='DNP': skipped.append((ref,'DNP')); continue
    if not lcsc.strip(): skipped.append((ref,'no LCSC')); continue
    p=f.GetPosition()
    rows.append(dict(ref=ref,val=f.GetValue(),fp=f.GetFPIDAsString().split(':')[-1],lcsc=lcsc,x=round(mm(p.x)-60,3),y=round(121-mm(p.y),3),rot=round(f.GetOrientationDegrees()%360,1),layer='Bottom' if f.IsFlipped() else 'Top'))
g=collections.OrderedDict()
for r in sorted(rows,key=lambda r:r['ref']):
    g.setdefault((r['val'],r['fp'],r['lcsc']),[]).append(r['ref'])
with open(out+'/speaker_main_BOM_JLC.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['Comment','Designator','Footprint','LCSC Part #','Quantity'])
    for (v,fp,l),refs in g.items(): w.writerow([v,','.join(refs),fp,l,len(refs)])
with open(out+'/speaker_main_CPL_JLC.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for r in sorted(rows,key=lambda r:r['ref']): w.writerow([r['ref'],f"{r['x']}mm",f"{r['y']}mm",r['layer'],r['rot']])
print('placed',len(rows),'lines',len(g),'skipped',len(skipped)); print(skipped)
