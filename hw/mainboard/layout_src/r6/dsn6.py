"""6-layer DSN for Freerouting: export, reduce to open connections (revb/reduce2), In1/In3/In4 are planes (layer type power),
board clearance 0.16 (+10 um), wire keep-outs on F.Cu/In2/B.Cu: charger SW window (+1 mm) and antenna area. usage: dsn6.py board drc.json out.dsn"""
import sys,re,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src/revb'); import reduce2
import design6 as D
bp,drcj,out=sys.argv[1:4]; b=pcbnew.LoadBoard(bp)
raw=out.replace('.dsn','_raw.dsn'); pcbnew.ExportSpecctraDSN(b,raw)
dsn,kept,full=reduce2.reduce(drcj,open(raw).read()); print('nets kept',len(kept))
dsn=re.sub(r'(\(rule\n\s*\(width 200\)\n\s*\(clearance )\d+(\))',r'\g<1>160\2',dsn)
# GND pours on the signal layers re-flow around new copper: drop them from the DSN (else they block every wire on that layer)
dsn,ng=re.subn(r'    \(plane GND \(polygon (?:F\.Cu|In2\.Cu|B\.Cu) [^)]*\)\)\n','',dsn); print('GND signal-layer planes dropped',ng)
dsn=dsn.replace('(use_via "Via[0-5]_600:300_um")','(use_via "Via[0-5]_500:250_um" "Via[0-5]_600:300_um")')
if 'Via[0-5]_500:250_um' not in dsn.split('(network')[0]:
    sh=''.join(f'        (shape (circle {l} 5000 0 0))\n' for l in ('F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu'))
    i=dsn.index('    (padstack "Via[0-5]_600:300_um"')
    dsn=dsn[:i]+'    (padstack "Via[0-5]_500:250_um"\n'+sh+'      (attach off)\n    )\n'+dsn[i:]
x0,y0,x1,y1=D.SW_WINDOW; KO=[(x0-1,y0-1,x1+1,y1+1),(59,72,63.3,122),(59,72,75.3,86.0),(59,115.0,75.3,122)]
ko=''
for k,(a,c,e,f) in enumerate(KO):
    for l in ('F.Cu','In2.Cu','B.Cu'):
        ko+=f'    (wire_keepout "ko{k}{l[0:3]}" (polygon {l} 0 {a*1000:.0f} {-c*1000:.0f} {e*1000:.0f} {-c*1000:.0f} {e*1000:.0f} {-f*1000:.0f} {a*1000:.0f} {-f*1000:.0f}))\n'
for k,(a,c,e,f) in enumerate(D.LANDINGS.values()):   # thermal landings: no B.Cu signal copper
    a,c,e,f=a-0.3,c-0.3,e+0.3,f+0.3
    ko+=f'    (wire_keepout "land{k}" (polygon B.Cu 0 {a*1000:.0f} {-c*1000:.0f} {e*1000:.0f} {-c*1000:.0f} {e*1000:.0f} {-f*1000:.0f} {a*1000:.0f} {-f*1000:.0f}))\n'
i=dsn.index('    (via '); dsn=dsn[:i]+ko+dsn[i:]
open(out,'w').write(dsn); print('keepouts',ko.count('wire_keepout'))
