"""KiCad-native step (approved exception, see LAYOUT_NOTES): run on the CLOSED board after Konnect saved it.
1) Restore via nets that KiCad's connectivity update reassigned to an overlapping zone (Konnect add_via has no 'free via' control),
   and mark every via that is not attached to a track as a free via so the net sticks.
2) Import the Freerouting session (KiCad's own File > Import > Specctra Session).
3) Refill zones and save."""
import sys, pcbnew
bp,ref,ses=sys.argv[1:4]
mm=pcbnew.ToMM
b=pcbnew.LoadBoard(bp); r=pcbnew.LoadBoard(ref)
n0=len(b.GetTracks())
ok=pcbnew.ImportSpecctraSES(b,ses) if ses!='-' else 'skipped'
want={(round(mm(t.GetPosition().x),3),round(mm(t.GetPosition().y),3)):t.GetNetname() for t in r.GetTracks() if t.GetClass()=='PCB_VIA'}
fixed=0; free=0
ends=set()
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA':
        ends.add((round(mm(t.GetStart().x),3),round(mm(t.GetStart().y),3))); ends.add((round(mm(t.GetEnd().x),3),round(mm(t.GetEnd().y),3)))
for t in b.GetTracks():
    if t.GetClass()!='PCB_VIA': continue
    k=(round(mm(t.GetPosition().x),3),round(mm(t.GetPosition().y),3))
    if k in want and t.GetNetname()!=want[k]:
        t.SetNet(b.FindNet(want[k])); fixed+=1
    if k not in ends: t.SetIsFree(True); free+=1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(bp,b)
print('via nets restored',fixed,'free vias',free,'SES import',ok,'items',n0,'->',len(b.GetTracks()))
