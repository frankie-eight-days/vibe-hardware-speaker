"""non-GND B.Cu copper (tracks, vias, pads, zones) inside candidate thermal-landing boxes. usage: landchk.py board"""
import sys,pcbnew,design6 as D
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
for name,(x0,y0,x1,y1) in D.LANDINGS.items():
    hit=[]
    ins=lambda x,y: x0-0.3<=x<=x1+0.3 and y0-0.3<=y<=y1+0.3
    for t in b.GetTracks():
        if t.GetNetname()=='GND': continue
        if t.GetClass()=='PCB_VIA':
            if ins(mm(t.GetX()),mm(t.GetY())): hit.append('via '+t.GetNetname().split('/')[-1])
        elif t.GetLayer()==pcbnew.B_Cu and (ins(mm(t.GetStart().x),mm(t.GetStart().y)) or ins(mm(t.GetEnd().x),mm(t.GetEnd().y))): hit.append('trk '+t.GetNetname().split('/')[-1])
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.B_Cu) and p.GetNetname()!='GND' and ins(mm(p.GetX()),mm(p.GetY())): hit.append('pad %s.%s'%(f.GetReference(),p.GetNumber()))
    import collections; print(name,(x0,y0,x1,y1),dict(collections.Counter(hit)))
