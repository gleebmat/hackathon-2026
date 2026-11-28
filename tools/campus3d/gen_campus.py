"""Build web/map3d/campus.json (the 3D campus map; the backend reads its bookable rooms) from the real AAU floor plans
in tools/campus3d/aau_plan.json (made by fetch_plan.py from campusplan.aau.at).

- Buildings V, N, Z, L (library), S and O (Nexus), every floor the plan has, real room numbers.
- Building shells: all spaces of a building on a floor, joined; courtyards (big unnamed "corridor" spaces) left out.
  Each piece of a building gets the floors it really has, so e.g. the bridges between Z and S exist on floor 1 only.
- Rooms: teaching rooms, offices and toilets. Corridors, stairs, lifts, storage and technical rooms are part of the
  shell but not drawn as rooms. Bookable: seminar rooms, lecture halls, computer and group-work rooms (real capacity).
- Exception: Z.1.04 is our sensor-board room (BOARD_ROOM); in reality an office, here a 51-seat seminar room.

Usage: uv run --with shapely python tools/campus3d/gen_campus.py
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from shapely.affinity import rotate
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "web" / "map3d" / "campus.json"

BUILDINGS = [  # id, name, floor height (m)
    ("V", "Vorstufe", 3.6), ("N", "Nordtrakt", 3.8), ("Z", "Zentralgebäude", 4.0), ("L", "Bibliothek", 3.8),
    ("S", "Südtrakt", 3.8), ("O", "Nexus", 3.6),
]
TEACHING, OFFICE, CORRIDOR, WC, STAIRS, LIFT, STORAGE = 6, 63, 44, 91, 79, 33, 94
BOOKABLE_NAMES = {"Seminarraum": "Seminar room", "Computerraum": "Computer room", "Gruppenarbeitsraum": "Group work room",
                  "Studierendenarbeitsraum": "Student work room"}
OTHER_NAMES = {"Lesesaal": "Reading room", "Leseraum": "Reading room", "Labor": "Lab", "Katalograum": "Catalogue room",
               "Büro": "Office", "Besprechungsraum": "Meeting room", "Küche": "Kitchen", "Kopierraum": "Copy room"}
BOARD_ROOM = "Z.1.04"
# Offices worth drawing: real offices and meeting rooms, box-shaped and not tiny. Kitchens, server, copy, technical and
# workshop rooms that the plan files as "office" are part of the building but not drawn; toilets aren't drawn either.
REAL_OFFICES = {"Büro", "Großraumbüro", "Besprechungsraum", "Projektraum"}
MIN_OFFICE_AREA = 6.0
BOX_FILL = 0.85        # area / its tightest rectangle: at least this to count as box-shaped
OUTLINE_TOLERANCE = 0.35   # m: building outlines are simplified this much (fewer polygons, same look)
ROOM_TOLERANCE = 0.2       # m: room outlines (lecture-hall fans keep their shape)
COURTYARD_MIN_AREA = 150   # unnamed "corridor" spaces this big are courtyards, not building
SKIP_ROOMS = {"Z.1.29"}    # Omansaal: left out of the map on request
MIN_PIECE = 40.0           # m2: smaller building pieces (stair and lift shafts, odd cells) join their neighbour
MIN_PIECE_WIDTH = 1.6      # m: thinner pieces too
MAX_FILLED_HOLE = 80.0     # m2: shafts and small light wells inside a building are filled
LINK_WIDTH = 8.0           # m: narrower parts of a building that reach another building are links (bridges,
                           # corridors); the map hides them when one building is shown on its own
ENTRANCE_FLOORS = {"O": {0}}   # floors with doors to the outside; others: 0 and 1 (the campus slopes up to Z)
# Entrances the door detection misses (seen on campusplan.aau.at): building, floor, x, z, outward direction.
EXTRA_DOORS = [("V", 1, -7.2, -26.6, (1, 0)),     # V north-west: the entrance building with its stairs
               ("O", 0, 242.0, 12.0, (0, 1)),     # Nexus: south side of the small west ground-floor part
               ("O", 0, 261.0, 11.5, (1, 0))]     # Nexus: east side of the ground floor, near the south-east corner
MANUAL_DOORS = {"O"}       # buildings whose entrances are only the EXTRA_DOORS (the plan's doors there are not entrances)
PILLARS = {"O"}            # buildings whose upper floors overhang the ground floor: legs under the overhang corners
PILLAR_SIZE = 1.2          # m
# Coffee and vending machines on floor 1, roughly where they are (x, z in metres); each is moved to the nearest free
# spot in the building (not in a room, a doorway or another machine), its back against the nearest wall.
MACHINES = [("coffee", -23.6, -2.6), ("coffee", -23.6, -1.2), ("coffee", 122.9, 31.6), ("coffee", 250.5, 9.3),
            ("coffee", 117.6, 71.2), ("vending", 120.2, 71.2), ("vending", 122.9, 71.2),
            ("coffee", 121.56, 142.9, (0, 1))]   # a direction given: placed exactly there, facing that way
MACHINE_FLOOR = 1
MACHINE_GAP = 0.42         # m from a room's wall to the machine's centre: its back touches the wall
OUTER_WALL_GAP = 0.57      # from a building wall (drawn 0.3 m thick on the outline): back touches its inner face
# Corrections: parts of a floor left out of the model (building, floor, outline). Z floor 1: the strip of storage,
# prep rooms and toilets behind HS 1 and HS 2 reads as thick wall; the hall ends right behind the halls.
CUTS = [("Z", 1, [(116.4, 66.0), (145.5, 66.0), (145.5, 71.33), (132.09, 70.97), (132.1, 70.74), (127.37, 70.61),
                  (116.53, 70.54), (116.4, 70.54)])]


def poly(s):
    g = Polygon(s["poly"], s.get("holes", []))
    return g if g.is_valid else max(rings(make_valid(g)), key=lambda p: p.area, default=g.buffer(0))   # repair


def is_courtyard(s):
    return s["type"] == CORRIDOR and not s["code"] and poly(s).area > COURTYARD_MIN_AREA


def is_box(g):
    """Roughly rectangular (an office), not an odd leftover shape."""
    r = g.minimum_rotated_rectangle
    return r.area > 0 and g.area / r.area >= BOX_FILL


def rings(geom):
    for p in getattr(geom, "geoms", [geom]):
        if isinstance(p, Polygon) and p.area > 2:
            yield p


def coords(ring):
    return [[round(x, 2), round(z, 2)] for x, z in list(ring.coords)[:-1]]


def floor_outlines(by_floor, taken, cuts=()):
    """Each floor's outline: its spaces joined (small gaps closed), minus what earlier buildings already cover."""
    out = {}
    for f, gs in by_floor.items():
        g = unary_union(gs).buffer(0.4, join_style=2).buffer(-0.4, join_style=2).simplify(OUTLINE_TOLERANCE)
        if f in taken:
            g = g.difference(taken[f])
        for cf, pts in cuts:
            if cf == f:
                g = g.difference(Polygon(pts))
        out[f] = unary_union([p for p in rings(g) if p.area >= 8])   # drop slivers
    return out


def polys(geom):
    for p in getattr(geom, "geoms", [geom]):
        if isinstance(p, Polygon) and not p.is_empty:
            yield p


def tidy(g):
    g = g.buffer(0.02, join_style=2).buffer(-0.02, join_style=2)
    try:
        return set_precision(g, 0.01)
    except Exception:            # GEOS can trip over rounding a tricky shape: round a repaired copy instead
        return set_precision(make_valid(g.buffer(0)), 0.01)


def shell_blocks(outlines, taken):
    """Building pieces with the floors they exist on: the floor outlines are cut into cells by all their edges, cells
    with the same floors are joined. Small or thin pieces (shafts, odd cells) join the neighbour they share the most
    wall with, so the model has no clutter of tiny boxes; small holes are filled. Every run of consecutive floors
    becomes one block."""
    lines = unary_union([g.boundary for g in outlines.values()])
    groups = defaultdict(list)
    for cell in polygonize(lines):
        pt = cell.representative_point()
        fl = tuple(f for f in sorted(outlines) if outlines[f].contains(pt))
        if fl:
            groups[fl].append(cell)
    pieces = [(p, fl) for fl, cells in groups.items() for p in polys(tidy(unary_union(cells)))]

    def small(p):
        return p.area < MIN_PIECE or p.buffer(-MIN_PIECE_WIDTH / 2, join_style=2).is_empty

    while True:
        bad = sorted((i for i, (p, _) in enumerate(pieces) if small(p)), key=lambda i: pieces[i][0].area)
        if not bad:
            break
        p, _ = pieces.pop(bad[0])
        shared = [(p.boundary.intersection(q.buffer(0.05)).length, j) for j, (q, _) in enumerate(pieces)]
        length, j = max(shared, default=(0, None))
        if j is not None and length > 0.3:          # an isolated small piece is dropped
            if any(f in taken and p.intersection(taken[f]).area > 0.1 for f in pieces[j][1]):
                continue                             # another building is there on the neighbour's floors: drop it
            q, fq = pieces.pop(j)
            pieces.extend((m, fq) for m in polys(tidy(unary_union([q, p]))))
    merged = defaultdict(list)
    for p, fl in pieces:
        merged[fl].append(p)
    blocks = []
    for fl, ps in merged.items():
        runs, run = [], [fl[0]]
        for f in fl[1:]:
            if f == run[-1] + 1:
                run.append(f)
            else:
                runs.append(run)
                run = [f]
        runs.append(run)
        for p in polys(tidy(unary_union(ps))):
            holes = [coords(h) for h in p.interiors if Polygon(h).area > MAX_FILLED_HOLE]
            for r in runs:
                b = {"poly": coords(p.exterior), "floors": r}
                if holes:
                    b["holes"] = holes
                blocks.append(b)
    return blocks


def split_links(buildings):
    """Marks the parts of each building that connect it to another one (narrower than LINK_WIDTH and touching the
    other building) as separate blocks with "link": true."""
    shapes = {b["id"]: [Polygon(x["poly"], x.get("holes", [])) for x in b["blocks"]] for b in buildings}
    for b in buildings:
        others = unary_union([g for o in buildings if o is not b for g in shapes[o["id"]]])
        rooms = [Polygon(r["poly"]) for r in b["rooms"]]
        core = {}   # per floor: the building without its narrow parts
        for f in b["floors"]:
            here = unary_union([g for x, g in zip(b["blocks"], shapes[b["id"]]) if f in x["floors"]])
            core[f] = here.buffer(-LINK_WIDTH / 2, join_style=2).buffer(LINK_WIDTH / 2, join_style=2).buffer(0.05, join_style=2)
        if 0 in core and 1 in core:   # underground parts beyond the building's body (e.g. stores under a courtyard)
            core[0] = core[0].intersection(core[1].buffer(0.5, join_style=2))
        out = []
        for x, g in zip(b["blocks"], shapes[b["id"]]):
            wide = unary_union([core[f] for f in x["floors"]])   # narrow on every floor it has
            links = [p for p in polys(g.difference(wide)) if p.area >= 8 and p.distance(others) < 0.6
                     and not any(r.intersection(p).area > 1 for r in rooms)]   # a part with rooms is building
            if not links:
                out.append(x)
                continue
            for p in polys(tidy(unary_union(links))):
                out.append({"poly": coords(p.exterior), "floors": x["floors"], "link": True})
            for p in polys(tidy(g.difference(unary_union(links)))):
                if p.area >= 2:
                    piece = {"poly": coords(p.exterior), "floors": x["floors"]}
                    holes = [coords(h) for h in p.interiors if Polygon(h).area > MAX_FILLED_HOLE]
                    if holes:
                        piece["holes"] = holes
                    out.append(piece)
        b["blocks"] = out


def block_union(b, floor):
    return unary_union([Polygon(x["poly"], x.get("holes", [])) for x in b["blocks"] if floor in x["floors"]])


DOOR_HALF = 1.4          # m: half the drawn door width (2.8 m)
DOOR_EDGE = 0.2          # m: a door keeps this far from the end of its wall
DOOR_SPACING = 4.0       # m: doors closer than this (any building) are one entrance


def wall_segments(g):
    """Straight wall pieces of a footprint (outer edges and courtyard edges), long enough to hold a door."""
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)
            for a, b in zip(c, c[1:]):
                if math.dist(a, b) >= 2 * (DOOR_HALF + DOOR_EDGE):
                    yield a, b


def outside_doors(b, doors, everything, placed):
    """The plan's doors to the outside (and EXTRA_DOORS), each put on a straight stretch of this building's wall on
    its floor: not on a corner, square to the wall, facing out, with nothing built in front of its whole width, and
    not on top of another door (`placed`: doors of all buildings so far). Only doors at ground level
    (ENTRANCE_FLOORS; floors 0 and 1 elsewhere: the campus slopes, the main entrance is on floor 1) and only the
    lowest of doors stacked above each other (the upper ones open onto terraces and balconies)."""
    out = []
    extra = [{"b": bid, "f": f, "x": x, "z": z} for bid, f, x, z, _ in EXTRA_DOORS]
    plan_doors = [d for d in doors if d["b"] not in MANUAL_DOORS]
    for d in sorted(extra + plan_doors, key=lambda d: d["f"]):
        if d["b"] != b["id"] or d["f"] not in b["floors"] or d["f"] not in ENTRANCE_FLOORS.get(b["id"], {0, 1}):
            continue
        here = block_union(b, d["f"])
        pt = Point(d["x"], d["z"])
        best = None
        for a, c in wall_segments(here):
            seg = LineString([a, c])
            dist = seg.distance(pt)
            if dist <= 1.5 and (best is None or dist < best[0]):
                best = (dist, a, c)
        if best is None:
            continue                                   # no straight wall long enough near it
        _, (ax, az), (cx, cz) = best
        length = math.dist((ax, az), (cx, cz))
        tx, tz = (cx - ax) / length, (cz - az) / length
        along = min(max((d["x"] - ax) * tx + (d["z"] - az) * tz, DOOR_HALF + DOOR_EDGE), length - DOOR_HALF - DOOR_EDGE)
        x, z = ax + tx * along, az + tz * along
        nx, nz = -tz, tx                               # square to the wall, pointing out of the building
        if here.contains(Point(x + nx * 0.6, z + nz * 0.6)):
            nx, nz = -nx, -nz
        front = [Point(x + tx * k + nx * 0.6, z + tz * k + nz * 0.6) for k in (-DOOR_HALF, 0, DOOR_HALF)]
        if any(everything[d["f"]].contains(q) for q in front):
            continue                                   # something built in front of it: not an outside door
        if any(e["floor"] == d["f"] and math.dist((e["x"], e["z"]), (x, z)) < 5 for e in b.get("entrances", [])):
            continue                                   # the main entrance has its own marker
        if any(math.dist((o["x"], o["z"]), (x, z)) < DOOR_SPACING for o in out + placed):
            continue
        out.append({"x": round(x, 2), "z": round(z, 2), "floor": d["f"], "dir": [round(nx, 3), round(nz, 3)]})
    placed.extend(out)
    return out


def place_machines(buildings):
    """Puts each machine at the free spot nearest to where it roughly is, its back to the nearest wall."""
    placed = []
    for kind, x, z, *fixed in MACHINES:
        want = Point(x, z)
        b = min(buildings, key=lambda b: block_union(b, MACHINE_FLOOR).distance(want))
        here = block_union(b, MACHINE_FLOOR)
        rooms = [Polygon(r["poly"], r.get("holes", [])) for r in b["rooms"]
                 if r["floor"] <= MACHINE_FLOOR < r["floor"] + r.get("storeys", 1)]
        walkable = here.difference(unary_union(rooms)) if rooms else here
        keep_clear = [Point(d["x"], d["z"]).buffer(2.5) for d in b["doors"] + b.get("entrances", [])
                      if d["floor"] == MACHINE_FLOOR]
        keep_clear += [Point(m["x"], m["z"]).buffer(1.2) for m in placed if m["building"] == b["id"]]
        free = walkable.buffer(-0.6, join_style=2)
        if keep_clear:
            free = free.difference(unary_union(keep_clear))
        if fixed:
            placed.append({"kind": kind, "building": b["id"], "floor": MACHINE_FLOOR, "x": x, "z": z,
                           "dir": list(fixed[0])})
            continue
        spot = want if free.contains(want) else nearest_points(free, want)[0]
        # back against the nearest wall, facing the corridor (if that spot is free too)
        edge = walkable.boundary
        at = edge.project(spot)
        wall = edge.interpolate(at)
        p0, p1 = edge.interpolate(at - 0.4), edge.interpolate(at + 0.4)
        n = math.hypot(p1.x - p0.x, p1.y - p0.y) or 1
        nx, nz = -(p1.y - p0.y) / n, (p1.x - p0.x) / n
        if not walkable.contains(Point(wall.x + nx * 0.3, wall.y + nz * 0.3)):
            nx, nz = -nx, -nz
        gap = OUTER_WALL_GAP if here.boundary.distance(wall) < 0.05 else MACHINE_GAP
        snug = Point(wall.x + nx * gap, wall.y + nz * gap)
        if walkable.buffer(-0.3, join_style=2).contains(snug) and not any(k.contains(snug) for k in keep_clear):
            spot = snug
        placed.append({"kind": kind, "building": b["id"], "floor": MACHINE_FLOOR, "x": round(spot.x, 2),
                       "z": round(spot.y, 2), "dir": [round(nx, 3), round(nz, 3)]})
    for b in buildings:
        mine = [{k: v for k, v in m.items() if k != "building"} for m in placed if m["building"] == b["id"]]
        if mine:
            b["machines"] = mine


def pillars(b):
    """Legs for a building whose upper floor overhangs its ground floor: one at every outer corner of the overhang."""
    ground, upper = block_union(b, 0), block_union(b, 1)
    legs = []
    for p in polys(upper.simplify(1.0)):
        pts = coords(p.exterior)
        if not Polygon(pts).exterior.is_ccw:
            pts = pts[::-1]
        for k, (x, z) in enumerate(pts):
            (px, pz), (qx, qz) = pts[k - 1], pts[(k + 1) % len(pts)]
            ax, az, bx, bz = px - x, pz - z, qx - x, qz - z
            la, lb = math.hypot(ax, az) or 1, math.hypot(bx, bz) or 1
            half = PILLAR_SIZE / 2 + 0.2               # the leg sits just inside the corner
            cx, cz = x + (ax / la + bx / lb) * half, z + (az / la + bz / lb) * half
            if not p.contains(Point(cx, cz)):          # inner corner: no leg
                continue
            if ground.buffer(0.5).contains(Point(cx, cz)):
                continue                               # the ground floor is already under it
            leg = rotate(Point(cx, cz).buffer(PILLAR_SIZE / 2, cap_style=3), math.atan2(bz, bx), use_radians=True)
            legs.append({"poly": coords(leg.exterior), "to_floor": 1})
    return legs


def room_entry(s, floor, storeys, geom):
    name = s["name"].strip()
    code = s["code"]
    hall = re.match(r"Hörsaal\s*([0-9A-Z]+)", name)
    bookable = bool(hall) or name in BOOKABLE_NAMES
    if hall:
        kind, label, eng = "seminar", f"HS {hall.group(1)}", "Lecture hall"
    elif s["type"] == TEACHING or name in BOOKABLE_NAMES:
        kind, label, eng = "seminar", None, BOOKABLE_NAMES.get(name) or OTHER_NAMES.get(name, name)
    elif s["type"] == WC:
        kind, label, eng = "wc", None, "WC"
    else:
        kind, label, eng = "office", None, OTHER_NAMES.get(name, name or "Office")
    cap = s["cap"] or (max(4, int(geom.area / 2)) if bookable else (2 if geom.area < 25 else 4) if kind == "office" else 0)
    if code == BOARD_ROOM:   # the sensor-board room: a bookable seminar room in our system
        kind, label, eng, bookable, cap = "seminar", None, "Seminar room", True, 51
    shrunk = geom.buffer(-0.12, join_style=2).simplify(ROOM_TOLERANCE)   # small gap between neighbours, fewer points
    if kind == "office":                       # offices are drawn as clean boxes
        box_ = shrunk.minimum_rotated_rectangle
        if box_.area and shrunk.area / box_.area >= BOX_FILL:
            shrunk = box_.intersection(geom.buffer(-0.12, join_style=2)).simplify(ROOM_TOLERANCE)
    if shrunk.is_empty:
        return None
    shrunk = max(rings(set_precision(shrunk, 0.01)), key=lambda p: p.area, default=geom)
    c = shrunk.centroid
    x0, z0, x1, z1 = shrunk.bounds
    r = {"id": code, "floor": floor, "x": round(c.x, 2), "z": round(c.y, 2), "w": round(x1 - x0, 2),
         "d": round(z1 - z0, 2), "poly": coords(shrunk.exterior), "capacity": cap, "type": kind,
         **({"holes": [coords(i) for i in shrunk.interiors if Polygon(i).area > 1]} if shrunk.interiors else {}),
         "bookable": bookable, "name": eng}
    if label:
        r["label"] = label
    if storeys > 1:
        r["storeys"] = storeys
    return r


def final_clip(b):
    """Last guarantee against intersections: every room lies inside its building's blocks on its floors and overlaps
    no room placed before it (teaching rooms first, so they keep their full shape)."""
    blocks = [(Polygon(x["poly"], x.get("holes", [])), set(x["floors"])) for x in b["blocks"]]
    order = sorted(b["rooms"], key=lambda r: (not r["bookable"], r["type"] != "seminar", r["id"]))
    placed, keep = [], []
    for r in order:
        span = set(range(r["floor"], r["floor"] + r.get("storeys", 1)))
        inside = unary_union([g for g, fl in blocks if span & fl]).buffer(-0.05, join_style=2)
        g = Polygon(r["poly"], r.get("holes", [])).intersection(inside)
        others = [pg for pg, fl in placed if fl & span]
        if others:
            g = g.difference(unary_union(others).buffer(0.05, join_style=2))
        g = max(rings(set_precision(g, 0.01)), key=lambda p: p.area, default=None)
        if g is None or g.area < 2:
            continue
        x0, z0, x1, z1 = g.bounds
        r.update(poly=coords(g.exterior), x=round(g.centroid.x, 2), z=round(g.centroid.y, 2), w=round(x1 - x0, 2),
                 d=round(z1 - z0, 2))
        holes = [coords(i) for i in g.interiors if Polygon(i).area > 0.05]
        if holes:
            r["holes"] = holes
        else:
            r.pop("holes", None)
        placed.append((g, span))
        keep.append(r)
    b["rooms"] = sorted(keep, key=lambda r: r["id"])


def main():
    plan = json.loads((HERE / "aau_plan.json").read_text(encoding="utf-8"))
    spaces = plan["spaces"]
    buildings = []
    taken = {}   # floor -> what earlier buildings cover (the plan's buildings touch; nothing may overlap)
    for bid, name, height in BUILDINGS:
        # the plan files a few rooms under the wrong building (e.g. a Lakeside room B01.* under Südtrakt): a numbered
        # room belongs here only if its number starts with this building's letter
        mine = [s for s in spaces if s["b"] == bid and (not s["code"] or s["code"].startswith(f"{bid}."))]
        coded = defaultdict(list)
        for s in mine:
            if s["code"]:
                coded[s["f"]].append(poly(s))
        near = {f: unary_union(gs).buffer(1.0) for f, gs in coded.items()}
        by_floor = defaultdict(list)
        for s in mine:   # unnumbered leftovers count only where they touch the building's numbered rooms
            if not is_courtyard(s) and (s["code"] or (s["f"] in near and poly(s).intersects(near[s["f"]]))):
                by_floor[s["f"]].append(poly(s))
        outlines = floor_outlines(by_floor, taken, [(f, pts) for cb, f, pts in CUTS if cb == bid])
        # rooms: one per code; a room on several floors (lecture halls) is one tall room at its lowest floor
        per_code = defaultdict(list)
        for s in mine:
            name_s = s["name"].strip()
            teaching = s["type"] == TEACHING or name_s.startswith("Hörsaal") or s["code"] == BOARD_ROOM
            office = s["type"] == OFFICE and name_s in REAL_OFFICES and poly(s).area >= MIN_OFFICE_AREA and is_box(poly(s))
            if (teaching or office) and s["code"] and s["code"] not in SKIP_ROOMS and poly(s).area >= 3:
                per_code[s["code"]].append(s)
        rooms, placed = [], defaultdict(list)
        teaching_first = sorted(per_code.items(), key=lambda kv: (kv[1][0]["type"] != TEACHING, kv[0]))
        for code, items in teaching_first:
            floors = sorted({s["f"] for s in items})
            biggest = max(items, key=lambda s: poly(s).area)
            span = range(floors[0], floors[-1] + 1)
            # inside its building on all its floors (a two-storey hall like HS A keeps its whole fan)
            geom = poly(biggest).intersection(unary_union([outlines[f] for f in span if f in outlines]))
            for f in span:                                                  # and not into a room already placed
                if placed[f]:
                    geom = geom.difference(unary_union(placed[f]))
            geom = max(rings(geom), key=lambda p: p.area, default=None)
            if geom is None or geom.area < 3:
                continue
            r = room_entry(biggest, floors[0], len(span), geom)
            if r:
                rooms.append(r)
                for f in span:
                    placed[f].append(geom)
        rooms.sort(key=lambda r: r["id"])
        b = {"id": bid, "name": name, "floors": sorted(by_floor), "floor_height": height,
             "blocks": shell_blocks(outlines, taken), "rooms": rooms,
             "source": "campusplan.aau.at floor plans (tools/campus3d/aau_plan.json), real room numbers"}
        if bid == "Z":   # main entrance: the outer wall of "Eingang" (Z.1.R0) on floor 1, facing east
            door = next(s for s in mine if s["code"] == "Z.1.R0")
            g = poly(door)
            b["entrances"] = [{"x": round(g.bounds[2], 2), "z": round(g.centroid.y, 2), "floor": door["f"],
                               "dir": [1, 0], "main": True}]
        for f in b["floors"]:
            g = block_union(b, f)
            taken[f] = g if f not in taken else taken[f].union(g)
        if bid in PILLARS:
            b["pillars"] = pillars(b)
        final_clip(b)
        buildings.append(b)
    split_links(buildings)
    everything = {f: unary_union([block_union(b, f) for b in buildings]) for f in range(4)}
    placed = []
    for b in buildings:
        b["doors"] = outside_doors(b, plan.get("doors", []), everything, placed)
    place_machines(buildings)
    campus = {"campus": "AAU Klagenfurt", "units": "metres; x along the campus grid (~east), z across (~south); "
              "origin = centre of building V", "north": plan["north"], "buildings": buildings}
    OUT.write_text(json.dumps(campus, ensure_ascii=False, indent=1), encoding="utf-8")
    for b in buildings:
        print(b["id"], b["floors"], len(b["blocks"]), "blocks,", len(b["rooms"]), "rooms,",
              sum(r["bookable"] for r in b["rooms"]), "bookable,", len(b["doors"]), "doors,", len(b.get("pillars", [])),
              "legs")


if __name__ == "__main__":
    main()
