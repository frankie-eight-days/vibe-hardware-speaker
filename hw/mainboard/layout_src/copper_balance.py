import sys, pcbnew, json
b=pcbnew.LoadBoard(sys.argv[1])
out={}
ol=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol,True)
A=ol.Area()/1e12
for name,l in (('L1 F.Cu',pcbnew.F_Cu),('L2 In1.Cu',pcbnew.In1_Cu),('L3 In2.Cu',pcbnew.In2_Cu),('L4 B.Cu',pcbnew.B_Cu)):
    ps=pcbnew.SHAPE_POLY_SET(); b.ConvertBrdLayerToPolygonalContours(l,ps); ps.Simplify()
    out[name]=round(100*ps.Area()/1e12/A,1)
print(json.dumps(dict(board_area_mm2=round(A,1),copper_pct=out)))
