"""t1 -> t2: native-style deletions DEL2, rip A* BAT_TS fan-out, add FIX2, write jobs for the U701 fan-out and small leftovers."""
import json,pcbnew,design6 as D
b=pcbnew.LoadBoard('t1.kicad_pcb'); F=pcbnew.FromMM
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in D.DEL2: b.Remove(t)
pcbnew.SaveBoard('t2.kicad_pcb',b)
