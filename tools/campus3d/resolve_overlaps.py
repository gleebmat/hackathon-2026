"""Remove geometry overlaps from the generated campus (needs shapely: `uv run --with shapely ...`).

1. Blocks: each building's plain blocks are merged into clean outlines; buildings placed later in ORDER are cut
   by the ones before them, so no two buildings share floor area. Special blocks (one-storey annexes, open halls)
   are cut by their own building's plain blocks too.
2. Rooms: placed in priority order per floor (lecture/seminar rooms and halls, then atrium, offices, restrooms,
   foyers). Each room is trimmed to its own building's outline and to the space still free on that floor.
   Rooms that stay (nearly) rectangular remain rectangles; small leftover offices are dropped.
"""
import math

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

ORDER = ["V", "N", "L", "S", "Z"]
PRIORITY = {"seminar": 4, "hall": 4, "atrium": 3, "office": 2, "wc": 1, "foyer": 0}


def _bpoly(b):
    return Polygon(b["poly"]) if "poly" in b else box(b["x"] - b["w"] / 2, b["z"] - b["d"] / 2,
                                                       b["x"] + b["w"] / 2, b["z"] + b["d"] / 2)


def _rpoly(r):
    return Polygon(r["poly"]) if "poly" in r else box(r["x"] - r["w"] / 2, r["z"] - r["d"] / 2,
                                                       r["x"] + r["w"] / 2, r["z"] + r["d"] / 2)


def _pieces(geom, min_area=1.0):
    geoms = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    return [g for g in geoms if isinstance(g, Polygon) and g.area >= min_area]


def _coords(ring):
    pts = [[round(x, 2), round(z, 2)] for x, z in list(ring.coords)[:-1]]
    return pts


def _block(poly, extra):
    poly = poly.simplify(0.05)
    b = {"poly": _coords(poly.exterior), **extra}
    holes = [_coords(i) for i in poly.interiors if Polygon(i).area > 1.0]
    if holes:
        b["holes"] = holes
    return b


def resolve_blocks(buildings):
    taken = None
    by_id = {b["id"]: b for b in buildings}
    for bid in ORDER:
        bd = by_id[bid]
        plain = [b for b in bd["blocks"] if not ({"floors", "open", "courtyard"} & b.keys())]
        keep = [b for b in bd["blocks"] if "courtyard" in b]          # V main block: left exactly as traced
        special = [b for b in bd["blocks"] if ({"floors", "open"} & b.keys()) and "courtyard" not in b]
        base = unary_union([_bpoly(b) for b in plain + keep]) if plain + keep else None
        new = list(keep)
        if plain:
            u = unary_union([_bpoly(b) for b in plain])
            if keep:
                u = u.difference(unary_union([_bpoly(b) for b in keep]))
            if taken is not None:
                u = u.difference(taken)
            new += [_block(p, {}) for p in _pieces(u)]
        for sb in special:
            p = _bpoly(sb)
            if base is not None:
                p = p.difference(base)
            if taken is not None:
                p = p.difference(taken)
            extra = {k: sb[k] for k in ("floors", "open") if k in sb}
            new += [_block(q, extra) for q in _pieces(p)]
        bd["blocks"] = new
        bd["_footprint"] = unary_union([_bpoly(b) for b in new] + ([_bpoly(b) for b in keep]))
        taken = bd["_footprint"] if taken is None else taken.union(bd["_footprint"])


def _fit(r, region):
    """Trim room r to region. Returns the updated room, or None if too little is left."""
    p = _rpoly(r)
    inter = p.intersection(region)
    if inter.area >= p.area - 0.05:
        return r, p
    pieces = _pieces(inter, 0.5)
    if not pieces:
        return None, None
    q = max(pieces, key=lambda g: g.area)
    if q.area < (3.0 if r["bookable"] else max(4.0, 0.3 * p.area)):
        return None, None
    out = {k: v for k, v in r.items() if k not in ("poly", "angle")}
    if "poly" not in r:
        # axis-aligned room: cut back whichever side loses the least area until nothing forbidden is left
        x0, z0, x1, z1 = p.bounds
        forbidden = p.difference(region)
        ok = False
        for _ in range(6):
            ov = box(x0, z0, x1, z1).intersection(forbidden)
            if ov.area < 0.05:
                ok = True
                break
            ox0, oz0, ox1, oz1 = ov.bounds
            cands = [c for c in [(x0, z0, ox0, z1), (ox1, z0, x1, z1), (x0, z0, x1, oz0), (x0, oz1, x1, z1)]
                     if c[2] - c[0] > 0.5 and c[3] - c[1] > 0.5]
            if not cands:
                break
            x0, z0, x1, z1 = max(cands, key=lambda c: box(*c).area - box(*c).intersection(forbidden).area)
        a = (x1 - x0) * (z1 - z0)
        if ok and a >= 0.6 * q.area and min(x1 - x0, z1 - z0) >= 1.2:
            out.update(x=round((x0 + x1) / 2, 2), z=round((z0 + z1) / 2, 2), w=round(x1 - x0, 2), d=round(z1 - z0, 2))
            return out, box(x0, z0, x1, z1)
        if not r["bookable"]:
            return None, None
        # bookable room that can't stay a clean rectangle: keep its exact trimmed outline (below)
    mrr = q.minimum_rotated_rectangle
    c = list(mrr.exterior.coords)
    e1, e2 = (c[1][0] - c[0][0], c[1][1] - c[0][1]), (c[2][0] - c[1][0], c[2][1] - c[1][1])
    (lx, lz), short = (e1, math.hypot(*e2)) if math.hypot(*e1) >= math.hypot(*e2) else (e2, math.hypot(*e1))
    fill = q.area / mrr.area                     # labels shrink for irregular shapes
    q = q.simplify(0.05)
    pt = q.representative_point() if not q.contains(q.centroid) else q.centroid
    out.update(poly=_coords(q.exterior), x=round(pt.x, 2), z=round(pt.y, 2),
               w=round(math.hypot(lx, lz) * fill, 2), d=round(short * fill, 2), angle=round(math.atan2(lz, lx), 4))
    return out, q


def resolve_rooms(buildings):
    floors = sorted({r["floor"] for bd in buildings for r in bd["rooms"]})
    dropped = 0
    taken = {f: Polygon() for f in range(min(floors), max(floors) + 3)}   # per floor; tall rooms fill several
    for f in floors:
        occupied = taken[f]
        queue = [(bd, r) for bd in buildings for r in bd["rooms"] if r is not None and r["floor"] == f]
        queue.sort(key=lambda x: (-PRIORITY.get(x[1]["type"], 1), -_rpoly(x[1]).area))
        for bd, r in queue:
            fitted, geom = _fit(r, bd["_footprint"].difference(occupied))
            idx = bd["rooms"].index(r)
            if fitted is None:
                bd["rooms"][idx] = None
                dropped += 1
                continue
            bd["rooms"][idx] = fitted
            g = geom.buffer(-0.05)
            occupied = occupied.union(g)
            for k in range(1, fitted.get("storeys", 1)):          # a two-storey hall also blocks the floor above
                taken[f + k] = taken[f + k].union(g)
    for bd in buildings:
        bd["rooms"] = [r for r in bd["rooms"] if r is not None]
        bd.pop("_footprint", None)
    return dropped


def resolve_connectors(buildings):
    """Trim every corridor to the open gap between buildings, so it ends flush at both walls.
    Must run after resolve_blocks (needs the building outlines). Tunnels are split later (split_tunnels)."""
    everything = unary_union([bd["_footprint"] for bd in buildings])
    for bd in buildings:
        for c in bd.get("connectors", []):
            if c.get("tunnel"):
                continue
            pieces = _pieces(_bpoly(c).difference(everything), 0.5)
            if not pieces:
                continue
            x0, z0, x1, z1 = max(pieces, key=lambda g: g.area).bounds
            c.update(x=round((x0 + x1) / 2, 2), z=round((z0 + z1) / 2, 2), w=round(x1 - x0, 2), d=round(z1 - z0, 2))


def _face(everything, x, zc, direction):
    """z of the first building wall hit when walking from (x, zc) north (-1) or south (+1)."""
    from shapely.geometry import LineString
    hit = LineString([(x, zc), (x, zc + direction * 200)]).intersection(everything)
    if hit.is_empty:
        return None
    zs = [c[1] for g in getattr(hit, "geoms", [hit]) for c in g.coords]
    return max(zs) if direction < 0 else min(zs)


def smooth_connectors(buildings, max_shift=8.0, step=0.25):
    """Slide each corridor sideways (as little as possible) until both of its side edges meet flat walls at both
    ends, then make it span exactly from wall to wall, so it joins both buildings cleanly."""
    everything = unary_union([bd["_footprint"] for bd in buildings])
    for bd in buildings:
        for c in bd.get("connectors", []):
            if c.get("tunnel"):
                continue
            half, zc = c["w"] / 2 - 0.05, c["z"]
            best = None
            for i in range(int(max_shift / step) + 1):
                for shift in ((i * step,) if i == 0 else (i * step, -i * step)):
                    x = c["x"] + shift
                    tops = [_face(everything, x + e, zc, -1) for e in (-half, 0, half)]
                    bots = [_face(everything, x + e, zc, +1) for e in (-half, 0, half)]
                    if None in tops or None in bots:
                        continue
                    if max(tops) - min(tops) < 0.05 and max(bots) - min(bots) < 0.05:
                        best = (x, max(tops), min(bots))
                        break
                if best:
                    break
            if best:
                x, z0, z1 = best
                c.update(x=round(x, 2), z=round((z0 + z1) / 2, 2), d=round(z1 - z0, 2))


def split_tunnels(buildings, min_len=2.0):
    """A tunnel runs as one long strip; every stretch of it that lies between two buildings becomes its own corridor,
    so it stops where a building (with its rooms) is in the way and goes on behind it. Stretches that touch a
    building on one end only (past the last one) are dropped."""
    everything = unary_union([bd["_footprint"] for bd in buildings])
    edge = everything.buffer(0.2)
    for bd in buildings:
        keep = []
        for c in bd.get("connectors", []):
            if not c.get("tunnel"):
                keep.append(c)
                continue
            pieces = sorted(_pieces(_bpoly(c).difference(everything), 0.5), key=lambda g: g.bounds[1])
            for p in pieces[:c.get("max_pieces", 9)]:
                x0, z0, x1, z1 = p.bounds
                ends = [box(x0, z0, x1, z0 + 0.05), box(x0, z1 - 0.05, x1, z1)]
                if z1 - z0 >= min_len and all(e.intersects(edge) for e in ends):
                    keep.append({"x": round((x0 + x1) / 2, 2), "z": round((z0 + z1) / 2, 2), "w": round(x1 - x0, 2),
                                 "d": round(z1 - z0, 2), "floors": c["floors"], "tunnel": True})
        bd["connectors"] = keep


def wall_point(buildings, x, z, direction):
    """The point where a line from (x, z) going east (+1) or west (-1) leaves the buildings: a door on that wall."""
    from shapely.geometry import LineString
    everything = unary_union([bd["_footprint"] for bd in buildings])
    hit = LineString([(x - direction * 30, z), (x + direction * 30, z)]).intersection(everything)
    xs = [c[0] for g in getattr(hit, "geoms", [hit]) for c in g.coords]
    return {"x": round(max(xs) if direction > 0 else min(xs), 2), "z": round(z, 2)}
