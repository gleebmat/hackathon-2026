"""Download the AAU floor plans (rooms of buildings V, N, Z, L, S and O) from campusplan.aau.at's public GeoServer
and store them, aligned to our map frame, in tools/campus3d/aau_plan.json (gen_campus.py builds the 3D map from it).

Frame: real metres; origin = centre of building V; x along the long side of building N (the campus grid, roughly
east), z perpendicular to it (roughly south). `north` is true north in that frame (for the compass).

Usage: uv run --with shapely python tools/campus3d/fetch_plan.py
Source: https://campusplan.aau.at/geoserver/wfs, layers indrz:spaces_<floor>_0 (EPSG:3857).
"""
import json
import math
import urllib.request
from pathlib import Path

from shapely.affinity import affine_transform, rotate
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

HERE = Path(__file__).parent
WFS = ("https://campusplan.aau.at/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature"
       "&typeNames=indrz:{layer}_{floor}_0&outputFormat=application/json&srsName=EPSG:3857")
FLOORS = (0, 1, 2, 3)
BUILDINGS = {"Vorstufe": "V", "Nordtrakt": "N", "Zentraltrakt": "Z", "Bibliothek": "L", "Südtrakt": "S",
             "Osttrakt": "O"}
K = math.cos(math.radians(46.617))   # web-mercator metres -> real metres at Klagenfurt


def fetch(floor, layer="spaces"):
    req = urllib.request.Request(WFS.format(floor=floor, layer=layer), headers={"User-Agent": "campus-map-builder"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["features"]


def outside_doors(spaces, frame):
    """Doors to the outside: door swing arcs (quarter circles of about 1 m in the plan's drawing lines) whose hinge side
    lies on a building's outer wall, courtyard walls included. Double doors count once."""
    from shapely.geometry import Point
    doors = []
    for floor in FLOORS:
        here = [s for s in spaces if s["f"] == floor]
        if not here:
            continue
        per_building = {}
        for s in here:
            if not (s["type"] == 44 and not s["code"] and s["g"].area > 150):   # courtyards stay outside
                per_building.setdefault(s["b"], []).append(s["g"])
        outlines = {b: frame(unary_union(gs).buffer(0.3).buffer(-0.3)) for b, gs in per_building.items()}
        found = []
        for f in fetch(floor, "cartolines"):
            geom = affine_transform(shape(f["geometry"]), [K, 0, 0, -K, 0, 0])
            for line in getattr(geom, "geoms", [geom]):
                pts = list(line.coords)
                if len(pts) < 5:
                    continue
                length, chord = line.length, math.dist(pts[0], pts[-1])
                if not (1.0 < length < 2.6 and 0.6 < chord / length < 0.95):   # quarter-circle swing of a door leaf
                    continue
                arc = frame(line)
                a, b = arc.coords[0], arc.coords[-1]
                for bid, outline in outlines.items():
                    edge = outline.exterior if outline.geom_type == "Polygon" else None
                    walls = outline.boundary
                    # one end of the arc is on the wall (the leaf when closed), the other end swings into the room
                    ends = sorted([(walls.distance(Point(a)), a), (walls.distance(Point(b)), b)])
                    if ends[0][0] > 0.35 or not outline.buffer(1.5).contains(arc):
                        continue
                    hinge = walls.interpolate(walls.project(Point(ends[0][1])))
                    # the door is to the outside if just beyond the wall there is no building
                    probe_in = Point(ends[1][1])
                    nx, nz = hinge.x - probe_in.x, hinge.y - probe_in.y
                    norm = math.hypot(nx, nz) or 1
                    outside = Point(hinge.x + nx / norm * 0.8, hinge.y + nz / norm * 0.8)
                    if not outline.contains(probe_in) or any(o.contains(outside) for o in outlines.values()):
                        continue
                    found.append((bid, hinge.x, hinge.y, nx / norm, nz / norm))
                    break
        for bid, x, z, dx, dz in found:   # merge double doors and repeated arcs
            if any(d["b"] == bid and d["f"] == floor and math.dist((d["x"], d["z"]), (x, z)) < 2.5 for d in doors):
                continue
            doors.append({"b": bid, "f": floor, "x": round(x, 2), "z": round(z, 2), "dir": [round(dx, 3), round(dz, 3)]})
    return doors


def main():
    spaces = []
    for floor in FLOORS:
        for f in fetch(floor):
            p = f["properties"]
            bid = BUILDINGS.get(p["building_name"])
            if not bid or not f["geometry"]:
                continue
            g = affine_transform(shape(f["geometry"]), [K, 0, 0, -K, 0, 0])   # metres, x east, z south
            spaces.append({"b": bid, "f": p["floor_num"], "code": p["room_code"], "type": p["space_type_id"],
                           "name": p["short_name"] or p["room_description"] or "", "cap": p["capacity"], "g": g})
    # frame: centre of V, x along N's long side
    v = unary_union([s["g"] for s in spaces if s["b"] == "V"]).minimum_rotated_rectangle
    n = unary_union([s["g"] for s in spaces if s["b"] == "N"]).minimum_rotated_rectangle
    pts = list(n.exterior.coords)[:4]
    _, a, b = max((math.dist(pts[i], pts[i + 1]), pts[i], pts[i + 1]) for i in range(3))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    if math.cos(ang) < 0:
        ang += math.pi
    cx, cz = v.centroid.x, v.centroid.y
    cos, sin = math.cos(-ang), math.sin(-ang)

    def frame(g):
        return affine_transform(g, [cos, -sin, sin, cos, -(cx * cos - cz * sin), -(cx * sin + cz * cos)])

    north = rotate(shape({"type": "Point", "coordinates": [0, -1]}), -ang, origin=(0, 0), use_radians=True)
    out = []
    for s in spaces:
        g = frame(s["g"]).simplify(0.05)
        for part in getattr(g, "geoms", [g]):
            if part.area < 0.5:
                continue
            ring = [[round(x, 2), round(z, 2)] for x, z in list(part.exterior.coords)[:-1]]
            holes = [[[round(x, 2), round(z, 2)] for x, z in list(i.coords)[:-1]] for i in part.interiors]
            out.append({**{k: s[k] for k in ("b", "f", "code", "type", "name", "cap")}, "poly": ring,
                        **({"holes": holes} if holes else {})})
    doors = outside_doors(spaces, frame)
    data = {"source": "campusplan.aau.at GeoServer (indrz:spaces_<floor>_0, door arcs from indrz:cartolines_<floor>_0)",
            "units": "metres; x along N, z across", "north": [round(north.x, 4), round(north.y, 4)],
            "spaces": out, "doors": doors}
    (HERE / "aau_plan.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(out)} spaces, {len(doors)} outside doors, grid angle {math.degrees(ang):.2f} deg, north {data['north']}")


if __name__ == "__main__":
    main()
