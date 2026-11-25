import sys,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
for r in sys.argv[2].split(','):
    f=b.FindFootprintByReference(r); print(r,f.GetValue(),[round(mm(f.GetX()),2),round(mm(f.GetY()),2),f.GetOrientationDegrees()],' '.join('%s:%s(%.2f,%.2f)'%(p.GetNumber(),p.GetNetname().split('/')[-1],mm(p.GetX()),mm(p.GetY())) for p in f.Pads()))
