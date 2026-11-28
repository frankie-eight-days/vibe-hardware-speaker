"""FACET cross-section: an irregular rounded octagon, constant along X.

Pure-python (no numpy) so FreeCAD, Blender and the .venv scorecard can all import it.

Coordinates as docs/mech_envelope.md, in the (Y, Z) section plane: -Y = front, +Z = up.
A facet is a half-plane n . p <= h with outward normal n(phi) = (-cos phi, sin phi), phi measured from
the front toward the top (phi 0 front, 90 top, 180 rear, 270 bottom), the same convention as the concept.

Design logic (docs/id/facet.md):
  * front, 40 deg shoulder and -40 deg lower facets are tangent to the old R 47.5 circle, so the woofer
    tunnel is never shallower than today's and the tweeter face centre stays exactly at today's
    (-36.4, 30.5) with its axis 40 deg up (pod, PR clearance and UI-board clearance unchanged);
  * top flat at Z 47.5 (display lens flush, as today), bottom flat at Z -44.5 (as today);
  * rear flat at Y 42.5 (inner 39.5 vs battery swell 39.05);
  * rear-top / rear-bottom 45 deg chamfers place the top flat edge at Y +25 (lens fits) and the
    desk flat edge at Y +26.9 (desk flat 51.6 mm corner to corner).
"""
import math

WALL = 3.0
# (name, phi_deg, h_outer_mm)
FACETS = [
    ("front", 0.0, 47.5),
    ("shoulder", 40.0, 47.5),        # tweeter facet: normal 40 deg above horizontal
    ("top", 90.0, 47.5),
    ("rear_top", 135.0, 0.70710678 * (25.0 + 47.5)),
    ("rear", 180.0, 42.5),
    ("rear_bottom", 225.0, 0.70710678 * (26.9 + 44.5)),
    ("bottom", 270.0, 44.5),
    ("lower_front", 320.0, 47.5),
]
# outer corner radius between facet i and i+1 (cyclic)
RADII = [10.0, 5.0, 5.0, 8.0, 8.0, 5.0, 5.0, 10.0]


def normal(phi):
    a = math.radians(phi)
    return (-math.cos(a), math.sin(a))


def _isect(n1, h1, n2, h2):
    det = n1[0] * n2[1] - n1[1] * n2[0]
    return ((h1 * n2[1] - h2 * n1[1]) / det, (n1[0] * h2 - n2[0] * h1) / det)


def geometry(offset=0.0, facets=None, radii=None):
    """Rounded polygon offset inward by `offset` (0 = outer skin, WALL = inner skin).
    Returns list of corners: dict(vertex, centre, r, t0 (tangent on facet i), t1 (tangent on facet i+1), mid)."""
    facets = facets or FACETS
    radii = radii or RADII
    out = []
    n = len(facets)
    for i in range(n):
        _, p1, h1 = facets[i]
        _, p2, h2 = facets[(i + 1) % n]
        n1, n2 = normal(p1), normal(p2)
        h1 -= offset
        h2 -= offset
        r = max(radii[i] - offset, 0.0)
        v = _isect(n1, h1, n2, h2)
        c = _isect(n1, h1 - r, n2, h2 - r)
        t0 = (c[0] + r * n1[0], c[1] + r * n1[1])
        t1 = (c[0] + r * n2[0], c[1] + r * n2[1])
        bm = (n1[0] + n2[0], n1[1] + n2[1])
        L = math.hypot(*bm)
        mid = (c[0] + r * bm[0] / L, c[1] + r * bm[1] / L)
        out.append(dict(vertex=v, centre=c, r=r, t0=t0, t1=t1, mid=mid, a=p1, b=p2))
    return out


def polyline(offset=0.0, n_arc=12):
    """Dense polyline (list of (y, z)) of the rounded section, returned CCW in the (Y, Z) plane."""
    g = geometry(offset)
    pts = []
    for k, cn in enumerate(g):
        c, r = cn["centre"], cn["r"]
        a0 = math.atan2(cn["t0"][1] - c[1], cn["t0"][0] - c[0])
        a1 = math.atan2(cn["t1"][1] - c[1], cn["t1"][0] - c[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi   # short way round
        a1 = a0 + da
        if r < 1e-9:
            pts.append(cn["vertex"])
            continue
        for j in range(n_arc + 1):
            a = a0 + (a1 - a0) * j / n_arc
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return pts[::-1]          # facets run front->top->rear (clockwise in Y,Z); reverse to CCW


def area(pts):
    s = 0.0
    for i in range(len(pts)):
        y0, z0 = pts[i]
        y1, z1 = pts[(i + 1) % len(pts)]
        s += y0 * z1 - y1 * z0
    return 0.5 * abs(s)


def inside(pts, p, tol=1e-9):
    """Convex CCW polygon containment; returns signed min distance to edges (>0 inside)."""
    dmin = 1e9
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        ex, ez = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ex, ez)
        if L < 1e-12:
            continue
        # inward normal of a CCW polygon is (-ez, ex)
        d = ((p[0] - a[0]) * (-ez) + (p[1] - a[1]) * ex) / L
        dmin = min(dmin, d)
    return dmin


def facet_flats(offset=0.0):
    """Per facet: straight length between the fillet tangent points, and corner-to-corner width."""
    g = geometry(offset)
    n = len(g)
    res = {}
    for i in range(n):
        prev, cur = g[i - 1], g[i]
        name = FACETS[i][0]
        flat = math.dist(prev["t1"], cur["t0"])
        sharp = math.dist(prev["vertex"], cur["vertex"])
        res[name] = dict(flat_mm=round(flat, 2), corner_to_corner_mm=round(sharp, 2),
                         from_=[round(v, 2) for v in prev["t1"]], to=[round(v, 2) for v in cur["t0"]])
    return res


if __name__ == "__main__":
    import json
    po, pi = polyline(0.0, 24), polyline(WALL, 24)
    print("outer area cm2", round(area(po) / 100, 2), "inner area cm2", round(area(pi) / 100, 2))
    print(json.dumps(facet_flats(0.0), indent=1))
