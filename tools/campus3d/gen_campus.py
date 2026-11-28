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
import re
from collections import defaultdict
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union
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
                  "Omansaal": "Seminar room", "Studierendenarbeitsraum": "Student work room"}
OTHER_NAMES = {"Lesesaal": "Reading room", "Leseraum": "Reading room", "Labor": "Lab", "Katalograum": "Catalogue room",
               "Büro": "Office", "Besprechungsraum": "Meeting room", "Küche": "Kitchen", "Kopierraum": "Copy room"}
BOARD_ROOM = "Z.1.04"
COURTYARD_MIN_AREA = 150   # unnamed "corridor" spaces this big are courtyards, not building


def poly(s):
    g = Polygon(s["poly"], s.get("holes", []))
    return g if g.is_valid else max(rings(make_valid(g)), key=lambda p: p.area, default=g.buffer(0))   # repair


def is_courtyard(s):
    return s["type"] == CORRIDOR and not s["code"] and poly(s).area > COURTYARD_MIN_AREA


def rings(geom):
    for p in getattr(geom, "geoms", [geom]):
        if isinstance(p, Polygon) and p.area > 2:
            yield p


def coords(ring):
    return [[round(x, 2), round(z, 2)] for x, z in list(ring.coords)[:-1]]


def floor_outlines(by_floor, taken):
    """Each floor's outline: its spaces joined (small gaps closed), minus what earlier buildings already cover."""
    out = {}
    for f, gs in by_floor.items():
        g = unary_union(gs).buffer(0.25, join_style=2).buffer(-0.25, join_style=2).simplify(0.03)
        if f in taken:
            g = g.difference(taken[f])
        out[f] = unary_union(list(rings(g)))
    return out


def shell_blocks(outlines):
    """Building pieces with the floors they exist on: the floor outlines are cut into cells by all their edges, cells
    with the same floors are joined; every run of consecutive floors becomes one block."""
    lines = unary_union([g.boundary for g in outlines.values()])
    groups = defaultdict(list)
    for cell in polygonize(lines):
        pt = cell.representative_point()
        fl = tuple(f for f in sorted(outlines) if outlines[f].contains(pt))
        if fl:
            groups[fl].append(cell)
    blocks = []
    for fl, cells in groups.items():
        runs, run = [], [fl[0]]
        for f in fl[1:]:
            if f == run[-1] + 1:
                run.append(f)
            else:
                runs.append(run)
                run = [f]
        runs.append(run)
        geom = set_precision(unary_union(cells).buffer(0.02, join_style=2).buffer(-0.02, join_style=2), 0.01)
        for p in rings(geom):
            for r in runs:
                b = {"poly": coords(p.exterior), "floors": r}
                holes = [coords(i) for i in p.interiors if Polygon(i).area > 1]
                if holes:
                    b["holes"] = holes
                blocks.append(b)
    return blocks


def room_entry(s, floor, storeys, geom):
    name = s["name"].strip()
    code = s["code"]
    hall = re.match(r"Hörsaal\s*([0-9A-Z]+)", name)
    bookable = bool(hall) or name in BOOKABLE_NAMES
    if hall:
        kind, label, eng = "seminar", f"HS {hall.group(1)}", "Lecture hall"
    elif s["type"] == TEACHING or name in BOOKABLE_NAMES:
        kind, label, eng = "seminar", "Omansaal" if name == "Omansaal" else None, BOOKABLE_NAMES.get(name) or OTHER_NAMES.get(name, name)
    elif s["type"] == WC:
        kind, label, eng = "wc", None, "WC"
    else:
        kind, label, eng = "office", None, OTHER_NAMES.get(name, name or "Office")
    cap = s["cap"] or (max(4, int(geom.area / 2)) if bookable else (2 if geom.area < 25 else 4) if kind == "office" else 0)
    if code == BOARD_ROOM:   # the sensor-board room: a bookable seminar room in our system
        kind, label, eng, bookable, cap = "seminar", None, "Seminar room", True, 51
    shrunk = geom.buffer(-0.12, join_style=2)   # small gap between neighbouring rooms
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
        outlines = floor_outlines(by_floor, taken)
        # rooms: one per code; a room on several floors (lecture halls) is one tall room at its lowest floor
        per_code = defaultdict(list)
        for s in mine:
            name_s = s["name"].strip()
            keep = (s["type"] in (TEACHING, OFFICE, WC) or name_s.startswith("Hörsaal")) and s["code"]
            if keep and poly(s).area >= 3:
                per_code[s["code"]].append(s)
        rooms, placed = [], defaultdict(list)
        teaching_first = sorted(per_code.items(), key=lambda kv: (kv[1][0]["type"] != TEACHING, kv[0]))
        for code, items in teaching_first:
            floors = sorted({s["f"] for s in items})
            biggest = max(items, key=lambda s: poly(s).area)
            span = range(floors[0], floors[-1] + 1)
            geom = poly(biggest).intersection(outlines[floors[0]])        # inside its building
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
        for f, g in outlines.items():
            taken[f] = g if f not in taken else taken[f].union(g)
        b = {"id": bid, "name": name, "floors": sorted(by_floor), "floor_height": height,
             "blocks": shell_blocks(outlines), "rooms": rooms,
             "source": "campusplan.aau.at floor plans (tools/campus3d/aau_plan.json), real room numbers"}
        if bid == "Z":   # main entrance: the outer wall of "Eingang" (Z.1.R0) on floor 1, facing east
            door = next(s for s in mine if s["code"] == "Z.1.R0")
            g = poly(door)
            b["entrances"] = [{"x": round(g.bounds[2], 2), "z": round(g.centroid.y, 2), "floor": door["f"],
                               "dir": [1, 0], "main": True}]
        final_clip(b)
        buildings.append(b)
    campus = {"campus": "AAU Klagenfurt", "units": "metres; x along the campus grid (~east), z across (~south); "
              "origin = centre of building V", "north": plan["north"], "buildings": buildings}
    OUT.write_text(json.dumps(campus, ensure_ascii=False, indent=1), encoding="utf-8")
    for b in buildings:
        print(b["id"], b["floors"], len(b["blocks"]), "blocks,", len(b["rooms"]), "rooms,",
              sum(r["bookable"] for r in b["rooms"]), "bookable")


if __name__ == "__main__":
    main()
