"""Walking routes for the 3D map's "Take me there": from the main entrance (or, for far rooms, the nearest outside door)
to every lecture hall and seminar room, along corridors, halls, bridges and stairs. Adds "routes" to
web/map3d/campus.json (run after gen_campus.py): {room id: {from: "main" | "door", start: [x, z, floor],
points: [[x, z, floor, y], ...], length: metres}}, y = the floor's height in the building the point is in.

- Walkable: the plan's corridors, halls, entrances, bridges, stairwells and lifts (tools/campus3d/aau_plan.json),
  and the library's reading rooms, joined across door openings; courtyards, other rooms and offices are not.
- Stairs: the stair flights found in the plan's drawing lines (fetch_plan.py). Two floors are connected only where a
  flight appears on both floors at the same spot (a stairwell); a floor change costs STAIR_COST metres extra.
- Start: the main entrance, unless the walk from it is longer than FAR metres; then the closest outside door
  (a door on floor 0 or 1, gen_campus.py) if that walk is shorter.
- End: the room's door (door swings in the plan), else the middle of the wall it shares with a corridor.

Usage: uv run --with shapely --with scipy python tools/campus3d/gen_routes.py
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely import contains_xy
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = Path(__file__).parent
CAMPUS = HERE.parent.parent / "web" / "map3d" / "campus.json"
CELL = 0.5            # m: grid step
JOIN = 0.3            # m: walkable spaces are grown this much, so neighbours join across walls with a door opening
WALL_PENALTY = 1.6    # cost factor for cells closer than 0.7 m to a wall: paths keep to the middle of corridors
STAIR_COST = 8.0      # extra metres for one floor up or down
STAIR_LINK = 3.0      # m: flights on two floors this close belong to one stairwell
FAR = 150.0           # m: rooms farther than this from the main entrance start at the closest outside door
WALKABLE_TYPES = {44, 79, 33}   # corridor/hall, stairs, lift (+ "Gang" filed as type 94)
WALK_THROUGH = {"Lesesaal", "Leseraum"}   # library reading rooms: open halls some group rooms are entered from
COURTYARD_MIN_AREA = 150


def poly(pts, holes=()):
    g = Polygon(pts, holes)
    return g if g.is_valid else make_valid(g).buffer(0)


def walkable_space(s):
    g = poly(s["poly"], s.get("holes", []))
    if s["type"] == 44 and not s["code"] and g.area > COURTYARD_MIN_AREA:
        return None                                          # a courtyard
    if s["type"] in WALKABLE_TYPES or (s["type"] == 94 and s["name"] == "Gang") or s["name"] in WALK_THROUGH:
        return g
    return None


def main():
    plan = json.loads((HERE / "aau_plan.json").read_text(encoding="utf-8"))
    campus = json.loads(CAMPUS.read_text(encoding="utf-8"))
    floors = sorted({s["f"] for s in plan["spaces"]})
    flights = {f: [poly(st["poly"]) for st in plan["stairs"] if st["f"] == f] for f in floors}
    walk = {}
    for f in floors:
        parts = [g for s in plan["spaces"] if s["f"] == f and (g := walkable_space(s)) is not None]
        parts += [g.buffer(0.4) for g in flights[f]]
        walk[f] = unary_union(parts).buffer(JOIN, join_style=2)
    x0, z0, x1, z1 = unary_union(list(walk.values())).bounds
    xs, zs = np.arange(x0, x1 + CELL, CELL), np.arange(z0, z1 + CELL, CELL)
    nx, nz = len(xs), len(zs)
    gx, gz = np.meshgrid(xs, zs)                             # [row = z, col = x]
    masks = {f: contains_xy(walk[f], gx, gz) for f in floors}
    ids = {}                                                 # (floor, row, col) -> node; one array per floor
    count = 0
    for f in floors:
        idx = np.full(masks[f].shape, -1, dtype=np.int64)
        n = int(masks[f].sum())
        idx[masks[f]] = np.arange(count, count + n)
        ids[f] = idx
        count += n
    node_xyf = np.zeros((count, 3))
    for f in floors:
        r, c = np.nonzero(masks[f])
        node_xyf[ids[f][r, c]] = np.stack([xs[c], zs[r], np.full(len(r), f)], axis=1)

    rows, cols, costs = [], [], []
    for f in floors:
        m, idx = masks[f], ids[f]
        near_wall = distance_transform_edt(m) * CELL < 0.7
        factor = np.where(near_wall, WALL_PENALTY, 1.0)
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):        # each neighbour pair once
            src = (slice(max(0, -dr), nz - max(0, dr)), slice(max(0, -dc), nx - max(0, dc)))
            dst = (slice(max(0, dr), nz - max(0, -dr)), slice(max(0, dc), nx - max(0, -dc)))
            ok = m[src] & m[dst]
            step = CELL * math.hypot(dr, dc)
            rows.append(idx[src][ok])
            cols.append(idx[dst][ok])
            costs.append(step * (factor[src][ok] + factor[dst][ok]) / 2)

    def nearest_node(x, z, f, within=6.0):
        if f not in masks:
            return None
        r, c = np.nonzero(masks[f])
        d = (xs[c] - x) ** 2 + (zs[r] - z) ** 2
        k = int(np.argmin(d)) if len(d) else None
        return None if k is None or d[k] > within ** 2 else int(ids[f][r[k], c[k]])

    stair_links = []
    for f in floors:
        if f + 1 not in flights:
            continue
        for a in flights[f]:
            for b in flights[f + 1]:
                if a.distance(b) <= STAIR_LINK:
                    na, nb = nearest_node(a.centroid.x, a.centroid.y, f), nearest_node(b.centroid.x, b.centroid.y, f + 1)
                    if na is not None and nb is not None:
                        horizontal = math.dist(node_xyf[na][:2], node_xyf[nb][:2])
                        rows.append(np.array([na])); cols.append(np.array([nb]))
                        costs.append(np.array([horizontal + STAIR_COST]))
                        stair_links.append((na, nb))
    # A building with no stairwell drawn on both floors of a pair (Nexus: its atrium stairs are drawn on floors 1-2
    # only) still has stairs: a flight right above (or below) a corridor of the other floor connects the two there.
    buildings_of = [(Polygon(bl["poly"]), b["id"]) for b in campus["buildings"] for bl in b["blocks"]]

    def building_at(g):
        c = g.centroid
        return next((bid for p, bid in buildings_of if p.contains(c)), None)

    paired = set()
    for f in floors:
        for a in flights.get(f, []):
            if any(a.distance(b) <= STAIR_LINK for b in flights.get(f + 1, [])):
                paired.add((building_at(a), f))
    for f in floors:
        if f + 1 not in flights:
            continue
        for g, here, there in [(g, f + 1, f) for g in flights[f + 1]] + [(g, f, f + 1) for g in flights[f]]:
            bid = building_at(g)
            low = min(here, there)
            if bid is None or (bid, low) in paired or walk[there].distance(g.centroid) > 1.5:
                continue
            na, nb = nearest_node(g.centroid.x, g.centroid.y, here), nearest_node(g.centroid.x, g.centroid.y, there)
            if na is not None and nb is not None:
                rows.append(np.array([na])); cols.append(np.array([nb]))
                costs.append(np.array([math.dist(node_xyf[na][:2], node_xyf[nb][:2]) + STAIR_COST]))
                stair_links.append((na, nb))
    graph = coo_matrix((np.concatenate(costs), (np.concatenate(rows), np.concatenate(cols))), shape=(count, count)).tocsr()

    # starts: the main entrance, then every outside door on floor 0/1
    main_entrance = next(e for b in campus["buildings"] for e in b.get("entrances", []) if e.get("main"))
    starts = [("main", main_entrance)] + [("door", d) for b in campus["buildings"] for d in b.get("doors", [])]
    start_nodes = []
    for kind, d in starts:
        inward = (d["x"] - d["dir"][0] * 1.0, d["z"] - d["dir"][1] * 1.0)
        n = nearest_node(*inward, d["floor"])
        if n is not None:
            start_nodes.append((kind, d, n))
    dist, pred = dijkstra(graph, directed=False, indices=[n for _, _, n in start_nodes], return_predecessors=True)

    doors_by_room = {}
    for d in plan["room_doors"]:
        doors_by_room.setdefault(d["code"], []).append(d)
    spaces_by_code = {}
    for s in plan["spaces"]:
        if s["code"]:
            spaces_by_code.setdefault(s["code"], []).append(s)
    routes = {}
    for b in campus["buildings"]:
        for room in b["rooms"]:
            if room["type"] != "seminar":                    # lecture halls and seminar rooms only, no offices
                continue
            span = range(room["floor"], room["floor"] + room.get("storeys", 1))
            goals = []                                       # (node, door point)
            for d in doors_by_room.get(room["id"], []):
                if d["f"] in span and (n := nearest_node(d["x"], d["z"], d["f"], within=2.0)) is not None:
                    goals.append((n, (d["x"], d["z"], d["f"])))
            if not goals:                                    # no door found: the middle of the wall next to a corridor
                for s in spaces_by_code.get(room["id"], []):
                    if s["f"] not in span:
                        continue
                    g = poly(s["poly"], s.get("holes", []))
                    shared = g.buffer(0.6).intersection(walk[s["f"]])
                    if not shared.is_empty:
                        p = shared.representative_point()
                        if (n := nearest_node(p.x, p.y, s["f"], within=2.0)) is not None:
                            goals.append((n, (p.x, p.y, s["f"])))
            if not goals:
                print("no way in:", room["id"])
                continue
            options = []
            for i, (kind, d, _) in enumerate(start_nodes):
                n, door = min(goals, key=lambda g: dist[i, g[0]])
                if math.isfinite(dist[i, n]):
                    options.append((dist[i, n], i, kind, d, n, door))
            if not options:
                print("unreachable:", room["id"])
                continue
            from_main = [o for o in options if o[2] == "main"]
            best = min(options)
            choice = from_main[0] if from_main and (from_main[0][0] <= FAR or from_main[0][0] <= best[0]) else best
            length, i, kind, d, n, door = choice
            chain = []
            while n >= 0:
                chain.append(n)
                n = pred[i, n]
            chain.reverse()
            points = [(d["x"], d["z"], d["floor"])] + [tuple(node_xyf[k]) for k in chain] + [door]
            routes[room["id"]] = {"from": kind, "start": [round(d["x"], 2), round(d["z"], 2), d["floor"]],
                                  "points": simplify(points, walk), "length": round(float(length), 1)}
    # height of each point: its floor in the building it is in (buildings have different floor heights)
    pieces = [(Polygon(bl["poly"]), set(bl["floors"]), b["floor_height"]) for b in campus["buildings"] for bl in b["blocks"]]
    for r in routes.values():
        for p in r["points"]:
            here = [(g.distance(Point(p[0], p[1])), h) for g, fl, h in pieces if p[2] in fl]
            p.append(round(p[2] * min(here)[1], 2) if here else round(p[2] * 4.0, 2))
    campus["routes"] = routes
    CAMPUS.write_text(json.dumps(campus, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds = [r["from"] for r in routes.values()]
    print(f"{len(routes)} routes ({kinds.count('main')} from the main entrance, {kinds.count('door')} from another door), "
          f"{len(stair_links)} stair links")


def simplify(points, walk):
    """Straightens each floor's part of the path (a line of sight inside the corridors, kept off the walls), keeps the
    floor changes (stairs) and rounds to cm."""
    out, i = [points[0]], 0
    inner = {f: g.buffer(-0.35) for f, g in walk.items()}
    while i < len(points) - 1:
        j = i + 1
        f = points[i][2]
        while (j + 1 < len(points) and points[j + 1][2] == f
               and inner[f].covers(LineString([points[i][:2], points[j + 1][:2]]))):
            j += 1
        out.append(points[j])
        i = j
    return [[round(float(x), 2), round(float(z), 2), int(f)] for x, z, f in out]


if __name__ == "__main__":
    main()
