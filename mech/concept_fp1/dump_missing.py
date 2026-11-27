import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
H = json.load(open(sys.argv[2]))
refs = sys.argv[3].split(",")
out = {}
for f in b.GetFootprints():
    r = f.GetReference()
    if r not in refs: continue
    side = "B" if f.IsFlipped() else "F"
    cy = f.GetCourtyard(pcbnew.B_Cu if side == "B" else pcbnew.F_Cu)
    bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
    x0, x1 = pcbnew.ToMM(bb.GetLeft()) - 150, pcbnew.ToMM(bb.GetRight()) - 150
    y0, y1 = 100 - pcbnew.ToMM(bb.GetBottom()), 100 - pcbnew.ToMM(bb.GetTop())
    out[r] = dict(side=side, x=[x0, x1], y=[y0, y1], h=H.get(r, [side, 2.0])[1], value=f.GetValue())
json.dump(out, open(sys.argv[4], "w"), indent=1)
print(json.dumps(out)[:600])
