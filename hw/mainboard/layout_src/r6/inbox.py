"""inbox.py board x0 y0 x1 y1 : pads, tracks, vias in a box"""
import sys,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM; x0,y0,x1,y1=map(float,sys.argv[2:6])
ins=lambda x,y: x0<=x<=x1 and y0<=y<=y1
for f in b.GetFootprints():
    for p in f.Pads():
        x,y=mm(p.GetX()),mm(p.GetY())
        if ins(x,y): print('pad %s.%s %s (%.2f,%.2f) %s %.2fx%.2f'%(f.GetReference(),p.GetNumber(),p.GetNetname().split('/')[-1],x,y,'B' if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else 'F',mm(p.GetSize(pcbnew.F_Cu).x),mm(p.GetSize(pcbnew.F_Cu).y)))
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA':
        if ins(mm(t.GetX()),mm(t.GetY())): print('via %s (%.2f,%.2f) %.2f/%.2f'%(t.GetNetname().split('/')[-1],mm(t.GetX()),mm(t.GetY()),mm(t.GetWidth(pcbnew.F_Cu)),mm(t.GetDrillValue())))
    elif ins(mm(t.GetStart().x),mm(t.GetStart().y)) or ins(mm(t.GetEnd().x),mm(t.GetEnd().y)):
        print('trk %s %s (%.2f,%.2f)-(%.2f,%.2f) w%.2f %s'%(t.GetNetname().split('/')[-1],b.GetLayerName(t.GetLayer()),mm(t.GetStart().x),mm(t.GetStart().y),mm(t.GetEnd().x),mm(t.GetEnd().y),mm(t.GetWidth()),t.m_Uuid.AsString()[:8]))
