"""Extract copper geometry from a KiCad board into JSON (runs under KiCad's bundled Python).

Usage: <kicad-python> extract_kicad.py BOARD.kicad_pcb OUT.json

Read-only: the board is loaded from a scratch copy, zones are refilled in memory if they
are unfilled, nothing is saved. Output (mm): outline, per-layer per-net merged copper
polygons (outline + holes), tracks, vias, pads, footprints.
"""
import json
import sys

import pcbnew

IU = 1e6  # nm per mm
LAYERS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}
MAXERR = int(0.005 * IU)


def chain_pts(ch):
    return [[ch.CPoint(i).x / IU, ch.CPoint(i).y / IU] for i in range(ch.PointCount())]


def polyset(ps):
    out = []
    for i in range(ps.OutlineCount()):
        out.append({"outline": chain_pts(ps.Outline(i)),
                    "holes": [chain_pts(ps.Hole(i, j)) for j in range(ps.HoleCount(i))]})
    return out


def main(path, out):
    b = pcbnew.LoadBoard(path)
    zones = list(b.Zones())
    if zones and not any(z.IsFilled() for z in zones):
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())

    edge = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(edge, True)
    bb = b.GetBoardEdgesBoundingBox()

    per = {}  # (layer, net) -> SHAPE_POLY_SET

    def add(lname, net, ps):
        key = (lname, net)
        if key not in per:
            per[key] = pcbnew.SHAPE_POLY_SET()
        per[key].Append(ps)

    for z in zones:
        if z.GetIsRuleArea():
            continue
        for lname, lid in LAYERS.items():
            if z.IsOnLayer(lid) and z.HasFilledPolysForLayer(lid):
                ps = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(lid))
                ps.Unfracture()
                add(lname, z.GetNetname(), ps)

    tracks, vias = [], []
    for t in b.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            lay = [ln for ln, lid in LAYERS.items() if t.IsOnLayer(lid)]
            vias.append({"x": t.GetX() / IU, "y": t.GetY() / IU, "drill": t.GetDrillValue() / IU,
                         "dia": t.GetWidth(pcbnew.F_Cu) / IU, "net": net, "layers": lay})
            for ln in lay:
                ps = pcbnew.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(ps, LAYERS[ln], 0, MAXERR, pcbnew.ERROR_INSIDE)
                add(ln, net, ps)
            continue
        lname = t.GetLayerName()
        if lname not in LAYERS:
            continue
        rec = {"layer": lname, "net": net, "w": t.GetWidth() / IU,
               "x1": t.GetStart().x / IU, "y1": t.GetStart().y / IU,
               "x2": t.GetEnd().x / IU, "y2": t.GetEnd().y / IU}
        if t.GetClass() == "PCB_ARC":
            m = t.GetMid()
            rec["xm"], rec["ym"] = m.x / IU, m.y / IU
        tracks.append(rec)
        ps = pcbnew.SHAPE_POLY_SET()
        t.TransformShapeToPolygon(ps, LAYERS[lname], 0, MAXERR, pcbnew.ERROR_INSIDE)
        add(lname, net, ps)

    pads, fps = [], []
    for fp in b.GetFootprints():
        fb = fp.GetBoundingBox(False)
        fps.append({"ref": fp.GetReference(), "value": fp.GetValue(), "x": fp.GetX() / IU,
                    "y": fp.GetY() / IU, "rot": fp.GetOrientationDegrees(),
                    "side": "B" if fp.IsFlipped() else "F",
                    "bbox": [fb.GetLeft() / IU, fb.GetTop() / IU, fb.GetRight() / IU, fb.GetBottom() / IU]})
        for p in fp.Pads():
            net = p.GetNetname()
            lay = [ln for ln, lid in LAYERS.items() if p.IsOnLayer(lid)]
            pb = p.GetBoundingBox()
            pads.append({"ref": fp.GetReference(), "pad": p.GetNumber(), "net": net,
                         "x": p.GetX() / IU, "y": p.GetY() / IU, "layers": lay,
                         "drill": p.GetDrillSize().x / IU,
                         "bbox": [pb.GetLeft() / IU, pb.GetTop() / IU, pb.GetRight() / IU, pb.GetBottom() / IU]})
            for ln in lay:
                ps = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(ps, LAYERS[ln], 0, MAXERR, pcbnew.ERROR_INSIDE)
                add(ln, net, ps)

    copper = []
    for (ln, net), ps in per.items():
        ps.Simplify()
        copper.append({"layer": ln, "net": net, "polys": polyset(ps)})

    data = {"board": path,
            "bbox": [bb.GetLeft() / IU, bb.GetTop() / IU, bb.GetRight() / IU, bb.GetBottom() / IU],
            "outline": polyset(edge), "copper": copper, "tracks": tracks, "vias": vias,
            "pads": pads, "footprints": fps}
    with open(out, "w") as f:
        json.dump(data, f)
    print(f"{path}: {len(copper)} layer-net regions, {len(tracks)} tracks, {len(vias)} vias, "
          f"{len(pads)} pads, {len(fps)} footprints")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
