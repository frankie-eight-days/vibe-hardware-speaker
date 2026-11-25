import sys, pcbnew, json
# copper % per layer (KiCad copper polygons / outline area, zones as filled) and mirrored-pair differences; 4- or 6-layer
b=pcbnew.LoadBoard(sys.argv[1])
out={}
ol=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol,True)
A=ol.Area()/1e12
L=[pcbnew.F_Cu]+[pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.In3_Cu,pcbnew.In4_Cu][:b.GetCopperLayerCount()-2]+[pcbnew.B_Cu]
names=['L%d %s'%(i+1,b.GetLayerName(l)) for i,l in enumerate(L)]
for name,l in zip(names,L):
    ps=pcbnew.SHAPE_POLY_SET(); b.ConvertBrdLayerToPolygonalContours(l,ps); ps.Simplify()
    out[name]=round(100*ps.Area()/1e12/A,1)
n=len(L); pairs={'%s-%s'%(names[i].split()[0],names[n-1-i].split()[0]):round(out[names[i]]-out[names[n-1-i]],1) for i in range(n//2)}
print(json.dumps(dict(board_area_mm2=round(A,1),copper_pct=out,mirror_pair_diff_pts=pairs)))
