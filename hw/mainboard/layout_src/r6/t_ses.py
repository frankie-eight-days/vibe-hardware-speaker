import pcbnew,sesw
b=pcbnew.LoadBoard('t6.kicad_pcb'); n0=len(b.GetTracks())
for t in b.GetTracks(): t.SetLocked(True)
L=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
sesw.write('t.ses',[dict(net='/mcu/LCD_SCLK',layer='In2.Cu',w=0.2,x1=100,y1=80,x2=110,y2=80)],[dict(net='/mcu/LCD_SCLK',x=100,y=80,size=0.6,drill=0.3)],L)
print(pcbnew.ImportSpecctraSES(b,'t.ses'), n0, len(b.GetTracks()), sum(t.IsLocked() for t in b.GetTracks()))
new=[t for t in b.GetTracks() if not t.IsLocked()]
for t in new: print(t.GetClass(), b.GetLayerName(t.GetLayer()), t.GetNetname(), pcbnew.ToMM(t.GetStart()), pcbnew.ToMM(t.GetWidth()))
